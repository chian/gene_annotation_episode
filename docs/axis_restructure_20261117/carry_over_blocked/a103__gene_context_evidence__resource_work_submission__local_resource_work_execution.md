# a103/gene_context_evidence/resource_work_submission/local_resource_work_execution: blocked, unplaced, misfits

## BLOCKED-ON-STORE-ACCESS
None. The episode's tools call `ctx.store.get`, `ctx.store.artifact`, `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)`, `ctx.store.refs()` and `records.holds` / `records.reasoning_schema()`, all of which are offered.

Library not carried (called as written, none touches the Store here): `episode_support/jobs/waiting.py::selected_wait`, `episode_support/instructions/launch_instructions.py::LaunchInstructions`, `episode_support/tools/tool_knowledge.py::ToolKnowledge`, `episode_support/records/hpc/resource_records.py` (pure schemas; the only copy, used for the local role too).

## BLOCKED-ON-SERVICES (no library module wraps them; the episode declares them)
- `resource_adapter`: the old explicit resource adapters (`resource_adapters`, keyed by `resource_id`; the A103 local adapter was in the deleted shared root). Members used: `declared_capabilities()`, `bound_resource_ids()`, `adapter_capabilities()`, `catalog(assignment)`, `prepare_assignment(assignment, scope, key=)`, `execute(assignment, tool, arguments, held, key=)`, `check_handoff(handoff, held, key=)`, `facts(assignment)`, `credit_view(assignment, held_refs)`, `decision_context(assignment)`. The run must supply a factory; nothing supplies one today.
- `native_events`: `NativeEventLedger` (no service wraps it): `wait_events`, `validate_event_targets`, read member `targets(assignment)`.

## Unplaced old functions
- `decision_inputs.py` `execution_expectations`, `job_execution_options`, `native_execution_expectations` and `waiting_support` (only the `launch_local` expectations capture and the resource estimator over them): they ran on old workflow services (`execution_expectations`, `job_episodes`, `resource_estimator`, `native_estimation_context`, `waiting_support`), which are not carried; the estimate table is README section 5 item 19. The adapter's own `decision_context` estimates are carried.
- `action_contract_feedback.py` repair texts for the BV-BRC MinHash results selector and `reads.map` parameters: they used `root.a103.read_mapping.parameter_schema_failure` and old-root diagnostics; rejected answers get the library `rejection_feedback` only.
- `initial_references.py` (`results` role only): never this episode's role.

## Contract misfits
- new field: local_resource_work_execution scope (record), scope_refs (record_refs), input_refs (record_refs), completion_target (number): the old request carried scope and the records in the message; the completion controller needs the target. The commissioning parent (`resource_work_submission`) must supply them in `msg_to_child`.
- RETURN_FORM adds new fields `adapter_facts` (the adapter's own fact sources, defined at run time so not declarable in the form) and `execution_handoff_refs` (handoff records in custody). `execution_handoff` is `{}` where the old fact was `null` (the form has no null).
- completion credit may pass its target: the credit is the adapter's own unbounded credit view (`adapter_credit`), and the commissioned `completion_target` is not tied to it; the controller's `ValueError('completion_credit_exceeds_target')` is the failure.
- The old pin-inheritance, field-equality and selection-equality checks of `prepare_assignment` against the launch parent are commission checks and are not carried (rule 1); `resource_selection` kind (`local`) is still tested in `read_from_parent`.
- Resource schemas for the local role live only in `records/hpc/resource_records.py` (a path named for HPC); no copy under a local or gene_context role folder exists.
