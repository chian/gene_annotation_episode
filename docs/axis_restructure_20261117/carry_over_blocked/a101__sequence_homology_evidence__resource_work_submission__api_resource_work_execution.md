# Blocked and unplaced: a101/sequence_homology_evidence/resource_work_submission/api_resource_work_execution

## BLOCKED-ON-STORE-ACCESS

None. The episode's Store use is `ctx.store.get`, `.artifact`, `.refs`, `.commit_reasoning` (tools) and `records.holds`, `records.reasoning_schema` (action). Library functions it imports (`jobs/waiting.py::selected_wait`, `records/hpc/resource_records.py`, the instruction, tool-knowledge, transport and feedback modules) do not touch the Store.

## Not built: services (not Store access)

- `resource_adapter`: the old resource adapters (explicit caller bindings keyed by `resource_id`; the A101 homology API adapter lived in the deleted shared root) have no library module and no service. `task.py` calls these members on it, in closed JSON: `declared_capabilities()`, `bound_resource_ids()`, `adapter_capabilities()`, `catalog(assignment)`, `prepare_assignment(assignment, scope, key=)`, `execute(assignment, tool, arguments, held, key=)`, `check_handoff(handoff, held, key=)`, `facts(assignment)`, `credit_view(assignment, held_refs)`, `decision_context(assignment)`. A run that links this episode must supply it, else `LinkError('service_required:...')`.
- `native_events`: `NativeEventLedger` is not wrapped as a service; `task.py` uses `validate_event_targets`, `wait_events` (through the library `selected_wait`) and a read member `targets(assignment)` (old `native_event_information.read`).
- Settings the episode reads: `cost`, `parameters` (controller), `tool_knowledge_directory`, `launch_instructions_directory`.

## Unplaced old functions

- `OperationalReport.validate_report`, the adapter part (`adapter.validate_report(context, form, original_schema)`): it validated the parent-defined JSON-Schema form, which no longer exists (the parent selects fields of the child's `RETURN_FORM`). Not carried; the episode's own handoff comparison is carried (`final_to_parent.validate_report`).
- `OperationalReport.fact_sources` for the adapter's own fact sources (`adapter.fact_sources('launch_api')`): the adapter defines them at run time; a `RecordForm` is fixed at class definition. They travel in the selectable field `adapter_facts` (new field).
- `ReceivedOperationalEvidence.received_form_references`: machinery (receipts bookkeeping); nothing replaces the adapter's "proof references"; the handoff records are returned in custody (`execution_handoff_refs`).
- The `sqlite3.Error` branch of the old `check_handoff` handler: dropped with the import (the service touches its own stores); `(ValueError, KeyError, OSError)` is kept.

## Contract misfits

- new field: api_resource_work_execution scope (record)
- new field: api_resource_work_execution scope_refs (record_refs)
- new field: api_resource_work_execution input_refs (record_refs)
- new field: api_resource_work_execution completion_target (number)
- new field: api_resource_work_execution adapter_facts (return, selectable record)
- new field: api_resource_work_execution execution_handoff_refs (return, selectable record_refs)
- completion credit may pass its target: the credit is the selected adapter's own credit view (`adapter.credit_view`), whose scale and ceiling are the adapter's; nothing here bounds it, so an adapter credit above `completion_target` raises the controller's `ValueError`. The old file named no estimator ("caller settings unchanged"); completion was chosen because the work ends with one usable handoff.
- null is not a form value (README 5, item 11): `execution_handoff` is `{}` where the old fact was `null` (zero or several physical executions).
- The old `report_update` / parent-defined report form (interpretive fields, `report_contract`, `initial_report`) has no place: the parent never authors a form; the model writes no report values in this episode.
- No `validate_form` is involved (the old episode called none).
- The old `resource.inspect` and `resource.check_handoff` handlers are carried in `resource_operation`, reachable only when the adapter's catalog names them (as before).
- Reasoning scope: `reason` needs the old request scope and the records it names as assignment fields (new fields above); `evidence_processing` is declared as an open optional object.
- No real runner test: the episode needs the `resource_adapter` and `native_events` services, which do not exist; no stand-in was written.
