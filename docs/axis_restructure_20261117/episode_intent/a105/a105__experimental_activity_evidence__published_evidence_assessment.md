# a105/experimental_activity_evidence/published_evidence_assessment — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/published_evidence_assessment/<file>`
(files directly in this folder plus `grading/` and `scoring/`; the `evidence_search_strategy_improvement/` child is
described separately). Class `LiteratureEpisode` (18 mixins), decision source `LiteratureTask`,
`decision_prompt_renderer = render_literature_experimental_prompt`. `binding_path =
'experimental_activity_evidence/published_evidence_assessment'`, `commissioning_parent = 'experimental_activity_evidence'`,
role `literature`, `roles = entry_roles = ('literature',)`, binding record `VERSION = 'literature_episode_binding_v1'`,
`binding_id 'experimental_activity_evidence/published_evidence_assessment'`.

## What this episode is for (its goal, in its own words)

`_ROLE_INSTRUCTIONS['literature']`: "Investigate which published evidence bears on the assigned scientific question.
You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower
question warrants iteration." Followed by the common literature paragraph: "This is an iterative scientific
investigation in the shared Episode loop. Earlier outcomes and admitted child forms inform later choices; no child
order, reading quota or complete-document requirement is prescribed. A one-off search/read is an ordinary tool. A
supplied reading selector is context, not an automatically executed action. Preserve the source's actual subject,
experimental conditions, representation, version and UTF-8 byte anchors. Distinguish source claims from their
applicability to the fixed target. Negative findings and qualifications can advance the investigation. Commit
interpretations with the common reasoning action and update only the parent's declared typed form in that same work
call. Navigation, byte coverage and repeated reading earn no scientific credit by themselves. The commissioned task's
own yield settings guide continuation."

The concrete goal is the commissioned **literature task** (`goal.task_schema`, version `literature_local_task_v1`,
evidence axis A105, `credit_unit > 0`, optional `yield_settings {kind, cutoff, uncertainty_alpha}`), one of:
- `verified_source_leads` — find sources that are relevant leads for the question (lead ≠ support);
- `source_answer/assessment` (`source_refs`) — a current retained assessment anchored in a named source;
- `source_answer/screening` (`examined` byte spans) — a source-grounded "no applicable evidence" over the whole spans;
- `source_answer/measurement` (`selection` = quantity population, `components` ⊆ reported_value/spread/relative_spread);
- `a105_experiments` (`experiments [{experiment_ref, assay_type}]`) — one graded assessment per original experiment;
- `a105_assembly` (`experiment_refs`, `metrics` ⊆ reliability/validity/relevance/attribution/overall) — A105 aggregate.
"A105 grading is a separate automatic operation, not earned by selecting a tool." `commissioned_task` also checks the
task's typed return is requested by the original return contract (`literature_source_lead_dispositions`,
`changed_assessment_refs`, `literature_screening_answers`, `literature_quantity_cells`, `literature_assay_grading_cells`,
`literature_a105_aggregation_cells`), components match, duplicate experiments are refused, and selected sources stay
inside an assigned page. `planning_context` shows `{objective, proposed_annotation_ref, commissioned_result,
progress_definition, planning_question}`.

## Task and instructions

`task_instructions.instructions`: base `runtime_prompt.INSTRUCTIONS` + this binding's instructions (appended) +
reasoning-commit requirement + tool-knowledge / launch-instruction texts + pending-child-delivery repair text; the wait
and native-event branches are `pass` (no wait text); decision-exchange history replacement as in the head.
`task.py` `LiteratureTask` has the same next/apply/execute/finish loop as the head, except: decision inputs are built
inline (no separate `decision_inputs.py`), `execute` has no `wait` branch and no `validate_execution_context` call,
`validate_report` is called with `grain='literature'`.

## What it reads from its parent's assignment

`assignment_schema('literature')` → `literature_assignment_v1 {question_context_refs, source_refs, literature_task,
proposed_annotation_ref}`; with `private_yield_binding` the task loses its required `credit_unit` and both
`literature_task` and `proposed_annotation_ref` become required. With `rate_population` ~30 `requested_*_components`
selectors are added (concentration window, measurement comparison, kinetic summary precision, rate grid, rate
observation, calibration recovery, product coupling, measurement validation, rate replicate, rate, quantity, assay,
ratio, binding, binding model, transport, endpoint signal, figure, amount, optical, kinetic, kinetic model, binding
interaction (+model)), plus per-flag selectors (ion discrimination, channel, compiled assay v1/v2/v3, assay grading +
A105 aggregation, product partition, completion time, active site, parent depletion, stoichiometric balance, ratio
source, controlled response components/views/keys, gel components/views/keys). Every `*_refs` field must be in scope
(`source` namespace except question context). `prepare_assignment`: with private yield binding, the task key
(`A105:verified_source_leads | source_answer:<kind> | experiments | assembly`) must have a declaration; its
`credit_unit` and `yield_settings` are written into the task (a supplied different value is refused); the proposed
annotation must equal the parent's.

