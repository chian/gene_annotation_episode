cmake_minimum_required(VERSION 3.18)

project(tld LANGUAGES C VERSION "0.1")

set (CMAKE_C_STANDARD 11)

# SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pg")
# SET(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -pg")
# SET(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -pg")


add_compile_options("$<$<CONFIG:RELEASE>:-W;-Wall;-pedantic>")
add_compile_options("$<$<CONFIG:DEBUG>:-W;-Wall;-O0;-pedantic;-DDEBUG>")


if(CMAKE_PROJECT_NAME STREQUAL PROJECT_NAME)
  if (MSVC)
    # warning level 4 and all warnings as errors
    add_compile_options(/W4 /WX)
  else()
    # lots of warnings and all warnings as errors
    add_compile_options(-Wall -Wextra -pedantic) # -Werror )
  endif()
endif()

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

#include(GNUInstallDirs)

find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
    set(CMAKE_C_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")    
endif()

#option(BUILD_SHARED_LIBS "Build all libraries as shared" OFF)


list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

# find_package(HTSlib)
# find_package(ZLIB)
# find_package(HDF5 COMPONENTS C HL)


add_subdirectory(src)
# add_library(tld-dev)
# target_sources(tld-dev PRIVATE "src/tld.c")
#set_property(TARGET tld-dev PROPERTY C_STANDARD 11)
#target_compile_features(tld PUBLIC c_std_99)
# target_include_directories(tld-dev PUBLIC "src") # "src/core")
# target_link_libraries(tld-dev PRIVATE m)
# target_link_libraries(tld-dev PRIVATE ZLIB::ZLIB)
#target_compile_definitions(rayfork-dev PUBLIC RAYFORK_GRAPHICS_BACKEND_DIRECTX)


#dunno what this does 
# set(tld_path "${CMAKE_CURRENT_SOURCE_DIR}/tld-dev")
# set(tld tld-dev)
#add_subdirectory(dev)

include(CTest)
add_subdirectory(tests)

  
# Package Generator  #######################################################
set(CPACK_PACKAGE_VENDOR "Vendor name")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Some summary")
set(CPACK_PACKAGE_CONTACT "Timo Lassmann")
set(CPACK_PACKAGE_VERSION_MAJOR ${PROJECT_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${PROJECT_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${PROJECT_VERSION_PATCH})
set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/COPYING")
set(CPACK_RESOURCE_FILE_README "${CMAKE_CURRENT_SOURCE_DIR}/Readme.org")
set(CPACK_SOURCE_GENERATOR "TGZ;ZIP")
set(CPACK_SOURCE_IGNORE_FILES
     /.git
     /dist
     /GPATH
     /GTAGS
     /GRTAGS
     /.*build.*
     /.dir-locals.el
     /\\\\.DS_Store
 )
 include (CPack)


