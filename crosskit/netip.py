"""给物理以太网追加/删除 IPv4（对应 Windows「高级 → IP 设置 → 添加」）。"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import httpshare, wsl


@dataclass
class EthIp:
    address: str
    prefix: int


@dataclass
class EthAdapter:
    name: str
    if_index: int
    status: str
    ips: list[EthIp]


def _looks_ipv4(s: str) -> bool:
    parts = s.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def mask_to_prefix(mask_or_prefix: str) -> int:
    """255.255.255.0 / 24 / /24 → 前缀长度。"""
    raw = (mask_or_prefix or "").strip().lstrip("/")
    if not raw:
        raise ValueError("请填写子网掩码或前缀长度")
    if raw.isdigit():
        n = int(raw)
        if not 0 <= n <= 32:
            raise ValueError(f"前缀长度无效: {n}")
        return n
    if not _looks_ipv4(raw):
        raise ValueError(f"掩码格式无效: {mask_or_prefix}")
    parts = [int(p) for p in raw.split(".")]
    bits = 0
    seen_zero = False
    for p in parts:
        if p < 0 or p > 255:
            raise ValueError(f"掩码格式无效: {mask_or_prefix}")
        b = bin(p)[2:].zfill(8)
        if "01" in b:
            raise ValueError(f"掩码不是连续 1: {mask_or_prefix}")
        ones = b.count("1")
        if seen_zero and ones:
            raise ValueError(f"掩码不是连续 1: {mask_or_prefix}")
        if ones < 8:
            seen_zero = True
        bits += ones
    return bits


def list_ethernet_adapters() -> list[EthAdapter]:
    """物理有线网卡 + 其上的 IPv4。"""
    ps = r"""
$ErrorActionPreference = 'SilentlyContinue'
$out = @()
Get-NetAdapter -Physical | Where-Object {
  $_.MediaType -eq '802.3' -or $_.NdisPhysicalMedium -eq '802.3'
} | ForEach-Object {
  $a = $_
  $ips = @(Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'
  } | ForEach-Object { @{ address = $_.IPAddress; prefix = [int]$_.PrefixLength } })
  $out += @{
    name = $a.Name
    ifIndex = [int]$a.ifIndex
    status = [string]$a.Status
    ips = $ips
  }
}
$out | ConvertTo-Json -Compress -Depth 4
"""
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            **wsl._hidden_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    text = (r.stdout or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    adapters: list[EthAdapter] = []
    for item in data:
        ips_raw = item.get("ips") or []
        if isinstance(ips_raw, dict):
            ips_raw = [ips_raw]
        ips = [
            EthIp(address=str(x.get("address", "")), prefix=int(x.get("prefix") or 0))
            for x in ips_raw
            if x.get("address") and _looks_ipv4(str(x.get("address")))
        ]
        adapters.append(
            EthAdapter(
                name=str(item.get("name") or ""),
                if_index=int(item.get("ifIndex") or 0),
                status=str(item.get("status") or ""),
                ips=ips,
            )
        )
    return [a for a in adapters if a.if_index > 0]


def pick_ethernet_adapter(adapters: list[EthAdapter] | None = None) -> EthAdapter | None:
    """优先已连接(Up)的有线网卡。"""
    ads = adapters if adapters is not None else list_ethernet_adapters()
    if not ads:
        return None
    up = [a for a in ads if a.status.lower() == "up"]
    pool = up or ads
    pool.sort(key=lambda a: len(a.ips), reverse=True)
    return pool[0]


def _run_elevated_ps1(script: str, on_line=None) -> int:
    fd, path = tempfile.mkstemp(prefix="qtarm64-netip-", suffix=".ps1")
    os.close(fd)
    ps1 = Path(path)
    try:
        ps1.write_text(script, encoding="utf-8-sig")
        wrapper = (
            f"$p = Start-Process -FilePath 'powershell.exe' "
            f"-ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','{ps1}') "
            f"-Verb RunAs -Wait -PassThru; "
            f"if ($null -eq $p) {{ exit 1223 }}; exit $p.ExitCode"
        )
        if on_line:
            on_line("[net] 请在弹出的 UAC 窗口点「是」…")
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", wrapper],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            **wsl._hidden_kwargs(),
        )
        if on_line:
            for line in (r.stdout or "").splitlines():
                if line.strip():
                    on_line(line.rstrip())
        return int(r.returncode)
    except subprocess.TimeoutExpired:
        if on_line:
            on_line("[net] 操作超时")
        return 1
    except OSError as e:
        if on_line:
            on_line(f"[net] 无法启动提升进程: {e}")
        return 1
    finally:
        ps1.unlink(missing_ok=True)


def add_ethernet_ipv4(
    ip: str,
    mask_or_prefix: str,
    *,
    if_index: int | None = None,
    on_line=None,
) -> tuple[str, str]:
    """追加地址。返回 (ok|cancelled|failed|exists, 说明)。"""
    ip = (ip or "").strip()
    if not _looks_ipv4(ip):
        return "failed", f"IP 无效: {ip}"
    try:
        prefix = mask_to_prefix(mask_or_prefix)
    except ValueError as e:
        return "failed", str(e)

    adapters = list_ethernet_adapters()
    if if_index is not None:
        ad = next((a for a in adapters if a.if_index == if_index), None)
    else:
        ad = pick_ethernet_adapter(adapters)
    if ad is None:
        return "failed", "未找到物理以太网卡"

    for existing in ad.ips:
        if existing.address == ip:
            return "exists", f"{ad.name} 已有 {ip}/{existing.prefix}"

    if on_line:
        on_line(f"[net] 将在「{ad.name}」(ifIndex={ad.if_index}) 追加 {ip}/{prefix}")

    log = Path(os.environ.get("TEMP", ".")) / "qt-arm64-cross-netip.log"
    script = f"""
