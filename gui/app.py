"""主界面：环境管理、交叉编译、HTTP 共享、日志（PySide6）。"""
from __future__ import annotations

import os
import threading
import webbrowser
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QTimer,
    Signal,
    QEvent,
    QObject,
    QRectF,
    QSize,
    QVariantAnimation,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QEasingCurve,
    QPoint,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QButtonGroup,
)

from gui.icons import (
    CheckAwareLabel,
    CircleCheckIcon,
    ChevronArrow,
    ExternalLinkIcon,
    FileCodeIcon,
    SparklesIcon,
    TerminalIcon,
    make_svg_icon,
)


class RecentCombo(QComboBox):
    """关闭时保持矮；弹出列表按条数加高加宽，避免只露出一行还带滚动箭头。"""

    _ROW_H = 30
    _MAX_ROWS = 10

    def showPopup(self) -> None:
        n = max(1, min(self.count(), self._MAX_ROWS))
        self.setMaxVisibleItems(n)
        view = self.view()
        view.setMinimumHeight(n * self._ROW_H)
        w = max(340, self.width() + 100)
        view.setMinimumWidth(w)
        super().showPopup()

        def _fit() -> None:
            popup = view.window()
            if popup is None or popup is self.window():
                return
            popup.setMinimumWidth(w)
            popup.resize(max(popup.width(), w), max(popup.height(), n * self._ROW_H + 10))

        QTimer.singleShot(0, _fit)


