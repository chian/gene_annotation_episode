# a104/evolutionary_history_evidence/execution_job_submission: blocked, unplaced and misfit items

Carried 19 November 2026. The folder holds the ten files, `tests/test_binding.py` (13 tests, real, passing through the
launcher) and the three child folders (untouched, not imported). Old code was read through
`git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` (the working tree has no `.git`). The
hook-era `submission_source.py` was deleted first; nothing else outside the ten-file set was in the folder.

## BLOCKED-ON-STORE-ACCESS

None. The library functions the tools call (`ToolKnowledge.execute`, `LaunchInstructions.execute`,
`TerminalExecution.validate_assignment`) take no Store.

## BLOCKED-ON-JOB-SERVICE

- `job_access.capabilities(resource_id)`; wanted call: `await ctx.services["job_access"].capabilities(resource_id)`
  (`task.py` `execution_capabilities`, for each API resource; raises `NotImplementedError`).
- `job_access.received_bvbrc_context()`; wanted call: `ctx.services["job_access"].received_bvbrc_context()` (old
  `api_execution.received_bvbrc_context(context)`, the `received_bvbrc_values` of the first tool result; raises).
- `job_access.validate_assignment(request)`; wanted call: `ctx.services["job_access"].read("validate_assignment", request)`
  (`task.py` `_bound`, the API service's own validation of an API request; raises).
- Handoff record kind (the job ledger of LAUNCH_MONITOR_EXTRACT_MECHANICS section 6); wanted call:
  `records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})` for each handoff reference a child returned
  (old `job_progress_provider.targets.usable_handoff(target)` and `.read_target`). `credit.py` and `read_from_child.py`
  count a handoff as usable when the child reports `execution_completed` with handoff references; the resource id is
  the one this episode commissioned.

## unplaced_old_functions

- `launch_requests.py` `LaunchLaunchRequests._request_schema`: the per-resource request schema alternatives
  (`requested_job_schemas`, `preparation_job_schemas` of `a104_execution_bindings`, `api_execution.assignment_schema`)
  have no module; `read_from_parent.py` admits each request with the library `validate_assignment` /
  `validate_api_assignment`.
- `launch_state.py` `LaunchLaunchState.initialize`: `_blast_launch_requirement` for a BLAST database grader request
  (`a104_homology_execution`, no module). A request of that kind raises
  `unplaced:a104_homology_execution.BLAST_GRADED_REQUEST_SCHEMA` in `read_from_parent.py`.
- `resource_information.py` `LaunchResourceInformation.resource_tool_contracts`: per-resource operation contracts with
  commission routes need `api_execution.operation_contracts`, `homology_api_contracts`, `native_operation_contracts`,
  `preparation_operation_contracts` and the BV-BRC proteome tool info (no module in the library).
- `result_operations.py` `native_result_operation_catalog`, `selector_contracts.py` (all rows), `target_custody.py` (all
  rows): the results role of the old multi-role execution binding, carried by `execution_result_acquisition`. The launch
  role's `_context_target` (re-read of the handoff target and the graded query digest) needs the handoff record kind.
- `internal_summary.py` `_with_selected_execution_task` for `native_hmmer` and `native_hmmer_preparation` raises
  `unplaced:native_profile_scientific_job_view` (no module: `native_profile_presentation`).
- The BV-BRC data fact sources (`bvbrc_data_fact_sources`, always in the old launch `fact_sources`), the AppService
  sources and `bvbrc_appservice_support_refs`, the UniProt sources: no module in the library for this axis; not declared
  in `RETURN_FORM`.
- The old renderers `render_selected_execution_prompt`, `render_api_launch_prompt` and the state frame of
  `presentation.py`: no module in the library; `task.py` renders its own task text.

## contract_misfits

- BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: await ctx.services["job_access"].capabilities(resource_id)
- BLOCKED-ON-JOB-SERVICE: job_access.received_bvbrc_context(); wanted call: ctx.services["job_access"].received_bvbrc_context()
- BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: ctx.services["job_access"].read("validate_assignment", request)
- BLOCKED-ON-JOB-SERVICE: handoff record kind (job ledger); wanted call: records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})
- new field: execution_job_submission record_refs (old code read the job inputs from the Store by reference)
- new field: execution_job_submission handoff_unit (old configuration value; `credit` has no settings and the API child takes it as its completion target)
- new field: execution_job_submission acquired_record_unit (old configuration value; the API child requires it)
- new field: execution_job_submission scientific_task (old `services.scientific_parent_task`; the API child reads it from the commission message, the local child takes it as an assignment field)
- new field: execution_job_submission received_handoff_resources (old receipts ledger `initial_known_record_refs`)
- api_job_execution declares `execution_handoff_refs` and `execution_completed` as REQUIRED fields, while hpc_job_execution and local_job_execution declare them selectable: `msg_to_child` selects both on the local and HPC commissions and nothing on the API commission (selecting a required field raises FormError, `selection_not_a_selectable_field`). The three children's return forms differ in this; the old `required_return_sources` (required only toward the A104 head with an annotation task) is therefore not expressible uniformly.
- api_job_execution's `read_from_parent` reads `message['scientific_question']` and `message['selected_tool_info']` unconditionally: a launch without `scientific_task` cannot commission the API child (the commission fails with TypeError in `msg_to_child`); local and HPC need none.
- hpc_job_execution declares no `record_refs` field: the records an HPC job's inputs name (masking, utility, query subject) cannot be passed to it; local_job_execution declares one and receives them.
- `permitted_common_actions` offered `reason` and `wait`: not carried. This episode declares no reasoning tool (it commissions launches and has no scientific content to commit) and the system has no wait.
- Return form: the dotted masking (`execution.masking_*`) and BLAST utility (`execution.blast_utility_*`) sources cannot be field names; the BV-BRC data, AppService, UniProt and `bvbrc_appservice_support_refs` sources have no library module; `execution_result_origin` is declared as a record (the old value was null for a launch, a form has no null) and selecting it raises `NotImplementedError('no_null_form_type:...')`; object family sources raise when selected (`native_result_family_empty_object_not_defined`).
- Yield: the old exact-zero estimator for a launch whose every eligible request already had a usable handoff is not carried and no controller has maximum 0, so such a launch raises `launch_every_original_request_already_has_a_handoff` when its controller is built.
- BoundedQualityYieldController needs a `task_yield_profiles` entry `launch:<classes>` in the episode's `continuation` settings; the yield cost is the profile's `cutoff`.
- Credit cannot pass the controller's maximum: it counts distinct commissioned resources without an earlier handoff, and only permitted resources are offered (no completion-target trap).
- Not a validate_form gap: A104 has `validate_form` (`forms/evolutionary_history_evidence/communication.py`) and `final_to_parent` calls it.
