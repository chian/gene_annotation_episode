# Blocked and unplaced: a102/structural_homology_evidence/execution_job_submission/local_job_execution

## BLOCKED-ON-JOB-SERVICE
- BLOCKED-ON-JOB-SERVICE: `job_access` (service, no implementation); wanted calls, all in `task.py exec_command`, each raising NotImplementedError at the call when the service lacks the method:
  - `await ctx.services["job_access"].begin_command(assignment, "exec_command", arguments, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)` (old `PracticalState.begin`: idempotent by operation key, a completed intent returns its receipt, reply `{state, intent, receipt}`)
  - `await ctx.services["job_access"].run_command(assignment, arguments, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)` (old `TerminalExecution.execute`)
  - `await ctx.services["job_access"].finish_command(key, outcome, validations, context_after=after)` (old `PracticalState.finish`, returns the immutable receipt)
- The service's durable practical state (intents, receipts, working context; old `TerminalState`, `PracticalState` directory) has no work table declared (no job record kind exists).

## BLOCKED-ON-STORE-ACCESS
- function = records/practical_receipt_information.py::PracticalReceiptInformation.publish / read / resolve; pattern = "library not carried" (store.db on `records`, `runtime_actions`, `runtime_episodes`; takes the old `BindingContext`). Old call -> intended call: `PracticalReceiptInformation(store, run_id).publish(context, receipt)` -> a custody-aware publish over `ctx.store`. Not called: `task.py publish_receipt` writes the same `source` record (provider `episode.practical_receipt`) through `ctx.store.put`; its body drops `scope` (the assignment has no scope now), so the old reader (`BODY_FIELDS` includes `scope`) would refuse it.
- function = findings/structural_homology_evidence/terminal_scientific_evidence.py::read_terminal_handoff, validate_terminal_handoff, captured_terminal_file, terminal_native_snapshot, validate_terminal_native, validate_terminal_observation (store.db / old receipts); pattern = "library not carried". Not called by this episode (only `finalize_scientific_command` and `terminal_artifact_paths`, which touch no Store, are).

## unplaced_old_functions
- contracts.py: launch_operation_catalog, native_result_operation_catalog, _outcome (catalogs of the launch/results operations for the parent's catalog; not this episode's own tool).
- internal_summary.py NativeSummary.resource_tool_contracts: the same, per resource, for the parent's catalog.
- result_records.py (ExecutionResultRecords and its methods): reading acquired results of received handoffs; a launch acquires none. The old import `execution_input_versions` has no module now.
- retained_protein_reader.py (NativeRetainedProteinReader and its methods): retained protein-structure read authority over store.db and runtime_episodes; a launch retains none.
- The old check of `immutable_input_versions` of the commissioning launch request (from_parent._validate_request): no module and it read runtime_episodes; not carried.
- received_information.py: the protein-structure fact sources and `execution_file_source_refs` / `execution_file_capture_outcomes` offered to annotation/structural receivers: no library module for them (`protein_structure_result_views`, `local_file_capture_results` not placed); not in RETURN_FORM.
- configuration.py: the builders of API execution, the progress provider, local-file sources and the native protein-structure results/returns have no use in a local launch leaf and are not carried.
- The native protein-structure presentation of `selected_execution_task` (internal_summary._with_selected_execution_task, `services.scientific_parent_task`): rebuilt from the intent record (question, selected_tool_info, request); the old file could not be read (no git).

## contract_misfits
- new field: local_job_execution record_refs (records the job inputs name, passed in custody).
- new field: local_job_execution scientific_task (scientific_question and selected_tool_info, old `services.scientific_parent_task`).
- `execution_result_origin` was null when no result is retained; a form has no null: selecting it raises NotImplementedError('no_null_form_type:execution_result_origin').
- Where the axis has no validate_form (A102): the old episode called none for this report; none written.
- The old files at 97308b94c could not be read (the checkout has no .git); the carry-over follows the intent record, the function list, the library, and the structurally identical carried sibling `hpc_work_planning/execution_job_submission/local_job_execution` (a private copy). The yield class suffix `_native_*` is derived from the native job keys of `requested_job`; the native job family allowed on a resource (`native_protein_structure`) is inferred.
- `read_from_parent` raises when a requirement earns credit outside `completion_keys` (the old hook-era port's check).
- Completion credit cannot pass its target: the credit is the sum of satisfied requirement credits and the target is the sum of all of them.
- The service reply shapes (`state`, `intent.context_before`, receipt) are those of `PracticalState`; the system fixes none.
- The finding is the episode's own handoff finding (not the typed investigation finding: this is not an A105/A108 evidence episode).
- The parent (`execution_job_submission`, role launch) writes the commission against ASSIGNMENT_FORM; the old parent-role and launch-assignment re-validation over `runtime_episodes` is machinery and not carried.
