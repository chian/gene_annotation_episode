# a105/…/source_relevance_assessment/source_evidence_examination: intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/<file>`.
I read the 28 files directly in the folder (README.md and 27 `.py` files, 3,960 lines) and grepped the `grading/` (8 files,
1,218 lines) and `scoring/` (77 files, 21,506 lines) subfolders for old-runner names. I read in full the three
grading/scoring files bound in `episode.py` and the head of `grading/literature_required_grading.py`. The folder also
holds `prompts/` (69 files), `tools/` (67 files) and `tests/` (5 files). They are outside this step and were not
read. The three child folders are other agents' work. I read their top-level files only to compare them with this one.
Every old-runner name is listed per file below and in `runs/carry_over/calls/a105_02.tsv`.

## What it is for (its goal, in its own words)

The source examination episode. Its method_loop role is `literature_page` and its commissioning parent is
`…/source_relevance_assessment`. From `README.md`:

> "An invocation supplies a source assignment, objective and result contract; it does not generate episode code.
> … These are responsibilities in the iterative process, not a one-pass pipeline. Planning and summary inform each
> next action. An accepted interpretation must retain its typed investigation finding and required grading sheet
> before credit. Scientific evidence scoring and task-progress credit remain distinct. The existing method_loop
> controller decides continuation from the yield estimate. Returning a partial or unresolved assessment does not
> manufacture support."

Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_page']`):

> "Investigate where and how this exact source should be examined. Choose ordinary source operations or selected
> table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML headings,
> tables and footnotes; retained original bytes remain addressable."

## Task and instructions

`goal.SourceGoal.instructions` returns the role instruction plus a fixed paragraph. The children use the same
paragraph:

> "This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted child forms
> inform later choices; no child order, reading quota or complete-document requirement is prescribed. A one-off
> search/read is an ordinary tool. A supplied reading selector is context, not an automatically executed action.
> Preserve the source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors.
> Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications can
> advance the investigation. Commit interpretations with the common reasoning action and update only the parent's
> declared typed form in that same work call. Navigation, byte coverage and repeated reading earn no scientific credit
> by themselves. The commissioned task's own yield settings guide continuation."

`goal.SourceGoal.planning_context` gives the next decision `objective` (the request goal),
`proposed_annotation_ref`, `commissioned_result` (the task), and `progress_definition`, which is the same credit record
used for credit. It also asks this question (this episode only; the children ask their instructions instead):

> "Which unresolved part of the commissioned source assessment should be investigated next, using the actual
> findings and returned components? Choose source operations or one of the declared children; revise the approach
> from outcomes while preserving the original objective."

`task_instructions.py` composes the model instructions on top of these. It adds the old `runtime_prompt.INSTRUCTIONS`,
the reasoning-commit requirement, tool knowledge, the launch library, a `pending_child_delivery` redelivery repair
paragraph, and a replacement of the history guidance under the exchange protocol. The decision prompt is rendered by
the private `prompts/literature_experimental_prompt.render_literature_experimental_prompt`
(`episode.decision_prompt_renderer`).

The commissioned task (`goal.task_schema`, version `literature_local_task_v1`, `evidence_axis: A105`, a positive
finite `credit_unit`, optional `yield_settings`) is exactly one of these:
- `verified_source_leads`: relevant/not-relevant lead dispositions for the proposed annotation.
- `source_answer` / `assessment` with `source_refs`: one current assessment anchored in those sources.
- `source_answer` / `screening` with `examined` spans: a "no applicable evidence" screening over exactly those spans.
- `source_answer` / `measurement` with a quantity `selection` and `components` (reported_value / reported_spread /
  relative_reported_spread).
- `a105_experiments` with `experiments[{experiment_ref, assay_type}]`: graded assessments per experiment.
- `a105_assembly` with `experiment_refs` and `metrics` (reliability / validity / relevance / attribution / overall).

`goal.commissioned_task` refuses any of the following:
- a task whose typed return (`x-source`) is not in the parent's report contract;
- components that are not in the requested return;
- duplicate experiments;
- metrics or measurement components that were not requested;
- spans with end ≤ start;
- sources outside the assigned page;
- screening on another artifact.

