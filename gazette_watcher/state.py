"""
Persists what's already been notified about, per rubrique, as a small JSON
file under config.STATE_DIR (one file per rubrique key, e.g.
state/encheres-a-la-une.json).

The stored shape is {"seen": {"<article_id>": "<date_string_or_null>"}, ...}.
Why a dict of id->date instead of just a list of known ids: testing showed
the site's article dates can genuinely change (a republish/edit), and we
want to re-notify in that case — so we need to remember not just "have we
seen this id" but "what date did we last see it with".

Also handles a small separate file (_alerts.json) tracking the last time
each kind of "something's wrong" alert (Cloudflare block / site changed)
was shown, so watcher.py can avoid re-alerting every 15 minutes during a
multi-hour outage — see config.ALERT_COOLDOWN_HOURS.
"""

import json
import logging
from datetime import datetime, timezone

from . import config

log = logging.getLogger("gazette_watcher")

# Bump this if the stored JSON shape ever changes again (it already has
# once, from a plain list of ids to this id->date dict). A state file
# written by a different schema version is treated as if it doesn't exist
# — see _load_raw — rather than risking misreading data in a shape this
# code doesn't understand.
SCHEMA_VERSION = 2


def _state_path(rubrique_key: str):
    return config.STATE_DIR / f"{rubrique_key}.json"


def _alert_path():
    return config.STATE_DIR / "_alerts.json"


def _load_raw(rubrique_key: str) -> dict | None:
    """Returns the parsed state file's contents, or None if there isn't one
    yet, or if it was written by an incompatible schema version (treated
    the same as "doesn't exist" — safer to silently reseed than to
    misinterpret data in an unexpected shape)."""
    path = _state_path(rubrique_key)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema_version") != SCHEMA_VERSION:
        log.warning(
            "[%s] state file has schema_version=%r, expected %d — treating as first run",
            rubrique_key,
            data.get("schema_version"),
            SCHEMA_VERSION,
        )
        return None
    return data


def is_first_run(rubrique_key: str) -> bool:
    """No usable state file yet for this rubrique (missing, or written by
    an incompatible schema version) = treat as never checked before."""
    return _load_raw(rubrique_key) is None


def load_seen(rubrique_key: str) -> dict[int, str | None]:
    """Returns {article_id: date_string_or_None}.

    A stored date of None is a special marker: it means the article was
    already notified once, at a time when it had NO date shown on the
    listing page. Rather than re-checking such an article forever (its
    "date" would always look different from nothing, or nothing would ever
    look "changed" if it stays absent), we just never touch it again once
    it's been notified — see is_new_or_changed below.
    """
    data = _load_raw(rubrique_key)
    if data is None:
        return {}
    # JSON object keys are always strings, so ids need converting back to int.
    return {int(k): v for k, v in data.get("seen", {}).items()}


def save_seen(rubrique_key: str, seen: dict[int, str | None]):
    """Writes the seen-articles dict back to disk. If it's grown past
    config.MAX_SEEN_IDS entries, trims down to the highest (i.e. most
    recent, since ids increase roughly over time) ids — we don't need to
    remember articles from months ago forever, only far enough back to
    reliably catch anything within our page-scan depth."""
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    if len(seen) > config.MAX_SEEN_IDS:
        keep_ids = sorted(seen.keys(), reverse=True)[: config.MAX_SEEN_IDS]
        seen = {i: seen[i] for i in keep_ids}
    data = {
        "schema_version": SCHEMA_VERSION,
        "seen": {str(k): v for k, v in seen.items()},
        "last_run": datetime.now(timezone.utc).isoformat(),
    }
    with open(_state_path(rubrique_key), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_new_or_changed(seen: dict[int, str | None], article_id: int, date: str | None) -> bool:
    """The core "should this article get a notification" rule:
      - never seen this id before -> yes, it's new
      - seen it before, but the date shown now is different from what we
        recorded -> yes, treat it as updated (the site likely republished it)
      - seen it before with NO date recorded (the None marker) -> no, never
        again, regardless of what date it has now
      - seen it before with the same date -> no, nothing's changed
    """
    if article_id not in seen:
        return True
    stored_date = seen[article_id]
    if stored_date is None:
        return False
    return stored_date != date


def load_last_alert(alert_key: str) -> str | None:
    """Returns the ISO timestamp of the last time this alert_key (e.g.
    "cloudflare" or "structure_changed") was shown to the user, or None if
    it's never been shown."""
    path = _alert_path()
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get(alert_key)


def save_last_alert(alert_key: str):
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = _alert_path()
    data = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    data[alert_key] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
