# a107/partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction: episode intent at 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/<file>`. 30 Python files (one empty `__init__.py`), 1,513 lines. Role `literature_table`. No children and no entry roles. There is no `grading/` or `scoring/` subfolder. Binding id/path `partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction`, commissioning parent `.../source_evidence_examination` (role `literature_page`).

## Purpose (own words)

`goal.py` instructions = `_ROLE_INSTRUCTIONS['literature_table']` + the A107 partner paragraph:

> "Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows."
> "Investigate reported partner removal, addback and coexpression evidence. Preserve the original molecule and partner roles, normalization, nonpartner conditions, physical measurement identity, source units and uncertainty. Condition-specific dependence does not establish universal necessity, genomic presence, target correspondence or annotation credit. A search or read earns no scientific credit by itself."

`contracts.py` docstring: the binding supplies operands, available ordinary operations and source custody. The workflow owns decisions, reasoning commits, commissioning and report updates. "a reading selection is information for an investigation, never a script that this binding executes."

## Task and instructions

- The task is `SourceInvestigationTask` (`task.py`). It composes `SourceTaskState`, `SourceTaskDecision`, `SourceTaskSuspension`, `SourceTaskAction`, `SourceTaskReportDelivery` and `SourceDecisionSummary`. `instruction_composer = task_instructions.instructions`, `decision_prompt_renderer = task_presentation.present_source_context`.
- `task_instructions.instructions` starts from the default `INSTRUCTIONS` and appends the specialist `instructions` (above). `replaces_default_instructions` is not set, so the specialist text is appended to the defaults. It adds `REASONING_COMMIT_REQUIREMENT` only when `reason` is permitted. Here it is not: the common actions are `tool`, `child` and `redeliver_report`. It also adds tool-knowledge instructions and launch-instruction-library instructions when those are in context, and always adds the pending-child-delivery repair paragraph (select `redeliver_report`, preserve `current_report_update`). The two wait paragraphs are added only if `wait` is permitted, which it is not. Under the decision-exchange protocol, the fresh-conversation history guidance is replaced with "use request_context exchanges ... read exact previously received outcomes with episode.history view=records".
- `task_reading_prompt.render_literature_experimental_prompt` is this episode's own TASK text. It requires `literature_experimental_work.version == literature_experimental_task_v1`. It has the following parts:
  - TASK lead for the selected family (default `A107_source`), SOURCE_AVAILABILITY, SOURCE_SCOPE, COMPONENT_READING_TASK, the instruction text, and FACT_CONTRACT_TASK under `operation_contract_information_v1`.
  - Sections: Assigned question, Assigned scope, Parent assignment and selected source operands, Assigned source parent, Representations available for selected sources, Supplied material and scoped access, Available selected operations, Permitted narrower investigations, Information requested by the parent, Parent's typed return meanings, Return interpretation timing.
  - STEERING: "Select the received source_ref, artifact_ref and zero-based half-open UTF-8 byte range for text witnesses. Preserve the exact observed subject, source meaning and unresolved target correspondence." It then has sections for recorded source inspections and access, own action yields, current continuation expectation, pending child delivery, current findings, received child reports, received operation results and own last outcome.
- `task_presentation.present_source_context` rebuilds prompt state from decision frames (`decision_bootstrap`, `decision_update`, `decision_lookup_result`) when the context is a literature experimental context, and renders the TASK text above. Any other context is sent as JSON. Under the contract-information profile, lookups are pending contract information.

## What it reads from its parent's assignment

`from_parent.assignment_schema`: `{version: const reading_assignment_v1, page: _PAGE, selection: anyOf[_TABLE, _WINDOW]}`, plus `partner_source_contracts.assignment_schema_fields()` (the requested partner components field or fields).

- `_PAGE` = `{version: page_assignment_v1, source_ref, representation (text|original|stdout|stderr), artifact_ref, question_context_refs[], prior_delivery_refs[]}`.
- `_TABLE` = `{source_ref, sheet_key, offset, limit, header_row (int>=1|null), where (null | {column A-Z letters|null, match equals|contains, value, case_sensitive})}`. This is the table-specific selection.
- `_WINDOW` = `{source_ref, representation, offset, limit}`. This is an article XML table read as an exact original-source window.

