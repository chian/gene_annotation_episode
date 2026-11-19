# Blocked, unplaced and misfit items: A103 execution_result_acquisition (19 November 2026)

Episode: `gene_context_evidence/hpc_work_planning/execution_result_acquisition`. Carried
without git in the repository directory: the old files were read with `git --git-dir=<disk copy of the repository>
show 97308b94c:<path>` (the repository directory has no `.git`). The generic native path (local or HPC resource,
requested paths and byte windows) is carried in full. No test contacts a remote service; no unit can run until the
`job_access` service and the handoff record kind exist.

## blocked_on_store_access

None. The episode calls no library function that touches the Store; the library functions it imports
(`readers/**/*_result_views.py` `*_fact_sources`, `records/gene_context_evidence/domain.py`,
`practical_execution_records.py`, `jobs/gene_context_evidence/practical_execution_operations.py::confined`,
`model_exchange/**`) take values only.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (declared in `SERVICES`; no factory or class exists, so a link raises
  `LinkError('service_required:...')`). Wanted calls, all idempotent on the key where they act:
  `ctx.services['job_access'].observe_target(target, key=ctx.operation_key)` (old
  `job_progress_provider.targets.observe_target`, returning `{'state', 'returncode', 'observed_at', ...}`);
  `ctx.services['job_access'].read_file(target, path=, offset=, limit=, key=ctx.operation_key + ':file:<i>')` (old
  `targets.read_file`, returning the window with `path`, `offset`, `returned_bytes`, `size_bytes`, `bytes_base64`;
  `ValueError`/`OSError` for an unavailable file).
- BLOCKED-ON-JOB-SERVICE: `job_access` reads in `decide`: `read('target', handoff_ref)` (old `targets.read_target`)
  and `read('target_description', handoff_ref, selector)` (old `targets.describe_target`).
- BLOCKED-ON-JOB-SERVICE: the job record kind handoff and its work table (`JOB_LEDGER` of the mechanics doc); wanted
  call in `task.py _read_target`: `row = ctx.store.table(JOB_LEDGER).get(handoff_refs[0])` then
  `ctx.services['job_access'].read_target(row)`. `_read_target` raises `NotImplementedError`.
