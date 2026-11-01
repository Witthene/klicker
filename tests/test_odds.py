import math
import random
import unittest

from klicker import odds
from klicker.odds import DropConfig


def simulate_drops(cfg, runs, trials, seed=1):
    rng = random.Random(seed)
    total = 0
    for _ in range(trials):
        counter = cfg.pity_progress
        for _ in range(runs):
            if (cfg.has_pity and counter == cfg.pity - 1) or rng.random() < cfg.p:
                total += 1
                counter = 0
            else:
                counter += 1
    return total / trials


class OddsTests(unittest.TestCase):
    def test_no_pity_mean_is_one_over_p(self):
        report = odds.analyze(DropConfig(chance=0.01, run_seconds=30))
        self.assertAlmostEqual(report.mean_runs, 100)
        self.assertIsNone(report.worst_runs)
        # Median of a geometric: ceil(ln 0.5 / ln 0.99) = 69.
        self.assertEqual(report.quantile_runs[0.5], 69)
        self.assertEqual(report.quantile_runs[0.9], 230)

    def test_pity_caps_mean_and_worst_case(self):
        cfg = DropConfig(chance=0.01, run_seconds=10, pity=50)
        report = odds.analyze(cfg)
        self.assertEqual(report.worst_runs, 50)
        self.assertAlmostEqual(report.mean_runs, (1 - 0.99 ** 50) / 0.01)
        self.assertEqual(report.quantile_runs[0.99], 50)

    def test_pity_progress_shortens_first_cycle(self):
        cfg = DropConfig(chance=0.01, run_seconds=10, pity=50, pity_progress=45)
        report = odds.analyze(cfg)
        self.assertEqual(report.worst_runs, 5)
        self.assertEqual(odds.chance_at_least_one(cfg, 5), 1.0)
        self.assertLess(odds.chance_at_least_one(cfg, 4), 0.05)

    def test_luck_multiplies_chance(self):
        self.assertAlmostEqual(DropConfig(chance=0.01, run_seconds=1, luck=2).p, 0.02)
        self.assertEqual(DropConfig(chance=0.8, run_seconds=1, luck=2).p, 1.0)

    def test_expected_drops_matches_simulation(self):
        cfg = DropConfig(chance=0.05, run_seconds=1, pity=10, pity_progress=3)
        exact = odds.expected_drops(cfg, 60)
        sim = simulate_drops(cfg, 60, 20_000)
        self.assertAlmostEqual(exact, sim, delta=0.05)

    def test_expected_drops_without_pity(self):
        cfg = DropConfig(chance=0.02, run_seconds=1)
        self.assertAlmostEqual(odds.expected_drops(cfg, 500), 10)

    def test_goal_and_farm(self):
        cfg = DropConfig(chance=0.1, run_seconds=60, pity=20, items_per_drop=2)
        report = odds.analyze(cfg, goal_items=5, farm_seconds=3600)
        self.assertEqual(report.goal_drops, 3)
        self.assertEqual(report.goal_worst_runs, 60)
        self.assertEqual(report.farm_runs, 60)
        self.assertAlmostEqual(report.farm_expected_items, 2 * odds.expected_drops(cfg, 60))
        self.assertLessEqual(report.goal_quantile_runs[0.99], 60)

    def test_formatting(self):
        self.assertEqual(odds.format_time(45), "45s")
        self.assertEqual(odds.format_time(6000), "1h 40min")
        self.assertEqual(odds.format_time(90061), "1d 1h")
        self.assertEqual(odds.format_time(math.inf), "∞")
        self.assertEqual(odds.format_number(12345.6, 1), "12.345,6")
        self.assertEqual(odds.format_chance(0.005), "0,5% (1 em 200)")
        self.assertEqual(odds.format_percent(0.6321), "63,2%")


if __name__ == "__main__":
    unittest.main()
