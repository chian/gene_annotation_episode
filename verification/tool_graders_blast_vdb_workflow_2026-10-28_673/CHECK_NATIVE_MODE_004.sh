#!/usr/bin/env bash
set -euo pipefail
# Each invocation explicitly selects one still-unverified inspection mode.
# Observe an existing attempt using status/collect; never invoke it twice.
vdb_mode="${1:?explicit info, paths or paths_all mode required}"
case "$vdb_mode" in
  info|paths|paths_all) ;;
  *) exit 2 ;;
esac
python3 verification/tool_graders_hmmer_map_verification_2026-10-28_529/run_checks.py launch "check131_vdb_workflow673_${vdb_mode}" \
  --dependencies-from verification/tool_graders_hmmer_map_verification_2026-10-28_529/check005/dependencies \
  --test test_blast_vdb_workflow_673.py::test_selected_native_workflow \
  --test-env "HMMER_NATIVE_ORACLE_VDB_MODE=${vdb_mode}" \
  --support-file verification/tool_graders_blast_vdb_native_observation_2026-10-28_661/SELECTED_REQUEST.json \
  --support-tree verification/tool_graders_blast_vdb_fixture_acquisition_2026-10-28_658/retained \
  --existing-native-executable /home/chia/repos/gene_annotation_episode/resources/software/ncbi-blast-2.17.0+/bin/blast_vdb_cmd \
  --native-library /usr/bin/bwrap \
  --native-library /usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 \
  --native-library /usr/lib/x86_64-linux-gnu/libbz2.so.1.0.4 \
  --native-library /usr/lib/x86_64-linux-gnu/libc.so.6 \
  --native-library /usr/lib/x86_64-linux-gnu/libcap.so.2.66 \
  --native-library /usr/lib/x86_64-linux-gnu/libdl.so.2 \
  --native-library /usr/lib/x86_64-linux-gnu/libgcc_s.so.1 \
  --native-library /usr/lib/x86_64-linux-gnu/libgomp.so.1.0.0 \
  --native-library /usr/lib/x86_64-linux-gnu/libm.so.6 \
  --native-library /usr/lib/x86_64-linux-gnu/libpcre2-8.so.0.11.2 \
  --native-library /usr/lib/x86_64-linux-gnu/libpthread.so.0 \
  --native-library /usr/lib/x86_64-linux-gnu/libresolv.so.2 \
  --native-library /usr/lib/x86_64-linux-gnu/libselinux.so.1 \
  --native-library /usr/lib/x86_64-linux-gnu/libz.so.1.3 \
  --native-library /etc/ld.so.cache
