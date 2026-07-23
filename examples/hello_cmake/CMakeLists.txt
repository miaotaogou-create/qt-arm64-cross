cmake_minimum_required(VERSION 3.10)
project(hello_cmake LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_executable(hello_cmake main.cpp)
target_link_libraries(hello_cmake PRIVATE Qt5::Widgets)

set_target_properties(hello_cmake PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
