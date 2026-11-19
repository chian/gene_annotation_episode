# a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/<file>`
(files directly in this folder plus `grading/` and `scoring/`; the `source_relevance_assessment/` child is described
separately). Class `LiteratureEpisode`, decision source `LiteratureTask`, `decision_prompt_renderer =
render_literature_experimental_prompt`. `binding_path = '.../published_evidence_assessment/evidence_search_strategy_improvement'`,
`commissioning_parent = 'experimental_activity_evidence/published_evidence_assessment'`, role `literature_strategy`,
`roles = ('literature_strategy',)`, **`entry_roles = ()`** (never an entry), binding id
`experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement`.

The files are copies of the parent `published_evidence_assessment` binding; everything below that is not called out as
different is the same code with this role name (see the parent's document for the full content of shared parts).

## What this episode is for (its goal, in its own words)

`_ROLE_INSTRUCTIONS['literature_strategy']`: "Investigate which search approach is productive. Keep the information
objective and evidence context separate from a literal provider query. Revise terms or source choices in light of
actual search/read outcomes; a search child can investigate which returned sources deserve examination." Followed by
the same common literature paragraph as the parent ("This is an iterative scientific investigation ... Navigation,
byte coverage and repeated reading earn no scientific credit by themselves. The commissioned task's own yield settings
guide continuation.").

The concrete goal is the same commissioned literature task (`literature_local_task_v1`, A105): verified source leads,
source answer (assessment / screening / measurement), A105 experiments or A105 assembly, with its credit unit and yield
settings, checked by `commissioned_task` against the requested return contract.

## Task and instructions

Same composition as the parent: base `runtime_prompt.INSTRUCTIONS` + this role's instructions + reasoning-commit
requirement + knowledge / launch texts + pending-child-delivery repair text; no wait text; exchange-protocol history
replacement. Same `LiteratureTask` loop; `validate_report` is called with `grain='literature_strategy'`; execution
expectations are captured under `'literature_strategy'`.

## What it reads from its parent's assignment

`assignment_schema('literature_strategy')` → **`strategy_assignment_v1 {question_context_refs, prior_search_refs,
literature_task, proposed_annotation_ref}`** plus the same population `requested_*_components` selectors (under
`rate_population` and the per-family flags). `prior_search_refs` must be in scope as `source` records. Preparation
applies the same private yield declaration (task key → credit unit + yield settings) and the proposed-annotation
equality check against the parent. The `literature_page` within-source branch can never apply here
(`'literature_strategy' not in _CHILDREN['literature_page']`).

## Children it may commission

| child role | folder | what it sends | what it takes back |
|---|---|---|---|
| `literature_search` | `source_relevance_assessment` | `to_child` = deep copy of the assignment; `prepare_request` (role `literature_search`): scope, expanded return schema, initial report, permitted role, child's `prepare_assignment` (search_assignment_v1) | `receive_source_relevance_assessment`: same population-cell admission and record-ref collection as the parent's `receive_evidence_search_strategy_improvement`; `receive_report` with receipts / progress provider / native timing |

## Decision state and what it shows the model

Same as the parent: common context + `decision_context` (`literature_assignment` with `prior_search_refs`; source
custody of `source_refs` only — a strategy assignment has no `source_refs`, so custody is empty unless a `page` is
present; own literature outcomes page; history meaning; examined source inputs; experimental-work marker; population
displays; current report facts; `literature_goal_plan`). No `waiting_support`. Presentation-aware model completion.

## Tools it offers

Identical catalogue to the parent: access + acquisition tools (pubmed-only NCBI search, xlsx-only execution
estimate), A105 population operations under `rate_population`, `source_location_inputs` wrapping; same source-bound
argument checks; same required-grading reasoning action and source-lead reasoning. Common actions: tool, reason, child,
redeliver_report; `supports_wait = False`.

## How its credit is counted

Identical `LiteratureTaskCredit`: `credit_unit × number of answers` for the commissioned task (lead dispositions,
screening answer, anchored assessment, measured quantity sheet, graded experiments, A105 aggregate); unbounded, finite
check only.

## Continuation

Identical `LiteratureYield`: task key declaration; `verified_source_leads` → accumulation; others → remaining
commissioned credit (completion with target = `credit_unit × len(experiments)` or `credit_unit`). Old `None` without a
private yield binding must become an explicit error.

## What it reports to its parent

Identical `fact_sources` / `facts` / `validate_report` / `validate_received_report`. **Does not** define
`received_form_references` (the parent does).

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | — | — |
| `binding_record.py` | 43 | record with own binding id | — |
| `configuration.py` | 119 | same flags / validation | `a105.composition_information:CONTRACT_INFORMATION_PROFILE`; 2 `a105.library` modules |
| `credit.py` | 289 | literature task credit (copy) | `self.services.{scientific_credit, scientific_credit_for, proposed_annotation_for, annotation_task_required}`; `workflow.{scientific_projector_for_context, projector_receipt_arguments, projection_view}`; tables `runtime_actions×4`, `runtime_report_attempts×2`; 5 `a105.library` modules |
| `decision_presentation.py` | 18 | completed-action reports; yield table | `self.workflow.controller_binding`; runtime `{_category_yield_parameters, Mapping, yield_table}`; `a105.episode_work_report` |
| `episode.py` | 88 | composition; role `literature_strategy`; child maps for `literature_search`; no `create_binding_tree` | `a105.library.literature_experimental_prompt` |
| `from_child_source_relevance_assessment.py` | 123 | receive search child's cells/refs | as parent's `from_child_evidence_search_strategy_improvement.py` |
| `from_parent.py` | 162 | strategy_assignment_v1 schema and preparation | `self.services.proposed_annotation_for`; 38 `a105.library` modules |
| `goal.py` | 131 | task schema/checks, strategy goal text, planning context | `a105.communication`, `a105.domain`, 2 `a105.library` modules |
| `grading/__init__.py` | 0 | — | — |
| `grading/assay_subscoring.py` | 17 | assay-grading repository | `self.services.workflow.{store, run_id}` |
| `grading/experimental_interpretation.py` | 60 | required grading + source leads in reasoning | `self.services.workflow.store`; imported runtime / journal / communication names |
| `internal_summary.py` | 311 | decision context displays | `self.services.{own_outcomes, read_record×5}`; `self.services.workflow.store`; `workflow.{store, run_id}`; table `runtime_actions×2`; 11 `a105.library` modules |
| `received_evidence.py` | 67 | received cells/tokens | `method_loop.durable:content_digest` |
| `scientific_records.py` | 357 | population repositories and routes | `self.services.workflow.{store×34, run_id×34}`; 40 `a105.library` modules |
| `scoring/__init__.py` | 0 | — | — |
| `scoring/experimental_main_sheet.py` | 12 | A105 aggregation repository | `self.services.workflow.{store, run_id}` |
| `source_contracts.py` | 42 | roles, children chain, tool lists, role texts | `a105.episode_bindings:reference_in_context`, `a105.composition_information`, `a105.experimental_database_acquisition`, `ReportBoundaryError` |
| `source_operations.py` | 77 | source-bound argument checks | `self.services.read_record×4` |
| `source_references.py` | 31 | scope reads, source ancestry | `self.services.{reference_in_scope, read_record}` |
| `task.py` | 311 | catalog/execute + decision loop (`grain='literature_strategy'`) | as parent `task.py` |
| `task_decision.py` | 352 | model call / exchanges / presentation completion | as parent `task_decision.py` (`providers` internals included) |
| `task_instructions.py` | 28 | instruction composition | `runtime_prompt.*`; `source.workflow.*` |
| `task_state.py` | 108 | episode state | as parent |
| `to_child_source_relevance_assessment.py` | 35 | `literature_search` request | `workflow.{store, expanded_contract_form, episode_bindings×3, binding_context×4, child_initial_report_input, specialist, available_child_roles, annotation_child_roles, services.capabilities, launch_instructions, run_id}`; runtime names |
| `to_parent.py` | 322 | fact sources, facts, received-report validation (no `received_form_references`) | `self.services.{read_record, record_selection}`; `self.services.workflow.store`; `ReportBoundaryError`; `a105.library` modules |
| `waiting.py` | 8 | `supports_wait = False` | — |
| `yield_estimator.py` | 109 | yield bindings, remaining-commissioned-credit forecast | `a105.numerical:{YieldController, YieldParameters, YieldEstimate, NumericBand, STATUS_NORMAL, estimate_score_yield}` |

Full counts: `runs/carry_over/calls/a105_01.tsv`.

## Differences from similar episodes

- vs parent `published_evidence_assessment`: role/binding id, `strategy_assignment_v1 prior_search_refs`, strategy role
  text, child `literature_search`, `entry_roles = ()`, no `create_binding_tree`, no `received_form_references`,
  `context_hook_applies` returns False for non-family roles (parent True).
- vs child `source_relevance_assessment`: same pattern one step down (search_assignment_v1, child `literature_page`).
- Its goal text is about search approach, but its credit is the same commissioned-task answer count as the parent's —
  a strategy episode earns only when the task's typed answers exist (e.g. verified source leads), not for search
  activity.

## Carried over

Carried over on 19 November 2026 into the ten-file private binding (class `EvidenceSearchStrategyImprovement` in `episode.py`). One row per row of `runs/carry_over/functions/a105__experimental_activity_evidence__published_evidence_assessment__evidence_search_strategy_improvement.tsv` (198 rows); the first three columns are copied from it. Class: `machinery` (old runner, not carried, with its reason) or `episode function` (its new place). "library candidate" marks a private copy that is not specific to this episode and could move to `episode_support/` later; nothing was added to the library in this step. Rows of `grading/` and `scoring/` are the old mix-in classes of this episode folder; the modules of `episode_support/` they call (`literature/**`, `records/**`, `tools/**`, `findings/**`, `acquisition/**`) are already in the library and are called, not copied. The folder is a private copy of its child's shape (the old files differed only in role name, `strategy_assignment_v1 prior_search_refs`, the role text and the child `literature_search`).

| old file | name | kind | class | new place or reason |
|---|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | class | machinery | the binding's own as_record (README 3e): settings are journaled by the system |
| binding_record.py | LiteratureBindingRecord.as_record | method | machinery | the binding's own as_record (README 3e): settings are journaled by the system |
| configuration.py | LiteratureConfiguration | class | machinery | configuration record: its flags are ctx.settings keys read in task.py (rate_population and FLAGS); its yield bindings are settings['cost'] / settings['parameters'] (README 3d) |
| configuration.py | LiteratureConfiguration.__init__ | method | machinery | flag validation and yield-binding validation: settings are the run's; the controller constructors raise on a bad cost or alpha (README 3d) |
| configuration.py | LiteratureConfiguration.reference_evidence | method | machinery | caller-assigned reference-source entry constructor of the old configuration (reference_parent_sources, contract-information profile default, rate_population default true): the run's caller sets settings (ctx.settings) and the root commissions this episode; contract-information freezing is not carried (README 5 item 16) |
| credit.py | _resolve | function | episode function | task.py resolve (private copy; library candidate) |
| credit.py | lead_schema | function | episode function | task.py lead_schema (private copy; library candidate) |
| credit.py | lead_return_schema | function | episode function | messages/final_to_parent.py RETURN_FORM field literature_source_lead_dispositions (a list field) |
| credit.py | validate_lead | function | episode function | task.py validate_lead (private copy on custody: store.require / store.get_artifact; library candidate) |
| credit.py | lead_dispositions | function | episode function | credit.py lead_dispositions (the own validated leads and the lead dispositions of the admitted child forms, from the unit outcomes in decision order) |
| credit.py | screening_schema | function | episode function | messages/final_to_parent.py RETURN_FORM field literature_screening_answers (a list field) |
| credit.py | _current_assessments | function | episode function | credit.py current_assessments (BLOCKED-ON-STORE-ACCESS: FindingValidity / target_eligible in the old form) |
| credit.py | screening_answers | function | episode function | credit.py screening_answers (the own no_applicable_evidence spans from the unit outcomes) |
| credit.py | LiteratureTaskCredit | class | episode function | credit.py: the projector's functions credit, answers, credit_binding (the class itself is hook-era) |
| credit.py | LiteratureTaskCredit.as_record | method | episode function | credit.py credit_binding (the credit definition shown to the model) |
| credit.py | LiteratureTaskCredit.__call__ | method | episode function | credit.py credit (credit_unit times the number of answers; unchanged formula) |
| credit.py | LiteratureTaskCredit._answers | method | episode function | credit.py answers |
| credit.py | measured_answers | function | episode function | credit.py measured_answers (BLOCKED-ON-STORE-ACCESS: LiteratureQuantityRepository) |
| credit.py | graded_experiment_answers | function | episode function | credit.py graded_experiment_answers (BLOCKED-ON-STORE-ACCESS: LiteratureAssayGradingRepository, current_sheet_refs) |
| credit.py | assembled_answers | function | episode function | credit.py assembled_answers (BLOCKED-ON-STORE-ACCESS: LiteratureA105AggregationRepository, current_sheet_refs) |
| credit.py | LiteratureCredit | class | machinery | hook-era mix-in class; replaced by credit.py |
| credit.py | LiteratureCredit._scientific_credit_invocation | method | machinery | the services.scientific_credit invocation and its receipt arguments (README 3d: credit has no services) |
| credit.py | LiteratureCredit.credit_kind | method | machinery | credit_kind is deleted (README 3d) |
| credit.py | LiteratureCredit.credit_view | method | episode function | credit.py credit (the number; the other fields of the old credit view are computed in messages/internal_summary.py) |
| credit.py | LiteratureCredit.credit_projector | method | episode function | credit.py credit / credit_binding (the projector as library functions over the summary and records) |
| decision_presentation.py | prepare_completed_work | function | episode function | not placed: completed_action_reports (root.a105.episode_work_report) has no module in the library; see unplaced_old_functions |
| decision_presentation.py | decision_yield_table | function | episode function | messages/internal_summary.py action_yields (yield_table over view.controller_state) |
| episode.py | LiteratureEpisode | class | episode function | episode.py class EvidenceSearchStrategyImprovement (EpisodeBinding) |
| episode.py | LiteratureEpisode._enabled | method | episode function | task.py population_entries (the population flags are ctx.settings keys) |
| episode.py | LiteratureEpisode.contract_information_configuration | method | machinery | contract-information freezing (README 5 item 16): not carried |
| episode.py | LiteratureEpisode.contract_information_profile | method | machinery | contract-information freezing (README 5 item 16): not carried |
| episode.py | LiteratureEpisode._role | method | machinery | role check: each role is its own episode now (README 3a BindingContext.role) |
| episode.py | LiteratureEpisode.allowed_children | method | episode function | task.py CHILD_SLOTS (the one child slot, source_relevance_assessment = old literature_search) |
| episode.py | LiteratureEpisode.child_roles | method | episode function | task.py CHILD_SLOTS (the one child slot, source_relevance_assessment = old literature_search) |
| episode.py | LiteratureEpisode.child_assignment_schema | method | machinery | the child's assignment schema is the child's own ASSIGNMENT_FORM (README 3b C3) |
| episode.py | LiteratureEpisode.context_hook_applies | method | machinery | decision-exchange context hook (README 3a) |
| episode.py | LiteratureEpisode.prepare_child_request | method | episode function | messages/msg_to_child.py msg_to_child (the old to_child copy); the rest of the old preparation is deleted (README 3b C3) |
| episode.py | LiteratureEpisode.receive_child_result | method | episode function | messages/read_from_child.py read_from_child |
| episode.py | LiteratureEpisode.child_request_preparer | method | machinery | binding lookup (README 3b C1) |
| episode.py | LiteratureEpisode.child_report_receiver | method | machinery | binding lookup (README 3b C1) |
| from_child_source_relevance_assessment.py | FromSourceRelevanceAssessment | class | episode function | messages/read_from_child.py read_from_child (slot source_relevance_assessment) |
| from_child_source_relevance_assessment.py | FromSourceRelevanceAssessment.receive_source_relevance_assessment | method | episode function | messages/read_from_child.py read_from_child: the report carries the child's cells and the records it returned; the write of the cells into the own repositories (receive_cells) is not carried (README 5 item 4: the child returns its sheets by reference, custody holds them) |
| from_child_source_relevance_assessment.py | receive_report | function | machinery | receipts bookkeeping, the admitted-return tables, the progress provider and native timing records on receipt: the system's custody and journal (README 3b R1, R3, R5; 3e) |
| from_parent.py | LiteratureAssignment | class | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) and messages/msg_to_child.py |
| from_parent.py | LiteratureAssignment.assignment_schema | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (+ task_schema) |
| from_parent.py | LiteratureAssignment._validate_page | method | machinery | Store check of a page commission (page artifact, context records), reached only for the page role (never for this strategy episode): a wrong commission fails (rule 1); records are named in record_refs fields |
| from_parent.py | LiteratureAssignment._validate_assignment | method | episode function | messages/read_from_parent.py read_from_parent (task schema, credit unit, commission rules); the Store checks (every *_refs field held, prior_search_refs sources) are not carried (rule 1) |
| from_parent.py | LiteratureAssignment.prepare_assignment | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM / read_from_parent (the assignment the parent's msg_to_child builds); the yield-binding fill-in, the proposed-annotation comparison with the parent and the source-ancestry check against the Store are not carried: a wrong commission fails |
| goal.py | _yield_kind | function | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion otherwise) |
| goal.py | _task_key | function | episode function | messages/read_from_parent.py task_key |
| goal.py | task_schema | function | episode function | messages/read_from_parent.py task_schema |
| goal.py | _return_sources | function | machinery | introspection of the parent's report contract (x-source fields): the parent selects return fields (rule 5) |
| goal.py | _return_components | function | machinery | introspection of the parent's report contract (x-source fields): the parent selects return fields (rule 5) |
| goal.py | commissioned_task | function | episode function | messages/read_from_parent.py read_from_parent (the checks that need no report contract and no Store) |
| goal.py | continuation_task | function | episode function | messages/read_from_parent.py task_key (parent_input['task_key']) |
| goal.py | task_schema_variants | function | episode function | messages/read_from_parent.py task_schema |
| goal.py | required_source | function | episode function | messages/msg_to_child.py msg_to_child (the family of the commissioned task is selected from the requested components) |
| goal.py | validate_commission | function | episode function | messages/read_from_parent.py validate_commission |
| goal.py | LiteratureGoal | class | episode function | goal.py (GOAL, PLANNING_QUESTION) and task.py instructions |
| goal.py | LiteratureGoal.instructions | method | episode function | goal.py GOAL; task.py instructions |
| goal.py | LiteratureGoal.planning_context | method | episode function | goal.py PLANNING_QUESTION; messages/internal_summary.py literature_goal_plan |
| grading/assay_subscoring.py | AssaySubscoring | class | machinery | hook-era mix-in class |
| grading/assay_subscoring.py | AssaySubscoring._required_grading_repository | method | episode function | task.py grading_execute (LiteratureAssayGradingRepository(store, run_id, read_cells=...); BLOCKED-ON-STORE-ACCESS) |
| grading/assay_subscoring.py | AssaySubscoring._assay_grading_repository | method | episode function | task.py grading_execute (LiteratureAssayGradingRepository(store, run_id, read_cells=...); BLOCKED-ON-STORE-ACCESS) |
| grading/experimental_interpretation.py | ExperimentalInterpretation | class | machinery | hook-era mix-in class |
| grading/experimental_interpretation.py | ExperimentalInterpretation.reasoning_action_schema | method | episode function | task.py reason_schema |
| grading/experimental_interpretation.py | ExperimentalInterpretation.reasoning_has_task_content | method | episode function | task.py action (an empty commit is rejected unless it carries a source_lead) |
| grading/experimental_interpretation.py | ExperimentalInterpretation.execute_reasoning | method | episode function | task.py reason (+ grading_execute) |
| internal_summary.py | LiteratureSummary | class | machinery | hook-era mix-in class; replaced by messages/internal_summary.py |
| internal_summary.py | LiteratureSummary.initial_decision_context | method | episode function | not placed: the root-only reference_evidence_parent context (needs caller-assigned reference parent sources), not this episode's commission; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary.decision_context | method | episode function | messages/internal_summary.py internal_summary (+ task.py decide) |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._population_task_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._concentration_window_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._measurement_comparison_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._summary_precision_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._endpoint_signal_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._controlled_response_bindings | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._gel_bindings | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._gel_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._received_fact_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._native_rate_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._native_rate_domain_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| internal_summary.py | LiteratureSummary._native_rate_meaning_display_context | method | episode function | not placed: shows the possessed rows of the family repositories (old Store form) and needs the run's flags, which a summary does not have; see unplaced_old_functions |
| received_evidence.py | LiteratureReceivedEvidence | class | machinery | admission of received child cells into the repositories on receipt (README 3b R1/R3): the child returns its cells and the records it named, read by messages/read_from_child.py, and the sheets are held through custody; this episode's own children's forms are admitted by the system |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | method | machinery | admission of received child cells into the repositories on receipt (README 3b R1/R3): the child returns its cells and the records it named, read by messages/read_from_child.py, and the sheets are held through custody; this episode's own children's forms are admitted by the system |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | method | machinery | admission of received child cells into the repositories on receipt (README 3b R1/R3): the child returns its cells and the records it named, read by messages/read_from_child.py, and the sheets are held through custody; this episode's own children's forms are admitted by the system |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | method | machinery | admission of received child cells into the repositories on receipt (README 3b R1/R3): the child returns its cells and the records it named, read by messages/read_from_child.py, and the sheets are held through custody; this episode's own children's forms are admitted by the system |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | method | machinery | admission of received child cells into the repositories on receipt (README 3b R1/R3): the child returns its cells and the records it named, read by messages/read_from_child.py, and the sheets are held through custody; this episode's own children's forms are admitted by the system |
| scientific_records.py | LiteratureScientificRecords | class | machinery | hook-era mix-in class |
| scientific_records.py | LiteratureScientificRecords.literature_rate_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_calibration_recovery_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_rate_observation_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_rate_replicate_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_quantity_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_assay_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_amount_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_optical_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_kinetic_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_binding_interaction_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_ratio_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_binding_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_binding_model_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_transport_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_figure_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_ratio_source_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_controlled_response_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords.literature_gel_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._endpoint_signal_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._concentration_window_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._measurement_comparison_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._summary_precision_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._rate_grid_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v2_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v3_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._product_coupling_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._measurement_validation_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._ion_discrimination_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._channel_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._completion_time_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._active_site_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._assay_grading_source_cells | method | episode function | task.py assay_grading_source_cells (BLOCKED-ON-STORE-ACCESS) |
| scientific_records.py | LiteratureScientificRecords._parent_depletion_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._stoichiometric_balance_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._product_partition_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._binding_interaction_model_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._kinetic_model_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._ratio_source_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._controlled_response_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._gel_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._native_rate_meaning_repository | method | episode function | repository accessor: one entry of task.py POPULATIONS / messages/internal_summary.py FAMILIES, library_repository(<Repository>) (library candidate; BLOCKED-ON-STORE-ACCESS: <Repository>(store, run_id) over store.db tables) |
| scientific_records.py | LiteratureScientificRecords._population_routes | method | episode function | messages/internal_summary.py FAMILIES (namespace, requested field, repository family) and family_cells |
| scoring/experimental_main_sheet.py | ExperimentalMainSheet | class | machinery | hook-era mix-in class |
| scoring/experimental_main_sheet.py | ExperimentalMainSheet._a105_aggregation_repository | method | episode function | task.py POPULATIONS['literature.a105.aggregate'] and credit.py assembled_answers (LiteratureA105AggregationRepository; BLOCKED-ON-STORE-ACCESS) |
| source_contracts.py | _required_grading_logic | function | episode function | task.py grading_execute (literature_required_grading.execute) |
| source_contracts.py | _population_catalog | function | episode function | task.py population_entries (the library population_catalog under the flags) |
| source_operations.py | LiteratureSourceOperations | class | machinery | hook-era mix-in class |
| source_operations.py | LiteratureSourceOperations._tool_arguments | method | episode function | task.py admitted / authorize_source_read (+ run_access_tool, run_population): the schema check and the rate_population source authorization; the containment of a read inside the assigned page applied only under assignment['page'], which a strategy assignment does not have (see unplaced_old_functions) |
| source_operations.py | LiteratureSourceOperations._materialize_text_arguments | method | episode function | task.py materialize_text_arguments |
| source_references.py | LiteratureReferences | class | machinery | hook-era mix-in class |
| source_references.py | LiteratureReferences._require | method | machinery | services.reference_in_scope / read_record: custody; the carried reads are records.require / records.holds |
| source_references.py | LiteratureReferences._artifact | method | episode function | not placed: no caller in the old episode files; see unplaced_old_functions |
| source_references.py | LiteratureReferences._within_source | method | episode function | not placed: its only callers (source_operations._tool_arguments under assignment['page'], from_parent.prepare_assignment for a literature_page parent) do not apply to a strategy assignment; see unplaced_old_functions |
| task.py | LiteratureOperations | class | machinery | hook-era mix-in class |
| task.py | LiteratureOperations.permitted_common_actions | method | machinery | common actions: tool and reason are tools, child is a ChildCall; redeliver_report does not exist |
| task.py | LiteratureOperations.catalog | method | episode function | task.py definitions / LIBRARY_DEFINITIONS / catalog / offered / population_entries (access and acquisition tools; ncbi narrowed to pubmed) |
| task.py | LiteratureOperations.execute | method | episode function | task.py run_access_tool, run_population, reason (tools) |
| task.py | LiteratureTask | class | machinery | the decision machine (README 3a) |
| task.py | LiteratureTask.next | method | episode function | task.py decide |
| task.py | LiteratureTask.apply_response | method | episode function | task.py action |
| task.py | LiteratureTask.execute | method | machinery | unit execution is the system's (ToolCall / ChildCall) |
| task.py | LiteratureTask.finish | method | machinery | saving the report and release: final_to_parent returns the result |
| task_decision.py | LiteratureTaskDecision | class | machinery | the decision exchange machine (README 3a) |
| task_decision.py | LiteratureTaskDecision.call | method | episode function | task.py decide (ModelRequest) |
| task_decision.py | LiteratureTaskDecision.instructions | method | episode function | task.py instructions |
| task_decision.py | LiteratureTaskDecision.decision_completion | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.conversation_key | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.interpretation_context | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_schema | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_response | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_decision | method | machinery | decision-exchange protocol, saved-exchange checks and conversation state (README 3a) |
| task_instructions.py | instructions | function | episode function | task.py instructions (the pending-delivery, wait and exchange paragraphs describe actions that no longer exist) |
| task_state.py | LiteratureTaskState | class | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.__init__ | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.bind_execution_context | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.suspension_changed | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.record_execution_failure | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.restore_checkpoint | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.restore | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.record_effect | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| task_state.py | LiteratureTaskState.checkpoint | method | machinery | restore, checkpoint, record_effect, execution context, failure recording (README 3a/3e): the model's report is the report tool's outcome |
| to_child_source_relevance_assessment.py | to_child | function | episode function | messages/msg_to_child.py msg_to_child (the old to_child copied the assignment unchanged: the search results, question context, task, annotation, requested components, scope and records are the assignment built there) |
| to_child_source_relevance_assessment.py | prepare_request | function | episode function | messages/msg_to_child.py msg_to_child (the child's assignment and the selection of return fields); the report-contract expansion, initial-report validation, allowed-roles check, launch-instruction materialization and prepare_assignment of the child are the old runner's or the child's own (README 3b C3, C4) |
| to_parent.py | LiteratureReport | class | machinery | hook-era mix-in class; replaced by messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | method | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | LiteratureReport.facts | method | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | LiteratureReport.current_report_facts | method | episode function | messages/internal_summary.py report_facts |
| to_parent.py | LiteratureReport._rate_fact_sources | method | episode function | messages/final_to_parent.py RETURN_FORM (one list field per family; meanings shortened) and messages/internal_summary.py FAMILIES |
| to_parent.py | LiteratureReport._rate_facts | method | episode function | messages/internal_summary.py family_cells (BLOCKED-ON-STORE-ACCESS: family repositories) |
| to_parent.py | LiteratureReport.validate_received_report | method | episode function | messages/final_to_parent.py validate_report (cells only for requested families; answers equal the saved work) |
| to_parent.py | LiteratureReport.resolve | method | machinery | reference_in_context resolver: custody (README 3b D2) |
| to_parent.py | LiteratureReport.validate_report | method | episode function | messages/final_to_parent.py validate_report (validate_form is not built for A105; the form is admitted exactly by the system) |
| waiting.py | LiteratureWaiting | class | machinery | wait support flag (README 3b) |
| waiting.py | LiteratureWaiting.supports_wait | method | machinery | wait support flag (README 3b) |
| yield_estimator.py | validate_yield_bindings | function | machinery | validation of the configured yield declarations: the settings are the run's and the controller constructors raise on a bad cost or alpha (README 3d) |
| yield_estimator.py | _RemainingCommissionedCredit | class | machinery | episode-local estimator: completion with the finite target (README 7b); the forecast cap is the controller's own |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | method | machinery | episode-local forecast: deleted (README 3d); CompletionYieldController's own forecast |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | method | machinery | episode-local estimator record: deleted (README 3d) |
| yield_estimator.py | _private_yield_controller | function | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | class | machinery | episode-local controller class: deleted; CompletionYieldController(target = credit_unit x answers) (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | method | machinery | episode-local controller class: deleted (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | method | machinery | transitioned(epoch) is deleted (README 3d) |
| yield_estimator.py | LiteratureYield | class | episode function | yield_estimator.py |
| yield_estimator.py | LiteratureYield.continuation_task | method | episode function | messages/read_from_parent.py task_key (parent_input['task_key']) |
| yield_estimator.py | LiteratureYield.yield_controller | method | episode function | yield_estimator.py yield_controller |
