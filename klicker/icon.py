"""App icon, drawn in code so the repo needs no binary assets.

A short-haired anime girl (dark violet bob, lilac highlights, violet eyes,
white ruffled collar) on a black tile, with a mouse pointer clicking beside her.
Everything is laid out on a 256×256 canvas and scaled to the requested size.
"""

import struct

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
TILE = QRectF(16, 16, 224, 224)
TILE_RADIUS = 52

HAIR_DARK = QColor(22, 14, 34)
HAIR_MID = QColor(48, 30, 74)
HAIR_SHINE = QColor(156, 124, 214)
SKIN = QColor(246, 232, 238)
SKIN_SHADE = QColor(214, 188, 208)
EYE_TOP = QColor(120, 62, 170)
EYE_BOTTOM = QColor(236, 178, 238)
LINE = QColor(18, 10, 26)


def _path(start, *segments, close=True):
    """Build a path from a start point and cubic segments ((c1x, c1y, c2x, c2y, x, y) or (x, y))."""
    path = QPainterPath(QPointF(*start))
    for seg in segments:
        if len(seg) == 6:
            path.cubicTo(*seg)
        else:
            path.lineTo(*seg)
    if close:
        path.closeSubpath()
    return path


def _background(p, tile, radius):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(6, 5, 9))
    p.drawRoundedRect(tile, radius, radius)
    glow = QRadialGradient(QPointF(118, 110), 140)
    glow.setColorAt(0, QColor(110, 70, 170, 90))
    glow.setColorAt(1, QColor(110, 70, 170, 0))
    p.setBrush(glow)
    p.drawRoundedRect(tile, radius, radius)


