# a101/sequence_homology_evidence/execution_job_submission: blocked, unplaced and misfit items

Carried 19 November 2026. The folder holds the ten files, `tests/test_binding.py` (13 tests, real, passing through the
launcher) and the three child folders (untouched). Old code was read through
`git --git-dir=/home/chia/repos/gene_annotation_episode_disk/.git show 97308b94c:<path>` (the working tree has no `.git`).

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
  `records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})` for each handoff reference a launch child
  returned (old `job_progress_provider.targets.usable_handoff(target)` and `.read_target`, `api_execution._read_handoff`).
  `credit.py` and `read_from_child.py` count a handoff as usable when the child reports `execution_completed` with
  handoff references; the resource id is the one this episode commissioned.

## unplaced_old_functions

- `blast_request_custody.py` `BlastRequestCustody`, `_blast_launch_requirement`, `_validate_blast_launch_selection`: BLAST
  database grader request custody; needs `library.blast_return_contracts` (no module) and a sequence read through the old
  tool registry. A request of that kind raises `unplaced:blast_return_contracts.BLAST_GRADED_REQUEST_SCHEMA` in
  `read_from_parent.py`.
- `blast_pending_work.py` `BlastPendingWork`, `annotation_axis_yield_context`: returned `{}` for every role but the
  annotation root; its source is `api_execution.received_blast_jobs` (job_access).
- `blast_received_context.py`: reads `runtime_episodes` (old table); only for the root and A101 head roles (machinery row).
- `execution_contracts.py` `native_result_operation_catalog`; `result_acquisition.py` (all rows); `execution_state.py`
  `_target`: results role, carried by `execution_result_acquisition`.
- `execution_operations.py` `resource_tool_contracts`: per-resource operation contracts with commission routes need
  `api_execution.operation_contracts`, `homology_api_contracts`, the BV-BRC proteome tool info and the native
  `*_tool_info` modules (none in the library).
- `execution_operations.py` `_has_appservice`, `_has_uniprot`, `_appservice_sources`: the BV-BRC AppService and UniProt
  fact sources have no library module.
- `execution_state.py` `_context_target`: re-read of the handoff target against the assignment and the graded query digest
  (handoff record kind).
- `internal_summary.py` `initial_decision_context`: `received_blast_jobs` and `received_minhash_values` (shown to the
  annotation and A101 head roles only); `_with_selected_execution_task` for `native_hmmer` and `native_hmmer_preparation`
  raises `unplaced:native_profile_scientific_job_view` (no module).
- `native_input_custody.py` (all rows): input custody of the masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and
  flux-balance operands; for the launch these were checks of a commission's inputs (rule 1); the rest is the results role.
- `to_parent.py` `_forwards_bvbrc_reports`, `_forwards_minhash_reports`: true only for the annotation and A101 head roles.

## contract_misfits

- BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: await ctx.services["job_access"].capabilities(resource_id)
- BLOCKED-ON-JOB-SERVICE: job_access.received_bvbrc_context(); wanted call: ctx.services["job_access"].received_bvbrc_context()
- BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: ctx.services["job_access"].read("validate_assignment", request)
- BLOCKED-ON-JOB-SERVICE: handoff record kind (job ledger); wanted call: records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})
- new field: execution_job_submission record_refs (old code read the job inputs from the Store by reference)
- new field: execution_job_submission handoff_unit (old configuration value; `credit` has no settings and the API child takes it as its completion target)
- new field: execution_job_submission acquired_record_unit (old configuration value)
- new field: execution_job_submission scope (old runner scope; the API child requires it, a commission without it fails at admission)
- new field: execution_job_submission scientific_task (old `services.scientific_parent_task`)
- new field: execution_job_submission received_handoff_resources (old receipts ledger `initial_known_record_refs`)
- api_job_execution declares `immutable_input_versions` as a record, the launch assignment's is a list: `msg_to_child` passes `{'versions': [...]}` (the key name is this episode's; the child may declare a list instead).
- hpc_job_execution declares no `record_refs` field: the records an HPC job's inputs name (masking, utility, query subject) cannot be passed to it; local_job_execution declares one and receives them.
- The old `required_return_sources` (`execution_handoff_refs` required when the commissioner was the A101 head with an annotation task) is not a required field: both `execution_handoff_refs` and `execution_completed` are selectable and `msg_to_child` selects both on every commission; the A101 head's own `msg_to_child` must select them from this episode.
- `permitted_common_actions` offered `reason` and `wait`: not carried. This episode declares no reasoning tool (it commissions launches and has no scientific content to commit) and the system has no wait.
- Return form: the dotted masking (`execution.masking_*`) and BLAST utility (`execution.blast_utility_*`) sources cannot be field names; the BV-BRC AppService, UniProt and `bvbrc_appservice_support_refs` sources have no library module; `execution_result_origin` is declared as a record (the old value was null for a launch, a form has no null) and selecting it raises `NotImplementedError('no_null_form_type:...')`; object family sources raise when selected (`native_result_family_empty_object_not_defined`).
- Yield: the old exact-zero estimator for a launch whose every eligible request already had a usable handoff is not carried and no controller has maximum 0, so such a launch raises `launch_every_original_request_already_has_a_handoff` when its controller is built.
- BoundedQualityYieldController needs a `task_yield_profiles` entry `launch:<classes>` in the episode's `continuation` settings; the yield cost is the profile's `cutoff`.
- Credit cannot pass the controller's maximum: it counts distinct commissioned resources without an earlier handoff, and only permitted resources are offered (no completion-target trap).
