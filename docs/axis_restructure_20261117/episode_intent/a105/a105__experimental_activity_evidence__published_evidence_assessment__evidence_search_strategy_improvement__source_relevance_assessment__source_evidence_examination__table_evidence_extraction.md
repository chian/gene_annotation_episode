# a105/…/source_evidence_examination/table_evidence_extraction: intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction/<file>`.
I read the 21 files directly in the folder (3,167 lines), `grading/` (3 files, 77 lines) and `scoring/` (2 files,
12 lines). There are no `prompts/`, `tools/` or `tests/` subfolders. I compared every file with the parent
(`source_evidence_examination`) and the two siblings. The old-runner names are listed per file below and in
`runs/carry_over/calls/a105_02.tsv`.

## What it is for (its goal, in its own words)

The table/sheet reading episode. Its method_loop role is `literature_table`, and it is commissioned by
`source_evidence_examination` (`episode.commissioning_parent`). The docstring says "C7 binding for C10 assignments;
no model connection or private loop." The role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_table']`)
reads:

> "Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes
> deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their
> native identity. Article XML tables are read through exact original-source windows."

## Task and instructions

`goal.LiteratureGoal.instructions` returns the role instruction followed by the shared iterative-investigation
paragraph. The parent uses the same paragraph:

> "This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted child forms
> inform later choices; no child order, reading quota or complete-document requirement is prescribed. A one-off
> search/read is an ordinary tool. A supplied reading selector is context, not an automatically executed action.
> Preserve the source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors.
> Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications can
> advance the investigation. Commit interpretations with the common reasoning action and update only the parent's
> declared typed form in that same work call. Navigation, byte coverage and repeated reading earn no scientific credit
> by themselves. The commissioned task's own yield settings guide continuation."

`planning_context` returns:
- `objective`, `proposed_annotation_ref` and `commissioned_result`;
- `progress_definition`, which is the credit record;
- `planning_question`, which here is the instructions above. The parent instead asks a fixed question.

`task_instructions.py` is identical to the parent's.

The commissioned task schema and its checks (`goal.task_schema`, `commissioned_task`, version
`literature_local_task_v1`) are the same as the parent's:
- the task kinds are verified_source_leads, assessment, screening, measurement, a105_experiments and a105_assembly;
- the task must match the typed return and the requested components;
- every source must be inside the assigned page. `commissioned_task` takes the page from `assignment['page']`.

## What it reads from its parent's assignment

`from_parent.LiteratureAssignment.assignment_schema` reads:
`{version: 'reading_assignment_v1', page: _PAGE, selection: anyOf[_TABLE, _WINDOW]}`. The two shapes are:
- `_TABLE`: `{source_ref, sheet_key, offset, limit, header_row (int ≥ 1 or null),
  where ({column (A–Z letters or null), match (equals|contains), value, case_sensitive} or null)}`, an XLSX sheet
  selection;
- `_WINDOW`: `{source_ref, representation, offset, limit}`, an original-source window for an article XML table.

