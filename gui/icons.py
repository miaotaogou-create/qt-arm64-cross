"""统一图标绘制：直线圆角对号等。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
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
    """硬盘/机箱线框图标（对齐设计稿 HardDrive）。"""

    def __init__(self, size: int = 24, color: str = "#14b8a6", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        pen = QPen(self._color, max(1.8, s * 0.09))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        m = s * 0.16
        p.drawRoundedRect(QRectF(m, s * 0.28, s - 2 * m, s * 0.48), 2.5, 2.5)
        p.drawLine(QPointF(s * 0.28, s * 0.28), QPointF(s * 0.22, s * 0.16))
        p.drawLine(QPointF(s * 0.22, s * 0.16), QPointF(s * 0.78, s * 0.16))
        p.drawLine(QPointF(s * 0.78, s * 0.16), QPointF(s * 0.72, s * 0.28))
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        r = max(1.2, s * 0.05)
        p.drawEllipse(QPointF(s * 0.38, s * 0.52), r, r)
        p.drawEllipse(QPointF(s * 0.52, s * 0.52), r, r)
        p.end()
