# Blocked and unplaced: A104 execution_job_submission/local_job_execution

The old episode files at 97308b94c could not be read with git show (the working checkout has no git history); the carry-over is taken from the intent record, the function list and the already carried sibling episode of the same old files (hpc_allocation_execution/execution_job_submission/local_job_execution, read as data, copied privately). The folder held a hook-era runtime.py and tests/test_local_job_runtime.py; both were deleted and the test is in retired_tests/<episode>.tsv.

## BLOCKED-ON-JOB-SERVICE
- `job_access.exec_command(assignment, arguments, key=ctx.operation_key)`: the local practical command execution (the old `native_tool_actions.execute` body: `PracticalState.begin/finish`, `TerminalExecution.execute`, `finalize_scientific_command`, cwd/environment revision tracking, `assess_validations`). Wanted call (in `task.exec_command`): `await ctx.services["job_access"].exec_command(arguments["assignment"], arguments["arguments"], key=ctx.operation_key)`, returning `{'receipt': <practical_action_receipt_v1>}`. Not provided; the tool raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.exec_command ...')` where the call is made.
- Job record kind: the handoff record. Wanted as a row of a declared job work table (`store.table(JOB_LEDGER).put({'job', 'event': 'handoff', 'at', 'detail', 'source_ref'})`). Not defined; the receipt artifact written by the tool stands in as the held handoff record (`execution_handoff_refs` returns the receipt artifacts of the commands that handed a job off).

## BLOCKED-ON-STORE-ACCESS
- `records/practical_receipt_information.py::PracticalReceiptInformation`: pattern "library not carried" (`store.db.execute('SELECT ... FROM runtime_actions' / 'runtime_episodes' ...)`, `sqlite_master`). Old call `PracticalReceiptInformation(self.store, context.run_id).publish(context, receipt)`; intended: publish the receipt as a record written through `ctx.store`. Not imported; `task.exec_command` writes the receipt with `ctx.store.artifact(canonical(receipt), 'application/json')`.
- `jobs/evolutionary_history_evidence/practical_execution_state.py::PracticalState`: file ledger under a coordinator directory (not the Store): not called; its receipts are the tool outcomes and its completion is `internal_summary._completion`.

## Unplaced old functions
- `LocalExecutionNativeState._result_directory` (native_state.py): immutable execution-results manifest of the results role.
- `native_result_operation_catalog` (result_operations.py): results role operation catalogue.
- `LocalExecutionSelectorContracts` (selector_contracts.py, whole file): results role selectors.
- `native_profile_scientific_job_view` (old import `native_profile_presentation`, listed "none" in `carry_over/axis_shared_modules.tsv`): no module holds it. `messages/internal_summary.py::_selected_execution_task` raises `NotImplementedError('unplaced:native_profile_scientific_job_view')` when the chosen job is `native_hmmer` or `native_hmmer_preparation` and a scientific task was supplied.
- `render_selected_execution_prompt`, `is_selected_execution_context` (old `evolutionary_history_evidence_prompt`) and `bvbrc_data_views.bvbrc_data_fact_sources` have no A104 module; the presentation is written in `task._task_text`, and the BV-BRC data fact sources are not in the return form.

## Contract misfits
- new field: local_job_execution record_refs (the records the job inputs name: masking and utility inputs, pinned input versions; the old code read them from the commissioning request).
- new field: local_job_execution scientific_task (the old `services.scientific_parent_task`: `scientific_question`, `selected_tool_info`).
- new field: local_job_execution completion_target (the old code had a completion proof, not a number). It is derived inside `read_from_parent` and is not an assignment field: the sum of the credits of every original `progress_requirements` entry, so the practical credit (the sum of the satisfied ones) cannot pass it. A target made of the completion keys' credits only (the credit the verified completion earns) would be passed as soon as another requirement is also satisfied and the controller would raise `ValueError('completion_credit_exceeds_target')`. Consequence: the controller stops on its forecast, not at the verified completion.
- completion credit may pass its target: only if `read_from_parent` is changed to the completion keys' credits (see above); as written it cannot.
- `ctx.settings` of this episode must hold `resources` (by resource id), `initial_information` (by resource id), `coordinator_workspace`, `launch_instructions_directory`, `tool_knowledge_directory` and `task_yield_profiles` (`{'launch_local:<request class>': {'cutoff', 'parameters'}}`, the old cutoff being the controller's cost).
- `job_access` must be supplied as a service factory (`SERVICES = ('job_access',)`); today none exists.
- The masking and utility fact sources are named `execution.<name>` (not lowercase identifiers), so a form cannot carry them: they are not in `RETURN_FORM`. Object-typed family sources and `execution_result_origin` (old value null) cannot be returned (a form has no null type and no empty-object value): selecting them raises `NotImplementedError`.
- The old API-resource return sources (AppService support refs, UniProt, BLAST graded return) depended on API resources configured in the shared old binding; a local-only binding does not carry them.
- The old `validate_form` of A104 `communication` is not called: the finding is a typed record admitted by the system; `validate_report` (recorded facts equal the report's fact fields) is kept in `final_to_parent`.
- The old frozen closed credit ("later reads return the original view") has no counterpart: the system's closure credit (`completion['credit']`) is returned.
- `PracticalYieldEstimator` verified a completion proof; no controller input carries a proof (README 5 item 5): the completion proof is derived from the held receipts for the model and the report only.
