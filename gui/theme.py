"""界面视觉：浅色工装风 + 青绿强调（参考现代桌面工具的 airy + teal）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


# 色板：冷灰底 + 青绿主色，避免紫/奶油/厚重阴影
C = {
    "bg": "#EEF2F6",
    "surface": "#FFFFFF",
    "surface2": "#F7FAFC",
    "border": "#D8E0EA",
    "border_strong": "#C5D0DE",
    "text": "#0F1C2E",
    "muted": "#5B6B7C",
    "primary": "#0F766E",
    "primary_hover": "#0D9488",
    "primary_fg": "#FFFFFF",
    "accent_soft": "#CCFBF1",
    "ok": "#15803D",
    "warn": "#B45309",
    "err": "#B91C1C",
    "idle": "#94A3B8",
    "log_bg": "#0F172A",
    "log_fg": "#E2E8F0",
    "log_border": "#1E293B",
    "header_top": "#0F766E",
    "header_bot": "#134E4A",
}


def pick_font(prefer: list[str], size: int, weight: str = "normal") -> tuple:
    """选本机已有字体；中文界面优先黑体族。"""
    # tk 字体名直接尝试，失败则回退
    return (prefer[0], size, weight)


def ui_font(size: int = 10, weight: str = "normal") -> tuple:
    return pick_font(["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"], size, weight)


def mono_font(size: int = 9) -> tuple:
    return pick_font(["Cascadia Mono", "Consolas", "Courier New"], size, "normal")


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=C["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=C["bg"], foreground=C["text"], font=ui_font(10))
    style.configure("TFrame", background=C["bg"])
    style.configure("Card.TFrame", background=C["surface"])
    style.configure("Header.TFrame", background=C["header_top"])
    style.configure("TLabel", background=C["bg"], foreground=C["text"], font=ui_font(10))
    style.configure("Card.TLabel", background=C["surface"], foreground=C["text"], font=ui_font(10))
    style.configure("Muted.TLabel", background=C["surface"], foreground=C["muted"], font=ui_font(9))
    style.configure("Title.TLabel", background=C["header_top"], foreground="#FFFFFF", font=ui_font(16, "bold"))
    style.configure("Sub.TLabel", background=C["header_top"], foreground="#CCFBF1", font=ui_font(9))
    style.configure("Section.TLabel", background=C["surface"], foreground=C["primary"], font=ui_font(10, "bold"))
    style.configure("Status.TLabel", background=C["bg"], foreground=C["muted"], font=ui_font(9))

    style.configure(
        "Card.TLabelframe",
        background=C["surface"],
        foreground=C["primary"],
        bordercolor=C["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=C["surface"],
        foreground=C["primary"],
        font=ui_font(10, "bold"),
    )

    style.configure(
        "TEntry",
        fieldbackground=C["surface2"],
        foreground=C["text"],
        bordercolor=C["border"],
        lightcolor=C["border"],
        darkcolor=C["border"],
        insertcolor=C["text"],
        padding=6,
    )
    style.map("TEntry", bordercolor=[("focus", C["primary"])])

    style.configure(
        "TCombobox",
        fieldbackground=C["surface2"],
        background=C["surface2"],
        foreground=C["text"],
        arrowcolor=C["primary"],
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", C["surface2"])],
        selectbackground=[("readonly", C["accent_soft"])],
    )

    style.configure(
        "TSpinbox",
        fieldbackground=C["surface2"],
        foreground=C["text"],
        padding=4,
        arrowcolor=C["primary"],
    )

    style.configure(
        "TButton",
        background=C["surface"],
        foreground=C["text"],
        bordercolor=C["border_strong"],
        focusthickness=1,
        focuscolor=C["accent_soft"],
        padding=(12, 7),
        font=ui_font(9),
    )
    style.map(
        "TButton",
        background=[("active", C["accent_soft"]), ("pressed", C["border"])],
        bordercolor=[("active", C["primary"])],
    )

    style.configure(
        "Primary.TButton",
        background=C["primary"],
        foreground=C["primary_fg"],
        bordercolor=C["primary"],
        padding=(18, 9),
        font=ui_font(10, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", C["primary_hover"]), ("pressed", C["header_bot"])],
        foreground=[("disabled", "#99A")],
    )

    style.configure(
        "Accent.TButton",
        background=C["accent_soft"],
        foreground=C["primary"],
        bordercolor=C["primary"],
        padding=(12, 7),
        font=ui_font(9, "bold"),
    )

    style.configure("TCheckbutton", background=C["surface"], foreground=C["text"], font=ui_font(9))
    style.configure("TRadiobutton", background=C["surface"], foreground=C["text"], font=ui_font(9))
    style.configure("TMenubutton", background=C["surface"], foreground=C["text"], padding=(10, 6))
    style.configure(
        "Horizontal.TScrollbar",
        background=C["border"],
        troughcolor=C["surface2"],
        bordercolor=C["border"],
        arrowcolor=C["muted"],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=C["border"],
        troughcolor=C["surface2"],
        bordercolor=C["border"],
        arrowcolor=C["muted"],
    )
    return style


def card(parent: tk.Misc, title: str) -> ttk.LabelFrame:
    box = ttk.LabelFrame(parent, text=f"  {title}  ", style="Card.TLabelframe", padding=(14, 10))
    return box


def primary_button(parent: tk.Misc, text: str, command) -> ttk.Button:
    return ttk.Button(parent, text=text, command=command, style="Primary.TButton")


class EqualTabs:
    """等宽分段页签（避开 ttk.Notebook 选中态高低不一）。"""

    def __init__(self, parent: tk.Misc, labels: list[str]) -> None:
        self._idx = 0
        self._btns: list[tk.Label] = []
        self._pages: list[ttk.Frame] = []

        self.bar = tk.Frame(parent, bg=C["bg"])
        self.bar.pack(fill=tk.X, padx=2, pady=(0, 8))
        rail = tk.Frame(self.bar, bg=C["border"], padx=1, pady=1)
        rail.pack(anchor=tk.W)

        self.host = ttk.Frame(parent, style="TFrame")
        self.host.pack(fill=tk.BOTH, expand=True)

        cell_w = max(8, max(len(t) for t in labels) + 2)
        for i, text in enumerate(labels):
            btn = tk.Label(
                rail,
                text=text,
                width=cell_w,
                anchor=tk.CENTER,
                bg=C["surface2"],
                fg=C["muted"],
                font=ui_font(10),
                padx=4,
                pady=8,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT)
            btn.bind("<Button-1>", lambda _e, n=i: self.select(n))
            self._btns.append(btn)

            page = ttk.Frame(self.host, style="TFrame")
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._pages.append(page)

        self.select(0)

    def page(self, index: int) -> ttk.Frame:
        return self._pages[index]

    def select(self, index: int) -> None:
        self._idx = index
        for i, (btn, page) in enumerate(zip(self._btns, self._pages)):
            on = i == index
            btn.configure(
                bg=C["surface"] if on else C["surface2"],
                fg=C["primary"] if on else C["muted"],
                font=ui_font(10, "bold" if on else "normal"),
            )
            if on:
                page.lift()

    def select_by_widget(self, widget: tk.Misc) -> None:
        """兼容旧 Notebook.select(0) 写法：传页 frame 或下标。"""
        if isinstance(widget, int):
            self.select(widget)
            return
        for i, p in enumerate(self._pages):
            if p is widget:
                self.select(i)
                return


def make_scrollable(parent: tk.Misc):
    """可垂直滚动的内容区。返回 (inner_frame, sync_scroll)。"""
    wrap = ttk.Frame(parent, style="TFrame")
    wrap.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(wrap, bg=C["bg"], highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    inner = ttk.Frame(canvas, style="TFrame")
    win = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _sync_scroll(_event=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_width(event) -> None:
        canvas.itemconfigure(win, width=event.width)

    inner.bind("<Configure>", _sync_scroll)
    canvas.bind("<Configure>", _sync_width)

    def _wheel(event) -> None:
        # Windows: event.delta 为 ±120 的倍数
        if event.delta:
            canvas.yview_scroll(int(-event.delta / 120), "units")

    def _bind_wheel(_e=None) -> None:
        canvas.bind_all("<MouseWheel>", _wheel)

    def _unbind_wheel(_e=None) -> None:
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _bind_wheel)
    canvas.bind("<Leave>", _unbind_wheel)
    return inner, _sync_scroll
