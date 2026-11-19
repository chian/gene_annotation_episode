# Episode intent: `a102/structural_homology_evidence/hpc_work_planning/hpc_resource_prediction`

Source: this episode's own files at commit `97308b94c`: 25 Python files (1,370 lines) directly in the folder plus a
`tests/` folder of 5 files (25 lines); no `grading/` or `scoring/` folder. Old role name: `hpc_prediction`. Old
class: `HPCEpisode` (fifteen mixins), task class `ResourcePredictionTask`. Old `binding_path`:
`structural_homology_evidence/hpc_work_planning/hpc_resource_prediction`; old `commissioning_parent`:
`structural_homology_evidence/hpc_work_planning` (role `hpc`).

## What this episode is for

It improves a time/resource prediction model for the HPC work its parent plans, using measured historical cases,
and compares the candidate resource portfolios with that model. It does not launch anything: launch, monitoring and
parsing belong to its execution sister. Goal text, verbatim from `goal.py`:

> Iterate on a generalized time/resource model using measured historical cases. Refresh shared history, inspect
> support and held-out quality, fit a disjoint training selection, and compare useful portfolios. Inspect missing
> capacity, launcher and queue facts with lightweight discovery; propose executable resource alternatives when the
> parent has not supplied them. Preparation and submission belong to the execution sister. Forecast CPU time and
> memory demand as well as queue, setup and work time. Compare node/worker counts, memory capacity, workload
> parameters and elapsed cost. The paired execution episode owns Launch, monitoring and parsing. Both sisters use
> this parent-owned ledger; preserve model and comparison identities for that sibling. The fixed reference and
> validation set cannot change. Model credit is modest measured improvement; the HPC parent later scores frozen
> predictions against real outcomes. Unknown inputs stay unknown. Return when further model improvement is less
> useful than running the next worthwhile portfolio.

## Task and instructions

One unit is one model-selected tool action (`permitted_common_actions` is `('tool',)`; no reasoning commit, no
wait, no child). The episode supplies its whole instructions (`replaces_default_instructions = True`):
`task_instructions.py` composes the goal text plus the tool-knowledge and launch-instruction library text when those
appear in the decision context. The HPC prompt renderer (`render_hpc_prompt`) presents each decision.

All state lives in the parent's HPC ledger (`<directory>/hpc/<digest(run_id, owner_episode_id)>/hpc.sqlite`),
which this episode opens but never creates (`prediction_state.py`); the ledger's owner record must have this
episode's scope and commission identity. On first use it records the reference model (the commission's prior), an
initial model fitted from shared history when shared memory is configured, and its entry quality once per episode.

## What it reads from its parent's assignment

| Field | Meaning |
|---|---|
| `owner_episode_id` | The `hpc` parent episode that owns the ledger (required) |
| `commission_id` | One of the binding's static commissions, or |
| `commission_source_ref` | A Store commission source read through `hpc_commission_sources.read` (exactly one of the two) |

The commission supplies resource id, history, validation ids, model specification, candidates, obligations,
preferences, credit scale (`credit.model_scale`), limits (`queue_max_age_seconds`), an optional execution profile
and, under the private yield binding, `yield_bindings`. `prepare_assignment` refuses an assignment that does not
come from an `hpc` parent whose own episode id is the owner and whose commission identity is the same.

Construction settings (`configuration.py`): `directory`, `resources` (at least one `pbs_ssh`), `commissions` (each
validated against the resources), optional `shared_execution_memory`, `require_commission_yield` (boolean; when
true every commission must carry `yield_bindings`).

## Children

None (`child_roles` returns `()`).

## Decision state and what the model sees

Per-episode state: call count, last outcome, feedback, report values and basis, restore/checkpoint state
(`task_state.py`).

Shown at each decision: the common decision fields (goal, scope, working state, visible records, credit, credit
binding, elapsed-time view, pending work, last outcome, feedback, deliveries, controller, tools, tool knowledge,
report facts, requested form, current report update) plus the inputs of `decision_inputs.py` (resource context,
launch-instruction library and selected launch instructions, the binding's initial context, completed action
reports, requested action history in an HPC context, pending work, execution expectations for `hpc_prediction`,
resource and native estimates) plus this episode's summary (`internal_summary.py`):

- `hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`, `hpc_tool_request`;
- `hpc_model_ref` (current model), `hpc_credit` (its credit view), `hpc_model_support`;
- `hpc_latest_comparison` (without episode id and operation key);
- `hpc_report_form` (`hpc_credit`, `hpc_model_ref`, `hpc_result_refs`);
- `hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_queue_refs`;
- `hpc_shared_memory` and `hpc_shared_history_refs` when shared memory is configured;
- `hpc_available_training_ids` (history minus validation ids).

## Tools

