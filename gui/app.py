"""tkinter 主界面：选工程、检测、编译、看日志。"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from crosskit import build as buildmod
from crosskit import detect, settings, wsl
from crosskit.httpshare import DirectoryShare, guess_share_dir


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Qt ARM64 交叉编译工具")
        self.geometry("960x760")
        self.minsize(800, 600)
        self._busy = False
        self._share = DirectoryShare()
        self._cfg = settings.load()

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
        self.share_urls = tk.StringVar(value="（未启动）")
        self.status = tk.StringVar(value="就绪")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        if self.project.get():
            self._refresh_build_files()
        if not self.share_dir.get():
            self._fill_share_from_project()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        top = ttk.Frame(self)
        top.pack(fill=tk.X, **pad)

        ttk.Label(top, text="工程目录").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.project, width=70).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(top, text="浏览…", command=self._browse_project).grid(row=0, column=2)
        recent = self._cfg.get("recent_projects") or []
        if recent:
            mb = ttk.Menubutton(top, text="最近")
            menu = tk.Menu(mb, tearoff=0)
            for p in recent:
                menu.add_command(label=p, command=lambda x=p: self._set_project(x))
            mb["menu"] = menu
            mb.grid(row=0, column=3, padx=4)

        ttk.Label(top, text="构建文件").grid(row=1, column=0, sticky=tk.W)
        self.build_combo = ttk.Combobox(top, textvariable=self.build_file, width=67)
        self.build_combo.grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(top, text="刷新", command=self._refresh_build_files).grid(row=1, column=2)

        ttk.Label(top, text="系统").grid(row=2, column=0, sticky=tk.W)
        sysf = ttk.Frame(top)
        sysf.grid(row=2, column=1, sticky=tk.W)
        for v, t in (("auto", "自动"), ("qmake", "qmake"), ("cmake", "CMake")):
            ttk.Radiobutton(sysf, text=t, value=v, variable=self.build_system).pack(side=tk.LEFT, padx=4)

        opts = ttk.LabelFrame(self, text="选项")
        opts.pack(fill=tk.X, **pad)
        ttk.Label(opts, text="应用名").grid(row=0, column=0, sticky=tk.W, padx=4)
        ttk.Entry(opts, textvariable=self.app_name, width=20).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(opts, text="产物路径").grid(row=0, column=2, sticky=tk.W, padx=4)
        ttk.Entry(opts, textvariable=self.out_bin, width=28).grid(row=0, column=3, sticky=tk.W)
        ttk.Label(opts, text="并行(-j)").grid(row=0, column=4, sticky=tk.W, padx=4)
        ttk.Spinbox(opts, from_=0, to=64, textvariable=self.jobs, width=5).grid(row=0, column=5)
        ttk.Label(opts, text="0=自动").grid(row=0, column=6, sticky=tk.W)
        ttk.Checkbutton(opts, text="打运行包", variable=self.do_bundle).grid(row=0, column=7, padx=8)
        ttk.Checkbutton(
            opts,
            text="附加 FFmpeg",
            variable=self.use_ffmpeg,
        ).grid(row=0, column=8, padx=8)

        ttk.Label(opts, text="插件").grid(row=1, column=0, sticky=tk.W, padx=4)
        ttk.Entry(opts, textvariable=self.plugins, width=70).grid(row=1, column=1, columnspan=7, sticky=tk.EW, pady=2)
        ttk.Label(opts, text="其他 pkg-config").grid(row=2, column=0, sticky=tk.W, padx=4)
        ttk.Entry(opts, textvariable=self.extra_pkg, width=70).grid(row=2, column=1, columnspan=7, sticky=tk.EW)
        ttk.Label(opts, text="EXTRA_COPY").grid(row=3, column=0, sticky=tk.W, padx=4)
        ttk.Entry(opts, textvariable=self.extra_copy, width=70).grid(row=3, column=1, columnspan=7, sticky=tk.EW)
        ttk.Label(opts, text="发行版").grid(row=4, column=0, sticky=tk.W, padx=4)
        ttk.Entry(opts, textvariable=self.distro, width=20).grid(row=4, column=1, sticky=tk.W)

        share = ttk.LabelFrame(self, text="客户机下载（HTTP 共享，替代 Everything）")
        share.pack(fill=tk.X, **pad)
        ttk.Label(share, text="共享目录").grid(row=0, column=0, sticky=tk.W, padx=4)
        ttk.Entry(share, textvariable=self.share_dir, width=55).grid(row=0, column=1, sticky=tk.EW, padx=2)
        ttk.Button(share, text="浏览…", command=self._browse_share).grid(row=0, column=2, padx=2)
        ttk.Button(share, text="用产物目录", command=self._fill_share_from_project).grid(row=0, column=3, padx=2)
        ttk.Label(share, text="端口").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Spinbox(share, from_=1, to=65535, textvariable=self.share_port, width=8).grid(
            row=1, column=1, sticky=tk.W, padx=2
        )
        sf = ttk.Frame(share)
        sf.grid(row=1, column=2, columnspan=2, sticky=tk.W)
        ttk.Button(sf, text="启动共享", command=self._share_start).pack(side=tk.LEFT, padx=2)
        ttk.Button(sf, text="停止", command=self._share_stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(sf, text="复制地址", command=self._share_copy_url).pack(side=tk.LEFT, padx=2)
        ttk.Label(share, text="客户机访问").grid(row=2, column=0, sticky=tk.NW, padx=4)
        ttk.Label(share, textvariable=self.share_urls, wraplength=720, justify=tk.LEFT).grid(
            row=2, column=1, columnspan=3, sticky=tk.W, padx=2, pady=4
        )
        share.columnconfigure(1, weight=1)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, **pad)
        for text, cmd in (
            ("检测环境", self._on_detect),
            ("安装工具链+sysroot", lambda: self._on_install("setup_cross_focal.sh")),
            ("编译 Qt 5.14.2", lambda: self._on_install("build_qt5142_arm64_cross.sh")),
            ("交叉编译", self._on_build),
            ("打开产物目录", self._open_out),
            ("复制日志", self._copy_log),
            ("清空日志", lambda: self.log.delete("1.0", tk.END)),
        ):
            ttk.Button(btns, text=text, command=cmd).pack(side=tk.LEFT, padx=3)

        self.env_box = tk.Text(self, height=6, wrap=tk.WORD)
        self.env_box.pack(fill=tk.X, padx=8, pady=4)

        self.log = tk.Text(self, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        scroll = ttk.Scrollbar(self.log, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)

        ttk.Label(self, textvariable=self.status).pack(anchor=tk.W, padx=8, pady=4)
        top.columnconfigure(1, weight=1)

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
        self.share_urls.set("\n".join(urls) if urls else f"http://127.0.0.1:{port}/")
        self._persist()
        self._append_log(f"[http] 共享已启动: {directory}")
        for u in urls:
            self._append_log(f"[http] {u}")
        self._append_log("[http] 客户机示例: wget http://<本机IP>:%d/<包名>.tar.gz" % port)
        self.status.set(f"HTTP 共享中 :{port}")

    def _share_stop(self) -> None:
        if not self._share.running:
            self.share_urls.set("（未启动）")
            return
        self._share.stop()
        self.share_urls.set("（未启动）")
        self._append_log("[http] 共享已停止")
        self.status.set("就绪")

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
            # 保持原值；若是 kind: path 形式则解析
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
        self.status.set(msg or ("忙碌…" if busy else "就绪"))

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
            }
        )

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
