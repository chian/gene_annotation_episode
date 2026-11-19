# a104 / execution_job_submission / api_job_execution: blocked, unplaced, misfits

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: the `job_access` service (declared in `task.py` `SERVICES`); wanted calls, all in `task.py`:
  `ctx.services['job_access'].read('launch_catalog', assignment)` (decide and action),
  `ctx.services['job_access'].read('capabilities', resource_id)` (decide),
  `ctx.services['job_access'].launch_operation(assignment, name, arguments, inputs=held, key=ctx.operation_key, resumed=ctx.resumed)`
  (tool `launch_operation`; returns `{status, event, feedback, submission_outcome, response, handoff, results}`;
  idempotent on `key`; one original remote-mutating submission; an unknown reply after a restart is reported as
  unknown). It stands for the old `APIJobService`, `HMMERJobService`, `AppServiceSubmission` and `AppServicePublication`
  executors with their per-operation files and SQL tables. The link of a run refuses until a factory supplies it.
- BLOCKED-ON-JOB-SERVICE: job record kind (the handoff row of the job ledger work table); wanted call:
  `ctx.store.table(JOB_LEDGER).put({'job', 'event': 'handoff', 'at', 'detail', 'source_ref'})` in tool `launch_operation`
  and `records.table(JOB_LEDGER).get(row_ref)` in `messages/internal_summary.py` `_initial_identities` (for an input
  ref that is a `row_` reference). `task._job_ledger()` raises `NotImplementedError` at the start of the tool, before
  any side effect; `_initial_identities` raises only when a `row_` reference is among `input_refs`.

## BLOCKED-ON-STORE-ACCESS

None. The library functions this episode calls (`time_accounting`, `rejection_feedback`, `generation_schema`,
`decode_response`, `LaunchInstructions`, `ToolKnowledge`, the `*_fact_sources` schema functions) touch no Store.

## Unplaced old functions (reason; the rows are in the intent record, "Carried over")

- `api_service.py` APIJobService methods `__init__`, `_legacy_context`, `_index_result`; `hmmer_service.py` HMMERJobService
  `__init__`, `_http`, `_failure`, `_prepare`: the executor and its durable state (job_access, above).
- `appservice_publication.py`, `appservice_submission.py` (all rows): BV-BRC AppService receipts, bundle publication and
  grading; need `job_access` and library modules (`appservice_record_access`, `appservice_record_values`,
  `appservice_publication_records`, `appservice_publication_values`) that are not in `episode_support`.
- `parent_launch_contract.py`, `scientific_inputs.py`, `from_parent.py` `_check_parent_inputs`: the child's re-validation of its
  commission against the parent's original launch request: not carried (a wrong commission fails).
- `presentation.py` `present_api_context`: the text renderers (`render_api_launch_prompt`, `render_selected_execution_prompt`,
  `render_hpc_prompt`, `render_monitor_prompt`, `render_receiver_prompt`) live in the old shared root, which is not read;
  `decide` gives the model its context as a mapping.
- `protected_reference_access.py`, `received_execution_records.py`, `received_reference_access.py`, `received_result_records.py`,
  `received_selector_contracts.py`, `result_operation_information.py`, `resource_operation_information.py`,
  `terminal_receipt_state.py`: functions of the results role, of a receiving parent, or of the local/hpc routes that were
  copied into this folder; they belong to `execution_result_acquisition`, the receivers, `local_job_execution` and
  `hpc_job_execution`.
- `resource_information.py` `resource_tool_contracts`: tool contracts with commission routes for other episodes' tools.
- Library modules not in `episode_support` (so their uses raise or are absent): `bvbrc_data_host` / `bvbrc_data_views` for A104
  (the `execution_bvbrc_*` fact sources), `bvbrc_homology_returns`, `bvbrc_phylogeny_returns`, `bvbrc_proteome_returns` (their
  fact sources and `bvbrc_appservice_support_refs`), `execution_input_versions`, `native_hmmer_acquisition`,
  `a104_homology_execution` (`BLAST_GRADED_RETURN_SOURCE`, `execution_blast_pairwise_result_refs`, `execution_result_origin`
  schema), `native_profile_presentation`. `RETURN_FORM` does not declare the fields they made.

## Contract misfits

- new field: api_job_execution input_refs (record_refs): the records the request names (the old code re-read them from the
  parent's launch request and the old `initial_references`); the launch passes them in custody.
- new field: api_job_execution handoff_unit; new field: api_job_execution acquired_record_unit (the old units were configuration of the
  binding; credit has no settings, and the completion target must come from the parent input).
- new field: api_job_execution message.scientific_question and message.selected_tool_info (read from the commission
  message in `read_from_parent`; the old code asked `services.scientific_parent_task`).
- Settings this episode reads (the `continuation` entry of its binding path): `resources`, `initial_information`,
  `task_yield_profiles` (`launch_api:<class>` -> `{cutoff, parameters}`), `launch_instruction_directory`,
  `tool_knowledge_directory`. `decide` reads the two directories (frozen document libraries) round `ctx`, so those reads
  are not journaled.
- completion credit may pass its target: the target is `handoff_unit`, reached by the one original handoff; the old
  formula also adds `acquired_record_unit` for each new result identity (an AppService launch that acquires results), which
  would exceed the target and raise `completion_credit_exceeds_target` from the controller. The old formula is kept.
- Form field names must be lowercase identifiers: the old fact sources `execution.masking_*` (7) and
  `execution.blast_utility_*` (14) have a dot and are not declared in `RETURN_FORM`; a selection naming one raises `FormError`.
- The form has no null type: `execution_result_origin` (always null for this episode) is declared selectable and
  selecting it raises; the two object-valued sources `execution_blast_database_acquisition` and
  `execution_blast_standard_database_acquisition` have no value for a launch and raise when selected.
- The old `wait` action permitted for `api_service_assignment_v1` is wait machinery and is not carried; this episode has no child
  and no native event target.
- `final_to_parent.validate_report` checks the report's fact fields against the facts of the summary. The old
  `validate_form(form, schema, resolver)` and the masking/utility/UniProt received-report validators need a JSON-schema
  form and received reports; A104 has `validate_form` but there is no schema to give it.
- No test runs the real runner: it needs the `job_access` factory, which does not exist. `tests/test_binding.py` runs the
  class-definition check, the form, credit, controller and result functions on real data.
- Folder residue: `api_job_execution/configuration.py` is deleted (nothing imported it). Deleted earlier: `api_job_binding.py`, `runtime_source.py`, `runtime_credit.py`, `appservice_source.py`. Still importing the deleted `appservice_source` (other folder, not touched): `episode_support/acquisition/service_calls/evolutionary_history_evidence/appservice_results.py`.
- The old `wait` action (permitted for `api_service_assignment_v1`) is wait/suspension machinery and is not carried.
- Source note: no `.git` in the working tree; old code was read from `/home/chia/repos/gene_annotation_episode_disk/.git`. The old files of this episode are the same as those of the `hpc_work_planning/execution_job_submission/api_job_execution` carry apart from the binding path and `parent_launch_contract.py`, so the ten files are a private copy of that carry's shape with this BINDING_PATH.


## Not repaired

- stale import outside the folder: `episode_support/acquisition/service_calls/evolutionary_history_evidence/appservice_results.py:46` imports the deleted `appservice_source`; library file, not edited in this step.
- BLOCKED-ON-JOB-SERVICE: `job_access` service and job record kind; wanted call: ctx.services['job_access'] (task.py), row_ refs in internal_summary.
- completion credit may pass its target: handoff_unit target vs acquired_record_unit per result identity (old formula kept).
