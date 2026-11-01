"""Drop-chance math for grinding games (Roblox and the like).

A *run* is one attempt: a stage, a boss kill, an egg, a chest. Every run drops
the item with probability ``chance``. With pity, the ``pity``-th run in a row
without the item always drops it, and the counter resets on every drop (the
usual gacha rule). ``pity_progress`` is how many runs you already did since
your last drop, so the first drop can arrive sooner than a fresh cycle.
"""

import math
from dataclasses import dataclass

MAX_PITY = 100_000
EXACT_RUNS_LIMIT = 200_000  # above this, expected drops use the renewal approximation
Z = {0.5: 0.0, 0.9: 1.2816, 0.99: 2.3263, 0.999: 3.0902}


@dataclass
class DropConfig:
    chance: float               # per-run probability, 0 < chance <= 1
    run_seconds: float          # how long one run takes
    pity: int = 0               # 0 = no pity
    pity_progress: int = 0      # runs already done without a drop
    items_per_drop: int = 1
    luck: float = 1.0           # luck multiplier (2x luck potions etc.)

    @property
    def p(self):
        return min(1.0, max(0.0, self.chance * self.luck))

    @property
    def has_pity(self):
        return self.pity > 0

    @property
    def first_cap(self):
        """Runs until the first drop is guaranteed, or None without pity."""
        if not self.has_pity:
            return None
        return max(1, self.pity - min(self.pity_progress, self.pity - 1))


@dataclass
class DropReport:
    p: float
    mean_runs: float            # average runs for the first drop
    quantile_runs: dict         # {0.5: runs, 0.9: runs, 0.99: runs, 0.999: runs} for the first drop
    worst_runs: int | None      # guaranteed by pity, None if no guarantee
    cycle_runs: float           # average runs between drops once the counter is reset
    goal_items: int
    goal_drops: int
    goal_mean_runs: float
    goal_quantile_runs: dict    # same keys as quantile_runs, for the whole goal
    goal_worst_runs: int | None
    farm_runs: int
    farm_expected_items: float
    farm_chance_any: float      # chance of at least one drop while farming
    run_seconds: float

    def seconds(self, runs):
        return math.inf if runs is None or runs == math.inf else runs * self.run_seconds


def _log_r(p):
    return math.log1p(-p) if p < 1 else -math.inf


def runs_for_quantile(p, q, cap=None):
    """Smallest n such that P(drop within n runs) >= q."""
    if p <= 0:
        return cap if cap is not None else math.inf
    if p >= 1 or q <= 0:
        return 1
    if q >= 1:
        return cap if cap is not None else math.inf
    n = max(1, math.ceil(math.log1p(-q) / _log_r(p) - 1e-9))
    return min(n, cap) if cap is not None else n


def cycle_moments(p, cap=None):
    """Mean and second moment of the runs needed for one drop, X = min(Geometric(p), cap)."""
    if p <= 0:
        return (float(cap), float(cap) ** 2) if cap is not None else (math.inf, math.inf)
    if cap is None:
        return 1 / p, (2 - p) / (p * p)
    # E[X] = sum P(X >= n), E[X^2] = sum (2n - 1) P(X >= n), for n = 1..cap.
    r = 1 - p
    survive = 1.0
    mean = second = 0.0
    for n in range(1, cap + 1):
        mean += survive
        second += (2 * n - 1) * survive
        survive *= r
        if survive < 1e-300:
            break
    return mean, second


def chance_at_least_one(cfg, runs):
    if runs <= 0:
        return 0.0
    cap = cfg.first_cap
    if cap is not None and runs >= cap:
        return 1.0
    p = cfg.p
    if p >= 1:
        return 1.0
    return -math.expm1(runs * _log_r(p))


