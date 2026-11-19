# Blocked and unplaced: A110 local_job_execution (hpc_work_planning/execution_job_submission)

The old source was read with `git -C <disk checkout> show 97308b94c:<path>` (28 files of the episode folder). The folder had no tests at that commit and none in the working tree, so `retired_tests/<episode>.tsv` has only its header. The sibling a110 `hpc_allocation_execution/.../local_job_execution` (identical old files except path strings) was the model of the ten-file form; its files were copied privately with the binding path changed, none is imported.

## BLOCKED-ON-JOB-SERVICE
- BLOCKED-ON-JOB-SERVICE: `job_access.exec_command(assignment, arguments, key=ctx.operation_key)`; wanted call (in `task.exec_command`): `await ctx.services["job_access"].exec_command(arguments["assignment"], arguments["arguments"], key=ctx.operation_key)`, returning `{'receipt': <practical_action_receipt_v1>}`. It is the local practical command execution (the old `TerminalExecutionBehavior.execute` body: `PracticalState.begin/finish`, `TerminalExecution.execute`, `finalize_scientific_command`, cwd/environment revision tracking, `assess_validations`). Not provided; the tool raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.exec_command ...')` where the call is made.
- BLOCKED-ON-JOB-SERVICE: job record kind, the handoff record; wanted call: `ctx.store.table(JOB_LEDGER).put({'job', 'event': 'handoff', 'at', 'detail', 'source_ref'})`. Not defined; the receipt artifact the tool writes (`ctx.store.artifact(canonical(receipt), 'application/json')`) stands in as the held handoff record, and `execution_handoff_refs` returns the receipt artifacts of the commands that handed a job off.

## BLOCKED-ON-STORE-ACCESS
- `records/practical_receipt_information.py::PracticalReceiptInformation`: pattern "library not carried" (`store.db.execute('SELECT ... FROM runtime_actions' / 'runtime_episodes' ...)`, `sqlite_master`). Old call `PracticalReceiptInformation(self.store, context.run_id).publish(context, receipt)`; intended: publish the receipt as a record written through `ctx.store`. Not imported; `task.exec_command` writes the receipt with `ctx.store.artifact(canonical(receipt), 'application/json')`.
- `jobs/biochemical_feasibility_evidence/practical_execution_state.py::PracticalState`: a file ledger under the coordinator directory (not the Store): not called; its receipts are the tool outcomes and its completion is `messages/internal_summary.py::_completion`.

## Unplaced old functions
- `scientific_job_view` (old import of `flux_balance_request_binding`, in no place now) used by `NativeInternalSummary._with_selected_execution_task`: `messages/internal_summary.py::_selected_execution_task` raises `NotImplementedError('unplaced:scientific_job_view')` when the request is a native flux-balance job and the parent supplied the scientific task.
- `flux_balance_tool_contracts` (old import of `native_flux_balance_tool_info`, in no place now) used by `NativeResourceInformation.resource_tool_contracts`: `task._capabilities` raises `NotImplementedError('unplaced:flux_balance_tool_contracts')` for a resource whose configuration binds `native_flux_balance`.
- `fba_fact_sources` (old import of `flux_balance_return_views`, in no place now) and the library `fact_sources` / `resolve` of `received_result_readers`: the empty flux-balance result fact sources of the old `_live_facts` are not declared in `RETURN_FORM` (their names are in no readable place).
- `native_flux_balance_returns.validate_received_report` (old `FluxBalanceReturns`, unplaced): the flux-balance part of the old `validate_report` is not called.
- The compact flux-balance assignment (`flux_balance_request_binding`: `is_compact_assignment`, `read_request_binding`, `materialized_assignment`, `resource_assignment_schema`) read the launch's request binding from the old runner's tables: not carried; the parent passes the materialized practical assignment.
- `native_result_operation_catalog` (execution_contracts.py), `NativeReceivedRecords._received` and the result readers (`_read_result`, `_result_directory`, `_selector`, `_target`, `_validate_result_body`, `_windows`), `_retained_flux_balance_target`, `LocalFileSourceResults`: results-role functions; this launch role does not use them (rows marked `unplaced` in the "Carried over" table).
- `render_selected_execution_prompt` / `is_selected_execution_context` (old `library.scientific_decision_presentation`): no module holds them; the presentation is written in `task._task_text`.
- `execution_capabilities` / `resource_information_for_id` / `operation_catalog` (old `library.execution_*`): no A110 module; `task._capabilities`, `task._resource` and `task.EXEC_COMMAND` are written from the old `TerminalExecutionBehavior` text and the A104 carry of the same shared library entry (the description text of `exec_command` is copied from that carry, not from the unreadable shared module).

## Contract misfits
- new field: local_job_execution record_refs (the records the job inputs name: the flux-balance input versions; the old code read them from the commissioning request and the launch request binding).
- new field: local_job_execution scientific_task (the old `services.scientific_parent_task`: `scientific_question`, `selected_tool_info`).
- new field: local_job_execution completion_target (the old code had a completion proof, not a number). It is derived inside `read_from_parent` and is not an assignment field: the sum of the credits of every original `progress_requirements` entry (each is at least zero in `validate_assignment`), so the practical credit (the sum of the satisfied ones) cannot pass it. Consequence: the controller stops on its forecast or at the target, not at the verified completion alone.
- completion credit may pass its target: no (credits are non-negative and the target is their sum); the controller's `ValueError` is the failure if it ever did. `CompletionYieldController` also needs cost below target: a profile `cutoff` of at least the total requirement credit raises `completion_cutoff_must_be_below_target`.
- validate_form: the A110 axis has no `validate_form` (its `communication` exports only `plain`). The old `validate_report` called it first; `messages/final_to_parent.py::validate_report` no longer calls it (no function written or borrowed), so the report form check is not built and the fact-agreement check alone runs. Repaired so `final_to_parent` can return.
- `ctx.settings` of this episode must hold `resources` (by resource id), `initial_information` (by resource id), `coordinator_workspace`, `launch_instructions_directory`, `tool_knowledge_directory` and `task_yield_profiles` (`{'launch_local:<request class>': {'cutoff', 'parameters'}}`, the old cutoff being the controller's cost; the old `results_yield_profiles['native_unbounded_local']` belongs to the results role).
- `job_access` must be supplied as a service factory (`SERVICES = ('job_access',)`); today none exists.
- Object-typed `execution_result_origin` (old value null for a launch) cannot be returned: a form has no null type; selecting it raises `NotImplementedError('no_null_form_type:execution_result_origin')`.
- The old `PracticalYieldEstimator` verified a completion proof; no controller input carries a proof (README 5 item 5): the completion proof is derived from the held receipts for the model and the report only.
- The old frozen closed credit ("later reads return the original view") has no counterpart: the system's closure credit (`completion['credit']`) is returned.
- `acquisition/native_terminal_transport.py::TerminalExecution` (the shared copy) still imports the A104 `LocalPracticalOperations`; this episode calls the A110 copy `jobs/local_execution/biochemical_feasibility_evidence/terminal_execution.py` instead.


## Not repaired

- `validate_form_not_built:biochemical_feasibility_evidence`: the axis has no validate_form; the form check is absent, not replaced.
- `unplaced:scientific_job_view` (internal_summary), `unplaced:flux_balance_tool_contracts` (task), the compact flux-balance assignment and `fba_fact_sources` result sources, `validate_received_report` for flux balance: in no place.
- BLOCKED-ON-JOB-SERVICE: job_access service; wanted call: exec_command through job_access.
- `no_null_form_type:execution_result_origin`: forms have no null type.
