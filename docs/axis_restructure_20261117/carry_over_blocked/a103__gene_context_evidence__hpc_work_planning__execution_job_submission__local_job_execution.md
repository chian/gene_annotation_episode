# Blocked and unplaced: a103 / gene_context_evidence / hpc_work_planning / execution_job_submission / local_job_execution

Carried 19 November 2026. The episode imports and passes its structural tests; it cannot run a command until the items below exist.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` service with an `exec_command` operation; wanted call: `await ctx.services["job_access"].exec_command(arguments["assignment"], arguments["arguments"], key=ctx.operation_key)`. It must do what the old `TerminalOperations.execute` did once per operation key: begin the intent, run the command on the local resource (`TerminalExecution.execute`, `native_lifecycle`), `finalize_scientific_command`, apply the working-context change, `assess_validations` of the original requirements, finish the receipt; and return `{'receipt': <practical receipt>, 'handoff': <handoff or None>}`. `task.py::exec_command` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` when the service has no such operation. Nothing was stubbed.

## BLOCKED-ON-STORE-ACCESS

- function = `episode_support/records/practical_receipt_information.py::PracticalReceiptInformation`; pattern = "library not carried": old call `PracticalReceiptInformation(self.store, context.run_id).publish(context, receipt)` (uses `store.db` on `runtime_actions`/`runtime_episodes`/`sqlite_master`, takes the old `BindingContext`, and the module imports `A102RuntimeContext` from `root/a102`) -> intended call: a custody write of the receipt as a Store record (`ctx.store.put('source', ..., origin='tool')` after `ctx.store.artifact(canonical(body), 'application/json')`). The tool is not calling it; it saves the receipt with `ctx.store.artifact(canonical(receipt), 'application/json')` and returns that reference as `receipt_ref`. The qualified source record of the old publication is not written.
- function = old `native_blast_masking_results.validate_job_inputs`, `native_blast_utility_results.validate_job_inputs`, `execution_input_versions.validate_execution_input_versions`, `native_blast_database_result_publication.validate_native_job_inputs`, `native_blast_standard_database_result_publication.validate_standard_blast_job_inputs` (called by `NativeAssignment.prepare_assignment`, `initial_references` and `NativeOperations._check_parent_inputs`); pattern: old `fn(self.store, context, assignment)` / `validate_execution_input_versions(self, versions, scope, context=...)` -> intended `records.holds(ref)` / `ctx.store.get(ref)` per named input. None of these modules exists in `episode_support/` (`axis_shared_modules.tsv`: target "none"). They are not called; see unplaced.

## Unplaced old functions

- `contracts.py` `launch_operation_catalog`, `native_result_operation_catalog`: serve the parent `launch` role and the `results` role, not `launch_local`; nothing of this episode calls them.
- `from_parent.py` `NativeAssignment._permitted`: the parent launch's resource permission test (role `launch`).
- `internal_summary.py` `NativeSummary.capabilities`, `resource_tool_contracts`: configured availability and operation declarations over every bound resource for the parent's catalogue.
- `result_records.py` (22 rows) except `_masking_inputs`, `_utility_inputs`, `_versions`: the `results` role.
- Masking, utility, input-version and native job input checks of the commissioning parent (the old `_masking_inputs`, `_utility_inputs`, `_versions`, `validate_native_job_inputs`, `validate_standard_blast_job_inputs`): the modules are in no library location, and by owner rule 1 a check of a commission is not added; the assignment's `record_refs` field passes the input records in custody.

## Contract misfits

- new field: local_job_execution record_refs (the records the job inputs name: masking and utility inputs; old code read them from the commissioning request).
- new field: local_job_execution scientific_task (old `services.scientific_parent_task(context)`: `scientific_question`, `selected_tool_info`; the parent supplies it in the assignment so that `selected_execution_task` can be built).
- completion credit may pass its target: `credit` is the old sum of the credits of every currently satisfied requirement (initial and non-completion keys included) while the target is the credit of the `completion_keys` only; with another requirement satisfied beyond them, or an initial credit at or above the target, `CompletionYieldController` raises `completion_credit_exceeds_target`. Left unchanged.
- The `execution.<name>` masking/utility fact sources of the old report are not lowercase identifiers, so no `RETURN_FORM` field can carry them; `execution_result_origin` (null type) and the empty native result family objects have no form type: selecting them raises. A launch returns none of them.
- `records/practical_receipt_information.py` (library) imports an episode folder (`root/a102/.../runtime_continuation.py`), contrary to the library rule; not imported here.
- Lookups: the old exchange served `knowledge.*` and `launch.instructions.*` lookups; they are carried as the two tools `knowledge_lookup` and `launch_instruction_lookup` (read operations only; `launch.instructions.select` pins sections for a child assignment and this episode has no child).
- `validate_form`: not used (the old report validation compares fact fields with the recorded facts, carried in `final_to_parent.py::validate_report`).
