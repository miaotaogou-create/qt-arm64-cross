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


def _hwnd(root: tk.Tk) -> int:
    root.update_idletasks()
    wid = root.winfo_id()
    parent = user32.GetParent(wid)
    return parent or wid


def show_in_taskbar(root: tk.Tk) -> None:
    """overrideredirect 后仍出现在任务栏。"""
    hwnd = _hwnd(root)
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    # 刷新壳层
    root.withdraw()
    root.after(20, root.deiconify)


class TitleChrome:
    """把青绿顶栏变成可拖动的自定义标题栏。"""

    def __init__(self, root: tk.Tk, on_close) -> None:
        self.root = root
        self.on_close = on_close
        self._drag_x = 0
        self._drag_y = 0
        self._maximized = False
        self._restore_geom = ""
        self._chrome_btns: list[tk.Label] = []

    def build(self, parent: tk.Misc) -> tk.Frame:
        self.root.overrideredirect(True)
        # 外圈细边，避免无边框时贴边难辨
        self.root.configure(highlightthickness=1, highlightbackground=C["header_bot"], highlightcolor=C["header_bot"])

        header = tk.Frame(parent, bg=C["header_top"], height=56)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Frame(header, bg=C["header_bot"], height=2).pack(side=tk.BOTTOM, fill=tk.X)

        bar = tk.Frame(header, bg=C["header_top"])
        bar.pack(fill=tk.BOTH, expand=True)

        # 左侧品牌
        left = tk.Frame(bar, bg=C["header_top"])
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(16, 8), pady=8)
        mark = tk.Canvas(left, width=28, height=28, bg=C["header_top"], highlightthickness=0)
        mark.pack(side=tk.LEFT, padx=(0, 10))
        mark.create_oval(2, 2, 26, 26, fill=C["accent_soft"], outline=C["accent_soft"])
        mark.create_text(14, 14, text="Q", fill=C["primary"], font=ui_font(11, "bold"))
        titles = tk.Frame(left, bg=C["header_top"])
        titles.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            titles,
            text="Qt ARM64 交叉编译",
            bg=C["header_top"],
            fg="#FFFFFF",
            font=ui_font(13, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            titles,
            text="Windows · WSL Ubuntu-20.04 · 麒麟 ARM64",
            bg=C["header_top"],
            fg="#99F6E4",
            font=ui_font(8),
        ).pack(anchor=tk.W)

        # 右侧：状态 + 窗控
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
        self.status_pill.pack(side=tk.LEFT, padx=(0, 12), pady=12)

        winbtns = tk.Frame(right, bg=C["header_top"])
        winbtns.pack(side=tk.RIGHT, padx=(0, 4))
        self._btn_min = self._chrome_btn(winbtns, "─", self.minimize)
        self._btn_max = self._chrome_btn(winbtns, "□", self.toggle_max)
        self._btn_close = self._chrome_btn(winbtns, "✕", self.on_close, hover_bg="#DC2626", hover_fg="#FFFFFF")

        # 拖拽区域（排除按钮）
        for w in (header, bar, left, titles, mark, *titles.winfo_children()):
            self._bind_drag(w)

        self.root.bind("<Map>", self._on_map)
        self.root.after(50, lambda: show_in_taskbar(self.root))
        self._add_resize_grip()
        return header

    def _add_resize_grip(self) -> None:
        """无边框窗口右下角缩放。"""
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

    def _chrome_btn(self, parent, text, cmd, hover_bg=None, hover_fg=None) -> tk.Label:
        hover_bg = hover_bg or C["header_bot"]
        hover_fg = hover_fg or "#FFFFFF"
        lab = tk.Label(
            parent,
            text=text,
            bg=C["header_top"],
            fg="#E2E8F0",
            width=4,
            font=ui_font(10),
            cursor="hand2",
        )
        lab.pack(side=tk.LEFT, fill=tk.Y, ipady=14)

        def enter(_e, b=hover_bg, f=hover_fg):
            lab.configure(bg=b, fg=f)

        def leave(_e):
            lab.configure(bg=C["header_top"], fg="#E2E8F0")

        lab.bind("<Enter>", enter)
        lab.bind("<Leave>", leave)
        lab.bind("<Button-1>", lambda _e: cmd())
        self._chrome_btns.append(lab)
        return lab

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
        # overrideredirect 下 iconify 需短暂恢复边框
        self.root.overrideredirect(False)
        self.root.iconify()

    def _on_map(self, _event=None) -> None:
        if self.root.state() == "normal":
            self.root.overrideredirect(True)
            show_in_taskbar(self.root)

    def toggle_max(self) -> None:
        if not self._maximized:
            self._restore_geom = self.root.geometry()
            # 工作区（排除任务栏）
            try:
                class RECT(ctypes.Structure):
                    _fields_ = [("l", wintypes.LONG), ("t", wintypes.LONG), ("r", wintypes.LONG), ("b", wintypes.LONG)]

                rect = RECT()
                # SPI_GETWORKAREA = 0x0030
                ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
                w = rect.r - rect.l
                h = rect.b - rect.t
                self.root.geometry(f"{w}x{h}+{rect.l}+{rect.t}")
            except Exception:
                self.root.state("zoomed")
            self._maximized = True
            self._btn_max.configure(text="❐")
        else:
            if self._restore_geom:
                self.root.geometry(self._restore_geom)
            self._maximized = False
            self._btn_max.configure(text="□")

    def set_status(self, text: str, bg: str, fg: str) -> None:
        self.status_pill.configure(text=text, bg=bg, fg=fg)
