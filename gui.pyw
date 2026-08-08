"""
Gazette Drouot Watcher — control panel GUI.

A small desktop window for the two things you'd otherwise need PowerShell
one-liners and a text editor for: managing the Windows Task Scheduler job
(install / enable / disable / uninstall) and editing the app's settings.

Settings are shown as a plain list of labeled fields rather than the raw
config.py source — Save rewrites only the specific values that changed,
using Python's own parser to find each setting's exact location in the
file, so your comments and formatting in config.py are left untouched.
"Reset to defaults" restores every setting to what the app ships with.

The UI text itself is translated (see i18n.py) — a flag icon next to the
theme toggle opens a language menu. Switching language rebuilds the whole
window (simplest reliable way to re-render every label), which reloads
settings from disk — save first if you have unsaved edits.

Run it by double-clicking this file (Windows runs .pyw files via
pythonw.exe automatically, so no console window appears), or manually:
    pythonw.exe gui.pyw

This file only ever shells out to install_task.ps1 / uninstall_task.ps1 and
a couple of Enable-ScheduledTask/Disable-ScheduledTask calls for the task
controls — it doesn't duplicate any of that logic itself, and it never
touches state/ or logs/.
"""

import ast
import ctypes
import importlib
import json
import subprocess
import sys
import tkinter as tk
import webbrowser
import winreg
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

import flags
import i18n

# When packaged into a standalone .exe (PyInstaller), __file__ points into a
# temporary extraction folder, not where the .exe actually sits — use the
# .exe's own location instead in that case. Either way, this file/exe is
# expected to live directly in the project's root folder, next to
# gazette_watcher/, install_task.ps1, etc.
if getattr(sys, "frozen", False):
    PROJECT_DIR = Path(sys.executable).resolve().parent
else:
    PROJECT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_DIR))

CONFIG_PATH = PROJECT_DIR / "gazette_watcher" / "config.py"
INSTALL_SCRIPT = PROJECT_DIR / "install_task.ps1"
UNINSTALL_SCRIPT = PROJECT_DIR / "uninstall_task.ps1"
ICON_PATH = PROJECT_DIR / "icon.ico"
TASK_NAME = "GazetteDrouotWatcher"

# Small per-machine GUI preferences (theme + language choice) — not app
# behavior, so kept separate from gazette_watcher/config.py.
GUI_PREFS_PATH = PROJECT_DIR / "gui_prefs.json"

AUTHOR = "Grégoire Pessiot"
AUTHOR_URL = "https://github.com/EryoGreg?tab=repositories"

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
    `NAME = ...` assignment's value in place."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    targets = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in updates:
                targets.append((node.lineno, node.end_lineno, name))
    # process bottom-to-top so earlier replacements don't shift later line numbers
    targets.sort(key=lambda t: t[0], reverse=True)
    for start, end, name in targets:
        lines[start - 1 : end] = [f"{name} = {updates[name]}\n"]
    return "".join(lines)


def _load_live_config():
    """Imports (or re-imports) gazette_watcher.config fresh, to read its
    current actual values — simplest, most robust way to read the file's
    current state (the patcher above is only used for writing)."""
    if "gazette_watcher.config" in sys.modules:
        return importlib.reload(sys.modules["gazette_watcher.config"])
    return importlib.import_module("gazette_watcher.config")


# ---------------------------------------------------------------------------
# Task Scheduler helpers
# ---------------------------------------------------------------------------
# Windows-only flag that stops subprocess.run from popping up a console
# window for the PowerShell process it launches — without this, every
# button click briefly flashes a PowerShell window on screen.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

_PERMISSION_MARKERS = ("access is denied", "accessdenied", "permissiondenied", "0x80070005")


def _run_powershell(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", *args],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=_NO_WINDOW,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
    except Exception as e:
        return False, str(e)


def _get_task_status_code() -> str:
    """Returns "not_installed", "ready", "disabled", or the raw Windows
    status string for anything else we don't have a translation for."""
    ok, output = _run_powershell(
        ["-Command", f"(Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue).State"]
    )
    output = output.strip()
    if not ok or not output:
        return "not_installed"
    if output == "Ready":
        return "ready"
    if output == "Disabled":
        return "disabled"
    return output


def _is_permission_error(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in _PERMISSION_MARKERS)


# Known, expected failure patterns for the task-control actions, mapped to a
# plain-language explanation of what actually happened and what to do about
# it — shown directly in the popup instead of just "check the log", since
# the log panel isn't resizable/easy to scan for the one relevant line.
def _diagnose_task_error(lang: str, output: str) -> str | None:
    lowered = output.lower()

    # Enable/Disable (and, in principle, other task-lookup calls) against a
    # task that isn't registered — confirmed exact wording via a real test.
    if "cannot find the file specified" in lowered or "0x80070002" in lowered:
        return i18n.t(lang, "diag_not_installed")

    # install_task.ps1's own explicit check for a misconfigured Python path.
    if "pythonw.exe not found" in lowered:
        return i18n.t(lang, "diag_python_not_found")

    # install_task.ps1's own explicit check when config.py can't be parsed.
    if "couldn't read poll_interval_minutes" in lowered:
        return i18n.t(lang, "diag_config_unreadable")

    return None


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin():
    """Re-runs this same GUI (script or frozen exe) elevated via the
    standard Windows UAC prompt."""
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, ""
    else:
        exe, params = sys.executable, f'"{Path(__file__).resolve()}"'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, str(PROJECT_DIR), 1)


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#f3f3f3",
        "fg": "#1a1a1a",
        "entry_bg": "#ffffff",
        "entry_fg": "#1a1a1a",
        "desc_fg": "#666666",
        "log_bg": "#ffffff",
        "log_fg": "#1a1a1a",
        "border": "#c9c9c9",
        "link_fg": "#0066cc",
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
    },
}


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


