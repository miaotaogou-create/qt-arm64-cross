#!/usr/bin/env bash
# 交叉编译 Qt 5.14.2（aarch64 / focal sysroot / glibc 2.31）。以 root 执行一次即可。
#   wsl -d Ubuntu-20.04 -u root bash .../tools/build_qt5142_arm64_cross.sh
set -euo pipefail

ROOTFS="${ROOTFS:-/opt/arm64-rootfs}"
QT_PREFIX="${QT_PREFIX:-/opt/Qt5.14.2-arm64}"
QT_HOST="${QT_HOST:-/opt/Qt5.14.2-host}"
QT_WORK="${QT_WORK:-/opt/qt5142-cross}"
QT_TAR="${QT_TAR:-${QT_WORK}/qt-everywhere-src-5.14.2.tar.xz}"
QT_SRC="${QT_SRC:-${QT_WORK}/qt-everywhere-src-5.14.2}"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:7897}"
QT_URLS=(
  "https://download.qt.io/archive/qt/5.14/5.14.2/single/qt-everywhere-src-5.14.2.tar.xz"
  "https://mirrors.tuna.tsinghua.edu.cn/qt/archive/qt/5.14/5.14.2/single/qt-everywhere-src-5.14.2.tar.xz"
)
JOBS="${JOBS:-$(nproc)}"

log() { echo "[qt5142-cross] $*"; }

[[ "$(id -u)" -eq 0 ]] || { echo "run as root" >&2; exit 1; }
[[ -f "${ROOTFS}/etc/os-release" ]] || { echo "missing ${ROOTFS} — run ensure_focal_rootfs.sh first" >&2; exit 1; }
command -v aarch64-linux-gnu-g++ >/dev/null || { echo "missing aarch64-linux-gnu-g++" >&2; exit 1; }

if [[ -f "${QT_PREFIX}/lib/libQt5Widgets.so" ]] && [[ -x "${QT_HOST}/bin/qmake" ]]; then
  log "already installed: ${QT_PREFIX} (host qmake ${QT_HOST}/bin/qmake)"
  "${QT_HOST}/bin/qmake" -query QT_VERSION QT_INSTALL_PREFIX 2>/dev/null || true
  exit 0
fi

export http_proxy="${PROXY_URL}" https_proxy="${PROXY_URL}"
mkdir -p "${QT_WORK}"

if [[ ! -f "${QT_SRC}/qtbase/configure" ]]; then
  if [[ ! -f "${QT_TAR}" ]] || ! xz -t "${QT_TAR}" 2>/dev/null; then
    rm -f "${QT_TAR}"
    log "downloading Qt 5.14.2 source ..."
    ok=0
    for url in "${QT_URLS[@]}"; do
      if wget -O "${QT_TAR}" "${url}"; then ok=1; break; fi
      rm -f "${QT_TAR}"
    done
    [[ "${ok}" -eq 1 ]] || { echo "Qt source download failed" >&2; exit 1; }
  fi
  log "extracting ${QT_TAR} ..."
  tar -xJf "${QT_TAR}" -C "${QT_WORK}"
fi

export PKG_CONFIG=pkg-config
export PKG_CONFIG_SYSROOT_DIR="${ROOTFS}"
export PKG_CONFIG_LIBDIR="${ROOTFS}/usr/lib/aarch64-linux-gnu/pkgconfig:${ROOTFS}/usr/share/pkgconfig"

# ponytail: hide static pthread/dl so shared libQt5*.so links against .so not .a (avoids _dl_* undefined refs)
hide_static_glibc() {
  local d="${ROOTFS}/usr/lib/aarch64-linux-gnu" f
  for f in libpthread.a libdl.a; do
    [[ -f "${d}/${f}" && ! -f "${d}/${f}.qt-hide" ]] && mv "${d}/${f}" "${d}/${f}.qt-hide"
  done
}
restore_static_glibc() {
  local d="${ROOTFS}/usr/lib/aarch64-linux-gnu" f
  for f in libpthread.a libdl.a; do
    [[ -f "${d}/${f}.qt-hide" ]] && mv "${d}/${f}.qt-hide" "${d}/${f}"
  done
}
trap restore_static_glibc EXIT

MK_SPEC="${QT_SRC}/qtbase/mkspecs/linux-aarch64-gnu-g++/qmake.conf"
if ! grep -q 'rpath-link.*arm64-rootfs' "${MK_SPEC}" 2>/dev/null; then
  cat >> "${MK_SPEC}" <<EOF

QMAKE_LFLAGS += -Wl,-rpath-link,${ROOTFS}/usr/lib/aarch64-linux-gnu -Wl,-rpath-link,${ROOTFS}/lib/aarch64-linux-gnu
QMAKE_LFLAGS += -Wl,-Bdynamic
EOF
fi
hide_static_glibc

BUILD="${QT_WORK}/build-qtbase"
if [[ -f "${BUILD}/config.summary" ]] && grep -qE 'XCB XKB \.+ yes' "${BUILD}/config.summary"; then
  log "resuming qtbase build in ${BUILD} ..."
else
  rm -rf "${BUILD}"
  mkdir -p "${BUILD}"
  cd "${BUILD}"

  log "configure qtbase (prefix=${QT_PREFIX}, sysroot=${ROOTFS}) ..."
  "${QT_SRC}/qtbase/configure" \
    -opensource -confirm-license \
    -release \
    -prefix "${QT_PREFIX}" \
    -extprefix "${QT_PREFIX}" \
    -hostprefix "${QT_HOST}" \
    -sysroot "${ROOTFS}" \
    -xplatform linux-aarch64-gnu-g++ \
    -device-option "CROSS_COMPILE=aarch64-linux-gnu-" \
    -device-option "QMAKE_LFLAGS+=-Wl,-rpath-link,${ROOTFS}/usr/lib/aarch64-linux-gnu -Wl,-rpath-link,${ROOTFS}/lib/aarch64-linux-gnu -Wl,-Bdynamic" \
    -no-opengl \
    -xcb \
    -no-gtk \
    -no-openssl \
    -sql-sqlite \
    -qt-sqlite \
    -nomake examples \
    -nomake tests

  grep -E 'DirectFB|XCB|xkbcommon|sqlite' config.summary | head -25
  grep -qE 'xkbcommon \.+ yes|XCB XKB \.+ yes' config.summary || { echo "xcb 未启用 — 请以 root 执行 tools/update_sysroot_xcb_deps.sh" >&2; exit 1; }
fi
cd "${BUILD}"

log "build qtbase (jobs=${JOBS}) ..."
make -j"${JOBS}"
make install

log "build qtmultimedia ..."
MM_BUILD="${QT_WORK}/build-qtmultimedia"
rm -rf "${MM_BUILD}"
mkdir -p "${MM_BUILD}"
cd "${MM_BUILD}"
"${QT_HOST}/bin/qmake" "${QT_SRC}/qtmultimedia"
make -j"${JOBS}"
make install

test -f "${QT_PREFIX}/lib/libQt5Widgets.so"
test -f "${QT_PREFIX}/lib/libQt5Multimedia.so"
test -f "${QT_PREFIX}/plugins/platforms/libqxcb.so"
test -x "${QT_HOST}/bin/qmake"
test -x "${QT_HOST}/bin/moc"

log "OK Qt $( "${QT_HOST}/bin/qmake" -query QT_VERSION )"
log "  target: ${QT_PREFIX}"
log "  host:   ${QT_HOST}"
