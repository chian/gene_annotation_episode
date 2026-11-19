# a107 / passage_evidence_extraction (old role `literature_targeted`)

Path: `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction`

Source of this note: the episode's own files at `97308b94c` (30 files; no subfolders, no grading/ or scoring/).

## What it is for

Goal (goal.py, own words): `_ROLE_INSTRUCTIONS['literature_targeted']` = "Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation." followed by the A107 partner text ("Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and partner roles, normalization, nonpartner conditions, physical measurement identity, source units and uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target correspondence or annotation credit. A search or read earns no scientific credit by itself.").

In short: extract partner evidence from one or more selected passages (byte windows) of one source, keeping spans separate.

## Task and instructions

Same task loop, instruction composition and TASK/STEERING prompt as its siblings (byte-identical files).

## What it reads from the parent's assignment

`reading_assignment_v1` (from_parent.py): `{version, page: _PAGE, selection: {spans: [>=1 _WINDOW {source_ref, representation, offset, limit}]}}` plus partner fields. Validation: page validated as in source_evidence_examination; each span must have the page's `source_ref` (`literature_reading_source_mismatch`) and representation (`literature_reading_representation_mismatch`); its offset must not exceed the page artifact size (`source_offset_out_of_bounds`). When prepared by a `literature_page` parent, the page source must lie within the parent's page source (`literature_reading_outside_assigned_source`); for that the file carries its own copy of the parent's page schema/validation (`_parent_page_schema`, `_validate_parent_page_assignment`).

## Children it may commission

None (`child_roles` = ()), though `child` stays in the permitted common actions list. No to_child/from_child files.

## Decision state and what the model sees

Own fields: `literature_assignment`, `literature_source_custody` for `assignment.page.source_ref`, `own_literature_outcomes` (limit 8), history meaning, experimental-work marker, owned population sources, latest failed population attempt, component-axis source origin/access. Old-runner fields as in the siblings' notes.

## Tools it offers

Access tools only (same list as source_evidence_examination, execution.estimate restricted to xlsx branches) + partner population operations; no acquisition tools. Every source ref must lie within `assignment.page.source_ref`. Common actions: `tool`, `child`, `redeliver_report`.

## Credit

`scientific` kind via services.scientific_credit; no projector; credit after each observed outcome; unbounded.

## Continuation

No own continuation; old default controller. Nearest new estimator: **accumulation**, default settings (inference).

## What it reports to its parent

Typed form via `form_with_facts` with partner fact cells of committed refs, requested components only; validated by `validate_report`.

## Differences from similar episodes

- vs `source_coverage_improvement` (sibling leaf): differs only in the assignment selection - here `selection.spans` is a list of >=1 windows; there `selection` is a single window - and in its role/path strings. All other files are identical.
- vs parent `source_evidence_examination`: no children, assignment = page + reading selection.

## File by file (old files at 97308b94c)

"Same in" lists the other episodes of this group (S=source_relevance_assessment, E=source_evidence_examination, P=passage_evidence_extraction, C=source_coverage_improvement) whose copy is byte-identical.

