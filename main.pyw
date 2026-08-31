"""
Gazette Drouot Watcher — single entry point for both halves of the app.

    main.pyw               -> opens the control panel GUI (default)
    main.pyw --watch       -> runs one watcher check and exits, no GUI

Task Scheduler is registered to call the second form — this is what makes
the whole app a single file once built with PyInstaller (see README):
one .exe, no separate Python install, no separate script files needed on
the machine that runs it.

The GUI is a small desktop window for the two things you'd otherwise need
PowerShell one-liners and a text editor for: managing the Windows Task
Scheduler job (install / enable / disable / uninstall — via the native
Task Scheduler COM API, see gazette_watcher/task_scheduler.py, no
PowerShell involved) and editing the app's settings.

Settings are shown as a plain list of labeled fields rather than the raw
config.py source — Save rewrites only the specific values that changed,
using Python's own parser to find each setting's exact location in the
file, so your comments and formatting in config.py are left untouched.
"Reset to defaults" restores every setting to what the app ships with.

The UI text itself is translated (see i18n.py) — a flag icon next to the
theme toggle opens a language menu. Switching language rebuilds the whole
window (simplest reliable way to re-render every label), which reloads
settings from disk — save first if you have unsaved edits.

Run the GUI by double-clicking this file (Windows runs .pyw files via
pythonw.exe automatically, so no console window appears), or manually:
    pythonw.exe main.pyw
"""

import ast
import ctypes
import datetime
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import types
import urllib.error
import urllib.request
import webbrowser
import winreg
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

# When packaged into a standalone .exe (PyInstaller), __file__ points into a
# temporary extraction folder, not where the .exe actually sits — use the
# .exe's own location instead in that case. This is still where the exe
# itself lives (and where icon.ico is looked for in source mode) — but not
# where user data (config.py, gui_prefs.json, state/, logs/) lives anymore,
# see APPDATA_DIR below.
if getattr(sys, "frozen", False):
    PROJECT_DIR = Path(sys.executable).resolve().parent
else:
    PROJECT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_DIR))

ICON_PATH = PROJECT_DIR / "icon.ico"

# All per-user, editable/generated data lives under %LOCALAPPDATA% instead
# of next to the exe — a plain double-clickable .exe dropped into e.g.
# Downloads used to scatter a gazette_watcher/ folder, gui_prefs.json,
# state/ and logs/ right alongside itself, which reads as the exe "leaving
# a mess" in whatever folder it's run from. This is also what
# gazette_watcher/config.py (and the embedded default_config_template.py)
# use for STATE_DIR/LOG_FILE, so everything the app writes ends up under
# this one folder regardless of where the exe itself sits.
APPDATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "GazetteDrouotWatcher"
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

# A cached copy of the exe itself, and a record of where the *visible* copy
# (wherever the user actually keeps/runs it from) last was -- see
# _refresh_exe_cache() and _maybe_self_destruct_if_deleted() below. Task
# Scheduler is pointed at CACHED_EXE_PATH (stable) rather than sys.executable
# (moves whenever the user moves their copy), so relocating the visible exe
# — e.g. Downloads -> Documents — doesn't silently break the scheduled task.
CACHED_EXE_PATH = APPDATA_DIR / "GazetteDrouotWatcher.exe"
LAST_KNOWN_EXE_PATH_FILE = APPDATA_DIR / "last_known_exe_path.txt"


def _cleanup_stale_pyinstaller_temp(max_to_remove: int = 40) -> int:
    """Removes leftover PyInstaller onefile extraction folders (%TEMP%\\_MEIxxxxx).

    A onefile .exe unpacks itself into one of these on every launch and
    deletes it on exit -- except the delete intermittently loses a race
    against Windows releasing the DLLs the process had loaded, and the
    bootloader then gives up (and, in windowed mode, shows the user a
    "Failed to remove temporary directory" warning). Each abandoned folder
    holds the bundled browser driver, so they are ~100 MB each; on this
    machine 75 of them had quietly accumulated to 727 MB since March.

    Safety comes from liveness rather than from guessing ownership: a
    folder still in use by *any* running program has its DLLs locked, so
    the delete fails and that folder is skipped. Combined with skipping
    our own folder and anything touched recently, that makes it safe even
    though other PyInstaller apps use the same naming scheme -- the worst
    case is clearing another app's already-dead leftovers, which are
    equally garbage.

    Returns how many folders were removed."""
    removed = 0
    try:
        temp_root = Path(tempfile.gettempdir())
        # The folder this very process is running from, which must survive.
        own = getattr(sys, "_MEIPASS", None)
        own_resolved = Path(own).resolve() if own else None
        cutoff = time.time() - 3600  # anything touched in the last hour is left alone

        for candidate in temp_root.glob("_MEI*"):
            if removed >= max_to_remove:
                break  # keep startup snappy; the rest go next time
            try:
                if not candidate.is_dir() or candidate.is_symlink():
                    continue
                if own_resolved and candidate.resolve() == own_resolved:
                    continue
                if candidate.stat().st_mtime > cutoff:
                    continue
                # Any locked file (i.e. a live process) makes this fail, and
                # the folder is simply left where it is.
                shutil.rmtree(candidate)
                removed += 1
            except OSError:
                continue
    except Exception:
        pass  # never let housekeeping break startup
    return removed


def _cleanup_stale_temp_in_background():
    """Runs the sweep off the main thread -- it can touch hundreds of
    megabytes and must not delay the window appearing."""

    def worker():
        count = _cleanup_stale_pyinstaller_temp()
        if count:
            _log_ui(f"cleaned up {count} leftover temporary folder(s) from previous runs")

    threading.Thread(target=worker, daemon=True).start()


def _refresh_exe_cache():
    """Called once at GUI startup, and again right before every
    install_task() call (Install, or a Save/Reset that re-syncs an already-
    installed task) -- keeps CACHED_EXE_PATH up to date with whatever's
    actually running, and records the visible copy's current real path so
    a later scheduled run can tell whether that copy still exists (see
    _maybe_self_destruct_if_deleted). Source/dev-mode runs skip this
    entirely -- there's no portable exe to cache, and Task Scheduler
    already points at a stable pythonw.exe + repo path in that case.

    Always copies unconditionally rather than skipping when the size looks
    unchanged: a user updating by downloading a new build and overwriting
    the old one at the exact same path is a completely ordinary way to
    "update" a portable exe, and a same-size coincidence between two
    genuinely different builds -- unlikely, but not impossible -- would
    otherwise leave the scheduled task silently running old code from a
    stale cache while the GUI (running the new build directly) reports
    itself as up to date. A ~50MB copy once per launch is cheap enough
    that there's no real reason to risk that for the sake of skipping it."""
    if not getattr(sys, "frozen", False):
        return
    try:
        LAST_KNOWN_EXE_PATH_FILE.write_text(sys.executable, encoding="utf-8")
        current = Path(sys.executable).resolve()
        if current == CACHED_EXE_PATH.resolve():
            return  # already running from the cache itself -- nothing to copy
        shutil.copyfile(current, CACHED_EXE_PATH)
    except Exception:
        # Best-effort -- worst case the scheduled task keeps using whichever
        # cached copy (if any) already exists from a previous run.
        pass


def _maybe_self_destruct_if_deleted() -> bool:
    """Only meaningful for a frozen scheduled --watch run. Returns True if
    this process just uninstalled the scheduled task and wiped APPDATA_DIR
    (the caller should stop, not run a normal check).

    LAST_KNOWN_EXE_PATH_FILE records where the *visible* copy of the app
    was the last time the GUI opened. If nothing exists there anymore, the
    most likely explanation is the user deleted it (e.g. dragged it to the
    Recycle Bin) without first clicking Uninstall -- so this cleans up
    after itself instead of running forever as an invisible background
    process with no way left to manage or stop it.

    A *moved* (not deleted) file looks identical from here: opening the
    app again from its new location re-writes the marker before this next
    runs, so the fix is the same either way -- open it once. That
    trade-off (move it, then reopen it before the next scheduled check, or
    it's treated as deleted) is explained in the first-run guide."""
    if not getattr(sys, "frozen", False):
        return False
    try:
        if not LAST_KNOWN_EXE_PATH_FILE.exists():
            return False  # GUI has never run yet -- nothing to check against
        last_known = LAST_KNOWN_EXE_PATH_FILE.read_text(encoding="utf-8").strip()
        if last_known and Path(last_known).exists():
            return False  # still there -- normal run
        try:
            ts.uninstall_task()
        except Exception:
            pass  # best-effort -- still proceed to wipe the folder either way
        try:
            # The link-handler protocol (if the user had picked a specific
            # browser) points at the exe inside the folder about to be
            # deleted -- leaving it registered would strand a dead handler.
            import browser_launch

            browser_launch.unregister_link_protocol()
        except Exception:
            pass
        shutil.rmtree(APPDATA_DIR, ignore_errors=True)
        return True
    except Exception:
        # Fail open: any unexpected error here means "don't know", and a
        # normal check running one extra time is a far smaller problem
        # than wiping a folder on a false positive.
        return False

CONFIG_PATH = APPDATA_DIR / "config.py"