def expected_drops(cfg, runs):
    """Expected number of drops in ``runs`` runs, pity resets included."""
    p = cfg.p
    if runs <= 0:
        return 0.0
    if not cfg.has_pity or p >= 1:
        return runs * p
    if runs > EXACT_RUNS_LIMIT:
        first, _ = cycle_moments(p, cfg.first_cap)
        cycle, _ = cycle_moments(p, cfg.pity)
        return 1 + (runs - first) / cycle if runs >= first else runs / first
    # a[i] = P(drop on run i). The pity run happens when the counter sits at pity - 1:
    # either the last drop was exactly `pity` runs ago with only misses since, or no drop
    # yet and the starting progress has just climbed to the limit.
    pity = cfg.pity
    r = 1 - p
    r_gap = r ** (pity - 1)
    first_guaranteed = cfg.first_cap
    a = [0.0] * (runs + 1)
    total = 0.0
    for i in range(1, runs + 1):
        g = a[i - pity] * r_gap if i > pity else 0.0
        if i == first_guaranteed:
            g += r ** (i - 1)
        a[i] = p + (1 - p) * g
        total += a[i]
    return total


def analyze(cfg, goal_items=1, farm_seconds=0.0):
    p = cfg.p
    first_cap = cfg.first_cap
    first_mean, first_second = cycle_moments(p, first_cap)
    cycle_mean, cycle_second = cycle_moments(p, cfg.pity if cfg.has_pity else None)
    quantiles = {q: runs_for_quantile(p, q, first_cap) for q in Z}

    goal_items = max(1, goal_items)
    drops = max(1, math.ceil(goal_items / max(1, cfg.items_per_drop)))
    goal_mean = first_mean + (drops - 1) * cycle_mean
    if cfg.has_pity:
        goal_worst = first_cap + (drops - 1) * cfg.pity
    elif p >= 1:
        goal_worst = drops
    else:
        goal_worst = None
    if drops == 1:
        goal_quantiles = dict(quantiles)
    else:
        # Sum of independent cycles: normal approximation, clamped to what is possible.
        variance = (first_second - first_mean ** 2) + (drops - 1) * (cycle_second - cycle_mean ** 2)
        sd = math.sqrt(max(0.0, variance))
        goal_quantiles = {}
        for q, z in Z.items():
            runs = goal_mean + z * sd if goal_mean != math.inf else math.inf
            if runs != math.inf:
                runs = max(drops, math.ceil(runs))
                if goal_worst is not None:
                    runs = min(runs, goal_worst)
            goal_quantiles[q] = runs

    farm_runs = int(farm_seconds // cfg.run_seconds) if cfg.run_seconds > 0 else 0
    return DropReport(
        p=p,
        mean_runs=first_mean,
        quantile_runs=quantiles,
        worst_runs=first_cap if cfg.has_pity else (1 if p >= 1 else None),
        cycle_runs=cycle_mean,
        goal_items=goal_items,
        goal_drops=drops,
        goal_mean_runs=goal_mean,
        goal_quantile_runs=goal_quantiles,
        goal_worst_runs=goal_worst,
        farm_runs=farm_runs,
        farm_expected_items=expected_drops(cfg, farm_runs) * cfg.items_per_drop,
        farm_chance_any=chance_at_least_one(cfg, farm_runs),
        run_seconds=cfg.run_seconds,
    )


# ----------------------------------------------------------------- formatting

def format_number(value, decimals=0):
    """Brazilian style: 12.345,6"""
    if value == math.inf:
        return "∞"
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def format_percent(fraction):
    pct = fraction * 100
    if pct >= 99.995 and fraction < 1:
        return ">99,99%"
    if 0 < pct < 0.01:
        return "<0,01%"
    decimals = 0 if pct >= 99.5 or pct == round(pct) else (1 if pct >= 10 else 2)
    return format_number(pct, decimals) + "%"


def format_chance(p):
    if p <= 0:
        return "0%"
    one_in = 1 / p
    pct = p * 100
    decimals = 4 if pct < 0.01 else (3 if pct < 0.1 else (2 if pct < 10 else 1))
    pct_text = format_number(pct, decimals).rstrip("0").rstrip(",") + "%"
    return f"{pct_text} (1 em {format_number(one_in, 0 if one_in >= 100 else 1).removesuffix(',0')})"


def format_time(seconds):
    if seconds == math.inf:
        return "∞"
    seconds = max(0, round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, s = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}min {s:02d}s" if s else f"{minutes}min"
    hours, m = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {m:02d}min" if m else f"{hours}h"
    days, h = divmod(hours, 24)
    if days < 365:
        return f"{days}d {h}h" if h else f"{days}d"
    return f"{format_number(days / 365, 1)} anos"
