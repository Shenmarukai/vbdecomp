if(NOT CMAKE_SIZEOF_VOID_P EQUAL 4)
    message(FATAL_ERROR "Legacy DirectX 8.1 audio libraries require an x86 build")
endif()

# DirectX 8 audio only. The renderer uses Direct3D 9 through vcpkg.
add_library(dx81-audio INTERFACE)
target_include_directories(dx81-audio INTERFACE
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/include"
)
target_link_libraries(dx81-audio INTERFACE
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/lib/dsound.lib"
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/lib/dxguid.lib"
    "${CMAKE_CURRENT_SOURCE_DIR}/dx81-audio/lib/strmiids.lib"
)
