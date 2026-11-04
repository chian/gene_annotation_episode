cmake_minimum_required(VERSION 3.1)

project(tld-tests LANGUAGES C)

# add_executable(unit-generic utests/generic.c) 
# target_link_libraries(unit-generic PRIVATE tld-dev)
find_package(Threads REQUIRED)
if(Threads_FOUND)
add_executable(unit-tpool
 utests/unit_tpool.c
  )
target_link_libraries(unit-tpool PRIVATE tld-dev Threads::Threads)
add_test(
    NAME unit-tpool
    COMMAND unit-tpool
)

endif(Threads_FOUND)


add_executable(unit-shuffle utests/unit_shuffle.c)
target_link_libraries(unit-shuffle PRIVATE tld-dev)
add_test(
    NAME unit-shuffle
    COMMAND unit-shuffle
)


add_executable(unit-misc utests/unit_misc.c)
target_link_libraries(unit-misc PRIVATE tld-dev)
add_test(
    NAME unit-misc
    COMMAND unit-misc
)


add_executable(unit-timing utests/unit_timing.c)
target_link_libraries(unit-timing PRIVATE tld-dev)
add_test(
    NAME unit-timing
    COMMAND unit-timing
)

add_executable(unit-sort utests/unit_sort.c)
target_link_libraries(unit-sort PRIVATE tld-dev)
add_test(
    NAME unit-sort 
    COMMAND unit-sort
)

add_executable(unit-sigmoid utests/unit_sigmoid.c)
target_link_libraries(unit-sigmoid PRIVATE tld-dev)
add_test(
    NAME unit-sigmoid 
    COMMAND unit-sigmoid
)



add_executable(kde_itest itests/kde_itest.c) 
target_link_libraries(kde_itest PRIVATE tld-dev)
add_test(
    NAME kde_itest
    COMMAND kde_itest
)

add_executable(unit-str utests/unit_str.c) 
target_link_libraries(unit-str PRIVATE tld-dev)
add_test(
    NAME unit-str
    COMMAND unit-str
)

add_executable(unit-seq-rev utests/unit_seq_rev.c) 
target_link_libraries(unit-seq-rev PRIVATE tld-dev)
add_test(
    NAME unit-seq-rev
    COMMAND unit-seq-rev
)


add_executable(int-noise itests/noise.c) 
target_link_libraries(int-noise PRIVATE tld-dev)
add_test(
    NAME int-noise
    COMMAND int-noise
)

add_executable(seq_shannon itests/seq_shannon.c) 
target_link_libraries(seq_shannon PRIVATE tld-dev)
add_test(
    NAME seq_shannon
    COMMAND seq_shannon ${CMAKE_CURRENT_SOURCE_DIR}/test_data/BB11001.fa
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)




add_executable(unit-stats utests/unit_stats.c) 
target_link_libraries(unit-stats PRIVATE tld-dev)
add_test(
    NAME unit-stats
    COMMAND unit-stats
)


add_executable(unit-hdf5 utests/unit_hdf5.c) 
target_link_libraries(unit-hdf5 PRIVATE tld-dev)
add_test(
    NAME unit-hdf5
    COMMAND unit-hdf5
)

# Setup unit-tests
add_executable(unit-test-suite utests/unit_tests.c) 
target_link_libraries(unit-test-suite PRIVATE tld-dev)
#set_property(TARGET unit-test-suite PROPERTY C_STANDARD 11)

# set_target_properties(unit-test-suite PROPERTIES
#         C_STANDARD 11
#         C_STANDARD_REQUIRED YES
#         C_EXTENSIONS NO
# )

add_test(
    NAME unit-test
    COMMAND unit-test-suite
)

add_executable(unit-rng utests/unit_rng.c) 
target_link_libraries(unit-rng PRIVATE tld-dev)
# set_property(TARGET unit-rng PROPERTY C_STANDARD 11)
# set_target_properties(unit-rng PROPERTIES
#         C_STANDARD 11
#         C_STANDARD_REQUIRED YES
#         C_EXTENSIONS NO
# )

add_test(
    NAME unit-rng
    COMMAND unit-rng
)

add_executable(unit-alpha utests/unit_alphabet.c) 
target_link_libraries(unit-alpha PRIVATE tld-dev)
add_test(
  NAME unit-alpha
  COMMAND unit-alpha  
  )


add_executable(unit-logsum utests/unit_logsum.c) 
target_link_libraries(unit-logsum PRIVATE tld-dev)
add_test(
  NAME unit-logsum
  COMMAND unit-logsum  
  )

add_executable(unit-seq utests/unit_seq.c) 
target_link_libraries(unit-seq PRIVATE tld-dev)

add_test(
  NAME unit-seq-nano
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/nano.fastq
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )


add_test(
  NAME unit-seq-BB11001
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/BB11001.fa
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )

add_test(
  NAME unit-seq-broken1
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/broken_fasta1.fa
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
set_property(TEST unit-seq-broken1
  PROPERTY WILL_FAIL true
  )

add_test(
  NAME unit-seq-broken2
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/broken_fasta2.fa
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
set_property(TEST unit-seq-broken2
  PROPERTY WILL_FAIL true
  )




add_test(
  NAME unit-seq-fastq-gz-1
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/ENCSR142YZV_chr19only_10000_reads_R1.fastq.gz
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )

add_test(
  NAME unit-seq-fastq-gz-2
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/ENCSR142YZV_chr19only_10000_reads_R2.fastq.gz
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )

add_test(
  NAME unit-seq-fastq-gz-3
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/ENCSR653DFZ_rep2_chr19_10000reads_R1.fastq.gz
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )

add_test(
  NAME unit-seq-fastq-gz-4
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/ENCSR653DFZ_rep1_chr19_10000reads_R2.fastq.gz
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )

add_test(
  NAME unit-seq-fastq-gz-5
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/ENCSR653DFZ_rep1_chr19_10000reads_R1.fastq.gz
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )

add_test(
  NAME unit-seq-fastq-gz-6
  COMMAND unit-seq ${CMAKE_CURRENT_SOURCE_DIR}/test_data/ENCSR653DFZ_rep2_chr19_10000reads_R2.fastq.gz
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