## Children it may commission

| child role | folder | what it sends | what it takes back |
|---|---|---|---|
| `literature_strategy` | `evidence_search_strategy_improvement` | `to_child(parent, assignment)` = deep copy (scientific request unchanged); `prepare_request`: scope validated, expanded child return schema (required sources exactly once), initial report validated, role permitted, `binding.prepare_assignment` of the child (strategy_assignment_v1) | `receive_evidence_search_strategy_improvement`: when `rate_population`, every population namespace's cells in the admitted form are `receive_cells`-ed into this episode's repositories; returns current sheet refs + cell record refs for every population family (window, comparison, summary precision, endpoint, coupling, validation, recovery, observation, grid, replicate, ion, channel, compiled, assay grading, A105 aggregation, partition, completion time, active site, parent depletion, stoichiometric balance, controlled response, gel). `receive_report` adds receipts, progress provider and native timing receipts. |

## Decision state and what it shows the model

Common decision context (as head: goal, scope, working_state, visible refs, current_credit, evidence vector,
investigation_progress, credit_binding, time_accounting, pending_work, last outcome/feedback, visual_evidence,
report deliveries, controller, tools, knowledge, job options, report facts/form/update), the annotation context, native
timing, `_completed_work_axis_results` (a101..a104 sheets, target_sheets, tool_attachments, source_contributions) and
this binding's `decision_context`:
- `literature_assignment`, `literature_source_custody` (version, artifact/text/stdout/stderr refs, parents),
  `own_literature_outcomes` (page of own acquisition/read outcomes, `outcome_page_size` default 8),
  `literature_history_meaning` ("Source delivery does not establish understanding, absence or resolved science.");
- with assay grading: `literature_examined_source_inputs`; with rate population:
  `literature_experimental_work {literature_experimental_task_v1, source_experimental_evidence, A105}`, rate source /
  domain / meaning displays (possessed cells + meaning records), received-fact display, endpoint / summary precision /
  comparison / window receipt bindings, `literature_owned_population_sources`, last failed population attempt;
- ratio-source return meanings, controlled-response and gel return bindings/records when enabled;
- `current_report_facts` (`literature_completed_work`, `literature_current_scoring_sheets`) and `literature_goal_plan`.
`initial_decision_context` (`reference_evidence_parent`, source custody, child population operations) applies only when
this binding stands as a root `annotation` reference-source investigation (`reference_parent_sources`).
`call` adds resource/shared/launch contexts, child options, completed_action_reports (`decision_presentation`),
execution expectations captured under `'literature'`, resource and native estimates, contract-information profile — but
no `waiting_support`. Model dispatch goes through `decision_completion()`, which routes the original provider to its
presentation-aware completion with this binding's `render_literature_experimental_prompt`.

## Tools it offers

`catalog`: from the scoped real catalog only `_ACCESS_TOOLS` (state.query, source.read/locate, source.sequence.scan/
references, source.experimental.records, image.view, source.archive.members/extract, source.xlsx.sheets/rows,
source.pdf.info/text/page, execution.estimate restricted to xlsx branches) and `_ACQUISITION_TOOLS`
(public.literature.search/read/sequence_identity, public.ncbi.search restricted to pubmed, public.pmc.versions/files/
asset, experimental database operations), plus — with `rate_population` — the A105 population operations in
`_CATALOG_ORDER` (35 `literature.*.populate` / `literature.a105.aggregate` operations, gated by flags; with contract
information they carry `CONTRACT_ARGUMENT_TRANSPORT`). All inputs are wrapped by `source_location_inputs`.
`_tool_arguments` keeps reads and population source operands inside an assigned page source and authorises source /
record access in the endpoint, summary-precision, comparison and window repositories. Population operations run
against their private repositories with text-witness materialisation; failures return typed invalid outcomes.
Common actions: tool, reason, child, redeliver_report (`supports_wait = False`).

`grading/experimental_interpretation.py` (the A105 required-grading coupling): when assay grading is enabled, the
reasoning action schema is the required-grading action schema over the assay-grading population schema, and
`execute_reasoning` runs the purpose-specific grader inside the reasoning action (interpretation + subscoring sheet in
one operation); for a `verified_source_leads` task the action carries `source_lead`, whose witness is read through the
normal source authorization and validated (`validate_lead`: same question/source, rationale, received inputs, acquired
non-search source, subject anchor inside the witness). `grading/assay_subscoring.py` builds the assay-grading
repository; `scoring/experimental_main_sheet.py` builds the A105 aggregation repository over grading cells.

