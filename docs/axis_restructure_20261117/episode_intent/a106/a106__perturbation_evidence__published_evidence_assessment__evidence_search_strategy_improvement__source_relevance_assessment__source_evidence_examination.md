# a106/.../source_relevance_assessment/source_evidence_examination — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/<file>`
(only files directly in this folder plus `grading/` and `scoring/`; the three child folders and `tests/`, which holds
only an empty `__init__.py`, are not covered here).

Old binding class: `LiteratureEpisode` (`binding_path = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'`,
`commissioning_parent = '.../source_relevance_assessment'`, `roles = ('literature_page',)`, `entry_roles = ()`).
Decision source `LiteratureTask`. Model prompt renderer `render_literature_experimental_prompt` (old shared
`library/literature_experimental_prompt`). Binding record version `literature_episode_binding_v1`; task contract
version `literature_local_task_v1`; evidence axis `A106`. The class docstring calls it the "C7 binding for C10
assignments; no model connection or private loop".

## What it is for (its goal, in its own words)

Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_page']`):

> Investigate where and how this exact source should be examined. Choose ordinary source operations or selected
> table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML
> headings, tables and footnotes; retained original bytes remain addressable.

`goal.py` `LiteratureGoal.instructions()` joins this text with `PERTURBATION_TASK` (old shared
`library/literature_perturbation_prompt`) and `TASK` (old shared `library/literature_a106_subscore`). Those two
texts live in the old shared library, which is out of bounds for this read; their content is not reproduced here.

The module docstring of `source_contracts.py` states the binding's own scope: it "supplies operands, available
ordinary operations, source custody, and the commissioned task's private yield binding when selected. The shared
source owns decisions, reasoning commits, commissioning and report updates. In particular, a reading selection is
information for an investigation, never a script that this binding executes."

