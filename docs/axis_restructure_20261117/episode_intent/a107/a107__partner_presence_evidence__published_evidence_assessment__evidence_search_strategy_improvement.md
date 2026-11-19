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

## Carried over

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3, machinery) |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() (README 3, machinery) |
| configuration.py | LiteratureConfiguration | machinery | old per-binding configuration object; outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py, the settings are the episode settings (cost, parameters, tool_registry) |
| configuration.py | LiteratureConfiguration.__init__ | machinery | old per-binding configuration object; outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py, the settings are the episode settings (cost, parameters, tool_registry) |
| configuration.py | LiteratureConfiguration.reference_evidence | machinery | reference-evidence parent mode applies to role annotation at path length 1 only; not this episode |
| configuration.py | LiteratureConfiguration.contract_information_configuration | machinery | old per-binding configuration object; outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py, the settings are the episode settings (cost, parameters, tool_registry) |
| configuration.py | LiteratureConfiguration.reasoning_action_schema | machinery | old per-binding configuration object; outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py, the settings are the episode settings (cost, parameters, tool_registry) |
| configuration.py | LiteratureConfiguration.reasoning_has_task_content | machinery | old per-binding configuration object; outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py, the settings are the episode settings (cost, parameters, tool_registry) |
| configuration.py | LiteratureConfiguration.execute_reasoning | machinery | old per-binding configuration object; outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py, the settings are the episode settings (cost, parameters, tool_registry) |
| contracts.py | _population_catalog | episode function | NOT PLACED: task.py population_catalog (raises NotImplementedError partner_source_contracts_not_placed) |
| credit.py | LiteratureCredit | episode function | credit.py credit (finding progress; no projector of its own in the old credit, so none copied) |
| credit.py | LiteratureCredit.credit_kind | episode function | credit.py credit (finding progress; no projector of its own in the old credit, so none copied) |
| credit.py | LiteratureCredit.credit_view | episode function | credit.py credit (finding progress; no projector of its own in the old credit, so none copied) |
| credit.py | LiteratureCredit.credit_projector | episode function | credit.py credit (finding progress; no projector of its own in the old credit, so none copied) |
| episode.py | LiteratureEpisode | machinery | old binding class; replaced by episode.py EvidenceSearchStrategyImprovement(EpisodeBinding) |
| episode.py | LiteratureEpisode._role | episode function | task.py (role validation not needed: one binding per episode) |
| episode.py | LiteratureEpisode.permitted_common_actions | machinery | common-action permissions (redeliver_report, wait) of the old runner |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | LiteratureEpisode.child_request_assembler | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | LiteratureEpisode.execution_child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| from_child_source_relevance_assessment.py | receive_report | machinery | receipts bookkeeping, progress notification and runtime_report_attempts; custody of the child return is the system's; read_from_child keeps only the admitted credit, finding and cells |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment.child_assignment_schema | episode function | task.py SEARCH / CHILD_SELECTIONS (the model-supplied search assignment) |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py (form admission); Store scope checks not carried: a wrong commission fails (task.py check_search checks the model answer names held records) |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/msg_to_child.py msg_to_child (builds the child assignment); validation not carried (wrong commission fails) |
| goal.py | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL |
| initial_information.py | initial_information | machinery | old-runner catalog readers (resource information, received API information) |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py internal_summary; task.py render_prompt (component_axis_source_origin/access context NOT PLACED) |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary; task.py render_prompt (component_axis_source_origin/access context NOT PLACED) |
| internal_summary.py | LiteratureSummary.facts | episode function | messages/internal_summary.py own_cells (partner cells; NOT PLACED when sheets exist) |
| internal_summary.py | LiteratureSummary.current_report_facts | episode function | messages/internal_summary.py (report = last report_finding outcome) |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | NOT PLACED: owned population sources read runtime_actions/sqlite_master through store.db; not carried |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | NOT PLACED: owned population sources read runtime_actions/sqlite_master through store.db; not carried |
| internal_summary.py | SourceDecisionSummary | episode function | task.py render_prompt / messages/internal_summary.py (yield_table; generic snapshot parts are old-runner state and not carried) |
| internal_summary.py | SourceDecisionSummary._decision_snapshot | episode function | task.py render_prompt / messages/internal_summary.py (yield_table; generic snapshot parts are old-runner state and not carried) |
| numerical_report_facts.py | LiteratureNumericalReportFacts | episode function | messages/internal_summary.py own_cells (NOT PLACED: partner_source_contracts); messages/final_to_parent.py RETURN_FORM literature_partner_cells |
| numerical_report_facts.py | LiteratureNumericalReportFacts._rate_fact_sources | episode function | messages/internal_summary.py own_cells (NOT PLACED: partner_source_contracts); messages/final_to_parent.py RETURN_FORM literature_partner_cells |
| numerical_report_facts.py | LiteratureNumericalReportFacts._rate_facts | episode function | messages/internal_summary.py own_cells (NOT PLACED: partner_source_contracts); messages/final_to_parent.py RETURN_FORM literature_partner_cells |
| parent_context.py | LiteratureParentContext | episode function | not carried: reference-evidence parent mode (role annotation at path length 1) does not apply; contract information profile is old-runner context |
| parent_context.py | LiteratureParentContext.initial_decision_context | episode function | not carried: reference-evidence parent mode (role annotation at path length 1) does not apply; contract information profile is old-runner context |
| parent_context.py | LiteratureParentContext.contract_information_profile | episode function | not carried: reference-evidence parent mode (role annotation at path length 1) does not apply; contract information profile is old-runner context |
| received_api_reports.py | received_api_reports | machinery | old-runner catalog readers (declared readers of the old runner) |
| received_execution_information.py | received_execution_information | machinery | old-runner catalog readers (declared readers of the old runner) |
| received_reports.py | LiteratureReceivedReports | episode function | messages/final_to_parent.py final_to_parent (cells of the selected field); empty declared arrays when nothing delivered: [] in internal_summary.own_cells |
| received_reports.py | LiteratureReceivedReports.received_report_sources | machinery | received_form_references / evidence tokens: writes cells into the repository on the child-return path and receipts (README 5 item 4); the child holds its sheets and returns sheet_refs |
| received_reports.py | LiteratureReceivedReports.received_report_facts | episode function | messages/final_to_parent.py final_to_parent (cells of the selected field); empty declared arrays when nothing delivered: [] in internal_summary.own_cells |
| received_reports.py | LiteratureReceivedReports._complete_requested_received_arrays | episode function | messages/final_to_parent.py final_to_parent (cells of the selected field); empty declared arrays when nothing delivered: [] in internal_summary.own_cells |
| received_reports.py | LiteratureReceivedReports.received_form_references | machinery | received_form_references / evidence tokens: writes cells into the repository on the child-return path and receipts (README 5 item 4); the child holds its sheets and returns sheet_refs |
| received_reports.py | LiteratureReceivedReports.received_evidence_tokens | machinery | received_form_references / evidence tokens: writes cells into the repository on the child-return path and receipts (README 5 item 4); the child holds its sheets and returns sheet_refs |
| received_reports.py | LiteratureReceivedReports.validate_received_report | episode function | messages/final_to_parent.py validate_report (called by final_to_parent) |
| source_custody.py | LiteratureSourceCustody | episode function | task.py check_search (named records must be held); artifact/page checks not carried (no page in this assignment) |
| source_custody.py | LiteratureSourceCustody._require | episode function | task.py check_search (named records must be held); artifact/page checks not carried (no page in this assignment) |
| source_custody.py | LiteratureSourceCustody._artifact | episode function | not carried: page checks never applied (the assignment names no page) |
| source_custody.py | LiteratureSourceCustody._within_source | episode function | not carried: page checks never applied (the assignment names no page) |
| source_custody.py | LiteratureSourceCustody._validate_page | episode function | not carried: page checks never applied (the assignment names no page) |
| source_operations.py | LiteratureSourceOperations | episode function | task.py tools (TOOLS) and offered_catalog |
| source_operations.py | LiteratureSourceOperations.catalog | episode function | task.py offered_catalog |
| source_operations.py | LiteratureSourceOperations.execute | episode function | task.py run_registry / populate / TOOLS |
| source_operations.py | LiteratureSourceOperations._tool_arguments | episode function | task.py action (decoded arguments) and run_registry |
| source_operations.py | LiteratureSourceOperations._materialize_text_arguments | episode function | task.py materialize_text_arguments |
| source_repositories.py | LiteratureRepositories | episode function | NOT PLACED: LiteraturePartnerRepository / population routes (partner_source_contracts); task.py populate raises NotImplementedError |
| source_repositories.py | LiteratureRepositories.literature_partner_repository | episode function | NOT PLACED: LiteraturePartnerRepository / population routes (partner_source_contracts); task.py populate raises NotImplementedError |
| source_repositories.py | LiteratureRepositories._population_routes | episode function | NOT PLACED: LiteraturePartnerRepository / population routes (partner_source_contracts); task.py populate raises NotImplementedError |
| task.py | SourceInvestigationTask | machinery | old generic next loop (SourceInvestigationTask); replaced by task.py decide/action |
| task.py | SourceInvestigationTask.next | machinery | old generic next loop (SourceInvestigationTask); replaced by task.py decide/action |
| task_action.py | SourceTaskAction | episode function | task.py action, run_registry, TOOLS (admission of an answer); generic reads.map/shared grading retention/decision exchange not carried (old runner) |
| task_action.py | SourceTaskAction.apply_response | episode function | task.py action, run_registry, TOOLS (admission of an answer); generic reads.map/shared grading retention/decision exchange not carried (old runner) |
| task_action.py | SourceTaskAction.execute | episode function | task.py run_registry / TOOLS (tool execution) |
| task_decision.py | SourceTaskDecision | episode function | task.py decide (action_schema, transport) |
| task_decision.py | SourceTaskDecision.call | episode function | task.py decide / render_prompt |
| task_decision.py | SourceTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | SourceTaskDecision.conversation_key | machinery | decision-exchange loop / contract exchange / conversation recording (README 3e) |
| task_decision.py | SourceTaskDecision.interpretation_context | episode function | task.py decide / render_prompt |
| task_decision.py | SourceTaskDecision.exchange_schema | machinery | decision-exchange loop / contract exchange / conversation recording (README 3e) |
| task_decision.py | SourceTaskDecision.exchange_response | machinery | decision-exchange loop / contract exchange / conversation recording (README 3e) |
| task_decision.py | SourceTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop / contract exchange / conversation recording (README 3e) |
| task_decision.py | SourceTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop / contract exchange / conversation recording (README 3e) |
| task_decision.py | SourceTaskDecision.exchange_decision | machinery | decision-exchange loop / contract exchange / conversation recording (README 3e) |
| task_decision.py | SourceTaskDecision.decision_completion | machinery | decision-exchange loop / contract exchange / conversation recording (README 3e) |
| task_instructions.py | instructions | episode function | task.py instructions |
| task_presentation.py | present_source_context | episode function | task.py render_prompt |
| task_reading_prompt.py | render_literature_experimental_prompt | episode function | task.py render_prompt (fixed paragraphs of literature_source_presentation NOT PLACED) |
| task_report_delivery.py | SourceTaskReportDelivery | machinery | report_form machinery (form_with_facts, release, pending handles); replaced by final_to_parent |
| task_report_delivery.py | SourceTaskReportDelivery.finish | machinery | report_form machinery (form_with_facts, release, pending handles); replaced by final_to_parent |
| task_state.py | SourceTaskState | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_state.py | SourceTaskState.__init__ | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_state.py | SourceTaskState.bind_execution_context | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_state.py | SourceTaskState.record_execution_failure | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_state.py | SourceTaskState.restore_checkpoint | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_state.py | SourceTaskState.restore | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_state.py | SourceTaskState.record_effect | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_state.py | SourceTaskState.checkpoint | machinery | old runner state: checkpoint/restore, recorded effects, execution-failure recording (README 3e) |
| task_suspension.py | SourceTaskSuspension | machinery | wait/suspension machinery (old execution backend) |
| task_suspension.py | SourceTaskSuspension.suspension_changed | machinery | wait/suspension machinery (old execution backend) |
| to_child_source_relevance_assessment.py | assemble_request | episode function | messages/msg_to_child.py msg_to_child (Episode.identity, receipts.bind, knowledge_inheritance are old runner and not carried) |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py RETURN_FORM / final_to_parent |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM literature_partner_cells, sheet_refs |
| to_parent.py | LiteratureReport.resolve | machinery | reference resolution through the old runner; custody is the system's |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| waiting.py | LiteratureWaiting | machinery | wait machinery: supports_wait=False, no wait tool in this episode |
| waiting.py | LiteratureWaiting.supports_wait | machinery | wait machinery: supports_wait=False, no wait tool in this episode |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py yield_controller (AccumulationYieldController) |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | yield_estimator.py yield_controller (AccumulationYieldController) |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller (AccumulationYieldController) |
