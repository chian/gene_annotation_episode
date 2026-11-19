# a110/biochemical_feasibility_evidence/execution_result_acquisition — episode intent at 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/execution_result_acquisition/<file>`
(only files directly in this folder; no tests/, grading/, scoring/ or child folders). 41 Python files, 2,188 lines.

## Purpose (own words)

`binding_path = 'biochemical_feasibility_evidence/execution_result_acquisition'`, `commissioning_parent = 'biochemical_feasibility_evidence'`,
`roles = entry_roles = ('results',)`, `replaces_default_instructions = True`, `received_execution_requires_authority = True`,
`initial_information_requires_authority = True`, class `ExecutionEpisode`, decision source `ResultsTask`, renderer `presentation.present_context`.
`instructions.ResultsInstructions.instructions`:

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested file/page reads using
> actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the current resource filesystem: the exact attempt
> observation does not establish that current file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot.
> The scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition
> establishes this endpoint.

A110-specific: besides native local/PBS file windows it acquires **flux balance analysis (FBA)** results (`native_flux_balance_results`,
`flux_balance_returns`, compact FBA assignments, `saved_sheet_recalculation` mode) and **local file sources** (`local_file_source_selector_v1`).

## Task and instructions

`task_instructions.instructions`: job-episode instructions when the source is a job source, otherwise the inlined default `INSTRUCTIONS`
("You own an iterative scientific annotation improvement, not a tool itinerary ...") — replaced entirely by the binding text above because
`replaces_default_instructions` is true — then tool knowledge, launch library, pending_child_delivery repair text, and under
`decision_exchange_v1` the history paragraph is replaced by the request_context exchange paragraph. `REASONING_COMMIT_REQUIREMENT` is
defined here but common action `reason` is not permitted (only `tool`). `task_decision.decision_completion` guards that the provider's
complete/complete_with_presentation are the original model methods before rendering with this binding's presenter.
`presentation.present_context` keeps per-(episode, role) prompt state across `decision_bootstrap`/`decision_update`/`decision_lookup_result`
frames and picks the HPC, published-scientific (A110 `render_biochemical_feasibility_evidence_prompt`), selected-execution, monitor or receiver
renderer; anything else is sent as JSON.

## What it reads from its parent's assignment

`assignment_schema('results')` = `library.execution_result_contract.RESULTS_SCHEMA` (handoff_ref, selector, constraints — schema text is in the
shared library, not read) with `selector` alternatives: `local_file_source_selector_v1` (LOCAL_FILE_SOURCE_SELECTOR_SCHEMA) and, when FBA is
configured, `flux_balance_result_selector_v1` (FBA_RESULT_SELECTOR_SCHEMA); a native selector is `{paths | path, offset, limit}`
(`selector_records.NATIVE_SELECTOR_SCHEMA`). `prepare_assignment`: validate (`checked`), restore a successfully returned original Results
commission (`saved_commission._recorded_results_assignment`: authenticated knowledge_inheritance manifest, recorded child form, same
assignment/scope/path, child yielded), otherwise target = retained FBA target or `job_progress_provider.targets.read_target(handoff_ref)`,
selector validated against the target, local file sources admitted. `required_return_sources`: `execution_result_refs` when the parent is
`biochemical_feasibility_evidence` and `services.annotation_task_required()`. `initial_references`: the handoff ref (plus the saved FBA sheet
artifact in recalculation mode).

## Children it may commission

None: `child_roles` = `allowed_children` = `()`, `permitted_common_actions` = `('tool',)`.

## Decision state and what it shows the model

`internal_summary.results_decision_snapshot` = the common snapshot (as in the monitor) without investigation_progress. The binding's
`decision_context`: compact FBA assignment → `practical_assignment`, `practical_progress` {credit, satisfied_keys}, `practical_completed`;
otherwise `execution_assignment`, `execution_progress` (= current facts), `execution_target` (local files / FBA scientific job view /
the native target) and `execution_target_description` (status/acquisition operations, provenance or target description), plus
`selected_execution_task` (scientific_question, selected_tool_info from `services.scientific_parent_task`, per-resource request/job/resource
view) for native FBA work. `task_decision` decision inputs add resource_context, shared_information_context, launch library, child_options,
initial binding context, completed_action_reports, requested_action_history for HPC contexts, pending_work, execution_expectations for
'results', resource estimates, native expectations.

## Tools offered

`work_operations.catalog`: native targets → `result_records.native_result_operation_catalog`: `execution.results.status` (observe the exact
handed-off attempt once), `execution.results.collect` (observe and acquire bounded first windows of every requested path),
`execution.results.read` (one window inside the requested paths/interval; limit <= 1 MiB). FBA targets → `native_flux_balance_results.operation_catalog`.
Local file sources → `LocalFileSourceResults.execute`. `native_file_acquisition._execute_native_results`: rejects reads outside the selector,
refuses new work after a completion proof, writes immutable intent/observation/window/receipt files keyed by digest(operation_key), records
per-window failures, publishes an `execution_result_information_v2` source (provider `episode.execution_result`) with NATIVE_RESULT_ORIGIN
qualification. Errors return an invalid outcome (`action_outcome._outcome`), except retained-artifact capture errors which raise.
`resource_information.resource_tool_contracts` lists launch/results operations per configured resource (incl. FBA tool contracts, merging
per-resource instructions/schemas).

## Credit

