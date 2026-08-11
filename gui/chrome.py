"""无边框窗口：深色标题条拖拽 / 缩放 / 最小化最大化关闭。"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from crosskit.app_version import VERSION
from gui.theme import C

_EDGE = 6


def make_ready_pill(text: str = "环境就绪", *, ok: bool = True) -> QFrame:
    """圆圈对号 + 文案的胶囊徽章（对齐设计稿）。"""
    pill = QFrame()
    pill.setObjectName("ReadyPillOk" if ok else "ReadyPillBad")
    lay = QHBoxLayout(pill)
    lay.setContentsMargins(7, 3, 10, 3)
    lay.setSpacing(6)
    circle = QLabel("✓" if ok else "!")
    circle.setObjectName("CheckCircleOk" if ok else "CheckCircleBad")
    circle.setFixedSize(15, 15)
    circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lab = QLabel(text)
    lab.setObjectName("ReadyPillTextOk" if ok else "ReadyPillTextBad")
    lay.addWidget(circle)
    lay.addWidget(lab)
    pill._circle = circle  # type: ignore[attr-defined]
    pill._label = lab  # type: ignore[attr-defined]
    return pill


def set_ready_pill(pill: QFrame, text: str, *, ok: bool) -> None:
    pill.setObjectName("ReadyPillOk" if ok else "ReadyPillBad")
    circle: QLabel = pill._circle  # type: ignore[attr-defined]
    lab: QLabel = pill._label  # type: ignore[attr-defined]
    circle.setText("✓" if ok else "!")
    circle.setObjectName("CheckCircleOk" if ok else "CheckCircleBad")
    lab.setText(text)
    lab.setObjectName("ReadyPillTextOk" if ok else "ReadyPillTextBad")
    for w in (pill, circle, lab):
        w.style().unpolish(w)
        w.style().polish(w)


class TitleChrome(QFrame):
    """AI Studio 风格：细标题条 + 主头栏。"""

    quick_compile = Signal()

    def __init__(self, window: QMainWindow) -> None:
        super().__init__()
        self._win = window
        self._drag_pos: QPoint | None = None
        self._maximized = False
        self._restore_geom = QRect()
        self.setObjectName("Chrome")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_titlebar())
        root.addWidget(self._build_mainbar())

    def _build_titlebar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(34)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 10, 0)
        lay.setSpacing(8)

        logo = QLabel("Qt")
        logo.setObjectName("TitleLogo")
        logo.setFixedSize(20, 20)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        name = QLabel("Qt ARM64 交叉编译助手")
        name.setObjectName("TitleAppName")
        lay.addWidget(name, 0, Qt.AlignmentFlag.AlignVCenter)

        ver = QLabel(f"v{VERSION} Modern")
        ver.setObjectName("TitleVerBadge")
        lay.addWidget(ver, 0, Qt.AlignmentFlag.AlignVCenter)

        lay.addStretch(1)

        self._center_dot = QLabel("●")
        self._center_dot.setObjectName("TitleDotWarn")
        self._center_dot.setFixedSize(8, 8)
        self._center_lbl = QLabel("环境检测中…")
        self._center_lbl.setObjectName("TitleCenter")
        self._center_sep = QLabel("|")
        self._center_sep.setObjectName("TitleCenterSep")
        self._center_tool = QLabel("")
        self._center_tool.setObjectName("TitleCenter")
        center = QHBoxLayout()
        center.setSpacing(6)
        center.addWidget(self._center_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        center.addWidget(self._center_lbl)
        center.addWidget(self._center_sep)
        center.addWidget(self._center_tool)
        lay.addLayout(center)
        lay.addStretch(1)

        self._btn_min = QPushButton("")
        self._btn_min.setObjectName("WinDot")
        self._btn_min.setFixedSize(12, 12)
        self._btn_min.setToolTip("最小化")
        self._btn_min.clicked.connect(self._win.showMinimized)
        self._btn_max = QPushButton("")
        self._btn_max.setObjectName("WinDot")
        self._btn_max.setFixedSize(12, 12)
        self._btn_max.setToolTip("最大化")
        self._btn_max.clicked.connect(self._toggle_max)
        self._btn_close = QPushButton("")
        self._btn_close.setObjectName("WinDotClose")
        self._btn_close.setFixedSize(12, 12)
        self._btn_close.setToolTip("关闭")
        self._btn_close.clicked.connect(self._win.close)
        for b in (self._btn_min, self._btn_max, self._btn_close):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            lay.addWidget(b)

        bar.mousePressEvent = self._title_press  # type: ignore[method-assign]
        bar.mouseMoveEvent = self._title_move  # type: ignore[method-assign]
        bar.mouseReleaseEvent = self._title_release  # type: ignore[method-assign]
        bar.mouseDoubleClickEvent = self._title_dbl  # type: ignore[method-assign]
        return bar

    def _build_mainbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("MainHeader")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(12)

        icon = QLabel("▣")
        icon.setObjectName("AppIcon")
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("Qt ARM64 交叉编译 Workstation")
        title.setObjectName("Title")
        row.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
        self._env_badge = make_ready_pill("检测中…", ok=False)
        row.addWidget(self._env_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        titles.addLayout(row)
        self._subtitle = QLabel("重构简化的 Windows 客户端 · 一键 WSL 交叉编译与板端 HTTP 快速分发")
        self._subtitle.setObjectName("Subtitle")
        titles.addWidget(self._subtitle)
        lay.addLayout(titles, 1)

        self._btn_quick = QPushButton(">_  一键极速编译")
        self._btn_quick.setObjectName("QuickPrimary")
        self._btn_quick.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_quick.clicked.connect(self.quick_compile.emit)
        lay.addWidget(self._btn_quick)

        self._busy_pill = QLabel("空闲")
        self._busy_pill.setObjectName("BusyPill")
        self._busy_pill.setVisible(False)
        lay.addWidget(self._busy_pill)
        return bar

    def set_env_ready(self, ready: bool, distro: str) -> None:
        if ready:
            set_ready_pill(self._env_badge, "环境就绪", ok=True)
            self._center_dot.setObjectName("TitleDotOk")
            self._center_lbl.setText(f"WSL2 {distro} 就绪")
            self._center_sep.setVisible(True)
            self._center_tool.setText("工具链: GCC 9.4.0 (aarch64)")
        else:
            set_ready_pill(self._env_badge, "环境未就绪", ok=False)
            self._center_dot.setObjectName("TitleDotWarn")
            self._center_lbl.setText("环境未就绪 — 请先导入环境包")
            self._center_sep.setVisible(False)
            self._center_tool.setText("")
        self._center_dot.style().unpolish(self._center_dot)
        self._center_dot.style().polish(self._center_dot)

    def set_busy_text(self, text: str, color: str | None = None) -> None:
        if not text or text in ("空闲", "就绪"):
            self._busy_pill.setVisible(False)
            self._btn_quick.setText(">_  一键极速编译")
            return
        self._busy_pill.setVisible(True)
        self._busy_pill.setText(text)
        c = color or C["warn"]
        self._busy_pill.setStyleSheet(
            f"color:{c}; background:rgba(30,41,59,0.9); border:1px solid {C['border']};"
            f"border-radius:10px; padding:4px 10px; font-weight:600; font-size:12px;"
        )
        if "编译" in text or "忙碌" in text:
            self._btn_quick.setText("编译进行中…")

    def set_quick_enabled(self, on: bool) -> None:
        self._btn_quick.setEnabled(on)

    def _toggle_max(self) -> None:
        if self._maximized:
            if self._restore_geom.isValid():
                self._win.setGeometry(self._restore_geom)
            self._maximized = False
            self._btn_max.setToolTip("最大化")
        else:
            self._restore_geom = self._win.geometry()
            screen = self._win.screen()
            if screen is not None:
                self._win.setGeometry(screen.availableGeometry())
            self._maximized = True
            self._btn_max.setToolTip("还原")

    def _title_press(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton and not self._maximized:
            self._drag_pos = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
        e.accept()

    def _title_move(self, e: QMouseEvent) -> None:
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton and not self._maximized:
            self._win.move(e.globalPosition().toPoint() - self._drag_pos)
        e.accept()

    def _title_release(self, e: QMouseEvent) -> None:
        self._drag_pos = None
        e.accept()

    def _title_dbl(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._toggle_max()
        e.accept()


class EdgeResizer:
    """无边框窗口边缘拖拽缩放。"""

    def __init__(self, window: QMainWindow) -> None:
        self._win = window
        self._edge: str | None = None
        self._origin = QPoint()
        self._geom = QRect()

    def hit(self, pos: QPoint) -> str | None:
        r = self._win.rect()
        x, y = pos.x(), pos.y()
        left = x <= _EDGE
        right = x >= r.width() - _EDGE
        top = y <= _EDGE
        bottom = y >= r.height() - _EDGE
        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        if left:
            return "l"
        if right:
            return "r"
        if top:
            return "t"
        if bottom:
            return "b"
        return None

    def press(self, e: QMouseEvent) -> bool:
        if e.button() != Qt.MouseButton.LeftButton:
            return False
        if getattr(self._win, "_chrome", None) is not None and getattr(self._win._chrome, "_maximized", False):
            return False
        edge = self.hit(e.position().toPoint())
        if edge is None:
            return False
        self._edge = edge
        self._origin = e.globalPosition().toPoint()
        self._geom = self._win.geometry()
        return True

    def move(self, e: QMouseEvent) -> bool:
        if self._edge is None:
            self._apply_cursor(self.hit(e.position().toPoint()))
            return False
        delta = e.globalPosition().toPoint() - self._origin
        g = QRect(self._geom)
        min_w, min_h = self._win.minimumWidth(), self._win.minimumHeight()
        edge = self._edge
        if "l" in edge:
            new_w = g.width() - delta.x()
            if new_w >= min_w:
                g.setX(g.x() + delta.x())
                g.setWidth(new_w)
        if "r" in edge:
            g.setWidth(max(min_w, self._geom.width() + delta.x()))
        if "t" in edge:
            new_h = g.height() - delta.y()
            if new_h >= min_h:
                g.setY(g.y() + delta.y())
                g.setHeight(new_h)
        if "b" in edge:
            g.setHeight(max(min_h, self._geom.height() + delta.y()))
        self._win.setGeometry(g)
        return True

    def release(self) -> None:
        self._edge = None

    def _apply_cursor(self, edge: str | None) -> None:
        cursors = {
            "l": Qt.CursorShape.SizeHorCursor,
            "r": Qt.CursorShape.SizeHorCursor,
            "t": Qt.CursorShape.SizeVerCursor,
            "b": Qt.CursorShape.SizeVerCursor,
            "tl": Qt.CursorShape.SizeFDiagCursor,
            "br": Qt.CursorShape.SizeFDiagCursor,
            "tr": Qt.CursorShape.SizeBDiagCursor,
            "bl": Qt.CursorShape.SizeBDiagCursor,
        }
        if edge is None:
            self._win.unsetCursor()
        else:
            self._win.setCursor(cursors[edge])
