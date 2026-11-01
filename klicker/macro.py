"""TinyTask-style macro recorder and player.

A macro is a list of events ``[t_ms, kind, ...]`` with ``t_ms`` measured from
the start of the recording:

    [t, "move", x, y]
    [t, "down" | "up", button, x, y]        button: left/right/middle/x1/x2
    [t, "wheel" | "hwheel", delta, x, y]
    [t, "kdown" | "kup", vk, scan, extended]

Coordinates are physical screen pixels, the same space SetCursorPos uses.
"""

import ctypes
import json
import shutil
import struct
import sys
import threading
import time
import zlib
from pathlib import Path

from .engine import wait_until

FORMAT = "klicker-macro"
LEGACY_FORMATS = {"glass-clicker-macro"}  # files saved before the rename still open
FILE_SUFFIX = ".kmacro"
PAYLOAD_MAGIC = b"KMACRO01"
_TRAILER = struct.Struct("<8sQ")  # magic + payload length, appended to compiled .exe files
MIN_MOVE_GAP_MS = 8               # coalesce mouse moves closer than this


# ----------------------------------------------------------------- recording

class Recorder:
    """Captures real (non-injected) mouse and keyboard input with low-level hooks."""

    def __init__(self, own_hwnd=0, record_moves=True, record_keys=True, backend=None,
                 include_injected=False):
        if backend is None:
            from . import winapi as backend
        self._w = backend
        self._own_hwnd = own_hwnd
        # Synthetic input (our own playback, other macro tools) is skipped unless asked for.
        self._mouse_skip = 0 if include_injected else backend.LLMHF_INJECTED
        self._key_skip = 0 if include_injected else backend.LLKHF_INJECTED
        self._record_moves = record_moves
        self._record_keys = record_keys
        self._events = []
        self._thread = None
        self._thread_id = 0
        self._ready = threading.Event()
        self._t0 = 0.0
        self.error = None

    @property
    def recording(self):
        return self._thread is not None and self._thread.is_alive()

    def elapsed(self):
        return time.perf_counter() - self._t0 if self._t0 else 0.0

    def event_count(self):
        return len(self._events)

    def start(self):
        self._events = []
        self._t0 = time.perf_counter()
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="macro-recorder", daemon=True)
        self._thread.start()
        self._ready.wait(2.0)
        if self.error:
            raise OSError(self.error)

    def stop(self, drop_keys=()):
        """Stop and return the cleaned-up event list."""
        if self._thread is not None:
            self._w.user32.PostThreadMessageW(self._thread_id, self._w.WM_QUIT, 0, 0)
            self._thread.join(2.0)
        return clean(self._events, drop_keys)

    def _run(self):
        w = self._w
        self._thread_id = w.kernel32.GetCurrentThreadId()
        mouse_proc = w.HOOKPROC(self._on_mouse)  # keep references alive for the hook's lifetime
        key_proc = w.HOOKPROC(self._on_key)
        module = w.kernel32.GetModuleHandleW(None)
        mouse_hook = w.user32.SetWindowsHookExW(w.WH_MOUSE_LL, mouse_proc, module, 0)
        key_hook = w.user32.SetWindowsHookExW(w.WH_KEYBOARD_LL, key_proc, module, 0) if self._record_keys else None
        if not mouse_hook or (self._record_keys and not key_hook):
            self.error = f"Não foi possível instalar o gancho de entrada ({ctypes.get_last_error()})"
        self._ready.set()
        try:
            msg = w.wt.MSG()
            while not self.error and w.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                pass
        finally:
            if mouse_hook:
                w.user32.UnhookWindowsHookEx(mouse_hook)
            if key_hook:
                w.user32.UnhookWindowsHookEx(key_hook)

    def _now(self):
        return round((time.perf_counter() - self._t0) * 1000)

    def _on_mouse(self, code, wparam, lparam):
        try:
            if code == 0:
                info = self._w.MSLLHOOKSTRUCT.from_address(lparam)
                if not info.flags & self._mouse_skip:
                    self._mouse(wparam, info)
        except Exception:
            pass  # never let an exception swallow the user's input
        return self._w.user32.CallNextHookEx(None, code, wparam, lparam)

    def _mouse(self, message, info):
        w = self._w
        t = self._now()
        x, y = info.pt.x, info.pt.y
        if message == w.WM_MOUSEMOVE:
            if not self._record_moves:
                return
            last = self._events[-1] if self._events else None
            if last is not None and last[1] == "move" and t - last[0] < MIN_MOVE_GAP_MS:
                last[2], last[3] = x, y
            else:
                self._events.append([t, "move", x, y])
            return
        # Clicks on Klicker itself (e.g. the record button) are UI, not macro.
        if self._own_hwnd and w.root_window_at(x, y) == self._own_hwnd:
            return
        if message in (w.WM_MOUSEWHEEL, w.WM_MOUSEHWHEEL):
            delta = ctypes.c_short(info.mouseData >> 16).value
            kind = "wheel" if message == w.WM_MOUSEWHEEL else "hwheel"
            self._events.append([t, kind, delta, x, y])
        elif message in w.MOUSE_BUTTON_MESSAGES:
            kind, button = w.MOUSE_BUTTON_MESSAGES[message]
            if button == "x":
                button = "x1" if (info.mouseData >> 16) == 1 else "x2"
            self._events.append([t, kind, button, x, y])

    def _on_key(self, code, wparam, lparam):
        try:
            if code == 0:
                w = self._w
                info = w.KBDLLHOOKSTRUCT.from_address(lparam)
                own_focus = self._own_hwnd and w.user32.GetForegroundWindow() == self._own_hwnd
                if not info.flags & self._key_skip and not own_focus:
                    up = wparam in (w.WM_KEYUP, w.WM_SYSKEYUP)
                    self._events.append([self._now(), "kup" if up else "kdown", info.vkCode,
                                         info.scanCode, bool(info.flags & w.LLKHF_EXTENDED)])
        except Exception:
            pass
        return self._w.user32.CallNextHookEx(None, code, wparam, lparam)


