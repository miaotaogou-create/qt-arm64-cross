# Qt ARM64 交叉编译工具

Windows GUI + WSL `Ubuntu-20.04`，把任意 Qt 工程（`.pro` / `CMakeLists.txt`）交叉编译到 aarch64（glibc ≤ 2.31，适配麒麟等 focal 系客户机）。

工具链与路径沿用已验证环境，不另起炉灶：

| 组件 | WSL 路径 |
|------|----------|
| 交叉编译器 | `aarch64-linux-gnu-g++` |
| sysroot | `/opt/arm64-rootfs`（Ubuntu focal） |
| Qt 目标库 | `/opt/Qt5.14.2-arm64` |
| Qt 主机工具 | `/opt/Qt5.14.2-host` |

## 环境前提

- Windows 10/11，已启用 WSL
- 发行版名称：`Ubuntu-20.04`（可用「检测环境」确认）
- 本机 Python 3.8+（仅用标准库 tkinter，无第三方依赖）

## 首次安装

在仓库根目录启动 GUI：

```powershell
python run.py
```

1. 点 **检测环境**
2. 若缺交叉编译器 / sysroot：点 **安装工具链+sysroot**（WSL root，需能拉 apt；脚本默认代理 `http://127.0.0.1:7897`，可按本机改 `PROXY_URL`）
3. 若缺 Qt：点 **编译 Qt 5.14.2**（约一小时，只需一次）
4. 再检测，直到交叉编译器、sysroot、Qt 均为 OK

命令行等价：

```powershell
wsl -d Ubuntu-20.04 -u root bash /mnt/c/ZYL/workspace/projects/qt-arm64-cross/tools/setup_cross_focal.sh
wsl -d Ubuntu-20.04 -u root bash /mnt/c/ZYL/workspace/projects/qt-arm64-cross/tools/build_qt5142_arm64_cross.sh
```

## 日常用法

1. **浏览** 选择工程根目录（自动识别 `*.pro` / `CMakeLists.txt`）
2. 需要时填写：
   - **应用名**：产物可执行文件名（默认取 `.pro` 名或目录名）
   - **产物路径**：如 `bin/release/app_mast`（可空，脚本会按常见路径查找）
   - **EXTRA_PKGCONFIG**：工程额外依赖，例如 app_mast 填 `libavformat libavcodec libavutil libswscale`
   - **EXTRA_COPY**：打包时额外拷贝，格式 `源:目标`，空格分隔
   - **插件**：默认 `platforms/libqxcb.so platforms/libqoffscreen.so`
3. 勾选 **打运行包**（可选）→ **交叉编译**
4. 日志流式输出；失败可 **复制日志**；成功用 **打开产物目录**

设置保存在 `%USERPROFILE%\.qt-arm64-cross\settings.json`。

### 命令行编译（无 GUI）

```powershell
$tk = "/mnt/c/ZYL/workspace/projects/qt-arm64-cross"
$proj = "/mnt/c/ZYL/workspace/projects/qt-arm64-cross/examples/hello_qmake"
wsl -d Ubuntu-20.04 bash -lc "export TOOLKIT='$tk' PROJECT='$proj' BUILD_SYSTEM=qmake PRO_FILE=hello_qmake.pro DO_BUNDLE=1 && bash '$tk/tools/cross_build.sh'"
```

CMake 示例把 `BUILD_SYSTEM=cmake`、`CMAKE_FILE=CMakeLists.txt`、`PROJECT=.../hello_cmake` 即可。

### 编译 app_mast

- 工程目录：`...\app_mast`
- 构建文件：`app_mast.pro`
- 应用名：`app_mast`
- 产物路径：`bin/release/app_mast`
- EXTRA_PKGCONFIG：`libavformat libavcodec libavutil libswscale`
- EXTRA_COPY（可选）：`src/core/config/app_config.json:config/app_config.json`
- 插件可按需加上：`sqldrivers/libqsqlite.so audio/libqtaudio_alsa.so mediaservice/libgstmediaplayer.so`

本工具**不会**默认跑 mediamtx / 桌面安装补丁等 app_mast 专属步骤。

需要强制全量重编时，命令行加 `CLEAN=1`。

## 目录结构

```
qt-arm64-cross/
  run.py                 # GUI 入口
  crosskit/              # WSL 编排、检测、设置
  gui/                   # tkinter 界面
  tools/
    cross_build.sh       # 通用交叉编译
    bundle.sh            # 通用运行包
    env_check.sh
    setup_cross_focal.sh / ensure_focal_rootfs.sh
    build_qt5142_arm64_cross.sh
    qmake/linux-aarch64-focal/
    cmake/aarch64-focal-toolchain.cmake
  examples/hello_qmake/
  examples/hello_cmake/
```

## 约束与不做事项

- 产物须通过 `GLIBC_2.32+` 检查（脚本内保留）
- 不重做 Qt、不换 sysroot 发行版
- 不做完整 IDE、不做远程部署（可后续）
