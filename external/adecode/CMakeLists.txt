add_library(adecode STATIC IMPORTED GLOBAL)

set_target_properties(adecode PROPERTIES
    IMPORTED_LOCATION
        "${CMAKE_CURRENT_SOURCE_DIR}/lib/Adecode.lib"
)

target_link_options(adecode INTERFACE
    "/NODEFAULTLIB:LIBC"
)