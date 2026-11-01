import os
import tempfile
import time
import unittest
from pathlib import Path

from klicker import macro


class FakeBackend:
    def __init__(self):
        self.played = []

    def play_event(self, e):
        self.played.append((time.perf_counter(), list(e)))

    def begin_precise_timing(self):
        pass

    def end_precise_timing(self):
        pass


CTRL, R = 0xA2, 0x52


class CleanTests(unittest.TestCase):
    def test_drops_hotkey_noise_and_rebases_time(self):
        raw = [
            [100, "kup", R, 19, False],           # release of the start hotkey
            [120, "kup", CTRL, 29, False],
            [300, "move", 10, 10],
            [400, "down", "left", 10, 10],
            [450, "up", "left", 10, 10],
            [500, "kdown", 0x41, 30, False],
            [520, "kdown", 0x41, 30, False],      # auto-repeat is kept
            [560, "kup", 0x41, 30, False],
            [900, "kdown", CTRL, 29, False],      # stop hotkey, never released
            [910, "kdown", R, 19, False],
        ]
        events = macro.clean(raw)
        self.assertEqual([e[1] for e in events], ["move", "down", "up", "kdown", "kdown", "kup"])
        self.assertEqual(events[0][0], 0)
        self.assertEqual(events[-1][0], 260)

    def test_drop_keys(self):
        raw = [[0, "kdown", 0x13, 69, False], [5, "kup", 0x13, 69, False], [9, "move", 1, 1]]
        self.assertEqual(macro.clean(raw, drop_keys={0x13}), [[0, "move", 1, 1]])


class PlayerTests(unittest.TestCase):
    def play(self, events, **kw):
        backend = FakeBackend()
        reasons = []
        player = macro.Player(backend, on_finished=reasons.append)
        player.start(events, **kw)
        player.join(5)
        return backend, reasons

    def test_loops_and_timing(self):
        events = [[0, "move", 1, 1], [60, "move", 2, 2]]
        backend, reasons = self.play(events, loops=3)
        self.assertEqual(reasons, ["done"])
        self.assertEqual(len(backend.played), 6)
        gap = backend.played[1][0] - backend.played[0][0]
        self.assertGreaterEqual(gap, 0.055)

    def test_speed_multiplier(self):
        events = [[0, "move", 1, 1], [1000, "move", 2, 2]]
        start = time.perf_counter()
        self.play(events, speed=100)
        self.assertLess(time.perf_counter() - start, 0.5)

    def test_stop_releases_held_input(self):
        events = [[0, "kdown", 0x41, 30, False], [0, "down", "left", 5, 5], [5000, "kup", 0x41, 30, False]]
        backend = FakeBackend()
        reasons = []
        player = macro.Player(backend, on_finished=reasons.append)
        player.start(events)
        time.sleep(0.1)
        player.stop()
        player.join(2)
        self.assertEqual(reasons, ["stopped"])
        kinds = sorted(e[1] for _, e in backend.played[2:])
        self.assertEqual(kinds, ["kup", "up"])


class FileTests(unittest.TestCase):
    def test_save_load_and_compile_roundtrip(self):
        events = [[0, "move", 1, 2], [10, "down", "left", 1, 2], [20, "up", "left", 1, 2]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.kmacro"
            macro.save(path, events, speed=2.0, loops=0)
            self.assertEqual(macro.load(path), (events, 2.0, 0))

            fake_exe = Path(tmp) / "host.exe"
            fake_exe.write_bytes(os.urandom(4096))
            out = Path(tmp) / "macro.exe"
            macro.compile_exe(out, events, speed=3.0, loops=5, source=fake_exe)
            self.assertEqual(macro.read_embedded(out), (events, 3.0, 5))
            self.assertEqual(out.read_bytes()[:4096], fake_exe.read_bytes())

            # Compiling from an already-compiled exe replaces the old payload.
            again = Path(tmp) / "again.exe"
            macro.compile_exe(again, events[:1], source=out)
            self.assertEqual(macro.read_embedded(again)[0], events[:1])
            self.assertLess(again.stat().st_size, out.stat().st_size + 64)

    def test_plain_exe_has_no_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "x.exe"
            exe.write_bytes(os.urandom(1000))
            self.assertIsNone(macro.read_embedded(exe))


if __name__ == "__main__":
    unittest.main()
