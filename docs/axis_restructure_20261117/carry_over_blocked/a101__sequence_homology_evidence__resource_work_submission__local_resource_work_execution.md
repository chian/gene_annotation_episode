# Carry-over report: a101/sequence_homology_evidence/resource_work_submission/local_resource_work_execution

## BLOCKED-ON-STORE-ACCESS

None. The only Store call is `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)` (task.py `reason`), which
custody offers. Every library function called (`jobs/waiting.py::selected_wait`, `instructions/*`, `model_exchange/*`,
`records/hpc/resource_records.py`, `records/progress_views.py`, `forms/sequence_homology_evidence/communication.py`)
takes values, not the Store.

## Unplaced old functions

- `from_parent.py` `OperationalAssignment._require_launch_child_instruction_pins` and the parent-equality loop of
  `prepare_assignment` (`resource_assignment_conflict`, `launch_instruction_inheritance_conflict`,
  `resource_selection_conflict` against the parent's selection): they check a commission against the parent's own
  assignment, which the child never sees. Not carried (rule 1: no check of a commission).
- `prepare_assignment`'s call `adapter.prepare_assignment(parent, 'launch_local', selected, scope, operation_key)`
  (adds `adapter_assignment`): the adapter is now the service `resources`, which receives the admitted assignment on
  every call. No place for the adapter's preparation of an assignment.
- `to_parent.py` `resolve` (report-reference resolution by `reference_in_context` or the adapter): the adapter checks
  the interpretation in the `report` tool (`service.validate_report`); no resolver exists.
- `task.py` `apply_response`: `validate_form(report_update, interpret_schema, resolver)` against the parent-defined
  interpretation schema: the parent writes no form now; the interpretation is one `record` field.
- `decision_inputs` pieces with no service or library function to read them from: `native_event_targets`,
  `native_execution_expectations`, `waiting_support`, `execution_expectations`, `job_execution_options`,
  `completed_action_reports`/`requested_action_history` (HPC contexts only), `visual_evidence` (image.view pixels;
  this episode has no image tool), `shared_information_context`, `resource_context` other than the capabilities and
  estimates the `resources` service gives. They are not shown to the model.

## Contract misfits

- new field: local_resource_work_execution `scope` and `initial_report` are read from the commission's `message`
  (the old request message carried them), because the message has no form and the old assignment schema has neither.
  A missing `scope` raises `KeyError` in `read_from_parent`. The old `job_assignment` and `report_contract` message
  fields are not read (no parent-defined report schema exists now).
- new field: local_resource_work_execution `adapter_facts` (RETURN_FORM, selectable): the old adapter-declared fact
  sources (`adapter.fact_sources('launch_local')`) have names the episode cannot know, and a form has fixed fields;
  they travel together in one record keyed by the adapter's names.
- new field: local_resource_work_execution `interpretation` (RETURN_FORM, selectable): the old model-written
  `report_update`; recorded by the new `report` tool.
- The form has no null type: `execution_handoff` (null for zero or several identities) is a list of zero or one
  handoff; `launch_instructions` (null allowed) is an optional assignment field; `allocation` and
  `immutable_input_versions` are untyped `record`/`list` fields because their members hold nulls.
- Handoffs are values (a `list` field), not records in custody: the job-record library (handoff, check, closure) does
  not exist yet (README section 5 item 22). They reach the parent in the result.
- Resource adapters, native event ledger and run-frozen instruction libraries are services named in
  `task.SERVICES` (`resources`, `native_events`, `instruction_libraries`) with the members listed in the `task.py`
  docstring. None exists yet; the old adapter methods took a `BindingContext`, the service takes the plain assignment.
  `credit_view(assignment)` is asked without the old `receiver_selection` (the parent's report selection is not known
  to the episode before `final_to_parent`).
- Credit is the `credit_view` a resource tool returned last; the credit definition itself was never in these files
  (`services.bound_role_credit`) and stays the service's. Credit before any unit is 0.0.
- Controller: `AccumulationYieldController` (README 7b), because the old assignment names no target or maximum; the
  intent record observes a definite end (a usable handoff) that would fit a completion controller, but there is
  no target field in the old assignment to take it from. Its `cost` and `parameters` come from the run's settings.
- The intent record notes the old `permitted_common_actions` listed `child` and `redeliver_report` for an episode
  with no children: neither is offered. `wait` is a tool unit (`jobs/waiting.py::selected_wait`); it earns nothing
  (it returns no credit view).
- Facts reach the result only as of the last unit that asked the service for them (`_observed`); the old code asked
  the adapter again at closure, which `final_to_parent` cannot (no services).
- `resource_tool` catches `sqlite3.Error` from `check_handoff` as the old `execute` did; this is the adapter's error
  type, not a Store access (a sweep hit for `sqlite3`, not a finding).
- `internal_summary` reads `view.controller_state.as_record()` and `view.records.reasoning_schema()`; neither was run
  through the real runner in this step (no real resource service exists to run it with, and no fake is written).

## Not repaired

- library import of the private names `_validate` and `obj` from episode_support/records/hpc/resource_records.py: the library may not be edited or renamed in this step; the import works and the library function is the only place of this schema validation (pattern: "library not carried" style point).
- `adapter.prepare_assignment`, the report-reference resolver and the decision-input pieces native_event_targets, native_execution_expectations, waiting_support, execution_expectations, job_execution_options, completed_action_reports/requested_action_history, visual_evidence, shared_information_context have no service or library place; they stay unplaced.
- Real-runner tests of decide/action/tools/final_to_parent: the resources, native_events and instruction_libraries services do not exist and fakes are forbidden.
