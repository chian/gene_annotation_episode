# a110/biochemical_feasibility_evidence/hpc_work_planning — episode intent at 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/hpc_work_planning/<file>`
(only the 46 files directly in this folder, 2,238 lines; `tests/` (6 files) not read; no grading/ or scoring/; child folders
`execution_job_submission/` (written up separately in this batch), `execution_progress_assessment/`, `execution_result_acquisition/`,
`hpc_allocation_execution/`, `hpc_resource_prediction/` belong to other agents).

## Purpose (own words)

`binding_path = 'biochemical_feasibility_evidence/hpc_work_planning'`, `commissioning_parent = 'biochemical_feasibility_evidence'`,
`roles = entry_roles = ('hpc',)`, `replaces_default_instructions = True`, class `HPCEpisode`, decision source `HPCWorkTask`, renderer
`library.hpc_prompt.render_hpc_prompt`. `goal.instructions` (abridged; full text in goal.py):

> Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource demand. The hpc parent
> can commission hpc_prediction and hpc_execution as sisters: prediction fits/measures/compares; execution prepares, launches, monitors and
> parses the selected work. Both assignments copy hpc_child_commission exactly and carry the hpc parent owner_episode_id. Both sisters inherit
> exactly hpc_child_scope, including an empty subject_refs list for an operational task with no biological inputs. ... Use hpc_report_form as
> the return contract. ... No historical validation support means no invented model-improvement credit. Queue/setup costs belong to an
> allocation, which should carry enough useful work. When candidates are absent, discover the remote environment and documentation with
> hpc.discovery.run, then design candidate portfolios with hpc.candidate.propose. ... You choose the real inputs, database, executable
> commands, resources, worker code and preparation instructions. Never fabricate inputs or receipts. Every work unit writes result.json and
> progress.json under os.environ["HPC_UNIT_DIRECTORY"] ... Compute commands must run on allocated compute nodes using the facility launcher.
> ... A plan freezes its original forecast, scientific manifest and acceptance criteria. Commission launch -> launch_hpc with that actual job
> and resource. ... Use hpc_launch_report_form as the Launch return contract. If a completed Launch return omitted its receipt, use
> redeliver_report ...; report repair must not commission another Launch. Attach that received handoff. Use hpc.monitor once when another
> observation can affect your decision ... Use hpc.results directly for known parsing. Commission monitor/results children only for actual
> investigation. ... When hpc_monitor_controllers is present, select hpc.monitor.wait ... Do not poll for credit or duplicate a submitted
> attempt. Never replace an uncertain submission. Accepted accomplishment, model improvement, and fixed prospective forecast validation are the
> only parent credit components; launch-local credits are not added again.

## Task and instructions

`task_instructions.instructions` = binding goal text (replaces the default) + tool knowledge + launch library + pending_child_delivery repair
paragraph + (wait permitted) in-process wait paragraph + (wait permitted and native events) native_event_targets paragraph.
Decision inputs add `requested_action_history` for HPC contexts and `execution_expectations` captured for 'hpc'. The task loop wires
`library.hpc_handoff_report_contract.validate_hpc_launch_report_contract` as `_validate_hpc_launch_report_contract` and validates reports with
grain 'hpc'.

## What it reads from its parent's assignment

`assignment_schema('hpc')`: `commission_source_ref` (reference) and, when commissions are configured, `commission_id` (enum) with
`oneOf` one of them (otherwise commission_source_ref required); optional `tool_request {name, resources api|local|hpc, arguments_json,
result_reader, objective}`. `prepare_assignment`: a commission_source_ref must be in `parent.received_record_refs` and readable by
`hpc_commission_sources.read`; a tool_request is resolved against the parent's frozen tool library
(`services.workflow.biochemical_feasibility_evidence_binding.tool_library`), must name an actual result reader and validate its arguments; it
carries the execution_rule "Implement this exact requested computation through the HPC template ... do not replace scientific grading with the
allocation acceptance score."; with `require_commission_yield` the commission must carry `yield_bindings`.
Configuration operands: services, store, run_id, directory, `resources` (at least one `pbs_ssh`), `commissions` (each through
`hpc_campaign.validate_commission`), optional `shared_execution_memory` (ExecutionMemory), `require_commission_yield`.

## Children it may commission (child_roles = hpc_prediction, hpc_execution, launch, monitor, results)

| Role | Child folder | Sends | Takes back |
|---|---|---|---|
| hpc_prediction | hpc_resource_prediction | `{commission_id \| commission_source_ref, owner_episode_id}`; owner must be this hpc episode and commission identity equal the parent's | `receive_prediction_report`: recorded-admission refs, else progress provider `receive_form`, form refs + `episode_bindings.received_form_references`, receipts (child_form / report_redelivery), tool attributions |
| hpc_execution | hpc_allocation_execution | same shape and checks | `receive_allocation_report` (same path) |
| launch | execution_job_submission | the frozen plan's `launch_assignment`; the child's `prepare_assignment` calls this folder's `authenticate_launch` (exact planned launch only, reserves `launch:<plan_id>` once, never after the allocation closed). `LaunchPreparation.initial_decision_context` (role launch / launch_hpc under this hpc path) supplies `hpc_execution_job {plan_id, objective, scientific_manifest, scientific_acceptance, supplied_input_file (immutable plan JSON), coordinator_workspace, instructions}` | `hpc_launch_report_form {execution_handoff_refs}`; `LaunchReceiptCustody.original_launch_handoff` recovers the actual PBS handoff from committed native outcomes under this hpc path (report repair) |
| monitor | execution_progress_assessment | `_ASSIGNMENT` from that child's contracts, validated unchanged ("This parent requests information; it never polls here") | `receive_progress`: episode_progress refs of the typed form, signed content digest, `provider._receive_progress` |
| results | execution_result_acquisition | assignment unchanged; request built by `to_child_execution_result_acquisition.assemble_request` (goal, scope, initial_report, inprocess order, report_contract_declaration, job/episode assignment, biochemical_feasibility_evidence, knowledge_inheritance) | `receive_report`: recorded-admission refs or specialist progress receivers / provider form, receipts, tool attributions |

`create_execution_bindings(*args, **configuration)` constructs this hpc parent's private Launch, local Launch, HPC Launch and Results bindings.
Common actions: `tool, child, redeliver_report` and also `wait` unless the commission carries `monitoring` (then waiting goes through
`hpc.monitor.wait`).