## What it reads from its parent's assignment

`from_parent.SourceAssignment.assignment_schema` uses `_PAGE`:
`{version: 'page_assignment_v1', source_ref, representation (text|original|stdout|stderr), artifact_ref,
question_context_refs, prior_delivery_refs}`. It adds `literature_task` and `proposed_annotation_ref`. With a private
yield binding, both are required and `credit_unit` is filled from the binding. With `rate_population` it also adds the
requested-component arrays for every enabled scientific family:
- concentration window, measurement comparison, kinetic summary precision;
- rate, rate observation and rate grid, calibration recovery, product coupling, measurement validation, rate replicate;
- quantity, assay, ratio, binding, binding model, transport, endpoint signal, figure, amount, optical;
- kinetic, kinetic model, binding interaction and binding interaction model;
- ion discrimination, channel, compiled assay v1/v2/v3, assay grading, A105 aggregation;
- product partition, completion time, active site, parent depletion, stoichiometric balance, ratio source;
- controlled response (components/views/keys) and gel (components/views/keys).

`_validate_page` checks that the page's artifact is the source's artifact for that representation. It also checks
that the artifact and every context/prior-delivery ref is in scope. `prepare_assignment` checks that a child's
proposed annotation equals the parent's and that a child's page lies inside this page's source ancestry
(`_within_source`).

## Children it may commission

`_CHILDREN['literature_page'] = ('literature_table', 'literature_ordered', 'literature_targeted')`. The connector
`episode.py` maps the roles to the folders. Each `to_child_*.to_child` deep-copies the assignment. If the child page
has the parent's `source_ref`, the child's `artifact_ref` and `representation` must equal the parent's
(`literature_reading_<field>_mismatch`). `prepare_request` then validates scope against the parent's scope, expands
the child's contract form, requires every `required_return_sources` once, validates the initial report, and has the
child binding admit the assignment.

| Child folder | Role | What it sends | What it takes back |
|---|---|---|---|
| table_evidence_extraction | literature_table | `{version: 'reading_assignment_v1', page, selection}` with `selection` = `_TABLE` (`source_ref, sheet_key, offset, limit, header_row, where{column, match, value, case_sensitive}`) or a `_WINDOW` (`source_ref, representation, offset, limit`), plus `literature_task`, `proposed_annotation_ref` and requested components | the typed form; `from_child_table_evidence_extraction` admits each requested cell family into this episode's own repositories (`receive_cells`) and returns the cell/sheet record refs |
| source_coverage_improvement | literature_ordered | the same envelope, `selection` = one `_WINDOW` | the same |
| passage_evidence_extraction | literature_targeted | the same envelope, `selection = {spans: [_WINDOW, ≥1]}` | the same |

The three `from_child_*` files are identical apart from the child's name. The child's cells are admitted, and they
become this episode's known record refs. Through them they feed this episode's own credit, because credit reads the
known sheets. The parent never adds child credit to its own.

## Decision state and what it shows the model

State (`task_state.SourceTaskState`): `calls`, `feedback`, `last_outcome`/`last_outcome_index`, `report_values` (it
starts from the request's `initial_report`), `report_basis`, and `interpret_schema` (the interpretation schema of the
report contract). The rest is old replay and checkpoint state.

The decision context (`task.py` `next`, line 237, plus `internal_summary.SourceSummary.decision_context`) shows the
model:
- goal, scope, working_state, visible_record_refs, current_credit, current_evidence_vector, investigation_progress,
  credit_binding;
- time_accounting (presented only, not a limit), pending_work, last_local_outcome, feedback, visual_evidence (the
  latest `image.view`), report_deliveries;
- controller and controller_binding, tools, tool_knowledge, job_episode_options, available_report_facts;
- requested_report_purpose, requested_form, current_report_update, current_report_basis_refs, report_lifecycle
  ("Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.").

