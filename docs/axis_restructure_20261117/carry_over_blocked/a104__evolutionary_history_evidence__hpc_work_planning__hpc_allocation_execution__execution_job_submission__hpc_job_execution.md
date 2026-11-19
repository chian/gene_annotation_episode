# Blocked and unplaced: A104 hpc_job_execution

Old source was read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` (the working tree `/home/chia/repos/gene_annotation_episode` is a RAM copy with no `.git`). The old folder had no tests; `retired_tests/<episode>.tsv` has only its header. The folder held only `__init__.py` before this carry-over, so nothing was deleted.

## BLOCKED-ON-JOB-SERVICE
- `job_access.exec_command(assignment, arguments, *, run_id, episode_id, key)`: executes one command on the HPC resource (target=resource over the configured PBS ssh transport) or in the coordinator run directory (target=coordinator), once per `key`, and returns the raw outcome `{'facts': ..., 'native_outcome': ...}` that the old `TerminalExecution.execute` returned. Wanted call, in `task.exec_command`: `await ctx.services["job_access"].exec_command(arguments["assignment"], arguments["arguments"], run_id=ctx.run_id, episode_id=ctx.episode_id, key=ctx.operation_key)`. Not provided: the tool raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.exec_command ...')` when the service object has no such member. The service would be configured with the PBS resource, the coordinator workspace and `terminal_artifact_paths` (all passed here through `ctx.settings`).
- Job record kind: the handoff row of the job ledger (MECHANICS section 6). Wanted call: `ctx.store.table(JOB_LEDGER).put({'job': <native job identity>, 'event': 'handoff', 'at': <submission time UTC>, 'detail': <job kind, how to find the job, launch estimates>, 'source_ref': receipt_ref})`. No `JOB_LEDGER` declaration exists. `task.exec_command` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job record kind ...')` when a command's receipt reports a handoff (after the receipt was written as an artifact).
- Not written (not needed by this tool): idempotency of the submission on `ctx.operation_key` is the service's, and `ctx.resumed` is not read.

