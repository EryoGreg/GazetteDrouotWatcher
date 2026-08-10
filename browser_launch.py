"""
Opening notification links in a browser the user explicitly chose, instead
of whatever Windows' `https` association happens to point at.

Why this exists at all: a toast's `on_click=<url>` uses protocol
activation, so Windows resolves the link through
`UrlAssociations\\https\\UserChoice` — the real "default browser" setting.
That is the correct default behavior and stays the default here. But a
very common Windows state is that someone uses Chrome/Firefox daily
while never having actually registered it as the default (installing a
browser doesn't do it; you have to click "Set default" in Settings), so
links open in Edge and it reads as the app misbehaving.

Rather than silently overriding the OS setting — which is precisely the
behavior that makes Edge obnoxious — the app lets the user *explicitly*
pick a browser. Only when they do does any of the machinery below come
into play:

    toast on_click = "gazettedrouotlink:https://..."
      -> HKCU-registered protocol handler
      -> our own exe, with --open-url
      -> chosen browser

The indirection is needed because the scheduled `--watch` process that
showed the toast has long since exited by the time anyone clicks it, so
there's no live process of ours to handle the click directly. Cost is
roughly a second of exe startup before the browser appears, which is
why it's strictly opt-in and never on the default path.
"""

import subprocess
import winreg
from urllib.parse import urlparse

# Deliberately specific/unlikely to collide. Registered under HKCU only
# (no admin needed) and removed again on Uninstall / self-destruct.
LINK_PROTOCOL = "gazettedrouotlink"

# Listed by Windows itself but not a real choice on any current machine —
# it just bounces to Edge, and showing it would only confuse someone
# picking from a list.
_EXCLUDED_BROWSER_KEYS = {"IEXPLORE.EXE"}


def detect_browsers() -> list[tuple[str, str]]:
    """[(display name, exe path)] for every browser Windows knows about,
    read from its own StartMenuInternet registry (the same source the
    Settings > Default apps list is built from). Deduplicated by exe, since
    a browser installed for both the machine and the user appears twice."""
    found: dict[str, str] = {}
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\Clients\StartMenuInternet") as root:
                index = 0
                while True:
                    try:
                        key_name = winreg.EnumKey(root, index)
                    except OSError:
                        break
                    index += 1
                    if key_name.upper() in _EXCLUDED_BROWSER_KEYS:
                        continue
                    try:
                        with winreg.OpenKey(root, key_name + r"\shell\open\command") as cmd_key:
                            exe = winreg.QueryValueEx(cmd_key, "")[0].strip().strip('"')
                    except OSError:
                        continue
                    try:
                        with winreg.OpenKey(root, key_name) as name_key:
                            display = winreg.QueryValueEx(name_key, "")[0]
                    except OSError:
                        display = key_name
                    found.setdefault(exe, display)
        except OSError:
            continue
    return sorted(((display, exe) for exe, display in found.items()), key=lambda pair: pair[0].lower())


def register_link_protocol(command_prefix: str):
    """Points LINK_PROTOCOL at `<command_prefix> --open-url "%1"`, under HKCU
    so no administrator rights are involved.

    command_prefix is already-quoted and may be more than just an exe (in
    source/dev mode it's pythonw plus the script path), which is why it's
    passed in whole rather than assembled here."""
    base = rf"Software\Classes\{LINK_PROTOCOL}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Gazette Drouot Watcher link")
        # Presence of this (empty) value is what marks a key as a URL
        # protocol handler as far as Windows is concerned.
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'{command_prefix} --open-url "%1"')


def unregister_link_protocol():
    """No-op if it was never registered. Called on Uninstall and on the
    self-destruct path, so opting out (or removing the app) doesn't leave
    a dangling handler pointing at an exe that no longer exists."""
    for sub in (rf"Software\Classes\{LINK_PROTOCOL}\shell\open\command",
                rf"Software\Classes\{LINK_PROTOCOL}\shell\open",
                rf"Software\Classes\{LINK_PROTOCOL}\shell",
                rf"Software\Classes\{LINK_PROTOCOL}"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except OSError:
            pass


def strip_link_protocol(raw: str) -> str:
    """"gazettedrouotlink:https://x" -> "https://x". Windows hands the whole
    URI to the handler, prefix included."""
    prefix = LINK_PROTOCOL + ":"
    if raw.lower().startswith(prefix):
        return raw[len(prefix):]
    return raw


def open_url(raw_uri: str, browser_exe: str | None) -> bool:
    """Opens `raw_uri` in `browser_exe`, or in the system default browser if
    that's empty/missing. Returns whether anything was launched.

    Only ever opens http/https. This function is reachable by anything on
    the machine that can invoke a URL protocol, so it must not become a
    way to launch arbitrary schemes (file:, or a local executable path)
    through us."""
    url = strip_link_protocol(raw_uri).strip()
    if urlparse(url).scheme.lower() not in ("http", "https"):
        return False

    if browser_exe:
        try:
            # Passed as a separate argv entry, never through a shell, so a
            # URL containing shell metacharacters can't do anything.
            subprocess.Popen([browser_exe, url], close_fds=True)
            return True
        except OSError:
            # Chosen browser was uninstalled/moved since it was picked --
            # fall through to the system default rather than doing nothing.
            pass

    import webbrowser

    return webbrowser.open(url)
