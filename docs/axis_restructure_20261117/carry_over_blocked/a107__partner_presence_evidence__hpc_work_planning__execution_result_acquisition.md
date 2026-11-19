# Blocked, unplaced and misfit items: A107 execution_result_acquisition (19 November 2026)

Episode: `partner_presence_evidence/hpc_work_planning/execution_result_acquisition`. The old files were read with
`git --git-dir=/home/chia/repos/gene_annotation_episode_disk/.git show 97308b94c:<path>` (the repository directory has no
`.git`). The folder held `__init__.py` and a hook-era `episode.py` (class `ExecutionEpisode` on
`ResultAcquisitionBinding` and `DescendantBinding`); `episode.py` was deleted first, nothing else existed. The generic
native path (local or HPC resource, requested paths and byte windows) is carried in full; the typed and API targets are
not. No test contacts a remote service; no unit can run until the `job_access` service and the handoff record kind exist.

## blocked_on_store_access

None. The episode calls no library function that touches the Store. The library functions it imports
(`readers/**/partner_presence_evidence/*_result_views.py` `*_fact_sources`, `records/partner_presence_evidence/domain.py`,
`practical_execution_records.py`, `jobs/partner_presence_evidence/practical_execution_operations.py::confined`,
`model_exchange/**`, `records/progress_views.py`, `instructions/launch_instructions.py`, `tools/tool_knowledge.py`) take values only.
Its own Store calls are `ctx.store.artifact`, `ctx.store.put('source', ...)` (a tool) and `records.get`, `records.get_artifact`
(`messages/internal_summary.py`).

## BLOCKED-ON-JOB-SERVICE

- BLOCKED-ON-JOB-SERVICE: `job_access` (declared in `SERVICES`; no factory or class exists, so a link raises
  `LinkError('service_required:...')`); wanted call: `await ctx.services['job_access'].observe_target(target, key=ctx.operation_key, resumed=ctx.resumed)`
  (old `job_progress_provider.targets.observe_target`) and `await ctx.services['job_access'].read_file(target, path=, offset=, limit=, key=ctx.operation_key + ':file:<i>', resumed=ctx.resumed)`
  (old `targets.read_file`), idempotent on the key.
- BLOCKED-ON-JOB-SERVICE: `job_access` reads in `decide`; wanted call: `ctx.services['job_access'].read('target', handoff_ref)` (old
  `targets.read_target`) and `ctx.services['job_access'].read('target_description', handoff_ref, selector)` (old `targets.describe_target`).
- BLOCKED-ON-JOB-SERVICE: the job record kind of the handoff and its work table (`JOB_LEDGER`); wanted call in `task.py _read_target`:
  `row = ctx.store.table(JOB_LEDGER).get(handoff_refs[0])` then `ctx.services['job_access'].read_target(row)`. `_read_target` raises `NotImplementedError`.
- BLOCKED-ON-JOB-SERVICE: the result host of a typed target (local file sources, masking, BLAST utility, standard and native BLAST database,
  HMMER preparation, HMMER, BLAST, RNA structure and comparison, expression NMF, Infernal and Infernal preparation) and of an API target
  (also EBI HMMER, NCBI BLAST with the BLAST grader requirement, AppService, BV-BRC, UniProt, Rfam): their `applies`, `catalog`, `execute`,
  `credit_view`, `completion`, `facts` and `validate_selected_inputs` (old `native_blast_masking_results`, `native_blast_utility_results`,
  `native_blast_standard_database_results`, `native_blast_database_results`, `native_hmmer_preparation_results`, `native_hmmer_results`,
  `native_blast_results`, `native_infernal_*`, `native_rna_structure_*`, `rna_structure_comparison_*`, `native_expression_nmf_*`, `api_execution`,
  `local_file_sources`). Wanted call: `ctx.services['job_access'].result_host(target)` with those members. `read_from_parent` raises
  `NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')` for a selector with a `version` or `resource_kind == 'api'`, so a typed commission fails at its start.
- BLOCKED-ON-JOB-SERVICE: the typed and API completion controller (old `PracticalYieldEstimator` on a verified completion proof); not built because
  credit and completion of those targets are blocked as above.
- BLOCKED-ON-JOB-SERVICE: the BLAST grader requirement (`target_custody._blast_target_requirement`, `to_parent._blast_grader_rows`,
  `result_state.initialize`): it rebuilt the original launch request from `runtime_episodes`; wanted: the original launch request in custody and
  the API result host.

## unplaced_old_functions

- `input_versions.py` (all five): launch-side validation of masking, utility and expression NMF job inputs; belongs to the launch role.
- `received_launch_requests.py` (all five): launch request validation (`_permitted`, `_request_schema`, `_launch`, `_constraints`); belongs to the launch role.
- `resource_information.py` (both): needs `job_access` reads (BLOCKED-ON-JOB-SERVICE); the resource capabilities and operation contracts are not shown to the model.
- `target_custody.py` (all three): target consistency with the context and the BLAST grader requirement (BLOCKED-ON-JOB-SERVICE).
- `terminal_execution.py` (`TerminalExecutionBehavior`, `_operations`, `_assignment`, `initialize`, `state`, `catalog`, `execute`, `fact_sources`, `facts`,
  `validate_report`): launch-side terminal behaviour for local/HPC launch roles; the launch episodes carry their own copy.
- `native_target_state.py` (`ResultsNativeTargetState`, `state`): the results role offered no state operation (it raised `practical_resource_role_required`); no tool carries it.
- `to_parent.py::_blast_grader_rows`: API result host and grader sheet (BLOCKED-ON-JOB-SERVICE).
- `yield_estimator.py::_request_yield_class`: classifies a launch request for a yield profile key (launch-side).
- `presentation.py::present_results_context`: the text renderers (`render_selected_execution_prompt`, `render_hpc_prompt`, RNA and API prompts) live in the old shared
  root and are not carried; `decide` passes the context mapping (README 5 item 16).
