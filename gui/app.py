"""主界面：环境管理、交叉编译、HTTP 共享、日志（PySide6）。"""
from __future__ import annotations

import os
import threading
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QMouseEvent, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
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

from crosskit import build as buildmod
from crosskit import detect, envpack, jobs, netip, settings, wsl, wsl_setup
from crosskit.httpshare import DirectoryShare, ensure_firewall_allow, ethernet_ipv4, guess_share_dir
from gui.chrome import EdgeResizer, TitleChrome
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
    lay.setContentsMargins(12, 12, 12, 12)
    lay.setSpacing(10)
    area.setWidget(inner)
    # 外层包一层，方便塞进 stacked
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

        QTimer.singleShot(600, self._maybe_resume_pending_import)
        QTimer.singleShot(200, self._refresh_eth_list)
        QTimer.singleShot(500, lambda: self._on_detect(auto=True))

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

        page_compile = QWidget()
        self._build_tab_compile(page_compile)
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
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(16, 10, 16, 8)
        lay.setSpacing(8)
        self._step_cards: list[QFrame] = []
        self._step_num_lbls: list[QLabel] = []
        specs = [
            ("1", "环境管理", "导入 / 检测交叉环境"),
            ("2", "交叉编译", "选工程 · 产物 · 日志"),
            ("3", "部署与共享", "HTTP 共享给麒麟机"),
        ]
        for i, (num, name, desc) in enumerate(specs):
            card = QFrame()
            card.setObjectName("StepIdle")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setMinimumHeight(56)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(10)
            badge = QLabel(num)
            badge.setFixedSize(26, 26)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background:{C['surface2']}; color:{C['muted']}; border-radius:8px; font-weight:700; font-size:11px;"
            )
            self._step_num_lbls.append(badge)
            texts = QVBoxLayout()
            texts.setSpacing(1)
            n = QLabel(name)
            n.setObjectName("CardTitle")
            d = QLabel(desc)
            d.setObjectName("Muted")
            texts.addWidget(n)
            texts.addWidget(d)
            cl.addWidget(badge)
            cl.addLayout(texts, 1)
            card.mousePressEvent = lambda _e, idx=i: self._select_step(idx)  # type: ignore[method-assign]
            lay.addWidget(card, 1)
            self._step_cards.append(card)

        self._flow_hint = QLabel("当前流程：检测环境…")
        self._flow_hint.setObjectName("FlowHint")
        self._flow_hint.setWordWrap(True)
        self._flow_hint.setMinimumWidth(200)
        self._flow_hint.setMaximumWidth(280)
        lay.addWidget(self._flow_hint, 0, Qt.AlignmentFlag.AlignVCenter)
        return wrap

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
                    f"background:{C['accent']}; color:white; border-radius:8px; font-weight:700; font-size:11px;"
                )
            elif self._env_ready and i == 0:
                badge.setText("✓")
                badge.setStyleSheet(
                    f"background:rgba(16,185,129,0.2); color:{C['ok']}; border-radius:8px; font-weight:700;"
                )
            else:
                badge.setText(str(i + 1))
                badge.setStyleSheet(
                    f"background:{C['surface2']}; color:{C['muted']}; border-radius:8px; font-weight:700; font-size:11px;"
                )
        self._refresh_flow_hint()

    def _refresh_flow_hint(self) -> None:
        if not hasattr(self, "_flow_hint"):
            return
        if self._current_step == 0:
            tip = "已完成 WSL 工具链预检 → 随时可编译" if self._env_ready else "请先导入 / 检测环境包"
        elif self._current_step == 1:
            tip = "工程已装载 → 点击开始交叉编译"
        else:
            tip = "HTTP 共享运行中" if self._share.running else "服务器就绪，一键启动板端共享"
        self._flow_hint.setText(f"当前流程：{tip}")

    def _build_footer(self, parent_lay: QVBoxLayout) -> None:
        foot = QFrame()
        foot.setObjectName("AppFooter")
        foot.setFixedHeight(34)
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
        hl.setContentsMargins(16, 14, 16, 14)
        hl.setSpacing(14)

        icon = QLabel("!")
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background:{C['surface2']}; color:{C['warn']}; border-radius:12px; font-size:18px; font-weight:700;"
        )
        self._env_hero_icon = icon
        hl.addWidget(icon)

        mid = QVBoxLayout()
        mid.setSpacing(4)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("本机 WSL2 交叉编译环境状态")
        title.setObjectName("CardTitle")
        title_row.addWidget(title)
        self._env_hero_badge = QLabel("检测中…")
        self._env_hero_badge.setObjectName("EnvBadgeIdle")
        title_row.addWidget(self._env_hero_badge)
        title_row.addStretch(1)
        mid.addLayout(title_row)
        ban = QLabel("正在检测交叉环境…")
        ban.setWordWrap(True)
        ban.setObjectName("Muted")
        mid.addWidget(ban)
        self._env_banner_labels.append(ban)
        self._env_hint_lbl = QLabel("")
        self._env_hint_lbl.setObjectName("Muted")
        self._env_hint_lbl.setWordWrap(True)
        mid.addWidget(self._env_hint_lbl)
        hl.addLayout(mid, 1)

        actions = QVBoxLayout()
        actions.setSpacing(8)
        b_redetect = _btn("重新检测环境")
        b_redetect.clicked.connect(lambda: self._on_detect(False))
        self._track_action(b_redetect)
        actions.addWidget(b_redetect)
        self._btn_go_compile = _btn("前往「2 交叉编译」 →", "Primary")
        self._btn_go_compile.clicked.connect(lambda: self._select_step(1))
        self._btn_go_compile.setEnabled(False)
        actions.addWidget(self._btn_go_compile)
        hl.addLayout(actions)
        self._refresh_env_hint()
        lay.addWidget(hero)

        body = QHBoxLayout()
        body.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(10)
        right = QVBoxLayout()
        right.setSpacing(10)

        envp, env_lay = _card("交叉编译环境包")
        row0 = QHBoxLayout()
        row0.addWidget(_field_label("安装目录"))
        self.ed_env_install = QLineEdit(self._env_install_dir)
        self.ed_env_install.textChanged.connect(lambda t: self._on_field("env_install", t))
        self._track_form(self.ed_env_install)
        row0.addWidget(self.ed_env_install, 1)
        b_br = _btn("浏览…")
        b_br.clicked.connect(self._browse_env_install)
        row0.addWidget(b_br)
        env_lay.addLayout(row0)

        row1 = QHBoxLayout()
        row1.addWidget(_field_label("发行版名"))
        self.ed_distro = QLineEdit(self._distro)
        self.ed_distro.textChanged.connect(lambda t: self._on_field("distro", t))
        self._track_form(self.ed_distro)
        row1.addWidget(self.ed_distro, 1)
        hint = QLabel("一般保持 Ubuntu-20.04")
        hint.setObjectName("Muted")
        row1.addWidget(hint)
        env_lay.addLayout(row1)

        opts = QHBoxLayout()
        opts.addSpacing(76)
        self.chk_env_slim = QCheckBox("导出时去掉 Qt 源码缓存")
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
        brow.addSpacing(76)
        b_imp = _btn("一键导入环境包…", "Primary")
        b_imp.clicked.connect(self._on_import_env)
        self._track_action(b_imp)
        brow.addWidget(b_imp)
        self._btn_download = _btn("下载环境包", "Accent")
        self._btn_download.clicked.connect(self._open_env_release)
        brow.addWidget(self._btn_download)
        b_det = _btn("检测环境")
        b_det.clicked.connect(lambda: self._on_detect(False))
        self._track_action(b_det)
        brow.addWidget(b_det)
        b_exp = _btn("导出…")
        b_exp.clicked.connect(self._on_export_env)
        self._track_action(b_exp)
        brow.addWidget(b_exp)
        brow.addStretch(1)
        env_lay.addLayout(brow)
        left.addWidget(envp)

        self._scratch_btn = QToolButton()
        self._scratch_btn.setText("从零搭建 ▸")
        self._scratch_btn.setObjectName("Accent")
        self._scratch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scratch_btn.clicked.connect(self._toggle_scratch)
        left.addWidget(self._scratch_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self._scratch = QWidget()
        self._scratch.setVisible(False)
        sc_lay = QVBoxLayout(self._scratch)
        sc_lay.setContentsMargins(0, 0, 0, 0)
        rare, rare_lay = _card("从零搭建")
        tip2 = QLabel("无现成环境包、或要本机重编工具链/Qt 时再用。有包请直接导入。")
        tip2.setObjectName("Muted")
        tip2.setWordWrap(True)
        rare_lay.addWidget(tip2)
        r2 = QHBoxLayout()
        b_tc = _btn("安装工具链")
        b_tc.clicked.connect(lambda: self._on_install("setup_cross_focal.sh"))
        self._track_action(b_tc)
        r2.addWidget(b_tc)
        b_qt = _btn("编译 Qt 5.14.2")
        b_qt.clicked.connect(lambda: self._on_install("build_qt5142_arm64_cross.sh"))
        self._track_action(b_qt)
        r2.addWidget(b_qt)
        r2.addStretch(1)
        rare_lay.addLayout(r2)
        sc_lay.addWidget(rare)
        left.addWidget(self._scratch)
        left.addStretch(1)

        tool, tool_lay = _card("工具链及 SYSROOT 明细")
        for k, v in (
            ("目标架构", "Linux ARM64 (aarch64)"),
            ("交叉编译器", "aarch64-linux-gnu-gcc 9.4"),
            ("Qt 目标库", "Qt 5.14.2"),
            ("配套工具", "readelf / pkg-config / ccache"),
        ):
            row = QHBoxLayout()
            kk = QLabel(k)
            kk.setObjectName("FieldLabel")
            kk.setFixedWidth(72)
            vv = QLabel(v)
            row.addWidget(kk)
            row.addWidget(vv, 1)
            tool_lay.addLayout(row)
        right.addWidget(tool)

        res, res_lay = _card("环境检测结果")
        self.env_box = QTextEdit()
        self.env_box.setReadOnly(True)
        self.env_box.setObjectName("Log")
        self.env_box.setMinimumHeight(160)
        self.env_box.setPlaceholderText("检测结果将显示在这里…")
        res_lay.addWidget(self.env_box)
        right.addWidget(res)
        right.addStretch(1)

        body.addLayout(left, 3)
        body.addLayout(right, 2)
        lay.addLayout(body)

    # ------------------------------------------------------------------ 编译页
    def _build_tab_compile(self, parent: QWidget) -> None:
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(8)

        ban_row = QHBoxLayout()
        ban = QLabel("正在检测交叉环境…")
        ban.setWordWrap(True)
        ban.setStyleSheet(f"font-weight:700; color:{C['muted']};")
        ban_row.addWidget(ban, 1)
        self._env_banner_labels.append(ban)
        b_go_env = _btn("去环境页", "Accent")
        b_go_env.clicked.connect(lambda: self._select_step(0))
        ban_row.addWidget(b_go_env)
        outer.addLayout(ban_row)

        proj, proj_lay = _card("工程")
        r0 = QHBoxLayout()
        r0.addWidget(_field_label("工程目录"))
        self.ed_project = QLineEdit(self._project)
        self.ed_project.textChanged.connect(lambda t: self._on_field("project", t))
        self._track_form(self.ed_project)
        r0.addWidget(self.ed_project, 1)
        b_bp = _btn("浏览…")
        b_bp.clicked.connect(self._browse_project)
        r0.addWidget(b_bp)
        recent = self._cfg.get("recent_projects") or []
        if recent:
            self.cmb_recent = QComboBox()
            self.cmb_recent.addItem("最近…")
            for p in recent:
                self.cmb_recent.addItem(p)
            self.cmb_recent.activated.connect(self._on_recent_picked)
            r0.addWidget(self.cmb_recent)
        proj_lay.addLayout(r0)

        r1 = QHBoxLayout()
        r1.addWidget(_field_label("构建文件"))
        self.build_combo = QComboBox()
        self.build_combo.setEditable(True)
        self.build_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if self._build_file:
            self.build_combo.setEditText(self._build_file)
        self.build_combo.currentTextChanged.connect(lambda t: self._on_field("build_file", t))
        self._track_form(self.build_combo)
        r1.addWidget(self.build_combo, 1)
        b_ref = _btn("刷新")
        b_ref.clicked.connect(self._refresh_build_files)
        r1.addWidget(b_ref)
        proj_lay.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(_field_label("产物目录"))
        self.ed_out_dir = QLineEdit(self._out_dir)
        self.ed_out_dir.textChanged.connect(lambda t: self._on_field("out_dir", t))
        self._track_form(self.ed_out_dir)
        r2.addWidget(self.ed_out_dir, 1)
        b_bo = _btn("浏览…")
        b_bo.clicked.connect(self._browse_out_dir)
        r2.addWidget(b_bo)
        proj_lay.addLayout(r2)
        outer.addWidget(proj)

        opts, opts_lay = _card("选项")
        flags = QHBoxLayout()
        self.chk_bundle = QCheckBox("生成运行包")
        self.chk_bundle.setChecked(self._do_bundle)
        self.chk_bundle.toggled.connect(lambda v: self._on_field("do_bundle", v))
        self._track_form(self.chk_bundle)
        flags.addWidget(self.chk_bundle)
        self.chk_ffmpeg = QCheckBox("附加 FFmpeg")
        self.chk_ffmpeg.setChecked(self._use_ffmpeg)
        self.chk_ffmpeg.toggled.connect(lambda v: self._on_field("use_ffmpeg", v))
        self._track_form(self.chk_ffmpeg)
        flags.addWidget(self.chk_ffmpeg)
        self.chk_clean = QCheckBox("全量清理")
        self.chk_clean.setChecked(self._do_clean)
        self.chk_clean.toggled.connect(lambda v: self._on_field("do_clean", v))
        self._track_form(self.chk_clean)
        flags.addWidget(self.chk_clean)
        self._adv_btn = _btn("高级 ▸", "Accent")
        self._adv_btn.clicked.connect(self._toggle_advanced)
        flags.addWidget(self._adv_btn)
        flags.addStretch(1)
        opts_lay.addLayout(flags)

        self._adv = QWidget()
        self._adv.setVisible(False)
        adv_lay = QVBoxLayout(self._adv)
        adv_lay.setContentsMargins(0, 8, 0, 0)

        sys_row = QHBoxLayout()
        sys_row.addWidget(QLabel("构建系统"))
        self._sys_group = QButtonGroup(self)
        for v, t in (("auto", "自动"), ("qmake", "qmake"), ("cmake", "CMake")):
            rb = QRadioButton(t)
            rb.setChecked(self._build_system == v)
            rb.toggled.connect(lambda on, val=v: on and self._on_field("build_system", val))
            self._sys_group.addButton(rb)
            self._track_form(rb)
            sys_row.addWidget(rb)
        sys_row.addStretch(1)
        adv_lay.addLayout(sys_row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("应用名"))
        self.ed_app_name = QLineEdit(self._app_name)
        self.ed_app_name.setMaximumWidth(160)
        self.ed_app_name.textChanged.connect(lambda t: self._on_field("app_name", t))
        self._track_form(self.ed_app_name)
        name_row.addWidget(self.ed_app_name)
        name_row.addWidget(QLabel("可执行文件"))
        self.ed_out_bin = QLineEdit(self._out_bin)
        self.ed_out_bin.textChanged.connect(lambda t: self._on_field("out_bin", t))
        self._track_form(self.ed_out_bin)
        name_row.addWidget(self.ed_out_bin, 1)
        adv_lay.addLayout(name_row)
        mute = QLabel("留空则自动查找")
        mute.setObjectName("Muted")
        adv_lay.addWidget(mute)

        jobs_row = QHBoxLayout()
        jobs_row.addWidget(QLabel("并行 -j"))
        self.sp_jobs = QSpinBox()
        self.sp_jobs.setRange(0, 64)
        self.sp_jobs.setValue(self._jobs_n)
        self.sp_jobs.valueChanged.connect(lambda v: self._on_field("jobs", v))
        self._track_form(self.sp_jobs)
        jobs_row.addWidget(self.sp_jobs)
        jh = QLabel("0=自动")
        jh.setObjectName("Muted")
        jobs_row.addWidget(jh)
        jobs_row.addStretch(1)
        adv_lay.addLayout(jobs_row)

        for label, attr, key in (
            ("插件", "_plugins", "plugins"),
            ("其他 pkg-config", "_extra_pkg", "extra_pkg"),
            ("额外复制", "_extra_copy", "extra_copy"),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            ed = QLineEdit(getattr(self, attr))
            ed.textChanged.connect(lambda t, k=key: self._on_field(k, t))
            self._track_form(ed)
            setattr(self, f"ed_{key}", ed)
            row.addWidget(ed, 1)
            adv_lay.addLayout(row)

        opts_lay.addWidget(self._adv)
        outer.addWidget(opts)

        actions = QHBoxLayout()
        self._btn_build = _btn("开始交叉编译 (aarch64)", "Primary")
        self._btn_build.clicked.connect(self._on_build)
        self._btn_build.setEnabled(False)
        self._track_action(self._btn_build)
        actions.addWidget(self._btn_build)
        b_out = _btn("打开产物文件夹")
        b_out.clicked.connect(self._open_out)
        self._track_action(b_out)
        actions.addWidget(b_out)
        b_share = _btn("去共享", "Accent")
        b_share.clicked.connect(lambda: self._select_step(2))
        self._track_action(b_share)
        actions.addWidget(b_share)
        actions.addStretch(1)
        b_clear = _btn("清空")
        b_clear.clicked.connect(self._clear_log)
        actions.addWidget(b_clear)
        b_copy = _btn("复制日志")
        b_copy.clicked.connect(self._copy_log)
        self._track_action(b_copy, keep_when_busy=True)
        actions.addWidget(b_copy)
        outer.addLayout(actions)

        log_card, log_lay = _card("构建日志")
        meta = QHBoxLayout()
        self._log_count_lbl = QLabel("0 行")
        self._log_count_lbl.setObjectName("Muted")
        meta.addWidget(self._log_count_lbl)
        meta.addStretch(1)
        self.chk_autoscroll = QCheckBox("自动滚动")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.toggled.connect(lambda v: setattr(self, "_log_auto_scroll", v))
        meta.addWidget(self.chk_autoscroll)
        log_lay.addLayout(meta)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("Log")
        self.log.setMinimumHeight(220)
        log_lay.addWidget(self.log, 1)
        outer.addWidget(log_card, 1)

    # ------------------------------------------------------------------ 共享页
    def _build_tab_share(self, lay: QVBoxLayout) -> None:
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
    def _toggle_advanced(self) -> None:
        self._advanced_open = not self._advanced_open
        self._adv.setVisible(self._advanced_open)
        self._adv_btn.setText("高级 ▾" if self._advanced_open else "高级 ▸")

    def _toggle_scratch(self) -> None:
        self._scratch_open = not self._scratch_open
        self._scratch.setVisible(self._scratch_open)
        self._scratch_btn.setText("从零搭建 ▾" if self._scratch_open else "从零搭建 ▸")

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
            # 编译按钮另由 _sync_build_enabled 管
            if b is getattr(self, "_btn_build", None):
                continue
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
        on = (not self._busy) and self._env_ready
        if hasattr(self, "_btn_build"):
            self._btn_build.setEnabled(on)
        if self._chrome is not None:
            self._chrome.set_quick_enabled(on)

    def _clear_log(self) -> None:
        self.log.clear()
        self._log_line_count = 0
        self._log_count_lbl.setText("0 行")

    def _set_env_box(self, text: str) -> None:
        self.env_box.setPlainText(text)

    def _apply_env_ready(self, ready: bool) -> None:
        self._env_ready = ready
        if ready:
            text = "检测到完整的 WSL2 交叉编译镜像。已预装 aarch64 工具链与 Qt 5.14.2，可直接编译。"
            fg = C["ok"]
            badge = "环境就绪 — 可直接编译"
            badge_obj = "EnvBadgeOk"
            hero_obj = "HeroBanner"
            icon_txt, icon_fg = "✓", C["ok"]
            if hasattr(self, "_footer_wsl"):
                self._footer_wsl.setText(f"WSL2 {self._distro_text()} (aarch64)")
        else:
            text = "环境未就绪 — 请先下载并导入环境包"
            fg = C["err"]
            badge = "环境未就绪"
            badge_obj = "EnvBadgeBad"
            hero_obj = "HeroBannerBad"
            icon_txt, icon_fg = "!", C["warn"]
            if hasattr(self, "_footer_wsl"):
                self._footer_wsl.setText("WSL2 环境未就绪")
        if self._chrome is not None:
            self._chrome.set_env_ready(ready, self._distro_text())
        if hasattr(self, "_env_hero"):
            self._env_hero.setObjectName(hero_obj)
            self._env_hero.style().unpolish(self._env_hero)
            self._env_hero.style().polish(self._env_hero)
        if hasattr(self, "_env_hero_icon"):
            self._env_hero_icon.setText(icon_txt)
            self._env_hero_icon.setStyleSheet(
                f"background:{C['surface2']}; color:{icon_fg}; border-radius:12px; font-size:18px; font-weight:700;"
            )
        if hasattr(self, "_env_hero_badge"):
            self._env_hero_badge.setText(badge)
            self._env_hero_badge.setObjectName(badge_obj)
            self._env_hero_badge.style().unpolish(self._env_hero_badge)
            self._env_hero_badge.style().polish(self._env_hero_badge)
        if hasattr(self, "_btn_go_compile"):
            self._btn_go_compile.setEnabled(ready and not self._busy)
        for lbl in self._env_banner_labels:
            lbl.setText(text)
            lbl.setStyleSheet(f"color:{fg};")
        self._refresh_env_hint()
        self._refresh_flow_hint()
        # 只刷新步骤角标，避免重复切页
        if hasattr(self, "_step_cards") and hasattr(self, "_step_num_lbls"):
            for i, badge in enumerate(self._step_num_lbls):
                active = i == self._current_step
                if active:
                    badge.setText(str(i + 1))
                    badge.setStyleSheet(
                        f"background:{C['accent']}; color:white; border-radius:8px; font-weight:700; font-size:11px;"
                    )
                elif ready and i == 0:
                    badge.setText("✓")
                    badge.setStyleSheet(
                        f"background:rgba(16,185,129,0.2); color:{C['ok']}; border-radius:8px; font-weight:700;"
                    )
                else:
                    badge.setText(str(i + 1))
                    badge.setStyleSheet(
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

    # ------------------------------------------------------------------ 工程 / 浏览
    def _on_recent_picked(self, idx: int) -> None:
        if idx <= 0:
            return
        path = self.cmb_recent.itemText(idx)
        if path:
            self._set_project(path)

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

    def _on_detect(self, auto: bool = False) -> None:
        if self._busy:
            return
        if not auto and not self._confirm_distro():
            return
        if not auto:
            self._select_step(1)
        jobs.begin()
        self._set_busy(True, "检测环境")
        if not auto:
            self._append_log("==== 开始检测环境 ====")
            self._append_log("[detect] 准备调用 WSL（可能稍慢，请看底栏进度）…")
        self._set_env_box("检测中…")

        def work() -> None:
            report = detect.detect(
                self._distro_text(),
                on_line=None if auto else (lambda line: self.sig_log.emit(line)),
            )

            def ui() -> None:
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
                if not auto:
                    self._append_log("==== 检测结束 ====")
                self._set_busy(False, "环境就绪" if report.ready else "环境不完整")
                if auto and not report.ready:
                    self._select_step(0)

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
