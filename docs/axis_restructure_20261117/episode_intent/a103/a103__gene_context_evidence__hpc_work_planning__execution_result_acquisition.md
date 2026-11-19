# a103/gene_context_evidence/hpc_work_planning/execution_result_acquisition — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/execution_result_acquisition/<file>` (only files directly in this
folder; no `tests/`, `grading/` or `scoring/` folder here). Old binding class `ExecutionEpisode`
(`binding_path = 'gene_context_evidence/hpc_work_planning/execution_result_acquisition'`,
`commissioning_parent = 'gene_context_evidence/hpc_work_planning'`, `roles = ('results',)`, `entry_roles = ()`),
decision source `ResultsTask`, prompt renderer `gene_context_evidence_prompt.render_selected_execution_prompt`, record
version `execution_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py`:

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the
> current resource filesystem: the exact attempt observation does not establish that current file bytes were produced
> by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets the returned
> records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes this endpoint.

## Task and instructions

Each unit is one tool action (or a wait for API service targets). Instructions (`instructions.py`): the goal, tool
knowledge and launch-library instructions when present, the pending-child repair text, the wait and native-event texts
when wait is permitted, and the exchange-history variant under the decision-exchange protocol. No `reason` action.

## What it reads from its parent's assignment

`execution_results_assignment_v1` `{handoff_ref, selector}` (`execution_contracts.RESULTS_SCHEMA`), with selector
conditions: `local_file_source_selector_v1` or one of the family selectors from `result_selector_conditions()` or the
generic native selector `{paths | path, offset, limit}`. Admission (`from_parent.prepare_assignment`): a recorded
returned commission is restored unchanged; otherwise the handoff target is read (or the retained masking/utility
target), the selector is validated against it, and family inputs are validated (local file sources, masking, utility,
standard BLAST database, native BLAST database, BV-BRC data, BV-BRC MinHash). The request's `initial_report` and report
contract (which must carry the BLAST-grader typed return when the target requires it).

## Children

None.

## Decision state shown to the model

The old generic view (same fields as the monitor: goal, scope, working state, visible refs, credit, credit binding, time
accounting, pending work, last outcome, feedback, deliveries, controller, tools, knowledge, report facts, requested form,
current report update/basis) plus, from this binding: `execution_resource_capabilities`, `execution_initial_information`,
`received_bvbrc_values`, `received_blast_jobs` (+ meaning), `received_minhash_values` (`resource_information.py`),
`execution_assignment`, `execution_progress`, `execution_target`, `execution_target_description`, `own_bvbrc_values`,
`selected_execution_task` (`internal_summary.py`, `selected_execution_context.py`), and per call
`shared_information_context`, `requested_action_history` (HPC contexts), execution expectations keyed `results`.

## Tools

By target family (`acquisition_operations.catalog`): masking result catalog, utility result catalog, standard/native
BLAST database catalogs, the API service's results catalog, HMMER preparation, HMMER, native BLAST result catalogs, or
the generic native operations:
- `execution.results.status` — observe the exact handed-off physical attempt once;
- `execution.results.collect` — observe and acquire bounded first windows of the requested paths;
- `execution.results.read` — one bounded byte window (`path`, `offset`, `limit` <= 1 MiB) inside the requested interval.

## Credit

Kind `operational`, unbounded. A closed (yielded) episode always returns its captured closing view. Otherwise the
family's own credit view, or generic: `acquired_record_unit x` (mean over requested paths of newly covered byte
fraction not already in initial known results) — `execution_received_selector_coverage_credit_v2`, qualification
`original_selector_byte_position_union_current_filesystem_version_unverified`; local file sources: `acquired_record_unit
x` new acquisitions. The handoff term is fixed at zero here.

## Continuation

`yield_estimator._results_yield_controller` chooses by target:
- generic native selector with an unbounded path: `results_yield_profiles['native_unbounded_<local|hpc>']`
  `{cutoff, parameters}` plain controller (new layout: **accumulation**);
