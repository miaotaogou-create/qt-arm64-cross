#!/usr/bin/env bash
# 通用交叉编译：focal sysroot + Qt 5.14.2 → aarch64
# 由 GUI / run 通过 WSL 调用。环境变量见下方。
set -euo pipefail

ROOTFS="${ROOTFS:-/opt/arm64-rootfs}"
QT_PREFIX="${QT_PREFIX:-/opt/Qt5.14.2-arm64}"
QT_HOST="${QT_HOST:-/opt/Qt5.14.2-host}"
QMAKE="${QMAKE:-${QT_HOST}/bin/qmake}"
JOBS="${JOBS:-$(nproc)}"
SKIP_LIB_RE='GLIBC_2\.(3[2-9]|[4-9])'

# TOOLKIT：本工具仓库根（含 mkspec / cmake toolchain）
# PROJECT：用户工程根
TOOLKIT="${TOOLKIT:?请设置 TOOLKIT=本工具仓库路径}"
PROJECT="${PROJECT:?请设置 PROJECT=工程根目录}"
BUILD_SYSTEM="${BUILD_SYSTEM:-auto}"   # auto|qmake|cmake
PRO_FILE="${PRO_FILE:-}"
CMAKE_FILE="${CMAKE_FILE:-}"
APP_NAME="${APP_NAME:-}"
OUT_BIN="${OUT_BIN:-}"                 # 相对 PROJECT；空则按常见路径猜
DO_BUNDLE="${DO_BUNDLE:-0}"
EXTRA_PKGCONFIG="${EXTRA_PKGCONFIG:-}" # 空格分隔，如 "libavformat libavcodec"
BUILD_DIR="${BUILD_DIR:-build-arm64}"  # 仅 cmake
CLEAN="${CLEAN:-0}"                    # 1=清掉常见中间产物再编

QMAKE_SPEC="${TOOLKIT}/tools/qmake/linux-aarch64-focal"
QTCONF="${QMAKE_SPEC}/target-qt.conf"
CMAKE_TOOLCHAIN="${TOOLKIT}/tools/cmake/aarch64-focal-toolchain.cmake"

log() { echo "[cross] $*"; }

need() {
  command -v "$1" >/dev/null || { echo "缺少 $1 — 请以 root 执行 tools/setup_cross_focal.sh" >&2; exit 1; }
}

win_to_unix_nl() {
  # Windows 挂载的脚本可能带 CRLF
  local f
  for f in "$@"; do
    [[ -f "$f" ]] && sed -i 's/\r$//' "$f" || true
  done
}

need aarch64-linux-gnu-g++
need aarch64-linux-gnu-readelf
[[ -x "${QMAKE}" ]] || {
  echo "缺少 ${QMAKE} — 执行: wsl -d Ubuntu-20.04 -u root bash ${TOOLKIT}/tools/build_qt5142_arm64_cross.sh" >&2
  exit 1
}
[[ -f "${QT_PREFIX}/lib/libQt5Widgets.so" ]] || {
  echo "缺少 Qt 5.14.2：${QT_PREFIX}" >&2
  exit 1
}
[[ -f "${ROOTFS}/etc/os-release" ]] || {
  echo "缺少 sysroot：${ROOTFS}" >&2
  exit 1
}
[[ -f "${QMAKE_SPEC}/qmake.conf" ]] || { echo "缺少 mkspec: ${QMAKE_SPEC}" >&2; exit 1; }

export PKG_CONFIG=pkg-config
export PKG_CONFIG_SYSROOT_DIR="${ROOTFS}"
export PKG_CONFIG_LIBDIR="${ROOTFS}/usr/lib/aarch64-linux-gnu/pkgconfig:${ROOTFS}/usr/share/pkgconfig"
export ROOTFS QT_PREFIX QT_HOST

cd "${PROJECT}"

if [[ "${CLEAN}" == "1" ]]; then
  log "CLEAN=1，清理常见中间产物"
  rm -rf bin/release tmp/obj tmp/moc "${BUILD_DIR}" Makefile Makefile.* .qmake.stash 2>/dev/null || true
  rm -f qrc_*.cpp moc_*.cpp 2>/dev/null || true
