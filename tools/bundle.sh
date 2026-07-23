#!/usr/bin/env bash
# 通用运行包：可执行文件 + 旁路资源 + Qt 插件 + 依赖 so + run.sh
# 旁路资源（theme/config 等）须由工程 .pro / CMakeLists.txt 在编译时放到可执行文件同目录；
# 本脚本只打包输出目录里已有内容，不解析工程源码树。
# 环境变量：PROJECT APP_NAME OUT_BIN ROOTFS QT_PREFIX
# 可选：BUNDLE_DIR PLUGINS EXTRA_COPY（src:dst 空格分隔，相对 PROJECT）
set -euo pipefail

ROOTFS="${ROOTFS:-/opt/arm64-rootfs}"
QT_PREFIX="${QT_PREFIX:-/opt/Qt5.14.2-arm64}"
PROJECT="${PROJECT:?请设置 PROJECT}"
APP_NAME="${APP_NAME:?请设置 APP_NAME}"
OUT_BIN="${OUT_BIN:?请设置 OUT_BIN}"
BUNDLE_DIR="${BUNDLE_DIR:-dist/arm64-kylin/${APP_NAME}}"
# 默认 Widgets 可用的最小插件集
PLUGINS="${PLUGINS:-platforms/libqxcb.so platforms/libqoffscreen.so}"
EXTRA_COPY="${EXTRA_COPY:-}"
SKIP_RE='^(libc\.so|libpthread\.so|libdl\.so|libm\.so|librt\.so|libstdc\+\+\.so|libgcc_s\.so|ld-linux-aarch64\.so)'
SKIP_LIB_RE='GLIBC_2\.(3[2-9]|[4-9])'

log() { echo "[bundle] $*"; }

cd "${PROJECT}"
[[ -x "${OUT_BIN}" ]] || { echo "missing ${OUT_BIN}" >&2; exit 1; }

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}/lib" "${BUNDLE_DIR}/plugins"
cp "${OUT_BIN}" "${BUNDLE_DIR}/${APP_NAME}"
chmod 755 "${BUNDLE_DIR}/${APP_NAME}"

