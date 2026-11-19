# a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/<file>`
(only files directly in this folder; it has no `grading/` or `scoring/` folder and no child episodes).
Old binding class: `ExecutionEpisode` (`binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'`,
`commissioning_parent = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'`, `roles = ('results',)`,
`entry_roles = ()`), decision source `ResultsTask`, prompt renderer `present_results_context`, contract version
`execution_episode_v1`.

## What it is for (its goal, in its own words)

`instructions.py` (and `replaces_default_instructions = True`, so this replaces the generic prompt):

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the
> current resource filesystem: the exact attempt observation does not establish that current file bytes were
> produced by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets
> the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition
> establishes this endpoint.

It is the Results half of an execution: it never launches work; it collects the bytes of a job that a launch
sibling already handed off, and returns typed records for the scientific parent to interpret.

## Task and instructions

- Instructions as above. `task_instructions.py` composes: job-episode instructions or generic `INSTRUCTIONS`,
  replaced by the binding text; then reasoning-commit requirement (if `reason` permitted — it is not here), tool
  knowledge, launch instruction library, pending-child redelivery text, wait text (only API service targets
  permit `wait`), native event targets text, decision-exchange history text.
- Decision prompt: `present_results_context` picks a text TASK renderer by context kind (HPC, partner-presence
  published evidence, API launch, RNA comparison results, RNA structure results, selected execution, monitor,
  RNA comparison receiver) else JSON.

## What it reads from its parent's assignment

`from_parent.py`: `RESULTS_SCHEMA` (library `execution_result_contract`) with `handoff_ref`, `selector`, and
`constraints`; selector branches for `local_file_source_selector_v1`, per-tool result selector conditions,
`expression_nmf_result_selector_v1`, RNA structure result selectors and RNA comparison selector.
`prepare_assignment`:
1. restores a previously successfully returned original Results commission (`saved_commission.py`: receipt
   manifest + admission index + child path `('results', 'child_<index>')` + same assignment and scope);
2. otherwise reads the target: retained NMF / utility / masking target, else the handoff target
   (`job_progress_provider.targets.read_target(handoff_ref, scope)`);
3. validates the selector against the target and each tool's selected inputs (local file admission, masking,
   utility, RNA comparison / structure, standard BLAST database, BLAST database).
`required_return_sources`: when the parent path ends in `partner_presence_evidence` and the services report that an
annotation task is required, the parent must request `execution_result_refs`.
`initial_references`: the handoff ref plus validated input refs (NMF saved sheet artifact, RNA/BLAST inputs).

## Children

None: `child_roles` and `allowed_children` return `()`. Permitted actions: `('tool',)`, or `('tool', 'wait')` for an
API target with `api_service_assignment_v1`.

## Decision state and what it shows the model

`internal_summary.py` `decision_context`:
- `execution_assignment` (the assignment), `execution_progress` (= current `facts`);
- `execution_target` (local file target or handoff target) and `execution_target_description`
  (status/collect operations and provenance for local files; NMF description; or the handoff target description
  with selector);
- `selected_execution_task` when the services supply the scientific parent task: scientific question, selected
  tool info, per-resource requests (resource id/kind, endpoint, constraints, the selected native job — NMF/HMMER
  shown through their scientific job views — and resource information), constraints, selector, result
  description.
`results_decision_snapshot` is the old generic snapshot (goal, scope, working state, visible refs, credit, time
accounting, pending work, last outcome, feedback, report deliveries, controller, tools, tool knowledge, job episode
options, report facts, requested form, current report update) followed by the binding's decision_context.

## Tools it offers

`work_operations.py` dispatches by target: NMF result operations; BLAST masking / utility result operations; RNA
comparison / structure result operations; standard BLAST database and BLAST database result operations; API result
operations (`api_execution.catalog`); HMMER preparation / HMMER, BLAST, Infernal / Infernal preparation result
operations; otherwise the native catalog (`result_records.py`): `execution.results.status` (observe the exact
handed-off attempt once), `execution.results.collect` (observe and acquire first windows of requested paths, at
most `min(log_window_bytes, 1 MiB)` each), `execution.results.read` (one window within the requested path and
interval, `limit` at most 1 MiB). Argument / selector errors return an `invalid` outcome
(`arguments_or_reference`). A new acquisition is refused once a completion proof exists
(`execution_results_assignment_already_completed`). `resource_information.py` additionally declares the launch and
results operation contracts per bound resource with commission routes (used by the parent for tool contracts).

