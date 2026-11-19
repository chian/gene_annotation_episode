# a104/evolutionary_history_evidence/execution_job_submission — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/execution_job_submission/`
(58 Python files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` and child folders not read).
Nothing from the old shared root was read; old shared modules used here (`a104_execution_bindings`,
`a104_homology_execution`, `execution_progress`, `library.api_record_access`, the native result views) are named only
by what this episode asks of them.

Old binding: class `ExecutionEpisode`, `binding_path = 'evolutionary_history_evidence/execution_job_submission'`,
`commissioning_parent = 'evolutionary_history_evidence'`, old role and entry role `launch`,
`replaces_default_instructions = True`, version `execution_episode_v1`. Decision source: `LaunchTask`. Prompt
renderer: `present_execution_context`. Several files still carry branches for the other execution roles
(`results`, `launch_local`, `launch_hpc`), inherited from the old multi-role execution binding.

## What this episode is for

It chooses which permitted concrete execution request to commission on which configured resource, and receives the
resource child's handoff. In its own words (`goal.py`, the whole text):

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded
> inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and
> pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed
> handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with
> exact zero future credit.

## Task and instructions

- Permitted actions (`episode.py`): under an `hpc` ancestor `tool, child, redeliver_report`; otherwise
  `tool, reason, child, wait, redeliver_report`.
- Instructions (`instructions.py`): the goal text replaces the defaults; then the reasoning-commit requirement when
  reason is permitted, tool knowledge, launch instruction library, redelivery paragraph, wait paragraphs and the
  native-event paragraph when wait is permitted, exchange-protocol history guidance (same composer text as the head).
- `task_action.py` keeps the head's admission/execution text, for grain `launch`.

## What it reads from its parent's assignment

`from_parent.py`, `launch_requests.py`, `launch_state.py`, `scientific_inputs.py`:

- Assignment: `version` `execution_launch_assignment_v1`; `requests` {resource_id → that resource's launch request
  schema: the API request schema, or the practical assignment schema with the resource's native and preparation job
  alternatives}, at least one; `immutable_input_versions`; `constraints`; `launch_instructions` selection.
- Checks: when the parent is `hpc`/`hpc_execution` its launch custody is authenticated; every request validates for
  its resource (workspace confined, resource operations validator, API requests also against the scope); a BLAST
  graded request must be on an `ncbi_blast` resource; constraints `allowed_resource_ids`/`allowed_kinds` are string
  lists; masking and utility job inputs, input versions, native BLAST database and standard database job inputs are
  validated. `initialize` repeats this and checks the BLAST launch requirement.
- Required return to an evolutionary parent when the annotation task is required: `execution_handoff_refs`.

## Children

`child_messages.py`, `episode.py`: child roles `launch_api`, `launch_local`, `launch_hpc`; a role is allowed when a
configured resource of that kind is permitted by the assignment (`_permitted`: request present and the resource
satisfies `allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind` constraints).

| Old role | Child episode | Sends | Takes back |
|---|---|---|---|
| `launch_api` | `api_job_execution` | goal, scope, typed form, initial report, the chosen request as episode assignment, knowledge inheritance | typed form: recorded admission refs, form refs, native timing receipts, tool attributions |
| `launch_local` | `local_job_execution` | same | same |
| `launch_hpc` | `hpc_job_execution` | same | same |

## Decision state and what it shows the model

- Context: the head's decision-context text without the annotation-context branch, plus the head's decision inputs
  inlined in `task_decision.py` (execution expectations captured for `launch`).
- Own block (`internal_summary.py`): `execution_assignment`, `execution_progress` (its current facts),
  `selected_execution_task` {scientific question and selected tool info from the scientific parent, each request's
  resource id/kind, endpoint, constraints, job (an `ebi_hmmer` API request, or the single native job; HMMER jobs in
  their scientific view), resource information; constraints; selector; result description}.
- Initial context (`resource_information.py`): `execution_resource_capabilities` (per resource: kind, availability
  "unknown", tool names, workspace/policy/account/python/service/base_url, inventory snapshot, API configuration
  facts), `execution_initial_information`, `received_bvbrc_values`; for annotation/evolutionary roles with an
  `ncbi_blast` resource, `received_blast_jobs` and their meaning text.

## Tools

`work_operations.py`, `resource_operations.py`: `execution.capabilities` ("Read the actual caller-bound resource
configuration and already recorded inventory; no discovery or selection."), whose outcome is the initial decision
context. In a masking/utility results context the result catalogs instead. `resource_information.resource_tool_contracts`
declares the launch, results, homology, proteome, native and preparation operations of every resource with their
commission routes (for the parent's tool view).

## Credit

`credit.py`, `closed_credit.py`: kind `operational`. A closed episode returns only its captured closing view. Live:
usable handoffs received, counted by distinct `resource_id` beyond those already in the initial known refs, times
`handoff_unit`; the acquired-record part is fixed at zero here. Binding `execution_received_records_credit_v1`,
qualification `original_request_resource_scope_selector_and_actual_received_unique_information`. Completion
(`completion.py`): an own action whose refs include a usable handoff matching this context gives a
`practical_completion_v1` proof, endpoint `usable_handoff`.

## Continuation

`yield_estimator.py`: requires `require_private_yield`. Eligible requests are the permitted ones; remaining =
(eligible minus those whose usable handoff was already initial) × `handoff_unit`. If any remain: bounded quality with
that remaining amount as the bound, profile `task_yield_profiles['launch:<sorted request classes>']` (cutoff,
parameters). If none remain the initial credit must be zero and the forecast is exact zero
(`launch_original_request_exhaustion_v1`). Request classes: `api_<service>[_<algorithm>][_<database>]_handoff`, or
`practical_<kind>_<native jobs>_<handoff|outputs>`. A practical estimator from `verify_completion` is also offered.
`results_yield_profiles` (`native_unbounded_local/hpc`) are configuration for the results role. In `yield_control/`
terms: bounded quality; the exhausted case is a zero-forecast special case that the new estimators must express
without a fourth estimator.

## What it reports to its parent

`to_parent.py`, `report_fields.py`: `execution_handoff_refs`, `execution_result_refs`, `execution_completed`,
`execution_result_origin`, `execution_blast_hsps` (empty here), file source refs/outcomes, AppService support refs,
empty native result families (HMMER, masking, utility, BLAST databases, HMMER preparation, BLAST pairwise), and the
closed credit capture. Every `x-source` field of the return must equal these facts. It also forwards received child
facts to annotation/evolutionary parents (`received_parent_records.py`, `received_report_admission.py`).

## Differences from similar episodes

- Compared with its API/HPC children: it has children, reason and wait, a goal text of its own, a bounded launch
  yield, and requires `execution_handoff_refs` toward an evolutionary parent.
- `from_child_*` and `to_child_*` files are the same receive/assemble text as the head's.

## Files

Name abbreviations: `wf.X` = old `self.workflow.X` / `source.workflow.X` / `workflow.X`; `wf(self).X` = a parent-runtime function bound into the old workflow namespace using `self.X`; `BC.X` = old `BindingContext` field; `services.X` = old binding services; `SelectionView.X` = old selection view; `tbl:` = old journal/receipt/provider table; `imp:` = import from old `root.a104.<module>`; `lrf.` = `library.live_runtime_functions` rebinding into the old runtime namespace; bare names are old runtime/provider/numerical names. Counts are uses in that file. Full rows: `runs/carry_over/calls/a104_01.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `action_outcome.py` | 5 | outcome envelope: completed with refs, or invalid with arguments_or_reference code | none |
| `binding_record.py` | 9 | binding identity: binding_id evolutionary_history_evidence/execution_job_submission, version, resources, initial_information, handoff_unit, acquired_record_unit, log window/roles, require_private_yield, results/task yield profiles | none |
| `binding_roles.py` | 6 | VERSION execution_episode_v1; ROLES launch, launch_api, launch_local, launch_hpc, results; resource kinds local / pbs_ssh(hpc) / hmmer_api(api) / api; ROLE_KINDS | none |
| `child_messages.py` | 28 | request assemblers and report receivers for children launch_api, launch_local, launch_hpc | none |
| `closed_credit.py` | 122 | closed operational credit: at closure captures the credit view with carrier, receipt-prefix, history and archive digests; later reads return only that original view | BC.as_record×2, BC.episode_id×8, BC.role×1, imp:communication×1, imp:episode_receipts×1, imp:episode_return_records×3, imp:execution_contracts×2, EpisodeReceipts×2, EpisodeReturnRecords×2, tbl:runtime_episodes×2, tbl:runtime_forms×3, tbl:runtime_observations×1, tbl:runtime_receipt_inheritance×2, tbl:runtime_record_receipts×2 |
| `completion.py` | 95 | practical completion proof: an action whose recorded refs include a usable handoff matching this context gives practical_completion_v1 endpoint usable_handoff; verification from recorded observation history or by recomputation | BC.assignment×2, BC.episode_id×7, BC.run_id×3, BC.scope×1, imp:communication×1, imp:episode_return_records×1, imp:execution_contracts×2, imp:method_loop.identities×1, imp:native_blast_database_acquisition×1, imp:native_blast_standard_database_acquisition×1, imp:numerical×1, imp:practical_execution_records×1, imp:practical_yield×1, ESTIMATOR_VERSION×2, NumericBand×2, UnitRef×2, tbl:runtime_actions×1, tbl:runtime_observations×1 |
| `configuration.py` | 76 | constructor: explicit resources and initial inventory, positive handoff/acquired units, log window, private-yield switch, results profiles (native_unbounded_local/hpc), task yield profiles; per-resource terminal behaviour, API record access, phylogeny returns, ExecutionProgressProvider with API observer, local file sources, A104 result readers, protected readers | imp:a104_execution_bindings×4, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:evolutionary_history_evidence.execution_progress_assessment.api_observer×1, imp:execution_contracts×1, imp:execution_progress×1, imp:library.api_record_access×1, imp:local_file_capture_results×1, imp:numerical×1, YieldController×3, YieldParameters×3 |
| `credit.py` | 41 | credit kind operational; closed view if any, else new usable handoffs counted per distinct resource_id beyond the initial ones times handoff_unit (acquired part fixed at zero); binding execution_received_records_credit_v1 | imp:communication×1 |
| `credit_records.py` | 3 | closed credit fact name execution_closed_operational_credit_v1 | none |
| `decision_context.py` | 54 | decision context assembly (same text as the head minus the annotation context branch) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, FACT_MEANINGS×1, FACT_SOURCES×1, _references_in×1, SelectionView.child_reports×2, SelectionView.controller_state×1, SelectionView.model_inputs×1, tbl:runtime_actions×2, wf.binding_context×2, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.tools×1, wf.working_state×1 |
| `decision_contracts.py` | 133 | exchange envelope and replay validation (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, apply_state_frame×1, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×1, is_contract_information×1, model_snapshot×1, _references_in×1, requested_contract_information×1, WorkflowError×9, tbl:runtime_model_calls×1, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.store×2, wf.validate_contract_information×2 |
| `decision_exchange.py` | 113 | request_context exchange loop (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _category_yield_parameters×1, child_option_information×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×2, lookup_attempts×1, model_snapshot×1, requested_contract_information×1, state_frame×1, yield_table×1, tbl:runtime_model_calls×2, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.run_id×1, wf.services×1, wf.validate_contract_information×1 |
| `decision_provider.py` | 60 | provider routing with prompt renderer (shared text) | imp:providers×2, imp:runtime×1, imp:root.providers×1, _ORIGINAL_DECLARED_PRESENTATION×2, _ORIGINAL_MODEL_COMPLETE×3, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION×3, _ORIGINAL_MODEL_INSTANCE_DICT×4, wf.provider×1, wf.specialist×2 |
| `episode.py` | 54 | assembles the launch binding; binding_path evolutionary_history_evidence/execution_job_submission, commissioning_parent evolutionary_history_evidence, roles/entry_roles (launch,), replaces_default_instructions; child roles from ROLE_KINDS filtered by permitted configured resources; actions tool, child, redeliver_report under an hpc ancestor, otherwise tool, reason, child, wait, redeliver_report | BC.assignment×1, BC.path×1, imp:a104_homology_execution×1, imp:communication×1 |
| `from_child_api_job_execution.py` | 44 | receives the API child's typed form (shared receive_report text) | imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, WorkflowError×1, tbl:runtime_report_attempts×2, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf.specialist×1, wf.store×7 |
| `from_child_hpc_job_execution.py` | 44 | receives the HPC child's typed form (shared receive_report text) | imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, WorkflowError×1, tbl:runtime_report_attempts×2, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf.specialist×1, wf.store×7 |
| `from_child_local_job_execution.py` | 44 | receives the local child's typed form (shared receive_report text) | imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, WorkflowError×1, tbl:runtime_report_attempts×2, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf.specialist×1, wf.store×7 |
| `from_parent.py` | 74 | assignment schema execution_launch_assignment_v1 (requests per configured resource, immutable_input_versions, constraints, launch_instructions); prepare_assignment authenticates an hpc parent's launch, validates requests, masking/utility inputs, input versions, native BLAST database inputs; required return execution_handoff_refs to an evolutionary parent when annotation task required; initial_references (masking/utility inputs; results role branches) | BC.assignment×2, BC.path×1, BC.role×5, imp:a104_execution_bindings×1, imp:communication×1, imp:execution_contracts×2, imp:launch_instructions×1, imp:library.hpc_launch_custody×1, imp:native_blast_database_acquisition×1, imp:native_blast_database_result_publication×2, imp:native_blast_standard_database_acquisition×1, imp:native_blast_standard_database_result_publication×2, imp:resource_records×1, services.annotation_task_required×1 |
| `goal.py` | 7 | the goal text | none |
| `instructions.py` | 36 | instruction composition (same composer text as the head's task_instructions.py) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime_prompt×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, DECISION_EXCHANGE_PROTOCOL×1, REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×2, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| `internal_summary.py` | 44 | own decision block: execution_assignment, execution_progress (facts), selected_execution_task (scientific question, selected tool info, each request's resource, endpoint, constraints, job; ebi_hmmer API or one native job) | BC.assignment×2, imp:communication×1, imp:native_profile_presentation×1, services.scientific_parent_task×1 |
| `launch_requests.py` | 76 | request rules: _permitted (allowed_resource_ids, allowed_kinds, resource_id, kind), per-resource request schema (API schema or practical schema with native/preparation job alternatives), _validate_request (workspace confinement, operations validator), _launch (BLAST graded request version), constraint shape | imp:a104_execution_bindings×2, imp:a104_homology_execution×2, imp:communication×1, imp:execution_contracts×2, imp:practical_execution_operations×1, imp:practical_execution_records×3 |
| `launch_state.py` | 38 | initialize: validates the launch assignment, BLAST launch requirement, inputs, versions; results directory manifest | BC.assignment×2, BC.episode_id×2, BC.run_id×2, BC.scope×4, imp:a104_homology_execution×1, imp:communication×1, imp:execution_contracts×2, imp:practical_execution_state×2 |
| `presentation.py` | 60 | presentation and renderer selection (same body as the head's, inlined) | imp:evolutionary_history_evidence_prompt×2, imp:library.hpc_prompt×1, imp:library.monitor_prompt×1, imp:native_profile_presentation×1, imp:providers×1, imp:receiver_prompt×1, apply_state_frame×3, DECISION_CONTEXT_VERSION×1, is_api_launch_context×2, is_published_scientific_context×2, _ordinary_runtime_receiver_context×1, render_api_launch_prompt×1, render_evolutionary_history_evidence_prompt×1, text_instructions×1 |
| `protected_reference_access.py` | 100 | protected readers (protein structure, fluorescence; NMF/ATAC/chromatin unset) and their access rules | BC.assignment×4, imp:communication×1, imp:library.fluorescence_returns×1, imp:library.native_fluorescence_results×1, imp:library.native_protein_structure_results×1, imp:library.native_protein_structure_returns×1, imp:library.protein_structure_operands×1 |
| `receipt_selection.py` | 59 | receiver record selection (known and initial known refs) from services, receipt inheritance or own actions; reads received handoffs and results | BC.assignment×1, BC.episode_id×7, BC.role×1, BC.scope×2, imp:communication×1, imp:episode_receipts×1, EpisodeReceipts×2, services.record_selection×1, tbl:runtime_actions×1, tbl:runtime_receipt_inheritance×2 |
| `received_action_identity.py` | 26 | the selected tool action for a result body must match the recorded action | imp:communication×1, imp:execution_contracts×1, imp:practical_execution_state×2, tbl:runtime_actions×1 |
| `received_launch_records.py` | 3 | LAUNCH_VERSION constant | none |
| `received_parent_records.py` | 106 | received report sources and facts forwarded to annotation/evolutionary parents (file sources, masking, utility, UniProt, BLAST databases, HMMER preparation, BLAST pairwise, BV-BRC data, AppService) | BC.request×2, BC.role×10, imp:a104_homology_execution×1, imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:bvbrc_data_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:hmmer_preparation_result_views×1, imp:library.bvbrc_proteome_returns×1, imp:native_blast_database_result_views×1, imp:native_blast_standard_database_result_views×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `received_reference_access.py` | 109 | resolve_received_reference over all received result families | BC.role×9, imp:a104_homology_execution×1, imp:blast_utility_result_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×1, imp:library.bvbrc_proteome_returns×1, imp:sequence_masking_result_views×1 |
| `received_report_admission.py` | 94 | validate_received_report and received_form_references (admits native/result references; reference qualification per x-source) | BC.role×1, imp:a104_homology_execution×1, imp:communication×1, imp:hmmer_native_result_views×1 |
| `received_result_custody.py` | 62 | result body validation against original target, selector, windows and saved receipt; _read_result | imp:communication×1, imp:domain×1, imp:execution_contracts×2, imp:local_file_capture_results×1, imp:practical_execution_state×1, tbl:runtime_episodes×1 |
| `report_delivery.py` | 32 | finish (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, form_with_facts×1, tbl:runtime_forms×2, wf.binding_context×2, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| `report_fields.py` | 61 | fact_sources for each role (native HMMER, file sources, masking, utility, UniProt, BLAST, AppService, BV-BRC, execution_handoff_refs, execution_result_refs, execution_completed, execution_result_origin, execution_blast_hsps, BLAST graded return) | imp:a104_homology_execution×2, imp:blast_pairwise_result_views×1, imp:blast_result_views×1, imp:blast_utility_result_views×1, imp:bvbrc_data_views×1, imp:communication×2, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:local_file_capture_results×2, imp:native_blast_database_result_views×1, imp:native_blast_standard_database_result_views×1, imp:native_hmmer_acquisition×1, imp:practical_receipt_information×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `report_reference_access.py` | 139 | resolve: reference access across every result family, handoffs, practical receipts, API records | BC.role×13, BC.scope×4, imp:a104_homology_execution×2, imp:bvbrc_data_views×1, imp:bvbrc_homology_returns×1, imp:bvbrc_phylogeny_returns×1, imp:communication×2, imp:episode_bindings×2, imp:execution_contracts×1, imp:hmmer_preparation_result_views×1, imp:library.bvbrc_proteome_returns×1, imp:library.native_blast_database_result_records×1, imp:library.native_blast_standard_database_result_records×1, imp:local_file_capture_results×1, imp:practical_receipt_information×1, reference_in_context×4 |
| `resource_information.py` | 95 | resource information and initial decision context (capabilities, inventory, received BV-BRC values, received BLAST jobs); capabilities without probes; resource_tool_contracts for launch/results/homology/proteome/native/preparation operations | BC.role×1, imp:a104_execution_bindings×3, imp:execution_contracts×1, imp:library.bvbrc_proteome_tool_info×1 |
| `resource_operations.py` | 7 | launch operation catalog: execution.capabilities | imp:execution_contracts×1 |
| `result_operations.py` | 10 | native result operations: execution.results.status / collect / read | imp:execution_contracts×1 |
| `result_records.py` | 9 | result provider, native result origin, results assignment schema | imp:execution_contracts×1 |
| `retained_native_receipts.py` | 14 | _delegate to the per-resource terminal behaviour; practical context is the context itself | BC.assignment×1, BC.role×1, imp:communication×1 |
| `schema_fields.py` | 6 | TEXT, OFFSET, LIMIT, FILE_LIMIT | none |
| `scientific_inputs.py` | 14 | masking / utility input validation and input version validation | imp:library.execution_input_versions×1 |
| `selector_contracts.py` | 80 | result selector validation per target family; byte windows | imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:local_file_capture_results×1, imp:native_blast_acquisition×1, imp:native_blast_database_acquisition×1, imp:native_blast_database_result_views×1, imp:native_blast_masking_acquisition×1, imp:native_blast_standard_database_acquisition×1, imp:native_blast_standard_database_result_views×1, imp:native_blast_utility_acquisition×1, imp:native_hmmer_acquisition×1, imp:native_hmmer_preparation_acquisition×1, imp:practical_execution_operations×1, imp:sequence_masking_result_views×1 |
| `selector_records.py` | 7 | native selector schema | imp:execution_contracts×1 |
| `target_custody.py` | 52 | target reading and context-target checks (launch: BLAST graded query digest; resource roles: same assignment; results: same target) | BC.assignment×3, BC.role×3, BC.scope×6, imp:a104_homology_execution×1, imp:communication×1, imp:execution_contracts×2 |
| `task.py` | 97 | decision-source next() (shared text) | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:providers×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ModelCallError×2, record_source_failure×2, SourceEnd×2, WorkflowError×1, SelectionView.units_consumed×4, tbl:runtime_actions×2, tbl:runtime_episodes×1, tbl:runtime_model_calls×1, wf.action_schema×1, wf.completed_unit×3, wf.completions×2, wf.delivery_resolution_inputs×1, wf.execution_binding×2, wf.inprocess_replay×4, wf.journal×4, wf.next_return×1, wf.resolve_pending_deliveries×1, wf.run_id×1, wf.selected×2, wf.store×3 |
| `task_action.py` | 159 | action admission and execution (same text as the head's, grain launch) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:read_mapping×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionFailure×1, _decode_recorded_action_response×1, observes_action_outcome×1, ReportRedelivery×2, _wait_target_feedback×2, WorkflowError×1, tbl:runtime_actions×6, tbl:runtime_model_calls×1, wf.automatic_score_updates×1, wf.binding_context×4, wf.completions×1, wf.controller_value×2, wf.decision_exchanges×3, wf.execute×1, wf.execution_binding×5, wf.journal×3, wf.last_observed_credit×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.reasoning_action_schema×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×2, wf.selected×1, wf.source_credit_view×1, wf.specialist×2, wf.store×6, wf.validate_report×1 |
| `task_decision.py` | 154 | decision call with inputs (head's decision_inputs inlined; execution expectations for launch) | imp:root.a104×1, imp:episode_work_report×2, imp:library.hpc_prompt×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _ASSIGNMENT_TRANSPORT×1, child_option_information×1, completed_action_reports×3, DECISION_EXCHANGE_PROTOCOL×5, instructional_model_context×1, _recorded_assignment_transport×1, requested_action_history×3, WorkflowError×5, tbl:runtime_model_calls×5, wf.available_child_roles×1, wf.binding_context×4, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.episode_bindings×1, wf.execution_expectations×1, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×3, wf.job_episodes×4, wf.journal×1, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.numerical_contracts×1, wf.pending_work×1, wf.permits_common_action×1, wf.provider×2, wf.receipts×4, wf.resource_context×1, wf.resource_estimator×5, wf.services×1, wf.shared_information_context×1, wf.store×2, wf.uses_received_record_context×2, wf.validate_contract_information×2, wf.waiting_support×1 |
| `task_state.py` | 117 | source state (shared text) | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionLeaf×1, EFFECT_VERSION×1, Episode.identity×1, record_source_failure×2, tbl:runtime_actions×5, wf.archive×1, wf.completions×4, wf.context×1, wf.controller_value×1, wf.execution_binding×4, wf.grains×1, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2 |
| `terminal_validation.py` | 67 | terminal execution behaviour for launch_local/launch_hpc resources: exec_command catalog, assignment, practical state directory, receipt resolution | BC.assignment×1, BC.episode_id×4, BC.role×1, BC.run_id×3, imp:acquisition×1, imp:communication×1, imp:domain×1, imp:library.native_terminal_transport×1, imp:practical_execution_operations×1, imp:practical_execution_records×1, imp:practical_execution_state×1, imp:practical_receipt_information×1, imp:terminal_scientific_evidence×1 |
| `to_child_api_job_execution.py` | 30 | request assembly for the API child | imp:episode_contract_information×1, imp:runtime×1, EpisodeGoal×2, Episode.identity×2, EpisodeRequest×1, validate_saved_fact_form×1, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2 |
| `to_child_hpc_job_execution.py` | 30 | request assembly for the HPC child | imp:episode_contract_information×1, imp:runtime×1, EpisodeGoal×2, Episode.identity×2, EpisodeRequest×1, validate_saved_fact_form×1, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2 |
| `to_child_local_job_execution.py` | 30 | request assembly for the local child | imp:episode_contract_information×1, imp:runtime×1, EpisodeGoal×2, Episode.identity×2, EpisodeRequest×1, validate_saved_fact_form×1, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2 |
| `to_parent.py` | 76 | facts: empty native families, execution_handoff_refs, AppService support refs, execution_result_refs, file sources/outcomes, result origin, execution_completed, plus closed credit; validate_report: x-source fields must equal facts (UniProt frozen facts when closed) | BC.scope×1, imp:a104_homology_execution×2, imp:blast_pairwise_result_views×1, imp:blast_utility_result_views×1, imp:communication×2, imp:execution_contracts×1, imp:hmmer_native_result_views×1, imp:hmmer_preparation_result_views×1, imp:library.native_blast_database_result_records×1, imp:library.native_blast_standard_database_result_records×1, imp:local_file_capture_results×1, imp:practical_receipt_information×1, imp:sequence_masking_result_views×1, imp:uniprot_return_contracts×1 |
| `waiting.py` | 9 | suspension notice to the execution backend | wf.execution_backend×1, wf.execution_handle×2 |
| `work_operations.py` | 32 | launch tools: execution.capabilities (or masking/utility result catalogs); execute returns the initial decision context as the outcome | BC.assignment×2, imp:communication×1, imp:execution_contracts×1, imp:library.native_blast_masking_result_records×1, imp:library.native_blast_utility_result_records×1, imp:native_file_capture×1 |
| `yield_estimator.py` | 67 | request yield class names; task profile key launch:<sorted classes>; bounded controller capped by uncredited eligible requests times handoff_unit; exact-zero forecast when none remain; practical estimator from verify_completion | BC.assignment×1, BC.role×1, BC.scope×1, imp:communication×1, imp:numerical×1, imp:practical_yield×1, BoundedYieldController×2, NumericBand×2, PracticalYieldEstimator×2, YieldController×2, YieldEstimate×2, YieldParameters×3 |

## Carried over

Carried 19 November 2026 into the ten-file form (`goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/*`). One row per row of `runs/carry_over/functions/a104__evolutionary_history_evidence__execution_job_submission.tsv` (178 rows: 102 machinery, 76 episode function; an episode-function row whose place says "not placed" is also in `carry_over_blocked/a104__evolutionary_history_evidence__execution_job_submission.md`). "machinery" = old-runner machinery, not carried (reason given); "episode function" = placed in the file named. The folder held only the hook-era `submission_source.py` (deleted first) beside the three child folders. Old code was read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` because the working tree has no `.git`. No old function is a library candidate: every placed function lives in the episode file that uses it; the parameterized library functions it calls already exist (`ToolKnowledge`, `LaunchInstructions`, `TerminalExecution`, `validate_assignment`, `validate_api_assignment`, the result-view fact sources, `validate_form`, `yield_table`, `time_accounting`, `rejection_feedback`, the strict action transport).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_outcome.py | _outcome | machinery | old outcome envelope (completed with refs / invalid code): a tool returns its own outcome and a failure is a returned outcome (README 3c, F6) |
| binding_record.py | LaunchBindingRecord | machinery | the binding's own as_record() and run record (README 3e) |
| binding_record.py | LaunchBindingRecord.as_record | machinery | the binding's own as_record() and run record (README 3e) |
| child_messages.py | LaunchChildMessages | machinery | child request assembler / report receiver lookup by role (README 3b C1): msg_to_child.py and read_from_child.py are plain functions of the episode |
| child_messages.py | LaunchChildMessages.child_request_assembler | machinery | child request assembler / report receiver lookup by role (README 3b C1): msg_to_child.py and read_from_child.py are plain functions of the episode |
| child_messages.py | LaunchChildMessages.child_report_receiver | machinery | child request assembler / report receiver lookup by role (README 3b C1): msg_to_child.py and read_from_child.py are plain functions of the episode |
| closed_credit.py | LaunchClosedCredit | machinery | closed operational credit view frozen at closure and re-checked against old journal tables (README 3d, 3e): the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | LaunchClosedCredit._closed_credit_carrier | machinery | closed operational credit view frozen at closure and re-checked against old journal tables (README 3d, 3e): the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | LaunchClosedCredit._closed_credit_receipts | machinery | closed operational credit view frozen at closure and re-checked against old journal tables (README 3d, 3e): the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | LaunchClosedCredit._closed_credit_value | machinery | closed operational credit view frozen at closure and re-checked against old journal tables (README 3d, 3e): the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | LaunchClosedCredit._closed_credit_facts | machinery | closed operational credit view frozen at closure and re-checked against old journal tables (README 3d, 3e): the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | LaunchClosedCredit._closed_operational_credit_view | machinery | closed operational credit view frozen at closure and re-checked against old journal tables (README 3d, 3e): the system hands the credit its controller last saw to final_to_parent |
| completion.py | LaunchCompletion | machinery | practical completion proof as controller input, recomputed from runtime_actions / runtime_observations (README 3d, section 5 item 5) |
| completion.py | LaunchCompletion._proof_for_action | machinery | practical completion proof as controller input, recomputed from runtime_actions / runtime_observations (README 3d, section 5 item 5) |
| completion.py | LaunchCompletion.completion_for_action | machinery | practical completion proof as controller input, recomputed from runtime_actions / runtime_observations (README 3d, section 5 item 5) |
| completion.py | LaunchCompletion._closed_completion_verdict | machinery | practical completion proof as controller input, recomputed from runtime_actions / runtime_observations (README 3d, section 5 item 5) |
| completion.py | LaunchCompletion.verify_completion | machinery | practical completion proof as controller input, recomputed from runtime_actions / runtime_observations (README 3d, section 5 item 5) |
| configuration.py | LaunchConfiguration | episode function | task.py `_resources` and ctx.settings (resources, initial_information, coordinator_workspace, directories); read_from_parent.py ASSIGNMENT_FORM (handoff_unit, acquired_record_unit); yield_estimator.py (task_yield_profiles); the per-resource terminal behaviours, API record access, progress provider and protected readers it built are machinery/services (README 3c) |
| configuration.py | LaunchConfiguration.__init__ | episode function | task.py `_resources` and ctx.settings (resources, initial_information, coordinator_workspace, directories); read_from_parent.py ASSIGNMENT_FORM (handoff_unit, acquired_record_unit); yield_estimator.py (task_yield_profiles); the per-resource terminal behaviours, API record access, progress provider and protected readers it built are machinery/services (README 3c) |
| credit.py | LaunchCredit | episode function | credit.py `credit` |
| credit.py | LaunchCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | LaunchCredit.project_credit | machinery | closed-credit dispatch (README 3d): the system prices each unit with credit(summary, records) |
| credit.py | LaunchCredit._live_project_credit | episode function | credit.py `credit` (formula kept: handoff_unit x new resources with a usable handoff; acquired part fixed at 0.0) |
| credit.py | LaunchCredit.credit_view | machinery | credit view record is deleted (README 3d): credit returns the number |
| decision_context.py | LaunchTaskContext | episode function | task.py `_context` and `decide` |
| decision_context.py | LaunchTaskContext.assemble_decision_context | episode function | task.py `_context` and `decide`; messages/internal_summary.py `internal_summary` |
| decision_context.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| decision_contracts.py | LaunchTaskDecisionContracts | machinery | decision-exchange envelope and saved-request validation (README 3a) |
| decision_contracts.py | LaunchTaskDecisionContracts.interpretation_context | machinery | decision-exchange envelope and saved-request validation (README 3a) |
| decision_contracts.py | LaunchTaskDecisionContracts.exchange_schema | machinery | decision-exchange envelope and saved-request validation (README 3a) |
| decision_contracts.py | LaunchTaskDecisionContracts.exchange_response | machinery | decision-exchange envelope and saved-request validation (README 3a) |
| decision_contracts.py | LaunchTaskDecisionContracts.validate_contract_exchange_request | machinery | decision-exchange envelope and saved-request validation (README 3a) |
| decision_contracts.py | LaunchTaskDecisionContracts.validate_contract_exchange_history | machinery | decision-exchange envelope and saved-request validation (README 3a) |
| decision_contracts.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| decision_exchange.py | LaunchTaskDecisionExchange | machinery | decision-exchange loop (README 3a): a lookup is a tool |
| decision_exchange.py | LaunchTaskDecisionExchange.exchange_decision | machinery | decision-exchange loop (README 3a): a lookup is a tool |
| decision_exchange.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| decision_provider.py | LaunchTaskDecisionProvider | machinery | provider routing / provider patching (README 3a) |
| decision_provider.py | LaunchTaskDecisionProvider.decision_completion | machinery | provider routing / provider patching (README 3a) |
| episode.py | ExecutionEpisode | episode function | episode.py `ExecutionJobSubmission` |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | ExecutionEpisode.allowed_children | episode function | messages/read_from_parent.py `_permitted`, `read_from_parent` (parent_input["permitted"]) and task.py `_schema` (only permitted slots are offered) |
| episode.py | ExecutionEpisode.permitted_common_actions | machinery | common-action set: reason, wait and redeliver_report are not carried (README 3a, 3b); tool and child are decide/action |
| from_child_api_job_execution.py | receive_report | machinery | receive_report: progress provider, receipts ledger and timing-receipt table are system custody (README 3b R1, R3, R5) |
| from_child_hpc_job_execution.py | receive_report | machinery | receive_report: progress provider, receipts ledger and timing-receipt table are system custody (README 3b R1, R3, R5) |
| from_child_local_job_execution.py | receive_report | machinery | receive_report: progress provider, receipts ledger and timing-receipt table are system custody (README 3b R1, R3, R5) |
| from_parent.py | LaunchFromParent | episode function | messages/read_from_parent.py |
| from_parent.py | LaunchFromParent.required_return_sources | episode function | messages/msg_to_child.py `SELECTION` (the local and HPC commissions select execution_handoff_refs and execution_completed; the API child returns them always) |
| from_parent.py | LaunchFromParent.child_assignment_schema | machinery | parent's view of the child's incoming form (README 5 item 10): the parent writes its own text, the child's form admits the commission |
| from_parent.py | LaunchFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | LaunchFromParent.prepare_assignment | episode function | messages/read_from_parent.py `read_from_parent` (the `_launch` check of the assignment); the HPC-parent authenticate_launch and input custody checks are checks of a commission (rule 1) and are not carried |
| from_parent.py | LaunchFromParent.initial_references | machinery | initial references: record passing is the record_refs field (README 3b P2, 3c) |
| goal.py | LaunchGoal | episode function | goal.py GOAL |
| goal.py | LaunchGoal.instructions | episode function | goal.py GOAL (text unchanged), used by task.py `decide` |
| instructions.py | instructions | episode function | task.py `decide` (GOAL + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION); the reasoning-commit, pending_child_delivery, wait, native-event and decision-exchange paragraphs describe actions that no longer exist |
| instructions.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| internal_summary.py | LaunchInternalSummary | episode function | messages/internal_summary.py `internal_summary`; task.py `_selected_execution_task` |
| internal_summary.py | LaunchInternalSummary._with_selected_execution_task | episode function | task.py `_selected_execution_task` (native_hmmer / native_hmmer_preparation jobs raise unplaced:native_profile_scientific_job_view) |
| internal_summary.py | LaunchInternalSummary.decision_context | episode function | messages/internal_summary.py `internal_summary` (execution_assignment, execution_progress) and task.py `_context` |
| launch_requests.py | LaunchLaunchRequests | episode function | messages/read_from_parent.py |
| launch_requests.py | LaunchLaunchRequests._permitted | episode function | messages/read_from_parent.py `_permitted` |
| launch_requests.py | LaunchLaunchRequests._request_schema | episode function | not placed (unplaced_old_functions): the per-resource request schema alternatives (`requested_job_schemas`, `preparation_job_schemas` of a104_execution_bindings, `api_execution.assignment_schema`) have no module in the library; the library `validate_assignment` / `validate_api_assignment` admit the request in read_from_parent.py |
| launch_requests.py | LaunchLaunchRequests._validate_request | episode function | messages/read_from_parent.py `_request` (closed request, resource identity) and task.py `_bound` (configured resource, kind, workspace and operations validation through TerminalExecution; API validation is BLOCKED-ON-JOB-SERVICE) |
| launch_requests.py | LaunchLaunchRequests._launch | episode function | messages/read_from_parent.py `read_from_parent` (a BLAST graded request raises unplaced:a104_homology_execution.BLAST_GRADED_REQUEST_SCHEMA) |
| launch_requests.py | LaunchLaunchRequests._constraints | episode function | messages/read_from_parent.py `_constraints` |
| launch_state.py | LaunchLaunchState | episode function | messages/read_from_parent.py (assignment re-validation); the BLAST launch requirement is not placed |
| launch_state.py | LaunchLaunchState.initialize | episode function | not placed (unplaced_old_functions): `_blast_launch_requirement(request, resource_id, scope)` for a BLAST graded request (a104_homology_execution, no module); the repeated validation of the assignment is read_from_parent.py |
| launch_state.py | LaunchLaunchState._result_directory | machinery | results-directory manifest under the old run directory (old state files, results role) |
| presentation.py | present_execution_context | episode function | task.py `_task_text` and `_context` (the old renderers render_selected_execution_prompt / render_api_launch_prompt / the state frame have no module in the library: README 5 item 16) |
| protected_reference_access.py | ProtectedReferenceAccess | machinery | protected reference readers installed for the old reference resolver (README 3b D2, F3) |
| protected_reference_access.py | ProtectedReferenceAccess._install_protected_reference_readers | machinery | protected reference readers installed for the old reference resolver (README 3b D2, F3): custody and records.holds |
| protected_reference_access.py | ProtectedReferenceAccess._protein_reference_access | machinery | protected reference readers installed for the old reference resolver (README 3b D2, F3): custody and records.holds |
| protected_reference_access.py | ProtectedReferenceAccess._fluorescence_reference_access | machinery | protected reference readers installed for the old reference resolver (README 3b D2, F3): custody and records.holds |
| protected_reference_access.py | ProtectedReferenceAccess._expression_nmf_reference_access | machinery | protected reference readers installed for the old reference resolver (README 3b D2, F3): custody and records.holds |
| protected_reference_access.py | ProtectedReferenceAccess._atac_reference_access | machinery | protected reference readers installed for the old reference resolver (README 3b D2, F3): custody and records.holds |
| protected_reference_access.py | ProtectedReferenceAccess._chromatin_reference_access | machinery | protected reference readers installed for the old reference resolver (README 3b D2, F3): custody and records.holds |
| receipt_selection.py | LaunchReceiptSelection | machinery | receiver record selection from the receipts ledger / receipt inheritance (README 3b R3, F1, F2) |
| receipt_selection.py | LaunchReceiptSelection._selection | machinery | receiver record selection from the receipts ledger / receipt inheritance (README 3b R3, F1, F2) |
| receipt_selection.py | LaunchReceiptSelection._received | machinery | receiver record selection from the receipts ledger / receipt inheritance (README 3b R3, F1, F2) |
| received_action_identity.py | LaunchReceivedActionIdentity | machinery | reads runtime_actions to match a result body to a recorded action (old runner table, README 3e); results role |
| received_action_identity.py | LaunchReceivedActionIdentity._selected_result_action | machinery | reads runtime_actions to match a result body to a recorded action (old runner table, README 3e); results role |
| received_parent_records.py | LaunchReceivedParentRecords | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_parent_records.py | LaunchReceivedParentRecords._has_appservice | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_parent_records.py | LaunchReceivedParentRecords._has_uniprot | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_parent_records.py | LaunchReceivedParentRecords._appservice_sources | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_parent_records.py | LaunchReceivedParentRecords._forwards_bvbrc_reports | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_parent_records.py | LaunchReceivedParentRecords.received_report_sources | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_parent_records.py | LaunchReceivedParentRecords.received_report_facts | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_parent_records.py | LaunchReceivedParentRecords.received_report_closure_facts | machinery | received report sources/facts forwarded to annotation/evolutionary parents through the old receipts ledger (README 3b R1, F5); not a launch role |
| received_reference_access.py | LaunchReceivedParentRecordsReferenceAccess | machinery | resolve_received_reference over received result families (README 3b R1, D2, F3) |
| received_reference_access.py | LaunchReceivedParentRecordsReferenceAccess._masking_reference_access | machinery | resolve_received_reference over received result families (README 3b R1, D2, F3) |
| received_reference_access.py | LaunchReceivedParentRecordsReferenceAccess._utility_reference_access | machinery | resolve_received_reference over received result families (README 3b R1, D2, F3) |
| received_reference_access.py | LaunchReceivedParentRecordsReferenceAccess.resolve_received_reference | machinery | resolve_received_reference over received result families (README 3b R1, D2, F3) |
| received_report_admission.py | LaunchReceivedParentRecordsAdmission | machinery | validate_received_report / received_form_references: the system admits the child result (README 3b R1, F4, F5) |
| received_report_admission.py | LaunchReceivedParentRecordsAdmission.validate_received_report | machinery | validate_received_report / received_form_references: the system admits the child result (README 3b R1, F4, F5) |
| received_report_admission.py | LaunchReceivedParentRecordsAdmission.received_form_references | machinery | validate_received_report / received_form_references: the system admits the child result (README 3b R1, F4, F5) |
| received_result_custody.py | LaunchReceivedResultCustody | machinery | result body validation against saved receipts and runtime_episodes (README 3e); results role |
| received_result_custody.py | LaunchReceivedResultCustody._validate_result_body | machinery | result body validation against saved receipts and runtime_episodes (README 3e); results role |
| received_result_custody.py | LaunchReceivedResultCustody._read_result | machinery | result body validation against saved receipts and runtime_episodes (README 3e); results role |
| report_delivery.py | LaunchReportDelivery | machinery | finish / form_with_facts / release: report_form machinery and release (README 3b D1, D3) |
| report_delivery.py | LaunchReportDelivery.finish | machinery | finish / form_with_facts / release: report_form machinery and release (README 3b D1, D3) |
| report_delivery.py | _bind_preserved_runtime_providers | machinery | finish / form_with_facts / release: report_form machinery and release (README 3b D1, D3) |
| report_fields.py | LaunchToParentFields | episode function | messages/final_to_parent.py RETURN_FORM |
| report_fields.py | LaunchToParentFields.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (selectable fields under the old names; dotted masking/utility sources, BV-BRC data, AppService and UniProt sources are not declared: contract_misfits) |
| report_reference_access.py | LaunchToParentReferenceAccess | episode function | messages/final_to_parent.py `_resolver` |
| report_reference_access.py | LaunchToParentReferenceAccess.resolve | episode function | messages/final_to_parent.py `_resolver` (execution_handoff references are the handoff records the launch children returned); resolution of the other result families, practical receipts and API records is custody (README 3b D2) and the results role |
| resource_information.py | LaunchResourceInformation | episode function | task.py `execution_capabilities` |
| resource_information.py | LaunchResourceInformation._resource_information | episode function | task.py `execution_capabilities` (per-resource value) |
| resource_information.py | LaunchResourceInformation.initial_decision_context | episode function | task.py `execution_capabilities` (the tool outcome is the initial decision context; received_blast_jobs shown only to the annotation/evolutionary roles is not placed) |
| resource_information.py | LaunchResourceInformation.capabilities | episode function | task.py `execution_capabilities` (tool_names: PRACTICAL_TOOL_NAMES or the job_access service for an API resource) |
| resource_information.py | LaunchResourceInformation.resource_tool_contracts | episode function | not placed (unplaced_old_functions): per-resource launch/results/homology/proteome/native/preparation operation contracts with commission routes need `api_execution.operation_contracts`, `homology_api_contracts`, `native_operation_contracts`, `preparation_operation_contracts` and the BV-BRC proteome tool info (no module in the library); the model is shown the permitted requests and the resource capabilities instead |
| resource_operations.py | launch_operation_catalog | episode function | task.py TOOLS `execution_capabilities` and CAPABILITIES_DESCRIPTION |
| result_operations.py | native_result_operation_catalog | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| retained_native_receipts.py | LaunchRetainedNativeReceipts | machinery | delegation of receipts to the per-resource terminal behaviour (README 3b R3, F9) |
| retained_native_receipts.py | LaunchRetainedNativeReceipts._delegate | machinery | delegation of receipts to the per-resource terminal behaviour (README 3b R3, F9) |
| retained_native_receipts.py | LaunchRetainedNativeReceipts._practical_context | machinery | delegation of receipts to the per-resource terminal behaviour (README 3b R3, F9) |
| scientific_inputs.py | LaunchScientificInputs | machinery | validation of the masking/utility inputs and pinned input versions of a commission: a wrong commission fails (rule 1); custody is the record_refs field |
| scientific_inputs.py | LaunchScientificInputs._masking_inputs | machinery | validation of the masking/utility inputs and pinned input versions of a commission: a wrong commission fails (rule 1); custody is the record_refs field |
| scientific_inputs.py | LaunchScientificInputs._utility_inputs | machinery | validation of the masking/utility inputs and pinned input versions of a commission: a wrong commission fails (rule 1); custody is the record_refs field |
| scientific_inputs.py | LaunchScientificInputs._versions | machinery | validation of the masking/utility inputs and pinned input versions of a commission: a wrong commission fails (rule 1); custody is the record_refs field |
| selector_contracts.py | LaunchSelectorContracts | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| selector_contracts.py | LaunchSelectorContracts._masking_selector | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| selector_contracts.py | LaunchSelectorContracts._utility_selector | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| selector_contracts.py | LaunchSelectorContracts._selector | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| selector_contracts.py | LaunchSelectorContracts._windows | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| target_custody.py | LaunchTargetCustody | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function; for the launch role `_context_target` re-read the handoff target against the assignment and the graded query digest (handoff record kind, BLOCKED-ON-JOB-SERVICE) |
| target_custody.py | LaunchTargetCustody._retained_masking_target | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| target_custody.py | LaunchTargetCustody._retained_utility_target | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| target_custody.py | LaunchTargetCustody._target | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function |
| target_custody.py | LaunchTargetCustody._context_target | episode function | not placed (unplaced_old_functions): results role of the old multi-role execution binding (carried by execution_result_acquisition); not a launch function; for the launch role it re-read the handoff target (handoff record kind, BLOCKED-ON-JOB-SERVICE) |
| task.py | LaunchTask | episode function | task.py `decide` and `action` |
| task.py | LaunchTask.next | episode function | task.py `decide` and `action` (the loop is the system's) |
| task.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| task_action.py | LaunchTaskAction | episode function | task.py `action` |
| task_action.py | LaunchTaskAction.apply_response | episode function | task.py `action` (validation of the answer against `_schema`, Rejected with rejection_feedback) |
| task_action.py | LaunchTaskAction.execute | episode function | task.py `action` returns ToolCall or ChildCall; the `reason`, `wait` and `redeliver_report` branches are not carried (README 3a, 3b) |
| task_action.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| task_decision.py | LaunchTaskDecision | episode function | task.py `decide` |
| task_decision.py | LaunchTaskDecision.call | episode function | task.py `decide` / `_context` returns the ModelRequest; the saved-call replay, exchange and journal code is machinery (README 3a) |
| task_decision.py | LaunchTaskDecision.instructions | episode function | task.py `decide` (instructions) |
| task_decision.py | LaunchTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| task_state.py | LaunchTaskState | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | LaunchTaskState.__init__ | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | LaunchTaskState.bind_execution_context | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | LaunchTaskState.record_execution_failure | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | LaunchTaskState.restore_checkpoint | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | LaunchTaskState.restore | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | LaunchTaskState.record_effect | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | LaunchTaskState.checkpoint | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | _bind_preserved_runtime_providers | machinery | provider patching (README 3a) |
| terminal_validation.py | operation_catalog | episode function | task.py PRACTICAL_TOOL_NAMES (the one general capability of a local or HPC resource, exec_command, offered by the launch children) |
| terminal_validation.py | TerminalExecutionBehavior | episode function | task.py `_bound` (TerminalExecution validation of a request); the practical state files and receipt resolution are machinery |
| terminal_validation.py | TerminalExecutionBehavior.__init__ | machinery | per-resource behaviour wiring from the old configuration (settings now, README 3d) |
| terminal_validation.py | TerminalExecutionBehavior._operations | episode function | task.py `_bound` (TerminalExecution(config, coordinator_workspace=..., artifact_selector=terminal_artifact_paths)) |
| terminal_validation.py | TerminalExecutionBehavior._assignment | episode function | task.py `_bound` (TerminalExecution.validate_assignment) and messages/read_from_parent.py `_request` (validate_assignment) |
| terminal_validation.py | TerminalExecutionBehavior._state_directory | machinery | practical state directory of the old runner (README 3e) |
| terminal_validation.py | TerminalExecutionBehavior.initialize | machinery | practical state initialisation of the old runner (README 3e) |
| terminal_validation.py | TerminalExecutionBehavior.state | machinery | practical state of the old runner (README 3e) |
| terminal_validation.py | TerminalExecutionBehavior.resolve | machinery | receipt resolution through the old resolver (README 3b D2, F9) |
| to_child_api_job_execution.py | assemble_request | episode function | messages/msg_to_child.py `msg_to_child` (slot launch_api) |
| to_child_hpc_job_execution.py | assemble_request | episode function | messages/msg_to_child.py `msg_to_child` (slot launch_hpc) |
| to_child_local_job_execution.py | assemble_request | episode function | messages/msg_to_child.py `msg_to_child` (slot launch_local) |
| to_parent.py | LaunchToParent | episode function | messages/final_to_parent.py |
| to_parent.py | LaunchToParent.facts | episode function | messages/final_to_parent.py `facts` (the closed credit facts are not carried: credit is completion["credit"]) |
| to_parent.py | LaunchToParent._live_facts | episode function | messages/final_to_parent.py `facts` |
| to_parent.py | LaunchToParent.validate_report | episode function | messages/final_to_parent.py `validate_report` / `validate_form`, called before the result is returned (the masking, utility and UniProt adapters' validate_received_report are not in the library) |
| waiting.py | LaunchWaiting | machinery | suspension notice of the wait machinery (README 3b) |
| waiting.py | LaunchWaiting.suspension_changed | machinery | suspension notice of the wait machinery (README 3b) |
| work_operations.py | LaunchWorkOperations | episode function | task.py TOOLS |
| work_operations.py | LaunchWorkOperations.catalog | episode function | task.py TOOLS (`execution_capabilities`); the masking/utility result catalogs are the results role |
| work_operations.py | LaunchWorkOperations.execute | episode function | task.py `execution_capabilities` (returns the initial decision context as the outcome) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py `_yield_class` |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py `_task_yield_profile` |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py `yield_controller` |
| yield_estimator.py | ExecutionEpisodeYield._launch_yield_controller | episode function | yield_estimator.py `yield_controller` (BoundedQualityYieldController; the exact-zero estimator `no_remaining_requests` is not carried, README 7b) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator over verify_completion (README 3d, 7b) |
