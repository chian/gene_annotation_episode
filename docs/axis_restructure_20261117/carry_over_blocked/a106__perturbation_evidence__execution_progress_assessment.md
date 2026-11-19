# Blocked, unplaced and contract misfits: A106 execution_progress_assessment

Old source was read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`; the working tree at the repo root has no `.git`). The folder held only a hook-era `episode.py` (class on `A106MonitorRuntime`); it was deleted and the ten files written. The carried A102 monitor of the same shape was read for the file shape only; nothing imported.

## BLOCKED-ON-STORE-ACCESS
None. The episode writes nothing to the Store; the log tool reads through `ctx.store.holds/get/open_artifact`; the summary reads `view.records.get` of committed records.

## BLOCKED-ON-JOB-SERVICE
- `job_access`; wanted call: `ctx.services['job_access'].read('resolve', target_handle, scope, 'execution_handle')` (task.py `target_in_scope`, from `decide`; the old `reference_in_scope` check of the assignment).
- `job_access`; wanted call: `ctx.services['job_access'].read('describe_progress_target', target_handle, scope)` (task.py `describe_target`).
- `job_access`; wanted call: `ctx.services['job_access'].read('direct_dependencies', target_handle, scope)` (task.py `direct_dependencies`; used by `decide` and by `action` to refuse a child that is not an exposed direct dependency).
- `job_access`; wanted call: `await ctx.services['job_access'].observe_progress(target_handle, requested_fields, scope, permitted_committed_record_types=..., operation_key=ctx.operation_key)` (task.py `observe_target`, tool `progress_observe`; idempotent on the key, returns a `progress_snapshot_v1`; an unchanged observation keeps its original `progress_ref`).
- `job_access`; wanted call: `ctx.services['job_access'].read_progress(reference, scope)` (task.py `snapshot_read` and credit.py `SummaryProgress.read_progress`): only reached for a progress reference received without its snapshot.
- `estimate_table`; wanted call: `ctx.services['estimate_table'].read('execution_expectations', 'monitor')` (task.py `execution_expectations`; only when the setting `execution_expectations` is present).
- `native_events`: the native event ledger is not wrapped as a service; `wait_for_events` calls `selected_wait(ctx.services['native_events'], condition)` (library `jobs/waiting.py`), which fails at link without a factory.
- `native_observation_options(native_operation, context)` of the old shared root has no copy in the library: `progress_observe` with `native_operation` raises `NotImplementedError('native_observation_options_not_placed...')`.
Every one raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` where it is reached; the first decision of a real run fails there (tests/test_episode_binding.py asserts it through the real runner).

## unplaced_old_functions
None unplaced. Not carried as machinery (see the table in the intent record): `redeliver_report`, wait on pending in-process children, report_update model output, decision-exchange loop, checkpoint/restore, report delivery bookkeeping. Not carried because their inputs have no object in the new runner (old `decision_inputs`): `resource_context`, `completed_action_reports`, `pending_work`, `resource_estimator` and native execution expectations (estimates need the estimate table); the instruction paragraphs RESOURCE_ESTIMATE_GUIDANCE, REPORT_GUIDANCE, HISTORY/EXCHANGE_HISTORY, REPAIR, WAIT (pending children) describe them.

## contract_misfits
- new field: execution_progress_assessment information_unit (the old monitor took it from its run configuration; `credit(summary, records)` has no settings, so it is an assignment field; the commissioning parent must send it; this episode sends its own to its dependency monitor).
- new field: execution_progress_assessment known_progress_snapshots (optional record: the snapshots of `known_progress_refs` by reference; the old provider held them; credit and the summary have no provider, so the commissioner passes the snapshots it received).
- new field: execution_progress_assessment scope kept as an assignment `record` (the old scope came from the old request); it is passed to job_access calls and to the projector. The old check that it is Store-admitted (`store_scope`: `validate_scope`) is not made: it needs every subject held, and no subject is passed.
- new field: execution_progress_assessment monitoring_progress_snapshots (selectable return field: the delivered snapshots by reference); the self-nesting commission selects it with `monitoring_progress_refs`, so the parent's credit can read the child's observations. Any commissioning parent that counts child progress must select both.
- A form has no null: `monitoring_execution_state`, `monitoring_result_available`, `monitoring_observed_at_unix_seconds` are `record` fields holding `{'value': ...}` (null without an observation, as the old report returned null).
- `monitoring_progress_refs` is selectable, not required: the old parent `structural_homology_evidence` required it only when it had an annotation task; a form cannot express the condition, so that parent must select it.
- `monitoring_committed_record_refs` (record_refs) and the summary's committed records need the committed records of an observation to be held by the monitor (custody): records published by an execution owner through a service are in no receipt, so `view.records.get` / `ctx.store.get` raises `CustodyError` for them. Committed records of a job reach the monitor only if the job service writes them through custody or the parent passes them.
- `validate_form` of the axis (old `validate_report` first step): A106 has `forms/perturbation_evidence/communication.validate_form`, but it validated the form the parent wrote; the parent now selects fields and the system admits RETURN_FORM, so the step has no object and is not called.
- Self-nesting: the job names no child folder, but the old episode commissions a monitor of its own kind (slot `monitor` -> own binding path, allowed by the contract), so `msg_to_child.py` and `read_from_child.py` exist.
- The finding is the monitor's own typed finding (target, observed, execution_state, result_available, progress count, qualification): this is not an A105/A108 evidence episode.
- Credit may pass its target: not applicable (accumulation controller).
- `plain` is not exported by `records/perturbation_evidence/domain.py`; the episode imports it from `forms/perturbation_evidence/communication.py`. The strict output transport is `model_exchange/perturbation_evidence/action_transport.py` (`generation_schema`, `decode_response`).
- Monitor credit is read from snapshots the summary holds (`SummaryProgress`); library `grading/perturbation_evidence/progress_information_credit.py` is called with that reader (it is in a form taking a provider with `read_progress`; not edited).
- git: the repo root of this working tree has no `.git`; old files were read from the sibling checkout `/home/chia/repos/gene_annotation_episode_disk` at commit 97308b94c.
