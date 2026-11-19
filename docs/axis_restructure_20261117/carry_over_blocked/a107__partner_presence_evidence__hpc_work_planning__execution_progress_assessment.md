# execution_progress_assessment (A107, under hpc_work_planning): blocked, unplaced and contract misfits

Episode: `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_progress_assessment`. Job episode (monitor). Old files were read with `git show 97308b94c:<path>` (the repository's `.git` is in `gene_annotation_episode_disk`, not in the checkout). The files are private copies of the finished same-axis sibling `hpc_allocation_execution/execution_progress_assessment` (the old episodes differ only in `binding_record.py` and `episode.py`); nothing is imported from it. Blocked items are therefore the same as the sibling's.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (declared in `task.py` `SERVICES = ('job_access',)`); wanted call: `ctx.services['job_access'].observe_progress(arguments['target_handle'], arguments['requested_fields'], permitted_committed_record_types=arguments['permitted_committed_record_types'], key=ctx.operation_key)`, returning the `progress_snapshot_v1` of the observation with the original identity of an unchanged observation (old `ProgressProvider.observe`). `task.py progress_observe` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ...')` where it is reached.
- BLOCKED-ON-JOB-SERVICE: `job_access`; wanted call (a recorded decision read): `ctx.services['job_access'].read('describe_progress_target', summary['target_handle'])` in `task.py decide` (old `services.describe_progress_target`). A run without the service fails at link.
- BLOCKED-ON-JOB-SERVICE: progress snapshot record for an assignment's `known_progress_refs`; wanted call: `ctx.services['job_access'].read('read_progress', reference, scope)`. `credit` has no services and the commission passes no snapshot record, so `credit.py _SummaryProgress.read_progress` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: progress snapshot record for ...')` as soon as the baseline is not empty (also at `internal_summary`). An assignment with `known_progress_refs == []` runs.
- BLOCKED-ON-JOB-SERVICE: `estimate_table` (not provided): the old `resource_tool_estimates`, `execution_expectations`, `native_execution_expectations` and `resource_context` of the decision inputs are not shown to the model, and the old `RESOURCE_ESTIMATE_GUIDANCE` is not carried; wanted call: `ctx.services['estimate_table'].read(...)`.
- BLOCKED-ON-JOB-SERVICE: custody of the records the job owner publishes (committed records, log-window sources and artifacts): they pass through `job_access` and have no receipt. Wanted call: `ctx.store.get(window['source_ref'])` / `ctx.store.open_artifact(window['artifact_ref'])` in `progress_log`, `ctx.store.get(ref)['record_type']` in `task.py _delivered` and `view.records.get(record)` in `messages/internal_summary.py`; each raises `CustodyError` for a record the Episode does not hold.

## BLOCKED-ON-STORE-ACCESS

- function = `gene_annotation_episode/episodic_workflow/episode_support/tools/partner_presence_evidence/tools.py::ToolRegistry (source.read branch)`, pattern = "library not carried" (raw Store registry). Old call `services.execute_tool('source.read', {source_ref, representation, offset, limit}, scope=..., operation_key=...)` -> intended call `ctx.store.open_artifact(window['artifact_ref'])` with a seek and an exact byte read after `ctx.store.get(window['source_ref'])`; `task.py progress_log` does this itself in a few lines (not a copy of the library function).
- function = `episode_support/grading/partner_presence_evidence/progress_information_credit.py::ProgressInformationCredit`: no Store pattern (it takes a reader with `read_progress(reference, scope)`); `credit.py` hands it a reader over the summary's snapshots.

## UNPLACED OLD FUNCTIONS

- `from_parent.py MonitorAssignment._assignment` / `prepare_assignment` (admission part): the target must be an execution handle in scope and every known progress ref an observation of the same target, checked through the old progress provider; `read_from_parent` is handed no records and no services. Not carried.
- `initial_information.py initial_information`, `received_api_reports.py received_api_reports`, `received_execution_information.py received_execution_information`: they select declared readers from the old catalog and call `library.execution_initial_information.presentation` (old shared root, no home found); not carried, not shown to the model.
- `decision_inputs.py` pieces `resource_context`, `execution_expectations`, `resource_tool_estimates`, `native_execution_expectations` (services not provided), `waiting_support`, `contract_information_profile`, `child_options`, `completed_action_reports`, `pending_work` (old-runner state): not shown to the model.
- `task_instructions.py`: `REPORT_GUIDANCE`, `HISTORY_GUIDANCE`, `EXCHANGE_HISTORY_GUIDANCE`, `REPAIR_GUIDANCE`, `WAIT_GUIDANCE`, `NATIVE_EVENT_GUIDANCE` describe actions that are gone; `RESOURCE_ESTIMATE_GUIDANCE` describes inputs of the missing estimate_table. Not carried.
- `to_parent.py` report update values (`report_update`, `report_values`, `report_basis`) and the `resolve` / permitted-record `visit` of `validate_report`: the model's interpretation before each action and the form resolver are not carried (README 3a, 3b D2); the report is recorded facts only. The old first step `validate_form(form, original_schema, resolver)` has no schema to take because the parent writes no form (A107 has `validate_form` in `forms/partner_presence_evidence/communication.py`, but nothing to hand it).
- `library.monitor_prompt.render_monitor_prompt` (old `decision_prompt_renderer`): old shared root, no home found; the episode renders its own context in `decide`.
- The annotation-axis branches of the old decision state (`annotation_axis_credit`, root arm table) belong to the old shared root and the root episode; not carried.

## CONTRACT MISFITS

- BLOCKED-ON-JOB-SERVICE: job_access; wanted call: `ctx.services['job_access'].observe_progress(...)` (see above).
- new field: execution_progress_assessment information_unit (assignment: the old monitor took it from its configuration; `credit` needs it and has no settings).
- new field: execution_progress_assessment monitoring_progress_snapshots (return, selectable: the delivered snapshots by identity, which the commissioning monitor's `credit` needs because it has no services).
- new field: execution_progress_assessment version (assignment, declared `monitor_assignment_v1`: the old schema's `version` property; the parent copies it).
- new field: execution_progress_assessment committed record refs the monitor may read (assignment `record_refs`): the old monitor read committed records of any permitted type from the shared Store; under custody they must be passed. Not added to the form (the old assignment had no such property); the parent's `msg_to_child` cannot pass them today. Callers of this episode (hpc_work_planning) must also supply `information_unit` and the declared `version`.
- the old `null` facts (`monitoring_execution_state`, `monitoring_result_available`, `monitoring_observed_at_unix_seconds` without an observation) are `record` fields holding `{'value': ...}`: a form has no null.
- tool names: the old `progress.observe`, `progress.read`, `progress.log` are `progress_observe`, `progress_read`, `progress_log` (a tool name matches `[a-z][a-z0-9_]*`). The model's commission selection is `monitor_dependency` with `dependency_handle`.
- progress observation identities and `known_progress_refs` are provider identities, not Store records: they travel in `list` fields, not `record_refs`, and are not custody.
- `monitor_private_yield_binding_not_enabled` and the cutoff value checks are kept in `yield_estimator.py` over `settings['cost']` and `settings['parameters']['uncertainty_alpha']`. Cost zero passes the old check but an accumulating controller then never stops; the run's settings must give a cost above zero.
- the monitor's credit raises `monitor_information_credit_cannot_decrease` against the credit the controller last saw (README 7b); the projection is monotonic by construction, so it cannot fire today.
- the old goal text had two variants (own yield settings, or the caller's projector); only the own-yield variant is carried; the old "original parent's typed form" became "your declared form" because the parent writes no form.
- the old rule that an axis-head parent must request `monitoring_progress_refs` belongs to that parent's `msg_to_child`.
- the old dependency check of a child commission (`prepare_dependency_request`) raises from `msg_to_child` while the commission is built (a wrong commission fails); the target list comes from the latest delivered observation's dependencies, not from a provider read before the first observation (no scope is in the assignment).
- the episode's only child slot names its own binding path (self-commission); the job lists no child folder.

## Not repaired

- decide, action, internal_summary and final_to_parent have no test: driving them needs a model or the job_access service (BLOCKED-ON-JOB-SERVICE), and a hand-built view or scripted answer would be a fake. credit is tested on a plain summary with no received progress (run rp_a107_04_u151_1, 8 passed).
- BLOCKED-ON-JOB-SERVICE job_access observe_progress / describe_progress_target / read_progress for baseline snapshots, and BLOCKED-ON-STORE-ACCESS for progress_log and _delivered: system limits, not repaired.