def _input_id(event):
    kind = event[1]
    if kind in ("kdown", "kup"):
        return ("k", event[2])
    if kind in ("down", "up"):
        return ("m", event[2])
    return None


def clean(events, drop_keys=()):
    """Remove the noise around a recording.

    * releases whose press happened before recording started (the start hotkey),
    * presses never released before it stopped (the stop hotkey),
    * any key in ``drop_keys`` (e.g. Pause / Scroll Lock, which stop playback),
    then shift time so the first event happens at t=0.
    """
    events = [list(e) for e in events if not (e[1] in ("kdown", "kup") and e[2] in drop_keys)]
    keep = [True] * len(events)
    open_presses = {}  # input -> indexes of its presses since the last release (auto-repeat adds more)
    for i, e in enumerate(events):
        ident = _input_id(e)
        if ident is None:
            continue
        if e[1] in ("down", "kdown"):
            open_presses.setdefault(ident, []).append(i)
        elif ident in open_presses:
            del open_presses[ident]
        else:
            keep[i] = False
    for indexes in open_presses.values():
        for i in indexes:
            keep[i] = False
    result = [e for e, k in zip(events, keep) if k]
    if result:
        t0 = result[0][0]
        for e in result:
            e[0] -= t0
    return result


def duration_ms(events):
    return events[-1][0] if events else 0


# ------------------------------------------------------------------- playback

