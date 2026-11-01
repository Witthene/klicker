"""Playback-only mode used by macros compiled to .exe (TinyTask's "Compile")."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QWidget

from . import macro, winapi
from .icon import app_icon

HK_STOP_PAUSE, HK_STOP_SCROLL = 1, 2


class _Bridge(QObject):
    finished = Signal(str)


class PlaybackHost(QWidget):
    """Invisible window that owns the stop hotkeys and a tray icon while the macro plays."""

    def __init__(self, events, speed, loops):
        super().__init__()
        self._events, self._speed, self._loops = events, speed, loops
        self._bridge = _Bridge()
        self._bridge.finished.connect(self._finished)
        self.player = macro.Player(on_finished=self._bridge.finished.emit)
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("Klicker — reproduzindo macro (Pause ou Scroll Lock para parar)")
        self._hwnd = int(self.winId())

    def start(self):
        winapi.register_hotkey(self._hwnd, HK_STOP_PAUSE, winapi.VK_PAUSE, 0)
        winapi.register_hotkey(self._hwnd, HK_STOP_SCROLL, winapi.VK_SCROLL, 0)
        self.tray.show()
        self.tray.showMessage("Klicker","Reproduzindo macro. Pause ou Scroll Lock para parar.",
                              QSystemTrayIcon.Information, 2500)
        self.player.start(self._events, self._speed, self._loops)

    def _finished(self, reason):
        winapi.unregister_hotkey(self._hwnd, HK_STOP_PAUSE)
        winapi.unregister_hotkey(self._hwnd, HK_STOP_SCROLL)
        self.tray.hide()
        QApplication.instance().exit(1 if reason.startswith("error:") else 0)

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = winapi.wt.MSG.from_address(int(message))
            if msg.message == winapi.WM_HOTKEY and msg.wParam in (HK_STOP_PAUSE, HK_STOP_SCROLL):
                self.player.stop()
                return True, 0
        return False, 0


def run(app, payload):
    events, speed, loops = payload
    if not events:
        return 0
    app.setQuitOnLastWindowClosed(False)
    host = PlaybackHost(events, speed, loops)
    host.start()
    return app.exec()