## How its credit is counted

Operational credit (`credit.py`), never scientific:
- generic native results: `credit = acquired_record_unit * fraction`, where fraction is the mean over requested
  paths of newly covered selector byte positions (union of windows) divided by the requested interval, minus bytes
  already in initially-known results ("Credit saved byte positions once, regardless of read boundaries");
  `handoff_unit * handoff_count` with handoff_count fixed at 0 here;
- local file sources: `acquired_record_unit * number of newly acquired files`;
- each native/API adapter supplies its own `credit_view` when it applies;
- after the episode yields, `closed_credit.py` returns only the frozen closing view (digest-checked), never a new
  projection.

## Continuation (yield estimator, settings)

`yield_estimator.py` (requires `require_private_yield=True`, else raises):
- unbounded native selector (a requested path with no length): `results_yield_profiles['native_unbounded_local'|
  'native_unbounded_hpc']` = `{cutoff, parameters}`, plain controller;
- finite native selector: `task_yield_profiles['results:native_finite_<kind>']` with a finite-result estimator:
  verified completion -> completion estimate; zero remaining uncredited selector credit -> exact zero; otherwise a
  bounded-credit yield whose maximum is `acquired_record_unit * (1 - fraction already known)`. (New design:
  completion-with-target / bounded-quality estimator; the maximum here is the remaining credit target, not a
  clamp on credit.)
- API / typed selectors: `task_yield_profiles['results:api_<service>[_<selector version>]']` or
  `['results:typed_<kind>_<selector version>']` with a completion-proof estimator (`PracticalYieldEstimator`
  verifying `verify_completion`). Missing profile raises.
Old settings name a `cutoff` per profile; that is the old controller's stop threshold and has to be re-expressed
through the three `yield_control/` estimators.

## What it reports to its parent

`to_parent.py` `facts`: for the applying adapter its facts with empty arrays for every other native family; for
API targets `api_execution.facts` plus BLAST grader rows when the launch requested the graded return
(`_blast_grader_rows`: exactly one grading entry per result, matching query digest/length, database); generic:
`execution_handoff_refs`, `execution_result_refs` (results with windows), `execution_file_source_refs`,
`execution_file_capture_outcomes`, `execution_result_origin` (NATIVE_RESULT_ORIGIN qualification),
`execution_completed`, optional `bvbrc_appservice_support_refs`; plus the closed credit snapshot.
`validate_report`: each typed-return adapter validates; references resolve; every `x-source` field must equal the
recorded facts (`execution_report_disagrees_with_recorded_facts`). Finish: saved form, or `form_with_facts`.

## Differences from similar episodes

- Compared with its prediction cousin (`hpc_work_planning/hpc_resource_prediction`): no ledger; operational
  credit counts acquired selector bytes, not model quality; yield profiles are keyed by result type rather than a
  commission's `yield_bindings`; permits `wait` for API service targets.
- It carries a very large per-tool dispatch (BLAST, masking, utility, databases, HMMER, Infernal, RNA structure,
  NMF, API) inherited from the shared execution Results design; for A107 the HPC route is the native
  status/collect/read path. `task_decision.py` differs from the literature episodes only by `binding.capture('results')`,
  the added `requested_action_history` for HPC contexts, and a guarded renderer lookup.
- The old instruction text says "bounded status or requested file/page reads": this is a description of selector
  windows, not a stopping budget.

## Files

