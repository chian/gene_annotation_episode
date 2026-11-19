# Blocked and unplaced: a103/gene_context_evidence/resource_work_submission/api_resource_work_execution

## BLOCKED-ON-STORE-ACCESS

None. The episode's Store use is `ctx.store.get`, `.artifact`, `.refs`, `.commit_reasoning` (tools) and `records.holds`, `records.reasoning_schema` (action). The library modules it imports (`jobs/waiting.py::selected_wait`, `records/hpc/resource_records.py`, the instruction, tool-knowledge, transport and feedback modules) do not touch the Store.

## Source of the carry

The first carry did not read the old files; `action_contract_feedback.py` was read at 97308b94c in the repair. The carry follows the episode's intent record (`episode_intent/a103/...`), the function list `runs/carry_over/functions/...tsv`, and the already carried sibling A101 `api_resource_work_execution` (same old structure; its A101 axis modules replaced by the A103 ones: `literature/prompts/gene_context_evidence/literature_investigation_prompt.py`, `model_exchange/gene_context_evidence/action_transport.py`). The old episode's exact A103 instruction wording and its repair hints could not be compared.

## Not built: services (not Store access)

- `resource_adapter`: the old resource adapters (explicit caller bindings keyed by `resource_id`) have no library module and no service. `task.py` calls these members on it, in closed JSON: `declared_capabilities()`, `bound_resource_ids()`, `adapter_capabilities()`, `catalog(assignment)`, `prepare_assignment(assignment, scope, key=)`, `execute(assignment, tool, arguments, held, key=)`, `check_handoff(handoff, held, key=)`, `facts(assignment)`, `credit_view(assignment, held_refs)`, `decision_context(assignment)`. A run that links this episode must supply it, else `LinkError('service_required:...')`.
- `native_events`: `NativeEventLedger` is not wrapped as a service; `task.py` uses `validate_event_targets`, `wait_events` (through the library `selected_wait`) and a read member `targets(assignment)`.
- Settings the episode reads: `cost`, `parameters` (controller), `tool_knowledge_directory`, `launch_instructions_directory`.

## Unplaced old functions

- `ResourceActionContractFeedback.reject_invalid_action`: carried in `task.py::_action_feedback` (generic rejection plus the `reads.map` parameter diagnostic). The contract-information repair text, `component_native_return_channels_required` detail and BV-BRC minhash selector input detail served child commissions and report forms; this episode has no child and no report form, so they have no place.
- `ResourceInitialReferences.initial_references` (the adapter's initial references for role `results`): the adapter member has no service; the records the operations read travel in the new field `input_refs`.
- `ResourceFromParent._require_launch_child_instruction_pins` and the parent-equality checks of `prepare_assignment`: not carried (a commission is never checked, rule 1); the parent copies its values in `msg_to_child`.
- `ResourceGoal.contract_information_profile`: returned None; nothing to place.
- Adapter part of `validate_report` (`adapter.validate_report(...)`), `fact_sources` of the adapter and `received_form_references` proof: no replacement (the adapter defines them at run time; a `RecordForm` is fixed). The adapter facts travel in the selectable field `adapter_facts`; handoff records in `execution_handoff_refs`.

## Contract misfits

- new field: api_resource_work_execution scope (record)
- new field: api_resource_work_execution scope_refs (record_refs)
- new field: api_resource_work_execution input_refs (record_refs)
- new field: api_resource_work_execution completion_target (number)
- new field: api_resource_work_execution adapter_facts (return, selectable record)
- new field: api_resource_work_execution execution_handoff_refs (return, selectable record_refs)
- completion credit may pass its target: the credit is the selected adapter's own credit view, whose scale and ceiling are the adapter's; nothing bounds it, so an adapter credit above `completion_target` raises the controller's `ValueError`. The old file named no estimator; completion was chosen because the work ends with one usable handoff.
- null is not a form value (README 5, item 11): `execution_handoff` is `{}` where the old fact was `null`.
- The parent-defined report form (interpretive fields, `report_contract`, `initial_report`) has no place; the model writes no report values here.
- No `validate_form` was involved (the old episode called none; A103 has one in `forms/gene_context_evidence/communication.py` but it was not used).
- Reasoning scope: `reason` needs the request scope and the records it names as assignment fields (new fields above). The A103 typed investigation finding / grader sheet rules of AGENTS.md apply to literature evidence episodes (A105/A108), not to this resource episode.
- No real runner test: the episode needs the `resource_adapter` and `native_events` services, which do not exist; no stand-in was written.

## Not repaired

- Old body of the A103 instruction wording and ResourceTask behaviour was not compared file by file (the verifier's `old_source_not_read`, environment limit of the first carry, not marked left undone).
- `resource_adapter` and `native_events` services do not exist: no real runner test possible.
- Completion credit may pass its target (contract misfit above).
