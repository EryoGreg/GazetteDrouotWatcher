"""
Optional Windows system tray icon -- only shown when the user opts in via
the "Show tray icon" checkbox in the control panel (off by default).

Runs its own native Win32 message loop (via pywin32's win32gui, already a
dependency for task_scheduler.py) on a background thread, since Tkinter's
mainloop can't share message-pump duties with one running in the same
thread. on_open/on_exit fire from that background thread -- callers that
need to touch a Tkinter window from them must marshal back to the main
thread themselves (e.g. root.after(0, ...)), same as any other
cross-thread Tkinter call.
"""

import sys
import threading

import win32api
import win32con
import win32gui

_WM_TRAYICON = win32con.WM_USER + 20
_CLASS_NAME = "GazetteDrouotWatcherTrayIcon"


class TrayIcon:
    def __init__(self, icon_path: str | None, tooltip: str, on_open, on_exit):
        """icon_path: a loose .ico file, or None to extract the icon
        embedded in the currently running executable's own resources
        instead (PyInstaller bakes icon.ico into the frozen exe via
        --icon, but doesn't also ship it as a separate file next to it —
        see main.py's ICON_PATH)."""
        self._icon_path = icon_path
        self._tooltip = tooltip
        self._on_open = on_open
        self._on_exit = on_exit
        self._hwnd = None
        self._thread = None

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Best-effort -- posts the window a close request and lets its own
        message loop tear the icon down and exit on its own thread, rather
        than trying to synchronize with it from here."""
        if self._hwnd is not None:
            win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
        self._hwnd = None
        self._thread = None

    def _run(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = _CLASS_NAME
        try:
            class_atom = win32gui.RegisterClass(wc)
        except win32gui.error:
            # Already registered by an earlier instance in this same
            # process (e.g. the checkbox was toggled off then on again) --
            # the existing registration works just as well.
            class_atom = _CLASS_NAME

        self._hwnd = win32gui.CreateWindow(
            class_atom, _CLASS_NAME, 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
        )
        hicon = self._load_icon()
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, (self._hwnd, 0, flags, _WM_TRAYICON, hicon, self._tooltip))
        win32gui.PumpMessages()

    def _load_icon(self):
        if self._icon_path:
            return win32gui.LoadImage(
                0, self._icon_path, win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            )
        large, small = win32gui.ExtractIconEx(sys.executable, 0, 1)
        if small:
            for h in large:
                win32gui.DestroyIcon(h)
            return small[0]
        if large:
            return large[0]
        # Last resort -- Windows' own generic application icon, so the
        # tray icon still shows *something* rather than nothing at all.
        return win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == _WM_TRAYICON:
            if lparam in (win32con.WM_LBUTTONDBLCLK, win32con.WM_LBUTTONUP):
                self._on_open()
            elif lparam == win32con.WM_RBUTTONUP:
                self._show_menu(hwnd)
            return 0
        if msg == win32con.WM_DESTROY:
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0))
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _show_menu(self, hwnd):
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Open")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "Exit")
        # A popup menu needs the window in the foreground first, or it can
        # fail to close itself on an outside click (a documented Win32
        # quirk, not specific to this app).
        win32gui.SetForegroundWindow(hwnd)
        pos = win32gui.GetCursorPos()
        cmd = win32gui.TrackPopupMenu(
            menu, win32con.TPM_LEFTALIGN | win32con.TPM_RETURNCMD, pos[0], pos[1], 0, hwnd, None
        )
        win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)
        if cmd == 1:
            self._on_open()
        elif cmd == 2:
            self._on_exit()