| Tool | What it does |
|---|---|
| `hpc.read` | Read retained HPC evidence by identity: a history case, a ledger record, or an owned received result source whose body equals the ledger receipt |
| `hpc.compare` | Forecast every approved candidate with a model and a queue observation; compare against obligations and preferences (excluding obligations already credited); rank by net expected value; no work is selected or launched |
| `hpc.history.refresh` | Only with shared memory: read age-weighted shared timing history once (queue history resource-wide; work timing only for a matching execution profile; at most 2000 new observations) |
| `hpc.discovery.run` | One lightweight read-only command over the resource's SSH argv in `/lus/flare/projects/BioReason-Aurora-Test` (stdout ≤ 64 KiB, stderr ≤ 8 KiB kept; cached in shared memory); no submission, installation or computation |
| `hpc.candidate.propose` | Retain an executable candidate portfolio (JSON: id, queue, nodes, wall_seconds, features, optional resource capacity, units with argv/environment/effort, optional files, preparation instructions); identities are immutable; validated with the commission |
| `hpc.queue.observe` | Acquire the PBS queue and ALCF score/status once (a fresh shared-memory observation within `queue_max_age_seconds` is reused) and derive per-candidate queue features |
| `hpc.model.fit` | Fit the selected training ids (original non-validation cases that precede every validation case in time) and validate on the fixed held-out cases |

Each action is cached in the ledger by operation key; a reference or argument error returns an `invalid` outcome
with feedback (and, for `hpc.compare`, a recovery hint). Note for the port: the old discovery call carries a fixed
elapsed-time cutoff (`subprocess.run(..., timeout=90)` in `prediction_operations.py`), which conflicts with the
repository's no-elapsed-time-limit rule; the 64 KiB / 8 KiB output truncation is a size bound, not a time bound.

## Credit

Credit kind `operational`. Credit = `commission.credit.model_scale` × (held-out quality of the current model −
quality at this episode's entry) + the `validation` contributions the parent ledger attributes to predictions made in
this episode (`prospective_validation_credit`). It is signed: a worse current model gives a negative gain. A model
trained on any case outside the commission's original history has no measured quality and adds no gain (its
improvement is credited later, prospectively, when real outcomes arrive). Actual job credit is not counted here
(`actual_job_credit_counted_here: False`). `hpc.model.fit` also records `model_credit(model_ref, quality −
reference quality)` in the ledger.

## Continuation