In both cases `windows = [selected]`. The schema also carries `literature_task`, `proposed_annotation_ref`,
and the requested-component arrays of every enabled scientific family (the same list as the parent's).

`_validate_assignment` checks:
- the page: its artifact matches its representation, and the page and context refs are in scope;
- the selection: same `source_ref` as the page. For a window only (`_TABLE` has no `representation`), it must also
  have the same representation and an `offset` not past the artifact size.

`prepare_assignment` checks:
- it fills `credit_unit` and `yield_settings` from this episode's private yield binding for the task key;
- a supplied different value raises `literature_task_supplied_yield_binding_mismatch`;
- the proposed annotation must equal the parent's;
- the page must lie inside the parent page's source (`_validate_parent_page` with `_parent_page_schema`).

## Children it may commission

None. `_CHILDREN['literature_table'] = ()`. `permitted_common_actions` still lists `child` and `redeliver_report`,
copied from the shared shape, but no child role is available. There are no `to_child_*` / `from_child_*` files.
`received_evidence.received_form_references` is a copy of the parent's child-cell admission and has no caller here.

## Decision state and what it shows the model

The state is the same as the parent's (`task_state.LiteratureTaskState`): `report_values` starts from
`initial_report`, plus feedback, last outcome and `interpret_schema`.

The decision context (`task.py` line 149) has the same keys as the parent's, minus the annotation-axis branch. It also
adds `internal_summary.decision_context`:
- `literature_assignment` and `literature_source_custody` (the page source only);
- `own_literature_outcomes` (paged by `outcome_page_size`, default 8) and `literature_history_meaning`;
- `literature_goal_plan` (the planning context; the parent's key is `source_examination_goal`);
- the examined source inputs and the experimental-work marker;
- the scientific display and receipt contexts, owned population sources, the last failed population attempt, and the
  current completed work / scoring sheets.

## Tools it offers

Common actions: `tool`, `reason`, `child`, `redeliver_report`.

`task.LiteratureOperations.catalog` offers the services catalog filtered to `_ACCESS_TOOLS`:
- `state.query`;
- `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`;
- `image.view`;
- `source.archive.members`, `source.archive.extract`;
- `source.xlsx.sheets`, `source.xlsx.rows`;
- `source.pdf.info`, `source.pdf.text`, `source.pdf.page`;
- `execution.estimate`, restricted to its xlsx branches.

Acquisition tools are never added (this catalog has no acquisition branch at all). With `rate_population`, the
`literature.*.populate` operations are added under their flags.

`source_operations._tool_arguments` does the following:
- validates operands against the input schema;
- requires every source ref, including nested sheet, model and covariance refs, to lie inside the page's source;
- rejects `source.xlsx.rows` on any sheet other than the assigned `sheet_key` (`literature_table_sheet_mismatch`);
- authorizes reads on the endpoint, summary-precision, comparison and concentration-window repositories.

`execute` returns `invalid` outcomes with feedback for contract errors.

Reasoning (`grading/experimental_interpretation.py`) is the same as the parent's:
- with assay grading on, the required-grading action commits the interpretation and its grading sheets together, and
  `investigation_finding` is required;
- `source_lead` is allowed for `verified_source_leads`.

## How its credit is counted

`credit.LiteratureTaskCredit`, identical to the parent's: `credit_unit × answered items`, finite and never bounded.
Per task kind it counts:
- relevant lead dispositions;
- full span coverage by no-applicable-evidence screening;
- one current anchored assessment;
- a fully populated quantity sheet;
- one current matching grading sheet per requested experiment;
- one complete aggregation sheet.

`revision_credit` and `activity_credit` are False, and annotation support is kept separate.

## Continuation (yield estimator and settings)

`yield_estimator.py` is identical to the parent's. `yield_bindings` are keyed by task key, each with
`{credit_unit, kind, cutoff, uncertainty_alpha}`:
- `verified_source_leads` uses kind `accumulation`. This is the new accumulation estimator.
- Every other task uses `remaining_commissioned_credit`, with capacity `credit_unit × (experiments | 1)`. The forecast
  is capped at the remaining credit and is exactly zero when everything is earned. This is the new
  completion-with-a-target estimator.

## What it reports to its parent

`to_parent.LiteratureReport`, the same as the parent's:
- fact sources: the enabled scientific cell families plus `literature_screening_answers` and
  `literature_source_lead_dispositions`;
- facts at completion and `current_report_facts`: `literature_completed_work` and `literature_current_scoring_sheets`;
- `validate_received_report`: answers must equal the saved work, cells must be exactly the requested subsets, and
  worksheet links are checked.

The parent's `from_child_table_evidence_extraction` admits these cells into the parent's repositories.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | none | none |
| binding_record.py | 43 | the configuration record with this binding id | none |
| configuration.py | 119 | the same flags as the parent; `reference_evidence` classmethod (a caller-assigned reference-source investigation, `rate_population` default True) | root.a105.composition_information, root.a105.library.literature_controlled_response_storage, root.a105.library.literature_gel_storage |
| credit.py | 289 | task credit, lead schema/validation, screening answers | root.a105.communication, root.a105.domain ×3, root.a105.finding_validity, root.a105.scientific_findings, root.a105.library (assay_inputs ×2, sheet_updates ×2, assay_grading_storage, required_grading, a105_aggregation_storage), table runtime_actions ×4, table runtime_report_attempts ×2, workflow.scientific_projector_for_context, workflow.projector_receipt_arguments, workflow.projection_view |
| decision_presentation.py | 18 | none | root.a105.runtime ×2, root.a105.episode_work_report, self.workflow.controller_binding, _category_yield_parameters ×2, yield_table ×2 |
| episode.py | 70 | role `literature_table`, binding path, commissioning parent | root.a105.library.literature_experimental_prompt |
| from_parent.py | 281 | the reading assignment with a table or window selection; selection and page checks; yield-binding fill | root.a105.library ×76 (component constants of 38 storage/calculation modules, each imported twice: own schema and `_parent_page_schema`) |
| goal.py | 131 | task schema, commission checks, instructions-as-planning-question | root.a105.communication, root.a105.domain ×2, root.a105.library.literature_assay_grading, root.a105.library.literature_quantity_storage |
| internal_summary.py | 311 | decision context, with `literature_goal_plan` | self.services.workflow ×2, self.services.workflow.store ×2, workflow.run_id ×2, workflow.store ×2, table runtime_actions ×2, root.a105.library ×16 (renderers, task selection, source inputs, work report, storages) |
| received_evidence.py | 157 | received-cell facts and tokens; `received_form_references` (no caller) | root.method_loop.durable, self.services.workflow.store, root.a105.library ×16 storages |
| scientific_records.py | 357 | one repository per scientific family; `_population_routes` | self.services.workflow.store ×34, self.services.workflow.run_id ×34, root.a105.library ×74 |
| source_contracts.py | 42 | the family-wide `ROLES` and `_CHILDREN`, `_WINDOW`, the role instruction | root.a105.communication, root.communication, root.a105.composition_information, root.a105.domain, root.a105.episode_bindings, root.a105.experimental_database_acquisition, root.a105.library, root.a105.library.literature_population_catalog |
| source_operations.py | 80 | operand and source-containment checks; `source.xlsx.rows` must use the assigned `sheet_key` (`literature_table_sheet_mismatch`) | getattr(self.services,'workflow') ×2, root.a105.library.literature_source_access ×2, root.a105.library.literature_assay_inputs |
| source_references.py | 31 | `_require`, artifact by representation, ancestry | none |
| task.py | 310 | catalog and tool execution; the rest is the old loop | 95 runner members (self.workflow.journal ×11, store ×12, execution_binding ×7, inprocess_replay ×4, binding_context ×4, …), root.a105.runtime ×2, root.a105.composition_information, root.a105.episode_source_failure, root.a105.literature_contract_error, root.communication, root.episode_contract_information, root.episode_journal, root.provider_errors, root.task_action_units, table runtime_actions ×9, runtime_forms ×2, runtime_model_calls ×2, runtime_episodes |
| task_decision.py | 352 | none (the model call and exchange protocol) | 56 runner members (validate_contract_information ×5, receipts ×4, decision_exchanges ×4, resource_estimator ×4, …), root.a105.runtime ×2, root.a105.providers ×2, root.providers, root.episode_journal, table runtime_model_calls ×8, _category_yield_parameters, yield_table |
| task_instructions.py | 28 | the pending-delivery repair text | root.a105.runtime_prompt, root.a105.library.literature_investigation_prompt, source.workflow.* ×10 |
| task_state.py | 108 | initial report values, interpretation schema | 34 runner members (inprocess_replay ×7, journal ×5, completions ×4, execution_binding ×4, …), workflow.context, workflow.grains, root.a105.runtime ×2, root.a105.episode_source_failure, table runtime_actions ×5 |
| to_parent.py | 322 | fact sources, facts, received-report validation | root.a105.domain ×2, root.communication, self.services.workflow.store ×4, workflow.store ×2, getattr(self.services,'workflow'), root.a105.library ×47 (cell schemas, worksheet, numerical contracts, work report) |
| waiting.py | 8 | `supports_wait = False` | none |
| yield_estimator.py | 109 | yield bindings, remaining-commissioned-credit forecast | root.a105.numerical, YieldController ×4, YieldParameters ×3, estimate_score_yield ×3, YieldEstimate ×2, NumericBand ×2, STATUS_NORMAL ×2 |
| grading/assay_subscoring.py | 17 | the grading repository when grading is on | self.services.workflow.store, self.services.workflow.run_id, root.a105.library.literature_assay_grading_storage |
| grading/experimental_interpretation.py | 60 | the required-grading reasoning and source-lead reasoning | self.services.workflow.store, root.a105.runtime, root.a105.literature_contract_error, root.communication, root.episode_contract_information, root.episode_journal, root.task_action_units |
| grading/`__init__.py` | 0 | none | none |
| scoring/experimental_main_sheet.py | 12 | the aggregation repository over grade rows | self.services.workflow.store, self.services.workflow.run_id, root.a105.library.literature_a105_aggregation_storage |
| scoring/`__init__.py` | 0 | none | none |

## Where it differs from its parent and siblings

- **Selection.** It is `_TABLE` (an XLSX sheet with rows, header and where-filter) or one `_WINDOW` (an XML table).
  Passage extraction takes a list of separate spans, and source coverage takes one window.
- **No private scientific copies.** Every grading, scoring, storage, prompt and calculation module is imported from the
  old shared `root/a105/library`, which is never restored. The parent has private copies under `grading/`,
  `scoring/`, `tools/` and `prompts/`. The scientific code this episode needs must come from those copies or the
  library placement (see `runs/placement_plan/placement.tsv`).
- **Roles and children.** `ROLES` and `_CHILDREN` hold the whole literature family table. It has no children, yet
  `child` and `redeliver_report` stay in its common actions.
- **Planning.** The planning question is its own instructions, under the key `literature_goal_plan`.
- **Resource estimates.** In `task_decision`, the job-source resource-estimate branch is `pass`.
- **Table rule.** Only this episode checks the sheet: `source_operations._tool_arguments` (lines 25–27) rejects
  `source.xlsx.rows` on another sheet than the assigned `sheet_key`. The parent's `task._tool_arguments` keeps the
  same check, under `context.role == 'literature_table'`.
- **Sibling copies.** Apart from the role name, the binding path, the selection shape and that sheet check, it is
  byte-identical to passage_evidence_extraction and source_coverage_improvement.

## Carried over

The old files were not readable in this checkout (no git history of 97308b94c); the carry was written from this record, the old-call table and the library. Rows with a first-three-column copy of `runs/carry_over/functions/a105__experimental_activity_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__table_evidence_extraction.tsv`. Old tests: none (the episode had no `tests/` folder).

| old_file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() are deleted (README 3) |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() are deleted (README 3) |
| configuration.py | LiteratureConfiguration | machinery | configuration values become the run's settings (ctx.settings) or constants of the file that uses them; old binding configuration is not carried |
| configuration.py | LiteratureConfiguration.__init__ | machinery | configuration values become the run's settings (ctx.settings) or constants of the file that uses them; old binding configuration is not carried |
| configuration.py | LiteratureConfiguration.reference_evidence | machinery | root-only reference_evidence configuration (caller-assigned reference investigation); not this episode's; settings are the run's |
| credit.py | _resolve | episode function | already in library: literature/grading/literature_task_credit.py::_resolve (imported by task.py) |
| credit.py | lead_schema | episode function | already in library: literature/grading/literature_task_credit.py::lead_schema (imported by task.py) |
| credit.py | lead_return_schema | episode function | not carried: the lead disposition field is declared by messages/final_to_parent.py RETURN_FORM (LEADS, a list) |
| credit.py | validate_lead | episode function | task.py::validate_source_lead (private copy on custody; library candidate) |
| credit.py | lead_dispositions | episode function | credit.py::lead_dispositions (private copy; library candidate) |
| credit.py | screening_schema | episode function | not carried: the screening field is declared by messages/final_to_parent.py RETURN_FORM (SCREENING, a list) |
| credit.py | _current_assessments | episode function | credit.py::current_assessments (private copy over records) |
| credit.py | screening_answers | episode function | credit.py::screening_answers (private copy; library candidate) |
| credit.py | LiteratureTaskCredit | episode function | credit.py::credit (the class becomes credit(summary, records)) |
| credit.py | LiteratureTaskCredit.as_record | episode function | credit.py::credit_binding (the credit projector's as_record(), README 3d) |
| credit.py | LiteratureTaskCredit.__call__ | episode function | credit.py::credit (credit_unit x answers; the commission-equality, scope and receiver checks are the old runner's custody/commission checks and are not carried) |
| credit.py | LiteratureTaskCredit._answers | episode function | credit.py::answers |
| credit.py | measured_answers | episode function | credit.py::measured_answers (BLOCKED-ON-STORE-ACCESS: sheet reads) |
| credit.py | graded_experiment_answers | episode function | credit.py::graded_experiment_answers (BLOCKED-ON-STORE-ACCESS: sheet reads) |
| credit.py | assembled_answers | episode function | credit.py::assembled_answers (BLOCKED-ON-STORE-ACCESS: sheet reads) |
| credit.py | LiteratureCredit | machinery | class LiteratureCredit: credit_kind/credit_view/credit_projector wiring of the old scientific_credit service |
| credit.py | LiteratureCredit._scientific_credit_invocation | machinery | old credit wiring (credit_kind, credit_view, services.scientific_credit invocation, credit_projector) |
| credit.py | LiteratureCredit.credit_kind | machinery | old credit wiring (credit_kind, credit_view, services.scientific_credit invocation, credit_projector) |
| credit.py | LiteratureCredit.credit_view | machinery | old credit wiring (credit_kind, credit_view, services.scientific_credit invocation, credit_projector) |
| credit.py | LiteratureCredit.credit_projector | machinery | old credit wiring (credit_kind, credit_view, services.scientific_credit invocation, credit_projector) |
| decision_presentation.py | prepare_completed_work | machinery | prepare_completed_work and decision_yield_table read the old runtime and controller binding; the yield table is messages/internal_summary.py (yield_table of the library over view.controller_state), the completed-work context belongs to the population route (not built) |
| decision_presentation.py | decision_yield_table | machinery | prepare_completed_work and decision_yield_table read the old runtime and controller binding; the yield table is messages/internal_summary.py (yield_table of the library over view.controller_state), the completed-work context belongs to the population route (not built) |
| episode.py | LiteratureEpisode | episode function | episode.py::TableEvidenceExtraction (the one class of the ten-file form) |
| episode.py | LiteratureEpisode._enabled | machinery | old mix-in hooks (_enabled, contract_information_*, _role, context_hook_applies): contract-information profile and role dispatch of the old runner |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | old mix-in hooks (_enabled, contract_information_*, _role, context_hook_applies): contract-information profile and role dispatch of the old runner |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | old mix-in hooks (_enabled, contract_information_*, _role, context_hook_applies): contract-information profile and role dispatch of the old runner |
| episode.py | LiteratureEpisode._role | machinery | old mix-in hooks (_enabled, contract_information_*, _role, context_hook_applies): contract-information profile and role dispatch of the old runner |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py::CHILD_SLOTS = {} (no child) |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py::CHILD_SLOTS = {} (no child) |
| episode.py | LiteratureEpisode.child_assignment_schema | episode function | task.py::CHILD_SLOTS = {} (no child) |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | old mix-in hooks (_enabled, contract_information_*, _role, context_hook_applies): contract-information profile and role dispatch of the old runner |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM and read_from_parent) |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | LiteratureAssignment._validate_page | episode function | messages/read_from_parent.py::read_from_parent (span/selection against page; the Store checks of the page are a commission check and are not carried) |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py::read_from_parent (selection against page) |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (the credit_unit/yield_settings fill and the proposed-annotation/parent-page equality checks are not carried: credit_unit is a field of the commissioned task, cost and parameters are settings, a wrong commission fails) |
| from_parent.py | LiteratureAssignment._parent_page_schema | machinery | check of the page against the parent's page: a commission check against another episode (rule 1), not carried |
| from_parent.py | LiteratureAssignment._validate_parent_page | machinery | check of the page against the parent's page: a commission check against another episode (rule 1), not carried |
| goal.py | _yield_kind | episode function | yield_estimator.py::yield_controller (kind choice) |
| goal.py | _task_key | episode function | messages/read_from_parent.py::task_key |
| goal.py | task_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM (literature_task field) |
| goal.py | _return_sources | machinery | check of the return schema against the original return contract (x-source scan): a commission check against the parent, not carried |
| goal.py | _return_components | machinery | check of the return schema against the original return contract (x-source scan): a commission check against the parent, not carried |
| goal.py | commissioned_task | episode function | messages/read_from_parent.py::read_from_parent (task kind, axis, credit_unit and experiments checks) |
| goal.py | continuation_task | episode function | messages/read_from_parent.py::task_key |
| goal.py | task_schema_variants | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM (task kinds and answer kinds) |
| goal.py | required_source | episode function | messages/final_to_parent.py::CELLS (the cell family each task kind requires) |
| goal.py | validate_commission | episode function | messages/read_from_parent.py::read_from_parent (duplicate experiments); requested-component checks are commission checks and are not carried |
| goal.py | LiteratureGoal | episode function | goal.py (GOAL, UNIT, RESULT) and task.py::instructions |
| goal.py | LiteratureGoal.instructions | episode function | goal.py::GOAL and task.py::instructions |
| goal.py | LiteratureGoal.planning_context | episode function | messages/internal_summary.py (assignment, credit_binding, controller yield table) |
| grading/assay_subscoring.py | AssaySubscoring | episode function | library: literature/storage/experimental_activity_evidence/literature_assay_grading_storage.py::LiteratureAssayGradingRepository (already in library; called by task.py::reason, library not carried) |
| grading/assay_subscoring.py | AssaySubscoring._required_grading_repository | episode function | library: literature/storage/experimental_activity_evidence/literature_assay_grading_storage.py::LiteratureAssayGradingRepository (already in library; called by task.py::reason, library not carried) |
| grading/assay_subscoring.py | AssaySubscoring._assay_grading_repository | episode function | library: literature/storage/experimental_activity_evidence/literature_assay_grading_storage.py::LiteratureAssayGradingRepository (already in library; called by task.py::reason, library not carried) |
| grading/experimental_interpretation.py | ExperimentalInterpretation | episode function | task.py::reason |
| grading/experimental_interpretation.py | ExperimentalInterpretation.reasoning_action_schema | episode function | task.py::reason_schema (library literature_required_grading.action_schema) |
| grading/experimental_interpretation.py | ExperimentalInterpretation.reasoning_has_task_content | episode function | task.py::empty_commit and task.py::action |
| grading/experimental_interpretation.py | ExperimentalInterpretation.execute_reasoning | episode function | task.py::reason (library literature_required_grading.execute; BLOCKED, library not carried) |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py::internal_summary and task.py::decide |
| internal_summary.py | LiteratureSummary.initial_decision_context | episode function | messages/internal_summary.py::internal_summary and task.py::decide |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py::internal_summary and task.py::decide |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _owned_population_task_sources ) |
| internal_summary.py | LiteratureSummary._population_task_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _population_task_context ) |
| internal_summary.py | LiteratureSummary._concentration_window_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _concentration_window_display_context ) |
| internal_summary.py | LiteratureSummary._measurement_comparison_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _measurement_comparison_display_context ) |
| internal_summary.py | LiteratureSummary._summary_precision_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _summary_precision_display_context ) |
| internal_summary.py | LiteratureSummary._endpoint_signal_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _endpoint_signal_display_context ) |
| internal_summary.py | LiteratureSummary._controlled_response_bindings | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _controlled_response_bindings ) |
| internal_summary.py | LiteratureSummary._gel_bindings | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _gel_bindings ) |
| internal_summary.py | LiteratureSummary._gel_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _gel_display_context ) |
| internal_summary.py | LiteratureSummary._received_fact_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _received_fact_display_context ) |
| internal_summary.py | LiteratureSummary._native_rate_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _native_rate_display_context ) |
| internal_summary.py | LiteratureSummary._native_rate_domain_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _native_rate_domain_display_context ) |
| internal_summary.py | LiteratureSummary._native_rate_meaning_display_context | episode function (unplaced) | UNPLACED: population route not built (population-route display context (not built): _native_rate_meaning_display_context ) |
| received_evidence.py | LiteratureReceivedEvidence | machinery | received-cell admission and receipt tokens of the old receipts bookkeeping; the copy of the parent's child-cell admission has no caller here (no child) |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | received-cell admission and receipt tokens of the old receipts bookkeeping; the copy of the parent's child-cell admission has no caller here (no child) |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | machinery | received-cell admission and receipt tokens of the old receipts bookkeeping; the copy of the parent's child-cell admission has no caller here (no child) |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | machinery | received-cell admission and receipt tokens of the old receipts bookkeeping; the copy of the parent's child-cell admission has no caller here (no child) |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | machinery | received-cell admission and receipt tokens of the old receipts bookkeeping; the copy of the parent's child-cell admission has no caller here (no child) |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | received-cell admission and receipt tokens of the old receipts bookkeeping; the copy of the parent's child-cell admission has no caller here (no child) |
| scientific_records.py | LiteratureScientificRecords | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_rate_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_calibration_recovery_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_rate_observation_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_rate_replicate_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_quantity_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_assay_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_amount_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_optical_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_kinetic_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_binding_interaction_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_ratio_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_binding_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_binding_model_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_transport_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_figure_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_ratio_source_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_controlled_response_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords.literature_gel_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._endpoint_signal_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._concentration_window_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._measurement_comparison_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._summary_precision_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._rate_grid_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v2_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v3_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._product_coupling_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._measurement_validation_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._ion_discrimination_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._channel_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._completion_time_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._active_site_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._assay_grading_source_cells | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._parent_depletion_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._stoichiometric_balance_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._product_partition_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._binding_interaction_model_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._kinetic_model_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._ratio_source_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._controlled_response_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._gel_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._native_rate_meaning_repository | episode function | already in library: literature/storage/experimental_activity_evidence/* repositories (one per scientific family; the population route that builds them is not built here) |
| scientific_records.py | LiteratureScientificRecords._population_routes | episode function (unplaced) | UNPLACED: population route not built (population-route dispatch of the old runner (not built) ) |
| scoring/experimental_main_sheet.py | ExperimentalMainSheet | episode function | library: literature/storage/experimental_activity_evidence/literature_aggregation_storage.py (already in library; the aggregation repository) |
| scoring/experimental_main_sheet.py | ExperimentalMainSheet._a105_aggregation_repository | episode function | library: literature/storage/experimental_activity_evidence/literature_aggregation_storage.py (already in library; the aggregation repository) |
| source_contracts.py | _required_grading_logic | episode function | final_to_parent.py::cells (required grading logic: library literature_required_grading, called by task.py::reason) |
| source_contracts.py | _population_catalog | episode function | goal.py::GOAL (role instruction) and messages/read_from_parent.py::ASSIGNMENT_FORM (population catalog: already in library literature/forms/experimental_activity_evidence/literature_population_catalog.py) |
| source_operations.py | LiteratureSourceOperations | episode function | task.py::run_access_tool (text-witness materialization is the library's materialize_text_witness_inputs, called inside literature_required_grading.execute) |
| source_operations.py | LiteratureSourceOperations._tool_arguments | episode function | task.py::admitted (operand schema, source containment and the sheet_key lock) and task.py::run_access_tool |
| source_operations.py | LiteratureSourceOperations._materialize_text_arguments | episode function | task.py::run_access_tool (text-witness materialization is the library's materialize_text_witness_inputs, called inside literature_required_grading.execute) |
| source_references.py | LiteratureReferences | episode function | task.py::within_source |
| source_references.py | LiteratureReferences._require | episode function | task.py::within_source (read_record_in_scope of the library) |
| source_references.py | LiteratureReferences._artifact | episode function | task.py::validate_source_lead (artifact by representation) and credit.py::screening (messages/internal_summary.py) |
| source_references.py | LiteratureReferences._within_source | episode function | task.py::within_source |
| task.py | LiteratureOperations | episode function | task.py::run_access_tool and the TOOLS table |
| task.py | LiteratureOperations.permitted_common_actions | machinery | common-action list (tool, reason, child, redeliver_report) of the old loop; the closing report is the report tool |
| task.py | LiteratureOperations.catalog | episode function | task.py::catalog and task.py::offered |
| task.py | LiteratureOperations.execute | episode function | task.py::run_access_tool |
| task.py | LiteratureTask | episode function | task.py::decide and task.py::action |
| task.py | LiteratureTask.next | episode function | task.py::decide |
| task.py | LiteratureTask.apply_response | episode function | task.py::action |
| task.py | LiteratureTask.execute | episode function | task.py::TOOLS (run_access_tool, reason, report) |
| task.py | LiteratureTask.finish | episode function | messages/final_to_parent.py::final_to_parent |
| task_decision.py | LiteratureTaskDecision | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py::decide (the model request); the provider call and exchange are the system's |
| task_decision.py | LiteratureTaskDecision.instructions | episode function | task.py::instructions |
| task_decision.py | LiteratureTaskDecision.decision_completion | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_decision.py | LiteratureTaskDecision.interpretation_context | episode function | task.py::decide (context) |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop, exchange schema/response/history validation and decision completion (exchange_decision), receipts and resource-estimate branch |
| task_instructions.py | instructions | episode function | task.py::instructions (the pending-delivery repair text and wait paragraphs are not carried) |
| task_state.py | LiteratureTaskState | episode function | messages/internal_summary.py::internal_summary (report values from the outcomes; the interpretation schema is view.records.reasoning_schema()) |
| task_state.py | LiteratureTaskState.__init__ | episode function | messages/internal_summary.py::internal_summary (report values from the outcomes; the interpretation schema is view.records.reasoning_schema()) |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | restore/checkpoint, execution-context binding, suspension and effect recording of the old runner (bind_execution_context) |
| task_state.py | LiteratureTaskState.suspension_changed | machinery | restore/checkpoint, execution-context binding, suspension and effect recording of the old runner (suspension_changed) |
| task_state.py | LiteratureTaskState.record_execution_failure | machinery | restore/checkpoint, execution-context binding, suspension and effect recording of the old runner (record_execution_failure) |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | restore/checkpoint, execution-context binding, suspension and effect recording of the old runner (restore_checkpoint) |
| task_state.py | LiteratureTaskState.restore | machinery | restore/checkpoint, execution-context binding, suspension and effect recording of the old runner (restore) |
| task_state.py | LiteratureTaskState.record_effect | machinery | restore/checkpoint, execution-context binding, suspension and effect recording of the old runner (record_effect) |
| task_state.py | LiteratureTaskState.checkpoint | machinery | restore/checkpoint, execution-context binding, suspension and effect recording of the old runner (checkpoint) |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py::final_to_parent |
| to_parent.py | LiteratureReport.current_report_facts | episode function | messages/internal_summary.py (investigation_findings, graded_sheet_refs) |
| to_parent.py | LiteratureReport._rate_fact_sources | episode function (unplaced) | UNPLACED: population route not built (population-route cell families (rate): not built, not declared in RETURN_FORM ) |
| to_parent.py | LiteratureReport._rate_facts | episode function (unplaced) | UNPLACED: population route not built (population-route cell families (rate): not built, not declared in RETURN_FORM ) |
| to_parent.py | LiteratureReport.validate_received_report | episode function | messages/final_to_parent.py::validate_report (answers computed from the same summary; the requested-subset and worksheet-link checks belong to the cell families: BLOCKED with cells) |
| to_parent.py | LiteratureReport.resolve | machinery | reference resolution of the old report delivery (resolve(context, reference, namespace)); the reference is read through custody |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py::validate_report |
| waiting.py | LiteratureWaiting | machinery | supports_wait = False: wait machinery; this episode has no wait tool |
| waiting.py | LiteratureWaiting.supports_wait | machinery | supports_wait = False: wait machinery; this episode has no wait tool |
| yield_estimator.py | validate_yield_bindings | machinery | old checks of the cutoff and alpha: the controllers' own checks |
| yield_estimator.py | _RemainingCommissionedCredit | machinery | episode-local estimator class: the CompletionYieldController of yield_control replaces it (README 7b) |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | machinery | episode-local estimator: replaced by CompletionYieldController |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | machinery | estimator as_record: deleted |
| yield_estimator.py | _private_yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | machinery | finite controller class: CompletionYieldController replaces it |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | machinery | finite controller: CompletionYieldController replaces it |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | machinery | finite controller transition: CompletionYieldController replaces it |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py::task_key |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py::yield_controller |
