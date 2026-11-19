# resource_result_acquisition (A102, structural_homology_evidence): blocked, unplaced and contract misfits

Episode: `gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/resource_result_acquisition` (binding path `structural_homology_evidence/resource_result_acquisition`). Job episode (the receiving child of a resource handoff; its resource adapters were explicit caller bindings, and the old tree holds no adapter). No children, so no `msg_to_child.py` or `read_from_child.py`. The working tree held only a hook-era `episode.py` (class on `A102LocalJobRuntime`, `A102ContractBinding`; deleted first and rewritten) and `__init__.py`. The old tree has no tests for this episode, so the retired-tests file has only its header.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: service `resources` (the resource adapters: capabilities, catalog, execute, facts, credit_view, validate_report, check_handoff); wanted call: `ctx.services['resources'].read('declared_capabilities')`, `.read('adapter_capabilities')`, `.read('catalog', assignment)`, `.read('decision_context', assignment)` in `task.py decide` and `action`; `.execute(assignment, tool_name, arguments, ctx.operation_key)`, `.credit_view(assignment)`, `.facts(assignment)`, `.validate_report(assignment, interpretation)`, `.check_handoff(handoff, ctx.operation_key)`, `.declared_capabilities()`, `.adapter_capabilities()`, `.is_bound(resource_id)` in the tools. The service selects the adapter from `assignment['handoff']['resource_selection']['resource_id']` and raises `resource_not_bound` when none is bound. The run fails at link until the caller supplies it.
- BLOCKED-ON-JOB-SERVICE: service `native_events` (the `NativeEventLedger` of detached local jobs); wanted call: `selected_wait(ctx.services['native_events'], arguments['condition'])` in the `wait` tool.
- BLOCKED-ON-JOB-SERVICE: job-record library (handoff, check, closure as a declared work table); wanted call: acquisition tools would write acquired results with `ctx.store.table(JOB_LEDGER).put({...})` and return them in `record_refs`. No such table exists, so handoffs and results reach the parent only as values (`adapter_facts`, `execution_handoffs`).

## BLOCKED-ON-STORE-ACCESS

None. The only Store call is `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)` (`task.py reason`); `internal_summary` reads `view.records.reasoning_schema()`. Library functions called (`jobs/waiting.py::selected_wait`, `instructions/*`, `model_exchange/*`, `records/hpc/resource_records.py`, `records/progress_views.py`, `tools/tool_knowledge.py`) take values or directories, not the Store.

## UNPLACED OLD FUNCTIONS

- `initial_references.py ResourceInitialReferences.initial_references`: asked the selected adapter for initial references; no member of the new form takes them and the adapter is a service call.
- `from_parent.py ResourceFromParent.prepare_assignment` (parts): `parent.role == 'launch'` test (a check of the commissioning parent: no check of a commission) and `adapter.prepare_assignment(parent, role, selected, scope, operation_key)` (adapter data added to the assignment).
- `received_messages.py ResourceReceivedMessages.received_form_references`: proof references per handoff from the owning adapter (`resource_information_handoff_proof_missing`): receipt custody is the system's.
- `report_reference_access.py ResourceReportReferenceAccess.resolve`: report-reference resolution; no resolver exists.
- `decision_inputs.py` parts: `execution_expectations`, `resource_estimator`/native estimates, `waiting_support`, `pending_work`, `completed_action_reports`, `requested_action_history`, `child_options`, `shared_information_context`, `native_event_targets`: no service or library function provides them.
- `decision_context.py` parts: `working_state`, `visible_record_refs`, receipt projection, `pending_work`, `report_deliveries`, `visual_evidence`, `report_lifecycle`: system custody or not provided.
- `action_contract_feedback.py` closed-top-level-form repair text and `component_native_return_channels_required` / `reads.map` diagnostics: built on the old runtime; the rejection feedback is `rejection_feedback`.
- `instructions.py` redeliver_report and decision-exchange history text: those actions do not exist.

