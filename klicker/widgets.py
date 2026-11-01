"""Custom-painted Liquid Glass controls."""

from PySide6.QtCore import (QEasingCurve, QEvent, QPointF, QRectF, QSize, Qt, QVariantAnimation,
                            Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import QAbstractButton, QFrame, QPushButton, QSizePolicy, QWidget

from . import theme, winapi

CLEAR = QColor(0, 0, 0, 0)


def _mix(a, b, t):
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def _with_alpha(color, alpha):
    c = QColor(color)
    c.setAlpha(max(0, min(255, round(alpha))))
    return c


def _animation(owner, duration, slot, overshoot=None):
    anim = QVariantAnimation(owner)
    anim.setDuration(duration)
    if overshoot is None:
        anim.setEasingCurve(QEasingCurve.OutCubic)
    else:
        curve = QEasingCurve(QEasingCurve.OutBack)
        curve.setOvershoot(overshoot)
        anim.setEasingCurve(curve)
    anim.valueChanged.connect(slot)
    return anim


def paint_glass(p, rect, radius, top, bottom, border_top, border_bottom, sheen=None):
    """Frosted fill + vertical sheen + light-catching rim: the core glass look."""
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    fill.setColorAt(0, top)
    fill.setColorAt(1, bottom)
    p.fillPath(path, QBrush(fill))
    if sheen is not None:
        gloss = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + rect.height() * 0.55))
        gloss.setColorAt(0, sheen)
        gloss.setColorAt(1, CLEAR)
        p.fillPath(path, QBrush(gloss))
    rim = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    rim.setColorAt(0, border_top)
    rim.setColorAt(1, border_bottom)
    p.setPen(QPen(QBrush(rim), 1))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    return path


class GlassCard(QFrame):
    RADIUS = 20

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal = theme.palette()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        paint_glass(p, rect, self.RADIUS, pal.card_top, pal.card_bottom,
                    pal.card_border_top, pal.card_border_bottom, pal.sheen)


class Segmented(QWidget):
    """Pill-shaped segmented control with a sliding, slightly springy glass thumb."""

    changed = Signal(int)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self._options = list(options)
        self._index = 0
        self._pos = 0.0
        self._anim = _animation(self, 320, self._set_pos, overshoot=0.9)
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        return QSize(90 * len(self._options), 34)

    def index(self):
        return self._index

    def setIndex(self, index, animate=True):
        index = max(0, min(len(self._options) - 1, index))
        self._index = index
        if animate and self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(float(index))
            self._anim.start()
        else:
            self._set_pos(float(index))

    def _set_pos(self, value):
        self._pos = value
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        index = int(event.position().x() / (self.width() / len(self._options)))
        index = max(0, min(len(self._options) - 1, index))
        if index != self._index:
            self.setIndex(index)
            self.changed.emit(index)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)
        pal = theme.palette()
        w, h = self.width(), self.height()
        track = QRectF(0.5, 0.5, w - 1, h - 1)
        p.setPen(QPen(pal.control_border, 1))
        p.setBrush(pal.control_bg)
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        n = len(self._options)
        seg = (w - 6) / n
        thumb = QRectF(3 + self._pos * seg, 3, seg, h - 6)
        p.setPen(Qt.NoPen)
        p.setBrush(pal.shadow)
        p.drawRoundedRect(thumb.translated(0, 1.2), thumb.height() / 2, thumb.height() / 2)
        paint_glass(p, thumb, thumb.height() / 2, pal.thumb_top, pal.thumb_bottom,
                    pal.thumb_border, _with_alpha(pal.thumb_border, pal.thumb_border.alpha() * 0.35))

        font = p.font()
        for i, label in enumerate(self._options):
            selected = i == self._index
            font.setWeight(QFont.Weight.DemiBold if selected else QFont.Weight.Normal)
            p.setFont(font)
            p.setPen(pal.text if selected else pal.subtext)
            p.drawText(QRectF(3 + i * seg, 0, seg, h), Qt.AlignCenter, label)


