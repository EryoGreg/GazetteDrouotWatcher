🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

Watches one or more gazette-drouot.com rubrique (article listing) pages and fires a Windows toast notification for each new or updated article — click a toast to open it in your default browser.

## How it works

- Every run, each configured rubrique gets its first `MAX_PAGES` listing pages scanned in full (not just until a "known" article is found — testing showed the site's pagination isn't reliably chronological, so an early stop could silently miss real news).
- Every article found is compared against stored state (`state/<rubrique-key>.json`) by its numeric id **and** its publish date. New id → notify. Known id but a different date than last time → notify again (the article was likely republished/edited). An article with no date shown at all is only ever notified once, then never re-checked.
- First run for a rubrique just records what's currently there as a baseline, silently — no notification flood for pre-existing articles on install.
- If more than `FLOOD_CAP` new/updated articles turn up in one rubrique in a single run, only the first few get their own toast — the rest collapse into one "N more new posts" summary toast.

## Setup

- **VPN must be off** while this runs — Cloudflare forces an interactive challenge on VPN IPs that automation can't clear. A plain home IP passes without issue.
- Requires Microsoft Edge installed (uses your system Edge via Playwright's `channel="msedge"`, no separate browser download needed).
- `pip install -r requirements.txt`

## Configuration

**`gazette_watcher/config.py` is the single file to edit** for everything: which pages to watch, how often to check, how deep to scan, notification flood limits, alert cooldowns, etc. — each setting has a comment explaining it (or edit them through the control panel's Settings tab instead, see below). After changing anything there, the change takes effect on the next run, **except** `POLL_INTERVAL_MINUTES`, which also needs clicking **Install** again in the control panel once to update the actual Windows Task Scheduler job with the new interval.

## Control panel GUI

**This is the app** — a single, self-contained `.exe`, no separate Python install or script files needed on the machine that runs it. A desktop window for everything: install / enable / disable / uninstall the scheduled task (via the native Task Scheduler API directly, no PowerShell involved), and a settings panel (with a "Reset to defaults" if something gets messed up) instead of hand-editing the config file. The flag icon switches the UI language (English, 中文, Español, हिन्दी, العربية, Português, Русский, Français, 日本語, Deutsch — defaults to your Windows UI language, falls back to English); the sun/moon icon switches light/dark (defaults to your Windows theme). Both choices persist in `gui_prefs.json`.

**If you just have the `.exe`:** double-click `GazetteDrouotWatcher.exe` — nothing else to install. It expects to sit directly in this project folder, next to `gazette_watcher/`, etc. Click **Install** in the window to register the scheduled task — from then on it checks automatically in the background, in the interval set in `config.py`, without this window (or the app at all) needing to stay open, and it starts itself again after every PC restart.

**Running from source instead:** double-click `main.pyw` (Windows runs `.pyw` files via `pythonw.exe`, no console window), or:
```
pythonw.exe main.pyw
```

**Building the `.exe` yourself** (it's gitignored — not committed to source, rebuild it or grab it from a Release):
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcher --icon icon.ico main.pyw
```
Then copy `dist/GazetteDrouotWatcher.exe` into the project root (next to `main.pyw`) and delete the `build/`, `dist/`, and `*.spec` leftovers.

## Manual run

`main.pyw --watch` (or the equivalent `GazetteDrouotWatcher.exe --watch`) is what the scheduled task actually calls — runs one check and exits, no GUI. This is also the same as:
```
python -m gazette_watcher.watcher
```

## If something goes wrong

Two distinct alert toasts exist, each rate-limited to at most one per `ALERT_COOLDOWN_HOURS` (config.py) so an ongoing issue doesn't spam a toast every run:

- **"blocked by Cloudflare"** — the site's bot-protection intercepted the request. Almost always fixed by turning off a VPN.
- **"needs an update"** — a page loaded fine but its HTML doesn't match what this script expects anymore. Most likely gazette-drouot.com changed their page layout and the scraper's selectors (`gazette_watcher/scraper.py`) need updating to match.

`logs/watcher.log` has full detail on every run — check here first if notifications stop appearing.

## Testing without touching the real site

`test/` contains a small local fake-site harness for testing scraping/notification logic in isolation, without hammering the real site or depending on its live content. See `test/README.md`.

## Adding another page to watch

Add another entry to `RUBRIQUES` in `config.py` — as long as the page uses the same `div.articleResume` card layout, nothing else needs to change.