## How its credit is counted

`LiteratureTaskCredit` (`literature_local_task_v1`): **credit = `credit_unit` × number of answers**, finite check
only, unbounded. Answers by task: relevant lead dispositions (latest per canonical source from own reasoning results and
admitted child forms); a screening answer when own `no_applicable_evidence` reasoning spans cover every requested span;
one current retained, target-eligible assessment anchored in a named source; a quantity sheet with all requested
components populated (or reported-spread/zero unavailable reasons); one graded sheet per wanted experiment matched to a
current assessment; an aggregation sheet whose metrics come from current grading sheets. The commission identity,
scope, and target-annotation link are re-checked. Policy record: unit text per kind, `revision_credit False`,
`activity_credit False`, `annotation_support separate`; result carries `task_status` and `source_contributions`.

## Continuation

`yield_estimator.LiteratureYield`: declaration per task key `{credit_unit, kind, cutoff, uncertainty_alpha}`;
`verified_source_leads` must be `accumulation`; all others `remaining_commissioned_credit`, which is a finite target:
maximum = `credit_unit × len(experiments)` for `a105_experiments`, else `credit_unit`; the forecast is the observed
next-action yield capped by the remaining commissioned credit and exactly zero when all requested answers are earned.
Maps onto **accumulation** and **completion with a target** (target = maximum commissioned credit). The cap is on the
forecast, not on credit. Old route returned `None` without a private yield binding — must become an explicit error.

## What it reports to its parent

