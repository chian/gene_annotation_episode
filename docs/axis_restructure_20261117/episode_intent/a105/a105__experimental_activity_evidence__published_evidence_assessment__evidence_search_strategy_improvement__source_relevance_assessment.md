# a105/.../evidence_search_strategy_improvement/source_relevance_assessment — intent carried over from 97308b94c

Full path: `a105/experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment`.
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/<that path>/<file>` (files directly in
this folder plus `grading/` and `scoring/`; the `source_evidence_examination/` child is described separately).
Class `LiteratureEpisode`, decision source `LiteratureTask`, `decision_prompt_renderer =
render_literature_experimental_prompt`. `binding_path = '.../evidence_search_strategy_improvement/source_relevance_assessment'`,
`commissioning_parent = '.../published_evidence_assessment/evidence_search_strategy_improvement'`, role
`literature_search`, `roles = ('literature_search',)`, **`entry_roles = ()`**, binding id
`experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment`.

Files are copies of its parent `evidence_search_strategy_improvement` (and of `published_evidence_assessment`); only the
differences listed below are this episode's own. See the `published_evidence_assessment` document for the full content
of the shared parts.

## What this episode is for (its goal, in its own words)

`_ROLE_INSTRUCTIONS['literature_search']`: "Investigate which returned sources merit examination for the assigned
question. Search results are source-discovery information. Examine original sources and their conditions before
asserting biological evidence. A page child can investigate where and how to examine a selected source." Followed by
the common literature paragraph ("This is an iterative scientific investigation in the shared Episode loop ...
Distinguish source claims from their applicability to the fixed target ... The commissioned task's own yield settings
guide continuation.").

The concrete goal is the same commissioned literature task (`literature_local_task_v1`, A105). For this role the
natural task is `verified_source_leads` (lead disposition `relevant` / `not_relevant`, relevance rationale, source
witness — "This is not evidence supporting or opposing the proposed annotation"; "a search hit or matching title alone
is not verification"), but every task kind of the schema is accepted.

## Task and instructions

Same composition and loop as the parent; `validate_report` with `grain='literature_search'`; execution expectations
captured under `'literature_search'`; no wait text.

## What it reads from its parent's assignment

`assignment_schema('literature_search')` → **`search_assignment_v1 {question_context_refs, search_result_refs,
literature_task, proposed_annotation_ref}`** plus the population `requested_*_components` selectors.
`search_result_refs` must be in scope as `source` records. Same private yield declaration and proposed-annotation
checks. The `literature_page` branch cannot apply (`'literature_search' not in _CHILDREN['literature_page']`).

## Children it may commission

| child role | folder | what it sends | what it takes back |
|---|---|---|---|
| `literature_page` | `source_evidence_examination` | `to_child` = deep copy; `prepare_request` (role `literature_page`): scope, expanded return schema, initial report, permitted role, child's `prepare_assignment` (page assignment for one selected source) | `receive_source_evidence_examination`: population-cell admission and record-ref collection (same code as the parent's receiver); `receive_report` with receipts / progress provider / native timing |

## Decision state and what it shows the model

Same as the parent; source custody uses `source_refs` (absent in a search assignment, so empty unless a page is
present); `literature_assignment` shows `search_result_refs`. No `waiting_support`. Presentation-aware completion.

## Tools it offers

Identical to the parent: access + acquisition tools, A105 population operations under `rate_population`, required
grading and source-lead reasoning. Common actions: tool, reason, child, redeliver_report; `supports_wait = False`.

## How its credit is counted

Identical `LiteratureTaskCredit`: `credit_unit × number of answers`; for `verified_source_leads`, the number of
current `relevant` lead dispositions (own reasoning results and admitted child forms, latest per canonical source).
Unbounded; finite check only.

## Continuation

Identical `LiteratureYield`: `verified_source_leads` → accumulation; others → completion with target (remaining
commissioned credit). Old `None` without private yield binding must become an explicit error.

## What it reports to its parent

Identical `fact_sources` / `facts` / `validate_report`; lead dispositions are returned as
`literature_source_lead_dispositions` and must equal the saved work. No `received_form_references`.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | — | — |
| `binding_record.py` | 43 | record with own binding id | — |
| `configuration.py` | 119 | same flags / validation | `a105.composition_information:CONTRACT_INFORMATION_PROFILE`; 2 `a105.library` modules |
| `credit.py` | 289 | literature task credit (copy) | `self.services.{scientific_credit, scientific_credit_for, proposed_annotation_for, annotation_task_required}`; `workflow.{scientific_projector_for_context, projector_receipt_arguments, projection_view}`; tables `runtime_actions×4`, `runtime_report_attempts×2`; 5 `a105.library` modules |
| `decision_presentation.py` | 18 | completed-action reports; yield table | `self.workflow.controller_binding`; runtime `{_category_yield_parameters, Mapping, yield_table}`; `a105.episode_work_report` |
| `episode.py` | 88 | composition; role `literature_search`; child maps for `literature_page` | `a105.library.literature_experimental_prompt` |
| `from_child_source_evidence_examination.py` | 123 | receive page child's cells/refs | `self.services.workflow.store`; `workflow.{receipts×3, is_job_source×2, store×8, run_id×4, binding_context×2, progress_provider×2, specialist, native_timing_information, job_episodes×2}`; table `runtime_report_attempts×2`; `EpisodeReturnRecords`; `WorkflowError`; 16 `a105.library` modules |
| `from_parent.py` | 162 | search_assignment_v1 schema and preparation | `self.services.proposed_annotation_for`; 38 `a105.library` modules |
| `goal.py` | 131 | task schema/checks, search goal text, planning context | `a105.communication`, `a105.domain`, 2 `a105.library` modules |
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
| `task.py` | 311 | catalog/execute + decision loop (`grain='literature_search'`) | as `published_evidence_assessment/task.py` |
| `task_decision.py` | 352 | model call / exchanges / presentation completion | as `published_evidence_assessment/task_decision.py` (`providers` internals included) |
| `task_instructions.py` | 28 | instruction composition | `runtime_prompt.*`; `source.workflow.*` |
| `task_state.py` | 108 | episode state | as parent |
| `to_child_source_evidence_examination.py` | 35 | `literature_page` request | `workflow.{store, expanded_contract_form, episode_bindings×3, binding_context×4, child_initial_report_input, specialist, available_child_roles, annotation_child_roles, services.capabilities, launch_instructions, run_id}`; runtime names |
| `to_parent.py` | 322 | fact sources, facts, received-report validation | `self.services.{read_record, record_selection}`; `self.services.workflow.store`; `ReportBoundaryError`; `a105.library` modules |
| `waiting.py` | 8 | `supports_wait = False` | — |
| `yield_estimator.py` | 109 | yield bindings, remaining-commissioned-credit forecast | `a105.numerical:{YieldController, YieldParameters, YieldEstimate, NumericBand, STATUS_NORMAL, estimate_score_yield}` |

Full counts: `runs/carry_over/calls/a105_01.tsv`.

## Differences from similar episodes

- vs parent `evidence_search_strategy_improvement`: role `literature_search`, binding id/path, `search_assignment_v1
  search_result_refs`, search role text, child `literature_page` (`source_evidence_examination`). Everything else is an
  identical copy (normalised `diff` shows only these lines).
- vs `published_evidence_assessment`: additionally `entry_roles = ()`, no `create_binding_tree`, no
  `received_form_references`, `context_hook_applies` False for non-family roles.
