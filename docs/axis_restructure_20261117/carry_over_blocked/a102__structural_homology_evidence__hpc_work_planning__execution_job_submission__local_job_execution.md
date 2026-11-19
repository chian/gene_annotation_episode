# Blocked and unplaced: a102/structural_homology_evidence/hpc_work_planning/execution_job_submission/local_job_execution

## BLOCKED-ON-JOB-SERVICE
- BLOCKED-ON-JOB-SERVICE: `job_access` (service, no implementation); wanted calls, all in `task.py exec_command`, each raising NotImplementedError at the call when the service lacks the method:
  - `await ctx.services["job_access"].begin_command(assignment, "exec_command", arguments, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)` (old `PracticalState.begin`: idempotent by operation key, a completed intent returns its receipt, reply `{state, intent, receipt}`)
  - `await ctx.services["job_access"].run_command(assignment, arguments, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)` (old `TerminalExecution.execute`)
  - `await ctx.services["job_access"].finish_command(key, outcome, validations, context_after=after)` (old `PracticalState.finish`, returns the immutable receipt)
- The service's durable practical state (intents, receipts, working context) is the old `PracticalState` directory; no work table is declared for it (no job record kind exists).

## BLOCKED-ON-STORE-ACCESS
- function = records/practical_receipt_information.py::PracticalReceiptInformation.publish / read / resolve; pattern = "library not carried" (store.db on `records`, `runtime_actions`, `runtime_episodes`; takes the old `BindingContext`). Old call -> intended call: `PracticalReceiptInformation(store, run_id).publish(context, receipt)` -> a custody-aware publish over `ctx.store`. Not called: `task.py publish_receipt` writes the same `source` record (provider `episode.practical_receipt`) through `ctx.store.put`; its body drops `scope` (the assignment has no scope now), so the old reader (`BODY_FIELDS` includes `scope`) would refuse it.
- function = findings/structural_homology_evidence/terminal_scientific_evidence.py::read_terminal_handoff, validate_terminal_handoff, captured_terminal_file, terminal_native_snapshot, validate_terminal_native, validate_terminal_observation (store.db / old receipts); pattern = "library not carried". Not called by this episode (only `finalize_scientific_command`, `terminal_artifact_paths`, which touch no Store, are).

## unplaced_old_functions
- result_records.py (ExecutionResultRecords and its methods `_versions`, `_target`, `_selector`, `_result_directory`, `_windows`, `_selected_result_action`, `_validate_result_body`, `_read_result`, `_selection`, `_context_target`): they serve reading acquired results of received handoffs; a launch acquires no results. The module `execution_input_versions` (old import) has no module now.
- retained_protein_reader.py (NativeRetainedProteinReader.retained_protein_structure_reader, `_protein_reference_access`, `_retained_protein_result`): retained protein-structure read authority over store.db and runtime_episodes; a launch retains none.
- The old check of `immutable_input_versions` of the commissioning launch request (from_parent.prepare_assignment): the module `execution_input_versions` has no current place and the check read runtime_episodes; not carried.
- The old `native_profile`/protein tool-information presentation of `selected_execution_task` (internal_summary._with_selected_execution_task, `services.scientific_parent_task`): the shape was rebuilt from the intent record (question, selected_tool_info, request); old file unreadable (no git).

## contract_misfits
- new field: local_job_execution record_refs (records the job inputs name, passed in custody).
- new field: local_job_execution scientific_task (scientific_question and selected_tool_info, old `services.scientific_parent_task`).
- `execution_result_origin` was null when no result is retained; a form has no null: selecting it raises NotImplementedError('no_null_form_type:execution_result_origin').
- The old files at 97308b94c could not be read (the checkout has no .git); the carry-over follows the intent record, the function list and the library. The yield class suffix `_native_*` is derived from the native job keys of `requested_job`; the A102 native job family allowed on a resource (`native_protein_structure`) is inferred.
- `read_from_parent` raises when a requirement earns credit outside `completion_keys` (the old hook-era port's check; `PracticalState.begin` refuses an action after the completion, so such credit would never reach the target).
- Completion credit cannot pass its target: the credit is the sum of satisfied requirement credits and the target is the sum of all of them.
- The service reply shapes (`state`, `intent.context_before`, receipt) are those of `PracticalState`; the system fixes none.
