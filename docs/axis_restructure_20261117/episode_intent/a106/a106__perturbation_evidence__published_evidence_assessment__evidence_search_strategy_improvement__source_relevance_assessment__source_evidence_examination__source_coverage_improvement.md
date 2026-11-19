# a106/.../source_evidence_examination/source_coverage_improvement — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/<file>`
(only files directly in this folder plus `grading/` and `scoring/`; `tests/` holds only an empty `__init__.py`).

Old binding class: `LiteratureEpisode` (`binding_path = '.../source_evidence_examination/source_coverage_improvement'`,
`commissioning_parent = '.../source_relevance_assessment/source_evidence_examination'`, `roles = ('literature_ordered',)`,
`entry_roles = ()`). Decision source `LiteratureTask`. Model prompt renderer `render_literature_experimental_prompt`
(old shared `library/literature_experimental_prompt`). Binding record version `literature_episode_binding_v1`; task
contract version `literature_local_task_v1`; evidence axis `A106`. A leaf: `_CHILDREN['literature_ordered'] = ()`.

## What it is for (its goal, in its own words)

Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_ordered']`):

> Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes.

`goal.py` `LiteratureGoal.instructions()` joins this text with `PERTURBATION_TASK` (old shared
`library/literature_perturbation_prompt`) and `TASK` (old shared `library/literature_a106_subscore`); those two texts
are in the old shared library (out of bounds; not reproduced). `source_contracts.py` docstring: "a reading selection
is information for an investigation, never a script that this binding executes."

`goal.planning_context()` (shown as `literature_goal_plan` when a `literature_task` is assigned): `objective`,
`proposed_annotation_ref`, `commissioned_result`, `progress_definition` (credit projector record),
`planning_question`.

## Task and instructions

Same three commissioned task kinds as its parent `source_evidence_examination` (`goal.task_schema()`, identical
code): `A106:verified_source_leads` (lead dispositions), `A106:source_answer:assessment` (`source_refs`;
`changed_assessment_refs`), `A106:source_answer:screening` (`examined` spans; `literature_screening_answers`), each
with `credit_unit` and optional `yield_settings` {kind, cutoff, uncertainty_alpha}. "A106 score computation is
automatic work, not an episode-credit task."

`commissioned_task` checks are the parent's, except the assigned page is `assignment.get('page', None)` (the page
inside the reading assignment): all task sources must be that page's source; screening spans must be on that page's
artifact.

Model instructions (`task_instructions.py`, identical to the parent's): base `INSTRUCTIONS` (old shared
`literature_investigation_prompt`) + goal text; `REASONING_COMMIT_REQUIREMENT`; tool-knowledge and launch
instructions when present; `pending_child_delivery` → `redeliver_report` repair paragraph; `pending_child_` wait
paragraph when wait is permitted ("Waiting only reports readiness and earns no scientific credit"); native event
targets paragraph; decision_exchange_v1 history replacement. `task.py`, `task_state.py`, `task_decision.py`,
`decision_inputs.py`, `decision_state.py`, `decision_presentation.py`, `report_delivery.py`, `waiting.py` are
byte-identical to the parent's apart from module paths and the role name in docstrings (same decision loop: invalid
or failed returned results still enter the iterator; model-call failure ends with `source_failed`).

## What it reads from its parent's assignment

Assignment schema (`from_parent.assignment_schema`): `version: reading_assignment_v1`, `page` = the parent's
`_PAGE` (`page_assignment_v1`, `source_ref`, `representation`, `artifact_ref`, `question_context_refs`,
`prior_delivery_refs`), and `selection` = one `_WINDOW` (`source_ref`, `representation`, `offset`, `limit`) — the starting window for reading in document order; plus top-level `literature_task`, `proposed_annotation_ref`
(required with `private_yield_binding`) and the same requested-component arrays for every numerical family as the
parent (conditional ones by population flag).

`_validate_assignment`: page validated as in the parent (source/artifact/representation/context refs in scope); then
for the single window, each window's `source_ref` must equal the page's (`literature_reading_source_mismatch`); a window with a
`representation` must match the page's (`literature_reading_representation_mismatch`) and its `offset` must not exceed
the page artifact's size (`source_offset_out_of_bounds`).

