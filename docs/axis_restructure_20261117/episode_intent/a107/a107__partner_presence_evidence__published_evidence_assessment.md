# a107/partner_presence_evidence/published_evidence_assessment — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/published_evidence_assessment/<file>`
(only files directly in this folder; no `grading/`/`scoring/` folder; the child folder
`evidence_search_strategy_improvement/` is covered separately).
Old binding class: `LiteratureEpisode` (`binding_path = 'partner_presence_evidence/published_evidence_assessment'`,
`commissioning_parent = 'partner_presence_evidence'`, `roles = entry_roles = ('literature',)`), decision source
`SourceInvestigationTask`, prompt renderer `present_source_context`, contract version
`literature_episode_binding_v1`.

## What it is for (its goal, in its own words)

`goal.py` = `_ROLE_INSTRUCTIONS['literature']` + A107 text:

> Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches
> and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.
> Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and
> partner roles, normalization, nonpartner conditions, physical measurement identity, source units and
> uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target
> correspondence or annotation credit. A search or read earns no scientific credit by itself.

`contracts.py` docstring: the binding supplies operands, operations and source custody; "a reading selection is
information for an investigation, never a script that this binding executes."

## Task and instructions

`task_instructions.py`: generic `INSTRUCTIONS` + the goal text above (not replacing), + reasoning-commit
requirement if `reason` is permitted (it is not: actions are tool/child/redeliver_report), + tool knowledge, launch
instruction library, pending-child redelivery text, wait text (not permitted), native event text, decision-exchange
history replacement.
Prompt: `task_presentation.py` renders `render_literature_experimental_prompt` when the context carries
`literature_experimental_work` (`literature_experimental_task_v1`): TASK (lead for the selected family or
`A107_source`, source availability, source scope, component reading task, instructions, fact-contract task under
the contract profile, assigned question, scope, parent assignment and source operands, assigned source parent,
representations, supplied material, selected operations, permitted narrower investigations, requested information,
return meanings, return timing) and STEERING ("Select the received source_ref, artifact_ref and zero-based
half-open UTF-8 byte range for text witnesses. Preserve the exact observed subject, source meaning and unresolved
target correspondence.", source inspections, own action yields, continuation expectation, pending child delivery,
current findings, child reports, operation results, last outcome).

## What it reads from its parent's assignment

`from_parent.py`: `literature_assignment_v1` with `question_context_refs` and `source_refs` (both unique reference
arrays) plus the partner source contract fields from `partner_source_contracts.assignment_schema_fields()`. Every
`*_refs` reference must be in scope (`source` namespace except question context). In reference-evidence parent
mode (`reference_parent_sources` configured; role `annotation` at path length 1) `parent_context.py` adds the parent
source custody and the child population operations to the initial decision context.

## Children

One child role, `literature_strategy` (the `evidence_search_strategy_improvement` episode):
- sends (`to_child_evidence_search_strategy_improvement.py` `assemble_request`): a child goal refining this goal
  (objective text chosen by the model, result contract = the declared report schema), message with scope, initial
  report, optional in-process completion order, validated report contract declaration, job / episode assignment
  (launch instructions materialized), `partner_presence_evidence` payload, and knowledge-inheritance receipts; the
  child assignment is `strategy_assignment_v1` (`question_context_refs`, `prior_search_refs`).
- takes back (`from_child_evidence_search_strategy_improvement.py` `receive_report`): the typed form; it is
  forwarded to the progress provider, its references collected (`_references_in` + own
  `received_form_references`, which stores delivered partner cells in the repository and returns current sheet
  refs), native timing receipts added, receipts and tool attributions recorded.
`create_binding_tree(services, **configuration)` builds this binding and its six literature descendants (strategy,
search, page, table, coverage, passage) from one configuration.

## Decision state and what it shows the model

