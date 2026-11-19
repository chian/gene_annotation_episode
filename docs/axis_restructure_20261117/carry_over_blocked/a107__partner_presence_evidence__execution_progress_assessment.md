# Blocked, unplaced and contract misfits: A107 execution_progress_assessment

Carried 19 November 2026. Old source was read with `git --git-dir=/home/chia/repos/gene_annotation_episode_disk/.git show 97308b94c:<path>` (the working tree has no `.git`). The folder held only a hook-era `episode.py` (inheriting `A107MonitorBinding`, `DescendantBinding`); it was deleted and the ten files written. The finished A102 monitor was read only for the shape of the form; nothing is imported from it. The A107 library names are used (`grading/partner_presence_evidence/progress_information_credit.py`, `jobs/service_calls/partner_presence_evidence/progress_provider.py`, `records/partner_presence_evidence/domain.py`, `forms/partner_presence_evidence/communication.py`).

## BLOCKED-ON-STORE-ACCESS
None. The episode writes nothing to the Store. `progress_log` reads through `ctx.store.holds/get/open_artifact`; `internal_summary` reads committed records through `view.records.get`. No library function is called that touches the Store.

## BLOCKED-ON-JOB-SERVICE
Each raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` where reached; the first decision of a real run fails there (tests/test_episode_binding.py asserts it through the real runner).
- `job_access`; wanted call: `ctx.services['job_access'].read('resolve', target_handle, scope, 'execution_handle')` (task.py `target_in_scope`, the old `reference_in_scope` of the assignment).
- `job_access`; wanted call: `ctx.services['job_access'].read('describe_progress_target', target_handle, scope)` (task.py `describe_target`).
- `job_access`; wanted call: `ctx.services['job_access'].read('direct_dependencies', target_handle, scope)` (task.py `direct_dependencies`, used by `decide` and by `action`).
- `job_access`; wanted call: `await ctx.services['job_access'].observe_progress(target_handle, requested_fields, scope, permitted_committed_record_types=..., operation_key=ctx.operation_key)` (task.py `observe_target`, tool `progress_observe`).
- `job_access`; wanted call: `ctx.services['job_access'].read_progress(reference, scope)` (task.py `snapshot_read`, credit.py `SummaryProgress.read_progress`): only for a progress reference received without its snapshot.
- `estimate_table`; wanted call: `ctx.services['estimate_table'].read('execution_expectations', 'monitor')` (task.py `execution_expectations`, only when the setting `execution_expectations` is present).
- `native_events`: the native event ledger is not wrapped as a service; `wait_for_events` calls library `jobs/waiting.py` `selected_wait(ctx.services['native_events'], condition)`, which fails at link without a factory.
- `native_observation_options(native_operation, context)` (old shared root `episode_bindings`) has no copy in the library: `progress_observe` with `native_operation` raises `NotImplementedError('native_observation_options_not_placed...')`.
- Job records: none are defined; progress snapshots travel in unit outcomes and the child's selectable return field, not in a job ledger.

## unplaced_old_functions
- `initial_information.py` `initial_information`: needs `library.execution_initial_information.presentation` (`resource_information`, `received_api_information`) of the old shared root, which has no module in `episode_support/`, and `catalog.readers` (old reader catalog). The model is not shown this information; nothing raises, it is simply absent.
- Not carried as machinery (see the table in the intent record): `redeliver_report`, the wait on pending in-process children, the `report_update` the model wrote, the decision-exchange loop, saved-exchange checks, checkpoint/restore, report delivery bookkeeping, provider conversation state. Not carried because their inputs have no object in the new runner: resource context, completed action reports, pending work, resource estimates and native execution expectations; the instruction paragraphs RESOURCE_ESTIMATE_GUIDANCE, REPORT_GUIDANCE, HISTORY/EXCHANGE_HISTORY, REPAIR and the pending-child WAIT text describe them.

## contract_misfits
- BLOCKED-ON-JOB-SERVICE: job_access and estimate_table and native_events (above); wanted calls as listed.
- new field: execution_progress_assessment information_unit (the old monitor took it from its run configuration; `credit(summary, records)` has no settings, so it is an assignment field the commissioning parent must send; this episode sends its own to its dependency monitor).
- new field: execution_progress_assessment known_progress_snapshots (optional record: the snapshots of `known_progress_refs` by reference; the old provider held them; credit and the summary have no provider, so the commissioner passes the snapshots it received).
- new field: execution_progress_assessment scope (assignment `record`; the old scope came from the old request). Its Store admission (`validate_scope`) is not made: it needs every subject held and none is passed.
- new field: execution_progress_assessment monitoring_progress_snapshots (selectable return field: the delivered snapshots by reference); the self-nesting commission selects it with `monitoring_progress_refs`. Any commissioning parent that counts child progress must select both.
- A form has no null: `monitoring_execution_state`, `monitoring_result_available`, `monitoring_observed_at_unix_seconds` are `record` fields holding `{'value': ...}` (null without an observation, as the old report returned null).
- `monitoring_*` fields are selectable, not required: the old parent `partner_presence_evidence` named its required sources in its own `to_child_execution_progress_assessment.py`; that parent must select what it needs.
- `monitoring_committed_record_refs` and the summary's committed records need the committed records of an observation to be held by the monitor (custody): records published by an execution owner through a service are in no receipt, so `view.records.get` / `ctx.store.get` raises `CustodyError` for them. They reach the monitor only if the job service writes them through custody or the parent passes them.
- `validate_form` of the axis (old `validate_report` first step): A107 has `forms/partner_presence_evidence/communication.validate_form`, but the parent writes no report form any more (it selects fields; the system admits RETURN_FORM), so it is not called. The rest of the old `validate_report` is `final_to_parent.validate_report`.
- Self-nesting: the job names no child folder, but the old episode commissions a monitor of its own kind (slot `monitor` -> own binding path, allowed by the contract), so `msg_to_child.py` and `read_from_child.py` exist.
- The finding is the monitor's own typed finding (target, observed, execution_state, result_available, progress count, qualification): not an A105/A108 evidence episode.
- `progress.log` reads the window with `ctx.store.open_artifact` (needs the window's source and artifact held) in place of the old `source.read` tool through `services.execute_tool`.
- Credit may pass its target: not applicable (accumulation controller; the old non-decrease rule is `credit.checked_increment`).
- GOAL/UNIT/RESULT are the texts of the earlier port of this binding (`episode.py`), the old `goal.py` having only instructions.
- git: the repo root of this working tree has no `.git`; old files were read from the sibling checkout `/home/chia/repos/gene_annotation_episode_disk` at commit 97308b94c.
