# a107/partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/<file>`
(only files directly in this folder; no `grading/`/`scoring/` folder; the child folder
`source_relevance_assessment/` is covered separately).
Old binding class: `LiteratureEpisode` (`binding_path =
'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement'`,
`commissioning_parent = 'partner_presence_evidence/published_evidence_assessment'`, `roles = ('literature_strategy',)`,
`entry_roles = ()`), decision source `SourceInvestigationTask`, prompt renderer `present_source_context`, contract
version `literature_episode_binding_v1`.

## What it is for (its goal, in its own words)

`goal.py` = `_ROLE_INSTRUCTIONS['literature_strategy']` + the A107 partner text:

> Investigate which search approach is productive. Keep the information objective and evidence context separate
> from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search
> child can investigate which returned sources deserve examination.
> Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and
> partner roles, normalization, nonpartner conditions, physical measurement identity, source units and
> uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target
> correspondence or annotation credit. A search or read earns no scientific credit by itself.

## Task and instructions

Same composition and prompt as its parent `published_evidence_assessment` (generic `INSTRUCTIONS` + goal text +
knowledge / launch / redelivery / native-event / exchange texts; literature experimental TASK/STEERING prompt via
`task_reading_prompt.py`, text-identical to the parent's).

## What it reads from its parent's assignment

`from_parent.py`: `strategy_assignment_v1` with `question_context_refs` and `prior_search_refs` plus the partner
source contract fields; every `*_refs` reference must be in scope (prior searches in the `source` namespace).
`parent_context.py` (reference-evidence parent mode) is present but only applies to role `annotation` at path
length 1, so it does not apply to this role.

## Children

One child role, `literature_search` (the `source_relevance_assessment` episode):
- sends (`to_child_source_relevance_assessment.py`, text-identical to the parent's to_child file): child goal
  refining this goal, scope, initial report, completion order, report contract declaration, job / episode
  assignment, `partner_presence_evidence` payload, knowledge-inheritance receipts;
- takes back (`from_child_source_relevance_assessment.py`, text-identical to the parent's from_child file): the
  typed form, partner cells received into the repository, references, timing receipts, tool attributions.

## Decision state and what it shows the model

As the parent: `literature_assignment` (here the strategy assignment), source custody of `source_refs` if any
(a strategy assignment has `prior_search_refs`, so custody is normally empty), own literature outcomes page, history
meaning, experimental-work marker, owned population sources, last failed population attempt, component axis
source origin/access, plus the old generic snapshot.

## Tools it offers

Same catalog as the parent (access tools, literature/NCBI/PMC acquisition, partner population operations; pubmed
only; xlsx-only estimates); assignment validated as `literature_strategy`.

## How its credit is counted

Credit kind `scientific`, `services.scientific_credit(context, selection)`; searches and reads earn nothing by
themselves.

## Continuation (yield estimator, settings)

None of its own (`yield_controller` returns None; `supports_wait = False`).

## What it reports to its parent

Partner rate facts and received partner cells, exactly as the parent (`to_parent.py`, `numerical_report_facts.py`,
`received_reports.py` text-identical).

## Differences from similar episodes

- Versus its parent `published_evidence_assessment`: role `literature_strategy`, not an entry role, assignment
  `strategy_assignment_v1`/`prior_search_refs`, strategy role instruction, child `literature_search`, no
  `create_binding_tree`, its own binding id in `binding_record.py`, `initial_information.py`,
  `received_api_reports.py`, `received_execution_information.py`, and the validated role name in `internal_summary.py` and `source_operations.py`. All other files are text-identical copies
  (intended copies under the private-binding rule).
- Its role instruction alone says to separate the information objective from a literal provider query and to revise
  search terms/sources from actual outcomes; that is the episode's distinct intent.

## Files

| old file | lines | this episode's own intent | old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `binding_record.py` | 13 | binding id `partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement`, version `literature_episode_binding_v1`; same configuration fields as its parent | none |
| `configuration.py` | 35 | constructor: `outcome_page_size` (positive int, default 8), optional unique `reference_parent_sources`, optional contract information profile (only CONTRACT_INFORMATION_PROFILE); `reference_evidence(...)` constructor for parent-source mode; no reasoning schema / reasoning execution of its own | none |
| `contracts.py` | 39 | VERSION, the seven literature ROLES and their child map, assignment/page/table/window schemas, tool name sets (access, acquisition, read), `_ROLE_INSTRUCTIONS` per role, `_population_catalog()` (partner source population operations) | `import:communication`, `import:composition_information`, `import:episode_bindings` |
| `credit.py` | 16 | credit kind `scientific`; `credit_view` = `services.scientific_credit(context, selection)`; no projector | none |
| `episode.py` | 65 | `LiteratureEpisode`: binding_path `.../published_evidence_assessment/evidence_search_strategy_improvement`, commissioning_parent `partner_presence_evidence/published_evidence_assessment`, roles `('literature_strategy',)`, no entry roles, actions tool/child/redeliver_report, one child role `literature_search`; no `create_binding_tree` | none |
| `from_child_source_relevance_assessment.py` | 44 | `receive_report` for child `literature_search` (text identical to the parent's from_child file) | `binding_context` (4), `import:delivery_counterpart`, `import:episode_return_records`, `import:runtime`, `param:workflow.binding_context` (4), `param:workflow.episode_bindings`, `param:workflow.job_episodes` (2), `param:workflow.native_timing_information`, `param:workflow.progress_provider` (4), `param:workflow.receipts` (3), `param:workflow.receive_tool_attributions`, `param:workflow.run_id` (6), `param:workflow.specialist`, `param:workflow.store` (7), `runtime._json`, `runtime.json`, `runtime._references_in`, `runtime.WorkflowError`, `table:runtime_report_attempts` (2) |
| `from_parent.py` | 35 | assignment `strategy_assignment_v1`: question_context_refs + `prior_search_refs` (+ partner source contract fields); validated as role `literature_strategy` | none |
| `goal.py` | 9 | instructions = `_ROLE_INSTRUCTIONS['literature_strategy']` + the same partner removal/addback/coexpression text | none |
| `initial_information.py` | 9 | resource information and received API information from this binding's declared readers | none |
| `internal_summary.py` | 133 | decision context: assignment, source custody, own literature outcomes page (acquisition+read tools), history meaning, `literature_experimental_work` marker, owned population sources (read-only metadata classification), last failed population attempt, component axis source origin and access; facts = partner rate facts; plus old SourceDecisionSummary snapshot | `binding_context`, `import:runtime`, `param:workflow.run_id` (2), `param:workflow.store` (2), `runtime.FACT_MEANINGS`, `runtime.FACT_SOURCES`, `runtime.json` (2), `runtime.Mapping` (3), `runtime._plain` (2), `runtime._references_in`, `self.workflow.action_schema`, `self.workflow.annotation_context`, `self.workflow.binding_context`, `self.workflow.catalog`, `self.workflow.controller_binding`, `self.workflow.delivery_resolution_inputs`, `self.workflow.delivery_status`, `self.workflow.extra_report_sources`, `self.workflow.is_scientific_source`, `self.workflow.job_episode_options`, `self.workflow.journal` (3), `self.workflow.knowledge`, `self.workflow.local_outcome_preview`, `self.workflow.pending_work`, `self.workflow.receipt_projection`, `self.workflow.run_id`, `self.workflow.source_credit_binding`, `self.workflow.source_credit_view`, `self.workflow.specialist`, `self.workflow.store` (3), `self.workflow.tools`, `self.workflow.working_state`, `services.workflow` (3), `table:runtime_actions` (4) |
| `numerical_report_facts.py` | 31 | `_rate_facts`: partner population fact cells from received source records of each route's provider (version must match), components from assignment or defaults; includes current sheet refs | `services.workflow.store` |
| `parent_context.py` | 21 | `initial_decision_context` for reference-evidence parent mode (role annotation at path length 1): parent source custody and child population operations; contract information profile for literature roles | none |
| `received_api_reports.py` | 4 | selects API reports declared for this binding path | none |
| `received_execution_information.py` | 4 | selects execution readers declared for this binding path | none |
| `received_reports.py` | 71 | received partner cells per population route, empty declared arrays when nothing delivered (not a zero or absence), receive cells into repository, evidence tokens, received report validation (sheet refs permitted, empty family validation, requested components only) | `import:method_loop.durable`, `services.workflow.store` |
| `source_custody.py` | 39 | `_require` reference in scope, artifact by representation, `_within_source` ancestry, page validation | none |
| `source_operations.py` | 96 | tool catalog = allowed access+acquisition tools (NCBI search restricted to pubmed, execution.estimate only for xlsx) + partner population operations; execute: argument errors -> invalid outcome; `literature.partner.populate`/`.source.populate` populate the partner sheet from materialized text witnesses; page assignments confine reads to the assigned source | `getattr(services,workflow)` (2), `import:composition_information` |
| `source_repositories.py` | 15 | LiteraturePartnerRepository (per run) and population routes | `services.workflow.run_id`, `services.workflow.store` |
| `task.py` | 84 | `SourceInvestigationTask`: old generic next loop | `import:episode_source_failure`, `import:providers`, `import:runtime`, `runtime.json` (4), `runtime.nullcontext`, `runtime.SourceEnd` (2), `runtime.WorkflowError`, `self.workflow.completed_unit` (3), `self.workflow.completions` (2), `self.workflow.execution_binding` (2), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (4), `self.workflow.next_return`, `self.workflow.resolve_pending_deliveries`, `self.workflow.run_id`, `self.workflow.selected` (2), `self.workflow.store` (3), `table:runtime_actions` (2), `table:runtime_episodes`, `table:runtime_model_calls` |
| `task_action.py` | 136 | old generic apply_response/execute (reason/tool, reads.map feedback, shared grading retention) | `binding_context`, `import:runtime`, `runtime.AcquisitionError` (2), `runtime.ActionFailure`, `runtime.ContractError`, `runtime.ContractInformationError`, `runtime._decode_recorded_action_response`, `runtime.Draft202012Validator` (3), `runtime.EventTargetError`, `runtime.inspect`, `runtime._json` (5), `runtime.json` (4), `runtime.Mapping` (3), `runtime.nullcontext` (4), `runtime.observes_action_outcome`, `runtime.ReportBoundaryError`, `runtime.ReportRedelivery` (2), `runtime.schema_failure_diagnostic`, `runtime.sqlite3` (2), `runtime.subprocess` (2), `runtime.validate_form`, `runtime.ValidationError` (3), `runtime._wait_target_feedback`, `runtime.WorkflowError`, `self.workflow.automatic_score_updates`, `self.workflow.binding_context`, `self.workflow.completions`, `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.execute`, `self.workflow.execution_binding` (5), `self.workflow.journal` (3), `self.workflow.last_observed_credit`, `self.workflow.pending_work`, `self.workflow.permits_common_action`, `self.workflow.reasoning_action_schema`, `self.workflow.receive_native_outcome`, `self.workflow.receive_outcome`, `self.workflow.resolver`, `self.workflow.retain_shared_grading_results`, `self.workflow.run_id`, `self.workflow.selected`, `self.workflow.source_credit_view`, `self.workflow.specialist`, `self.workflow.store` (5), `self.workflow.validate_report`, `table:runtime_actions` (6), `table:runtime_model_calls` |
| `task_decision.py` | 351 | old generic model call / decision exchange protocol | `binding_context`, `import:episode_work_report`, `import:providers`, `import:runtime`, `runtime._action_generation_schema` (2), `runtime.apply_state_frame`, `runtime._ASSIGNMENT_TRANSPORT`, `runtime._category_yield_parameters`, `runtime.child_option_information` (2), `runtime.composition_lookup_schema` (2), `runtime.CONTRACT_INFORMATION_OPERATIONS`, `runtime.DECISION_CONTEXT_VERSION` (2), `runtime.DECISION_EXCHANGE_PROTOCOL` (5), `runtime._digest`, `runtime.Draft202012Validator`, `runtime.infernal_receiver_context` (2), `runtime.instructional_model_context` (4), `runtime.is_contract_information`, `runtime._json` (14), `runtime.json` (3), `runtime.lookup_attempts`, `runtime.Mapping` (4), `runtime.model_snapshot` (2), `runtime._object` (3), `runtime._plain` (2), `runtime._recorded_action_generation_schema`, `runtime._recorded_assignment_transport`, `runtime._references_in`, `runtime.requested_contract_information` (2), `runtime.schema_failure_diagnostic` (2), `runtime.sqlite3`, `runtime.state_frame`, `runtime.ValidationError` (5), `runtime.WorkflowError` (14), `runtime.yield_table`, `self.workflow.available_child_roles`, `self.workflow.binding_context`, `self.workflow.contract_information_profile`, `self.workflow.contract_information_reply`, `self.workflow.controller_binding`, `self.workflow.decision_exchanges` (4), `self.workflow.decision_protocol` (3), `self.workflow.episode_bindings`, `self.workflow.execute`, `self.workflow.execution_expectations`, `self.workflow.freeze_contract_information`, `self.workflow.freeze_literature_numerical_contracts`, `self.workflow.history_preview`, `self.workflow.journal` (3), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context`, `self.workflow.numerical_contracts`, `self.workflow.pending_work`, `self.workflow.permits_common_action`, `self.workflow.provider` (3), `self.workflow.receipts` (4), `self.workflow.resource_context`, `self.workflow.resource_estimator` (4), `self.workflow.run_id`, `self.workflow.services` (2), `self.workflow.shared_information_context`, `self.workflow.specialist`, `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (5), `self.workflow.waiting_support`, `table:runtime_model_calls` (8) |
| `task_instructions.py` | 25 | generic INSTRUCTIONS + binding instructions + reason/knowledge/launch/redelivery/wait/native-event/exchange texts | `binding_context`, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL`, `runtime_prompt.INSTRUCTIONS` (4), `runtime_prompt.REASONING_COMMIT_REQUIREMENT`, `self.workflow.binding_context`, `self.workflow.decision_protocol`, `self.workflow.knowledge`, `self.workflow.launch_instructions`, `self.workflow.native_event_information`, `self.workflow.permits_common_action` (3), `self.workflow.specialist` |
| `task_presentation.py` | 48 | `present_source_context`: renders the literature experimental TASK prompt from reconstructed frames, else JSON | `import:decision_context` |
| `task_reading_prompt.py` | 37 | `render_literature_experimental_prompt`: TASK sections (assigned question/scope, assignment and source operands, parent source, representations, material, selected operations, permitted narrower investigations, requested information and return meanings, timing) and STEERING (byte-range witnesses, preserve observed subject and unresolved target correspondence, source inspections, action yields, continuation, pending delivery, findings, child reports, results, last outcome) | none |
| `task_report_delivery.py` | 23 | `finish`: rootless credit+pending or saved/filled form | `binding_context`, `import:runtime`, `runtime.form_with_facts`, `runtime._json` (2), `runtime.json`, `runtime.Record` (2), `self.workflow.binding_context`, `self.workflow.episode_bindings`, `self.workflow.facts`, `self.workflow.journal` (2), `self.workflow.pending_handles`, `self.workflow.release` (2), `self.workflow.source_credit_view`, `table:runtime_forms` (2) |
| `task_state.py` | 108 | old generic source state | `import:episode_source_failure`, `import:runtime`, `param:workflow.context`, `param:workflow.grains`, `runtime.ActionLeaf`, `runtime.EFFECT_VERSION`, `runtime.Episode`, `runtime.interpretation_schema`, `runtime._json` (2), `runtime.json` (4), `runtime._object`, `runtime._plain`, `runtime.Record`, `self.workflow.archive`, `self.workflow.completions` (4), `self.workflow.controller_value`, `self.workflow.execution_binding` (4), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions`, `self.workflow.run_id`, `self.workflow.source_credit_view`, `self.workflow.store` (2), `table:runtime_actions` (5) |
| `task_suspension.py` | 9 | `suspension_changed` on old execution backend | `self.workflow.execution_backend`, `self.workflow.execution_handle` (2) |
| `to_child_source_relevance_assessment.py` | 28 | `assemble_request` for child `literature_search` (text identical to the parent's to_child file) | `import:runtime`, `param:workflow.context` (2), `param:workflow.grains` (2), `param:workflow.inprocess_completion_order` (2), `param:workflow.launch_instructions`, `param:workflow.receipts` (2), `runtime.ContractInformationError`, `runtime.Episode` (2), `runtime.EpisodeGoal` (2), `runtime.EpisodeRequest`, `runtime._plain` (3), `runtime.Record`, `runtime.validate_saved_fact_form` |
| `to_parent.py` | 18 | fact sources = partner rate fact sources; resolve; validate_report = assignment + form + received report validation | none |
| `waiting.py` | 8 | `supports_wait = False` | none |
| `yield_estimator.py` | 12 | no continuation task and `yield_controller` returns None (no private yield binding) | none |