class Player:
    def __init__(self, backend=None, on_finished=None):
        if backend is None:
            from . import winapi as backend
        self._w = backend
        self._on_finished = on_finished or (lambda reason: None)
        self._stop = threading.Event()
        self._thread = None
        self.loop = 0
        self.loops = 1
        self._loop_started = 0.0
        self.speed = 1.0

    @property
    def playing(self):
        return self._thread is not None and self._thread.is_alive()

    def loop_elapsed(self):
        return (time.perf_counter() - self._loop_started) * self.speed if self._loop_started else 0.0

    def start(self, events, speed=1.0, loops=1):
        """``loops=0`` plays continuously until stopped."""
        if self.playing or not events:
            return
        self._stop.clear()
        self.speed = max(0.01, float(speed))
        self.loops = loops
        self.loop = 0
        self._thread = threading.Thread(target=self._run, args=(list(events),), name="macro-player",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self, events):
        reason = "done"
        held = {}
        self._w.begin_precise_timing()
        try:
            while self.loops == 0 or self.loop < self.loops:
                self.loop += 1
                self._loop_started = time.perf_counter()
                for e in events:
                    if wait_until(self._stop, self._loop_started + e[0] / 1000 / self.speed):
                        reason = "stopped"
                        return
                    self._w.play_event(e)
                    ident = _input_id(e)
                    if ident is not None:
                        if e[1] in ("down", "kdown"):
                            held[ident] = e
                        else:
                            held.pop(ident, None)
        except Exception as exc:
            reason = f"error:{exc}"
        finally:
            # Never leave a key or button stuck down when playback is interrupted.
            for e in held.values():
                try:
                    release = list(e)
                    release[1] = "up" if e[1] == "down" else "kup"
                    self._w.play_event(release)
                except Exception:
                    pass
            self._w.end_precise_timing()
            self._loop_started = 0.0
            self._on_finished(reason)


# ---------------------------------------------------------------------- files

def to_document(events, speed=1.0, loops=1):
    return {"format": FORMAT, "version": 1, "speed": speed, "loops": loops, "events": events}


def from_document(doc):
    if (not isinstance(doc, dict) or (doc.get("format") != FORMAT and doc.get("format") not in LEGACY_FORMATS)
            or not isinstance(doc.get("events"), list)):
        raise ValueError("Este arquivo não parece ser uma macro do Klicker.")
    events = [list(e) for e in doc["events"] if isinstance(e, list) and len(e) >= 4]
    return events, float(doc.get("speed", 1.0)), int(doc.get("loops", 1))


def save(path, events, speed=1.0, loops=1):
    Path(path).write_text(json.dumps(to_document(events, speed, loops), separators=(",", ":")),
                          encoding="utf-8")


def load(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Não foi possível ler “{Path(path).name}”: {exc}") from exc
    return from_document(doc)


def _exe_without_payload(data):
    if len(data) >= _TRAILER.size:
        magic, length = _TRAILER.unpack(data[-_TRAILER.size:])
        if magic == PAYLOAD_MAGIC and length + _TRAILER.size <= len(data):
            return data[:-(_TRAILER.size + length)]
    return data


def can_compile():
    return getattr(sys, "frozen", False)


def compile_exe(target, events, speed=1.0, loops=1, source=None):
    """Like TinyTask's "Compile": a standalone .exe that just plays this macro.

    The running Klicker.exe is copied and the macro is appended after it;
    on start-up the copy finds the payload and plays it instead of opening the UI.
    """
    source = Path(source or sys.executable)
    payload = zlib.compress(json.dumps(to_document(events, speed, loops)).encode("utf-8"), 9)
    tmp = Path(str(target) + ".tmp")
    with open(source, "rb") as src, open(tmp, "wb") as dst:
        shutil.copyfileobj(src, dst)
    data = tmp.read_bytes()
    stripped = _exe_without_payload(data)
    with open(tmp, "r+b") as f:
        f.truncate(len(stripped))
        f.seek(0, 2)
        f.write(payload)
        f.write(_TRAILER.pack(PAYLOAD_MAGIC, len(payload)))
    tmp.replace(target)


def read_embedded(path=None):
    """Return ``(events, speed, loops)`` if this executable carries a macro."""
    if path is None:
        if not getattr(sys, "frozen", False):
            return None
        path = sys.executable
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size < _TRAILER.size:
                return None
            f.seek(size - _TRAILER.size)
            magic, length = _TRAILER.unpack(f.read(_TRAILER.size))
            if magic != PAYLOAD_MAGIC or length > size - _TRAILER.size:
                return None
            f.seek(size - _TRAILER.size - length)
            doc = json.loads(zlib.decompress(f.read(length)))
        return from_document(doc)
    except (OSError, ValueError, zlib.error):
        return None