| old file | lines | this episode's own intent | old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `action_outcome.py` | 5 | `_outcome(result, references, code)`: the episode's ordinary completed/invalid outcome record (invalid carries `arguments_or_reference` feedback) | none |
| `binding_record.py` | 9 | `as_record()`: binding id `.../execution_result_acquisition`, version `execution_episode_v1`, configuration (resources, initial_information, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield, results/task yield profiles) | none |
| `binding_roles.py` | 6 | VERSION `execution_episode_v1`; ROLES (launch, launch_api, launch_local, launch_hpc, results); resource KINDS map (local, pbs_ssh->hpc, hmmer_api/api->api); ROLE_KINDS | none |
| `closed_credit.py` | 122 | closed operational credit: once the episode yields, its credit view is frozen into its closing facts (`execution_closed_operational_credit_v1`) with digests of context, binding, completion, archive, observation history and receipt prefix; later reads return only that frozen view ("later delivery never reprices it") | `import:communication`, `import:episode_receipts`, `import:episode_return_records` (3), `table:runtime_episodes` (2), `table:runtime_forms` (3), `table:runtime_observations`, `table:runtime_receipt_inheritance` (2), `table:runtime_record_receipts` (2) |
| `completion.py` | 184 | completion proofs: generic native results complete when every requested selector byte window is covered by a completed returncode-0 attempt; per-adapter completion (RNA structure, NMF, Infernal, BLAST masking/utility/database/standard database, HMMER, API); `verify_completion` reuses a recorded endpoint verdict from history (exactly one matching observation with zero expected next gain) before recomputing | `import:communication`, `import:episode_return_records`, `import:method_loop.identities`, `import:numerical`, `import:practical_yield`, `table:runtime_actions` (2), `table:runtime_observations`, `yield:ESTIMATOR_VERSION` (2), `yield:NumericBand` (2) |
| `configuration.py` | 120 | constructor: explicit resources (kinds local/pbs_ssh/api), initial information per resource, positive finite `handoff_unit` and `acquired_record_unit`, `log_window_bytes`, `log_roles`, `require_private_yield`, `results_yield_profiles` (only `native_unbounded_local`/`native_unbounded_hpc`) and `task_yield_profiles` each `{cutoff, parameters}`; validates per-resource native bindings (NMF/RNA structure/Infernal local-only); builds TerminalExecutionBehavior per non-API resource, APIServiceExecution, ExecutionProgressProvider, LocalFileSourceResults and per-tool native result readers | `import:communication`, `import:numerical`, `yield:YieldController` (3), `yield:YieldParameters` (3) |
| `credit.py` | 81 | operational credit: native selector byte-coverage fraction newly acquired (union of byte positions, minus those already in initially-known results), `credit = handoff_unit*0 + acquired_record_unit*fraction`; local file sources count unique acquired files; per-adapter credit views; closed view wins once closed | `import:communication` |
| `credit_records.py` | 3 | `_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'` | none |
| `episode.py` | 109 | `ExecutionEpisode` composition: binding_path `partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`, commissioning_parent `.../hpc_allocation_execution`, roles `('results',)`, no entry roles, `replaces_default_instructions = True`, prompt renderer `present_results_context`, received execution/API/initial information require authority; attaches shared result-reader helpers as methods; mixes in A107BlastExecution | `import:communication` |
| `from_parent.py` | 122 | assignment schema = RESULTS_SCHEMA plus selector branches (local file source, result selector conditions, NMF, RNA structure/comparison); `prepare_assignment` restores a recorded original Results commission or reads the handoff target and validates the selector and per-tool selected inputs; `required_return_sources` demands `execution_result_refs` when the parent is `partner_presence_evidence` and an annotation task is required; `initial_references` (handoff ref plus validated inputs) | `import:communication` |
| `goal.py` | 19 | no children; permitted actions `tool` (plus `wait` for `api_service_assignment_v1` API targets) | `import:communication` |
| `initial_information.py` | 12 | local file sources get only their local resource capability; otherwise resource information and received API information from this binding's declared readers | none |
| `input_versions.py` | 21 | validates masking/utility/NMF job inputs and execution input versions | none |
| `instructions.py` | 7 | goal text: acquire the original selected execution results through the original handoff; bounded status/file/page reads chosen from preceding outcomes; preserve partial bytes and native scores; current filesystem bytes are not proven to come from the attempt; read windows are not an atomic snapshot; the scientific parent interprets; work, resource and selector fixed; only actual complete acquisition establishes the endpoint | none |
| `internal_summary.py` | 97 | `decision_context`: execution_assignment, execution_progress (= facts), execution_target and its description (local file / NMF / handoff target description), `selected_execution_task` (parent scientific question, selected tool info, requests, constraints, selector); plus `results_decision_snapshot` = the old generic decision snapshot | `binding_context`, `import:communication`, `import:runtime`, `runtime.FACT_MEANINGS`, `runtime.FACT_SOURCES`, `runtime.json` (2), `runtime.Mapping` (3), `runtime._plain` (2), `runtime._references_in`, `self.workflow.binding_context`, `self.workflow.catalog`, `self.workflow.controller_binding`, `self.workflow.delivery_status`, `self.workflow.extra_report_sources`, `self.workflow.job_episode_options`, `self.workflow.journal` (3), `self.workflow.knowledge`, `self.workflow.local_outcome_preview`, `self.workflow.pending_work`, `self.workflow.run_id`, `self.workflow.source_credit_binding`, `self.workflow.source_credit_view`, `self.workflow.specialist`, `self.workflow.store` (3), `self.workflow.tools`, `self.workflow.working_state`, `table:runtime_actions` (2) |
| `native_file_acquisition.py` | 63 | `execution.results.status/collect/read`: immutable intent/observation/window/receipt files under the result directory; collect reads first windows up to min(log_window_bytes, 1 MiB); refuses a new acquisition once a completion proof exists; publishes result as a Store source | `import:communication`, `table:runtime_actions` |
| `native_target_state.py` | 8 | `state()` raises `practical_resource_role_required` (Results has no practical state) | none |
| `presentation.py` | 73 | `present_results_context`: chooses a text TASK renderer (HPC, partner-presence published evidence, API launch, RNA comparison/structure, selected execution, monitor, RNA receiver) from the reconstructed state frame, else JSON | `import:decision_context` |
| `receipt_selection.py` | 35 | `_received`: from known record refs collects own result bodies (same assignment) and returnable practical/API handoffs whose target matches this context | `import:communication` |
| `received_api_reports.py` | 4 | selects API reports declared for this binding path | none |
| `received_execution_information.py` | 4 | selects execution result readers declared for this binding path | none |
| `received_launch_records.py` | 3 | `LAUNCH_VERSION = 'execution_launch_assignment_v1'` | none |
| `received_launch_requests.py` | 69 | launch request schemas per resource (API or practical assignment, requested_job alternatives per native tool), `_launch` validation incl. BLAST graded request, constraint validation | none |
| `report_delivery.py` | 23 | `finish`: rootless returns credit+pending handles; otherwise saved form or `form_with_facts` from facts and interpretations | `binding_context`, `import:runtime`, `runtime.form_with_facts`, `runtime._json` (2), `runtime.json`, `runtime.Record` (2), `self.workflow.binding_context`, `self.workflow.episode_bindings`, `self.workflow.facts`, `self.workflow.journal` (2), `self.workflow.pending_handles`, `self.workflow.release` (2), `self.workflow.source_credit_view`, `table:runtime_forms` (2) |
| `resource_information.py` | 68 | `resource_tool_contracts`: launch and results operation contracts per bound resource (API services, homology API, NMF, RNA, Infernal, native and preparation operations) with commission routes | none |
| `result_publication.py` | 13 | publishes a result body as source `episode.execution_result` | none |
| `result_records.py` | 14 | RESULTS_VERSION, RESULT_PROVIDER, NATIVE_RESULT_ORIGIN qualification (current filesystem, unverified attempt version, no atomic snapshot), native result operation catalog (status, collect, read) | none |
| `result_state.py` | 26 | `initialize`: validates selector/target, requires the BLAST grader typed return when the launch requested it, prepares API or result directory | `import:communication` |
| `saved_commission.py` | 46 | restores a successfully returned original Results commission from receipts/admission records (same assignment and scope) | `import:communication`, `import:episode_receipts`, `import:episode_return_records`, `table:runtime_actions`, `table:runtime_episodes`, `table:runtime_report_attempts` |
| `schema_fields.py` | 6 | TEXT, OFFSET, LIMIT, FILE_LIMIT (1 MiB per read window) | none |
| `selector_records.py` | 7 | NATIVE_SELECTOR_SCHEMA (paths/path/offset/limit) | none |
| `target_custody.py` | 68 | target/context consistency (launch BLAST graded query digest, role kind assignment equality, results target equality); `_blast_target_requirement` rebuilds the original BLAST grader return requirement from its launch request | `import:communication`, `table:runtime_episodes` (2) |
| `task.py` | 228 | `ResultsTask` decision source: old generic next/apply_response/execute loop (replay, completions, model call, report update, reason/wait/tool execute, credit save) | `binding_context` (2), `import:episode_source_failure`, `import:providers`, `import:runtime`, `runtime.AcquisitionError` (2), `runtime.ActionFailure`, `runtime.ContractError`, `runtime.ContractInformationError`, `runtime._decode_recorded_action_response`, `runtime.Draft202012Validator` (3), `runtime.EventTargetError` (2), `runtime.inspect`, `runtime._json` (5), `runtime.json` (8), `runtime.Mapping` (3), `runtime.nullcontext` (5), `runtime.observes_action_outcome`, `runtime.ReportBoundaryError`, `runtime.ReportRedelivery` (2), `runtime.schema_failure_diagnostic`, `runtime.SourceEnd` (2), `runtime.sqlite3` (2), `runtime.subprocess` (2), `runtime.validate_form`, `runtime.ValidationError` (3), `runtime._wait_target_feedback` (2), `runtime.WorkflowError` (2), `self.workflow.action_schema`, `self.workflow.automatic_score_updates`, `self.workflow.binding_context` (2), `self.workflow.completed_unit` (3), `self.workflow.completions` (3), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.delivery_resolution_inputs`, `self.workflow.execute`, `self.workflow.execution_binding` (7), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (7), `self.workflow.last_observed_credit`, `self.workflow.next_return`, `self.workflow.pending_work`, `self.workflow.perform_selected_wait`, `self.workflow.permits_common_action`, `self.workflow.reasoning_action_schema`, `self.workflow.receive_native_outcome`, `self.workflow.receive_outcome`, `self.workflow.resolve_pending_deliveries`, `self.workflow.resolver`, `self.workflow.retain_shared_grading_results`, `self.workflow.run_id` (3), `self.workflow.selected` (3), `self.workflow.source_credit_view`, `self.workflow.specialist` (2), `self.workflow.store` (9), `self.workflow.validate_report`, `table:runtime_actions` (8), `table:runtime_episodes`, `table:runtime_model_calls` (2) |
| `task_decision.py` | 360 | old generic model call / decision exchange protocol (same as published_evidence_assessment's except `binding.capture('results')` and adds `requested_action_history` for HPC contexts) | `binding_context`, `import:episode_work_report` (2), `import:providers`, `import:runtime`, `runtime._action_generation_schema` (2), `runtime.apply_state_frame`, `runtime._ASSIGNMENT_TRANSPORT`, `runtime._category_yield_parameters`, `runtime.child_option_information` (2), `runtime.composition_lookup_schema` (2), `runtime.CONTRACT_INFORMATION_OPERATIONS`, `runtime.DECISION_CONTEXT_VERSION` (2), `runtime.DECISION_EXCHANGE_PROTOCOL` (5), `runtime._digest`, `runtime.Draft202012Validator`, `runtime.infernal_receiver_context` (2), `runtime.instructional_model_context` (4), `runtime.is_contract_information`, `runtime._json` (14), `runtime.json` (3), `runtime.lookup_attempts`, `runtime.Mapping` (4), `runtime.model_snapshot` (2), `runtime._object` (3), `runtime._plain` (2), `runtime._recorded_action_generation_schema`, `runtime._recorded_assignment_transport`, `runtime._references_in`, `runtime.requested_contract_information` (2), `runtime.schema_failure_diagnostic` (2), `runtime.sqlite3`, `runtime.state_frame`, `runtime.ValidationError` (5), `runtime.WorkflowError` (14), `runtime.yield_table`, `self.workflow.available_child_roles`, `self.workflow.binding_context`, `self.workflow.contract_information_profile`, `self.workflow.contract_information_reply`, `self.workflow.controller_binding`, `self.workflow.decision_exchanges` (4), `self.workflow.decision_protocol` (3), `self.workflow.episode_bindings`, `self.workflow.execute`, `self.workflow.execution_expectations`, `self.workflow.freeze_contract_information`, `self.workflow.freeze_literature_numerical_contracts`, `self.workflow.history_preview`, `self.workflow.journal` (3), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context`, `self.workflow.numerical_contracts`, `self.workflow.pending_work`, `self.workflow.permits_common_action`, `self.workflow.provider` (3), `self.workflow.receipts` (4), `self.workflow.resource_context`, `self.workflow.resource_estimator` (4), `self.workflow.run_id`, `self.workflow.services` (2), `self.workflow.shared_information_context`, `self.workflow.specialist`, `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (5), `self.workflow.waiting_support`, `table:runtime_model_calls` (8) |
| `task_instructions.py` | 28 | instruction composition: job-episode or generic INSTRUCTIONS, replaced by binding instructions (replaces_default_instructions), plus reason/knowledge/launch/redelivery/wait/native-event/exchange texts | `binding_context`, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL`, `runtime_prompt.INSTRUCTIONS` (4), `runtime_prompt.REASONING_COMMIT_REQUIREMENT`, `self.workflow.binding_context`, `self.workflow.decision_protocol`, `self.workflow.is_job_source`, `self.workflow.job_episodes`, `self.workflow.knowledge`, `self.workflow.launch_instructions`, `self.workflow.native_event_information`, `self.workflow.permits_common_action` (3), `self.workflow.specialist` |
| `task_state.py` | 108 | old generic source state (identity, report values, restore, checkpoint, record_effect, record_execution_failure) | `import:episode_source_failure`, `import:runtime`, `param:workflow.context`, `param:workflow.grains`, `runtime.ActionLeaf`, `runtime.EFFECT_VERSION`, `runtime.Episode`, `runtime.interpretation_schema`, `runtime._json` (2), `runtime.json` (4), `runtime._object`, `runtime._plain`, `runtime.Record`, `self.workflow.archive`, `self.workflow.completions` (4), `self.workflow.controller_value`, `self.workflow.execution_binding` (4), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions`, `self.workflow.run_id`, `self.workflow.source_credit_view`, `self.workflow.store` (2), `table:runtime_actions` (5) |
| `task_suspension.py` | 9 | `suspension_changed` on old execution backend | `self.workflow.execution_backend`, `self.workflow.execution_handle` (2) |
| `terminal_execution.py` | 131 | TerminalExecutionBehavior: practical launch_local/launch_hpc command execution with PracticalState, validations, practical receipts, completion proof, PracticalYieldEstimator, practical facts and credit (used here per non-API resource) | `import:communication`, `import:practical_yield`, `yield:PracticalYieldEstimator` (2) |
| `to_parent.py` | 145 | facts: per-adapter native facts with empty families for others; API facts plus BLAST grader rows; generic: execution_handoff_refs, execution_result_refs, file sources, file capture outcomes, NATIVE_RESULT_ORIGIN, execution_completed; plus closed credit facts; `validate_report` requires typed-return adapters to accept and every x-source field equal recorded facts | `import:communication` (2) |
| `work_operations.py` | 121 | `catalog`/`execute`: dispatch by target to the per-tool result operation catalog (NMF, masking, utility, RNA comparison/structure, BLAST databases, API, HMMER prep/HMMER, BLAST, Infernal/prep) or native status/collect/read; argument errors become invalid outcomes | `import:communication` |
| `yield_estimator.py` | 99 | `yield_controller` (requires `require_private_yield`): unbounded native selectors use `results_yield_profiles[native_unbounded_<kind>]`; finite native selectors use `task_yield_profiles['results:native_finite_<kind>']` with a finite-result estimator (verified endpoint -> completion; zero remaining -> exact 0; else bounded-credit yield with maximum = remaining uncredited selector credit); API/typed selectors use `results:api_<service>[_<version>]` / `results:typed_<kind>_<version>` profiles with PracticalYieldEstimator | `import:communication`, `import:numerical`, `import:practical_yield` (2), `yield:estimate_bounded_credit_yield` (2), `yield:NumericBand` (2), `yield:PracticalYieldEstimator` (5), `yield:YieldController` (4), `yield:YieldEstimate` (2), `yield:YieldParameters` (4) |