- BLOCKED-ON-JOB-SERVICE: the result host of a typed target (masking, BLAST utility, standard or native BLAST database,
  HMMER preparation, HMMER, BLAST), of an API target and of local file sources: their `applies`, `catalog`, `execute`,
  `credit_view`, `completion`, `facts` and `validate_selected_inputs` (old `native_blast_masking_results`,
  `native_blast_utility_results`, `native_blast_standard_database_results`, `native_blast_database_results`,
  `native_hmmer_preparation_results`, `native_hmmer_results`, `native_blast_results`, `api_execution`,
  `local_file_sources`, installed by `install_primary_result_readers`/`install_preparation_result_readers` of the old
  shared root, not in the library). Wanted call: `ctx.services['job_access'].result_host(target)` with those
  members. `read_from_parent` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` for a selector with a
  `version` or for `resource_kind == 'api'`, so a typed commission fails at its start.
- BLOCKED-ON-JOB-SERVICE: for the typed and API targets the old controller was a completion with a target (the verified
  practical completion proof; `PracticalYieldEstimator`); not built because the target's credit and completion are
  blocked as above.

## unplaced_old_functions

- `execution_contracts.py::launch_operation_catalog`: `execution.capabilities` is an operation of the launch head.
- `parent_input_custody.py` (`_permitted`, `_validate_request`, `_launch`, `_constraints`): launch request validation
  belongs to the launch role.
- `from_parent.py::required_return_sources`: the parent selects `execution_result_refs` in its `msg_to_child`.
- `received_records.py::_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_forwards_bvbrc_reports`,
  `_forwards_minhash_reports`; `to_parent.py` sources `uniprot_*` (`uniprot_return_contracts`), the AppService
  sources (`homology_fact_sources`), `bvbrc_minhash` sources (`minhash_fact_sources` exists in the library but is
  API-only), `BLAST_GRADED_RETURN_SOURCE` and `execution_blast_grader`: API-only, not declared in RETURN_FORM;
  `uniprot_return_contracts` and `homology_fact_sources` are not in the library.
- `received_report_facts.py` (`received_report_sources`, `received_report_facts`, `received_report_closure_facts`):
  facts supplied to a receiving annotation/gene_context_evidence parent; that parent selects fields of RETURN_FORM.
- `resource_information.py` (all four methods): resource information, capabilities, resource tool contracts; needs
  `job_access` reads (BLOCKED-ON-JOB-SERVICE).
- `decision_inputs.py::decision_inputs`: not carried because nothing supplies them: `launch_instruction_library` and
  its lookups, `shared_information_context`, `completed_action_reports`, `requested_action_history`,
  `execution_expectations`, `resource_tool_estimates`, `native_execution_expectations`, `native_event_targets`,
  `waiting_support`.
- `retained_masking_reader.py`, `retained_utility_reader.py`: typed target access (result host, blocked).
- `terminal_execution.py` (`TerminalExecutionBehavior`, `operation_catalog`): launch-side terminal behaviour; the
  launch episodes carry their own copy.
- `execution_state.py::_delegate`; `result_selection.py::_context_target`.
- Local file sources (`local_file_sources.*`, `execution_file_source_refs`, `execution_file_capture_outcomes`): the
  two fact sources are declared selectable and return an empty value for a generic native acquisition (as the old
  empty facts); the capture itself is blocked (result host).
- `ExecutionResultAcquisition` cannot show the typed families' live facts: selecting a record valued typed field
  raises `ValueError('a_generic_native_acquisition_has_no_value_for:<name>')`; a list valued one returns `[]`.

## contract_misfits

- BLOCKED-ON-JOB-SERVICE: job_access.observe_target and read_file, the reads `target` and `target_description`, the
  handoff record kind / `JOB_LEDGER`, and the typed result host; wanted calls: see the items above.
- new field: execution_result_acquisition resource_kind (ChoiceField `local`, `hpc`, `api`): the old code read the
  target through the job provider; the parent now copies it from the handoff it holds, because
  `yield_estimator.py` may read only `parent_input`.
- new field: execution_result_acquisition workspace (text): confines the requested paths; read by the old code from
  the target.
- new field: execution_result_acquisition acquired_record_unit (number, positive): was the configuration value; credit
  has no settings, so the credit unit travels in the assignment. The old `handoff_unit` (always multiplied by a
  count fixed at 0) is not carried.
- new field: execution_result_acquisition initial_result_refs and initial_result_artifact_refs (record_refs,
  optional): the old initial known record references (receipt inheritance); the parent names each earlier
  `episode.execution_result` source and its artifact (a passed record does not bring the records it names).
- `handoff_ref` is a `record_refs` field (a list of exactly one reference), not text: custody requires it.
- Tool names `execution.results.status|collect|read` become `execution_results_status|collect|read` (a tool name is
  `[a-z][a-z0-9_]*`); the `masking_*` / `blast_utility_*` fact sources keep the dot-to-underscore rename of their
  family functions. This renames them against "names both sides use are the old names".
- A form has no null: `execution_result_origin` (null when nothing is retained) is selectable and selecting it
  with no retained window raises `ValueError('a_generic_native_acquisition_has_no_value_for:execution_result_origin')`
  in `final_to_parent`.
- Bounded quality maximum: the old maximum was `acquired_record_unit` times the fraction the earlier results left
  uncovered; `yield_controller` has no records, so the maximum is `acquired_record_unit`. Credit counts only new
  positions, so it never exceeds the old maximum, only the forecast bound is looser. The old exact-zero forecast when
  no uncredited bytes remain and the practical-endpoint estimate are not carried (only the controller stops).
- Settings: the caller's `continuation` entry for this binding path carries `log_window_bytes` (the `collect` window)
  and `results_yield_profiles['native_unbounded_<local|hpc>']` or `task_yield_profiles['results:native_finite_<local|hpc>']`
  with `{'cutoff', 'parameters'}` (a missing profile raises `results_original_task_yield_profile_required:<key>`).
- After the acquisition is complete a further action is not rejected: it is a returned `invalid` outcome
  (`execution_results_assignment_already_completed`, as the old refusal) and enters the iterator with credit unchanged;
  the system has no end action, so the controller stops the Episode when the forecast falls to the cost.
- The tool arguments carry the model's operation plus the requested windows, the handoff references and the
  completion flag (`operation`, `requested`, `handoff_refs`, `completed`): a tool is handed only its arguments and
  `ctx`.
- A103 is not an A105/A108 literature episode: the typed `investigation_finding` of "Required literature evidence
  processing" does not apply; `finding` is this episode's own acquisition finding.
- No old test existed for this folder at `97308b94c`; `retired_tests/<this episode>.tsv` has only its header.
