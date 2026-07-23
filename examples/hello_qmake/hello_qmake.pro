QT += widgets
CONFIG += c++14 release
TARGET = hello_qmake
TEMPLATE = app

DESTDIR = bin/release
OBJECTS_DIR = tmp/obj
MOC_DIR = tmp/moc

SOURCES += main.cpp
