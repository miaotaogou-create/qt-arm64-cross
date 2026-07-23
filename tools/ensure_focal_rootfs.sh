#!/usr/bin/env bash
# 确保 /opt/arm64-rootfs 存在且含编译依赖（chroot / 交叉编译共用）。
# 以 root 执行: wsl -u root bash .../tools/ensure_focal_rootfs.sh
set -euo pipefail

ROOTFS="${ROOTFS:-/opt/arm64-rootfs}"
UBUNTU_CODENAME="${UBUNTU_CODENAME:-focal}"
MIRROR="${MIRROR:-http://ports.ubuntu.com/ubuntu-ports}"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:7897}"

log() { echo "[rootfs] $*"; }

cleanup_mounts() {
  local m
  for m in "${ROOTFS}/dev/pts" "${ROOTFS}/dev" "${ROOTFS}/sys" "${ROOTFS}/proc"; do
    mountpoint -q "$m" 2>/dev/null && umount -l "$m" || true
  done
}

need_bootstrap() {
  [[ ! -f "${ROOTFS}/etc/os-release" ]] && return 0
  grep -q "VERSION_CODENAME=${UBUNTU_CODENAME}" "${ROOTFS}/etc/os-release" || return 0
  [[ ! -f "${ROOTFS}/usr/include/aarch64-linux-gnu/libavcodec/avcodec.h" ]] && return 0
  return 1
}

if need_bootstrap; then
  log "creating ${UBUNTU_CODENAME} arm64 rootfs at ${ROOTFS}"
  export http_proxy="${PROXY_URL}" https_proxy="${PROXY_URL}"
  cleanup_mounts
  rm -rf "${ROOTFS}"
  debootstrap --arch=arm64 --foreign "${UBUNTU_CODENAME}" "${ROOTFS}" "${MIRROR}"
  install -D -m 0755 /usr/bin/qemu-aarch64-static "${ROOTFS}/usr/bin/qemu-aarch64-static"
  tee "${ROOTFS}/etc/apt/sources.list" >/dev/null <<EOF
deb http://ports.ubuntu.com/ubuntu-ports ${UBUNTU_CODENAME} main restricted universe multiverse
deb http://ports.ubuntu.com/ubuntu-ports ${UBUNTU_CODENAME}-updates main restricted universe multiverse
deb http://ports.ubuntu.com/ubuntu-ports ${UBUNTU_CODENAME}-backports main restricted universe multiverse
deb http://ports.ubuntu.com/ubuntu-ports ${UBUNTU_CODENAME}-security main restricted universe multiverse
EOF
  tee "${ROOTFS}/etc/apt/apt.conf.d/99proxy" >/dev/null <<EOF
Acquire::http::Proxy "${PROXY_URL}";
Acquire::https::Proxy "${PROXY_URL}";
EOF
  cp /etc/resolv.conf "${ROOTFS}/etc/resolv.conf"
  mkdir -p "${ROOTFS}/proc" "${ROOTFS}/sys" "${ROOTFS}/dev/pts"
  mount -t proc proc "${ROOTFS}/proc"
  mount --rbind /sys "${ROOTFS}/sys"
  mount --rbind /dev "${ROOTFS}/dev"
  trap cleanup_mounts EXIT
  chroot "${ROOTFS}" /debootstrap/debootstrap --second-stage
  chroot "${ROOTFS}" /usr/bin/env DEBIAN_FRONTEND=noninteractive http_proxy="${PROXY_URL}" https_proxy="${PROXY_URL}" bash -lc "
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends \
  build-essential pkg-config file rsync ca-certificates \
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
else
  log "rootfs OK: ${ROOTFS} (${UBUNTU_CODENAME}, glibc $(chroot ${ROOTFS} ldd --version 2>/dev/null | head -1 || echo unknown))"
fi