class HeroPillBtn(QFrame):
    """圆角矩形操作钮：手绘圆角底，避免 QFrame QSS radius 在 Windows 不生效。"""

    clicked = Signal()

    def __init__(self, object_name: str = "HeroGhost", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._hover = False
        self._primary = object_name == "HeroPrimary"
        self._radius = 8  # 圆角矩形（非胶囊）
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(14, 0, 16, 0)
        self._lay.setSpacing(6)

    def add_content(self, *widgets: QWidget) -> None:
        for w in widgets:
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._lay.addWidget(w)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802
        if event.type() == QEvent.Type.EnabledChange:
            self.update()
        super().changeEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if not self.isEnabled():
            bg, bd = QColor("#111827"), QColor(C["border"])
        elif self._primary:
            bg = QColor(C["primary_hover"] if self._hover else C["primary"])
            bd = QColor("#2DD4BF" if self._hover else C["accent"])
        else:
            bg = QColor(C["border_input"] if self._hover else C["surface2"])
            bd = QColor("#4B5563" if self._hover else C["border_input"])
        p.setPen(QPen(bd, 1.0))
        p.setBrush(bg)
        p.drawRoundedRect(r, self._radius, self._radius)
        p.end()


class _RotatingArrowIcon(QWidget):
    """双向环形箭头旋转图标（QPainter 绘制）。"""

    def __init__(self, size: int = 20, color: str = "#14b8a6", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)
        self._angle = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(360.0)
        self._anim.setDuration(1000)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._on_angle)

    def _on_angle(self, v: float) -> None:
        self._angle = v
        self.update()

    def start(self) -> None:
        if self._anim.state() != QVariantAnimation.State.Running:
            self._anim.start()

    def stop(self) -> None:
        self._anim.stop()
        self._angle = 0.0
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        p.translate(w / 2, w / 2)
        p.rotate(self._angle)
        pw = max(2, int(w / 10))
        pen = QPen(self._color, pw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        r = (w - pw * 2) / 2
        rect = QRectF(-r, -r, r * 2, r * 2)
        p.drawArc(rect, int(30 * 16), int(120 * 16))
        p.drawArc(rect, int(210 * 16), int(120 * 16))
        p.setBrush(self._color)
        a1 = QPainterPath()
        a1.moveTo(r * 0.7, -r * 0.6)
        a1.lineTo(r * 1.1, -r * 0.1)
        a1.lineTo(r * 0.4, -r * 0.1)
        a1.closeSubpath()
        p.drawPath(a1)
        a2 = QPainterPath()
        a2.moveTo(-r * 0.7, r * 0.6)
        a2.lineTo(-r * 1.1, r * 0.1)
        a2.lineTo(-r * 0.4, r * 0.1)
        a2.closeSubpath()
        p.drawPath(a2)
        p.end()


class ToastNotification(QWidget):
    """实心绿色 toast：持续上下弹跳，到时后淡出关闭。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        text: str = "环境全面检测完成：aarch64 交叉编译器与 Qt 库正常！",
        duration: int = 3000,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.duration = duration
        self._base_y = 0
        self._init_ui(text)
        self._init_animations()

    def _init_ui(self, text: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 20, 10)
        layout.setSpacing(10)
        layout.addWidget(CircleCheckIcon(20, "#FFFFFF", circle=True, parent=self))
        text_label = QLabel(text)
        font = QFont("Microsoft YaHei", 9)
        font.setBold(True)
        text_label.setFont(font)
        text_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        layout.addWidget(text_label)
        self.adjustSize()

    def paintEvent(self, _e) -> None:  # noqa: N802
        # WA_TranslucentBackground 下样式表背景常不生效，手动画圆角绿底
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#059669"))
        p.drawRoundedRect(self.rect(), 12, 12)
        p.end()

    def _init_animations(self) -> None:
        self._anim_up = QPropertyAnimation(self, b"pos", self)
        self._anim_up.setDuration(350)
        self._anim_up.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim_down = QPropertyAnimation(self, b"pos", self)
        self._anim_down.setDuration(350)
        self._anim_down.setEasingCurve(QEasingCurve.Type.InQuad)
        self._bounce_group = QSequentialAnimationGroup(self)
        self._bounce_group.addAnimation(self._anim_up)
        self._bounce_group.addAnimation(self._anim_down)
        self._bounce_group.setLoopCount(-1)

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)
        self._fade_out = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_out.setDuration(400)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.finished.connect(self.close)

    def show_toast(self, parent_widget: QWidget) -> None:
        # Tool 窗口用全局坐标，贴主窗口右下角
        br = parent_widget.mapToGlobal(parent_widget.rect().bottomRight())
        x = br.x() - self.width() - 24
        y = br.y() - self.height() - 24
        self._base_y = y
        self.move(x, y)
        self._anim_up.setStartValue(QPoint(x, self._base_y))
        self._anim_up.setEndValue(QPoint(x, self._base_y - 12))
        self._anim_down.setStartValue(QPoint(x, self._base_y - 12))
        self._anim_down.setEndValue(QPoint(x, self._base_y))
        self.show()
        self.raise_()
        self._bounce_group.start()
        QTimer.singleShot(self.duration, self.dismiss)

    def dismiss(self) -> None:
        self._bounce_group.stop()
        self._fade_out.start()


from crosskit import build as buildmod
from crosskit import detect, envpack, jobs, netip, settings, wsl, wsl_setup
from crosskit.httpshare import DirectoryShare, ensure_firewall_allow, ethernet_ipv4, guess_share_dir
from gui.adv_panel import AdvancedOptionsPanel
from gui.chrome import EdgeResizer, TitleChrome, make_ready_pill, set_ready_pill
from gui.share_btn import GoShareButton
from gui.env_panel import (
    build_preset_row,
    build_toolchain_specs,
    card_header,
    form_label,
    hline,
    PathInputField,
)
from gui.theme import C, apply_theme

ENV_RELEASE_URL = "https://github.com/miaotaogou-create/qt-arm64-cross/releases/tag/env-ubuntu-20.04"


def _field_label(text: str, width: int = 76) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("FieldLabel")
    lb.setFixedWidth(width)
    lb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return lb


def _card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(8)
    if title:
        t = QLabel(title)
        t.setObjectName("CardTitle")
        lay.addWidget(t)
    return frame, lay


def _btn(text: str, kind: str = "Ghost") -> QPushButton:
    b = QPushButton(text)
    b.setObjectName(kind)  # Primary / Accent / Ghost
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _scroll_page() -> tuple[QWidget, QVBoxLayout]:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(12, 8, 12, 8)
    lay.setSpacing(10)
    area.setWidget(inner)
    wrap = QWidget()
    wl = QVBoxLayout(wrap)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.addWidget(area)
    return wrap, lay


class MainWindow(QMainWindow):
    sig_log = Signal(str)
    sig_busy_done = Signal(object)  # callable，在 UI 线程执行

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Qt ARM64 交叉编译工具")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.resize(1080, 760)
        self.setMinimumSize(900, 600)
        self._chrome: TitleChrome | None = None
        self._resizer = EdgeResizer(self)

        self._busy = False
        self._env_ready = False
        self._action_btns: list[QWidget] = []
        self._busy_keep: set[int] = set()
        self._form_widgets: list[QWidget] = []
        self._share = DirectoryShare()
        self._advanced_open = False
        self._eth_open = False
        self._scratch_open = False
        self._cfg = settings.load()
        self._env_banner_labels: list[QLabel] = []
        self._env_hint_lbl: QLabel | None = None
        self._share_log: QTextEdit | None = None
        self._btn_cancel: QPushButton | None = None
        self._recent_log_lines: list[str] = []
        self._btn_download: QPushButton | None = None
        self._pulse_timer: QTimer | None = None
        self._pulse_base = ""
        self._pulse_n = 0
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.timeout.connect(self._persist)
        self._log_auto_scroll = True
        self._log_line_count = 0
        self._current_step = 0

        # —— 配置字段 ——
        default_env = self._cfg.get("env_install_dir") or str(
            Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "WSL" / "Ubuntu-20.04"
        )
        self._project = self._cfg.get("project", "") or ""
        self._build_file = self._cfg.get("build_file", "") or ""
        self._build_system = self._cfg.get("build_system", "auto") or "auto"
        self._app_name = self._cfg.get("app_name", "") or ""
        self._out_dir = self._cfg.get("out_dir", "") or ""
        self._out_bin = self._cfg.get("out_bin", "") or ""
        self._jobs_n = int(self._cfg.get("jobs") or 0)
        self._do_bundle = bool(self._cfg.get("do_bundle", True))
        self._do_clean = bool(self._cfg.get("do_clean", False))
        self._use_ffmpeg = bool(self._cfg.get("use_ffmpeg", False))
        self._build_mode = (self._cfg.get("build_mode") or "release").lower()
        if self._build_mode not in ("release", "debug"):
            self._build_mode = "release"
        self._use_ccache = bool(self._cfg.get("use_ccache", True))
        self._plugins = self._cfg.get("plugins", "") or ""
        self._extra_pkg = self._cfg.get("extra_pkgconfig", "") or ""
        self._extra_copy = self._cfg.get("extra_copy", "") or ""
        self._distro = self._cfg.get("distro", wsl.DEFAULT_DISTRO) or wsl.DEFAULT_DISTRO
        self._share_dir = self._cfg.get("share_dir", "") or ""
        self._share_port = int(self._cfg.get("share_port") or 18080)
        self._eth_add_ip = self._cfg.get("eth_add_ip", "") or ""
        self._eth_add_mask = self._cfg.get("eth_add_mask") or "255.255.255.0"
        self._env_install_dir = default_env
        self._env_slim = bool(self._cfg.get("env_slim_export", False))
        self._env_replace = bool(self._cfg.get("env_replace_on_import", False))

        self.sig_log.connect(self._append_log)
        self.sig_busy_done.connect(self._run_on_ui)

        self._build_ui()
        if self._project:
            self._refresh_build_files()
        if not self._share_dir:
            self._fill_share_from_project()
        self._set_http_dot(False)

        # 记住上次检测结果：已就绪则直达交叉编译页，不再每次启动跑 WSL 检测
        remembered = bool(self._cfg.get("env_ready", False))
        self._apply_env_ready(remembered)
        if remembered:
            self._select_step(1)

        QTimer.singleShot(600, self._maybe_resume_pending_import)
        QTimer.singleShot(200, self._refresh_eth_list)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        self._chrome = TitleChrome(self)
        self._chrome.quick_compile.connect(self._on_quick_compile)
        root_lay.addWidget(self._chrome)
        root_lay.addWidget(self._build_step_nav())
        self._stack = QStackedWidget()
        root_lay.addWidget(self._stack, 1)

        page_env, env_lay = _scroll_page()
        self._build_tab_env(env_lay)
        env_lay.addStretch(1)
        self._stack.addWidget(page_env)

        page_compile, compile_lay = _scroll_page()
        compile_lay.setContentsMargins(16, 12, 16, 8)
        compile_lay.setSpacing(16)
        self._build_tab_compile(compile_lay)
        self._stack.addWidget(page_compile)

        page_share, share_lay = _scroll_page()
        self._build_tab_share(share_lay)
        share_lay.addStretch(1)
        self._stack.addWidget(page_share)

        self._build_footer(root_lay)
        self._select_step(0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._resizer.press(event):
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._resizer.move(event):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._resizer.release()
        super().mouseReleaseEvent(event)

    def _on_quick_compile(self) -> None:
        self._select_step(1)
        if self._busy:
            return
        self._on_build()

    def _build_step_nav(self) -> QWidget:
        wrap = QFrame()
        wrap.setObjectName("StepNavBar")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(6)
        self._step_cards: list[QFrame] = []
        self._step_num_lbls: list[CheckAwareLabel] = []
        specs = [
            ("1", "环境管理", "WSL2 交叉编译链检测与配置"),
            ("2", "交叉编译", "Qt工程加载、参数设定与构建日志"),
            ("3", "部署与共享", "HTTP 文件极速分发与多网卡 IP"),
        ]
        for i, (num, name, desc) in enumerate(specs):
            card = QFrame()
            card.setObjectName("StepIdle")
            card.setFrameShape(QFrame.Shape.NoFrame)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setMinimumHeight(56)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(12, 8, 10, 8)
            cl.setSpacing(10)
            badge = CheckAwareLabel(num)
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background:#1e293b; color:#64748b; border:none; border-radius:8px; font-weight:700; font-size:11px;"
            )
            self._step_num_lbls.append(badge)
            texts = QVBoxLayout()
            texts.setSpacing(1)
            texts.setContentsMargins(0, 0, 0, 0)
            n = QLabel(name)
            n.setObjectName("StepTitle")
            d = QLabel(desc)
            d.setObjectName("StepDesc")
            texts.addWidget(n)
            texts.addWidget(d)
            cl.addWidget(badge)
            cl.addLayout(texts, 1)
            if i < len(specs) - 1:
                chev = QLabel("›")
                chev.setObjectName("StepChevron")
                chev.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                cl.addWidget(chev)
            card.mousePressEvent = lambda _e, idx=i: self._select_step(idx)  # type: ignore[method-assign]
            lay.addWidget(card, 1)
            self._step_cards.append(card)

        lay.addStretch(1)

        flow = QFrame()
        flow.setObjectName("FlowHintBox")
        flow.setFrameShape(QFrame.Shape.NoFrame)
        flow.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        fl = QHBoxLayout(flow)
        fl.setContentsMargins(12, 6, 12, 6)
        fl.setSpacing(6)
        self._flow_hint_key = QLabel("当前流程状态：")
        self._flow_hint_key.setObjectName("FlowHintKey")
        self._flow_hint_val = QLabel("检测环境…")
        self._flow_hint_val.setObjectName("FlowHintVal")
        self._flow_hint_val.setWordWrap(False)
        fl.addWidget(self._flow_hint_key)
        fl.addWidget(self._flow_hint_val)
        self._flow_hint = flow  # 兼容 hasattr 检查
        lay.addWidget(flow, 0, Qt.AlignmentFlag.AlignVCenter)
        return wrap

    def _refresh_flow_hint(self) -> None:
        if not hasattr(self, "_flow_hint_val"):
            return
        if self._current_step == 0:
            tip = "已完成 WSL 工具链预检 → 随时可编译" if self._env_ready else "请先导入 / 检测环境包"
        elif self._current_step == 1:
            tip = "工程已装载 → 点击开始交叉编译"
        else:
            tip = "HTTP 共享运行中" if self._share.running else "服务器就绪，一键启动板端共享"
        self._flow_hint_val.setText(tip)

    def _select_step(self, idx: int) -> None:
        self._current_step = idx
        self._stack.setCurrentIndex(idx)
        for i, card in enumerate(self._step_cards):
            active = i == idx
            card.setObjectName("StepActive" if active else "StepIdle")
            card.style().unpolish(card)
            card.style().polish(card)
            badge = self._step_num_lbls[i]
            if active:
                badge.setText(str(i + 1))
                badge.setStyleSheet(
                    "background:#14b8a6; color:white; border:none; border-radius:8px; font-weight:700; font-size:11px;"
                )
            elif self._env_ready and i == 0:
                badge.setText("✓")
                badge.setStyleSheet(
                    "background:rgba(16,185,129,0.2); color:#34d399; border:none; border-radius:8px; font-weight:700; font-size:12px;"
                )
            else:
                badge.setText(str(i + 1))
                badge.setStyleSheet(
                    "background:#1e293b; color:#64748b; border:none; border-radius:8px; font-weight:700; font-size:11px;"
                )
        self._refresh_flow_hint()

    def _build_footer(self, parent_lay: QVBoxLayout) -> None:
        foot = QFrame()
        foot.setObjectName("AppFooter")
        foot.setFixedHeight(38)
        lay = QHBoxLayout(foot)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        brand = QLabel("Qt ARM64 交叉编译 Workstation")
        brand.setObjectName("FooterBrand")
        lay.addWidget(brand)

        lay.addStretch(1)

        self._activity_lbl = QLabel("")
        self._activity_lbl.setObjectName("FooterMuted")
        self._activity_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._activity_lbl.setMaximumWidth(420)
        lay.addWidget(self._activity_lbl)

        self._btn_cancel = QPushButton("取消任务")
        self._btn_cancel.setObjectName("FooterCancel")
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.setVisible(False)
        lay.addWidget(self._btn_cancel)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(96)
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        lay.addWidget(self._progress, 0, Qt.AlignmentFlag.AlignVCenter)

        sep = QLabel("|")
        sep.setObjectName("FooterSep")
        lay.addWidget(sep)

        self._status_lbl = QLabel("就绪")
        self._status_lbl.setObjectName("FooterMuted")
        lay.addWidget(self._status_lbl)

        sep2 = QLabel("|")
        sep2.setObjectName("FooterSep")
        lay.addWidget(sep2)

        self._footer_wsl = QLabel("WSL2 检测中…")
        self._footer_wsl.setObjectName("FooterWsl")
        lay.addWidget(self._footer_wsl)

        parent_lay.addWidget(foot)

    def _build_tab_env(self, lay: QVBoxLayout) -> None:
        hero = QFrame()
        hero.setObjectName("HeroBannerBad")
        self._env_hero = hero
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(14)

        icon = QFrame()
        icon.setFixedSize(44, 44)
        icon.setObjectName("HeroIconBad")
        self._env_hero_icon = icon
        il = QHBoxLayout(icon)
        il.setContentsMargins(0, 0, 0, 0)
        mark = CheckAwareLabel("!")
        mark.setObjectName("HeroWarnMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._env_hero_mark = mark
        il.addWidget(mark)
        hl.addWidget(icon)

        mid = QVBoxLayout()
        mid.setSpacing(4)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("本机 WSL2 交叉编译环境状态")
        title.setObjectName("HeroTitle")
        title_row.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
        self._env_hero_badge = make_ready_pill("检测中…", ok=False, show_check=False)
        title_row.addWidget(self._env_hero_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        mid.addLayout(title_row)
        ban = QLabel("正在检测交叉环境…")
        ban.setWordWrap(True)
        ban.setObjectName("HeroDesc")
        mid.addWidget(ban)
        self._env_banner_labels.append(ban)
        self._env_hint_lbl = QLabel("")
        self._env_hint_lbl.setObjectName("HeroDesc")
        self._env_hint_lbl.setWordWrap(True)
        mid.addWidget(self._env_hint_lbl)
        hl.addLayout(mid, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        det_wrap = HeroPillBtn("HeroGhost")
        det_wrap.clicked.connect(self._on_detect)
        self._track_action(det_wrap)
        self._detect_icon = _RotatingArrowIcon(14, "#14b8a6")
        self._detect_label = QLabel("重新检测环境")
        self._detect_label.setStyleSheet(
            "background:transparent; border:none; color:#E2E8F0; font-size:12px; font-weight:500;"
        )
        det_wrap.add_content(self._detect_icon, self._detect_label)
        actions.addWidget(det_wrap)
        self._btn_redetect = det_wrap

        self._btn_go_compile = HeroPillBtn("HeroPrimary")
        self._go_text = QLabel("前往「2 交叉编译」")
        self._go_text.setStyleSheet(
            "background:transparent; border:none; color:#FFFFFF; font-size:12px; font-weight:600;"
        )
        self._go_icon = ExternalLinkIcon(size=12, color="#FFFFFF")
        self._btn_go_compile.add_content(self._go_text, self._go_icon)
        self._btn_go_compile.clicked.connect(lambda: self._select_step(1))
        self._btn_go_compile.setEnabled(False)
        actions.addWidget(self._btn_go_compile)
        self._sync_go_compile_btn_style()
        hl.addLayout(actions)
        self._refresh_env_hint()
        lay.addWidget(hero)

        body_host = QWidget()
        self._env_cols_host = body_host
        self._env_cols_mode: str | None = None
        self._env_left_col = QWidget()
        self._env_right_col = QWidget()
        left = QVBoxLayout(self._env_left_col)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)
        right = QVBoxLayout(self._env_right_col)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)

        # —— 左：交叉编译环境包（对齐参考卡片）——
        envp = QFrame()
        envp.setObjectName("Card")
        env_lay = QVBoxLayout(envp)
        env_lay.setContentsMargins(24, 20, 24, 20)
        env_lay.setSpacing(18)
        env_lay.addWidget(card_header("▣", "交叉编译环境包 (WSL Distro)", "Windows Subsystem for Linux"))

        sec1 = QVBoxLayout()
        sec1.setSpacing(10)
        sec1.addWidget(form_label("快捷选择预设发行版 (Distro Presets)"))
        preset_row, self._preset_cards = build_preset_row(self._on_preset_picked)
        self._preset_host = preset_row
        sec1.addWidget(preset_row)
        env_lay.addLayout(sec1)
        self._sync_preset_selection(self._distro_text())

        sec2 = QVBoxLayout()
        sec2.setSpacing(6)
        sec2.addWidget(form_label("WSL 安装目录 (Install Path)"))
        row0 = QHBoxLayout()
        row0.setSpacing(10)
        self._env_path_field = PathInputField(
            self._env_install_dir,
            placeholder=r"C:\Users\...\AppData\Local\WSL\Ubuntu-20.04",
        )
        self.ed_env_install = self._env_path_field.ed
        self._env_path_field.textChanged.connect(lambda t: self._on_field("env_install", t))
        self._track_form(self.ed_env_install)
        row0.addWidget(self._env_path_field, 1)
        b_br = QPushButton("浏览...")
        b_br.setObjectName("EnvGhost")
        b_br.setCursor(Qt.CursorShape.PointingHandCursor)
        b_br.clicked.connect(self._browse_env_install)
        row0.addWidget(b_br)
        sec2.addLayout(row0)
        env_lay.addLayout(sec2)

        sec3 = QVBoxLayout()
        sec3.setSpacing(6)
        sec3.addWidget(form_label("发行版注册标识 (Distro Name)"))
        row1 = QHBoxLayout()
        row1.setSpacing(14)
        self.ed_distro = QLineEdit(self._distro)
        self.ed_distro.setObjectName("PathEdit")
        self.ed_distro.textChanged.connect(self._on_distro_edited)
        self._track_form(self.ed_distro)
        row1.addWidget(self.ed_distro, 1)
        hint = QLabel("提示: 默认保持为 Ubuntu-20.04")
        hint.setObjectName("Muted")
        row1.addWidget(hint)
        sec3.addLayout(row1)
        env_lay.addLayout(sec3)

        div2 = hline()
        env_lay.addWidget(div2)

        opts = QHBoxLayout()
        opts.setSpacing(20)
        self.chk_env_slim = QCheckBox("导出环境包时自动清除 Qt 源码构建缓存")
        self.chk_env_slim.setChecked(self._env_slim)
        self.chk_env_slim.toggled.connect(lambda v: self._on_field("env_slim", v))
        self._track_form(self.chk_env_slim)
        opts.addWidget(self.chk_env_slim)
        self.chk_env_replace = QCheckBox("覆盖已有同名发行版")
        self.chk_env_replace.setChecked(self._env_replace)
        self.chk_env_replace.toggled.connect(lambda v: self._on_field("env_replace", v))
        self._track_form(self.chk_env_replace)
        opts.addWidget(self.chk_env_replace)
        opts.addStretch(1)
        env_lay.addLayout(opts)

        brow = QHBoxLayout()
        brow.setSpacing(12)
        b_imp = QPushButton("一键导入环境包 (.tar.gz)")
        b_imp.setObjectName("EnvPrimary")
        b_imp.setIcon(make_svg_icon("upload", "#FFFFFF", 16))
        b_imp.setIconSize(QSize(16, 16))
        b_imp.setCursor(Qt.CursorShape.PointingHandCursor)
        b_imp.clicked.connect(self._on_import_env)
        self._track_action(b_imp)
        brow.addWidget(b_imp)
        self._btn_download = QPushButton("下载预制环境包")
        self._btn_download.setObjectName("EnvAccent")
        self._btn_download.setIcon(make_svg_icon("download", "#14B8A6", 16))
        self._btn_download.setIconSize(QSize(16, 16))
        self._btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_download.clicked.connect(self._open_env_release)
        brow.addWidget(self._btn_download)
        b_det = QPushButton("检测环境")
        b_det.setObjectName("EnvGhost")
        b_det.setIcon(make_svg_icon("refresh", "#0D9488", 16))
        b_det.setIconSize(QSize(16, 16))
        b_det.setCursor(Qt.CursorShape.PointingHandCursor)
        b_det.clicked.connect(lambda: self._on_detect())
        self._track_action(b_det)
        brow.addWidget(b_det)
        b_exp = QPushButton("导出环境...")
        b_exp.setObjectName("EnvGhost")
        b_exp.setIcon(make_svg_icon("upload", "#E5E7EB", 16))
        b_exp.setIconSize(QSize(16, 16))
        b_exp.setCursor(Qt.CursorShape.PointingHandCursor)
        b_exp.clicked.connect(self._on_export_env)
        self._track_action(b_exp)
        brow.addWidget(b_exp)
        brow.addStretch(1)
        env_lay.addLayout(brow)
        left.addWidget(envp)

        # —— 右：工具链明细 + 从零搭建 + 检测结果 ——
        right.addWidget(build_toolchain_specs())

        scratch = QFrame()
        scratch.setObjectName("ScratchCard")
        sc_outer = QVBoxLayout(scratch)
        sc_outer.setContentsMargins(16, 14, 16, 14)
        sc_outer.setSpacing(10)

        # 整行可点：星标 + 标题 + 箭头
        head = QFrame()
        head.setObjectName("ScratchHeader")
        head.setCursor(Qt.CursorShape.PointingHandCursor)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        self._scratch_icon = SparklesIcon(16, "#F59E0B")
        self._scratch_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        hl.addWidget(self._scratch_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        self._scratch_title = QLabel("无现有环境包？从零搭建向导")
        self._scratch_title.setObjectName("ScratchTitle")
        self._scratch_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        hl.addWidget(self._scratch_title, 1, Qt.AlignmentFlag.AlignVCenter)
        self._scratch_arrow = ChevronArrow(direction="down", color="#94A3B8", size=16)
        self._scratch_arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        hl.addWidget(self._scratch_arrow, 0, Qt.AlignmentFlag.AlignVCenter)
        head.mousePressEvent = self._on_scratch_header_press  # type: ignore[method-assign]
        sc_outer.addWidget(head)

        tip2 = QLabel("无需现成环境包，系统将自动配置全新 WSL Ubuntu 实例并自动编译 Qt 5.14.2 ARM64 工具链。")
        tip2.setObjectName("ScratchDesc")
        tip2.setWordWrap(True)
        sc_outer.addWidget(tip2)

        self._scratch = QWidget()
        self._scratch.setVisible(False)
        sc_lay = QVBoxLayout(self._scratch)
        sc_lay.setContentsMargins(0, 4, 0, 0)
        sc_lay.setSpacing(8)
        scratch_btns: list[QPushButton] = []
        for title, sub, script, btn_text in (
            ("步骤 1: 安装 aarch64 基础工具链", "gcc-aarch64-linux-gnu, g++-aarch64", "setup_cross_focal.sh", "安装工具链"),
            ("步骤 2: 自动编译 Qt 5.14.2 ARM64", "交叉编译 Qt5 源码并配置 mkspecs", "build_qt5142_arm64_cross.sh", "编译 Qt 5.14.2"),
        ):
            step = QFrame()
            step.setObjectName("PresetCard")
            sl = QHBoxLayout(step)
            sl.setContentsMargins(12, 10, 12, 10)
            texts = QVBoxLayout()
            t1 = QLabel(title)
            t1.setObjectName("PresetTitle")
            t2 = QLabel(sub)
            t2.setObjectName("PresetMeta")
            texts.addWidget(t1)
            texts.addWidget(t2)
            sl.addLayout(texts, 1)
            b = QPushButton(btn_text)
            b.setObjectName("EnvGhost")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, s=script: self._on_install(s))
            self._track_action(b)
            scratch_btns.append(b)
            sl.addWidget(b)
            sc_lay.addWidget(step)
        # 两按钮等宽：按较长文案统一最小宽度
        if scratch_btns:
            mw = max(b.sizeHint().width() for b in scratch_btns)
            for b in scratch_btns:
                b.setMinimumWidth(mw)
        sc_outer.addWidget(self._scratch)
        right.addWidget(scratch)

        # ponytail: env_box 保留为隐藏 dummy，避免 _set_env_box 崩溃
        self.env_box = QTextEdit()
        self.env_box.hide()
        right.addStretch(1)

        self._apply_env_cols_layout(max(self.width(), 1000))
        lay.addWidget(self._env_cols_host)

    # ------------------------------------------------------------------ 编译页
    def _build_tab_compile(self, outer: QVBoxLayout) -> None:
        def _c_label(text: str) -> QLabel:
            lb = QLabel(text)
            lb.setObjectName("FieldLabel")
            lb.setFixedWidth(158)
            lb.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            return lb

        # —— 配置卡（对齐参考：标题+最近工程 / 三行路径 / 选项）——
        config = QFrame()
        config.setObjectName("Card")
        # Minimum：矮窗口也不压扁内容，不够高就整页滚动
        config.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        cfg = QVBoxLayout(config)
        cfg.setContentsMargins(20, 16, 20, 16)
        cfg.setSpacing(12)

        # 标题行固定高度，避免「最近工程」外壳比标题高导致视觉偏下/贴底裁切
        head_wrap = QWidget()
        head_wrap.setFixedHeight(28)
        head = QHBoxLayout(head_wrap)
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        head.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(FileCodeIcon(20, "#14B8A6"), 0, Qt.AlignmentFlag.AlignVCenter)
        ht = QLabel("Qt 工程路径与构建参数配置")
        ht.setObjectName("CardHeadTitle")
        head.addWidget(ht, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addStretch(1)

        recent_lbl = QLabel("最近工程:")
        recent_lbl.setObjectName("RecentLabel")
        head.addWidget(recent_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        shell = QFrame()
        shell.setObjectName("RecentComboShell")
        shell.setFixedHeight(26)
        shell.setMinimumWidth(240)
        shell.setMaximumWidth(360)
        shell.setCursor(Qt.CursorShape.PointingHandCursor)
        shell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sl = QHBoxLayout(shell)
        sl.setContentsMargins(10, 0, 6, 0)
        sl.setSpacing(2)

        self.cmb_recent = RecentCombo()
        self.cmb_recent.setObjectName("RecentComboInner")
        self.cmb_recent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_recent.setFixedHeight(22)
        self.cmb_recent.setMaxVisibleItems(10)
        self.cmb_recent.addItem("选择最近工程…")
        for p in self._cfg.get("recent_projects") or []:
            self.cmb_recent.addItem(self._recent_display_label(p), p)
        self.cmb_recent.activated.connect(self._on_recent_picked)
        sl.addWidget(self.cmb_recent, 1)

        chev = ChevronArrow("down", "#E5E7EB", 12)
        chev.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        sl.addWidget(chev, 0, Qt.AlignmentFlag.AlignVCenter)

        class _RecentShellFilter(QObject):
            def __init__(self, combo: QComboBox) -> None:
                super().__init__(combo)
                self._combo = combo

            def eventFilter(self, obj, event) -> bool:  # noqa: N802
                if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                    self._combo.showPopup()
                return False

        self._recent_shell_filter = _RecentShellFilter(self.cmb_recent)
        shell.installEventFilter(self._recent_shell_filter)
        head.addWidget(shell, 0, Qt.AlignmentFlag.AlignVCenter)
        cfg.addWidget(head_wrap)
        cfg.addWidget(hline(bright=True))

        # 工程 / 构建 / 产物：左列同宽拉伸，右列按钮统一宽度对齐
        _side_btn_w = 88

        def _side_btn(text: str = "", *, icon: str | None = None, tip: str = "") -> QPushButton:
            b = QPushButton(text)
            b.setObjectName("EnvGhost")
            b.setFixedWidth(_side_btn_w)
            b.setFixedHeight(36)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if icon:
                b.setIcon(make_svg_icon(icon, "#0D9488", 16))
                b.setIconSize(QSize(16, 16))
            if tip:
                b.setToolTip(tip)
            return b

        # 工程目录
        r0 = QHBoxLayout()
        r0.setSpacing(10)
        r0.addWidget(_c_label("工程目录 (Project):"))
        self._proj_path_field = PathInputField(
            self._project,
            placeholder=r"选择 Qt 工程目录…",
            folder_color="#F59E0B",
        )
        self.ed_project = self._proj_path_field.ed
        self._proj_path_field.textChanged.connect(lambda t: self._on_field("project", t))
        self._track_form(self.ed_project)
        r0.addWidget(self._proj_path_field, 1)
        b_bp = _side_btn("浏览...")
        b_bp.clicked.connect(self._browse_project)
        r0.addWidget(b_bp)
        cfg.addLayout(r0)

        # 构建文件
        r1 = QHBoxLayout()
        r1.setSpacing(10)
        r1.addWidget(_c_label("构建文件 (Build File):"))
        self.build_combo = QComboBox()
        self.build_combo.setObjectName("CompileFieldCombo")
        self.build_combo.setEditable(True)
        self.build_combo.setFixedHeight(36)
        self.build_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if self._build_file:
            self.build_combo.setEditText(self._build_file)
        self.build_combo.currentTextChanged.connect(lambda t: self._on_field("build_file", t))
        self._track_form(self.build_combo)
        r1.addWidget(self.build_combo, 1)
        b_ref = _side_btn(icon="refresh", tip="刷新构建文件列表")
        b_ref.clicked.connect(self._refresh_build_files)
        r1.addWidget(b_ref)
        cfg.addLayout(r1)

        # 产物目录
        r2 = QHBoxLayout()
        r2.setSpacing(10)
        r2.addWidget(_c_label("产物目录 (Output):"))
        self._out_path_field = PathInputField(
            self._out_dir,
            placeholder=r"留空则用工程下 dist/…",
            folder_color="#14B8A6",
        )
        self.ed_out_dir = self._out_path_field.ed
        self._out_path_field.textChanged.connect(lambda t: self._on_field("out_dir", t))
        self._track_form(self.ed_out_dir)
        r2.addWidget(self._out_path_field, 1)
        b_bo = _side_btn("浏览...")
        b_bo.clicked.connect(self._browse_out_dir)
        r2.addWidget(b_bo)
        cfg.addLayout(r2)

        cfg.addWidget(hline(bright=True))

        # 选项 + 高级折叠：按参考组件（薄荷绿切换钮 / 模式+ccache）
        self._adv_panel = AdvancedOptionsPanel(
            do_bundle=self._do_bundle,
            use_ffmpeg=self._use_ffmpeg,
            do_clean=self._do_clean,
            build_mode=self._build_mode,
            use_ccache=self._use_ccache,
            expanded=False,
        )
        self.chk_bundle = self._adv_panel.chk_bundle
        self.chk_ffmpeg = self._adv_panel.chk_ffmpeg
        self.chk_clean = self._adv_panel.chk_clean
        self.chk_ccache = self._adv_panel.chk_ccache
        self._btn_mode_release = self._adv_panel.btn_release
        self._btn_mode_debug = self._adv_panel.btn_debug
        self._track_form(self.chk_bundle)
        self._track_form(self.chk_ffmpeg)
        self._track_form(self.chk_clean)
        self._track_form(self.chk_ccache)
        self._track_form(self._btn_mode_release)
        self._track_form(self._btn_mode_debug)
        self._adv_panel.bundle_changed.connect(lambda v: self._on_field("do_bundle", v))
        self._adv_panel.ffmpeg_changed.connect(lambda v: self._on_field("use_ffmpeg", v))
        self._adv_panel.clean_changed.connect(lambda v: self._on_field("do_clean", v))
        self._adv_panel.ccache_changed.connect(lambda v: self._on_field("use_ccache", v))
        self._adv_panel.build_mode_changed.connect(self._set_build_mode)
        self._adv_panel.expanded_changed.connect(self._on_adv_expanded)
        cfg.addWidget(self._adv_panel)

        self._compile_config = config
        outer.addWidget(config)

        # —— 操作栏独立卡片（对齐参考 ActionBar）——
        action = QFrame()
        action.setObjectName("ActionBar")
        action.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        btn_row = QHBoxLayout(action)
        btn_row.setContentsMargins(14, 10, 14, 10)
        btn_row.setSpacing(10)

        self._btn_build = QPushButton("开始交叉编译 (aarch64)")
        self._btn_build.setObjectName("BtnStartBuild")
        self._btn_build.setIcon(make_svg_icon("play_solid", "#FFFFFF", 16))
        self._btn_build.setIconSize(QSize(16, 16))
        self._btn_build.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_build.clicked.connect(self._on_build)
        self._track_action(self._btn_build)
        btn_row.addWidget(self._btn_build)

        b_out = QPushButton("打开产物文件夹")
        b_out.setObjectName("BtnOpenOutFolder")
        b_out.setIcon(make_svg_icon("folder_open", "#F59E0B", 18, pad_right=6))
        b_out.setIconSize(QSize(24, 18))
        b_out.setCursor(Qt.CursorShape.PointingHandCursor)
        b_out.clicked.connect(self._open_out)
        self._track_action(b_out)
        btn_row.addWidget(b_out)

        btn_row.addStretch(1)

        b_share = GoShareButton()
        b_share.clicked.connect(lambda: self._select_step(2))
        self._track_action(b_share)
        btn_row.addWidget(b_share)

        b_copy = QPushButton()
        b_copy.setObjectName("IconGhost")
        b_copy.setToolTip("复制日志")
        b_copy.setIcon(make_svg_icon("copy", "#E5E7EB", 15))
        b_copy.setIconSize(QSize(15, 15))
        b_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        b_copy.clicked.connect(self._copy_log)
        self._track_action(b_copy, keep_when_busy=True)
        btn_row.addWidget(b_copy)

        b_clear = QPushButton()
        b_clear.setObjectName("IconGhost")
        b_clear.setToolTip("清空日志")
        b_clear.setIcon(make_svg_icon("trash", "#E5E7EB", 15))
        b_clear.setIconSize(QSize(15, 15))
        b_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        b_clear.clicked.connect(self._clear_log)
        btn_row.addWidget(b_clear)
        outer.addWidget(action)

        # —— 日志终端卡 ——
        console = QFrame()
        console.setObjectName("TerminalCard")
        console.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        clog = QVBoxLayout(console)
        clog.setContentsMargins(20, 16, 20, 16)
        clog.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(TerminalIcon(18, "#10B981"))
        ctitle = QLabel("交叉编译日志终端 (aarch64-linux-gnu-gcc)")
        ctitle.setStyleSheet("font-weight:700; color:#10B981; font-size:13px; background:transparent; border:none;")
        top.addWidget(ctitle)
        top.addStretch(1)
        self._log_count_lbl = QLabel("0 行")
        self._log_count_lbl.setObjectName("Muted")
        top.addWidget(self._log_count_lbl)
        self.chk_autoscroll = QCheckBox("自动滚动")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.toggled.connect(lambda v: setattr(self, "_log_auto_scroll", v))
        top.addWidget(self.chk_autoscroll)
        self._compile_progress = QProgressBar()
        self._compile_progress.setFixedWidth(180)
        self._compile_progress.setFixedHeight(10)
        self._compile_progress.setRange(0, 0)
        self._compile_progress.setTextVisible(False)
        self._compile_progress.setVisible(False)
        top.addWidget(self._compile_progress)
        clog.addLayout(top)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("TerminalLog")
        self.log.setMinimumHeight(240)
        self.log.setPlainText(
            "[INFO] 交叉编译控制台已就绪…\n"
            "[INFO] 目标架构: aarch64-linux-gnu (GCC 9.4.0 / Qt 5.14.2)\n"
            "等待开始编译指令…"
        )
        clog.addWidget(self.log, 1)
        outer.addWidget(console)
        outer.addStretch(1)

    # ------------------------------------------------------------------ 共享页
    def _build_tab_share(self, lay: QVBoxLayout) -> None:
        hero = QFrame()
        hero.setObjectName("SectionHero")
        hero_lay = QHBoxLayout(hero)
        hero_lay.setContentsMargins(20, 16, 20, 16)
        hero_lay.setSpacing(16)
        texts = QVBoxLayout()
        texts.setSpacing(3)
        t1 = QLabel("嵌入式板端 HTTP 极速部署共享")
        t1.setObjectName("SectionHeroTitle")
        texts.addWidget(t1)
        t2 = QLabel("支持浏览器 / wget / curl 直连下载，适配麒麟、飞腾和树莓派等板端环境。")
        t2.setObjectName("SectionHeroDesc")
        t2.setWordWrap(True)
        texts.addWidget(t2)
        hero_lay.addLayout(texts, 1)
        lay.addWidget(hero)

        share, share_lay = _card("HTTP 共享")
        r0 = QHBoxLayout()
        r0.addWidget(_field_label("共享目录"))
        self.ed_share_dir = QLineEdit(self._share_dir)
        self.ed_share_dir.textChanged.connect(lambda t: self._on_field("share_dir", t))
        self._track_form(self.ed_share_dir)
        r0.addWidget(self.ed_share_dir, 1)
        b_bs = _btn("浏览…")
        b_bs.clicked.connect(self._browse_share)
        r0.addWidget(b_bs)
        b_use = _btn("用产物目录", "Accent")
        b_use.clicked.connect(self._fill_share_from_project)
        r0.addWidget(b_use)
        share_lay.addLayout(r0)

        r1 = QHBoxLayout()
        r1.addWidget(_field_label("端口"))
        self.sp_port = QSpinBox()
        self.sp_port.setRange(1, 65535)
        self.sp_port.setValue(self._share_port)
        self.sp_port.valueChanged.connect(lambda v: self._on_field("share_port", v))
        self._track_form(self.sp_port)
        r1.addWidget(self.sp_port)
        b_start = _btn("启动共享", "Accent")
        b_start.clicked.connect(self._share_start)
        self._track_action(b_start)
        r1.addWidget(b_start)
        b_stop = _btn("停止")
        b_stop.clicked.connect(self._share_stop)
        self._track_action(b_stop, keep_when_busy=True)
        r1.addWidget(b_stop)
        r1.addStretch(1)
        share_lay.addLayout(r1)

        head = QHBoxLayout()
        self._http_dot = QLabel("●")
        self._http_dot.setStyleSheet(f"color:{C['idle']}; font-size:14px;")
        head.addWidget(self._http_dot)
        self._share_state_lbl = QLabel("未启动")
        self._share_state_lbl.setObjectName("Muted")
        head.addWidget(self._share_state_lbl)
        head.addStretch(1)
        share_lay.addLayout(head)

        local_row = QHBoxLayout()
        local_row.addWidget(QLabel("本机测试"))
        self.ed_share_local = QLineEdit("—")
        self.ed_share_local.setReadOnly(True)
        local_row.addWidget(self.ed_share_local, 1)
        b_open = _btn("打开")
        b_open.clicked.connect(self._share_open_local)
        local_row.addWidget(b_open)
        b_probe = _btn("自检", "Accent")
        b_probe.clicked.connect(self._share_probe_local)
        local_row.addWidget(b_probe)
        share_lay.addLayout(local_row)

        lan_row = QHBoxLayout()
        lan_row.addWidget(QLabel("局域网地址"))
        self.ed_share_urls = QLineEdit("—")
        self.ed_share_urls.setReadOnly(True)
        lan_row.addWidget(self.ed_share_urls, 1)
        b_copy_u = _btn("复制")
        b_copy_u.clicked.connect(self._share_copy_url)
        lan_row.addWidget(b_copy_u)
        share_lay.addLayout(lan_row)
        lay.addWidget(share)

        tip = QLabel("麒麟机浏览器打开「局域网地址」。本机打不开时先点「自检」，并确认代理绕过 127.0.0.1。")
        tip.setObjectName("Muted")
        tip.setWordWrap(True)
        lay.addWidget(tip)

        slog, slog_lay = _card("本页日志")
        self._share_log = QTextEdit()
        self._share_log.setReadOnly(True)
        self._share_log.setObjectName("Log")
        self._share_log.setMaximumHeight(140)
        slog_lay.addWidget(self._share_log)
        lay.addWidget(slog)

        self._eth_btn = QToolButton()
        self._eth_btn.setText("网卡高级 ▸")
        self._eth_btn.setObjectName("Accent")
        self._eth_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._eth_btn.clicked.connect(self._toggle_eth)
        lay.addWidget(self._eth_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self._eth = QWidget()
        self._eth.setVisible(False)
        eth_outer = QVBoxLayout(self._eth)
        eth_outer.setContentsMargins(0, 0, 0, 0)
        eth, eth_lay = _card("有线网卡 IP（追加地址）")
        eth_tip = QLabel("等同 Windows「IP 设置 → 添加」；不改网关，需 UAC。")
        eth_tip.setObjectName("Muted")
        eth_tip.setWordWrap(True)
        eth_lay.addWidget(eth_tip)
        self._eth_list_lbl = QLabel("（尚未刷新）")
        self._eth_list_lbl.setWordWrap(True)
        eth_lay.addWidget(self._eth_list_lbl)
        erow = QHBoxLayout()
        erow.addWidget(QLabel("附加 IP"))
        self.ed_eth_ip = QLineEdit(self._eth_add_ip)
        self.ed_eth_ip.setMaximumWidth(140)
        self.ed_eth_ip.textChanged.connect(lambda t: self._on_field("eth_add_ip", t))
        self._track_form(self.ed_eth_ip)
        erow.addWidget(self.ed_eth_ip)
        erow.addWidget(QLabel("掩码"))
        self.ed_eth_mask = QLineEdit(self._eth_add_mask)
        self.ed_eth_mask.setMaximumWidth(130)
        self.ed_eth_mask.textChanged.connect(lambda t: self._on_field("eth_add_mask", t))
        self._track_form(self.ed_eth_mask)
        erow.addWidget(self.ed_eth_mask)
        b_add = _btn("添加 IP", "Accent")
        b_add.clicked.connect(self._on_add_eth_ip)
        self._track_action(b_add)
        erow.addWidget(b_add)
        b_del = _btn("删除所选")
        b_del.clicked.connect(self._on_remove_eth_ip)
        self._track_action(b_del)
        erow.addWidget(b_del)
        b_er = _btn("刷新")
        b_er.clicked.connect(self._refresh_eth_list)
        self._track_action(b_er)
        erow.addWidget(b_er)
        erow.addStretch(1)
        eth_lay.addLayout(erow)
        mute = QLabel("删除时在下方选一个已有地址：")
        mute.setObjectName("Muted")
        eth_lay.addWidget(mute)
        self.eth_combo = QComboBox()
        self._track_form(self.eth_combo)
        eth_lay.addWidget(self.eth_combo)
        eth_outer.addWidget(eth)
        lay.addWidget(self._eth)

    # ------------------------------------------------------------------ 折叠 / 跟踪
    def _set_build_mode(self, mode: str) -> None:
        self._build_mode = "debug" if mode == "debug" else "release"
        self._on_field("build_mode", self._build_mode)

    def _on_adv_expanded(self, expanded: bool) -> None:
        self._advanced_open = bool(expanded)
        # 整页可滚，只需刷新几何；不再 setFixedHeight
        cfg = getattr(self, "_compile_config", None)
        if cfg is not None:
            cfg.updateGeometry()
            parent = cfg.parentWidget()
            if parent is not None and parent.layout() is not None:
                parent.layout().activate()

    def _recent_display_label(self, path: str) -> str:
        """最近工程下拉显示：目录名 (xxx.pro)，对齐参考。"""
        p = Path(path)
        name = p.name or path
        if p.is_dir():
            pros = sorted(p.glob("*.pro"))
            if pros:
                return f"{name} ({pros[0].name})"
        return name

    def _on_scratch_header_press(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_scratch()

    def _toggle_scratch(self) -> None:
        self._scratch_open = not self._scratch_open
        self._scratch.setVisible(self._scratch_open)
        if hasattr(self, "_scratch_arrow"):
            self._scratch_arrow.set_direction("up" if self._scratch_open else "down")

    def _on_preset_picked(self, name: str) -> None:
        """界面：点预设卡填入发行版名（非 20.04 仅预留，稍后接逻辑）。"""
        if hasattr(self, "ed_distro"):
            self.ed_distro.setText(name)
        self._sync_preset_selection(name)
        # 同步建议安装目录末段
        if hasattr(self, "ed_env_install"):
            cur = self.ed_env_install.text().strip()
            base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "WSL" / name
            if (not cur) or cur.rstrip("\\/").endswith(("Ubuntu-20.04", "Ubuntu-22.04", "Kirin-ARM64-SDK")):
                self.ed_env_install.setText(str(base))

    def _on_distro_edited(self, text: str) -> None:
        self._on_field("distro", text)
        self._sync_preset_selection(text.strip())

    def _sync_preset_selection(self, name: str) -> None:
        cards = getattr(self, "_preset_cards", None)
        if not cards:
            return
        for n, card in cards.items():
            card.set_selected(n == name)

    def _toggle_eth(self) -> None:
        self._eth_open = not self._eth_open
        self._eth.setVisible(self._eth_open)
        self._eth_btn.setText("网卡高级 ▾" if self._eth_open else "网卡高级 ▸")
        if self._eth_open:
            self._refresh_eth_list()

    def _refresh_env_hint(self) -> None:
        if self._env_hint_lbl is None:
            return
        if self._env_ready:
            self._env_hint_lbl.setText("可直接去「2 编译」。需要换机时再用「导出…」打包环境。")
        else:
            self._env_hint_lbl.setText("① 点「下载环境包」→ ②「一键导入」→ ③ 自动检测通过后去「2 编译」。")

    def _track_action(self, btn: QWidget, *, keep_when_busy: bool = False) -> QWidget:
        self._action_btns.append(btn)
        if keep_when_busy:
            self._busy_keep.add(id(btn))
        return btn

    def _track_form(self, widget: QWidget) -> QWidget:
        self._form_widgets.append(widget)
        return widget

    def _set_form_enabled(self, enabled: bool) -> None:
        for w in self._form_widgets:
            w.setEnabled(enabled)

    def _set_actions_enabled(self, enabled: bool) -> None:
        for b in self._action_btns:
            keep = (not enabled) and id(b) in self._busy_keep
            on = enabled or keep
            b.setEnabled(on)
        if self._btn_cancel is not None:
            self._btn_cancel.setVisible(not enabled)
            self._btn_cancel.setEnabled(not enabled)

    def _run_on_ui(self, fn: object) -> None:
        if callable(fn):
            fn()

    def _ui(self, fn) -> None:
        """工作线程里把回调丢回 UI 线程。"""
        self.sig_busy_done.emit(fn)

    # ------------------------------------------------------------------ 字段 / 持久化
    def _on_field(self, key: str, value) -> None:
        mapping = {
            "project": ("_project",),
            "build_file": ("_build_file",),
            "build_system": ("_build_system",),
            "app_name": ("_app_name",),
            "out_dir": ("_out_dir",),
            "out_bin": ("_out_bin",),
            "jobs": ("_jobs_n",),
            "do_bundle": ("_do_bundle",),
            "do_clean": ("_do_clean",),
            "use_ffmpeg": ("_use_ffmpeg",),
            "build_mode": ("_build_mode",),
            "use_ccache": ("_use_ccache",),
            "plugins": ("_plugins",),
            "extra_pkg": ("_extra_pkg",),
            "extra_copy": ("_extra_copy",),
            "distro": ("_distro",),
            "share_dir": ("_share_dir",),
            "share_port": ("_share_port",),
            "eth_add_ip": ("_eth_add_ip",),
            "eth_add_mask": ("_eth_add_mask",),
            "env_install": ("_env_install_dir",),
            "env_slim": ("_env_slim",),
            "env_replace": ("_env_replace",),
        }
        attrs = mapping.get(key)
        if attrs:
            setattr(self, attrs[0], value)
        self._schedule_persist()

    def _schedule_persist(self) -> None:
        self._persist_timer.start(400)

    def _persist(self) -> None:
        kind, path = self._parse_build_combo()
        settings.save(
            {
                "project": (self.ed_project.text() if hasattr(self, "ed_project") else self._project).strip(),
                "build_file": f"{kind}: {path}" if path else "",
                "build_system": self._build_system,
                "app_name": self._app_name,
                "out_dir": self._out_dir.strip() if isinstance(self._out_dir, str) else str(self._out_dir),
                "out_bin": self._out_bin,
                "jobs": int(self._jobs_n or 0),
                "do_bundle": bool(self._do_bundle),
                "do_clean": bool(self._do_clean),
                "use_ffmpeg": bool(self._use_ffmpeg),
                "build_mode": self._build_mode,
                "use_ccache": bool(self._use_ccache),
                "plugins": self._plugins,
                "extra_pkgconfig": self._extra_pkg,
                "extra_copy": self._extra_copy,
                "distro": (self._distro or "").strip() or wsl.DEFAULT_DISTRO,
                "share_dir": (self._share_dir or "").strip(),
                "share_port": int(self._share_port or 18080),
                "eth_add_ip": (self._eth_add_ip or "").strip(),
                "eth_add_mask": (self._eth_add_mask or "").strip() or "255.255.255.0",
                "env_install_dir": (self._env_install_dir or "").strip(),
                "env_slim_export": bool(self._env_slim),
                "env_replace_on_import": bool(self._env_replace),
                "env_ready": bool(self._env_ready),
            }
        )

    def _project_text(self) -> str:
        return self.ed_project.text().strip() if hasattr(self, "ed_project") else self._project.strip()

    def _out_dir_text(self) -> str:
        return self.ed_out_dir.text().strip() if hasattr(self, "ed_out_dir") else self._out_dir.strip()

    def _distro_text(self) -> str:
        if hasattr(self, "ed_distro"):
            return self.ed_distro.text().strip() or wsl.DEFAULT_DISTRO
        return (self._distro or "").strip() or wsl.DEFAULT_DISTRO

    # ------------------------------------------------------------------ 忙碌 / 日志
    def _on_cancel(self) -> None:
        if not self._busy:
            return
        distro = self._distro_text()
        self._append_log("[cancel] 正在取消当前任务…")
        jobs.cancel(distro=distro)

    def _open_env_release(self) -> None:
        webbrowser.open(ENV_RELEASE_URL)

    def _busy_result_msg(self, code: int, ok: str, fail_prefix: str) -> str:
        if code == jobs.CANCELLED:
            return "已取消"
        if code == 0:
            return ok
        return f"{fail_prefix} exit={code}"

    def _fail_summary_from_log(self) -> str:
        blob = "\n".join(self._recent_log_lines[-80:])
        rules = [
            ("磁盘空间可能不足", "磁盘空间不足，请换更大的盘或清理空间后重试。"),
            ("GLIBC_2", "产物需要过高的 glibc，请检查是否链到了过新系统库。"),
            ("libqxcb", "缺少 qxcb 平台插件。请先「检测环境」，必要时重新导入环境包。"),
            ("qxcb", "缺少 qxcb 平台插件。请先「检测环境」，必要时重新导入环境包。"),
            ("pkg-config", "pkg-config 失败。若勾了「附加 FFmpeg」，请确认环境包含 FFmpeg 开发库。"),
            ("找不到产物", "找不到可执行文件。请在高级里填写「可执行文件」路径，或检查工程 TARGET。"),
            ("missing", "交叉环境不完整。请去「1 环境」导入环境包或点「检测环境」。"),
            ("ERROR:", None),
        ]
        for key, tip in rules:
            if key in blob:
                if tip:
                    return tip
                for line in reversed(self._recent_log_lines):
                    if "ERROR:" in line or line.strip().startswith("ERROR"):
                        return line.strip()[:200]
        return "请查看「2 编译」页日志中的 ERROR / 最后几行。"

    def _confirm_distro(self) -> bool:
        d = self._distro_text()
        if hasattr(self, "ed_distro"):
            self.ed_distro.setText(d)
        self._distro = d
        if d == wsl.DEFAULT_DISTRO:
            return True
        r = QMessageBox.question(
            self,
            "发行版名称",
            f"当前发行版为「{d}」（默认是 {wsl.DEFAULT_DISTRO}）。\n"
            "导入 / 导出 / 检测都会用这个名字。确认继续？",
        )
        return r == QMessageBox.StandardButton.Yes

    def _sync_build_enabled(self) -> None:
        # 主按钮始终可点；环境未就绪时点下去再提示，不灰掉
        on = not self._busy
        if hasattr(self, "_btn_build"):
            self._btn_build.setEnabled(on)
        if self._chrome is not None:
            self._chrome.set_quick_enabled(on)

    def _clear_log(self) -> None:
        self.log.clear()
        self._log_line_count = 0
        self._log_count_lbl.setText("0 行")

    def _on_clean_cache_hint(self) -> None:
        """勾选全量清理，下次编译会清缓存；仅提示，不立刻删目录。"""
        if hasattr(self, "chk_clean"):
            self.chk_clean.setChecked(True)
        self._append_log("[CLEAN] 已勾选「全量清理」，下次一键编译将清空构建缓存。")
        self._append_log("[SUCCESS] 准备就绪。")

    def _set_env_box(self, text: str) -> None:
        self.env_box.setPlainText(text)

    def _sync_go_compile_btn_style(self) -> None:
        if not hasattr(self, "_go_text"):
            return
        on = self._btn_go_compile.isEnabled()
        fg = "#FFFFFF" if on else C["idle"]
        self._go_text.setStyleSheet(
            f"background:transparent; border:none; color:{fg}; font-size:12px; font-weight:600;"
        )
        self._go_icon.set_color(fg)

    def _start_detect_spin(self) -> None:
        self._detect_icon.start()
        self._detect_label.setText("检测中...")
        self._btn_redetect.setEnabled(False)

    def _stop_detect_spin(self) -> None:
        self._detect_icon.stop()
        self._detect_label.setText("重新检测环境")
        if not self._busy:
            self._btn_redetect.setEnabled(True)

    def _show_toast(self, msg: str, duration: int = 3500) -> None:
        """右下角绿色 toast：持续上下弹跳，到时淡出关闭。"""
        toast = ToastNotification(parent=self, text=msg, duration=duration)
        # 保留引用，避免被 GC 提前销毁
        if not hasattr(self, "_active_toasts"):
            self._active_toasts: list[ToastNotification] = []
        self._active_toasts = [t for t in self._active_toasts if t.isVisible()]
        self._active_toasts.append(toast)
        toast.destroyed.connect(lambda *_: self._active_toasts.remove(toast) if toast in self._active_toasts else None)
        toast.show_toast(self)

    def _apply_env_ready(self, ready: bool) -> None:
        self._env_ready = ready
        self._schedule_persist()
        if ready:
            text = (
                "检测到完整的 WSL2 Linux 交叉编译镜像。已预装 ARM64 交叉编译器 "
                "(aarch64-linux-gnu-g++) 和 Qt 5.14.2 独立依赖，无需重复初始化。"
            )
            fg = "#94a3b8"
            badge = "环境就绪 — 可直接编译"
            hero_obj = "HeroBanner"
            if hasattr(self, "_footer_wsl"):
                self._footer_wsl.setText(f"WSL2 {self._distro_text()} (aarch64)")
        else:
            text = "环境未就绪 — 请先下载并导入环境包"
            fg = C["err"]
            badge = "环境未就绪"
            hero_obj = "HeroBannerBad"
            if hasattr(self, "_footer_wsl"):
                self._footer_wsl.setText("WSL2 环境未就绪")
        if self._chrome is not None:
            self._chrome.set_env_ready(ready, self._distro_text())
        if hasattr(self, "_env_hero"):
            self._env_hero.setObjectName(hero_obj)
            self._env_hero.style().unpolish(self._env_hero)
            self._env_hero.style().polish(self._env_hero)
        if hasattr(self, "_env_hero_icon") and hasattr(self, "_env_hero_mark"):
            self._env_hero_icon.setObjectName("HeroIconOk" if ready else "HeroIconBad")
            self._env_hero_icon.style().unpolish(self._env_hero_icon)
            self._env_hero_icon.style().polish(self._env_hero_icon)
            if ready:
                self._env_hero_mark.setText("✓")
                self._env_hero_mark.setObjectName("HeroCheckCircle")
                self._env_hero_mark.setFixedSize(22, 22)
            else:
                self._env_hero_mark.setText("!")
                self._env_hero_mark.setObjectName("HeroWarnMark")
                self._env_hero_mark.setFixedSize(44, 44)
            self._env_hero_mark.style().unpolish(self._env_hero_mark)
            self._env_hero_mark.style().polish(self._env_hero_mark)
        if hasattr(self, "_env_hero_badge"):
            set_ready_pill(self._env_hero_badge, badge, ok=ready)
        if hasattr(self, "_btn_go_compile"):
            self._btn_go_compile.setEnabled(ready and not self._busy)
            self._sync_go_compile_btn_style()
        for lbl in self._env_banner_labels:
            lbl.setText(text)
            lbl.setStyleSheet(f"color:{fg};")
        self._refresh_env_hint()
        self._refresh_flow_hint()
        # 只刷新步骤角标，避免重复切页
        if hasattr(self, "_step_cards") and hasattr(self, "_step_num_lbls"):
            for i, badge_lbl in enumerate(self._step_num_lbls):
                active = i == self._current_step
                if active:
                    badge_lbl.setText(str(i + 1))
                    badge_lbl.setStyleSheet(
                        f"background:{C['accent']}; color:white; border-radius:8px; font-weight:700; font-size:11px;"
                    )
                elif ready and i == 0:
                    badge_lbl.setText("✓")
                    badge_lbl.setStyleSheet(
                        f"background:rgba(16,185,129,0.2); color:{C['ok']}; border-radius:8px; font-weight:700;"
                    )
                else:
                    badge_lbl.setText(str(i + 1))
                    badge_lbl.setStyleSheet(
                        f"background:{C['surface2']}; color:{C['muted']}; border-radius:8px; font-weight:700; font-size:11px;"
                    )
        if not self._busy:
            self._sync_build_enabled()

    def _show_log_tab(self) -> None:
        self._select_step(1)

    def _pill(self, text: str, fg: str | None = None) -> None:
        if self._chrome is not None:
            self._chrome.set_busy_text(text, fg)

    def _set_http_dot(self, on: bool) -> None:
        color = C["ok"] if on else C["idle"]
        self._http_dot.setStyleSheet(f"color:{color}; font-size:14px;")

    def _log_color_for(self, line: str) -> str:
        low = line.lower()
        if "error" in low or "fail" in low or "失败" in line or line.strip().startswith("ERROR"):
            return C["err"]
        if " ok" in low or low.startswith("[ok]") or "成功" in line or "就绪" in line:
            return C["ok"]
        if line.startswith("[http]") or line.startswith("[env]") or line.startswith("[net]") or line.startswith("[detect]"):
            return C["accent"]
        return C["log_fg"]

    def _append_log(self, line: str) -> None:
        self._recent_log_lines.append(line)
        if len(self._recent_log_lines) > 400:
            self._recent_log_lines = self._recent_log_lines[-300:]

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self._log_color_for(line)))
        cur = self.log.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText(line + "\n", fmt)
        self._log_line_count += 1
        self._log_count_lbl.setText(f"{self._log_line_count} 行")
        if self._log_auto_scroll:
            self.log.moveCursor(QTextCursor.MoveOperation.End)

        if self._share_log is not None and (
            line.startswith("[http]")
            or line.startswith("[net]")
            or line.startswith("[env]")
            or line.startswith("[cancel]")
        ):
            sfmt = QTextCharFormat()
            sfmt.setForeground(QColor(self._log_color_for(line)))
            sc = self._share_log.textCursor()
            sc.movePosition(QTextCursor.MoveOperation.End)
            sc.insertText(line + "\n", sfmt)
            # 只保留末尾约 200 行
            doc = self._share_log.document()
            if doc.blockCount() > 220:
                c = QTextCursor(doc)
                c.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(doc.blockCount() - 200):
                    c.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor)
                c.removeSelectedText()
            self._share_log.moveCursor(QTextCursor.MoveOperation.End)

        short = line.strip()
        if len(short) > 72:
            short = short[:69] + "…"
        self._activity_lbl.setText(short)

    def _start_pulse(self, base: str) -> None:
        self._stop_pulse()
        self._pulse_base = base.rstrip(".")
        self._pulse_n = 0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start(400)
        self._pulse_tick()

    def _pulse_tick(self) -> None:
        self._pulse_n = (self._pulse_n % 3) + 1
        dots = "." * self._pulse_n
        text = f"{self._pulse_base}{dots}"
        self._status_lbl.setText(text)
        self._pill(text, "#FDE68A")

    def _stop_pulse(self) -> None:
        if self._pulse_timer is not None:
            self._pulse_timer.stop()
            self._pulse_timer.deleteLater()
            self._pulse_timer = None

    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self._busy = busy
        self._set_actions_enabled(not busy)
        self._set_form_enabled(not busy)
        self._sync_build_enabled()
        text = msg or ("忙碌…" if busy else "就绪")
        self._status_lbl.setText(text)
        if hasattr(self, "_compile_progress"):
            self._compile_progress.setVisible(busy)
        if busy:
            self._progress.setVisible(True)
            if self._btn_cancel is not None:
                self._btn_cancel.setVisible(True)
                self._btn_cancel.setEnabled(True)
            self._start_pulse(text.rstrip("…").rstrip("."))
            self._pill(text, "#FDE68A")
        else:
            self._progress.setVisible(False)
            if self._btn_cancel is not None:
                self._btn_cancel.setVisible(False)
                self._btn_cancel.setEnabled(False)
            self._stop_pulse()
            self._activity_lbl.setText("")
            if "共享" in text:
                self._pill(text.replace("HTTP ", ""), "#99F6E4")
            elif text.startswith("成功") or text.startswith("环境就绪"):
                self._pill("环境就绪" if "环境就绪" in text else "成功", "#86EFAC")
            elif text.startswith("已取消"):
                self._pill("已取消", "#FDE68A")
            elif text.startswith("失败") or "失败" in text or "不完整" in text:
                self._pill("失败" if "失败" in text else "环境缺项", "#FCA5A5")
            else:
                self._pill("空闲" if text == "就绪" else text, "#99F6E4")
            self._status_lbl.setText(text)
        if hasattr(self, "_btn_go_compile"):
            self._btn_go_compile.setEnabled((not busy) and self._env_ready)
            self._sync_go_compile_btn_style()

    # ------------------------------------------------------------------ 工程 / 浏览
    def _on_recent_picked(self, idx: int) -> None:
        if idx <= 0:
            return
        path = self.cmb_recent.itemData(idx)
        if not path:
            path = self.cmb_recent.itemText(idx)
        if path:
            self._set_project(str(path))

    def _set_project(self, path: str) -> None:
        self.ed_project.setText(path)
        self.build_combo.setEditText("")
        self._refresh_build_files()
        self._reset_out_dir_if_foreign()
        if not self.ed_share_dir.text().strip():
            self._fill_share_from_project()

    def _reset_out_dir_if_foreign(self) -> None:
        proj = self._project_text()
        out = self._out_dir_text()
        if not proj or not out:
            return
        try:
            Path(out).resolve().relative_to(Path(proj).resolve())
        except (ValueError, OSError):
            self.ed_out_dir.setText("")

    def _browse_project(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "选择工程目录", self._project_text() or os.path.expanduser("~")
        )
        if d:
            self._set_project(d)

    def _browse_out_dir(self) -> None:
        init = self._out_dir_text() or self._project_text() or os.path.expanduser("~")
        if init and not Path(init).is_dir():
            init = self._project_text() or os.path.expanduser("~")
        d = QFileDialog.getExistingDirectory(self, "选择产物目录（压缩包放置位置）", init)
        if d:
            self.ed_out_dir.setText(d)

    def _browse_share(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self,
            "选择共享目录",
            self.ed_share_dir.text().strip() or self._project_text() or os.path.expanduser("~"),
        )
        if d:
            self.ed_share_dir.setText(d)

    def _browse_env_install(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "选择安装目录", self.ed_env_install.text().strip() or os.path.expanduser("~")
        )
        if d:
            self.ed_env_install.setText(d)

    def _fill_share_from_project(self) -> None:
        out = self._out_dir_text()
        if out and Path(out).is_dir():
            self.ed_share_dir.setText(out)
            return
        g = guess_share_dir(self._project_text(), self._app_name)
        if g is not None:
            self.ed_share_dir.setText(str(g))
            if not self._out_dir_text():
                self.ed_out_dir.setText(str(g))

    def _refresh_build_files(self) -> None:
        files = buildmod.discover_build_files(self._project_text())
        values = [f"{k}: {p}" for k, p in files]
        cur = self.build_combo.currentText().strip()
        self.build_combo.blockSignals(True)
        self.build_combo.clear()
        self.build_combo.addItems(values)
        if not values:
            self.build_combo.setEditText("")
            self.build_combo.blockSignals(False)
            return
        if cur not in values:
            cur = values[0]
        self.build_combo.setCurrentText(cur)
        self.build_combo.blockSignals(False)
        self._build_file = cur
        self._parse_build_combo()
        self._reset_out_dir_if_foreign()

    def _parse_build_combo(self) -> tuple[str, str]:
        raw = self.build_combo.currentText().strip() if hasattr(self, "build_combo") else self._build_file
        if ": " in raw and raw.split(": ", 1)[0] in ("qmake", "cmake"):
            kind, path = raw.split(": ", 1)
            self._build_system = kind
            return kind, path
        if raw.endswith(".pro"):
            return "qmake", raw
        if raw.endswith("CMakeLists.txt"):
            return "cmake", raw
        return self._build_system, raw

    # ------------------------------------------------------------------ 共享业务
    def _share_start(self) -> None:
        if self._busy:
            return
        if self._share.running:
            QMessageBox.information(self, "提示", "共享已在运行")
            return
        directory = self.ed_share_dir.text().strip()
        if not directory or not Path(directory).is_dir():
            QMessageBox.critical(self, "错误", "请先选择有效的共享目录（可用「用产物目录」）")
            return
        port = int(self.sp_port.value() or 18080)
        self._set_busy(True, "启动共享…")
        self._append_log(f"[http] 正在启动共享 :{port} …")
        self._share_state_lbl.setText("启动中…")

        def work() -> None:
            err: str | None = None
            primary = local = ""
            eth: list = []
            ok, detail = False, ""
            try:
                self._ui(lambda: self._append_log(f"[http] 监听目录: {directory}"))
                self._ui(lambda: self._share_state_lbl.setText("启动中 · 监听端口…"))
                self._share.start(directory, port)
                self._ui(lambda: self._share_state_lbl.setText("启动中 · 防火墙…"))
                self._ui(lambda: self._append_log("[http] 尝试放行防火墙…"))
                ensure_firewall_allow(port, on_line=lambda line: self.sig_log.emit(line))
                primary = self._share.primary_url()
                local = self._share.local_url()
                self._ui(lambda: self._share_state_lbl.setText("启动中 · 解析网卡…"))
                self._ui(lambda: self._append_log("[http] 解析局域网地址…"))
                eth = ethernet_ipv4()
                self._ui(lambda: self._share_state_lbl.setText("启动中 · 本机自检…"))
                self._ui(lambda: self._append_log("[http] 本机自检…"))
                ok, detail = self._share.probe_local()
            except OSError as e:
                err = str(e)

            def done() -> None:
                if err:
                    self._append_log(f"[http] 启动失败: {err}")
                    self._share_state_lbl.setText("未启动")
                    self._set_busy(False, "共享启动失败")
                    QMessageBox.critical(self, "错误", f"无法监听端口 {port}: {err}")
                    return
                self.ed_share_urls.setText(primary or "—")
                self.ed_share_local.setText(local or f"http://127.0.0.1:{port}/")
                self._share_state_lbl.setText(f"运行中 · 端口 {port}")
                self._set_http_dot(True)
                self._persist()
                self._append_log(f"[http] 共享已启动: {directory}")
                self._append_log(f"[http] 本机测试: {local}")
                if eth:
                    self._append_log(f"[http] 局域网地址: {primary}")
                else:
                    self._append_log(f"[http] 未检测到有线网卡，局域网地址退回: {primary}")
                self._append_log(f"[http] 本机自检: {detail}")
                if not ok:
                    QMessageBox.warning(
                        self,
                        "本机自检失败",
                        "服务已启动，但本机探测未通过。\n"
                        "若浏览器也打不开，请换端口（如 18080），并确认代理绕过 127.0.0.1。",
                    )
                self._append_log("[http] 客户机示例: wget <局域网地址><包名>.tar.gz")
                self._set_busy(False, f"HTTP 共享中 :{port}")
                self._pill(f"共享 :{port}", "#99F6E4")

            self._ui(done)

        threading.Thread(target=work, daemon=True).start()

    def _share_stop(self) -> None:
        if not self._share.running:
            self.ed_share_urls.setText("—")
            self.ed_share_local.setText("—")
            self._share_state_lbl.setText("未启动")
            self._set_http_dot(False)
            return
        self._share.stop()
        self.ed_share_urls.setText("—")
        self.ed_share_local.setText("—")
        self._share_state_lbl.setText("未启动")
        self._set_http_dot(False)
        self._append_log("[http] 共享已停止")
        self._set_busy(False, "就绪")

    def _share_copy_url(self) -> None:
        url = self._share.primary_url()
        if not url:
            QMessageBox.information(self, "提示", "请先启动共享")
            return
        QApplication.clipboard().setText(url)
        self._status_lbl.setText("局域网地址已复制")

    def _refresh_eth_list(self) -> None:
        adapters = netip.list_ethernet_adapters()
        if not adapters:
            self._eth_list_lbl.setText("未检测到物理以太网卡")
            self.eth_combo.clear()
            return
        lines: list[str] = []
        picks: list[str] = []
        for a in adapters:
            ip_s = ", ".join(f"{x.address}/{x.prefix}" for x in a.ips) or "（无 IPv4）"
            lines.append(f"{a.name} [{a.status}]  ifIndex={a.if_index}  {ip_s}")
            for x in a.ips:
                picks.append(f"{x.address}  ({a.name})")
        self._eth_list_lbl.setText("\n".join(lines))
        cur = self.eth_combo.currentText()
        self.eth_combo.clear()
        self.eth_combo.addItems(picks)
        if picks:
            if cur in picks:
                self.eth_combo.setCurrentText(cur)
            else:
                self.eth_combo.setCurrentIndex(0)

    def _on_add_eth_ip(self) -> None:
        if self._busy:
            return
        ip = self.ed_eth_ip.text().strip()
        mask = self.ed_eth_mask.text().strip() or "255.255.255.0"
        if not ip:
            QMessageBox.critical(self, "错误", "请填写要附加的 IP")
            return
        self._persist()

        def work() -> None:
            self._ui(lambda: self._set_busy(True, "添加网卡 IP…"))
            status, msg = netip.add_ethernet_ipv4(ip, mask, on_line=lambda line: self.sig_log.emit(line))

            def done() -> None:
                self._append_log(f"[net] {msg}")
                self._refresh_eth_list()
                self._set_busy(False, "就绪" if status in ("ok", "exists") else f"失败: {msg}")
                if status in ("ok", "exists"):
                    QMessageBox.information(self, "网卡 IP", msg)
                else:
                    QMessageBox.critical(self, "网卡 IP", msg)

            self._ui(done)

        threading.Thread(target=work, daemon=True).start()

    def _on_remove_eth_ip(self) -> None:
        if self._busy:
            return
        pick = self.eth_combo.currentText().strip()
        if not pick:
            QMessageBox.information(self, "提示", "请先在列表中选一个要删除的地址")
            return
        ip = pick.split()[0]
        if (
            QMessageBox.question(self, "确认", f"从有线网卡删除附加地址 {ip}？")
            != QMessageBox.StandardButton.Yes
        ):
            return

        def work() -> None:
            self._ui(lambda: self._set_busy(True, "删除网卡 IP…"))
            status, msg = netip.remove_ethernet_ipv4(ip, on_line=lambda line: self.sig_log.emit(line))

            def done() -> None:
                self._append_log(f"[net] {msg}")
                self._refresh_eth_list()
                self._set_busy(False, "就绪" if status == "ok" else f"失败: {msg}")
                if status == "ok":
                    QMessageBox.information(self, "网卡 IP", msg)
                else:
                    QMessageBox.critical(self, "网卡 IP", msg)

            self._ui(done)

        threading.Thread(target=work, daemon=True).start()

    def _share_open_local(self) -> None:
        url = self._share.local_url()
        if not url:
            QMessageBox.information(self, "提示", "请先启动共享")
            return
        ok, detail = self._share.probe_local()
        self._append_log(f"[http] 打开前自检: {detail}")
        if not ok:
            QMessageBox.warning(
                self,
                "本机自检失败",
                f"{detail}\n\n服务进程可能未真正响应，或端口冲突。请换端口后重试。",
            )
            return
        try:
            os.startfile(url)  # noqa: S606
        except OSError as e:
            QMessageBox.critical(self, "错误", f"无法打开浏览器: {e}")

    def _share_probe_local(self) -> None:
        if not self._share.running:
            QMessageBox.information(self, "提示", "请先启动共享")
            return
        ok, detail = self._share.probe_local()
        self._append_log(f"[http] 自检: {detail}")
        if ok:
            QMessageBox.information(self, "自检通过", f"本机服务正常（已绕过系统代理）。\n{detail}")
        else:
            QMessageBox.critical(
                self,
                "自检失败",
                f"{detail}\n\n可换端口（如 18080）后重试；浏览器打不开时请让代理绕过 localhost。",
            )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_env_responsive(event.size().width())

    def _apply_env_responsive(self, width: int) -> None:
        host = getattr(self, "_preset_host", None)
        if host is not None and hasattr(host, "update_responsive_layout"):
            host.update_responsive_layout(width)
        self._apply_env_cols_layout(width)

    def _apply_env_cols_layout(self, width: int) -> None:
        if not hasattr(self, "_env_cols_host"):
            return
        mode = "desktop" if width >= 900 else "mobile"
        if getattr(self, "_env_cols_mode", None) == mode:
            return
        self._env_cols_mode = mode
        old = self._env_cols_host.layout()
        if old is not None:
            old.removeWidget(self._env_left_col)
            old.removeWidget(self._env_right_col)
            QWidget().setLayout(old)
        if mode == "desktop":
            lay = QHBoxLayout(self._env_cols_host)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)
            lay.addWidget(self._env_left_col, 3)
            lay.addWidget(self._env_right_col, 2)
        else:
            lay = QVBoxLayout(self._env_cols_host)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)
            lay.addWidget(self._env_left_col)
            lay.addWidget(self._env_right_col)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist()
        try:
            self._share.stop()
        except Exception:
            pass
        event.accept()

    # ------------------------------------------------------------------ 环境导入导出
    def _on_export_env(self) -> None:
        if self._busy:
            return
        if not self._confirm_distro():
            return
        distro = self._distro_text()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出交叉编译环境包",
            f"{distro}-cross-env.tar.gz",
            "环境包 (*.tar.gz);;未压缩 tar (*.tar);;全部 (*.*)",
        )
        if not path:
            return
        slim = bool(self.chk_env_slim.isChecked())
        tip = (
            "将导出完整 WSL 发行版（含已安装的 Qt、sysroot、FFmpeg、交叉编译器）。\n"
            + ("另：会删除 /opt/qt5142-cross 源码缓存以减小体积，不影响交叉编译。\n" if slim else "")
            + "体积可能数 GB，耗时较长。继续？"
        )
        if QMessageBox.question(self, "导出环境包", tip) != QMessageBox.StandardButton.Yes:
            return
        self._persist()
        self._show_log_tab()
        low = path.lower()
        compress = low.endswith(".tar.gz") or low.endswith(".tgz") or not low.endswith(".tar")
        jobs.begin()
        self._set_busy(True, "导出环境包…")

        def work() -> None:
            code = envpack.export_distro(
                path,
                distro=distro,
                slim=slim,
                compress=compress,
                on_line=lambda line: self.sig_log.emit(line),
            )

            def done() -> None:
                self._append_log(f"[env] 导出结束 exit={code}")
                msg = self._busy_result_msg(code, "导出成功", "导出失败")
                self._set_busy(False, msg)
                if code not in (0, jobs.CANCELLED):
                    QMessageBox.critical(self, "导出失败", self._fail_summary_from_log())

            self._ui(done)

        threading.Thread(target=work, daemon=True).start()

    def _on_import_env(self) -> None:
        if self._busy:
            return
        if not self._confirm_distro():
            return
        distro = self._distro_text()
        archive, _ = QFileDialog.getOpenFileName(
            self,
            "选择环境包",
            "",
            "环境包 (*.tar.gz *.tgz *.tar);;全部 (*.*)",
        )
        if not archive:
            return
        install_dir = self.ed_env_install.text().strip()
        if not install_dir:
            QMessageBox.critical(self, "错误", "请填写导入安装目录")
            return
        replace = bool(self.chk_env_replace.isChecked())
        if wsl_setup.wsl_usable() and wsl.distro_exists(distro) and not replace:
            if (
                QMessageBox.question(
                    self,
                    "已有同名环境",
                    f"本机已有发行版「{distro}」。\n是否覆盖后重新导入？",
                )
                == QMessageBox.StandardButton.Yes
            ):
                replace = True
                self.chk_env_replace.setChecked(True)
            else:
                return
        tip = (
            "将自动：启用 WSL（如需要）→ 导入交叉环境。\n"
            f"发行版：{distro}\n安装到：{install_dir}\n"
            "启用 WSL 时可能弹出 UAC，请点「是」。\n"
        )
        need = envpack.estimate_import_need_bytes(Path(archive))
        free = envpack.free_bytes(install_dir)
        if free is not None:
            tip += f"目标盘剩余约 {free / (1024**3):.1f} GB（建议至少约 {need / (1024**3):.1f} GB）。\n"
            if free < need:
                tip += "空间可能不足，导入可能失败。\n"
        tip += "继续？"
        if QMessageBox.question(self, "一键导入环境包", tip) != QMessageBox.StandardButton.Yes:
            return
        self._persist()
        self._start_import(archive, install_dir, distro, replace)

    def _start_import(self, archive: str, install_dir: str, distro: str, replace: bool) -> None:
        self._select_step(1)
        jobs.begin()
        self._set_busy(True, "准备 WSL / 导入环境…")

        def work() -> None:
            code = envpack.import_distro(
                archive,
                install_dir,
                distro=distro,
                replace=replace,
                set_default=True,
                auto_enable_wsl=True,
                on_line=lambda line: self.sig_log.emit(line),
            )

            def done() -> None:
                self._append_log(f"[env] 导入结束 exit={code}")
                if code == jobs.CANCELLED:
                    self._set_busy(False, "已取消")
                    return
                if code == 2:
                    settings.save(
                        {
                            "pending_import_archive": archive,
                            "pending_import_dir": install_dir,
                            "pending_import_distro": distro,
                            "pending_import_replace": replace,
                        }
                    )
                    self._set_busy(False, "请重启后再打开本工具")
                    QMessageBox.information(
                        self,
                        "需要重启",
                        "已尝试启用 WSL，但需要重启 Windows 一次才能继续。\n\n"
                        "请重启电脑，然后重新打开本工具——会自动接着导入刚才选中的环境包。",
                    )
                elif code == 0:
                    self._clear_pending_import()
                    self._set_busy(False, "导入成功")
                    QMessageBox.information(
                        self, "导入成功", "环境已导入，正在自动检测。通过后即可去「2 编译」。"
                    )
                    self._on_detect()
                else:
                    self._set_busy(False, f"导入失败 exit={code}")
                    QMessageBox.critical(
                        self,
                        "导入失败",
                        self._fail_summary_from_log() + "\n\n若取消了 UAC，请再点一次「一键导入」。",
                    )

            self._ui(done)

        threading.Thread(target=work, daemon=True).start()

    def _clear_pending_import(self) -> None:
        settings.save(
            {
                "pending_import_archive": "",
                "pending_import_dir": "",
                "pending_import_distro": "",
                "pending_import_replace": False,
            }
        )

    def _maybe_resume_pending_import(self) -> None:
        cfg = settings.load()
        archive = (cfg.get("pending_import_archive") or "").strip()
        if not archive:
            return
        install_dir = (cfg.get("pending_import_dir") or "").strip() or self.ed_env_install.text().strip()
        distro = (cfg.get("pending_import_distro") or "").strip() or self._distro_text()
        replace = bool(cfg.get("pending_import_replace", False))
        if not Path(archive).is_file():
            self._append_log(f"[env] 待续导入的环境包已不存在: {archive}")
            self._clear_pending_import()
            return
        if (
            QMessageBox.question(
                self,
                "继续导入",
                "检测到上次因启用 WSL 需要重启，导入尚未完成。\n\n"
                f"环境包：{archive}\n是否现在继续导入？",
            )
            != QMessageBox.StandardButton.Yes
        ):
            if (
                QMessageBox.question(
                    self, "放弃", "是否清除「待续导入」记录？（以后需手动再选文件）"
                )
                == QMessageBox.StandardButton.Yes
            ):
                self._clear_pending_import()
            return
        self.ed_env_install.setText(install_dir)
        self.ed_distro.setText(distro)
        self.chk_env_replace.setChecked(replace)
        self._start_import(archive, install_dir, distro, replace)

    def _on_detect(self) -> None:
        if self._busy:
            return
        if not self._confirm_distro():
            return
        jobs.begin()
        self._set_busy(True, "检测环境")
        self._append_log("==== 开始检测环境 ====")
        self._append_log("[detect] 准备调用 WSL（可能稍慢，请看底栏进度）…")
        self._set_env_box("检测中…")
        self._start_detect_spin()

        def work() -> None:
            report = detect.detect(
                self._distro_text(),
                on_line=lambda line: self.sig_log.emit(line),
            )

            def ui() -> None:
                self._stop_detect_spin()
                if jobs.is_cancelled():
                    self._set_env_box("已取消")
                    self._set_busy(False, "已取消")
                    return
                lines = []
                for it in report.items:
                    mark = "OK" if it.ok else "缺"
                    lines.append(f"[{mark}] {it.label}")
                    if not it.ok and it.fix:
                        lines.append(f"      → {it.fix}")
                self._set_env_box("\n".join(lines) or "(无结果)")
                self._apply_env_ready(report.ready)
                self._append_log("==== 检测结束 ====")
                self._set_busy(False, "环境就绪" if report.ready else "环境不完整")
                if report.ready:
                    self._show_toast("环境全面检测完成：aarch64 交叉编译器与 Qt 库正常！")
                else:
                    self._show_toast("环境检测完成：部分组件缺失，请导入环境包。")

            self._ui(ui)

        threading.Thread(target=work, daemon=True).start()

    def _on_install(self, script: str) -> None:
        if self._busy:
            return
        if (
            QMessageBox.question(self, "确认", f"将以 WSL root 执行 tools/{script}，可能较久。继续？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self._show_log_tab()
        jobs.begin()
        self._set_busy(True, f"安装: {script}")

        def work() -> None:
            code = buildmod.run_install(
                script,
                distro=self._distro_text(),
                on_line=lambda line: self.sig_log.emit(line),
            )

            def done() -> None:
                msg = self._busy_result_msg(code, f"安装结束 exit={code}", "安装失败")
                if code == 0:
                    msg = "安装成功"
                self._set_busy(False, msg)
                if code not in (0, jobs.CANCELLED):
                    QMessageBox.critical(self, "安装失败", self._fail_summary_from_log())

            self._ui(done)

        threading.Thread(target=work, daemon=True).start()

    def _on_build(self) -> None:
        if self._busy:
            return
        if not self._env_ready:
            if (
                QMessageBox.question(self, "环境未就绪", "交叉环境尚未就绪。是否前往「1 环境」导入/检测？")
                == QMessageBox.StandardButton.Yes
            ):
                self._select_step(0)
            return
        proj = self._project_text()
        if not proj or not Path(proj).is_dir():
            QMessageBox.critical(self, "错误", "请先选择有效的工程目录")
            return
        kind, bfile = self._parse_build_combo()
        if not bfile:
            QMessageBox.critical(self, "错误", "请选择 .pro 或 CMakeLists.txt")
            return
        self._persist()
        jobs.begin()
        self._set_busy(True, "交叉编译中…")
        self._append_log("==== 开始编译 ====")

        def work() -> None:
            code = buildmod.build(
                project=proj,
                build_system=kind,
                build_file=bfile,
                app_name=self._app_name,
                out_bin=self._out_bin,
                jobs=int(self._jobs_n or 0),
                do_bundle=bool(self._do_bundle),
                plugins=self._plugins,
                extra_pkgconfig=self._extra_pkg,
                extra_copy=self._extra_copy,
                use_ffmpeg=bool(self._use_ffmpeg),
                build_mode=self._build_mode,
                use_ccache=bool(self._use_ccache),
                out_dir=self._out_dir_text(),
                clean=bool(self._do_clean),
                distro=self._distro_text(),
                on_line=lambda line: self.sig_log.emit(line),
            )

            def done() -> None:
                self._append_log(f"==== 结束 exit={code} ====")
                msg = self._busy_result_msg(code, "成功", "失败")
                self._set_busy(False, msg)
                if code == 0:
                    self._after_build_ok()
                elif code != jobs.CANCELLED:
                    QMessageBox.critical(self, "编译失败", self._fail_summary_from_log())

            self._ui(done)

        threading.Thread(target=work, daemon=True).start()

    def _after_build_ok(self) -> None:
        out = self._out_dir_text()
        if out and Path(out).is_dir():
            self.ed_share_dir.setText(out)
        else:
            self._fill_share_from_project()
            out = self.ed_share_dir.text().strip() or self._out_dir_text()
        tip = "编译成功。"
        if out:
            tip += f"\n产物目录：\n{out}"
            try:
                tars = sorted(Path(out).glob("*_bundle.tar.gz"))
                if tars:
                    tip += f"\n运行包：{tars[-1].name}"
            except OSError:
                pass
        tip += "\n\n是否前往「3 共享」启动下载服务？"
        if QMessageBox.question(self, "编译成功", tip) == QMessageBox.StandardButton.Yes:
            self._select_step(2)

    def _open_out(self) -> None:
        out = self._out_dir_text()
        if out and Path(out).is_dir():
            os.startfile(out)  # noqa: S606
            return
        proj = Path(self._project_text())
        name = self._app_name.strip()
        candidates = []
        if name:
            candidates.append(proj / "dist" / "arm64-kylin" / name)
        candidates += [
            proj / "dist" / "arm64-kylin",
            proj / "dist",
            proj / "bin" / "release",
            proj / "build-arm64",
            proj,
        ]
        for c in candidates:
            if c.is_dir():
                if not self._out_dir_text():
                    self.ed_out_dir.setText(str(c))
                os.startfile(str(c))  # noqa: S606
                return
        QMessageBox.information(self, "提示", "尚未找到产物文件夹（通常在工程下的 dist/arm64-kylin）")

    def _copy_log(self) -> None:
        QApplication.clipboard().setText(self.log.toPlainText())
        self._status_lbl.setText("日志已复制")


def main() -> None:
    import sys

    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
