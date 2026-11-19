# Carry-over report: a101/sequence_homology_evidence/resource_result_acquisition

## BLOCKED-ON-STORE-ACCESS

None. The only Store call is `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)` (task.py `reason`), which
custody offers; `internal_summary` reads `view.records.reasoning_schema()`. Every library function called
(`jobs/waiting.py::selected_wait`, `instructions/*`, `model_exchange/*`, `records/hpc/resource_records.py`,
`records/progress_views.py`, `forms/sequence_homology_evidence/communication.py`) takes values, not the Store.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: service `resources` (the resource adapters of the old episode: capabilities, catalog, execute,
  facts, credit_view, validate_report, check_handoff); wanted call: `ctx.services['resources'].read('declared_capabilities')`,
  `.read('adapter_capabilities')`, `.read('catalog', assignment)`, `.read('decision_context', assignment)` in `decide` and
  `action`; `.execute(assignment, tool_name, arguments, ctx.operation_key)`, `.credit_view(assignment)`,
  `.facts(assignment)`, `.validate_report(assignment, interpretation)`, `.check_handoff(handoff, ctx.operation_key)`,
  `.declared_capabilities()`, `.adapter_capabilities()`, `.is_bound(resource_id)` in the tools. The service selects the
  adapter from `assignment['handoff']['resource_selection']['resource_id']` (for `check_handoff`: from the handoff given)
  and raises `resource_not_bound` when none is bound. No such service exists; the run fails at link
  (`LinkError('service_required:...')`) until the caller supplies it.
- BLOCKED-ON-JOB-SERVICE: service `native_events` (the `NativeEventLedger` of detached local jobs); wanted call:
  `selected_wait(ctx.services['native_events'], arguments['condition'])` in the `wait` tool.
- BLOCKED-ON-JOB-SERVICE: service `instruction_libraries` (run-frozen tool-knowledge and launch-instruction listings);
  wanted call: `ctx.services['instruction_libraries'].read('tool_knowledge')` and `.read('launch_instruction_library')` in
  `decide`.
- BLOCKED-ON-JOB-SERVICE: job-record library (handoff, check, closure as a declared work table; README section 5 item 22);
  wanted call: the acquisition tools would write the acquired results and a closure row with
  `ctx.store.table(JOB_LEDGER).put({...})` and return them in `record_refs` fields. No such table exists, so acquired
  results reach the parent only as values (`adapter_facts`, `execution_handoffs`), not as records in custody.

## Unplaced old functions

- `from_parent.py` `OperationalAssignment._permitted`: compared a capability with the assignment's constraints; the results
  assignment has neither `resource_selection` nor `constraints` (it is `version`, `handoff`, `requested_data_selector`), and
  the old results path never called it. Not carried.
- `from_parent.py` `OperationalAssignment._require_launch_child_instruction_pins`: checks a commission against the parent's
  own assignment, which the child never sees (rule 1: no check of a commission). Not carried.
- `from_parent.py` `prepare_assignment`: the launch-parent test (`resource_child_role_not_owned_by_launch`, a check of the
  commissioning parent's role) and the call `adapter.prepare_assignment(parent, 'results', selected, scope, operation_key)`
  (adds adapter data to the assignment): the adapter is the service `resources`, which receives the admitted assignment on
  every call. No place for the adapter's preparation of an assignment.
- `to_parent.py` `resolve` (report-reference resolution by `reference_in_context` or the adapter): the adapter checks the
  interpretation in the `report` tool (`service.validate_report`); no resolver exists.
- `task.py` `apply_response`: `validate_form(report_update, interpret_schema, resolver)` against the parent-defined
  interpretation schema: the parent writes no form now; the interpretation is one `record` field. (Axis A101 does have
  `validate_form`, but there is no schema to validate against.)
- `decision_inputs` pieces with no service or library function to read them from: `native_event_targets`,
  `native_execution_expectations`, `waiting_support`, `execution_expectations`, `job_execution_options`,
  `completed_action_reports`/`requested_action_history`, `visual_evidence`, `shared_information_context`,
  `resource_context` other than the capabilities and estimates the `resources` service gives. They are not shown to the model.
- `received_evidence.py` `received_form_references` (each handoff fact of a received form needs proof references from the
  adapter that owns it, `resource_information_handoff_proof_missing`): receipt checks are system custody (README 3b R3). No
  place; the proof references the adapter gave are not returned.

## Contract misfits

- new field: resource_result_acquisition `scope` and `initial_report` are read from the commission's `message` (the old
  request message carried them), because the message has no form and the old assignment schema has neither. A missing
  `scope` raises `KeyError` in `read_from_parent`. The old `job_assignment` and `report_contract` message fields are not
  read (no parent-defined report schema exists now).
