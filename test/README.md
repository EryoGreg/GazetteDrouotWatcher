# Test harness

A small local fake site for exercising the real, unmodified `gazette_watcher`
scraping/state/notification pipeline without touching the real site or
depending on its live, constantly-changing content.

## How it fits together

- `fakesite/server.py` — a plain `http.server` that serves fake rubrique
  listing pages using the exact same HTML structure the scraper looks for
  (`div.articleResume` cards, the "à ne pas manquer" decoy banner, real
  pagination via `?page=N`). Article content comes from `fakesite/articles*.json`.
- `fakesite/fake_data.py` — helpers to edit those article pools:
  `reset_baseline(n, site=...)` writes a fresh baseline (simulates "articles
  that already existed before you installed the app"), `prepend_new(n, label,
  site=..., with_image=..., with_result=...)` adds new articles to the front
  (simulates new posts appearing).
- `run_scenario.py` / `run_scenario_dual.py` / `run_scenario_blocked.py` —
  each points the real `gazette_watcher.watcher.run()` at the fake site
  instead of the live one (by overriding `config.RUBRIQUES`/`STATE_DIR`/
  `LOG_FILE` before calling it), so every run genuinely exercises the same
  code path production uses. `_dual` configures two rubriques at once (for
  testing cross-rubrique behavior like worst-case notification counts);
  `_blocked` points at a route that mimics Cloudflare's challenge page, for
  testing the block-detection/alert path without needing a real block.

State and logs from these runs are isolated under `test/state/` and
`test/watcher_test.log` — they never touch your real `state/` or
`logs/watcher.log`.

## Running a scenario

1. Start the fake server (leave it running in the background):
   ```
   python test/fakesite/server.py 8791
   ```
2. Seed a baseline and do a first (silent) run:
   ```python
   import sys; sys.path.insert(0, "test/fakesite")
   from fake_data import reset_baseline
   reset_baseline(25)  # fills all 5 pages so no empty-page timeouts during testing
   ```
   ```
   python test/run_scenario.py
   ```
3. Add new articles and run again — check `test/watcher_test.log` and your
   actual Windows notifications for the expected result:
   ```python
   from fake_data import prepend_new
   prepend_new(5, "mytest")  # 5 new -> 3 individual toasts + "2 more" summary
   ```
   ```
   python test/run_scenario.py
   ```

## Gotcha: restart the server after editing `server.py`

The server is a long-running background process — editing `server.py` while
it's already running does nothing until it's restarted (find its PID via
`tasklist`, kill it, relaunch). Editing `articles*.json` via `fake_data.py`
does NOT need a restart — the server reads that file fresh on every request.
