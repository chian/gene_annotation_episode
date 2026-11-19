# Blocked and unplaced: a102/structural_homology_evidence/resource_work_submission/local_resource_work_execution

## BLOCKED-ON-JOB-SERVICE
- `job_access` (service, no implementation). Wanted calls, each in `task.py`, each raising NotImplementedError at the call when the service lacks the method:
  - `exec_command`: `await ctx.services["job_access"].begin_command(assignment, "exec_command", arguments, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)`, `.run_command(assignment, arguments, key=..., run_id=..., episode_id=...)`, `.finish_command(key, outcome, validations, context_after=after)` (old adapter `execute` over `PracticalState`/`TerminalExecution`).
  - `resource_check_handoff`: `await ctx.services["job_access"].check_handoff(handoff, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)` (old adapter `check_handoff(context, handoff, operation_key)`); the reply is taken in the shape of the old adapter outcome (`status, record_refs, changed_record_refs, result, feedback`) with `result` the checked `execution_handoff_v1`. The old `receiving_interface_unavailable` failure (adapter without `check_handoff`) has no equivalent: a service without the method raises.
- The service's durable state (intents, receipts, working context) has no work table declared (no job record kind exists).

## BLOCKED-ON-STORE-ACCESS
- function = records/practical_receipt_information.py::PracticalReceiptInformation.publish / read / resolve; pattern = "library not carried" (store.db on `records`, `runtime_actions`, `runtime_episodes`; takes the old `BindingContext`). Old call -> intended call: `PracticalReceiptInformation(store, run_id).publish(context, receipt)` -> a custody-aware publish over `ctx.store`. Not called: `task.py publish_receipt` writes the same `source` record (provider `episode.practical_receipt`) through `ctx.store.put` / `artifact`; its body drops `scope`.
- function = findings/structural_homology_evidence/terminal_scientific_evidence.py::read_terminal_handoff, validate_terminal_handoff, captured_terminal_file, terminal_native_snapshot, validate_terminal_native, validate_terminal_observation; pattern = "library not carried". Not called (only `finalize_scientific_command` and `terminal_artifact_paths`, which touch no Store, are).
- The proof records of an execution handoff (`check_record_refs`) are written by the service, outside custody; returning them in `execution_handoff_record_refs` raises CustodyError at the return unless the Episode holds them (no custody-aware path writes them yet).

## unplaced_old_functions
- configuration.py ResourceConfiguration.__init__ (adapter API check `explicit_resource_adapter_required`, `duplicate_resource_id`, `bind_record_selection`): per-run adapter objects do not exist; the configured resources and capabilities are settings.
- internal_summary.py ResourceInternalSummary.decision_context, the `resource_tool_estimates` part: the selected adapter's optional `decision_context` (prospective duration estimates) has no object or service to ask; no estimates are shown.
- decision_inputs.py: `execution_expectations`, `native_execution_expectations`, `resource_tool_estimates`, `waiting_support`, `requested_action_history`: need the old runner's estimator and waits; not carried.
- from_parent.py `_require_launch_child_instruction_pins`, `prepare_assignment` checks, resource_selection.py `_permitted`: checks of a commission (rule 1); not carried.
- to_parent.py ResourceToParent.validate_report: the call of the selected adapter's own `validate_report` (no adapter object); the handoff-fact check is kept.
- initial_references.py: returned references only for role `results`, never this role.
- report_reference_access.py resolve: report-form resolution through `reference_in_context` and the adapter; system custody now.

## contract_misfits
- new field: local_resource_work_execution adapter_assignment (the practical_assignment_v1 the selected adapter prepared from the launch request; the child has no adapter object to prepare it).
- new field: local_resource_work_execution scope (old `message['scope']`).
- new field: local_resource_work_execution record_refs (records the job inputs name, passed in custody).
- new field: local_resource_work_execution execution_handoff_record_refs (return: the proof records of the returned handoffs; the old `received_form_references`).
- Old tool names `resource.capabilities`, `resource.inspect`, `resource.check_handoff` are not valid tool names; they are `resource_capabilities`, `resource_inspect`, `resource_check_handoff`. The parent, which names them in its prompt, must use the new names.
- `execution_handoff` was null for zero or several identities and a form has no null: selecting it then raises NotImplementedError('no_null_form_type:execution_handoff').
- `resource_selection` was nullable in LAUNCH_SCHEMA; this role required a selection, so the field is a required record (a null would be a FormError).
- Where the axis has no validate_form (A102): the old episode called none for this report; none written.
- Completion credit cannot pass its target: the credit is the sum of satisfied requirement credits and the target is the sum of all of them (read_from_parent raises when a credited requirement lies outside completion_keys).
- The old folder had no yield estimator (the old runner's `task_yield_profiles` key `launch_local:<class>` governed). The completion controller with target from the job assignment follows README 7b (`PracticalYieldEstimator`) and the carried siblings; the intent record's inference (accumulation) was not followed because the old role's profile key is per request class and the credit is bounded by the declared requirements.
- The old adapter objects (resource_adapters) are not carried: the episode is an exec_command resource agent (shape of the carried sibling `execution_job_submission/local_job_execution`); the adapter's `catalog`, `execute`, `facts`, `credit_view` are tools over the `job_access` service, tool outcomes and the practical credit. The service reply shapes are those of `PracticalState`; the system fixes none.
- Settings the episode reads (`ctx.settings`): resources, resource_capabilities, initial_information, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles. The existing parent test `resource_work_submission/tests/test_resource_work_link.py` was written for the hook-era class and the earlier port's construction operands; it is not this episode's and was not touched.
- The model's answer is a tool name plus the JSON text of its arguments (the old action schema of this role was the old shared one and is not carried).
- The old files at 97308b94c were read from the history repository `gene_annotation_episode_disk` (the working checkout has no .git).
