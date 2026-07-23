"""主界面：工程选择、交叉编译、HTTP 共享、日志。"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from crosskit import build as buildmod
from crosskit import detect, envpack, settings, wsl, wsl_setup
from crosskit.httpshare import DirectoryShare, guess_share_dir
from gui.chrome import TitleChrome
from gui.theme import C, EqualTabs, apply_theme, card, make_scrollable, mono_font, primary_button


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Qt ARM64 交叉编译工具")
        self.geometry("980x720")
        self.minsize(820, 560)
        self._busy = False
        self._share = DirectoryShare()
        self._advanced_open = False
        self._cfg = settings.load()
        self._chrome: TitleChrome | None = None

        self.project = tk.StringVar(value=self._cfg.get("project", ""))
        self.build_file = tk.StringVar(value=self._cfg.get("build_file", ""))
        self.build_system = tk.StringVar(value=self._cfg.get("build_system", "auto"))
        self.app_name = tk.StringVar(value=self._cfg.get("app_name", ""))
        self.out_bin = tk.StringVar(value=self._cfg.get("out_bin", ""))
        self.jobs = tk.IntVar(value=int(self._cfg.get("jobs") or 0))
        self.do_bundle = tk.BooleanVar(value=bool(self._cfg.get("do_bundle", True)))
        self.use_ffmpeg = tk.BooleanVar(value=bool(self._cfg.get("use_ffmpeg", False)))
        self.plugins = tk.StringVar(value=self._cfg.get("plugins", ""))
        self.extra_pkg = tk.StringVar(value=self._cfg.get("extra_pkgconfig", ""))
        self.extra_copy = tk.StringVar(value=self._cfg.get("extra_copy", ""))
        self.distro = tk.StringVar(value=self._cfg.get("distro", wsl.DEFAULT_DISTRO))
        self.share_dir = tk.StringVar(value=self._cfg.get("share_dir", ""))
        self.share_port = tk.IntVar(value=int(self._cfg.get("share_port") or 8080))
        self.share_urls = tk.StringVar(value="未启动")
        default_env = self._cfg.get("env_install_dir") or str(
            Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "WSL" / "Ubuntu-20.04"
        )
        self.env_install_dir = tk.StringVar(value=default_env)
        self.env_slim = tk.BooleanVar(value=bool(self._cfg.get("env_slim_export", False)))
        self.env_replace = tk.BooleanVar(value=bool(self._cfg.get("env_replace_on_import", False)))
        self.status = tk.StringVar(value="就绪")
        self.header_status = tk.StringVar(value="空闲")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        apply_theme(self)
        self._build_ui()
        if self.project.get():
            self._refresh_build_files()
        if not self.share_dir.get():
            self._fill_share_from_project()
        self._set_http_dot(False)
        self.after(600, self._maybe_resume_pending_import)

    def _build_ui(self) -> None:
        self._chrome = TitleChrome(self, on_close=self._on_close)
        self._chrome.build(self)
        self._status_pill = self._chrome.status_pill
        self._status_pill.configure(textvariable=self.header_status)

        shell = ttk.Frame(self, style="TFrame")
        shell.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 0))

        self._nb = EqualTabs(shell, ["编译", "环境准备", "下载共享"])
        self._build_tab_compile(self._nb.page(0))
        self._build_tab_env(self._nb.page(1))
        self._build_tab_share(self._nb.page(2))

        foot = ttk.Frame(self)
        foot.pack(fill=tk.X, padx=14, pady=(4, 8))
        ttk.Label(foot, textvariable=self.status, style="Status.TLabel").pack(side=tk.LEFT)

    def _build_tab_compile(self, parent: ttk.Frame) -> None:
        """日常：选工程 → 编译 → 看日志。"""
        top = ttk.Frame(parent, style="TFrame")
        top.pack(fill=tk.X, padx=10, pady=(10, 0))

        proj = card(top, "工程")
        proj.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(proj, text="工程目录", style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(proj, textvariable=self.project).grid(row=0, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(proj, text="浏览…", command=self._browse_project).grid(row=0, column=2, padx=2)
        recent = self._cfg.get("recent_projects") or []
        if recent:
            mb = ttk.Menubutton(proj, text="最近")
            menu = tk.Menu(mb, tearoff=0, bg=C["surface"], fg=C["text"], activebackground=C["accent_soft"])
            for p in recent:
                menu.add_command(label=p, command=lambda x=p: self._set_project(x))
            mb["menu"] = menu
            mb.grid(row=0, column=3, padx=2)

        ttk.Label(proj, text="构建文件", style="Card.TLabel").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.build_combo = ttk.Combobox(proj, textvariable=self.build_file)
        self.build_combo.grid(row=1, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(proj, text="刷新", command=self._refresh_build_files).grid(row=1, column=2, padx=2)
        proj.columnconfigure(1, weight=1)

        opts = card(top, "选项")
        opts.pack(fill=tk.X, pady=(0, 8))
        flags = ttk.Frame(opts, style="Card.TFrame")
        flags.pack(fill=tk.X)
        ttk.Checkbutton(flags, text="打运行包", variable=self.do_bundle).pack(side=tk.LEFT, padx=(0, 14))
        ttk.Checkbutton(flags, text="附加 FFmpeg（app_mast 类工程）", variable=self.use_ffmpeg).pack(
            side=tk.LEFT, padx=(0, 14)
        )
        self._adv_btn = ttk.Button(flags, text="高级 ▸", command=self._toggle_advanced, style="Accent.TButton")
        self._adv_btn.pack(side=tk.LEFT)

        self._adv = ttk.Frame(opts, style="Card.TFrame")
        ttk.Label(self._adv, text="构建系统", style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=3)
        sysf = ttk.Frame(self._adv, style="Card.TFrame")
        sysf.grid(row=0, column=1, sticky=tk.W, padx=8)
        for v, t in (("auto", "自动"), ("qmake", "qmake"), ("cmake", "CMake")):
            ttk.Radiobutton(sysf, text=t, value=v, variable=self.build_system).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(self._adv, text="应用名", style="Card.TLabel").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.app_name, width=18).grid(row=1, column=1, sticky=tk.W, padx=8)
        ttk.Label(self._adv, text="产物路径", style="Card.TLabel").grid(row=1, column=2, sticky=tk.W, padx=(8, 0))
        ttk.Entry(self._adv, textvariable=self.out_bin, width=24).grid(row=1, column=3, sticky=tk.W, padx=8)
        ttk.Label(self._adv, text="并行 -j", style="Card.TLabel").grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Spinbox(self._adv, from_=0, to=64, textvariable=self.jobs, width=5).grid(
            row=2, column=1, sticky=tk.W, padx=8
        )
        ttk.Label(self._adv, text="0=自动", style="Muted.TLabel").grid(row=2, column=2, sticky=tk.W)
        ttk.Label(self._adv, text="插件", style="Card.TLabel").grid(row=3, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.plugins).grid(
            row=3, column=1, columnspan=3, sticky=tk.EW, padx=8, pady=3
        )
        ttk.Label(self._adv, text="其他 pkg-config", style="Card.TLabel").grid(row=4, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.extra_pkg).grid(
            row=4, column=1, columnspan=3, sticky=tk.EW, padx=8, pady=3
        )
        ttk.Label(self._adv, text="EXTRA_COPY", style="Card.TLabel").grid(row=5, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.extra_copy).grid(
            row=5, column=1, columnspan=3, sticky=tk.EW, padx=8, pady=3
        )
        ttk.Label(self._adv, text="发行版", style="Card.TLabel").grid(row=6, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.distro, width=22).grid(row=6, column=1, sticky=tk.W, padx=8, pady=3)
        self._adv.columnconfigure(1, weight=1)

        actions = ttk.Frame(top)
        actions.pack(fill=tk.X, pady=(0, 8))
        primary_button(actions, "▶  交叉编译", self._on_build).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="检测环境", command=self._on_detect).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="打开产物", command=self._open_out).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="复制日志", command=self._copy_log).pack(side=tk.RIGHT, padx=3)
        ttk.Button(actions, text="清空", command=lambda: self.log.delete("1.0", tk.END)).pack(side=tk.RIGHT, padx=3)

        env_card = card(top, "环境状态")
        env_card.pack(fill=tk.X, pady=(0, 8))
        self.env_box = tk.Text(
            env_card,
            height=3,
            wrap=tk.WORD,
            bg=C["surface2"],
            fg=C["text"],
            relief=tk.FLAT,
            font=mono_font(9),
            insertbackground=C["text"],
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["primary"],
            padx=8,
            pady=6,
        )
        self.env_box.pack(fill=tk.X)

        log_card = card(parent, "构建日志")
        log_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        log_wrap = tk.Frame(log_card, bg=C["log_border"])
        log_wrap.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(
            log_wrap,
            wrap=tk.WORD,
            bg=C["log_bg"],
            fg=C["log_fg"],
            insertbackground=C["log_fg"],
            relief=tk.FLAT,
            font=mono_font(9),
            padx=10,
            pady=8,
            highlightthickness=0,
        )
        scroll = ttk.Scrollbar(log_wrap, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_tab_env(self, parent: ttk.Frame) -> None:
        """换机 / 首次：导入环境包、检测、从零装工具链。"""
        inner, _sync = make_scrollable(parent)
        pad = ttk.Frame(inner, style="TFrame")
        pad.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        tip = card(pad, "怎么用")
        tip.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            tip,
            text="同事机：下载环境包 → 点「一键导入」→ 检测环境 → 回「编译」页选工程即可。\n"
            "未开 WSL 会弹 UAC 自动启用；若提示重启，重启后再开本工具会接着导入。",
            style="Muted.TLabel",
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        envp = card(pad, "交叉编译环境包")
        envp.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(envp, text="安装目录", style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(envp, textvariable=self.env_install_dir).grid(row=0, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(envp, text="浏览…", command=self._browse_env_install).grid(row=0, column=2, padx=2)

        row = ttk.Frame(envp, style="Card.TFrame")
        row.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(10, 4))
        primary_button(row, "一键导入环境包…", self._on_import_env).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="导出环境包…", command=self._on_export_env).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="检测环境", command=self._on_detect).pack(side=tk.LEFT, padx=4)

        opts = ttk.Frame(envp, style="Card.TFrame")
        opts.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))
        ttk.Checkbutton(opts, text="导出时去掉 Qt 源码缓存", variable=self.env_slim).pack(side=tk.LEFT, padx=(0, 14))
        ttk.Checkbutton(opts, text="覆盖已有同名发行版", variable=self.env_replace).pack(side=tk.LEFT)
        envp.columnconfigure(1, weight=1)

        rare = card(pad, "从零搭建（一般不用）")
        rare.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            rare,
            text="已有环境包请直接导入。仅在无包、需本机重新编译工具链/Qt 时使用。",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(0, 8))
        row2 = ttk.Frame(rare, style="Card.TFrame")
        row2.pack(anchor=tk.W)
        ttk.Button(row2, text="安装工具链", command=lambda: self._on_install("setup_cross_focal.sh")).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(
            row2, text="编译 Qt 5.14.2", command=lambda: self._on_install("build_qt5142_arm64_cross.sh")
        ).pack(side=tk.LEFT, padx=6)

        ttk.Label(pad, text="检测结果与构建日志在「编译」页查看。", style="Status.TLabel").pack(
            anchor=tk.W, pady=(4, 0)
        )

    def _build_tab_share(self, parent: ttk.Frame) -> None:
        inner, _sync = make_scrollable(parent)
        pad = ttk.Frame(inner, style="TFrame")
        pad.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        share = card(pad, "HTTP 共享（给客户机下载运行包）")
        share.pack(fill=tk.X)
        ttk.Label(share, text="共享目录", style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(share, textvariable=self.share_dir).grid(row=0, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(share, text="浏览…", command=self._browse_share).grid(row=0, column=2, padx=2)
        ttk.Button(share, text="用产物目录", command=self._fill_share_from_project, style="Accent.TButton").grid(
            row=0, column=3, padx=2
        )

        ttk.Label(share, text="端口", style="Card.TLabel").grid(row=1, column=0, sticky=tk.W, pady=4)
        row1 = ttk.Frame(share, style="Card.TFrame")
        row1.grid(row=1, column=1, columnspan=3, sticky=tk.EW, padx=8)
        ttk.Spinbox(row1, from_=1, to=65535, textvariable=self.share_port, width=8).pack(side=tk.LEFT)
        ttk.Button(row1, text="启动共享", command=self._share_start, style="Accent.TButton").pack(
            side=tk.LEFT, padx=(10, 4)
        )
        ttk.Button(row1, text="停止", command=self._share_stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="复制地址", command=self._share_copy_url).pack(side=tk.LEFT, padx=2)

        st = ttk.Frame(share, style="Card.TFrame")
        st.grid(row=2, column=0, columnspan=4, sticky=tk.EW, pady=(8, 2))
        self._http_dot = tk.Canvas(st, width=12, height=12, bg=C["surface"], highlightthickness=0)
        self._http_dot.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(st, text="以太网地址", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Label(st, textvariable=self.share_urls, style="Card.TLabel").pack(side=tk.LEFT, padx=8)
        share.columnconfigure(1, weight=1)

        ttk.Label(
            pad,
            text="启动后把地址发给客户机，用浏览器或 wget 下载 .tar.gz 运行包。",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(10, 0))

    def _toggle_advanced(self) -> None:
        self._advanced_open = not self._advanced_open
        if self._advanced_open:
            self._adv.pack(fill=tk.X, pady=(8, 0))
            self._adv_btn.configure(text="高级 ▾")
        else:
            self._adv.pack_forget()
            self._adv_btn.configure(text="高级 ▸")

    def _set_http_dot(self, on: bool) -> None:
        self._http_dot.delete("all")
        color = C["ok"] if on else C["idle"]
        self._http_dot.create_oval(2, 2, 10, 10, fill=color, outline=color)

    def _set_project(self, path: str) -> None:
        self.project.set(path)
        self._refresh_build_files()
        self._fill_share_from_project()

    def _browse_project(self) -> None:
        d = filedialog.askdirectory(initialdir=self.project.get() or os.path.expanduser("~"))
        if d:
            self._set_project(d)

    def _browse_share(self) -> None:
        d = filedialog.askdirectory(
            initialdir=self.share_dir.get() or self.project.get() or os.path.expanduser("~")
        )
        if d:
            self.share_dir.set(d)

    def _fill_share_from_project(self) -> None:
        g = guess_share_dir(self.project.get().strip(), self.app_name.get())
        if g is not None:
            self.share_dir.set(str(g))

    def _share_start(self) -> None:
        if self._share.running:
            messagebox.showinfo("提示", "共享已在运行")
            return
        directory = self.share_dir.get().strip()
        if not directory or not Path(directory).is_dir():
            messagebox.showerror("错误", "请先选择有效的共享目录（可用「用产物目录」）")
            return
        port = int(self.share_port.get() or 8080)
        try:
            self._share.start(directory, port)
        except OSError as e:
            messagebox.showerror("错误", f"无法监听端口 {port}: {e}")
            return
        urls = self._share.urls()
        primary = self._share.primary_url()
        self.share_urls.set(primary or f"http://127.0.0.1:{port}/")
        self._set_http_dot(True)
        self._persist()
        self._append_log(f"[http] 共享已启动: {directory}")
        from crosskit.httpshare import ethernet_ipv4

        eth = ethernet_ipv4()
        if eth:
            self._append_log(f"[http] 以太网地址: {primary}")
        else:
            self._append_log(f"[http] 未检测到有线网卡，退回: {primary}")
        if len(urls) > 1:
            self._append_log(f"[http] 其它网卡 {len(urls) - 1} 个（客户机一般用不到）")
            for u in urls:
                if u != primary:
                    self._append_log(f"[http]   {u}")
        self._append_log("[http] 客户机示例: wget <地址><包名>.tar.gz")
        self._set_busy(False, f"HTTP 共享中 :{port}")
        self.header_status.set(f"共享 :{port}")

    def _share_stop(self) -> None:
        if not self._share.running:
            self.share_urls.set("未启动")
            self._set_http_dot(False)
            return
        self._share.stop()
        self.share_urls.set("未启动")
        self._set_http_dot(False)
        self._append_log("[http] 共享已停止")
        self._set_busy(False, "就绪")

    def _share_copy_url(self) -> None:
        url = self._share.primary_url()
        if not url:
            messagebox.showinfo("提示", "请先启动共享")
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.status.set("下载地址已复制")

    def _on_close(self) -> None:
        try:
            self._share.stop()
        except Exception:
            pass
        self.destroy()

    def _refresh_build_files(self) -> None:
        files = buildmod.discover_build_files(self.project.get())
        values = [f"{k}: {p}" for k, p in files]
        self.build_combo["values"] = values
        if values and not self.build_file.get():
            self.build_combo.current(0)
            self._parse_build_combo()
        elif self.build_file.get():
            self._parse_build_combo()

    def _parse_build_combo(self) -> tuple[str, str]:
        raw = self.build_file.get().strip()
        if ": " in raw and raw.split(": ", 1)[0] in ("qmake", "cmake"):
            kind, path = raw.split(": ", 1)
            self.build_system.set(kind)
            return kind, path
        if raw.endswith(".pro"):
            return "qmake", raw
        if raw.endswith("CMakeLists.txt"):
            return "cmake", raw
        return self.build_system.get(), raw

    def _append_log(self, line: str) -> None:
        self.log.insert(tk.END, line + "\n")
        self.log.see(tk.END)

    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self._busy = busy
        text = msg or ("忙碌…" if busy else "就绪")
        self.status.set(text)
        # 顶栏状态：与青绿标题栏同底，只改字色，避免浅色色块跳戏
        if busy:
            self.header_status.set("工作中")
            self._status_pill.configure(bg=C["header_top"], fg="#FDE68A")
        elif "共享" in text:
            self.header_status.set(text.replace("HTTP ", ""))
            self._status_pill.configure(bg=C["header_top"], fg="#99F6E4")
        elif text.startswith("成功"):
            self.header_status.set("成功")
            self._status_pill.configure(bg=C["header_top"], fg="#86EFAC")
        elif text.startswith("失败"):
            self.header_status.set("失败")
            self._status_pill.configure(bg=C["header_top"], fg="#FCA5A5")
        else:
            self.header_status.set("空闲" if text == "就绪" else text)
            self._status_pill.configure(bg=C["header_top"], fg="#99F6E4")

    def _persist(self) -> None:
        kind, path = self._parse_build_combo()
        settings.save(
            {
                "project": self.project.get().strip(),
                "build_file": f"{kind}: {path}" if path else "",
                "build_system": self.build_system.get(),
                "app_name": self.app_name.get(),
                "out_bin": self.out_bin.get(),
                "jobs": int(self.jobs.get() or 0),
                "do_bundle": bool(self.do_bundle.get()),
                "use_ffmpeg": bool(self.use_ffmpeg.get()),
                "plugins": self.plugins.get(),
                "extra_pkgconfig": self.extra_pkg.get(),
                "extra_copy": self.extra_copy.get(),
                "distro": self.distro.get().strip() or wsl.DEFAULT_DISTRO,
                "share_dir": self.share_dir.get().strip(),
                "share_port": int(self.share_port.get() or 8080),
                "env_install_dir": self.env_install_dir.get().strip(),
                "env_slim_export": bool(self.env_slim.get()),
                "env_replace_on_import": bool(self.env_replace.get()),
            }
        )

    def _browse_env_install(self) -> None:
        d = filedialog.askdirectory(initialdir=self.env_install_dir.get() or os.path.expanduser("~"))
        if d:
            self.env_install_dir.set(d)

    def _on_export_env(self) -> None:
        if self._busy:
            return
        distro = self.distro.get().strip() or wsl.DEFAULT_DISTRO
        path = filedialog.asksaveasfilename(
            title="导出交叉编译环境包",
            defaultextension=".tar.gz",
            filetypes=[("环境包", "*.tar.gz"), ("未压缩 tar", "*.tar"), ("全部", "*.*")],
            initialfile=f"{distro}-cross-env.tar.gz",
        )
        if not path:
            return
        slim = bool(self.env_slim.get())
        tip = (
            "将导出完整 WSL 发行版（含已安装的 Qt、sysroot、FFmpeg、交叉编译器）。\n"
            + ("另：会删除 /opt/qt5142-cross 源码缓存以减小体积，不影响交叉编译。\n" if slim else "")
            + "体积可能数 GB，耗时较长。继续？"
        )
        if not messagebox.askokcancel("导出环境包", tip):
            return
        self._persist()
        low = path.lower()
        compress = low.endswith(".tar.gz") or low.endswith(".tgz") or not low.endswith(".tar")

        def work() -> None:
            self._set_busy(True, "导出环境包…")
            code = envpack.export_distro(
                path,
                distro=distro,
                slim=slim,
                compress=compress,
                on_line=lambda line: self.after(0, lambda l=line: self._append_log(l)),
            )
            self.after(
                0,
                lambda: (
                    self._append_log(f"[env] 导出结束 exit={code}"),
                    self._set_busy(False, "导出成功" if code == 0 else f"导出失败 exit={code}"),
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def _on_import_env(self) -> None:
        if self._busy:
            return
        distro = self.distro.get().strip() or wsl.DEFAULT_DISTRO
        archive = filedialog.askopenfilename(
            title="选择环境包",
            filetypes=[("环境包", "*.tar.gz;*.tgz;*.tar"), ("全部", "*.*")],
        )
        if not archive:
            return
        install_dir = self.env_install_dir.get().strip()
        if not install_dir:
            messagebox.showerror("错误", "请填写导入安装目录")
            return
        replace = bool(self.env_replace.get())
        # 傻瓜式：同名已存在且未勾选覆盖 → 直接问要不要覆盖
        if wsl_setup.wsl_usable() and wsl.distro_exists(distro) and not replace:
            if messagebox.askyesno(
                "已有同名环境",
                f"本机已有发行版「{distro}」。\n是否覆盖后重新导入？",
            ):
                replace = True
                self.env_replace.set(True)
            else:
                return
        tip = (
            "将自动：启用 WSL（如需要）→ 导入交叉环境。\n"
            f"发行版：{distro}\n安装到：{install_dir}\n"
            "启用 WSL 时可能弹出 UAC，请点「是」。\n继续？"
        )
        if not messagebox.askokcancel("一键导入环境包", tip):
            return
        self._persist()
        self._start_import(archive, install_dir, distro, replace)

    def _start_import(self, archive: str, install_dir: str, distro: str, replace: bool) -> None:
        if hasattr(self, "_nb"):
            self._nb.select(0)  # 日志在编译页

        def work() -> None:
            self._set_busy(True, "准备 WSL / 导入环境…")
            code = envpack.import_distro(
                archive,
                install_dir,
                distro=distro,
                replace=replace,
                set_default=True,
                auto_enable_wsl=True,
                on_line=lambda line: self.after(0, lambda l=line: self._append_log(l)),
            )

            def done() -> None:
                self._append_log(f"[env] 导入结束 exit={code}")
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
                    messagebox.showinfo(
                        "需要重启",
                        "已尝试启用 WSL，但需要重启 Windows 一次才能继续。\n\n"
                        "请重启电脑，然后重新打开本工具——会自动接着导入刚才选中的环境包。",
                    )
                elif code == 0:
                    self._clear_pending_import()
                    self._set_busy(False, "导入成功")
                    messagebox.showinfo("导入成功", "环境已导入。建议点「检测环境」确认，然后即可交叉编译。")
                    self._on_detect()
                else:
                    self._set_busy(False, f"导入失败 exit={code}")
                    messagebox.showerror("导入失败", "请查看下方日志。若取消了 UAC，请再点一次「一键导入」。")

            self.after(0, done)

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
        install_dir = (cfg.get("pending_import_dir") or "").strip() or self.env_install_dir.get().strip()
        distro = (cfg.get("pending_import_distro") or "").strip() or (
            self.distro.get().strip() or wsl.DEFAULT_DISTRO
        )
        replace = bool(cfg.get("pending_import_replace", False))
        if not Path(archive).is_file():
            self._append_log(f"[env] 待续导入的环境包已不存在: {archive}")
            self._clear_pending_import()
            return
        if not messagebox.askyesno(
            "继续导入",
            "检测到上次因启用 WSL 需要重启，导入尚未完成。\n\n"
            f"环境包：{archive}\n是否现在继续导入？",
        ):
            if messagebox.askyesno("放弃", "是否清除「待续导入」记录？（以后需手动再选文件）"):
                self._clear_pending_import()
            return
        self.env_install_dir.set(install_dir)
        self.distro.set(distro)
        self.env_replace.set(replace)
        self._start_import(archive, install_dir, distro, replace)

    def _on_detect(self) -> None:
        if self._busy:
            return

        def work() -> None:
            self._set_busy(True, "检测中…")
            report = detect.detect(self.distro.get().strip() or wsl.DEFAULT_DISTRO)

            def ui() -> None:
                self.env_box.delete("1.0", tk.END)
                lines = []
                for it in report.items:
                    mark = "OK" if it.ok else "缺"
                    lines.append(f"[{mark}] {it.label}")
                    if not it.ok and it.fix:
                        lines.append(f"      → {it.fix}")
                self.env_box.insert(tk.END, "\n".join(lines) or "(无结果)")
                self._set_busy(False, "环境就绪" if report.ready else "环境不完整")
                if hasattr(self, "_nb"):
                    self._nb.select(0)

            self.after(0, ui)

        threading.Thread(target=work, daemon=True).start()

    def _on_install(self, script: str) -> None:
        if self._busy:
            return
        if not messagebox.askokcancel("确认", f"将以 WSL root 执行 tools/{script}，可能较久。继续？"):
            return

        def work() -> None:
            self._set_busy(True, f"安装: {script}")
            code = buildmod.run_install(
                script,
                distro=self.distro.get().strip() or wsl.DEFAULT_DISTRO,
                on_line=lambda line: self.after(0, lambda l=line: self._append_log(l)),
            )
            self.after(0, lambda: self._set_busy(False, f"安装结束 exit={code}"))

        threading.Thread(target=work, daemon=True).start()

    def _on_build(self) -> None:
        if self._busy:
            return
        proj = self.project.get().strip()
        if not proj or not Path(proj).is_dir():
            messagebox.showerror("错误", "请先选择有效的工程目录")
            return
        kind, bfile = self._parse_build_combo()
        if not bfile:
            messagebox.showerror("错误", "请选择 .pro 或 CMakeLists.txt")
            return
        self._persist()

        def work() -> None:
            self._set_busy(True, "交叉编译中…")
            self.after(0, lambda: self._append_log("==== 开始编译 ===="))
            code = buildmod.build(
                project=proj,
                build_system=kind,
                build_file=bfile,
                app_name=self.app_name.get(),
                out_bin=self.out_bin.get(),
                jobs=int(self.jobs.get() or 0),
                do_bundle=bool(self.do_bundle.get()),
                plugins=self.plugins.get(),
                extra_pkgconfig=self.extra_pkg.get(),
                extra_copy=self.extra_copy.get(),
                use_ffmpeg=bool(self.use_ffmpeg.get()),
                distro=self.distro.get().strip() or wsl.DEFAULT_DISTRO,
                on_line=lambda line: self.after(0, lambda l=line: self._append_log(l)),
            )
            self.after(
                0,
                lambda: (
                    self._append_log(f"==== 结束 exit={code} ===="),
                    self._set_busy(False, "成功" if code == 0 else f"失败 exit={code}"),
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def _open_out(self) -> None:
        proj = Path(self.project.get().strip())
        name = self.app_name.get().strip()
        candidates = []
        if name:
            candidates.append(proj / "dist" / "arm64-kylin" / name)
        candidates += [
            proj / "dist" / "arm64-kylin",
            proj / "bin" / "release",
            proj / "build-arm64",
            proj,
        ]
        for c in candidates:
            if c.is_dir():
                os.startfile(str(c))  # noqa: S606
                return
        messagebox.showinfo("提示", "尚未找到产物目录")

    def _copy_log(self) -> None:
        text = self.log.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("日志已复制")


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
