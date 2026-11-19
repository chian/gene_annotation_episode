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