if not CONFIG_PATH.exists():
    # Older builds kept config.py in gazette_watcher/config.py next to the
    # exe — if one's sitting there with the user's actual customized
    # settings, carry it over instead of silently replacing it with
    # factory defaults.
    _legacy_config = PROJECT_DIR / "gazette_watcher" / "config.py"
    if _legacy_config.exists():
        CONFIG_PATH.write_text(_legacy_config.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        # A truly standalone exe: dropped into any folder with nothing else
        # alongside it, this recreates config.py (with its comments intact)
        # from an embedded factory-default template instead of requiring the
        # user to have the file pre-staged — previously this just crashed on
        # launch. gazette_watcher/task_scheduler.py etc. are real code and
        # stay bundled inside the exe as normal; only config.py needs to
        # exist externally, since it's meant to be genuinely user-editable
        # data.
        import default_config_template

        CONFIG_PATH.write_text(default_config_template.DEFAULT_CONFIG_SOURCE, encoding="utf-8")


def _load_live_config():
    """Reads gazette_watcher/config.py's current on-disk content fresh, on
    every call, by exec()'ing its source directly into a new module object
    — not via importlib (import_module/reload, or even
    spec_from_file_location's default loader), because both of those go
    through Python's normal module machinery, and that machinery works
    against us here in two separate ways:

    1. In a frozen exe, PyInstaller bundles its own build-time copy of
       gazette_watcher.config *inside* the exe. importlib.reload() doesn't
       re-run the loader/spec a module already has — it re-resolves the
       module by name through the normal import system, which finds that
       baked-in copy instead of the real external file. Every Settings
       Save appeared to work (the file was written correctly) but the
       very next read silently went back to stale, build-time values.
    2. Even spec_from_file_location's default loader writes/reads a
       __pycache__/*.pyc for the file it loads. Save immediately followed
       by a reload can land inside the same mtime tick, so the cache
       doesn't look stale yet and a just-written change can momentarily
       reload as the previous value.

    A plain exec() has no module-resolution step and never touches
    __pycache__, so neither failure mode applies — it always reflects
    exactly what's on disk right now. This same function is also what the
    frozen-startup block below calls, so every read (GUI or --watch) goes
    through this one path.
    """
    source = CONFIG_PATH.read_text(encoding="utf-8")
    module = types.ModuleType("gazette_watcher.config")
    module.__file__ = str(CONFIG_PATH)
    exec(compile(source, str(CONFIG_PATH), "exec"), module.__dict__)
    sys.modules["gazette_watcher.config"] = module
    import gazette_watcher

    gazette_watcher.config = module
    return module


# config.py now lives under APPDATA_DIR, not inside the gazette_watcher/
# package folder — so plain `import gazette_watcher.config` /
# `from . import config` (used by scraper.py, notifier.py, watcher.py, ...)
# would no longer find it there at all. In a frozen exe it's worse than a
# plain miss: PyInstaller bundles its own build-time gazette_watcher/config.py
# inside the exe, so a normal import would silently resolve to *that* baked-in
# copy instead of erroring — meaning every edit made through Settings (or by
# hand) would be completely invisible to the running exe.
#
# Registering it in sys.modules BEFORE anything else imports
# gazette_watcher.config makes every such import elsewhere resolve to this
# real, on-disk, APPDATA_DIR version instead — in both frozen and source-run
# mode, since the package-relative file is never the live copy in either case
# anymore.
_load_live_config()

import browser_launch
import flags
import i18n
import tray_icon
from gazette_watcher import task_scheduler as ts

TASK_NAME = ts.TASK_NAME

# Small per-machine GUI preferences (theme + language choice) — not app
# behavior, so kept separate from gazette_watcher/config.py. Same
# next-to-the-exe -> AppData migration as CONFIG_PATH above.
GUI_PREFS_PATH = APPDATA_DIR / "gui_prefs.json"
if not GUI_PREFS_PATH.exists():
    _legacy_prefs = PROJECT_DIR / "gui_prefs.json"
    if _legacy_prefs.exists():
        GUI_PREFS_PATH.write_text(_legacy_prefs.read_text(encoding="utf-8"), encoding="utf-8")

AUTHOR = "Grégoire Pessiot"
AUTHOR_URL = "https://github.com/EryoGreg?tab=repositories"

# Bump this on every release — compared against GitHub's "latest release"
# tag by the Updates section to tell the user a newer version exists.
APP_VERSION = "1.3.0"
GITHUB_REPO = "EryoGreg/GazetteDrouotWatcher"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

LOG_FILE_PATH = APPDATA_DIR / "logs" / "watcher.log"


# Kept separate from watcher.log on purpose: that one is a record of what
# the background checks found on the website, and interleaving every click
# and settings tweak into it would bury the thing it exists to show. This
# is the other half -- what the *person* did, and what the app changed on
# disk as a result.
UI_LOG_PATH = APPDATA_DIR / "logs" / "control_panel.log"
_UI_LOG_MAX_BYTES = 1_000_000


def _log_ui(message: str):
    """Appends one line to the control-panel activity log.

    Deliberately plain appends rather than the logging module: the watcher
    process owns a rotating handler on its own file, and attaching handlers
    from several processes to one file is how truncation races happen. One
    previous generation is kept, so the file can't grow without bound but
    recent history always survives a rollover."""
    try:
        UI_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            if UI_LOG_PATH.stat().st_size > _UI_LOG_MAX_BYTES:
                backup = UI_LOG_PATH.with_suffix(".log.1")
                backup.unlink(missing_ok=True)
                UI_LOG_PATH.rename(backup)
        except OSError:
            pass  # locked or missing -- just keep appending
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        with open(UI_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{stamp} {message}\n")
    except Exception:
        # Logging must never be the thing that breaks the app.
        pass

# The simple (non-rubrique) settings this GUI can edit, in display order.
# Each: (config.py variable name, i18n label key, i18n description key, value type)
SIMPLE_FIELDS = [
    ("POLL_INTERVAL_MINUTES", "field_poll_interval_label", "field_poll_interval_desc", "int"),
    ("MAX_PAGES", "field_max_pages_label", "field_max_pages_desc", "int"),
    ("PAGE_DELAY_SECONDS", "field_page_delay_label", "field_page_delay_desc", "float"),
    ("MAX_SEEN_IDS", "field_max_seen_label", "field_max_seen_desc", "int"),
    ("FLOOD_CAP", "field_flood_cap_label", "field_flood_cap_desc", "int"),
    ("NOTIF_GAP_SECONDS", "field_notif_gap_label", "field_notif_gap_desc", "int"),
    ("ALERT_COOLDOWN_HOURS", "field_alert_cooldown_label", "field_alert_cooldown_desc", "float"),
    ("HEADLESS", "field_headless_label", "field_headless_desc", "bool"),
    ("BROWSER_CHANNEL", "field_browser_label", "field_browser_desc", "str"),
    # "browser" renders a dropdown of installed browsers rather than a text
    # box -- the stored value is an .exe path, which nobody should be
    # typing by hand. Empty = use whatever Windows opens links with.
    ("NOTIFICATION_BROWSER", "field_link_browser_label", "field_link_browser_desc", "browser"),
]

# Factory defaults — what "Reset to defaults" restores. Mirrors what
# gazette_watcher/config.py ships with.
DEFAULT_RUBRIQUES = [
    {
        "key": "encheres-a-la-une",
        "label": "Enchères à la une",
        "url": "https://www.gazette-drouot.com/rubrique/encheres-a-la-une",
    },
    {
        "key": "marche-de-l-art",
        "label": "Marché de l'art",
        "url": "https://www.gazette-drouot.com/rubrique/marche-de-l-art",
    },
]
DEFAULTS = {
    "POLL_INTERVAL_MINUTES": 15,
    "MAX_PAGES": 5,
    "PAGE_DELAY_SECONDS": 1.5,
    "MAX_SEEN_IDS": 300,
    "FLOOD_CAP": 3,
    "NOTIF_GAP_SECONDS": 7,
    "ALERT_COOLDOWN_HOURS": 2,
    "HEADLESS": True,
    "BROWSER_CHANNEL": "msedge",
    "NOTIFICATION_BROWSER": "",
    "RUBRIQUES": DEFAULT_RUBRIQUES,
}


# ---------------------------------------------------------------------------
# config.py surgical patcher — rewrites only specific top-level `NAME = ...`
# assignments, leaving every comment and everything else byte-for-byte
# untouched. Values are supplied as ready-to-write Python source strings.
# ---------------------------------------------------------------------------
def _format_rubriques(rubriques: list[dict]) -> str:
    lines = ["["]
    for r in rubriques:
        lines.append("    {")
        lines.append(f'        "key": {r["key"]!r},')
        lines.append(f'        "label": {r["label"]!r},')
        lines.append(f'        "url": {r["url"]!r},')
        lines.append("    },")
    lines.append("]")
    return "\n".join(lines)


def patch_config(source: str, updates: dict[str, str]) -> str:
    """updates: {NAME: new_source_expression}. Replaces each top-level
    `NAME = ...` assignment's value in place, and appends any setting that
    isn't in the file at all yet.

    That append matters for anyone upgrading: their config.py was written
    by an older build and simply has no line for a setting added since, so
    a replace-only patcher would silently drop it and the setting could
    never be saved."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    targets = []
    seen = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in updates:
                targets.append((node.lineno, node.end_lineno, name))
                seen.add(name)
    # process bottom-to-top so earlier replacements don't shift later line numbers
    targets.sort(key=lambda t: t[0], reverse=True)
    for start, end, name in targets:
        lines[start - 1 : end] = [f"{name} = {updates[name]}\n"]

    missing = [name for name in updates if name not in seen]
    if missing:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append("\n")
        for name in missing:
            lines.append(f"{name} = {updates[name]}\n")
    return "".join(lines)


# ---------------------------------------------------------------------------
# Task Scheduler helpers — thin wrappers around gazette_watcher.task_scheduler
# translating its typed exceptions into the (ok, message) shape the rest of
# this file's action/logging flow expects.
# ---------------------------------------------------------------------------
def _resolve_scheduled_action() -> tuple[str, str, str]:
    """(exe_path, arguments, working_dir) for what Task Scheduler should run.
    Frozen exe: the cached copy in APPDATA_DIR (not sys.executable directly
    -- see CACHED_EXE_PATH/_refresh_exe_cache above), with --watch. Running
    from source: pythonw.exe running this file, with --watch."""
    if getattr(sys, "frozen", False):
        return str(CACHED_EXE_PATH), "--watch", str(APPDATA_DIR)
    pythonw = sys.executable
    if pythonw.lower().endswith("python.exe"):
        candidate = pythonw[: -len("python.exe")] + "pythonw.exe"
        if Path(candidate).exists():
            pythonw = candidate
    return pythonw, f'"{Path(__file__).resolve()}" --watch', str(PROJECT_DIR)


# Sentinel strings recognized by _run_action to show a specific translated
# explanation instead of the raw exception text.
_NOT_INSTALLED_SENTINEL = "__NOT_INSTALLED__"
_PERMISSION_DENIED_SENTINEL = "__PERMISSION_DENIED__"


def _call_task_scheduler(fn, *args, **kwargs) -> tuple[bool, str]:
    try:
        fn(*args, **kwargs)
        return True, ""
    except ts.TaskNotInstalledError:
        return False, _NOT_INSTALLED_SENTINEL
    except ts.PermissionDeniedError:
        return False, _PERMISSION_DENIED_SENTINEL
    except Exception as e:
        return False, str(e)


def _link_handler_command() -> str:
    """Quoted command that should receive a clicked notification link, in
    the same frozen-vs-source shape as _resolve_scheduled_action. Frozen
    uses the AppData cache rather than sys.executable so the handler keeps
    working after the visible copy of the app is moved."""
    if getattr(sys, "frozen", False):
        return f'"{CACHED_EXE_PATH}"'
    pythonw = sys.executable
    if pythonw.lower().endswith("python.exe"):
        candidate = pythonw[: -len("python.exe")] + "pythonw.exe"
        if Path(candidate).exists():
            pythonw = candidate
    return f'"{pythonw}" "{Path(__file__).resolve()}"'


def _sync_link_protocol():
    """Registers our link-handling protocol only while the user actually has
    a specific browser chosen, and removes it again the moment they go back
    to the system default -- so the no-override path leaves nothing behind
    in the registry at all. Called at GUI startup (to self-heal a stale
    handler path) and after any settings write."""
    try:
        import browser_launch

        chosen = getattr(_load_live_config(), "NOTIFICATION_BROWSER", "")
        if chosen:
            browser_launch.register_link_protocol(_link_handler_command())
            _log_ui(f"registered link handler so notifications open in: {chosen}")
        else:
            browser_launch.unregister_link_protocol()
            _log_ui("notification links set to use the system default browser")
    except Exception:
        # Never let this break startup or saving -- worst case links open
        # in the system default browser, which is the normal behavior.
        pass


def _do_install() -> tuple[bool, str]:
    try:
        config = _load_live_config()
        interval = int(config.POLL_INTERVAL_MINUTES)
    except Exception as e:
        return False, f"__CONFIG_UNREADABLE__{e}"
    # Re-sync the cache right before pointing Task Scheduler at it, not just
    # once at GUI startup -- guarantees CACHED_EXE_PATH actually exists and
    # matches the running exe at the moment it's needed, regardless of how
    # long the GUI's been open or whether the cache was cleared some other way.
    _refresh_exe_cache()
    exe_path, arguments, working_dir = _resolve_scheduled_action()
    return _call_task_scheduler(ts.install_task, exe_path, arguments, working_dir, interval)


def _get_task_status_code() -> str:
    return ts.get_task_status()


def _do_sync_installed_task() -> tuple[bool, str]:
    """Re-registers the scheduled task with whatever POLL_INTERVAL_MINUTES
    was just saved, preserving its enabled/disabled state. Called after a
    Settings Save so a changed interval takes effect without a separate
    Install click — but install_task() always sets Enabled=True on the task
    it (re)registers (see task_scheduler.py), so a task the user had
    deliberately disabled needs disabling again right after, or Save would
    silently turn a disabled watcher back on."""
    was_disabled = _get_task_status_code() == "disabled"
    ok, output = _do_install()
    if not ok:
        return ok, output
    if was_disabled:
        return _call_task_scheduler(ts.set_enabled, False)
    return True, ""


def _version_tuple(version: str) -> tuple[int, ...]:
    """"1.2.3" -> (1, 2, 3), for a plain numeric comparison — a version
    string that doesn't parse this way (or isn't found at all) sorts as
    (), i.e. never counts as newer than anything real."""
    try:
        return tuple(int(p) for p in version.split("."))
    except ValueError:
        return ()


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Full reset — deletes everything this app has ever written, so a broken or
# half-migrated config from an older version can be cleared without hunting
# through AppData by hand.
#
# This is the only destructive path in the app, and PROJECT_DIR is wherever
# the user happens to keep the .exe — very possibly Documents or Downloads,
# full of files that are none of our business. So nothing here deletes a
# directory it merely *expects* to be ours: every target is verified to be
# at an exactly-computed path, to be the right kind of object, and to not be
# a symlink/junction (which could otherwise redirect a recursive delete
# somewhere catastrophic).
# ---------------------------------------------------------------------------
def _appdata_dir_is_safe_to_delete(target: Path) -> bool:
    """True only for the one specific folder we own under %LOCALAPPDATA%."""
    try:
        local_appdata = Path(os.environ["LOCALAPPDATA"]).resolve(strict=True)
        expected = (local_appdata / "GazetteDrouotWatcher").resolve(strict=False)
        if target.resolve(strict=False) != expected:
            return False
        # A junction pointing elsewhere would make rmtree walk into some
        # unrelated tree, so refuse rather than follow it.
        if target.is_symlink() or not target.is_dir():
            return False
        # Belt and braces: never the drive root, never AppData\Local itself.
        resolved = target.resolve(strict=False)
        if resolved == local_appdata or resolved.parent == resolved:
            return False
        return resolved.name == "GazetteDrouotWatcher"
    except Exception:
        return False


def _looks_like_source_checkout(folder: Path) -> bool:
    """True if `folder` is the gazette_watcher *source package* rather than
    the bare data folder older builds dropped next to the .exe.

    This matters because a built .exe is very often kept inside its own
    source repo, so PROJECT_DIR and the checkout are the same place -- and
    deleting config.py there destroys a real tracked file rather than a
    stale leftover. The data folder only ever contained config.py; the
    package obviously has the rest of the modules beside it."""
    try:
        return any(
            (folder / name).is_file()
            for name in ("watcher.py", "scraper.py", "notifier.py", "task_scheduler.py", "state.py")
        )
    except Exception:
        return True  # can't tell -> assume it's source and leave it alone


def _delete_tree_resilient(root: Path) -> list[str]:
    """Deletes `root` bottom-up, retrying each entry briefly, and returns
    whatever survived instead of aborting the whole operation.

    shutil.rmtree gives up entirely the moment one file is locked, which in
    practice meant a single transient handle on watcher.log -- Windows
    Search indexing it, an antivirus scanning it, or the user having it
    open in a viewer -- blocked the entire reset. Everything here is
    independent, so one stubborn file shouldn't save the rest."""
    survivors: list[str] = []

    def remove(path: Path, remover):
        # Two quick retries: the common case is a handle being released a
        # fraction of a second later, not a permanent lock.
        for attempt in range(3):
            try:
                remover(path)
                return True
            except OSError:
                if attempt < 2:
                    time.sleep(0.25)
        survivors.append(str(path))
        return False

    for current, dirs, files in os.walk(root, topdown=False):
        current_path = Path(current)
        for name in files:
            remove(current_path / name, lambda p: p.unlink())
        for name in dirs:
            sub = current_path / name
            # Only ever rmdir: a junction inside would otherwise be walked
            # into, and a non-empty dir means something above survived.
            if not any(sub.iterdir()) if sub.is_dir() else False:
                remove(sub, lambda p: p.rmdir())
            elif sub.is_dir():
                survivors.append(str(sub))
    if not survivors:
        remove(root, lambda p: p.rmdir())
    return survivors


def _delete_all_app_data() -> tuple[list[str], list[str]]:
    """Removes the AppData folder plus the legacy next-to-the-exe config
    files older builds used to write. Returns (deleted, failed) as display
    strings for the confirmation log."""
    deleted: list[str] = []
    failed: list[str] = []

    if APPDATA_DIR.exists():
        if _appdata_dir_is_safe_to_delete(APPDATA_DIR):
            survivors = _delete_tree_resilient(APPDATA_DIR)
            if not APPDATA_DIR.exists():
                deleted.append(str(APPDATA_DIR))
            else:
                # Everything that actually holds settings/state is gone even
                # in this case -- what survives a reset is essentially always
                # the log file, which is regenerated and harmless. Report it
                # so nothing is hidden, but don't call the reset a failure.
                deleted.append(f"{APPDATA_DIR} (partially)")
                for path in survivors:
                    failed.append(f"{path} (in use by another program)")
        else:
            failed.append(f"{APPDATA_DIR} (failed a safety check, left untouched)")

    # Legacy leftovers from before everything moved to AppData. Frozen only:
    # running from source, PROJECT_DIR/gazette_watcher/ is the actual source
    # package, and config.py in it is a real tracked file -- deleting the
    # developer's own checkout would be an unpleasant surprise.
    if getattr(sys, "frozen", False):
        legacy_paths = [PROJECT_DIR / "gui_prefs.json"]
        # Only when it's genuinely the old data folder -- a built .exe is
        # commonly kept inside its own source repo, and this deleted a real
        # tracked config.py there before this check existed.
        if not _looks_like_source_checkout(PROJECT_DIR / "gazette_watcher"):
            legacy_paths.insert(0, PROJECT_DIR / "gazette_watcher" / "config.py")
        for legacy in legacy_paths:
            try:
                # is_file() is False for directories and for broken links,
                # so this can only ever remove a real regular file at the
                # one exact path we constructed.
                if legacy.is_file() and not legacy.is_symlink():
                    legacy.unlink()
                    deleted.append(str(legacy))
            except Exception as e:
                failed.append(f"{legacy} ({e})")

        # Only if our own folder is now genuinely empty -- rmdir refuses to
        # remove a non-empty directory, so anything else living in there
        # (the user's, or a source checkout) keeps it alive untouched.
        legacy_dir = PROJECT_DIR / "gazette_watcher"
        try:
            if legacy_dir.is_dir() and not legacy_dir.is_symlink() and not any(legacy_dir.iterdir()):
                legacy_dir.rmdir()
                deleted.append(str(legacy_dir))
        except Exception:
            pass  # non-empty or in use -- nothing worth reporting

    return deleted, failed


def _relaunch_self() -> bool:
    """Starts a fresh copy of this app (the visible one the user launched,
    not the AppData cache, which the reset just deleted)."""
    try:
        if getattr(sys, "frozen", False):
            os.startfile(sys.executable)
        else:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve())], close_fds=True)
        return True
    except Exception:
        return False


