# a103/gene_context_evidence/execution_result_acquisition — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/execution_result_acquisition/<file>`
(only files directly in this folder; no `grading/` or `scoring/` subfolder, no child folders; `tests/` not covered).
Old binding class: `ExecutionEpisode` (`binding_path = 'gene_context_evidence/execution_result_acquisition'`,
`commissioning_parent = 'gene_context_evidence'`, `roles = entry_roles = ('results',)`), decision source
`ResultsTask`, prompt renderer `gene_context_evidence_prompt.render_selected_execution_prompt`,
`replaces_default_instructions = True`. Contract version `execution_episode_v1`; assignment
`execution_results_assignment_v1`; result body `execution_result_information_v2`.

## What it is for (its goal, in its own words)

`goal.py`:

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the
> current resource filesystem: the exact attempt observation does not establish that current file bytes were
> produced by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets
> the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes
> this endpoint.

## Task and instructions

`instructions.py` (same composition as launch_local): goal + reasoning commit requirement when reason is permitted
+ tool knowledge + launch library + repair + wait (when permitted) + native event paragraphs; exchange-protocol
history replacement. Task = old iterator copied with grain `'results'` plus reason-action path, job_child failure
feedback, native return channel repair feedback, `reads.map` feedback, automatic score updates, shared grading
retention. `decision_provider` uses the presentation renderer only for a selected-execution context that is not HPC,
not published-scientific and not API launch, and not a state frame.

## What it reads from its parent's assignment

`execution_results_assignment_v1`: `handoff_ref` (original execution handoff) and `selector`, with conditional
schemas per family (local file source selector, masking, utility, native/standard BLAST DB, HMMER, HMMER preparation,
BLAST pairwise, generic native {paths | path+offset+limit}). `prepare_assignment` restores a recorded successfully
returned results commission (saved_result_commission), else reads the target (retained masking/utility target or
handoff), validates the selector and the selected inputs for its family (local file admission, BLAST DB selected
inputs, BV-BRC inputs, MinHash commission inputs). `required_return_sources` = `('execution_result_refs',)` when the
parent is `gene_context_evidence` under an annotation task.

## Children it may commission

None (`child_roles = ()`, `allowed_children = ()`).

## Decision state and what it shows the model

Common decision state plus `is_scientific_source`; `initial_decision_context` (resource capabilities, initial
information, BV-BRC values, BLAST jobs/MinHash for receivers); `decision_context`: `execution_assignment`,
`execution_progress` (its own current facts), `execution_target` and `execution_target_description` (status and
acquisition operations; local file targets list files and provenance), `own_bvbrc_values` for BV-BRC API targets,
`selected_execution_task` from the scientific parent.

## Tools it offers

Per target family (`acquisition_operations.catalog`): masking/utility result catalogs, standard/native BLAST DB
result catalogs, the API execution catalog, HMMER preparation / HMMER / BLAST result catalogs, else the generic
`execution.results.status` (observe the exact attempt once), `execution.results.collect` (observe and acquire first
windows of requested paths), `execution.results.read` (one selected byte window within the original selector).
Generic acquisition writes immutable intent/observation/window files and refuses once the assignment is completed;
read failures are retained in the body. Common actions: tool; tool + wait for API service targets.

## How its credit is counted

`credit_kind = 'operational'`. Closed view if saved; else the family's credit view; API targets → API credit view;
generic native: `credit = acquired_record_unit × new selector coverage fraction` (`selector_coverage_credit`: union
of newly saved byte positions per requested path ÷ requested length, averaged over paths; bytes known at entry are
excluded), or for mixed local file sources `acquired_record_unit × acquisition count`. Handoff count is 0 here.
Binding `execution_received_selector_coverage_credit_v2` / `execution_received_records_credit_v1`.

## Continuation

Only with `require_private_yield`:
- generic native selector with an unbounded window (no limit): `results_yield_profiles['native_unbounded_<kind>']`
  → plain `YieldController(cutoff, parameters)`;
- generic native finite selector: task profile `results:native_finite_<kind>` with `finite_result_yield`: the
  endpoint estimator once a verified completion exists; exact zero when no uncredited bytes remain; otherwise
  `estimate_bounded_credit_yield(maximum_credit = acquired_record_unit × (1 − original fraction))` — new-layout
  **bounded quality**;
- API (`results:api_<service>[_<selector version>]`) and typed native (`results:typed_<kind>_<selector version>`):
  task profile with `PracticalYieldEstimator(verify_completion)` — **completion with a target**.
Settings: `cutoff` (> 0) and `parameters` per profile key.

## What it reports to its parent

Fact sources: native HMMER family, local file sources/outcomes, masking, utility, UniProt, BLAST DB, HMMER
preparation, BLAST pairwise, AppService, BV-BRC data, MinHash, `execution_handoff_refs`, `execution_result_refs`,
`execution_completed`, `execution_result_origin`, `execution_blast_hsps`, and the BLAST database grader return when
NCBI BLAST is configured. Live facts: family facts; API facts (+ BLAST grader rows when the target requires them,
origin null); generic native: handoffs, result refs with windows, file source refs/outcomes, origin, completed
(completed returncode-0 observation and every requested byte range covered). Closed credit facts are added at
closure. `validate_report`: fact-sourced fields equal recorded (or frozen UniProt) facts.

## Differences from siblings / similar episodes

- Near-copy of launch_local for configuration, closed credit, reference custody and report access; differs in goal,
  credit (selector coverage instead of terminal practical state), yield (three profile kinds incl. bounded),
  required return source, action policy (wait for API) and provider presentation rule.