The binding's own part (`decision_context`) adds:
- `literature_assignment` and `literature_source_custody` (version, artifact, text, stdout and stderr refs, and
  parents);
- `own_literature_outcomes` (paged by `outcome_page_size`, default 8) and `literature_history_meaning`;
- `source_examination_goal` (the planning context above) and `literature_examined_source_inputs`;
- `literature_experimental_work`;
- the ratio-source, controlled-response and gel bindings, and the rate/rate-domain/rate-meaning display;
- the received-fact display and the endpoint, summary-precision, comparison and concentration-window receipt bindings;
- `literature_owned_population_sources`, and the last failed population attempt;
- `literature_completed_work` / `literature_current_scoring_sheets`.

`task_decision.py` adds resource and shared-information context, the launch-instruction library, `child_options`,
completed-action reports, execution expectations and resource estimates, and the yield table. It also handles the
`request_context`/`select_action` exchange protocol. Under the exchange protocol, a `request_context` lookup creates no
unit. An invalid response gets feedback and another decision.

## Tools it offers

Common actions: `tool`, `reason`, `child`, `redeliver_report`.

`task.SourceTask.catalog` takes the services catalog and keeps only `_ACCESS_TOOLS`:
- `state.query`;
- `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`;
- `image.view`;
- `source.archive.members`, `source.archive.extract`;
- `source.xlsx.sheets`, `source.xlsx.rows`;
- `source.pdf.info`, `source.pdf.text`, `source.pdf.page`;
- `execution.estimate`, restricted to its xlsx branches.

The acquisition tools are offered only to the `literature`, `literature_strategy` and `literature_search` roles, so
this episode does not get them. When `rate_population` is set, the 35 `literature.*.populate` /
`literature.a105.aggregate` operations are appended in `_CATALOG_ORDER`, each family behind its own flag.

`_tool_arguments` validates operands against the input schema. Every source ref (including nested sheet, model and
covariance refs) must lie inside the assigned page's source. The `literature_table` sheet must match. Reads are
authorized on the endpoint, summary-precision, comparison and concentration-window repositories. Invalid operands
return an `invalid` outcome with feedback, which still enters the iterator.

Reasoning (`grading/experimental_interpretation.py`):
- When assay grading is on, a reasoning action must use `literature_required_grading.action_schema`. The interpretation
  and its purpose-specific grading sheets are committed as one action. Each assessment needs an
  `investigation_finding`. `no_applicable_evidence` names the examined spans and carries no assessments.
- A `verified_source_leads` task adds `source_lead`. `credit.validate_lead` checks the proposed annotation, the
  received inputs, that the subject is anchored inside the quoted witness, and that the source is not a search page.

## How its credit is counted

`credit.LiteratureTaskCredit`. The credit is `credit_unit × number of answered items` (checked finite, never bounded).
Its policy record:
`{kind: 'literature_local_task_v1', task, credit_unit, unit, revision_credit: False, activity_credit: False,
annotation_support: 'separate'}`. Unit per task kind:
- `verified_source_leads`: relevant lead dispositions. They come from this episode's own `reason` results and from
  child forms admitted with `literature_source_lead_dispositions`, merged in decision order, latest per canonical
  source.
- `screening`: one answer when the own `no_applicable_evidence` reasoning spans (each with a reason) cover every
  requested span.
- `assessment`: one answer when a current, retained, target-eligible assessment of the proposed annotation has an
  anchored (or visually anchored) observation in `source_refs`.
- `measurement`: one answer for a quantity sheet with exactly the requested selection whose requested components are
  all populated. `reported_spread_unavailable` and `zero_reported_value` also count.
- `a105_experiments`: one per requested experiment that has a current grading sheet of the requested assay type
  matching a current assessment (`_matches_grading`).
- `a105_assembly`: one answer for an aggregation sheet over exactly the requested experiments and metrics, every
  selected grade current.

Before counting, `credit` checks the commission (run, episode, scope, goal, purpose, schema, initial report). It also
checks that the hypothesis is in scope and rooted in the subject. Scientific support is reported separately.

## Continuation (yield estimator and settings)

