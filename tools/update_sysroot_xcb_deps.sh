#!/usr/bin/env bash
# 向 focal ARM64 sysroot 安装 xcb/xkb + ffmpeg 依赖（QEMU chroot）。
# 以 root 执行: wsl -d Ubuntu-20.04 -u root bash .../tools/update_sysroot_xcb_deps.sh
set -euo pipefail

ROOTFS="${ROOTFS:-/opt/arm64-rootfs}"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:7897}"

cleanup_mounts() {
  local m
  for m in "${ROOTFS}/dev/pts" "${ROOTFS}/dev" "${ROOTFS}/sys" "${ROOTFS}/proc"; do
    mountpoint -q "$m" 2>/dev/null && umount -l "$m" || true
  done
}

[[ "$(id -u)" -eq 0 ]] || { echo "run as root" >&2; exit 1; }
[[ -f "${ROOTFS}/etc/os-release" ]] || { echo "missing ${ROOTFS}" >&2; exit 1; }

install -D -m 0755 /usr/bin/qemu-aarch64-static "${ROOTFS}/usr/bin/qemu-aarch64-static"
mkdir -p "${ROOTFS}/proc" "${ROOTFS}/sys" "${ROOTFS}/dev/pts"
mount -t proc proc "${ROOTFS}/proc"
mount --rbind /sys "${ROOTFS}/sys"
mount --rbind /dev "${ROOTFS}/dev"
trap cleanup_mounts EXIT

export http_proxy="${PROXY_URL}" https_proxy="${PROXY_URL}"
chroot "${ROOTFS}" /usr/bin/env DEBIAN_FRONTEND=noninteractive http_proxy="${PROXY_URL}" https_proxy="${PROXY_URL}" bash -lc "
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends \
  libfontconfig1-dev libfreetype6-dev libx11-dev libx11-xcb-dev libxext-dev \
  libxfixes-dev libxi-dev libxrender-dev libxcb1-dev libxcb-glx0-dev \
  libxcb-keysyms1-dev libxcb-image0-dev libxcb-shm0-dev libxcb-icccm4-dev \
  libxcb-sync-dev libxcb-xfixes0-dev libxcb-shape0-dev libxcb-randr0-dev \
  libxcb-render-util0-dev libxcb-util-dev libxkbcommon-dev libxkbcommon-x11-dev \
  libdbus-1-dev libgl1-mesa-dev libglib2.0-dev libsqlite3-dev \
  libavformat-dev libavcodec-dev libavutil-dev libswscale-dev
"

cleanup_mounts
trap - EXIT
echo "[sysroot] xcb deps OK"