- Carries a single-file `terminal_execution.py` copy of the Launch terminal behaviour, built by its configuration for
  non-API resources (results itself never runs `exec_command`).
- Flag for the port: `retained_result_acquisition` caps collect windows at `min(log_window_bytes, 1 MiB, length)` and
  `FILE_LIMIT` caps reads at 1 MiB (byte-window sizes, not elapsed/count limits; keep or confirm as resource bounds).

## File by file
| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `acquisition_operations.py` | 74 | Tool catalog and dispatch per result family (masking, utility, standard/native BLAST DB, API, HMMER prep, HMMER, BLAST, generic native status/collect/read); invalid arguments return an invalid outcome. | import:native_blast_database_results, import:native_blast_masking_results, import:native_blast_results, import:native_blast_standard_database_results, import:native_blast_utility_results, import:native_file_capture, import:native_hmmer_preparation_results, import:native_hmmer_results |
| `action_policy.py` | 10 | Common actions: tool; tool+wait for API service targets. | none |
| `binding_record.py` | 8 | Binding descriptor (same fields as launch_local). | none |
| `child_commissioning.py` | 11 | No children. | none |
| `closed_completion.py` | 32 | Recorded endpoint verdict reuse for closed episodes. | import:episode_return_records, import:method_loop.identities, import:numerical, import:practical_yield, runtime_observations |
| `closed_credit.py` | 116 | Closed operational credit (same as launch_local). | EpisodeReceipts, EpisodeReturnRecords, import:episode_receipts, import:episode_return_records×3, runtime_episodes×2, runtime_forms×3, runtime_observations, runtime_receipt_inheritance×2, runtime_record_receipts×2 |
| `completion.py` | 57 | Completion proof per family, API delegate, or generic _proof_for_action; verify_completion. | none |
| `configuration.py` | 64 | Settings (same as launch_local). | import:api_service_execution, import:execution_progress, import:numerical |
| `credit.py` | 49 | Credit kind 'operational'; family credit views; API credit view; generic: handoff_unit x 0 + acquired_record_unit x new selector byte-coverage fraction (or mixed file-acquisition counts). | none |
| `decision_contracts.py` | 39 | Split exchange envelope (common). | import:decision_context, import:execution_prompt, import:gene_context_evidence_prompt, import:library.hpc_prompt, import:root.a103, import:runtime, runtime.composition_lookup_schema×2, runtime.Draft202012Validator, runtime._object×3 |
| `decision_exchange.py` | 119 | Split exchange loop (common). | import:decision_context, import:execution_prompt, import:gene_context_evidence_prompt, import:library.hpc_prompt, import:root.a103, import:runtime, runtime._action_generation_schema, runtime._category_yield_parameters, runtime.child_option_information, runtime.DECISION_CONTEXT_VERSION, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts, runtime.Mapping×3, runtime_model_calls×2, runtime.model_snapshot, runtime._plain×2, runtime._references_in, runtime.requested_contract_information, runtime.schema_failure_diagnostic×2, runtime.sqlite3, runtime.state_frame, runtime.ValidationError×4, runtime.yield_table, workflow.controller_binding, workflow.decision_exchanges, workflow.execute, workflow.journal, workflow.run_id, workflow.services, workflow.store×2, workflow.validate_contract_information |
| `decision_inputs.py` | 69 | Copy of decision inputs for role 'results' plus shared context, HPC action history, job-source estimates. | import:episode_work_report×2, import:library.hpc_prompt, import:root.a103, import:runtime, runtime.child_option_information, runtime.Mapping, workflow.available_child_roles, workflow.binding_context×2, workflow.episode_bindings, workflow.execution_expectations, workflow.is_job_source, workflow.job_episodes×4, workflow.launch_instructions×2, workflow.native_estimation_context, workflow.native_event_information×2, workflow.pending_work, workflow.permits_common_action, workflow.resource_context, workflow.resource_estimator×5, workflow.shared_information_context, workflow.store×2, workflow.waiting_support |
| `decision_provider.py` | 21 | Provider dispatch; uses presentation only for a selected-execution (non-HPC, non-published, non-API launch) context. | import:decision_context, import:execution_prompt, import:gene_context_evidence_prompt, import:library.hpc_prompt, import:runtime, workflow.provider×2, workflow.specialist |
| `decision_state.py` | 45 | Copy (common). | import:root.a103, import:runtime, runtime_actions×2, runtime.FACT_MEANINGS, runtime.FACT_SOURCES, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in, workflow.binding_context, workflow.catalog, workflow.controller_binding, workflow.delivery_status, workflow.extra_report_sources, workflow.is_scientific_source, workflow.job_episode_options, workflow.journal×3, workflow.knowledge, workflow.local_outcome_preview, workflow.pending_work, workflow.receipt_projection, workflow.run_id, workflow.source_credit_binding, workflow.source_credit_view, workflow.specialist, workflow.store×3, workflow.tools, workflow.working_state |
| `episode.py` | 47 | Wires Results: path gene_context_evidence/execution_result_acquisition, role/entry 'results', task ResultsTask, render_selected_execution_prompt, replaces default instructions. | import:gene_context_evidence_prompt |
| `execution_contracts.py` | 54 | Same constants/catalogs as launch_local contracts, importing its own terminal_execution. | import:a103_execution_bindings, import:a103_homology_execution, import:communication, import:domain, import:execution_contracts, import:gene_context_evidence.execution_result_acquisition.terminal_execution, import:launch_instructions, import:local_file_capture_results, import:native_blast_acquisition, import:native_blast_database_acquisition, import:native_blast_masking_acquisition, import:native_blast_standard_database_acquisition, import:native_blast_utility_acquisition, import:native_hmmer_acquisition, import:native_hmmer_preparation_acquisition, import:practical_execution_operations, import:practical_execution_records, import:practical_execution_state, import:practical_receipt_information, import:resource_records |
| `execution_state.py` | 47 | Initialize: result directory with immutable assignment manifest; BLAST grader typed return required when the target needs it; API initialize. | none |
| `from_parent.py` | 52 | Assignment execution_results_assignment_v1 (handoff_ref, selector with family conditions); restore a recorded results commission; validate selector inputs per family; required return source execution_result_refs under an annotation task. | import:bvbrc_data_host, import:native_blast_database_result_publication, import:native_blast_standard_database_result_publication |
| `goal.py` | 9 | Goal text (quoted in the doc). | none |
| `initial_input_references.py` | 31 | Initial references: handoff plus selected BLAST DB inputs; masking/utility selected inputs. | import:native_blast_database_result_publication, import:native_blast_standard_database_result_publication |
| `__init__.py` | 0 | Package marker; no intent. | none |
| `instructions.py` | 23 | Instruction composition (same as launch_local). | import:root.a103, import:runtime_prompt, runtime_prompt.DECISION_EXCHANGE_PROTOCOL, runtime_prompt.INSTRUCTIONS×3, runtime_prompt.REASONING_COMMIT_REQUIREMENT, workflow.binding_context, workflow.decision_protocol, workflow.knowledge, workflow.launch_instructions, workflow.native_event_information, workflow.permits_common_action×3, workflow.specialist |
| `internal_summary.py` | 20 | Decision context: assignment, execution progress (own facts), target and its description, own BV-BRC values, selected_execution_task. | import:bvbrc_data_host, import:local_file_capture_results |
| `parent_input_custody.py` | 49 | Request/launch validation helpers for received launch contexts. | none |
| `received_records.py` | 52 | Received handoffs and result bodies; service checks. | import:bvbrc_homology_returns |
| `received_reference_custody.py` | 160 | Receiver-side reference custody (same as launch_local). | import:bvbrc_homology_returns, import:hmmer_native_result_views |
| `received_report_facts.py` | 103 | Forwarded fact sources/facts for annotation/gene_context_evidence receivers. | import:blast_pairwise_result_views, import:blast_utility_result_views, import:bvbrc_data_views, import:bvbrc_minhash_views, import:hmmer_preparation_result_views, import:native_blast_database_result_views, import:native_blast_standard_database_result_views, import:sequence_masking_result_views, import:uniprot_return_contracts |
| `report_delivery.py` | 25 | Copy (common). | import:library.private_policy_call, import:library.report_fact_assembly, import:root.a103, import:runtime, runtime_forms×2, runtime.form_with_facts, runtime._json×2, runtime.json, runtime.Record×2, workflow.binding_context, workflow.episode_bindings, workflow.facts, workflow.journal×2, workflow.pending_handles, workflow.release×2, workflow.source_credit_view |
| `report_reference_access.py` | 115 | Outgoing reference resolution (same as launch_local). | import:bvbrc_data_views, import:bvbrc_homology_returns, import:episode_bindings×2, import:hmmer_preparation_result_views, import:native_blast_database_results, import:native_blast_standard_database_results |
| `resource_information.py` | 86 | Resource information, initial decision context, capabilities, resource tool contracts. | none |
| `result_completion.py` | 84 | Native results complete only when completed returncode-0 observations cover every requested byte range; generic completion proof. | runtime_actions×2 |
| `result_selection.py` | 116 | Target, selector validation per family, windows, receiver selection, context target checks. | EpisodeReceipts, import:blast_pairwise_result_views, import:blast_utility_result_views, import:episode_receipts, import:hmmer_native_result_views, import:hmmer_preparation_result_views, import:native_blast_database_result_views, import:native_blast_standard_database_result_views, import:sequence_masking_result_views, runtime_actions, runtime_receipt_inheritance×2 |
| `retained_masking_reader.py` | 29 | Masking selector/inputs/target/reference access. | import:sequence_masking_result_views |
| `retained_result_acquisition.py` | 70 | Generic native status/collect/read: immutable intent/observation/window files, refuse after completion, publish result Source. | runtime_actions×2 |
| `retained_result_publication.py` | 59 | Publish/validate/read execution_result_information_v2 bodies. | runtime_episodes |
| `retained_utility_reader.py` | 29 | Utility selector/inputs/target/reference access. | import:blast_utility_result_views |
| `saved_decision_exchange.py` | 85 | Split copy of saved-exchange authentication against the old journal; replay-only, no own intent. | import:decision_context, import:execution_prompt, import:gene_context_evidence_prompt, import:library.hpc_prompt, import:root.a103, import:runtime, runtime.apply_state_frame, runtime.CONTRACT_INFORMATION_OPERATIONS, runtime.DECISION_CONTEXT_VERSION, runtime.instructional_model_context, runtime.is_contract_information, runtime._json×8, runtime.json, runtime_model_calls, runtime.model_snapshot, runtime._recorded_action_generation_schema, runtime.requested_contract_information, runtime.ValidationError, runtime.WorkflowError×9, workflow.contract_information_reply, workflow.decision_exchanges×2, workflow.journal, workflow.validate_contract_information×2 |
| `saved_result_commission.py` | 45 | Restore an original successfully returned results commission from old receipts/report attempts. | EpisodeReceipts, EpisodeReturnRecords, import:episode_receipts, import:episode_return_records, runtime_actions, runtime_episodes, runtime_report_attempts |
| `selected_execution_context.py` | 38 | selected_execution_task from the scientific parent task. | import:native_profile_presentation |
| `selector_coverage_credit.py` | 34 | Credit = union of newly saved byte positions per requested path / path length, averaged over paths; old (initial) bytes excluded. | none |
| `task_decision.py` | 83 | Decision call (freeze literature numerical contracts; receipts except job sources) mixing in the split exchange files. | import:decision_context, import:execution_prompt, import:gene_context_evidence_prompt, import:library.hpc_prompt, import:root.a103, import:runtime, runtime._action_generation_schema, runtime._ASSIGNMENT_TRANSPORT, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest, runtime.instructional_model_context, runtime._json×4, runtime.json×2, runtime_model_calls×5, runtime._recorded_assignment_transport, runtime.WorkflowError×5, workflow.contract_information_profile, workflow.decision_exchanges, workflow.decision_protocol×3, workflow.freeze_contract_information, workflow.freeze_literature_numerical_contracts, workflow.history_preview, workflow.is_job_source×2, workflow.journal, workflow.numerical_contracts, workflow.provider, workflow.receipts×4, workflow.services, workflow.uses_received_record_context×2, workflow.validate_contract_information×2 |
| `task.py` | 229 | Copy of task step with grain 'results' (reason action, job_child feedback, reads.map feedback, automatic score updates, shared grading retention). | import:episode_source_failure, import:library.action_contracts, import:library.private_policy_call, import:providers, import:read_mapping, import:root.a103, import:runtime, runtime.AcquisitionError×2, runtime.ActionFailure, runtime_actions×8, runtime.ContractError×2, runtime.ContractInformationError, runtime._decode_recorded_action_response, runtime.Draft202012Validator×2, runtime_episodes, runtime.EventTargetError×2, runtime.inspect, runtime._json×5, runtime.json×8, runtime.Mapping×9, runtime_model_calls×2, runtime.nullcontext×5, runtime.observes_action_outcome, runtime._plain, runtime.ReportBoundaryError, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form, runtime.ValidationError×3, runtime._wait_target_feedback×2, runtime.WorkflowError×2, workflow.action_schema, workflow.automatic_score_updates, workflow.binding_context, workflow.completed_unit×3, workflow.completions×3, workflow.controller_value×2, workflow.decision_exchanges×3, workflow.delivery_resolution_inputs, workflow.execute, workflow.execution_binding×7, workflow.inprocess_replay×4, workflow.journal×7, workflow.last_observed_credit, workflow.next_return, workflow.pending_work, workflow.perform_selected_wait, workflow.permits_common_action, workflow.receive_native_outcome, workflow.receive_outcome, workflow.resolve_pending_deliveries, workflow.resolver, workflow.retain_shared_grading_results, workflow.run_id×3, workflow.selected×3, workflow.source_credit_view, workflow.specialist, workflow.store×8, workflow.validate_report |
| `task_state.py` | 108 | Copy (common). | import:episode_source_failure, import:root.a103, import:runtime, runtime.ActionLeaf, runtime_actions×5, runtime.EFFECT_VERSION, runtime.Episode, runtime.interpretation_schema, runtime._json×2, runtime.json×4, runtime._object, runtime._plain, runtime.Record, workflow.archive, workflow.completions×4, workflow.context, workflow.controller_value, workflow.execution_binding×4, workflow.grains, workflow.inprocess_replay×7, workflow.journal×5, workflow.progress_provider×2, workflow.recover_commissions, workflow.run_id, workflow.source_credit_view, workflow.store×2 |
| `terminal_execution.py` | 242 | Single-file copy of TerminalExecutionBehavior (exec_command launch behaviour) used by Results' configuration for non-API resources. | import:acquisition, import:communication, import:domain, import:practical_execution_operations, import:practical_execution_records, import:practical_execution_state, import:practical_receipt_information×3, import:practical_yield, import:terminal_execution, import:terminal_scientific_evidence×2 |
| `to_parent.py` | 120 | Fact sources and live/closed facts (API facts with BLAST grader rows; native: handoffs, result refs, file sources/outcomes, origin, completed); validate_report. | import:blast_pairwise_result_views×2, import:blast_result_views, import:blast_utility_result_views×2, import:bvbrc_data_views, import:bvbrc_minhash_views, import:hmmer_native_result_views×2, import:hmmer_preparation_result_views×2, import:local_file_capture_results, import:native_blast_database_results, import:native_blast_database_result_views, import:native_blast_standard_database_results, import:native_blast_standard_database_result_views, import:native_hmmer_acquisition, import:sequence_masking_result_views×2, import:uniprot_return_contracts×2 |
| `waiting.py` | 9 | Suspension hook (common). | workflow.execution_backend, workflow.execution_handle×2 |
| `yield_estimator.py` | 79 | Results yield: unbounded native selectors -> results_yield_profiles['native_unbounded_<kind>'] (plain controller); finite native -> task profile 'results:native_finite_<kind>' with bounded-quality estimate (maximum = acquired_record_unit x remaining fraction; exact zero when all bytes credited; endpoint estimator on verified completion); API/typed -> task profile with PracticalYieldEstimator. | import:practical_yield×2 |

