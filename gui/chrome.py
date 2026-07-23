"""无标题栏：无边框窗口 + 与主题一体的顶栏拖拽/最小化/最大化/关闭。"""
from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes

from gui.theme import C, ui_font

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

# 窗控统一尺寸（避免 Unicode 字形粗细不一致）
_BTN_W = 46
_BTN_H = 40
_ICON = 10  # 半宽，图标约 20×20


def _hwnd(root: tk.Tk) -> int:
    root.update_idletasks()
    wid = root.winfo_id()
    parent = user32.GetParent(wid)
    return parent or wid


def show_in_taskbar(root: tk.Tk) -> None:
    """overrideredirect 后仍出现在任务栏。

    注意：不要用 withdraw/deiconify 刷新——会触发 Map 循环导致任务栏狂闪。
    """
    hwnd = _hwnd(root)
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    user32.SetWindowPos(
        hwnd,
        0,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
    )


def _paint_icon(cv: tk.Canvas, kind: str, color: str) -> None:
    """用相同线宽画最小化 / 最大化 / 还原 / 关闭。"""
    cv.delete("icon")
    cx, cy = _BTN_W // 2, _BTN_H // 2
    s = _ICON
    w = 1.6
    if kind == "min":
        cv.create_line(cx - s, cy + 1, cx + s, cy + 1, fill=color, width=w, tags="icon")
    elif kind == "max":
        cv.create_rectangle(cx - s, cy - s, cx + s, cy + s, outline=color, width=w, tags="icon")
    elif kind == "restore":
        # 两层方框，视觉重量与 max 接近
        cv.create_rectangle(cx - s + 3, cy - s - 1, cx + s + 1, cy + s - 3, outline=color, width=w, tags="icon")
        cv.create_rectangle(cx - s - 1, cy - s + 3, cx + s - 3, cy + s + 1, outline=color, width=w, fill=C["header_top"], tags="icon")
    elif kind == "close":
        cv.create_line(cx - s, cy - s, cx + s, cy + s, fill=color, width=w, tags="icon")
        cv.create_line(cx + s, cy - s, cx - s, cy + s, fill=color, width=w, tags="icon")