`prepare_assignment` (called by the parent page episode): operation key required; private yield binding fills
`credit_unit`/`yield_settings` from this binding's `yield_bindings[task key]` (supplied mismatch is an error);
proposed annotation must equal the parent's; and, because the parent role is `literature_page`, the parent's own page
assignment is validated with `from_parent_page.OriginalPageAssignment._validate_parent_page` (the parent's `_PAGE`
schema with task, annotation and requested components) and the reading's `page.source_ref` must be within the
parent's page source (`literature_reading_outside_assigned_source`).

## Children it may commission

None (`_CHILDREN['literature_ordered'] = ()`; `allowed_children` returns `()`), although `permitted_common_actions` still lists
`child`. No `to_child_*` / `from_child_*` files.

## Decision state and what it shows the model

As the parent (`decision_state.py`, `decision_inputs.py` identical). `internal_summary.decision_context()` is the
parent's with `page = assignment.get('page')`: `literature_assignment` (the whole reading assignment, including the
selection), source custody of the page source, `own_literature_outcomes` (page of `outcome_page_size`, default 8),
`literature_history_meaning`, `literature_examined_source_inputs`, `received_intervention_analysis_rows`,
`literature_experimental_work`, the numerical display/receipt-binding contexts, owned population sources and the
latest failed population attempt, `literature_completed_work`, current scoring sheets, `literature_goal_plan`.

## Tools it offers

