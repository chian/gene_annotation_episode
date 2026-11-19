# execution_job_submission (A110, under hpc_work_planning): blocked, unplaced and contract misfits

Episode: `gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission`. Launch episode of the job family: it commissions one of its two route children (`hpc_job_execution`, `local_job_execution`) for one requested job and returns the handoff. It calls no job service itself (`SERVICES = ()`); submitting is the route children's. Its only old test (`tests/test_launch_connected.py`, inheriting the old shared-root `LaunchConnectedChecks`) is retired; `tests/test_episode.py` is new and real.

## BLOCKED-ON-JOB-SERVICE

- None of its own. BLOCKED-ON-JOB-SERVICE: `job_access`; wanted call: `await ctx.services['job_access'].exec_command(...)` is made by the route children (see their blocked files), not by this episode. This episode only names their slots and the records they return (`execution_handoff_refs`); no job record kind is invented here.

## BLOCKED-ON-STORE-ACCESS

- None. This episode calls no library function that touches the Store, and its functions read no record (`credit.py`, `internal_summary` and `read_from_child` work on the parent input and the child results).

## UNPLACED OLD FUNCTIONS

- `initial_information.py initial_information`: the reader catalog `library.execution_initial_information.presentation.resource_information` (old shared root) has no home in `episode_support/`; the assignment (requests, inventory_snapshot, constraints) is shown to the model in `decide` as `execution_assignment`.
- `work_operations.py LaunchWorkOperations.execute` / tool `execution_capabilities`: `library.execution_resource_information.execution_capability_information` has no home; `task.py execution_capabilities` raises `NotImplementedError('library_not_placed:...')` when selected.
- `resource_information.py LaunchResourceInformation.resource_tool_contracts`: commissionable operation contracts per configured resource (`library.execution_operation_information`, `native_flux_balance_tool_info`; no home).
- `internal_summary.py LaunchInternalSummary._with_selected_execution_task`: `scientific_job_view` (old `flux_balance_request_binding`) and `resource_information_for_id` (`library.execution_resource_information`) have no home; `messages/internal_summary.py selected_execution_task` raises when every request is a native flux-balance request and a `scientific_task` was passed.
- `input_versions.py LaunchInputVersions._versions` (`validate_execution_input_versions`) and `_flux_balance_inputs` (`flux_balance_execution_inputs`): no home; the immutable input versions are validated against the launch schema only.
- `scientific_reference_support.py ..._matches_flux_balance_assignment`: compact flux-balance assignment check over the request binding (old runtime tables), local only; not carried.
- `received_result_records.py native_result_operation_catalog`: the `execution.results.*` operations belong to the results role (execution_result_acquisition), not to this launch.
- `task_presentation.py present_launch_context` (part): the renderers `library.hpc_prompt`, `library.monitor_prompt`, `library.scientific_decision_presentation` (old shared root) have no home; the context goes to the model as the structured `ModelRequest` context.
- `task.py` hook `validate_hpc_launch_report_contract` (`library.hpc_handoff_report_contract`, no home): it checked the parent-written report form `hpc_launch_report_form {execution_handoff_refs}`; in the new form the parent selects `execution_handoff_refs` from the declared `RETURN_FORM`, so no parent-written form exists to check.
- `task_decision.py` `call` (part): `execution_expectations`, `resource_tool_estimates`, `native_execution_expectations` (resource estimator and estimate table: README 5 item 19, not provided).
- Registry tools of the old catalogue (`launch.instructions.search/entry/read/select`, tool-knowledge lookups) were not in this episode's own `work_operations` and are not offered here; the old instruction paragraphs that name them are not carried.

## CONTRACT MISFITS

