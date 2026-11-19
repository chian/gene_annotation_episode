# Blocked, unplaced and misfit items: A104 execution_result_acquisition (19 November 2026)

Episode: `evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`. Carried
without git in the repository directory: the old files were read with `git -C <disk copy of the repository> show
97308b94c:<path>`. The generic native path (local or HPC resource, requested paths and byte windows) is carried in
full; it is the same shape as the A103 episode of the same name, as a private copy with A104's own library imports.
No test contacts a remote service; no unit can run until the `job_access` service and the handoff record kind exist.

## blocked_on_store_access

None. The episode calls no library function that touches the Store. The library functions it imports
(`readers/**/evolutionary_history_evidence/*_result_views.py` `*_fact_sources`,
`forms/sequence_and_context_sources/uniprot_return_contracts.py::uniprot_fact_sources`,
`records/evolutionary_history_evidence/domain.py`, `practical_execution_records.py`,
`jobs/evolutionary_history_evidence/practical_execution_operations.py::confined`, `model_exchange/**`) take values only.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (declared in `SERVICES`; no factory or class exists, so a link raises
  `LinkError('service_required:...')`). Wanted calls, idempotent on the key where they act:
  `ctx.services['job_access'].observe_target(target, key=ctx.operation_key)` (old
  `job_progress_provider.targets.observe_target`, returning `{'state', 'returncode', 'observed_at', ...}`);
  `ctx.services['job_access'].read_file(target, path=, offset=, limit=, key=ctx.operation_key + ':file:<i>')` (old
  `targets.read_file`, returning the window with `path`, `offset`, `returned_bytes`, `size_bytes`, `bytes_base64`;
  `ValueError` / `OSError` for an unavailable file).
- BLOCKED-ON-JOB-SERVICE: `job_access` reads in `decide`: `read('target', handoff_ref)` (old `targets.read_target`) and
  `read('target_description', handoff_ref, selector)` (old `targets.describe_target`).
- BLOCKED-ON-JOB-SERVICE: the job record kind handoff and its work table (`JOB_LEDGER` of the mechanics document);
  wanted call in `task.py _read_target`: `row = ctx.store.table(JOB_LEDGER).get(handoff_refs[0])` then
  `ctx.services['job_access'].read_target(row)`. `_read_target` raises `NotImplementedError`.
- BLOCKED-ON-JOB-SERVICE: the result host of a typed target (native BLAST masking, BLAST utility, standard or native
  BLAST database, HMMER preparation, HMMER, pairwise BLAST), of an API target (NCBI BLAST, EBI HMMER, BV-BRC data and
  AppService, UniProt) and of local file sources: their `applies`, `catalog`, `execute`, `credit_view`, `completion`,
  `facts`, `retained_target` and `validate_selected_inputs` (old `native_blast_masking_results`,
  `native_blast_utility_results`, `native_blast_standard_database_results`, `native_blast_database_results`,
  `native_hmmer_preparation_results`, `native_hmmer_results`, `native_blast_results`, `api_execution`,
  `local_file_sources`, installed by `install_primary_result_readers` / `install_preparation_result_readers` of the
  old shared root, not in the library). Wanted call: `ctx.services['job_access'].result_host(target)` with those
  members. `read_from_parent` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` for a selector with a
  `version` or for `resource_kind == 'api'`, so a typed commission fails at its start.
- BLOCKED-ON-JOB-SERVICE: for the typed and API targets the old controller was a completion with a target (the
  verified practical completion proof, `PracticalYieldEstimator`, profiles `results:typed_<kind>_<version>` and
  `results:api_<service>[_<version>]`); not built because the target's credit and completion are blocked as above.

## unplaced_old_functions

- `launch_operation_catalog` (`resource_operations.py`): `execution.capabilities` is an operation of the launch head.
- `received_launch_requests.py` (`_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`):
  launch request validation belongs to the launch role.
- `terminal_validation.py` (`TerminalExecutionBehavior`, `operation_catalog`): launch-side terminal behaviour; the
  launch episodes carry their own copy.
- `from_parent.py::required_return_sources`: `execution_result_refs` is a required field of RETURN_FORM instead.
- `received_parent_records.py` (`_has_appservice`, `_has_uniprot`, `_appservice_sources`, `_forwards_bvbrc_reports`,
  `received_report_sources`, `received_report_facts`, `received_report_closure_facts`): facts forwarded to a
  receiving `annotation` / `evolutionary_history_evidence` parent; that parent selects fields of RETURN_FORM.
- `report_fields.py` sources with no A104 library function: `bvbrc_data_fact_sources` (the library has copies only for
  A101 and A103, none for A104; `a104/bvbrc_data_views` is not placed), the AppService sources
  (`bvbrc_appservice_support_refs` and family, from `bvbrc_homology_returns`, not in the library), the BV-BRC minhash
  sources, and `BLAST_GRADED_RETURN_SOURCE` / `BLAST_GRADED_RETURN_SCHEMA` (`a104_homology_execution`, not in the
  library): none is declared in RETURN_FORM.
- `resource_information.py` (all four methods): resource information, capabilities and tool contracts; need
  `job_access` reads.
- `scientific_inputs.py`, `target_custody.py`: masking and utility job inputs and the target custody (result host and
  handoff record, blocked).
- `presentation.py::present_results_context`: renderer selection by prompt kind; `decide` sends the structured context
  with the instruction text.
- `instructions.py`: tool-knowledge, launch-instruction library, pending-child redelivery, wait and native event
  target text are not carried (those actions and libraries are not offered to this episode).
- `protected_reference_access.py`, `received_reference_access.py`, `report_reference_access.py`,
  `received_report_admission.py`: reference resolvers and admission over old receipts (machinery).
- Local file sources (`execution_file_source_refs`, `execution_file_capture_outcomes`): declared selectable and valued
  as empty for a generic native acquisition (as the old empty facts); the capture itself is blocked (result host).
- A generic native acquisition cannot show the typed families' live facts: selecting a record-valued typed field
  raises `ValueError('a_generic_native_acquisition_has_no_value_for:<name>')`; a list-valued one returns `[]`.

## contract_misfits

- BLOCKED-ON-JOB-SERVICE: job_access.observe_target and read_file, the reads `target` and `target_description`, the
  handoff record kind / `JOB_LEDGER`, and the typed / API result host; wanted calls: see the items above.
- new field: execution_result_acquisition resource_kind (ChoiceField `local`, `hpc`, `api`): the old code read the
  target through the job provider; the parent now copies it from the handoff it holds, because `yield_estimator.py`
  may read only `parent_input`.
- new field: execution_result_acquisition workspace (text): confines the requested paths; the old code read it from
  the target.
- new field: execution_result_acquisition acquired_record_unit (number, positive): was the configuration value; credit
  has no settings, so the credit unit travels in the assignment. The old `handoff_unit` (always multiplied by a count
  fixed at 0) is not carried.
- new field: execution_result_acquisition initial_result_refs and initial_result_artifact_refs (record_refs,
  optional): the old initial known record references (receipt inheritance); the parent names each earlier
  `episode.execution_result` source and its artifact (a passed record does not bring the records it names).
- `handoff_ref` is a `record_refs` field (a list of exactly one reference), not text: custody requires it.
- Tool names `execution.results.status|collect|read` become `execution_results_status|collect|read` (a tool name is
  `[a-z][a-z0-9_]*`); fact sources with a dot (masking, BLAST utility families) keep the dot-to-underscore rename. This
  renames them against "names both sides use are the old names".
- A form has no null: `execution_result_origin` (null when nothing is retained) is selectable, and selecting it with no
  retained window raises `ValueError('a_generic_native_acquisition_has_no_value_for:execution_result_origin')`.
- Bounded quality maximum: the old maximum was `acquired_record_unit` times the fraction the earlier results left
  uncovered; `yield_controller` has no records, so the maximum is `acquired_record_unit`. Credit counts only new
  positions, so it never exceeds the old maximum; only the forecast bound is looser. The old exact-zero forecast and
  the practical-endpoint estimate are not carried (only the controller stops).
- Settings: the caller's `continuation` entry for this binding path carries `log_window_bytes` (the `collect` window) and
  `results_yield_profiles['native_unbounded_<local|hpc>']` or `task_yield_profiles['results:native_finite_<local|hpc>']`
  with `{'cutoff', 'parameters'}` (a missing profile raises `results_original_task_yield_profile_required:<key>`).
- After the acquisition is complete a further action is not rejected: it is a returned `invalid` outcome
  (`execution_results_assignment_already_completed`, as the old refusal) and enters the iterator with credit
  unchanged; the system has no end action, so the controller stops the Episode when the forecast falls to the cost.
- The tool arguments carry the model's operation plus the requested windows, the handoff references and the completion
  flag (`operation`, `requested`, `handoff_refs`, `completed`): a tool is handed only its arguments and `ctx`.
- `execution_result_refs` is required in RETURN_FORM (the old `required_return_sources` forced it under the
  `evolutionary_history_evidence` parent when an annotation task was required); the other fact sources are selectable.
- A104 is not an A105/A108 literature episode: the typed `investigation_finding` does not apply; `finding` is this
  episode's own acquisition finding.
- No old test existed for this folder at `97308b94c`; `retired_tests/<this episode>.tsv` has only its header.
