#!/usr/bin/env bash
# 环境探测：输出 KEY=ok|missing，供 GUI 解析
set -euo pipefail
ROOTFS="${ROOTFS:-/opt/arm64-rootfs}"
QT_PREFIX="${QT_PREFIX:-/opt/Qt5.14.2-arm64}"
QT_HOST="${QT_HOST:-/opt/Qt5.14.2-host}"

check() {
  local key="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "${key}=ok"
  else
    echo "${key}=missing"
  fi
}

check wsl_shell true
check cross_gpp command -v aarch64-linux-gnu-g++
check cross_readelf command -v aarch64-linux-gnu-readelf
check pkg_config command -v pkg-config
check cmake_bin command -v cmake
check ccache_bin command -v ccache
check rootfs test -f "${ROOTFS}/etc/os-release"
check rootfs_glibc grep -q VERSION_CODENAME=focal "${ROOTFS}/etc/os-release"
check qt_widgets test -f "${QT_PREFIX}/lib/libQt5Widgets.so"
check qt_qmake test -x "${QT_HOST}/bin/qmake"
check qt_moc test -x "${QT_HOST}/bin/moc"
check qt_xcb test -f "${QT_PREFIX}/plugins/platforms/libqxcb.so"

echo "rootfs_path=${ROOTFS}"
echo "qt_prefix=${QT_PREFIX}"
if command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then
  echo "gcc_ver=$(aarch64-linux-gnu-gcc -dumpversion 2>/dev/null || echo unknown)"
  echo "gcc_machine=$(aarch64-linux-gnu-gcc -dumpmachine 2>/dev/null || echo aarch64-linux-gnu)"
else
  echo "gcc_ver=missing"
  echo "gcc_machine=missing"
fi
if [[ -x "${QT_HOST}/bin/qmake" ]]; then
  echo "qt_version=$("${QT_HOST}/bin/qmake" -query QT_VERSION 2>/dev/null || echo unknown)"
else
  echo "qt_version=missing"
fi
if [[ -f "${ROOTFS}/etc/os-release" ]]; then
  echo "rootfs_codename=$(grep VERSION_CODENAME= "${ROOTFS}/etc/os-release" | cut -d= -f2)"
fi