`yield_estimator.py`. It is used only when `private_yield_binding` is set. `yield_bindings` is keyed by task key
(`A105:verified_source_leads`, `A105:source_answer:assessment|screening|measurement`, `A105:experiments`,
`A105:assembly`). Each key holds exactly `{credit_unit, kind, cutoff, uncertainty_alpha}`.

- `verified_source_leads` uses kind `accumulation` and a plain controller with the cutoff and uncertainty_alpha. This
  is the new `yield_control` accumulation estimator.
- Every other task uses kind `remaining_commissioned_credit`. Its finite capacity is
  `credit_unit × (number of experiments | 1)`. The forecast of the next gain is the observed score yield, with the
  forecast band capped at the remaining commissioned credit. It is exactly zero once all requested answers are earned
  (`terminal_forecast: exact_zero_when_all_requested_answers_earned`). This is the new completion-with-a-target
  estimator. The cap applies only to the forecast, never to credit.

A task's own `yield_settings` must equal its binding, and its kind must match the task.

## What it reports to its parent

`to_parent.SourceReport`.
- **Fact sources:** every enabled scientific cell family (`_rate_fact_sources`, with meanings and report schemas),
  plus `literature_screening_answers` and `literature_source_lead_dispositions`.
- **Facts at completion:** the screening answers or lead dispositions for the commissioned task. With
  `rate_population` they also include each family's requested cells from known sheets, `literature_completed_work`
  and `literature_current_scoring_sheets`.
- **`validate_received_report`:** lead and screening answers must equal the saved work. Each family must return
  exactly the requested subset of possessed cells, and an empty-family return must be valid. Controlled-response and
  gel component keys must be requested. A105 worksheet links are checked.