`credit_kind` = `operational`. `project_credit` returns the saved closed view when one exists (`closed_credit`: authenticated
`execution_closed_operational_credit_v1` facts pinned to context/binding/completion/archive/history/receipt-prefix digests; never reprojected),
else the live view: FBA → `native_flux_balance_results.credit_view`; otherwise `handoff_count = 0` and
credit = `acquired_record_unit × new selector byte-coverage fraction` (`_generic_result_selector_progress`: union of newly received byte
positions per requested path, averaged over paths; binding `execution_received_selector_coverage_credit_v2`), or for local file sources
`acquired_record_unit × new file acquisitions` (`execution_received_records_credit_v1`). No clamping (the fraction is covered/requested bytes).

## Continuation

`yield_controller` requires `require_private_yield` and uses `_results_yield_controller`:
- native selector with any open-ended length → `results_yield_profiles['native_unbounded_<kind>']` plain `YieldController` → **accumulation**;
- native finite selector → task profile `results:native_finite_<kind>`; remaining = acquired_record_unit × (1 − baseline coverage);
  `finite_result_yield`: verified endpoint → `PracticalYieldEstimator`; nothing remaining → exact zero; else
  `estimate_bounded_credit_yield(maximum_credit=remaining)` → **bounded quality** (maximum = remaining coverage credit);
- typed selector (FBA / local file) → task profile `results:typed_<kind>_<version>` with `PracticalYieldEstimator` (verified completion proof)
  → **completion with a target**.
Settings: `results_yield_profiles` (only keys native_unbounded_local/hpc) and `task_yield_profiles`, each `{cutoff > 0, parameters}`.
`completion.verify_completion` / `_proof_for_action`: a `practical_completion_v1` proof only when complete acquisition of every requested path
is observed from a successful (returncode 0) attempt (`usable_handoff` endpoint), or from FBA/local-file completion; a closed episode reuses the
single matching historical verification. The file also carries `_launch_*_yield_controller` methods that the results role never calls.

## Report to parent

`to_parent.facts` = live facts + closed-credit snapshot: FBA facts (fba_fact_sources, empty defaults) or `execution_handoff_refs`,
`execution_result_refs` (results with windows), `execution_file_source_refs`, `execution_file_capture_outcomes`, `execution_result_origin`,
`execution_completed`. `validate_report`: FBA received-report validation, references resolve, x-source fields equal facts
(`execution_report_disagrees_with_recorded_facts`). `report_delivery.finish` saves facts+form once.

## Differences from similar episodes

- vs `a107/partner_presence_evidence/execution_result_acquisition`: a107 resolves API handoffs (`received_api_reports.py`, `api_*` yield classes,
  `api` resource kind); A110 instead adds FBA (configuration builds FluxBalanceExecutionInputs/RequestBindings/NativeFluxBalanceResults/
  FluxBalanceReturns), local file-source capture, FBA selectors and credit/fact paths.
- vs the job-submission episode: same configuration/closed-credit/yield-profile machinery, but credit counts acquired bytes (handoff_count is
  fixed 0) and its tools acquire result windows instead of commissioning a resource child.
- `terminal_execution.TerminalExecutionBehavior` (instruction-led launch_local/launch_hpc terminal behaviour) is constructed per resource in
  configuration even though this episode only has the results role.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 0 | empty package marker | none |