$ErrorActionPreference = 'Stop'
$log = '{log.as_posix()}'
function W($m) {{ Add-Content -Path $log -Value $m -Encoding UTF8; Write-Output $m }}
try {{
  if (Test-Path $log) {{ Remove-Item $log -Force }}
  New-NetIPAddress -InterfaceIndex {ad.if_index} -IPAddress '{ip}' -PrefixLength {prefix} | Out-Null
  W "[net] 已添加 {ip}/{prefix} → {ad.name}"
  exit 0
}} catch {{
  W ("[net] 失败: " + $_.Exception.Message)
  exit 1
}}
"""
    code = _run_elevated_ps1(script, on_line=on_line)
    if log.is_file():
        try:
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
                if on_line and line.strip():
                    on_line(line.rstrip())
        except OSError:
            pass
    httpshare.clear_ethernet_cache()
    if code == 1223:
        return "cancelled", "已取消管理员授权"
    if code != 0:
        return "failed", f"添加失败 exit={code}"
    return "ok", f"已在 {ad.name} 添加 {ip}/{prefix}"


def remove_ethernet_ipv4(ip: str, *, if_index: int | None = None, on_line=None) -> tuple[str, str]:
    """删除附加地址（需 UAC）。"""
    ip = (ip or "").strip()
    if not _looks_ipv4(ip):
        return "failed", f"IP 无效: {ip}"
    adapters = list_ethernet_adapters()
    ad = None
    if if_index is not None:
        ad = next((a for a in adapters if a.if_index == if_index), None)
    else:
        for a in adapters:
            if any(x.address == ip for x in a.ips):
                ad = a
                break
    if ad is None:
        return "failed", f"有线网卡上找不到 {ip}"

    log = Path(os.environ.get("TEMP", ".")) / "qt-arm64-cross-netip.log"
    script = f"""
$ErrorActionPreference = 'Stop'
$log = '{log.as_posix()}'
function W($m) {{ Add-Content -Path $log -Value $m -Encoding UTF8; Write-Output $m }}
try {{
  if (Test-Path $log) {{ Remove-Item $log -Force }}
  Remove-NetIPAddress -InterfaceIndex {ad.if_index} -IPAddress '{ip}' -Confirm:$false
  W "[net] 已删除 {ip} ← {ad.name}"
  exit 0
}} catch {{
  W ("[net] 失败: " + $_.Exception.Message)
  exit 1
}}
"""
    if on_line:
        on_line(f"[net] 将从「{ad.name}」删除 {ip}")
    code = _run_elevated_ps1(script, on_line=on_line)
    if log.is_file():
        try:
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
                if on_line and line.strip():
                    on_line(line.rstrip())
        except OSError:
            pass
    httpshare.clear_ethernet_cache()
    if code == 1223:
        return "cancelled", "已取消管理员授权"
    if code != 0:
        return "failed", f"删除失败 exit={code}"
    return "ok", f"已从 {ad.name} 删除 {ip}"
