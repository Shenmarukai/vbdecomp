cmake_minimum_required (VERSION 3.28)

project("f3")
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED YES)
set(CMAKE_CXX_EXTENSIONS OFF)

add_subdirectory("src")
add_subdirectory("external")