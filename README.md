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

**`gazette_watcher/config.py` is the single file to edit** for everything: which pages to watch, how often to check, how deep to scan, notification flood limits, alert cooldowns, etc. — each setting has a comment explaining it. After changing anything there, the change takes effect on the next run, **except** `POLL_INTERVAL_MINUTES`, which also needs `install_task.ps1` re-run once to update the actual Windows Task Scheduler job.

## Control panel GUI

A desktop window for everything below without touching PowerShell or config.py directly: install / enable / disable / uninstall the scheduled task, and a settings panel (with a "Reset to defaults" if something gets messed up) instead of hand-editing the config file. The flag icon switches the UI language (English, 中文, Español, हिन्दी, العربية, Português, Русский, Français, 日本語, Deutsch — defaults to your Windows UI language, falls back to English); the sun/moon icon switches light/dark (defaults to your Windows theme). Both choices persist in `gui_prefs.json`.

**If you just have the `.exe`:** double-click `GazetteDrouotWatcherGUI.exe` — nothing else to install. It expects to sit directly in this project folder, next to `gazette_watcher/`, `install_task.ps1`, etc.

**Running from source instead:** double-click `gui.pyw` (Windows runs `.pyw` files via `pythonw.exe`, no console window), or:
```
pythonw.exe gui.pyw
```

**Building the `.exe` yourself** (it's gitignored — not committed to source, rebuild it or grab it from a Release):
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcherGUI --icon icon.ico gui.pyw
```
Then copy `dist/GazetteDrouotWatcherGUI.exe` into the project root (next to `gui.pyw`) and delete the `build/`, `dist/`, and `*.spec` leftovers.

## Manual run

```
python -m gazette_watcher.watcher
```

## Scheduling

Run `install_task.ps1` to register a "GazetteDrouotWatcher" Task Scheduler job that runs on the interval set in `config.py`, while you're logged in. Re-run it any time (e.g. after changing `POLL_INTERVAL_MINUTES`) to update the already-registered task.

```
powershell -ExecutionPolicy Bypass -File install_task.ps1
```

Run once immediately for testing:
```
powershell -Command "Start-ScheduledTask -TaskName GazetteDrouotWatcher"
```

Remove it with `uninstall_task.ps1`:
```
powershell -ExecutionPolicy Bypass -File uninstall_task.ps1
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
