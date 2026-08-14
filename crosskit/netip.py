"""给物理以太网追加/删除 IPv4（对应 Windows「高级 → IP 设置 → 添加」）。"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import tempfile
import time
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
    # 写 UTF-8 临时文件，避开控制台代码页把「以太网」弄成乱码
    fd, tmp = tempfile.mkstemp(prefix="qtarm64-eth-", suffix=".json")
    os.close(fd)
    tmp_path = Path(tmp)
    ps_tmp = str(tmp_path).replace("'", "''")
    ps = rf"""
$ErrorActionPreference = 'SilentlyContinue'
$out = @()
Get-NetAdapter -Physical | Where-Object {{
  $_.MediaType -eq '802.3' -or $_.NdisPhysicalMedium -eq '802.3'
}} | ForEach-Object {{
  $a = $_
  $ips = @(Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 | Where-Object {{
    $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'
  }} | ForEach-Object {{ @{{ address = $_.IPAddress; prefix = [int]$_.PrefixLength }} }})
  $out += @{{
    name = $a.Name
    ifIndex = [int]$a.ifIndex
    status = [string]$a.Status
    ips = $ips
  }}
}}
$json = if ($out.Count -eq 0) {{ '[]' }} else {{ ($out | ConvertTo-Json -Compress -Depth 4) }}
[System.IO.File]::WriteAllText('{ps_tmp}', $json, (New-Object System.Text.UTF8Encoding $false))
"""
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            timeout=15,
            **wsl._hidden_kwargs(),
        )
        text = tmp_path.read_text(encoding="utf-8").strip()
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return []
    finally:
        tmp_path.unlink(missing_ok=True)
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
        name = str(item.get("name") or "").strip()
        if not name or "\ufffd" in name:
            name = f"有线网卡#{int(item.get('ifIndex') or 0)}"
        adapters.append(
            EthAdapter(
                name=name,
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


def _helper_dir() -> Path:
    return Path(os.environ.get("TEMP", ".")) / "qtarm64-netip-helper"


def is_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _helper_running() -> bool:
    _d, alive, _c, _a = _helper_paths()
    if not alive.is_file():
        return False
    if _helper_ping():
        return True
    alive.unlink(missing_ok=True)
    return False


def elevation_ready() -> bool:
    return is_admin() or _helper_running()


def _helper_paths() -> tuple[Path, Path, Path, Path]:
    d = _helper_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d, d / "alive", d / "cmd.json", d / "ack.json"


def _helper_ping() -> bool:
    try:
        r = _helper_rpc({"op": "ping"}, timeout=1.5)
    except Exception:
        return False
    return bool(r.get("ok"))


def _helper_rpc(payload: dict, timeout: float = 60) -> dict:
    _d, _alive, cmd, ack = _helper_paths()
    if ack.is_file():
        ack.unlink(missing_ok=True)
    if cmd.is_file():
        cmd.unlink(missing_ok=True)
    cmd.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ack.is_file():
            try:
                text = ack.read_text(encoding="utf-8-sig").strip()
                data = json.loads(text) if text else {}
            except (OSError, json.JSONDecodeError):
                time.sleep(0.05)
                continue
            ack.unlink(missing_ok=True)
            if not isinstance(data, dict):
                return {"ok": False, "msg": "助手返回无效"}
            if "ok" not in data and "Ok" in data:
                data["ok"] = data["Ok"]
            return data
        time.sleep(0.08)
    cmd.unlink(missing_ok=True)
    return {"ok": False, "msg": "授权助手无响应"}


# ponytail: 作业走 %TEMP% 明文 JSON，本机可写即可投递；升级路径是 Named Pipe + ACL
_HELPER_PS1 = r"""
$ErrorActionPreference = 'Stop'
$dir = '{dir}'
$alive = Join-Path $dir 'alive'
$cmdf = Join-Path $dir 'cmd.json'
$ackf = Join-Path $dir 'ack.json'
$ppid = {ppid}
function Wack($ok, $msg) {{
  $obj = @{{ ok = [bool]$ok; msg = [string]$msg }}
  $json = $obj | ConvertTo-Json -Compress
  [System.IO.File]::WriteAllText($ackf, $json, (New-Object System.Text.UTF8Encoding $false))
}}
New-Item -ItemType Directory -Path $dir -Force | Out-Null
[System.IO.File]::WriteAllText($alive, '1', (New-Object System.Text.UTF8Encoding $false))
while (Test-Path $alive) {{
  if ($ppid -gt 0) {{
    if (-not (Get-Process -Id $ppid -ErrorAction SilentlyContinue)) {{ break }}
  }}
  if (Test-Path $cmdf) {{
    try {{
      $raw = [System.IO.File]::ReadAllText($cmdf)
      Remove-Item $cmdf -Force -ErrorAction SilentlyContinue
      $j = $raw | ConvertFrom-Json
      $op = [string]$j.op
      if ($op -eq 'exit') {{ Wack $true 'bye'; break }}
      if ($op -eq 'ping') {{ Wack $true 'pong'; continue }}
      if ($op -eq 'add') {{
        New-NetIPAddress -InterfaceIndex ([int]$j.ifIndex) -IPAddress ([string]$j.ip) -PrefixLength ([int]$j.prefix) | Out-Null
        Wack $true ('added ' + $j.ip)
        continue
      }}
      if ($op -eq 'del') {{
        Remove-NetIPAddress -InterfaceIndex ([int]$j.ifIndex) -IPAddress ([string]$j.ip) -Confirm:$false
        Wack $true ('removed ' + $j.ip)
        continue
      }}
      Wack $false ('unknown op')
    }} catch {{
      Wack $false ([string]$_.Exception.Message)
    }}
  }}
  Start-Sleep -Milliseconds 200
}}
Remove-Item $alive -Force -ErrorAction SilentlyContinue
"""


def ensure_elevation(on_line=None) -> tuple[str, str]:
    """点一次 UAC，拉起常驻助手；本次运行后续改 IP 不再弹窗。"""
    if is_admin():
        return "ok", "当前已是管理员，追加/删除 IP 无需再授权。"
    if _helper_running():
        return "ok", "已授权，本次运行期间追加/删除 IP 不再弹出 UAC。"

    d, alive, cmd, ack = _helper_paths()
    for p in (alive, cmd, ack):
        p.unlink(missing_ok=True)
    ps1 = d / "helper.ps1"
    body = _HELPER_PS1.format(dir=str(d).replace("'", "''"), ppid=os.getpid())
    ps1.write_text(body, encoding="utf-8-sig")
    ps1_arg = str(ps1).replace("'", "''")
    wrapper = (
        f"$p = Start-Process -FilePath 'powershell.exe' "
        f"-ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass',"
        f"'-WindowStyle','Hidden','-File','{ps1_arg}') "
        f"-Verb RunAs -WindowStyle Hidden -PassThru; "
        f"if ($null -eq $p) {{ exit 1223 }}; exit 0"
    )
    if on_line:
        on_line("[net] 请在弹出的 UAC 窗口点「是」（只需授权一次）…")
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", wrapper],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            **wsl._hidden_kwargs(),
        )
    except subprocess.TimeoutExpired:
        return "failed", "等待 UAC 超时"
    except OSError as e:
        return "failed", f"无法启动授权: {e}"
    if int(r.returncode) == 1223:
        return "cancelled", "已取消管理员授权"
    if int(r.returncode) != 0:
        return "failed", f"授权失败 exit={r.returncode}"

    deadline = time.time() + 20
    while time.time() < deadline:
        if _helper_ping():
            return "ok", "已授权，本次运行期间追加/删除 IP 不再弹出 UAC。"
        time.sleep(0.25)
    return "failed", "授权进程已启动，但助手未就绪"


def stop_helper() -> None:
    d, alive, cmd, ack = _helper_paths()
    try:
        if alive.is_file():
            _helper_rpc({"op": "exit"}, timeout=2)
    except Exception:
        pass
    alive.unlink(missing_ok=True)
    cmd.unlink(missing_ok=True)
    ack.unlink(missing_ok=True)


def _run_hidden_ps1(script: str) -> int:
    fd, path = tempfile.mkstemp(prefix="qtarm64-netip-", suffix=".ps1")
    os.close(fd)
    ps1 = Path(path)
    try:
        ps1.write_text(script, encoding="utf-8-sig")
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            capture_output=True,
            timeout=60,
            **wsl._hidden_kwargs(),
        )
        return int(r.returncode)
    except subprocess.TimeoutExpired:
        return 1
    except OSError:
        return 1
    finally:
        ps1.unlink(missing_ok=True)


def _drain_log(log: Path, on_line) -> None:
    if not log.is_file():
        return
    try:
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if on_line and line.strip():
                on_line(line.rstrip())
    except OSError:
        pass


def _apply_net_change(
    op: str,
    *,
    if_index: int,
    ip: str,
    prefix: int | None,
    script: str,
    on_line,
    log: Path,
) -> tuple[str, str]:
    """已是管理员或助手在跑则不再弹 UAC；否则先拉起常驻助手（只授权一次）。"""
    if is_admin():
        code = _run_hidden_ps1(script)
        _drain_log(log, on_line)
        if code != 0:
            return "failed", f"操作失败 exit={code}"
        return "ok", ""
    st, msg = ensure_elevation(on_line=on_line)
    if st != "ok":
        return st, msg
    payload: dict = {"op": op, "ifIndex": if_index, "ip": ip}
    if prefix is not None:
        payload["prefix"] = prefix
    r = _helper_rpc(payload, timeout=60)
    if r.get("ok"):
        if on_line and r.get("msg"):
            on_line(f"[net] {r.get('msg')}")
        return "ok", ""
    return "failed", str(r.get("msg") or "授权助手执行失败")


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
    status, detail = _apply_net_change(
        "add",
        if_index=ad.if_index,
        ip=ip,
        prefix=prefix,
        script=script,
        on_line=on_line,
        log=log,
    )
    httpshare.clear_ethernet_cache()
    if status == "ok":
        return "ok", f"已在 {ad.name} 添加 {ip}/{prefix}"
    if status == "cancelled":
        return "cancelled", "已取消管理员授权"
    return "failed", detail or "添加失败"


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
    status, detail = _apply_net_change(
        "del",
        if_index=ad.if_index,
        ip=ip,
        prefix=None,
        script=script,
        on_line=on_line,
        log=log,
    )
    httpshare.clear_ethernet_cache()
    if status == "ok":
        return "ok", f"已从 {ad.name} 删除 {ip}"
    if status == "cancelled":
        return "cancelled", "已取消管理员授权"
    return "failed", detail or "删除失败"