## Decision state and what it shows the model

Common snapshot (without the annotation-axis branch and monitoring-information fields) plus `internal_summary.decision_context`:
`hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`, `hpc_child_scope`, `hpc_child_commission`,
`hpc_launch_deliveries` (launch child delivery_ref + delivered form from runtime_report_attempts), `hpc_launch_report_form`, `hpc_tool_request`,
`hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form` {hpc_credit, hpc_model_ref, hpc_result_refs},
`hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_activity_decision` (waiting.activity_advice from the last observation's
activity_mode: wait/collect, suggested tool, active_next_gain, pending_expected_credit, pending_credit_upper_bound), `hpc_queue_refs`,
shared memory and shared history refs, `hpc_available_training_ids`. The ledger is initialised with the prior reference model and, with shared
memory, a model fitted to imported shared history.

## Tools offered (work_operations.catalog)

`hpc.read`, `hpc.compare` (all approved portfolios; nothing launched), `hpc.history.refresh` (shared memory only), `hpc.discovery.run` (one
lightweight remote inspection over the established SSH transport; no submission/installation/computation), `hpc.candidate.propose`
(candidate_json: id, queue, nodes, wall_seconds, features, optional resource_capacity, units, files, preparation instructions; identities
immutable), `hpc.queue.observe`, `hpc.plan` (freeze one portfolio and forecasts → launch assignment; requires a fresh, enabled, started
Execution queue and observed queue limits), `hpc.handoff` (bind the received PBS handoff to the frozen plan; attaches a MonitorCronController
when the commission has monitoring), `hpc.monitor` (observe job + allocation-status.json + unit progress once; conditional forecast update),
`hpc.monitor.wait` (attached controller: persist timer, wait, observe once), `hpc.results` (parse result.json of complete/failed units, hash
check against the unit receipt, apply acceptance predicates, publish `episode.hpc_result` sources, close and export the allocation),
`hpc.allocation.order` (reorder pending original units). Every action is cached by operation key in the HPCLedger and saved via
`ledger.save_action`; invalid arguments return invalid outcomes with recovery feedback.

## Credit

`credit_kind` = `operational`; `credit_view` = `HPCLedger.credit_view()` (contributions: accepted actual obligations, model improvement,
prospective forecast validation slots). Repeated polling adds none (`hpc_credit` meaning: "Signed measured credit").

## Continuation

`yield_controller`: requires `require_commission_yield`; `commission['yield_bindings'][role]` gives `cutoff` and `parameters`;
`YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=HPCContinuationEstimator(verify).with_continuation_cost(cutoff))`.
`continuation_for_action` builds and freezes a continuation evidence packet per operation key: earned_wait_credit 0; remaining obligations;
zero when all accepted; per open monitor controller the pending valuation (unresolved acceptance upper bound when outputs await collection,
else `choose_schedule` valuation with per-obligation expected credit scaled by `min(1.0, expected_continuation/expected_actual)`),
`pending_action` collect, active_credit_ceiling 0 when nothing new can be trained and all remaining obligations are pending single-unit work,
and `active_history_indices` (non-passive actions from runtime_observations/runtime_actions). Closest yield_control estimator: **completion with
a target** (remaining original obligations are the target; pending allocation valuations are its evidence) — the HPC pending-work valuation has
to enter as that estimator's settings/inputs, not as a fourth estimator.

## Report to parent

`fact_sources`: `hpc_credit`, `hpc_model_ref` (namespace hpc_model), `hpc_accepted_obligations`, `hpc_result_refs` (received sources).
`resolve`: hpc_model refs from the ledger, otherwise `reference_in_context`. `validate_report`: x-source fields equal facts
(`hpc_report_disagrees_with_recorded_evidence`). `closed_models.frozen_reference` validates a closed model id read-only from the saved form and
the ledger sqlite. `report_delivery.finish` saves facts+form once.

## Notes for carrying over

- `resource_discovery` runs `subprocess.run(..., timeout=90)` and truncates stdout to 65536 / stderr to 8192 bytes; `measured_history` keeps at
  most 2000 shared observations; it also hard-codes `cd /lus/flare/projects/BioReason-Aurora-Test`. The timeout is an elapsed-time limit the
  project rules forbid; flag before carrying over.
- `continuation_for_action` scales expected credit by `min(1.0, ...)`; check against the never-bound-credit rule (it scales a forecast, not earned credit).

## Differences from similar episodes

- vs `a107/partner_presence_evidence/hpc_work_planning`: no `api_job_execution` binding (a107 builds 5 execution bindings, A110 4); no
  `received_api_reports`; the results/prediction/allocation receivers do not add native timing receipts (`native_timing_information`) as a107's
  do; the summary adds `hpc_owner_episode_id`; ExecutionTargetReader is built without `api_execution`; a107 task_decision wraps snapshots in
  `infernal_receiver_context`.
- vs the monitor and result episodes: owns a persistent HPCLedger (portfolio state, forecasts, models), five child kinds, and a continuation
  evidence packet rather than an accumulation/coverage yield.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 0 | empty package marker | none |
