# hpc_resource_work_execution (A103, launch_hpc): blocked, unplaced and contract misfits

Carried as a private copy of the carried sibling `api_resource_work_execution` with the role `launch_hpc`, kind `hpc` and the HPC goal text (the old folders were byte-identical except for those). The working tree has no git history, so the old files were read from `gene_annotation_episode_disk` at 97308b94c for the differences only.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: the `resource_adapter` service (explicit adapters keyed by `resource_id`, the old `services.capabilities` / bound adapters; the A103 HPC adapter lived in the deleted shared root; no library module wraps it); wanted call: `ctx.services['resource_adapter'].execute(assignment, tool, arguments, held, key=ctx.operation_key)` (also `declared_capabilities`, `bound_resource_ids`, `adapter_capabilities`, `catalog`, `prepare_assignment`, `check_handoff`, `facts`, `credit_view`, `decision_context`), idempotent on the key, in `task.py resource_operation`. Declared in `SERVICES`; a run without it fails at link. Nothing is stubbed.
- BLOCKED-ON-JOB-SERVICE: the `native_events` service (`NativeEventLedger`: `validate_event_targets`, `wait_events`, `targets`); wanted call: `await selected_wait(ctx.services['native_events'], condition)` and `ctx.services['native_events'].read('targets', assignment)`.
- BLOCKED-ON-JOB-SERVICE: the job record kinds (handoff, check, closure; `JOB_LEDGER`): no module declares them; the episode writes only each handoff as an artifact through `ctx.store.artifact` and returns the references (`execution_handoff_refs`).

## BLOCKED-ON-STORE-ACCESS

- none new: `ctx.store.get/refs/artifact/commit_reasoning` and `records.holds/reasoning_schema` are the custody operations used. Library modules imported are the carried ones named in `task.py` (`jobs.waiting.selected_wait`, `instructions.*`, `tools.tool_knowledge`, `records.progress_views`, `records.hpc.resource_records`). Not verified here that each is in final form beyond importing.

## UNPLACED OLD FUNCTIONS

- `action_contract_feedback.py` repair hints (contract-information, component-native return channels, BV-BRC MinHash results selector, `reads.map` parameter feedback): not carried; the rejection is `Rejected(rejection_feedback(error, category='action_contract'))`. `read_mapping.parameter_schema_failure` lived in the old shared root.
- `decision_inputs.py` `execution_expectations` (`launch_hpc`, `job_execution_options`), `resource_tool_estimates` from the resource estimator, `native_execution_expectations`, `requested_action_history` (`library.hpc_prompt.is_hpc_context`, shared root, not read): not carried; the adapter's `decision_context` read supplies `resource_tool_estimates`.
- `from_parent.py` parent-equality, instruction-pin inheritance and resource_selection inheritance checks: checks of a commission; a wrong commission fails.
- `initial_references.py` adapter initial references (role `results` only, never this role).

## CONTRACT MISFITS

- BLOCKED-ON-JOB-SERVICE: `resource_adapter`; wanted call: `await ctx.services['resource_adapter'].execute(assignment, tool, arguments, held, key=ctx.operation_key)`
- BLOCKED-ON-JOB-SERVICE: `native_events`; wanted call: `await selected_wait(ctx.services['native_events'], arguments['condition'])`
- new field: hpc_resource_work_execution assignment `scope`, `scope_refs`, `input_refs`, `completion_target` (the old request message/runner carried them; the completion controller needs the target).
- new field: hpc_resource_work_execution return `adapter_facts` (the adapter's own fact sources are defined at run time) and `execution_handoff_refs`; form has no null so `execution_handoff` is `{}` for zero or several identities.
- new field: hpc_resource_work_execution finding (the old report had none): `resource_id`, `kind`, `availability`, `usable_handoff`, `qualification`.
- new field: settings read by the episode: `cost`, `parameters`, `tool_knowledge_directory`, `launch_instructions_directory`.
- new field: tool arguments carry `assignment` and `held_refs` added by `action` from the summary.
- no validate_form needed: A103's report is checked by `validate_report` in final_to_parent.
- completion credit may pass its target: the adapter's credit view is used unchanged and nothing bounds it against `completion_target`; the controller's own ValueError is the failure.
- old per-role `launch_hpc` job-execution expectations (HPC wall-time/queue estimates) have no service; the adapter's `decision_context` is the only source.
