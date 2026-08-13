"""去极速 HTTP 共享按钮：霓虹呼吸灯 + hover 图标脉冲。"""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QEvent, Qt, QTimer, QSize, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton

from gui.icons import make_svg_icon


class GoShareButton(QPushButton):
    """暗青绿共享按钮：paintEvent 呼吸发光；悬停时图标 OutBack 放大。"""

    _ICON_NORMAL = 18
    _ICON_HOVER = 22
    _ICON_PAD = 8
    _RADIUS = 10.0

    def __init__(self, text: str = "去极速 HTTP 共享", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("BtnGoShare")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(180)
        self.setFixedHeight(38)
        self._hovering = False
        self._breath_factor = 0.0
        self._breath_phase = 0.0
        self._apply_icon("#14B8A6", self._ICON_NORMAL)

        self._anim_scale = QVariantAnimation(self)
        self._anim_scale.setDuration(250)
        self._anim_scale.setStartValue(self._ICON_NORMAL)
        self._anim_scale.setEndValue(self._ICON_HOVER)
        self._anim_scale.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim_scale.valueChanged.connect(self._on_icon_scale)

        # ponytail: 正弦相位 + update()，避免每帧 setStyleSheet / 改阴影半径触发布局抖动
        self._breath_timer = QTimer(self)
        self._breath_timer.setInterval(16)
        self._breath_timer.timeout.connect(self._tick_breath)
        self._breath_timer.start()

    def _icon_color(self) -> str:
        if not self.isEnabled():
            return "#4B5563"
        return "#2DD4BF" if self._hovering else "#14B8A6"

    def _apply_icon(self, color: str, size: int) -> None:
        self.setIcon(make_svg_icon("share", color, size, pad_right=self._ICON_PAD))
        self.setIconSize(QSize(size + self._ICON_PAD, size))

    def _on_icon_scale(self, val: float) -> None:
        self._apply_icon(self._icon_color(), int(val))

    def _tick_breath(self) -> None:
        if not self.isEnabled():
            return
        self._breath_phase += 16.0 / 1600.0
        if self._breath_phase >= 2.0:
            self._breath_phase -= 2.0
        # 0→1→0 平滑往复，无动画首尾跳变
        self._breath_factor = (math.sin(self._breath_phase * math.pi - math.pi / 2) + 1.0) * 0.5
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        f = self._breath_factor

        if not self.isEnabled():
            bg = QColor("#111827")
            border = QColor("#1F2937")
        else:
            bg = QColor(int(13 + f * 10), int(32 + f * 30), int(36 + f * 25))
            border = QColor(20, 184, 166, int(100 + f * 155))
            glow_a = int(80 + f * 140)
            glow_pen = QPen(QColor(13, 148, 136, glow_a // 2))
            glow_pen.setWidthF(2.0 + f * 5.0)
            p.setPen(glow_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, self._RADIUS, self._RADIUS)

        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, self._RADIUS, self._RADIUS)
        p.end()
        super().paintEvent(event)

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
            self._breath_timer.start()
        else:
            self._breath_timer.stop()
            self._breath_factor = 0.0
            self.update()
