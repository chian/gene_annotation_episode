# Blocked and unplaced: a103/gene_context_evidence/resource_work_submission

## BLOCKED-ON-STORE-ACCESS

None. The episode's Store use is `ctx.store.artifact`, `.get`, `.holds`, `.refs`, `.commit_reasoning` (tools) and
`records.holds`, `records.reasoning_schema` (action). The library modules it imports (`jobs/waiting.py::selected_wait`,
`records/hpc/resource_records.py`, the instruction, tool-knowledge, transport, feedback and progress-view modules) do
not touch the Store.

## Not built: services (not Store access)

- `resource_adapter`: the old explicit resource adapters (keyed by `resource_id`) have no library module and no service.
  `task.py` calls these members, in closed JSON: `declared_capabilities()`, `bound_resource_ids()`,
  `adapter_capabilities()`, `can_check_handoff(resource_id)`, `check_handoff(handoff, held, key=)` (may be a coroutine),
  `facts(assignment)` (the handoffs and facts of every configured adapter), `credit_view(assignment, held_refs)` and
  `decision_context(assignment)`. A run that links this episode must supply it, else `LinkError('service_required:...')`.
- `native_events`: `NativeEventLedger` is not wrapped as a service; `task.py` uses `selected_wait` (library) over it and a
  read member `targets(assignment)`.
- Settings the episode reads: `cost`, `parameters` (controller), `tool_knowledge_directory`,
  `launch_instructions_directory`.

## Unplaced old functions

- `ResourceActionContractFeedback.reject_invalid_action` extra repair hints (contract-information repair text,
  `component_native_return_channels_required` detail, BV-BRC minhash selector input detail, `reads.map` parameter feedback):
  not carried; they served the decision exchange and tools this episode does not offer. The generic rejection
  (`rejection_feedback`) is carried.
- `ResourceInitialReferences.initial_references`: answered only for role `results`, which this episode does not have.
- `ResourceToParent.validate_report` per-adapter part (`adapter.validate_report(...)`): no replacement (the adapters are a
  service and `final_to_parent` has none). The episode's own check (every reported handoff field equals the recorded facts)
  is carried.
- `ResourceReceivedMessages.received_form_references`, `_handoff_receiver`, `from_child_*.receive_handoff`: replaced by
  custody (the child returns the handoff records in `execution_handoff_refs`; the system writes the `returned` receipts).
- `ResourceChildCommissioning.child_request_assembler`, `to_child_*` request ownership: machinery (README 3b C1); the three
  assemblers are one `msg_to_child`.
- `ResourceDecisionInputs` parts that read the old workflow object (`resource_context`, `shared_information_context`,
  `pending_work`, HPC request history, `job_execution_options`, `execution_expectations` capture): not carried; the adapters'
  duration information is the `decision_context` member of the `resource_adapter` service.
- Old tests: none existed at 97308b94c for this episode. The hook-era `tests/test_resource_work_link.py` in the working tree
  was deleted and recorded in `retired_tests/a103__gene_context_evidence__resource_work_submission.tsv`.
- The old `a103/gene_context_evidence/episode.py`, `home.py` and `runtime_source.py` (head folder, not mine) still mention
  this episode's hook-era class; they are outside this job.

## Contract misfits

- new field: resource_work_submission scope (record)
- new field: resource_work_submission scope_refs (record_refs)
- new field: resource_work_submission input_refs (record_refs)
- new field: resource_work_submission completion_target (number)
- new field: resource_work_submission adapter_facts (return, selectable record; the adapters' fact sources are defined at run time and a form is fixed at class definition)
- new field: resource_work_submission execution_handoff_refs (return, selectable record_refs; the old adapters wrote handoff records straight into the Store)
- completion credit may pass its target: the credit is the adapters' own credit view (`adapter_credit`), whose scale and ceiling are the adapters'; nothing bounds it, so an adapter credit above `completion_target` raises the controller's `ValueError`. The old file named no estimator; completion was chosen because the work ends with a usable handoff.
- A child commission does not move this episode's credit: `credit(summary, records)` has no services and no tool unit runs for a `ChildCall`, so the adapters' credit view is measured only after a resource tool unit (`resource_capabilities`, `resource_inspect`, `resource_check_handoff`). Old credit was recomputed from the Store after every unit including a child's; a handoff a child returned earns credit here only after the next resource tool unit (typically the receiving check). Not worked around; a parent's credit is never the sum of its children's (README 3d).
- null is not a form value (README 5, item 11): `execution_handoff` is `{}` where the old fact was `null`; `resource_selection` is optional in the assignment form where the old schema allowed `null` (read_from_parent gives `None`).
- The parent-defined report form (interpretive fields, `report_contract`, `initial_report` as report seed) has no place; the model writes no report values here. `initial_report` rides in the commission message.
- The contract-information profile and `episode.return_contract` discovery of the old goal are decision-exchange text: not carried.
- The children's assignment forms (all three identical) require `scope`, `scope_refs`, `input_refs`, `completion_target`; this episode fills them from its own new fields. The children return `execution_handoff_refs` for the handoff records (all three).
- No `validate_form` was involved (the old episode called none; A103 has `forms/gene_context_evidence/communication.py` but it was not used).
- No real runner test: the episode needs the `resource_adapter` and `native_events` services, which do not exist; no stand-in was written.
- `AGENTS.md` / the repository is a ramdisk copy (`/tmp/ramrepo`) with no `.git`; old files were read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>`.