`yield_estimator.py`: requires the private yield binding (`hpc_episode_yield_binding_required` otherwise) and the
commission's `yield_bindings['hpc_prediction']` = `{cutoff, parameters}`. It builds an old `YieldController(epoch,
initial_credit, cutoff, YieldParameters(**parameters))` with an `HPCContinuationEstimator` (bound to the cutoff as its
continuation cost) that verifies continuation packets against the ledger. Which of the three current estimators the
old default controller estimate corresponds to is not visible from this folder; the credit is a signed measured
gain.

`continuation_for_action` records a zero continuation packet (earned 0, expected 0, ceiling 0; reason
`prediction_ready_without_new_measured_improvement_opportunities`) when the commission has no validation ids, every
available case is already in the current model's training set, candidates exist, and comparisons by this episode
cover exactly the current candidates for the current model with a queue observation no older than
`queue_max_age_seconds`. The comment states it bounds available action value, not action count; new observations
reopen prediction.

## What it reports to its parent

| Fact | Meaning |
|---|---|
| `hpc_credit` | Signed measured credit (repeated polling adds none) |
| `hpc_model_ref` | The selected model's identity (`hpc_model` namespace) |
| `hpc_accepted_obligations` | Obligations with accepted actual results in the ledger |
| `hpc_result_refs` | Known result sources with original bytes and attempt custody |

A report field declared from a fact must equal it (`hpc_report_disagrees_with_recorded_evidence`). After closure a
model reference is accepted only through the saved closure form and a read-only look at the owner's ledger
(`closed_models.py`).

## Differences from similar episodes

- The same episode exists under `a103/gene_context_evidence`, `a104/evolutionary_history_evidence`,
  `a107/partner_presence_evidence` and `a110/biochemical_feasibility_evidence` (`hpc_work_planning/hpc_resource_prediction`).
  After replacing axis names, `goal.py`, `credit.py`, `yield_estimator.py`, `prediction_operations.py`,
  `from_parent.py`, `to_parent.py` and `configuration.py` are the same text in all five; the A107 copy's summary
  omits `hpc_owner_episode_id`; the A104 copy splits the decision files differently (`action_admission.py`,
  `action_execution.py`, `decision_contracts.py`, `decision_exchange.py`, `presentation*.py`).
- Against its sister `hpc_allocation_execution`: this one forecasts and compares; the sister launches, monitors and
  parses. Both use the same parent-owned ledger.
- Carried text that is not prediction-specific: `decision_state.py` and `task.py`/`task_decision.py`/`task_state.py`
  are the old generic loop; the `literature_completed_work` and `literature_numerical_contracts` branches have no
  role here.
- Its tests (`tests/*.py`) only bind shared old-root test classes (`root.tests.hpc_*`) to this binding path; they
  contain no test of their own.

## Old support modules this episode imports

Looked up in `runs/placement_plan/placement.tsv` and by file name under `episode_support/` (the modules themselves
were not read). "Files" counts the files in this folder that import it.

| Old module (`root.a102.`...) | Files | Home now |
|---|---|---|
| `communication` | 7 | no structural_homology_evidence copy found (copies for other axes under episode_support/forms/AXIS/) |
| `domain` | 3 | episode_support/records/structural_homology_evidence/domain.py |
| `episode_bindings` | 1 | the deleted old per-axis binding table |
| `episode_return_records` | 1 | no placed home found |
| `episode_source_failure` | 2 | no placed home found |
| `episode_work_report` | 1 | no placed home found |
| `execution_contracts` | 2 | episode_support/forms/structural_homology_evidence/execution_contracts.py |
| `execution_guidance` | 3 | episode_support/instructions/execution_guidance.py |
| `execution_memory` | 1 | episode_support/records/structural_homology_evidence/execution_memory.py |
| `hpc_campaign` | 2 | episode_support/jobs/hpc/structural_homology_evidence/hpc_campaign.py |
| `hpc_commission_sources` | 1 | episode_support/jobs/hpc/structural_homology_evidence/hpc_commission_sources.py |
| `hpc_ledger` | 1 | episode_support/jobs/hpc/structural_homology_evidence/hpc_ledger.py |
| `hpc_queue` | 5 | episode_support/jobs/hpc/hpc_queue.py |
| `library.action_contracts` | 1 | no placed home found |
| `library.hpc_continuation` | 1 | no placed home found (old yield code) |
| `library.hpc_prediction` | 5 | episode_support/jobs/hpc/structural_homology_evidence/hpc_prediction.py |
| `library.hpc_prompt` | 2 | no placed home found |
| `library.hpc_resource_prediction` | 1 | episode_support/jobs/hpc/structural_homology_evidence/hpc_resource_prediction.py |
| `library.private_policy_call` | 2 | no placed home found |
| `library.report_fact_assembly` | 1 | no placed home found |
| `numerical` | 1 | old yield code; `YieldParameters` is now in top-level yield_control, `YieldController` is not |
| `providers` | 1 | gene_annotation_episode/model_provider.py (defines ModelCallError) |
| `runtime` | 5 | the deleted old per-axis runner |
| `root.tests.hpc_*` (4 modules) | 4 tests | old shared root tests; never restored |

## File by file

Counts are occurrences in the file text. `self.workflow` also covers `source.workflow` and a `workflow` argument;
"BindingContext fields" are attribute reads on the old context object (`context`, `parent`, `child`); "old-runner
callbacks defined" are methods the old runner called on the binding or task. The same rows, one per name and file,
are in `runs/carry_over/calls/a102_06.tsv` (320 rows, 530 uses in this episode).

| Old file | Lines | This episode's own intent in it | Old-runner names used (name×uses) |
|---|---|---|---|
| `__init__.py` | 0 | Nothing (package marker). | none |
| `binding_record.py` | 12 | Its configuration record (`hpc_episode_v1`): resources, static commissions, shared execution memory record, `require_commission_yield`. | **old-runner callbacks defined**: `as_record`; **per-axis providers**: `self.memory`×2 |
| `closed_models.py` | 29 | Accepting a closed model reference (`hpc_model` namespace) only when the saved closure form names it and the owner's HPC ledger (opened read-only) holds that model with matching run, owner episode and scope. Mostly old journal custody. | **BindingContext fields**: `assignment`, `episode_id`, `role`, `run_id`×2, `scope`; **imports from old `root.a102`**: `communication`, `episode_return_records`, `hpc_queue`; **old-runner callbacks defined**: `frozen_reference`; **old support classes**: `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_forms` |
| `configuration.py` | 30 | Settings and checks: resources must include a `pbs_ssh` resource; static commissions validated against resources; `require_commission_yield` boolean, and when set every commission must carry `yield_bindings`; optional shared execution memory. | **imports from old `root.a102`**: `communication`, `execution_memory`, `hpc_campaign`; **per-axis providers**: `self.memory`; **old support classes**: `ExecutionMemory`×2 |
| `credit.py` | 31 | Credit kind `operational`. Credit = `commission.credit.model_scale` × (held-out validation quality of the current model − quality at this episode's entry) + prospective validation credit the parent ledger attributes to predictions from this episode. A model trained on any case outside the commission's original history has no measurable quality, so its gain is 0. Actual job credit is not counted here. | **BindingContext fields**: `episode_id`×2; **imports from old `root.a102`**: `library.hpc_prediction`; **old-runner callbacks defined**: `credit_kind`, `credit_view` |
| `decision_inputs.py` | 46 | Additions to each decision: resource context, launch-instruction library and selected launch instructions, the binding's initial decision context, completed action reports, `requested_action_history` in an HPC context, pending work, execution expectations for role `hpc_prediction`, resource estimates, native execution expectations. | **imports from old `root.a102`**: `episode_work_report`×2, `library.hpc_prompt`; **old-runner callbacks defined**: `decision_inputs`; **self.workflow**: `binding_context`, `episode_bindings`, `execution_expectations`, `launch_instructions`×2, `native_estimation_context`, `pending_work`, `resource_context`, `resource_estimator`×4 |
| `decision_state.py` | 31 | What the model is shown (the common decision fields) plus this binding's `decision_context`. Nothing of its own beyond the field list. | **imports from old `root.a102`**: `runtime`×2; **old-runner callbacks defined**: `decision_state`; **old runtime**: `FACT_MEANINGS`, `FACT_SOURCES`, `json`, `Mapping`×2, `_plain`×2, `_references_in`; **self.workflow**: `binding_context`, `catalog`, `controller_binding`, `delivery_status`, `extra_report_sources`, `job_episode_options`, `journal`×2, `knowledge`, `local_outcome_preview`, `pending_work`, `receipt_projection`, `run_id`, `source_credit_binding`, `source_credit_view`, `specialist`, `store`×3, `store.reference_subset`, `tools`, `tools.model_contract_catalog`, `working_state`; **journal/receipt tables**: `runtime_actions` |
| `episode.py` | 38 | The binding: path `structural_homology_evidence/hpc_work_planning/hpc_resource_prediction`, parent `hpc_work_planning`, role `hpc_prediction`, no entry role, supplies its whole instructions, HPC prompt renderer; no children; permitted action `tool` only. | **BindingContext fields**: `role`; **imports from old `root.a102`**: `library.hpc_prompt`; **old binding attributes**: `binding_path`, `commissioning_parent`, `decision_prompt_renderer`, `decision_source_type`, `entry_roles`, `replaces_default_instructions`, `roles`; **old-runner callbacks defined**: `allowed_children`, `child_roles`, `permitted_common_actions` |
| `from_parent.py` | 44 | Assignment form: `owner_episode_id` (required) and exactly one of `commission_id` (from static commissions) or `commission_source_ref` (a Store commission source). The assignment must come from an `hpc` parent whose episode id is the owner and whose commission identity matches; with private yield the commission must carry `yield_bindings`. | **BindingContext fields**: `assignment`, `episode_id`, `role`; **imports from old `root.a102`**: `communication`, `domain`, `execution_contracts`, `hpc_commission_sources`; **old-runner callbacks defined**: `assignment_schema`, `prepare_assignment` |
| `goal.py` | 20 | The goal text: iterate on a generalised time/resource model from measured history; refresh history, inspect support and held-out quality, fit a disjoint training selection, compare portfolios; lightweight discovery of capacity, launcher and queue facts; propose executable resource alternatives; forecast CPU time, memory, queue, setup and work time; the execution sister owns launch, monitoring and parsing; fixed reference and validation set; credit is modest measured improvement; unknown inputs stay unknown; return when model improvement is worth less than running the next portfolio. | **old-runner callbacks defined**: `instructions` |
| `internal_summary.py` | 36 | Per-decision summary from the parent's HPC ledger: commission, owner, candidates, resource, tool requests, current model, credit view, latest comparison, model support, the HPC report form (`hpc_credit`, `hpc_model_ref`, `hpc_result_refs`), plans, latest monitor, monitor controllers, queue refs, shared memory and history refs, available training ids (history minus validation ids). | **imports from old `root.a102`**: `library.hpc_prediction`; **old-runner callbacks defined**: `decision_context`; **per-axis providers**: `self.memory`×2 |
| `portfolio_comparison.py` | 31 | Candidate set (commission candidates plus proposed candidates); candidate features (features, nodes, wall seconds, queue indicator, numeric queue features); comparison: forecast each candidate with the model and observed queue, compare against obligations and preferences excluding already credited obligations, sort by net expected value. | **imports from old `root.a102`**: `hpc_queue`, `library.hpc_prediction` |
| `prediction_history.py` | 63 | Training history: the commission's original history, the latest shared-history snapshot (excluding the same physical attempts), and one latest measured observation per closed allocation plan (censored duration kept for failed work). Shared history: age-weighted queue history for the resource plus profile-matched work timing; queue metric kept only when the portfolio has one matching queue or the model carries the queue indicator; at most 2000 new observations. | **imports from old `root.a102`**: `execution_guidance`, `library.hpc_resource_prediction`; **per-axis providers**: `self.memory`×3 |
| `prediction_operations.py` | 147 | The tools and their execution: `hpc.read`, `hpc.compare`, `hpc.history.refresh` (with shared memory), `hpc.discovery.run` (one read-only SSH command in the project directory, cached in shared memory), `hpc.candidate.propose` (immutable candidate identities, validated against the commission), `hpc.queue.observe`, `hpc.model.fit` (training ids must be non-validation and precede the temporal validation; model credit = quality − reference quality, or 0 when trained on later cases). Every action is cached by operation key in the ledger; invalid arguments become an `invalid` outcome with feedback. | **BindingContext fields**: `episode_id`×3; **imports from old `root.a102`**: `communication`, `domain`, `execution_contracts`, `execution_guidance`, `hpc_campaign`, `hpc_queue`, `library.hpc_prediction`; **old-runner callbacks defined**: `catalog`, `execute`; **per-axis providers**: `self.memory`×6 |
| `prediction_state.py` | 43 | Opening the parent-owned HPC ledger (`hpc/<digest(run, owner)>/hpc.sqlite`) and refusing a scope or commission that differs from the owner's; initialisation: reference model from the prior, optional initial model fitted from shared history, entry quality recorded once per episode; current model = last model choice. | **BindingContext fields**: `assignment`×4, `episode_id`, `role`, `scope`×2; **imports from old `root.a102`**: `communication`, `domain`, `hpc_ledger`, `hpc_queue`, `library.hpc_prediction`; **old-runner callbacks defined**: `initialize`; **per-axis providers**: `self.memory`; **old support classes**: `HPCLedger`×2 |
| `queue_observations.py` | 27 | PBS queue observation through the resource, using a fresh shared-memory observation within `queue_max_age_seconds`; reading a queue observation and optionally requiring freshness. | **imports from old `root.a102`**: `execution_guidance`, `hpc_queue`; **per-axis providers**: `self.memory`×4 |
| `received_evidence.py` | 51 | Known record refs (received plus record selection); a received `episode.hpc_result` Store source is accepted only when known, of this run and within the parent scope; reading evidence by history id, ledger id or an owned result source whose body matches the ledger receipt. | **BindingContext fields**: `received_record_refs`, `scope`; **imports from old `root.a102`**: `communication`; **old-runner callbacks defined**: `resolve_received_reference`; **self.services**: `record_selection` |
| `report_delivery.py` | 25 | Closure: typed form built once from saved facts and last interpretation (same text as the other A102 copies). | **imports from old `root.a102`**: `library.private_policy_call`, `library.report_fact_assembly`, `runtime`×2; **old-runner callbacks defined**: `finish`; **old runtime**: `form_with_facts`, `_json`×2, `json`, `Record`×2; **self.workflow**: `binding_context`, `episode_bindings`, `facts`, `journal`×2, `pending_handles`, `release`×2, `source_credit_view`; **journal/receipt tables**: `runtime_forms`×2 |
| `task.py` | 150 | The decision loop (old runner): restore/replay, model call, response admission, action execution, credit recorded after each action; report grain name `hpc_prediction`. | **imports from old `root.a102`**: `episode_source_failure`, `library.action_contracts`, `library.private_policy_call`, `providers`, `runtime`×2; **old-runner callbacks defined**: `apply_response`, `execute`, `next`; **old runtime**: `ActionFailure`, `ContractInformationError`, `_decode_recorded_action_response`, `Draft202012Validator`, `EventTargetError`, `inspect`, `_json`×5, `json`×8, `nullcontext`×5, `observes_action_outcome`, `ReportBoundaryError`, `schema_failure_diagnostic`, `SourceEnd`×2, `validate_form`, `ValidationError`×2, `_wait_target_feedback`, `WorkflowError`; **self.workflow**: `action_schema`, `completed_unit`, `completions`×2, `controller_value`×2, `decision_exchanges`×3, `execute`, `execution_binding`×7, `inprocess_replay`×4, `journal`×7, `pending_work`, `receive_native_outcome`, `receive_outcome`, `resolver`, `run_id`×2, `selected`×3, `source_credit_view`, `store`×7, `validate_report`; **journal/receipt tables**: `runtime_actions`×8, `runtime_episodes`, `runtime_model_calls`×2 |
| `task_decision.py` | 288 | The model call and exchange protocol (old runner); instructions come from the old services composer; prompt renderer passed to the provider. Nothing of its own. | **imports from old `root.a102`**: `runtime`×2; **old binding attributes**: `instruction_composer`; **old-runner callbacks defined**: `call`, `complete_decision`, `conversation_key`, `exchange_decision`, `exchange_response`, `exchange_schema`, `instructions`, `interpretation_context`, `validate_contract_exchange_history`, `validate_contract_exchange_request`; **old provider interface**: `complete_with_presentation`, `has_session`×3, `prompt_renderer`; **old runtime**: `_action_generation_schema`×2, `apply_state_frame`, `_ASSIGNMENT_TRANSPORT`, `_category_yield_parameters`, `composition_lookup_schema`×2, `CONTRACT_INFORMATION_OPERATIONS`, `DECISION_CONTEXT_VERSION`×2, `DECISION_EXCHANGE_PROTOCOL`×5, `_digest`, `Draft202012Validator`, `instructional_model_context`×4, `is_contract_information`, `_json`×14, `json`×3, `lookup_attempts`, `Mapping`×2, `model_snapshot`×2, `_object`×3, `_plain`×2, `_recorded_action_generation_schema`, `_recorded_assignment_transport`, `_references_in`, `requested_contract_information`×2, `schema_failure_diagnostic`×2, `sqlite3`, `state_frame`, `ValidationError`×5, `WorkflowError`×14, `yield_table`; **self.workflow**: `contract_information_profile`, `contract_information_reply`, `controller_binding`, `decision_exchanges`×4, `decision_protocol`×3, `execute`, `freeze_contract_information`, `history_preview`, `journal`×3, `numerical_contracts`, `provider`×3, `provider.conversation_key`, `provider.has_session`, `receipts`×4, `run_id`, `services`×2, `specialist`, `store`×2, `store.reference_subset`, `uses_received_record_context`×2, `validate_contract_information`×5; **journal/receipt tables**: `runtime_model_calls`×8; **old yield names**: `_category_yield_parameters`×2, `yield_table`×2 |
| `task_instructions.py` | 11 | Instruction composer: the goal text plus tool-knowledge and launch-instruction text when present in the context. | **old-runner callbacks defined**: `instructions`; **self.workflow**: `binding_context`, `knowledge`, `launch_instructions`, `specialist` |
| `task_state.py` | 108 | Per-episode decision state and restore/checkpoint; unfinished own actions are only of kind `tool`. | **imports from old `root.a102`**: `episode_source_failure`, `runtime`×2; **old-runner callbacks defined**: `bind_execution_context`, `checkpoint`, `record_effect`, `record_execution_failure`, `restore`, `restore_checkpoint`; **old runtime**: `ActionLeaf`, `EFFECT_VERSION`, `Episode`, `interpretation_schema`, `_json`×2, `json`×4, `_object`, `_plain`, `Record`; **self.workflow**: `archive`, `completions`×4, `context`, `controller_value`, `execution_binding`×4, `grains`, `inprocess_replay`×7, `journal`×5, `progress_provider`×2, `recover_commissions`, `run_id`, `source_credit_view`, `store`×2; **journal/receipt tables**: `runtime_actions`×5 |
| `to_parent.py` | 40 | Report facts: `hpc_credit` (signed measured credit; polling adds none), `hpc_model_ref`, `hpc_accepted_obligations` (actual contributions), `hpc_result_refs` (known result sources); `hpc_model` references resolve against ledger models; the report must equal the recorded facts. | **imports from old `root.a102`**: `communication`, `episode_bindings`; **old-runner callbacks defined**: `facts`, `fact_sources`, `resolve`, `validate_report` |
| `waiting.py` | 9 | Records the suspension condition and passes it to the external executor. | **old-runner callbacks defined**: `suspension_changed`; **self.workflow**: `execution_backend`, `execution_handle`×2 |
| `yield_estimator.py` | 60 | Continuation: requires the private yield binding; uses the commission's `yield_bindings['hpc_prediction']` = {cutoff, parameters} in an old `YieldController` with an HPC continuation estimator that verifies continuation packets. `continuation_for_action`: when there are no validation ids, every available case is already trained, candidates exist and current comparisons cover them all with a queue observation younger than `queue_max_age_seconds`, it records a zero-continuation packet (`prediction_ready_without_new_measured_improvement_opportunities`); new observations reopen prediction. | **BindingContext fields**: `assignment`, `episode_id`×2, `role`×5, `run_id`, `scope`; **imports from old `root.a102`**: `library.hpc_continuation`, `numerical`; **old-runner callbacks defined**: `continuation_for_action`, `practical_estimator`, `yield_controller`; **old yield names**: `HPCContinuationEstimator`×2, `with_continuation_cost`, `YieldController`×2, `YieldParameters`×2 |
| `tests/__init__.py` | 0 | Nothing (package marker). | none |
| `tests/test_calculation_connections.py` | 7 | Binds the shared HPC calculation-connection checks to this binding (`axis a102`, role `hpc_prediction`). No test body of its own. | **imports from old shared `root.tests`**: `hpc_calculation_behavior`; **old binding attributes**: `binding_path` |
| `tests/test_prediction_behavior.py` | 6 | Binds the shared prediction behaviour checks to this binding. No test body of its own. | **imports from old shared `root.tests`**: `hpc_prediction_behavior`; **old binding attributes**: `binding_path` |
| `tests/test_prediction_prompt.py` | 6 | Binds the shared prediction prompt checks to this binding. No test body of its own. | **imports from old shared `root.tests`**: `hpc_prediction_prompt_behavior`; **old binding attributes**: `binding_path` |
| `tests/test_prediction_task.py` | 6 | Binds the shared prediction task checks to this binding. No test body of its own. | **imports from old shared `root.tests`**: `hpc_prediction_task_behavior`; **old binding attributes**: `binding_path` |

## Carried over

Old files read at `97308b94c` through `git show` (the repository's `.git` is in `gene_annotation_episode_disk`).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | PredictionBindingRecord | machinery | the binding's own record class |
| binding_record.py | PredictionBindingRecord.as_record | machinery | the binding's own as_record() is deleted (README 3e) |
| closed_models.py | ClosedModels | machinery | re-validation of a model identity after closure from runtime_forms and EpisodeReturnRecords |
| closed_models.py | ClosedModels.frozen_reference | machinery | journal/runtime_forms re-validation after closure (sqlite3 read of the owner ledger); the model identity is returned as a fact and the system admits the result |
| configuration.py | PredictionConfiguration | episode function | settings values: task.py resources_of, memory_configured (ctx.settings); the construction of ExecutionMemory is the service estimate_table (BLOCKED-ON-JOB-SERVICE) |
| configuration.py | PredictionConfiguration.__init__ | episode function | task.py resources_of (explicit_hpc_resource_required) and memory_configured; directory, commissions, require_commission_yield, store and run_id are not carried (the commission is the ledger record; the yield binding is the assignment field yield_binding; ctx.run_id) |
| credit.py | HPCEpisodeCredit | episode function | credit.py |
| credit.py | HPCEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | HPCEpisodeCredit._quality | episode function | task.py model_quality |
| credit.py | HPCEpisodeCredit.credit_view | episode function | credit.py credit_view and credit |
| decision_inputs.py | PredictionDecisionInputs | episode function | task.py decide (resource context, launch-instruction library and selected launch instructions, initial information) |
| decision_inputs.py | PredictionDecisionInputs.decision_inputs | episode function | task.py decide; messages/internal_summary.py history (requested_action_history from view.outcomes); not carried (unplaced): completed_action_reports, pending_work, execution_expectations, resource and native estimates |
| decision_state.py | PredictionDecisionState | episode function | messages/internal_summary.py internal_summary and task.py decide |
| decision_state.py | PredictionDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (last outcome, controller state) and task.py decide (context); the visual_evidence SQL on runtime_actions, the receipt/credit/binding/delivery fields and the report-fact fields are machinery |
| episode.py | HPCEpisode | episode function | episode.py HPCResourcePrediction |
| episode.py | HPCEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} |
| episode.py | HPCEpisode.allowed_children | machinery | child binding lookup; the child set is CHILD_SLOTS |
| episode.py | HPCEpisode.permitted_common_actions | episode function | task.py selection_schema (the tool action only) |
| from_parent.py | PredictionAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | PredictionAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | PredictionAssignment.commission_identity | episode function | messages/read_from_parent.py commission_identity |
| from_parent.py | PredictionAssignment._commission | episode function | task.py ledger_commission (the commission is the ledger's own record; BLOCKED-ON-JOB-SERVICE); the Store commission-source read (hpc_commission_sources.read) is not called |
| from_parent.py | PredictionAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (the form admits the schema; the ownership/identity check and the yield-binding check are a check of a commission and are not carried; the yield binding is the required field yield_binding) |
| goal.py | PredictionGoal | episode function | goal.py GOAL |
| goal.py | PredictionGoal.instructions | episode function | goal.py GOAL (text unchanged); composed into the instructions by task.py instructions |
| internal_summary.py | PredictionSummary | episode function | messages/internal_summary.py |
| internal_summary.py | PredictionSummary.decision_context | episode function | messages/internal_summary.py ledger_state and internal_summary (the initialize-on-first-decision side effect is the unit hpc_initialize offered by task.py decide; hpc_report_form is machinery) |
| portfolio_comparison.py | PortfolioComparison | episode function | task.py |
| portfolio_comparison.py | PortfolioComparison._candidates | episode function | task.py candidates |
| portfolio_comparison.py | PortfolioComparison._features | episode function | task.py candidate_features |
| portfolio_comparison.py | PortfolioComparison._comparisons | episode function | task.py comparisons |
| prediction_history.py | PredictionHistory | episode function | task.py |
| prediction_history.py | PredictionHistory._history | episode function | task.py history_cases |
| prediction_history.py | PredictionHistory._shared_history | episode function | task.py shared_history (shared memory through the service estimate_table: BLOCKED-ON-JOB-SERVICE) |
| prediction_operations.py | PredictionOperations | episode function | task.py TOOLS |
| prediction_operations.py | PredictionOperations.catalog | episode function | task.py CATALOG and operation_catalog |
| prediction_operations.py | PredictionOperations.execute | episode function | task.py tools hpc_read, hpc_compare, hpc_history_refresh, hpc_discovery_run (job_access), hpc_candidate_propose, hpc_queue_observe (job_access), hpc_model_fit; the schema validation of arguments is action; the cached/save_action/action_intent ledger rows are machinery (the attempts journal and ctx.operation_key); the fixed 90 second discovery cutoff is not carried |
| prediction_state.py | PredictionState | episode function | task.py |
| prediction_state.py | PredictionState.state | episode function | task.py state_of and ledger_commission (the assignment re-validation and the owner scope/identity comparison are not carried) |
| prediction_state.py | PredictionState.initialize | episode function | task.py initialize and the tool hpc_initialize |
| prediction_state.py | PredictionState._current_model | episode function | task.py current_model |
| queue_observations.py | QueueObservations | episode function | task.py |
| queue_observations.py | QueueObservations._observe_queue | episode function | task.py observed_queue (job_access and estimate_table: BLOCKED-ON-JOB-SERVICE) |
| queue_observations.py | QueueObservations._queue | episode function | task.py queue_snapshot |
| received_evidence.py | ReceivedEvidence | episode function | task.py |
| received_evidence.py | ReceivedEvidence._known | machinery | received-record bookkeeping (record_selection, received_record_refs); custody: reader.holds |
| received_evidence.py | ReceivedEvidence.resolve_received_reference | episode function | task.py resolve_result_source (held source; the scope comparison is custody) |
| received_evidence.py | ReceivedEvidence.read_evidence | episode function | task.py read_evidence |
| report_delivery.py | PredictionReportDelivery | machinery | report delivery: saved runtime_forms, form_with_facts, release |
| report_delivery.py | PredictionReportDelivery.finish | machinery | report delivery (runtime_forms save/restore, release(episode_id)); the result is final_to_parent |
| task.py | ResourcePredictionTask | episode function | task.py decide, action and the tools |
| task.py | ResourcePredictionTask.next | machinery | the decision loop with replay, in-process completion slots and SourceEnd; the decision is task.py decide |
| task.py | ResourcePredictionTask.apply_response | episode function | task.py action (schema validation of the selection and the rejection feedback); the report_update admission is machinery |
| task.py | ResourcePredictionTask.execute | machinery | the unit execution with runtime_actions rows, journal.measure and ActionFailure; the unit is a ToolCall |
| task_decision.py | PredictionTaskDecision | episode function | task.py decide and instructions |
| task_decision.py | PredictionTaskDecision.call | machinery | the model call with saved exchanges and session state; ModelRequest |
| task_decision.py | PredictionTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | PredictionTaskDecision.complete_decision | machinery | the model call with recorded exchanges |
| task_decision.py | PredictionTaskDecision.conversation_key | machinery | conversation state |
| task_decision.py | PredictionTaskDecision.interpretation_context | machinery | the exchange lookups (a lookup is a tool) |
| task_decision.py | PredictionTaskDecision.exchange_schema | machinery | the decision-exchange loop |
| task_decision.py | PredictionTaskDecision.exchange_response | machinery | the decision-exchange loop |
| task_decision.py | PredictionTaskDecision.validate_contract_exchange_request | machinery | saved-request checks |
| task_decision.py | PredictionTaskDecision.validate_contract_exchange_history | machinery | saved-request checks |
| task_decision.py | PredictionTaskDecision.exchange_decision | machinery | the decision-exchange loop |
| task_instructions.py | instructions | episode function | task.py instructions |
| task_state.py | PredictionTaskState | machinery | task checkpoint/restore state |
| task_state.py | PredictionTaskState.__init__ | machinery | task checkpoint/restore state |
| task_state.py | PredictionTaskState.bind_execution_context | machinery | execution-binding wiring |
| task_state.py | PredictionTaskState.record_execution_failure | machinery | failure recording through the journal; a tool returns its failure |
| task_state.py | PredictionTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | PredictionTaskState.restore | machinery | restore from runtime_* tables |
| task_state.py | PredictionTaskState.record_effect | machinery | record_effect |
| task_state.py | PredictionTaskState.checkpoint | machinery | checkpoint |
| to_parent.py | PredictionReport | episode function | messages/final_to_parent.py |
| to_parent.py | PredictionReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs, selectable) |
| to_parent.py | PredictionReport.facts | episode function | messages/internal_summary.py facts and messages/final_to_parent.py final_to_parent |
| to_parent.py | PredictionReport.resolve | machinery | the report reference resolver (hpc_model namespace, reference_in_context); the result is admitted by the system |
| to_parent.py | PredictionReport.validate_report | episode function | messages/final_to_parent.py validate_report (validate_form is not built for A102: NotImplementedError) |
| waiting.py | PredictionSuspension | machinery | wait/suspension machinery |
| waiting.py | PredictionSuspension.suspension_changed | machinery | wait/suspension machinery |
| yield_estimator.py | HPCEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (AccumulationYieldController; cost = the binding cutoff) |
| yield_estimator.py | HPCEpisodeYield.continuation_for_action | machinery | the zero-continuation packet is an estimator packet and a stop rule; only the controller stops |
| yield_estimator.py | HPCEpisodeYield.practical_estimator | machinery | HPCContinuationEstimator verifying packets against the ledger; deleted (README 7b) |
