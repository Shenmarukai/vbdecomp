set(ZLIB_PUBLIC_HDRS
    "zconf.h"
    "zlib.h"
)

set(ZLIB_PRIVATE_HDRS
    "deflate.h"
    "infblock.h"
    "infcodes.h"
    "inffast.h"
    "inffixed.h"
    "inftrees.h"
    "infutil.h"
    "trees.h"
    "zutil.h"
)
set(ZLIB_SRCS
    "adler32.c"
    "compress.c"
    "crc32.c"
    "deflate.c"
    "gzio.c"
    "infblock.c"
    "infcodes.c"
    "inffast.c"
    "inflate.c"
    "inftrees.c"
    "infutil.c"
    "trees.c"
    "uncompr.c"
    "zutil.c"
)

add_library(zlib STATIC ${ZLIB_SRCS} ${ZLIB_PUBLIC_HDRS} ${ZLIB_PRIVATE_HDRS})
target_include_directories(zlib PUBLIC ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(zlib PRIVATE ZLIB_BUILD _LARGEFILE64_SOURCE=1)