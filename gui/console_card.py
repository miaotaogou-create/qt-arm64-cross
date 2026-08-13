"""交叉构建实时控制台卡片：顶栏筛选 + 彩色日志流 + 自动滚动。"""
from __future__ import annotations

import datetime
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
)

_SVG_SEARCH = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="11" cy="11" r="8"></circle>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"></line>'
    "</svg>"
)
_SVG_TERMINAL = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="4 17 10 11 4 5"></polyline>'
    '<line x1="12" y1="19" x2="20" y2="19"></line>'
    "</svg>"
)


class _SvgIcon(QSvgWidget):
    def __init__(self, tpl: str, color: str = "#14B8A6", size: int = 16, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._tpl = tpl
        self._color = color
        self._reload()

    def set_color(self, color: str) -> None:
        self._color = color
        self._reload()

    def _reload(self) -> None:
        self.load(self._tpl.format(color=self._color).encode("utf-8"))


def _parse_log_line(line: str) -> tuple[str, str]:
    s = line.strip()
    m = re.match(r"^\[([^\]]+)\]\s*(.*)$", s)
    if m:
        return m.group(1), m.group(2) if m.group(2) else s
    return "INFO", s


class BuildLogConsoleCard(QFrame):
    """交叉构建实时控制台：筛选、行数角标、自动滚动、彩色日志。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ConsoleCard")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.auto_scroll = True
        self._entries: list[dict[str, str]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶栏底色与日志区分离（参考图：标题区略亮、内容区更深）
        header_bar = QFrame()
        header_bar.setObjectName("ConsoleHeader")
        header_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header = QHBoxLayout(header_bar)
        header.setContentsMargins(18, 12, 18, 12)
        header.setSpacing(10)

        header.addWidget(_SvgIcon(_SVG_TERMINAL, "#34D399", 18))
        title = QLabel("交叉构建实时控制台 (Build Log Stream)")
        title.setObjectName("ConsoleTitle")
        header.addWidget(title)

        self._count_badge = QLabel(" 0 行输出 ")
        self._count_badge.setObjectName("BadgeCount")
        header.addWidget(self._count_badge)
        header.addStretch(1)

        search_box = QFrame()
        search_box.setObjectName("SearchBox")
        search_lay = QHBoxLayout(search_box)
        search_lay.setContentsMargins(8, 0, 8, 0)
        search_lay.setSpacing(6)
        search_lay.addWidget(_SvgIcon(_SVG_SEARCH, "#64748B", 14))
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("筛选日志...")
        self._filter.setObjectName("FilterEdit")
        self._filter.textChanged.connect(self._filter_logs)
        search_lay.addWidget(self._filter, 1)
        header.addWidget(search_box)

        self._btn_autoscroll = QPushButton("自动滚动: 开")
        self._btn_autoscroll.setObjectName("AutoScrollBtnOn")
        self._btn_autoscroll.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_autoscroll.clicked.connect(self._toggle_autoscroll)
        header.addWidget(self._btn_autoscroll)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        header.addWidget(self.progress_bar)

        root.addWidget(header_bar)

        body = QFrame()
        body.setObjectName("ConsoleBody")
        body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(18, 10, 18, 14)
        body_lay.setSpacing(0)

        self.editor = QTextEdit()
        self.editor.setObjectName("TerminalEdit")
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(240)
        body_lay.addWidget(self.editor, 1)
        root.addWidget(body, 1)

    def append_line(self, line: str) -> None:
        tag, msg = _parse_log_line(line)
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {"time": now_str, "tag": tag, "msg": msg}
        self._entries.append(entry)

        kw = self._filter.text().strip().lower()
        if not kw or kw in f"{tag} {msg}".lower():
            self._render_entry(entry)

        self._count_badge.setText(f" {len(self._entries)} 行输出 ")
        if self.auto_scroll:
            self.editor.moveCursor(QTextCursor.MoveOperation.End)

    def clear(self) -> None:
        self._entries.clear()
        self.editor.clear()
        self._count_badge.setText(" 0 行输出 ")

    def plain_text(self) -> str:
        return self.editor.toPlainText()

    def _render_entry(self, entry: dict[str, str]) -> None:
        cur = self.editor.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)

        fmt_time = QTextCharFormat()
        fmt_time.setForeground(QColor("#475569"))
        cur.insertText(f"{entry['time']}  ", fmt_time)

        tag = entry["tag"].upper()
        fmt_tag = QTextCharFormat()
        fmt_tag.setFontWeight(800)
        if "OK" in tag or "SUCCESS" in tag:
            fmt_tag.setForeground(QColor("#34D399"))
        elif "ERR" in tag or "FAIL" in tag or "ERROR" in tag:
            fmt_tag.setForeground(QColor("#F87171"))
        else:
            fmt_tag.setForeground(QColor("#38BDF8"))
        cur.insertText(f"[{tag}] ", fmt_tag)

        fmt_msg = QTextCharFormat()
        fmt_msg.setForeground(QColor("#34D399") if "OK" in tag or "SUCCESS" in tag else QColor("#E2E8F0"))
        cur.insertText(f"{entry['msg']}\n", fmt_msg)

    def _filter_logs(self, keyword: str) -> None:
        kw = keyword.strip().lower()
        self.editor.clear()
        for entry in self._entries:
            if not kw or kw in f"{entry['tag']} {entry['msg']}".lower():
                self._render_entry(entry)
        if self.auto_scroll:
            self.editor.moveCursor(QTextCursor.MoveOperation.End)

    def _toggle_autoscroll(self) -> None:
        self.auto_scroll = not self.auto_scroll
        if self.auto_scroll:
            self._btn_autoscroll.setText("自动滚动: 开")
            self._btn_autoscroll.setObjectName("AutoScrollBtnOn")
            self.editor.moveCursor(QTextCursor.MoveOperation.End)
        else:
            self._btn_autoscroll.setText("自动滚动: 关")
            self._btn_autoscroll.setObjectName("AutoScrollBtnOff")
        st = self._btn_autoscroll.style()
        st.unpolish(self._btn_autoscroll)
        st.polish(self._btn_autoscroll)
        self._btn_autoscroll.update()
