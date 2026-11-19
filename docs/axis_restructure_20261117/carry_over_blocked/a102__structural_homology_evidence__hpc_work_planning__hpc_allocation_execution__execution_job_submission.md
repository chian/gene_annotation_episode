# execution_job_submission (A102): blocked, unplaced and contract misfits

Episode: `gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission`. Job episode (a parent that commissions the launching route children `api_job_execution`, `local_job_execution`, `hpc_job_execution`; it submits nothing itself).

No old source was readable: the checkout has no git history (`git show 97308b94c:<path>` fails: "not a git repository"), so every file was written from the episode intent record, the call table, the function list and the finished files of the three children. The folder's `tests/` held only `__init__.py`, so `retired_tests/<episode>.tsv` has only its header.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `estimate_table` (declared in `task.py` `SERVICES = ('estimate_table',)`); wanted call: `ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')` in `task.py decide` (the old execution expectations of role `launch`, timing information of earlier runs, shown to the model). No estimate table exists (MECHANICS "Not provided yet" item 2); the run's `services` collaborator needs a factory for it (`LinkError('service_required:...')` otherwise), so `decide` cannot run until it exists.
- The episode itself submits, checks and fetches nothing: no `job_access` call and no job record kind. The children carry those (their own blocked files).

## BLOCKED-ON-STORE-ACCESS

- None. The episode calls no library function that touches the Store; `credit.py` uses `records.holds`.

## Unplaced old functions

See the "unplaced" rows of the Carried over table (all in the intent record):

- `execution_contracts.py native_result_operation_catalog`, `_outcome`; `execution_state.py LaunchExecutionState._result_directory`; `result_selection.py` `_target`, `_selector`, `_windows`; `retained_protein_reader.py` (class and three methods); `retained_result_publication.py` (class and two methods): results-side code carried in the launch copy; it belongs to `execution_result_acquisition`.
- `terminal_execution.py` (`operation_catalog`, `TerminalExecutionBehavior` and its methods except `validate_report`): terminal behaviour of the `launch_local`/`launch_hpc` children, carried by those children.
- `parent_input_custody.py LaunchParentInputCustody._versions`: validation of `immutable_input_versions` through the old `execution_input_versions` module (no placed home; reads the Store). The versions travel unchanged in the assignment.
- `parent_input_custody.py LaunchParentInputCustody._launch`: `authenticate_launch` (under an HPC parent the launch must be the exact launch assignment of one frozen plan in the owner's ledger, one reservation per plan): it reads the parent's ledger (README 5 item 14); a wrong commission fails (rule 1), no check is carried.
- `parent_input_custody.py LaunchParentInputCustody._validate_request` (partly): validation of an API request by the API provider (`api_service_execution`, no placed home), of native protein-structure job inputs (`protein_structure_operands`, Store reads) and of the request workspace against the resource's configured workspace (settings are not handed to `read_from_parent`). Practical requests are checked by the library `validate_assignment`.
- `resource_information.py LaunchResourceInformation.resource_tool_contracts`: commissionable launch/results operation contracts per resource (API operation catalog: no placed home; local protein-structure contracts: `tools/protein_structure/native_protein_structure_tool_info.py::protein_structure_tool_contracts`, needs the configured bindings). The model is shown the resources' configuration and inventory (`execution_capabilities`) and the permitted resource ids.
- Context pieces of `decision_inputs.py` with no home here: the shared-information context, `requested_action_history` (an HPC context), `available_child_roles`/`job_episode_options` (the parent's own text lists its slots), `pending_work` and `waiting_support` (no pending children, no wait), `native_estimation_context`. The old selected-execution prompt renderer (`structural_homology_evidence_prompt`) lived in the shared root and is not read: the selected execution task is sent as a context field.

## Contract misfits

- new field: execution_job_submission scope; new field: execution_job_submission input_refs (record_refs); new field: execution_job_submission handoff_unit (the old code read it from its configuration; `credit` has no settings and the yield controller reads only the parent input); new field: execution_job_submission already_handed_off; new field: execution_job_submission scientific_task (optional; the old `services.scientific_parent_task` callback); new field: execution_job_submission hpc_execution_job (optional; handed to the old code at its first decision).
- new field: execution_job_submission execution_handoff_artifact_refs (return, selectable record_refs): the artifacts the handoff records name (the local child returns `practical_receipt_artifact_refs`); a pass carries only the records named.
- new field: execution_job_submission finding (return; the old report was the parent's JSON-Schema form with fact sources): `FINDING_FORM` has `requested_resource_ids`, `already_handed_off`, `handed_off`, `handoff_complete`, `qualification`.
- `execution_result_origin` was `null` when no result window exists and a form has no null: declared as a `record`, returned as `{}`.
- The old `validate_report` is carried as the fact-agreement check; the intent record does not say it called `validate_form` (the row for `to_parent.py` lists no `validate_form`, `task.py` does), so no `NotImplementedError('validate_form_not_built:A102')` is raised. If the unreadable old body did call it, that call is missing.
- Reconstructed from the intent record because the old bodies were unreadable: `permitted` (constraint keys `allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind`), `request_yield_class` (API: `api_<service>[_<algorithm>][_<database>]_handoff`; practical; `compact_<version>` is not produced, the version is `compact_<version>` only for a request that is neither) and the profile key `launch:` + the sorted distinct classes of the eligible requests joined by `+` (the order and de-duplication of the old key are not recorded).
- Choice of controller (README 7b): the old `BoundedYieldController` becomes `BoundedQualityYieldController` with maximum `handoff_unit` times the eligible requests not handed off at the start (`read_from_parent`). The old completion estimator (`practical_estimator`, proof `practical_completion_v1`) is not a controller input (README 5 item 5) and is not carried. When no eligible request remains the maximum is zero: the controller's own checks decide (the old rule "any non-zero credit is an error"). No "completion credit may pass its target" case: credit is `handoff_unit` times distinct resources that are eligible and not handed off, which is at most the maximum.
- The old reasoning-commit action (`reason`, with the `empty_reasoning_commit` refusal) and the wait and `redeliver_report` actions are not offered: the binding path is fixed under the HPC work-planning ancestors, where the old action policy offered tool, child and `redeliver_report` only; `redeliver_report` and `wait` no longer exist.
- The model's selection is one enum (`execution_capabilities` or `commission:<resource_id>`); the old selection wrapper with `report_update` and the strict transport (`strict_output_schema`) are not used: the schema is already a flat closed object.
- `msg_to_child` passes `launch_instructions` as the selection, not materialised (it has no library directory; each child materialises it from its own library). The old report-contract declaration and receipt inheritance are not carried (child's own return form; system custody). `message['initial_report']` is the text `nothing yet` (the api child's form requires it; the old initial report values are not recorded).
- `ctx.settings` of this episode must hold `resources` (resource id -> configuration), `initial_information` (resource id -> recorded inventory), `task_yield_profiles` (`{'launch:<classes>': {'cutoff': cost, 'parameters': ...}}`) and optional `launch_instruction_directory`. `decide` reads the launch instruction library from disk (not a recorded service read), as the local child does.
- The three children's assignment forms differ: the hpc child's form has no `scope` or `input_refs` field, so `msg_to_child` does not send them to it (the hpc child cannot read the subject scope or the job's input records); the api child's `request` field is the whole request record; the local child additionally takes `scientific_task`. Admission of each commission by the child's real form is tested.

## Not repaired

- `old_source_not_read`: the old bodies (permitted, request_yield_class, the `launch:` profile key, validate_report, decide/action) were reconstructed from the intent record and calls table; the repair step did not re-derive them from `git show 97308b94c`. Not a code defect found; left as carried.
- BLOCKED-ON-JOB-SERVICE `estimate_table`: unchanged (see above); a run cannot link or decide until the service exists.
- The unplaced old functions listed above stay unplaced (other episodes' code, or the operations they need do not exist).
