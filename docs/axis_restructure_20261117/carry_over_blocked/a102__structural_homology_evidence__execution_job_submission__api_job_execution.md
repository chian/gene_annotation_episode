# Blocked and unplaced: A102 execution_job_submission/api_job_execution

Old source was read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`). The folder is a private copy of the shape of the finished carry of the sibling with the same old source (`hpc_work_planning/execution_job_submission/api_job_execution`); nothing imported. Old test `tests/test_api_job_receipts.py` used the old runner and is retired (retired_tests/<episode>.tsv).

## BLOCKED-ON-JOB-SERVICE
- BLOCKED-ON-JOB-SERVICE: job_access.read('api_catalog', ...); wanted call: `ctx.services['job_access'].read('api_catalog', summary['service'], summary['algorithm'], summary['database'])` (task.catalog_of, from decide and action): the API service executor's operation catalog (old `api_execution.catalog`, `operation_contracts`). Not provided.
- BLOCKED-ON-JOB-SERVICE: job_access.api_execute; wanted call: `job_access.api_execute(resource_id=, service=, algorithm=, database=, operation=, arguments=, request=, scope=, input_refs=, immutable_input_versions=, handoff_unit=, acquired_record_unit=, key=ctx.operation_key)` returning `{status, event, feedback, credit, facts}` (old `api_execution.execute`, `credit_view`, `facts`, `verify_completion`). `task.required_member` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.api_execute')`.
- BLOCKED-ON-JOB-SERVICE: job_access.wait_for_job; wanted call: `await job_access.wait_for_job(resource_id=, service=, condition=, handoff_refs=, key=)` (old `wait` action and `waiting.py`). Raises the same way.
- BLOCKED-ON-JOB-SERVICE: job record kind (handoff row of a declared job ledger work table); wanted call: `store.table(JOB_LEDGER).put({'job', 'event': 'handoff', 'at', 'detail', 'source_ref'})`. `task.write_handoff_record` raises.

## BLOCKED-ON-STORE-ACCESS
- `records/service_calls/structural_homology_evidence/api_job_receipts.py::ApiJobReceipts`: pattern "library not carried" (constructor takes the old `bound`). Wanted: `ApiJobReceipts(...).publish(position, outcome)` in `write_handoff_record`. Not imported.
- `acquisition/service_calls/structural_homology_evidence/api_services.py::publish_existing_acquisition`: pattern "library not carried" (`tools.store.db.execute('SELECT * FROM tool_operations ...')`). Not called.

## Unplaced old functions
- `execution_contracts.py::native_result_operation_catalog`, `execution_state.py::_practical_context`, `execution_state.py::_result_directory`, `resource_information.py::resource_tool_contracts`, `retained_result_publication.py::_validate_result_body`, `_read_result`: results/practical roles or parent-commission text, never used by this episode's launch_api branch.
- all of `terminal_execution.py` (35 rows), `result_selection.py` (6), `retained_protein_reader.py` (4), `retained_result_acquisition.py` (2), `retained_result_publication.py` (3): episode functions (library candidates), not machinery, and not carried. Checked against the old code at 97308b94c: the old episode declares `roles = ('launch_api',)`; `TerminalExecutionBehavior` builds the local/hpc `exec_command` shell catalog (`ROLE_KINDS = launch_local/launch_hpc`), `APIResultSelection` reads `RESULTS_SCHEMA` (the results role), and the retained readers/acquisition use `store.db`, `runtime_actions` and `Store(...)` with no custody replacement. launch_api's own tools do not call them.
- `render_api_launch_prompt` (old `execution_prompt`, outside the episode trees): not found; the presentation is written in `decide`.
- Old wait paragraphs about `pending_child_` handles and `native_event_targets` are not carried (no pending children exist); a new wait paragraph was written.
- Old validate_form calls: A102 has none; none written.

## Contract misfits
- new field: api_job_execution scope; new field: api_job_execution request; new field: api_job_execution input_refs; new field: api_job_execution completion_target (old code had a completion proof, not a numeric target); the executor-schema properties of the assignment are unknown (executor outside the episode trees).
- completion credit may pass its target: the executor's credit view adds `acquired_record_unit` credit beyond one `handoff_unit`; the controller raises `ValueError('completion_credit_exceeds_target')` if the commissioned target is passed.
- `execution_result_origin` is always null in the old facts and a form has no null type: declared as text, selecting it raises.
- The old frozen closed credit ("later delivery never reprices it") has no counterpart; the system's closure credit is used.
- `ctx.settings` must hold `resources`, `initial_information`, `handoff_unit`, `acquired_record_unit`, `cost`, `parameters`; optional `launch_instructions_directory`, `tool_knowledge_directory`.
- The parent `execution_job_submission` folder (not mine) must supply `completion_target`, `scope`, `request`, `input_refs` and `initial_report` in its msg_to_child.

## Not repaired
- BLOCKED-ON-JOB-SERVICE items above (api_catalog read, api_execute, wait_for_job, job ledger record kind), BLOCKED-ON-STORE-ACCESS items (ApiJobReceipts, publish_existing_acquisition) and the contract misfits (completion credit may pass its target; execution_result_origin null; no frozen closed credit) are system limits and are not worked around.
- tests: decide, action, internal_summary and the tools cannot be run for real here: decide/action read the catalog through the missing job_access service, and a real runner test would need that service; no fake is written.