## BLOCKED-ON-STORE-ACCESS
- `records/practical_receipt_information.py::PracticalReceiptInformation` (`publish`, `resolve`): pattern "library not carried" (`self.store.db.execute(... sqlite_master ...)`, `runtime_actions`, `runtime_episodes`). The old tool published each receipt through it as a Store source. Not imported. The receipt is written as `ctx.store.artifact(canonical(receipt), 'application/json')`, the one record kind a tool can write today (an artifact is a custody record the parent can be handed in a `record_refs` field); the old source format (`source_...` references accepted by the progress provider's handoff reader) is not reproduced.
- `jobs/evolutionary_history_evidence/practical_execution_state.py::PracticalState`: pattern "library not carried" (its own intent/receipt files under a directory, not custody). Not imported; its receipt, context tracking and validation steps are in `task.exec_command`, its completion proof in `messages/internal_summary.py::_completion` (copied; library candidate), its credit view is `grading/.../practical_execution_credit.py::project_practical_credit` (pure; called).
- `acquisition/native_terminal_transport.py::TerminalExecution`: the Store is not touched; imported for `validate_assignment` and `validate_action` only (pure validation of the configuration, assignment and action). Its `execute` (filesystem, subprocess, ssh) belongs behind the job-access service and is not called.
- Reading the input records of the job through custody (`ctx.store.open_artifact(ref)` for the files the model has to stage on the resource): no operation hands the bytes to a command on the resource; the model's commands can use only the paths the assignment names. Not wired.

## Unplaced old functions
See the `unplaced` rows of the Carried over table (5 rows):
- `HPCExecutionFromParent.child_assignment_schema` (the frozen-request enum): a commission check, not carried.
- `HPCExecutionResourceInformation.capabilities` and `.resource_tool_contracts`: the commissioning parent's text about resources and commission routes.
- `resource_operations.launch_operation_catalog`, `result_operations.native_result_operation_catalog`: catalogues of the parent and of the results role.
Not found anywhere: `render_hpc_prompt` / `is_hpc_context` (old `library/hpc_prompt.py`, outside the episode trees); the presentation is rewritten in `task._task_text`. A BV-BRC data reader for A104 (`bvbrc_data_views.bvbrc_data_fact_sources`, in `to_parent.py`/`report_fields.py`): no A104 copy exists (only A101 and A103), so its fact sources are not declared in `RETURN_FORM`. `empty_facts()` of `native_blast_database_result_records` and `native_blast_standard_database_result_records` (old `library/`): not found; selecting `execution_blast_database_acquisition` or `execution_blast_standard_database_acquisition` (object sources) raises `NotImplementedError('native_result_family_empty_object_not_defined:<name>')`.

## Contract misfits
- new field: hpc_job_execution record_refs (the records the job inputs name, passed in custody; the old code read them from the commissioning launch request).
- completion credit may pass its target: the credit is the sum of all satisfied original requirements, the target is the credit of the completion keys only (`math.fsum` over `progress_requirements` whose key is in `completion_keys`). A satisfied non-completion requirement before the completion keys are satisfied can lift the credit above the target; the controller raises `ValueError('completion_credit_exceeds_target')`.
- The frozen-request enum of `child_assignment_schema` (the assignment must equal one of the launch parent's already authorised hpc requests) cannot be a property of a static `RecordForm`, and a check of a commission is not carried. The commissioning `launch` parent must copy its authorised request into the assignment (`msg_to_child`).
- The 21 masking and utility fact sources are named `execution.<name>` (not lowercase identifiers), so no `RecordForm` field can carry them; always empty for a launch in the old code.
- `execution_result_origin` was always `None` for a launch and a form has no null type: declared as `record`, selecting it raises `NotImplementedError('no_null_form_type:execution_result_origin')`.
- The old `validate_report` called A104's `communication.validate_form(form, original_schema, resolver)` on the JSON-schema form the parent wrote; that form no longer exists (the parent selects fields, the system admits `RETURN_FORM`), so no `validate_form` call is carried. The `x-source` equality check is kept in `final_to_parent.validate_report`.
- The old frozen closed credit ("later delivery never reprices it") has no counterpart; the system's closure credit (`completion['credit']`) is returned.
- The old `private_yield_binding` flag (`execution_private_yield_binding_not_enabled`) is configuration machinery; the per-class profile selection (`launch_hpc:<request class>`, `{cutoff, parameters}`) is kept in `yield_estimator.py` and read from `settings['task_yield_profiles']`.
- `ctx.settings` of this episode must hold: `resource` (the PBS resource configuration, kind `pbs_ssh`), `coordinator_workspace`, `initial_information`, `launch_instructions_directory`, `tool_knowledge_directory`, `task_yield_profiles` (cost > 0 below the completion target). The service `job_access` must be supplied to `link`.
- The tool reads the real clock (`started_at`, `finished_at`, each validation's `checked_at`) and returns the receipt in its outcome; two attempts of one unit (resume) produce receipts that differ in those times.

## Not repaired

Limits of the system, contract or guide; none is worked around.

- credit_vs_completion_target: credit is the sum of all satisfied requirements (old formula, kept), the completion target is the credit of the completion keys only; credit may pass its target (cwd 1.0 + handoff 4.0 = 5.0 against 4.0) and the controller's ValueError is the failure.
- BLOCKED-ON-JOB-SERVICE: job_access.exec_command does not exist; the tool raises at the call.
- BLOCKED-ON-JOB-SERVICE: JOB_LEDGER job record kind; a handoff receipt raises after the receipt artifact is saved.
- BLOCKED-ON-STORE-ACCESS: receipt as a Store source (PracticalReceiptInformation.publish/resolve), PracticalState files, and handing record_refs to a command.
- execution_result_origin (null has no form type) and the object family sources raise when selected.
- The 21 execution.<name> sources are not lowercase identifiers; the A104 BV-BRC data fact sources have no A104 copy.
- Seven unplaced old functions (see above).
- Real clock in the tool: a rerun after resume gives a receipt with different times.