- `to_parent.py` facts of the hosts that have no A107 library module (`rna_structure_comparison_views`, `rna_structure_result_views`, `expression_nmf_return_views`,
  `infernal_native_result_views`, `infernal_preparation_result_views`) and of the API (`uniprot_return_contracts`, `bvbrc_data_views`, `BLAST_GRADED_RETURN_SOURCE`): not declared
  in RETURN_FORM (no `*_fact_sources` function exists for A107 for them). The `bvbrc_appservice_support_refs` source is declared (selectable, empty for a native acquisition).
- Local file sources (`execution_file_source_refs`, `execution_file_capture_outcomes`): declared selectable, an empty list for a generic native acquisition; the capture is the blocked result host.
- A selectable record-valued typed field raises `ValueError('a_generic_native_acquisition_has_no_value_for:<name>')` when selected and no value exists; a list-valued one returns `[]`.

## contract_misfits

- BLOCKED-ON-JOB-SERVICE: `job_access.observe_target` and `read_file`, the reads `target` and `target_description`, the handoff record kind / `JOB_LEDGER`, and the typed and API result host; wanted calls above.
- new field: execution_result_acquisition resource_kind (ChoiceField `local`, `hpc`, `api`): the old code read it from the target; the parent copies it from the handoff it holds, because `yield_estimator.py` may read only `parent_input`.
- new field: execution_result_acquisition workspace (text): confines the requested paths; read by the old code from the target.
- new field: execution_result_acquisition acquired_record_unit (number, positive): was the configuration value; credit has no settings, so the credit unit travels in the assignment. The old `handoff_unit` (always multiplied by a count fixed at 0) is not carried.
- new field: execution_result_acquisition initial_result_refs and initial_result_artifact_refs (record_refs, optional): the old initial known record references; the parent names each earlier `episode.execution_result` source and its artifact (a passed record does not bring the records it names).
- new field: execution_result_acquisition execution_result_artifact_refs (record_refs, selectable return field): the artifact of each result source, returned with it for the same reason.
- `handoff_ref` is a `record_refs` field (a list of exactly one reference), not text. `constraints` is an optional record field of the assignment (old property).
- Tool names `execution.results.status|collect|read` become `execution_results_status|collect|read`; the `masking_*` / `blast_utility_*` fact sources get dot-to-underscore field names (a form field name is a lowercase identifier). This renames them against "names both sides use are the old names".
- A form has no null: `execution_result_origin` (null when nothing is retained) is selectable; selecting it with no retained window raises in `final_to_parent`.
- All fact sources are selectable (the old `required_return_sources` made `execution_result_refs` required only for an axis head parent with an annotation task; this episode's parent is the HPC work planning episode).
- Bounded quality maximum: the old maximum was `acquired_record_unit` times the fraction the earlier results left uncovered; `yield_controller` has no records, so the maximum is `acquired_record_unit`. Credit counts only new positions, so it never exceeds the old maximum; only the forecast bound is looser. The old exact-zero forecast and the practical-endpoint estimate are not carried.
- Settings: the `continuation` entry for this binding path carries `log_window_bytes` and `results_yield_profiles['native_unbounded_<local|hpc>']` or `task_yield_profiles['results:native_finite_<local|hpc>']` with `{'cutoff', 'parameters'}`; optional `knowledge_library_directory` and `launch_instructions_directory`.
- After the acquisition is complete a further action is a returned `invalid` outcome (`execution_results_assignment_already_completed`, the old refusal) with credit unchanged; the system has no end action, so the controller stops the Episode when the forecast falls to the cost.
- The old `validate_report` also ran the adapters' `validate_received_report` and `validate_form` (partner_presence `communication.validate_form` exists) over the parent-written JSON-Schema report form; the parent writes no form now (RecordForm, admitted by the system), so only the facts-agreement body is carried.
- The tool arguments carry the model's operation plus the assignment, requested windows, handoff references and completion flag (`operation`, `assignment`, `requested`, `handoff_refs`, `completed`), because a tool is handed no summary. The result record version is `execution_result_information_v3` (the body drops `scope` and gains `handoff_refs` and `requested`).
- A107 is not an A105/A108 literature episode: the typed `investigation_finding` section does not apply; `finding` is this episode's own acquisition finding.
- Not a completion controller, so no "completion credit may pass its target" item.
- No old test existed for this folder at `97308b94c`; the retired_tests file has only its header.
- `GOAL.md` named in the task as the first document to read does not exist in `docs/axis_restructure_20261117/` (the other documents were read).

## Not repaired

- Launch-side rows (`terminal_execution.py` TerminalExecutionBehavior and its members, `native_target_state.py`, `yield_estimator.py::_request_yield_class`): members of the old shared `ExecutionEpisode` mixin that no call of the results role reaches; carrying them into this episode would add dead launch code. The launch episodes carry their own. Rows in the "Carried over" table state this.
- `input_versions.py` and `received_launch_requests.py` rows: they served only the typed-selector validation of `from_parent.py`; blocked with the typed result host (BLOCKED-ON-JOB-SERVICE, wanted call in the table).
- `messages/internal_summary.py::internal_summary(view)`: not tested; it needs a real runner view (units with tool outcomes), and every tool unit needs the missing `job_access` service, so no real view can be produced; a hand-built view would be a stand-in.
- `task.py::_read_target`, `decide` job_access reads, the typed and API result hosts, and the bounded-quality maximum: unchanged, real system limits (see above).
