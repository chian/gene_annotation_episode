# Blocked and unplaced: A102 structural_homology_evidence/execution_job_submission

Old source was read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`; the working tree has no `.git`). The folder is a private copy of the shape of the finished A106 `execution_job_submission` carry, adapted to A102 (three resource children, practical requests). Nothing is imported from another episode folder. No old test of this episode existed at `97308b94c` (the folder had no `tests/`), so the retired-tests file has only its header.

## BLOCKED-ON-JOB-SERVICE
- BLOCKED-ON-JOB-SERVICE: job_access.api_capabilities; wanted call: `ctx.services['job_access'].api_capabilities(resource_id)` in `task.execution_capabilities` (tool), and `ctx.services['job_access'].read('api_capabilities', resource_id)` in `task.decide` (recorded read). It returns the old `api_execution.capabilities(resource_id)` entries (`name`, `configuration`) of an API resource: the operation names and the `ncbi_contact_configured` / `provider_rate_state_configured` facts. Only an API resource needs it; a local or HPC resource shows the `exec_command` operation. The tool raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` when the service has no such member.

## BLOCKED-ON-STORE-ACCESS
- function = `readers/protein_structure/protein_structure_operands.py::validate_protein_structure_job_inputs`, pattern = "library not carried": the old `from_parent.prepare_assignment`, `initial_references` and `execution_state.initialize` called `validate_protein_structure_job_inputs(self.store, parent, request, returns=...)` for each request. Intended: a check of the held input records of each request through `records`/`ctx.store`. Not called: `read_from_parent` is handed no `records`, and no tool or function of this episode runs at commission time with a store. Its result (the input references) is the assignment field `input_refs`, which the commissioner names in custody.
- old call -> intended call: `validate_execution_input_versions(self, versions, scope, context=parent)` (old `_versions`, module `root.a102.execution_input_versions`, not in the library) -> a check of `immutable_input_versions` over `records`. Not placed (no library module, no function with `records` at commission time).
- old call -> intended call: `self.store.db.execute('SELECT ... FROM runtime_actions / runtime_episodes / runtime_observations ...')` in `completion.py`, `closed_credit.py`, `result_selection.py`, `retained_*.py` -> none: old-runner machinery (usable handoff is read from held handoff references in `credit.py` through `records.holds`).

## Unplaced old functions
- `execution_contracts.native_result_operation_catalog`, `execution_state._result_directory`, `result_selection` (`LaunchResultSelection`, `_target`, `_selector`, `_windows`), `retained_protein_reader.py` (all rows), `retained_result_acquisition.py`, `retained_result_publication.py`: serve the old `results` role, which is the sibling `execution_result_acquisition`, not this launch role.
- `decision_provider.complete_decision`'s selected-execution prompt renderer (`render_selected_execution_prompt`): in the old shared root, not carried.
- `decision_inputs`: `execution_expectations`, `resource_tool_estimates`, `native_execution_expectations`, `completed_action_reports`, `requested_action_history`: services of the old shared root (resource estimator, execution expectations); no estimate table exists yet (README section 5, item 19).
- `resource_information.resource_tool_contracts`: commission-route contracts of every resource for the head's tool text; the head writes its own text over its own slots.
- `terminal_execution.py` (`TerminalExecutionBehavior` and its methods other than the catalog): the local/HPC command behaviour, which `local_job_execution` and `hpc_job_execution` carry in their own folders.
- `from_parent.prepare_assignment`'s `authenticate_launch` (imported from `hpc_work_planning.to_child_execution_job_submission`): authenticated the commission against the old runtime tables; a wrong commission just fails (no check). Not carried.

## Contract misfits
- new field: execution_job_submission scope; new field: execution_job_submission input_refs; new field: execution_job_submission handoff_unit (the old `configuration.handoff_unit`; `credit` has no settings); new field: execution_job_submission already_handed_off_resource_ids (the old `initial_known_record_refs` baseline); new field: execution_job_submission scientific_task (old `services.scientific_parent_task`).
- new field: api_job_execution immutable_input_versions is declared as a `record` by the child; the old assignment (this episode's) is a list. `msg_to_child` sends it as `{'input_versions': [...]}`. The two folders should agree on one type.
- `ctx.settings` must hold `resources` (resource_id -> configuration with `kind` in `local`, `pbs_ssh`, `api`) and `task_yield_profiles` (key `launch:<sorted request classes joined by +>` -> `{cutoff, parameters}`); optional `initial_information`, `launch_instructions_directory`, `tool_knowledge_directory`. `yield_controller` raises `execution_resource_not_bound` / `execution_resource_kind_conflict` / `execution_original_task_yield_profile_required:<key>` when the settings do not fit the commission.
- `validate_report` raises `NotImplementedError('validate_form_not_built:structural_homology_evidence')` at its first step (the old `validate_form` of the parent-written form; A102 has no `validate_form`), so `final_to_parent` always raises until that is built. `api_job_execution` and `local_job_execution` dropped that step and `hpc_job_execution` raises likewise: the folders disagree.
- `execution_result_origin` was null when no result is retained; a form has no null type. It is declared selectable and selecting it raises, as in the three children.
- The old `required_return_sources` (`execution_handoff_refs` required when the commissioning parent is the head and an annotation task is required) is the commissioner's `selection` now; this episode cannot require it of itself.
- Usable handoff: the old `usable_handoff(target)` read the handoff record through the old progress provider. Now a resource has a usable handoff when its resource child returned `execution_handoff_refs` that this episode holds (`credit.py`). No handoff record kind or library exists yet (job record kind: BLOCKED-ON-JOB-SERVICE in the children).
- The old baseline (`initial_known_record_refs`, resources already handed off in the episode's initial records) is the optional assignment field `already_handed_off_resource_ids`; with none given the baseline is empty and the controller's maximum is every eligible request times `handoff_unit`.
- The old `no_remaining_requests` exact-zero controller is not carried (README 7b): a commission with no uncredited eligible request fails in `yield_controller` (`launch_no_uncredited_original_request`).
- completion credit may pass its target: not applicable (the controller is bounded quality; the credit is `handoff_unit` times the distinct eligible resources handed off, which cannot pass the maximum `handoff_unit` times the eligible resources not already handed off, because `action` offers only eligible resources).
- The check of `immutable_input_versions` and of the protein-structure inputs at commission time cannot be made in `read_from_parent` (no `records`): see BLOCKED-ON-STORE-ACCESS.

## Not repaired

- `validate_report`: A102 has no validate_form; `messages/final_to_parent.py` raises NotImplementedError('validate_form_not_built:structural_homology_evidence') (system limit, reported).
- BLOCKED-ON-JOB-SERVICE: job_access.api_capabilities; wanted call: job_access.api_capabilities(resource) for an API resource (task.py raises explicitly).
- BLOCKED-ON-STORE-ACCESS: commission-time checks (validate_protein_structure_job_inputs, validate_execution_input_versions, parent-input custody checks); no records in read_from_parent.
- Type disagreement: `immutable_input_versions` is sent as {'input_versions': [...]} to api_job_execution, which declares an untyped record (contract misfit between folders).

## Repaired

- `submission_source.py` (hook-era, used bound.recorder, stale imports) deleted from the folder; the test no longer excludes it.
