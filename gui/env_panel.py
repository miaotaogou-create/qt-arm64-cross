"""环境页：发行版配置卡 + 工具链明细（对齐参考卡片）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.icons import CpuIcon, FolderIcon, FolderOpenIcon, HardDriveIcon
from gui.theme import C


def hline(*, spec: bool = False, bright: bool = False) -> QFrame:
    """卡片内水平分隔线（参考图浅灰横线；bright=白线对齐参数卡参考）。"""
    line = QFrame()
    if bright:
        line.setObjectName("BrightDivider")
    else:
        line.setObjectName("SpecDivider" if spec else "CardDivider")
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    line.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return line


class PathInputField(QFrame):
    """带左侧 Folder 图标的路径输入框（px-3 + icon + gap-2 对齐参考）。"""

    textChanged = Signal(str)

    def __init__(
        self,
        text: str = "",
        *,
        placeholder: str = "",
        folder_color: str = "#F59E0B",
        folder_open: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PathField")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(36)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        if folder_open:
            icon = FolderOpenIcon(16, folder_color)
        else:
            icon = FolderIcon(16, folder_color)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)
        self.ed = QLineEdit(text)
        self.ed.setObjectName("PathEditInner")
        if placeholder:
            self.ed.setPlaceholderText(placeholder)
        self.ed.textChanged.connect(self.textChanged.emit)
        self.ed.installEventFilter(self)
        lay.addWidget(self.ed, 1)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.ed and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.setProperty("focused", event.type() == QEvent.Type.FocusIn)
            self.style().unpolish(self)
            self.style().polish(self)
        return super().eventFilter(obj, event)


# 界面预设；当前仅 Ubuntu-20.04 有现成环境包
DISTRO_PRESETS: list[dict[str, str]] = [
    {
        "name": "Ubuntu-20.04",
        "tag": "推荐 / 稳妥",
        "meta": "Qt 5.14.2 · GCC 9.4.0",
        "supported": "1",
    },
    {
        "name": "Ubuntu-22.04",
        "tag": "Qt6 推荐",
        "meta": "Qt 6.5.2 · GCC 11.2.0",
        "supported": "0",
    },
    {
        "name": "Kylin-ARM64-SDK",
        "tag": "国产麒麟适配",
        "meta": "Qt 5.12.8 · GCC 8.3.0",
        "supported": "0",
    },
]

TOOLCHAIN_SPEC_KEYS: list[tuple[str, str]] = [
    ("arch", "目标架构"),
    ("gcc", "GCC 交叉编译器"),
    ("qt", "Qt 库版本"),
    ("sysroot", "SYSROOT"),
    ("tools", "辅助工具"),
]


class ToolchainSpecsCard(QFrame):
    """工具链明细：检测后写入真实版本，未检测时显示等待。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(0)
        lay.addWidget(card_header("cpu", "工具链及 SYSROOT 明细", icon_color="#14B8A6"))

        body = QVBoxLayout()
        body.setContentsMargins(0, 8, 0, 0)
        body.setSpacing(0)
        self._vals: dict[str, QLabel] = {}
        for i, (key, title) in enumerate(TOOLCHAIN_SPEC_KEYS):
            row = QFrame()
            row.setObjectName("SpecRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 7, 0, 7)
            kk = QLabel(title)
            kk.setObjectName("SpecKey")
            vv = QLabel("等待检测…")
            vv.setObjectName("SpecVal")
            vv.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            rl.addWidget(kk)
            rl.addWidget(vv, 1)
            body.addWidget(row)
            body.addWidget(hline(spec=True))
            self._vals[key] = vv
        lay.addLayout(body)

    def _set(self, key: str, text: str, kind: str) -> None:
        lb = self._vals.get(key)
        if lb is None:
            return
        lb.setText(text)
        name = {"accent": "SpecValAccent", "ok": "SpecValOk", "bad": "SpecValBad"}.get(kind, "SpecVal")
        lb.setObjectName(name)
        lb.style().unpolish(lb)
        lb.style().polish(lb)

    def apply_report(self, report) -> None:
        facts = dict(getattr(report, "facts", None) or {})
        ok = {i.key: i.ok for i in getattr(report, "items", [])}
        if not getattr(report, "distro_ok", False):
            tip = "未检测到发行版" if ok.get("distro") is False else "WSL 不可用"
            for key, _title in TOOLCHAIN_SPEC_KEYS:
                self._set(key, tip, "bad")
            return

        machine = facts.get("gcc_machine") or ""
        if machine and machine != "missing":
            self._set("arch", f"Linux ARM64 ({machine})", "accent")
        else:
            self._set("arch", "未检测到交叉编译器", "bad")

        gcc_ver = facts.get("gcc_ver") or ""
        if gcc_ver and gcc_ver != "missing":
            self._set("gcc", f"aarch64-linux-gnu-gcc {gcc_ver}", "ok")
        else:
            self._set("gcc", "未安装", "bad")

        qt_ver = facts.get("qt_version") or ""
        if ok.get("qt_widgets") and qt_ver and qt_ver not in ("unknown", "missing"):
            self._set("qt", f"Qt {qt_ver}", "ok")
        else:
            self._set("qt", "未安装", "bad")

        rootfs = facts.get("rootfs_path") or "/opt/arm64-rootfs"
        code = facts.get("rootfs_codename") or ""
        if ok.get("rootfs"):
            extra = f" ({code})" if code else ""
            self._set("sysroot", f"{rootfs}{extra}", "ok")
        else:
            self._set("sysroot", "未就绪", "bad")

        bits = [
            ("Readelf", ok.get("cross_readelf")),
            ("Pkg-config", ok.get("pkg_config")),
            ("CCACHE", ok.get("ccache_bin")),
        ]
        tools = " · ".join(name if yes else f"{name} 缺" for name, yes in bits)
        self._set("tools", tools, "ok" if all(yes for _n, yes in bits) else "bad")


def build_toolchain_specs() -> ToolchainSpecsCard:
    return ToolchainSpecsCard()


class PresetCard(QFrame):
    """预设发行版单选卡片（对齐参考代码）。"""

    clicked = Signal(str)

    def __init__(self, name: str, tag: str, meta: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.is_active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        self.lbl_name = QLabel(name)
        self.lbl_name.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #F9FAFB; background: transparent; border: none;"
        )
        self.lbl_tag = QLabel(tag)
        top.addWidget(self.lbl_name)
        top.addStretch()
        top.addWidget(self.lbl_tag)
        lay.addLayout(top)

        self.lbl_desc = QLabel(meta)
        self.lbl_desc.setStyleSheet(
            "font-size: 11px; color: #64748B; background: transparent; border: none;"
        )
        lay.addWidget(self.lbl_desc)
        self.update_style()

    def set_selected(self, selected: bool) -> None:
        self.set_active(selected)

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self.update_style()

    def update_style(self) -> None:
        if self.is_active:
            self.setStyleSheet(
                "QFrame {"
                "background-color: #030712;"
                "border: 2px solid #0D9488;"
                "border-radius: 8px;"
                "}"
            )
            self.lbl_tag.setStyleSheet(
                "background-color: #0D9488;"
                "color: #FFFFFF;"
                "font-size: 10px;"
                "font-weight: bold;"
                "padding: 2px 8px;"
                "border-radius: 4px;"
                "border: none;"
            )
        else:
            self.setStyleSheet(
                "QFrame {"
                "background-color: #030712;"
                "border: 1px solid #1F2937;"
                "border-radius: 8px;"
                "}"
                "QFrame:hover {"
                "border: 1px solid #334155;"
                "}"
            )
            self.lbl_tag.setStyleSheet(
                "background-color: #1E293B;"
                "color: #94A3B8;"
                "font-size: 10px;"
                "padding: 2px 8px;"
                "border-radius: 4px;"
                "border: 1px solid #334155;"
            )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)
        super().mousePressEvent(event)


