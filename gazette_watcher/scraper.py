"""
Scrapes a "rubrique" (article listing) page from gazette-drouot.com.

How it works, in short:
  - Each rubrique has a listing page (e.g. /rubrique/encheres-a-la-une) that
    shows the most recent articles as a list of <div class="articleResume">
    cards, paginated via a "?page=N" query parameter.
  - Each card already contains everything we need for a notification: the
    article's URL (and therefore its numeric id), title, publish date,
    excerpt, optional "Résultat" (auction result) line, and a thumbnail
    image. We never need to open the individual article pages.
  - We always scan a fixed number of pages (config.MAX_PAGES) on every run,
    rather than stopping early at the first "already seen" article. This is
    deliberate: testing showed the site's pagination order is NOT reliably
    chronological — the same article can drift between pages over time — so
    "stop at the first known id" is unsafe and could silently skip real new
    articles sitting deeper on the page. Scanning the full fixed depth every
    time and diffing by id against stored state (see state.py) is slower
    but correct.

Two distinct failure modes are detected and raised as their own exception
types, so watcher.py can tell the user exactly what's wrong instead of a
generic "something broke":
  - CloudflareBlockedError: the site's bot-protection intercepted us (shows
    a "Just a moment..." challenge page instead of real content). Usually
    fixed by turning off a VPN.
  - SiteStructureChangedError: we got a real page back, but it doesn't look
    like we expect (no article cards on page 1, or a card is missing a
    field we rely on). This most likely means gazette-drouot.com changed
    their HTML and this script needs updating to match.
"""

import re
import time
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Matches the trailing numeric id in an article URL, e.g.
# ".../article/some-title/103336" -> 103336. This id is the stable
# identifier we track in state.py — titles/dates/positions can all change,
# but the id is permanent for a given article.
ARTICLE_ID_RE = re.compile(r"(\d+)/?$")

# Title text Cloudflare's interstitial challenge page uses, in the locales
# we've actually observed it in.
_CLOUDFLARE_TITLE_MARKERS = ("just a moment", "un instant", "moment d'attente")

# Language-independent markers pulled from the challenge page's own HTML
# (its Content-Security-Policy meta tag references challenges.cloudflare.com,
# and its scripts/ids commonly contain "cf-chl" / "cf_chl"). Checked in
# addition to the title so a locale we haven't seen yet doesn't slip through
# and get misclassified as "site structure changed" instead of "blocked" —
# a missed block is worse than a false alarm.
_CLOUDFLARE_CONTENT_MARKERS = ("challenges.cloudflare.com", "cf-chl", "cf_chl")


class CloudflareBlockedError(Exception):
    """Raised when the site's bot-protection served a challenge page instead
    of real content. Not our bug — see notifier.notify_cloudflare_blocked
    for the user-facing explanation (usually: turn off your VPN)."""


class SiteStructureChangedError(Exception):
    """Raised when a page loaded fine (not a Cloudflare block) but doesn't
    match the HTML structure this scraper expects. Most likely cause: the
    real site changed its markup and gazette_watcher needs a code update to
    match it — see notifier.notify_site_structure_changed."""


def _extract_id(url: str) -> int:
    m = ARTICLE_ID_RE.search(url)
    if not m:
        raise SiteStructureChangedError(f"could not extract a numeric article id from url: {url!r}")
    return int(m.group(1))


