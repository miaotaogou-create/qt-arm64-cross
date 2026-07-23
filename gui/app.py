"""主界面：工程选择、交叉编译、HTTP 共享、日志。"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from crosskit import build as buildmod
from crosskit import detect, envpack, settings, wsl
from crosskit.httpshare import DirectoryShare, guess_share_dir
from gui.chrome import TitleChrome
from gui.theme import C, apply_theme, card, mono_font, primary_button, ui_font


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Qt ARM64 交叉编译工具")
        self.geometry("1040x820")
        self.minsize(900, 680)
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

    def _build_ui(self) -> None:
        # --- 自定义标题栏（与主题一体，去掉系统白顶栏）---
        self._chrome = TitleChrome(self, on_close=self._on_close)
        self._chrome.build(self)
        self._status_pill = self._chrome.status_pill
        self._status_pill.configure(textvariable=self.header_status)

        body = ttk.Frame(self, style="TFrame")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # --- 工程 ---
        proj = card(body, "工程")
        proj.pack(fill=tk.X, pady=(0, 10))
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

        ttk.Label(proj, text="构建系统", style="Card.TLabel").grid(row=2, column=0, sticky=tk.W, pady=4)
        sysf = ttk.Frame(proj, style="Card.TFrame")
        sysf.grid(row=2, column=1, sticky=tk.W, padx=8)
        for v, t in (("auto", "自动"), ("qmake", "qmake"), ("cmake", "CMake")):
            ttk.Radiobutton(sysf, text=t, value=v, variable=self.build_system).pack(side=tk.LEFT, padx=(0, 12))
        proj.columnconfigure(1, weight=1)

        # --- 选项 ---
        opts = card(body, "编译选项")
        opts.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(opts, text="应用名", style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(opts, textvariable=self.app_name, width=18).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Label(opts, text="产物路径", style="Card.TLabel").grid(row=0, column=2, sticky=tk.W, padx=(12, 0))
        ttk.Entry(opts, textvariable=self.out_bin, width=28).grid(row=0, column=3, sticky=tk.W, padx=6)
        ttk.Label(opts, text="并行 -j", style="Card.TLabel").grid(row=0, column=4, sticky=tk.W, padx=(12, 0))
        ttk.Spinbox(opts, from_=0, to=64, textvariable=self.jobs, width=5).grid(row=0, column=5, sticky=tk.W, padx=6)
        ttk.Label(opts, text="0 = 自动", style="Muted.TLabel").grid(row=0, column=6, sticky=tk.W)

        flags = ttk.Frame(opts, style="Card.TFrame")
        flags.grid(row=1, column=0, columnspan=7, sticky=tk.W, pady=(6, 2))
        ttk.Checkbutton(flags, text="打运行包", variable=self.do_bundle).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(flags, text="附加 FFmpeg", variable=self.use_ffmpeg).pack(side=tk.LEFT, padx=(0, 16))
        self._adv_btn = ttk.Button(flags, text="高级选项 ▸", command=self._toggle_advanced, style="Accent.TButton")
        self._adv_btn.pack(side=tk.LEFT)

        self._adv = ttk.Frame(opts, style="Card.TFrame")
        ttk.Label(self._adv, text="插件", style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.plugins).grid(row=0, column=1, sticky=tk.EW, padx=8, pady=3)
        ttk.Label(self._adv, text="其他 pkg-config", style="Card.TLabel").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.extra_pkg).grid(row=1, column=1, sticky=tk.EW, padx=8, pady=3)
        ttk.Label(self._adv, text="EXTRA_COPY", style="Card.TLabel").grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.extra_copy).grid(row=2, column=1, sticky=tk.EW, padx=8, pady=3)
        ttk.Label(self._adv, text="发行版", style="Card.TLabel").grid(row=3, column=0, sticky=tk.W, pady=3)
        ttk.Entry(self._adv, textvariable=self.distro, width=22).grid(row=3, column=1, sticky=tk.W, padx=8, pady=3)
        self._adv.columnconfigure(1, weight=1)

        # --- HTTP ---
        share = card(body, "客户机下载 · HTTP 共享")
        share.pack(fill=tk.X, pady=(0, 10))
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
        ttk.Button(row1, text="启动共享", command=self._share_start, style="Accent.TButton").pack(side=tk.LEFT, padx=(10, 4))
        ttk.Button(row1, text="停止", command=self._share_stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="复制地址", command=self._share_copy_url).pack(side=tk.LEFT, padx=2)

        st = ttk.Frame(share, style="Card.TFrame")
        st.grid(row=2, column=0, columnspan=4, sticky=tk.EW, pady=(6, 2))
        self._http_dot = tk.Canvas(st, width=12, height=12, bg=C["surface"], highlightthickness=0)
        self._http_dot.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(st, text="客户机访问", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Label(st, textvariable=self.share_urls, style="Card.TLabel").pack(side=tk.LEFT, padx=8)
        share.columnconfigure(1, weight=1)

        # --- 环境包（发给同事）---
        envp = card(body, "交叉编译环境包 · 导出 / 导入")
        envp.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            envp,
            text="给同事：QtArm64Cross.exe + 本环境包。导入后即可交叉编译 app_mast 这类 Qt+FFmpeg 工程。",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 6))
        ttk.Label(envp, text="导入安装目录", style="Card.TLabel").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(envp, textvariable=self.env_install_dir).grid(row=1, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(envp, text="浏览…", command=self._browse_env_install).grid(row=1, column=2, padx=2)
        row_env = ttk.Frame(envp, style="Card.TFrame")
        row_env.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=6)
        ttk.Checkbutton(
            row_env,
            text="导出时去掉 Qt 源码缓存（可选，减小体积；交叉编译照常用）",
            variable=self.env_slim,
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(row_env, text="导入时覆盖已有同名发行版", variable=self.env_replace).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(row_env, text="导出环境包…", command=self._on_export_env, style="Accent.TButton").pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(row_env, text="导入环境包…", command=self._on_import_env, style="Primary.TButton").pack(
            side=tk.LEFT, padx=4
        )
        envp.columnconfigure(1, weight=1)

        # --- 操作条 ---
        actions = ttk.Frame(body)
        actions.pack(fill=tk.X, pady=(0, 10))
        primary_button(actions, "▶  交叉编译", self._on_build).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="检测环境", command=self._on_detect).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="打开产物", command=self._open_out).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="安装工具链", command=lambda: self._on_install("setup_cross_focal.sh")).pack(
            side=tk.LEFT, padx=3
        )
        ttk.Button(actions, text="编译 Qt 5.14.2", command=lambda: self._on_install("build_qt5142_arm64_cross.sh")).pack(
            side=tk.LEFT, padx=3
        )
        ttk.Button(actions, text="复制日志", command=self._copy_log).pack(side=tk.RIGHT, padx=3)
        ttk.Button(actions, text="清空日志", command=lambda: self.log.delete("1.0", tk.END)).pack(side=tk.RIGHT, padx=3)

        # --- 环境 / 日志 ---
        mid = ttk.Frame(body)
        mid.pack(fill=tk.BOTH, expand=True)
        env_card = card(mid, "环境状态")
        env_card.pack(fill=tk.X, pady=(0, 10))
        self.env_box = tk.Text(
            env_card,
            height=4,
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

        log_card = card(mid, "构建日志")
        log_card.pack(fill=tk.BOTH, expand=True)
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

        foot = ttk.Frame(self)
        foot.pack(fill=tk.X, padx=16, pady=(0, 10))
        ttk.Label(foot, textvariable=self.status, style="Status.TLabel").pack(side=tk.LEFT)

    def _toggle_advanced(self) -> None:
        self._advanced_open = not self._advanced_open
        if self._advanced_open:
            self._adv.grid(row=2, column=0, columnspan=7, sticky=tk.EW, pady=(8, 0))
            self._adv_btn.configure(text="高级选项 ▾")
        else:
            self._adv.grid_forget()
            self._adv_btn.configure(text="高级选项 ▸")

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
        self.share_urls.set("  |  ".join(urls) if urls else f"http://127.0.0.1:{port}/")
        self._set_http_dot(True)
        self._persist()
        self._append_log(f"[http] 共享已启动: {directory}")
        for u in urls:
            self._append_log(f"[http] {u}")
        self._append_log("[http] 客户机示例: wget http://<本机IP>:%d/<包名>.tar.gz" % port)
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
        urls = self._share.urls()
        if not urls:
            messagebox.showinfo("提示", "请先启动共享")
            return
        text = "\n".join(urls)
        self.clipboard_clear()
        self.clipboard_append(text)
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
        if busy:
            self.header_status.set("工作中")
            self._status_pill.configure(bg="#FEF3C7", fg=C["warn"])
        elif "共享" in text:
            self.header_status.set(text.replace("HTTP ", ""))
            self._status_pill.configure(bg=C["accent_soft"], fg=C["primary"])
        elif text.startswith("成功"):
            self.header_status.set("成功")
            self._status_pill.configure(bg="#DCFCE7", fg=C["ok"])
        elif text.startswith("失败"):
            self.header_status.set("失败")
            self._status_pill.configure(bg="#FEE2E2", fg=C["err"])
        else:
            self.header_status.set("空闲" if text == "就绪" else text)
            self._status_pill.configure(bg=C["accent_soft"], fg=C["primary"])

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
        if wsl.distro_exists(distro) and not replace:
            messagebox.showerror(
                "错误",
                f"本机已有发行版 {distro}。\n勾选「导入时覆盖已有同名发行版」或先改高级选项里的发行版名。",
            )
            return
        if not messagebox.askokcancel(
            "导入环境包",
            f"将导入为 WSL 发行版「{distro}」\n安装到：{install_dir}\n"
            + ("会先注销已有同名发行版。\n" if replace else "")
            + "对方机器需已启用 WSL2。继续？",
        ):
            return
        self._persist()

        def work() -> None:
            self._set_busy(True, "导入环境包…")
            code = envpack.import_distro(
                archive,
                install_dir,
                distro=distro,
                replace=replace,
                set_default=True,
                on_line=lambda line: self.after(0, lambda l=line: self._append_log(l)),
            )
            self.after(
                0,
                lambda: (
                    self._append_log(f"[env] 导入结束 exit={code}"),
                    self._set_busy(False, "导入成功" if code == 0 else f"导入失败 exit={code}"),
                ),
            )

        threading.Thread(target=work, daemon=True).start()

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
