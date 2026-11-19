# api_job_execution (A106, published_evidence_assessment/execution_job_submission child): blocked, unplaced and contract misfits

Old tests at 97308b94c: only `tests/__init__.py`; nothing retired (the retired_tests file holds its header only).

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (the run's job-access service for API resources); wanted call: `ctx.services['job_access'].api_capabilities(resource_id)` in tool `api_capabilities` (old `OperationalOperations.capabilities` / `_resource_information`: availability, tool names, service, base_url of the configured API resource, no probe).
- BLOCKED-ON-JOB-SERVICE: `job_access`; wanted call: `ctx.services['job_access'].api_operation(assignment, operation, operation_arguments, held, key=ctx.operation_key)` in tool `api_operation` (old `api_execution.execute`). It must be idempotent on the key. Reply read by the tool: `status`, `result`, `feedback`, `facts` (recorded fact sources by their old names, e.g. `bvbrc_application_outcomes`), `events` (list of `{name, event: {state, kind, facts, failure_code}}`, the old `api._events` rows), `handoffs`, `support_receipts` and `artifacts` (each a list of `{content, media_type}`, written by the tool with `ctx.store.artifact`), `handoff_established`, `execution_completed` (the verified completion of old `api_execution.verify_completion`), `job_identity`, `request_identity`, `submission_outcome`. The old `APIServiceExecution` (`api_service_execution`, with `standalone_api_context`, `api_operational_credit`, `bvbrc_appservice_host`, `standalone_appservice_reports`, `execution_progress`, `bvbrc_appservice_custody`) lived in the old shared root and has no copy in `episode_support/`.
- BLOCKED-ON-JOB-SERVICE: `job_access`; wanted call: `await ctx.services['job_access'].api_wait(assignment, handle, after_cursor, reconsider_at)` in tool `wait_for_service_job` (old `perform_selected_wait` of the `wait` the episode permitted).
- BLOCKED-ON-JOB-SERVICE: job record kind (handoff record). `episode_support/` declares no work table for job records, so the tool writes each handoff, support receipt and result with `ctx.store.artifact(...)` and returns the references; no record kind was invented. Wanted: the declared job ledger row of the handoff.
- BLOCKED-ON-JOB-SERVICE: `api_execution.assignment_schema(resource_id)` (the concrete closed request schema per bound resource, old `_request_schema`) is not in the library; `read_from_parent` validates the envelope with the library's `validate_api_assignment` (`request` is an open record).

## BLOCKED-ON-STORE-ACCESS

- Nothing in this episode calls a library function that touches the Store through a raw `Store`. The library calls it makes (`validate_api_assignment`, `application_fact_sources`, `yield_table`, `time_accounting`, `rejection_feedback`, `ToolKnowledge`, `LaunchInstructions`, `generation_schema`/`decode_response` of the A106 action transport) take values or a directory.
- function = `gene_annotation_episode/episodic_workflow/episode_support/records/perturbation_evidence/held_inputs.py::HeldInputs` / `read_receipt`, pattern = "library not carried". Not called: the tool passes `ctx.store.get(ref)` of each held input record to the service instead (old: `HeldInputs` assembled the AppService operands from `store`).

## UNPLACED OLD FUNCTIONS

- `execution_state.py _check_parent_inputs`, `from_parent.py _launch`, `_permitted`, `_constraints`, `from_parent_launch.py _parent_launch_assignment_schema`, `native_input_custody.py _versions` (the input-version re-validation of the parent launch assignment): checks of the commission against the parent's own launch assignment and Store (a commission check; a wrong commission fails, README 5).
- `native_input_custody.py` (all rows except the class) and `execution_state.py _target`, `_context_target`: results-role target, retained-input authority and native input-version functions (protein, ATAC, MACS2, LUMPY, NMF, fluorescence, flux balance). `execution_input_versions` and the `retained_input_authority` classes are old-shared-root modules; the API launch role reaches none of them. The inputs the service reads are the records the parent passes in `input_refs`.
- `decision_inputs.py` context pieces without a home here: `resource_context`, `shared_information_context`, `child_options`, `completed_action_reports`, `pending_work`, `execution_expectations`, `resource_tool_estimates`, `native_execution_expectations`, `waiting_support`, the contract information profile. The launch instruction library, the selected launch instructions and tool knowledge are carried (settings `launch_instructions_directory`, `tool_knowledge_directory`).
- `decision_presentation.py present_credit_state`: presentation of the root's annotation-axis credit and child report forms; not this leaf.
- `received_evidence.py` (13 rows): forwarding and re-validation of a child's received report facts over `runtime_report_attempts`; this leaf has no child.
- `execution_operations.py resource_tool_contracts`: invocation-route contracts of the old launch commission of its resource children; no child here.
- `execution_contracts.py launch_operation_catalog`: the `execution.capabilities` catalog entry of the old launch role; replaced by the tool `api_capabilities`.
- `to_parent.py _application_facts`, `_application_resolve_*`, `resolve`: read saved adapter results through the old publications (results role) and resolve report references (custody is the system's). Not in the library: `bvbrc_appservice_host.SUPPORT_SOURCE` (its text `bvbrc_appservice_support_refs` is declared in `final_to_parent.py`), `read_latest_adapter_result` use.
- The old validate_form call of `validate_report` (A106's `validate_form(form, schema, resolver)`) has no object: the parent-written JSON-Schema form with `x-source` fields no longer exists (rule 5). The fact-agreement part is carried in `final_to_parent.validate_report`.

## CONTRACT MISFITS

- new field: api_job_execution completion_target (assignment, number). The completion controller needs its finite target from the commission; the old assignment had none. The parent should send the credit a verified original handoff earns (the episode's `handoff_unit`).
- new field: api_job_execution input_refs (assignment, `record_refs`). The records the service operations read (the subject record and what it names) must be named by the parent: a pass carries only the records named.
- new field: api_job_execution finding (return). Declared form: service, resource_id, handoff_established, qualification, and optional submission_outcome, request_identity, job_identity. The old report had none. (This is not an A105/A108 evidence episode: no investigation_finding or grading sheet applies.)
- new field: api_job_execution execution_handoff_refs and execution_completed are required return fields (old: always-present fact sources); `execution_result_refs`, `bvbrc_appservice_support_refs` and `bvbrc_application_outcomes` are selectable. `bvbrc_application_outcomes` is a `list` field (array of objects; there is no typed array-of-objects field).
- (repaired) completion credit passing its target: the controller is now AccumulationYieldController (README 7b, old plain accumulating YieldController), so no target applies.
- A fact that is a `record_refs` field is filled from the records the tool wrote through `ctx.store`: the system requires the Episode to hold every returned record (`CustodyError('returned_record_not_held:...')`), so `job_access` replies carry content, not references.
- `launch_instructions` of the assignment is `null` or a selection in the old schema; the form field is an optional `record` (no null).
- The old goal text names the assigned service; `goal.py` holds the text with "the assigned API service" and `task.py` writes it with the actual service.
- The settings the episode reads (`continuation` entry of its binding path): `task_yield_profiles` (`launch_api:<class>` -> `cutoff` as controller cost, `parameters`), `handoff_unit`, `acquired_record_unit`, `initial_information` (old configuration value, keyed by resource_id), `tool_knowledge_directory`, `launch_instructions_directory`. Old settings not read here: `resources`, `log_window_bytes`, `log_roles`, `require_private_yield`.
- The tool is handed no summary: `action` wraps the model's operation arguments in an envelope with the original assignment and `input_refs`, so the tool can read them.
- The old wait offered through `permitted_common_actions` (`tool`, `wait`) is the tool `wait_for_service_job`, always offered (every A106 API assignment is a service job).

## Not repaired

- completion_target remains a field of ASSIGNMENT_FORM (messages/read_from_parent.py) because the parent's msg_to_child.py:33 still sends it; the child no longer reads it (accumulation controller). The parent's agent and this field should drop it together.
- credit formula unverified: old operational_credit_from_identities lived in the old shared root and is not readable; credit counts result_refs, not identities.
- BLOCKED-ON-JOB-SERVICE: job_access (see above); no job record kind, no per-resource assignment_schema, no array-of-objects field.