fi

# --- 识别构建系统 ---
if [[ "${BUILD_SYSTEM}" == "auto" ]]; then
  if [[ -n "${PRO_FILE}" ]]; then
    BUILD_SYSTEM=qmake
  elif [[ -n "${CMAKE_FILE}" ]]; then
    BUILD_SYSTEM=cmake
  elif ls ./*.pro >/dev/null 2>&1; then
    BUILD_SYSTEM=qmake
    PRO_FILE="$(ls ./*.pro | head -1)"
    PRO_FILE="${PRO_FILE#./}"
  elif [[ -f CMakeLists.txt ]]; then
    BUILD_SYSTEM=cmake
    CMAKE_FILE=CMakeLists.txt
  else
    echo "未找到 .pro 或 CMakeLists.txt，请指定 PRO_FILE / CMAKE_FILE" >&2
    exit 1
  fi
fi

if [[ "${BUILD_SYSTEM}" == "qmake" ]]; then
  [[ -n "${PRO_FILE}" ]] || PRO_FILE="$(ls ./*.pro | head -1 | sed 's|^\./||')"
  [[ -f "${PRO_FILE}" ]] || { echo "找不到 ${PRO_FILE}" >&2; exit 1; }
  if [[ -z "${APP_NAME}" ]]; then
    APP_NAME="$(basename "${PRO_FILE}" .pro)"
  fi
elif [[ "${BUILD_SYSTEM}" == "cmake" ]]; then
  [[ -n "${CMAKE_FILE}" ]] || CMAKE_FILE=CMakeLists.txt
  [[ -f "${CMAKE_FILE}" ]] || { echo "找不到 ${CMAKE_FILE}" >&2; exit 1; }
  [[ -n "${APP_NAME}" ]] || APP_NAME="$(basename "${PROJECT}")"
else
  echo "未知 BUILD_SYSTEM=${BUILD_SYSTEM}" >&2
  exit 1
fi

check_glibc() {
  local bin="$1"
  log "glibc symbols ($bin):"
  strings "${bin}" | grep '^GLIBC_' | sort -Vu | tail -5 || true
  if strings "${bin}" | grep -qE "${SKIP_LIB_RE}"; then
    echo "ERROR: 二进制需要 glibc > 2.31（客户机为 focal/麒麟 glibc 2.31）" >&2
    exit 1
  fi
}

patch_qmake_makefile() {
  # 工具链层补丁（与 app_mast 验证过的行为一致）；与业务无关
  sed -i "s| /usr/lib/x86_64-linux-gnu/libGL.so | ${ROOTFS}/usr/lib/aarch64-linux-gnu/libGL.so |g" Makefile
  sed -i 's|--sysroot= |-pipe |g' Makefile
  sed -i 's|-lpthread|-pthread|g' Makefile
  sed -i "s|\(/opt/arm64-rootfs/usr/lib/aarch64-linux-gnu/libGL.so \)\$|\1${ROOTFS}/usr/lib/aarch64-linux-gnu/libstdc++.so.6 ${ROOTFS}/usr/lib/aarch64-linux-gnu/libgcc_s.so.1 |" Makefile
  sed -i "s|-pthread|${ROOTFS}/usr/lib/aarch64-linux-gnu/libpthread.so.0|" Makefile

  if [[ -n "${EXTRA_PKGCONFIG}" ]]; then
    # shellcheck disable=SC2086
    local ffmpeg_libs
    ffmpeg_libs=$(PKG_CONFIG_SYSROOT_DIR="${ROOTFS}" PKG_CONFIG_LIBDIR="${PKG_CONFIG_LIBDIR}" \
      pkg-config --libs ${EXTRA_PKGCONFIG})
    sed -i "s|LIBS          = \$(SUBLIBS)|LIBS          = \$(SUBLIBS) -Wl,-Bdynamic ${ffmpeg_libs} -Wl,-Bdynamic|" Makefile
  fi
}

resolve_out_bin() {
  if [[ -n "${OUT_BIN}" ]]; then
    [[ -x "${OUT_BIN}" ]] || { echo "OUT_BIN 不可执行: ${OUT_BIN}" >&2; exit 1; }
    return
  fi
  local candidates=(
    "bin/release/${APP_NAME}"
    "bin/${APP_NAME}"
    "${BUILD_DIR}/${APP_NAME}"
    "${APP_NAME}"
  )
  local c
  for c in "${candidates[@]}"; do
    if [[ -x "$c" ]]; then
      OUT_BIN="$c"
      return
    fi
  done
  # cmake 常见：build-arm64 下任意同名可执行文件
  if [[ -d "${BUILD_DIR}" ]]; then
    c="$(find "${BUILD_DIR}" -type f -name "${APP_NAME}" -perm -111 2>/dev/null | head -1 || true)"
    if [[ -n "$c" ]]; then
      OUT_BIN="$c"
      return
    fi
  fi
  echo "找不到产物可执行文件 APP_NAME=${APP_NAME}，请设置 OUT_BIN" >&2
  exit 1
}

# --- 编译 ---
if [[ "${BUILD_SYSTEM}" == "qmake" ]]; then
  log "qmake Qt $("${QMAKE}" -query QT_VERSION) spec=${QMAKE_SPEC} project=${PRO_FILE}"
  rm -f Makefile Makefile.* .qmake.stash 2>/dev/null || true
  "${QMAKE}" "${PRO_FILE}" CONFIG+=release \
    "SYSROOT=${ROOTFS}" \
    "QT_PREFIX=${QT_PREFIX}" \
    "QT_HOST=${QT_HOST}" \
    "PKG_CONFIG=pkg-config" \
    -qtconf "${QTCONF}" \
    -spec "${QMAKE_SPEC}"
  patch_qmake_makefile
  log "make -j${JOBS}"
  make -j"${JOBS}"
else
  need cmake
  log "cmake toolchain=${CMAKE_TOOLCHAIN} build=${BUILD_DIR}"
  rm -rf "${BUILD_DIR}"
  cmake -S "$(dirname "${CMAKE_FILE}")" -B "${BUILD_DIR}" \
    -DCMAKE_TOOLCHAIN_FILE="${CMAKE_TOOLCHAIN}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DQt5_DIR="${QT_PREFIX}/lib/cmake/Qt5" \
    -DQT_QMAKE_EXECUTABLE="${QMAKE}" \
    -DCMAKE_PREFIX_PATH="${QT_PREFIX}"
  cmake --build "${BUILD_DIR}" -j"${JOBS}"
fi

resolve_out_bin
file "${OUT_BIN}"
check_glibc "${OUT_BIN}"
log "产物: ${PROJECT}/${OUT_BIN}"

if [[ "${DO_BUNDLE}" == "1" ]]; then
  # 增量 make 常跳过链接 → POST_LINK/POST_BUILD 不跑 → 旁路资源（theme 等）缺失。
  # 打可部署包前强制重链一次，让工程自己的部署步骤落到可执行文件旁。
  log "打运行包：强制重链以触发工程 POST_LINK / POST_BUILD"
  rm -f "${OUT_BIN}"
  if [[ "${BUILD_SYSTEM}" == "qmake" ]]; then
    make -j"${JOBS}"
  else
    cmake --build "${BUILD_DIR}" -j"${JOBS}"
  fi
  resolve_out_bin
  file "${OUT_BIN}"
  check_glibc "${OUT_BIN}"

  win_to_unix_nl "${TOOLKIT}/tools/bundle.sh"
  chmod +x "${TOOLKIT}/tools/bundle.sh"
  export PROJECT APP_NAME OUT_BIN ROOTFS QT_PREFIX
  export PLUGINS="${PLUGINS:-platforms/libqxcb.so platforms/libqoffscreen.so}"
  export EXTRA_COPY="${EXTRA_COPY:-}"
  # OUT_DIR：产物压缩包所在目录（相对 PROJECT 或绝对路径）；空则 dist/arm64-kylin
  if [[ -n "${OUT_DIR:-}" ]]; then
    export BUNDLE_DIR="${OUT_DIR%/}/${APP_NAME}"
  fi
  bash "${TOOLKIT}/tools/bundle.sh"
fi

log "DONE"
