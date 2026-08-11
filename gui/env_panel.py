"""环境页：发行版配置卡 + 工具链明细（先对齐界面，再接逻辑）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.theme import C

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
        "name": "Kirin-ARM64-SDK",
        "tag": "国产麒麟适配",
        "meta": "Qt 5.12.8 · GCC 8.3.0",
        "supported": "0",
    },
]

TOOLCHAIN_SPECS: list[tuple[str, str, str]] = [
    ("目标架构", "Linux ARM64 (aarch64)", "accent"),
    ("GCC 交叉编译器", "aarch64-linux-gnu-gcc 9.4", "text"),
    ("Qt 库版本", "Qt 5.14.2 (Desktop/EGLFS)", "text"),
    ("Multilib 支持", "Readelf, Pkg-config, CCACHE", "ok"),
]


class PresetCard(QFrame):
    """发行版快捷选择卡片。"""

    clicked = Signal(str)

    def __init__(self, name: str, tag: str, meta: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.setObjectName("PresetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(68)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(6)
        title = QLabel(name)
        title.setObjectName("PresetTitle")
        top.addWidget(title, 1)
        self._tag = QLabel(tag)
        self._tag.setObjectName("PresetTag")
        top.addWidget(self._tag, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        meta_lbl = QLabel(meta)
        meta_lbl.setObjectName("PresetMeta")
        lay.addWidget(meta_lbl)

    def set_selected(self, selected: bool) -> None:
        self.setObjectName("PresetCardActive" if selected else "PresetCard")
        self._tag.setObjectName("PresetTagActive" if selected else "PresetTag")
        self.style().unpolish(self)
        self.style().polish(self)
        self._tag.style().unpolish(self._tag)
        self._tag.style().polish(self._tag)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)
        super().mousePressEvent(event)


def card_header(icon_text: str, title: str, right: str = "", icon_color: str | None = None) -> QWidget:
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 10)
    lay.setSpacing(8)
    icon = QLabel(icon_text)
    icon.setFixedSize(22, 22)
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    color = icon_color or C["accent"]
    icon.setStyleSheet(
        f"color:{color}; background:rgba(20,184,166,0.12); border-radius:6px; font-size:12px; font-weight:700;"
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
    line = QFrame()
    line.setObjectName("CardDivider")
    line.setFixedHeight(1)
    # 外层再包一层：标题行 + 分割线
    box = QWidget()
    vl = QVBoxLayout(box)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(0)
    vl.addWidget(wrap)
    vl.addWidget(line)
    return box


def form_label(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("FormSectionLabel")
    return lb


def build_preset_row(on_pick) -> tuple[QWidget, dict[str, PresetCard]]:
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    cards: dict[str, PresetCard] = {}
    for item in DISTRO_PRESETS:
        card = PresetCard(item["name"], item["tag"], item["meta"])
        card.clicked.connect(on_pick)
        lay.addWidget(card, 1)
        cards[item["name"]] = card
    return wrap, cards


def build_toolchain_specs() -> QFrame:
    frame = QFrame()
    frame.setObjectName("Card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 10, 14, 10)
    lay.setSpacing(0)
    lay.addWidget(card_header("▣", "工具链及 SYSROOT 明细", icon_color=C["ok"]))

    body = QVBoxLayout()
    body.setContentsMargins(0, 8, 0, 0)
    body.setSpacing(0)
    for i, (k, v, kind) in enumerate(TOOLCHAIN_SPECS):
        row = QFrame()
        row.setObjectName("SpecRow")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 7, 0, 7)
        kk = QLabel(k)
        kk.setObjectName("SpecKey")
        vv = QLabel(v)
        if kind == "accent":
            vv.setObjectName("SpecValAccent")
        elif kind == "ok":
            vv.setObjectName("SpecValOk")
        else:
            vv.setObjectName("SpecVal")
        vv.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rl.addWidget(kk)
        rl.addWidget(vv, 1)
        body.addWidget(row)
        if i < len(TOOLCHAIN_SPECS) - 1:
            div = QFrame()
            div.setObjectName("SpecDivider")
            div.setFixedHeight(1)
            body.addWidget(div)
    lay.addLayout(body)
    return frame
