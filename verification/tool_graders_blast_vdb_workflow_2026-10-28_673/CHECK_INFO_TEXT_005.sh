#!/usr/bin/env bash
set -euo pipefail
# Retain original info stdout for the specific wrapping defect. No native work.
python3 verification/tool_graders_hmmer_map_verification_2026-10-28_529/run_checks.py launch check131_vdb_workflow673_info_text \
  --attempt-parent verification/tool_graders_hmmer_map_verification_2026-10-28_529/check131_vdb_workflow673_info \
  --working-root verification/tool_graders_hmmer_map_verification_2026-10-28_529/check131_vdb_workflow673_info \
  --dependencies-from verification/tool_graders_hmmer_map_verification_2026-10-28_529/check005/dependencies \
  --test test_blast_vdb_workflow_673.py::test_retain_closed_info_native_text \
  --test-env HMMER_NATIVE_ORACLE_VDB_MODE=info \
  --test-env HMMER_NATIVE_ORACLE_VDB_REOPEN=/home/chia/repos/gene_annotation_episode/verification/tool_graders_hmmer_map_verification_2026-10-28_529/check131_vdb_workflow673_info/temporary/pytest/vdb-workflow673-info0