- **Without a report contract:** `finish` reports `credit`, `pending_handles` and the current report facts.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| README.md | 103 | responsibilities, the grading-before-credit rule and the iterative process | none (prose) |
| `__init__.py` | 1 | none | none |
| binding_record.py | 43 | the configuration record (`literature_episode_binding_v1`, binding id) | none |
| configuration.py | 106 | constructor flags for the scientific families (each needs `rate_population`), `private_yield_binding` / `yield_bindings`, `outcome_page_size`, `reference_parent_sources`, evidence origins and descriptors | root.a105.composition_information |
| credit.py | 287 | task credit (above), lead schema/validation, screening answers | root.a105.communication, root.a105.domain ×3, root.a105.finding_validity, root.a105.scientific_findings, table runtime_actions ×4, table runtime_report_attempts ×2, workflow.scientific_projector_for_context, workflow.projector_receipt_arguments, workflow.projection_view |
| decision_presentation.py | 18 | none (presentation glue) | root.a105.runtime, root.a105.episode_work_report, self.workflow.controller_binding, _category_yield_parameters ×2, yield_table ×2 |
| episode.py | 90 | connector: role `literature_page`, binding path, commissioning parent, child-role→folder maps, `assay_grading_population` switch | none directly (composes the classes) |
| from_child_passage_evidence_extraction.py | 124 | admit child cell families into own repositories, return refs | EpisodeReturnRecords ×2, root.a105.episode_return_records, root.a105.runtime, root.episode_journal, self.services.workflow.store, table runtime_report_attempts ×2, workflow.binding_context ×2, workflow.is_job_source ×2, workflow.job_episodes ×2, workflow.native_timing_information, workflow.progress_provider ×2, workflow.receipts ×3, workflow.run_id ×4, workflow.specialist, workflow.store ×7 |
| from_child_source_coverage_improvement.py | 124 | same | same |
| from_child_table_evidence_extraction.py | 124 | same | same |
| from_parent.py | 180 | page assignment, requested components, child assignment checks | none |
| goal.py | 129 | task schema, commission checks, task key / yield kind, instructions, planning question | root.a105.communication, root.a105.domain ×2 |
| internal_summary.py | 311 | decision context (above), initial reference-parent context | self.services.workflow ×2, self.services.workflow.store ×2, workflow.run_id ×2, workflow.store ×2, table runtime_actions ×2 |
| received_evidence.py | 67 | received-cell facts and tokens (used when it is not `literature_page`) | root.method_loop.durable |
| scientific_records.py | 357 | one repository per scientific family, plus `_population_routes` | self.services.workflow.store ×34, self.services.workflow.run_id ×34 |
| source_contracts.py | 42 | `ROLES`, `_CHILDREN`, `_PAGE` / `_WINDOW` / `_TABLE`, access tools, role instruction, catalog order | root.a105.communication, root.communication, root.a105.composition_information, root.a105.domain, root.a105.episode_bindings, root.a105.experimental_database_acquisition |
| source_references.py | 31 | `_require`, artifact by representation, source ancestry | none |
| task.py | 400 | catalog, operand checks, tool execution with invalid outcomes; the rest is the old decision/execute loop | 98 runner members, including self.workflow.journal ×12, self.workflow.store ×12, self.workflow.execution_binding ×7, self.workflow.inprocess_replay ×4, self.workflow.binding_context ×4, self.workflow.source_credit_view ×3, self.workflow.selected ×3, self.workflow.completions ×3; root.communication ×2, root.episode_journal, root.task_action_units, root.provider_errors, root.a105.episode_source_failure, root.episode_contract_information, root.a105.composition_information; table runtime_actions ×10, runtime_model_calls ×2, runtime_forms ×2, runtime_episodes |
| task_decision.py | 375 | none of its own (model call and exchange protocol) | 59 runner members (self.workflow.validate_contract_information ×5, resource_estimator ×5, receipts ×4, decision_exchanges ×4, …), root.a105.providers ×2, root.providers, root.episode_journal, table runtime_model_calls ×8, _category_yield_parameters, yield_table |
| task_instructions.py | 28 | the pending-delivery repair text | root.a105.runtime_prompt, root.a105.library.literature_investigation_prompt, source.workflow.permits_common_action ×3, source.workflow.specialist, binding_context, knowledge, launch_instructions, decision_protocol, is_job_source, native_event_information |
| task_records.py | 356 | none (a copy of old runtime helpers) | BindingContext, EpisodeBindingRegistry, CompletionLedger, CommissionCoordinator; imports from root.method_loop (and its archive, identities, communication and durable modules) and root.receiving_context; root.a105.episode_bindings, episode_journal, episode_receipts, decision_context, decision_exchanges, decision_history, composition_information, episode_admission, episode_completion, episode_commissions, episode_application_services, episode_reports, waiting, wait_estimation_inputs, resource_estimation, execution_expectations, execution_timing, native_timing_information, run_statistics, local_return_history, boundary_validation, schema_support ×2, communication, episode_contract_information; root.communication, root.episode_journal, root.episode_contract_information; _category_yield_parameters, yield_table |
| task_state.py | 106 | initial report values and interpretation schema | 34 runner members (self.workflow.inprocess_replay ×7, journal ×5, completions ×4, execution_binding ×4, …), workflow.context, workflow.grains, root.a105.episode_source_failure, table runtime_actions ×5 |
| to_child_passage_evidence_extraction.py | 43 | same-source artifact/representation rule | root.a105.runtime ×2, workflow.binding_context ×4, workflow.episode_bindings ×3, workflow.store, workflow.expanded_contract_form, workflow.child_initial_report_input, workflow.specialist, workflow.available_child_roles, workflow.annotation_child_roles, workflow.services, workflow.launch_instructions, workflow.run_id |
| to_child_source_coverage_improvement.py | 43 | same | same |
| to_child_table_evidence_extraction.py | 43 | same | same |
| to_parent.py | 316 | fact sources, facts, received-report validation | root.a105.domain ×2, root.communication, self.services.workflow.store ×4, workflow.store ×2, getattr(self.services,'workflow') |
| waiting.py | 8 | `supports_wait = False` | none |
| yield_estimator.py | 105 | yield bindings, the remaining-commissioned-credit forecast | root.a105.numerical, YieldController ×4, YieldParameters ×3, estimate_score_yield ×3, YieldEstimate ×2, NumericBand ×2, STATUS_NORMAL ×2 |
| grading/assay_subscoring.py | 17 | the assay-grading repository when grading is on | self.services.workflow.store, self.services.workflow.run_id |
| grading/experimental_interpretation.py | 61 | the required-grading reasoning schema and execution, the source-lead reasoning | self.services.workflow.store, root.communication ×2, root.episode_contract_information, root.episode_journal, root.task_action_units |
| grading/literature_required_grading.py | 177 | one action holding the interpretation and its graders; `investigation_finding` required; no_applicable_evidence rules | root.a105.communication, root.a105.domain |
| grading/literature_assay_grading.py | 154 | assay-type assessments feeding the A105 dimensions | root.a105.domain |
| grading/literature_assay_grading_inputs.py | 379 | binding reader results to assay assessments | root.a105.domain, root.a105.experimental_database_measurements ×2, root.a105.library.literature_received_partner_contract |
| grading/literature_assay_grading_storage.py | 318 | saved grading sheets and requested components | root.a105.communication, root.a105.domain |
| grading/literature_experimental_contracts.py | 111 | rate extraction contracts | none |
| grading/`__init__.py` | 1 | none | none |
| scoring/experimental_main_sheet.py | 12 | the A105 aggregation repository over the grade rows | self.services.workflow.store, self.services.workflow.run_id |
| scoring/literature_controlled_response_storage.py | 759 | controlled-response custody | BindingContext ×2, EpisodeReceipts ×3, root.receiving_context, root.a105.episode_receipts, root.a105.communication, root.a105.domain, table runtime_episodes ×4, runtime_actions ×2, runtime_report_attempts, runtime_record_receipts, runtime_receipt_inheritance, literature_controlled_response_runtime_bindings |
| scoring/literature_gel_storage.py | 603 | gel custody | the same pattern (BindingContext ×2, EpisodeReceipts ×3, runtime_* tables, literature_gel_runtime_bindings) |
| scoring/literature_rate_storage.py | 731 | rate sheets | root.a105.communication, root.a105.domain ×3, table runtime_report_attempts ×3, runtime_actions ×2, runtime_episodes ×2, runtime_model_calls ×2 |
| scoring/literature_optical_storage.py | 371 | optical storage | root.a105.communication, root.a105.domain, table runtime_report_attempts ×2 |
| scoring/literature_ratio_source_storage.py | 362 | ratio-source custody | root.a105.communication, root.a105.domain, table runtime_actions ×2 |
| scoring/literature_a105_aggregation_storage.py | 314 | A105 aggregation sheets | root.a105.communication ×2, root.a105.domain, root.a105.component_assessment_dependencies |
| scoring/: the other 70 files | 18,354 | the original formulas: calculations, storage and sheet updates per family | only root.a105.domain / root.a105.communication (helpers), in 49 of them; 21 (pure calculations and `__init__`) use none |

## Where it differs from its siblings and similar episodes

- **Private scientific code.** Only this episode holds private copies of its scientific code (`grading/`, `scoring/`,
  `tools/`, `prompts/`; README: 214 helper modules plus the 7 assay functions moved to `scoring/assay_evidence.py`).
  The three children import the same modules from the old shared `root/a105/library`, which is never restored.
- **Children.** It is the only one of the four with children: three `to_child_*`/`from_child_*` pairs and
  `prepare_child_request`.
- **Roles and contracts.** `ROLES` and `_CHILDREN` hold only `literature_page`. The children carry the whole literature
  family table.
- **Assignment.** Its assignment is the page itself (`_PAGE`). A child's is `{version: 'reading_assignment_v1', page,
  selection}`.
- **Planning.** The planning question is fixed text, and the context key is `source_examination_goal`. The children
  use `literature_goal_plan` and their instructions.
- **Operand checks.** `_tool_arguments` lives in `task.py` and still holds the `literature_table` sheet check. The
  children hold it in `source_operations.py`.
- **Resource estimates.** `task_decision` keeps the job-source resource estimate branch. The children replace it with
  `pass`.
