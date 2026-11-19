# a105/…/source_evidence_examination/source_coverage_improvement: intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/<file>`.
I read the 21 files directly in the folder (3,164 lines), `grading/` (3 files, 77 lines) and `scoring/` (2 files,
12 lines). There are no `prompts/`, `tools/` or `tests/` subfolders. I compared every file with the parent
(`source_evidence_examination`) and the two siblings. The old-runner names are listed per file below and in
`runs/carry_over/calls/a105_02.tsv`.

## What it is for (its goal, in its own words)

The ordered (document-order) reading episode. Its method_loop role is `literature_ordered`, and it is commissioned by
`source_evidence_examination` (`episode.commissioning_parent`). The parent's own role instruction calls it an
"ordered-reading" investigation. The docstring says "C7 binding for C10 assignments; no model connection or private
loop." The role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_ordered']`) reads:

> "Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte
> continuations and retain representation identity. Decide whether to continue, reread, change the examined window or
> interpret obtained evidence from actual outcomes."

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
`{version: 'reading_assignment_v1', page: _PAGE, selection: _WINDOW}`: one window
`{source_ref, representation, offset, limit}` where reading starts (`windows = [selected]`). The schema also carries `literature_task`, `proposed_annotation_ref`,
and the requested-component arrays of every enabled scientific family (the same list as the parent's).

`_validate_assignment` checks:
- the page: its artifact matches its representation, and the page and context refs are in scope;
- the window: same `source_ref` as the page, same representation, `offset` not past the artifact size.

`prepare_assignment` checks:
- it fills `credit_unit` and `yield_settings` from this episode's private yield binding for the task key;
- a supplied different value raises `literature_task_supplied_yield_binding_mismatch`;
- the proposed annotation must equal the parent's;
- the page must lie inside the parent page's source (`_validate_parent_page` with `_parent_page_schema`).

## Children it may commission

None. `_CHILDREN['literature_ordered'] = ()`. `permitted_common_actions` still lists `child` and `redeliver_report`,
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

The parent's `from_child_source_coverage_improvement` admits these cells into the parent's repositories.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | none | none |
| binding_record.py | 43 | the configuration record with this binding id | none |
| configuration.py | 119 | the same flags as the parent; `reference_evidence` classmethod (a caller-assigned reference-source investigation, `rate_population` default True) | root.a105.composition_information, root.a105.library.literature_controlled_response_storage, root.a105.library.literature_gel_storage |
| credit.py | 289 | task credit, lead schema/validation, screening answers | root.a105.communication, root.a105.domain ×3, root.a105.finding_validity, root.a105.scientific_findings, root.a105.library (assay_inputs ×2, sheet_updates ×2, assay_grading_storage, required_grading, a105_aggregation_storage), table runtime_actions ×4, table runtime_report_attempts ×2, workflow.scientific_projector_for_context, workflow.projector_receipt_arguments, workflow.projection_view |
| decision_presentation.py | 18 | none | root.a105.runtime ×2, root.a105.episode_work_report, self.workflow.controller_binding, _category_yield_parameters ×2, yield_table ×2 |
| episode.py | 70 | role `literature_ordered`, binding path, commissioning parent | root.a105.library.literature_experimental_prompt |
| from_parent.py | 281 | the reading assignment with one window; window and page checks; yield-binding fill | root.a105.library ×76 (component constants of 38 storage/calculation modules, each imported twice: own schema and `_parent_page_schema`) |
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

- **Selection.** It is one starting `_WINDOW`; the investigation continues in document order through byte
  continuations. Passage extraction takes a list of separate spans, and table extraction takes `_TABLE` or a window.
- **No private scientific copies.** Every grading, scoring, storage, prompt and calculation module is imported from the
  old shared `root/a105/library`, which is never restored. The parent has private copies under `grading/`,
  `scoring/`, `tools/` and `prompts/`. The scientific code this episode needs must come from those copies or the
  library placement (see `runs/placement_plan/placement.tsv`).
- **Roles and children.** `ROLES` and `_CHILDREN` hold the whole literature family table. It has no children, yet
  `child` and `redeliver_report` stay in its common actions.
- **Planning.** The planning question is its own instructions, under the key `literature_goal_plan`.
- **Resource estimates.** In `task_decision`, the job-source resource-estimate branch is `pass`.
- **Table rule.** There is no `literature_table` sheet check; only the table sibling has it.
- **Sibling copies.** It is byte-identical to passage_evidence_extraction apart from the role name, the binding path
  and the selection shape (`selection = _WINDOW`; `windows = [selected]`).

## Carried over

Carried over on 19 November 2026 into the final ten-file form (episode.py class `SourceCoverageImprovement`). One row per row of `runs/carry_over/functions/<this episode>.tsv`; the first three columns are copied from it. "library not carried" means the library function the new code calls is still in its old form (it opens the Store's `db`), reported in `carry_over_blocked/`.

| old file | kind | name | class | new place or reason |
|---|---|---|---|---|
| binding_record.py | class | LiteratureBindingRecord | machinery | binding_record.py: the binding's own as_record (README 3e); settings are journaled by the runner |
| binding_record.py | method | LiteratureBindingRecord.as_record | machinery | the binding's own as_record (README 3e) |
| configuration.py | class | LiteratureConfiguration | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| configuration.py | method | LiteratureConfiguration.__init__ | episode function | task.py::population_flags (booleans, optional families require rate_population; values are ctx.settings) and task.py::offered; the check of yield_bindings (validate_yield_bindings) is machinery; the evidence-origin and implementation-descriptor checks of ratio_source/controlled_response/gel are not carried (repositories use the old defaults, see contract_misfits); outcome_page_size is internal_summary.py::OUTCOME_PAGE_SIZE; reference_parent_sources applies only to a root entry episode, not to this commissioned child |
| configuration.py | method | LiteratureConfiguration.reference_evidence | machinery | old construction path of an entry-caller configuration (reference_parent_sources); never applies to a commissioned child |
| credit.py | function | _resolve | episode function | credit.py::_resolve |
| credit.py | function | lead_schema | episode function | credit.py::lead_schema |
| credit.py | function | lead_return_schema | episode function | credit.py::lead_return_schema |
| credit.py | function | validate_lead | episode function | credit.py::validate_lead (store.require / ctx.store; the old known-set is the held records) |
| credit.py | function | lead_dispositions | episode function | credit.py::lead_dispositions (the old runtime_actions and runtime_report_attempts reads are the summary's source_leads, from view.outcomes; this episode has no child) |
| credit.py | function | screening_schema | episode function | credit.py::screening_schema |
| credit.py | function | _current_assessments | episode function | credit.py::_current_assessments (library FindingValidity/target_eligible: library not carried) |
| credit.py | function | screening_answers | episode function | credit.py::screening_answers (the old runtime_actions read is summary no_applicable_witnesses, from view.outcomes) |
| credit.py | class | LiteratureTaskCredit | episode function | credit.py::credit_view / credit_record / task_answers (the projector class as functions over summary and records) |
| credit.py | method | LiteratureTaskCredit.as_record | episode function | credit.py::credit_record (the credit projector's as_record is episode content, README 3d) |
| credit.py | method | LiteratureTaskCredit.__call__ | episode function | credit.py::credit_view; the commission-mismatch, scope and target-annotation checks (literature_task_credit_commission_mismatch, literature_task_annotation_outside_scope, literature_task_requires_target_annotation) are checks of a commission and are not carried (a wrong commission fails) |
| credit.py | method | LiteratureTaskCredit._answers | episode function | credit.py::task_answers |
| credit.py | function | measured_answers | episode function | credit.py::measured_answers |
| credit.py | function | graded_experiment_answers | episode function | credit.py::graded_experiment_answers |
| credit.py | function | assembled_answers | episode function | credit.py::assembled_answers |
| credit.py | class | LiteratureCredit | machinery | old credit mix-in routing through services.scientific_credit; replaced by credit.py::credit |
| credit.py | method | LiteratureCredit._scientific_credit_invocation | machinery | services.scientific_credit / projector_receipt_arguments / projection_view plumbing (README 3d) |
| credit.py | method | LiteratureCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | LiteratureCredit.credit_view | episode function | credit.py::credit (number) and credit.py::credit_view (shown from the summary) |
| credit.py | method | LiteratureCredit.credit_projector | machinery | projector lookup of the old services; credit.py calls its own functions |
| decision_presentation.py | function | prepare_completed_work | episode function | internal_summary.py::internal_summary (own_literature_outcomes and last_outcome from view.outcomes); the old completed_action_reports of the shared root episode_work_report module is not in the library (unplaced) |
| decision_presentation.py | function | decision_yield_table | episode function | internal_summary.py::internal_summary (action_yields via library yield_table(view.controller_state)) |
| episode.py | class | LiteratureEpisode | machinery | mix-in class; replaced by episode.py::SourceCoverageImprovement |
| episode.py | method | LiteratureEpisode._enabled | episode function | task.py::population_flags |
| episode.py | method | LiteratureEpisode.contract_information_configuration | machinery | contract-information freezing profile (old shared-root exchange; README section 5 item 16); default None |
| episode.py | method | LiteratureEpisode.contract_information_profile | machinery | contract-information freezing profile (old shared-root exchange; README section 5 item 16) |
| episode.py | method | LiteratureEpisode._role | machinery | single-role check of the old shared class; the episode is its own binding |
| episode.py | method | LiteratureEpisode.allowed_children | episode function | task.py::CHILD_SLOTS = {} (no child) |
| episode.py | method | LiteratureEpisode.child_roles | episode function | task.py::CHILD_SLOTS = {} (no child) |
| episode.py | method | LiteratureEpisode.child_assignment_schema | machinery | no child; the parent writes the child's assignment in msg_to_child |
| episode.py | method | LiteratureEpisode.context_hook_applies | machinery | hook-era context hook selection |
| from_parent.py | class | LiteratureAssignment | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) |
| from_parent.py | method | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM and task_schema (one field per property of the old schema, same names; new fields scope and record_refs) |
| from_parent.py | method | LiteratureAssignment._validate_page | episode function | messages/read_from_parent.py::read_from_parent (page/window representation, source and offset checks); the records of the page being in scope is custody (record_refs) |
| from_parent.py | method | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py::read_from_parent |
| from_parent.py | method | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (task schema, credit unit, completion target = credit_unit x answers); the yield_settings/credit_unit fill from the private yield binding is the settings (yield_estimator.py); the proposed-annotation-equals-parent check is a check of a commission and is not carried |
| from_parent.py | method | LiteratureAssignment._parent_page_schema | machinery | check of the page against the parent's own page (the child cannot read its parent's assignment; a wrong commission fails) |
| from_parent.py | method | LiteratureAssignment._validate_parent_page | machinery | check of the page against the parent's own page (a wrong commission fails) |
| goal.py | function | _yield_kind | episode function | yield_estimator.py::yield_controller (accumulation for verified_source_leads, completion otherwise) |
| goal.py | function | _task_key | episode function | messages/read_from_parent.py::task_key |
| goal.py | function | task_schema | episode function | messages/read_from_parent.py::task_schema |
| goal.py | function | _return_sources | machinery | the parent's report-contract sources of the old return form; the parent writes no return form (README 3b C4) |
| goal.py | function | _return_components | machinery | the parent's report-contract components of the old return form (README 3b C4) |
| goal.py | function | commissioned_task | episode function | messages/read_from_parent.py::read_from_parent (task validated and returned in the parent input; the old check of the typed return/requested components against the report contract is a check of the commission and is not carried) |
| goal.py | function | continuation_task | episode function | messages/read_from_parent.py::task_key |
| goal.py | function | task_schema_variants | episode function | messages/read_from_parent.py::task_schema |
| goal.py | function | required_source | machinery | maps the task to the fact source the parent's report contract must request; the parent selects return fields in msg_to_child and nothing checks the commission (README 3b C4) |
| goal.py | function | validate_commission | episode function | messages/read_from_parent.py::validate_commission |
| goal.py | class | LiteratureGoal | episode function | messages/internal_summary.py::ROLE_INSTRUCTION, GOAL_INSTRUCTIONS and the literature_goal_plan |
| goal.py | method | LiteratureGoal.instructions | episode function | messages/internal_summary.py::GOAL_INSTRUCTIONS (used by task.py::instructions) |
| goal.py | method | LiteratureGoal.planning_context | episode function | messages/internal_summary.py::internal_summary (literature_goal_plan) |
| grading/assay_subscoring.py | class | AssaySubscoring | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| grading/assay_subscoring.py | method | AssaySubscoring._required_grading_repository | episode function | task.py::reason (the grading repository is built when the settings enable assay_grading_population) |
| grading/assay_subscoring.py | method | AssaySubscoring._assay_grading_repository | episode function | credit.py::repository('assay_grading') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| grading/experimental_interpretation.py | class | ExperimentalInterpretation | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.reasoning_action_schema | episode function | task.py::reason_schema (library literature_required_grading.action_schema; source_lead from credit.py::lead_schema) |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.reasoning_has_task_content | episode function | task.py::action (a reasoning commit with no row is rejected unless it carries a no-applicable-evidence processing or a source lead) |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.execute_reasoning | episode function | task.py::reason (original action: interpretation and grading sheets together via library literature_required_grading.execute; source_lead in one transaction) |
| internal_summary.py | class | LiteratureSummary | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| internal_summary.py | method | LiteratureSummary.initial_decision_context | machinery | applies only to a root entry episode with reference_parent_sources (role annotation, path length 1); this commissioned child never is one |
| internal_summary.py | method | LiteratureSummary.decision_context | episode function | messages/internal_summary.py::internal_summary (and task.py::decide) |
| internal_summary.py | method | LiteratureSummary._owned_population_task_sources | episode function | messages/internal_summary.py::owned_population_sources (the old SQL over the operation tables is the episode's own populate units in view.outcomes; the old population_task_metadata_specs of the literature_task_selection module is not in the library, re-expressed from the storage modules' PROVIDER and VERSION) |
| internal_summary.py | method | LiteratureSummary._population_task_context | episode function | messages/internal_summary.py::population_task_context (the old runtime_actions read is view.outcomes) |
| internal_summary.py | method | LiteratureSummary._concentration_window_display_context | episode function | messages/internal_summary.py::receipt_bindings_context (RECEIPT_BINDINGS) |
| internal_summary.py | method | LiteratureSummary._measurement_comparison_display_context | episode function | messages/internal_summary.py::receipt_bindings_context (RECEIPT_BINDINGS) |
| internal_summary.py | method | LiteratureSummary._summary_precision_display_context | episode function | messages/internal_summary.py::receipt_bindings_context (RECEIPT_BINDINGS) |
| internal_summary.py | method | LiteratureSummary._endpoint_signal_display_context | episode function | messages/internal_summary.py::receipt_bindings_context (RECEIPT_BINDINGS) |
| internal_summary.py | method | LiteratureSummary._controlled_response_bindings | episode function | messages/internal_summary.py::controlled_response_bindings('controlled_response') |
| internal_summary.py | method | LiteratureSummary._gel_bindings | episode function | messages/internal_summary.py::controlled_response_bindings('gel') (the two differ only in the repository and the requested field names) |
| internal_summary.py | method | LiteratureSummary._gel_display_context | episode function | messages/internal_summary.py::gel_display_context |
| internal_summary.py | method | LiteratureSummary._received_fact_display_context | episode function | messages/internal_summary.py::received_fact_display_context (the old source_metadata of the literature_work_report module is not in the library: unplaced) |
| internal_summary.py | method | LiteratureSummary._native_rate_display_context | episode function | messages/internal_summary.py::rate_display_context (RATE_DISPLAYS: the three differ in projection and name) |
| internal_summary.py | method | LiteratureSummary._native_rate_domain_display_context | episode function | messages/internal_summary.py::rate_display_context (RATE_DISPLAYS: the three differ in projection and name) |
| internal_summary.py | method | LiteratureSummary._native_rate_meaning_display_context | episode function | messages/internal_summary.py::rate_display_context (RATE_DISPLAYS: the three differ in projection and name) |
| received_evidence.py | class | LiteratureReceivedEvidence | machinery | admission of the cells of a child's return into the parent's repositories (README 3b R1/R3, F5); a copy of the parent's, with no caller here: this episode has no child |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_sources | machinery | admission of the cells of a child's return into the parent's repositories (README 3b R1/R3, F5); a copy of the parent's, with no caller here: this episode has no child |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_facts | machinery | admission of the cells of a child's return into the parent's repositories (README 3b R1/R3, F5); a copy of the parent's, with no caller here: this episode has no child |
| received_evidence.py | method | LiteratureReceivedEvidence._complete_requested_received_arrays | machinery | admission of the cells of a child's return into the parent's repositories (README 3b R1/R3, F5); a copy of the parent's, with no caller here: this episode has no child |
| received_evidence.py | method | LiteratureReceivedEvidence.received_form_references | machinery | admission of the cells of a child's return into the parent's repositories (README 3b R1/R3, F5); a copy of the parent's, with no caller here: this episode has no child |
| received_evidence.py | method | LiteratureReceivedEvidence.received_evidence_tokens | machinery | admission of the cells of a child's return into the parent's repositories (README 3b R1/R3, F5); a copy of the parent's, with no caller here: this episode has no child |
| scientific_records.py | class | LiteratureScientificRecords | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_repository | episode function | credit.py::repository('rate') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_calibration_recovery_repository | episode function | credit.py::repository('calibration_recovery') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_observation_repository | episode function | credit.py::repository('rate_observation') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_replicate_repository | episode function | credit.py::repository('rate_replicate') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_quantity_repository | episode function | credit.py::repository('quantity') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_assay_repository | episode function | credit.py::repository('assay') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_amount_repository | episode function | credit.py::repository('amount') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_optical_repository | episode function | credit.py::repository('optical') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_kinetic_repository | episode function | credit.py::repository('kinetic') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_interaction_repository | episode function | credit.py::repository('binding_interaction') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_ratio_repository | episode function | credit.py::repository('ratio') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_repository | episode function | credit.py::repository('binding') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_model_repository | episode function | credit.py::repository('binding_model') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_transport_repository | episode function | credit.py::repository('transport') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_figure_repository | episode function | credit.py::repository('figure') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_ratio_source_repository | episode function | credit.py::repository('ratio_source') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_controlled_response_repository | episode function | credit.py::repository('controlled_response') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords.literature_gel_repository | episode function | credit.py::repository('gel') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._endpoint_signal_repository | episode function | credit.py::repository('endpoint_signal') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._concentration_window_repository | episode function | credit.py::repository('concentration_window') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._measurement_comparison_repository | episode function | credit.py::repository('measurement_comparison') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._summary_precision_repository | episode function | credit.py::repository('summary_precision') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._rate_grid_repository | episode function | credit.py::repository('rate_grid') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_repository | episode function | credit.py::repository('compiled_assay') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_v2_repository | episode function | credit.py::repository('compiled_assay_v2') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_v3_repository | episode function | credit.py::repository('compiled_assay_v3') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._product_coupling_repository | episode function | credit.py::repository('product_coupling') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._measurement_validation_repository | episode function | credit.py::repository('measurement_validation') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._ion_discrimination_repository | episode function | credit.py::repository('ion_discrimination') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._channel_repository | episode function | credit.py::repository('channel') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._completion_time_repository | episode function | credit.py::repository('completion_time') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._active_site_repository | episode function | credit.py::repository('active_site') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._assay_grading_source_cells | episode function | credit.py::assay_grading_source_cells |
| scientific_records.py | method | LiteratureScientificRecords._parent_depletion_repository | episode function | credit.py::repository('parent_depletion') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._stoichiometric_balance_repository | episode function | credit.py::repository('stoichiometric_balance') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._product_partition_repository | episode function | credit.py::repository('product_partition') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._binding_interaction_model_repository | episode function | credit.py::repository('binding_interaction_model') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._kinetic_model_repository | episode function | credit.py::repository('kinetic_model') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._ratio_source_repository | episode function | credit.py::repository('ratio_source') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._controlled_response_repository | episode function | credit.py::repository('controlled_response') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._gel_repository | episode function | credit.py::repository('gel') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._native_rate_meaning_repository | episode function | credit.py::repository('rate_source_meaning') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| scientific_records.py | method | LiteratureScientificRecords._population_routes | episode function | credit.py::routes (ROUTE_SPECS: every family; which are offered is task.py's choice from the settings) |
| scoring/experimental_main_sheet.py | class | ExperimentalMainSheet | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| scoring/experimental_main_sheet.py | method | ExperimentalMainSheet._a105_aggregation_repository | episode function | credit.py::repository('a105_aggregation') (old factory method as one row of REPOSITORY_CLASSES; library not carried: the repository opens the Store's db) |
| source_contracts.py | function | _required_grading_logic | episode function | already in library: literature/grading/experimental_activity_evidence/literature_required_grading.py (imported as required_grading in task.py) |
| source_contracts.py | function | _population_catalog | episode function | task.py::population_entries (library population_catalog, sorted in the established order) |
| source_operations.py | class | LiteratureSourceOperations | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| source_operations.py | method | LiteratureSourceOperations._tool_arguments | episode function | task.py::admitted, population_sources, authorize_source_access, authorize_read (the old rejection_detail of the literature_source_access module is not in the library: unplaced) |
| source_operations.py | method | LiteratureSourceOperations._materialize_text_arguments | episode function | task.py::materialize_text_arguments |
| source_references.py | class | LiteratureReferences | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| source_references.py | method | LiteratureReferences._require | episode function | already in library: records/received_records.py::read_record_in_scope (reference_in_scope + read_record) |
| source_references.py | method | LiteratureReferences._artifact | episode function | messages/internal_summary.py::representation_artifact |
| source_references.py | method | LiteratureReferences._within_source | episode function | task.py::within_source |
| task.py | class | LiteratureOperations | machinery | old mix-in class of the hook-era episode class; replaced by episode.py::SourceCoverageImprovement and the files named on the rows of its methods |
| task.py | method | LiteratureOperations.permitted_common_actions | machinery | common actions tool/reason/child/redeliver_report of the old decision machine; decide returns a tool call, reason is a tool, there is no child and no redelivery |
| task.py | method | LiteratureOperations.catalog | episode function | task.py::catalog, offered, population_entries (the old catalog was the registry's catalog filtered to _ACCESS_TOOLS plus the population catalog) |
| task.py | method | LiteratureOperations.execute | episode function | task.py tools: run_access_tool and the access tool functions, run_population and the literature_*_populate functions, reason |
| task.py | class | LiteratureTask | machinery | old decision loop class; replaced by task.py::decide and task.py::action |
| task.py | method | LiteratureTask.next | machinery | old loop with replay/restore; the system's decision loop |
| task.py | method | LiteratureTask.apply_response | episode function | task.py::action (validation of the answer, empty reasoning commit rejected, Rejected carries the old rejection feedback) |
| task.py | method | LiteratureTask.execute | episode function | task.py tools (the unit execution); the runtime_actions/journal/checkpoint writes are machinery |
| task.py | method | LiteratureTask.finish | machinery | closing of the old action/episode record; the system builds the result by final_to_parent |
| task_decision.py | class | LiteratureTaskDecision | machinery | old model-decision class (model call, provider patching, decision-exchange loop) |
| task_decision.py | method | LiteratureTaskDecision.call | machinery | old model call and its recording; decide returns a ModelRequest |
| task_decision.py | method | LiteratureTaskDecision.instructions | episode function | task.py::instructions |
| task_decision.py | method | LiteratureTaskDecision.decision_completion | machinery | provider patching and presentation binding (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.conversation_key | machinery | conversation state is deleted (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange lookup context; a lookup is a tool (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop (request_context / select_action) |
| task_decision.py | method | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision exchange (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_history | machinery | saved-request check of the decision exchange (README 3a) |
| task_decision.py | method | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop (exchange_decision is not carried) |
| task_instructions.py | function | instructions | episode function | task.py::instructions (the redelivery/history paragraphs are replaced; the request_context paragraph the old code appended is not carried) |
| task_state.py | class | LiteratureTaskState | machinery | old task state (report values, restore, checkpoint); state is the view (internal_summary) |
| task_state.py | method | LiteratureTaskState.__init__ | machinery | state of the old loop; report_values and interpret_schema are the parent-written report form (README 3b C4, 3a running report) |
| task_state.py | method | LiteratureTaskState.bind_execution_context | machinery | old execution context binding |
| task_state.py | method | LiteratureTaskState.suspension_changed | machinery | suspension machinery |
| task_state.py | method | LiteratureTaskState.record_execution_failure | episode function | task.py::run_access_tool (a failed selected operation is returned as failure_outcome; the runtime_actions/checkpoint writes are machinery) |
| task_state.py | method | LiteratureTaskState.restore_checkpoint | machinery | checkpoint/restore/effect recording (README 3e) |
| task_state.py | method | LiteratureTaskState.restore | machinery | checkpoint/restore/effect recording (README 3e) |
| task_state.py | method | LiteratureTaskState.record_effect | machinery | checkpoint/restore/effect recording (README 3e) |
| task_state.py | method | LiteratureTaskState.checkpoint | machinery | checkpoint/restore/effect recording (README 3e) |
| to_parent.py | class | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM (every fact source a selectable field under its old name), fact_sources |
| to_parent.py | method | LiteratureReport.facts | episode function | messages/final_to_parent.py::final_to_parent and selected_fact (the facts are computed in internal_summary.py::internal_summary over view.records) |
| to_parent.py | method | LiteratureReport.current_report_facts | episode function | messages/internal_summary.py::internal_summary (literature_current_scoring_sheets via library current_scoring_sheets); literature_completed_work: the completed_work function of the literature_work_report module is not in the library (unplaced), selecting it raises NotImplementedError |
| to_parent.py | method | LiteratureReport._rate_fact_sources | episode function | messages/final_to_parent.py::FACT_ROWS, fact_sources, fact_meanings (the meaning text and the library schema of each family) |
| to_parent.py | method | LiteratureReport._rate_facts | episode function | messages/internal_summary.py::family_rows and version_gate |
| to_parent.py | method | LiteratureReport.validate_received_report | episode function | messages/final_to_parent.py::validate_received_report (summary-only checks) and messages/internal_summary.py::check_family and the worksheet-link check (the Store-dependent checks: final_to_parent is handed no records) |
| to_parent.py | method | LiteratureReport.resolve | machinery | reference_in_context resolver of the old receipt ledger (README 3b D2); custody is records.holds |
| to_parent.py | method | LiteratureReport.validate_report | episode function | messages/final_to_parent.py::validate_report (raises NotImplementedError(validate_form_not_built:a105) at the old validate_form call) |
| waiting.py | class | LiteratureWaiting | machinery | wait machinery (supports_wait is False) |
| waiting.py | method | LiteratureWaiting.supports_wait | machinery | wait machinery (supports_wait is False) |
| yield_estimator.py | function | validate_yield_bindings | machinery | check of the configured yield declarations when the old episode was constructed (README 3d); settings are journaled at link |
| yield_estimator.py | class | _RemainingCommissionedCredit | episode function | yield_estimator.py: CompletionYieldController with target = parent input completion_target (credit_unit x answers requested); README 7b |
| yield_estimator.py | method | _RemainingCommissionedCredit.__call__ | episode function | the completion controller's own forecast (README 7b); the old max(0, remaining) is the controller's ValueError when credit passes the target |
| yield_estimator.py | method | _RemainingCommissionedCredit.as_record | machinery | estimator record of the old declaration check (README 3d) |
| yield_estimator.py | function | _private_yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | class | _FiniteLiteratureYieldController | machinery | episode-local controller class; no episode supplies a controller class (README 7b) |
| yield_estimator.py | method | _FiniteLiteratureYieldController.__init__ | machinery | episode-local controller class (README 7b) |
| yield_estimator.py | method | _FiniteLiteratureYieldController.transitioned | machinery | transitioned(epoch) is deleted (README 3d) |
| yield_estimator.py | class | LiteratureYield | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | method | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py::task_key |
| yield_estimator.py | method | LiteratureYield.yield_controller | episode function | yield_estimator.py::yield_controller (accumulation for verified_source_leads, completion otherwise; cost and parameters from settings, target from parent input) |
