# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

if("/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat_2_2_3/thirdparty/htslib-1.16.tar.bz2" STREQUAL "")
  message(FATAL_ERROR "LOCAL can't be empty")
endif()

if(NOT EXISTS "/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat_2_2_3/thirdparty/htslib-1.16.tar.bz2")
  message(FATAL_ERROR "File not found: /home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat_2_2_3/thirdparty/htslib-1.16.tar.bz2")
endif()

if("MD5" STREQUAL "")
  message(WARNING "File cannot be verified since no URL_HASH specified")
  return()
endif()

if("d31777ef90d1369a52049ba0ac3c0375" STREQUAL "")
  message(FATAL_ERROR "EXPECT_VALUE can't be empty")
endif()

message(VERBOSE "verifying file...
     file='/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat_2_2_3/thirdparty/htslib-1.16.tar.bz2'")

file("MD5" "/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat_2_2_3/thirdparty/htslib-1.16.tar.bz2" actual_value)

if(NOT "${actual_value}" STREQUAL "d31777ef90d1369a52049ba0ac3c0375")
  message(FATAL_ERROR "error: MD5 hash of
  /home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat_2_2_3/thirdparty/htslib-1.16.tar.bz2
does not match expected value
  expected: 'd31777ef90d1369a52049ba0ac3c0375'
    actual: '${actual_value}'
")
endif()

message(VERBOSE "verifying file... done")
