# Blocked and unplaced: a107 / partner_presence_evidence / hpc_work_planning / execution_job_submission / local_job_execution

Carried 19 November 2026. The episode imports and passes its structural tests; it cannot run a command until the items below exist. No new file under `episode_support/`; nothing was stubbed.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` service with an `exec_command` operation; wanted call: `await ctx.services["job_access"].exec_command(arguments["assignment"], arguments["arguments"], key=ctx.operation_key)`. It must do what the old `TerminalExecutionBehavior.execute` did once per operation key: begin the intent, run the command on the local resource (`TerminalExecution.execute`, `native_lifecycle`), `finalize_scientific_command`, apply the working-context change, `assess_validations` of the original requirements, finish the receipt; and return `{'receipt': <practical receipt>}`. `task.py::exec_command` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` when the service has no such operation.

## BLOCKED-ON-STORE-ACCESS

- function = `episode_support/records/practical_receipt_information.py::PracticalReceiptInformation`; pattern = "library not carried": old call `PracticalReceiptInformation(self.store, context.run_id).publish(context, receipt)` (uses `store.db` on `runtime_actions`/`runtime_episodes`/`sqlite_master` and takes the old `BindingContext`) -> intended call: a custody write of the receipt as a Store record (`ctx.store.put('source', ..., origin='tool')` after `ctx.store.artifact(canonical(body), 'application/json')`). The tool does not call it; it saves the receipt with `ctx.store.artifact(canonical(receipt), 'application/json')` and returns that reference as `receipt_ref`. The qualified source record of the old publication is not written.
- function = old `native_blast_masking_results.validate_job_inputs`, `native_blast_utility_results.validate_job_inputs`, `expression_nmf_operands.validate_expression_nmf_job_inputs`, `execution_input_versions.validate_execution_input_versions`, `native_blast_database_result_publication.validate_native_job_inputs`, `native_blast_standard_database_result_publication.validate_standard_blast_job_inputs`, `native_rna_structure_result_publication.validate_rna_structure_job_inputs` (called by `prepare_assignment`, `initial_references`, `_check_parent_inputs`); pattern: old `fn(self.store, context, assignment)` -> intended `records.holds(ref)` / `ctx.store.get(ref)` per named input. None of these modules exists in `episode_support/` (`axis_shared_modules.tsv`: target "none"). Not called; see unplaced.

## Unplaced old functions

- `execution_contracts.py` `native_result_operation_catalog`: serves the `results` role; nothing of this episode calls it.
- `from_parent.py` `NativeParentRequests._permitted`: the parent launch's resource permission test (role `launch`).
- `resource_information.py` `NativeResourceInformation.resource_tool_contracts`: declared operations over every bound resource for the parent's catalogue.
- `science.py` `_masking_inputs`, `_utility_inputs`, `_expression_nmf_inputs`, `_versions` and `from_parent.py` `prepare_assignment` input validations: the modules are in no library location and, by owner rule 1, a check of a commission is not added; the assignment's `record_refs` field passes the input records in custody.
- `internal_summary.py` `_with_selected_execution_task` job views: `expression_nmf_presentation.expression_nmf_scientific_job_view` and `native_profile_presentation.native_profile_scientific_job_view` are in no library location; `messages/internal_summary.py::_selected_execution_task` raises `NotImplementedError('unplaced:...')` for `native_expression_nmf`, `native_hmmer` and `native_hmmer_preparation` requests.
- `initial_information.py` `initial_information`: the library presentation (`library.execution_initial_information.presentation`: `resource_information`, `received_api_information`) is in no library location; `task.py::decide` builds the context keys from the settings instead (no api information: this is a local resource).
- Result family fact sources of the infernal readers (`infernal_native_result_views.FAMILY_SOURCES`, `infernal_preparation_result_views.preparation_fact_sources`) and `native_blast_database_results.empty_facts` / `native_blast_standard_database_results.empty_facts`: the infernal modules are in no library location; only `execution_infernal_result_refs` (a name in the old code) is declared.

## Contract misfits

- new field: local_job_execution record_refs (the records the job inputs name: masking, utility and expression inputs; old code read them from the commissioning request).
- new field: local_job_execution scientific_task (old `services.scientific_parent_task(context)`: `scientific_question`, `selected_tool_info`; the parent supplies it in the assignment so that `selected_execution_task` can be built).
- completion credit may pass its target: `credit` is the old sum of the credits of every currently satisfied requirement (initial and non-completion keys included) while the target is the credit of the `completion_keys` only; with another requirement satisfied beyond them, or an initial credit at or above the target, `CompletionYieldController` raises `completion_credit_exceeds_target`. Left unchanged.
- The 21 `execution.<name>` masking and utility fact sources of the old report are not lowercase identifiers, so no `RETURN_FORM` field can carry them; `execution_result_origin` (null type) and the empty native result family object `execution_blast_standard_database_acquisition` have no form type: selecting them raises. A launch returns none of them.
- `records/practical_receipt_information.py` (library) imports an episode folder; not imported here.
- Lookups: the old exchange served `knowledge.*` and `launch.instructions.*` lookups; they are carried as the two tools `knowledge_lookup` and `launch_instruction_lookup` (read operations only; `launch.instructions.select` pins sections for a child assignment and this episode has no child).
- Settings keys used by this episode (`ctx.settings`): `resources` (by resource id), `initial_information` (by resource id), `coordinator_workspace`, `launch_instructions_directory`, `tool_knowledge_directory`, `task_yield_profiles`; the caller of `link` must supply them in `continuation`.
- `validate_form`: not used (the old report validation compares fact fields with the recorded facts, carried in `final_to_parent.py::validate_report`; A107 has an axis `validate_form` but the form is admitted by the system).
- BLOCKED-ON-JOB-SERVICE: see above; no `job_access` service is provided yet.
- No old tests existed for this episode folder at 97308b94c or in the working tree; `retired_tests/...local_job_execution.tsv` holds the header only.

## Not repaired

- BLOCKED-ON-JOB-SERVICE: `job_access.exec_command` does not exist; `task.py::exec_command` raises at that point.
- BLOCKED-ON-STORE-ACCESS: `PracticalReceiptInformation.publish` (library not carried); the receipt is saved with `ctx.store.artifact`.
- Unplaced, raising: `task.py::_resource_configuration` raises `NotImplementedError('unplaced:validate_primary_resource_bindings:<names>')` for a resource that binds `native_*` jobs (old `validate_primary_resource_bindings` and the native binding validators are in no library location). `messages/internal_summary.py::_selected_execution_task` raises `unplaced:expression_nmf_scientific_job_view` / `unplaced:native_profile_scientific_job_view`.
- Return-form limits (contract misfits): the 21 dotted `execution.<name>` sources cannot be field names; `execution_result_origin` and the object family sources raise when selected.
- Corrections to the text above: `final_to_parent.validate_report` only compares fact fields with the recorded facts (it builds no closed schema and calls no A107 `validate_form`); completion credit may pass its target (see Contract misfits), it is not guaranteed to stay below it.
- Retired tests: the old folder held no `tests/` at 97308b94c (git ls-tree); no old test was retired, and the retired_tests file holds the header only. Any statement above that `tests/test_local_job_runtime.py` was retired is wrong.
