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

## 启动（推荐）

双击 **`QtArm64Cross.exe`** 即可（绿色单文件：内嵌 GUI、`tools/` 与 Tcl/Tk，可单独拷到任意目录）。

首次运行会把 Tcl/Tk 缓存到 `%LOCALAPPDATA%\QtArm64Cross\`。交叉编译依赖本机 WSL 发行版（默认 `Ubuntu-20.04`）及其中的工具链/Qt。

### 换机 / 发给同事（推荐）

环境太大，**不打进 exe / 不进 git 仓库**。交付两样东西即可：

1. `QtArm64Cross.exe`（仓库根目录，或自行 `.\build_exe.ps1`）
2. 环境包 [`Ubuntu-20.04-cross-env.tar.gz`](https://github.com/miaotaogou-create/qt-arm64-cross/releases/tag/env-ubuntu-20.04)（约 1.8 GB，GitHub Release）

也可在本机 GUI「交叉编译环境包」→ **导出环境包** 自行再打一份。

对方机器：

1. 双击 `QtArm64Cross.exe` → **一键导入环境包** → 选中该 `.tar.gz`
2. 若尚未启用 WSL，会弹出 UAC，点「是」即可自动启用；若提示需重启，重启后再开本工具会接着导入
3. 导入完成后点 **检测环境**（成功时也会自动检测）
4. 打开工程交叉编译；编 **app_mast 同类**（Qt Widgets + FFmpeg）时勾选「附加 FFmpeg」

导出默认是**完整环境**（与本机已验证工具链一致：交叉编译器、`/opt/arm64-rootfs`、已安装的 Qt 前缀、sysroot 内 FFmpeg）。可选勾选去掉 `/opt/qt5142-cross`（仅当初编 Qt 的源码缓存，不影响交叉编译）。

重新打包 GUI：

```powershell
pip install pyinstaller
.\build_exe.ps1
```

开发调试仍可用：`python run.py`

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
   - **附加 FFmpeg**：勾选后自动链接 `libavformat/libavcodec/libavutil/libswscale`（多数视频工程需要；纯 Widgets 可不勾）
   - **其他 pkg-config**：FFmpeg 以外的额外包名（空格分隔）
   - **EXTRA_COPY**：打包时额外拷贝，格式 `源:目标`，空格分隔
   - **插件**：默认 `platforms/libqxcb.so platforms/libqoffscreen.so`
3. 勾选 **打运行包**（可选）→ **交叉编译**
4. 日志流式输出；失败可 **复制日志**；成功用 **打开产物目录**
5. **客户机下载**：在「HTTP 共享」里点 **用产物目录** → **启动共享**，把显示的 `http://本机IP:端口/` 给客户机（浏览器或 `wget`）。效果类似 Everything 的 HTTP 服务，无需再开 Everything。若客户机访问不通，检查 Windows 防火墙是否放行该端口。

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
- **勾选「附加 FFmpeg」**
- EXTRA_COPY（可选）：`src/core/config/app_config.json:config/app_config.json`
- 插件可按需加上：`sqldrivers/libqsqlite.so`

本工具**不会**默认跑 mediamtx / 桌面安装补丁等 app_mast 专属步骤。

需要强制全量重编时，命令行加 `CLEAN=1`。

## 目录结构

```
qt-arm64-cross/
  QtArm64Cross.exe       # 绿色单文件，双击即可
  build_exe.ps1          # 重新打包 exe
  run.py                 # 开发用入口
  crosskit/              # WSL 编排、检测、设置、HTTP 共享
  gui/                   # tkinter 界面
  tools/                 # 源码侧工具链脚本（也会打进 exe）
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
