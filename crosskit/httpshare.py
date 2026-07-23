"""简易 HTTP 目录共享（替代 Everything 的 HTTP 服务，给客户机 wget/浏览器下载）。"""
from __future__ import annotations

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def lan_ipv4() -> list[str]:
    """本机局域网 IPv4（排除回环）。"""
    found: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    # 连外网路由探测一次，常能拿到真正上网的网卡 IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and ip not in found:
            found.insert(0, ip)
    except OSError:
        pass
    return found


def guess_share_dir(project: str, app_name: str = "") -> Path | None:
    """优先猜产物目录 dist/arm64-kylin。"""
    root = Path(project) if project else None
    if not root or not root.is_dir():
        return None
    name = (app_name or "").strip()
    candidates = []
    if name:
        candidates.append(root / "dist" / "arm64-kylin")
    candidates += [
        root / "dist" / "arm64-kylin",
        root / "dist",
        root,
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return root


class DirectoryShare:
    """后台线程跑 ThreadingHTTPServer。"""

    def __init__(self) -> None:
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.directory: Path | None = None
        self.port: int = 0

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def start(self, directory: str | Path, port: int = 8080) -> None:
        if self.running:
            raise RuntimeError("共享已在运行，请先停止")
        path = Path(directory).resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"目录不存在: {path}")
        handler = partial(SimpleHTTPRequestHandler, directory=str(path))
        # 允许地址复用，方便快速重启
        ThreadingHTTPServer.allow_reuse_address = True
        httpd = ThreadingHTTPServer(("0.0.0.0", int(port)), handler)
        self._httpd = httpd
        self.directory = path
        self.port = int(port)

        def serve() -> None:
            try:
                httpd.serve_forever(poll_interval=0.5)
            finally:
                httpd.server_close()

        self._thread = threading.Thread(target=serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        httpd = self._httpd
        self._httpd = None
        if httpd is not None:
            httpd.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        self.directory = None
        self.port = 0

    def urls(self) -> list[str]:
        if not self.running:
            return []
        ips = lan_ipv4() or ["127.0.0.1"]
        return [f"http://{ip}:{self.port}/" for ip in ips]
