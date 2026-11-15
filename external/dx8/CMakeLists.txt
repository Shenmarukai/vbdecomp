if(NOT CMAKE_SIZEOF_VOID_P EQUAL 4)
    message(FATAL_ERROR "Legacy DirectX 8.1 libraries require an x86 build")
endif()

# DirectX 8.1

add_library(dx81 STATIC IMPORTED GLOBAL)

set_target_properties(dx81 PROPERTIES
    IMPORTED_LOCATION
        "${CMAKE_CURRENT_SOURCE_DIR}/dx81/lib/d3dx8.lib"
    INTERFACE_INCLUDE_DIRECTORIES
        "${CMAKE_CURRENT_SOURCE_DIR}/dx81/include"
)

set_property(TARGET dx81 APPEND PROPERTY
    INTERFACE_LINK_LIBRARIES
        "${CMAKE_CURRENT_SOURCE_DIR}/dx81/lib/d3d8.lib"
)

# DirectX 8.1 Audio

add_library(dx81-audio INTERFACE)

target_include_directories(dx81-audio INTERFACE
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/include"
)

target_link_libraries(dx81-audio INTERFACE
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/lib/dsound.lib"
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/lib/dxguid.lib"
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/lib/strmiids.lib"
)

# DirectX 8.1 Errors

add_library(dx81-errors STATIC IMPORTED GLOBAL)

set_target_properties(dx81-errors PROPERTIES
    IMPORTED_LOCATION
        "${CMAKE_CURRENT_SOURCE_DIR}/dx81-errors/lib/DxErr8.lib"
    INTERFACE_INCLUDE_DIRECTORIES
        "${CMAKE_CURRENT_SOURCE_DIR}/dx81-errors/include"
)

# DirectX 8.1 Font

add_library(dx81-font STATIC
    "dx81-font/src/d3dfont.cpp"
)
target_include_directories(dx81-font PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/dx81-font/include")
target_link_libraries(dx81-font PUBLIC dx81)

