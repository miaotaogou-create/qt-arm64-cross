# aarch64 + Ubuntu focal sysroot + Qt 5.14.2（与 qmake mkspec 共用同一套前缀）
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(ROOTFS "/opt/arm64-rootfs" CACHE PATH "focal arm64 sysroot")
set(QT_PREFIX "/opt/Qt5.14.2-arm64" CACHE PATH "Qt 目标库前缀")
set(QT_HOST "/opt/Qt5.14.2-host" CACHE PATH "Qt 主机工具前缀")

set(CMAKE_SYSROOT "${ROOTFS}")
set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)

set(CMAKE_FIND_ROOT_PATH "${ROOTFS}" "${QT_PREFIX}")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# 链接时能找到 sysroot / Qt 的依赖
set(CMAKE_EXE_LINKER_FLAGS_INIT
  "--sysroot=${ROOTFS} -Wl,-rpath-link,${ROOTFS}/lib/aarch64-linux-gnu -Wl,-rpath-link,${ROOTFS}/usr/lib/aarch64-linux-gnu -Wl,-rpath-link,${QT_PREFIX}/lib")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "${CMAKE_EXE_LINKER_FLAGS_INIT}")
set(CMAKE_C_FLAGS_INIT "--sysroot=${ROOTFS}")
set(CMAKE_CXX_FLAGS_INIT "--sysroot=${ROOTFS}")

set(ENV{PKG_CONFIG_SYSROOT_DIR} "${ROOTFS}")
set(ENV{PKG_CONFIG_LIBDIR} "${ROOTFS}/usr/lib/aarch64-linux-gnu/pkgconfig:${ROOTFS}/usr/share/pkgconfig")

set(QT_QMAKE_EXECUTABLE "${QT_HOST}/bin/qmake" CACHE FILEPATH "" FORCE)
set(Qt5_DIR "${QT_PREFIX}/lib/cmake/Qt5" CACHE PATH "" FORCE)
