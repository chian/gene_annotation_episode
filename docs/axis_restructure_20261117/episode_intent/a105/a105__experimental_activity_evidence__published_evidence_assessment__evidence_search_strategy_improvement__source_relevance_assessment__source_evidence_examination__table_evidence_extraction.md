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