| allocation_handoff.py | 35 | hpc.handoff: bind received PBS handoff to the frozen plan (+ monitor controller); dispatch monitor.wait/order/observe on an attached plan | import:root.a110.episode_bindings(1), import:root.a110.hpc_monitoring(1) |
| allocation_observations.py | 82 | ExecutionTargetReader for pbs_ssh; read allocation-status.json and unit progress; observe once; phase/rate telemetry; then monitor or results | import:root.a110.episode_bindings(1), import:root.a110.execution_progress(1), import:root.a110.hpc_campaign(3) |
| allocation_order.py | 16 | hpc.allocation.order: write allocation control reordering original units | none |
| allocation_results.py | 74 | hpc.results: hash-checked unit results, acceptance predicates, publish episode.hpc_result sources, close/export allocation | import:root.a110.communication(1), import:root.a110.hpc_campaign(1), import:root.a110.hpc_queue(module)(1) |
| binding_record.py | 8 | as_record hpc_episode_v1: resources, commissions, shared memory, require_commission_yield | none |
| closed_models.py | 27 | frozen_reference: validate closed hpc_model id read-only from saved form and ledger sqlite | import:root.a110.communication(1), import:root.a110.episode_return_records(1), import:root.a110.hpc_queue(module)(1), table:runtime_forms(1) |
| configuration.py | 32 | operands; at least one pbs_ssh resource; validate commissions; require yield bindings; ExecutionMemory | import:root.a110.communication(4), import:root.a110.execution_memory(1), import:root.a110.hpc_campaign(1) |
| credit.py | 16 | credit_kind operational; credit_view = ledger.credit_view() | none |
| decision_inputs.py | 53 | extra decision inputs incl. requested_action_history and hpc execution expectations | _live_original_runtime.child_option_information(1), import:root.a110.episode_work_report(2), import:root.a110.library.hpc_prompt(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow(passed)(3), self.workflow.available_child_roles(1), self.workflow.binding_context(1), self.workflow.episode_bindings(1), self.workflow.execution_expectations(1), self.workflow.launch_instructions(2), self.workflow.native_estimation_context(1), self.workflow.pending_work(1), self.workflow.permits_common_action(1), self.workflow.resource_context(1), self.workflow.resource_estimator(4), self.workflow.waiting_support(1) |
| decision_state.py | 31 | common decision snapshot and binding decision_context | _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.Mapping(2), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), _live_original_runtime.json(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.catalog(1), self.workflow.controller_binding(1), self.workflow.delivery_status(1), self.workflow.extra_report_sources(1), self.workflow.job_episode_options(1), self.workflow.journal(2), self.workflow.knowledge(1), self.workflow.local_outcome_preview(1), self.workflow.pending_work(1), self.workflow.receipt_projection(1), self.workflow.run_id(1), self.workflow.source_credit_binding(1), self.workflow.source_credit_view(1), self.workflow.specialist(1), self.workflow.store(3), self.workflow.tools(1), self.workflow.working_state(1), table:runtime_actions(1) |
| episode.py | 101 | HPCEpisode composition; roles hpc; child roles; common actions; child request/receivers/assembler; create_execution_bindings | import:root.a110.library.hpc_prompt(1) |
| forecast_observations.py | 80 | freeze forecasts into validation slots; last forecast; measure queue/work/setup metrics; hpc.monitor conditional forecast update | import:root.a110.hpc_campaign(1), import:root.a110.hpc_queue(module)(1), import:root.a110.library(4), import:root.a110.library.hpc_resource_prediction(2) |
| from_child_execution_job_submission.py | 46 | LaunchReceiptCustody.original_launch_handoff: recover the plan's actual PBS handoff from committed outcomes | import:root.a110.communication(2), import:root.a110.hpc_ledger(1), import:root.a110.hpc_queue(module)(1), import:root.a110.method_loop.identities(1), table:runtime_actions(1), table:runtime_episodes(1) |
| from_child_execution_progress_assessment.py | 23 | receive monitor form progress refs with content-digest signature | import:root.a110.communication(4), import:root.a110.domain(1), import:root.a110.method_loop.durable(1) |
| from_child_execution_result_acquisition.py | 32 | receive results child form through recorded admission / progress receivers / receipts | _live_original_runtime._references_in(1), import:root.a110.delivery_counterpart(1), import:root.a110.episode_return_records(1), import:root.a110.runtime(module)(1), workflow.binding_context(4), workflow.episode_bindings(1), workflow.is_job_source(2), workflow.progress_provider(4), workflow.receipts(3), workflow.receive_tool_attributions(1), workflow.run_id(5), workflow.specialist(1), workflow.store(3) |
| from_child_hpc_allocation_execution.py | 20 | receive allocation child form (receipt path) | _live_original_runtime._references_in(1), import:root.a110.episode_return_records(1), import:root.a110.runtime(module)(1), workflow.binding_context(2), workflow.episode_bindings(1), workflow.is_job_source(2), workflow.progress_provider(2), workflow.receipts(3), workflow.receive_tool_attributions(1), workflow.run_id(3), workflow.store(3) |
| from_child_hpc_resource_prediction.py | 20 | receive prediction child form (receipt path) | _live_original_runtime._references_in(1), import:root.a110.episode_return_records(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), workflow.binding_context(2), workflow.episode_bindings(1), workflow.is_job_source(2), workflow.progress_provider(2), workflow.receipts(3), workflow.receive_tool_attributions(1), workflow.run_id(3), workflow.store(3) |
| from_parent.py | 69 | assignment schema (commission id/source ref, tool_request); commission lookup; tool_request resolution with execution_rule | import:root.a110.communication(2), import:root.a110.domain(2), import:root.a110.execution_contracts(2), import:root.a110.hpc_commission_sources(1) |
| goal.py | 10 | own goal text | none |
| initial_information.py | 8 | resource_information from catalog readers of this binding path | import:root.a110.library.execution_initial_information.presentation(1) |
| internal_summary.py | 56 | hpc decision_context (commission, candidates, forms, deliveries, models, plans, monitors, activity advice, queue, shared history) | import:root.a110.communication(1), import:root.a110.library(1), table:runtime_episodes(1), table:runtime_report_attempts(1) |
| measured_history.py | 82 | training history from commission + shared history + closed allocations; shared history query/filter (<=2000); export closed measurements; hpc.history.refresh | import:root.a110.execution_guidance(1), import:root.a110.hpc_history(1), import:root.a110.library.hpc_resource_prediction(4) |
| portfolio_candidates.py | 23 | hpc.candidate.propose: immutable candidate identity, revalidated commission | import:root.a110.hpc_campaign(1) |
| portfolio_comparison.py | 44 | candidate list, features, compare all candidates by net expected value; hpc.compare | import:root.a110.hpc_queue(module)(1), import:root.a110.library(2) |
| portfolio_planning.py | 38 | hpc.plan: fresh enabled queue, limits check, build_plan, original prediction/reference, prediction episode id, freeze forecast | import:root.a110.hpc_campaign(1), import:root.a110.hpc_queue(module)(1), import:root.a110.library(2) |
| portfolio_state.py | 38 | HPCLedger per owner episode; owner record; tool_request once; initialize prior/shared-history model; current model | import:root.a110.communication(4), import:root.a110.domain(1), import:root.a110.hpc_ledger(1), import:root.a110.hpc_queue(module)(1), import:root.a110.library(2) |
| queue_observations.py | 35 | observe PBS queue (fresh memory cache), queue freshness for planning; hpc.queue.observe | import:root.a110.execution_guidance(1), import:root.a110.hpc_queue(module)(1) |
| received_evidence.py | 60 | known refs; resolve received episode.hpc_result sources in scope; hpc.read retained evidence | import:root.a110.communication(1) |
| received_execution_information.py | 4 | select this path's configured/received result readers | none |
| report_delivery.py | 23 | finish: save facts+form once, release, return form | _live_original_runtime.Record(2), _live_original_runtime._json(2), _live_original_runtime.form_with_facts(1), _live_original_runtime.json(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.episode_bindings(1), self.workflow.facts(1), self.workflow.journal(2), self.workflow.pending_handles(1), self.workflow.release(2), self.workflow.source_credit_view(1), table:runtime_forms(2) |
| resource_discovery.py | 30 | hpc.discovery.run over ssh_argv in the project directory (memory cache; timeout 90 s; truncation) | import:root.a110.execution_guidance(1), import:root.a110.hpc_queue(module)(1) |
| task.py | 183 | decision loop; own: hpc launch report contract hook, grain hpc | _live_original_runtime.ActionFailure(1), _live_original_runtime.ContractInformationError(1), _live_original_runtime.Draft202012Validator(2), _live_original_runtime.EventTargetError(2), _live_original_runtime.ReportBoundaryError(1), _live_original_runtime.ReportRedelivery(2), _live_original_runtime.SourceEnd(2), _live_original_runtime.ValidationError(2), _live_original_runtime.WorkflowError(2), _live_original_runtime._decode_recorded_action_response(1), _live_original_runtime._json(5), _live_original_runtime._wait_target_feedback(2), _live_original_runtime.inspect(1), _live_original_runtime.json(8), _live_original_runtime.nullcontext(5), _live_original_runtime.observes_action_outcome(1), _live_original_runtime.schema_failure_diagnostic(1), _live_original_runtime.validate_form(1), import:root.a110.episode_source_failure(1), import:root.a110.library.hpc_handoff_report_contract(1), import:root.a110.providers(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.action_schema(1), self.workflow.completed_unit(3), self.workflow.completions(3), self.workflow.controller_value(2), self.workflow.decision_exchanges(3), self.workflow.delivery_resolution_inputs(1), self.workflow.execute(1), self.workflow.execution_binding(7), self.workflow.inprocess_replay(4), self.workflow.journal(7), self.workflow.last_observed_credit(1), self.workflow.next_return(1), self.workflow.pending_work(1), self.workflow.perform_selected_wait(1), self.workflow.receive_native_outcome(1), self.workflow.receive_outcome(1), self.workflow.resolve_pending_deliveries(1), self.workflow.resolver(1), self.workflow.run_id(2), self.workflow.selected(3), self.workflow.source_credit_view(1), self.workflow.store(7), self.workflow.validate_report(1), table:runtime_actions(8), table:runtime_episodes(1), table:runtime_model_calls(2) |
| task_decision.py | 289 | decision call/exchange protocol and provider completion with the hpc renderer | _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS(1), _live_original_runtime.DECISION_CONTEXT_VERSION(2), _live_original_runtime.DECISION_EXCHANGE_PROTOCOL(5), _live_original_runtime.Draft202012Validator(1), _live_original_runtime.Mapping(2), _live_original_runtime.ValidationError(5), _live_original_runtime.WorkflowError(14), _live_original_runtime._ASSIGNMENT_TRANSPORT(1), _live_original_runtime._action_generation_schema(2), _live_original_runtime._category_yield_parameters(1), _live_original_runtime._digest(1), _live_original_runtime._json(14), _live_original_runtime._object(3), _live_original_runtime._plain(2), _live_original_runtime._recorded_action_generation_schema(1), _live_original_runtime._recorded_assignment_transport(1), _live_original_runtime._references_in(1), _live_original_runtime.apply_state_frame(1), _live_original_runtime.child_option_information(1), _live_original_runtime.composition_lookup_schema(2), _live_original_runtime.instructional_model_context(4), _live_original_runtime.is_contract_information(1), _live_original_runtime.json(3), _live_original_runtime.lookup_attempts(1), _live_original_runtime.model_snapshot(2), _live_original_runtime.requested_contract_information(2), _live_original_runtime.schema_failure_diagnostic(2), _live_original_runtime.sqlite3(1), _live_original_runtime.state_frame(1), _live_original_runtime.yield_table(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow(passed)(3), self.workflow.contract_information_profile(1), self.workflow.contract_information_reply(1), self.workflow.controller_binding(1), self.workflow.decision_exchanges(4), self.workflow.decision_protocol(3), self.workflow.execute(1), self.workflow.freeze_contract_information(1), self.workflow.history_preview(1), self.workflow.journal(3), self.workflow.numerical_contracts(1), self.workflow.provider(3), self.workflow.receipts(4), self.workflow.run_id(1), self.workflow.services(1), self.workflow.specialist(1), self.workflow.store(2), self.workflow.uses_received_record_context(2), self.workflow.validate_contract_information(5), table:runtime_model_calls(8) |
| task_instructions.py | 14 | composition of goal text, knowledge, launch library, repair, wait and native event paragraphs | workflow.binding_context(1), workflow.knowledge(1), workflow.launch_instructions(1), workflow.native_event_information(1), workflow.permits_common_action(2), workflow.specialist(1) |
| task_state.py | 108 | episode source state, checkpoint/restore, record_effect | _live_original_runtime.ActionLeaf(1), _live_original_runtime.EFFECT_VERSION(1), _live_original_runtime.Episode(1), _live_original_runtime.Record(1), _live_original_runtime._json(2), _live_original_runtime._object(1), _live_original_runtime._plain(1), _live_original_runtime.interpretation_schema(1), _live_original_runtime.json(4), import:root.a110.episode_source_failure(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.archive(1), self.workflow.completions(4), self.workflow.controller_value(1), self.workflow.execution_binding(4), self.workflow.inprocess_replay(7), self.workflow.journal(5), self.workflow.progress_provider(2), self.workflow.recover_commissions(1), self.workflow.run_id(1), self.workflow.source_credit_view(1), self.workflow.store(2), table:runtime_actions(5), workflow.context(1), workflow.grains(1) |
| task_waiting.py | 9 | suspension_changed -> execution backend suspension | self.workflow.execution_backend(1), self.workflow.execution_handle(2) |
| to_child_execution_job_submission.py | 70 | authenticate_launch (exact planned launch, one reservation, not after close); LaunchPreparation.initial_decision_context hpc_execution_job | import:root.a110.communication(4), import:root.a110.hpc_ledger(2), import:root.a110.hpc_queue(module)(1), import:root.a110.method_loop.identities(1), import:root.a110.practical_execution_state(1) |
| to_child_execution_progress_assessment.py | 12 | monitor request = child _ASSIGNMENT validated unchanged | import:root.a110.communication(1), import:root.a110.domain(1) |
| to_child_execution_result_acquisition.py | 29 | assemble results child request envelope | _live_original_runtime.ContractInformationError(1), _live_original_runtime.Episode(2), _live_original_runtime.EpisodeGoal(2), _live_original_runtime.EpisodeRequest(1), _live_original_runtime.Record(1), _live_original_runtime._plain(3), _live_original_runtime.validate_saved_fact_form(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), workflow.context(2), workflow.grains(2), workflow.inprocess_completion_order(2), workflow.launch_instructions(1), workflow.receipts(2) |
| to_child_hpc_allocation_execution.py | 33 | allocation child assignment schema with owner_episode_id; must belong to this hpc parent and commission | import:root.a110.communication(1), import:root.a110.domain(1), import:root.a110.execution_contracts(1) |
| to_child_hpc_resource_prediction.py | 29 | prediction child assignment schema with owner_episode_id; same ownership checks | import:root.a110.communication(1), import:root.a110.domain(1), import:root.a110.execution_contracts(1) |
| to_parent.py | 41 | fact sources/facts (credit, model, accepted obligations, received result refs); resolve; validate_report | import:root.a110.communication(1), import:root.a110.episode_bindings(1) |
| waiting.py | 50 | activity_advice from last observation; hpc.monitor.wait through MonitorCronController (initial monitor, collect-now, schedule/wait/observe) | import:root.a110.hpc_monitoring(1), table:runtime_observations(1) |
| work_operations.py | 54 | tool catalog (11 hpc tools, 12 with shared memory) and execute dispatch with ledger action cache | import:root.a110.communication(1), import:root.a110.domain(1), import:root.a110.execution_contracts(12) |
| yield_estimator.py | 101 | yield_controller from commission yield_bindings with HPCContinuationEstimator; continuation_for_action evidence packet; practical_estimator | import:root.a110.hpc_monitoring(1), import:root.a110.library(1), import:root.a110.library.hpc_continuation(1), import:root.a110.numerical(2), table:runtime_actions(2), table:runtime_observations(1), yield:HPCContinuationEstimator(1), yield:YieldController(1), yield:YieldParameters(1) |

## Carried over

Carried over to the final ten-file form (19 November 2026). Every row of `runs/carry_over/functions/a110__biochemical_feasibility_evidence__hpc_work_planning.tsv` appears once.
Items that are blocked or unplaced are in `docs/axis_restructure_20261117/carry_over_blocked/a110__biochemical_feasibility_evidence__hpc_work_planning.md`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| allocation_handoff.py | AllocationHandoff | episode function | task.py (the tools hpc_handoff and the routing of the plan tools); library candidate (stays in task.py: not in episode_support/) |
| allocation_handoff.py | AllocationHandoff._attach_original_handoff | episode function | task.py hpc_handoff; library candidate (stays in task.py: not in episode_support/) |
| allocation_handoff.py | AllocationHandoff._work_on_original_allocation | episode function | task.py original_plan, original_target and the tools hpc_monitor, hpc_monitor_wait, hpc_allocation_order, hpc_results; library candidate (stays in task.py: not in episode_support/) |
| allocation_observations.py | AllocationObservations | episode function | task.py (observe_allocation and its helpers); library candidate (stays in task.py: not in episode_support/) |
| allocation_observations.py | AllocationObservations.targets | episode function | task.py observe_target, read_window, write_allocation_control (BLOCKED-ON-JOB-SERVICE: job_access; the old ExecutionTargetReader is not carried); library candidate (stays in task.py: not in episode_support/) |
| allocation_observations.py | AllocationObservations._target | episode function | task.py original_target (handoff_target is BLOCKED-ON-JOB-SERVICE); library candidate (stays in task.py: not in episode_support/) |
| allocation_observations.py | AllocationObservations._window | episode function | task.py window, window_value; library candidate (stays in task.py: not in episode_support/) |
| allocation_observations.py | AllocationObservations._allocation | episode function | task.py allocation_receipt; library candidate (stays in task.py: not in episode_support/) |
| allocation_observations.py | AllocationObservations._observe_original_allocation | episode function | task.py observe_allocation; library candidate (stays in task.py: not in episode_support/) |
| allocation_order.py | AllocationOrder | episode function | task.py hpc_allocation_order; library candidate (stays in task.py: not in episode_support/) |
| allocation_order.py | AllocationOrder._order_original_units | episode function | task.py hpc_allocation_order; library candidate (stays in task.py: not in episode_support/) |
| allocation_results.py | AllocationResults | episode function | task.py (collect_original_results, hpc_results); library candidate (stays in task.py: not in episode_support/) |
| allocation_results.py | AllocationResults._collected_unit_ids | episode function | task.py collected_unit_ids; library candidate (stays in task.py: not in episode_support/) |
| allocation_results.py | AllocationResults._uncollected_completed_unit_ids | episode function | task.py uncollected_completed_unit_ids; library candidate (stays in task.py: not in episode_support/) |
| allocation_results.py | AllocationResults._publish | episode function | task.py publish_result (ctx.store.artifact and ctx.store.put); library candidate (stays in task.py: not in episode_support/) |
| allocation_results.py | AllocationResults._collect_original_results | episode function | task.py collect_original_results, hpc_results; library candidate (stays in task.py: not in episode_support/) |
| binding_record.py | HPCBindingRecord | machinery | binding_record.py (binding identity and configuration record) |
| binding_record.py | HPCBindingRecord.as_record | machinery | the binding's own as_record() (README 3 table: binding_record.py) |
| closed_models.py | ClosedModels | machinery | closed-episode model validation over the old runtime_forms table and a read-only ledger connection |
| closed_models.py | ClosedModels.frozen_reference | machinery | EpisodeReturnRecords and runtime_forms re-validation; the check that a reported model ref names a ledger model is messages/final_to_parent.py resolve |
| configuration.py | HPCConfiguration | episode function | task.py settings (ctx.settings: resources, commissions, directory, shared_execution_memory) read by resources_of, commission_of, memory_enabled |
| configuration.py | HPCConfiguration.__init__ | machinery | constructor of the old configuration; its values are settings (task.py resources_of, commission_of, memory_enabled; yield_estimator.py cutoff, parameters) |
| credit.py | HPCEpisodeCredit | episode function | credit.py credit |
| credit.py | HPCEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | HPCEpisodeCredit.credit_view | episode function | credit.py credit (reads summary ledger_credit) and task.py ledger_view (the tools return the ledger credit view) |
| decision_inputs.py | HPCWorkDecisionInputs | episode function | task.py decide |
| decision_inputs.py | HPCWorkDecisionInputs.decision_inputs | episode function | task.py decide (launch library, tool knowledge, tool estimates, time accounting, action history from messages/internal_summary.py); pending_work, waiting_support, native expectations and the resource estimator are not carried (see the blocked file) |
| decision_state.py | HPCWorkDecisionState | machinery | generic old decision state (working_state, runtime_actions, receipts, journal) |
| decision_state.py | HPCWorkDecisionState.decision_state | machinery | generic old decision state; what is HPC-specific is messages/internal_summary.py and task.py decide |
| episode.py | HPCEpisode | episode function | episode.py HPCWorkPlanning |
| episode.py | HPCEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | HPCEpisode.allowed_children | machinery | binding lookup of the allowed children (README 3b C2): CHILD_SLOTS |
| episode.py | HPCEpisode.permitted_common_actions | machinery | common action list (tool, child, wait, redeliver_report): wait and redeliver_report are not carried; tool and child are task.py offered |
| episode.py | HPCEpisode.prepare_child_request | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | HPCEpisode.receive_child_progress_for_role | machinery | receive_child_progress (README 3b R5) |
| episode.py | HPCEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| episode.py | HPCEpisode.execution_child_report_receiver | machinery | receiver selection for the results child (README 3b C1, R1): the system admits the result; messages/read_from_child.py read_from_child (results) |
| episode.py | HPCEpisode.child_request_assembler | machinery | binding lookup of the results request assembler (README 3b C1); the request is messages/msg_to_child.py msg_to_child (results) |
| episode.py | create_execution_bindings | machinery | home factory building the private child bindings (the child episode folders are the bindings now) |
| forecast_observations.py | ForecastObservations | episode function | task.py (freeze_forecast, measure, update_conditional_forecast); library candidate (stays in task.py: not in episode_support/) |
| forecast_observations.py | ForecastObservations._freeze | episode function | task.py freeze_forecast; library candidate (stays in task.py: not in episode_support/) |
| forecast_observations.py | ForecastObservations._last_forecast | episode function | task.py last_forecast; library candidate (stays in task.py: not in episode_support/) |
| forecast_observations.py | ForecastObservations._measure | episode function | task.py measure; library candidate (stays in task.py: not in episode_support/) |
| forecast_observations.py | ForecastObservations._update_conditional_forecast | episode function | task.py update_conditional_forecast; library candidate (stays in task.py: not in episode_support/) |
| from_child_execution_job_submission.py | LaunchReceiptCustody | machinery | receipt custody of the launch handoff across report repair (runtime_actions, runtime_episodes) |
| from_child_execution_job_submission.py | LaunchReceiptCustody.original_launch_handoff | machinery | recovery of the plan handoff from the old committed outcome tables; the launch result names its handoff records in custody (messages/read_from_child.py launch) |
| from_child_execution_progress_assessment.py | receive_progress | machinery | progress provider receipt of the monitor form (README 3b R5); the monitor result is read in messages/read_from_child.py monitor |
| from_child_execution_result_acquisition.py | receive_report | machinery | recorded admissions, specialist progress receivers, provider form, receipts, tool attributions (README 3b R1, R3, R5); the report is read in messages/read_from_child.py read_from_child (results) |
| from_child_hpc_allocation_execution.py | receive_allocation_report | machinery | receipts, progress provider, timing receipts, tool attributions (README 3b R1, R3); the report is read in messages/read_from_child.py hpc_execution |
| from_child_hpc_resource_prediction.py | receive_prediction_report | machinery | receipts, progress provider, timing receipts, tool attributions (README 3b R1, R3); the report is read in messages/read_from_child.py hpc_prediction |
| from_parent.py | HPCAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | HPCAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | HPCAssignment.commission_identity | episode function | messages/read_from_parent.py read_from_parent (commission_identity of the parent input) |
| from_parent.py | HPCAssignment._commission | episode function | task.py commission_of (a configured commission is validated as the old constructor did; the host-issued commission_source_ref raises NotImplementedError hpc_commission_sources_not_placed:A110, the old head module has no copy in episode_support/); library candidate (stays in task.py: not in episode_support/) |
| from_parent.py | HPCAssignment.prepare_assignment | machinery | commission preparation and check at the parent (received ref, yield binding): a wrong commission fails; the schema is the form admission; the tool request is task.py resolve_tool_request |
| from_parent.py | HPCAssignment._tool_request | episode function | task.py resolve_tool_request (raises: the A110 head tool library is not reachable) |
| goal.py | HPCGoal | episode function | goal.py GOAL, UNIT, RESULT and task.py INSTRUCTIONS |
| goal.py | HPCGoal.instructions | episode function | task.py INSTRUCTIONS (the redeliver_report sentence is not carried) and goal.py GOAL |
| initial_information.py | initial_information | episode function | not placed: it called resource_information(catalog.readers(binding_path, context)) of execution_initial_information.presentation, which is not in episode_support/ (reported in unplaced_old_functions); decide shows the configured resource (hpc_resource) and the tool estimates |
| internal_summary.py | HPCSummary | episode function | messages/internal_summary.py and task.py ledger_view |
| internal_summary.py | HPCSummary.decision_context | episode function | messages/internal_summary.py internal_summary, task.py ledger_view and decide (hpc_launch_report_form, hpc_report_form and hpc_activity_decision are not carried) |
| measured_history.py | MeasuredHistory | episode function | task.py (measured_history, shared_history, export_closed, hpc_history_refresh); library candidate (stays in task.py: not in episode_support/) |
| measured_history.py | MeasuredHistory._history | episode function | task.py measured_history; library candidate (stays in task.py: not in episode_support/) |
| measured_history.py | MeasuredHistory._shared_history | episode function | task.py shared_history (the [:2000] count limit is not carried); library candidate (stays in task.py: not in episode_support/) |
| measured_history.py | MeasuredHistory.export_closed | episode function | task.py export_closed (estimate_record is BLOCKED-ON-JOB-SERVICE: estimate_table); library candidate (stays in task.py: not in episode_support/) |
| measured_history.py | MeasuredHistory._refresh_measured_history | episode function | task.py hpc_history_refresh; library candidate (stays in task.py: not in episode_support/) |
| portfolio_candidates.py | PortfolioCandidates | episode function | task.py hpc_candidate_propose; library candidate (stays in task.py: not in episode_support/) |
| portfolio_candidates.py | PortfolioCandidates._propose_portfolio | episode function | task.py hpc_candidate_propose; library candidate (stays in task.py: not in episode_support/) |
| portfolio_comparison.py | PortfolioComparison | episode function | task.py (candidates_of, candidate_features, comparisons, candidate_of, hpc_compare); library candidate (stays in task.py: not in episode_support/) |
| portfolio_comparison.py | PortfolioComparison._candidates | episode function | task.py candidates_of; library candidate (stays in task.py: not in episode_support/) |
| portfolio_comparison.py | PortfolioComparison._features | episode function | task.py candidate_features; library candidate (stays in task.py: not in episode_support/) |
| portfolio_comparison.py | PortfolioComparison._comparisons | episode function | task.py comparisons; library candidate (stays in task.py: not in episode_support/) |
| portfolio_comparison.py | PortfolioComparison._candidate | episode function | task.py candidate_of; library candidate (stays in task.py: not in episode_support/) |
| portfolio_comparison.py | PortfolioComparison._compare_portfolios | episode function | task.py hpc_compare; library candidate (stays in task.py: not in episode_support/) |
| portfolio_planning.py | PortfolioPlanning | episode function | task.py hpc_plan; library candidate (stays in task.py: not in episode_support/) |
| portfolio_planning.py | PortfolioPlanning._freeze_portfolio_plan | episode function | task.py hpc_plan; library candidate (stays in task.py: not in episode_support/) |
| portfolio_state.py | PortfolioState | episode function | task.py (open_ledger, hpc_initialize, current_model); library candidate (stays in task.py: not in episode_support/) |
| portfolio_state.py | PortfolioState.state | episode function | task.py hpc_initialize (creates the ledger with the commission, writes owner and tool request) and open_ledger; library candidate (stays in task.py: not in episode_support/) |
| portfolio_state.py | PortfolioState.initialize | episode function | task.py hpc_initialize (reference model, initial model from shared history); library candidate (stays in task.py: not in episode_support/) |
| portfolio_state.py | PortfolioState._current_model | episode function | task.py current_model; library candidate (stays in task.py: not in episode_support/) |
| queue_observations.py | QueueObservations | episode function | task.py (observe_queue, queue_snapshot, hpc_queue_observe); library candidate (stays in task.py: not in episode_support/) |
| queue_observations.py | QueueObservations._observe_queue | episode function | task.py observe_queue (observe_queue_value is BLOCKED-ON-JOB-SERVICE: job_access); library candidate (stays in task.py: not in episode_support/) |
| queue_observations.py | QueueObservations._queue | episode function | task.py queue_snapshot; library candidate (stays in task.py: not in episode_support/) |
| queue_observations.py | QueueObservations._observe_resource_queue | episode function | task.py hpc_queue_observe; library candidate (stays in task.py: not in episode_support/) |
| received_evidence.py | ReceivedEvidence | episode function | task.py (read_evidence, resolve_result_source, hpc_read); library candidate (stays in task.py: not in episode_support/) |
| received_evidence.py | ReceivedEvidence._known | machinery | the received-reference set (record_selection, received_record_refs): custody, ctx.store.holds |
| received_evidence.py | ReceivedEvidence.resolve_received_reference | episode function | task.py resolve_result_source; library candidate (stays in task.py: not in episode_support/) |
| received_evidence.py | ReceivedEvidence.read_evidence | episode function | task.py read_evidence; library candidate (stays in task.py: not in episode_support/) |
| received_evidence.py | ReceivedEvidence._read_retained_evidence | episode function | task.py hpc_read; library candidate (stays in task.py: not in episode_support/) |
| received_execution_information.py | received_execution_information | episode function | not placed: it selected this path's configured/received result readers of the old catalog (catalog.configured, catalog.received), which is not in episode_support/ (reported in unplaced_old_functions) |
| report_delivery.py | HPCWorkReportDelivery | machinery | report_form machinery (saved runtime_forms, form_with_facts, release) |
| report_delivery.py | HPCWorkReportDelivery.finish | machinery | report finish: saved runtime_forms, release, pending_handles; the facts are messages/final_to_parent.py facts |
| resource_discovery.py | ResourceDiscovery | episode function | task.py hpc_discovery_run; library candidate (stays in task.py: not in episode_support/) |
| resource_discovery.py | ResourceDiscovery._discover_resource | episode function | task.py hpc_discovery_run (run_command is BLOCKED-ON-JOB-SERVICE: job_access; the 90 s timeout and the output truncation are not carried); library candidate (stays in task.py: not in episode_support/) |
| task.py | HPCWorkTask | episode function | task.py decide, action and the TOOLS |
| task.py | HPCWorkTask.next | machinery | the old decision loop (next, journal replay, completions); decide and action replace it |
| task.py | HPCWorkTask.apply_response | episode function | task.py action (the validation and rejection of the model answer); library candidate (stays in task.py: not in episode_support/) |
| task.py | HPCWorkTask.execute | machinery | old execute branches (tool, reason, child, wait, redeliver_report): ToolCall and ChildCall |
| task_decision.py | HPCWorkTaskDecision | episode function | task.py decide (the model request) |
| task_decision.py | HPCWorkTaskDecision.call | episode function | task.py decide (instructions, context and output schema of the model request) |
| task_decision.py | HPCWorkTaskDecision.instructions | episode function | task.py INSTRUCTIONS and decide |
| task_decision.py | HPCWorkTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | HPCWorkTaskDecision.interpretation_context | machinery | decision exchange context (README 3a) |
| task_decision.py | HPCWorkTaskDecision.exchange_schema | machinery | decision exchange (README 3a) |
| task_decision.py | HPCWorkTaskDecision.exchange_response | machinery | decision exchange (README 3a) |
| task_decision.py | HPCWorkTaskDecision.validate_contract_exchange_request | machinery | saved-request check (README 3a) |
| task_decision.py | HPCWorkTaskDecision.validate_contract_exchange_history | machinery | saved-request check (README 3a) |
| task_decision.py | HPCWorkTaskDecision.exchange_decision | machinery | decision exchange loop (README 3a) |
| task_decision.py | HPCWorkTaskDecision.complete_decision | episode function | task.py decide (ModelRequest) and action |
| task_instructions.py | instructions | episode function | task.py decide (INSTRUCTIONS plus the tool-knowledge and launch-library texts; the pending-child and wait texts are not carried) |
| task_state.py | HPCWorkTaskState | machinery | task state, checkpoint and restore |
| task_state.py | HPCWorkTaskState.__init__ | machinery | task state, checkpoint and restore |
| task_state.py | HPCWorkTaskState.bind_execution_context | machinery | execution binding (README 3e) |
| task_state.py | HPCWorkTaskState.record_execution_failure | machinery | record_execution_failure (README 3c: the tool returns the failure) |
| task_state.py | HPCWorkTaskState.restore_checkpoint | machinery | restore_checkpoint |
| task_state.py | HPCWorkTaskState.restore | machinery | restore |
| task_state.py | HPCWorkTaskState.record_effect | machinery | record_effect |
| task_state.py | HPCWorkTaskState.checkpoint | machinery | checkpoint |
| task_waiting.py | HPCWorkSuspension | machinery | wait/suspension machinery |
| task_waiting.py | HPCWorkSuspension.suspension_changed | machinery | wait/suspension machinery |
| to_child_execution_job_submission.py | authenticate_launch | episode function | task.py action (a plan is launched once and never after its allocation closed); the receipt reservation in the ledger is the old runner bookkeeping and is not carried |
| to_child_execution_job_submission.py | LaunchPreparation | episode function | messages/msg_to_child.py launch |
| to_child_execution_job_submission.py | LaunchPreparation.initial_decision_context | episode function | messages/msg_to_child.py launch (hpc_execution_job in the message) and task.py hpc_plan (writes the supplied input file) |
| to_child_execution_progress_assessment.py | prepare_request | episode function | messages/msg_to_child.py monitor |
| to_child_execution_result_acquisition.py | assemble_request | episode function | messages/msg_to_child.py msg_to_child (results): the assignment as selected, the one handoff in custody, resource_kind and acquired_record_unit; the old request envelope (goal, scope, initial_report, report_contract_declaration, inprocess order, knowledge_inheritance) is old-runner machinery |
| to_child_hpc_allocation_execution.py | assignment_schema | episode function | messages/msg_to_child.py hpc_execution (the assignment the child admits) |
| to_child_hpc_allocation_execution.py | commission_identity | episode function | messages/read_from_parent.py read_from_parent (commission_identity) |
| to_child_hpc_allocation_execution.py | prepare_request | episode function | messages/msg_to_child.py hpc_execution (the ownership check against the parent is not carried: a wrong commission fails) |
| to_child_hpc_resource_prediction.py | assignment_schema | episode function | messages/msg_to_child.py hpc_prediction (the assignment the child admits) |
| to_child_hpc_resource_prediction.py | commission_identity | episode function | messages/read_from_parent.py read_from_parent (commission_identity) |
| to_child_hpc_resource_prediction.py | prepare_request | episode function | messages/msg_to_child.py hpc_prediction (ledger_refs is BLOCKED-ON-JOB-SERVICE; the ownership check is not carried) |
| to_parent.py | HPCReport | episode function | messages/final_to_parent.py |
| to_parent.py | HPCReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs, plus credit and finding) |
| to_parent.py | HPCReport.facts | episode function | messages/final_to_parent.py facts and final_to_parent |
| to_parent.py | HPCReport.resolve | episode function | messages/final_to_parent.py resolve |
| to_parent.py | HPCReport.validate_report | episode function | messages/final_to_parent.py validate_report (its validate_form call raises NotImplementedError validate_form_not_built:A110) |
| waiting.py | HPCActivityAdvice | episode function | task.py hpc_monitor_wait (MonitorCronController is not placed for A110: monitor_attach, monitor_reserve and monitor_wait raise); library candidate (stays in task.py: not in episode_support/) |
| waiting.py | HPCActivityAdvice.activity_advice | machinery | activity advice read from the old runtime_observations estimator diagnostics (the estimator is deleted, README 3d) |
| waiting.py | HPCActivityAdvice._wait_for_original_observation | episode function | task.py hpc_monitor_wait (MonitorCronController is not placed for A110: monitor_attach, monitor_reserve and monitor_wait raise); library candidate (stays in task.py: not in episode_support/) |
| work_operations.py | HPCWorkOperations | episode function | task.py TOOL_CATALOG, TOOLS; library candidate (stays in task.py: not in episode_support/) |
| work_operations.py | HPCWorkOperations.catalog | episode function | task.py TOOL_CATALOG and CHILD_CATALOG (offered); library candidate (stays in task.py: not in episode_support/) |
| work_operations.py | HPCWorkOperations.execute | episode function | task.py TOOLS (each tool opens the ledger and dispatches; ledger caching by operation key is the ledger and ctx.operation_key); library candidate (stays in task.py: not in episode_support/) |
| yield_estimator.py | HPCEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (AccumulationYieldController from settings cutoff and parameters) |
| yield_estimator.py | HPCEpisodeYield.continuation_for_action | machinery | continuation packet of the deleted HPCContinuationEstimator (README 3d, 7b) |
| yield_estimator.py | HPCEpisodeYield.practical_estimator | machinery | HPCContinuationEstimator construction (README 3d, 7b) |
