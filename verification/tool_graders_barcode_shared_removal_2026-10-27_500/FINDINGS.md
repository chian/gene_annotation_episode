# Shared barcode-wrapper removal, 2026-10-27, task 500

This is an implementation evidence record. The original user attachment remains authoritative; the explicit later instruction removes analyze_barcode_sequencing_data. No scoring sheet or calculator was changed.

## Applied scope

Only the six assigned production files were edited. Barcode resource configuration, launch/request/result schemas, input authority/versioning, execution dispatch, native preparation/status/output reading, result fact registration/admission/resolution, credit forwarding and completion forwarding were removed. The NMF, ATAC and other operation branches remain. No compatibility shim or replacement operation was added.

All applicable complete affected functions were read before editing. The signature/reference scan found no other production consumer outside the six owned files and the dedicated barcode modules assigned to root for removal. The remaining active references after the shared removal were exactly 20 dedicated production modules and 14 dedicated tests.

## Verification actually performed

- Host Python standard-library AST parsing passed for all six edited source files; no application module was imported.
- Case-insensitive barcode scanning found zero references in all six edited files.
- Applied source differences exactly match the reviewed per-file removal diffs.
- The literature_channel_cells schema branch has an identical before/after AST.
- Before/after hashes, changed-function positions and original reference scans are retained in this directory.
- This checkout has no Git metadata. before_worktree_diff_status.txt records the unsuccessful git diff query; removal.diff compares captured pre-edit source bytes with the applied edits.
- No tests, native jobs, model calls, barcode executions or runtime verification were performed. No running NMF handle was inspected, restarted or cancelled.

## Handoff and remaining checks

Root owns deletion of the dedicated barcode modules/tests, additive scope/accounting updates and combined bounded verification. Suggested remaining checks are the planned tests/test_communication.py, tests/test_practical_execution_state.py and tests/test_expression_nmf_execution_integration.py, with tests/test_execution_progress.py and tests/test_atac_input_identity_replay.py covering affected neighboring progress and input-version consumers. These suggestions are not executed test evidence.

Old barcode-specific configuration, requested-job and result contracts are no longer supplied by these shared files. Historical receipts and frozen source snapshots remain evidence; current-code reconstruction of removed barcode workflows is not claimed. The original NMF verification must retain its frozen inputs and handle.

## Exact changed functions

### gene_annotation_episode/execution_episodes.py

- `ExecutionEpisodes.__init__` — current line 92.
- `ExecutionEpisodes._request_schema` — current line 284.
- `ExecutionEpisodes.assignment_schema` — current line 368.
- `ExecutionEpisodes._barcode_reference_access` — removed; original line 544.
- `ExecutionEpisodes._barcode_selector` — removed; original line 562.
- `ExecutionEpisodes._retained_barcode_target` — removed; original line 565.
- `ExecutionEpisodes._versions` — current line 627.
- `ExecutionEpisodes._barcode_inputs` — removed; original line 682.
- `ExecutionEpisodes.prepare_assignment` — current line 670.
- `ExecutionEpisodes.initialize` — current line 758.
- `ExecutionEpisodes._check_parent_inputs` — current line 788.
- `ExecutionEpisodes.resource_tool_contracts` — current line 867.
- `ExecutionEpisodes.decision_context` — current line 1123.
- `ExecutionEpisodes._target` — current line 1174.
- `ExecutionEpisodes._selector` — current line 1252.
- `ExecutionEpisodes.catalog` — current line 1373.
- `ExecutionEpisodes.execute` — current line 1445.
- `ExecutionEpisodes.received_report_sources` — current line 1751.
- `ExecutionEpisodes.received_report_facts` — current line 1807.
- `ExecutionEpisodes.resolve_received_reference` — current line 1872.
- `ExecutionEpisodes.validate_received_report` — current line 1991.
- `ExecutionEpisodes.fact_sources` — current line 2033.
- `ExecutionEpisodes.facts` — current line 2162.
- `ExecutionEpisodes.received_form_references` — current line 2261.
- `ExecutionEpisodes.initial_references` — current line 2348.
- `ExecutionEpisodes.resolve` — current line 2429.
- `ExecutionEpisodes.validate_report` — current line 2647.
- `ExecutionEpisodes.project_credit` — current line 2664.
- `ExecutionEpisodes._native_results_complete` — current line 2724.
- `ExecutionEpisodes._proof_for_action` — current line 2769.
- `ExecutionEpisodes.completion_for_action` — current line 2851.
- `ExecutionEpisodes.verify_completion` — current line 2900.

155 removed lines; 10 added lines in the reviewed diff.

### gene_annotation_episode/communication.py

- `_compile_closed_schema` — current line 118.
- `_validate_form` — current line 414.
- `_validate_form_semantics` — current line 493.

22 removed lines; 3 added lines in the reviewed diff.

### gene_annotation_episode/execution_progress.py

- `describe_execution_target` — current line 71.
- `ExecutionTargetReader._native` — current line 228.
- `ExecutionTargetReader.describe_target` — current line 375.
- `ExecutionTargetReader.returnable_handoff` — current line 907.

22 removed lines; 1 added lines in the reviewed diff.

### gene_annotation_episode/practical_execution_operations.py

- `LocalPracticalOperations.__init__` — current line 87.
- `LocalPracticalOperations.validate_assignment` — current line 136.
- `LocalPracticalOperations._handle` — current line 301.
- `LocalPracticalOperations._barcode_plan` — removed; original line 467.
- `LocalPracticalOperations._job_fact` — current line 449.
- `LocalPracticalOperations.observe_execution` — current line 545.
- `LocalPracticalOperations.read_output` — current line 775.
- `LocalPracticalOperations._execute` — current line 861.

106 removed lines; 16 added lines in the reviewed diff.

### gene_annotation_episode/practical_execution_records.py

- `validate_assignment` — current line 230.

11 removed lines; 2 added lines in the reviewed diff.

### gene_annotation_episode/execution_input_versions.py

- `validate_execution_input_versions` — current line 15.

19 removed lines; 2 added lines in the reviewed diff.

