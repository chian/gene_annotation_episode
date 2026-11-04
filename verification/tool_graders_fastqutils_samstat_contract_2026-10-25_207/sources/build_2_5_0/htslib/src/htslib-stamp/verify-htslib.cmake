# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

if("/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat/thirdparty/htslib-1.24.tar.bz2" STREQUAL "")
  message(FATAL_ERROR "LOCAL can't be empty")
endif()

if(NOT EXISTS "/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat/thirdparty/htslib-1.24.tar.bz2")
  message(FATAL_ERROR "File not found: /home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat/thirdparty/htslib-1.24.tar.bz2")
endif()

if("SHA256" STREQUAL "")
  message(WARNING "File cannot be verified since no URL_HASH specified")
  return()
endif()

if("28a8de191381c7a97a35675ceac76fa1ea95e7b678d6a2e9d600a7874e4077de" STREQUAL "")
  message(FATAL_ERROR "EXPECT_VALUE can't be empty")
endif()

message(VERBOSE "verifying file...
     file='/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat/thirdparty/htslib-1.24.tar.bz2'")

file("SHA256" "/home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat/thirdparty/htslib-1.24.tar.bz2" actual_value)

if(NOT "${actual_value}" STREQUAL "28a8de191381c7a97a35675ceac76fa1ea95e7b678d6a2e9d600a7874e4077de")
  message(FATAL_ERROR "error: SHA256 hash of
  /home/chia/repos/gene_annotation_episode/verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207/sources/samstat/thirdparty/htslib-1.24.tar.bz2
does not match expected value
  expected: '28a8de191381c7a97a35675ceac76fa1ea95e7b678d6a2e9d600a7874e4077de'
    actual: '${actual_value}'
")
endif()

message(VERBOSE "verifying file... done")
