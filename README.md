# Qt ARM64 交叉编译工具

Windows 绿色 GUI + WSL `Ubuntu-20.04`，把 Qt 工程（`.pro` / `CMakeLists.txt`）交叉编译到 aarch64（glibc ≤ 2.31，适配麒麟等 focal 系客户机）。

界面三步：**1 环境 → 2 编译 → 3 共享**。

| 组件 | WSL 路径 |
|------|----------|
| 交叉编译器 | `aarch64-linux-gnu-g++` |
| sysroot | `/opt/arm64-rootfs`（Ubuntu focal） |
| Qt 目标库 | `/opt/Qt5.14.2-arm64` |
| Qt 主机工具 | `/opt/Qt5.14.2-host` |

## 交付物（换机 / 发给同事）

环境太大，**不打进 exe、不进 git**。两样东西即可：

1. `QtArm64Cross.exe`（仓库根目录；可单独拷贝）
2. 环境包 [`Ubuntu-20.04-cross-env.tar.gz`](https://github.com/miaotaogou-create/qt-arm64-cross/releases/tag/env-ubuntu-20.04)（约 1.8 GB，GitHub Release）

也可在本机 GUI「导出环境包」再打一份。

## 用法

### 1 环境

1. 双击 `QtArm64Cross.exe`
2. **一键导入环境包** → 选中上述 `.tar.gz`
3. 若尚未启用 WSL，按 UAC 提示操作；若需重启，重启后再开本工具会接着导入
4. 导入成功后会自动检测；显示「环境就绪」即可去编译

首次运行会把 Tcl/Tk 缓存到 `%LOCALAPPDATA%\QtArm64Cross\`。  
设置保存在 `%USERPROFILE%\.qt-arm64-cross\settings.json`。

### 2 编译

1. 选工程根目录（自动识别 `*.pro` / `CMakeLists.txt`）
2. 需要时填写应用名、产物路径；视频类工程勾选 **附加 FFmpeg**
3. 勾选 **打运行包**（可选）→ **交叉编译**（环境未就绪时按钮不可点）
4. 日志在本页；成功后可用 **打开产物文件夹** / **去共享**

高级项（其他 pkg-config、EXTRA_COPY、插件列表等）收在「高级」里。默认插件含 `platforms/libqxcb.so`；缺 qxcb 时打包会失败，避免客户机下了却开不了窗。

强制全量重编（命令行）：加环境变量 `CLEAN=1`。

### 3 共享

**用产物目录** → **启动共享**，把显示的 `http://本机IP:端口/` 给客户机（浏览器或 `wget`）。访问不通时检查 Windows 防火墙是否放行该端口。

## 从零搭建（无环境包时）

有 Release 环境包时**不必**走这条路径。仅在无包、或要本机重编工具链/Qt 时使用：

1. 已装好 WSL，且发行版名为 `Ubuntu-20.04`
2. GUI「从零搭建」→ **安装工具链** → 再 **编译 Qt 5.14.2**（后者约一小时）
3. 脚本默认代理 `http://127.0.0.1:7897`，可按本机改 `PROXY_URL`

命令行等价（把 `TOOLKIT` 换成你本机仓库在 WSL 下的路径）：

```powershell
wsl -d Ubuntu-20.04 -u root bash /mnt/c/path/to/qt-arm64-cross/tools/setup_cross_focal.sh
wsl -d Ubuntu-20.04 -u root bash /mnt/c/path/to/qt-arm64-cross/tools/build_qt5142_arm64_cross.sh
```

## 开发与重新打包

日常交付用 exe，不必装 Python。改界面/脚本后：

```powershell
pip install pyinstaller
.\build_exe.ps1
```

开发调试：`python run.py`  
最小自检：`python selfcheck.py`

### 命令行编译（无 GUI）

```powershell
$tk = "/mnt/c/path/to/qt-arm64-cross"
$proj = "$tk/examples/hello_qmake"
wsl -d Ubuntu-20.04 bash -lc "export TOOLKIT='$tk' PROJECT='$proj' BUILD_SYSTEM=qmake PRO_FILE=hello_qmake.pro DO_BUNDLE=1 && bash '$tk/tools/cross_build.sh'"
```

CMake：设 `BUILD_SYSTEM=cmake`、`CMAKE_FILE=CMakeLists.txt`。

### 编译 app_mast 类工程

- 构建文件：`app_mast.pro`
- 产物路径：如 `bin/release/app_mast`
- **勾选「附加 FFmpeg」**
- 皮肤/配置等由工程 `.pro` / CMake 的 POST_LINK、POST_BUILD 落到可执行文件旁；本工具只打包旁路已有文件

本工具不会默认跑 mediamtx 等工程专属步骤。

## 目录结构

```
qt-arm64-cross/
  QtArm64Cross.exe       # 绿色单文件，双击即可
  build_exe.ps1          # 重新打包 exe
  run.py                 # 开发用入口
  crosskit/              # WSL 编排、检测、设置、HTTP 共享
  gui/                   # tkinter 界面
  tools/                 # 工具链脚本（打进 exe）
  examples/hello_qmake/
  examples/hello_cmake/
```

## 约束

- 产物须通过 `GLIBC_2.32+` 检查（脚本内保留）
- 不重做 Qt、不换 sysroot 发行版
- 不做完整 IDE、不做远程部署
