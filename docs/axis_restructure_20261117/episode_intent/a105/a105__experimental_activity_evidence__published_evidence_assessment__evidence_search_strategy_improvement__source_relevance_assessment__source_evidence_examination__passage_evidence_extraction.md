# a105/…/source_evidence_examination/passage_evidence_extraction: intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/<file>`.
I read the 21 files directly in the folder (3,164 lines), `grading/` (3 files, 77 lines) and `scoring/` (2 files,
12 lines). There are no `prompts/`, `tools/` or `tests/` subfolders. I compared every file with the parent
(`source_evidence_examination`) and the two siblings. The old-runner names are listed per file below and in
`runs/carry_over/calls/a105_02.tsv`.

## What it is for (its goal, in its own words)

The targeted-passage reading episode. Its method_loop role is `literature_targeted`, and it is commissioned by
`source_evidence_examination` (`episode.commissioning_parent`). The docstring says "C7 binding for C10 assignments;
no model connection or private loop." The role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_targeted']`)
reads:

> "Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications
> or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain
> separate; never concatenate them into a fabricated quotation."

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
`{version: 'reading_assignment_v1', page: _PAGE, selection: {spans: [_WINDOW, minItems 1]}}`. Each `_WINDOW` is
`{source_ref, representation, offset, limit}`. The schema also carries `literature_task`, `proposed_annotation_ref`,
and the requested-component arrays of every enabled scientific family (the same list as the parent's).

`_validate_assignment` checks:
- the page: its artifact matches its representation, and the page and context refs are in scope;
- every span: same `source_ref` as the page, same representation, `offset` not past the artifact size.

`prepare_assignment` checks:
- it fills `credit_unit` and `yield_settings` from this episode's private yield binding for the task key;
- a supplied different value raises `literature_task_supplied_yield_binding_mismatch`;
- the proposed annotation must equal the parent's;
- the page must lie inside the parent page's source (`_validate_parent_page` with `_parent_page_schema`).

## Children it may commission

None. `_CHILDREN['literature_targeted'] = ()`. `permitted_common_actions` still lists `child` and `redeliver_report`,
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

The parent's `from_child_passage_evidence_extraction` admits these cells into the parent's repositories.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | none | none |
| binding_record.py | 43 | the configuration record with this binding id | none |
| configuration.py | 119 | the same flags as the parent; `reference_evidence` classmethod (a caller-assigned reference-source investigation, `rate_population` default True) | root.a105.composition_information, root.a105.library.literature_controlled_response_storage, root.a105.library.literature_gel_storage |
| credit.py | 289 | task credit, lead schema/validation, screening answers | root.a105.communication, root.a105.domain ×3, root.a105.finding_validity, root.a105.scientific_findings, root.a105.library (assay_inputs ×2, sheet_updates ×2, assay_grading_storage, required_grading, a105_aggregation_storage), table runtime_actions ×4, table runtime_report_attempts ×2, workflow.scientific_projector_for_context, workflow.projector_receipt_arguments, workflow.projection_view |
| decision_presentation.py | 18 | none | root.a105.runtime ×2, root.a105.episode_work_report, self.workflow.controller_binding, _category_yield_parameters ×2, yield_table ×2 |
| episode.py | 70 | role `literature_targeted`, binding path, commissioning parent | root.a105.library.literature_experimental_prompt |
| from_parent.py | 281 | the reading assignment with spans; span and page checks; yield-binding fill | root.a105.library ×76 (component constants of 38 storage/calculation modules, each imported twice: own schema and `_parent_page_schema`) |
| goal.py | 131 | task schema, commission checks, instructions-as-planning-question | root.a105.communication, root.a105.domain ×2, root.a105.library.literature_assay_grading, root.a105.library.literature_quantity_storage |
| internal_summary.py | 311 | decision context, with `literature_goal_plan` | self.services.workflow ×2, self.services.workflow.store ×2, workflow.run_id ×2, workflow.store ×2, table runtime_actions ×2, root.a105.library ×16 (renderers, task selection, source inputs, work report, storages) |
| received_evidence.py | 157 | received-cell facts and tokens; `received_form_references` (no caller) | root.method_loop.durable, self.services.workflow.store, root.a105.library ×16 storages |
| scientific_records.py | 357 | one repository per scientific family; `_population_routes` | self.services.workflow.store ×34, self.services.workflow.run_id ×34, root.a105.library ×74 |
| source_contracts.py | 42 | the family-wide `ROLES` and `_CHILDREN`, `_WINDOW`, the role instruction | root.a105.communication, root.communication, root.a105.composition_information, root.a105.domain, root.a105.episode_bindings, root.a105.experimental_database_acquisition, root.a105.library, root.a105.library.literature_population_catalog |
| source_operations.py | 77 | operand and source-containment checks | getattr(self.services,'workflow') ×2, root.a105.library.literature_source_access ×2, root.a105.library.literature_assay_inputs |
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

- **Selection.** It is a list of spans (`{spans: [_WINDOW, …]}`); the instruction says the spans stay separate. Source
  coverage takes one window, and table extraction takes `_TABLE` or a window.
- **No private scientific copies.** Every grading, scoring, storage, prompt and calculation module is imported from the
  old shared `root/a105/library`, which is never restored. The parent has private copies under `grading/`,
  `scoring/`, `tools/` and `prompts/`. The scientific code this episode needs must come from those copies or the
  library placement (see `runs/placement_plan/placement.tsv`).
- **Roles and children.** `ROLES` and `_CHILDREN` hold the whole literature family table. It has no children, yet
  `child` and `redeliver_report` stay in its common actions.
- **Planning.** The planning question is its own instructions, under the key `literature_goal_plan`.
- **Resource estimates.** In `task_decision`, the job-source resource-estimate branch is `pass`.
- **Table rule.** There is no `literature_table` sheet check; only the table sibling has it.
- **Sibling copies.** It is byte-identical to source_coverage_improvement apart from the role name, the binding path
  and the selection shape.

## Carried over

Carried over on 19 November 2026 into the ten-file private binding (class `PassageEvidenceExtraction` in `episode.py`). One row per row of `runs/carry_over/functions/a105__experimental_activity_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.tsv` (192 rows: the first three columns are copied from it). Machinery is not carried and its reason is given; an episode function names its new file and name. "Library candidate" marks an episode function that stays in the episode's file because the library does not hold it yet. Where a row says BLOCKED-ON-STORE-ACCESS or "not placed" the item is in `docs/axis_restructure_20261117/carry_over_blocked/a105__experimental_activity_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.md`.

| old file | kind | name | class | new place or reason |
|---|---|---|---|---|
| binding_record.py | class | LiteratureBindingRecord | machinery | the binding's own as_record (README 3e): settings are journaled by the system |
| binding_record.py | method | LiteratureBindingRecord.as_record | machinery | the binding's own as_record (README 3e): settings are journaled by the system |
| configuration.py | class | LiteratureConfiguration | machinery | configuration record: its flags are ctx.settings keys read in task.py (rate_population and FLAGS); its yield bindings are settings['cost'] / settings['parameters'] (README 3d) |
| configuration.py | method | LiteratureConfiguration.__init__ | machinery | flag validation and yield-binding validation: settings are the run's; controller constructors raise on a bad cost or alpha (README 3d) |
| configuration.py | method | LiteratureConfiguration.reference_evidence | machinery | caller-assigned reference-source investigation entry (root-side configuration constructor); not this episode's commission |
| credit.py | function | _resolve | episode function | task.py resolve (private copy; library candidate) |
| credit.py | function | lead_schema | episode function | task.py lead_schema (private copy; library candidate) |
| credit.py | function | lead_return_schema | episode function | messages/final_to_parent.py RETURN_FORM field literature_source_lead_dispositions (a list field) |
| credit.py | function | validate_lead | episode function | task.py validate_lead (private copy on custody: store.require / store.get_artifact; library candidate) |
| credit.py | function | lead_dispositions | episode function | credit.py lead_dispositions (own validated leads from the unit outcomes; no admitted child forms: no child) |
| credit.py | function | screening_schema | episode function | messages/final_to_parent.py RETURN_FORM field literature_screening_answers (a list field) |
| credit.py | function | _current_assessments | episode function | credit.py current_assessments (BLOCKED-ON-STORE-ACCESS: FindingValidity / target_eligible, store._assessment_write_extent) |
| credit.py | function | screening_answers | episode function | credit.py screening_answers |
| credit.py | class | LiteratureTaskCredit | episode function | credit.py (module functions credit_binding, answers, credit) |
| credit.py | method | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding (the projector's as_record is episode content, README 3d) |
| credit.py | method | LiteratureTaskCredit.__call__ | episode function | credit.py credit (formula unchanged: credit_unit times answers, finite); the commission-mismatch checks are not carried (a wrong commission fails) |
| credit.py | method | LiteratureTaskCredit._answers | episode function | credit.py answers |
| credit.py | function | measured_answers | episode function | credit.py measured_answers (BLOCKED-ON-STORE-ACCESS: LiteratureQuantityRepository) |
| credit.py | function | graded_experiment_answers | episode function | credit.py graded_experiment_answers (BLOCKED-ON-STORE-ACCESS: LiteratureAssayGradingRepository, current_sheet_refs) |
| credit.py | function | assembled_answers | episode function | credit.py assembled_answers (BLOCKED-ON-STORE-ACCESS: LiteratureA105AggregationRepository, current_sheet_refs) |
| credit.py | class | LiteratureCredit | machinery | credit mix-in over services.scientific_credit (README 3d) |
| credit.py | method | LiteratureCredit._scientific_credit_invocation | machinery | workflow.scientific_projector_for_context / projector_receipt_arguments / projection_view (README 3d) |
| credit.py | method | LiteratureCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | LiteratureCredit.credit_view | machinery | services.scientific_credit view (README 3d) |
| credit.py | method | LiteratureCredit.credit_projector | episode function | credit.py credit / credit_binding (the projector is built per call) |
| decision_presentation.py | function | prepare_completed_work | episode function | not placed: completed_action_reports (root.a105.episode_work_report) has no module in the library; see unplaced_old_functions |
| decision_presentation.py | function | decision_yield_table | episode function | messages/internal_summary.py action_yields (yield_table over view.controller_state; the annotation-axis branch is root-only) |
| episode.py | class | LiteratureEpisode | machinery | hook-era mix-in class; replaced by episode.py PassageEvidenceExtraction |
| episode.py | method | LiteratureEpisode._enabled | episode function | task.py population_entries / FLAGS (the flags read from ctx.settings) |
| episode.py | method | LiteratureEpisode.contract_information_configuration | machinery | contract-information freezing (README 5 item 16): not carried |
| episode.py | method | LiteratureEpisode.contract_information_profile | machinery | contract-information freezing (README 5 item 16): not carried |
| episode.py | method | LiteratureEpisode._role | machinery | role check (each role is its own episode now) |
| episode.py | method | LiteratureEpisode.allowed_children | machinery | no children (task.py CHILD_SLOTS = {}) |
| episode.py | method | LiteratureEpisode.child_roles | machinery | no children (task.py CHILD_SLOTS = {}) |
| episode.py | method | LiteratureEpisode.child_assignment_schema | machinery | no children |
| episode.py | method | LiteratureEpisode.context_hook_applies | machinery | context hook of the old runner |
| from_parent.py | class | LiteratureAssignment | machinery | hook-era mix-in class; replaced by messages/read_from_parent.py |
| from_parent.py | method | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per old property) |
| from_parent.py | method | LiteratureAssignment._validate_page | episode function | messages/read_from_parent.py read_from_parent (span against page: source, representation, window range); the page-against-Store test is not carried (a wrong commission fails) |
| from_parent.py | method | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent |
| from_parent.py | method | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent; the credit_unit / yield_settings fill-in from the yield binding is settings (credit_unit is a field of the task now) |
| from_parent.py | method | LiteratureAssignment._parent_page_schema | machinery | check of the page against the parent's page: a wrong commission fails (rule 1), not carried |
| from_parent.py | method | LiteratureAssignment._validate_parent_page | machinery | check of the page against the parent's page: a wrong commission fails (rule 1), not carried |
| goal.py | function | _yield_kind | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion otherwise) |
| goal.py | function | _task_key | episode function | messages/read_from_parent.py task_key |
| goal.py | function | task_schema | episode function | messages/read_from_parent.py read_from_parent (kind, answer kind, axis A105 and credit_unit checks of the task record) |
| goal.py | function | _return_sources | machinery | check of the task against the parent-written return schema (the parent writes no return form now) |
| goal.py | function | _return_components | machinery | check of the task against the parent-written return schema (the parent writes no return form now) |
| goal.py | function | commissioned_task | episode function | messages/read_from_parent.py read_from_parent (task and proposed annotation read from the assignment); the return-schema and assigned-page cross-checks are not carried (a wrong commission fails) |
| goal.py | function | continuation_task | episode function | messages/read_from_parent.py task_key |
| goal.py | function | task_schema_variants | episode function | messages/read_from_parent.py read_from_parent (task kinds verified_source_leads, source_answer: assessment/screening/measurement, a105_experiments, a105_assembly; experiments unique) |
| goal.py | function | required_source | machinery | names the parent-written return source of a task (the parent selects return fields now) |
| goal.py | function | validate_commission | episode function | messages/read_from_parent.py read_from_parent (duplicate experiments); the requested-component subset checks are not carried (a wrong commission fails) |
| goal.py | class | LiteratureGoal | machinery | hook-era mix-in class; replaced by goal.py |
| goal.py | method | LiteratureGoal.instructions | episode function | goal.py GOAL (and task.py instructions, which composes it with the investigation text) |
| goal.py | method | LiteratureGoal.planning_context | episode function | messages/internal_summary.py literature_goal_plan |
| grading/assay_subscoring.py | class | AssaySubscoring | machinery | hook-era mix-in class |
| grading/assay_subscoring.py | method | AssaySubscoring._required_grading_repository | episode function | task.py grading_execute (grading is on for every commit: AGENTS.md required literature evidence processing) |
| grading/assay_subscoring.py | method | AssaySubscoring._assay_grading_repository | episode function | task.py grading_execute (LiteratureAssayGradingRepository(store, run_id, read_cells=...); BLOCKED-ON-STORE-ACCESS) |
| grading/experimental_interpretation.py | class | ExperimentalInterpretation | machinery | hook-era mix-in class |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.reasoning_action_schema | episode function | task.py reason_schema |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.reasoning_has_task_content | episode function | task.py action (an empty commit is rejected unless it carries a source_lead) |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.execute_reasoning | episode function | task.py reason (+ grading_execute) |
| internal_summary.py | class | LiteratureSummary | machinery | hook-era mix-in class; replaced by messages/internal_summary.py |
| internal_summary.py | method | LiteratureSummary.initial_decision_context | machinery | root-only reference_evidence_parent context (needs caller-assigned reference parent sources); not this episode's |
| internal_summary.py | method | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (+ task.py decide) |
| internal_summary.py | method | LiteratureSummary._owned_population_task_sources | episode function | not placed: reads the old operations tables with SQL and needs the run's flags; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._population_task_context | episode function | not placed: reads runtime_actions and operations tables; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._concentration_window_display_context | episode function | not placed: shows the family repository's receipt bindings; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._measurement_comparison_display_context | episode function | not placed: shows the family repository's receipt bindings; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._summary_precision_display_context | episode function | not placed: shows the family repository's receipt bindings; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._endpoint_signal_display_context | episode function | not placed: shows the family repository's receipt bindings; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._controlled_response_bindings | episode function | not placed: shows possessed rows of the family repositories; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._gel_bindings | episode function | not placed: shows possessed rows of the family repositories; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._gel_display_context | episode function | not placed: shows possessed rows of the family repositories; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._received_fact_display_context | episode function | not placed: shows possessed rows of the family repositories; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._native_rate_display_context | episode function | not placed: shows possessed rows of the family repositories; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._native_rate_domain_display_context | episode function | not placed: shows possessed rows of the family repositories; see unplaced_old_functions |
| internal_summary.py | method | LiteratureSummary._native_rate_meaning_display_context | episode function | not placed: shows possessed rows of the family repositories; see unplaced_old_functions |
| received_evidence.py | class | LiteratureReceivedEvidence | machinery | admission of child cells into the repositories on receipt (README 3b R1/R3); this episode has no child and the old functions had no caller here |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_sources | machinery | admission of child cells into the repositories on receipt (README 3b R1/R3); this episode has no child and the old functions had no caller here |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_facts | machinery | admission of child cells into the repositories on receipt (README 3b R1/R3); this episode has no child and the old functions had no caller here |
| received_evidence.py | method | LiteratureReceivedEvidence._complete_requested_received_arrays | machinery | admission of child cells into the repositories on receipt (README 3b R1/R3); this episode has no child and the old functions had no caller here |
| received_evidence.py | method | LiteratureReceivedEvidence.received_form_references | machinery | admission of child cells into the repositories on receipt (README 3b R1/R3); this episode has no child and the old functions had no caller here |
| received_evidence.py | method | LiteratureReceivedEvidence.received_evidence_tokens | machinery | admission of child cells into the repositories on receipt (README 3b R1/R3); this episode has no child and the old functions had no caller here |
| scientific_records.py | class | LiteratureScientificRecords | machinery | hook-era mix-in class |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_calibration_recovery_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_observation_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_replicate_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_quantity_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_assay_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_amount_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_optical_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_kinetic_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_interaction_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_ratio_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_model_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_transport_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_figure_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_ratio_source_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_controlled_response_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords.literature_gel_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._endpoint_signal_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._concentration_window_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._measurement_comparison_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._summary_precision_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._rate_grid_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_v2_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_v3_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._product_coupling_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._measurement_validation_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._ion_discrimination_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._channel_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._completion_time_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._active_site_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._assay_grading_source_cells | episode function | task.py assay_grading_source_cells (BLOCKED-ON-STORE-ACCESS) |
| scientific_records.py | method | LiteratureScientificRecords._parent_depletion_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._stoichiometric_balance_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._product_partition_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._binding_interaction_model_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._kinetic_model_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._ratio_source_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._controlled_response_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._gel_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._native_rate_meaning_repository | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | method | LiteratureScientificRecords._population_routes | episode function | messages/internal_summary.py FAMILIES (namespace, requested field, repository family) and family_cells |
| scoring/experimental_main_sheet.py | class | ExperimentalMainSheet | machinery | hook-era mix-in class |
| scoring/experimental_main_sheet.py | method | ExperimentalMainSheet._a105_aggregation_repository | episode function | task.py POPULATIONS['literature.a105.aggregate'] and credit.py assembled_answers (LiteratureA105AggregationRepository; BLOCKED-ON-STORE-ACCESS) |
| source_contracts.py | function | _required_grading_logic | episode function | task.py grading_execute (literature_required_grading.execute) |
| source_contracts.py | function | _population_catalog | episode function | task.py population_entries (library population_catalog under the flags) |
| source_operations.py | class | LiteratureSourceOperations | machinery | hook-era mix-in class |
| source_operations.py | method | LiteratureSourceOperations._tool_arguments | episode function | task.py admitted (+ population_sources, run_access_tool, run_population) |
| source_operations.py | method | LiteratureSourceOperations._materialize_text_arguments | episode function | task.py materialize_text_arguments |
| source_references.py | class | LiteratureReferences | machinery | hook-era mix-in class |
| source_references.py | method | LiteratureReferences._require | machinery | services.reference_in_scope / read_record: custody; the carried reads are read_record_in_scope (library) and records.require |
| source_references.py | method | LiteratureReferences._artifact | episode function | not placed: no caller in the old episode files; see unplaced_old_functions |
| source_references.py | method | LiteratureReferences._within_source | episode function | task.py within_source |
| task.py | class | LiteratureOperations | machinery | hook-era mix-in class |
| task.py | method | LiteratureOperations.permitted_common_actions | machinery | common actions: tool and reason are the tools; child and redeliver_report do not exist |
| task.py | method | LiteratureOperations.catalog | episode function | task.py catalog / offered / population_entries / ACCESS_DEFINITIONS |
| task.py | method | LiteratureOperations.execute | episode function | task.py run_access_tool, run_population, reason (tools) |
| task.py | class | LiteratureTask | machinery | the decision machine (README 3a) |
| task.py | method | LiteratureTask.next | episode function | task.py decide |
| task.py | method | LiteratureTask.apply_response | episode function | task.py action |
| task.py | method | LiteratureTask.execute | machinery | unit execution is the system's (ToolCall) |
| task.py | method | LiteratureTask.finish | machinery | saving the report and release: final_to_parent returns the result |
| task_decision.py | class | LiteratureTaskDecision | machinery | the decision exchange machine (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.call | episode function | task.py decide (ModelRequest) |
| task_decision.py | method | LiteratureTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | method | LiteratureTaskDecision.decision_completion | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.conversation_key | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.exchange_response | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_instructions.py | function | instructions | episode function | task.py instructions (the pending-delivery, wait and exchange paragraphs describe actions that no longer exist) |
| task_state.py | class | LiteratureTaskState | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.__init__ | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.bind_execution_context | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.suspension_changed | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.record_execution_failure | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.restore_checkpoint | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.restore | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.record_effect | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | method | LiteratureTaskState.checkpoint | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| to_parent.py | class | LiteratureReport | machinery | hook-era mix-in class; replaced by messages/final_to_parent.py |
| to_parent.py | method | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | method | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | method | LiteratureReport.current_report_facts | episode function | messages/internal_summary.py report_facts |
| to_parent.py | method | LiteratureReport._rate_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (one list field per family; meanings shortened) and messages/internal_summary.py FAMILIES |
| to_parent.py | method | LiteratureReport._rate_facts | episode function | messages/internal_summary.py family_cells (BLOCKED-ON-STORE-ACCESS: family repositories) |
| to_parent.py | method | LiteratureReport.validate_received_report | episode function | messages/final_to_parent.py validate_report (answers equal the saved work, cells only for requested families) |
| to_parent.py | method | LiteratureReport.resolve | machinery | reference_in_context resolver: custody (README 3b D2) |
| to_parent.py | method | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (validate_form is not built for A105: NotImplementedError(validate_form_not_built:experimental_activity_evidence) is not reached; the form is admitted exactly by the system) |
| waiting.py | class | LiteratureWaiting | machinery | wait support flag (README 3b) |
| waiting.py | method | LiteratureWaiting.supports_wait | machinery | wait support flag (README 3b) |
| yield_estimator.py | function | validate_yield_bindings | machinery | checks of the configured cutoff and alpha: the controllers' own ValueError (README 3d) |
| yield_estimator.py | class | _RemainingCommissionedCredit | machinery | episode-local estimator: CompletionYieldController with target = credit_unit x experiments (README 7b) |
| yield_estimator.py | method | _RemainingCommissionedCredit.__call__ | machinery | episode-local estimator: CompletionYieldController with target = credit_unit x experiments (README 7b) |
| yield_estimator.py | method | _RemainingCommissionedCredit.as_record | machinery | episode-local estimator: CompletionYieldController with target = credit_unit x experiments (README 7b) |
| yield_estimator.py | function | _private_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | class | _FiniteLiteratureYieldController | machinery | episode-local controller class (README 3d) |
| yield_estimator.py | method | _FiniteLiteratureYieldController.__init__ | machinery | episode-local controller class (README 3d) |
| yield_estimator.py | method | _FiniteLiteratureYieldController.transitioned | machinery | episode-local controller class (README 3d) |
| yield_estimator.py | class | LiteratureYield | machinery | hook-era mix-in class |
| yield_estimator.py | method | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py task_key |
| yield_estimator.py | method | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