| old file | lines | this episode's own intent | old-runner names used (x count) | same in |
|---|---|---|---|---|
| __init__.py | 0 | Empty package marker; no intent. | `none` | SEC |
| binding_record.py | 13 | Records the binding: version `literature_episode_binding_v1`, binding_id = this episode's own path, configuration {outcome_page_size, reference_parent_sources if set, contract_information_profile if set}. | `none` | - |
| configuration.py | 35 | Own settings: `outcome_page_size` (default 8, must be a positive int), optional explicit unique `reference_parent_sources`, optional `contract_information_profile` (only the A107 profile is accepted). No own reasoning action: `reasoning_action_schema` None, `reasoning_has_task_content` False, `execute_reasoning` None. | `none` | SEC |
| contracts.py | 39 | A107 literature vocabulary copied into this episode: ROLES (literature, _strategy, _search, _page, _table, _ordered, _targeted), `_CHILDREN` tree, schemas `_REFERENCES`, `_WINDOW` (source_ref, representation text/original/stdout/stderr, offset>=0, limit>=1), `_TABLE`, `_PAGE` (page_assignment_v1), tool lists `_ACCESS_TOOLS` / `_ACQUISITION_TOOLS` / `_READ_TOOLS`, the per-role `_ROLE_INSTRUCTIONS` texts, `_population_catalog()` (partner population operations from library.partner_source_contracts). | `import:a107.communication x1, import:a107.composition_information x1, import:a107.domain x1, import:a107.episode_bindings x1, import:a107.library.partner_source_contracts x1` | SEC |
| credit.py | 16 | Credit kind is `scientific`; credit view is the services' scientific credit for (context, receiver_selection); no credit projector. | `self.services.scientific_credit x1` | SEC |
| episode.py | 53 | Composes this episode from its own mixins; binding_path / commissioning_parent; single role; permitted common actions `tool`, `child`, `redeliver_report` (no `reason`, no `wait`); decision task type SourceInvestigationTask; prompt renderer present_source_context; child role -> own to_child/from_child modules. | `none` | - |
| from_parent.py | 65 | Parent assignment schema and validation (see section above), plus partner fields from `library.partner_source_contracts.assignment_schema_fields()`. | `import:a107.library.partner_source_contracts x2, self.services.read_record x1` | - |
| goal.py | 9 | Goal text = this role's `_ROLE_INSTRUCTIONS` entry + the A107 partner text: "Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and partner roles, normalization, nonpartner conditions, physical measurement identity, source units and uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target correspondence or annotation credit. A search or read earns no scientific credit by itself." | `none` | - |
| initial_information.py | 9 | Initial information = resource information + received API information from the readers declared for this episode's own path. | `catalog.readers x1, import:a107.library.execution_initial_information.presentation x1` | - |
| internal_summary.py | 133 | Own decision context: `literature_assignment`, `literature_source_custody` (version, artifact/text/stdout/stderr refs, parent_source_refs of assigned sources), `own_literature_outcomes` (own acquisition+read outcomes, first `outcome_page_size`), `literature_history_meaning`, `literature_experimental_work` marker (aspect `source_experimental_evidence`), owned population sources, latest failed population attempt, `component_axis_source_origin`, `component_axis_source_access`. `facts()` = partner fact cells of committed refs; `current_report_facts()` = {}. The second class SourceDecisionSummary is the old runner's decision snapshot assembly (what the model saw; see section above). | `import:a107.component_axis_source_access x1, import:a107.library.literature_source_origin x1, import:a107.library.partner_source_task_selection x1, import:a107.runtime x1, runtime.FACT_MEANINGS x1, runtime.FACT_SOURCES x1, runtime.json x2, runtime.Mapping x3, runtime._plain x2, runtime._references_in x1, self.request.goal x1, self.request.report_contract x4, self.services.own_outcomes x1, self.workflow.action_schema x1, self.workflow.annotation_context x1, self.workflow.binding_context x1, self.workflow.catalog x1, self.workflow.controller_binding x1, self.workflow.delivery_resolution_inputs x1, self.workflow.delivery_status x1, self.workflow.extra_report_sources x1, self.workflow.is_scientific_source x1, self.workflow.job_episode_options x1, self.workflow.journal x3, self.workflow.knowledge x1, self.workflow.local_outcome_preview x1, self.workflow.pending_work x1, self.workflow.receipt_projection x1, self.workflow.run_id x1, self.workflow.source_credit_binding x1, self.workflow.source_credit_view x1, self.workflow.specialist x1, self.workflow.store x3, self.workflow.tools x1, self.workflow.working_state x1, table:runtime_actions x4, table:sqlite_master x2, view.child_reports x2, view.controller_state x1, view.model_inputs x1, workflow.run_id x2, workflow.store x2` | - |
| numerical_report_facts.py | 31 | Report fact sources = partner_source_contracts.fact_sources(); `_rate_facts` = for each population route, received source records of that provider (version must match the repository record version, else error) plus current sheet refs, cells restricted to the components the assignment requested (or route defaults). | `import:a107.library.literature_sheet_updates x1, import:a107.library.partner_source_contracts x1, self.services.read_record x1, self.services.workflow.store x1, view.received_record_refs x1` | SEC |
| parent_context.py | 21 | Root-only initial context (annotation role, path length 1, reference parent sources) - returns {} for this role; contract information profile applies to every literature role. | `none` | SEC |
| received_api_reports.py | 4 | Selects the API reader authority configured/received for this episode's own path. | `catalog.configured x1, catalog.received x1` | - |
| received_execution_information.py | 4 | Selects the result readers configured/received for this episode's own path. | `catalog.configured x1, catalog.received x1` | - |
| received_reports.py | 71 | Received-report facts only for non-literature roles ({} here); requested arrays filled with [] when no cells (not zero, not absence); received child cells stored in the partner repository; evidence tokens from received cell digests; received report validation: sheet_ref must be permitted, components must be requested, empty family validated. | `import:a107.library.literature_sheet_updates x1, import:a107.method_loop.durable x1, self.services.record_selection x1, self.services.workflow.store x1` | SEC |
| source_custody.py | 39 | Source custody: `_require` (scope check, then read record), representation -> artifact mapping, `_within_source` (ancestry via parent_source_refs), `_validate_page` (artifact must match representation; question/prior refs in scope). | `self.services.read_record x1, self.services.reference_in_scope x1` | SEC |
| source_operations.py | 95 | Tool catalog filter and execution (see Tools section); partner population tools run through library.literature_partner_sheet_population with text witness materialization; failures return `invalid` outcomes with feedback. | `import:a107.component_axis_source_access x2, import:a107.composition_information x1, import:a107.library.literature_assay_inputs x1, import:a107.library.literature_partner_sheet_population x1, import:a107.literature_contract_error x1, self.services.execute_tool x1, self.services.tool_catalog x1` | - |
| source_repositories.py | 15 | Partner repository (LiteraturePartnerRepository over store/run_id) and population routes from library.partner_source_contracts. | `import:a107.library.partner_source_contracts x1, import:a107.literature_partner_storage x1, self.services.workflow.run_id x1, self.services.workflow.store x1` | SEC |
| task.py | 84 | Decision iterator `next()`: own intent is the loop snapshot -> model call -> apply response; a model-call error is recorded as a source failure with feedback and the episode ends `source_failed`. Everything else (closed-episode check, in-process replay, execution binding slots, unfinished actions, saved model calls) is old-runner replay machinery. | `import:a107.episode_source_failure x1, import:a107.providers x1, import:a107.runtime x1, runtime.json x4, runtime.nullcontext x1, runtime.SourceEnd x2, runtime.WorkflowError x1, self.workflow.completed_unit x3, self.workflow.completions x2, self.workflow.execution_binding x2, self.workflow.inprocess_replay x4, self.workflow.journal x4, self.workflow.next_return x1, self.workflow.resolve_pending_deliveries x1, self.workflow.run_id x1, self.workflow.selected x2, self.workflow.store x3, table:runtime_actions x2, table:runtime_episodes x1, table:runtime_model_calls x1, view.units_consumed x4` | SEC |
| task_action.py | 136 | Own intent: admission of a model response (selection validated against schema; invalid selection -> feedback `action_contract` with schema diagnostic and repair texts, failed job handoff -> `job_assignment`, reads.map parameter diagnostics) and of report_update (validated; basis = visible refs; invalid -> `report_format`); `execute()`: run the tool, record result, automatic score update, credit after each observed outcome, wait keeps last credit, unobserved failure -> ActionFailure. | `import:a107.read_mapping x1, import:a107.runtime x1, runtime.AcquisitionError x2, runtime.ActionFailure x1, runtime.ContractError x1, runtime.ContractInformationError x1, runtime._decode_recorded_action_response x1, runtime.Draft202012Validator x3, runtime.EventTargetError x1, runtime.inspect x1, runtime._json x5, runtime.json x4, runtime.Mapping x3, runtime.nullcontext x4, runtime.observes_action_outcome x1, runtime.ReportBoundaryError x1, runtime.ReportRedelivery x2, runtime.schema_failure_diagnostic x1, runtime.sqlite3 x2, runtime.subprocess x2, runtime.validate_form x1, runtime.ValidationError x3, runtime._wait_target_feedback x1, runtime.WorkflowError x1, self.request.message x1, self.workflow.automatic_score_updates x1, self.workflow.binding_context x1, self.workflow.completions x1, self.workflow.controller_value x2, self.workflow.decision_exchanges x3, self.workflow.execute x1, self.workflow.execution_binding x5, self.workflow.journal x3, self.workflow.last_observed_credit x1, self.workflow.pending_work x1, self.workflow.permits_common_action x1, self.workflow.reasoning_action_schema x1, self.workflow.receive_native_outcome x1, self.workflow.receive_outcome x1, self.workflow.resolver x1, self.workflow.retain_shared_grading_results x1, self.workflow.run_id x1, self.workflow.selected x1, self.workflow.source_credit_view x1, self.workflow.specialist x1, self.workflow.store x5, self.workflow.validate_report x1, table:runtime_actions x6, table:runtime_model_calls x1` | SEC |
| task_decision.py | 351 | Own intent: what goes into a decision (see section above), exchange protocol `request_context` (lookups: child_options, composition_information, own attempts) / `select_action`, yield table of own actions shown as `action_yields`. Rest is old journal/replay/contract-freezing machinery and the presentation hook into the old provider. | `import:a107.episode_work_report x1, import:a107.providers x1, import:a107.runtime x1, runtime._action_generation_schema x2, runtime.apply_state_frame x1, runtime._ASSIGNMENT_TRANSPORT x1, runtime._category_yield_parameters x1, runtime.child_option_information x2, runtime.composition_lookup_schema x2, runtime.CONTRACT_INFORMATION_OPERATIONS x1, runtime.DECISION_CONTEXT_VERSION x2, runtime.DECISION_EXCHANGE_PROTOCOL x5, runtime._digest x1, runtime.Draft202012Validator x1, runtime.infernal_receiver_context x2, runtime.instructional_model_context x4, runtime.is_contract_information x1, runtime._json x14, runtime.json x3, runtime.lookup_attempts x1, runtime.Mapping x4, runtime.model_snapshot x2, runtime._object x3, runtime._plain x2, runtime._recorded_action_generation_schema x1, runtime._recorded_assignment_transport x1, runtime._references_in x1, runtime.requested_contract_information x2, runtime.schema_failure_diagnostic x2, runtime.sqlite3 x1, runtime.state_frame x1, runtime.ValidationError x5, runtime.WorkflowError x14, runtime.yield_table x1, self.request.message x1, self.workflow.available_child_roles x1, self.workflow.binding_context x1, self.workflow.contract_information_profile x1, self.workflow.contract_information_reply x1, self.workflow.controller_binding x1, self.workflow.decision_exchanges x4, self.workflow.decision_protocol x3, self.workflow.episode_bindings x1, self.workflow.execute x1, self.workflow.execution_expectations x1, self.workflow.freeze_contract_information x1, self.workflow.freeze_literature_numerical_contracts x1, self.workflow.history_preview x1, self.workflow.journal x3, self.workflow.launch_instructions x2, self.workflow.native_estimation_context x1, self.workflow.numerical_contracts x1, self.workflow.pending_work x1, self.workflow.permits_common_action x1, self.workflow.provider x3, self.workflow.receipts x4, self.workflow.resource_context x1, self.workflow.resource_estimator x4, self.workflow.run_id x1, self.workflow.services x2, self.workflow.shared_information_context x1, self.workflow.specialist x1, self.workflow.store x2, self.workflow.uses_received_record_context x2, self.workflow.validate_contract_information x5, self.workflow.waiting_support x1, table:runtime_model_calls x8` | SEC |
| task_instructions.py | 25 | Instruction composition: base INSTRUCTIONS + this episode's goal text; conditional texts for reasoning commit, tool knowledge, launch instructions, pending child redelivery, wait, native event targets; exchange-protocol replacement of history guidance. | `import:a107.library.scientific_instruction_text x1, runtime_prompt.DECISION_EXCHANGE_PROTOCOL x1, runtime_prompt.INSTRUCTIONS x4, runtime_prompt.REASONING_COMMIT_REQUIREMENT x1, source.workflow.binding_context x1, source.workflow.decision_protocol x1, source.workflow.knowledge x1, source.workflow.launch_instructions x1, source.workflow.native_event_information x1, source.workflow.permits_common_action x3, source.workflow.specialist x1` | SEC |
| task_presentation.py | 48 | Renders the TASK text prompt when the `literature_experimental_work` marker is present (bootstrap/update/lookup frames), else JSON context. | `import:a107.decision_context x1, import:a107.library.literature_source_presentation x1, import:a107.library.scientific_decision_presentation x1` | SEC |
| task_reading_prompt.py | 37 | Own prompt layout: TASK (lead, source availability, source scope, component reading task, instructions, fact contract task; assigned question, scope, parent assignment, source parent, source custody, supplied material, operations, permitted narrower investigations, requested information, parent's return meanings, return timing) and STEERING ("Select the received source_ref, artifact_ref and zero-based half-open UTF-8 byte range for text witnesses. Preserve the exact observed subject, source meaning and unresolved target correspondence."; source access, own action yields, continuation expectation, pending delivery, current findings, child reports, operation results, last outcome). | `import:a107.library.literature_source_presentation x1` | SEC |
| task_report_delivery.py | 23 | Report: with a parent contract, the form = report_values filled with facts (saved once); without one, credit + pending handles + current report facts. | `import:a107.runtime x1, runtime.form_with_facts x1, runtime._json x2, runtime.json x1, runtime.Record x2, self.request.report_contract x2, self.workflow.binding_context x1, self.workflow.episode_bindings x1, self.workflow.facts x1, self.workflow.journal x2, self.workflow.pending_handles x1, self.workflow.release x2, self.workflow.source_credit_view x1, table:runtime_forms x2` | SEC |
| task_state.py | 108 | Own state: report_values (initialised from parent initial_report), report_basis, feedback, last outcome, interpretation schema from the parent's report contract; an execution failure of a tool/reason action is recorded as a failed outcome with credit and enters the iterator. Restore/checkpoint is old-runner machinery. | `import:a107.episode_source_failure x1, import:a107.runtime x1, runtime.ActionLeaf x1, runtime.EFFECT_VERSION x1, runtime.Episode x1, runtime.interpretation_schema x1, runtime._json x2, runtime.json x4, runtime._object x1, runtime._plain x1, runtime.Record x1, self.workflow.archive x1, self.workflow.completions x4, self.workflow.controller_value x1, self.workflow.execution_binding x4, self.workflow.inprocess_replay x7, self.workflow.journal x5, self.workflow.progress_provider x2, self.workflow.recover_commissions x1, self.workflow.run_id x1, self.workflow.source_credit_view x1, self.workflow.store x2, table:runtime_actions x5, workflow.context x1, workflow.grains x1` | SEC |
| task_suspension.py | 9 | Stores the suspension condition; pushes it to the old execution backend. | `self.workflow.execution_backend x1, self.workflow.execution_handle x2` | SEC |
| to_parent.py | 18 | Report facts sources; reference resolution in context; `validate_report` = assignment revalidated + form validated + received partner cells validated. | `none` | SEC |
| waiting.py | 8 | `supports_wait` False. | `none` | SEC |
| yield_estimator.py | 12 | `continuation_task` None and `yield_controller` None: no episode-specific continuation; the old runner's default controller applied. | `none` | SEC |

## Carried over

Carried over on 19 November 2026 into the ten-file form (`episode.py` class `PassageEvidenceExtraction`). One row per old function, class and method (`runs/carry_over/functions/a107__partner_presence_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.tsv`); columns old file, kind, name, then whether it is old-runner machinery or an episode function, and where it lives now. "unplaced" rows are named in `docs/axis_restructure_20261117/carry_over_blocked/a107__partner_presence_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.md`.

| old file | kind | name | class | new place or machinery reason |
|---|---|---|---|---|
| binding_record.py | class | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() are deleted (README 3d, 3e) |
| binding_record.py | method | LiteratureBindingRecord.as_record | machinery | binding's own as_record(): recorded by the system (settings/declaration) |
| configuration.py | class | LiteratureConfiguration | machinery | configuration class: values become constants of the file that uses them or settings (README 3) |
| configuration.py | method | LiteratureConfiguration.__init__ | episode function | outcome_page_size 8 -> messages/internal_summary.py OUTCOME_PAGE_SIZE; reference_parent_sources and contract_information_profile are root-only / contract-information freezing (deleted exchange machinery) |
| configuration.py | method | LiteratureConfiguration.reference_evidence | machinery | old-runner configuration hook (reference_parent_sources) |
| configuration.py | method | LiteratureConfiguration.contract_information_configuration | machinery | contract-information freezing (deleted exchange machinery) |
| configuration.py | method | LiteratureConfiguration.reasoning_action_schema | machinery | returns None: this episode has no reason action |
| configuration.py | method | LiteratureConfiguration.reasoning_has_task_content | machinery | returns False: this episode has no reason action |
| configuration.py | method | LiteratureConfiguration.execute_reasoning | machinery | returns None: this episode has no reason action |
| contracts.py | function | _population_catalog | episode function | task.py population_catalog (raises NotImplementedError: library module partner_source_contracts not placed) -- library candidate |
| credit.py | class | LiteratureCredit | machinery | credit mix-in class |
| credit.py | method | LiteratureCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | method | LiteratureCredit.credit_view | episode function | credit.py credit (finding progress over held records; the old services.scientific_credit is a removed service) |
| credit.py | method | LiteratureCredit.credit_projector | machinery | returned None: no projector of its own |
| episode.py | class | LiteratureEpisode | episode function | episode.py PassageEvidenceExtraction |
| episode.py | method | LiteratureEpisode._role | machinery | role dispatch: each role is its own episode now |
| episode.py | method | LiteratureEpisode.permitted_common_actions | machinery | tool -> TOOLS in task.py; child -> CHILD_SLOTS = {}; redeliver_report deleted (README 3b R2) |
| episode.py | method | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| episode.py | method | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} |
| from_parent.py | class | LiteratureAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | method | LiteratureAssignment.child_assignment_schema | machinery | parent-side commission schema lookup; the child's own form is ASSIGNMENT_FORM |
| from_parent.py | method | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (partner fields: partner_components, name unverified; partner_source_contracts.assignment_schema_fields not placed) |
| from_parent.py | method | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (source and representation checks); the offset-within-artifact check needs a Store read and is not carried (unplaced); page validation -> messages/internal_summary.py source_custody |
| from_parent.py | method | LiteratureAssignment.prepare_assignment | machinery | check of a commission made by the parent (wrong commission fails, rule 1) |
| from_parent.py | method | LiteratureAssignment._parent_page_schema | machinery | private copy of the parent's page schema, used only to check a commission |
| from_parent.py | method | LiteratureAssignment._validate_parent_page_assignment | machinery | check of the parent's own assignment, used only to check a commission |
| goal.py | class | LiteratureGoal | episode function | goal.py (GOAL, UNIT, RESULT) and task.py instruction constants |
| goal.py | method | LiteratureGoal.instructions | episode function | task.py ROLE_INSTRUCTIONS + PARTNER_INSTRUCTIONS, composed by task.py instructions() |
| initial_information.py | function | initial_information | episode function | not carried: reads library.execution_initial_information.presentation, which has no placed module (unplaced) |
| internal_summary.py | class | LiteratureSummary | episode function | messages/internal_summary.py |
| internal_summary.py | method | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (assignment, source custody, own outcomes page of 8, history meaning); component_axis_source_origin/access not carried (unplaced); rendered by task.py render_prompt |
| internal_summary.py | method | LiteratureSummary.facts | episode function | messages/internal_summary.py partner_cells + messages/final_to_parent.py final_to_parent |
| internal_summary.py | method | LiteratureSummary.current_report_facts | machinery | returned {}: nothing to carry |
| internal_summary.py | method | LiteratureSummary._owned_population_task_sources | episode function | not carried (unplaced): needs library.partner_source_task_selection (no module) and raw SQL on store.db/sqlite_master |
| internal_summary.py | method | LiteratureSummary._population_task_context | episode function | not carried (unplaced): reads runtime_actions and the above |
| internal_summary.py | class | SourceDecisionSummary | machinery | old runner's decision snapshot assembly (replaced by internal_summary and decide) |
| internal_summary.py | method | SourceDecisionSummary._decision_snapshot | machinery | old runner's decision snapshot (journal reads, credit view, annotation context) |
| numerical_report_facts.py | class | LiteratureNumericalReportFacts | episode function | messages/final_to_parent.py and messages/internal_summary.py |
| numerical_report_facts.py | method | LiteratureNumericalReportFacts._rate_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM literature_partner_cells and sheet_refs (partner_source_contracts.fact_sources not placed) |
| numerical_report_facts.py | method | LiteratureNumericalReportFacts._rate_facts | episode function | messages/internal_summary.py partner_cells (raises for held sheets: repository not carried, routes not placed) |
| parent_context.py | class | LiteratureParentContext | machinery | root-only initial context |
| parent_context.py | method | LiteratureParentContext.initial_decision_context | machinery | returned {} for this role |
| parent_context.py | method | LiteratureParentContext.contract_information_profile | machinery | contract-information freezing (deleted exchange machinery) |
| received_api_reports.py | function | received_api_reports | episode function | not carried (unplaced): selected readers via catalog.readers; no placed module (feeds initial_information) |
| received_execution_information.py | function | received_execution_information | episode function | not carried (unplaced): selected readers via catalog.readers; no placed module (feeds initial_information) |
| received_reports.py | class | LiteratureReceivedReports | machinery | receipt of child reports; this leaf has no children |
| received_reports.py | method | LiteratureReceivedReports.received_report_sources | machinery | returned {} for a literature role |
| received_reports.py | method | LiteratureReceivedReports.received_report_facts | machinery | returned {} for a literature role |
| received_reports.py | method | LiteratureReceivedReports._complete_requested_received_arrays | machinery | only for received child cells (non-literature roles) |
| received_reports.py | method | LiteratureReceivedReports.received_form_references | machinery | receipts bookkeeping (storing received cells, returning refs) |
| received_reports.py | method | LiteratureReceivedReports.received_evidence_tokens | machinery | receipts bookkeeping (evidence tokens of received cells) |
| received_reports.py | method | LiteratureReceivedReports.validate_received_report | episode function | messages/final_to_parent.py validate_report (requested components, cells name a held sheet) |
| source_custody.py | class | LiteratureSourceCustody | episode function | task.py and messages/internal_summary.py (below) |
| source_custody.py | method | LiteratureSourceCustody._require | machinery | scope check then read: custody (records.holds / records.get) |
| source_custody.py | method | LiteratureSourceCustody._artifact | episode function | messages/internal_summary.py source_artifact |
| source_custody.py | method | LiteratureSourceCustody._within_source | episode function | task.py within_source |
| source_custody.py | method | LiteratureSourceCustody._validate_page | episode function | messages/internal_summary.py source_custody |
| source_operations.py | class | LiteratureSourceOperations | episode function | task.py tools |
| source_operations.py | method | LiteratureSourceOperations.catalog | episode function | task.py offered_catalog (dotted old names kept in ACCESS_TOOLS) |
| source_operations.py | method | LiteratureSourceOperations.execute | episode function | task.py TOOLS (run_registry, populate) |
| source_operations.py | method | LiteratureSourceOperations._tool_arguments | episode function | task.py check_sources and action (schema validation in action) |
| source_operations.py | method | LiteratureSourceOperations._materialize_text_arguments | episode function | task.py materialize_text_arguments |
| source_repositories.py | class | LiteratureRepositories | machinery | repository holder over the raw store |
| source_repositories.py | method | LiteratureRepositories.literature_partner_repository | episode function | not carried (unplaced): LiteraturePartnerRepository(store, run_id) is written against the raw Store (called in task.py populate path: raises) |
| source_repositories.py | method | LiteratureRepositories._population_routes | episode function | not carried (unplaced): partner_source_contracts.population_routes not placed |
| task.py | class | SourceInvestigationTask | machinery | old decision iterator |
| task.py | method | SourceInvestigationTask.next | machinery | old loop (replay, model call, source_failed end): decide/action and the system's loop |
| task_action.py | class | SourceTaskAction | episode function | task.py action and tools |
| task_action.py | method | SourceTaskAction.apply_response | episode function | task.py action (admission of the answer, Rejected feedback) |
| task_action.py | method | SourceTaskAction.execute | episode function | task.py TOOLS (tool units); credit after each outcome is the system's; report_update -> report_finding tool |
| task_decision.py | class | SourceTaskDecision | episode function | task.py decide |
| task_decision.py | method | SourceTaskDecision.call | episode function | task.py decide (what a decision contains) |
| task_decision.py | method | SourceTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | method | SourceTaskDecision.conversation_key | machinery | conversation state deleted (README 3a) |
| task_decision.py | method | SourceTaskDecision.interpretation_context | machinery | old exchange context |
| task_decision.py | method | SourceTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | method | SourceTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | method | SourceTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop |
| task_decision.py | method | SourceTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop |
| task_decision.py | method | SourceTaskDecision.exchange_decision | machinery | decision-exchange loop |
| task_decision.py | method | SourceTaskDecision.decision_completion | machinery | decision-exchange loop |
| task_instructions.py | function | instructions | episode function | task.py instructions (shared text from instructions/scientific_instruction_text.py; wait, native-event, redelivery, exchange spans dropped) |
| task_presentation.py | function | present_source_context | episode function | task.py render_prompt (declared-TASK dispatch and state-frame replay dropped); fixed paragraphs of library.literature_source_presentation not placed |
| task_reading_prompt.py | function | render_literature_experimental_prompt | episode function | task.py render_prompt (sections kept; lead, SOURCE_AVAILABILITY, SOURCE_SCOPE, COMPONENT_READING_TASK, FACT_CONTRACT_TASK not reproduced: module not placed) |
| task_report_delivery.py | class | SourceTaskReportDelivery | episode function | messages/final_to_parent.py |
| task_report_delivery.py | method | SourceTaskReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (form saving, release and pending handles are machinery) |
| task_state.py | class | SourceTaskState | machinery | old per-episode source state |
| task_state.py | method | SourceTaskState.__init__ | machinery | report_values/feedback/last outcome state: the view, the report_finding tool outcome and decide's feedback |
| task_state.py | method | SourceTaskState.bind_execution_context | machinery | execution binding slots |
| task_state.py | method | SourceTaskState.record_execution_failure | episode function | task.py run_registry returns failure_outcome(...) as the unit's outcome |
| task_state.py | method | SourceTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | method | SourceTaskState.restore | machinery | checkpoint/restore |
| task_state.py | method | SourceTaskState.record_effect | machinery | checkpoint/restore bookkeeping |
| task_state.py | method | SourceTaskState.checkpoint | machinery | checkpoint/restore |
| task_suspension.py | class | SourceTaskSuspension | machinery | wait/suspension machinery |
| task_suspension.py | method | SourceTaskSuspension.suspension_changed | machinery | wait/suspension machinery |
| to_parent.py | class | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | method | LiteratureReport.resolve | machinery | reference_in_context resolver: custody (records.holds) |
| to_parent.py | method | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (assignment revalidation is read_from_parent; the report form is admitted by the system) |
| waiting.py | class | LiteratureWaiting | machinery | wait machinery |
| waiting.py | method | LiteratureWaiting.supports_wait | machinery | wait machinery (False) |
| yield_estimator.py | class | LiteratureYield | episode function | yield_estimator.py |
| yield_estimator.py | method | LiteratureYield.continuation_task | machinery | returned None; deleted |
| yield_estimator.py | method | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller (old: None = default controller -> AccumulationYieldController, README 7b) |
