"""统一图标绘制：直线圆角对号等。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtSvgWidgets import QSvgWidget
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


class HardDriveIcon(QSvgWidget):
    """Lucide HardDrive SVG 图标。"""

    _SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="2" y1="12" x2="22" y2="12"></line>'
        '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>'
        '<line x1="6" y1="16" x2="6.01" y2="16"></line>'
        '<line x1="10" y1="16" x2="10.01" y2="16"></line>'
        "</svg>"
    )

    def __init__(self, size: int = 24, color: str = "#06B6D4", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._reload()

    def set_color(self, color_hex: str) -> None:
        self._color = color_hex
        self._reload()

    def _reload(self) -> None:
        self.load(self._SVG.format(color=self._color).encode("utf-8"))
