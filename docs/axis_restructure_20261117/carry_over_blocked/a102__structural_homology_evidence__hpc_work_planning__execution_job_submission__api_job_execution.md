# Blocked and unplaced: A102 execution_job_submission/api_job_execution

Old source was read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`). The folder was carried from the shape of the sibling `hpc_allocation_execution/.../api_job_execution` (same old source, private copy, nothing imported). Old tests: none existed; `retired_tests/<episode>.tsv` has only its header.

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
- all of `terminal_execution.py` (35 rows): local/hpc shell-execution copy never delegated to by launch_api; carried by hpc_job_execution and local_job_execution.
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