def _save_gui_prefs(prefs: dict):
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
        # second monitor it was on last time could be unplugged) — otherwise
        # fall back to the default size and let Windows pick a position.
        restored = _saved_geometry_if_onscreen(prefs)
        if restored:
            x, y, w, h = restored
            self.geometry(f"{w}x{h}+{x}+{y}")
        else:
            self.geometry("760x780")

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

        self.title(f"Gazette Drouot Watcher — {self.t('window_title_suffix')}")

        self._build_header()
        self._build_task_section()
        self._build_settings_section()
        self._build_log_section()

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
        ttk.Separator(self).pack(fill="x")

    def _show_language_menu(self, event):
        c = THEMES[self.current_theme]
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
        if code == self.lang:
            return
        self.lang = code
        _save_gui_prefs({**_load_gui_prefs(), "language": code})
        self.rebuild_ui()

    def on_theme_toggle(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        _save_gui_prefs({**_load_gui_prefs(), "theme": self.current_theme})
        self.apply_theme(self.current_theme)

    def apply_theme(self, resolved: str):
        self.current_theme = resolved
        c = THEMES[resolved]
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
        self.style.configure("TButton", background=c["entry_bg"], foreground=c["fg"])
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

        buttons_row = ttk.Frame(frame)
        buttons_row.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons_row, text=self.t("btn_install"), command=self.on_install).pack(side="left", padx=(0, 6))
        ttk.Button(buttons_row, text=self.t("btn_enable"), command=self.on_enable).pack(side="left", padx=6)
        ttk.Button(buttons_row, text=self.t("btn_disable"), command=self.on_disable).pack(side="left", padx=6)
        ttk.Button(buttons_row, text=self.t("btn_uninstall"), command=self.on_uninstall).pack(side="left", padx=6)

    def refresh_status(self):
        code = _get_task_status_code()
        text = {"not_installed": self.t("status_not_installed"), "ready": self.t("status_ready"), "disabled": self.t("status_disabled")}.get(
            code, code
        )
        self.status_var.set(text)

    def _run_action(self, action_key: str, fn):
        action_name = self.t(action_key)
        self.log(self.t("log_action_dashes", action=action_name))
        ok, output = fn()
        self.log(output or self.t("log_no_output"))

        if not ok and not _is_admin() and _is_permission_error(output):
            self.log(self.t("log_permission_hint"))
            if messagebox.askyesno(action_name, self.t("dlg_admin_needed_body", action=action_name)):
                _relaunch_as_admin()
                self.on_close()
            return

        self.log(self.t("log_ok") if ok else self.t("log_failed"))
        self.refresh_status()
        if not ok:
            friendly = _diagnose_task_error(self.lang, output)
            if friendly:
                messagebox.showerror(action_name, friendly)
            else:
                # No known explanation for this one — show the actual error
                # right here instead of pointing at the (non-resizable,
                # easy-to-lose-the-relevant-line-in) log panel below.
                detail = output.strip() or self.t("log_no_output")
                if len(detail) > 600:
                    detail = "...\n" + detail[-600:]
                messagebox.showerror(action_name, self.t("dlg_action_failed_body", action=action_name, detail=detail))

    def on_install(self):
        self._run_action("btn_install", lambda: _run_powershell(["-File", str(INSTALL_SCRIPT)]))

    def on_uninstall(self):
        self._run_action("btn_uninstall", lambda: _run_powershell(["-File", str(UNINSTALL_SCRIPT)]))

    def on_enable(self):
        self._run_action(
            "btn_enable", lambda: _run_powershell(["-Command", f"Enable-ScheduledTask -TaskName '{TASK_NAME}'"])
        )

    def on_disable(self):
        self._run_action(
            "btn_disable", lambda: _run_powershell(["-Command", f"Disable-ScheduledTask -TaskName '{TASK_NAME}'"])
        )

    # -- settings section -------------------------------------------------------
    def _build_settings_section(self):
        outer = ttk.LabelFrame(self, text=self.t("section_settings"), padding=12)
        outer.pack(fill="both", expand=True, padx=12, pady=8)

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
        ttk.Button(rub_header, text=self.t("btn_add_page"), command=lambda: self._add_rubrique_row()).pack(
            side="right"
        )

        self.rubriques_frame = ttk.Frame(self.scroll_frame)
        self.rubriques_frame.pack(fill="x")

        ttk.Separator(self.scroll_frame).pack(fill="x", pady=10)

        buttons_row = ttk.Frame(self.scroll_frame)
        buttons_row.pack(fill="x", pady=(0, 8))
        ttk.Button(buttons_row, text=self.t("btn_save"), command=self.on_save_settings).pack(side="left")
        ttk.Button(buttons_row, text=self.t("btn_reload"), command=self.load_settings).pack(side="left", padx=6)
        ttk.Button(buttons_row, text=self.t("btn_reset_defaults"), command=self.on_reset_defaults).pack(
            side="right"
        )

    def _add_field_row(self, parent, name, label, desc, kind):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)

        text_col = ttk.Frame(row)
        text_col.pack(side="left", fill="x", expand=True)
        ttk.Label(text_col, text=label, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        desc_label = ttk.Label(text_col, text=desc, wraplength=520, style="Desc.TLabel")
        desc_label.pack(anchor="w")
        self._desc_labels.append(desc_label)

        if kind == "bool":
            var = tk.BooleanVar()
            ttk.Checkbutton(row, variable=var).pack(side="right", padx=4)
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
        else:
            var = tk.StringVar()
            ttk.Entry(row, textvariable=var, width=16, justify="right").pack(side="right", padx=4)

        self.field_vars[name] = (var, kind)

    def _add_rubrique_row(self, key="", label="", url=""):
        row = ttk.Frame(self.rubriques_frame)
        row.pack(fill="x", pady=3)

        key_var = tk.StringVar(value=key)
        label_var = tk.StringVar(value=label)
        url_var = tk.StringVar(value=url)

        ttk.Label(row, text=self.t("rubrique_key")).pack(side="left")
        ttk.Entry(row, textvariable=key_var, width=16).pack(side="left", padx=(2, 8))
        ttk.Label(row, text=self.t("rubrique_label")).pack(side="left")
        ttk.Entry(row, textvariable=label_var, width=16).pack(side="left", padx=(2, 8))
        ttk.Label(row, text=self.t("rubrique_url")).pack(side="left")
        ttk.Entry(row, textvariable=url_var, width=32).pack(side="left", padx=(2, 8), fill="x", expand=True)

        entry = {"frame": row, "key": key_var, "label": label_var, "url": url_var}

        def remove():
            row.destroy()
            self.rubrique_rows.remove(entry)

        ttk.Button(row, text="✕", width=3, command=remove).pack(side="left")

        self.rubrique_rows.append(entry)

    def _clear_rubrique_rows(self):
        for entry in self.rubrique_rows:
            entry["frame"].destroy()
        self.rubrique_rows = []

    def load_settings(self):
        try:
            config = _load_live_config()
        except Exception as e:
            messagebox.showerror(self.t("err_load_failed_title"), self.t("err_load_failed_body", error=e))
            return

        for name, _label_key, _desc_key, kind in SIMPLE_FIELDS:
            var, _kind = self.field_vars[name]
            value = getattr(config, name)
            if kind == "bool":
                var.set(bool(value))
            else:
                var.set(str(value))

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
        updates = self._collect_updates()
        if updates is None:
            return
        try:
            source = CONFIG_PATH.read_text(encoding="utf-8")
            patched = patch_config(source, updates)
            ast.parse(patched)  # sanity check before writing
            CONFIG_PATH.write_text(patched, encoding="utf-8")
        except Exception as e:
            messagebox.showerror(self.t("err_save_failed_title"), self.t("err_save_failed_body", error=e))
            return
        self.log(self.t("log_saved_settings"))
        self.load_settings()
        messagebox.showinfo(self.t("dlg_saved_title"), self.t("dlg_saved_body"))

    def on_reset_defaults(self):
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
        self.log(self.t("log_reset_settings"))
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

    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # -- lifecycle -------------------------------------------------------------
    def on_close(self):
        try:
            prefs = _load_gui_prefs()
            prefs["window"] = {
                "x": self.winfo_x(),
                "y": self.winfo_y(),
                "w": self.winfo_width(),
                "h": self.winfo_height(),
            }
            _save_gui_prefs(prefs)
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
