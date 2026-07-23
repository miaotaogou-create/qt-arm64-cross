"""简易 HTTP 目录共享（替代 Everything 的 HTTP 服务，给客户机 wget/浏览器下载）。"""
from __future__ import annotations

import socket
import subprocess
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import wsl

# 短缓存，避免每次点「复制」都跑 PowerShell
_eth_cache: tuple[float, list[str]] | None = None
_ETH_TTL = 30.0


def default_route_ipv4() -> str | None:
    """经默认网关出网时本机绑定的 IPv4。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return None


def lan_ipv4() -> list[str]:
    """本机全部非回环 IPv4（含虚拟网卡）。"""
    found: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    route = default_route_ipv4()
    if route and route not in found:
        found.insert(0, route)
    return found


def ethernet_ipv4() -> list[str]:
    """物理有线网卡（以太网）上的 IPv4——客户机走网线时优先用。"""
    global _eth_cache
    now = time.monotonic()
    if _eth_cache is not None and now - _eth_cache[0] < _ETH_TTL:
        return list(_eth_cache[1])

    # Get-NetAdapter -Physical + MediaType 802.3 = 真·以太网（排除 WiFi / Hyper-V / VMware）
    ps = r"""
$ErrorActionPreference = 'SilentlyContinue'
$idxs = @(Get-NetAdapter -Physical | Where-Object {
  $_.Status -eq 'Up' -and ($_.MediaType -eq '802.3' -or $_.NdisPhysicalMedium -eq '802.3')
} | Select-Object -ExpandProperty ifIndex)
foreach ($ip in Get-NetIPAddress -AddressFamily IPv4) {
  if ($idxs -contains $ip.InterfaceIndex -and $ip.IPAddress -notlike '127.*' -and $ip.IPAddress -notlike '169.254.*') {
    $ip.IPAddress
  }
}
"""
    ips: list[str] = []
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
            **wsl._hidden_kwargs(),
        )
        for line in (r.stdout or "").splitlines():
            ip = line.strip()
            if ip and ip not in ips and _looks_ipv4(ip):
                ips.append(ip)
    except (OSError, subprocess.TimeoutExpired):
        ips = []

    _eth_cache = (now, ips)
    return list(ips)


def _looks_ipv4(s: str) -> bool:
    parts = s.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _score_ip(ip: str) -> int:
    """同一张以太网多 IP 时的排序（略压低网关形 .1）。"""
    try:
        a, b, _c, d = (int(x) for x in ip.split("."))
    except ValueError:
        return -100
    if ip.startswith("127.") or ip.startswith("169.254."):
        return -100
    score = 0
    if a == 192 and b == 168:
        score += 40
    elif a == 10:
        score += 45
    elif a == 172 and 16 <= b <= 31:
        score += 35
    if d == 1:
        score -= 8
    return score


def best_lan_ipv4() -> str:
    """优先物理以太网 IP；没有有线再退回评分启发式。"""
    eth = ethernet_ipv4()
    if eth:
        return sorted(eth, key=_score_ip, reverse=True)[0]

    candidates = lan_ipv4()
    if not candidates:
        return default_route_ipv4() or "127.0.0.1"
    ranked = sorted(candidates, key=_score_ip, reverse=True)
    return ranked[0]


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


class _ShareHandler(SimpleHTTPRequestHandler):
    """目录列表；异常也回正文，避免浏览器只看到空响应。"""

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        # 不往 stderr 打，GUI 无控制台时无意义
        return

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except Exception:
            try:
                self.send_error(500, "internal error")
            except Exception:
                pass


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
        handler = partial(_ShareHandler, directory=str(path))
        ThreadingHTTPServer.allow_reuse_address = True
        try:
            httpd = ThreadingHTTPServer(("0.0.0.0", int(port)), handler)
        except OSError as e:
            raise OSError(f"端口 {port} 无法监听（可能被占用）: {e}") from e
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

    def primary_url(self) -> str:
        """给客户机的一条推荐地址（优先以太网）。"""
        if not self.running:
            return ""
        return f"http://{best_lan_ipv4()}:{self.port}/"

    def local_url(self) -> str:
        """本机自测地址（与 Everything 一样可用 127.0.0.1）。"""
        if not self.running:
            return ""
        return f"http://127.0.0.1:{self.port}/"

    def urls(self) -> list[str]:
        """全部网卡地址（仅日志排错用）。"""
        if not self.running:
            return []
        ips = lan_ipv4() or ["127.0.0.1"]
        return [f"http://{ip}:{self.port}/" for ip in ips]

    def probe_local(self) -> tuple[bool, str]:
        """绕过系统代理探测本机服务是否真在响应。"""
        url = self.local_url()
        if not url:
            return False, "未启动"
        try:
            import urllib.request

            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url, timeout=5) as r:
                body = r.read(64)
                if r.status == 200 and body:
                    return True, f"OK HTTP {r.status}"
                return False, f"异常 HTTP {r.status} 空正文={not body}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"


def ensure_firewall_allow(port: int, on_line=None) -> bool:
    """尝试为共享端口放行入站（同事连不上时常见原因是防火墙）。"""
    name = f"QtArm64Cross-HTTP-{int(port)}"
    # 先删同名再加，避免重复规则堆积
    cmds = [
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"],
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={name}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={int(port)}",
            "profile=any",
            "enable=yes",
        ],
    ]
    try:
        subprocess.run(cmds[0], capture_output=True, timeout=15, **wsl._hidden_kwargs())
        r = subprocess.run(
            cmds[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            **wsl._hidden_kwargs(),
        )
        ok = r.returncode == 0
        if on_line:
            if ok:
                on_line(f"[http] 已放行防火墙入站 TCP {port}（规则 {name}）")
            else:
                on_line(f"[http] 防火墙放行失败（可能需管理员）: {(r.stderr or r.stdout or '').strip()}")
                on_line("[http] 同事连不上时：Windows 安全中心 → 防火墙 → 允许应用，或用管理员重开本工具")
        return ok
    except (OSError, subprocess.TimeoutExpired) as e:
        if on_line:
            on_line(f"[http] 防火墙配置异常: {e}")
        return False
