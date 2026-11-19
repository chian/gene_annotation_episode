# Blocked, unplaced and misfit items: A103 local_job_execution (19 November 2026)

## blocked_on_store_access

- `episode_support/records/practical_receipt_information.py::PracticalReceiptInformation.publish` (old call in `terminal_operations.execute` and `terminal_report.facts`: `PracticalReceiptInformation(self.store, context.run_id).publish(context, receipt)`). Pattern: "library not carried". It runs raw SQL on `store.db` (`records` by provider and accession, `sqlite_master`, `runtime_actions`, `runtime_episodes`) and needs the old `BindingContext`. Not called. The tool writes the receipt itself as an artifact (`ctx.store.artifact(canonical(receipt), 'application/json')`) and returns its reference as `receipt_ref` (this is the episode's own call; it needs no library). Intended: a library `publish(store, receipt)` over `store.artifact` and a work table.
- `result_records.py::_masking_inputs` and `_utility_inputs` (old calls `native_blast_masking_results.validate_job_inputs(context, assignment)` and `native_blast_utility_results.validate_job_inputs(context, assignment)`, old Store reads of the sequence inputs a requested job names). Not carried: the providers are not in `episode_support/`. The input records ride in the new optional `record_refs` assignment field.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access`; wanted call: `await ctx.services["job_access"].exec_command(arguments["assignment"], arguments["arguments"], key=ctx.operation_key)` returning `{'receipt': <practical_action_receipt_v1>, 'handoff': <native job handoff or None>}`. It is what the old `TerminalOperations.execute` did: `state.begin(operation_key, ...)` (idempotent on the key), `TerminalExecution.execute`, `finalize_scientific_command`, `assess_validations`, `state.finish(...)` (the practical state is a directory of intents and receipts outside the Store). The tool raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.exec_command ...')` where the call is made, and the link refuses without a `job_access` factory (`LinkError('service_required:...')`). Nothing of the service is written.
- BLOCKED-ON-JOB-SERVICE: reading the Store records named by a native masking or utility job (`record_refs`) for the staged job inputs: the service is handed no custody; no job record kind carries them yet.

## unplaced_old_functions

- `contracts.py::launch_operation_catalog`: operation of the parent role launch; launch_local never offered it.
- `contracts.py::native_result_operation_catalog`: operations of the results role.
- `internal_summary.py::NativeSummary.resource_tool_contracts`: contracts of every resource of the parent's routes.
- `credit.py::_live_project_credit` native result-family branches (masking, utility, standard database, native database, hmmer preparation, blast, hmmer): the `applies(context)` of each tests a results assignment (`execution_results_assignment_v1`); this episode's form admits only `practical_assignment_v1`, so none can apply. Their providers are not in `episode_support/`.
- `completion.py::completion_for_action` native result-family branches: same reason.
- `result_records.py` (`_masking_selector`, `_retained_masking_target`, `_utility_selector`, `_retained_utility_target`, `_target`, `_selector`, `_result_directory`, `_windows`, `_selected_result_action`, `_validate_result_body`, `_read_result`, `_selection`): the result-acquisition role.
- `result_records.py::_has_appservice`, `_has_uniprot`, `_appservice_sources`: api resources only.
- `received_information.py` (all methods): forwarded report sources and facts for the roles annotation and gene_context_evidence.
- `decision_inputs`: child options, completed_action_reports, the hpc requested_action_history, pending_work, execution_expectations, resource_tool_estimates, native_execution_expectations, native_event_targets and waiting_support are not carried: no service supplies them (estimate table, resource estimator, native event information are not provided) and wait is not an action.
- `yield_estimator.py::_request_yield_class` and `_task_yield_profile`: the profile key `launch_local:<request class>`; see contract_misfits.

## contract_misfits

- new field: local_job_execution record_refs (the job input records the old `initial_references` named, passed in custody; optional)
- new field: local_job_execution scientific_task (optional: the scientific parent task, `scientific_question` and `selected_tool_info`, which the old `services.scientific_parent_task` supplied for the `selected_execution_task` context)
- new field: local_job_execution finding (record: practical_completed, endpoint, commands_run, satisfied_keys, unsatisfied_keys, failures). The old report had no typed finding; this is not an A105/A108 evidence episode.
- new field: local_job_execution completion target: `read_from_parent` returns `completion_target` = the sum of the credits of the assignment's `completion_keys`. The old assignment carries no target.
- new field: local_job_execution settings: `resource` (the configuration of the local resource), `coordinator_workspace`, `launch_instructions_directory`, `tool_knowledge_directory`, `cost`, `parameters` (the old binding configuration).
- completion credit may pass its target: the credit sums every satisfied requirement while the target is the credit of the completion keys. Requirements outside `completion_keys` that are satisfied, or completion keys satisfied before the endpoint predicate holds on the last receipt, make the controller raise `ValueError('completion_credit_exceeds_target')` or stop earlier or later than the old verified completion. After a verified completion the service refuses a further command (`practical_assignment_already_completed`); credit.py was not changed (no min, max or clamp).
- BLOCKED-ON-JOB-SERVICE: see above (`job_access`).
- The 21 sources named `execution.masking_*` and `execution.blast_utility_*` of the old `fact_sources` are not lowercase identifiers (`^[a-z][a-z0-9_]*$`): no `RecordForm` can declare them, so RETURN_FORM omits them. They were always empty for launch_local.
- Two old family sources have an `object` type (`execution_blast_database_acquisition`, `execution_blast_standard_database_acquisition`) and their empty value (`empty_facts` of the old result providers) is not in `episode_support/`; `execution_result_origin` was null when empty and no form type is null. `final_to_parent` raises `NotImplementedError` when the parent selects one of these three.
- The old `execution_handoff_refs` were Store source records read through the old job progress provider; here they are the artifact references of the saved receipts whose reply carried a handoff, which only the (missing) service can tell. The old `practical_receipt_refs` were published `source_...` records; here artifact references.
- The old yield profiles were keyed by request class (`launch_local:practical_local_<native families>_<handoff|outputs>`), each with its own cutoff and parameters. The `continuation` settings hold one entry per binding path, so one cost and one parameter set serve every request class.
- The baseline validations of the initial context are assessed with a fixed `checked_at` (`1970-01-01T00:00:00+00:00`) so that the summary stays a pure function of the view; the old state recorded the time of the baseline.
- `decide` reads the frozen launch-instruction and tool-knowledge libraries from directories named in settings (README 7a); the files are outside custody and outside the recorded service reads.
- `validate_form` of the axis (`forms/gene_context_evidence/communication.py`) is not used: the report is a typed record form, not a JSON-Schema form with `x-source` fields; `validate_report` keeps the old fact-equality check.
- The first controller observation may already hold credit (the baseline satisfies requirements of the initial context); `initial_credit` passed to the completion controller must be below the target or the controller raises.
