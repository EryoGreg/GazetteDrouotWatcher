"""
Everything to do with actually showing Windows toast notifications.

Uses the `win11toast` package, which wraps the native WinRT toast API.
A couple of non-obvious gotchas discovered during development, both worked
around below:
  - Toast images from an unpackaged script (we're not an installed/signed
    app) must be a LOCAL file path — Windows silently drops remote
    http(s) image URLs with no error. So thumbnails are downloaded to a
    temp-folder cache first (_local_image_path) and only the local path is
    ever passed to the toast.
  - Click-to-open-browser (`on_click=<url>`) works fine as a plain string —
    Windows handles the "launch this URL" activation itself even though
    we're an unpackaged script, no special app registration needed.
"""

import hashlib
import logging
import tempfile
import time
import urllib.request
from pathlib import Path

from win11toast import notify

from . import config

log = logging.getLogger("gazette_watcher")

# win11toast defaults to app_id="Python" (its own hardcoded default), which
# is what shows as the toast's header/sender name for an unpackaged script —
# there's no real Windows app registration involved, so any string works;
# passing this one explicitly on every notify() call below is the whole fix.
APP_ID = "Gazette Drouot Watcher"

# Where downloaded thumbnail images are cached (see _local_image_path).
_IMAGE_CACHE_DIR = Path(tempfile.gettempdir()) / "gazette_watcher_images"


def _local_image_path(url: str) -> str | None:
    """Downloads a remote thumbnail to a local cache file and returns a
    file:// URI to it, or None if the download fails (caller should just
    show the toast without an image in that case, not crash the whole run)."""
    try:
        _IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(url.split("?")[0]).suffix or ".jpg"
        # Cache filename is a hash of the URL — same image URL is never
        # re-downloaded on a later run.
        cached = _IMAGE_CACHE_DIR / f"{hashlib.sha1(url.encode()).hexdigest()}{ext}"
        if not cached.exists():
            # A plain urllib request gets a 403 from gazette-drouot's CDN
            # (it checks for a browser-like User-Agent), so we spoof one.
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                    )
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp, open(cached, "wb") as f:
                f.write(resp.read())
        return cached.as_uri()
    except Exception:
        log.exception("failed to download thumbnail, showing toast without image: %s", url)
        return None


def _notify_article(article: dict):
    """Shows one toast for one article. Clicking it opens the article's URL
    in the user's default browser (handled natively by Windows via on_click)."""
    body = f"Publié le {article['date']}" if article.get("date") else "Date de publication indisponible"
    if article.get("result"):
        body += f" — Résultat {article['result']}"
    if article.get("excerpt"):
        body += f"\n{article['excerpt']}"

    kwargs = {"on_click": article["url"], "app_id": APP_ID}
    if article.get("image"):
        local_image = _local_image_path(article["image"])
        if local_image:
            kwargs["image"] = local_image

    try:
        notify(article["title"], body, **kwargs)
    except Exception:
        # If the image itself is somehow the problem (corrupt download,
        # unsupported format, ...), don't lose the notification entirely —
        # retry once without it.
        log.exception("toast with image failed, retrying without image: %s", article["url"])
        kwargs.pop("image", None)
        notify(article["title"], body, **kwargs)


def notify_new_articles(new_articles: list[dict], rubrique_label: str, listing_url: str):
    """Shows toasts for a batch of new/updated articles from one rubrique.

    new_articles should already be sorted (ascending by id) by the caller —
    the site's own page order isn't reliably chronological, so numeric id
    order is used as a deterministic stand-in for "oldest new -> newest new".

    To avoid flooding the user with notifications if a lot of articles piled
    up at once (e.g. the computer was off for a while), only the first
    config.FLOOD_CAP articles get their own individual toast — anything
    beyond that is collapsed into a single "N more new posts" summary toast
    that opens the rubrique's listing page when clicked.
    """
    if not new_articles:
        return

    shown = new_articles[: config.FLOOD_CAP]
    rest = new_articles[config.FLOOD_CAP :]

    for i, article in enumerate(shown):
        _notify_article(article)
        log.info("notified: %s", article["url"])
        # Space consecutive toasts out so they don't all appear stacked on
        # top of each other at once — skip the wait after the very last one.
        if i < len(shown) - 1 or rest:
            time.sleep(config.NOTIF_GAP_SECONDS)

    if rest:
        notify(
            f"{len(rest)} more new posts — {rubrique_label}",
            "Click to view the listing",
            on_click=listing_url,
            app_id=APP_ID,
        )
        log.info("notified summary: %d more articles on %s", len(rest), rubrique_label)


def notify_first_run_seeded(rubrique_label: str, count: int):
    """Fires once, the very first time a rubrique is checked (see
    watcher.process_rubrique) — otherwise a fresh install gives no feedback
    at all that anything happened, since the baseline-seeding itself stays
    silent on purpose (no flood of toasts for pre-existing articles)."""
    try:
        notify(
            "Gazette Drouot Watcher — set up",
            f"Now tracking {rubrique_label} ({count} articles seeded as baseline). "
            "You'll be notified about new ones from here.",
            app_id=APP_ID,
        )
    except Exception:
        log.exception("failed to show first-run-seeded toast for %s", rubrique_label)


def notify_cloudflare_blocked(blocked_rubriques: list[str]):
    """The site's bot-protection intercepted us — this is not a bug in the
    scraper itself, just tells the user what's happening and the most
    common fix (a VPN being on)."""
    body = (
        "Couldn't reach: " + ", ".join(blocked_rubriques) + ".\n"
        "Likely cause: a VPN is active — disable it and it should clear up.\n"
        "If not, check logs\\watcher.log for details."
    )
    try:
        notify("Gazette Drouot Watcher — blocked by Cloudflare", body, app_id=APP_ID)
    except Exception:
        log.exception("failed to show Cloudflare-block alert toast")


def notify_site_structure_changed(affected_rubriques: list[str]):
    """The site loaded fine but its HTML doesn't match what this script
    expects anymore — most likely gazette-drouot.com changed their page
    layout and the scraper's selectors need to be updated to match. This is
    a real "the app is broken" signal, distinct from a Cloudflare block."""
    body = (
        "Site layout changed on: " + ", ".join(affected_rubriques) + ".\n"
        "This script needs an update to keep working — contact the developer "
        "for a fix / new version.\n"
        "Details are in logs\\watcher.log."
    )
    try:
        notify("Gazette Drouot Watcher — needs an update", body, app_id=APP_ID)
    except Exception:
        log.exception("failed to show site-structure-changed alert toast")
