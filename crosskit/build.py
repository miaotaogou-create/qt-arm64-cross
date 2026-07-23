"""编译编排：拼环境变量，调 tools/cross_build.sh。"""
from __future__ import annotations

from pathlib import Path

from . import detect, wsl


def discover_build_files(project: str | Path) -> list[tuple[str, str]]:
    """返回 [(kind, relative_path), ...] kind=qmake|cmake"""
    root = Path(project)
    found: list[tuple[str, str]] = []
    if not root.is_dir():
        return found
    for p in sorted(root.glob("*.pro")):
        found.append(("qmake", p.name))
    cmake = root / "CMakeLists.txt"
    if cmake.is_file():
        found.append(("cmake", "CMakeLists.txt"))
    # 一层子目录常见布局
    for p in sorted(root.glob("*/*.pro")):
        found.append(("qmake", str(p.relative_to(root)).replace("\\", "/")))
    for p in sorted(root.glob("*/CMakeLists.txt")):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if rel != "CMakeLists.txt":
            found.append(("cmake", rel))
    return found


def build(
    *,
    project: str,
    build_system: str,
    build_file: str,
    app_name: str,
    out_bin: str,
    jobs: int,
    do_bundle: bool,
    plugins: str,
    extra_pkgconfig: str,
    extra_copy: str,
    distro: str = wsl.DEFAULT_DISTRO,
    on_line=None,
) -> int:
    tk = detect.toolkit_root()
    tk_w = wsl.win_to_wsl(tk)
    proj_w = wsl.win_to_wsl(project)

    env = {
        "TOOLKIT": tk_w,
        "PROJECT": proj_w,
        "BUILD_SYSTEM": build_system if build_system != "auto" else "auto",
        "JOBS": str(jobs if jobs > 0 else "$(nproc)"),
        "DO_BUNDLE": "1" if do_bundle else "0",
        "PLUGINS": plugins.strip(),
        "EXTRA_PKGCONFIG": extra_pkgconfig.strip(),
        "EXTRA_COPY": extra_copy.strip(),
    }
    # jobs 不能是 $(nproc) 字符串进 export；空则让脚本自己 nproc
    if jobs <= 0:
        del env["JOBS"]
    else:
        env["JOBS"] = str(jobs)

    if build_system == "qmake" or (build_system == "auto" and build_file.endswith(".pro")):
        env["BUILD_SYSTEM"] = "qmake"
        env["PRO_FILE"] = build_file
    elif build_system == "cmake" or build_file.endswith("CMakeLists.txt"):
        env["BUILD_SYSTEM"] = "cmake"
        env["CMAKE_FILE"] = build_file

    if app_name.strip():
        env["APP_NAME"] = app_name.strip()
    if out_bin.strip():
        env["OUT_BIN"] = out_bin.strip().replace("\\", "/")

    # bundle.sh 读 PLUGINS / EXTRA_COPY
    script = (
        f"sed -i 's/\\r$//' '{tk_w}/tools/cross_build.sh' '{tk_w}/tools/bundle.sh' && "
        f"bash '{tk_w}/tools/cross_build.sh'"
    )
    return wsl.run_wsl(script, distro=distro, env=env, on_line=on_line)


def run_install(script_rel: str, distro: str = wsl.DEFAULT_DISTRO, on_line=None) -> int:
    tk_w = wsl.win_to_wsl(detect.toolkit_root())
    path = f"{tk_w}/tools/{script_rel}"
    cmd = f"sed -i 's/\\r$//' '{path}' && bash '{path}'"
    return wsl.run_wsl(cmd, distro=distro, user="root", on_line=on_line)
