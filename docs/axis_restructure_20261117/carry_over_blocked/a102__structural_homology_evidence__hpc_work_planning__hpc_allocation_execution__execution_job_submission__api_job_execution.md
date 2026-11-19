# Blocked and unplaced: A102 api_job_execution

No old source was readable: the checkout has no git history (`git show 97308b94c:<path>` fails: "not a git repository"), so every file was written from the episode intent record, the call table and the guide. The old tests of this folder could not be listed either; `retired_tests/<episode>.tsv` has only its header.

## BLOCKED-ON-JOB-SERVICE
- `job_access.read('api_catalog', service, algorithm, database)`: the API service executor's operation catalog for the assignment (wanted in `task.catalog_of`, from `decide` and `action`). Not provided.
- `job_access.api_execute(resource_id=, service=, algorithm=, database=, operation=, arguments=, request=, scope=, input_refs=, immutable_input_versions=, handoff_unit=, acquired_record_unit=, key=ctx.operation_key)`: one operation, idempotent on the key; returns `{status, event{handoff_ready, native_handle, ...}, feedback, credit, facts{execution_completed, execution_result_refs}}`. The old executor (credit view, facts, completion) lived outside the episode trees. `task.required_member` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.api_execute')`.
- `await job_access.wait_for_job(resource_id=, service=, condition=, handoff_refs=, key=)`: the wait on a remote service job. Raises the same way.
- Job record kind: the handoff row, wanted as `store.table(JOB_LEDGER).put({'job', 'event': 'handoff', 'at', 'detail', 'source_ref'})`. `task.write_handoff_record` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job record kind ...')` when a reply reports a handoff.

## BLOCKED-ON-STORE-ACCESS
- `records/service_calls/structural_homology_evidence/api_job_receipts.py::ApiJobReceipts`: pattern "library not carried" (its constructor takes the old `bound`: `bound.assignment`, `bound.run_id`, `bound.episode_id`). Wanted: `ApiJobReceipts(...).publish(position, outcome)` inside `write_handoff_record`. Not imported.
- `acquisition/service_calls/structural_homology_evidence/api_services.py::publish_existing_acquisition`: pattern "library not carried" (`tools.store.db.execute('SELECT * FROM tool_operations ...')`). Not called.

## Unplaced old functions
See the "unplaced" rows of the Carried over table (35 rows: the results-role catalog, practical context, results directory, retained-result reader, commissionable tool contracts, and the whole `terminal_execution.py` sibling copy).
Also not found anywhere: `render_api_launch_prompt` (old `execution_prompt`, outside the episode trees); the episode's presentation is written in `decide` instead.

## Contract misfits
- new field: api_job_execution scope; new field: api_job_execution request; new field: api_job_execution input_refs; new field: api_job_execution completion_target (the old code had the completion proof, not a numeric target); the assignment's remaining executor-schema properties are unknown (executor outside the trees).
- completion credit may pass its target: the executor's credit view adds `acquired_record_unit` credit beyond one `handoff_unit`; the controller raises `ValueError('completion_credit_exceeds_target')` if the commissioned `completion_target` is passed.
- `execution_result_origin` is always null in the old facts and a form has no null type: declared as text, selecting it raises.
- The old per-axis `validate_form` does not exist for A102: none called (the old report check is `validate_report`, carried in final_to_parent).
- The old frozen closed credit ("later delivery never reprices it") has no counterpart; the system's closure credit is used.
- `ctx.settings` of this episode must hold `resources`, `initial_information`, `handoff_unit`, `acquired_record_unit`, `cost`, `parameters`; optional `launch_instructions_directory`, `tool_knowledge_directory`.
- Not carried but in the old code: the old `wait` paragraph about `pending_child_` handles and `native_event_targets` (pending children do not exist); a new wait paragraph was written.

## Not repaired
- Unplaced (previously labelled machinery in the Carried over table, now "episode function, unplaced"): `result_selection.py` (`APIResultSelection` and its 5 methods), `retained_protein_reader.py` (`APIRetainedProteinReader` and its 3 methods), `retained_result_acquisition.py` (`APIRetainedResultAcquisition`, `_selected_result_action`), `retained_result_publication.py` (`APIRetainedResultPublication`). They are results-role code over old runtime tables/receipts, with no placement found; nothing here uses them.
- `render_api_launch_prompt` (old `execution_prompt`, outside the episode trees): not found anywhere, no row in the old function list; the presentation is written in `decide`.
- Tests of `internal_summary`, `final_to_parent` and `validate_report`: they need the system's view/records objects, which a test could only hand-assemble (a fake); the job service parts are blocked. Not written.
- All BLOCKED-ON-JOB-SERVICE and BLOCKED-ON-STORE-ACCESS items above, and the contract misfits, are system limits and are not repaired.
