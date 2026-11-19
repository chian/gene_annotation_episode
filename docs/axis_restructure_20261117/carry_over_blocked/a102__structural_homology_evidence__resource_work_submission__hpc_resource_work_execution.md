# Carry-over report: a102/structural_homology_evidence/resource_work_submission/hpc_resource_work_execution

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: `ctx.services['resource_adapter'].read(member, *arguments)` with member `capabilities`, `bound_resource_ids`, `catalog` (arguments: the assignment), `estimates` (arguments: the assignment) (task.py `read_adapter`, in `decide` and `action`; raises NotImplementedError).
- BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: `ctx.services['resource_adapter'].capabilities()` (task.py `resource_capabilities`, `resource_inspect`).
- BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: `ctx.services['resource_adapter'].bound_resource_ids()` (task.py `resource_inspect`).
- BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: `await ctx.services['resource_adapter'].check_handoff(assignment, handoff, key=ctx.operation_key, resumed=ctx.resumed)` (task.py `check_adapter_handoff`).
- BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: `await ctx.services['resource_adapter'].execute(assignment, tool_name, tool_arguments, key=ctx.operation_key, resumed=ctx.resumed)`, idempotent on the key (task.py `execute_adapter`).
- Not carried, same service: the adapter's `fact_sources(role)` / `facts(...)` (fields of the return form), `validate_report`, `resolve`, `received_form_references`, `prepare_assignment`, `credit_view`. Their names and shapes are unknown to the episode and a form has fixed fields.

## BLOCKED-ON-STORE-ACCESS

None. The only Store call is `ctx.store.artifact(text, 'application/json')` (task.py `record_reply`). Every library function called takes values, not the Store (`records/hpc/resource_records.py`, `instructions/*`, `model_exchange/*`, `records/progress_views.py`, `records/structural_homology_evidence/domain.py::plain`, `tools/tool_knowledge.py`).

## Unplaced old functions

- `from_parent.py` `_require_launch_child_instruction_pins` and the parent-equality loop of `prepare_assignment` (`resource_assignment_conflict`, `launch_instruction_inheritance_conflict`, `resource_selection_conflict` against the parent): they check a commission against the parent's assignment, which the child never sees; not carried (rule 1).
- `prepare_assignment`'s `adapter.prepare_assignment(...)` (adds `adapter_assignment`): the adapter is a service that receives the admitted assignment on every call.
- `action_contract_feedback` repairs (`closed_top_level_form_required`, `component_native_return_channels_required`, reads.map parameter feedback, `contract_error` details): they belong to report forms and tools this episode does not offer.
- `task.apply_response` report_update admission (`validate_form(report_update, interpret_schema, resolver)` with grain `launch_hpc`) and the `reason` branch (empty reasoning commit): the parent writes no form now; the launch assignment has no scope. A102 has no `validate_form` (`NotImplementedError('validate_form_not_built:structural_homology')` would be raised if it were called).
- `decision_inputs` pieces with no service or library function to read them from: `native_event_targets`, `native_execution_expectations`, `waiting_support`, `execution_expectations`, `job_episode_options`, `completed_action_reports`, `visual_evidence`, `shared_information_context`, `resource_context` beyond the adapter's capabilities and estimates, the annotation-axis-credit reduction. Not shown to the model.
- `to_parent.resolve`, `report_reference_access`, `received_messages`: report resolver and proof references (custody now).

## Contract misfits

- new field: hpc_resource_work_execution `input_refs` (ASSIGNMENT_FORM, `record_refs`): the records of the job's inputs, passed in custody; the old schema had no such field. The parent adds it in its `msg_to_child`.
- new field: hpc_resource_work_execution `handoff_refs` (RETURN_FORM, required `record_refs`): the artifact records of the handoff checks the tools wrote, returned in custody.
- RETURN_FORM has no null type: `execution_handoff` (old null for zero or several identities) is `{}`; `launch_instructions` (null allowed) is an optional assignment field; `allocation`, `immutable_input_versions` stay untyped `record` / `list` fields because their members hold nulls.
- The old model-written `report_update` (interpretation) is not carried: no field declares it; a parent that wants one would need a new field.
- Handoffs are values in the unit outcomes and returned as `list`/`record` fields, with their reply artifacts in custody; the job-record library (handoff, check, closure) does not exist (README section 5 item 22).
- A102 has no `communication` module: `ReportBoundaryError` and `plain` are not available for this axis. `validate_report` raises `ValueError('resource_handoff_fact_mismatch: ...')` and `plain` is the one of `records/structural_homology_evidence/domain.py`.
- The strict transport: A102 has no transport module; `strict_output_schema(..., open_records_as_text=True)` is used as in the carried A102 `hpc_job_execution` (the old shared transport's flag for this axis is not recorded anywhere).
- `check_handoff`'s `except sqlite3.Error` is not carried (no Store or SQLite access in the folder); the adapter's own error classes would be the service's.
- Credit is the count of distinct usable handoffs held (`len(summary['execution_handoffs'])`); the old credit definition (`services.bound_role_credit`) was never in these files. Credit before any unit is 0.0. Controller: `AccumulationYieldController` (README 7b), `cost` and `parameters` from the run's settings; the old assignment names no target or maximum.
- Facts reach the result as of the last unit that asked the service (the summary); the old code asked the adapter again at closure, which `final_to_parent` cannot.
- The intent record notes the old `permitted_common_actions` listed `child` and `redeliver_report` for an episode with no children: neither is offered. `wait` is not carried (no wait in the system; README section 5 item 18).
- `internal_summary` reads `view.controller_state` through `yield_table`; this was not run through the real runner in this step (no real resource service exists, and no fake is written).
- GOAL.md (`docs/axis_restructure_20261117/GOAL.md`) named as first reading does not exist in the repository.

## Not repaired

- BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted calls: read(capabilities|bound_resource_ids|catalog|estimates), capabilities(), bound_resource_ids(), check_handoff(...), execute(...). decide, action, selected_capability and the four tools raise where they reach the service; tests assert this (a real run of them cannot be done).
- Contract misfits: new fields input_refs (ASSIGNMENT_FORM) and handoff_refs (RETURN_FORM); no null type in forms; allocation and immutable_input_versions untyped.
- The yield controller reads settings only (README 7b inference), a design choice of the carry-over.
