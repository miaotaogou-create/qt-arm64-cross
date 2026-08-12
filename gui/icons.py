"""统一图标绘制：直线圆角对号等。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QWidget


def paint_straight_check(
    painter: QPainter,
    *,
    cx: float,
    cy: float,
    size: float,
    color: QColor | str,
    pen_width: float | None = None,
) -> None:
    """画参考图那种直线对号：短臂 + 长臂，圆角端点。"""
    s = float(size)
    pw = pen_width if pen_width is not None else max(1.6, s * 0.14)
    pen = QPen(QColor(color), pw)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    p1 = QPointF(cx - s * 0.28, cy + s * 0.02)
    p2 = QPointF(cx - s * 0.06, cy + s * 0.22)
    p3 = QPointF(cx + s * 0.30, cy - s * 0.24)
    painter.drawLine(p1, p2)
    painter.drawLine(p2, p3)


def _fg_from_stylesheet(ss: str, fallback: QColor) -> QColor:
    for part in (ss or "").replace("\n", ";").split(";"):
        part = part.strip()
        low = part.lower().replace(" ", "")
        if low.startswith("color:") and not low.startswith("color:transparent"):
            raw = part.split(":", 1)[1].strip().rstrip(";")
            c = QColor(raw)
            if c.isValid():
                return c
    return fallback


class CheckAwareLabel(QLabel):
    """普通 Label；setText('✓') 时画直线对号，背景/边框仍走样式表。"""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._as_check = False
        if text:
            self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802
        self._as_check = text == "✓"
        # 清空可见文字，避免字体 ✓；对号在 paintEvent 手绘
        super().setText("" if self._as_check else text)
        self.update()

    def text(self) -> str:  # noqa: N802
        return "✓" if self._as_check else super().text()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._as_check:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = _fg_from_stylesheet(
            self.styleSheet(),
            self.palette().color(self.foregroundRole()),
        )
        name = self.objectName()
        if name in ("ReadyPillCircleOk",) or "Ok" in name:
            if not self.styleSheet() or "color:" not in self.styleSheet().lower():
                color = QColor("#10b981")
        if name == "HeroCheckCircle":
            color = QColor("#14b8a6")
        s = min(self.width(), self.height()) * 0.55
        paint_straight_check(
            p,
            cx=self.width() / 2,
            cy=self.height() / 2,
            size=s,
            color=color,
            pen_width=max(1.6, min(self.width(), self.height()) * 0.12),
        )
        p.end()


class CircleCheckIcon(QWidget):
    """空心圆 + 直线对号。"""

    def __init__(
        self,
        size: int = 20,
        color: str = "#FFFFFF",
        *,
        circle: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)
        self._circle = circle
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        if self._circle:
            pen = QPen(self._color, max(1.5, w * 0.09))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            m = max(1, int(w * 0.08))
            p.drawEllipse(m, m, w - 2 * m, w - 2 * m)
        paint_straight_check(
            p,
            cx=w / 2,
            cy=w / 2,
            size=w * 0.62,
            color=self._color,
            pen_width=max(1.6, w * 0.11),
        )
        p.end()


class HardDriveIcon(QWidget):
    """交叉编译 / WSL 服务器机箱矢量图标（上梯形 + 下圆角盒 + 双指示灯）。"""

    def __init__(self, size: int = 24, color: str = "#06B6D4", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_color(self, color_hex: str) -> None:
        self._color = QColor(color_hex)
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pen_width = max(2.0, w / 12.0)
        pen = QPen(self._color, pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        m = pen_width / 2.0
        r = w * 0.18
        box_top_y = h * 0.45

        path = QPainterPath()
        path.moveTo(m + r, h - m)
        path.lineTo(w - m - r, h - m)
        path.quadTo(w - m, h - m, w - m, h - m - r)
        path.lineTo(w - m, box_top_y)
        path.lineTo(m, box_top_y)
        path.lineTo(m, h - m - r)
        path.quadTo(m, h - m, m + r, h - m)

        top_inset = w * 0.2
        top_y = m + h * 0.05
        path.moveTo(m, box_top_y)
        path.lineTo(top_inset, top_y)
        path.lineTo(w - top_inset, top_y)
        path.lineTo(w - m, box_top_y)
        painter.drawPath(path)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._color))
        dot_radius = pen_width * 0.75
        dot_y = box_top_y + (h - box_top_y) / 2.0
        for fx in (0.22, 0.42):
            dx = m + w * fx
            painter.drawEllipse(
                QRectF(dx - dot_radius, dot_y - dot_radius, dot_radius * 2, dot_radius * 2)
            )
        painter.end()
