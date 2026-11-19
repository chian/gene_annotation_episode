# execution_result_acquisition (A110, under hpc_work_planning): blocked, unplaced and contract misfits

Job episode (result acquisition, no children). Old files read with `git show 97308b94c:<path>` from `gene_annotation_episode_disk` (the checkout used for this step has no `.git`). Old tests: none existed (no `tests/` at 97308b94c), so the retired-tests file holds only its header.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: handoff job record (`execution_target_v1`, record kind not defined); wanted call: `ctx.store.get(handoff_ref)` read as the execution target, validated by `validate_target` and matched to the commissioned assignment (old `job_progress_provider.targets.read_target`, `_context_target`), or `ctx.services['job_access'].read_target(handoff_ref)`. `task.py _read_target` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` where it is reached.
- BLOCKED-ON-JOB-SERVICE: `job_access` (declared in `SERVICES`); wanted call: `ctx.services['job_access'].observe_target(target, key=ctx.operation_key)` returning the observation of the exact attempt (`state`, `returncode`, `observed_at`; old `targets.observe_target`). `task.py _observe_target` raises.
- BLOCKED-ON-JOB-SERVICE: `job_access`; wanted call: `ctx.services['job_access'].read_file(target, path=..., offset=..., limit=..., key=ctx.operation_key + ':file:' + str(index))` returning one window (`path`, `offset`, `returned_bytes`, `size_bytes`; old `targets.read_file`). `task.py _read_window` raises (a `ValueError` / `OSError` of the real call would be kept as a failure of the receipt, as before).
- BLOCKED-ON-JOB-SERVICE: `job_access`; wanted call (a recorded decision read): `ctx.services['job_access'].read('describe_result_target', summary['handoff_ref'], summary['selector'])` in `task.py decide` (old `targets.describe_target(handle, scope, selector=...)`). Called as written; a run without the service fails at link (`LinkError('service_required:...')`).
- BLOCKED-ON-JOB-SERVICE: `estimate_table` (not provided): the old resource and native estimates (`resource_estimator`, `execution_expectations` for `results`, `native_estimation_context`) of the decision inputs are not shown; wanted call `ctx.services['estimate_table'].read(...)`.
- Consequence: no tool of this episode can complete today, so no real run of the episode through the runner exists (only the pure functions are tested).

## BLOCKED-ON-STORE-ACCESS

- None for the native path. `_publish_result` writes with `ctx.store.artifact` and `ctx.store.put('source', ..., origin='tool')` (custody-aware). Old `_publish_result` / receipt bodies `store.db` reads of `runtime_actions` are machinery. Library functions called: `forms/biochemical_feasibility_evidence/execution_contracts.py::canonical, checked, digest, obj` (pure, no Store).

## UNPLACED OLD FUNCTIONS

- `completion.py` completion proof and re-validation (`_proof_for_action`, `completion_for_action`, `_closed_completion_verdict`, `verify_completion`): a completion proof is not a controller input; the endpoint is the credit reaching its maximum (see misfits).
- `from_parent.py` / `result_state.py` / `work_operations.py` / `credit.py` / `to_parent.py` / `internal_summary.py` branches for typed selectors: `LocalFileSourceResults` (`local_file_source_selector_v1`; library `records/local_execution/local_file_capture_results.py` is still in the old binding form and takes the binding) and `NativeFluxBalanceResults` / `FluxBalanceReturns` / `FluxBalanceRequestBindings` / `FluxBalanceExecutionInputs` (`flux_balance_result_selector_v1`, compact FBA assignments, `selected_execution_task`, `fba_fact_sources`): no carried home exists; a typed selector raises `NotImplementedError` in `messages/read_from_parent.py selector_windows`.
- `from_parent.py` `RESULTS_SCHEMA` (library `execution_result_contract`) and `received_result_readers` (`_target`, `_selector`, `_windows`, `_validate_request`, `_validate_result_body`, `_read_result`, `_selection`, `_selected_result_action`, `_result_directory`, `fact_sources`, `resolve`): not in `episode_support/` (they were in the old shared root, not read). `selector_windows` is rebuilt from the native selector schema; the assignment fields come from the intent record; the validation of the selector against the handoff target and the validation of a result body are not carried; `resolve` (reference resolution of the report) is not carried.
- `initial_information.py`, `resource_information.py`, `received_execution_information.py` readers (`execution_initial_information`, `execution_operation_information`, `execution_resource_information`): not in `episode_support/`; replaced by the recorded `describe_result_target` read.
- `presentation.py present_results_context` (renderers `hpc_prompt`, `monitor_prompt`, `receiver_prompt`, `scientific_decision_presentation`, `task_decision.present_*`): not in `episode_support/`; the context travels as JSON.
- `target_custody.py` (handoff target matches the assignment) and `input_versions.py`: need the handoff target / FBA inputs (BLOCKED-ON-JOB-SERVICE, above).
- `terminal_execution.py TerminalExecutionBehavior`, `received_launch_requests.py`, launch yield controllers: copies of the shared execution binding, not used by the results role.
- `internal_summary.py _with_selected_execution_task` and the model-facing `local_outcome_preview`: the preview is a plain shape of the last outcome in `messages/internal_summary.py _preview`.
- Tool-knowledge and launch-instruction `INSTRUCTIONS` texts, the delivery-repair paragraph and the exchange-history replacement (`task_instructions.py`): they describe lookup tools and actions this episode does not offer; the library contexts are shown when the settings name their directories.

## CONTRACT MISFITS

- BLOCKED-ON-JOB-SERVICE: job_access; wanted call: `ctx.services['job_access'].observe_target(target, key=ctx.operation_key)` (and the handoff read and window read above).
- validate_form_not_built:A110: the axis has no validate_form; `validate_report` in `messages/final_to_parent.py` now does the fact comparison only and returns (the former trailing raise was removed so the Episode can return).
- new field: execution_result_acquisition resource_kind (assignment: the old binding read it from the handoff target; the yield profile key and the controller kind need it from `parent_input`).
- new field: execution_result_acquisition acquired_record_unit (assignment: the old binding took it from its configuration; `credit` has no settings).
- new field: execution_result_acquisition version (assignment, declared `execution_results_assignment_v1`: the old schema's version).
- new field: execution_result_acquisition execution_result_artifact_refs (return, required: the artifacts of the returned result Sources; a Source passed alone does not bring its artifact, decision T5).
- `handoff_ref` is an old single reference; in the form it is a `record_refs` field that must hold exactly one record (`read_from_parent` raises otherwise).
- `constraints` is optional in the form (the old code read `assignment.get('constraints', {})`); the old `RESULTS_SCHEMA` itself was not available, so the field list is taken from the intent record and the old uses.
- tool names: old `execution.results.status`, `.collect`, `.read` are `execution_results_status`, `execution_results_collect`, `execution_results_read` (a tool name matches `[a-z][a-z0-9_]*`).
- `execution_result_origin` was `null` without a received window; a form has no null: it is a `record` field and selecting it without a window raises.
- the old `handoff_unit * 0` credit term is dropped (always zero); the positions already in the initial refs are none.
- the old per-resource `results_yield_profiles` / `task_yield_profiles` (configuration) are read from `settings` under the old profile keys (`native_unbounded_<kind>`, `results:native_finite_<kind>`); `log_window_bytes` is a setting; `log_roles` was only used by the progress provider and is not carried.
- finite selector: the old estimator was bounded credit yield and, once a verified completion proof was supplied, the practical completion estimator. Only one controller can be built: bounded quality with the maximum `acquired_record_unit * (1 - original fraction)`. The credit reaches that maximum when every requested byte position is received; the old completion proof also required a completed, return-code-0 attempt observation, so the stop and the verified endpoint can differ (`execution_completed` in the report still carries the old verdict). Typed selectors would have been completion with a target; not carried (unplaced).
- completion credit may pass its target: not applicable (bounded quality); the credit cannot pass the maximum because the union of windows within a finite span is at most the span.
- unbounded selector: accumulation; the settings must give the units a cost above zero (the profile `cutoff` is required positive), or the Episode never stops.
- the old refusal of a new acquisition after completion (read from `runtime_actions`) is the tool argument `already_completed` copied by `action` from the summary; the unit is still a unit (invalid outcome), as before.
- the receipt body no longer carries `scope` (no scope in the final form); it carries the parent input as `assignment`.

## Not repaired
- BLOCKED-ON-JOB-SERVICE: job_access reads (describe_result_target, read_target, observe_target, read_file) in task.py; system has no such service.
- Typed selectors (local_file_source_selector_v1, flux_balance_result_selector_v1) and flux balance fact sources: no carried home.
- Handoff target match to the assignment and result body validation: depend on the job service.
- Prompt renderers (present_results_context, task_instructions, hpc/monitor/receiver prompts): not in episode_support.
- Yield controller: BoundedQualityYieldController for finite selectors follows README 7b.
- Tests of action and internal_summary need a model answer or a system-built view; no fake is written.
