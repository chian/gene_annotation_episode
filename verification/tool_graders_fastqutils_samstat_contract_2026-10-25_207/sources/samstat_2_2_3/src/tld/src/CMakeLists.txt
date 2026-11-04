find_package(HDF5 REQUIRED COMPONENTS C HL)
find_package(ZLIB)

find_package(Threads REQUIRED)
if(Threads_FOUND)
  message(STATUS "Threads are enabled.")
  add_definitions (-DHAVE_PTHREAD)
endif(Threads_FOUND)



set(HDF5_USE_STATIC_LIBRARIES ON)

if(EXISTS ${CMAKE_CURRENT_BINARY_DIR}/tld-seq-tables.h)
  #add some compilation flags
  
  add_library(tld-dev STATIC
    tld.c
    ${CMAKE_CURRENT_BINARY_DIR}/tld-seq-tables.h
    )

  

  target_include_directories(tld-dev
    INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
    PRIVATE ${CMAKE_CURRENT_BINARY_DIR}
    )

  target_link_libraries(tld-dev PRIVATE m ZLIB::ZLIB Threads::Threads ${HDF5_C_LIBRARIES})
  # list(APPEND INCLUDE_LIST ${HDF5_C_INCLUDE_DIRS})
  target_include_directories(tld-dev PUBLIC ${HDF5_C_INCLUDE_DIRS})
else()
  add_library(boot STATIC
    tld.c
    )
  target_compile_options(boot PRIVATE -DBOOT)
  target_link_libraries(boot  PRIVATE m ZLIB::ZLIB Threads::Threads)
  
  add_executable(gentable
    gentables.c
    )
  target_compile_options(gentable PRIVATE -DBOOT)
  target_link_libraries(gentable PRIVATE boot)

  add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/tld-seq-tables.h
    COMMAND gentable ${CMAKE_CURRENT_BINARY_DIR}/tld-seq-tables.h
    DEPENDS gentable
    )

  # add_custom_target(mktable
  #   # OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/seq/tld-seq-tables.h
  #   COMMAND gentable ${CMAKE_CURRENT_BINARY_DIR}/tld-seq-tables.h
  #   DEPENDS gentable
  #   )

  #find_package(HDF5 REQUIRED COMPONENTS C HL)
  #find_package(ZLIB)

  #set(HDF5_USE_STATIC_LIBRARIES ON)

  add_library(tld-dev STATIC
    tld.c
    ${CMAKE_CURRENT_BINARY_DIR}/tld-seq-tables.h
    )
  # add_dependencies(tld-dev mktable)

  target_include_directories(tld-dev
    INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
    PRIVATE ${CMAKE_CURRENT_BINARY_DIR}
    )

  target_link_libraries(tld-dev PRIVATE m ZLIB::ZLIB Threads::Threads ${HDF5_C_LIBRARIES})
  # list(APPEND INCLUDE_LIST ${HDF5_C_INCLUDE_DIRS})
  target_include_directories(tld-dev PUBLIC ${HDF5_C_INCLUDE_DIRS})
  
endif(EXISTS ${CMAKE_CURRENT_BINARY_DIR}/tld-seq-tables.h)






# target_compile_definitions(tld-dev INTERFACE ${HDF5_DEFINITIONS})


# if(HDF5_FOUND)
#   message(STATUS "HDF5 was  found")
#   set_target_properties(tld-dev PROPERTIES COMPILE_FLAGS "-DHAVE_HDF5")

# endif()




# include_directories(${CMAKE_CURRENT_BINARY_DIR})
