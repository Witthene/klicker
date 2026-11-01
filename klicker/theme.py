"""Liquid Glass palettes (light/dark) and the matching Qt stylesheet."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication


def _c(r, g, b, a=255):
    return QColor(r, g, b, a)


DARK = dict(
    text=_c(245, 247, 250), subtext=_c(235, 235, 245, 150), on_accent=_c(255, 255, 255),
    window_tint=_c(20, 22, 32, 125), window_solid=_c(24, 26, 36, 242), window_border=_c(255, 255, 255, 45),
    acrylic_tint=_c(14, 16, 24, 70),
    card_top=_c(255, 255, 255, 30), card_bottom=_c(255, 255, 255, 9),
    card_border_top=_c(255, 255, 255, 95), card_border_bottom=_c(255, 255, 255, 16), sheen=_c(255, 255, 255, 16),
    control_bg=_c(255, 255, 255, 20), control_hover=_c(255, 255, 255, 34), control_pressed=_c(255, 255, 255, 12),
    control_border=_c(255, 255, 255, 30), control_strong=_c(255, 255, 255, 48),
    thumb_top=_c(255, 255, 255, 72), thumb_bottom=_c(255, 255, 255, 36), thumb_border=_c(255, 255, 255, 115),
    shadow=_c(0, 0, 0, 80),
    accent=_c(10, 132, 255), danger=_c(255, 69, 58), success=_c(48, 209, 88),
    blob1=_c(10, 132, 255, 75), blob2=_c(191, 90, 242, 60), blob3=_c(100, 210, 255, 42),
    menu_bg=_c(36, 38, 48, 248),
)

LIGHT = dict(
    text=_c(28, 28, 30), subtext=_c(60, 60, 67, 165), on_accent=_c(255, 255, 255),
    window_tint=_c(246, 247, 252, 135), window_solid=_c(243, 245, 250, 245), window_border=_c(255, 255, 255, 210),
    acrylic_tint=_c(238, 240, 248, 80),
    card_top=_c(255, 255, 255, 175), card_bottom=_c(255, 255, 255, 95),
    card_border_top=_c(255, 255, 255, 255), card_border_bottom=_c(255, 255, 255, 120), sheen=_c(255, 255, 255, 70),
    control_bg=_c(118, 118, 128, 24), control_hover=_c(118, 118, 128, 40), control_pressed=_c(118, 118, 128, 58),
    control_border=_c(0, 0, 0, 14), control_strong=_c(120, 120, 128, 80),
    thumb_top=_c(255, 255, 255, 255), thumb_bottom=_c(248, 249, 252, 240), thumb_border=_c(0, 0, 0, 20),
    shadow=_c(0, 0, 0, 45),
    accent=_c(0, 122, 255), danger=_c(255, 59, 48), success=_c(52, 199, 89),
    blob1=_c(0, 122, 255, 60), blob2=_c(175, 82, 222, 48), blob3=_c(90, 200, 250, 55),
    menu_bg=_c(250, 250, 252, 250),
)


# Sakura dusk: pastel pinks over an indigo sky, drawn as an animated scene.
ANIME = dict(
    DARK,
    text=_c(255, 250, 253), subtext=_c(255, 232, 244, 185),
    window_tint=_c(40, 24, 70, 150), window_solid=_c(36, 22, 64, 245), window_border=_c(255, 200, 230, 95),
    acrylic_tint=_c(40, 20, 60, 80),
    card_top=_c(255, 255, 255, 46), card_bottom=_c(255, 214, 236, 16),
    card_border_top=_c(255, 232, 246, 150), card_border_bottom=_c(255, 170, 215, 34), sheen=_c(255, 255, 255, 24),
    control_bg=_c(255, 255, 255, 28), control_hover=_c(255, 255, 255, 44), control_pressed=_c(255, 255, 255, 16),
    control_border=_c(255, 210, 235, 55), control_strong=_c(255, 255, 255, 60),
    thumb_top=_c(255, 186, 222, 135), thumb_bottom=_c(255, 130, 196, 85), thumb_border=_c(255, 236, 248, 185),
    shadow=_c(70, 0, 50, 85),
    accent=_c(255, 92, 168), danger=_c(255, 84, 112), success=_c(120, 230, 180),
    menu_bg=_c(52, 30, 80, 248),
)

# Noir: matches the app icon — near-black glass, violet hair tones, lilac highlights.
NOIR = dict(
    DARK,
    text=_c(244, 238, 252), subtext=_c(214, 198, 238, 150), on_accent=_c(255, 255, 255),
    window_tint=_c(6, 4, 10, 175), window_solid=_c(8, 6, 12, 250), window_border=_c(156, 124, 214, 90),
    acrylic_tint=_c(4, 2, 8, 150),
    card_top=_c(156, 124, 214, 26), card_bottom=_c(40, 24, 64, 14),
    card_border_top=_c(196, 168, 245, 105), card_border_bottom=_c(120, 80, 180, 26), sheen=_c(220, 200, 255, 12),
    control_bg=_c(156, 124, 214, 20), control_hover=_c(156, 124, 214, 38), control_pressed=_c(156, 124, 214, 12),
    control_border=_c(176, 146, 230, 42), control_strong=_c(176, 146, 230, 70),
    thumb_top=_c(150, 108, 220, 150), thumb_bottom=_c(96, 58, 160, 110), thumb_border=_c(214, 190, 255, 150),
    shadow=_c(0, 0, 0, 120),
    accent=_c(146, 96, 232), danger=_c(236, 72, 128), success=_c(150, 220, 190),
    blob1=_c(110, 70, 170, 70), blob2=_c(70, 30, 120, 70), blob3=_c(200, 150, 240, 30),
    menu_bg=_c(14, 10, 22, 250),
)

PALETTES = {"dark": DARK, "light": LIGHT, "anime": ANIME, "noir": NOIR}


class Palette:
    def __init__(self, name):
        self.name = name
        self.dark = name != "light"
        self.scene = name == "anime"  # paint the animated sakura sky behind the glass
        for key, value in PALETTES[name].items():
            setattr(self, key, value)


_mode = "system"
_palette = Palette("dark")


def system_is_dark():
    app = QGuiApplication.instance()
    if app is None:
        return True
    return app.styleHints().colorScheme() != Qt.ColorScheme.Light


def set_mode(mode):
    global _mode, _palette
    _mode = mode
    if mode == "system":
        mode = "dark" if system_is_dark() else "light"
    _palette = Palette(mode if mode in PALETTES else "dark")


def mode():
    return _mode


def palette():
    return _palette


def qss(color):
    return f"rgba({color.red()},{color.green()},{color.blue()},{color.alpha()})"


def stylesheet():
    p = _palette
    return f"""
    QWidget {{
        color: {qss(p.text)};
        font-family: 'Segoe UI Variable Text', 'Segoe UI';
        font-size: 13px;
    }}
    QLabel#appTitle {{ font-size: 13px; font-weight: 600; }}
    QLabel#caption {{ color: {qss(p.subtext)}; font-size: 12px; }}
    QLabel#section {{ font-size: 13px; font-weight: 600; }}
    QLabel#status {{ color: {qss(p.subtext)}; font-size: 13px; }}
    QLabel#statValue {{
        font-family: 'Segoe UI Variable Display', 'Segoe UI';
        font-size: 22px; font-weight: 600;
    }}
    QLabel#badge {{
        background: {qss(p.accent)}; color: {qss(p.on_accent)};
        border-radius: 10px; font-size: 11px; font-weight: 700;
        min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px;
    }}
    QSpinBox, QDoubleSpinBox {{
        background: {qss(p.control_bg)};
        border: 1px solid {qss(p.control_border)};
        border-radius: 11px;
        padding: 0px 6px;
        font-size: 15px;
        selection-background-color: {qss(p.accent)};
        selection-color: {qss(p.on_accent)};
    }}
    QSpinBox:hover, QDoubleSpinBox:hover {{ background: {qss(p.control_hover)}; }}
    QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {qss(p.accent)}; }}
    QSpinBox:disabled, QDoubleSpinBox:disabled {{ color: {qss(p.subtext)}; }}
    /* Hide the arrows here, not with NoButtons: a styled QSpinBox with NoButtons
       collapses its editor to 1px wide (Qt 6 bug). */
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}
    QLabel#resultValue {{ font-weight: 600; }}
    QLabel#resultHint {{ color: {qss(p.subtext)}; font-size: 11px; }}
    QPushButton#pill {{
        background: {qss(p.control_bg)};
        border: 1px solid {qss(p.control_border)};
        border-radius: 14px;
        padding: 6px 16px;
        font-weight: 600;
    }}
    QPushButton#pill:hover {{ background: {qss(p.control_hover)}; }}
    QPushButton#pill:pressed {{ background: {qss(p.control_pressed)}; }}
    QPushButton#pill:disabled {{ color: {qss(p.subtext)}; }}
    QPushButton#pill[capturing="true"] {{ border: 1px solid {qss(p.accent)}; color: {qss(p.accent)}; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ width: 6px; background: transparent; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {qss(p.control_strong)}; border-radius: 3px; min-height: 24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QMenu {{
        background: {qss(p.menu_bg)};
        border: 1px solid {qss(p.control_border)};
        border-radius: 10px; padding: 6px;
    }}
    QMenu::item {{ padding: 6px 22px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {qss(p.accent)}; color: {qss(p.on_accent)}; }}
    QToolTip {{
        background: {qss(p.menu_bg)}; color: {qss(p.text)};
        border: 1px solid {qss(p.control_border)}; border-radius: 6px; padding: 4px 8px;
    }}
    """