## CONTRACT MISFITS

- BLOCKED-ON-JOB-SERVICE: `resources`; wanted call: `ctx.services['resources'].read('catalog', assignment)` and every call listed above.
- BLOCKED-ON-JOB-SERVICE: `native_events`; wanted call: `selected_wait(ctx.services['native_events'], arguments['condition'])`.
- validate_form_not_built:A102: the old `apply_response` called `validate_form(report_update, interpret_schema, resolver)` on the model's interpretation; A102 has no report-form validator, so `task.py report` raises `NotImplementedError('validate_form_not_built:A102')` at that point (the `report` unit is therefore not usable until the validator exists). The old `validate_report` body (adapter validation, then handoff facts equal) has no validate_form call; it is `messages/final_to_parent.py validate_report`, and the adapter's part is in the `report` tool after that raise.
- new field: resource_result_acquisition `scope` (commission message): the old request message carried the subject scope; the form has none. A missing `scope` raises `KeyError` in `read_from_parent`. `initial_report` (message, optional) likewise.
- new field: resource_result_acquisition `adapter_facts` (RETURN_FORM, selectable): the adapter-declared fact sources (`adapter.fact_sources('results')`) have names the episode cannot know; they travel in one record keyed by the adapter's names.
- new field: resource_result_acquisition `interpretation` (RETURN_FORM, selectable): the old model-written `report_update`, recorded by the `report` tool.
- The form has no null type: `execution_handoff` (null for zero or several identities) is a list of zero or one handoff; `handoff` (holds nulls) is one untyped `record` field.
- `ReportBoundaryError` (old `communication`) does not exist for A102; the fact mismatch is a `ValueError('resource_handoff_fact_mismatch: ...')`.
- Credit is the `credit_view` a resource tool returned last (old `services.bound_role_credit`, never in these files); credit before any unit is 0.0. `credit_view` is asked without the old `receiver_selection`. Facts reach the result only as of the last unit that asked the service for them; the old code asked the adapter again at closure, which `final_to_parent` cannot.
- Controller: `AccumulationYieldController` (README 7b): the old episode had no estimator ("Only the configured local controller governs continuation") and its assignment names no target or maximum. Cost and parameters come from `settings['cost']` and `settings['parameters']`; at cost zero it never stops. No completion controller, so no "completion credit may pass its target" item.
- The old `permitted_common_actions` listed `child` and `redeliver_report` for an episode with no children: neither is offered. `wait` is a tool unit and earns nothing.
- The old `execute` refused a tool outside the adapter catalogue and validated arguments against its schema; both are done by `action` (selection schema from the catalogue, `Draft202012Validator`) as a rejected answer. `resource.inspect` and `resource.check_handoff` are in the selection only if the service's catalog lists them (the old catalogue did not offer them).
- `task.py resource_tool` catches `(ValueError, KeyError, OSError)` from `check_handoff`; the sqlite3 import and `sqlite3.Error` were removed.
- The tool-knowledge and launch-instruction libraries are read from the settings directories `knowledge_library_directory` and `launch_instructions_directory` (as the sibling A102 episodes do), not from a service.
- `internal_summary` reads `view.controller_state.as_record()` and `view.records.reasoning_schema()`; neither was run through the real runner (no resource service exists to run it with, and no fake is written).
- AGENTS.md "Required literature evidence processing" does not apply: operational A102 episode; its `finding` is the handoff-state record.

## Not repaired

- `task.py report`: raises `NotImplementedError('validate_form_not_built:A102')`; no A102 validator exists (system limit).
- BLOCKED-ON-JOB-SERVICE: services `resources` and `native_events` are not implemented; decide, action and the tools cannot run.
- BLOCKED-ON-JOB-SERVICE: no job-record work table; handoffs and results reach the parent as values, `record_refs` is `[]`.