- validate_form_not_built:biochemical_feasibility_evidence: the old `validate_report` called the axis `validate_form(form, original_schema, resolver)`. The axis has none; `messages/final_to_parent.py validate_report` raises `NotImplementedError('validate_form_not_built:biochemical_feasibility_evidence')` where that call was, so `final_to_parent` raises on every run until a validator exists.
- new field: execution_job_submission handoff_unit (number): the old configuration value `handoff_unit`; `credit(summary, records)` has no settings, so the commissioner states it in the assignment.
- new field: execution_job_submission handed_off_resource_ids (list, optional): the resources whose usable handoff the commissioner already held (old initial known records, which the old runner inherited by receipts).
- new field: execution_job_submission record_refs (record_refs, optional): the records the job inputs name (flux-balance input versions); `msg_to_child` passes them to the local child's `record_refs` field.
- new field: execution_job_submission scientific_task (record, optional): the old `services.scientific_parent_task`; forwarded to the local child's `scientific_task` field and shown in `selected_execution_task`.
- new field: execution_job_submission hpc_execution_job (record, optional): the planner's `LaunchPreparation.initial_decision_context` value (plan id, objective, manifest, acceptance, supplied input file, coordinator workspace, instructions), shown in `decide`. The hpc child declares no such field though its old `initial_decision_context` also supplied it for role launch_hpc.
- The old compact flux-balance launch assignment (anyOf with `flux_balance_request_binding.launch_assignment_schema`; `flux_balance_requests.preview`) is not carried, as in the local child: the parent passes the materialized practical requests. `authenticate_launch` (the planner's ledger, `HPCLedger`) is a check of the commission against another episode's file ledger: a wrong commission fails (rule 1); not carried.
- `launch_instructions` is nullable in the old schema (`anyOf null | object`); a form field has no null (README 5 item 11): the commissioner omits it. A request carrying `launch_instructions: null` fails the child's form.
- Tool name `execution.capabilities` became `execution_capabilities` (tool names are `[a-z][a-z0-9_]*`).
- A usable handoff is a non-empty `execution_handoff_refs` of a route child's return (selected in `msg_to_child`, with `execution_completed`): the old test (`job_progress_provider.targets._handoff_reader`, `usable_handoff`) has no home. The resource identity is the unit's `resource_id` argument. This is an assumption of this carry-over.
- `execution_result_origin` is null in the old facts when no result is retained, and a form field has no null: selectable `record` field; `final_to_parent` raises `NotImplementedError('no_null_form_type:execution_result_origin')` when selected. `execution_result_refs`, `execution_file_source_refs` and `execution_file_capture_outcomes` are always empty (a launch acquires no results). The old flux-balance fact sources (`fba_fact_sources()`) are not declared (no home).
- Settings the episode reads (`continuation['biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission']`): `task_yield_profiles` (`'launch:<sorted request classes joined by +>'` -> `{'cutoff', 'parameters'}`), optional `launch_instructions_directory`. The old results profiles, acquired-record unit, log window and private-yield flag are not read.
- Controller: `BoundedQualityYieldController` with maximum = permitted requests not already handed off x `handoff_unit`; the credit (new handed-off resources x unit) cannot pass it. When no request remains the maximum is zero (the old exact-zero estimator is not carried; only the controller stops an Episode).
- Offered tool `execution_capabilities` raises when selected (library not placed), and `final_to_parent` raises on every run (`validate_form_not_built`): a real run cannot complete until both are placed. The route children's own blocks (`job_access`, `PracticalReceiptInformation`) also stop a real run.
- The old goal text is task.py `INSTRUCTIONS`; `goal.py` GOAL, UNIT and RESULT are the earlier port's texts.

## Not repaired

Real limits of the system, contract or guide, reported and not worked around (repair step 2026-11-19):

- messages/final_to_parent.py: validate_report raises NotImplementedError('validate_form_not_built:biochemical_feasibility_evidence'); the axis has no validate_form.
- task.py execution_capabilities: raises library_not_placed (execution_capability_information has no home in episode_support).
- The nine unplaced old function groups listed above (library has no home in episode_support).
- The commission checks (authenticate_launch, immutable-input-version check, _constraints) are not carried: a wrong commission just fails.
- Exact-zero yield estimator not carried: README 7b maps the episode to the bounded quality controller.
- New assignment fields (handoff_unit, handed_off_resource_ids, record_refs, scientific_task, hpc_execution_job): the parent supplies them; contract misfits as listed.
- hpc_execution_job is not forwarded to the children: the old job_assignment channel is not evidenced as a request-level field.
