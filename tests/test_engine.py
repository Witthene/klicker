import time
import unittest

from klicker.engine import ClickConfig, ClickEngine


class FakeBackend:
    """Records what the engine would have done instead of touching the real mouse."""

    def __init__(self, window_at=0):
        self.cursor = (500, 500)
        self.clicks = []
        self.window_at = window_at

    def send_click(self, button, count):
        self.clicks.append((button, count, self.cursor))

    def get_cursor_pos(self):
        return self.cursor

    def set_cursor_pos(self, x, y):
        self.cursor = (x, y)

    def root_window_at(self, x, y):
        return self.window_at

    def begin_precise_timing(self):
        pass

    def end_precise_timing(self):
        pass


def run(cfg, backend, timeout=5.0):
    reasons = []
    engine = ClickEngine(backend, on_finished=reasons.append)
    engine.start(cfg)
    engine.join(timeout)
    return engine, reasons


class EngineTests(unittest.TestCase):
    def test_count_mode_stops_after_n_clicks(self):
        backend = FakeBackend()
        engine, reasons = run(ClickConfig(interval_ms=1, repeat_mode="count", repeat_count=25), backend)
        self.assertEqual(reasons, ["done"])
        self.assertEqual(engine.clicks, 25)
        self.assertEqual(len(backend.clicks), 25)

    def test_button_and_click_type_are_forwarded(self):
        backend = FakeBackend()
        run(ClickConfig(interval_ms=1, button="right", clicks=2, repeat_mode="count", repeat_count=1), backend)
        self.assertEqual(backend.clicks, [("right", 2, (500, 500))])

    def test_points_cycle_and_cursor_is_restored(self):
        backend = FakeBackend()
        cfg = ClickConfig(interval_ms=1, repeat_mode="count", repeat_count=5,
                          position_mode="points", points=[(1, 1), (2, 2)], restore_cursor=True)
        run(cfg, backend)
        self.assertEqual([c[2] for c in backend.clicks], [(1, 1), (2, 2), (1, 1), (2, 2), (1, 1)])
        self.assertEqual(backend.cursor, (500, 500))

    def test_never_clicks_on_protected_window(self):
        backend = FakeBackend(window_at=42)
        cfg = ClickConfig(interval_ms=1, repeat_mode="duration", duration_s=0.05, protect_hwnd=42)
        engine, reasons = run(cfg, backend)
        self.assertEqual(reasons, ["done"])
        self.assertEqual(backend.clicks, [])

    def test_stop_ends_infinite_run(self):
        engine = ClickEngine(FakeBackend())
        engine.start(ClickConfig(interval_ms=5))
        time.sleep(0.1)
        self.assertTrue(engine.running)
        engine.stop()
        engine.join(1.0)
        self.assertFalse(engine.running)

    def test_interval_is_respected(self):
        backend = FakeBackend()
        engine, _ = run(ClickConfig(interval_ms=20, repeat_mode="count", repeat_count=11), backend)
        # 10 gaps of 20 ms; allow generous slack for a busy CI machine.
        self.assertGreaterEqual(engine.elapsed(), 0.19)
        self.assertLess(engine.elapsed(), 0.6)


if __name__ == "__main__":
    unittest.main()
