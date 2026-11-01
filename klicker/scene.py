"""Animated anime-style backdrop: a sakura dusk sky drawn entirely in code."""

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainterPath, QRadialGradient

CLEAR = QColor(0, 0, 0, 0)


def _petal_path():
    path = QPainterPath(QPointF(0, -1))
    path.cubicTo(QPointF(0.95, -0.75), QPointF(0.75, 0.65), QPointF(0, 1))
    path.cubicTo(QPointF(-0.75, 0.65), QPointF(-0.95, -0.75), QPointF(0, -1))
    # The little notch at the tip that makes it read as a cherry-blossom petal.
    notch = QPainterPath(QPointF(-0.18, -1.05))
    notch.lineTo(QPointF(0, -0.72))
    notch.lineTo(QPointF(0.18, -1.05))
    notch.closeSubpath()
    return path.subtracted(notch)


PETAL = _petal_path()


class SakuraScene:
    def __init__(self, petal_count=26, seed=7):
        self._rng = random.Random(seed)
        self._size = (440.0, 820.0)
        self._time = 0.0
        self._stars = [(self._rng.random(), self._rng.random() * 0.45, self._rng.uniform(0.6, 1.8),
                        self._rng.uniform(0, math.tau)) for _ in range(46)]
        self._petals = [self._new_petal(initial=True) for _ in range(petal_count)]

    def _new_petal(self, initial=False):
        w, h = self._size
        r = self._rng
        return {
            "x": r.uniform(-40, w),
            "y": r.uniform(-h, h) if initial else r.uniform(-60, -10),
            "size": r.uniform(4.5, 9.5),
            "vy": r.uniform(26, 58),
            "vx": r.uniform(10, 32),
            "sway": r.uniform(14, 34),
            "phase": r.uniform(0, math.tau),
            "rot": r.uniform(0, 360),
            "vrot": r.uniform(-90, 90),
            "flip": r.uniform(0, math.tau),
            "tone": r.random(),
        }

    def tick(self, dt, width, height):
        self._size = (float(width), float(height))
        self._time += dt
        for i, p in enumerate(self._petals):
            p["y"] += p["vy"] * dt
            p["x"] += (p["vx"] + math.sin(self._time * 1.3 + p["phase"]) * p["sway"]) * dt
            p["rot"] += p["vrot"] * dt
            p["flip"] += dt * 2.2
            if p["y"] > height + 20 or p["x"] > width + 30:
                self._petals[i] = self._new_petal()

    def paint(self, p, rect, show_petals=True):
        w, h = rect.width(), rect.height()

        sky = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        sky.setColorAt(0.0, QColor(22, 18, 58))
        sky.setColorAt(0.38, QColor(64, 40, 112))
        sky.setColorAt(0.68, QColor(170, 86, 150))
        sky.setColorAt(0.86, QColor(246, 140, 150))
        sky.setColorAt(1.0, QColor(255, 196, 160))
        p.fillRect(rect, QBrush(sky))

        for sx, sy, size, phase in self._stars:
            twinkle = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(self._time * 1.7 + phase))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 246, 255, round(200 * twinkle)))
            p.drawEllipse(QPointF(rect.left() + sx * w, rect.top() + sy * h), size * 0.6, size * 0.6)

        moon = QPointF(rect.left() + w * 0.88, rect.top() + h * 0.15)
        glow = QRadialGradient(moon, 100)
        glow.setColorAt(0, QColor(255, 220, 240, 110))
        glow.setColorAt(1, CLEAR)
        p.setBrush(QBrush(glow))
        p.drawEllipse(moon, 100, 100)
        body = QRadialGradient(QPointF(moon.x() - 8, moon.y() - 10), 42)
        body.setColorAt(0, QColor(255, 252, 250))
        body.setColorAt(1, QColor(255, 222, 236))
        p.setBrush(QBrush(body))
        p.drawEllipse(moon, 30, 30)

        self._mountains(p, rect, 0.80, 46, QColor(120, 60, 130, 150), 1.7)
        self._mountains(p, rect, 0.88, 34, QColor(70, 34, 92, 200), 2.6)

        if show_petals:
            for petal in self._petals:
                self._petal(p, rect, petal)

    def _mountains(self, p, rect, base, amplitude, color, freq):
        w, h = rect.width(), rect.height()
        path = QPainterPath(QPointF(rect.left(), rect.bottom()))
        steps = 40
        for i in range(steps + 1):
            x = i / steps
            y = base * h - amplitude * (0.55 * math.sin(x * math.pi * freq + 0.8)
                                        + 0.45 * math.sin(x * math.pi * freq * 2.3 + 2.1))
            path.lineTo(rect.left() + x * w, rect.top() + y)
        path.lineTo(rect.right(), rect.bottom())
        path.closeSubpath()
        p.fillPath(path, color)

    def _petal(self, p, rect, petal):
        p.save()
        p.translate(rect.left() + petal["x"], rect.top() + petal["y"])
        p.rotate(petal["rot"])
        # Scaling one axis by a cosine fakes the petal turning over as it falls.
        p.scale(petal["size"] * (0.35 + 0.65 * abs(math.cos(petal["flip"]))), petal["size"])
        top = QColor(255, 214 + round(30 * petal["tone"]), 232)
        bottom = QColor(255, 140 + round(40 * petal["tone"]), 186)
        grad = QLinearGradient(QPointF(0, -1), QPointF(0, 1))
        grad.setColorAt(0, top)
        grad.setColorAt(1, bottom)
        p.setOpacity(0.85)
        p.fillPath(PETAL, QBrush(grad))
        p.restore()


def paint_cover_image(p, rect, pixmap):
    """Draw ``pixmap`` scaled to cover ``rect`` (like CSS background-size: cover)."""
    if pixmap is None or pixmap.isNull():
        return
    src_w, src_h = pixmap.width(), pixmap.height()
    scale = max(rect.width() / src_w, rect.height() / src_h)
    w, h = rect.width() / scale, rect.height() / scale
    source = QRectF((src_w - w) / 2, (src_h - h) / 2, w, h)
    p.drawPixmap(rect, pixmap, source)