def card_header(icon_text: str, title: str, right: str = "", icon_color: str | None = None) -> QWidget:
    wrap = QWidget()
    wrap.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    color = icon_color or "#06B6D4"
    if icon_text in ("cpu", "chip"):
        icon = CpuIcon(22, color if icon_color else "#14B8A6")
    elif icon_text in ("▣", "hdd", "drive", ""):
        icon = HardDriveIcon(24, color)
    else:
        icon = QLabel(icon_text)
        icon.setObjectName("CardHeadIcon")
        icon.setFixedSize(24, 24)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"color:{color}; background:transparent; border:none; font-size:20px; font-weight:700;"
        )
    lay.addWidget(icon)
    t = QLabel(title)
    t.setObjectName("CardHeadTitle")
    lay.addWidget(t)
    lay.addStretch(1)
    if right:
        r = QLabel(right)
        r.setObjectName("CardHeadRight")
        lay.addWidget(r)

    box = QWidget()
    box.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    vl = QVBoxLayout(box)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(0)
    vl.addWidget(wrap)
    vl.addSpacing(12)
    vl.addWidget(hline())
    return box


def form_label(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("FormSectionLabel")
    return lb


def build_preset_row(on_pick) -> tuple[QWidget, dict[str, PresetCard]]:
    """预设发行版行：宽屏三列横排，窄屏单列堆叠（断点 900px）。"""
    host = ResponsivePresetHost(on_pick)
    return host, host.cards


class ResponsivePresetHost(QWidget):
    """监听宽度：≥900 横排三列，<900 纵排堆叠。"""

    BREAKPOINT = 900

    def __init__(self, on_pick, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cards: dict[str, PresetCard] = {}
        self._mode: str | None = None
        self._card_list: list[PresetCard] = []
        for item in DISTRO_PRESETS:
            card = PresetCard(item["name"], item["tag"], item["meta"])
            card.clicked.connect(on_pick)
            self.cards[item["name"]] = card
            self._card_list.append(card)
        self.update_responsive_layout(self.width() or 1000)

    def update_responsive_layout(self, current_width: int) -> None:
        target = "desktop" if current_width >= self.BREAKPOINT else "mobile"
        if self._mode == target:
            return
        self._mode = target
        old = self.layout()
        if old is not None:
            for c in self._card_list:
                old.removeWidget(c)
            QWidget().setLayout(old)
        if target == "desktop":
            lay = QHBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(14)
            for c in self._card_list:
                lay.addWidget(c, 1)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)
            for c in self._card_list:
                lay.addWidget(c)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        # 用主窗口宽度断点更稳；若宿主尚无父窗，退回自身宽度
        win = self.window()
        w = win.width() if win is not None else event.size().width()
        self.update_responsive_layout(w)
