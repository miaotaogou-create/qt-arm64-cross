"""高级选项折叠面板：对齐参考实现（复选框行 + 薄荷绿切换钮 + 模式/ccache）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_SVG_SLIDERS = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line>'
    '<line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line>'
    '<line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line>'
    '<line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line>'
    '<line x1="17" y1="16" x2="23" y2="16"></line>'
    "</svg>"
)
_SVG_CHEVRON_DOWN = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="6 9 12 15 18 9"></polyline>'
    "</svg>"
)
_SVG_CHEVRON_UP = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="18 15 12 9 6 15"></polyline>'
    "</svg>"
)


class _SvgIcon(QSvgWidget):
    def __init__(self, tpl: str, color: str = "#0D9488", size: int = 16, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._tpl = tpl
        self._color = color
        self._reload()

    def set_color(self, color: str) -> None:
        self._color = color
        self._reload()

    def set_template(self, tpl: str) -> None:
        self._tpl = tpl
        self._reload()

    def _reload(self) -> None:
        self.load(self._tpl.format(color=self._color).encode("utf-8"))


class _AdvToggleBtn(QFrame):
    """薄荷绿胶囊按钮：滑块图标 + 文案 + 箭头（避免往 QPushButton 里塞 layout）。"""

    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AdvToggleBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 10, 0)
        lay.setSpacing(6)
        self._icon = _SvgIcon(_SVG_SLIDERS, "#0D9488", 16)
        self._lbl = QLabel("高级选项")
        self._lbl.setObjectName("AdvToggleLabel")
        self._arrow = _SvgIcon(_SVG_CHEVRON_DOWN, "#0D9488", 14)
        lay.addWidget(self._icon)
        lay.addWidget(self._lbl)
        lay.addWidget(self._arrow)

    def set_expanded(self, expanded: bool) -> None:
        if expanded:
            self.setProperty("expanded", True)
            self._icon.set_color("#0D9488")
            self._arrow.set_color("#0D9488")
            self._arrow.set_template(_SVG_CHEVRON_UP)
            self._lbl.setStyleSheet("color:#0F766E; font-weight:700; background:transparent; border:none;")
        else:
            self.setProperty("expanded", False)
            self._icon.set_color("#9CA3AF")
            self._arrow.set_color("#9CA3AF")
            self._arrow.set_template(_SVG_CHEVRON_DOWN)
            self._lbl.setStyleSheet("color:#9CA3AF; font-weight:700; background:transparent; border:none;")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AdvancedOptionsPanel(QWidget):
    """顶部三复选框 + 高级选项折叠：编译模式 / ccache。"""

    bundle_changed = Signal(bool)
    ffmpeg_changed = Signal(bool)
    clean_changed = Signal(bool)
    build_mode_changed = Signal(str)
    ccache_changed = Signal(bool)
    expanded_changed = Signal(bool)

    def __init__(
        self,
        *,
        do_bundle: bool = True,
        use_ffmpeg: bool = False,
        do_clean: bool = False,
        build_mode: str = "release",
        use_ccache: bool = True,
        expanded: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._expanded = bool(expanded)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(16)

        self.chk_bundle = QCheckBox("生成运行独立打包 (.tar.gz)")
        self.chk_bundle.setChecked(do_bundle)
        self.chk_bundle.toggled.connect(self.bundle_changed.emit)
        top.addWidget(self.chk_bundle)

        self.chk_ffmpeg = QCheckBox("附加 FFmpeg 多媒体依赖")
        self.chk_ffmpeg.setChecked(use_ffmpeg)
        self.chk_ffmpeg.toggled.connect(self.ffmpeg_changed.emit)
        top.addWidget(self.chk_ffmpeg)

        self.chk_clean = QCheckBox("编译前全量清理 (make clean)")
        self.chk_clean.setChecked(do_clean)
        self.chk_clean.toggled.connect(self.clean_changed.emit)
        top.addWidget(self.chk_clean)
        top.addStretch(1)

        self._toggle = _AdvToggleBtn()
        self._toggle.clicked.connect(self.toggle_panel)
        top.addWidget(self._toggle)
        root.addLayout(top)

        self.panel_frame = QFrame()
        self.panel_frame.setObjectName("AdvPanelFrame")
        self.panel_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel = QHBoxLayout(self.panel_frame)
        panel.setContentsMargins(20, 14, 20, 14)
        panel.setSpacing(32)

        mode_col = QVBoxLayout()
        mode_col.setSpacing(8)
        lbl_mode = QLabel("编译模式 (Build Mode):")
        lbl_mode.setObjectName("AdvSectionLabel")
        mode_col.addWidget(lbl_mode)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.btn_release = QPushButton("Release (O2 优化)")
        self.btn_release.setCheckable(True)
        self.btn_release.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_debug = QPushButton("Debug (带符号)")
        self.btn_debug.setCheckable(True)
        self.btn_debug.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_group.addButton(self.btn_release)
        self._mode_group.addButton(self.btn_debug)
        self._mode_group.buttonToggled.connect(self._on_mode_toggled)
        mode_row.addWidget(self.btn_release)
        mode_row.addWidget(self.btn_debug)
        mode_row.addStretch(1)
        mode_col.addLayout(mode_row)
        panel.addLayout(mode_col)

        cc_col = QVBoxLayout()
        cc_col.setSpacing(8)
        lbl_cc = QLabel("CCACHE 缓存加速:")
        lbl_cc.setObjectName("AdvSectionLabel")
        cc_col.addWidget(lbl_cc)
        self.chk_ccache = QCheckBox("启用 ccache 增量加速编译 (缩短 60% 构筑时间)")
        self.chk_ccache.setChecked(use_ccache)
        self.chk_ccache.toggled.connect(self.ccache_changed.emit)
        cc_col.addWidget(self.chk_ccache)
        cc_col.addStretch(1)
        panel.addLayout(cc_col, 1)

        root.addWidget(self.panel_frame)

        mode = "debug" if (build_mode or "").lower() == "debug" else "release"
        self.btn_release.setChecked(mode == "release")
        self.btn_debug.setChecked(mode == "debug")
        self._apply_mode_style()

        self.panel_frame.setVisible(self._expanded)
        self._toggle.set_expanded(self._expanded)

    def is_expanded(self) -> bool:
        return self._expanded

    def toggle_panel(self) -> None:
        """直接 setVisible，由布局引擎重算高度；不要 setFixedHeight。"""
        self._expanded = not self._expanded
        self.panel_frame.setVisible(self._expanded)
        self._toggle.set_expanded(self._expanded)
        self.updateGeometry()
        self.expanded_changed.emit(self._expanded)

    def _on_mode_toggled(self, button: QPushButton, checked: bool) -> None:
        if not checked:
            return
        self._apply_mode_style()
        mode = "debug" if button is self.btn_debug else "release"
        self.build_mode_changed.emit(mode)

    def _apply_mode_style(self) -> None:
        release_on = self.btn_release.isChecked()
        self.btn_release.setObjectName("ModeBtnSelected" if release_on else "ModeBtn")
        self.btn_debug.setObjectName("ModeBtnSelected" if not release_on else "ModeBtn")
        for b in (self.btn_release, self.btn_debug):
            b.style().unpolish(b)
            b.style().polish(b)