def _body(p):
    # Black blazer shoulders.
    shoulders = _path((30, 260), (36, 222, 70, 206, 104, 200), (152, 200),
                      (186, 206, 220, 222, 226, 260))
    p.setBrush(QColor(16, 13, 22))
    p.setPen(QPen(QColor(90, 70, 130, 120), 2))
    p.drawPath(shoulders)
    # Neck with the chin's shadow.
    p.setPen(Qt.NoPen)
    p.setBrush(SKIN)
    p.drawRect(QRectF(113, 170, 30, 38))
    p.setBrush(QColor(SKIN_SHADE.red(), SKIN_SHADE.green(), SKIN_SHADE.blue(), 200))
    p.drawPath(_path((113, 172), (143, 172), (143, 184), (128, 192, 128, 192, 113, 184)))
    # Ruffled high collar: a white band whose lower edge waves like a frill.
    collar = QPainterPath(QPointF(106, 194))
    collar.cubicTo(118, 200, 138, 200, 150, 194)
    collar.lineTo(160, 214)
    xs = [160, 150, 140, 128, 116, 106, 96]
    for a, b in zip(xs, xs[1:]):
        collar.quadTo((a + b) / 2, 226 if (a // 10) % 2 else 220, b, 214 + (4 if b in (128,) else 0))
    collar.closeSubpath()
    p.setPen(QPen(QColor(170, 160, 185), 1.6))
    p.setBrush(QColor(250, 248, 252))
    p.drawPath(collar)
    p.setPen(QPen(QColor(190, 180, 205), 1.4, Qt.SolidLine, Qt.RoundCap))
    for x0, x1 in ((112, 108), (122, 120), (134, 136), (144, 148)):
        p.drawLine(QPointF(x0, 200), QPointF(x1, 216))
    # Ribbon tie hanging from the collar.
    p.setPen(QPen(QColor(250, 248, 252), 3.5, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(128, 222), QPointF(114, 252))
    p.drawLine(QPointF(128, 222), QPointF(142, 254))
    p.setBrush(QColor(250, 248, 252))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(128, 222), 4.5, 4)


def _back_hair(p):
    bob = _path((64, 124), (60, 60, 96, 34, 128, 34), (160, 34, 196, 60, 192, 124),
                (192, 160, 200, 182, 206, 194), (186, 196, 170, 190, 160, 184),
                (128, 186), (96, 184), (86, 190, 70, 196, 50, 194),
                (56, 182, 64, 160, 64, 124))
    grad = QLinearGradient(QPointF(0, 34), QPointF(0, 196))
    grad.setColorAt(0, HAIR_MID)
    grad.setColorAt(1, HAIR_DARK)
    # A lilac rim light keeps the dark hair from melting into the black tile.
    p.setPen(QPen(QColor(150, 116, 214, 150), 3))
    p.setBrush(grad)
    p.drawPath(bob)


def _face(p):
    face = _path((82, 96), (82, 146, 104, 174, 128, 184), (152, 174, 174, 146, 174, 96))
    grad = QLinearGradient(QPointF(0, 96), QPointF(0, 184))
    grad.setColorAt(0, SKIN)
    grad.setColorAt(1, QColor(240, 222, 232))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawPath(face)
    # Blush, nose and a small, serious mouth.
    p.setBrush(QColor(236, 150, 180, 70))
    p.drawEllipse(QPointF(100, 154), 9, 4)
    p.drawEllipse(QPointF(156, 154), 9, 4)
    p.setPen(QPen(QColor(196, 150, 170), 2, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(129, 150), QPointF(127, 156))
    p.setPen(QPen(QColor(176, 92, 118), 2.4, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(_path((121, 167), (125, 169, 131, 169, 135, 167), close=False))


def _eye(p, cx, mirror):
    s = -1 if mirror else 1
    # Almond, a little half-lidded like the reference's calm stare.
    white = _path((cx - 15 * s, 133), (cx - 8 * s, 124, cx + 10 * s, 122, cx + 16 * s, 128),
                  (cx + 12 * s, 142, cx - 6 * s, 146, cx - 15 * s, 133))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(252, 248, 252))
    p.drawPath(white)
    p.save()
    p.setClipPath(white)
    iris = QLinearGradient(QPointF(0, 122), QPointF(0, 146))
    iris.setColorAt(0, EYE_TOP)
    iris.setColorAt(1, EYE_BOTTOM)
    p.setBrush(iris)
    p.drawEllipse(QPointF(cx + 1 * s, 134), 10, 12.5)
    p.setBrush(QColor(60, 24, 90))
    p.drawEllipse(QPointF(cx + 1 * s, 134), 4.2, 5.6)
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawEllipse(QPointF(cx - 3 * s, 130), 3, 3)
    p.drawEllipse(QPointF(cx + 5 * s, 139), 1.6, 1.6)
    # Shadow cast by the upper lid.
    p.setBrush(QColor(40, 20, 60, 90))
    p.drawRect(QRectF(cx - 18, 118, 36, 8))
    p.restore()
    # Heavy upper lash with a flick at the outer corner, thin lower lash.
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(LINE, 4.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    outer = cx + 16 * s
    p.drawPath(_path((cx - 15 * s, 133), (cx - 8 * s, 124, cx + 10 * s, 122, outer, 128),
                     (outer + 3 * s, 126), close=False))
    p.setPen(QPen(QColor(120, 80, 120, 170), 1.4, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(_path((cx - 10 * s, 141), (cx - 2 * s, 145, cx + 7 * s, 144, cx + 12 * s, 140), close=False))


def _front_hair(p):
    # Blunt hime bangs over the brows, with a jagged, strand-y lower edge.
    bangs = QPainterPath(QPointF(70, 128))
    bangs.cubicTo(66, 64, 98, 40, 128, 40)
    bangs.cubicTo(158, 40, 190, 64, 186, 128)
    # Strand tips hang to just above the eyes; between tips the edge lifts a little.
    tips = [(176, 121), (162, 119), (148, 121), (134, 118), (120, 121), (106, 118), (92, 121), (80, 119)]
    x_prev = 186
    for x, y in tips:
        gap_x = (x_prev + x) / 2
        # Up into a rounded gap, then down to a sharp tip: reads as strands, not a hem.
        bangs.quadTo(x_prev - 2, 114, gap_x, 108)
        bangs.quadTo(x + 2, 112, x, y)
        x_prev = x
    bangs.quadTo(74, 112, 70, 128)
    bangs.closeSubpath()
    grad = QLinearGradient(QPointF(0, 40), QPointF(0, 120))
    grad.setColorAt(0, HAIR_MID)
    grad.setColorAt(1, HAIR_DARK)
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawPath(bangs)
    # Side locks framing the cheeks, ending at the jaw (short hair).
    for s in (1, -1):
        x = 128 - 58 * s
        lock = _path((x, 96), (x - 4 * s, 130, x - 6 * s, 160, x - 2 * s, 184),
                     (x + 8 * s, 168, x + 14 * s, 142, x + 18 * s, 112))
        p.drawPath(lock)
    # Lilac highlights: a sheen ring on the crown and a few strands.
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(HAIR_SHINE.red(), HAIR_SHINE.green(), HAIR_SHINE.blue(), 150), 5, Qt.SolidLine,
                  Qt.RoundCap))
    p.drawArc(QRectF(84, 52, 88, 40), 30 * 16, 120 * 16)
    p.setPen(QPen(QColor(HAIR_SHINE.red(), HAIR_SHINE.green(), HAIR_SHINE.blue(), 140), 2.4, Qt.SolidLine,
                  Qt.RoundCap))
    for strand in (((104, 58), (98, 74, 98, 92, 100, 110)), ((146, 56), (154, 72, 156, 92, 154, 110)),
                   ((126, 50), (124, 70, 124, 90, 127, 108)),
                   ((72, 132), (70, 150, 70, 166, 72, 178)), ((184, 132), (186, 150, 186, 166, 184, 178))):
        p.drawPath(_path(strand[0], strand[1], close=False))


def _cursor(p):
    tip = QPointF(170, 160)
    # Click ripples open toward the lower right, away from her face.
    for radius, alpha in ((16, 230), (26, 130)):
        p.setPen(QPen(QColor(200, 166, 255, alpha), 4.5, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(tip.x() - radius, tip.y() - radius, radius * 2, radius * 2), -10 * 16, 80 * 16)
    arrow = QPainterPath(tip)
    for dx, dy in [(0, 72), (18, 56), (31, 82), (44, 76), (32, 50), (55, 48)]:
        arrow.lineTo(tip.x() + dx * 0.86, tip.y() + dy * 0.86)
    arrow.closeSubpath()
    p.setPen(QPen(QColor(0, 0, 0), 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(QColor(0, 0, 0))
    p.drawPath(arrow)
    p.setPen(QPen(QColor(255, 255, 255), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(QColor(255, 255, 255))
    p.drawPath(arrow)


def render_icon(size, framed=True):
    """``framed=False`` fills the whole square with no rounded tile or rim, for platforms
    that cut the icon into their own shape (Android adaptive icons)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 256, size / 256)

    tile, radius = (TILE, TILE_RADIUS) if framed else (QRectF(0, 0, 256, 256), 0)
    _background(p, tile, radius)
    clip = QPainterPath()
    clip.addRoundedRect(tile, radius, radius)
    p.save()
    p.setClipPath(clip)
    _back_hair(p)
    _body(p)
    _face(p)
    _eye(p, 104, mirror=True)  # the lash flick points away from the nose
    _eye(p, 152, mirror=False)
    _front_hair(p)
    p.restore()
    _cursor(p)

    if framed:
        p.setPen(QPen(QColor(150, 110, 220, 150), 3))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(TILE.adjusted(1.5, 1.5, -1.5, -1.5), TILE_RADIUS - 1, TILE_RADIUS - 1)
    p.end()
    return pm


def app_icon():
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(render_icon(size))
    return icon


def _png_bytes(size):
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    render_icon(size).save(buf, "PNG")
    buf.close()
    return bytes(data)


def _dib_bytes(size):
    """Classic 32-bit BMP entry: every Windows API (GDI included) can read it."""
    image = render_icon(size).toImage().convertToFormat(QImage.Format_ARGB32)
    stride = size * 4
    raw = bytes(image.constBits())[:image.bytesPerLine() * size]
    rows = [raw[y * image.bytesPerLine():y * image.bytesPerLine() + stride] for y in range(size)]
    pixels = b"".join(reversed(rows))  # BMP rows go bottom-up
    mask = b"\0" * (((size + 31) // 32) * 4 * size)  # alpha channel does the masking
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, len(pixels) + len(mask), 0, 0, 0, 0)
    return header + pixels + mask


def save_ico(path):
    """Write a multi-size .ico. Explorer picks the exact size it needs; a single
    256 px image makes it fall back to stale cached icons."""
    images = [(size, _png_bytes(size) if size >= 256 else _dib_bytes(size)) for size in ICON_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, blobs = b"", b""
    for size, png in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(blobs))
        blobs += png
    with open(path, "wb") as f:
        f.write(header + entries + blobs)
    return True
