"""User preferences, persisted as JSON in %APPDATA%\\Klicker."""

import json
import os
import shutil
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class Settings:
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    millis: int = 100
    jitter_enabled: bool = False
    jitter_ms: int = 20
    button: str = "left"
    clicks: int = 1
    repeat_mode: str = "infinite"
    repeat_count: int = 100
    duration_s: int = 60
    position_mode: str = "cursor"
    points: list = field(default_factory=list)
    restore_cursor: bool = True
    hotkey_vk: int = 0x77  # F8, same default as GS Auto Clicker
    hotkey_mods: int = 0
    always_on_top: bool = False
    protect_self: bool = True
    acrylic: bool = True
    theme: str = "system"  # system | dark | light | anime | noir
    background_image: str = ""
    petals: bool = True

    # Macro (TinyTask-style). Hotkeys default to TinyTask's Ctrl+Shift+Alt+R / P.
    speed_index: int = 0   # 1x | 2x | 100x | custom
    speed_custom: int = 10
    macro_repeat: str = "once"  # once | count | continuous
    macro_loops: int = 3
    record_moves: bool = True
    record_keys: bool = True
    record_vk: int = 0x52
    record_mods: int = 0x7
    play_vk: int = 0x50
    play_mods: int = 0x7

    # Drop calculator.
    drop_chance_mode: str = "percent"  # percent | one_in
    drop_chance_pct: float = 1.0
    drop_one_in: float = 100.0
    drop_luck: float = 1.0
    drop_items: int = 1
    run_minutes: int = 0
    run_seconds: int = 30
    pity_enabled: bool = False
    pity_runs: int = 100
    pity_progress: int = 0
    goal_items: int = 1
    farm_hours: int = 1
    farm_minutes: int = 0

    @property
    def drop_chance(self):
        """Per-run probability (0–1), before luck."""
        if self.drop_chance_mode == "one_in":
            return 1 / max(1.0, self.drop_one_in)
        return min(100.0, max(0.0, self.drop_chance_pct)) / 100

    @property
    def macro_speed(self):
        return (1, 2, 100, self.speed_custom)[self.speed_index]

    @property
    def macro_loop_count(self):
        """0 means continuous playback."""
        return {"once": 1, "count": self.macro_loops, "continuous": 0}[self.macro_repeat]

    @property
    def interval_ms(self):
        return ((self.hours * 60 + self.minutes) * 60 + self.seconds) * 1000 + self.millis


def _appdata():
    return Path(os.environ.get("APPDATA") or str(Path.home()))


def data_dir():
    return _appdata() / "Klicker"


def migrate_legacy():
    """Carry settings and the last recording over from the Glass Clicker days."""
    legacy = _appdata() / "GlassClicker"
    target = data_dir()
    if target.exists() or not legacy.is_dir():
        return
    try:
        shutil.copytree(legacy, target)
        old_macro = target / "ultima-gravacao.gcmacro"
        if old_macro.exists():
            old_macro.replace(last_macro_path())
    except OSError:
        pass


def settings_path():
    return data_dir() / "settings.json"


def last_macro_path():
    """The most recent recording, kept between sessions."""
    return data_dir() / "ultima-gravacao.kmacro"


def load():
    migrate_legacy()
    s = Settings()
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return s
    defaults = asdict(s)
    for f in fields(Settings):
        if f.name in data and isinstance(data[f.name], type(defaults[f.name])):
            setattr(s, f.name, data[f.name])
    s.points = [tuple(p) for p in s.points if isinstance(p, list) and len(p) == 2]
    s.speed_index = min(max(s.speed_index, 0), 3)
    s.speed_custom = min(max(s.speed_custom, 1), 100)
    if s.macro_repeat not in ("once", "count", "continuous"):
        s.macro_repeat = "once"
    if s.drop_chance_mode not in ("percent", "one_in"):
        s.drop_chance_mode = "percent"
    return s


def save(s):
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(s), indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass
