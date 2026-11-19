# Blocked, unplaced and misfit items: A104 execution_result_acquisition (19 November 2026)

Episode: `evolutionary_history_evidence/hpc_work_planning/execution_result_acquisition`. The old files were read with
`git --git-dir=<disk copy of the repository> show 97308b94c:<path>` (the repository directory has no `.git`). The folder
had only `__init__.py`; nothing was deleted. The old code of this folder is the same as the A103 sibling's old code (same
goal text, credit, yield, completion); the files are private copies with the A104 library modules. The generic native
path (local or HPC resource, requested paths and byte windows) is carried in full. No test contacts a remote service; no
unit can run until the `job_access` service and the handoff record kind exist.

## blocked_on_store_access

None. The episode calls no library function that touches the Store. The library functions it imports
(`readers/**/evolutionary_history_evidence/*_result_views.py` `*_fact_sources`, `records/evolutionary_history_evidence/domain.py`,
`practical_execution_records.py`, `jobs/evolutionary_history_evidence/practical_execution_operations.py::confined`,
`model_exchange/**`) take values only.

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (declared in `SERVICES`; no factory or class exists, so a link raises
  `LinkError('service_required:...')`). Wanted calls, idempotent on the key where they act:
  `ctx.services['job_access'].observe_target(target, key=ctx.operation_key)` (old `job_progress_provider.targets.observe_target`);
  `ctx.services['job_access'].read_file(target, path=, offset=, limit=, key=ctx.operation_key + ':file:<i>')` (old `targets.read_file`).
- BLOCKED-ON-JOB-SERVICE: `job_access` reads in `decide`: `read('target', handoff_ref)` (old `targets.read_target`) and
  `read('target_description', handoff_ref, selector)` (old `targets.describe_target`).
- BLOCKED-ON-JOB-SERVICE: the job record kind handoff and its work table (`JOB_LEDGER`); wanted call in `task.py _read_target`:
  `row = ctx.store.table(JOB_LEDGER).get(handoff_refs[0])` then `ctx.services['job_access'].read_target(row)`. `_read_target` raises
  `NotImplementedError`.
- BLOCKED-ON-JOB-SERVICE: the result host of a typed target (masking, BLAST utility, standard or native BLAST database, HMMER
  preparation, HMMER, BLAST), of an API target (also AppService, BV-BRC, UniProt, EBI HMMER) and of local file sources: their
  `applies`, `catalog`, `execute`, `credit_view`, `completion`, `facts` and `validate_selected_inputs` (old
  `native_blast_masking_results`, `native_blast_utility_results`, `native_blast_standard_database_results`,
  `native_blast_database_results`, `native_hmmer_preparation_results`, `native_hmmer_results`, `native_blast_results`,
  `api_execution`, `local_file_sources`). Wanted call: `ctx.services['job_access'].result_host(target)` with those members.
  `read_from_parent` raises `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` for a selector with a `version` or for
  `resource_kind == 'api'`, so a typed commission fails at its start.
- BLOCKED-ON-JOB-SERVICE: for typed and API targets the old controller was a completion with a target (verified practical
  completion proof, `PracticalYieldEstimator`); not built because credit and completion of those targets are blocked as above.

## unplaced_old_functions

- `execution_contracts.py::launch_operation_catalog` (`resource_operations.py`): `execution.capabilities` is an operation of the launch role.
- `received_launch_requests.py` (`_permitted`, `_request_schema`, `_validate_request`, `_launch`, `_constraints`): launch request validation belongs to the launch role.
- `from_parent.py::required_return_sources`: the parent selects `execution_result_refs` in its `msg_to_child`; it is a required field here.
- `received_parent_records.py` (all): facts forwarded to annotation receivers; that parent selects fields of RETURN_FORM.
- `resource_information.py` (all four methods): needs `job_access` reads (BLOCKED-ON-JOB-SERVICE).
- `scientific_inputs.py`, `target_custody.py` (retained masking / utility target, `_context_target`), `selector_contracts.py` (`_masking_selector`, `_utility_selector`): typed target access, result host blocked.
- `terminal_validation.py` (`TerminalExecutionBehavior`, `operation_catalog`): launch-side behaviour; the launch episodes carry their own copy.
- `api_acquisition.py`, `appservice_acquisition.py`, `appservice_publication.py`, `hmmer_acquisition.py`, `native_blast_*_result_acquisition.py`, `native_hmmer_*_result_acquisition.py`: result hosts of API and typed native targets, blocked as above.
- `to_parent.py` sources `bvbrc_data_*` (old `bvbrc_data_views.bvbrc_data_fact_sources`): there is no `readers/sequence_and_context_sources/evolutionary_history_evidence/bvbrc_data_views.py` (only the sequence_homology and gene_context copies exist), so these fields are not declared in RETURN_FORM. The `uniprot_*`, AppService and `BLAST_GRADED_RETURN_SOURCE` sources are API-only and not declared either (`uniprot_return_contracts` is not an A104 library module; `homology_fact_sources` is in no module).
- `presentation.py::present_results_context`: the text renderer `render_selected_execution_prompt` lives in the old shared root and is not carried; `decide` passes the context mapping (README 5 item 16).
- Local file sources (`execution_file_source_refs`, `execution_file_capture_outcomes`): declared selectable, an empty list for a generic native acquisition; the capture is the blocked result host.
- A selectable record-valued typed field raises `ValueError('a_generic_native_acquisition_has_no_value_for:<name>')`; a list-valued one returns `[]`.

## contract_misfits

- BLOCKED-ON-JOB-SERVICE: job_access.observe_target and read_file, the reads `target` and `target_description`, the handoff record kind / `JOB_LEDGER`, and the typed result host; wanted calls above.
- new field: execution_result_acquisition resource_kind (ChoiceField `local`, `hpc`, `api`): the old code read it from the target; the parent copies it from the handoff it holds, because `yield_estimator.py` may read only `parent_input`.
- new field: execution_result_acquisition workspace (text): confines the requested paths; read by the old code from the target.
- new field: execution_result_acquisition acquired_record_unit (number, positive): was the configuration value; credit has no settings, so the credit unit travels in the assignment. The old `handoff_unit` (always multiplied by a count fixed at 0) is not carried.
- new field: execution_result_acquisition initial_result_refs and initial_result_artifact_refs (record_refs, optional): the old initial known record references; the parent names each earlier `episode.execution_result` source and its artifact (a passed record does not bring the records it names).
- `handoff_ref` is a `record_refs` field (a list of exactly one reference), not text.
- Tool names `execution.results.status|collect|read` become `execution_results_status|collect|read`; the `masking_*` / `blast_utility_*` fact sources get dot-to-underscore field names (a form field name is a lowercase identifier). This renames them against "names both sides use are the old names".
- A form has no null: `execution_result_origin` (null when nothing is retained) is selectable; selecting it with no retained window raises in `final_to_parent`.
- Bounded quality maximum: the old maximum was `acquired_record_unit` times the fraction the earlier results left uncovered; `yield_controller` has no records, so the maximum is `acquired_record_unit`. Credit counts only new positions, so it never exceeds the old maximum; only the forecast bound is looser. The old exact-zero forecast and the practical-endpoint estimate are not carried.
- Settings: the `continuation` entry for this binding path carries `log_window_bytes` and `results_yield_profiles['native_unbounded_<local|hpc>']` or `task_yield_profiles['results:native_finite_<local|hpc>']` with `{'cutoff', 'parameters'}`.
- After the acquisition is complete a further action is a returned `invalid` outcome (`execution_results_assignment_already_completed`) with credit unchanged; the system has no end action, so the controller stops the Episode when the forecast falls to the cost.
- The old `validate_report` also ran `validate_form` (evolutionary_history `communication.validate_form`) over the parent-written JSON-Schema report form; the parent writes no form now (RecordForm, admitted by the system), so only the facts-agreement body is carried.
- The tool arguments carry the model's operation plus the requested windows, handoff references and completion flag (`operation`, `requested`, `handoff_refs`, `completed`).
- A104 is not an A105/A108 literature episode: the typed `investigation_finding` section does not apply; `finding` is this episode's own acquisition finding.
- Not a completion controller, so no "completion credit may pass its target" item.
- No old test existed for this folder at `97308b94c`; the retired_tests file has only its header.

## Not repaired

- The `reason` selection of old `task_action.py` is accounted, not carried: `permitted_common_actions` returned ('tool',) or ('tool','wait') and never 'reason', so the selection was not offered for this episode; `task.py` action accepts the three tools only.
- BLOCKED-ON-JOB-SERVICE items above (job_access, handoff record kind, typed and API result hosts) and the unplaced bvbrc_data_* / uniprot_* return sources: system limits, not repaired.
- Bounded-quality controller instead of completion with a target (yield_controller has no records): documented in contract_misfits.
