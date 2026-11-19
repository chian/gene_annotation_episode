# execution_job_submission (A110, head child): blocked, unplaced and contract misfits

Episode: `gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/execution_job_submission`. Job episode: a parent that commissions the two launching route children `local_job_execution` (slot `launch_local`) and `hpc_job_execution` (slot `launch_hpc`); it submits nothing itself. Old source was read with `git --git-dir=/home/chia/repos/gene_annotation_episode_disk/.git show 97308b94c:<path>` (the working checkout has no git history). Importing `episode.py` passes the class-definition checks; `tests/test_episode.py` passes (11 tests). The old folder had no tests; the retired-tests file holds only its header.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `estimate_table` (declared in `task.py` `SERVICES = ('estimate_table',)`); wanted call: `ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')` in `task.py decide` (the old `execution_expectations('launch')` and `resource_tool_estimates`: the timing information of earlier runs shown to the model). No estimate table exists (MECHANICS "Not provided yet"); the run's `services` collaborator needs a factory for it, and `decide` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` where the service has no such member.
- The episode submits, checks and fetches nothing itself: no `job_access` call and no job record kind. The children carry those (their own blocked files).

## BLOCKED-ON-STORE-ACCESS

- None. The episode calls no library function that touches the Store; `credit.py` reads the summary only. Called library functions (none touches the Store): `validate_assignment`, `validate_schema`, `TerminalExecution(config).validate_assignment`, `LaunchInstructions`, `ToolKnowledge`, `rejection_feedback`, `extend_context`, `time_accounting`, `yield_table`.

## Unplaced old functions

- `input_versions.py LaunchInputVersions` (`_versions`, `_flux_balance_inputs`): Store-backed validation of `immutable_input_versions` through the old `execution_input_versions` module (no placed home) and the flux balance input binding. The versions travel unchanged in the assignment (shape checked with `INPUT_VERSION_SCHEMA`), the input records as the `record_refs` field.
- `received_result_records.py native_result_operation_catalog`: result-side operations; they belong to `execution_result_acquisition`.
- `resource_information.py LaunchResourceInformation.resource_tool_contracts`: commissionable launch/results operation contracts per resource, including the native flux balance contracts (no placed home). The model is shown the resource configuration and inventory (`execution_capabilities`) and the permitted resource ids.
- `presentation.py present_context`: the per-context prompt renderers lived in the old shared root (README 5 item 16); `task.py _task_text` is the episode's own text.
- Decision inputs of `task_decision.py LaunchTaskDecision.call` with no home: `resource_context`, `shared_information_context`, `child_options`, `completed_action_reports`, `requested_action_history`, `native_execution_expectations`, `pending_work`.
- `configuration.py LaunchConfiguration`: not carried are `results_yield_profiles`, `log_window_bytes`, `log_roles` (result-side), `require_private_yield`, the native flux balance configuration check and the per-resource `TerminalExecutionBehavior` delegates (the children carry their own).
- `from_parent.py prepare_assignment` (partly): `authenticate_launch` (reads the planner parent's ledger, README 5 item 14), the compact flux balance launch preview, the flux balance inputs / input versions in scope: checks of a commission, a wrong commission fails (rule 1); none carried.

## Contract misfits

- new field: execution_job_submission handoff_unit; new field: execution_job_submission acquired_record_unit (read from configuration in the old code; `credit` has no settings); new field: execution_job_submission record_refs (the records the job inputs name); new field: execution_job_submission received_handoff_resources (resources that already had a usable handoff: the old initial known handoff records); new field: execution_job_submission scientific_task (optional; the old `services.scientific_parent_task`). The commissioning parent (`biochemical_feasibility_evidence`) must fill them. The old assignment's `launch_instructions` and the other old properties keep their names.
- `execution_handoff_refs` is a required field of `RETURN_FORM` (the old `required_return_sources` required it only when the parent is the A110 head and an annotation task is required; a form has no condition). A parent cannot select it (`selection_not_a_selectable_field`): it is always returned. `execution_completed` and the empty result sources stay selectable.
- Usable handoff: the old credit asked the job progress provider (`targets.usable_handoff(target)`) about each received handoff record. There is no counterpart in the custody API and `credit` has no services; a launch child returns `execution_handoff_refs` only for a returnable handoff of its exact assignment, and credit counts a resource when its child's report says completed with handoff references. Weaker than the old per-record provider test.
- `execution_result_origin` was `null` when no result window exists and a form has no null: declared as a `record`, selecting it raises `NotImplementedError('no_null_form_type:execution_result_origin')`.
- The native flux balance fact sources (`fba_fact_sources()`) have no placed home: not declared.
- `validate_report`: the old body called the axis `validate_form(form, original_schema, resolver)`; A110 has none. The fact-agreement comparison runs and then `final_to_parent` raises `NotImplementedError('validate_form_not_built:biochemical_feasibility')`: every return of this episode raises until A110 gets one.
- Controller (README 7b): the old `BoundedYieldController` becomes `BoundedQualityYieldController` (maximum = `handoff_unit` times the eligible requests without a handoff at the start, from `read_from_parent`). No completion-target case: credit is `handoff_unit` times distinct permitted resources, at most the maximum, so no "completion credit may pass its target". When no eligible request remains, maximum and cost are 0 and a nonzero initial credit raises (the old rule); the old exact-zero estimator and `PracticalYieldEstimator(verify_completion)` are not carried.
- Reconstructed without the unread shared root: the resource keys shown by `execution_capabilities` (`workspace, policy, account, ssh_argv, python_executable, scheduler`), the profile key `launch:` + sorted eligible classes joined by `+` (from `_launch_yield_controller`), the child-kind slot table (the old `ROLE_KINDS`).
- The old reasoning-commit, wait and `redeliver_report` actions are not offered. The model answers one `slot` and `resource_id`.
- `ctx.settings` must hold `resources` (kinds `local` / `pbs_ssh`), `coordinator_workspace`, `task_yield_profiles` (`{'launch:<classes>': {'cutoff': cost, 'parameters': ...}}`) and optionally `initial_information`, `launch_instructions_directory`, `tool_knowledge_directory`. The units need a cost above zero.
- The HPC child's `ASSIGNMENT_FORM` has no `record_refs` or `scientific_task` field, so `msg_to_child` does not send them to it; the local child takes both.
- The old hook-era `episode.py` and `submission_source.py` (`JobSubmissionBinding`) were deleted. Other axes' docstrings and `a104/.../runtime_bindings.py` still name an `execution_job_submission.submission_source` of their own axis folders; that is not this folder.
- The child forms are imported by `tests/test_episode.py` only, to admit the commissions against the real forms; no non-test module imports them.

## Not repaired

- Tests of `internal_summary`, `execution_capabilities` and `decide`: each needs a real view or ctx (system classes made by the runner); a hand-built one would be a fake, and a runner test cannot pass `decide` while `estimate_table` is BLOCKED-ON-JOB-SERVICE. Not tested.
- The test of each commission against the child's real ASSIGNMENT_FORM was removed: it imported another episode folder. The commission is checked only as a ChildMessage on its slot.