# 只打包「编译输出目录里、可执行文件旁」已有的东西。
# theme/config 等定制资源由工程 .pro / CMakeLists.txt 的 POST_LINK、POST_BUILD、install 负责落到此处；
# 本工具不猜测工程源码树布局。
out_dir="$(dirname "${OUT_BIN}")"
out_base="$(basename "${OUT_BIN}")"
shopt -s nullglob
for item in "${out_dir}"/*; do
  name="$(basename "${item}")"
  [[ "${name}" == "${out_base}" ]] && continue
  [[ "${name}" == "${APP_NAME}" ]] && continue
  if [[ -d "${item}" ]]; then
    cp -a "${item}" "${BUNDLE_DIR}/"
    log "旁路目录: ${name}/"
  elif [[ -f "${item}" ]]; then
    case "${name}" in
      *.o|*.obj|*.cpp|*.h|*.hpp|Makefile*|*.stash|*.prl|*.pc) continue ;;
    esac
    cp -a "${item}" "${BUNDLE_DIR}/"
    log "旁路文件: ${name}"
  fi
done
shopt -u nullglob

if [[ -n "${EXTRA_COPY}" ]]; then
  local_pair=
  for local_pair in ${EXTRA_COPY}; do
    src="${local_pair%%:*}"
    dst="${local_pair#*:}"
    mkdir -p "${BUNDLE_DIR}/$(dirname "${dst}")"
    cp -a "${src}" "${BUNDLE_DIR}/${dst}"
  done
fi

cat >"${BUNDLE_DIR}/qt.conf" <<'QTC'
[Paths]
Prefix=.
Libraries=lib
Plugins=plugins
QTC

copy_plugin() {
  local rel="$1"
  local src="${QT_PREFIX}/plugins/${rel}"
  local dst="${BUNDLE_DIR}/plugins/${rel}"
  if [[ -f "${src}" ]]; then
    mkdir -p "$(dirname "${dst}")"
    cp -L "${src}" "${dst}"
    chmod 755 "${dst}"
  else
    log "跳过缺失插件: ${rel}"
  fi
}

for p in ${PLUGINS}; do
  copy_plugin "${p}"
done

should_skip() { [[ "$1" =~ ${SKIP_RE} ]]; }

resolve_lib() {
  local name="$1"
  local dir base path
  for dir in \
    "${QT_PREFIX}/lib" \
    "${ROOTFS}/lib/aarch64-linux-gnu" \
    "${ROOTFS}/usr/lib/aarch64-linux-gnu" \
    "${ROOTFS}/lib"; do
    if [[ -f "${dir}/${name}" ]]; then
      echo "${dir}/${name}"
      return 0
    fi
  done
  base="${name%%.*}"*
  for dir in \
    "${QT_PREFIX}/lib" \
    "${ROOTFS}/lib/aarch64-linux-gnu" \
    "${ROOTFS}/usr/lib/aarch64-linux-gnu"; do
    for path in "${dir}/${base}"*; do
      [[ -f "${path}" ]] || continue
      echo "${path}"
      return 0
    done
  done
  return 1
}

needed_sos() {
  aarch64-linux-gnu-readelf -d "$1" 2>/dev/null \
    | awk '/NEEDED/ {gsub(/[\[\]]/,"",$5); print $5}'
}

copy_deps_of() {
  local target="$1"
  local so resolved base dst
  while IFS= read -r so; do
    [[ -n "${so}" ]] || continue
    should_skip "${so}" && continue
    resolved="$(resolve_lib "${so}")" || continue
    base="$(basename "${resolved}")"
    dst="${BUNDLE_DIR}/lib/${base}"
    if [[ ! -f "${dst}" ]]; then
      cp -L "${resolved}" "${dst}"
      chmod 755 "${dst}"
      echo "${dst}"
    fi
  done < <(needed_sos "${target}")
}

mapfile -t pending < <(printf '%s\n' "${BUNDLE_DIR}/${APP_NAME}" && find "${BUNDLE_DIR}/plugins" -type f -name '*.so*' 2>/dev/null | sort)
i=0
while (( i < ${#pending[@]} )); do
  cur="${pending[i]}"
  while IFS= read -r added; do
    [[ -n "${added}" ]] && pending+=("${added}")
  done < <(copy_deps_of "${cur}")
  i=$((i + 1))
done

cat >"${BUNDLE_DIR}/run.sh" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export LD_LIBRARY_PATH="$ROOT/lib:${LD_LIBRARY_PATH:-}"
export QT_PLUGIN_PATH="$ROOT/plugins"
exec "$ROOT/__APP_NAME__" "$@"
RUN
sed -i "s/__APP_NAME__/${APP_NAME}/g" "${BUNDLE_DIR}/run.sh"
chmod +x "${BUNDLE_DIR}/run.sh"
sed -i 's/\r$//' "${BUNDLE_DIR}/run.sh"

{
  echo "build: ubuntu-focal arm64 Qt 5.14.2 cross (sysroot ${ROOTFS})"
  echo "qt: ${QT_PREFIX}"
  chroot "${ROOTFS}" ldd --version 2>/dev/null | head -1 || true
  file "${BUNDLE_DIR}/${APP_NAME}"
} > "${BUNDLE_DIR}/build_info.txt"

if strings "${BUNDLE_DIR}/${APP_NAME}" | grep -qE "${SKIP_LIB_RE}"; then
  echo "ERROR: 打包后的二进制需要 glibc > 2.31" >&2
  exit 1
fi

TAR_PARENT="$(dirname "${BUNDLE_DIR}")"
TAR_NAME="$(basename "${BUNDLE_DIR}")"
mkdir -p "${TAR_PARENT}"
tar -C "${TAR_PARENT}" -czf "${TAR_PARENT}/${TAR_NAME}_bundle.tar.gz" "${TAR_NAME}"
log "libs: $(find "${BUNDLE_DIR}/lib" -type f | wc -l)"
ls -lh "${TAR_PARENT}/${TAR_NAME}_bundle.tar.gz"
log "目录: ${PROJECT}/${BUNDLE_DIR}"
