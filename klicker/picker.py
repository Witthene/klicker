"""Full-screen overlay for choosing click points on any monitor."""

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import theme, winapi
from .widgets import paint_glass


class PointPicker(QObject):
    picked = Signal(int, int)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._overlays = []

    def start(self):
        self._overlays = [_Overlay(screen, self) for screen in QGuiApplication.screens()]
        for overlay in self._overlays:
            overlay.show()
        under_cursor = QGuiApplication.screenAt(QCursor.pos())
        for overlay in self._overlays:
            if overlay.screen() is under_cursor or under_cursor is None:
                overlay.activateWindow()
                overlay.setFocus()
                break

    def _close_all(self):
        for overlay in self._overlays:
            overlay.close()
            overlay.deleteLater()
        self._overlays = []

    def finish(self, point):
        self._close_all()
        if point is None:
            self.cancelled.emit()
        else:
            self.picked.emit(*point)


class _Overlay(QWidget):
    def __init__(self, screen, picker):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self._picker = picker
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def mouseMoveEvent(self, event):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._picker.finish(winapi.get_cursor_pos())  # physical pixels, as SetCursorPos expects
        else:
            self._picker.finish(None)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._picker.finish(None)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal = theme.palette()
        p.fillRect(self.rect(), QColor(8, 10, 18, 70))

        hint = "Clique onde deseja automatizar  ·  Esc ou botão direito para cancelar"
        font = QFont(self.font())
        font.setPixelSize(14)
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        width = p.fontMetrics().horizontalAdvance(hint) + 40
        pill = QRectF((self.width() - width) / 2, 28, width, 40)
        paint_glass(p, pill, 20, pal.window_solid, pal.window_solid,
                    pal.card_border_top, pal.card_border_bottom, pal.sheen)
        p.setPen(pal.text)
        p.drawText(pill, Qt.AlignCenter, hint)

        local = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(local):
            return
        x, y = local.x() + 0.5, local.y() + 0.5
        p.setPen(QPen(_alpha(pal.accent, 170), 1))
        p.drawLine(QPointF(0, y), QPointF(self.width(), y))
        p.drawLine(QPointF(x, 0), QPointF(x, self.height()))
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setBrush(_alpha(pal.accent, 90))
        p.drawEllipse(QPointF(x, y), 11, 11)

        gx, gy = winapi.get_cursor_pos()
        label = f"X {gx}   Y {gy}"
        bubble = QRectF(x + 18, y + 18, p.fontMetrics().horizontalAdvance(label) + 24, 30)
        if bubble.right() > self.width():
            bubble.moveRight(x - 18)
        if bubble.bottom() > self.height():
            bubble.moveBottom(y - 18)
        paint_glass(p, bubble, 15, pal.window_solid, pal.window_solid,
                    pal.card_border_top, pal.card_border_bottom)
        p.setPen(pal.text)
        p.drawText(bubble, Qt.AlignCenter, label)


def _alpha(color, alpha):
    c = QColor(color)
    c.setAlpha(alpha)
    return c