class Toggle(QAbstractButton):
    """iOS-style switch with a glass knob."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(48, 28)
        self.setCursor(Qt.PointingHandCursor)
        self._t = 0.0
        self._anim = _animation(self, 260, self._set_t, overshoot=1.1)
        self.toggled.connect(self._animate)

    def setValue(self, checked):
        """Set the state without animating (used when loading settings)."""
        self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(False)
        self._set_t(1.0 if checked else 0.0)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _set_t(self, value):
        self._t = value
        self.update()

    def sizeHint(self):
        return QSize(48, 28)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)
        pal = theme.palette()
        t = max(0.0, min(1.0, self._t))
        track = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(pal.control_border, 1))
        p.setBrush(_mix(pal.control_strong, pal.accent, t))
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        d = self.height() - 6
        x = 3 + self._t * (self.width() - 6 - d)
        knob = QRectF(x, 3, d, d)
        p.setPen(Qt.NoPen)
        p.setBrush(_with_alpha(QColor(0, 0, 0), 60))
        p.drawEllipse(knob.translated(0, 1.2))
        grad = QLinearGradient(knob.topLeft(), knob.bottomLeft())
        grad.setColorAt(0, QColor(255, 255, 255))
        grad.setColorAt(1, QColor(236, 238, 244))
        p.setBrush(grad)
        p.setPen(QPen(QColor(255, 255, 255, 200), 0.8))
        p.drawEllipse(knob)


class OrbButton(QAbstractButton):
    """The big start/stop button: a glossy liquid orb that breathes while running.

    ``glyph`` is "play" or "record"; ``role`` names the palette colour used at rest.
    """

    def __init__(self, glyph="play", role="accent", size=136, parent=None):
        super().__init__(parent)
        self._glyph = glyph
        self._role = role
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._running = False
        self._pulse = 0.0
        self._hover = 0.0
        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setDuration(1500)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.valueChanged.connect(self._set_pulse)
        self._hover_anim = _animation(self, 180, self._set_hover)

    def setRunning(self, running):
        self._running = running
        if running:
            self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._pulse = 0.0
        self.update()

    def _set_pulse(self, value):
        self._pulse = value
        self.update()

    def _set_hover(self, value):
        self._hover = value
        self.update()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)
        pal = theme.palette()
        color = pal.danger if self._running else getattr(pal, self._role)
        c = QPointF(self.width() / 2, self.height() / 2)
        base = self.width() * 0.34
        radius = base * (0.95 if self.isDown() else 1.0 + 0.02 * self._hover)

        # Soft halo; expands and fades on every breath while running.
        halo_r = radius + base * 0.26 + self._pulse * base * 0.22
        halo = QRadialGradient(c, halo_r)
        halo.setColorAt(radius / halo_r * 0.9, _with_alpha(color, 120 * (1 - self._pulse * 0.7) + 30 * self._hover))
        halo.setColorAt(1, CLEAR)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(c, halo_r, halo_r)

        # Liquid body: light enters top-left, deepens toward the bottom.
        body = QRadialGradient(QPointF(c.x() - radius * 0.35, c.y() - radius * 0.45), radius * 1.6)
        body.setColorAt(0, color.lighter(145))
        body.setColorAt(0.55, color)
        body.setColorAt(1, color.darker(150))
        p.setBrush(body)
        p.drawEllipse(c, radius, radius)

        # Caustic glow pooling at the bottom edge.
        caustic = QRadialGradient(QPointF(c.x(), c.y() + radius * 0.85), radius * 0.8)
        caustic.setColorAt(0, _with_alpha(color.lighter(170), 150))
        caustic.setColorAt(1, CLEAR)
        p.setBrush(caustic)
        p.drawEllipse(c, radius, radius)

        # Specular highlight across the top.
        gloss_rect = QRectF(c.x() - radius * 0.72, c.y() - radius * 0.93, radius * 1.44, radius * 0.92)
        gloss = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
        gloss.setColorAt(0, QColor(255, 255, 255, 170))
        gloss.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(gloss)
        p.drawEllipse(gloss_rect)

        rim = QLinearGradient(QPointF(c.x(), c.y() - radius), QPointF(c.x(), c.y() + radius))
        rim.setColorAt(0, QColor(255, 255, 255, 190))
        rim.setColorAt(0.5, QColor(255, 255, 255, 40))
        rim.setColorAt(1, QColor(255, 255, 255, 110))
        p.setPen(QPen(QBrush(rim), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, radius, radius)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        self._paint_glyph(p, QPointF(c.x(), c.y() + 1.5), base / 46)
        p.setBrush(QColor(255, 255, 255))
        self._paint_glyph(p, c, base / 46)

    def _paint_glyph(self, p, c, k):
        if self._running:
            p.drawRoundedRect(QRectF(c.x() - 14 * k, c.y() - 14 * k, 28 * k, 28 * k), 6 * k, 6 * k)
        elif self._glyph == "record":
            p.drawEllipse(c, 15 * k, 15 * k)
        else:
            path = QPainterPath()
            path.moveTo(c.x() - 11 * k, c.y() - 18 * k)
            path.lineTo(c.x() + 19 * k, c.y())
            path.lineTo(c.x() - 11 * k, c.y() + 18 * k)
            path.closeSubpath()
            p.drawPath(path)


class GlyphButton(QAbstractButton):
    """Small round glass button drawing a vector glyph (minimise / close / remove)."""

    def __init__(self, glyph, size=28, danger_hover=False, parent=None):
        super().__init__(parent)
        self._glyph = glyph
        self._danger = danger_hover
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal = theme.palette()
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        hovered = self.underMouse()
        if hovered and self._danger:
            bg = pal.danger
        elif self.isDown():
            bg = pal.control_pressed
        elif hovered:
            bg = pal.control_hover
        else:
            bg = pal.control_bg
        p.setPen(QPen(pal.control_border, 1))
        p.setBrush(bg)
        p.drawEllipse(r)
        fg = pal.on_accent if hovered and self._danger else pal.text
        p.setPen(QPen(fg, 1.5, Qt.SolidLine, Qt.RoundCap))
        c = r.center()
        s = r.width() * 0.17
        if self._glyph == "minimize":
            p.drawLine(QPointF(c.x() - s, c.y()), QPointF(c.x() + s, c.y()))
        else:
            p.drawLine(QPointF(c.x() - s, c.y() - s), QPointF(c.x() + s, c.y() + s))
            p.drawLine(QPointF(c.x() - s, c.y() + s), QPointF(c.x() + s, c.y() - s))


_MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}


class HotkeyButton(QPushButton):
    """Click it, then press the desired combination. Esc cancels."""

    captureStarted = Signal()
    captureEnded = Signal(bool)  # True when a new hotkey was chosen

    def __init__(self, parent=None):
        self._capturing = False  # event() can fire during the base constructor
        super().__init__(parent)
        self.setObjectName("pill")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(130)
        self.vk = 0x77
        self.mods = 0
        self.clicked.connect(self._begin)

    def setHotkey(self, vk, mods):
        self.vk, self.mods = vk, mods
        self.setText(winapi.hotkey_text(vk, mods))

    def _set_capturing(self, capturing):
        self._capturing = capturing
        self.setProperty("capturing", capturing)
        self.style().unpolish(self)
        self.style().polish(self)

    def _begin(self):
        if self._capturing:
            return
        self._set_capturing(True)
        self.setText("Pressione as teclas…")
        self.grabKeyboard()
        self.captureStarted.emit()

    def _end(self, accepted):
        self.releaseKeyboard()
        self._set_capturing(False)
        self.setText(winapi.hotkey_text(self.vk, self.mods))
        self.captureEnded.emit(accepted)

    def event(self, event):
        # Tab / Shift+Tab never reach keyPressEvent: Qt uses them for focus moves.
        if self._capturing and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            self.keyPressEvent(event)
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if not self._capturing:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key_Escape:
            self._end(False)
            return
        vk = event.nativeVirtualKey()
        mods = 0
        m = event.modifiers()
        if m & Qt.ControlModifier:
            mods |= winapi.MOD_CONTROL
        if m & Qt.AltModifier:
            mods |= winapi.MOD_ALT
        if m & Qt.ShiftModifier:
            mods |= winapi.MOD_SHIFT
        if m & Qt.MetaModifier:
            mods |= winapi.MOD_WIN
        if not vk or vk in _MODIFIER_VKS:
            return  # wait for the non-modifier key
        self.vk, self.mods = vk, mods
        self._end(True)

    def focusOutEvent(self, event):
        if self._capturing:
            self._end(False)
        super().focusOutEvent(event)