- generic native finite selector: `task_yield_profiles['results:native_finite_<kind>']`; forecast capped at the
  remaining uncredited bytes `acquired_record_unit x (1 - original_fraction)` (`estimate_bounded_credit_yield`), exact
  zero once nothing remains, and the verified endpoint ends it (new layout: **bounded quality** with the remaining
  credit as its bound, plus the completion endpoint);
- API target: `task_yield_profiles['results:api_<service>[_<selector version>]']`; typed native family:
  `'results:typed_<kind>_<selector version>'`; both with `PracticalYieldEstimator(verify_completion)` (new layout:
  **completion with a target**).
Raises unless `require_private_yield` was set and the named profile exists.

## Report to its parent

Fact sources (`to_parent.fact_sources`): native HMMER family facts; `execution_file_source_refs`,
`execution_file_capture_outcomes`; masking and BLAST-utility facts; UniProt (when bound); standard/native BLAST database,
HMMER preparation and native BLAST pairwise facts and `execution_blast_pairwise_result_refs`; AppService sources; BV-BRC
data and MinHash facts; `execution_handoff_refs`, `execution_result_refs`, `execution_completed`,
`execution_result_origin`, `execution_blast_hsps`; the BLAST-grader return when an NCBI BLAST service is bound. Facts
come from the matching family or the generic native reading (`execution_completed` = requested windows covered by a
successful exact attempt). Closing facts also carry the closed-credit capture. Required source `execution_result_refs`
under `gene_context_evidence` with an annotation task.

## Differences from similar episodes

Byte-identical except `episode.py`, `binding_record.py` and `execution_contracts.py` (path of the in-folder
`terminal_execution` import) to `a103/gene_context_evidence/execution_result_acquisition` and
`.../hpc_allocation_execution/execution_result_acquisition`. Against the Launch episode
(`hpc_allocation_execution/execution_job_submission`): Results has no children and no `reason`, takes a
`handoff_ref + selector` instead of a request map, its credit counts acquired bytes/records not handoffs, its decision
provider only uses the presentation renderer for a plain selected-execution context, and `to_parent` additionally reports
API facts and the BLAST-grader rows.

