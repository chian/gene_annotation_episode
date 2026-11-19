# a106/perturbation_evidence/execution_job_submission: blocked, unplaced and misfit items

Carried 19 November 2026. The folder holds the ten files, `tests/test_binding.py` (13 tests, real, passing through the
launcher, run `runs/cov_a106_01_u125_1`) and the child folder `api_job_execution` (untouched). Old code was read with
`git --git-dir=/home/chia/repos/gene_annotation_episode_disk/.git show 97308b94c:<path>` (the working tree has no
`.git`). Deleted first: hook-era `episode.py` (class `ExecutionEpisode(JobSubmissionContract)`) and
`submission_source.py`; no other episode folder imported either.

## BLOCKED-ON-STORE-ACCESS

None. The library functions the tools call (`ToolKnowledge.execute`, `LaunchInstructions.execute`) take no Store.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: `await ctx.services["job_access"].capabilities(resource_id)` (`task.execution_capabilities`, for each API resource; raises `NotImplementedError`).
- BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: `ctx.services["job_access"].read("validate_assignment", request)` (`task._bound`, the API service's own validation of a request; old `api_execution.validate_assignment`; raises).
- BLOCKED-ON-JOB-SERVICE: handoff record kind (job ledger, LAUNCH_MONITOR_EXTRACT_MECHANICS section 6); wanted call: `records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})` for each handoff reference the API child returned (old `job_progress_provider.targets.usable_handoff(target)`). `credit.py`, `read_from_child.py` and `internal_summary.py` count a handoff as usable when the child reports `execution_completed` with handoff references; the resource id is the one this episode commissioned.
- BLOCKED-ON-JOB-SERVICE: job_access.read('saved_adapter_results'); wanted call: `ctx.services["job_access"].read("saved_adapter_results", reference, namespace)` (`final_to_parent._resolver`: resolving a reference inside a returned `bvbrc_application_outcomes` value, old `returns.records._resolve` over `read_latest_adapter_result` and the publications store; raises when an outcome is returned and validated).

## unplaced_old_functions

- `native_input_custody.py` (all 17 rows), `received_evidence.py` (all but `_received`, `received_report_facts`, `_appservice_received_support_refs`), `to_parent.py::resolve` native custodian branches: reference resolution and validation of native inputs and received reports over the old receipts and `runtime_*` tables; the system checks held records and this episode only commissions an API job. Classified machinery in the "Carried over" table.
- `execution_state._target` and `_context_target`: the results role (`execution_results_assignment_v1`) belongs to the result-acquisition episode.
- `execution_state._check_parent_inputs`: re-read of the parent launch assignment from `runtime_episodes` and the pinned input versions against the Store; a commission check (owner's rule 1), none is carried.
- Old `from_parent._request_schema` (the concrete per-resource request schema `api_execution.assignment_schema`): outside the episode trees, the job service's; a request is checked against the closed envelope `validate_api_assignment` and by `job_access.validate_assignment`.
- Old `to_parent._application_facts`: the projection `project_application_facts(body, sheet=, components=)` of the latest adapter result is not called; `bvbrc_application_outcomes` is the child's own report.

## contract_misfits

- BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: await ctx.services["job_access"].capabilities(resource_id)
- BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: ctx.services["job_access"].read("validate_assignment", request)
- BLOCKED-ON-JOB-SERVICE: handoff record kind (job ledger); wanted call: records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})
- BLOCKED-ON-JOB-SERVICE: job_access.read('saved_adapter_results'); wanted call: ctx.services["job_access"].read("saved_adapter_results", reference, namespace)
- new field: execution_job_submission record_refs (old code read the job inputs from the Store by reference)
- new field: execution_job_submission handoff_unit (old configuration value; `credit` has no settings and the API child takes it as its completion target)
- new field: execution_job_submission scope (old runner scope; the API child requires it)
- new field: execution_job_submission received_handoff_resources (old receipts ledger `initial_known_record_refs`)
- `acquired_record_unit` (old configuration value) is not an assignment field: the old A106 launch credit had `new_acquired_record_count` 0 and never used it.
- api_job_execution declares `immutable_input_versions` as a record, the launch assignment's is a list: `msg_to_child` passes `{'versions': [...]}` (the key name is this episode's; the child may declare a list instead).
- `msg_to_child` passes the `request` of the closed API service envelope as the child's `request` and the envelope's `service` as its `service`.
- The child declares `bvbrc_appservice_support_refs` and `bvbrc_application_outcomes` selectable and raises (`api_job_fact_not_recorded`) when the service did not report one; this episode's `msg_to_child` selects both on every commission (the old live facts always had the support refs and the outcomes `[]` when no saved result existed), so a commission whose job reports no outcome fails in the child. The child, not this episode, would have to return `[]`.
- The old `required_return_sources` (`execution_handoff_refs` required only when the commissioner was the perturbation head with an annotation task) is not a required field: all sources are selectable and `msg_to_child` selects them on every commission; the perturbation head's own `msg_to_child` must select them from this episode.
- `permitted_common_actions` offered `reason`, `wait` and `redeliver_report`: not carried (no reasoning tool: the episode commissions launches and has no scientific content to commit; the system has no wait or redelivery).
- Yield: the old exact-zero estimator for a launch whose every eligible request already had a usable handoff is not carried and no controller has maximum 0, so such a launch raises `launch_every_original_request_already_has_a_handoff` when its controller is built. `BoundedQualityYieldController` needs a `task_yield_profiles` entry `launch:<classes>` in the episode's `continuation` settings (`ctx.settings` must also hold `resources`, `initial_information`, `launch_instructions_directory`, `tool_knowledge_directory`).
- Credit cannot pass the controller's maximum: it counts distinct commissioned resources without an earlier handoff, only permitted resources are offered (no completion-target trap).
- `perturbation_evidence/episode_contract.py` (not mine) docstring still names `execution_job_submission.submission_source.JobSubmissionContract` (deleted).