`_validate_assignment` checks the following. The value must be plain and JSON-serialisable (no NaN) and must match the schema. The page must pass `_validate_page`: the source is in scope, the artifact for the page's representation equals `artifact_ref`, the artifact is in scope, and the question-context and prior-delivery refs are in scope. The selection's `source_ref` must equal the page source (`literature_reading_source_mismatch`). For a window, the representation must equal the page representation, and the offset must not exceed the artifact size (`source_offset_out_of_bounds`).

`prepare_assignment` also requires a non-empty `operation_key`. When the parent is `literature_page`, it re-validates the parent's own page assignment (`_parent_page_schema`) and requires the selected source to lie within the parent's assigned source through the `parent_source_refs` ancestry (`literature_reading_outside_assigned_source`).

## Children

None. `child_roles` returns `()`, and `_CHILDREN['literature_table'] = ()`. `permitted_common_actions` nonetheless lists `child`; with no child roles, no child is offered. `parent_context.initial_decision_context` returns `{}` for this role, because it applies only to the root `annotation` role with `reference_parent_sources`.

## Decision state and what the model sees

`internal_summary.LiteratureSummary.decision_context` provides:

- `literature_assignment` (the validated assignment);
- `literature_source_custody`: for the page source, `version`, `artifact_ref`, `text_ref`, `stdout_ref`, `stderr_ref` and `parent_source_refs`;
- `own_literature_outcomes`: own outcomes for the acquisition and read tools, page size `outcome_page_size` (default 8);
- `literature_history_meaning`: "Own outcome metadata only. Inspect original source records and exact prior operations before interpreting them.";
- `literature_experimental_work`: `{literature_experimental_task_v1, aspect: source_experimental_evidence}`;
- `literature_owned_population_sources`: a read-only SQL classification of this episode's own completed population operations whose `sheet_ref` was received and whose metadata match the provider and version;
- `literature_selected_population_attempt`: the latest own tool action that ended invalid, failed or error, with its tool and arguments version or population_version;
- `component_axis_source_origin`, when one exists;
- `component_axis_source_access`, when one exists.

The generic `SourceDecisionSummary._decision_snapshot` (old runner shape) adds the following:

- goal, scope, working_state and visible_record_refs;
- current_credit or the annotation-axis view, and current_evidence_vector;
- investigation_progress, credit_binding and time_accounting;
- pending_work, last_local_outcome, feedback and visual_evidence (the most recent completed `image.view`);
- report_deliveries, controller and controller_binding;
- tools, tool_knowledge and job_episode_options;
- available_report_facts, requested_report_purpose and requested_form;
- current_report_update, current_report_basis_refs and report_lifecycle;
- the specialist decision_context;
- `_completed_work_axis_results`: a107_sheet, target_sheets, tool_attachments and source_contributions;
- the model_contract_catalog.

`task_decision.call` then adds:

- resource_context, shared_information_context and launch_instruction_library;
- selected_launch_instructions and child_options;
- the binding's initial_decision_context;
- completed_action_reports, pending_work, execution_expectations, resource_tool_estimates and native_execution_expectations;
- contract_information_profile, and frozen literature numerical contracts.

## Tools offered

`source_operations.catalog` is the scoped tool catalog filtered to `_ACCESS_TOOLS`:

- `state.query`, `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`, `image.view`;
- `source.archive.members`, `source.archive.extract`;
- `source.xlsx.sheets`, `source.xlsx.rows`;
- `source.pdf.info`, `source.pdf.text`, `source.pdf.page`;
- `execution.estimate`, narrowed to its `source.xlsx.sheets` and `source.xlsx.rows` branches and dropped if neither exists.

