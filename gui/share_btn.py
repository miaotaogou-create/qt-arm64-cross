"""去极速 HTTP 共享按钮：霓虹呼吸灯 + hover 图标脉冲。"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, Qt, QSize, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

from gui.icons import make_svg_icon


class GoShareButton(QPushButton):
    """暗青绿共享按钮：常驻正弦呼吸发光；悬停时图标 OutBack 放大。"""

    _ICON_NORMAL = 18
    _ICON_HOVER = 22
    _ICON_PAD = 8

    def __init__(self, text: str = "去极速 HTTP 共享", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("BtnGoShare")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(180)
        self.setFixedHeight(38)
        self._hovering = False
        self._breath_factor = 0.0
        self._apply_icon("#14B8A6", self._ICON_NORMAL)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setColor(QColor(13, 148, 136, 80))
        self._shadow.setBlurRadius(4)
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)

        self._anim_scale = QVariantAnimation(self)
        self._anim_scale.setDuration(250)
        self._anim_scale.setStartValue(self._ICON_NORMAL)
        self._anim_scale.setEndValue(self._ICON_HOVER)
        self._anim_scale.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim_scale.valueChanged.connect(self._on_icon_scale)

        self._breath = QVariantAnimation(self)
        self._breath.setDuration(1600)
        self._breath.setStartValue(0.0)
        self._breath.setEndValue(1.0)
        self._breath.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._breath.valueChanged.connect(self._on_breath_step)
        self._breath.finished.connect(self._on_breath_finished)
        self._apply_breath(0.0)
        self._breath.start()

    def _icon_color(self) -> str:
        if not self.isEnabled():
            return "#4B5563"
        return "#2DD4BF" if self._hovering else "#14B8A6"

    def _apply_icon(self, color: str, size: int) -> None:
        self.setIcon(make_svg_icon("share", color, size, pad_right=self._ICON_PAD))
        self.setIconSize(QSize(size + self._ICON_PAD, size))

    def _on_icon_scale(self, val: float) -> None:
        self._apply_icon(self._icon_color(), int(val))

    def _apply_breath(self, factor: float) -> None:
        """factor 0→暗 / 1→亮：阴影半径、透明度与青绿底/边同步呼吸。"""
        self._breath_factor = float(factor)
        if not self.isEnabled():
            self._shadow.setBlurRadius(0)
            self._shadow.setColor(QColor(0, 0, 0, 0))
            self.setStyleSheet(
                "QPushButton#BtnGoShare {"
                "background-color:#111827; border:1px solid #1F2937; border-radius:10px;"
                "}"
            )
            return

        blur = 4 + int(factor * 14)
        alpha = int(80 + factor * 140)
        self._shadow.setBlurRadius(blur)
        self._shadow.setColor(QColor(13, 148, 136, alpha))

        bg_r = int(13 + factor * 10)
        bg_g = int(32 + factor * 30)
        bg_b = int(36 + factor * 25)
        border_a = (100 + factor * 155) / 255.0
        self.setStyleSheet(
            "QPushButton#BtnGoShare {"
            f"background-color: rgb({bg_r}, {bg_g}, {bg_b});"
            f"border: 1px solid rgba(20, 184, 166, {border_a:.2f});"
            "border-radius: 10px;"
            "}"
        )

    def _on_breath_step(self, factor: float) -> None:
        self._apply_breath(factor)

    def _on_breath_finished(self) -> None:
        if not self.isEnabled():
            return
        # 往复振荡，避免 loop 从 1 跳回 0 的断点
        fwd = QVariantAnimation.Direction.Forward
        back = QVariantAnimation.Direction.Backward
        self._breath.setDirection(back if self._breath.direction() == fwd else fwd)
        self._breath.start()

    def enterEvent(self, event) -> None:
        if self.isEnabled():
            self._hovering = True
            self._anim_scale.setDirection(QVariantAnimation.Direction.Forward)
            self._anim_scale.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self.isEnabled():
            self._hovering = False
            self._anim_scale.setDirection(QVariantAnimation.Direction.Backward)
            self._anim_scale.start()
        super().leaveEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() != QEvent.Type.EnabledChange:
            return
        self._hovering = False
        self._anim_scale.stop()
        self._apply_icon(self._icon_color(), self._ICON_NORMAL)
        if self.isEnabled():
            self._breath.setDirection(QVariantAnimation.Direction.Forward)
            self._breath.start()
        else:
            self._breath.stop()
            self._apply_breath(0.0)