`tool`, `reason`, `child`, `wait`, `redeliver_report`. Same catalog as the parent: access tools (`state.query`,
`source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`,
`image.view`, `source.archive.*`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.*`, `execution.estimate`
restricted to xlsx branches) plus the 36 A106 population operations (some flag-gated) and
`literature.intervention_analysis.contract` in `execute`. Custody: every source argument must lie within the page
source (`_within_source` over `parent_source_refs`). Lead reasoning (`source_lead`, validated witness) only
for a `verified_source_leads` task; `_required_grading_repository` is `None`. `grading/intervention_assessment.py`
and `scoring/intervention_main_sheet.py` are identical to the parent's (intervention-grading cell reader; A106
subscore repository and automatic score judgments).

## How its credit is counted

Identical to the parent (`credit.py` same code): `credit_kind` `scientific`; `LiteratureTaskCredit` record
`{kind: literature_local_task_v1, task, credit_unit, unit, revision_credit: False, activity_credit: False,
annotation_support: separate}`; `credit = credit_unit × len(items)`, finite, never clamped. Items: relevant lead
dispositions (own reason results; `runtime_report_attempts` admitted child forms, none here since it has no
children), one screening answer when all requested examined spans are covered by own `no_applicable_evidence`
witnesses, or one current retained target-eligible assessment anchored in a task source.

## Continuation (yield estimator and settings)

Identical to the parent: only with `private_yield_binding`; `yield_bindings[task key] = {credit_unit, kind, cutoff,
uncertainty_alpha}`; leads → **accumulation**; source answers → **completion with a target** (target = `credit_unit`,
forecast band limited to remaining commissioned credit, exact zero once earned). Stops when the next-credit upper
estimate is at or below `cutoff`.

## What it reports to its parent

Identical to the parent (`to_parent.py`, `received_evidence.py`, `report_delivery.py` same code): all numerical
`literature_*_cells` namespaces, `literature_screening_answers`, `literature_source_lead_dispositions`; facts from
committed/current sheets actually received, completed work and scoring sheets; validation that leads/screening equal
saved work and numerical rows are received and exactly the requested subset. The parent page episode receives this
through its `from_child_source_coverage_improvement.py` (typed form references, population-cell receipts, native timing receipts), and
counts relevant leads in this form toward its own leads credit.

## Differences from siblings / similar episodes

- vs parent `source_evidence_examination`: reading assignment (`reading_assignment_v1`: page + selection) instead of
  the page itself; extra `from_parent_page.py`; leaf (no child files or child maps); `commissioning_parent` is the page
  episode; `page = assignment.get('page')` in goal, internal summary and source operations.
- vs siblings: `passage_evidence_extraction` takes one or more separate spans; `table_evidence_extraction` takes a table or one window and enforces the selected `sheet_key` on `source.xlsx.rows`; this episode takes exactly one window and continues by returned UTF-8 byte continuations. Everything else (credit, yield, report, tools, decision loop) is the same code.

## File by file

| old file | lines | own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `episode.py` | 63 | composes the binding with `OriginalPageAssignment` first, role `literature_ordered`, `_SOURCE_REPOSITORIES` | library `literature_experimental_prompt` |
| `binding_record.py` | 26 | saved configuration record, `binding_id` = this path | — |
| `configuration.py` | 100 | same constructor as parent | `composition_information`, library controlled_response/gel storage |
| `source_contracts.py` | 51 | ROLES, `_WINDOW`/`_TABLE`/`_PAGE`, `_CHILDREN`, tools, role instructions, catalog order (same values as parent) | `communication`, `composition_information`, `domain`, `episode_bindings` (`reference_in_context`), `experimental_database_acquisition`, `library` |
| `goal.py` | 104 | task schema, commissioned task (page from `assignment['page']`), instructions, planning context | `communication`, `domain`, `numerical` (YieldController, YieldEstimate, YieldParameters, estimate_score_yield, NumericBand, STATUS_NORMAL; imported) |
| `from_parent.py` | 177 | reading assignment schema with selection, window checks, `prepare_assignment` | services.read_record (artifact size), services.proposed_annotation_for; ~40 library component imports |
| `from_parent_page.py` | 119 | `_parent_page_schema`, `_validate_parent_page` | ~40 library component imports |
| `task.py` | 215 | decision loop (identical to parent) | as parent: runtime (+module), bind_functions, episode_source_failure, providers; self.workflow.journal ×7, store ×9, execution_binding ×7, inprocess_replay ×4, ... ; tables runtime_actions ×8, runtime_model_calls ×2, runtime_episodes |
| `task_state.py` | 114 | state/restore/checkpoint (identical) | as parent; workflow.context, workflow.grains; runtime_actions ×5 |
| `task_decision.py` | 427 | model call / decision exchange (identical) | as parent; runtime_model_calls ×8 |
| `task_instructions.py` | 24 | instruction composition (identical) | source.workflow.* (7 members) |
| `decision_inputs.py` | 78 | identical | self.workflow.* (17 members) |
| `decision_state.py` | 59 | identical | self.workflow.* (24 members); runtime_actions ×2 |
| `decision_presentation.py` | 33 | identical | `episode_work_report`, controller_binding |
| `internal_summary.py` | 306 | decision context with `page = assignment.get('page')` | services.read_record ×5, own_outcomes, self.services.workflow.store ×2, workflow.store/run_id; runtime_actions ×2 |
| `received_evidence.py` | 269 | identical | services.record_selection ×3, self.services.workflow.store ×2, `method_loop.durable`, `library.intervention_execution_lookup` |
| `scientific_records.py` | 223 | identical | self.services.workflow.store ×18, run_id ×18 |
| `source_operations.py` | 216 | catalog, execute, custody with `page = assignment.get('page')` | services.tool_catalog, execute_tool, read_record ×4, self.services.workflow.store; `composition_information`, `literature_contract_error`, `bvbrc_appservice_adapters` |
| `source_references.py` | 35 | identical | services.reference_in_scope, read_record; `reference_in_context` |
| `credit.py` | 202 | identical | services.scientific_credit_for, scientific_credit, proposed_annotation_for, annotation_task_required; workflow.scientific_projector_for_context, projector_receipt_arguments, projection_view; runtime_actions ×4, runtime_report_attempts ×2 |
| `yield_estimator.py` | 103 | identical | YieldController ×4, YieldParameters ×3, estimate_score_yield ×3, YieldEstimate ×2, NumericBand ×2, STATUS_NORMAL ×2 |
| `to_parent.py` | 185 | identical | services.read_record ×3, self.services.workflow.store ×3, workflow.store ×2; 44 library imports |
| `report_delivery.py` | 33 | identical | self.workflow.release ×2, journal ×2, facts, pending_handles, source_credit_view, episode_bindings, binding_context; runtime_forms ×2 |
| `waiting.py` | 37 | identical | perform_selected_wait, execution_handle ×2, execution_backend |
| `grading/intervention_assessment.py` | 33 | identical | self.services.workflow.store, run_id |
| `scoring/intervention_main_sheet.py` | 13 | identical | self.services.workflow.store, run_id |

Full per-file counts: `runs/carry_over/calls/a106_03.tsv`.
