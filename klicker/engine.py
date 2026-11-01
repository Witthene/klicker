"""The click loop. Runs on a worker thread and knows nothing about the UI."""

import random
import threading
import time
from dataclasses import dataclass, field


@dataclass
class ClickConfig:
    interval_ms: int = 100
    jitter_ms: int = 0
    button: str = "left"            # left | middle | right
    clicks: int = 1                 # 1 = single, 2 = double, 3 = triple
    repeat_mode: str = "infinite"   # infinite | count | duration
    repeat_count: int = 100
    duration_s: float = 60
    position_mode: str = "cursor"   # cursor | points
    points: list = field(default_factory=list)
    restore_cursor: bool = True
    protect_hwnd: int = 0           # never click on this top-level window


class ClickEngine:
    def __init__(self, backend=None, on_finished=None):
        if backend is None:
            from . import winapi as backend
        self._backend = backend
        self._on_finished = on_finished or (lambda reason: None)
        self._stop = threading.Event()
        self._thread = None
        self.clicks = 0
        self.started_at = 0.0
        self.ended_at = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, cfg):
        if self.running:
            return
        self._stop.clear()
        self.clicks = 0
        self.started_at = time.perf_counter()
        self.ended_at = None
        self._thread = threading.Thread(target=self._run, args=(cfg,), name="clicker", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    def elapsed(self):
        if not self.started_at:
            return 0.0
        return (self.ended_at or time.perf_counter()) - self.started_at

    def _run(self, cfg):
        reason = "stopped"
        self._backend.begin_precise_timing()
        try:
            reason = self._loop(cfg)
        except Exception as exc:  # surface any Win32 failure to the UI instead of dying silently
            reason = f"error:{exc}"
        finally:
            self._backend.end_precise_timing()
            self.ended_at = time.perf_counter()
            self._on_finished(reason)

    def _loop(self, cfg):
        start = self.started_at
        deadline = start + cfg.duration_s if cfg.repeat_mode == "duration" else None
        next_at = start
        index = 0
        while True:
            if self._stop.is_set():
                return "stopped"
            if cfg.repeat_mode == "count" and self.clicks >= cfg.repeat_count:
                return "done"
            if deadline is not None and time.perf_counter() >= deadline:
                return "done"

            self._click_once(cfg, index)
            index += 1

            jitter = random.randint(-cfg.jitter_ms, cfg.jitter_ms) if cfg.jitter_ms else 0
            next_at += max(1, cfg.interval_ms + jitter) / 1000
            now = time.perf_counter()
            if next_at < now:  # we fell behind (slow target app): don't burst to catch up
                next_at = now
            target = next_at if deadline is None else min(next_at, deadline)
            if self._wait_until(target):
                return "stopped"

    def _click_once(self, cfg, index):
        b = self._backend
        saved = None
        if cfg.position_mode == "points" and cfg.points:
            if cfg.restore_cursor:
                saved = b.get_cursor_pos()
            x, y = cfg.points[index % len(cfg.points)]
            b.set_cursor_pos(x, y)
        x, y = b.get_cursor_pos()
        if not (cfg.protect_hwnd and b.root_window_at(x, y) == cfg.protect_hwnd):
            b.send_click(cfg.button, cfg.clicks)
            self.clicks += 1
        if saved is not None:
            b.set_cursor_pos(*saved)

    def _wait_until(self, target):
        return wait_until(self._stop, target)


def wait_until(stop, target):
    """Sleep until ``target`` (perf_counter time). Returns True if ``stop`` was set."""
    while True:
        remaining = target - time.perf_counter()
        if remaining <= 0:
            return stop.is_set()
        if remaining > 0.002:
            if stop.wait(min(remaining - 0.0015, 0.05)):
                return True
        else:
            time.sleep(0)  # spin out the last couple of milliseconds for accuracy
            if stop.is_set():
                return True