`internal_summary.py` `decision_context`: `literature_assignment`, `literature_source_custody` (per source:
version, artifact/text/stdout/stderr refs, parent sources), `own_literature_outcomes` (own outcomes of
acquisition+read tools, page size `outcome_page_size`), `literature_history_meaning` ("Own outcome metadata only.
Inspect original source records and exact prior operations before interpreting them."),
`literature_experimental_work` marker, `literature_owned_population_sources` (read-only classification of own
completed population outputs), `literature_selected_population_attempt` (latest failed/invalid population tool),
`component_axis_source_origin`, `component_axis_source_access`. Plus the old generic snapshot (with annotation
context for scientific sources and `_completed_work_axis_results` from the credit view: `a107_sheet`,
`target_sheets`, tool attachments, source contributions).

## Tools it offers

`source_operations.py`: from the service catalog only `state.query`, `source.read`, `source.locate`,
`source.sequence.scan`, `source.sequence.references`, `source.experimental.records`, `image.view`,
`source.archive.members`/`extract`, `source.xlsx.sheets`/`rows`, `source.pdf.info`/`text`/`page`,
`execution.estimate` (only its xlsx branches), and acquisition `public.literature.search`/`read`/
`sequence_identity`, `public.ncbi.search` (database restricted to `pubmed`), `public.pmc.versions`/`files`/`asset`;
plus the partner population operations (`literature.partner.populate`, `literature.partner.source.populate`) from
the population catalog (argument transport under the contract profile). Population operations materialize text
witnesses from source reads and populate the partner sheet. Argument errors are returned as `invalid` outcomes.
Page assignments confine every read to the assigned source and its descendants.

## How its credit is counted

Credit kind `scientific`; `credit_view` delegates to `services.scientific_credit(context, receiver_selection)`
(the axis's scientific credit over the partner sheet), no projector. A search or read earns nothing by itself.

## Continuation (yield estimator, settings)

`yield_estimator.py`: `continuation_task` None and `yield_controller` None — no private yield binding; continuation
was whatever the runner's default controller binding supplied. `waiting.py`: `supports_wait = False`.

## What it reports to its parent

`to_parent.py`: fact sources = partner rate fact sources (`partner_source_contracts.fact_sources()`); facts
(`numerical_report_facts.py`) = per population route, the fact cells of received source records of that route's
provider and version, components from the assignment or defaults, including current sheet refs.
`validate_report`: assignment valid, form valid with reference resolution, and `validate_received_report` (cell
sheet refs permitted, empty families validated, only requested components). Received reports
(`received_reports.py`) return declared arrays empty when no cells were delivered ("does not report an unavailable
numerical component as zero, infer a biological absence ...").

## Differences from similar episodes

- Text-identical to its child `evidence_search_strategy_improvement` in 21 of 30 shared files; differs in role
  (`literature` vs `literature_strategy`), assignment (`literature_assignment_v1`/`source_refs` vs
  `strategy_assignment_v1`/`prior_search_refs`), role instruction, binding path, child role and child message
  files, and it alone is an entry role and owns `create_binding_tree`.
- Unlike the HPC episodes: scientific credit, has a child, no private yield controller, no wait.

## Files

| old file | lines | this episode's own intent | old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `binding_record.py` | 13 | binding id `partner_presence_evidence/published_evidence_assessment`, version `literature_episode_binding_v1`; configuration outcome_page_size, reference_parent_sources, contract_information_profile | none |
| `configuration.py` | 35 | constructor: `outcome_page_size` (positive int, default 8), optional unique `reference_parent_sources`, optional contract information profile (only CONTRACT_INFORMATION_PROFILE); `reference_evidence(...)` constructor for parent-source mode; no reasoning schema / reasoning execution of its own | none |
| `contracts.py` | 39 | VERSION, the seven literature ROLES and their child map, assignment/page/table/window schemas, tool name sets (access, acquisition, read), `_ROLE_INSTRUCTIONS` per role, `_population_catalog()` (partner source population operations) | `import:communication`, `import:composition_information`, `import:episode_bindings` |
| `credit.py` | 16 | credit kind `scientific`; `credit_view` = `services.scientific_credit(context, selection)`; no projector | none |
| `episode.py` | 76 | `LiteratureEpisode`: binding_path `partner_presence_evidence/published_evidence_assessment`, commissioning_parent `partner_presence_evidence`, roles = entry_roles = `('literature',)`, actions tool/child/redeliver_report, one child role `literature_strategy`, decision source SourceInvestigationTask, renderer `present_source_context`; `create_binding_tree` builds this and its six descendant literature bindings from one configuration | none |
| `from_child_evidence_search_strategy_improvement.py` | 44 | `receive_report` for child `literature_strategy`: recorded admission references, progress-provider forwarding, receipt references, own `received_form_references` (partner cells), native timing receipts, receipts and tool attributions | `binding_context` (4), `import:delivery_counterpart`, `import:episode_return_records`, `import:runtime`, `param:workflow.binding_context` (4), `param:workflow.episode_bindings`, `param:workflow.job_episodes` (2), `param:workflow.native_timing_information`, `param:workflow.progress_provider` (4), `param:workflow.receipts` (3), `param:workflow.receive_tool_attributions`, `param:workflow.run_id` (6), `param:workflow.specialist`, `param:workflow.store` (7), `runtime._json`, `runtime.json`, `runtime._references_in`, `runtime.WorkflowError`, `table:runtime_report_attempts` (2) |
| `from_parent.py` | 35 | assignment `literature_assignment_v1`: question_context_refs + source_refs (+ partner source contract fields); every ref must be in scope (source namespace) | none |
| `goal.py` | 9 | instructions = `_ROLE_INSTRUCTIONS['literature']` + partner removal/addback/coexpression text | none |
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
| `to_child_evidence_search_strategy_improvement.py` | 28 | `assemble_request` for child `literature_strategy`: child goal from parent goal, message (scope, initial report, completion order, report contract declaration, job/episode assignment, `partner_presence_evidence`), receipts knowledge inheritance | `import:runtime`, `param:workflow.context` (2), `param:workflow.grains` (2), `param:workflow.inprocess_completion_order` (2), `param:workflow.launch_instructions`, `param:workflow.receipts` (2), `runtime.ContractInformationError`, `runtime.Episode` (2), `runtime.EpisodeGoal` (2), `runtime.EpisodeRequest`, `runtime._plain` (3), `runtime.Record`, `runtime.validate_saved_fact_form` |
| `to_parent.py` | 18 | fact sources = partner rate fact sources; resolve; validate_report = assignment + form + received report validation | none |
| `waiting.py` | 8 | `supports_wait = False` | none |
| `yield_estimator.py` | 12 | no continuation task and `yield_controller` returns None (no private yield binding) | none |

## Carried over

Old files at `97308b94c`, one row per row of `runs/carry_over/functions/a107__partner_presence_evidence__published_evidence_assessment.tsv`. "library candidate": none; every episode function lives in this episode's own files. No file was added to `episode_support/`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding record and the binding's own as_record() are deleted (system records settings and services) |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding record and the binding's own as_record() are deleted (system records settings and services) |
| configuration.py | LiteratureConfiguration | machinery | configuration class; its values are settings (ctx.settings) and constants of the files that use them |
| configuration.py | LiteratureConfiguration.__init__ | machinery | constructor values: outcome_page_size is the constant OUTCOME_PAGE_SIZE in messages/internal_summary.py; reference_parent_sources and contract_information_profile are not carried (no source names them; reference-evidence parent mode is the head's); services are declared in task.py SERVICES |
| configuration.py | LiteratureConfiguration.reference_evidence | machinery | constructor for reference-parent-source mode (old runner configuration); not carried |
| configuration.py | LiteratureConfiguration.contract_information_configuration | machinery | contract_information profile / reasoning schema / reasoning execution hooks: this episode has no reason action (old reasoning_* returned None/False); contract information is old-runner machinery |
| configuration.py | LiteratureConfiguration.reasoning_action_schema | machinery | contract_information profile / reasoning schema / reasoning execution hooks: this episode has no reason action (old reasoning_* returned None/False); contract information is old-runner machinery |
| configuration.py | LiteratureConfiguration.reasoning_has_task_content | machinery | contract_information profile / reasoning schema / reasoning execution hooks: this episode has no reason action (old reasoning_* returned None/False); contract information is old-runner machinery |
| configuration.py | LiteratureConfiguration.execute_reasoning | machinery | contract_information profile / reasoning schema / reasoning execution hooks: this episode has no reason action (old reasoning_* returned None/False); contract information is old-runner machinery |
| contracts.py | _population_catalog | episode function | task.py: population_catalog (raises NotImplementedError partner_source_contracts_not_placed) and offered_catalog |
| credit.py | LiteratureCredit | machinery | credit_kind / credit_projector (kind scientific, no projector) are deleted; the credit is credit.py credit |
| credit.py | LiteratureCredit.credit_kind | machinery | credit_kind / credit_projector (kind scientific, no projector) are deleted; the credit is credit.py credit |
| credit.py | LiteratureCredit.credit_view | episode function | credit.py: credit (finding progress of held assessments via library project_finding_progress; replaces services.scientific_credit) |
| credit.py | LiteratureCredit.credit_projector | machinery | credit_kind / credit_projector (kind scientific, no projector) are deleted; the credit is credit.py credit |
| episode.py | LiteratureEpisode | episode function | episode.py: PublishedEvidenceAssessment(EpisodeBinding) |
| episode.py | LiteratureEpisode._role | machinery | role check: each role is its own episode (single role literature) |
| episode.py | LiteratureEpisode.permitted_common_actions | episode function | task.py: action_schema offers tool and child; redeliver_report is not carried (README 3b R2) |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py: CHILD_SLOTS = {literature_strategy: ...evidence_search_strategy_improvement} |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py: CHILD_SLOTS = {literature_strategy: ...evidence_search_strategy_improvement} |
| episode.py | LiteratureEpisode.child_request_assembler | episode function | messages/msg_to_child.py: msg_to_child |
| episode.py | LiteratureEpisode.execution_child_report_receiver | episode function | messages/read_from_child.py: read_from_child |
| episode.py | create_binding_tree | machinery | create_binding_tree: home/tree factory deleted; the registry is built by the caller of link |
| from_child_evidence_search_strategy_improvement.py | receive_report | episode function | messages/read_from_child.py: read_from_child (credit, finding, partner cells, sheet refs); recorded admission, progress-provider forwarding, receipts, tool attributions, timing receipts and the repository write of received cells are machinery / README section 5 item 4 |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment.child_assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM (the schema); the in-scope checks against the Store are checks of a commission and are not carried (a wrong commission fails) |
| from_parent.py | LiteratureAssignment.prepare_assignment | machinery | child-side preparation of a commission; the admission of the assignment is the system's (ASSIGNMENT_FORM) |
| goal.py | LiteratureGoal | episode function | goal.py: GOAL (role sentence plus A107 sentences) |
| goal.py | LiteratureGoal.instructions | episode function | goal.py: GOAL (role sentence plus A107 sentences) |
| initial_information.py | initial_information | machinery | old-runner catalog readers (resource and received API information); unplaced, listed in unplaced_old_functions |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py: internal_summary |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py: internal_summary (source_custody, own_literature_outcomes, literature_history_meaning); the literature_assignment is the parent input in the summary |
| internal_summary.py | LiteratureSummary.facts | episode function | messages/internal_summary.py: own_cells / cells and sheet_refs; messages/final_to_parent.py: final_to_parent (partner cells) |
| internal_summary.py | LiteratureSummary.current_report_facts | episode function | messages/internal_summary.py: own_cells / cells and sheet_refs; messages/final_to_parent.py: final_to_parent (partner cells) |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | UNPLACED: helper module has no placement and reads old-runner tables; context keys not carried (unplaced_old_functions) |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | UNPLACED: helper module has no placement and reads old-runner tables; context keys not carried (unplaced_old_functions) |
| internal_summary.py | SourceDecisionSummary | episode function | messages/internal_summary.py: internal_summary |
| internal_summary.py | SourceDecisionSummary._decision_snapshot | episode function | messages/internal_summary.py: internal_summary (outcomes, child reports, yield_table, report); old working-state/annotation-context/pending-work parts are old runner |
| numerical_report_facts.py | LiteratureNumericalReportFacts | episode function | UNPLACED: messages/internal_summary.py own_cells raises NotImplementedError partner_source_contracts_not_placed:fact_cells_over_held_sheets when a sheet is held |
| numerical_report_facts.py | LiteratureNumericalReportFacts._rate_fact_sources | episode function | UNPLACED: messages/internal_summary.py own_cells raises NotImplementedError partner_source_contracts_not_placed:fact_cells_over_held_sheets when a sheet is held |
| numerical_report_facts.py | LiteratureNumericalReportFacts._rate_facts | episode function | UNPLACED: messages/internal_summary.py own_cells raises NotImplementedError partner_source_contracts_not_placed:fact_cells_over_held_sheets when a sheet is held |
| parent_context.py | LiteratureParentContext | machinery | contract information profile is old-runner contract-information machinery |
| parent_context.py | LiteratureParentContext.initial_decision_context | machinery | reference-evidence parent mode context (role annotation, path length 1) belongs to the head; not carried here |
| parent_context.py | LiteratureParentContext.contract_information_profile | machinery | contract information profile is old-runner contract-information machinery |
| received_api_reports.py | received_api_reports | machinery | old-runner catalog readers; unplaced (unplaced_old_functions) |
| received_execution_information.py | received_execution_information | machinery | old-runner catalog readers; unplaced (unplaced_old_functions) |
| received_reports.py | LiteratureReceivedReports | episode function | messages/internal_summary.py: own_cells / cells (declared arrays empty when nothing delivered) |
| received_reports.py | LiteratureReceivedReports.received_report_sources | episode function | messages/internal_summary.py: own_cells / cells (declared arrays empty when nothing delivered) |
| received_reports.py | LiteratureReceivedReports.received_report_facts | episode function | messages/internal_summary.py: own_cells / cells (declared arrays empty when nothing delivered) |
| received_reports.py | LiteratureReceivedReports._complete_requested_received_arrays | episode function | messages/internal_summary.py: own_cells / cells (declared arrays empty when nothing delivered) |
| received_reports.py | LiteratureReceivedReports.received_form_references | machinery | a write on the child-return path (README section 5 item 4): the child holds its sheets and returns sheet_refs |
| received_reports.py | LiteratureReceivedReports.received_evidence_tokens | machinery | receipt/evidence tokens of the old runner |
| received_reports.py | LiteratureReceivedReports.validate_received_report | episode function | messages/final_to_parent.py: validate_report (sheet refs known, requested components only) |
| source_custody.py | LiteratureSourceCustody | machinery | page custody (_artifact, _within_source, _validate_page): the old assignment named no page; not applicable |
| source_custody.py | LiteratureSourceCustody._require | machinery | reference-in-scope check: custody is the system's (records.holds); action rejects an unheld model-named reference |
| source_custody.py | LiteratureSourceCustody._artifact | machinery | page custody (_artifact, _within_source, _validate_page): the old assignment named no page; not applicable |
| source_custody.py | LiteratureSourceCustody._within_source | machinery | page custody (_artifact, _within_source, _validate_page): the old assignment named no page; not applicable |
| source_custody.py | LiteratureSourceCustody._validate_page | machinery | page custody (_artifact, _within_source, _validate_page): the old assignment named no page; not applicable |
| source_operations.py | LiteratureSourceOperations | episode function | task.py: materialize_text_arguments |
| source_operations.py | LiteratureSourceOperations.catalog | episode function | task.py: offered_catalog |
| source_operations.py | LiteratureSourceOperations.execute | episode function | task.py: run_registry (access and acquisition tools), populate (population tools) |
| source_operations.py | LiteratureSourceOperations._tool_arguments | episode function | task.py: action (argument validation, unheld references rejected) and offered_catalog (source_location_inputs) |
| source_operations.py | LiteratureSourceOperations._materialize_text_arguments | episode function | task.py: materialize_text_arguments |
| source_repositories.py | LiteratureRepositories | episode function | UNPLACED: partner population routes and LiteraturePartnerRepository (raw Store, not placed); populate raises NotImplementedError |
| source_repositories.py | LiteratureRepositories.literature_partner_repository | episode function | UNPLACED: partner population routes and LiteraturePartnerRepository (raw Store, not placed); populate raises NotImplementedError |
| source_repositories.py | LiteratureRepositories._population_routes | episode function | UNPLACED: partner population routes and LiteraturePartnerRepository (raw Store, not placed); populate raises NotImplementedError |
| task.py | SourceInvestigationTask | machinery | old generic next loop: replaced by decide and action |
| task.py | SourceInvestigationTask.next | machinery | old generic next loop: replaced by decide and action |
| task_action.py | SourceTaskAction | episode function | task.py: the tools (run_registry, populate, report_finding) and the ChildCall branch of action |
| task_action.py | SourceTaskAction.apply_response | episode function | task.py: action (validation of the answer, Rejected feedback for tool arguments only; the child commission is not checked) |
| task_action.py | SourceTaskAction.execute | episode function | task.py: the tools (run_registry, populate, report_finding) and the ChildCall branch of action |
| task_decision.py | SourceTaskDecision | machinery | decision exchange / saved exchange / conversation key / exchange schema: decision-exchange loop, not carried (a lookup is a tool) |
| task_decision.py | SourceTaskDecision.call | episode function | task.py: decide (ModelRequest with instructions, context, output schema) |
| task_decision.py | SourceTaskDecision.instructions | episode function | task.py: instructions |
| task_decision.py | SourceTaskDecision.conversation_key | machinery | decision exchange / saved exchange / conversation key / exchange schema: decision-exchange loop, not carried (a lookup is a tool) |
| task_decision.py | SourceTaskDecision.interpretation_context | episode function | task.py: decide (ModelRequest with instructions, context, output schema) |
| task_decision.py | SourceTaskDecision.exchange_schema | machinery | decision exchange / saved exchange / conversation key / exchange schema: decision-exchange loop, not carried (a lookup is a tool) |
| task_decision.py | SourceTaskDecision.exchange_response | machinery | decision exchange / saved exchange / conversation key / exchange schema: decision-exchange loop, not carried (a lookup is a tool) |
| task_decision.py | SourceTaskDecision.validate_contract_exchange_request | machinery | decision exchange / saved exchange / conversation key / exchange schema: decision-exchange loop, not carried (a lookup is a tool) |
| task_decision.py | SourceTaskDecision.validate_contract_exchange_history | machinery | decision exchange / saved exchange / conversation key / exchange schema: decision-exchange loop, not carried (a lookup is a tool) |
| task_decision.py | SourceTaskDecision.exchange_decision | machinery | decision exchange / saved exchange / conversation key / exchange schema: decision-exchange loop, not carried (a lookup is a tool) |
| task_decision.py | SourceTaskDecision.decision_completion | episode function | task.py: decide (ModelRequest with instructions, context, output schema) |
| task_instructions.py | instructions | episode function | task.py: instructions (shared text with redelivery/history spans replaced; wait, reason, knowledge and launch texts not added for this role) |
| task_presentation.py | present_source_context | episode function | task.py: render_prompt (the TASK and STEERING prompt from the summary); state-frame reconstruction is old runner |
| task_reading_prompt.py | render_literature_experimental_prompt | episode function | task.py: render_prompt and section |
| task_report_delivery.py | SourceTaskReportDelivery | episode function | messages/final_to_parent.py: final_to_parent (saving, pending handles and release are machinery) |
| task_report_delivery.py | SourceTaskReportDelivery.finish | episode function | messages/final_to_parent.py: final_to_parent (saving, pending handles and release are machinery) |
| task_state.py | SourceTaskState | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_state.py | SourceTaskState.__init__ | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_state.py | SourceTaskState.bind_execution_context | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_state.py | SourceTaskState.record_execution_failure | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_state.py | SourceTaskState.restore_checkpoint | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_state.py | SourceTaskState.restore | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_state.py | SourceTaskState.record_effect | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_state.py | SourceTaskState.checkpoint | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_suspension.py | SourceTaskSuspension | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| task_suspension.py | SourceTaskSuspension.suspension_changed | machinery | checkpoint/restore/record_effect/suspension of the old runner |
| to_child_evidence_search_strategy_improvement.py | assemble_request | episode function | messages/msg_to_child.py: msg_to_child (strategy assignment, scope, finding unit, held records, selection); goal, report-contract declaration and knowledge-inheritance receipts are machinery |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py: RETURN_FORM and final_to_parent |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM (literature_partner_cells, sheet_refs plus credit and finding) |
| to_parent.py | LiteratureReport.resolve | machinery | reference resolver of the old report form; the system admits the result and requires held records |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py: validate_report (the episode's own report check) |
| waiting.py | LiteratureWaiting | machinery | wait support flag (supports_wait False): wait machinery |
| waiting.py | LiteratureWaiting.supports_wait | machinery | wait support flag (supports_wait False): wait machinery |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py: yield_controller (AccumulationYieldController; old returned None) |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | yield_estimator.py: yield_controller (AccumulationYieldController; old returned None) |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py: yield_controller (AccumulationYieldController; old returned None) |