`goal.planning_context()` (shown to the model as `literature_goal_plan` when the assignment carries a
`literature_task`): `objective` (= request goal), `proposed_annotation_ref`, `commissioned_result` (the task),
`progress_definition` (= the credit projector's `as_record()`), `planning_question` (= the instructions above).

## Task and instructions

The commissioned task (`goal.task_schema()`) is one of three typed results, each with `version`
`literature_local_task_v1`, `evidence_axis` `A106`, a positive `credit_unit` and optional `yield_settings`
(`kind` accumulation | remaining_commissioned_credit, `cutoff` >= 0, `uncertainty_alpha` in (0,1)):

| task key | shape | answer |
|---|---|---|
| `A106:verified_source_leads` | `kind: verified_source_leads` | source-lead dispositions (`literature_source_lead_dispositions`) |
| `A106:source_answer:assessment` | `answer_kind: assessment`, `source_refs` (>=1) | `changed_assessment_refs` |
| `A106:source_answer:screening` | `answer_kind: screening`, `examined` spans (`source_ref`, `artifact_ref`, `start`, `end`) | `literature_screening_answers` |

Schema description: "Select only a task whose typed result is requested by the original return contract. A106
score computation is automatic work, not an episode-credit task."

`goal.commissioned_task(context)` rejects (each a named `ContractError`): no `literature_task`; non-finite
`credit_unit`; no `proposed_annotation_ref`; request without goal/report_contract or whose
`message.episode_assignment` differs from the assignment; return schema lacking the `x-source` the task needs;
selected `metrics`/`components` not a subset of one declared return's component enum; screening span with
`end <= start`; any task source outside the assigned page (`assignment.get('page', assignment)` — here the
assignment itself is the page); screening span on a different artifact than the page.

Model instructions (`task_instructions.py`), in order:
1. base `INSTRUCTIONS` from old shared `library/literature_investigation_prompt`, extended (or replaced when the
   binding sets `replaces_default_instructions`; this one does not) by the goal text above;
2. `REASONING_COMMIT_REQUIREMENT` when `reason` is permitted;
3. tool-knowledge and launch-instruction-library instructions when those inputs are in context;
4. the fixed `pending_child_delivery` → `redeliver_report` repair paragraph ("Use only the saved child facts and
   interpretations for this repair and preserve current_report_update ... this repair does not select new
   scientific work");
5. when `wait` is permitted, the in-process `pending_child_` wait paragraph (event `returned`, `after_cursor 0`,
   `reconsider_at null`; "Waiting only reports readiness and earns no scientific credit");
6. when native event targets exist and `wait` is permitted, the native_event_targets paragraph ("No event
   probability, gain or scientific credit follows from registration or passing time alone");
7. under `decision_exchange_v1`, the fresh-conversation history paragraph is replaced by the request_context /
   `episode.history view=records` paragraph.

`task.py` (`LiteratureTask`) is one decision per unit: replay saved calls/actions, build `decision_state(view)` and
the action schema, call the model, `apply_response()` admits the selection (reason commit must be non-empty unless
`evidence_processing.kind == no_applicable_evidence` or the binding's `reasoning_has_task_content` accepts a
`source_lead`), validates `report_update` against the interpretation form; `execute()` runs tool / reason / wait,
records the result, receives native and scientific outcomes, runs automatic score updates (not for wait), reads
credit (`last_observed_credit` for wait, otherwise `source_credit_view`), and returns the controller value. A
model-call failure ends the episode with `SourceEnd('source_failed')` and a recorded source failure; an
invalid/failed tool result still enters the iterator (feedback recorded, credit read, `ActionFailure` raised only
when no outcome was observed).

## What it reads from its parent's assignment

Assignment schema (`from_parent.assignment_schema`) = `_PAGE`:
`version: page_assignment_v1`, `source_ref`, `representation` (text | original | stdout | stderr), `artifact_ref`,
`question_context_refs`, `prior_delivery_refs`; plus `literature_task` (above), `proposed_annotation_ref` (both
required when `private_yield_binding`), and arrays of requested return components for each numerical family:
concentration window, measurement comparison, kinetic summary precision, reported-curve grid, rate observation,
calibration recovery, product coupling, measurement validation, rate replicate, rate, quantity, assay, ratio,
binding, binding model, transport, perturbation, perturbation summary, endpoint signal, figure, amount, optical,
kinetic, kinetic model, binding interaction (and model), perturbation operands, intervention grading, A106
subscore; conditionally ion discrimination, channel, compiled assay v1/v2/v3, product partition, completion time,
active site, parent depletion, stoichiometric balance, ratio source, controlled response (components, views,
component keys), gel (components, views, component keys).

`_validate_page`: source in scope; `artifact_ref` equals the source's artifact for that representation (`text`
falls back to `artifact_ref` when no `text_ref`); artifact in scope; every question-context and prior-delivery ref
in scope.

`prepare_assignment` (used by its parent `source_relevance_assessment` to build this episode's assignment): an
operation key is required; with `private_yield_binding`, the task key must have a declaration in
`yield_bindings`, and `credit_unit`/`yield_settings` are filled from that declaration (a supplied value that differs
is an error); the child's `proposed_annotation_ref` must equal the parent's
(`services.proposed_annotation_for(parent)` or the parent assignment's). The `parent.role == 'literature_page'`
branch in this copy is unreachable here (its parent is `literature_search`).

## Children it may commission

`_CHILDREN['literature_page'] = ('literature_table', 'literature_ordered', 'literature_targeted')`:

| old role | child folder | to_child / from_child |
|---|---|---|
| `literature_table` | `table_evidence_extraction` | `to_child_table_evidence_extraction.py` / `from_child_table_evidence_extraction.py` |
| `literature_ordered` | `source_coverage_improvement` | `to_child_source_coverage_improvement.py` / `from_child_source_coverage_improvement.py` |
| `literature_targeted` | `passage_evidence_extraction` | `to_child_passage_evidence_extraction.py` / `from_child_passage_evidence_extraction.py` |

What it sends (`to_child_*.prepare_request`, identical except the role string): child scope validated as a
sub-scope of this episode's; child report schema and declaration from the expanded contract form; each fact source
the child binding requires must appear exactly once in the schema; the initial report must satisfy the
interpretation schema; the role must be allowed for this parent; launch instructions materialized; optional
`prepare_child_request`; then the child binding's `prepare_assignment` builds the child's assignment with operation
key `run:episode:index`. The child's assignment shape (owned by the child) is `reading_assignment_v1` = this
page (`page`) plus a reading `selection`: table — a `_TABLE` (`source_ref`, `sheet_key`, `offset`, `limit`,
`header_row`, `where` {column, equals|contains, value, case_sensitive}) or a byte `_WINDOW` (`source_ref`,
`representation`, `offset`, `limit`); ordered — one `_WINDOW`; targeted — `spans`, one or more `_WINDOW`s. The child
re-checks that its reading stays within this page's source.

What it takes back (`from_child_*.receive_report`, identical): the child's typed form; references inside the
admitted form (scoped), plus population-cell receipts registered through `received_form_references` (each numerical
family's `receive_cells` / `cell_record_refs`), plus native timing receipts; child progress forms are passed to the
progress receiver. Received source-lead dispositions in a child form also count toward this episode's leads credit
(`credit.lead_dispositions` reads admitted child forms).

## Decision state and what it shows the model

`decision_state.py`: goal, scope, working state, visible record refs, `current_credit`, `current_evidence_vector`,
`investigation_progress` (retained_finding_count, inactive_dependencies, detail_pages) when receipt projection is
on, credit binding, time accounting, pending work, last local outcome and feedback, visual evidence from the last
completed `image.view`, report deliveries, controller state and binding, tools, tool knowledge, job episode options,
`available_report_facts`, requested report purpose/form, current report update and basis, report lifecycle note;
proposed annotations/annotation context for scientific sources; then the binding's own `decision_context`.

`internal_summary.decision_context()` (this episode's own view): `literature_assignment`,
`literature_source_custody` (version, artifact/text/stdout/stderr refs, parent_source_refs of the page source),
`own_literature_outcomes` (own acquisition/read outcome metadata, page of `outcome_page_size`, default 8),
`literature_history_meaning` ("Own outcome metadata only ... Source delivery does not establish understanding,
absence or resolved science."), `literature_examined_source_inputs`, `received_intervention_analysis_rows`
(BV-BRC application return rows actually received), `literature_experimental_work`
(`literature_experimental_task_v1`, aspect `source_experimental_evidence`, axis A106), ratio-source return meanings,
controlled-response and gel return bindings/records (when enabled), native rate / rate-domain / rate-meaning
display, received fact display, endpoint / summary-precision / measurement-comparison / concentration-window
receipt bindings, `literature_owned_population_sources` and the latest failed population attempt,
`literature_completed_work` and `literature_current_scoring_sheets`, and `literature_goal_plan`.

`decision_inputs.py` adds resource context, shared information context, launch instruction library (and selected
launch instructions), child options, `completed_action_reports`, pending work, execution expectations, resource and
native estimates, waiting support and the contract-information profile.

## Tools it offers

`permitted_common_actions`: `tool`, `reason`, `child`, `wait`, `redeliver_report`.

Catalog (`source_operations.catalog`): access tools only — `state.query`, `source.read`, `source.locate`,
`source.sequence.scan`, `source.sequence.references`, `source.experimental.records`, `image.view`,
`source.archive.members`, `source.archive.extract`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`,
`source.pdf.text`, `source.pdf.page`, and `execution.estimate` restricted to its xlsx sheets/rows branches. Public
acquisition tools (`public.literature.*`, `public.ncbi.search`, `public.pmc.*`, experiment-database operations) are
not offered; they are only used to filter own outcome history. Then the A106 population operations in fixed order
(36: `literature.concentration_window.populate` ... `literature.intervention_grading.populate`,
`literature.a106.finalize`, ..., `literature.gel.populate`), several gated by the population flags; with a
contract-information profile each gets `argument_transport`. `literature.intervention_analysis.contract` is handled
in `execute` (BV-BRC TnSeq/RNASeq adapter contract; `service_availability: not_observed`).

Custody rules (`_tool_arguments`): every source argument (including `metadata_source_ref`, sheet/covariance/model/
km/data/coordinate/validation source refs, visual refs) must be within the assigned page source (walking
`parent_source_refs`), else `literature_reading_outside_assigned_source`; reads and `state.query` are authorized
against the endpoint-signal, summary-precision, measurement-comparison and concentration-window repositories.

Reasoning: `_required_grading_repository` returns `None`, so the reason envelope is the ordinary commit, except for a
`verified_source_leads` task, where it gains a `source_lead`. `execute_reasoning` then reads the witness span, commits
the reasoning and validates the lead (`credit.validate_lead`: proposed annotation and source match, non-empty
relevance rationale, source/subject/annotation actually received, subject anchored in that source and inside the
witness, source is an acquired page not a search page).

`grading/intervention_assessment.py`: `InterventionAssessment` gives the intervention-grading repository its cell
reader (BV-BRC application outcomes, controlled-response, gel or any population route, each validated against its
report schema). `scoring/intervention_main_sheet.py`: `InterventionMainSheet` holds the A106 subscore repository
(`literature.a106.finalize`, `automatic_score_judgments`, `complete_score_judgment`).

## How its credit is counted

`credit_kind` = `scientific`. `credit_view` goes through `services.scientific_credit_for` (with
`_scientific_credit_invocation`) or `services.scientific_credit`. `credit_projector` = `LiteratureTaskCredit`:

- record: `{kind: literature_local_task_v1, task: <task key>, credit_unit, unit: one_verified_source_for_original_question | one_answer_to_original_commission, revision_credit: False, activity_credit: False, annotation_support: separate}`;
- checks: same run/episode/scope/goal/purpose/schema/initial report and proposed annotation as the commission;
  the proposed annotation is a hypothesis in scope rooted in a target subject;
- `credit = credit_unit × len(items)`, finite, never clamped:
  - leads: lead dispositions with `disposition == 'relevant'`, from own completed reason results and from admitted
    child forms in decision order, latest per canonical source identity wins;
  - screening: one answer only when every requested examined span is covered by own `no_applicable_evidence`
    witnesses on the same source/artifact;
  - assessment: one item for the first current, retained, target-eligible assessment of the proposed annotation
    whose observation is anchored in one of the task's `source_refs`;
- `task_status`: answered | unanswered | unresolved_contract; `source_contributions` lists the items.

## Continuation (yield estimator and settings)

`yield_estimator.LiteratureYield.yield_controller`: only when `private_yield_binding`; key = task key; declaration
from `yield_bindings[key]` = `{credit_unit, kind, cutoff, uncertainty_alpha}` (validated up front; kind must be
`accumulation` for leads, `remaining_commissioned_credit` for the two answers; positive finite unit).

- `A106:verified_source_leads` → plain controller (`epoch`, initial credit, `cutoff`, `uncertainty_alpha`):
  maps to the **accumulation** estimator.
- `A106:source_answer:*` → `_FiniteLiteratureYieldController` with `maximum_credit = credit_unit`: forecast next gain
  is the observed-history forecast with its band limited to the remaining commissioned credit, exactly zero once all
  requested answers are earned: maps to **completion with a target** (target = `credit_unit`). The limit applies to
  the forecast, not to credit.

Stops when the next-credit upper estimate is at or below `cutoff`, in this task's credit unit.

## What it reports to its parent

`fact_sources`: all numerical return namespaces (`literature_*_cells`, each with its meaning text and report schema;
conditional ones by flag), `literature_screening_answers`, `literature_source_lead_dispositions`.
`facts`: numerical cells for committed and current sheet refs actually received (per-namespace version checks), current
report facts (`literature_completed_work`, `literature_current_scoring_sheets`), screening answers (screening task)
and lead dispositions (leads task). `validate_report`: assignment re-validated; leads/screening returns must equal the
saved work exactly; numerical rows must be received or known to the receiver, only requested components, and the exact
requested subset. `finish`: without a contract, `{credit, pending_handles, current report facts}`; otherwise the form is
built from interpretations plus facts and saved.

`received_report_sources` / `received_report_facts` return empty for all literature roles.

## Differences from siblings / similar episodes

- The three children have identical file sets, nearly identical code; this episode alone has `to_child_*`/
  `from_child_*` files and the `child_request_preparer` / `child_report_receiver` maps, and no `from_parent_page.py`.
- Its assignment is the page itself; the children's is `reading_assignment_v1` (page + selection).
- Its `commissioning_parent` is `source_relevance_assessment` (role `literature_search`).

## File by file

| old file | lines | own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `episode.py` | 74 | composes the binding (15 mixins), roles, child preparer/receiver maps, `_SOURCE_REPOSITORIES` (19 repository classes), `context_hook_applies` | import of old `library.literature_experimental_prompt` |
| `binding_record.py` | 26 | saved configuration record (flags, yield bindings, profile, descriptors) | — |
| `configuration.py` | 100 | constructor: `outcome_page_size`, 11 population flags, ratio/controlled-response/gel evidence origin + descriptors, `private_yield_binding`/`yield_bindings`, contract-information profile, `reference_parent_sources`; `reference_evidence()` entry | `import:a106.composition_information`, library controlled_response/gel storage |
| `source_contracts.py` | 51 | ROLES, schemas `_WINDOW`/`_TABLE`/`_PAGE`, `_CHILDREN`, tool lists, role instructions, population catalog order | `import:a106.communication`, `composition_information`, `domain`, `episode_bindings` (`reference_in_context`), `experimental_database_acquisition`, `library` |
| `goal.py` | 104 | task schema, `commissioned_task`, `continuation_task`, instructions, planning context | `import:a106.communication`, `domain`, `numerical` (YieldController, YieldEstimate, YieldParameters, estimate_score_yield, NumericBand, STATUS_NORMAL — imported, unused here), library prompts |
| `task.py` | 215 | decision loop: next / apply_response / execute | `import:a106.runtime` (+module), `bind_functions`, `episode_source_failure`, `providers` (ModelCallError); self.workflow.journal ×7, store ×9, execution_binding ×7, inprocess_replay ×4, completions ×3, completed_unit ×3, selected ×3, decision_exchanges ×3, run_id ×3, controller_value ×2, specialist ×2, binding_context ×2, services, permits_common_action, reasoning_action_schema, resolver, validate_report, execute, pending_work, receive_native_outcome, receive_outcome, automatic_score_updates, last_observed_credit, source_credit_view, retain_shared_grading_results, next_return, resolve_pending_deliveries; tables runtime_actions ×8, runtime_model_calls ×2, runtime_episodes |
| `task_state.py` | 114 | per-episode state, restore/checkpoint, execution-failure recording | runtime (+module), bind_functions, episode_source_failure; self.workflow.inprocess_replay ×7, journal ×5, completions ×4, execution_binding ×4, progress_provider ×2, store ×2, archive, controller_value, recover_commissions, run_id, source_credit_view; workflow.context, workflow.grains; table runtime_actions ×5 |
| `task_decision.py` | 427 | model call, decision-exchange protocol, contract-information validation, presentation dispatch | runtime (+module), bind_functions, `a106.providers` / root `providers` `_ORIGINAL_MODEL_*`; self.workflow.validate_contract_information ×5, decision_exchanges ×4, receipts ×4, decision_protocol ×3, journal ×3, provider ×3, specialist ×2, store ×2, uses_received_record_context ×2, contract_information_profile, contract_information_reply, freeze_contract_information, freeze_literature_numerical_contracts, numerical_contracts, history_preview, execute, services (decision_exchange_instructions), run_id; table runtime_model_calls ×8 |
| `task_instructions.py` | 24 | instruction composition (above) | source.workflow.permits_common_action ×3, specialist, binding_context, knowledge, launch_instructions, native_event_information, decision_protocol; library `literature_investigation_prompt` |
| `decision_inputs.py` | 78 | extra decision inputs | runtime (+module), bind_functions; self.workflow.resource_estimator ×4, launch_instructions ×2, resource_context, shared_information_context, available_child_roles, episode_bindings, binding_context, pending_work, execution_expectations, native_estimation_context, permits_common_action, waiting_support, action_schema, delivery_resolution_inputs |
| `decision_state.py` | 59 | decision state composition | runtime (+module), bind_functions; self.workflow.journal ×3, store ×3, working_state, run_id, local_outcome_preview, source_credit_view, receipt_projection, source_credit_binding, pending_work, delivery_status, controller_binding, catalog, knowledge, job_episode_options, extra_report_sources, is_scientific_source, annotation_context, specialist, binding_context, tools; table runtime_actions ×2 |
| `decision_presentation.py` | 33 | completed-work reports, yield table | runtime (+module), bind_functions, `episode_work_report`; self.workflow.controller_binding; `_category_yield_parameters`, `yield_table` |
| `from_parent.py` | 165 | assignment schema, page validation, `prepare_assignment` with private yield binding | services.proposed_annotation_for; ~40 library storage/calculation imports for component enums |
| `to_child_table_evidence_extraction.py` | 33 | sends `literature_table` request | `import:a106.runtime`; workflow.binding_context ×4, episode_bindings ×3, expanded_contract_form, child_initial_report_input, available_child_roles, annotation_child_roles, services (capabilities), specialist, launch_instructions, store, run_id |
| `to_child_source_coverage_improvement.py` | 33 | sends `literature_ordered` request | same as above |
| `to_child_passage_evidence_extraction.py` | 33 | sends `literature_targeted` request | same as above |
| `from_child_table_evidence_extraction.py` | 42 | receives child typed form | runtime, `episode_return_records`, `delivery_counterpart`; workflow.store ×7, run_id ×6, binding_context ×4, progress_provider ×4, receipts ×3, is_job_source ×2, job_episodes ×2, native_timing_information, episode_bindings, specialist; table runtime_report_attempts ×2 |
| `from_child_source_coverage_improvement.py` | 42 | same | same |
| `from_child_passage_evidence_extraction.py` | 42 | same | same |
| `internal_summary.py` | 306 | decision context (above), owned population sources, display contexts | services.read_record ×5, own_outcomes, self.services.workflow.store ×2, workflow.store ×2, workflow.run_id ×2; table runtime_actions ×2; 11 library imports |
| `received_evidence.py` | 269 | received-report facts/references/tokens, return validation, `received_application_rows` | services.record_selection ×3, self.services.workflow.store ×2, `domain`, `method_loop.durable`, `library.intervention_execution_lookup`; 16 library imports |
| `scientific_records.py` | 223 | lazy construction of every A106 numerical repository, `_population_routes` | self.services.workflow.store ×18, run_id ×18; 40 library imports |
| `source_operations.py` | 216 | permitted actions, reason schema, lead reasoning, catalog, execute, custody, `prepare_analysis_contract` | services.tool_catalog, execute_tool, read_record ×4, self.services.workflow.store; `composition_information`, `domain`, `literature_contract_error`, `bvbrc_appservice_adapters`, `library.intervention_execution_lookup` |
| `source_references.py` | 35 | scope check, artifact by representation, `_within_source`, resolve | services.reference_in_scope, read_record; `reference_in_context` |
| `credit.py` | 202 | lead validation, lead dispositions, screening answers, current assessments, `LiteratureTaskCredit`, credit view | services.scientific_credit_for, scientific_credit, proposed_annotation_for, annotation_task_required; workflow.scientific_projector_for_context, projector_receipt_arguments, projection_view; `numerical` names (imported); `finding_validity`, `scientific_findings`; tables runtime_actions ×4, runtime_report_attempts ×2 |
| `yield_estimator.py` | 103 | yield binding validation, remaining-commissioned-credit forecast, controller | `numerical`: YieldController ×4, YieldParameters ×3, estimate_score_yield ×3, YieldEstimate ×2, NumericBand ×2, STATUS_NORMAL ×2 |
| `to_parent.py` | 185 | fact sources and their meanings, facts, validate_report | services.read_record ×3, self.services.workflow.store ×3, services.workflow / workflow.store ×2; 44 library imports |
| `report_delivery.py` | 33 | finish | runtime (+module), bind_functions; self.workflow.release ×2, journal ×2, source_credit_view, pending_handles, episode_bindings, binding_context, facts; table runtime_forms ×2 |
| `waiting.py` | 37 | `supports_wait = True`, selected wait, suspension | runtime (+module), bind_functions; self.workflow.perform_selected_wait, execution_handle ×2, execution_backend |
| `grading/intervention_assessment.py` | 33 | intervention grading repository and its cell reader | self.services.workflow.store, run_id; library intervention storage |
| `scoring/intervention_main_sheet.py` | 13 | A106 subscore repository, automatic score judgments | self.services.workflow.store, run_id; library a106 subscore storage |

Every `bind_functions` file also calls `_bind_original_task_runtime_providers(vars(runtime))` at import.
Full per-file counts: `runs/carry_over/calls/a106_03.tsv`.