| action_outcome.py | 5 | _outcome: completed with refs, or invalid with arguments_or_reference feedback | none |
| binding_record.py | 9 | as_record: execution_episode_v1 with resources, initial_information, units, log selection, yield profiles | none |
| binding_roles.py | 6 | VERSION; ROLES launch/launch_local/launch_hpc/results; KINDS local/pbs_ssh->hpc; ROLE_KINDS | none |
| closed_credit.py | 122 | closed operational credit: authenticate carrier (episode/archive/history), pin receipt prefix, capture once, return only the saved view | import:root.a110.communication(1), import:root.a110.episode_receipts(1), import:root.a110.episode_return_records(4), import:root.a110.execution_contracts(14), table:runtime_episodes(2), table:runtime_forms(3), table:runtime_observations(1), table:runtime_receipt_inheritance(2), table:runtime_record_receipts(2), table:sqlite_master(2) |
| completion.py | 118 | completion proof for an action (complete acquisition of requested windows from a successful attempt; FBA/local-file completion) and verification incl. historical verdict | import:root.a110.communication(4), import:root.a110.episode_return_records(4), import:root.a110.execution_contracts(6), import:root.a110.flux_balance_request_binding(2), import:root.a110.method_loop.identities(1), import:root.a110.numerical(1), import:root.a110.practical_execution_records(1), import:root.a110.practical_yield(1), table:runtime_actions(2), table:runtime_observations(1), yield:ESTIMATOR_VERSION(1), yield:NumericBand(1) |
| configuration.py | 74 | operands (resources, initial_information, tool_registry, handoff_unit, acquired_record_unit, log window/roles, private yield, yield profiles); builds terminal behaviours, progress provider, local file sources, FBA inputs/requests/results/returns | import:root.a110.communication(2), import:root.a110.execution_contracts(2), import:root.a110.execution_progress(1), import:root.a110.flux_balance_execution_inputs(1), import:root.a110.flux_balance_request_binding(1), import:root.a110.flux_balance_returns(1), import:root.a110.library.received_execution_information.received_result_readers(1), import:root.a110.local_file_capture_results(1), import:root.a110.native_flux_balance_bindings(1), import:root.a110.native_flux_balance_results(1), import:root.a110.numerical(4), yield:YieldController(2), yield:YieldParameters(2) |
| credit.py | 64 | operational credit: closed view or live (FBA view; selector byte coverage × unit; local file count × unit) | import:root.a110.communication(1) |
| credit_records.py | 3 | _CLOSED_CREDIT version name | none |
| episode.py | 83 | ExecutionEpisode composition; binding_path, commissioning_parent, roles results, authority flags; shared result-reader methods bound in | import:root.a110.communication(0), import:root.a110.execution_contracts(0), import:root.a110.library.execution_resource_information(2), import:root.a110.library.received_execution_information.received_result_readers(17) |
| from_parent.py | 78 | required_return_sources execution_result_refs; RESULTS_SCHEMA with local-file/FBA selector alternatives; prepare_assignment (recorded commission, target, selector); initial_references | import:root.a110.communication(4), import:root.a110.execution_contracts(1), import:root.a110.flux_balance_request_binding(5), import:root.a110.flux_balance_result_selection(1), import:root.a110.launch_instructions(0), import:root.a110.library.execution_result_contract(1), import:root.a110.local_file_capture_results(2), import:root.a110.resource_records(0) |
| goal.py | 16 | no children; only common action tool | import:root.a110.communication(0) |
| initial_information.py | 11 | local file sources: local capability only; otherwise resource_information from catalog readers | import:root.a110.library.execution_initial_information.presentation(1) |
| input_versions.py | 30 | validate immutable input versions; FBA input references must match original versions | import:root.a110.communication(3), import:root.a110.episode_return_records(1), import:root.a110.execution_contracts(2), import:root.a110.execution_input_versions(1), import:root.a110.flux_balance_request_binding(2) |
| instructions.py | 7 | own goal text (acquire original results through handoff ...) | none |
| internal_summary.py | 90 | decision_context (practical/execution assignment, progress, target, description, selected FBA task) and the common decision snapshot | _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.Mapping(3), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), _live_original_runtime.json(2), import:root.a110.communication(5), import:root.a110.flux_balance_request_binding(6), import:root.a110.local_file_capture_results(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.catalog(1), self.workflow.controller_binding(1), self.workflow.delivery_status(1), self.workflow.extra_report_sources(1), self.workflow.job_episode_options(1), self.workflow.journal(3), self.workflow.knowledge(1), self.workflow.local_outcome_preview(1), self.workflow.pending_work(1), self.workflow.run_id(1), self.workflow.source_credit_binding(1), self.workflow.source_credit_view(1), self.workflow.specialist(1), self.workflow.store(3), self.workflow.tools(1), self.workflow.working_state(1), table:runtime_actions(2) |
| native_file_acquisition.py | 63 | execute status/collect/read: selector confinement, completion refusal, immutable intent/observation/window/receipt files, publish result source | import:root.a110.communication(4), import:root.a110.execution_contracts(1), import:root.a110.practical_execution_state(8), table:runtime_actions(1) |
| native_target_state.py | 8 | state() refuses: practical state belongs to resource roles | none |
| presentation.py | 61 | prompt presenter: frame state per episode/role and renderer choice (hpc, A110 scientific, selected execution, monitor, receiver) | _live_original_providers.DECISION_CONTEXT_VERSION(1), _live_original_providers._ordinary_runtime_receiver_context(1), _live_original_providers.apply_state_frame(3), _live_original_providers.deepcopy(1), _live_original_providers.is_published_scientific_context(2), _live_original_providers.json(1), _live_original_providers.render_biochemical_feasibility_evidence_prompt(1), _live_original_providers.text_instructions(1), import:episode:biochemical_feasibility_evidence.task_decision(0), import:root.a110.decision_context(0), import:root.a110.library.hpc_prompt(3), import:root.a110.library.monitor_prompt(3), import:root.a110.library.scientific_decision_presentation(3), import:root.a110.providers(module)(1), import:root.a110.receiver_prompt(1) |
| receipt_selection.py | 35 | _received: split known refs into result bodies (own assignment) and usable practical handoffs; skip native bundle versions | import:root.a110.communication(1) |
| received_execution_information.py | 4 | select this path's configured/received result readers | none |
| received_launch_records.py | 3 | LAUNCH_VERSION name | none |
| received_launch_requests.py | 41 | launch request permission by constraints, per-resource request schema (FBA alternatives, compact form), _launch validation | import:root.a110.execution_contracts(1), import:root.a110.flux_balance_contracts(1), import:root.a110.flux_balance_request_binding(1), import:root.a110.practical_execution_records(3) |
| report_delivery.py | 23 | finish: save facts+form once, release, return form | _live_original_runtime.Record(2), _live_original_runtime._json(2), _live_original_runtime.form_with_facts(1), _live_original_runtime.json(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.episode_bindings(1), self.workflow.facts(1), self.workflow.journal(2), self.workflow.pending_handles(1), self.workflow.release(2), self.workflow.source_credit_view(1), table:runtime_forms(2) |
| resource_information.py | 59 | resource_tool_contracts: launch/results operations per resource incl. FBA tool contracts | import:root.a110.execution_contracts(2), import:root.a110.library.execution_operation_information(1), import:root.a110.native_flux_balance_tool_info(1) |
| result_publication.py | 13 | _publish_result: store result body artifact as source episode.execution_result | import:root.a110.execution_contracts(2) |
| result_records.py | 14 | RESULTS_VERSION, RESULT_PROVIDER, NATIVE_RESULT_ORIGIN qualification, native result operation catalog | import:root.a110.execution_contracts(4) |
| result_state.py | 25 | initialize per assignment kind (compact launch/assignment, local files, native selector, FBA selector) | import:root.a110.communication(5), import:root.a110.flux_balance_request_binding(2) |
| saved_commission.py | 46 | restore a successfully returned original Results commission (authenticated) | import:root.a110.communication(1), import:root.a110.episode_receipts(1), import:root.a110.episode_return_records(1), table:runtime_actions(1), table:runtime_episodes(1), table:runtime_report_attempts(1) |
| schema_fields.py | 6 | TEXT/OFFSET/LIMIT/FILE_LIMIT (1 MiB) schema fragments | none |
| selector_records.py | 7 | NATIVE_SELECTOR_SCHEMA | import:root.a110.execution_contracts(1) |
| target_custody.py | 22 | _context_target: handoff target must match assignment (compact FBA bindings, resource roles, results target) | import:root.a110.communication(2), import:root.a110.execution_contracts(2), import:root.a110.flux_balance_request_binding(4) |
| task.py | 220 | decision loop; own: results_decision_snapshot, job_child storage failure feedback, component_native_return_channels_required repair feedback, input_detail; reason-commit check | _live_original_runtime.AcquisitionError(2), _live_original_runtime.ActionFailure(1), _live_original_runtime.ContractError(2), _live_original_runtime.ContractInformationError(1), _live_original_runtime.Draft202012Validator(3), _live_original_runtime.EventTargetError(2), _live_original_runtime.Mapping(8), _live_original_runtime.ReportBoundaryError(1), _live_original_runtime.ReportRedelivery(2), _live_original_runtime.SourceEnd(2), _live_original_runtime.ValidationError(2), _live_original_runtime.WorkflowError(2), _live_original_runtime._decode_recorded_action_response(1), _live_original_runtime._json(5), _live_original_runtime._plain(1), _live_original_runtime._wait_target_feedback(2), _live_original_runtime.inspect(1), _live_original_runtime.json(8), _live_original_runtime.nullcontext(5), _live_original_runtime.observes_action_outcome(1), _live_original_runtime.schema_failure_diagnostic(1), _live_original_runtime.sqlite3(2), _live_original_runtime.subprocess(2), _live_original_runtime.validate_form(1), import:root.a110.episode_source_failure(1), import:root.a110.providers(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.action_schema(1), self.workflow.automatic_score_updates(1), self.workflow.binding_context(2), self.workflow.completed_unit(3), self.workflow.completions(3), self.workflow.controller_value(2), self.workflow.decision_exchanges(3), self.workflow.delivery_resolution_inputs(1), self.workflow.execute(1), self.workflow.execution_binding(7), self.workflow.inprocess_replay(4), self.workflow.journal(7), self.workflow.last_observed_credit(1), self.workflow.next_return(1), self.workflow.pending_work(1), self.workflow.perform_selected_wait(1), self.workflow.permits_common_action(1), self.workflow.reasoning_action_schema(1), self.workflow.receive_native_outcome(1), self.workflow.receive_outcome(1), self.workflow.resolve_pending_deliveries(1), self.workflow.resolver(1), self.workflow.retain_shared_grading_results(1), self.workflow.run_id(3), self.workflow.selected(3), self.workflow.source_credit_view(1), self.workflow.specialist(2), self.workflow.store(9), self.workflow.validate_report(1), table:runtime_actions(8), table:runtime_episodes(1), table:runtime_model_calls(2) |
| task_decision.py | 360 | decision call/exchange; decision inputs for results; decision_completion guard of original provider methods | _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS(1), _live_original_runtime.DECISION_CONTEXT_VERSION(2), _live_original_runtime.DECISION_EXCHANGE_PROTOCOL(5), _live_original_runtime.Draft202012Validator(1), _live_original_runtime.Mapping(4), _live_original_runtime.ValidationError(5), _live_original_runtime.WorkflowError(14), _live_original_runtime._ASSIGNMENT_TRANSPORT(1), _live_original_runtime._action_generation_schema(2), _live_original_runtime._category_yield_parameters(1), _live_original_runtime._digest(1), _live_original_runtime._json(14), _live_original_runtime._object(3), _live_original_runtime._plain(2), _live_original_runtime._recorded_action_generation_schema(1), _live_original_runtime._recorded_assignment_transport(1), _live_original_runtime._references_in(1), _live_original_runtime.apply_state_frame(1), _live_original_runtime.child_option_information(2), _live_original_runtime.composition_lookup_schema(2), _live_original_runtime.instructional_model_context(4), _live_original_runtime.is_contract_information(1), _live_original_runtime.json(3), _live_original_runtime.lookup_attempts(1), _live_original_runtime.model_snapshot(2), _live_original_runtime.requested_contract_information(2), _live_original_runtime.schema_failure_diagnostic(2), _live_original_runtime.sqlite3(1), _live_original_runtime.state_frame(1), _live_original_runtime.yield_table(1), import:root.a110.episode_work_report(2), import:root.a110.library.hpc_prompt(1), import:root.a110.providers(4), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow(passed)(6), self.workflow.available_child_roles(1), self.workflow.binding_context(1), self.workflow.contract_information_profile(1), self.workflow.contract_information_reply(1), self.workflow.controller_binding(1), self.workflow.decision_exchanges(4), self.workflow.decision_protocol(3), self.workflow.episode_bindings(1), self.workflow.execute(1), self.workflow.execution_expectations(1), self.workflow.freeze_contract_information(1), self.workflow.freeze_literature_numerical_contracts(1), self.workflow.history_preview(1), self.workflow.is_job_source(3), self.workflow.job_episodes(2), self.workflow.journal(3), self.workflow.launch_instructions(2), self.workflow.native_estimation_context(1), self.workflow.numerical_contracts(1), self.workflow.pending_work(1), self.workflow.provider(3), self.workflow.receipts(4), self.workflow.resource_context(1), self.workflow.resource_estimator(5), self.workflow.run_id(1), self.workflow.services(2), self.workflow.shared_information_context(1), self.workflow.specialist(1), self.workflow.store(2), self.workflow.uses_received_record_context(2), self.workflow.validate_contract_information(5), table:runtime_model_calls(8) |
| task_instructions.py | 22 | inlined default INSTRUCTIONS/REASONING_COMMIT_REQUIREMENT and composition order | workflow.binding_context(1), workflow.decision_protocol(1), workflow.is_job_source(1), workflow.job_episodes(1), workflow.knowledge(1), workflow.launch_instructions(1), workflow.native_event_information(1), workflow.specialist(1) |
| task_state.py | 108 | episode source state, checkpoint/restore, record_effect | _live_original_runtime.ActionLeaf(1), _live_original_runtime.EFFECT_VERSION(1), _live_original_runtime.Episode(1), _live_original_runtime.Record(1), _live_original_runtime._json(2), _live_original_runtime._object(1), _live_original_runtime._plain(1), _live_original_runtime.interpretation_schema(1), _live_original_runtime.json(4), import:root.a110.episode_source_failure(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.archive(1), self.workflow.completions(4), self.workflow.controller_value(1), self.workflow.execution_binding(4), self.workflow.inprocess_replay(7), self.workflow.journal(5), self.workflow.progress_provider(2), self.workflow.recover_commissions(1), self.workflow.run_id(1), self.workflow.source_credit_view(1), self.workflow.store(2), table:runtime_actions(5), workflow.context(1), workflow.grains(1) |
| task_suspension.py | 9 | suspension_changed -> execution backend suspension | self.workflow.execution_backend(1), self.workflow.execution_handle(2) |
| terminal_execution.py | 131 | TerminalExecutionBehavior: instruction-led terminal execution per resource kind (state, catalog, execute with receipts, completion, facts, resolve, validate, credit) | import:root.a110.acquisition(1), import:root.a110.communication(8), import:root.a110.domain(1), import:root.a110.library.execution_operation_information(1), import:root.a110.practical_execution_operations(0), import:root.a110.practical_execution_records(3), import:root.a110.practical_execution_state(1), import:root.a110.practical_receipt_information(3), import:root.a110.practical_yield(1), import:root.a110.terminal_execution(5), import:root.a110.terminal_scientific_evidence(2), yield:PracticalYieldEstimator(1) |
| to_parent.py | 38 | facts (FBA or handoff/result/file refs, origin, completed) + closed credit; validate_report | import:root.a110.communication(2), import:root.a110.flux_balance_return_views(1) |
| work_operations.py | 36 | catalog and execute dispatch (local files, FBA, native windows); invalid outcome on error | import:root.a110.communication(2), import:root.a110.execution_contracts(1), import:root.a110.native_file_capture(1), import:root.a110.native_flux_balance_results(1) |
| yield_estimator.py | 118 | request yield class; task yield profiles; results yield (accumulation / bounded remaining coverage / completion proof); unused launch yield methods | import:root.a110.communication(4), import:root.a110.execution_contracts(1), import:root.a110.library.execution_result_contract(1), import:root.a110.numerical(19), import:root.a110.practical_yield(5), yield:BoundedYieldController(1), yield:NumericBand(2), yield:PracticalYieldEstimator(5), yield:YieldController(6), yield:YieldEstimate(2), yield:YieldParameters(7), yield:estimate_bounded_credit_yield(1) |

## Carried over

Carried over on 19 November 2026 into the ten-file form (no children: no `msg_to_child.py`, no `read_from_child.py`). Old files read with `git show 97308b94c:<path>` from the `gene_annotation_episode_disk` checkout (the working checkout has no `.git`). The old files of this episode have the same function list as those of `hpc_work_planning/execution_result_acquisition`; this folder is a private copy of that carried form with this episode's own binding path. One row per row of `runs/carry_over/functions/a110__biochemical_feasibility_evidence__execution_result_acquisition.tsv` (first three columns copied). Machinery rows are not carried (reason given). Library candidates: `selector_progress` and `native_results_complete` (windows, requested spans) are not in `episode_support/` and stay in this episode.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_outcome.py | _outcome | function -> episode function | task.py _outcome (extended with artifact_refs) |
| binding_record.py | ResultsBindingRecord | class -> machinery | binding_record.py is old-runner machinery (the binding record) |
| binding_record.py | ResultsBindingRecord.as_record | method -> machinery | the binding's own as_record() is deleted (README 3d) |
| closed_credit.py | ResultsClosedCredit | class -> machinery | closed-credit pinning with digests of context, binding, completion, archive, observation history and receipt prefix, read from runtime_* tables: old-runner machinery; the system hands final_to_parent the credit the controller stopped on |
| closed_credit.py | ResultsClosedCredit._closed_credit_carrier | method -> machinery | closed-credit pinning with digests of context, binding, completion, archive, observation history and receipt prefix, read from runtime_* tables: old-runner machinery; the system hands final_to_parent the credit the controller stopped on |
| closed_credit.py | ResultsClosedCredit._closed_credit_receipts | method -> machinery | closed-credit pinning with digests of context, binding, completion, archive, observation history and receipt prefix, read from runtime_* tables: old-runner machinery; the system hands final_to_parent the credit the controller stopped on |
| closed_credit.py | ResultsClosedCredit._closed_credit_value | method -> machinery | closed-credit pinning with digests of context, binding, completion, archive, observation history and receipt prefix, read from runtime_* tables: old-runner machinery; the system hands final_to_parent the credit the controller stopped on |
| closed_credit.py | ResultsClosedCredit._closed_credit_facts | method -> machinery | closed-credit pinning with digests of context, binding, completion, archive, observation history and receipt prefix, read from runtime_* tables: old-runner machinery; the system hands final_to_parent the credit the controller stopped on |
| closed_credit.py | ResultsClosedCredit._closed_operational_credit_view | method -> machinery | closed-credit pinning with digests of context, binding, completion, archive, observation history and receipt prefix, read from runtime_* tables: old-runner machinery; the system hands final_to_parent the credit the controller stopped on |
| completion.py | ResultsCompletion | class -> machinery | completion proof (practical_completion_v1), completion_for_action and verify_completion re-validation from runtime_actions / runtime_observations: a completion proof is not a controller input (README 3d, 7b) |
| completion.py | ResultsCompletion._native_results_complete | method -> episode function | messages/internal_summary.py native_results_complete (used by facts and by action for the already-completed refusal) |
| completion.py | ResultsCompletion._proof_for_action | method -> machinery | completion proof (practical_completion_v1), completion_for_action and verify_completion re-validation from runtime_actions / runtime_observations: a completion proof is not a controller input (README 3d, 7b) |
| completion.py | ResultsCompletion.completion_for_action | method -> machinery | completion proof (practical_completion_v1), completion_for_action and verify_completion re-validation from runtime_actions / runtime_observations: a completion proof is not a controller input (README 3d, 7b) |
| completion.py | ResultsCompletion._closed_completion_verdict | method -> machinery | completion proof (practical_completion_v1), completion_for_action and verify_completion re-validation from runtime_actions / runtime_observations: a completion proof is not a controller input (README 3d, 7b) |
| completion.py | ResultsCompletion.verify_completion | method -> machinery | completion proof (practical_completion_v1), completion_for_action and verify_completion re-validation from runtime_actions / runtime_observations: a completion proof is not a controller input (README 3d, 7b) |
| configuration.py | ResultsConfiguration | class -> episode function | settings and assignment fields: log_window_bytes, yield profiles -> ctx.settings / settings (yield_estimator.py, task.py); acquired_record_unit, resource_kind -> assignment (messages/read_from_parent.py); handoff_unit dropped (its credit term is always 0); resources, initial_information, tool_registry, job_progress_provider, TerminalExecutionBehavior, FBA bindings: see unplaced |
| configuration.py | ResultsConfiguration.__init__ | method -> episode function | settings and assignment fields: log_window_bytes, yield profiles -> ctx.settings / settings (yield_estimator.py, task.py); acquired_record_unit, resource_kind -> assignment (messages/read_from_parent.py); handoff_unit dropped (its credit term is always 0); resources, initial_information, tool_registry, job_progress_provider, TerminalExecutionBehavior, FBA bindings: see unplaced |
| credit.py | ResultsCredit | class -> episode function | credit.py |
| credit.py | ResultsCredit._generic_result_selector_progress | method -> episode function | credit.py selector_progress |
| credit.py | ResultsCredit.credit_kind | method -> machinery | credit_kind is deleted (README 3d) |
| credit.py | ResultsCredit.project_credit | method -> episode function | credit.py credit (the closed-credit alternative is machinery) |
| credit.py | ResultsCredit._live_project_credit | method -> episode function | credit.py credit, credit_binding (the FBA branch is unplaced) |
| credit.py | ResultsCredit.credit_view | method -> machinery | credit view record deleted: credit returns the number, the other fields are in internal_summary (README 3d) |
| episode.py | ExecutionEpisode | class -> episode function | episode.py ExecutionResultAcquisition (the one class; mix-ins deleted) |
| from_parent.py | ResultsFromParent | class -> episode function | messages/read_from_parent.py |
| from_parent.py | ResultsFromParent.required_return_sources | method -> episode function | messages/final_to_parent.py RETURN_FORM (execution_result_refs required) |
| from_parent.py | ResultsFromParent.child_assignment_schema | method -> machinery | child_assignment_schema (a branch that never ran); deleted (README 3b C3) |
| from_parent.py | ResultsFromParent.assignment_schema | method -> episode function | messages/read_from_parent.py ASSIGNMENT_FORM, NATIVE_SELECTOR_SCHEMA (the typed selector extensions are unplaced) |
| from_parent.py | ResultsFromParent.prepare_assignment | method -> episode function | messages/read_from_parent.py read_from_parent (saved-commission restore: machinery; handoff target read: BLOCKED-ON-JOB-SERVICE in task.py _read_target) |
| from_parent.py | ResultsFromParent.initial_references | method -> machinery | initial references of the old receipt ledger; the handoff ref is the assignment record_refs field (custody) |
| goal.py | ResultsGoal | class -> episode function | goal.py; children and permitted actions are task.py CHILD_SLOTS = {} and the tool-only action |
| goal.py | ResultsGoal.child_roles | method -> episode function | task.py CHILD_SLOTS = {} |
| goal.py | ResultsGoal.allowed_children | method -> episode function | task.py CHILD_SLOTS = {} |
| goal.py | ResultsGoal.permitted_common_actions | method -> episode function | task.py selection_schema / action (tool only) |
| initial_information.py | initial_information | function -> episode function | unplaced: reads the declared resource readers (library execution_initial_information, not in episode_support); a recorded read of the job service in decide (describe_result_target) replaces what it showed |
| input_versions.py | ResultsInputVersions | class -> episode function | unplaced: input versions of flux balance inputs (execution_input_versions, flux_balance_request_binding not carried); no native results use |
| input_versions.py | ResultsInputVersions._versions | method -> episode function | unplaced: input versions of flux balance inputs (execution_input_versions, flux_balance_request_binding not carried); no native results use |
| input_versions.py | ResultsInputVersions._flux_balance_inputs | method -> episode function | unplaced: input versions of flux balance inputs (execution_input_versions, flux_balance_request_binding not carried); no native results use |
| input_versions.py | ResultsInputVersions._matches_flux_balance_assignment | method -> episode function | unplaced: input versions of flux balance inputs (execution_input_versions, flux_balance_request_binding not carried); no native results use |
| instructions.py | ResultsInstructions | class -> episode function | goal.py GOAL |
| instructions.py | ResultsInstructions.instructions | method -> episode function | goal.py GOAL, used as the instructions in task.py decide |
| internal_summary.py | ResultsInternalSummary | class -> episode function | messages/internal_summary.py |
| internal_summary.py | ResultsInternalSummary._with_selected_execution_task | method -> episode function | unplaced: selected_execution_task of flux balance work (flux_balance_request_binding, scientific_parent_task not carried) |
| internal_summary.py | ResultsInternalSummary.decision_context | method -> episode function | messages/internal_summary.py internal_summary (execution_assignment, execution_progress) and task.py decide (execution_target_description); the compact FBA, local file source and FBA selector views are unplaced |
| internal_summary.py | results_decision_snapshot | function -> episode function | messages/internal_summary.py internal_summary and task.py decide (the shared state fields from the old runner are machinery) |
| native_file_acquisition.py | ResultsNativeFileAcquisition | class -> episode function | task.py _acquire, _window_requests, _publish_result and the three tools (intent/observation/window files and receipt replay: machinery; the refusal read from runtime_actions is the already_completed argument); target, observation and window reads BLOCKED-ON-JOB-SERVICE |
| native_file_acquisition.py | ResultsNativeFileAcquisition._execute_native_results | method -> episode function | task.py _acquire, _window_requests, _publish_result and the three tools (intent/observation/window files and receipt replay: machinery; the refusal read from runtime_actions is the already_completed argument); target, observation and window reads BLOCKED-ON-JOB-SERVICE |
| native_target_state.py | ResultsNativeTargetState | class -> machinery | state() always refused (practical resource role required): nothing to carry |
| native_target_state.py | ResultsNativeTargetState.state | method -> machinery | state() always refused (practical resource role required): nothing to carry |
| presentation.py | present_context | function -> episode function | unplaced: prompt renderers hpc_prompt, monitor_prompt, receiver_prompt, scientific_decision_presentation are not in episode_support; decide passes the context as JSON |
| receipt_selection.py | ResultsReceiptSelection | class -> machinery | selection of known records through runtime receipts and the Store (_received): custody replaces it; results come from view.outcomes (messages/internal_summary.py) |
| receipt_selection.py | ResultsReceiptSelection._received | method -> machinery | selection of known records through runtime receipts and the Store (_received): custody replaces it; results come from view.outcomes (messages/internal_summary.py) |
| received_execution_information.py | received_execution_information | function -> machinery | configured/received result readers of the old catalog (received_execution_requires_authority): old-runner configuration |
| received_launch_requests.py | ResultsReceivedLaunchRequests | class -> machinery | launch request schemas of the copied shared execution binding; not used by the results role |
| received_launch_requests.py | ResultsReceivedLaunchRequests._permitted | method -> machinery | launch request schemas of the copied shared execution binding; not used by the results role |
| received_launch_requests.py | ResultsReceivedLaunchRequests._request_schema | method -> machinery | launch request schemas of the copied shared execution binding; not used by the results role |
| received_launch_requests.py | ResultsReceivedLaunchRequests._launch | method -> machinery | launch request schemas of the copied shared execution binding; not used by the results role |
| report_delivery.py | ResultsReportDelivery | class -> episode function | messages/final_to_parent.py final_to_parent (finish: saving the form and release are machinery) |
| report_delivery.py | ResultsReportDelivery.finish | method -> episode function | messages/final_to_parent.py final_to_parent (finish: saving the form and release are machinery) |
| resource_information.py | ResultsResourceInformation | class -> episode function | unplaced: resource tool contracts of configured resources (library execution_operation_information, native_flux_balance_tool_info not carried); the catalog shown is task.py CATALOG |
| resource_information.py | ResultsResourceInformation.resource_tool_contracts | method -> episode function | unplaced: resource tool contracts of configured resources (library execution_operation_information, native_flux_balance_tool_info not carried); the catalog shown is task.py CATALOG |
| result_publication.py | ResultsResultPublication | class -> episode function | task.py _publish_result |
| result_publication.py | ResultsResultPublication._publish_result | method -> episode function | task.py _publish_result |
| result_records.py | native_result_operation_catalog | function -> episode function | task.py CATALOG (tool names execution_results_status / collect / read) |
| result_state.py | ResultsResultState | class -> episode function | messages/read_from_parent.py read_from_parent (validation of selector); result directory preparation, local file source and compact FBA initialisation: machinery / unplaced |
| result_state.py | ResultsResultState.initialize | method -> episode function | messages/read_from_parent.py read_from_parent (validation of selector); result directory preparation, local file source and compact FBA initialisation: machinery / unplaced |
| saved_commission.py | ResultsSavedCommission | class -> machinery | restore of an admitted Results commission from runtime_actions / runtime_episodes / runtime_report_attempts |
| saved_commission.py | ResultsSavedCommission._recorded_results_assignment | method -> machinery | restore of an admitted Results commission from runtime_actions / runtime_episodes / runtime_report_attempts |
| target_custody.py | ResultsTargetCustody | class -> episode function | unplaced: a handoff target must match this episode assignment (needs the handoff target: BLOCKED-ON-JOB-SERVICE, task.py _read_target) |
| target_custody.py | ResultsTargetCustody._context_target | method -> episode function | unplaced: a handoff target must match this episode assignment (needs the handoff target: BLOCKED-ON-JOB-SERVICE, task.py _read_target) |
| task.py | ResultsTask | class -> episode function | task.py decide / action / tools (the loop, replay, checkpoint, redelivery, reason action and exchange are machinery) |
| task.py | ResultsTask.next | method -> episode function | task.py decide / action / tools (the loop, replay, checkpoint, redelivery, reason action and exchange are machinery) |
| task.py | ResultsTask.apply_response | method -> episode function | task.py decide / action / tools (the loop, replay, checkpoint, redelivery, reason action and exchange are machinery) |
| task.py | ResultsTask.execute | method -> episode function | task.py decide / action / tools (the loop, replay, checkpoint, redelivery, reason action and exchange are machinery) |
| task_decision.py | ResultsTaskDecision | class -> episode function | task.py decide / action |
| task_decision.py | ResultsTaskDecision.call | method -> episode function | task.py decide (ModelRequest); recording of the model call is machinery |
| task_decision.py | ResultsTaskDecision.instructions | method -> episode function | goal.py GOAL used in task.py decide |
| task_decision.py | ResultsTaskDecision.conversation_key | method -> machinery | conversation state |
| task_decision.py | ResultsTaskDecision.interpretation_context | method -> machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.exchange_schema | method -> machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.exchange_response | method -> machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.validate_contract_exchange_request | method -> machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.validate_contract_exchange_history | method -> machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.exchange_decision | method -> machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.decision_completion | method -> machinery | provider call wrapper |
| task_instructions.py | instructions | function -> episode function | task.py decide (goal.py GOAL as instructions); tool-knowledge / launch-instruction texts, delivery repair and exchange replacement describe actions that no longer exist and are not appended |
| task_state.py | ResultsTaskState | class -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_state.py | ResultsTaskState.__init__ | method -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_state.py | ResultsTaskState.bind_execution_context | method -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_state.py | ResultsTaskState.record_execution_failure | method -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_state.py | ResultsTaskState.restore_checkpoint | method -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_state.py | ResultsTaskState.restore | method -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_state.py | ResultsTaskState.record_effect | method -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_state.py | ResultsTaskState.checkpoint | method -> machinery | per-episode decision state, checkpoint / restore, record_effect, record_execution_failure (a failed tool returns its outcome) |
| task_suspension.py | ResultsTaskSuspension | class -> machinery | wait / suspension machinery |
| task_suspension.py | ResultsTaskSuspension.suspension_changed | method -> machinery | wait / suspension machinery |
| terminal_execution.py | TerminalExecutionBehavior | class -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior._operations | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior._assignment | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.initialize | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.state | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.catalog | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.execute | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.facts | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.resolve | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | method -> episode function | unplaced: TerminalExecutionBehavior is a copy of the shared execution binding (practical state, receipts, completion proof) used only through configuration for launch roles; the results role reads the target through the job service (task.py _read_target / _observe_target / _read_window, BLOCKED-ON-JOB-SERVICE) |
| to_parent.py | ResultsToParent | class -> episode function | messages/final_to_parent.py |
| to_parent.py | ResultsToParent.facts | method -> episode function | messages/internal_summary.py facts (the closed credit facts are machinery) |
| to_parent.py | ResultsToParent._live_facts | method -> episode function | messages/internal_summary.py facts (flux balance facts unplaced) |
| to_parent.py | ResultsToParent.validate_report | method -> episode function | messages/final_to_parent.py validate_report (fact comparison only; the axis has no validate_form and RETURN_FORM validates) |
| work_operations.py | ResultsWorkOperations | class -> episode function | task.py |
| work_operations.py | ResultsWorkOperations.catalog | method -> episode function | task.py CATALOG, TOOLS |
| work_operations.py | ResultsWorkOperations.execute | method -> episode function | task.py _acquire (invalid outcome on ValueError / TypeError); local file source and FBA routes unplaced |
| yield_estimator.py | ExecutionEpisodeYield | class -> episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | method -> machinery | launch yield controllers of the copied shared execution binding, not used by the results role (README 7b: deleted) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | method -> episode function | yield_estimator.py _profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | method -> episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._launch_yield_controller | method -> machinery | launch yield controllers of the copied shared execution binding, not used by the results role (README 7b: deleted) |
| yield_estimator.py | ExecutionEpisodeYield._launch_local_yield_controller | method -> machinery | launch yield controllers of the copied shared execution binding, not used by the results role (README 7b: deleted) |
| yield_estimator.py | ExecutionEpisodeYield._launch_hpc_yield_controller | method -> machinery | launch yield controllers of the copied shared execution binding, not used by the results role (README 7b: deleted) |
| yield_estimator.py | ExecutionEpisodeYield._results_yield_controller | method -> episode function | yield_estimator.py yield_controller (accumulation / bounded quality; exhaustion and completion-proof estimators deleted) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | method -> machinery | PracticalYieldEstimator is deleted (README 7b) |