## Files

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `acquisition_operations.py` | 74 | Tool catalog and dispatch by target family: BLAST masking, BLAST utility, standard BLAST database, native BLAST database, API, HMMER preparation, HMMER, native BLAST, or the generic native `execution.results.*` operations; local-file sources first. Value/Type errors become an `invalid` outcome. | `BindingContext`: assignment×6; `import`: native_blast_database_results, native_blast_masking_results, native_blast_results, native_blast_standard_database_results, native_blast_utility_results, native_file_capture, native_hmmer_preparation_results, native_hmmer_results |
| `action_policy.py` | 10 | Permitted common actions: `tool` and `wait` for an API target with `api_service_assignment_v1`, otherwise only `tool`. | none |
| `binding_record.py` | 8 | Binding identity record: version `execution_episode_v1`, `binding_id` = this path, resources, initial information, `handoff_unit`, `acquired_record_unit`, `log_window_bytes`, `log_roles`, yield profile flags. | none |
| `child_commissioning.py` | 11 | No children (`child_roles` and `allowed_children` are empty). | none |
| `closed_completion.py` | 32 | Reuse a completion verdict only if it was actually recorded once in this episode's observation history with the verified-endpoint estimator, matching run, episode, assignment digest and operation key. | `BindingContext`: assignment, episode_id×4; `import`: episode_return_records, method_loop.identities, numerical, practical_yield; `table`: runtime_observations; `yield`: ESTIMATOR_VERSION, NumericBand |
| `closed_credit.py` | 116 | Closed operational credit: once the episode yielded, its credit view is captured in its closing facts with digests of context, binding, completion, archive, observation history and receipt prefix; later reads return exactly that view and never re-price it. | `BindingContext`: as_record×2, episode_id×8, role; `import`: episode_receipts, episode_return_records×3; `table`: runtime_episodes×2, runtime_forms×3, runtime_observations, runtime_receipt_inheritance×2, runtime_record_receipts×2 |
| `completion.py` | 57 | Completion proof per target family (`completion_for_action`, `verify_completion`); generic native proof from `_proof_for_action`. | none |
| `configuration.py` | 64 | Construction settings: resources (kinds local, pbs_ssh->hpc, hmmer_api/api->api), initial inventory, positive `handoff_unit` and `acquired_record_unit`, `log_window_bytes`, `log_roles`, `require_private_yield`, `results_yield_profiles` (only `native_unbounded_local\|hpc`), `task_yield_profiles` (each `{cutoff>0, parameters}`); builds terminal behaviours, API execution, progress provider, local file sources and result readers. Rejects foreign `native_*` resource bindings. | `import`: api_service_execution, execution_progress, numerical×2; `yield`: YieldController×2, YieldParameters×2 |
| `credit.py` | 49 | Credit kind `operational`. Closed view if captured, else family-specific credit view, else generic: `handoff_unit x 0` (this Results episode counts no new handoffs) + `acquired_record_unit x` newly covered selector byte fraction (`execution_received_selector_coverage_credit_v2`), or, for local file sources, `acquired_record_unit x` new file acquisitions (`execution_received_records_credit_v1`). | none |
| `decision_contracts.py` | 39 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Decision-exchange envelope and lookup schema validation. | `import`: decision_context, execution_prompt, gene_context_evidence_prompt×2, library.hpc_prompt, runtime (module), runtime×30; `runtime`: Draft202012Validator, _object×3, composition_lookup_schema×2 |
| `decision_exchange.py` | 119 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. The pending-decision lookup exchange loop. | `import`: decision_context, execution_prompt, gene_context_evidence_prompt×2, library.hpc_prompt, runtime (module), runtime×30; `name`: composition_information; `runtime`: DECISION_CONTEXT_VERSION, Mapping×3, ValidationError×4, _action_generation_schema, _category_yield_parameters, _json×2, _plain×2, _references_in, child_option_information, instructional_model_context×2, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic×2, sqlite3, state_frame, yield_table; `self.workflow`: controller_binding, decision_exchanges, execute, journal, run_id, services, store×2, validate_contract_information; `table`: runtime_model_calls×2 |
| `decision_inputs.py` | 69 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Adds `shared_information_context`, `requested_action_history` for HPC contexts; expectations keyed by role `results`; resource estimates for job sources. | `import`: episode_work_report×2, library.hpc_prompt, runtime (module), runtime×2; `runtime`: Mapping, child_option_information; `self.workflow`: available_child_roles, binding_context×2, episode_bindings, execution_expectations, is_job_source, job_episodes×4, launch_instructions×2, native_estimation_context, native_event_information×2, pending_work, permits_common_action, resource_context, resource_estimator×5, shared_information_context, store×2, waiting_support |
| `decision_provider.py` | 21 | Provider dispatch: `complete_with_presentation` with the selected-execution prompt renderer only for a selected-execution context that is not HPC, published-scientific or API-launch; otherwise plain `complete`. | `import`: decision_context, execution_prompt, gene_context_evidence_prompt×2, library.hpc_prompt, runtime×30; `self.workflow`: provider×2, specialist |
| `decision_state.py` | 45 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Same model view as the monitor (see "decision state"). | `import`: runtime (module), runtime×6; `runtime`: FACT_MEANINGS, FACT_SOURCES, Mapping×3, _plain×2, _references_in, json×2; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, is_scientific_source, job_episode_options, journal×3, knowledge, local_outcome_preview, pending_work, receipt_projection, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `table`: runtime_actions×2; `view`: child_reports×2, controller_state, model_inputs |
| `episode.py` | 47 | The binding: path, commissioning parent `gene_context_evidence/hpc_work_planning`, role `results`, no entry roles, decision source `ResultsTask`, prompt renderer `render_selected_execution_prompt`, `replaces_default_instructions`. Mixes in `A103HomologyExecution` (BLAST grader behaviour). | `import`: gene_context_evidence_prompt |
| `execution_contracts.py` | 54 | Shared constants of the execution family: versions, roles `launch, launch_api, launch_local, launch_hpc, results`, kinds, `RESULTS_SCHEMA` `{version: execution_results_assignment_v1, handoff_ref, selector}`, `NATIVE_SELECTOR_SCHEMA` (paths/path/offset/limit), `NATIVE_RESULT_ORIGIN` qualifications, the two operation catalogs and `_outcome`. | `import`: a103_execution_bindings×11, a103_homology_execution×5, communication×2, domain, execution_contracts×4, gene_context_evidence.hpc_work_planning.execution_result_acquisition.terminal_execution×2, launch_instructions, local_file_capture_results×5, native_blast_acquisition, native_blast_database_acquisition, native_blast_masking_acquisition, native_blast_standard_database_acquisition, native_blast_utility_acquisition, native_hmmer_acquisition, native_hmmer_preparation_acquisition, practical_execution_operations, practical_execution_records×4, practical_execution_state×2, practical_receipt_information, resource_records |
| `execution_state.py` | 47 | Episode initialisation: validates selector against the target, requires a BLAST-grader typed return in the report contract when the target needs one, prepares masking/utility inputs, creates the immutable `execution-results/<digest>/assignment.json` manifest. | `BindingContext`: assignment×6, episode_id×2, request, role, run_id×2, scope×2 |
| `from_parent.py` | 52 | Assignment form and admission (see "What it reads"); `required_return_sources` = `execution_result_refs` under `gene_context_evidence` with an annotation task. | `BindingContext`: path, role×2; `import`: bvbrc_data_host, native_blast_database_result_publication, native_blast_standard_database_result_publication; `services`: annotation_task_required |
| `goal.py` | 9 | Goal text (quoted). | none |
| `initial_input_references.py` | 31 | Initial known references for the Results role: the handoff plus validated BLAST database/masking/utility selected inputs. | `BindingContext`: assignment×2, role×3; `import`: native_blast_database_result_publication, native_blast_standard_database_result_publication |
| `instructions.py` | 23 | Instruction composition: goal + reasoning-commit requirement if `reason` is permitted (it is not here) + tool knowledge + launch library + pending-child repair, wait and native-event guidance; history guidance swapped for the exchange variant. | `import`: runtime_prompt (module), runtime_prompt×3; `runtime_prompt`: DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS×3, REASONING_COMMIT_REQUIREMENT; `self.workflow`: binding_context, decision_protocol, knowledge, launch_instructions, native_event_information, permits_common_action×3, specialist |
| `internal_summary.py` | 20 | Decision context: `execution_assignment`, `execution_progress` (live facts), `execution_target`, `execution_target_description`, BV-BRC own values, `selected_execution_task`. | `BindingContext`: assignment×2, scope; `import`: bvbrc_data_host, local_file_capture_results |
| `parent_input_custody.py` | 49 | Validation of launch requests/constraints shared with Launch (`_permitted`, `_validate_request`, `_launch`, `_constraints`); used here for receiving-context checks. | none |
| `received_records.py` | 52 | Which received references are this episode's handoffs and result bodies (by provider, version and assignment); AppService/UniProt presence; BV-BRC/MinHash forwarding for receiving roles. | `BindingContext`: assignment, role, scope×2; `import`: bvbrc_homology_returns |
| `received_reference_custody.py` | 160 | Receiving-context reference resolution, typed report validation and admitted-reference collection for every native/API return family (used when a scientific parent receives this report). | `BindingContext`: role×10; `import`: bvbrc_homology_returns, hmmer_native_result_views |
| `received_report_facts.py` | 103 | Fact sources/facts a receiving `annotation`/`gene_context_evidence` parent may request from this family's returns. | `BindingContext`: request×2, role×11; `import`: blast_pairwise_result_views, blast_utility_result_views, bvbrc_data_views, bvbrc_minhash_views, hmmer_preparation_result_views, native_blast_database_result_views, native_blast_standard_database_result_views, sequence_masking_result_views, uniprot_return_contracts |
| `report_delivery.py` | 25 | Old-runner closure (same as monitor): saved form or facts-filled form in `runtime_forms`. | `import`: library.private_policy_call, library.report_fact_assembly, runtime (module), runtime×4; `runtime`: Record×2, _json×2, form_with_facts, json; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `table`: runtime_forms×2 |
| `report_reference_access.py` | 115 | Outgoing report reference resolution per namespace and family; failures resolve to false. | `BindingContext`: role×12, scope×4; `import`: bvbrc_data_views, bvbrc_homology_returns, episode_bindings×2, hmmer_preparation_result_views, native_blast_database_results, native_blast_standard_database_results |
| `resource_information.py` | 86 | Resource capabilities (no probe; availability `unknown`), initial decision context (capabilities, inventory, received BV-BRC values, received BLAST jobs summary and meaning text), declared resource tool contracts. | `BindingContext`: role×3 |
| `result_completion.py` | 84 | Generic native completion: every requested path window covered by completed returncode-0 observations; proof `practical_completion_v1` with validation keys `requested_filesystem_acquisition, successful_exact_attempt_observed, attempt_output_version_unverified` (local files: `requested_complete_file_sources, ...`). | `BindingContext`: assignment×3, episode_id×4, run_id×4, scope; `table`: runtime_actions×2 |
| `result_selection.py` | 116 | Target and selector validation per family; generic native selector paths confined to the workspace; receiver selection from services, receipt inheritance or own outcomes; context-target identity checks. | `BindingContext`: assignment×3, episode_id×7, role×3, scope×6; `import`: blast_pairwise_result_views, blast_utility_result_views, episode_receipts, hmmer_native_result_views, hmmer_preparation_result_views, native_blast_database_result_views, native_blast_standard_database_result_views, sequence_masking_result_views; `services`: record_selection; `table`: runtime_actions, runtime_receipt_inheritance×2 |
| `retained_masking_reader.py` | 29 | BLAST masking selector detection and its retained target/reference access. | `import`: sequence_masking_result_views |
| `retained_result_acquisition.py` | 70 | Generic native acquisition: status/collect/read observe the exact attempt once and read bounded windows (collect: first `min(log_window_bytes, 1 MiB)` of each requested path); immutable intent/observation/window/receipt files; refuses after completion. | `BindingContext`: assignment×3, episode_id×4, run_id, scope; `table`: runtime_actions×2 |
| `retained_result_publication.py` | 59 | Publish a result body as a Store `source` (`episode.execution_result`) and authenticate it on read (scope, target, selector windows, original receipt, saved outcome). | `BindingContext`: episode_id, run_id, scope; `table`: runtime_episodes |
| `retained_utility_reader.py` | 29 | BLAST utility selector detection and its retained target/reference access. | `import`: blast_utility_result_views |
| `saved_decision_exchange.py` | 85 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Authentication of saved exchanges against frozen contract information. | `import`: decision_context, execution_prompt, gene_context_evidence_prompt×2, library.hpc_prompt, runtime (module), runtime×30; `name`: composition_information; `runtime`: CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, ValidationError, WorkflowError×9, _json×8, _recorded_action_generation_schema, apply_state_frame, instructional_model_context, is_contract_information, json, model_snapshot, requested_contract_information; `self.workflow`: contract_information_reply, decision_exchanges×2, journal, validate_contract_information×2; `table`: runtime_model_calls |
| `saved_result_commission.py` | 45 | Restore a parent's recorded Results commission (same assignment, scope, child path) only if it was successfully returned before. | `BindingContext`: episode_id×3, path, request; `import`: episode_receipts, episode_return_records; `table`: runtime_actions, runtime_episodes, runtime_report_attempts |
| `selected_execution_context.py` | 38 | `selected_execution_task_v1`: the parent's scientific question and selected tool info, the native job (one supported family) or EBI HMMER request, constraints, selector, result description. | `BindingContext`: assignment; `import`: native_profile_presentation; `services`: scientific_parent_task |
| `selector_coverage_credit.py` | 34 | Credit operand: per requested path, newly covered byte positions (not already in initial known results) / requested span; mean over paths. | `BindingContext`: assignment |
| `task.py` | 229 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Here: `job_child` storage/control errors become feedback; `reads.map` schema feedback; report grain `results`; `automatic_score_updates` after non-wait actions; `shared.read_information` retains shared grading results. | `import`: episode_source_failure, library.action_contracts, library.private_policy_call, providers, read_mapping, runtime (module), runtime×24; `runtime`: AcquisitionError×2, ActionFailure, ContractError×2, ContractInformationError, Draft202012Validator×2, EventTargetError×2, Mapping×9, ReportBoundaryError, ReportRedelivery×2, SourceEnd×2, ValidationError×3, WorkflowError×2, _decode_recorded_action_response, _json×5, _plain, _wait_target_feedback×2, inspect, json×8, nullcontext×5, observes_action_outcome, schema_failure_diagnostic, sqlite3×2, subprocess×2, validate_form; `self.workflow`: action_schema, automatic_score_updates, binding_context, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, permits_common_action, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, retain_shared_grading_results, run_id×3, selected×3, source_credit_view, specialist, store×8, validate_report; `table`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_decision.py` | 83 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Also freezes literature numerical contracts. | `import`: decision_context, execution_prompt, gene_context_evidence_prompt×2, library.hpc_prompt, runtime (module), runtime×30; `runtime`: DECISION_EXCHANGE_PROTOCOL×5, WorkflowError×5, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _digest, _json×4, _recorded_assignment_transport, instructional_model_context, json×2; `self.workflow`: contract_information_profile, decision_exchanges, decision_protocol×3, freeze_contract_information, freeze_literature_numerical_contracts, history_preview, is_job_source×2, journal, numerical_contracts, provider, receipts×4, services, uses_received_record_context×2, validate_contract_information×2; `table`: runtime_model_calls×5 |
| `task_state.py` | 108 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. | `import`: episode_source_failure, runtime (module), runtime×9; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, Record, _json×2, _object, _plain, interpretation_schema, json×4; `self.workflow`: archive, completions×4, controller_value, execution_binding×4, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `table`: runtime_actions×5 |
| `terminal_execution.py` | 242 | Instruction-led local/HPC terminal behaviour (`exec_command`) used by the Launch roles of this family; carried here as an in-folder copy because `execution_contracts.py` imports it. | `BindingContext`: assignment×9, episode_id×4, role, run_id×5; `import`: acquisition, communication×2, domain, practical_execution_operations, practical_execution_records×3, practical_execution_state, practical_receipt_information×3, practical_yield, terminal_execution×2, terminal_scientific_evidence×2; `yield`: PracticalYieldEstimator |
| `to_parent.py` | 120 | Fact sources and live facts (see "Report to parent"); report validation: every `x-source` field equals the recorded or frozen (UniProt) facts. | `BindingContext`: scope; `import`: blast_pairwise_result_views×2, blast_result_views, blast_utility_result_views×2, bvbrc_data_views, bvbrc_minhash_views, hmmer_native_result_views×2, hmmer_preparation_result_views×2, local_file_capture_results×2, native_blast_database_result_views, native_blast_database_results, native_blast_standard_database_result_views, native_blast_standard_database_results, native_hmmer_acquisition, sequence_masking_result_views×2, uniprot_return_contracts×2 |
| `waiting.py` | 9 | Wait suspension to the execution backend. | `self.workflow`: execution_backend, execution_handle×2 |
| `yield_estimator.py` | 79 | Continuation by target (see "Continuation"). | `BindingContext`: assignment, role; `import`: numerical×3, practical_yield×2; `yield`: NumericBand, PracticalYieldEstimator×3, YieldController×3, YieldEstimate, YieldParameters×4, estimate_bounded_credit_yield×2, estimate_with_context×2 |
