# execution_job_submission (A107, under hpc_work_planning): blocked, unplaced and contract misfits

Episode: `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_job_submission`. Job episode (the launch parent of the API, local and HPC route children). Tests: `tests/test_binding.py` (13 pass, no remote contact).

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access.capabilities(resource_id)`; wanted call: `await ctx.services["job_access"].capabilities(resource_id)` (the configured operations and configuration facts of an API resource, for the `execution_capabilities` tool). `task.py execution_capabilities` raises `NotImplementedError` at that point for an API resource.
- BLOCKED-ON-JOB-SERVICE: `job_access.validate_assignment(request)`; wanted call: `ctx.services["job_access"].read("validate_assignment", request)` (the API service's own validation of an API request, old `api_execution.validate_assignment`). `task.py _bound` raises `NotImplementedError` where it is reached.
- BLOCKED-ON-JOB-SERVICE: job record kind (the handoff row of the job ledger, LAUNCH_MONITOR_EXTRACT_MECHANICS section 6); wanted call: `records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})` for each handoff reference a launch child returned, to learn the target resource and usability (old `job_progress_provider.targets.usable_handoff(target)`, `handoff_receipts._received`, `credit._live_project_credit`). No job record kind exists: `credit.py` counts the child's own report (completed, with handoff references) and the resource id this episode commissioned. credit.py is real code and raises nowhere.

## BLOCKED-ON-STORE-ACCESS

None. The episode reads and writes no Store record: its tools return values and call no library function with `ctx.store`.
Library functions it calls, all pure (no Store): `validate_api_assignment`, `validate_assignment` (practical records), `TerminalExecution.validate_assignment` (configuration and assignment checks, no Store), `LaunchInstructions`, `ToolKnowledge`, `strict_output_schema`, `decode_strict_output`, `rejection_feedback`, `time_accounting`, `yield_table`, `validate_form` (axis), the result-view `*_fact_sources` declarations. `TerminalExecution` is in its old form (it opens a transport when it executes) but only `validate_assignment` is called.

## UNPLACED OLD FUNCTIONS

- `from_parent.py LaunchFromParent.prepare_assignment` (commission checks): `authenticate_launch` of hpc_work_planning, masking/utility/native/standard BLAST/RNA structure job-input checks and the pinned input versions are checks of a commission; a wrong commission fails (rule 1). Not carried.
- `from_parent.py _launch` BLAST graded request (`BLAST_GRADED_REQUEST_SCHEMA`, `BLAST_GRADED_REQUEST_VERSION`, old `a107_blast_execution`): no library module; `read_from_parent._request` raises `NotImplementedError('unplaced:a107_blast_execution.BLAST_GRADED_REQUEST_SCHEMA:<version>')`.
- `launch_state.py LaunchLaunchState.initialize` (`_blast_launch_requirement`, masking/utility/NMF inputs, `execution_input_versions.validate_execution_input_versions`): no library module; checks of a commission.
- `input_versions.py` (`_masking_inputs`, `_utility_inputs`, `_expression_nmf_inputs`, `_versions`): `native_blast_masking_results.validate_job_inputs`, `native_blast_utility_results.validate_job_inputs`, `expression_nmf_operands.validate_expression_nmf_job_inputs`, `execution_input_versions`: no library module; checks of a commission.
- `handoff_receipts.py _context_target` and `_received`: re-read of the handoff target against the assignment and the BLAST graded query sha256 through the old `job_progress_provider`/`api_execution`; BLOCKED-ON-JOB-SERVICE (handoff record kind).
- `resource_information.py LaunchResourceInformation.resource_tool_contracts`: the per-resource launch/results operation contracts with commission routes (`api_execution.operation_contracts`, `homology_api_contracts`, `native_operation_contracts`, `preparation_operation_contracts`, the native `*_tool_info` modules): no library module.
- `received_result_records.py native_result_operation_catalog`: `execution.results.*` operations belong to the results role.
- `internal_summary.py _with_selected_execution_task`: `expression_nmf_presentation.expression_nmf_scientific_job_view` and `native_profile_presentation.native_profile_scientific_job_view` are in no place; `task.py _selected_execution_task` raises `NotImplementedError('unplaced:...')` for a native_expression_nmf, native_hmmer or native_hmmer_preparation job when a scientific task is present.
- `task_presentation.py present_launch_context`: the prompt renderers (`render_hpc_prompt`, `render_partner_presence_evidence_prompt`, `render_api_launch_prompt`, `render_selected_execution_prompt`, `render_monitor_prompt`, RNA prompts) are in no library module; the episode renders its own text task.
- `task.py` `_validate_hpc_launch_report_contract` (`validate_hpc_launch_report_contract`) and `to_parent.validate_report` adapters (RNA comparison/structure, NMF, Infernal, masking, utility, UniProt, Rfam `validate_received_report`): no library module; they checked the old parent-written JSON-Schema form, which no longer exists.
- `task_decision.py` context additions `resource_context`, `shared_information_context`, `execution_expectations`, `resource_tool_estimates`, `native_execution_expectations`, `requested_action_history`: old-runner services; not carried.
- `configuration.py` native binding validators (`validate_expression_nmf_bindings`, `validate_rna_structure_bindings`, `validate_native_infernal_bindings`, `validate_native_infernal_preparation_bindings`, `validate_primary_resource_bindings`, `validate_preparation_resource_binding`): no library module.

## CONTRACT MISFITS

- new field: execution_job_submission record_refs (the records the job inputs name; the old code read them from the Store by reference)
- new field: execution_job_submission handoff_unit (old configuration value; credit and the yield maximum read it from the parent input)
- new field: execution_job_submission acquired_record_unit (old configuration value; the formula's second term, always times 0.0)
- new field: execution_job_submission scope (the subject scope the old runner passed to prepare_assignment; the API child requires it; optional here, an API commission without it fails at admission)
- new field: execution_job_submission scientific_task (old `services.scientific_parent_task`)
- new field: execution_job_submission received_handoff_resources (the resources whose usable handoff the old receipts ledger already held: old `initial_known_record_refs`)
- new field: hpc_job_execution record_refs: the HPC child declares no `record_refs` field, so the records its job inputs name (masking, utility, NMF inputs held by the launch) cannot be passed to it; the HPC commission passes only the request.
- api_job_execution declares `immutable_input_versions` as a `record`; the launch assignment's `immutable_input_versions` is a list (an array of INPUT_VERSION_SCHEMA). The launch passes the list unchanged, so a launch_api commission fails at admission with FormError until one side changes. Not worked around.
- api_job_execution requires `completion_target`; the launch passes `handoff_unit` (the credit one verified handoff earns).
- completion credit may pass its target: not applicable (this episode uses bounded quality; the maximum is uncredited requests x handoff_unit, and credit is handoff_unit x new handoff resources: it cannot pass the maximum).
- `required_return_sources`: the old rule required `execution_handoff_refs` only when the commissioner was the A107 head; this episode's commissioner is hpc_work_planning, so no field is required. Both `execution_handoff_refs` and `execution_completed` are selectable (all three children declare them selectable) and every `msg_to_child` selects them.
- Tool name `execution.capabilities` is `execution_capabilities` (a tool name is `[a-z][a-z0-9_]*`).
- The 21 masking (`execution.masking_*`) and BLAST utility (`execution.blast_utility_*`) fact sources have dotted names: no form field can carry them; they are not declared in RETURN_FORM and not renamed. The Infernal and Infernal-preparation family sources are in no library module. `execution_result_origin` was null (a form has no null): declared as a record; selecting it raises. `bvbrc_appservice_support_refs`: no launch child returns it; selecting it raises. The object-typed family sources raise when selected (empty object not defined).
- The old exact-zero estimator for a launch whose every eligible request already had a handoff is not carried (only the controller stops an Episode); a bounded-quality controller has no maximum 0, so such a launch fails with ValueError('launch_every_original_request_already_has_a_handoff').
- `decide` validates the configured resources and requests (`_bound`) before the first unit; a refused configuration raises and fails the run (not a model answer).
- Where the axis has no validate_form: A107 has `forms/partner_presence_evidence/communication.py validate_form`, which `final_to_parent.validate_form` calls; no NotImplementedError('validate_form_not_built') arises.
