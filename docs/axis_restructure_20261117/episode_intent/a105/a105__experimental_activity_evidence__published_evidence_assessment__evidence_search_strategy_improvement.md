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