`fact_sources`: rate fact sources (when `rate_population`; each with meaning text and report schema),
`literature_screening_answers`, `literature_source_lead_dispositions`. `facts`: screening answers / lead dispositions
for their tasks, population cells for each requested family from received sheets, `current_report_facts`.
`validate_report`: assignment + form + `validate_received_report` (answers equal saved work; each population family's
rows equal the requested subset of possessed sheets; controlled-response/gel keys requested; A105 worksheet links).
Only this episode (not its strategy/search descendants) also has `received_form_references` — used when a
non-literature receiver (the A105 head) admits a literature form, to receive cells and return their record refs.
`create_binding_tree` (episode.py, this episode only) builds this binding plus the six literature descendants from one
shared configuration.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | — | — |
| `binding_record.py` | 43 | record of page size, yield bindings and every population flag/descriptor/origin | — |
| `configuration.py` | 119 | population flags (most require `rate_population`), evidence origins, descriptors, contract profile, reference parent sources, yield validation; `reference_evidence` constructor | `a105.composition_information:CONTRACT_INFORMATION_PROFILE`; `a105.library` (controlled-response, gel storage) |
| `credit.py` | 289 | literature task credit (above); lead/screening schemas and readers | `self.services.{scientific_credit, scientific_credit_for, proposed_annotation_for, annotation_task_required}`; `services.workflow`→`workflow.scientific_projector_for_context/projector_receipt_arguments/projection_view`; tables `runtime_actions×4`, `runtime_report_attempts×2`; `a105.communication`, `a105.domain`, `a105.scientific_findings`, `a105.finding_validity`, 5 `a105.library` modules |
| `decision_presentation.py` | 18 | completed-action reports; root-shaped yield table | `self.workflow.controller_binding`; runtime `{_category_yield_parameters, Mapping, yield_table}`; `a105.episode_work_report` |
| `episode.py` | 99 | composition, role, child maps, hook ownership, `create_binding_tree` | `a105.library.literature_experimental_prompt` |
| `from_child_evidence_search_strategy_improvement.py` | 123 | receive strategy child's cells/refs (above) | `self.services.workflow.store`; `workflow.{receipts×3, is_job_source×2, store×8, run_id×4, binding_context×2, progress_provider×2, specialist, native_timing_information, job_episodes×2}`; table `runtime_report_attempts×2`; runtime `_references_in, json, _json`; `EpisodeReturnRecords`; `WorkflowError`; 16 `a105.library` modules |
| `from_parent.py` | 162 | assignment schema and preparation (above) | `self.services.proposed_annotation_for`; 38 `a105.library` modules (component constants) |
| `goal.py` | 131 | task schema, task key, commission checks, goal text, planning context | `a105.communication`, `a105.domain`, 2 `a105.library` modules |
| `grading/__init__.py` | 0 | — | — |
| `grading/assay_subscoring.py` | 17 | assay-grading repository (subscoring sheet) | `self.services.workflow.{store, run_id}`; `a105.library.literature_assay_grading_storage` |
| `grading/experimental_interpretation.py` | 60 | required grading in the reasoning action; source leads | `self.services.workflow.store`; `a105.literature_contract_error`; ~25 `a105.runtime` names (imported, mostly unused), `ReportBoundaryError`, `WorkflowError`, `ContractInformationError`, `ActionFailure` |
| `internal_summary.py` | 311 | decision context displays (above) | `self.services.{own_outcomes, read_record×5}`; `self.services.workflow.store`; `workflow.{store, run_id}` (raw SQL over population tables); table `runtime_actions×2`; 11 `a105.library` modules |
| `received_evidence.py` | 67 | received cells/facts and tokens for non-literature receivers | `method_loop.durable:content_digest` |
| `scientific_records.py` | 357 | ~40 lazy population repositories and `_population_routes` | `self.services.workflow.{store×34, run_id×34}`; 40 `a105.library` modules |
| `scoring/__init__.py` | 0 | — | — |
| `scoring/experimental_main_sheet.py` | 12 | A105 aggregation repository | `self.services.workflow.{store, run_id}`; `a105.library.literature_a105_aggregation_storage` |
| `source_contracts.py` | 42 | ROLES, `_CHILDREN` chain, tool lists, role instruction texts, population catalogue order | `a105.communication`, `communication:ReportBoundaryError`, `a105.composition_information`, `a105.domain`, `a105.episode_bindings:reference_in_context`, `a105.experimental_database_acquisition`, 2 `a105.library` modules |
| `source_operations.py` | 77 | source-bound tool argument checks; text-witness materialisation | `self.services.read_record×4`; `getattr(self.services,'workflow')`; 2 `a105.library` modules |
| `source_references.py` | 31 | scope/record reads; source ancestry | `self.services.{reference_in_scope, read_record}` |
| `task.py` | 311 | catalog/execute (lines 1-72) + decision loop (73-311) | as head `task.py` plus inline decision inputs: `self.workflow.{working_state, local_outcome_preview, source_credit_binding, receipt_projection, delivery_status, catalog, knowledge, job_episode_options, extra_report_sources, is_scientific_source, annotation_context, tools}`; `self.services.{tool_catalog, execute_tool}`; tables `runtime_actions/model_calls/episodes/forms` |
| `task_decision.py` | 352 | model call + exchange protocol; `decision_completion` presentation route | as head `task_decision.py` minus `experimental_activity_evidence_binding`/`waiting_support`; plus `a105.providers:_ORIGINAL_*` and `providers:_ORIGINAL_*` internals |
| `task_instructions.py` | 28 | instruction composition (no wait text) | `runtime_prompt.*`; `source.workflow.{specialist, binding_context, permits_common_action×3, knowledge, launch_instructions, native_event_information, decision_protocol, is_job_source}` |
| `task_state.py` | 108 | identical to head `task_state.py` | identical names |
| `to_child_evidence_search_strategy_improvement.py` | 35 | strategy child request | `workflow.{store, expanded_contract_form, episode_bindings×3, binding_context×4, child_initial_report_input, specialist, available_child_roles, annotation_child_roles, services.capabilities, launch_instructions, run_id}`; runtime `{ContractError, parse_json_object, validate_form, interpretation_schema}` |
| `to_parent.py` | 414 | fact sources, facts, received-report validation, `received_form_references` | `self.services.{read_record×4, record_selection×4}`; `self.services.workflow.store×5`; `ReportBoundaryError`; `reference_in_context`; 42 `a105.library` modules |
| `waiting.py` | 8 | `supports_wait = False` | — |
| `yield_estimator.py` | 109 | yield bindings, remaining-commissioned-credit forecast | `a105.numerical:{YieldController, YieldParameters, YieldEstimate, NumericBand, STATUS_NORMAL, estimate_score_yield}` |

Full counts: `runs/carry_over/calls/a105_01.tsv`.

## Differences from similar episodes

- vs the A105 head: literature-task credit (count × unit) instead of the whole-axis finding projector; two yield kinds
  (accumulation / remaining commissioned credit) per six task keys; no wait; source/acquisition tool catalogue plus A105
  population operations instead of an A/P tool selection; the presentation-aware `decision_completion`.
- vs its descendants `evidence_search_strategy_improvement` and `source_relevance_assessment`: the files are copies
  with only these differences — role (`literature` / `literature_strategy` / `literature_search`), binding id/path,
  assignment version and ref field (`literature_assignment_v1 source_refs` / `strategy_assignment_v1 prior_search_refs`
  / `search_assignment_v1 search_result_refs`), role instruction text, child role (`literature_strategy` /
  `literature_search` / `literature_page`), `entry_roles` (only this one is an entry), `create_binding_tree` and
  `to_parent.received_form_references` (only this one), `context_hook_applies` (True for non-family roles only here).
  Credit, yield, configuration, catalogue, grading and scoring code are identical copies.
- `goal.py`, `credit.py` and `yield_estimator.py` each duplicate the constants block (`VERSION`, `SCREENING`, `LEADS`,
  `YIELD_TASKS`) and then re-import them from `goal.py`.
