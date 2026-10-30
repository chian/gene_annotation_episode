# Host integration commands and original receipts

All commands ran from `/home/chia/repos/gene_annotation_episode` with the local
`.venv/bin/python`. Service responses and original selections are controlled;
the publication, records, custody, provider and return objects are production.
No live BV-BRC request, native program, HPC job or model call was made.

1. Initial test run, exit 1; `pytest_001.txt` and `pytest_001.xml` preserve the
   original failure. Full Store and executor receipts are in `failed_run_001/`.
   `FAILURE_001_PUBLICATIONS.json` contains the two original publication views.

   ```sh
   bash -o pipefail -c '.venv/bin/python -m pytest tests/test_bvbrc_genome_alignment_host.py -q -x --junitxml=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_001.xml 2>&1 | tee verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_001.txt'
   ```

   The real native number was `690 / 693 = 0.9956709956709957`, but status was
   partial. Actual task-info receipts use purpose `observation`; C required
   `support`. Actual typed manifest acquisition uses `Workspace.get` and an
   exact `receipt_row`; C required direct `task_info_object` while that real
   selection carries unknown type/path. Root recorded correction015 for both.

2. Explicit unreceived-log selection rejection, exit 0; one passed and ten
   deselected in 13.55 seconds. This test requires the actual custody validator
   to reject the selected content and verifies no transport occurred.

   ```sh
   bash -o pipefail -c '.venv/bin/python -m pytest tests/test_bvbrc_genome_alignment_host.py -q -k explicitly_selecting_unreceived --junitxml=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_002.xml 2>&1 | tee verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_002.txt'
   ```

3. After correction015, full test invocation, exit 1: four native-format cases
   passed, then the candidate test's assertion used insertion order instead of
   the stored requested form's canonical field order. The actual publication and parent admission had
   already succeeded with distinct `0` and `null`. All Store bytes and original
   forms remain in `runs_003/`; the assertion was corrected to match exact field
   identities. Result: 1 failed, 4 passed in 524.06 seconds.

   ```sh
   bash -o pipefail -c '.venv/bin/python -m pytest tests/test_bvbrc_genome_alignment_host.py -q -x --basetemp=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/runs_003 --junitxml=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_003.xml 2>&1 | tee verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_003.txt'
   ```

4. Remaining eight cases after the field-identity assertion correction, including
   the later wrong-task case and identity-content extension. The four unchanged
   passing native-format cases from run003 are excluded. Root reports that only
   tool information and presentation changed since run003 began; these paths
   are outside the E closure and separately verified by root. All original
   run003 publication pins match the current 43-file E closure exactly, recorded
   in `SOURCE_COMPARISON_004.json`.

   Exit 1: 4 passed, 1 failed, 4 deselected in 283.89 seconds. Candidate metadata,
   unreceived stdout, explicit unreceived-content rejection, and wrong native
   task/receipt cases passed. The current-acquisition negative asserted the
   collector's later error name, while the actual ArtifactBundle validator
   rejected its malformed task earlier with `original_task_mismatch`. Per-case
   exact error names were corrected after inspecting the real validators.
   No production validation was changed. `runs_004/` preserves original state.

   ```sh
   bash -o pipefail -c '.venv/bin/python -m pytest tests/test_bvbrc_genome_alignment_host.py -q -x -k "not registered_provider_native_publication" --basetemp=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/runs_004 --junitxml=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_004.xml 2>&1 | tee verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_004.txt'
   ```

5. Original run003 receipt inspection, exit 0. The script uses read-only SQLite
   connections, verifies saved artifact byte counts/hashes, and copies frozen
   records into an index. It imports no scientific parser/calculator. The five
   `runtime_model_calls` rows per case are scripted child-decision records
   written by the existing `SavedRecords.child` helper; no model service ran.

   ```sh
   bash -o pipefail -c '.venv/bin/python verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/inspect_saved_runs.py verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/runs_003 > verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/SAVED_TRACE_003.json 2> verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/saved_trace_003.stderr'
   ```

The failed run's bindings retain their original source pins. Later invocations
compute current source pins prospectively at real service configuration.

6. Remaining four cases after exact error-name correction, exit 0: 4 passed,
   8 deselected in 290.46 seconds.

   ```sh
   bash -o pipefail -c '.venv/bin/python -m pytest tests/test_bvbrc_genome_alignment_host.py -q -x -k "actual_current or saved_host_return or explicit_saved_recalculation or latest_partial" --basetemp=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/runs_005 --junitxml=verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_005.xml 2>&1 | tee verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/pytest_005.txt'
   ```

7. Read-only run004 trace inspection, exit 0:

   ```sh
   bash -o pipefail -c '.venv/bin/python verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/inspect_saved_runs.py verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/runs_004 > verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/SAVED_TRACE_004.json 2> verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/saved_trace_004.stderr'
   ```

8. Current suite collection, exit 0, 12 cases:

   ```sh
   bash -o pipefail -c '.venv/bin/python -m pytest tests/test_bvbrc_genome_alignment_host.py --collect-only -q 2>&1 | tee verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/collect_004.txt'
   ```

9. Read-only run005 trace inspection, exit 0:

   ```sh
   bash -o pipefail -c '.venv/bin/python verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/inspect_saved_runs.py verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/runs_005 > verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/SAVED_TRACE_005.json 2> verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/saved_trace_005.stderr'
   ```

10. Final receipt/source index, exit 0. All 12 current cases have a passing latest
    receipt; 16 original attempts and 14 traced Stores remain recorded. Every
    run003–005 E pin equals the current 43-file source closure. Only the owned
    test changed after `SOURCE_COMPARISON_004.json`.

    ```sh
    bash -o pipefail -c '.venv/bin/python verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/finalize_verification.py 2>&1 | tee verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/finalize_001.txt'
    ```