def _relaunch_as_admin() -> bool:
    """Re-runs this same GUI (script or frozen exe) elevated via the
    standard Windows UAC prompt. Returns whether an elevated process
    actually got launched -- ShellExecuteW blocks until the UAC prompt is
    resolved, then returns a real instance handle (> 32) on success, or
    one of a handful of small SE_ERR_* codes (<= 32, e.g. 5 for
    "access denied") if the user clicked No/Cancel on it. Callers use
    this to decide whether to close the current window: closing it when
    nothing actually launched to replace it would just lose the user's
    open session for nothing."""
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, ""
    else:
        exe, params = sys.executable, f'"{Path(__file__).resolve()}"'
    ctypes.windll.shell32.ShellExecuteW.restype = ctypes.c_void_p
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, str(PROJECT_DIR), 1)
    return (result or 0) > 32


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
THEMES = {
    # "Indigo Slate" -- picked after comparing 5 candidates side by side
    # (see git tag before-light-theme-experiment for the old flat
    # white/grey version and the other 4 candidates).
    "light": {
        "bg": "#F5F6FA",
        "fg": "#1E2129",
        "entry_bg": "#FFFFFF",
        "entry_fg": "#1E2129",
        "desc_fg": "#6B7280",
        "log_bg": "#FFFFFF",
        "log_fg": "#1E2129",
        "border": "#D8DAE5",
        "link_fg": "#4F46E5",
        "warning_fg": "#DC2626",
        "danger_active": "#B91C1C",  # pressed/hover shade of warning_fg
        "accent_active": "#4338CA",  # pressed/hover shade of link_fg, for filled Primary.TButton
        "accent_fg": "#FFFFFF",  # text color on top of a link_fg-filled button
        "disabled_fg": "#79808E",  # disabled BUTTON text -- desc_fg is too low-contrast for this
    },
    # Dracula palette (https://draculatheme.com) — Background/Foreground for
    # the base, Selection for input fields (visually distinct from the main
    # background), Comment for secondary/description text.
    "dark": {
        "bg": "#282A36",
        "fg": "#F8F8F2",
        "entry_bg": "#44475A",
        "entry_fg": "#F8F8F2",
        "desc_fg": "#6272A4",
        "log_bg": "#282A36",
        "log_fg": "#F8F8F2",
        "border": "#6272A4",
        "link_fg": "#8BE9FD",  # Dracula Cyan
        "warning_fg": "#FF5555",  # Dracula Red
        "danger_active": "#E14747",  # pressed/hover shade of warning_fg
        "accent_active": "#62D9F0",  # pressed/hover shade of link_fg, for filled Primary.TButton
        "accent_fg": "#282A36",  # dark text on top of the bright cyan-filled button, matches bg
        "disabled_fg": "#9AA0C0",  # disabled BUTTON text -- desc_fg happens to equal border in
        # this theme (#6272A4 == #6272A4), so a disabled Primary.TButton (background=border) with
        # foreground=desc_fg rendered completely invisible text -- same color on same color.
    },
}

# Unsaved-change indicator colors for settings rows — constant across both
# themes (they're accent/status colors, not base palette) with dark text
# that stays readable on either bright background.
DIRTY_BG = "#FFB86C"  # Dracula Orange — row has an edit not yet saved
DIRTY_FG = "#282A36"
FLASH_BG = "#50FA7B"  # Dracula Green — briefly shown right after Save
FLASH_FG = "#282A36"

# Same idea, applied to the Save/Reload/Reset buttons themselves rather than
# individual rows — pastel tints (not the same saturated orange/green above,
# which would visually read as "just saved" rather than "has unsaved
# changes") so it's readable as a hint rather than a status flash.
SAVE_BUTTON_DIRTY_BG = "#C6F6C6"  # light green
RELOAD_BUTTON_DIRTY_BG = "#FFF3B0"  # light yellow
RESET_BUTTON_DIRTY_BG = "#FFD9A0"  # light orange
DIRTY_BUTTON_FG = "#282A36"


def _set_titlebar_theme(root: tk.Tk, dark: bool):
    """The window's own titlebar (icon/text/min-max-close buttons) is drawn
    by Windows itself (DWM), not Tkinter — self.configure(bg=...) never
    touches it. This asks DWM directly to draw it dark or light, via the
    window's real top-level HWND (winfo_id() alone can point at an internal
    Tk child window, not the actual top-level frame DWM manages)."""
    try:
        GA_ROOT = 2
        hwnd = ctypes.windll.user32.GetAncestor(root.winfo_id(), GA_ROOT)
        value = ctypes.c_int(1 if dark else 0)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE on Windows 10 20H1+ / 11;
        # 19 was the same attribute's id on early Windows 10 dark-mode
        # preview builds — try both, ignore whichever one the OS rejects.
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass


