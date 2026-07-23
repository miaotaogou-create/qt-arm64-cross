#!/usr/bin/env bash
# 一次性主机环境：WSL Ubuntu 20.04 交叉编译工具链 + focal arm64 sysroot
# 以 root 执行: wsl -u root bash .../tools/setup_cross_focal.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:7897}"

export http_proxy="${PROXY_URL}" https_proxy="${PROXY_URL}"
apt-get update
apt-get install -y --no-install-recommends \
  build-essential g++ \
  gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
  binutils-aarch64-linux-gnu \
  qemu-user-static debootstrap \
  pkg-config file wget xz-utils cmake

bash "${SCRIPT_DIR}/ensure_focal_rootfs.sh"
echo "[setup] cross g++: $(command -v aarch64-linux-gnu-g++)"
echo "[setup] sysroot: /opt/arm64-rootfs"
echo "[setup] 下一步（root，约 1 小时一次）: bash ${SCRIPT_DIR}/build_qt5142_arm64_cross.sh"