class TitleChrome:
    """把青绿顶栏变成可拖动的自定义标题栏。"""

    def __init__(self, root: tk.Tk, on_close) -> None:
        self.root = root
        self.on_close = on_close
        self._drag_x = 0
        self._drag_y = 0
        self._maximized = False
        self._restore_geom = ""
        self._map_guard = False
        self._taskbar_ready = False
        self._max_kind = "max"

    def build(self, parent: tk.Misc) -> tk.Frame:
        self.root.overrideredirect(True)
        self.root.configure(highlightthickness=1, highlightbackground=C["header_bot"], highlightcolor=C["header_bot"])

        header = tk.Frame(parent, bg=C["header_top"], height=52)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Frame(header, bg=C["header_bot"], height=2).pack(side=tk.BOTTOM, fill=tk.X)

        bar = tk.Frame(header, bg=C["header_top"])
        bar.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(bar, bg=C["header_top"])
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(14, 8), pady=6)
        mark = tk.Canvas(left, width=26, height=26, bg=C["header_top"], highlightthickness=0)
        mark.pack(side=tk.LEFT, padx=(0, 10))
        mark.create_oval(1, 1, 25, 25, fill=C["accent_soft"], outline=C["accent_soft"])
        mark.create_text(13, 13, text="Q", fill=C["primary"], font=ui_font(10, "bold"))
        titles = tk.Frame(left, bg=C["header_top"])
        titles.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            titles,
            text="Qt ARM64 交叉编译",
            bg=C["header_top"],
            fg="#FFFFFF",
            font=ui_font(12, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            titles,
            text="选工程 → 编译 · 换机导入环境包",
            bg=C["header_top"],
            fg="#99F6E4",
            font=ui_font(8),
        ).pack(anchor=tk.W)

        right = tk.Frame(bar, bg=C["header_top"])
        right.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_pill = tk.Label(
            right,
            text="空闲",
            bg=C["accent_soft"],
            fg=C["primary"],
            font=ui_font(9, "bold"),
            padx=10,
            pady=3,
        )
        self.status_pill.pack(side=tk.LEFT, padx=(0, 8), pady=10)

        winbtns = tk.Frame(right, bg=C["header_top"])
        winbtns.pack(side=tk.RIGHT)
        self._btn_min = self._chrome_btn(winbtns, "min", self.minimize)
        self._btn_max = self._chrome_btn(winbtns, "max", self.toggle_max)
        self._btn_close = self._chrome_btn(
            winbtns, "close", self.on_close, hover_bg="#DC2626", hover_fg="#FFFFFF"
        )

        for w in (header, bar, left, titles, mark, *titles.winfo_children()):
            self._bind_drag(w)

        self.root.bind("<Map>", self._on_map)
        self.root.after(80, self._init_taskbar)
        self._add_resize_grip()
        return header

    def _init_taskbar(self) -> None:
        if self._taskbar_ready:
            return
        show_in_taskbar(self.root)
        self._taskbar_ready = True

    def _add_resize_grip(self) -> None:
        grip = tk.Label(
            self.root,
            text="◢",
            bg=C["bg"],
            fg=C["muted"],
            cursor="size_nw_se",
            font=ui_font(8),
        )
        grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-1)
        self._grip = grip
        self._rz = {"x": 0, "y": 0, "w": 0, "h": 0}

        def start(e):
            self._rz = {
                "x": e.x_root,
                "y": e.y_root,
                "w": self.root.winfo_width(),
                "h": self.root.winfo_height(),
            }

        def move(e):
            if self._maximized:
                return
            dw = e.x_root - self._rz["x"]
            dh = e.y_root - self._rz["y"]
            nw = max(self.root.minsize()[0], self._rz["w"] + dw)
            nh = max(self.root.minsize()[1], self._rz["h"] + dh)
            self.root.geometry(f"{nw}x{nh}")

        grip.bind("<ButtonPress-1>", start)
        grip.bind("<B1-Motion>", move)

    def _chrome_btn(self, parent, kind: str, cmd, hover_bg=None, hover_fg=None) -> tk.Canvas:
        hover_bg = hover_bg or C["header_bot"]
        hover_fg = hover_fg or "#FFFFFF"
        idle_fg = "#E2E8F0"
        cv = tk.Canvas(
            parent,
            width=_BTN_W,
            height=_BTN_H,
            bg=C["header_top"],
            highlightthickness=0,
            cursor="hand2",
        )
        cv.pack(side=tk.LEFT, fill=tk.Y)
        _paint_icon(cv, kind, idle_fg)
        cv._icon_kind = kind  # type: ignore[attr-defined]

        def enter(_e, b=hover_bg, f=hover_fg):
            cv.configure(bg=b)
            k = getattr(cv, "_icon_kind", kind)
            # 还原图标底色要跟悬停底一致
            if k == "restore":
                cv.delete("icon")
                cx, cy = _BTN_W // 2, _BTN_H // 2
                s = _ICON
                w = 1.6
                cv.create_rectangle(cx - s + 3, cy - s - 1, cx + s + 1, cy + s - 3, outline=f, width=w, tags="icon")
                cv.create_rectangle(
                    cx - s - 1, cy - s + 3, cx + s - 3, cy + s + 1, outline=f, width=w, fill=b, tags="icon"
                )
            else:
                _paint_icon(cv, k, f)

        def leave(_e):
            cv.configure(bg=C["header_top"])
            _paint_icon(cv, getattr(cv, "_icon_kind", kind), idle_fg)

        cv.bind("<Enter>", enter)
        cv.bind("<Leave>", leave)
        cv.bind("<Button-1>", lambda _e: cmd())
        return cv

    def _set_max_icon(self, kind: str) -> None:
        self._max_kind = kind
        self._btn_max._icon_kind = kind  # type: ignore[attr-defined]
        _paint_icon(self._btn_max, kind, "#E2E8F0")

    def _bind_drag(self, widget: tk.Misc) -> None:
        widget.bind("<ButtonPress-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._on_drag)
        widget.bind("<Double-Button-1>", lambda _e: self.toggle_max())

    def _start_drag(self, event) -> None:
        if self._maximized:
            return
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event) -> None:
        if self._maximized:
            return
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def minimize(self) -> None:
        self._map_guard = True
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.after(100, lambda: setattr(self, "_map_guard", False))

    def _on_map(self, _event=None) -> None:
        if self._map_guard:
            return
        if self.root.state() != "normal":
            return
        if not self.root.overrideredirect():
            self._map_guard = True
            self.root.overrideredirect(True)
            show_in_taskbar(self.root)
            self.root.after(100, lambda: setattr(self, "_map_guard", False))

    def toggle_max(self) -> None:
        if not self._maximized:
            self._restore_geom = self.root.geometry()
            try:

                class RECT(ctypes.Structure):
                    _fields_ = [("l", wintypes.LONG), ("t", wintypes.LONG), ("r", wintypes.LONG), ("b", wintypes.LONG)]

                rect = RECT()
                ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
                w = rect.r - rect.l
                h = rect.b - rect.t
                self.root.geometry(f"{w}x{h}+{rect.l}+{rect.t}")
            except Exception:
                self.root.state("zoomed")
            self._maximized = True
            self._set_max_icon("restore")
        else:
            if self._restore_geom:
                self.root.geometry(self._restore_geom)
            self._maximized = False
            self._set_max_icon("max")

    def set_status(self, text: str, bg: str, fg: str) -> None:
        self.status_pill.configure(text=text, bg=bg, fg=fg)