def _detect_os_theme() -> str:
    """Reads Windows' current app theme (light/dark) from the registry."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if value else "dark"
    except Exception:
        return "light"


def _virtual_screen_bounds() -> tuple[int, int, int, int]:
    """(x, y, width, height) of the full virtual desktop — spans every
    connected monitor, not just the primary one (winfo_screenwidth/height
    only ever reports the primary monitor, which isn't good enough here:
    the saved window position could be on a secondary monitor)."""
    gsm = ctypes.windll.user32.GetSystemMetrics
    SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
    return gsm(SM_XVIRTUALSCREEN), gsm(SM_YVIRTUALSCREEN), gsm(SM_CXVIRTUALSCREEN), gsm(SM_CYVIRTUALSCREEN)


def _primary_screen_size() -> tuple[int, int]:
    """(width, height) of specifically the PRIMARY monitor — the one
    Windows treats as "main" in Display Settings, wherever the taskbar
    lives, regardless of its actual resolution (most screens aren't the
    2560x1440 this was developed on). Deliberately not using Tk's own
    winfo_screenwidth/height here — those aren't consistently reliable
    across different multi-monitor/DPI setups, whereas asking Windows
    itself via GetSystemMetrics always reflects the real primary monitor."""
    gsm = ctypes.windll.user32.GetSystemMetrics
    SM_CXSCREEN, SM_CYSCREEN = 0, 1
    return gsm(SM_CXSCREEN), gsm(SM_CYSCREEN)


def _saved_geometry_if_onscreen(prefs: dict) -> tuple[int, int, int, int] | None:
    """Returns the saved (x, y, w, h) only if enough of the titlebar would
    actually be visible/reachable on the CURRENT monitor setup — e.g. a
    second monitor the window was on last time might be unplugged now.
    Returns None (caller falls back to the default size/position) otherwise."""
    win = prefs.get("window")
    if not isinstance(win, dict):
        return None
    try:
        x, y, w, h = int(win["x"]), int(win["y"]), int(win["w"]), int(win["h"])
    except (KeyError, TypeError, ValueError):
        return None
    if w < 200 or h < 200:
        return None

    vx, vy, vw, vh = _virtual_screen_bounds()
    titlebar_h = 40  # enough to grab and drag the window back onscreen
    min_visible_w = 80  # enough of the titlebar's width to click into

    if y < vy or y > vy + vh - titlebar_h:
        return None
    if x + w < vx + min_visible_w or x > vx + vw - min_visible_w:
        return None
    return x, y, w, h


def _load_gui_prefs() -> dict:
    if GUI_PREFS_PATH.exists():
        try:
            return json.loads(GUI_PREFS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_gui_prefs(prefs: dict, _reason: str = ""):
    _log_ui(f"file written: {GUI_PREFS_PATH}" + (f" ({_reason})" if _reason else ""))
    try:
        GUI_PREFS_PATH.write_text(json.dumps(prefs), encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # A running process can't gain/lose elevation without restarting, so
        # this is checked once here rather than on every button click —
        # every action-button's disabled/normal state derives from it.
        self._is_admin_at_launch = _is_admin()
        self._tray_icon: tray_icon.TrayIcon | None = None
        self.minsize(640, 560)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        if ICON_PATH.exists():
            # Sets both the window/taskbar icon here, and — since PyInstaller
            # also embeds this same file as the .exe's own resource icon
            # (see the build command in README) — matches what File Explorer
            # shows for the .exe too.
            try:
                self.iconbitmap(str(ICON_PATH))
            except tk.TclError:
                pass

        # int/float fields get live "stupid proofing" — keystrokes that
        # can't possibly be part of a valid value are simply rejected.
        self._vcmd_int = (self.register(self._validate_int_input), "%P")
        self._vcmd_float = (self.register(self._validate_float_input), "%P")

        # Windows renders flag emoji as plain two-letter codes, not actual
        # flag pictures (a deliberate Microsoft choice, not a font bug with
        # a workaround) — so real flag icons are drawn ourselves. Built
        # once and kept alive for the app's lifetime; a PhotoImage with no
        # surviving Python reference gets silently garbage-collected and
        # the image just vanishes from the widget.
        self._flag_images = {code: tk.PhotoImage(data=flags.FLAGS[code]) for code, _flag, _name in i18n.LANGUAGES}

        prefs = _load_gui_prefs()

        # Restore the last-used window position/size, but only if it'd
        # actually be reachable on this monitor setup right now (e.g. a
        # second monitor it was on last time could be unplugged). Otherwise
        # — which includes the very first launch ever, before any position
        # has been saved — center on the primary monitor rather than
        # letting Windows pick an arbitrary spot.
        restored = _saved_geometry_if_onscreen(prefs)
        if restored:
            x, y, w, h = restored
            self.geometry(f"{w}x{h}+{x}+{y}")
        else:
            w, h = 836, 858  # 760x780 default, +10% both dimensions
            sw, sh = _primary_screen_size()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")

        # First launch (no saved preference yet) follows the OS theme; once
        # the sun/moon icon is clicked, that explicit choice is remembered
        # and wins from then on. Same pattern for language, via the OS's
        # UI language instead of its theme.
        saved_theme = prefs.get("theme")
        self.current_theme = saved_theme if saved_theme in ("light", "dark") else _detect_os_theme()

        saved_lang = prefs.get("language")
        supported = {code for code, _flag, _name in i18n.LANGUAGES}
        self.lang = saved_lang if saved_lang in supported else i18n.detect_os_language()

        self.style = ttk.Style(self)
        self.style.theme_use("clam")  # base theme that actually honors custom colors on Windows

        self._build_all()
        _log_ui(
            f"--- control panel opened (v{APP_VERSION}, "
            f"{'administrator' if self._is_admin_at_launch else 'standard user'}, "
            f"language={self.lang}, theme={self.current_theme}) ---"
        )
        _log_ui(f"running from: {sys.executable}")
        self.after(150, self._maybe_show_first_run_guide)

    def _maybe_show_first_run_guide(self):
        """Shown on every launch — not just the first ever — until the
        user checks "don't show this again" inside the dialog itself (or
        unchecks the equivalent checkbox in the header, see
        _build_header). Tracked as show_guide_on_start in gui_prefs.json,
        defaulting to True (shown) when absent, e.g. on a fresh install.
        Content here is a placeholder — the real step-by-step guide is
        meant to be written later; this just makes sure the mechanism is
        already in place and working."""
        if _load_gui_prefs().get("show_guide_on_start", True):
            self._show_first_run_guide()

    def _show_first_run_guide(self):
        _log_ui("setup guide window opened")
        c = self._theme_colors()
        win = tk.Toplevel(self)
        win.title(self.t("welcome_title"))
        # Center over the main window (standard modal-dialog behavior) —
        # by this point the main window is itself already centered on the
        # primary monitor, so this lands near screen-center too.
        w, h = 777, 420  # 676 width +15% (already +30% over the original 520) -- still too narrow
        px, py = self.winfo_x(), self.winfo_y()
        pw, ph = self.winfo_width(), self.winfo_height()
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.configure(bg=c["bg"])
        win.transient(self)
        win.grab_set()
        if ICON_PATH.exists():
            try:
                win.iconbitmap(str(ICON_PATH))
            except tk.TclError:
                pass

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=self.t("welcome_title"), font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))

        dont_show_var = tk.BooleanVar(value=False)

        def dismiss():
            if dont_show_var.get():
                self._set_show_guide_on_start(False)
            win.destroy()

        # Packed to the bottom BEFORE the expanding text body below, so it
        # always reserves its own space and can never get squeezed out by
        # the body's fill=both/expand=True claiming the whole window —
        # that's what was happening before (only visible after a manual
        # resize gave Tk enough room to fit everything at once).
        bottom_row = ttk.Frame(frame)
        bottom_row.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Checkbutton(bottom_row, text=self.t("welcome_dont_show_again"), variable=dont_show_var).pack(side="left")
        ttk.Button(bottom_row, text=self.t("welcome_dismiss"), command=dismiss).pack(side="right")

        # Packed side="bottom" right after bottom_row (so it lands just
        # above it, below the scrolled body) -- only shown when not already
        # elevated, since without that the scheduled task can't actually be
        # kept in sync with Settings changes (Install/Enable/Disable/
        # Uninstall/Save all need it).
        if not _is_admin():
            # Stacked (label above, button below) rather than side-by-side —
            # side-by-side meant the button's own width ate into the space
            # left for the label, and widening the whole dialog to fit both
            # on one line never quite kept up with translations of either.
            # Stacked, the button always gets its full natural width
            # regardless of how long the label's text ends up being.
            # Red + bold (not just the grey/secondary Desc.TLabel style
            # used elsewhere) so it's impossible to miss — this is the one
            # thing in the whole guide that actually affects whether
            # Settings changes reach the scheduled task.
            self.style.configure("Warning.TLabel", background=c["bg"], foreground=c["warning_fg"], font=("Segoe UI", 9, "bold"))
            admin_row = ttk.Frame(frame)
            admin_row.pack(side="bottom", fill="x", pady=(0, 8))
            ttk.Label(admin_row, text=self.t("guide_admin_note"), wraplength=600, style="Warning.TLabel").pack(
                anchor="w", fill="x"
            )
            self.style.configure("RestartAdmin.TButton", background=SAVE_BUTTON_DIRTY_BG, foreground=DIRTY_BUTTON_FG)
            ttk.Button(
                admin_row,
                text=self.t("btn_restart_admin"),
                command=self._on_restart_as_admin_click,
                style="RestartAdmin.TButton",
            ).pack(anchor="e", pady=(6, 0))

        body = scrolledtext.ScrolledText(frame, wrap="word", font=("Segoe UI", 10))
        body.tag_configure("h", font=("Segoe UI", 11, "bold"), spacing1=6, spacing3=4)
        body.tag_configure("p", font=("Segoe UI", 10), spacing3=10)
        body.tag_configure("path", font=("Consolas", 9), foreground=c["desc_fg"], spacing3=10)
        # "**...**" inside a paragraph marks the single sentence most worth
        # a non-technical user actually noticing and remembering (right
        # now: moving the app needs reopening it once from the new spot) --
        # red + underlined instead of the normal paragraph style.
        body.tag_configure("warn_inline", font=("Segoe UI", 10, "underline"), foreground=c["warning_fg"])
        # welcome_body is 8 "\n\n"-separated paragraphs (verified to match
        # this across every language) with welcome_h1..welcome_h8 as their
        # titles, kept as separate short keys rather than folding the
        # titles into welcome_body itself — much less to re-translate
        # correctly than re-editing 8 paragraphs of running prose in 9
        # languages every time a title needs a tweak.
        titles = [self.t(f"welcome_h{i}") for i in range(1, 9)]
        paragraphs = self.t("welcome_body").split("\n\n")
        for i, (title, paragraph) in enumerate(zip(titles, paragraphs), start=1):
            body.insert("end", title + "\n", "h")
            for j, part in enumerate(re.split(r"\*\*(.+?)\*\*", paragraph, flags=re.DOTALL)):
                if part:
                    body.insert("end", part, "warn_inline" if j % 2 else "p")
            body.insert("end", "\n", "p")
            if i == 5:
                # welcome_h5 ("Your settings and files") — the actual path
                # it's talking about, greyed out like other secondary/
                # supporting text rather than translated prose.
                body.insert("end", str(APPDATA_DIR) + "\n", "path")
            body.insert("end", "\n")
        body.configure(state="disabled", bg=c["entry_bg"], fg=c["entry_fg"])
        body.pack(fill="both", expand=True)

        win.protocol("WM_DELETE_WINDOW", dismiss)
        win.wait_window()

    def _set_show_guide_on_start(self, value: bool):
        _log_ui(f"setting changed: show setup guide at startup -> {value}")
        _save_gui_prefs({**_load_gui_prefs(), "show_guide_on_start": value}, "show setup guide at startup")
        if hasattr(self, "show_guide_var"):
            self.show_guide_var.set(value)

    def t(self, key: str, **kwargs) -> str:
        return i18n.t(self.lang, key, **kwargs)

    # -- (re)building the whole UI ------------------------------------------
    def _build_all(self):
        """Builds every section fresh. Used at startup, and again whenever
        the language changes (simplest reliable way to re-render every
        label without hunting down and updating each widget individually)."""
        self.field_vars: dict[str, tuple[tk.Variable, str]] = {}
        self.rubrique_rows: list[dict] = []  # each: {"frame":..., "key":Var, "label":Var, "url":Var}
        self._desc_labels: list[ttk.Label] = []  # "Desc.TLabel"-styled labels, re-themed on theme change

        # Unsaved-change ("dirty") tracking for the orange/green row
        # highlighting — see _apply_row_style, _is_field_dirty,
        # _is_rubrique_dirty.
        self._row_styles: dict[str, dict[str, str]] = {}  # SIMPLE_FIELDS name -> per-row ttk style names
        self._baseline_simple: dict[str, object] = {}  # SIMPLE_FIELDS name -> last loaded/saved value
        self._rubrique_row_counter = 0  # gives each rubrique row its own unique style names

        self.title(f"Gazette Drouot Watcher — {self.t('window_title_suffix')}")

        self._build_header()
        self._build_updates_section()
        self._build_task_section()
        self._build_settings_section()
        self._build_log_section()
        self._build_reset_section()

        self.apply_theme(self.current_theme)
        self.refresh_status()
        self.load_settings()

    def rebuild_ui(self):
        for child in self.winfo_children():
            child.destroy()
        self._build_all()

    # -- input validation (live, on keystroke) -------------------------------
    @staticmethod
    def _validate_int_input(proposed: str) -> bool:
        if proposed == "":
            return True
        return proposed.isdigit()

    @staticmethod
    def _validate_float_input(proposed: str) -> bool:
        if proposed == "":
            return True
        # Accept digits and at most one decimal separator, either "." or ","
        # (both get normalized to "." when actually parsed on save).
        separators = proposed.count(".") + proposed.count(",")
        if separators > 1:
            return False
        return all(ch.isdigit() or ch in ".," for ch in proposed)

    @staticmethod
    def _parse_float(raw: str) -> float:
        return float(raw.replace(",", "."))

    # -- header ---------------------------------------------------------------
    def _build_header(self):
        self.header_frame = ttk.Frame(self, padding=12)
        self.header_frame.pack(fill="x")

        top_row = ttk.Frame(self.header_frame)
        top_row.pack(fill="x")
        ttk.Label(top_row, text="Gazette Drouot Watcher", font=("Segoe UI", 14, "bold")).pack(side="left")

        icons_box = ttk.Frame(top_row)
        icons_box.pack(side="right")

        # Sun/moon icon toggle — shows the currently-active mode, click to switch.
        self.theme_toggle = tk.Label(icons_box, cursor="hand2", font=("Segoe UI Emoji", 14))
        self.theme_toggle.pack(side="right")
        self.theme_toggle.bind("<Button-1>", lambda e: self.on_theme_toggle())

        # Flag icon — click opens a menu ("burger list") of every supported
        # language. First launch defaults to the OS UI language (falling
        # back to English); once a language is picked, that choice is saved
        # and wins over the OS language from then on.
        self.lang_toggle = tk.Label(icons_box, image=self._flag_images[self.lang], cursor="hand2", bd=1, relief="solid")
        self.lang_toggle.pack(side="right", padx=(0, 10))
        self.lang_toggle.bind("<Button-1>", lambda e: self._show_language_menu(e))

        self.desc_label = ttk.Label(self.header_frame, text=self.t("description"), wraplength=720, justify="left")
        self.desc_label.pack(anchor="w", pady=(4, 4))
        author_row = ttk.Frame(self.header_frame)
        author_row.pack(anchor="w")
        ttk.Label(author_row, text=f"{self.t('author_prefix')} ", font=("Segoe UI", 9, "italic")).pack(side="left")
        self.author_link = tk.Label(
            author_row, text=AUTHOR, font=("Segoe UI", 9, "italic", "underline"), cursor="hand2"
        )
        self.author_link.pack(side="left")
        self.author_link.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_URL))

        # App-level preference (like theme/language above, not a watcher
        # setting — lives in gui_prefs.json, applies immediately, no Save
        # needed). Brings the first-run guide back if it was dismissed.
        self.show_guide_var = tk.BooleanVar(value=_load_gui_prefs().get("show_guide_on_start", True))
        ttk.Checkbutton(
            self.header_frame,
            text=self.t("show_guide_checkbox"),
            variable=self.show_guide_var,
            command=lambda: self._set_show_guide_on_start(self.show_guide_var.get()),
        ).pack(anchor="w", pady=(6, 0))

        ttk.Separator(self).pack(fill="x")

    def _show_language_menu(self, event):
        c = self._theme_colors()
        menu = tk.Menu(self, tearoff=0, bg=c["entry_bg"], fg=c["fg"], activebackground=c["desc_fg"])
        for code, _flag, name in i18n.LANGUAGES:
            marker = "●  " if code == self.lang else "     "
            menu.add_command(
                image=self._flag_images[code],
                compound="left",
                label=f"{marker}{name}",
                command=lambda c=code: self.on_language_change(c),
            )
        menu.tk_popup(event.x_root, event.y_root)

    def on_language_change(self, code: str):
        _log_ui(f"clicked: language menu -> changed language from '{self.lang}' to '{code}'")
        if code == self.lang:
            return
        self.lang = code
        _save_gui_prefs({**_load_gui_prefs(), "language": code}, f"language = {code}")
        self.rebuild_ui()

    def on_theme_toggle(self):
        _log_ui(
            f"clicked: theme toggle -> switching from '{self.current_theme}' to "
            f"'{'light' if self.current_theme == 'dark' else 'dark'}'"
        )
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        _save_gui_prefs({**_load_gui_prefs(), "theme": self.current_theme}, f"theme = {self.current_theme}")
        self.apply_theme(self.current_theme)

    def _theme_colors(self, resolved: str | None = None) -> dict:
        return THEMES[resolved or self.current_theme]

    def apply_theme(self, resolved: str):
        self.current_theme = resolved
        c = self._theme_colors(resolved)
        self.theme_toggle.configure(text="☀" if resolved == "light" else "🌙", bg=c["bg"], fg=c["fg"])
        self.lang_toggle.configure(bg=c["bg"])
        self.author_link.configure(bg=c["bg"], fg=c["link_fg"])
        _set_titlebar_theme(self, resolved == "dark")

        self.configure(bg=c["bg"])
        self.style.configure(".", background=c["bg"], foreground=c["fg"])
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabelframe", background=c["bg"], foreground=c["fg"])
        self.style.configure("TLabelframe.Label", background=c["bg"], foreground=c["fg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        self.style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])

        # Modern flat button treatment (same idea in both themes): a thin
        # border instead of clam's default bevel, generous padding instead
        # of the cramped default, and actual hover/pressed feedback (the
        # border tints toward the accent color on hover; the fill darkens
        # slightly on press) -- previously there was no hover/press
        # feedback at all, which is a big part of why buttons read as
        # inert/dated regardless of which colors they used.
        self.style.configure(
            "TButton",
            background=c["entry_bg"],
            foreground=c["fg"],
            bordercolor=c["border"],
            borderwidth=1,
            relief="flat",
            padding=(14, 8),
        )
        self.style.map(
            "TButton",
            background=[("pressed", c["border"])],
            bordercolor=[("pressed", c["link_fg"]), ("active", c["link_fg"])],
            foreground=[("disabled", c["disabled_fg"])],
        )
        # Primary.TButton -- accent-filled, for the one main call-to-action
        # per section (Save, Install, Download update). Everything else
        # (Reload, Reset, Enable/Disable/Uninstall, Refresh, ...) stays on
        # the neutral bordered style above so the one primary action per
        # section actually stands out instead of every button competing.
        self.style.configure(
            "Primary.TButton",
            background=c["link_fg"],
            foreground=c["accent_fg"],
            bordercolor=c["link_fg"],
            borderwidth=1,
            relief="flat",
            padding=(14, 8),
        )
        self.style.map(
            "Primary.TButton",
            # Disabled falls back to the exact same neutral look as a
            # disabled plain TButton (entry_bg + disabled_fg), rather than
            # trying to dim the accent fill itself -- that's what caused
            # completely invisible text on the Install/Download update/Save
            # buttons in dark mode: background=border and foreground=desc_fg
            # happen to be the identical color there, so the text vanished
            # into its own background.
            background=[
                ("disabled", c["entry_bg"]),
                ("pressed", c["accent_active"]),
                ("active", c["accent_active"]),
            ],
            bordercolor=[("disabled", c["border"]), ("pressed", c["accent_active"]), ("active", c["accent_active"])],
            foreground=[("disabled", c["disabled_fg"])],
        )

        # Danger.TButton -- the full-reset button, and the only destructive
        # control in the app. Filled red rather than merely red-texted, so
        # it can't be mistaken for the ordinary buttons around it.
        self.style.configure(
            "Danger.TButton",
            background=c["warning_fg"],
            foreground="#FFFFFF",
            bordercolor=c["warning_fg"],
            borderwidth=1,
            relief="flat",
            padding=(14, 8),
        )
        self.style.map(
            "Danger.TButton",
            background=[("pressed", c["danger_active"]), ("active", c["danger_active"])],
            bordercolor=[("pressed", c["danger_active"]), ("active", c["danger_active"])],
            foreground=[("disabled", c["disabled_fg"])],
        )

        self.style.configure(
            "TEntry", fieldbackground=c["entry_bg"], foreground=c["entry_fg"], insertcolor=c["fg"]
        )
        self.style.configure(
            "TCombobox", fieldbackground=c["entry_bg"], foreground=c["entry_fg"], background=c["entry_bg"]
        )
        self.style.map("TCombobox", fieldbackground=[("readonly", c["entry_bg"])])
        self.style.configure("TScrollbar", background=c["bg"], troughcolor=c["bg"])

        # description-style (gray, secondary) labels use this explicit style
        self.style.configure("Desc.TLabel", background=c["bg"], foreground=c["desc_fg"])

        # non-ttk widgets need their colors set directly
        if hasattr(self, "settings_canvas"):
            self.settings_canvas.configure(bg=c["bg"], highlightbackground=c["border"])
        if hasattr(self, "log_text"):
            self.log_text.configure(bg=c["log_bg"], fg=c["log_fg"], insertbackground=c["fg"])

        # re-apply the "Desc.TLabel" style to every description label created
        # in _add_field_row (they're plain TLabel by default otherwise)
        for widget in getattr(self, "_desc_labels", []):
            widget.configure(style="Desc.TLabel")

        # Settings rows use their own per-row styles (so each can be tinted
        # orange/green independently), which the global "TFrame"/"TLabel"
        # restyle above doesn't touch — reapply them here, recomputing
        # dirty/clean per row so the highlight survives a theme switch.
        for name, styles in getattr(self, "_row_styles", {}).items():
            self._apply_row_style(styles, "dirty" if self._is_field_dirty(name) else "clean")
        for entry in getattr(self, "rubrique_rows", []):
            self._update_rubrique_row_style(entry)

        # ttk on Windows updates its style *database* immediately, but
        # doesn't always ask the compositor to actually repaint existing
        # widgets with the new colors — they visibly stay stale until some
        # unrelated event (alt-tabbing away and back) forces a redraw.
        # update_idletasks() alone isn't enough to fix that; nudging the
        # window size by a pixel and back forces a real WM_SIZE repaint,
        # which is — too small to notice, but does force it.
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        if w > 1 and h > 1:
            self.geometry(f"{w}x{h + 1}")
            self.update_idletasks()
            self.geometry(f"{w}x{h}")

    # -- update check -----------------------------------------------------------
    def _build_updates_section(self):
        frame = ttk.LabelFrame(self, text=self.t("section_updates"), padding=12)
        frame.pack(fill="x", padx=12, pady=(0, 8))

        note = ttk.Label(frame, text=self.t("updates_note"), wraplength=700, style="Desc.TLabel")
        note.pack(anchor="w", pady=(0, 8))
        self._desc_labels.append(note)

        row = ttk.Frame(frame)
        row.pack(fill="x")
        self.update_status_var = tk.StringVar(value=self.t("update_checking"))
        ttk.Label(row, textvariable=self.update_status_var).pack(side="left")
        self.update_download_button = ttk.Button(
            row,
            text=self.t("btn_download_update"),
            command=self._open_latest_release,
            state="disabled",
            style="Primary.TButton",
        )
        self.update_download_button.pack(side="right", padx=(6, 0))
        ttk.Button(row, text=self.t("btn_check_updates"), command=self._check_for_updates_async).pack(side="right")

        self._latest_release_url = RELEASES_PAGE_URL
        self._check_for_updates_async()

    def _check_for_updates_async(self):
        _log_ui(f"checking for updates (installed version {APP_VERSION})")
        self.update_status_var.set(self.t("update_checking"))
        self.update_download_button.configure(state="disabled")
        threading.Thread(target=self._check_for_updates_worker, daemon=True).start()

    def _check_for_updates_worker(self):
        """Runs off the GUI thread. Returns (version, url, reason) where
        reason is a translation key naming *why* it failed, or None on
        success -- "couldn't check" with no further detail is impossible to
        act on, and previously this failed completely silently with nothing
        written anywhere."""
        latest = url = None
        reason = "update_check_failed"
        # One retry, because the automatic check fires the instant the
        # window opens -- if that happens right after boot or resume, the
        # network stack may simply not be up yet, and a single blip
        # shouldn't be reported as "couldn't check for updates".
        for attempt in (1, 2):
            try:
                req = urllib.request.Request(
                    GITHUB_LATEST_RELEASE_API,
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "GazetteDrouotWatcher"},
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                latest = str(data.get("tag_name", "")).lstrip("vV")
                url = data.get("html_url") or RELEASES_PAGE_URL
                reason = None
                break
            except urllib.error.HTTPError as e:
                # GitHub allows 60 unauthenticated API calls per hour per
                # IP. We spend one per launch plus one per button click,
                # so this is only realistically reachable by someone
                # repeatedly relaunching the app (or several people behind
                # one address). It answers 403 with the remaining budget at
                # zero, which is what separates it from a real failure.
                if e.code in (403, 429) and e.headers.get("X-RateLimit-Remaining") == "0":
                    reason = "update_check_rate_limited"
                else:
                    reason = "update_check_failed"
                _log_ui(f"update check failed: HTTP {e.code} {e.reason}")
                break  # a real answer from GitHub -- retrying won't change it
            except urllib.error.URLError as e:
                # Certificate verification failing is NOT the same as being
                # offline, and telling someone to check their internet
                # connection when the real cause is TLS interception (an
                # antivirus or corporate proxy substituting its own
                # certificate) sends them looking in the wrong place
                # entirely. Note we only ever report this -- never retry
                # with verification disabled, which would turn a warning
                # sign into an actual vulnerability.
                if isinstance(getattr(e, "reason", None), ssl.SSLError):
                    reason = "update_check_tls_blocked"
                    _log_ui(f"update check failed, TLS verification: {e.reason}")
                    break
                reason = "update_check_offline"
                _log_ui(f"update check failed, host unreachable (attempt {attempt}): {e.reason}")
            except Exception as e:
                reason = "update_check_failed"
                _log_ui(f"update check failed (attempt {attempt}): {type(e).__name__}: {e}")
            if attempt == 1:
                time.sleep(2)

        # This runs on a background thread, so the window may have been
        # closed (and self already destroyed) by the time the request
        # comes back -- self.after() itself would raise in that case,
        # which would otherwise surface as an unhandled exception on a
        # daemon thread right as the app is shutting down.
        try:
            self.after(0, self._on_update_check_done, latest, url, reason)
        except (RuntimeError, tk.TclError):
            pass

    def _on_update_check_done(self, latest_version: str | None, url: str | None, reason: str | None = None):
        if not self.winfo_exists():
            return
        if not latest_version:
            _log_ui(f"update check result: could not check ({reason})")
            self.update_status_var.set(self.t(reason or "update_check_failed"))
            return
        self._latest_release_url = url or RELEASES_PAGE_URL
        _log_ui(f"update check result: latest is v{latest_version}, installed is v{APP_VERSION}")
        if _version_tuple(latest_version) > _version_tuple(APP_VERSION):
            self.update_status_var.set(self.t("update_available", version=latest_version))
            self.update_download_button.configure(state="normal")
        else:
            self.update_status_var.set(self.t("update_up_to_date", version=APP_VERSION))

    def _open_latest_release(self):
        _log_ui(f"clicked: Download update -> opening {self._latest_release_url}")
        webbrowser.open(self._latest_release_url)

    # -- scheduled task controls ---------------------------------------------
    def _build_task_section(self):
        frame = ttk.LabelFrame(self, text=self.t("section_task"), padding=12)
        frame.pack(fill="x", padx=12, pady=8)

        note = ttk.Label(frame, text=self.t("task_note"), wraplength=700, style="Desc.TLabel")
        note.pack(anchor="w", pady=(0, 8))
        self._desc_labels.append(note)

        status_row = ttk.Frame(frame)
        status_row.pack(fill="x")
        ttk.Label(status_row, text=self.t("status_label")).pack(side="left")
        self.status_var = tk.StringVar(value=self.t("status_checking"))
        ttk.Label(status_row, textvariable=self.status_var, font=("Segoe UI", 9, "bold")).pack(
            side="left", padx=(4, 0)
        )
        ttk.Button(status_row, text=self.t("btn_refresh"), command=self.refresh_status).pack(side="right")
        ttk.Button(
            status_row,
            text=self.t("btn_open_activity_log"),
            command=lambda: self._open_log_file(UI_LOG_PATH, "btn_open_activity_log"),
        ).pack(side="right", padx=(0, 6))
        ttk.Button(status_row, text=self.t("btn_open_log"), command=self._open_log_file).pack(
            side="right", padx=(0, 6)
        )

        action_state = "normal" if self._is_admin_at_launch else "disabled"

        if not self._is_admin_at_launch:
            admin_row = ttk.Frame(frame)
            admin_row.pack(fill="x", pady=(8, 0))
            note2 = ttk.Label(admin_row, text=self.t("guide_admin_note"), wraplength=560, style="Desc.TLabel")
            note2.pack(side="left", fill="x", expand=True)
            self._desc_labels.append(note2)
            self.style.configure("RestartAdmin.TButton", background=SAVE_BUTTON_DIRTY_BG, foreground=DIRTY_BUTTON_FG)
            ttk.Button(
                admin_row,
                text=self.t("btn_restart_admin"),
                command=self._on_restart_as_admin_click,
                style="RestartAdmin.TButton",
            ).pack(side="right", padx=(8, 0))

        buttons_row = ttk.Frame(frame)
        buttons_row.pack(fill="x", pady=(8, 0))
        ttk.Button(
            buttons_row,
            text=self.t("btn_install"),
            command=self.on_install,
            state=action_state,
            style="Primary.TButton",
        ).pack(side="left", padx=(0, 6))
        ttk.Button(buttons_row, text=self.t("btn_enable"), command=self.on_enable, state=action_state).pack(
            side="left", padx=6
        )
        ttk.Button(buttons_row, text=self.t("btn_disable"), command=self.on_disable, state=action_state).pack(
            side="left", padx=6
        )
        ttk.Button(buttons_row, text=self.t("btn_uninstall"), command=self.on_uninstall, state=action_state).pack(
            side="left", padx=6
        )
        # No tray icon toggle here for now -- the underlying TrayIcon /
        # on_close() hide-to-tray plumbing (below) is left in place, just
        # never turned on and with no GUI path to enable it.

    def _on_restart_as_admin_click(self):
        _log_ui("clicked: Restart as Administrator")
        if _relaunch_as_admin():
            # Always a real shutdown, never hide-to-tray -- this process is
            # about to be replaced by the elevated relaunch, so leaving it
            # running hidden in the tray would just be a stray duplicate.
            self._really_quit()

    def refresh_status(self):
        code = _get_task_status_code()
        # "queued"/"running"/"unknown" are real states get_task_status() can
        # return (a scheduled run can be caught mid-flight) that this map
        # used to be missing entirely -- falling through to the raw,
        # untranslated English status string via dict.get's default.
        text = {
            "not_installed": self.t("status_not_installed"),
            "ready": self.t("status_ready"),
            "disabled": self.t("status_disabled"),
            "queued": self.t("status_queued"),
            "running": self.t("status_running"),
            "unknown": self.t("status_unknown"),
        }.get(code, code)
        self.status_var.set(text)
        if getattr(self, "_last_logged_status", None) != code:
            # Only on change: refresh_status() also runs after every action
            # and on a timer, and logging it each time would drown the file.
            self._last_logged_status = code
            _log_ui(f"scheduled task status: {code}")

    def _open_log_file(self, path=None, title_key="btn_open_log"):
        """Opens one of the two logs: what the background checks found
        (watcher.log), or what was done in this window (control_panel.log)."""
        path = path or LOG_FILE_PATH
        _log_ui(f"clicked: open log -> {path}")
        if not path.exists():
            messagebox.showinfo(self.t(title_key), self.t("log_file_missing"))
            return
        try:
            os.startfile(str(path))
        except OSError as e:
            messagebox.showerror(self.t(title_key), self.t("err_open_log_failed", error=e))

    def _run_action(self, action_key: str, fn):
        action_name = self.t(action_key)
        _log_ui(f"clicked: {action_key} ('{action_name}')")
        self.log(self.t("log_action_dashes", action=action_name))
        ok, output = fn()

        if not ok and output == _PERMISSION_DENIED_SENTINEL and not _is_admin():
            _log_ui(f"result: {action_key} -> needs administrator rights")
            self.log(self.t("log_permission_hint"))
            if messagebox.askyesno(action_name, self.t("dlg_admin_needed_body", action=action_name)):
                if _relaunch_as_admin():
                    self._really_quit()  # see _on_restart_as_admin_click -- same reasoning
            return

        # Translate the internal sentinels into something a user should
        # actually see — never show a raw __LIKE_THIS__ marker, and don't
        # log a "(no output)" filler line for the common case (success,
        # nothing to say).
        friendly = None
        if output == _NOT_INSTALLED_SENTINEL:
            friendly = self.t("diag_not_installed")
        elif output.startswith("__CONFIG_UNREADABLE__"):
            friendly = self.t("diag_config_unreadable")

        if friendly:
            self.log(friendly)
        elif output:
            self.log(output)

        _log_ui(f"result: {action_key} -> {'OK' if ok else 'FAILED'}" + (f" ({output})" if output else ""))
        self.log(self.t("log_ok") if ok else self.t("log_failed"))
        self.refresh_status()
        if not ok:
            if friendly:
                messagebox.showerror(action_name, friendly)
            else:
                # No known explanation for this one — show the actual error
                # right here instead of pointing at the (non-resizable,
                # easy-to-lose-the-relevant-line-in) log panel below.
                detail = output.strip() if output else self.t("log_failed")
                if len(detail) > 600:
                    detail = "...\n" + detail[-600:]
                messagebox.showerror(action_name, self.t("dlg_action_failed_body", action=action_name, detail=detail))

    def on_install(self):
        self._run_action("btn_install", _do_install)

    def on_uninstall(self):
        def uninstall():
            result = _call_task_scheduler(ts.uninstall_task)
            try:
                # Nothing left to click a notification into once the task is
                # gone, so don't leave the protocol handler registered.
                import browser_launch

                browser_launch.unregister_link_protocol()
            except Exception:
                pass
            return result

        self._run_action("btn_uninstall", uninstall)

    def on_enable(self):
        self._run_action("btn_enable", lambda: _call_task_scheduler(ts.set_enabled, True))

    def on_disable(self):
        self._run_action("btn_disable", lambda: _call_task_scheduler(ts.set_enabled, False))

    # -- settings section -------------------------------------------------------
    def _build_settings_section(self):
        outer = ttk.LabelFrame(self, text=self.t("section_settings"), padding=12)
        outer.pack(fill="both", expand=True, padx=12, pady=8)

        # Save/Reload/Reset live in a fixed footer OUTSIDE the scrollable
        # area (packed to the bottom first, so it always reserves its own
        # space) rather than as the last item inside the scrolled content
        # — previously they were only reachable by scrolling all the way
        # down, and putting them at the *top* of the scrolled content
        # instead wouldn't actually fix that: they'd still scroll out of
        # view the moment you scroll down to edit anything below them.
        action_state = "normal" if self._is_admin_at_launch else "disabled"

        buttons_row = ttk.Frame(outer)
        buttons_row.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Separator(outer).pack(side="bottom", fill="x", pady=(4, 0))
        self.save_button = ttk.Button(
            buttons_row, text=self.t("btn_save"), command=self.on_save_settings, state=action_state
        )
        self.save_button.pack(side="left")
        self.reload_button = ttk.Button(
            buttons_row, text=self.t("btn_reload"), command=self.load_settings, state=action_state
        )
        self.reload_button.pack(side="left", padx=6)
        self.reset_button = ttk.Button(
            buttons_row, text=self.t("btn_reset_defaults"), command=self.on_reset_defaults, state=action_state
        )
        self.reset_button.pack(side="right")
        # Not calling _update_action_button_styles() here: SIMPLE_FIELDS
        # rows don't exist yet at this point (they're added right below),
        # and a freshly created ttk.Button already renders in the plain/
        # clean "TButton" style by default anyway.

        # scrollable area, since the rubrique list can grow
        canvas = tk.Canvas(outer, highlightthickness=1)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.settings_canvas = canvas

        # Mouse wheel doesn't scroll a Canvas by default — bind it explicitly.
        # Only active while the pointer is over the settings area, so it
        # doesn't hijack scrolling elsewhere in the window.
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        # -- simple fields --
        for name, label_key, desc_key, kind in SIMPLE_FIELDS:
            self._add_field_row(self.scroll_frame, name, self.t(label_key), self.t(desc_key), kind)

        ttk.Separator(self.scroll_frame).pack(fill="x", pady=10)

        # -- rubriques (pages to watch) --
        rub_header = ttk.Frame(self.scroll_frame)
        rub_header.pack(fill="x", pady=(0, 4))
        ttk.Label(rub_header, text=self.t("pages_to_watch"), font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(
            rub_header,
            text=self.t("btn_add_page"),
            command=lambda: (_log_ui("clicked: Add page"), self._add_rubrique_row(is_new=True)),
            state=action_state,
        ).pack(side="right")

        self.rubriques_frame = ttk.Frame(self.scroll_frame)
        self.rubriques_frame.pack(fill="x")

    # -- unsaved-change ("dirty") row highlighting ---------------------------
    # Each settings row gets its own ttk style names (suffixed .TFrame/
    # .TLabel/... so ttk reuses the matching built-in layout — same trick
    # as the existing "Desc.TLabel" style) instead of the shared "TFrame"/
    # "TLabel" styles, so it can be tinted independently of every other row.
    def _apply_row_style(self, style_names: dict, state: str):
        if state == "dirty":
            bg, fg = DIRTY_BG, DIRTY_FG
        elif state == "flash":
            bg, fg = FLASH_BG, FLASH_FG
        else:
            c = self._theme_colors()
            bg, fg = c["bg"], c["fg"]
        self.style.configure(style_names["row"], background=bg)
        if "label" in style_names:
            self.style.configure(style_names["label"], background=bg, foreground=fg)
        if "desc" in style_names:
            self.style.configure(style_names["desc"], background=bg, foreground=fg)
        if "checkbutton" in style_names:
            self.style.configure(style_names["checkbutton"], background=bg, foreground=fg)

    def _is_field_dirty(self, name: str) -> bool:
        var, kind = self.field_vars[name]
        baseline = self._baseline_simple.get(name)
        current = bool(var.get()) if kind == "bool" else str(var.get())
        return baseline is not None and current != baseline

    def _on_field_dirty_check(self, name: str):
        dirty = self._is_field_dirty(name)
        self._apply_row_style(self._row_styles[name], "dirty" if dirty else "clean")
        self._update_action_button_styles()

    def _is_rubrique_dirty(self, entry: dict) -> bool:
        current = (entry["key"].get(), entry["label"].get(), entry["url"].get())
        return entry["is_new"] or current != entry["baseline"]

    def _update_rubrique_row_style(self, entry: dict):
        dirty = self._is_rubrique_dirty(entry)
        self._apply_row_style(entry["style"], "dirty" if dirty else "clean")
        self._update_action_button_styles()

    def _any_settings_dirty(self) -> bool:
        if any(self._is_field_dirty(name) for name, *_ in SIMPLE_FIELDS):
            return True
        return any(self._is_rubrique_dirty(e) for e in self.rubrique_rows)

    def _update_action_button_styles(self):
        """Save/Reload/Reset get a light tint whenever there's at least one
        unsaved change anywhere in Settings — the row-level orange/green
        highlighting (_apply_row_style) says *what* changed; this says
        *that* something did, visible even when the change scrolled out of
        view. Reload and Reset are tinted too since both are also ways to
        resolve that unsaved state (discard it, or reset to factory
        defaults), not just Save."""
        if not hasattr(self, "save_button"):
            return  # called during _add_field_row before the footer buttons exist yet
        if self._any_settings_dirty():
            self.style.configure("SaveDirty.TButton", background=SAVE_BUTTON_DIRTY_BG, foreground=DIRTY_BUTTON_FG)
            self.style.configure(
                "ReloadDirty.TButton", background=RELOAD_BUTTON_DIRTY_BG, foreground=DIRTY_BUTTON_FG
            )
            self.style.configure("ResetDirty.TButton", background=RESET_BUTTON_DIRTY_BG, foreground=DIRTY_BUTTON_FG)
            self.save_button.configure(style="SaveDirty.TButton")
            self.reload_button.configure(style="ReloadDirty.TButton")
            self.reset_button.configure(style="ResetDirty.TButton")
        else:
            # Save is the primary action of this section when there's
            # nothing unsaved to flag -- Reload/Reset stay on the neutral
            # style either way, they're not "the" action here.
            self.save_button.configure(style="Primary.TButton")
            self.reload_button.configure(style="TButton")
            self.reset_button.configure(style="TButton")

    def _add_field_row(self, parent, name, label, desc, kind):
        row_style = f"F{name}.TFrame"
        label_style = f"F{name}.TLabel"
        desc_style = f"F{name}Desc.TLabel"

        row = ttk.Frame(parent, style=row_style)
        row.pack(fill="x", pady=4)

        text_col = ttk.Frame(row, style=row_style)
        text_col.pack(side="left", fill="x", expand=True)
        ttk.Label(text_col, text=label, font=("Segoe UI", 9, "bold"), style=label_style).pack(anchor="w")
        desc_label = ttk.Label(text_col, text=desc, wraplength=520, style=desc_style)
        desc_label.pack(anchor="w")
        self._desc_labels.append(desc_label)

        style_names = {"row": row_style, "label": label_style, "desc": desc_style}

        if kind == "bool":
            var = tk.BooleanVar()
            cb_style = f"F{name}.TCheckbutton"
            ttk.Checkbutton(row, variable=var, style=cb_style).pack(side="right", padx=4)
            style_names["checkbutton"] = cb_style
        elif kind == "int":
            var = tk.StringVar()
            ttk.Entry(row, textvariable=var, width=16, justify="right", validate="key", validatecommand=self._vcmd_int).pack(
                side="right", padx=4
            )
        elif kind == "float":
            var = tk.StringVar()
            ttk.Entry(
                row, textvariable=var, width=16, justify="right", validate="key", validatecommand=self._vcmd_float
            ).pack(side="right", padx=4)
        elif kind == "browser":
            # Readonly so the value can only ever be one of the detected
            # browsers (or the system default) -- the config stores an .exe
            # path and a free-text box would just invite broken ones.
            var = tk.StringVar()
            self._browser_display_to_path = {self.t("browser_system_default"): ""}
            for display, exe in browser_launch.detect_browsers():
                self._browser_display_to_path[display] = exe
            ttk.Combobox(
                row,
                textvariable=var,
                values=list(self._browser_display_to_path),
                state="readonly",
                width=24,
            ).pack(side="right", padx=4)
        else:
            var = tk.StringVar()
            ttk.Entry(row, textvariable=var, width=16, justify="right").pack(side="right", padx=4)

        self.field_vars[name] = (var, kind)
        self._row_styles[name] = style_names
        self._apply_row_style(style_names, "clean")
        var.trace_add("write", lambda *_a, n=name: self._on_field_dirty_check(n))

    def _add_rubrique_row(self, key="", label="", url="", is_new=False):
        idx = self._rubrique_row_counter
        self._rubrique_row_counter += 1
        row_style = f"Rub{idx}.TFrame"
        label_style = f"Rub{idx}.TLabel"

        row = ttk.Frame(self.rubriques_frame, style=row_style)
        row.pack(fill="x", pady=3)

        key_var = tk.StringVar(value=key)
        label_var = tk.StringVar(value=label)
        url_var = tk.StringVar(value=url)

        ttk.Label(row, text=self.t("rubrique_key"), style=label_style).pack(side="left")
        ttk.Entry(row, textvariable=key_var, width=16).pack(side="left", padx=(2, 8))
        ttk.Label(row, text=self.t("rubrique_label"), style=label_style).pack(side="left")
        ttk.Entry(row, textvariable=label_var, width=16).pack(side="left", padx=(2, 8))
        ttk.Label(row, text=self.t("rubrique_url"), style=label_style).pack(side="left")
        ttk.Entry(row, textvariable=url_var, width=32).pack(side="left", padx=(2, 8), fill="x", expand=True)

        entry = {
            "frame": row,
            "key": key_var,
            "label": label_var,
            "url": url_var,
            "baseline": (key, label, url),  # values as loaded — not yet-dirty reference point
            "is_new": is_new,  # added via "+ Add page" this session, not yet saved at all
            "style": {"row": row_style, "label": label_style},
        }

        def remove():
            _log_ui(f"clicked: remove page -> key={entry['key'].get()!r} (not saved yet)")
            row.destroy()
            self.rubrique_rows.remove(entry)
            self._update_action_button_styles()

        remove_state = "normal" if self._is_admin_at_launch else "disabled"
        ttk.Button(row, text="✕", width=3, command=remove, state=remove_state).pack(side="left")

        self.rubrique_rows.append(entry)
        self._update_rubrique_row_style(entry)

        def _on_change(*_a, e=entry):
            self._update_rubrique_row_style(e)

        key_var.trace_add("write", _on_change)
        label_var.trace_add("write", _on_change)
        url_var.trace_add("write", _on_change)

    def _clear_rubrique_rows(self):
        for entry in self.rubrique_rows:
            entry["frame"].destroy()
        self.rubrique_rows = []

    def load_settings(self):
        _log_ui(f"loading settings from {CONFIG_PATH}")
        try:
            config = _load_live_config()
        except Exception as e:
            messagebox.showerror(self.t("err_load_failed_title"), self.t("err_load_failed_body", error=e))
            return

        for name, _label_key, _desc_key, kind in SIMPLE_FIELDS:
            var, _kind = self.field_vars[name]
            # getattr default: a config.py written by an older build has no
            # line for a setting added since, and that's a normal upgrade
            # state, not a corrupt file.
            value = getattr(config, name, "" if kind == "browser" else None)
            if kind == "browser":
                # Stored as an .exe path; shown as the browser's name. An
                # unknown path (browser uninstalled since, or hand-edited)
                # falls back to showing the system-default entry.
                baseline_value = self.t("browser_system_default")
                for display, exe in getattr(self, "_browser_display_to_path", {}).items():
                    if exe and str(value) and os.path.normcase(exe) == os.path.normcase(str(value)):
                        baseline_value = display
                        break
            else:
                baseline_value = bool(value) if kind == "bool" else str(value)
            # Baseline set before var.set() so the dirty-check trace it
            # fires sees "matches baseline" and colors the row clean, not
            # a stale/missing baseline that would read as dirty.
            self._baseline_simple[name] = baseline_value
            var.set(baseline_value)
            self._apply_row_style(self._row_styles[name], "clean")

        self._clear_rubrique_rows()
        for r in config.RUBRIQUES:
            self._add_rubrique_row(r.get("key", ""), r.get("label", ""), r.get("url", ""))

        self.log(self.t("log_loaded_settings"))

    def _collect_updates(self) -> dict[str, str] | None:
        """Reads the form, validates it, and returns {NAME: source_expr}
        ready for patch_config — or None (with an error dialog shown) if
        something doesn't validate."""
        updates = {}
        for name, label_key, _desc_key, kind in SIMPLE_FIELDS:
            var, _kind = self.field_vars[name]
            raw = var.get()
            try:
                if kind == "int":
                    value = int(raw)
                elif kind == "float":
                    value = self._parse_float(raw)
                elif kind == "bool":
                    value = bool(raw)
                elif kind == "browser":
                    # Back from the displayed browser name to the .exe path
                    # actually stored in config.py ("" = system default).
                    value = getattr(self, "_browser_display_to_path", {}).get(raw, "")
                else:
                    value = str(raw)
            except ValueError:
                kind_text = self.t("kind_int") if kind == "int" else self.t("kind_float")
                messagebox.showerror(
                    self.t("err_invalid_value_title"),
                    self.t("err_invalid_value_body", label=self.t(label_key), kind=kind_text, raw=raw),
                )
                return None
            updates[name] = repr(value)

        rubriques = []
        for entry in self.rubrique_rows:
            key, label, url = entry["key"].get().strip(), entry["label"].get().strip(), entry["url"].get().strip()
            if not key or not label or not url:
                messagebox.showerror(self.t("err_invalid_page_title"), self.t("err_invalid_page_body"))
                return None
            rubriques.append({"key": key, "label": label, "url": url})
        if not rubriques:
            messagebox.showerror(self.t("err_invalid_pages_title"), self.t("err_invalid_pages_body"))
            return None
        updates["RUBRIQUES"] = _format_rubriques(rubriques)

        return updates

    def on_save_settings(self):
        _log_ui("clicked: Save settings")
        updates = self._collect_updates()
        if updates is None:
            _log_ui("save aborted: a value failed validation, nothing was written")
            return

        # Recorded before the write, since load_settings() resets the
        # baselines straight afterwards -- this is the only moment both the
        # old and new values are still known.
        for name, *_ in SIMPLE_FIELDS:
            if self._is_field_dirty(name):
                old = self._baseline_simple.get(name)
                new = self.field_vars[name][0].get()
                _log_ui(f"setting changed: {name}: {old!r} -> {new!r}")
        for i, entry in enumerate(self.rubrique_rows):
            if self._is_rubrique_dirty(entry):
                now = (entry["key"].get(), entry["label"].get(), entry["url"].get())
                if entry["is_new"]:
                    _log_ui(f"page added: key={now[0]!r} label={now[1]!r} url={now[2]!r}")
                else:
                    _log_ui(f"page {i + 1} changed: {entry['baseline']!r} -> {now!r}")

        # Snapshot which rows are orange (unsaved) *before* saving — after a
        # successful save everything is clean by definition (baseline gets
        # reset to what was just written), so this is the only point where
        # we still know which rows to flash green. Rubrique rows are
        # captured by position: load_settings() below rebuilds them in the
        # same order they were just written in, so the indices still line up.
        dirty_field_names = [name for name, *_ in SIMPLE_FIELDS if self._is_field_dirty(name)]
        dirty_rubrique_indices = [i for i, e in enumerate(self.rubrique_rows) if self._is_rubrique_dirty(e)]

        try:
            source = CONFIG_PATH.read_text(encoding="utf-8")
            patched = patch_config(source, updates)
            ast.parse(patched)  # sanity check before writing
            CONFIG_PATH.write_text(patched, encoding="utf-8")
        except Exception as e:
            _log_ui(f"save FAILED, {CONFIG_PATH} left unchanged: {type(e).__name__}: {e}")
            messagebox.showerror(self.t("err_save_failed_title"), self.t("err_save_failed_body", error=e))
            return
        _log_ui(f"file written: {CONFIG_PATH}")
        self.log(self.t("log_saved_settings"))
        _sync_link_protocol()

        # If the task is already installed, re-register it now so a changed
        # POLL_INTERVAL_MINUTES takes effect immediately instead of silently
        # waiting for a manual Install click. Skipped entirely when the task
        # isn't installed at all — Save shouldn't be the thing that starts
        # scheduling it. _do_sync_installed_task() preserves disabled state.
        if _get_task_status_code() != "not_installed":
            self._run_action("action_task_sync", _do_sync_installed_task)
            if not self.winfo_exists():
                # _run_action's permission-denied path can offer to relaunch
                # as admin, which closes this window — nothing left to do.
                return

        self.load_settings()
        self._flash_saved_rows(dirty_field_names, dirty_rubrique_indices)
        messagebox.showinfo(self.t("dlg_saved_title"), self.t("dlg_saved_body"))

    def _flash_saved_rows(self, field_names: list[str], rubrique_indices: list[int]):
        """Briefly turns just-saved rows green, then back to normal — the
        visual confirmation that what was orange (unsaved) is now saved."""
        flashed_styles = [self._row_styles[n] for n in field_names if n in self._row_styles]
        for i in rubrique_indices:
            if i < len(self.rubrique_rows):
                flashed_styles.append(self.rubrique_rows[i]["style"])

        for styles in flashed_styles:
            self._apply_row_style(styles, "flash")

        def revert():
            for styles in flashed_styles:
                self._apply_row_style(styles, "clean")

        self.after(500, revert)

    def on_reset_defaults(self):
        _log_ui("clicked: Reset to defaults")
        if not messagebox.askyesno(self.t("dlg_reset_confirm_title"), self.t("dlg_reset_confirm_body")):
            return
        updates = {name: repr(DEFAULTS[name]) for name, *_ in SIMPLE_FIELDS}
        updates["RUBRIQUES"] = _format_rubriques(DEFAULT_RUBRIQUES)
        try:
            source = CONFIG_PATH.read_text(encoding="utf-8")
            patched = patch_config(source, updates)
            ast.parse(patched)
            CONFIG_PATH.write_text(patched, encoding="utf-8")
        except Exception as e:
            messagebox.showerror(self.t("err_reset_failed_title"), self.t("err_reset_failed_body", error=e))
            return
        _log_ui(f"file written: {CONFIG_PATH} (all settings restored to factory defaults)")
        self.log(self.t("log_reset_settings"))
        _sync_link_protocol()

        # Same reasoning as on_save_settings: if the task's already
        # installed, re-sync it now (reset also changes
        # POLL_INTERVAL_MINUTES back to the factory value) so the user
        # doesn't have to separately click Save right after Reset for it
        # to actually take effect. Preserves disabled state, and is
        # skipped entirely if the task isn't installed at all.
        if _get_task_status_code() != "not_installed":
            self._run_action("action_task_sync", _do_sync_installed_task)
            if not self.winfo_exists():
                return

        self.load_settings()
        messagebox.showinfo(self.t("dlg_reset_done_title"), self.t("dlg_reset_done_body"))

    # -- log area ----------------------------------------------------------------
    def _build_log_section(self):
        frame = ttk.LabelFrame(self, text=self.t("section_log"), padding=8)
        frame.pack(fill="x", padx=12, pady=(0, 12))
        self.log_text = scrolledtext.ScrolledText(
            frame, height=6, wrap="word", font=("Consolas", 9), state="disabled"
        )
        self.log_text.pack(fill="x")

    # -- full reset (very bottom of the window) --------------------------------
    def _build_reset_section(self):
        row = ttk.Frame(self, padding=(12, 0, 12, 12))
        row.pack(fill="x", side="bottom")
        note = ttk.Label(row, text=self.t("reset_all_note"), wraplength=560, style="Desc.TLabel")
        note.pack(side="left", fill="x", expand=True)
        self._desc_labels.append(note)
        ttk.Button(
            row, text=self.t("btn_reset_all"), command=self.on_reset_all, style="Danger.TButton"
        ).pack(side="right", padx=(8, 0))

    def on_reset_all(self):
        _log_ui("clicked: Reset everything and restart")
        """Deletes everything the app has written and restarts it, for when
        a config carried over from an older version is broken enough that
        editing settings can't fix it."""
        # The AppData folder holds the cached copy of the .exe, and Windows
        # locks a running executable -- so if this instance *is* that copy,
        # the delete would half-succeed and leave the folder behind. Send
        # the user to their own copy instead of failing confusingly.
        if getattr(sys, "frozen", False):
            try:
                running_from_cache = Path(sys.executable).resolve() == CACHED_EXE_PATH.resolve()
            except Exception:
                running_from_cache = False
            if running_from_cache:
                messagebox.showinfo(self.t("dlg_reset_all_title"), self.t("err_reset_all_running_from_cache"))
                return

        targets = [str(APPDATA_DIR)]
        if getattr(sys, "frozen", False):
            legacy = PROJECT_DIR / "gazette_watcher" / "config.py"
            if legacy.is_file():
                targets.append(str(legacy))
            legacy_prefs = PROJECT_DIR / "gui_prefs.json"
            if legacy_prefs.is_file():
                targets.append(str(legacy_prefs))

        if not messagebox.askyesno(
            self.t("dlg_reset_all_title"),
            self.t("dlg_reset_all_body", targets="\n".join(f"    {t}" for t in targets)),
            icon="warning",
            default="no",
        ):
            return

        _log_ui("full reset confirmed by user, deleting application data")
        deleted, failed = _delete_all_app_data()
        for _p in deleted:
            _log_ui(f"deleted: {_p}")
        for _p in failed:
            _log_ui(f"could NOT delete: {_p}")
        for path in deleted:
            self.log(self.t("log_reset_all_deleted", path=path))
        for path in failed:
            self.log(self.t("log_reset_all_failed", path=path))

        if failed:
            messagebox.showerror(self.t("dlg_reset_all_title"), self.t("err_reset_all_body", detail="\n".join(failed)))
            return

        if not _relaunch_self():
            messagebox.showerror(self.t("dlg_reset_all_title"), self.t("err_reset_all_relaunch"))
            return
        # Leave immediately: this instance still holds the now-deleted
        # settings in memory, and anything it wrote on the way out (window
        # position, prefs) would recreate the very files just removed.
        self.destroy()

    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # -- lifecycle -------------------------------------------------------------
    def on_close(self):
        """The window's own close (X) button — hides to the tray instead of
        actually exiting if the tray icon is turned on, same as any other
        minimize-to-tray app. _really_quit() (tray's own Exit item, or an
        admin relaunch replacing this process) is what actually shuts down."""
        if self._tray_icon is not None:
            self.withdraw()
            return
        self._really_quit()

    def _really_quit(self):
        _log_ui("--- control panel closed ---")
        if self._tray_icon is not None:
            self._tray_icon.stop()
            self._tray_icon = None
        try:
            prefs = _load_gui_prefs()
            prefs["window"] = {
                "x": self.winfo_x(),
                "y": self.winfo_y(),
                "w": self.winfo_width(),
                "h": self.winfo_height(),
            }
            _save_gui_prefs(prefs, "window position and size")
        except Exception:
            pass
        self.destroy()

    def _restore_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _apply_tray_icon_preference(self, enabled: bool):
        if enabled and self._tray_icon is None:
            self._tray_icon = tray_icon.TrayIcon(
                icon_path=str(ICON_PATH) if ICON_PATH.exists() else None,
                tooltip="Gazette Drouot Watcher",
                on_open=lambda: self.after(0, self._restore_from_tray),
                on_exit=lambda: self.after(0, self._really_quit),
            )
            self._tray_icon.start()
        elif not enabled and self._tray_icon is not None:
            self._tray_icon.stop()
            self._tray_icon = None

    def on_toggle_tray_icon(self, var: tk.BooleanVar):
        enabled = var.get()
        self._apply_tray_icon_preference(enabled)
        _save_gui_prefs({**_load_gui_prefs(), "show_tray_icon": enabled}, f"tray icon = {enabled}")


