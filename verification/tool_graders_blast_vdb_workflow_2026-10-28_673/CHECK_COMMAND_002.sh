#!/usr/bin/env bash
set -euo pipefail
# Retained closed-run verification only, after the676 source/check handoff.
# This launch is staged, not evidence that the check has run or passed.
# Once launched, observe its original handle instead of launching it again.
python3 verification/tool_graders_hmmer_map_verification_2026-10-28_529/run_checks.py launch check131_vdb_workflow673_reopen \
  --working-root verification/tool_graders_hmmer_map_verification_2026-10-28_529 \
  --dependencies-from verification/tool_graders_hmmer_map_verification_2026-10-28_529/check005/dependencies \
  --test test_blast_vdb_workflow_673.py::test_reopen_selected_native_workflow \
  --support-tree verification/tool_graders_blast_vdb_fixture_acquisition_2026-10-28_658/retained \
  --test-env HMMER_NATIVE_ORACLE_VDB_REOPEN=/home/chia/repos/gene_annotation_episode/verification/tool_graders_hmmer_map_verification_2026-10-28_529/check131_vdb_workflow673/temporary/pytest/vdb-workflow673-extract_sequences0