- new field: resource_result_acquisition `adapter_facts` (RETURN_FORM, selectable): the old adapter-declared fact sources
  (`adapter.fact_sources('results')`) have names the episode cannot know, and a form has fixed fields; they travel together
  in one record keyed by the adapter's names.
- new field: resource_result_acquisition `interpretation` (RETURN_FORM, selectable): the old model-written `report_update`;
  recorded by the new `report` tool.
- The form has no null type: `execution_handoff` (null for zero or several identities) is a list of zero or one handoff;
  `handoff` (holds `failure: null`, nullable input versions) is one untyped `record` field.
- Handoffs and acquired results are values, not records in custody: the job-record library does not exist yet (README
  section 5 item 22). They reach the parent in the result.
- Credit is the `credit_view` a resource tool returned last; the credit definition itself was never in these files
  (`services.bound_role_credit`) and stays the service's. Credit before any unit is 0.0. `credit_view(assignment)` is asked
  without the old `receiver_selection` (not known to the episode before `final_to_parent`). Facts reach the result only as
  of the last unit that asked the service for them (`_observed`); the old code asked the adapter again at closure, which
  `final_to_parent` cannot (no services).
- Controller: `AccumulationYieldController` (README 7b), because the old results assignment names no target or maximum and the
  old file named no estimator ("caller settings unchanged"); `PracticalYieldEstimator`/completion would need the commission's
  target, which no field of the old assignment supplies. Its `cost` and `parameters` come from the run's settings; at cost
  zero it never stops. No "completion credit may pass its target" item (no completion controller).
- The old `permitted_common_actions` listed `child` and `redeliver_report` for an episode with no children: neither is
  offered. `wait` is a tool unit (`jobs/waiting.py::selected_wait`) and earns nothing (it returns no credit view).
- The old `execute` refused a tool outside the adapter catalogue (`tool_not_owned_by_resource_role`) and validated arguments
  against the tool's schema; here both are done by `action` (the selection schema is built from the catalogue and validated
  with `Draft202012Validator`), as a rejected model answer.
- The old `resource.inspect` and `resource.check_handoff` ran only if the assigned adapter listed them; here they are in the
  selection schema only if `service.catalog` lists them, and `resource.check_handoff` selects the adapter from the handoff
  argument through `service.check_handoff`.
- `resource_tool` catches `sqlite3.Error` from `check_handoff` as the old `execute` did; this is the adapter's error type,
  not a Store access (a sweep hit for `sqlite3`, not a finding).
- `internal_summary` reads `view.controller_state.as_record()` and `view.records.reasoning_schema()`; neither was run through
  the real runner in this step (no resource service exists to run it with, and no fake is written).
- AGENTS.md "Required literature evidence processing" (A105/A108 grading, subscoring sheet, `investigation_finding`) does not
  apply: this is an A101 operational episode and its `finding` is the handoff-state record, not an investigation finding.

## Not repaired

BLOCKED-ON-JOB-SERVICE: services resources, native_events, instruction_libraries do not exist yet; the job-record work table for acquired results and closure is not written. These are system limits, not repaired here.
