# execution_job_submission (A106, under published_evidence_assessment): blocked, unplaced and contract misfits

Old tests at 97308b94c: only `tests/__init__.py`; nothing retired (the retired_tests file holds its header only).
Tests written: `tests/test_execution_job_submission_binding.py` (6 real tests: class-definition import check, ten-file
set, no import of another episode folder, assignment/return forms, commission, selection schema through the A106
transport). No test runs the runner: the episode declares the `job_access` service and the run has no factory for it.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (the run's job-access service for API resources); wanted call:
  `ctx.services['job_access'].api_capabilities(resource_id)` in tool `execution_capabilities`, and
  `ctx.services['job_access'].read('api_capabilities', resource_id)` (a recorded read) in `decide`. Reply wanted:
  `{'availability': ..., 'tool_names': [...]}` (old `OperationalOperations.capabilities`: availability `unknown`,
  tool names of `api_execution.capabilities(resource_id)`, no probe). The old `APIServiceExecution` lived in the old
  shared root and has no copy in `episode_support/`. Linking a run of this episode raises
  `LinkError('service_required:...')` until a factory for `job_access` exists. This episode submits nothing itself;
  the submission is its child's.
- BLOCKED-ON-JOB-SERVICE: `api_execution.assignment_schema(resource_id)` / `api_execution.validate_assignment(...)`
  (the concrete closed request schema per bound resource, old `_request_schema`, `_validate_request`, `_launch`) is
  not in the library; `read_from_parent.validate_request` checks the envelope with the library's
  `validate_api_assignment` (`request` is an open record) and the identity of the resource.
- BLOCKED-ON-JOB-SERVICE: job record kind (handoff record). No work table declares the handoff; this episode writes
  no job record. It receives the child's handoff references in `execution_handoff_refs` and treats a resource as
  handed off when the child returned non-empty references that this episode holds (`records.holds`). The old
  `usable_handoff(target)` of the progress provider (read the handoff record, test it) has no replacement; wanted:
  `records.table(JOB_LEDGER).select({'job': handle, 'event': 'handoff'})` to read the handoff row and test its
  usability. Not invented.

## BLOCKED-ON-STORE-ACCESS

- Nothing in this episode calls a library function that touches a raw `Store`. The library calls it makes take values
  or a directory (`validate_api_assignment`, `validate_selection`, `application_fact_sources`, `yield_table`,
  `time_accounting`, `rejection_feedback`, `extend_context`, `ToolKnowledge`, `LaunchInstructions`,
  `generation_schema`/`decode_response` of the A106 action transport, `validate_schema`). Its Store uses go through
  custody: `ctx.store.holds`, `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)` in the `reason` tool,
  `records.holds` in `credit`, `view.records.reasoning_schema()` in `internal_summary`.
- Not called: `records/perturbation_evidence/held_inputs.py` (`HeldInputs`, `read_receipt`): the API job execution
  child assembles operands, not this episode.

## UNPLACED OLD FUNCTIONS

- `decision_inputs.py decision_inputs` context pieces without a home here: `resource_context`,
  `shared_information_context`, `completed_action_reports`, `pending_work`, `execution_expectations`,
  `resource_tool_estimates`, `native_execution_expectations`, `waiting_support`, the contract-information profile
  (wait/exchange/estimator context of the old runner; no library function holds them). The launch instruction
  library, the selected launch instructions, tool knowledge, the credit binding and the child options are carried.
- `execution_state.py _check_parent_inputs`, `initialize`, `from_parent.py _launch` scope checks, `_permitted` against
  the run's configured resources, `native_input_custody.py _versions` (the immutable-input-version re-validation
  against the Store): checks of the commission against the parent's own launch assignment and the Store (a wrong
  commission fails, no check). The bound-resource test is `task.action`'s `checked_resources` (raises
  `execution_resource_not_bound`).
- `native_input_custody.py` (all rows) and `execution_state.py _target`, `_context_target`: results-role target,
  retained-input authority and native input-version functions (protein, ATAC, MACS2, LUMPY, NMF, fluorescence, flux
  balance). `execution_input_versions` and the `retained_input_authority` hosts are old-shared-root modules; this
  launch role reaches none of them on its API route.