The catalog adds the A107 population operations from `partner_source_contracts.population_catalog_entries()` (`literature.partner.populate` and `literature.partner.source.populate`). These carry `CONTRACT_ARGUMENT_TRANSPORT` when a contract-information profile is configured. Every input schema is wrapped by `source_location_inputs`. There are no acquisition or search tools, even though `_ACQUISITION_TOOLS` is used for the outcome view.

`execute` and `_tool_arguments` validate as follows:

- The tool must be in the catalog, and its arguments must match the tool's schema.
- Every `source_ref` (or an archive member's `source_ref`) must lie within the page source.
- Table-specific check: `source.xlsx.rows` must use the assignment's `sheet_key` (`literature_table_sheet_mismatch`).
- For the populate tools, every nested `source_ref`, `data_source_ref`, `sheet_ref` and `metadata_source_ref` must lie within the page source.
- The populate tools materialise text-witness inputs (source.read authorisation per ref) and call `populate_partner_sheet(repo, context, native, operation_key)`.
- `source.locate`, the `source.sequence.*` tools and `source.experimental.records` receive `permitted_record_refs = received_record_refs`.
- An invalid argument returns an `invalid` outcome with `operation_ref` and `arguments_or_reference` feedback. It is returned to the iterator, not raised.

## Credit

`credit_kind = 'scientific'`. `credit_view = services.scientific_credit(context, receiver_selection)`. `credit_projector` returns None. The episode has no own projector and no bound.

## Continuation

`yield_estimator.LiteratureYield.continuation_task` and `yield_controller` both return None, so the episode declares no controller of its own; the old runner's default controller governed it. Its own files name none of the three current estimators (accumulation, bounded quality, completion with a target) and give no settings, so this is an open choice for the port. `supports_wait = False`.

## Report to parent

- `fact_sources = partner_source_contracts.fact_sources()`, which is the partner numerical fact families.
- `facts(context, snapshot)` = `_rate_facts(context, committed_record_refs)`. The references are the committed refs plus the current partner sheet refs in the store. For each population route `(namespace, requested_field, provider, defaults, repository)`, it takes the received source rows of that provider and checks their version (`literature_partner_projection_version_mismatch`). It then returns `adapter.fact_cells(view, selected, components=assignment[requested_field] or defaults)`.
- `current_report_facts` = `{}`.
- `validate_report` re-validates the assignment, runs `validate_form` with reference resolution through `episode_bindings.reference_in_context`, and then runs `validate_received_report`. `validate_received_report` checks partner cell rows per x-source namespace:
  - sheet_refs must be received, or known to the receiver's own record selection (`literature_partner_receiver_mismatch`);
  - an empty return family must be validated by its repository;
  - fact values must validate;
  - components must have been requested (`unrequested_literature_partner_component`).
- `received_report_*` are empty for this role, because `literature_table` is in `ROLES`. They act only for non-literature receivers.
- `task_report_delivery.finish`: without a report contract, it returns credit and pending handles plus the current report facts. With a contract, it saves or reloads `runtime_forms`, fills it with `form_with_facts(report_values, schema, facts)` and returns `{form}`.

## Differences from its sibling and similar episodes

The sibling is `passage_evidence_extraction` (role `literature_targeted`). It is identical in 24 of 30 files. The table episode differs as follows:

- The selection is `anyOf[_TABLE, _WINDOW]`, one selection. The sibling uses `{spans: [_WINDOW, ...] minItems 1}` and validates each span.
- `_ROLE_INSTRUCTIONS['literature_table']` is the table/sheet text. The sibling uses the targeted-passage text. The A107 partner paragraph is the same in both.
- `source_operations._tool_arguments` has the `literature_table_sheet_mismatch` check for `source.xlsx.rows`. The sibling has none.
- Role names, binding_path and the reader-catalog keys (`initial_information`, `received_*`) differ only in their path.

The A107 literature files are shared by copy across all seven literature roles, as `contracts.ROLES` and `_CHILDREN` show. This episode keeps only its own row.

## File by file

Name key: `wf.` = `self.workflow.` (or `source.workflow.`). `import:X` = an import from the old `root/a107/X`, which is the deleted axis-level tree. `runtime.X` / `runtime_prompt.X` = an attribute of the old `root/a107/runtime` / `runtime_prompt` module. `table:` = a journal table.

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 0 | none | none |
| binding_record.py | 13 | as_record: version literature_episode_binding_v1, binding_id .../table_evidence_extraction, configuration outcome_page_size [+reference_parent_sources, contract_information_profile] | none |
| configuration.py | 35 | constructor: positive int outcome_page_size (default 8), optional unique reference_parent_sources, contract_information_profile only CONTRACT_INFORMATION_PROFILE; `reference_evidence` classmethod; no reasoning schema/content/execution (returns None/False) | none (CONTRACT_INFORMATION_PROFILE via contracts) |
| contracts.py | 39 | VERSION, ROLES, schemas _WINDOW/_TABLE/_PAGE, _CHILDREN, tool sets _ACCESS/_ACQUISITION/_READ, _ROLE_INSTRUCTIONS, _population_catalog | import:communication(1), import:composition_information(1), import:domain(1), import:episode_bindings(1), import:library.partner_source_contracts(1) |
| credit.py | 16 | scientific credit kind; credit_view delegates; no projector | self.services.scientific_credit(1) |
| episode.py | 53 | composes the private mixins; role literature_table; common actions tool/child/redeliver_report; no children; decision_source_type SourceInvestigationTask; prompt renderer present_source_context | none (own-path absolute imports of received_* only) |
| from_parent.py | 65 | reading_assignment_v1 with page + table-or-window selection; source/representation/offset checks; within-parent-source check; parent page schema | import:library.partner_source_contracts(2), self.services.read_record(1) |
| goal.py | 9 | literature_table role instructions + A107 partner removal/addback/coexpression paragraph | none |
| initial_information.py | 9 | resource + received API info from this episode's readers | import:library.execution_initial_information.presentation(1) |
| internal_summary.py | 133 | decision_context fields (assignment, custody, own outcomes, experimental marker, owned population sources, last failed population attempt, source origin/access); facts -> _rate_facts; plus old generic _decision_snapshot | import:component_axis_source_access(1), import:library.literature_source_origin(1), import:library.partner_source_task_selection(1), import:runtime(2), runtime.FACT_MEANINGS(1), runtime.FACT_SOURCES(1), runtime.json(2), runtime.Mapping(3), runtime._plain(2), runtime._references_in(1), self.services.own_outcomes(1), self.services.workflow(3), workflow.store.db(2), wf.action_schema(1), wf.annotation_context(1), wf.binding_context(1), wf.catalog(1), wf.controller_binding(1), wf.delivery_resolution_inputs(1), wf.delivery_status(1), wf.extra_report_sources(1), wf.is_scientific_source(1), wf.job_episode_options(1), wf.journal(3), wf.knowledge(1), wf.local_outcome_preview(1), wf.pending_work(1), wf.receipt_projection(1), wf.run_id(1), wf.source_credit_binding(1), wf.source_credit_view(1), wf.specialist(1), wf.store(3), wf.tools(1), wf.working_state(1), table:runtime_actions(4) |
| numerical_report_facts.py | 31 | partner fact cells per population route from received provider sources, components requested or default | import:library.literature_sheet_updates(1), import:library.partner_source_contracts(1), self.services.read_record(1), self.services.workflow.store(1) |
| parent_context.py | 21 | initial context only for root annotation with reference sources (inactive here); contract_information_profile for literature roles | none |
| received_api_reports.py | 4 | selects this episode's API reader authority | none |
| received_execution_information.py | 4 | selects this episode's result readers | none |
| received_reports.py | 71 | received partner cells for non-literature receivers; empty requested arrays; validation of returned partner cells (receiver, empty family, values, requested components) | import:library.literature_sheet_updates(1), import:method_loop.durable(1), self.services.record_selection(1), self.services.workflow.store(1) |
| source_custody.py | 39 | reference scope check, representation->artifact, ancestry within-source, page validation | self.services.read_record(1), self.services.reference_in_scope(1) |
| source_operations.py | 97 | access-tool catalog + population ops; argument checks incl. sheet_key match; populate execution; text witness materialisation | import:component_axis_source_access(2), import:composition_information(1), import:library.literature_assay_inputs(1), import:library.literature_partner_sheet_population(1), import:literature_contract_error(1), self.services.execute_tool(1), self.services.tool_catalog(1), self.services.workflow(getattr)(2) |
| source_repositories.py | 15 | LiteraturePartnerRepository on store/run; population routes | import:library.partner_source_contracts(1), import:literature_partner_storage(1), self.services.workflow.run_id(1), self.services.workflow.store(1) |
| task.py | 84 | iterator `next`: source_failed end, replay/resume, model call, ModelCallError -> source failure, apply_response | import:episode_source_failure(1), import:providers(1), import:runtime(2), runtime.json(4), runtime.nullcontext(1), runtime.SourceEnd(2), runtime.WorkflowError(1), wf.completed_unit(3), wf.completions(2), wf.execution_binding(2), wf.inprocess_replay(4), wf.journal(4), wf.next_return(1), wf.resolve_pending_deliveries(1), wf.run_id(1), wf.selected(2), wf.store(3), table:runtime_actions(2), table:runtime_episodes(1), table:runtime_model_calls(1) |
| task_action.py | 136 | response admission (selection schema, delivery repair keeps report, empty reasoning commit rejected), failure feedback categories, report_update admission, tool execution + credit recording | import:read_mapping(1), import:runtime(2), runtime.AcquisitionError(2), runtime.ActionFailure(1), runtime.ContractError(1), runtime.ContractInformationError(1), runtime._decode_recorded_action_response(1), runtime.Draft202012Validator(3), runtime.EventTargetError(1), runtime.inspect(1), runtime._json(5), runtime.json(4), runtime.Mapping(3), runtime.nullcontext(4), runtime.observes_action_outcome(1), runtime.ReportBoundaryError(1), runtime.ReportRedelivery(2), runtime.schema_failure_diagnostic(1), runtime.sqlite3(2), runtime.subprocess(2), runtime.validate_form(1), runtime.ValidationError(3), runtime._wait_target_feedback(1), runtime.WorkflowError(1), wf.automatic_score_updates(1), wf.binding_context(1), wf.completions(1), wf.controller_value(2), wf.decision_exchanges(3), wf.execute(1), wf.execution_binding(5), wf.journal(3), wf.last_observed_credit(1), wf.pending_work(1), wf.permits_common_action(1), wf.reasoning_action_schema(1), wf.receive_native_outcome(1), wf.receive_outcome(1), wf.resolver(1), wf.retain_shared_grading_results(1), wf.run_id(1), wf.selected(1), wf.source_credit_view(1), wf.specialist(1), wf.store(5), wf.validate_report(1), table:runtime_actions(6), table:runtime_model_calls(1) |
| task_decision.py | 351 | decision call assembly; saved-call replay checks; decision-exchange protocol (request_context lookups: child_options, composition_information, own attempts); presentation-aware completion with this episode's prompt renderer | import:episode_work_report(1), import:providers(1), import:runtime(2), providers._ORIGINAL_MODEL_COMPLETE(2), providers._ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION(2), providers._ORIGINAL_MODEL_INSTANCE_DICT(3), runtime._action_generation_schema(2), runtime.apply_state_frame(1), runtime._ASSIGNMENT_TRANSPORT(1), runtime._category_yield_parameters(1), runtime.child_option_information(2), runtime.composition_lookup_schema(2), runtime.CONTRACT_INFORMATION_OPERATIONS(1), runtime.DECISION_CONTEXT_VERSION(2), runtime.DECISION_EXCHANGE_PROTOCOL(5), runtime._digest(1), runtime.Draft202012Validator(1), runtime.infernal_receiver_context(2), runtime.instructional_model_context(4), runtime.is_contract_information(1), runtime._json(14), runtime.json(3), runtime.lookup_attempts(1), runtime.Mapping(4), runtime.model_snapshot(2), runtime._object(3), runtime._plain(2), runtime._recorded_action_generation_schema(1), runtime._recorded_assignment_transport(1), runtime._references_in(1), runtime.requested_contract_information(2), runtime.schema_failure_diagnostic(2), runtime.sqlite3(1), runtime.state_frame(1), runtime.ValidationError(5), runtime.WorkflowError(14), runtime.yield_table(1), wf.available_child_roles(1), wf.binding_context(1), wf.contract_information_profile(1), wf.contract_information_reply(1), wf.controller_binding(1), wf.decision_exchanges(4), wf.decision_protocol(3), wf.episode_bindings(1), wf.execute(1), wf.execution_expectations(1), wf.freeze_contract_information(1), wf.freeze_literature_numerical_contracts(1), wf.history_preview(1), wf.journal(3), wf.launch_instructions(2), wf.native_estimation_context(1), wf.numerical_contracts(1), wf.pending_work(1), wf.permits_common_action(1), wf.provider(3), wf.receipts(4), wf.resource_context(1), wf.resource_estimator(4), wf.run_id(1), wf.services(2), wf.shared_information_context(1), wf.specialist(1), wf.store(2), wf.uses_received_record_context(2), wf.validate_contract_information(5), wf.waiting_support(1), table:runtime_model_calls(8) |
| task_instructions.py | 25 | instruction composition: defaults + specialist; reasoning commit only if reason permitted; pending-child-delivery repair text; wait/native-event paragraphs (inactive: no wait); exchange-protocol history replacement | import:library.scientific_instruction_text(1), import:runtime_prompt(1), runtime_prompt.DECISION_EXCHANGE_PROTOCOL(1), runtime_prompt.INSTRUCTIONS(4), runtime_prompt.REASONING_COMMIT_REQUIREMENT(1), wf.binding_context(1), wf.decision_protocol(1), wf.knowledge(1), wf.launch_instructions(1), wf.native_event_information(1), wf.permits_common_action(3), wf.specialist(1) |
| task_presentation.py | 48 | frame-based prompt state; renders this episode's TASK prompt | import:decision_context(1), import:library.literature_source_presentation(1), import:library.scientific_decision_presentation(1), self.scientific_prompt_states(4) (provider attribute) |
| task_reading_prompt.py | 37 | full TASK/STEERING text and section order (see above) | import:library.literature_source_presentation(1) |
| task_report_delivery.py | 23 | finish: credit+handles without contract; form_with_facts with contract | import:runtime(2), runtime.form_with_facts(1), runtime._json(2), runtime.json(1), runtime.Record(2), wf.binding_context(1), wf.episode_bindings(1), wf.facts(1), wf.journal(2), wf.pending_handles(1), wf.release(2), wf.source_credit_view(1), table:runtime_forms(2) |
| task_state.py | 108 | source state (report values/basis, feedback, last outcome); a failed selected tool/reason action becomes a failed outcome unit with credit (returned failure enters the iterator) | import:episode_source_failure(1), import:runtime(2), runtime.ActionLeaf(1), runtime.EFFECT_VERSION(1), runtime.Episode(1), runtime.interpretation_schema(1), runtime._json(2), runtime.json(4), runtime._object(1), runtime._plain(1), runtime.Record(1), wf.archive(1), wf.completions(4), wf.controller_value(1), wf.execution_binding(4), wf.inprocess_replay(7), wf.journal(5), wf.progress_provider(2), wf.recover_commissions(1), wf.run_id(1), wf.source_credit_view(1), wf.store(2), table:runtime_actions(5) |
| task_suspension.py | 9 | records suspension condition | wf.execution_backend(1), wf.execution_handle(2) |
| to_parent.py | 18 | fact_sources; resolve via reference_in_context; validate_report | none directly (reference_in_context from episode_bindings via contracts) |
| waiting.py | 8 | supports_wait False | none |
| yield_estimator.py | 12 | no own continuation task, no own yield controller | none |
