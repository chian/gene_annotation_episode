# Blocked and unplaced: a102/structural_homology_evidence/resource_work_submission/api_resource_work_execution

Old source was read with `git show 97308b94c:<path>` using the git dir `/home/chia/repos/gene_annotation_episode_disk/.git` (the working tree has no `.git`). The folder is a private copy of the shape of the finished a101 sibling with the same old source; nothing is imported from it. The old folder had no tests, so no test is retired (the retired-tests file holds only its header).

## BLOCKED-ON-STORE-ACCESS

None. The episode's Store use is `ctx.store.get`, `.artifact`, `.refs`, `.commit_reasoning` (tools) and `records.holds`, `records.reasoning_schema` (action). The library functions it imports (`jobs/waiting.py::selected_wait`, `records/hpc/resource_records.py`, `instructions/*`, `tools/tool_knowledge.py`, `model_exchange/strict_output.py`, `model_exchange/rejection_feedback.py`, `records/progress_views.py`) do not touch the Store.

## Not built: services (not Store access)

- `resource_adapter`: the old resource adapters (explicit caller bindings keyed by `resource_id`; the A102 structural API adapter lived in the deleted shared root) have no library module and no service. `task.py` calls these members on it, closed JSON: `declared_capabilities()`, `bound_resource_ids()`, `adapter_capabilities()`, `catalog(assignment)`, `prepare_assignment(assignment, scope, key=)`, `execute(assignment, tool, arguments, held, key=)`, `check_handoff(handoff, held, key=)`, `facts(assignment)`, `credit_view(assignment, held_refs)`, `decision_context(assignment)`. A run that links this episode must supply it, else `LinkError('service_required:...')`.
- `native_events`: `NativeEventLedger` is not wrapped as a service; `task.py` uses `validate_event_targets`, `wait_events` (through the library `selected_wait`) and a read member `targets(assignment)`.
- Settings read: `cost`, `parameters` (controller), `tool_knowledge_directory`, `launch_instructions_directory`.

## Unplaced old functions

- `from_parent.py ResourceFromParent._require_launch_child_instruction_pins`, and the field-equality and `resource_selection` equality checks of `prepare_assignment` (`resource_assignment_conflict`, `resource_selection_conflict`, `launch_instruction_inheritance_conflict`): checks of the commission against the parent's assignment; a wrong commission just fails and nothing checks it. The parent copies its values in its own `msg_to_child`.
- `goal.py ResourceGoal.contract_information_profile` and the discovery paragraph: always `None`, never used.
- `initial_references.py ResourceInitialReferences.initial_references`: acted only for role `results`, never for `launch_api`.
- `to_parent.py ResourceToParent.validate_report`, the adapter part (`adapter.validate_report(context, form, original_schema)`): it validated the parent-defined JSON-Schema form, which no longer exists. The episode's own handoff comparison is carried (`final_to_parent.validate_report`).
- `report_fields.py ResourceReportFields.fact_sources` for the adapter's own fact sources: the adapter defines them at run time; a `RecordForm` is fixed at class definition. They travel in the selectable field `adapter_facts` (new field).
- `task.py ResourceTask.apply_response`, the `report_update` admission (`validate_form`, `workflow.validate_report` with the parent's form): the parent never authors a form and the model writes no report values here. A102 has no `validate_form`; none is written or called (`validate_form_not_built:A102` is not reached).
- The `sqlite3.Error` branch of the old `check_handoff` handler: dropped with the import; `(ValueError, KeyError, OSError)` is kept.
- The instruction texts for the specialist, job-episode options, `redeliver_report` and the `pending_child_` wait handle: not carried (no child, no pending handle).

## Contract misfits

- new field: api_resource_work_execution scope (record)
- new field: api_resource_work_execution scope_refs (record_refs)
- new field: api_resource_work_execution input_refs (record_refs)
- new field: api_resource_work_execution completion_target (number)
- new field: api_resource_work_execution adapter_facts (return, selectable record)
- new field: api_resource_work_execution execution_handoff_refs (return, selectable record_refs)
- completion credit may pass its target: the credit is the selected adapter's own credit view (`adapter.credit_view`), whose scale and ceiling are the adapter's; nothing here bounds it, so an adapter credit above `completion_target` raises the controller's `ValueError`. The old episode named no estimator ("Only the configured local controller governs continuation"); completion was chosen (README 7b) because the work ends with one usable handoff.
- null is not a form value: `execution_handoff` is `{}` where the old fact was `null` (zero or several physical executions).
- The old `report_update` / parent-defined report form has no place: no `report_contract`, no `initial_report`.
- The old `resource.inspect` and `resource.check_handoff` handlers are carried in `resource_operation`, reachable only when the adapter's catalog names them (as before).
- Reasoning scope: `reason` needs the old request scope and the records it names as assignment fields (new fields above).
- A102 has no `model_exchange/structural_homology_evidence/action_transport.py` and no literature prompt module; the strict output transport is the parametrized library `model_exchange/strict_output.py` (open records as text), and the instruction text is `instructions/structural_homology_evidence/runtime_prompt.py`.
- No real runner test: the episode needs the `resource_adapter` and `native_events` services, which do not exist; no stand-in was written.
- The brief reads old code with `git show` in the repository, but the working tree has no `.git`; the disk copy's git dir was used read-only.