- `to_parent.py _application_facts`, `_application_resolve_*`, `resolve`: read saved adapter results of the results
  role and resolve report references (custody is the system's). A launch acquires no results.
- The old `validate_form(form, schema, resolver)` call of `validate_report` (A106's `validate_form`) has no object:
  the parent-written JSON-Schema form with `x-source` fields no longer exists (rule 5). The fact-agreement part is
  carried in `final_to_parent.validate_report`.
- `task.py` branches: the model's `wait` (`_execute_selected_wait`, `waiting.py`) and `redeliver_report` actions,
  `pending_work_after_action`, automatic score updates, `retain_shared_grading_results`: wait/redelivery machinery or
  old-runner bookkeeping, not carried.

## CONTRACT MISFITS

- new field: execution_job_submission scope (assignment, `record`). The old context scope; the typed reasoning commit
  (`commit_reasoning(payload, scope, ...)`) names it. Not sent to the child (its form has no scope).
- new field: execution_job_submission input_refs (assignment, `record_refs`, optional). The records the requests name
  and the reasoning commit reads; passed on to the child in its `input_refs` (a pass carries only the records named).
- new field: execution_job_submission handoff_unit (assignment, number). The old `configuration.handoff_unit`: the
  credit needs it and `credit` has no settings; also the child's `completion_target`.
- new field: execution_job_submission already_handed_off_resource_ids (assignment, list, optional). The old
  `initial_known_record_refs` baseline: resources that already had a usable handoff earn nothing again.
- new field: execution_job_submission finding (return). Declared form: `commissions` (resource_id, slot,
  handoff_established, completed), `handoff_resource_ids`, `new_handoff_count`, `qualification`. The old report had
  none. (This is not an A105/A108 evidence episode: no investigation_finding or grading sheet applies.)
- Return fields: `execution_handoff_refs`, `execution_result_refs`, `execution_completed`,
  `bvbrc_appservice_support_refs` and `bvbrc_application_outcomes` are all selectable (old: fact sources the
  parent's report contract chose; `required_return_sources` made `execution_handoff_refs` required for a scientific
  parent: the commissioner selects it). `execution_result_refs` and `bvbrc_application_outcomes` are always empty for
  a launch (the old live facts named neither). `bvbrc_application_outcomes` is a `list` field.
- The child declares `execution_handoff_refs` and `execution_completed` as required fields, so this episode cannot
  select them: its commission selects only `bvbrc_appservice_support_refs`.
- The child's form has no `immutable_input_versions` or `scope`: the old child re-checked the original launch's
  immutable input versions; that check cannot be commissioned and is not carried (see unplaced).
- The child's `yield_estimator.request_yield_class(parent_input)` reads `algorithm` and `database` at the top level
  of its assignment, which its form does not declare; the child's profile key is therefore always
  `launch_api:api_<service>_handoff` whatever the request contains (the parent's own key reads them from the request,
  as in the old code). A fact about the child, which is read-only here.
- `launch_instructions` of the assignment and of a request is `null` or a selection in the old schema; the assignment
  field is an optional `record` (no null); a request's `null` falls to the pinned selection of the assignment, and is
  omitted when neither exists.
- The old `exact-zero` yield estimator (nothing uncredited remains) is not carried (README 7b `no_remaining_requests`):
  a commission whose eligible resources all already have a handoff fails in `yield_estimator`
  (`launch_no_uncredited_original_request`); the old code raised `launch_no_uncredited_requests_but_nonzero_initial_credit`
  only for a non-zero initial credit and otherwise stopped at once.
- Credit cannot pass the bounded-quality maximum: credit is `handoff_unit` times the new resources handed off, the
  maximum is `handoff_unit` times the eligible resources not already handed off, and a commission goes only to an
  eligible resource, so no "completion credit may pass its target" case exists.
- `settings` (the `continuation` entry of this binding path): `task_yield_profiles` (`launch:<classes>` -> `cutoff` as
  the controller's cost, `parameters`), `resources` (resource_id -> `{kind: 'api', service, base_url}`),
  `initial_information`, `tool_knowledge_directory`, `launch_instructions_directory` (the last three optional). A
  cost above zero is needed for the bounded-quality controller to stop the Episode.
- `action` raises (not `Rejected`) for a permitted resource the settings do not bind: a configuration conflict.
- The slot keeps the old role name `launch_api` (the old `child_roles` returned `('launch_api',)`).
- The old `permitted_common_actions` offered `reason`; the `reason` tool commits through `ctx.store.commit_reasoning`
  and returns an invalid outcome for a named record the Episode does not hold. This episode holds only `input_refs`.