Usage counts per name and file: `runs/carry_over/calls/a103_02.tsv`.

## Carried over

Carried over on 19 November 2026 (job: execution_result_acquisition). The generic native path (local or HPC resource, requested paths and byte windows) is carried in full; typed, API and local-file-source targets raise at `messages/read_from_parent.py` (BLOCKED-ON-JOB-SERVICE). One row per old function; the first three columns are the function list.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| acquisition_operations.py | ResultsAcquisitionOperations | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| acquisition_operations.py | ResultsAcquisitionOperations.catalog | episode function | task.py OPERATIONS/CATALOG (generic native); typed, API and local-file catalogs: BLOCKED-ON-JOB-SERVICE (read_from_parent raises) |
| acquisition_operations.py | ResultsAcquisitionOperations.execute | episode function | task.py execution_results_status/collect/read via _acquire (generic native); typed routes raise in read_from_parent |
| action_policy.py | ResultsActionPolicy | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| action_policy.py | ResultsActionPolicy.permitted_common_actions | episode function | task.py action returns a ToolCall only; the API wait is not carried (wait machinery) |
| binding_record.py | ResultsBindingRecord | machinery | binding record and as_record(), deleted (README 3d) |
| binding_record.py | ResultsBindingRecord.as_record | machinery | binding record and as_record(), deleted (README 3d) |
| child_commissioning.py | ResultsChildCommissioning | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_commissioning.py | ResultsChildCommissioning.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_commissioning.py | ResultsChildCommissioning.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| closed_completion.py | ResultsClosedCompletion | machinery | reuse of a saved verdict from runtime_observations (journal re-validation) |
| closed_completion.py | ResultsClosedCompletion._closed_completion_verdict | machinery | reuse of a saved verdict from runtime_observations (journal re-validation) |
| closed_credit.py | ResultsClosedCredit | machinery | freezes and re-authenticates the credit view against runtime_episodes/runtime_forms/receipt tables; credit is the system's completion['credit'] |
| closed_credit.py | ResultsClosedCredit._closed_credit_carrier | machinery | freezes and re-authenticates the credit view against runtime_episodes/runtime_forms/receipt tables; credit is the system's completion['credit'] |
| closed_credit.py | ResultsClosedCredit._closed_credit_receipts | machinery | freezes and re-authenticates the credit view against runtime_episodes/runtime_forms/receipt tables; credit is the system's completion['credit'] |
| closed_credit.py | ResultsClosedCredit._closed_credit_value | machinery | freezes and re-authenticates the credit view against runtime_episodes/runtime_forms/receipt tables; credit is the system's completion['credit'] |
| closed_credit.py | ResultsClosedCredit._closed_credit_facts | machinery | freezes and re-authenticates the credit view against runtime_episodes/runtime_forms/receipt tables; credit is the system's completion['credit'] |
| closed_credit.py | ResultsClosedCredit._closed_operational_credit_view | machinery | freezes and re-authenticates the credit view against runtime_episodes/runtime_forms/receipt tables; credit is the system's completion['credit'] |
| completion.py | ResultsCompletion | machinery | completion proof as controller input and its verification (README 3d, section 5 item 5); the generic native completion test is kept as internal_summary.native_results_complete |
| completion.py | ResultsCompletion.completion_for_action | machinery | completion proof as controller input and its verification (README 3d, section 5 item 5); the generic native completion test is kept as internal_summary.native_results_complete |
| completion.py | ResultsCompletion.verify_completion | machinery | completion proof as controller input and its verification (README 3d, section 5 item 5); the generic native completion test is kept as internal_summary.native_results_complete |
| configuration.py | ResultsConfiguration | episode function | settings in ctx.settings/settings (log_window_bytes, results_yield_profiles, task_yield_profiles); acquired_record_unit is an ASSIGNMENT_FORM field; provider/host construction is machinery (home factories, provider objects) |
| configuration.py | ResultsConfiguration.__init__ | episode function | settings in ctx.settings/settings (log_window_bytes, results_yield_profiles, task_yield_profiles); acquired_record_unit is an ASSIGNMENT_FORM field; provider/host construction is machinery (home factories, provider objects) |
| credit.py | ResultsCredit | episode function | credit.py credit |
| credit.py | ResultsCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | ResultsCredit.project_credit | episode function | credit.py credit |
| credit.py | ResultsCredit._live_project_credit | episode function | credit.py credit and selector_progress (generic native); typed credit views: BLOCKED-ON-JOB-SERVICE |
| credit.py | ResultsCredit.credit_view | episode function | credit.py credit |
| decision_contracts.py | ResultsDecisionContracts | machinery | decision-exchange envelope (exchange_decision loop) |
| decision_contracts.py | ResultsDecisionContracts.exchange_schema | machinery | decision-exchange envelope (exchange_decision loop) |
| decision_contracts.py | ResultsDecisionContracts.exchange_response | machinery | decision-exchange envelope (exchange_decision loop) |
| decision_exchange.py | ResultsDecisionExchange | machinery | decision-exchange loop (request_context) |
| decision_exchange.py | ResultsDecisionExchange.interpretation_context | machinery | decision-exchange loop (request_context) |
| decision_exchange.py | ResultsDecisionExchange.exchange_decision | machinery | decision-exchange loop (request_context) |
| decision_inputs.py | ResultsDecisionInputs | episode function (unplaced) | only the execution target, progress and actions context is carried (task.py decide); launch_instruction_library, shared_information_context, completed_action_reports, requested_action_history, execution_expectations, resource_tool_estimates, native_event_targets and waiting_support are not supplied by anything |
| decision_inputs.py | ResultsDecisionInputs.decision_inputs | episode function (unplaced) | only the execution target, progress and actions context is carried (task.py decide); launch_instruction_library, shared_information_context, completed_action_reports, requested_action_history, execution_expectations, resource_tool_estimates, native_event_targets and waiting_support are not supplied by anything |
| decision_provider.py | ResultsDecisionProvider | machinery | provider dispatch and conversation keys |
| decision_provider.py | ResultsDecisionProvider.conversation_key | machinery | provider dispatch and conversation keys |
| decision_provider.py | ResultsDecisionProvider.complete_decision | machinery | provider dispatch and conversation keys |
| decision_state.py | ResultsDecisionState | episode function | messages/internal_summary.py internal_summary and task.py decide (context) |
| decision_state.py | ResultsDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary and task.py decide (context) |
| episode.py | ExecutionEpisode | episode function | episode.py ExecutionResultAcquisition |
| execution_contracts.py | launch_operation_catalog | episode function (unplaced) | execution.capabilities is an operation of the launch head, not of results |
| execution_contracts.py | native_result_operation_catalog | episode function | task.py OPERATIONS/CATALOG |
| execution_contracts.py | _outcome | episode function | task.py _outcome |
| execution_state.py | ResultsExecutionState | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| execution_state.py | ResultsExecutionState._delegate | episode function (unplaced) | delegation to the API or terminal behaviour; API and terminal behaviour are not carried |
| execution_state.py | ResultsExecutionState._practical_context | machinery | binding context passthrough |
| execution_state.py | ResultsExecutionState.initialize | episode function | messages/read_from_parent.py read_from_parent/native_windows (selector validation); typed and BLAST-grader checks: BLOCKED-ON-JOB-SERVICE |
| execution_state.py | ResultsExecutionState._result_directory | machinery | immutable assignment/intent/receipt files under execution-results/; replaced by custody and the journal |
| from_parent.py | ResultsFromParent | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| from_parent.py | ResultsFromParent.required_return_sources | episode function (unplaced) | the parent selects execution_result_refs in its msg_to_child (ChildMessage.selection) |
| from_parent.py | ResultsFromParent.child_assignment_schema | machinery | parent-side assignment schema; the parent writes its own in msg_to_child |
| from_parent.py | ResultsFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and NATIVE_SELECTOR_SCHEMA |
| from_parent.py | ResultsFromParent.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (generic native); target resolution, typed input validation: BLOCKED-ON-JOB-SERVICE |
| goal.py | ResultsGoal | episode function | goal.py GOAL; task.py INSTRUCTIONS |
| goal.py | ResultsGoal.instructions | episode function | goal.py GOAL; task.py INSTRUCTIONS |
| initial_input_references.py | ResultsInitialInputReferences | machinery | authenticates inherited initial references (receipts inheritance); the parent names them in initial_result_refs |
| initial_input_references.py | ResultsInitialInputReferences.initial_references | machinery | authenticates inherited initial references (receipts inheritance); the parent names them in initial_result_refs |
| instructions.py | instructions | episode function | task.py INSTRUCTIONS (the pending-delivery, wait, native-event and exchange paragraphs describe actions that no longer exist) |
| internal_summary.py | ResultsInternalSummary | episode function | messages/internal_summary.py internal_summary; task.py decide (execution_target, execution_target_description read from job_access: BLOCKED-ON-JOB-SERVICE) |
| internal_summary.py | ResultsInternalSummary.decision_context | episode function | messages/internal_summary.py and task.py decide |
| parent_input_custody.py | ResultsParentInputCustody | episode function (unplaced) | launch request validation (_permitted, _validate_request, _launch, _constraints) belongs to the launch head, not to results |
| parent_input_custody.py | ResultsParentInputCustody._permitted | episode function (unplaced) | launch request validation (_permitted, _validate_request, _launch, _constraints) belongs to the launch head, not to results |
| parent_input_custody.py | ResultsParentInputCustody._validate_request | episode function (unplaced) | launch request validation (_permitted, _validate_request, _launch, _constraints) belongs to the launch head, not to results |
| parent_input_custody.py | ResultsParentInputCustody._launch | episode function (unplaced) | launch request validation (_permitted, _validate_request, _launch, _constraints) belongs to the launch head, not to results |
| parent_input_custody.py | ResultsParentInputCustody._constraints | episode function (unplaced) | launch request validation (_permitted, _validate_request, _launch, _constraints) belongs to the launch head, not to results |
| received_records.py | ResultsReceivedRecords | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| received_records.py | ResultsReceivedRecords._has_appservice | episode function (unplaced) | API-only (BV-BRC AppService); API targets are not carried |
| received_records.py | ResultsReceivedRecords._has_uniprot | episode function (unplaced) | API-only (UniProt); API targets are not carried |
| received_records.py | ResultsReceivedRecords._appservice_sources | episode function (unplaced) | API-only; homology_fact_sources of the old shared root is not in the library |
| received_records.py | ResultsReceivedRecords._received | machinery | handoffs and results from receipts/known refs; replaced by custody, initial_result_refs and internal_summary |
| received_records.py | ResultsReceivedRecords._forwards_bvbrc_reports | episode function (unplaced) | API-only forwarding rule |
| received_records.py | ResultsReceivedRecords._forwards_minhash_reports | episode function (unplaced) | API-only forwarding rule |
| received_reference_custody.py | ResultsReceivedReferenceCustody | machinery | received-reference receipts and resolution (R3); custody is the system's |
| received_reference_custody.py | ResultsReceivedReferenceCustody.resolve_received_reference | machinery | received-reference receipts and resolution (R3); custody is the system's |
| received_reference_custody.py | ResultsReceivedReferenceCustody.validate_received_report | machinery | received-reference receipts and resolution (R3); custody is the system's |
| received_reference_custody.py | ResultsReceivedReferenceCustody.received_form_references | machinery | received-reference receipts and resolution (R3); custody is the system's |
| received_report_facts.py | ResultsReceivedReportFacts | episode function (unplaced) | facts/sources this binding supplied to a receiving annotation/gene_context_evidence parent: the parent now selects fields of RETURN_FORM and reads them in its read_from_child |
| received_report_facts.py | ResultsReceivedReportFacts.received_report_sources | episode function (unplaced) | facts/sources this binding supplied to a receiving annotation/gene_context_evidence parent: the parent now selects fields of RETURN_FORM and reads them in its read_from_child |
| received_report_facts.py | ResultsReceivedReportFacts.received_report_facts | episode function (unplaced) | facts/sources this binding supplied to a receiving annotation/gene_context_evidence parent: the parent now selects fields of RETURN_FORM and reads them in its read_from_child |
| received_report_facts.py | ResultsReceivedReportFacts.received_report_closure_facts | episode function (unplaced) | facts/sources this binding supplied to a receiving annotation/gene_context_evidence parent: the parent now selects fields of RETURN_FORM and reads them in its read_from_child |
| report_delivery.py | ResultsReportDelivery | machinery | finish(): report form saved once, release; replaced by final_to_parent |
| report_delivery.py | ResultsReportDelivery.finish | machinery | finish(): report form saved once, release; replaced by final_to_parent |
| report_reference_access.py | ResultsReportReferenceAccess | machinery | report reference resolver over receipts (R1/R3, D2) |
| report_reference_access.py | ResultsReportReferenceAccess.resolve | machinery | report reference resolver over receipts (R1/R3, D2) |
| resource_information.py | ResultsResourceInformation | episode function (unplaced) | BLOCKED-ON-JOB-SERVICE: resource information, capabilities and resource tool contracts of the old configuration; wanted reads ctx.services['job_access'].read('resource_information', resource_id) |
| resource_information.py | ResultsResourceInformation._resource_information | episode function (unplaced) | BLOCKED-ON-JOB-SERVICE: resource information, capabilities and resource tool contracts of the old configuration; wanted reads ctx.services['job_access'].read('resource_information', resource_id) |
| resource_information.py | ResultsResourceInformation.initial_decision_context | episode function (unplaced) | BLOCKED-ON-JOB-SERVICE: resource information, capabilities and resource tool contracts of the old configuration; wanted reads ctx.services['job_access'].read('resource_information', resource_id) |
| resource_information.py | ResultsResourceInformation.capabilities | episode function (unplaced) | BLOCKED-ON-JOB-SERVICE: resource information, capabilities and resource tool contracts of the old configuration; wanted reads ctx.services['job_access'].read('resource_information', resource_id) |
| resource_information.py | ResultsResourceInformation.resource_tool_contracts | episode function (unplaced) | BLOCKED-ON-JOB-SERVICE: resource information, capabilities and resource tool contracts of the old configuration; wanted reads ctx.services['job_access'].read('resource_information', resource_id) |
| result_completion.py | ResultsResultCompletion | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| result_completion.py | ResultsResultCompletion._native_results_complete | episode function | messages/internal_summary.py native_results_complete (library candidate); local-file, masking, utility and database branches: BLOCKED-ON-JOB-SERVICE |
| result_completion.py | ResultsResultCompletion._proof_for_action | machinery | completion proof built from runtime_actions rows |
| result_selection.py | ResultsResultSelection | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| result_selection.py | ResultsResultSelection._target | episode function | task.py _read_target (raises: BLOCKED-ON-JOB-SERVICE) |
| result_selection.py | ResultsResultSelection._selector | episode function | messages/read_from_parent.py native_windows (generic native); typed selectors: raise in read_from_parent |
| result_selection.py | ResultsResultSelection._windows | episode function | messages/read_from_parent.py native_windows |
| result_selection.py | ResultsResultSelection._selection | machinery | known/initial refs from services, runtime_receipt_inheritance and runtime_actions; replaced by initial_result_refs and view.outcomes |
| result_selection.py | ResultsResultSelection._context_target | episode function (unplaced) | launch and graded-BLAST target conflict checks of the launch role; the results branch compared against the receipt-read target (machinery) |
| retained_masking_reader.py | ResultsRetainedMaskingReader | episode function (unplaced) | typed masking target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_masking_reader.py | ResultsRetainedMaskingReader._masking_selector | episode function (unplaced) | typed masking target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_masking_reader.py | ResultsRetainedMaskingReader._masking_inputs | episode function (unplaced) | typed masking target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_masking_reader.py | ResultsRetainedMaskingReader._retained_masking_target | episode function (unplaced) | typed masking target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_masking_reader.py | ResultsRetainedMaskingReader._masking_reference_access | episode function (unplaced) | typed masking target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_result_acquisition.py | ResultsRetainedResultAcquisition | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| retained_result_acquisition.py | ResultsRetainedResultAcquisition._selected_result_action | machinery | checks the saved action in runtime_actions (the system journals the unit) |
| retained_result_acquisition.py | ResultsRetainedResultAcquisition._execute_native_results | episode function | task.py _acquire and _windows (the intent/observation/window/receipt files are the system's journal and custody) |
| retained_result_publication.py | ResultsRetainedResultPublication | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| retained_result_publication.py | ResultsRetainedResultPublication._publish_result | episode function | task.py _publish |
| retained_result_publication.py | ResultsRetainedResultPublication._validate_result_body | episode function | task.py validate_result_body (content checks); checks against runtime_actions/runtime_episodes/receipt files are machinery |
| retained_result_publication.py | ResultsRetainedResultPublication._read_result | episode function | messages/internal_summary.py _initial_bodies (reads held sources and artifacts through view.records); the identity re-validation is machinery |
| retained_utility_reader.py | ResultsRetainedUtilityReader | episode function (unplaced) | typed BLAST utility target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_utility_reader.py | ResultsRetainedUtilityReader._utility_selector | episode function (unplaced) | typed BLAST utility target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_utility_reader.py | ResultsRetainedUtilityReader._utility_inputs | episode function (unplaced) | typed BLAST utility target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_utility_reader.py | ResultsRetainedUtilityReader._retained_utility_target | episode function (unplaced) | typed BLAST utility target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| retained_utility_reader.py | ResultsRetainedUtilityReader._utility_reference_access | episode function (unplaced) | typed BLAST utility target access: needs the target's result host (BLOCKED-ON-JOB-SERVICE); read_from_parent raises for a typed selector |
| saved_decision_exchange.py | ResultsSavedDecisionExchange | machinery | saved-exchange authentication; the system compares a rebuilt model request on resume |
| saved_decision_exchange.py | ResultsSavedDecisionExchange.validate_contract_exchange_request | machinery | saved-exchange authentication; the system compares a rebuilt model request on resume |
| saved_decision_exchange.py | ResultsSavedDecisionExchange.validate_contract_exchange_history | machinery | saved-exchange authentication; the system compares a rebuilt model request on resume |
| saved_result_commission.py | ResultsSavedResultCommission | machinery | restores a returned commission from runtime_actions/runtime_episodes/runtime_report_attempts (resume) |
| saved_result_commission.py | ResultsSavedResultCommission._recorded_results_assignment | machinery | restores a returned commission from runtime_actions/runtime_episodes/runtime_report_attempts (resume) |
| selected_execution_context.py | ResultsSelectedExecutionContext | episode function | task.py decide context selected_execution_task (scientific_task from the commission message; the per-resource request views of the old shared root are not carried) |
| selected_execution_context.py | ResultsSelectedExecutionContext._with_selected_execution_task | episode function | task.py decide context selected_execution_task (scientific_task from the commission message; the per-resource request views of the old shared root are not carried) |
| selector_coverage_credit.py | ResultsSelectorCoverageCredit | episode function | credit.py selector_progress (library candidate) |
| selector_coverage_credit.py | ResultsSelectorCoverageCredit._generic_result_selector_progress | episode function | credit.py selector_progress (library candidate) |
| task.py | ResultsTask | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| task.py | ResultsTask.next | machinery | decision loop |
| task.py | ResultsTask.apply_response | episode function | task.py action (schema validation, Rejected feedback); the exchange, redelivery, job_child and reads.map feedback paths are machinery or not carried |
| task.py | ResultsTask.execute | machinery | execution of the selection through the old runner (journal, wait, redelivery); the tools are in task.py |
| task_decision.py | ResultsTaskDecision | episode function | task.py decide (ModelRequest) and INSTRUCTIONS; the exchange-protocol and saved-transport parts are machinery |
| task_decision.py | ResultsTaskDecision.call | episode function | task.py decide (ModelRequest) and INSTRUCTIONS; the exchange-protocol and saved-transport parts are machinery |
| task_decision.py | ResultsTaskDecision.instructions | episode function | task.py INSTRUCTIONS |
| task_state.py | ResultsTaskState | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| task_state.py | ResultsTaskState.__init__ | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| task_state.py | ResultsTaskState.bind_execution_context | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| task_state.py | ResultsTaskState.record_execution_failure | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| task_state.py | ResultsTaskState.restore_checkpoint | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| task_state.py | ResultsTaskState.restore | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| task_state.py | ResultsTaskState.record_effect | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| task_state.py | ResultsTaskState.checkpoint | machinery | source state, restore/checkpoint, execution-failure recording (checkpoint/restore, journal) |
| terminal_execution.py | operation_catalog | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.initialize | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.state | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | binding as_record() |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function (unplaced) | launch-side terminal behaviour (exec_command, TerminalExecutionBehavior, operation_catalog): not a Results tool; execution_job_submission/hpc_job_execution carry their own copy |
| to_parent.py | ResultsToParent | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| to_parent.py | ResultsToParent.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (typed families through the library fact_sources functions); UniProt, AppService, MinHash and BLAST grader sources: unplaced (API only, not in the library) |
| to_parent.py | ResultsToParent.facts | episode function | messages/final_to_parent.py _facts / final_to_parent |
| to_parent.py | ResultsToParent._live_facts | episode function | messages/final_to_parent.py _facts (generic native); typed families' live facts: BLOCKED-ON-JOB-SERVICE |
| to_parent.py | ResultsToParent.validate_report | episode function | messages/final_to_parent.py validate_report (the facts-agreement check); validate_form and the typed validate_received_report calls are not carried |
| waiting.py | ResultsWaiting | machinery | suspension/wait machinery |
| waiting.py | ResultsWaiting.suspension_changed | machinery | suspension/wait machinery |
| yield_estimator.py | ExecutionEpisodeYield | machinery | old mix-in class of the 33-mixin ExecutionEpisode; its methods are listed on their own rows |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._results_yield_controller | episode function | yield_estimator.py yield_controller (native: accumulation or bounded quality; API and typed: completion with a target, BLOCKED-ON-JOB-SERVICE, read_from_parent raises) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator (completion proof estimator) |
