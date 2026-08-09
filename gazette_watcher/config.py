"""
All the settings you're likely to want to tweak live in this one file.
After changing anything here, the change takes effect on the very next run —
EXCEPT for POLL_INTERVAL_MINUTES, which also requires clicking Install
again in the control panel (or re-running with --watch's caller) to
re-register the Windows Task Scheduler job with the new interval.
"""

import sys
from pathlib import Path

# When packaged into a standalone .exe (PyInstaller), __file__ points into a
# temporary extraction folder, not where the .exe actually sits — use the
# .exe's own location instead in that case, same reasoning as main.pyw's
# PROJECT_DIR. Without this, a frozen exe's state/logs go into that
# temp folder and vanish when it exits, instead of into the real project dir.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = BASE_DIR / "state"
LOG_FILE = BASE_DIR / "logs" / "watcher.log"


# ---------------------------------------------------------------------------
# Which pages to watch. To add another rubrique (or any other gazette-drouot
# listing page that uses the same "articleResume" card layout), just add
# another entry here — nothing else needs to change.
#   key:   short, unique, filesystem-safe id — used as the state filename
#          (state/<key>.json), so don't reuse a key or rename one that's
#          already running without also renaming/removing its state file.
#   label: human-readable name shown in notification text.
#   url:   the rubrique's listing page URL (its page-1 URL, no "?page=").
# ---------------------------------------------------------------------------
RUBRIQUES = [
    {
        "key": 'encheres-a-la-une',
        "label": 'Enchères à la une',
        "url": 'https://www.gazette-drouot.com/rubrique/encheres-a-la-une',
    },
    {
        "key": 'marche-de-l-art',
        "label": "Marché de l'art",
        "url": 'https://www.gazette-drouot.com/rubrique/marche-de-l-art',
    },
]


# ---------------------------------------------------------------------------
# How often to check. Read when the control panel's Install button
# (re-)registers the Task Scheduler job — changing this number requires
# clicking Install again once for the new interval to actually take effect.
# ---------------------------------------------------------------------------
POLL_INTERVAL_MINUTES = 15


# ---------------------------------------------------------------------------
# How deep to scan each rubrique's pagination, every single run.
#
# We deliberately do NOT stop early at the first "already seen" article:
# testing showed the site's pagination order isn't reliably chronological —
# the same article can drift to a different page over time — so an early
# stop could silently skip real new articles sitting deeper on the page.
# Scanning the full fixed depth below and diffing everything found against
# stored state (by article id) is slower per run but correct.
#
# 5 pages at ~9 articles/page is a large multiple of "a few posts per day"
# checked every POLL_INTERVAL_MINUTES, so this should never realistically
# be exceeded in normal use — it would take an enormous publishing burst
# (or the computer being off for a very long time) to actually miss
# something because of this cap.
# ---------------------------------------------------------------------------
MAX_PAGES = 5

# Small pause between each of the MAX_PAGES page fetches within one run, so
# they don't all fire back-to-back and look more bot-like than necessary.
PAGE_DELAY_SECONDS = 1.5


# ---------------------------------------------------------------------------
# How many already-notified article ids to remember per rubrique, at most.
# Once past this, the OLDEST (numerically lowest id) entries are dropped
# first — they're the least likely to still be within MAX_PAGES' reach anyway.
# ---------------------------------------------------------------------------
MAX_SEEN_IDS = 300


# ---------------------------------------------------------------------------
# Notification flood control. If more than FLOOD_CAP new/updated articles
# are found on one rubrique in a single run (e.g. the computer was off for a
# while), only the first FLOOD_CAP get their own individual toast — the
# rest are collapsed into one "N more new posts" summary toast instead of
# flooding the screen.
# ---------------------------------------------------------------------------
FLOOD_CAP = 3

# Seconds to wait between showing each individual toast, so they don't all
# stack up on screen at once.
NOTIF_GAP_SECONDS = 7


# ---------------------------------------------------------------------------
# If a run fails (Cloudflare block, or the site's HTML no longer matching
# what this script expects), how long to wait before showing the same kind
# of "something's wrong" alert toast again — so a multi-hour outage doesn't
# spam a toast every POLL_INTERVAL_MINUTES.
# ---------------------------------------------------------------------------
ALERT_COOLDOWN_HOURS = 2.0


# ---------------------------------------------------------------------------
# Browser settings. A real installed browser (as opposed to Playwright's own
# bundled Chromium) is needed to pass Cloudflare reliably. Headless works
# fine — the thing that actually breaks Cloudflare is a VPN being active on
# this machine, not headless vs. visible.
#
# BROWSER_CHANNEL valid values:
#   "msedge", "chrome" (and their "-beta"/"-dev"/"-canary" variants) — drives
#     your real installed Edge/Chrome directly, no extra download needed.
#   "firefox" — Playwright's own bundled Firefox build, NOT your installed
#     one. Needs a one-time `playwright install firefox` before first use.
#   Anything else (Opera, Brave, Vivaldi, Safari, ...) isn't supported —
#     Playwright only knows how to drive the browsers listed above.
# ---------------------------------------------------------------------------
HEADLESS = True
BROWSER_CHANNEL = 'chrome'
WINDOW_ARGS = []
