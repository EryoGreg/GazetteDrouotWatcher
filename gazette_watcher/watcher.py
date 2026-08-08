"""
Entry point — one call to run() does one full check cycle:
  for each configured rubrique (see config.RUBRIQUES):
    1. scrape all pages (scraper.scrape_rubrique_all)
    2. diff the results against stored state (state.py) to find
       new-or-updated articles
    3. save the updated state (BEFORE notifying — see the comment on that
       below, it's a deliberate crash-safety choice)
    4. fire Windows toast notifications for whatever's new (notifier.py)

Task Scheduler calls `python -m gazette_watcher.watcher` on a timer
(see config.POLL_INTERVAL_MINUTES and install_task.ps1) — this script does
not loop or sleep itself, each run is a fresh, independent process.
"""

import logging
import logging.handlers
from datetime import datetime, timedelta, timezone

from playwright.sync_api import sync_playwright

from . import config, notifier, scraper, state
from .scraper import CloudflareBlockedError, SiteStructureChangedError


def _setup_logging():
    # Runs every POLL_INTERVAL_MINUTES forever — a plain, never-rotated log
    # file would grow without bound over months of use. Caps it at
    # 2MB/file, keeping 3 old copies (watcher.log.1, .2, .3) before the
    # oldest is discarded — ~8MB max total, plenty of history for debugging.
    config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def process_rubrique(page, rubrique: dict) -> str | None:
    """Scrapes one rubrique, updates its state, and notifies about anything
    new-or-updated. Returns None on success, or a short string identifying
    which kind of failure happened ("cloudflare" / "structure_changed") so
    run() can decide whether to alert the user about it."""
    key, label, url = rubrique["key"], rubrique["label"], rubrique["url"]
    log = logging.getLogger("gazette_watcher")

    try:
        articles = scraper.scrape_rubrique_all(page, url, config.MAX_PAGES, config.PAGE_DELAY_SECONDS)
    except CloudflareBlockedError as e:
        log.warning("[%s] Cloudflare blocked this run: %s", key, e)
        return "cloudflare"
    except SiteStructureChangedError as e:
        log.error("[%s] site structure looks different than expected: %s", key, e)
        return "structure_changed"

    first_run = state.is_first_run(key)
    seen = state.load_seen(key)  # {article_id: date_or_None}

    # An article is "new" if we've never recorded its id, or "updated" if we
    # have recorded it but with a different date than what's shown now
    # (e.g. the site republished/edited it). An article we already notified
    # about with NO date (stored as None) is a special case: we never
    # re-check it again regardless of what date shows up later — see
    # state.is_new_or_changed for the exact rule.
    new_or_changed = [a for a in articles if state.is_new_or_changed(seen, a["id"], a["date"])]

    # Update every scraped article's stored date to what we just saw — but
    # never overwrite a stored None (that's the "already notified once with
    # no date, never touch again" marker described above).
    for a in articles:
        aid, date = a["id"], a["date"]
        if aid not in seen:
            seen[aid] = date
        elif seen[aid] is not None:
            seen[aid] = date

    # Save state BEFORE sending notifications. If this process gets killed
    # mid-notification-batch (crash, forced stop, etc.), the worst case on
    # the next run is a couple of missed toasts for articles that were
    # already marked seen — never a duplicate notification for the same
    # article. Tested and confirmed during development.
    state.save_seen(key, seen)

    if first_run:
        # First time this rubrique has ever been checked: record what's
        # currently there as the baseline — no per-article notification
        # flood for pre-existing content, but one short toast confirming
        # setup worked (otherwise a fresh install gives zero feedback that
        # anything happened at all).
        log.info("[%s] first run: seeded %d articles, no notifications", key, len(articles))
        notifier.notify_first_run_seeded(label, len(articles))
        return None

    if new_or_changed:
        # Order by id ascending for display — the site's own page order
        # isn't reliably chronological (see scraper.py's module docstring),
        # so numeric id is used as a deterministic, good-enough stand-in.
        new_or_changed.sort(key=lambda a: a["id"])
        log.info("[%s] found %d new/updated article(s)", key, len(new_or_changed))
        notifier.notify_new_articles(new_or_changed, label, url)
    else:
        log.info("[%s] no new articles", key)

    return None


def _maybe_alert(alert_key: str, send_fn):
    """Sends an alert toast via send_fn(), unless we already sent this same
    kind of alert within the last config.ALERT_COOLDOWN_HOURS — so an
    outage that lasts for hours doesn't spam a toast every 15 minutes."""
    log = logging.getLogger("gazette_watcher")
    last = state.load_last_alert(alert_key)
    if last:
        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(last)
        if elapsed < timedelta(hours=config.ALERT_COOLDOWN_HOURS):
            log.info("'%s' alert suppressed (cooldown, last alerted %s)", alert_key, last)
            return
    send_fn()
    state.save_last_alert(alert_key)
    log.info("'%s' alert sent", alert_key)


def run():
    _setup_logging()
    log = logging.getLogger("gazette_watcher")
    log.info("run start")

    # Rubriques that failed this run, grouped by why — used below to decide
    # which alert toast(s) to fire, if any.
    cloudflare_blocked = []
    structure_changed = []

    try:
        with sync_playwright() as p:
            # "firefox" is a genuinely different Playwright browser type (its
            # own bundled build, downloaded via `playwright install firefox`
            # — not a --channel like the Chromium-family browsers below).
            # Everything else (chrome/chrome-beta/.../msedge/msedge-beta/...)
            # drives your real installed browser via Playwright's `channel`.
            if config.BROWSER_CHANNEL == "firefox":
                browser = p.firefox.launch(headless=config.HEADLESS)
            else:
                browser = p.chromium.launch(
                    channel=config.BROWSER_CHANNEL,
                    headless=config.HEADLESS,
                    args=config.WINDOW_ARGS,
                )
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                for rubrique in config.RUBRIQUES:
                    try:
                        failure = process_rubrique(page, rubrique)
                        if failure == "cloudflare":
                            cloudflare_blocked.append(rubrique["label"])
                        elif failure == "structure_changed":
                            structure_changed.append(rubrique["label"])
                    except Exception:
                        # Anything unexpected we didn't already handle above —
                        # log it and keep going with the other rubrique(s)
                        # rather than letting one bad page take down the run.
                        log.exception("[%s] run failed", rubrique["key"])
            finally:
                browser.close()
    except Exception:
        log.exception("watcher run failed")

    if cloudflare_blocked:
        _maybe_alert("cloudflare", lambda: notifier.notify_cloudflare_blocked(cloudflare_blocked))
    if structure_changed:
        _maybe_alert("structure_changed", lambda: notifier.notify_site_structure_changed(structure_changed))

    log.info("run end")


if __name__ == "__main__":
    run()