def _parse_card(card, base_url: str) -> dict:
    """Extracts one article's data out of a single <div class="articleResume">
    card. Any field we consider essential (id, title) raises
    SiteStructureChangedError if it can't be found — better to loudly flag
    "this needs a fix" than to silently notify with garbage/missing data."""
    content = card.locator(".contenuArticle")
    if content.count() == 0:
        raise SiteStructureChangedError("articleResume card is missing its .contenuArticle wrapper")

    # The article's own link (and thus its id) — several links inside the
    # card point to the same article (date link, title link, image link);
    # we only need the first match.
    link = content.locator("a[href*='/article/']").first
    url = link.get_attribute("href")
    if not url:
        raise SiteStructureChangedError("articleResume card has no /article/ link — can't identify it")
    if not url.startswith("http"):
        url = urljoin(base_url, url)
    article_id = _extract_id(url)

    # Publish date. Some articles genuinely have no date shown on the
    # listing card at all — state.py has a special rule for that case (an
    # article with no date is only ever notified once, then permanently
    # skipped, since we have no date to compare against on future runs).
    date = None
    date_locator = content.locator("span a.colorBlueDark")
    if date_locator.count() > 0:
        date_text = date_locator.first.inner_text()
        date = date_text.replace("Publié le", "").strip() or None

    title_locator = content.locator("h3.titreArticle")
    if title_locator.count() == 0:
        raise SiteStructureChangedError(f"articleResume card ({url}) has no h3.titreArticle title")
    title = title_locator.first.inner_text().strip()
    if not title:
        raise SiteStructureChangedError(f"articleResume card ({url}) has an empty title")

    # "Résultat X EUR" — only present on already-sold ("Les adjugés") auction
    # articles, absent on plain market-news articles. Optional, no error if missing.
    result = None
    result_locator = content.locator(".font-red .fontRadikalBold")
    if result_locator.count() > 0:
        result = result_locator.first.inner_text().strip()

    # Short excerpt text. Optional, no error if missing.
    excerpt_locator = content.locator("h4.resumeArticle")
    excerpt = excerpt_locator.first.inner_text().strip() if excerpt_locator.count() > 0 else ""

    # Thumbnail image. Optional, no error if missing — not every card has one.
    image = None
    img_locator = card.locator(".imageArticle img")
    if img_locator.count() > 0:
        image = img_locator.first.get_attribute("src")
        if image and not image.startswith("http"):
            image = urljoin(base_url, image)

    return {
        "id": article_id,
        "url": url,
        "date": date,
        "title": title,
        "result": result,
        "excerpt": excerpt,
        "image": image,
    }


def scrape_listing_page(page, base_url: str, page_num: int) -> list[dict]:
    """Loads one page of a rubrique's listing (page_num starting at 1) and
    returns the articles found on it, newest-appearing-first as laid out on
    the page (though see the module docstring — that page order is not
    trustworthy as a "chronological" signal on its own)."""
    url = base_url if page_num == 1 else f"{base_url}?page={page_num}"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)

    try:
        page.wait_for_selector("div.articleResume", timeout=15000)
    except PlaywrightTimeoutError:
        # No article cards showed up in time. Three possible reasons, checked
        # in order of how confident we can be about which one it is:
        title = (page.title() or "").lower()
        html = page.content().lower()

        # 1) Cloudflare's challenge page — recognizable by its title/markup
        #    regardless of the real site's own layout.
        if any(marker in title for marker in _CLOUDFLARE_TITLE_MARKERS) or any(
            marker in html for marker in _CLOUDFLARE_CONTENT_MARKERS
        ):
            raise CloudflareBlockedError(f"Cloudflare challenge blocked {url} (page title: {page.title()!r})")

        # 2) A genuinely empty page past the real content (e.g. page 5 asked
        #    for but the rubrique only has 4 pages worth of articles right
        #    now). This is only plausible for page_num > 1 — page 1 of an
        #    active rubrique should never legitimately be empty, so if it
        #    is, treat it as the site's markup having changed instead of
        #    silently pretending there's nothing new (see SiteStructureChangedError).
        if page_num > 1 and page.locator("div.articleResume").count() == 0:
            return []

        # 3) Neither of the above: page 1 came back with zero article
        #    cards and it's not a Cloudflare page — the site's HTML has
        #    likely changed shape and our selectors no longer match it.
        raise SiteStructureChangedError(
            f"page {page_num} of {url} loaded but no div.articleResume cards were found "
            f"(and it doesn't look like a Cloudflare block) — the site's markup may have changed"
        )

    cards = page.locator("div.articleResume")
    articles = []
    for i in range(cards.count()):
        articles.append(_parse_card(cards.nth(i), base_url))
    return articles


def scrape_rubrique_all(page, base_url: str, max_pages: int, page_delay: float = 0) -> list[dict]:
    """Scrapes pages 1..max_pages unconditionally — no early-stop optimization,
    see the module docstring for why. Returns every article found, deduped by
    id (first occurrence kept) since a page reshuffling mid-walk can otherwise
    surface the same article twice across two adjacent page fetches."""
    by_id: dict[int, dict] = {}
    for page_num in range(1, max_pages + 1):
        if page_num > 1 and page_delay:
            # Small politeness gap between page fetches, so 5 requests don't
            # fire back-to-back and look more bot-like than necessary.
            time.sleep(page_delay)
        page_articles = scrape_listing_page(page, base_url, page_num)
        if not page_articles:
            break  # ran past the last page that has any content
        for article in page_articles:
            by_id.setdefault(article["id"], article)
    return list(by_id.values())