if __name__ == "__main__":
    if "--open-url" in sys.argv:
        # Reached only via the gazettedrouotlink: protocol handler, i.e. the
        # user clicked a notification while having explicitly chosen a
        # browser in Settings. No GUI, no watcher — resolve the browser and
        # hand the URL over. browser_launch.open_url refuses anything that
        # isn't http/https, since a registered protocol handler is callable
        # by anything on the machine.
        import browser_launch

        index = sys.argv.index("--open-url")
        raw = sys.argv[index + 1] if index + 1 < len(sys.argv) else ""
        chosen = ""
        try:
            chosen = getattr(_load_live_config(), "NOTIFICATION_BROWSER", "")
        except Exception:
            pass
        if raw:
            browser_launch.open_url(raw, chosen or None)
    elif "--watch" in sys.argv:
        # This is what Task Scheduler actually calls — run one check and exit,
        # no GUI. See gazette_watcher/watcher.py for what a "check" does --
        # unless the visible copy of the app is gone, in which case this
        # cleans up after itself instead (see _maybe_self_destruct_if_deleted).
        if not _maybe_self_destruct_if_deleted():
            # Scheduled runs are where these leftovers mostly come from, so
            # sweep here too -- synchronously, since this process exits as
            # soon as the check finishes and a daemon thread would just be
            # killed mid-delete. Capped, so it never delays a run for long.
            _cleanup_stale_pyinstaller_temp(max_to_remove=10)
            from gazette_watcher import watcher

            watcher.run()
    else:
        _refresh_exe_cache()
        _sync_link_protocol()
        _cleanup_stale_temp_in_background()
        App().mainloop()
