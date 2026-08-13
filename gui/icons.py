"""统一图标绘制：直线圆角对号等。"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QLabel, QWidget


# Lucide 操作图标 SVG
_SVG_UPLOAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>'
    '<polyline points="17 8 12 3 7 8"></polyline>'
    '<line x1="12" y1="3" x2="12" y2="15"></line>'
    "</svg>"
)
_SVG_DOWNLOAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>'
    '<polyline points="7 10 12 15 17 10"></polyline>'
    '<line x1="12" y1="15" x2="12" y2="3"></line>'
    "</svg>"
)
_SVG_REFRESH = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M21 2v6h-6"></path>'
    '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"></path>'
    '<path d="M3 22v-6h6"></path>'
    '<path d="M21 12a9 9 0 0 1-15 6.7L3 16"></path>'
    "</svg>"
)


def make_svg_icon(kind: str, color: str = "#FFFFFF", size: int = 16) -> QIcon:
    """把 Lucide SVG 渲成 QIcon，供 QPushButton.setIcon 使用。"""
    tpl = {
        "upload": _SVG_UPLOAD,
        "download": _SVG_DOWNLOAD,
        "refresh": _SVG_REFRESH,
    }.get(kind, _SVG_UPLOAD)
    renderer = QSvgRenderer(tpl.format(color=color).encode("utf-8"))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p)
    p.end()
    return QIcon(pix)


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


class CpuIcon(QSvgWidget):
    """Lucide Cpu SVG 图标（工具链卡片）。"""

    _SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>'
        '<rect x="9" y="9" width="6" height="6"></rect>'
        '<line x1="9" y1="1" x2="9" y2="4"></line>'
        '<line x1="15" y1="1" x2="15" y2="4"></line>'
        '<line x1="9" y1="20" x2="9" y2="23"></line>'
        '<line x1="15" y1="20" x2="15" y2="23"></line>'
        '<line x1="1" y1="9" x2="4" y2="9"></line>'
        '<line x1="1" y1="15" x2="4" y2="15"></line>'
        '<line x1="20" y1="9" x2="23" y2="9"></line>'
        '<line x1="20" y1="15" x2="23" y2="15"></line>'
        "</svg>"
    )

    def __init__(self, size: int = 22, color: str = "#14B8A6", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._reload()

    def set_color(self, color_hex: str) -> None:
        self._color = color_hex
        self._reload()

    def _reload(self) -> None:
        self.load(self._SVG.format(color=self._color).encode("utf-8"))


class HeaderCpuLogo(QSvgWidget):
    """顶部 Header：绿底圆角 + 白色 CPU（Lucide）。"""

    _SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36" fill="none">'
        '<rect width="36" height="36" rx="10" ry="10" fill="{bg_color}" />'
        '<g transform="translate(6, 6)">'
        '<rect x="4" y="4" width="16" height="16" rx="2" ry="2" stroke="#FFFFFF" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" fill="none" />'
        '<rect x="9" y="9" width="6" height="6" stroke="#FFFFFF" stroke-width="2" fill="none" />'
        '<line x1="9" y1="1" x2="9" y2="4" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        '<line x1="15" y1="1" x2="15" y2="4" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        '<line x1="9" y1="20" x2="9" y2="23" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        '<line x1="15" y1="20" x2="15" y2="23" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        '<line x1="1" y1="9" x2="4" y2="9" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        '<line x1="1" y1="15" x2="4" y2="15" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        '<line x1="20" y1="9" x2="23" y2="9" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        '<line x1="20" y1="15" x2="23" y2="15" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />'
        "</g></svg>"
    )

    def __init__(self, size: int = 36, bg_color: str = "#0D9488", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._bg = bg_color
        self._reload()

    def set_bg_color(self, bg_color_hex: str) -> None:
        self._bg = bg_color_hex
        self._reload()

    def _reload(self) -> None:
        self.load(self._SVG.format(bg_color=self._bg).encode("utf-8"))


class SparklesIcon(QSvgWidget):
    """Lucide Sparkles SVG（从零搭建 / 极速编译）。"""

    _SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 '
        "9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 "
        '0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path>'
        '<path d="M20 3v4"></path>'
        '<path d="M22 5h-4"></path>'
        '<path d="M4 17v2"></path>'
        '<path d="M5 18H3"></path>'
        "</svg>"
    )

    def __init__(self, size: int = 20, color: str = "#F59E0B", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._reload()

    def set_color(self, color_hex: str) -> None:
        self._color = color_hex
        self._reload()

    def _reload(self) -> None:
        self.load(self._SVG.format(color=self._color).encode("utf-8"))


class ChevronArrow(QSvgWidget):
    """Lucide ChevronDown / ChevronUp。"""

    _DOWN = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="6 9 12 15 18 9"></polyline></svg>'
    )
    _UP = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="18 15 12 9 6 15"></polyline></svg>'
    )

    def __init__(
        self,
        direction: str = "down",
        color: str = "#94A3B8",
        size: int = 16,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._direction = direction
        self._color = color
        self._reload()

    def set_direction(self, direction: str) -> None:
        self._direction = direction
        self._reload()

    def set_color(self, color_hex: str) -> None:
        self._color = color_hex
        self._reload()

    def _reload(self) -> None:
        tpl = self._DOWN if self._direction == "down" else self._UP
        self.load(tpl.format(color=self._color).encode("utf-8"))


class ExternalLinkIcon(QSvgWidget):
    """Lucide ExternalLink 图标。"""

    _SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>'
        '<line x1="10" y1="14" x2="21" y2="3"></line>'
        '<polyline points="15 3 21 3 21 9"></polyline>'
        "</svg>"
    )

    def __init__(self, size: int = 16, color: str = "#FFFFFF", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._reload()

    def set_color(self, color_hex: str) -> None:
        self._color = color_hex
        self._reload()

    def _reload(self) -> None:
        self.load(self._SVG.format(color=self._color).encode("utf-8"))


class FolderIcon(QSvgWidget):
    """Lucide Folder 图标（WSL 路径输入框）。"""

    _SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2z"></path>'
        "</svg>"
    )

    def __init__(self, size: int = 18, color: str = "#F59E0B", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._reload()

    def set_color(self, color_hex: str) -> None:
        self._color = color_hex
        self._reload()

    def _reload(self) -> None:
        self.load(self._SVG.format(color=self._color).encode("utf-8"))
