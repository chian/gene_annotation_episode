# hpc_resource_work_execution (A101): blocked, unplaced and contract misfits

Episode: `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/resource_work_submission/hpc_resource_work_execution`. Job episode (old role `launch_hpc`): the thin resource-adapter form; everything resource specific came from the selected resource adapter, which is now the declared service `resource_adapter`.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `resource_adapter` (declared in `task.py` `SERVICES`); wanted call: `ctx.services['resource_adapter'].read('capabilities')`, `.read('bound_resource_ids')`, `.read('catalog', assignment)`, `.read('estimates', assignment)` (decisions, recorded reads; the old `services.capabilities()`, `adapter.catalog(context)`, `adapter.decision_context(context)['resource_tool_estimates']`). `task.read_adapter` raises `NotImplementedError` where reached (tested).
- BLOCKED-ON-JOB-SERVICE: `resource_adapter`; wanted call: `ctx.services['resource_adapter'].capabilities()` (tool `resource_capabilities`; the old `resource.capabilities`). Raises where reached (tested).
- BLOCKED-ON-JOB-SERVICE: `resource_adapter`; wanted call: `await ctx.services['resource_adapter'].execute(assignment, tool_name, tool_arguments, key=ctx.operation_key, resumed=ctx.resumed)` (tool `adapter_tool`; the old `adapter.execute(context, tool_name, arguments, operation_key)`), idempotent on the key. Raises where reached.
- BLOCKED-ON-JOB-SERVICE: `resource_adapter.prepare_assignment`; wanted call: `ctx.services['resource_adapter'].prepare_assignment(assignment, 'launch_hpc')` (the old `adapter.prepare_assignment(parent, 'launch_hpc', selected, scope, operation_key)`, which added `adapter_assignment`). Not called anywhere; a tool-side call is wanted once the service exists, with the result passed in the tool's arguments.
- BLOCKED-ON-JOB-SERVICE: job record kind for a handoff check (the adapter's own `check_record_refs`, `handoff_receipt` records): the adapter wrote them into the old Store. The episode writes each adapter reply as one artifact through `ctx.store.artifact` (`reply_ref`, returned as `handoff_refs`); a real handoff record kind and the adapter's own records in custody are not provided.

## BLOCKED-ON-STORE-ACCESS

None. Library functions called (`replace_span`, `extend_context`, `rejection_feedback`, `decode_response`/`generation_schema` of A101, `time_accounting`, `yield_table`, `resource_records`, `LaunchInstructions`, `ToolKnowledge`, `validate_selection`) read no Store. `LaunchInstructions` and `ToolKnowledge` are only built when the optional settings directories are given.

## UNPLACED OLD FUNCTIONS

- `execution_contracts.py _availability_failure`: used only by the `resource.inspect` handler of `execute`, which this episode's catalog does not list (the launch parent's tool)
- `execution_operations.py OperationalOperations.execute`, branches `resource.inspect` and `resource.check_handoff`: not in this episode's catalog (the launch parent's tools); an adapter tool of those names goes through `adapter_tool` unchanged
- `from_parent.py OperationalAssignment._require_launch_child_instruction_pins` and the parent comparisons of `prepare_assignment` (`resource_assignment_conflict`, `resource_selection_conflict` against the parent, `launch_instruction_inheritance_conflict`): they read the launch parent's own assignment, which a child cannot read (README 5 item 14); the parent copies what it fixes into the child's assignment in its `msg_to_child`
- adapter facts (`adapter.fact_sources('launch_hpc')`, `adapter.facts`): the adapter's fact names are not known to this folder, so they cannot be declared as `RETURN_FORM` fields; BLOCKED-ON-JOB-SERVICE: `resource_adapter.fact_sources`; wanted call: `ctx.services['resource_adapter'].read('fact_sources', 'launch_hpc')` at declaration time (a form is static)
- adapter `validate_report(context, form, original_schema)`: validated the report against the parent-written JSON schema, which no longer exists, and `final_to_parent` is handed no services
- `to_parent.py OperationalReport.resolve`, `received_evidence.py`: report reference checks and receipt registration are the system's custody

## CONTRACT MISFITS

- BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: `await ctx.services['resource_adapter'].execute(assignment, tool_name, tool_arguments, key=ctx.operation_key, resumed=ctx.resumed)`.
- The adapter's tool catalogue is dynamic (the adapter's list is authoritative) but `TOOLS` is static: the episode declares `resource_capabilities` and one generic `adapter_tool`; the model-facing names stay the old ones (`resource.capabilities`, the adapter's tool names), mapped in `action`. Tool names cannot contain a dot.
- Assumption about the adapter reply: a handoff is `result['execution_handoff']` of an adapter tool reply (an `execution_handoff_v1` record). The old code did not show where the adapter put it.
- new field: hpc_resource_work_execution input_refs (assignment; the records of the job's inputs, passed in custody)
- new field: hpc_resource_work_execution handoff_refs (return, required; the reply records of the handoff checks)
- new field: hpc_resource_work_execution finding (return; the old episode returned the parent's requested JSON-Schema form). `FINDING_FORM`: `resource_id`, `kind`, `availability`, `usable_handoffs`, `unavailable_checks`, `tool_calls`, `failed_calls`, `qualification`.
- `execution_handoff` is null in the old facts for zero or several identities; a form has no null, so it is a `record` returned as `{}`. `launch_instructions` was nullable; it is an optional field (absent for null).
- Old `reason` action is carried as the tool `reason` (`ctx.store.commit_reasoning(commit, {'subject_refs': input_refs}, ctx.operation_key)`); the scope is the assignment's `input_refs` (an assumption: the old scope came from the parent's `prepare_assignment`).
- Old `wait` action not carried (machinery, README 3b); a wait on an HPC job event would be a tool unit over a service that has no wait; the job-access design provides none. `resource.capabilities` is always offered, so `action` always accepts a unit.
- Controller choice: accumulation (README 7b; the old file named none). Credit counts distinct usable handoffs; there is no commissioned amount, so completion has no target. Settings the episode reads: `cost` (above zero, or the controller never stops), `parameters`, optional `launch_instructions_directory`, `knowledge_library_directory`. The `resource_adapter` service needs a factory in the run's `services` collaborator (a `LinkError` otherwise).
- The old credit was `services.bound_role_credit` (the adapter's `credit_view`), defined outside this folder; the new credit is the count of usable handoffs returned by the tools (an owner decision to confirm).
- Estimates (`resource_tool_estimates`) are a recorded read of the service in `decide`, not shown by `internal_summary`.
- `validate_report`: the handoff fact check is carried in `final_to_parent`; since the result is built from the same summary it cannot differ today.

## Not repaired

- BLOCKED-ON-JOB-SERVICE: `resource_adapter` (read, capabilities, execute, prepare_assignment, fact_sources, validate_report) and the handoff record kind: a limit of the system, not repaired; each call raises where reached.
- Contract misfit: the adapter's catalogue is dynamic while `TOOLS` is static; one generic `adapter_tool` plus `resource_capabilities` stays. The handoff location `result['execution_handoff']` of an adapter reply is an unverified assumption.
