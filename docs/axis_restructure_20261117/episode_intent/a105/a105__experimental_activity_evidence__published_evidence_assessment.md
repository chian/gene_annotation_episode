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

## Carried over

One row per old function, class and method of the episode (`runs/carry_over/functions/a105__experimental_activity_evidence__published_evidence_assessment.tsv`, 200 rows). New files are in `gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/published_evidence_assessment/`. Every library call is to an already existing `episode_support/` function, called as the final form requires; those still in the old Store form raise `RuntimeError('library_not_carried:...')` at the point of the call (listed in `carry_over_blocked/a105__experimental_activity_evidence__published_evidence_assessment.md`).

| old file | kind | name | classification | new place or reason |
|---|---|---|---|---|
| binding_record.py | class | LiteratureBindingRecord | machinery | the binding's own as_record() and VERSION record: deleted (README 3, configuration.py/binding_record.py row); the system journals settings and declarations |
| binding_record.py | method | LiteratureBindingRecord.as_record | machinery | the binding's own as_record() and VERSION record: deleted (README 3, configuration.py/binding_record.py row); the system journals settings and declarations |
| configuration.py | class | LiteratureConfiguration | episode function | settings: the run's `continuation` entry (`ctx.settings`, `settings`); fixed values are constants of the file that uses them (messages/internal_summary.py OUTCOME_PAGE_SIZE, task.py FLAGS) |
| configuration.py | method | LiteratureConfiguration.__init__ | episode function | settings (`rate_population`, population flags, `knowledge_library_directory`, `tool_registry`, yield `cost`/`parameters`) read as `ctx.settings` in task.py population_entries/offered/decide and as `settings` in yield_estimator.py; outcome_page_size is messages/internal_summary.py OUTCOME_PAGE_SIZE; the `validate_yield_bindings` check is machinery (controller's own checks) |
| configuration.py | method | LiteratureConfiguration.reference_evidence | episode function | unplaced: the root-only reference-source entry constructor (caller-assigned `reference_parent_sources`); the run's caller sets `settings['rate_population']`; not this episode's |
| credit.py | function | _resolve | episode function | task.py resolve (private copy); library candidate |
| credit.py | function | lead_schema | episode function | task.py lead_schema (private copy); library candidate |
| credit.py | function | lead_return_schema | episode function | messages/final_to_parent.py RETURN_FORM field literature_source_lead_dispositions (the old return-schema node is a form field) |
| credit.py | function | validate_lead | episode function | task.py validate_lead (private copy, on custody `store.require`, `get_artifact`); library candidate |
| credit.py | function | lead_dispositions | episode function | credit.py lead_dispositions (over the summary's source_leads; the old runtime_actions / runtime_report_attempts reads are the unit outcomes in view.outcomes); library candidate |
| credit.py | function | screening_schema | episode function | messages/final_to_parent.py RETURN_FORM field literature_screening_answers |
| credit.py | function | _current_assessments | episode function | credit.py current_assessments (library FindingValidity/target_eligible called as written; BLOCKED-ON-STORE-ACCESS); library candidate |
| credit.py | function | screening_answers | episode function | credit.py screening_answers (over the summary's no_applicable_evidence spans built in messages/internal_summary.py); library candidate |
| credit.py | class | LiteratureTaskCredit | episode function | credit.py credit (+ credit_binding, answers, assessment_answers) |
| credit.py | method | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding (the credit definition shown to the model; README 3d) |
| credit.py | method | LiteratureTaskCredit.__call__ | episode function | credit.py credit: credit_unit times the number of answers, unchanged and unbounded; the commission-identity comparison (run/episode/scope/assignment match) is machinery; the target-annotation test (`store._record_roots`, `reference_subset`) is unplaced: BLOCKED-ON-STORE-ACCESS |
| credit.py | method | LiteratureTaskCredit._answers | episode function | credit.py answers |
| credit.py | function | measured_answers | episode function | credit.py measured_answers (library repository call as written, library not carried); library candidate |
| credit.py | function | graded_experiment_answers | episode function | credit.py graded_experiment_answers (library repository calls as written, library not carried); library candidate |
| credit.py | function | assembled_answers | episode function | credit.py assembled_answers (library repository calls as written, library not carried); library candidate |
| credit.py | class | LiteratureCredit | machinery | credit-provider mix-in (credit_kind/credit_view/credit_projector over services.scientific_credit): replaced by credit.credit(summary, records) |
| credit.py | method | LiteratureCredit._scientific_credit_invocation | machinery | services.workflow.projection_view / projector_receipt_arguments / scientific_projector_for_context: provider and receipts bookkeeping |
| credit.py | method | LiteratureCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | LiteratureCredit.credit_view | machinery | services.scientific_credit view: replaced by credit.credit |
| credit.py | method | LiteratureCredit.credit_projector | episode function | credit.py credit (the projector is the module's functions over the summary and records) |
| decision_presentation.py | function | prepare_completed_work | episode function | unplaced: completed_action_reports (`root.a105.episode_work_report`) has no module in the library; the completed-action reports are not shown |
| decision_presentation.py | function | decision_yield_table | episode function | messages/internal_summary.py `action_yields` (library records/progress_views.yield_table over view.controller_state), shown by task.py decide |
| episode.py | class | LiteratureEpisode | episode function | episode.py PublishedEvidenceAssessment (decision_source_type / decision_prompt_renderer / binding_path: member assignments; binding_path in goal.py) |
| episode.py | method | LiteratureEpisode._enabled | episode function | task.py population_entries (`assay_grading_population` setting, default true) |
| episode.py | method | LiteratureEpisode.contract_information_configuration | episode function | unplaced: contract-information profile freezing is not carried (README section 5 item 16) |
| episode.py | method | LiteratureEpisode.contract_information_profile | episode function | unplaced: contract-information profile freezing is not carried (README section 5 item 16) |
| episode.py | method | LiteratureEpisode._role | machinery | role check: each role is its own episode now |
| episode.py | method | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS |
| episode.py | method | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | method | LiteratureEpisode.child_assignment_schema | machinery | the child's assignment schema is the child's own ASSIGNMENT_FORM (a wrong commission fails) |
| episode.py | method | LiteratureEpisode.context_hook_applies | machinery | hook-era context hook: deleted |
| episode.py | method | LiteratureEpisode.prepare_child_request | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | method | LiteratureEpisode.receive_child_result | episode function | messages/read_from_child.py read_from_child |
| episode.py | method | LiteratureEpisode.child_request_preparer | machinery | binding lookup (README 3b C1): deleted |
| episode.py | method | LiteratureEpisode.child_report_receiver | machinery | binding lookup (README 3b C1): deleted |
| episode.py | function | create_binding_tree | machinery | home factory / binding tree (README 3b C1): deleted; no table of bindings |
| from_child_evidence_search_strategy_improvement.py | class | FromEvidenceSearchStrategyImprovement | episode function | messages/read_from_child.py read_from_child |
| from_child_evidence_search_strategy_improvement.py | method | FromEvidenceSearchStrategyImprovement.receive_evidence_search_strategy_improvement | episode function | messages/read_from_child.py read_from_child (reads the child's admitted result; the `receive_cells` writes into this episode's repositories are not carried: README section 5 item 4; the child returns its sheets by reference) |
| from_child_evidence_search_strategy_improvement.py | function | receive_report | machinery | EpisodeReturnRecords / progress_provider.receive_form / runtime_report_attempts / receipts.receive / native timing records: system custody (README 3b R1, R3, R5) |
| from_parent.py | class | LiteratureAssignment | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) |
| from_parent.py | method | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per old property; the `*_population` flag branches are the optional `requested_*` fields, all declared) |
| from_parent.py | method | LiteratureAssignment._validate_page | machinery | Store check of a page assignment (rule 1; not this episode's assignment, which names no page) |
| from_parent.py | method | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (schema checks); the reference checks against the Store (`_require`, source namespace) are machinery (a wrong commission fails) |
| from_parent.py | method | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent; the fill-in of credit_unit / yield_settings from the parent's yield binding and the proposed-annotation comparison with the parent's are not carried (credit_unit is a task field; settings carry the rest) |
| goal.py | function | _yield_kind | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion otherwise) |
| goal.py | function | _task_key | episode function | messages/read_from_parent.py task_key; library candidate |
| goal.py | function | task_schema | episode function | messages/read_from_parent.py task_schema (private copy); library candidate |
| goal.py | function | _return_sources | machinery | check of the commissioned task against the parent's report contract: the contract is the child's RETURN_FORM and the parent's selection |
| goal.py | function | _return_components | machinery | check of the commissioned task against the parent's report contract (as above) |
| goal.py | function | commissioned_task | episode function | messages/read_from_parent.py read_from_parent (schema, finite credit unit, spans, validate_commission); the report-contract and request-identity checks are machinery |
| goal.py | function | continuation_task | episode function | messages/read_from_parent.py task_key (carried in the parent input as task_key) |
| goal.py | function | task_schema_variants | episode function | messages/read_from_parent.py task_schema (the measurement, experiments and assembly variants); library candidate |
| goal.py | function | required_source | machinery | names the report-contract fact source of a task kind for the contract check: the contract check is deleted |
| goal.py | function | validate_commission | episode function | messages/read_from_parent.py validate_commission; library candidate |
| goal.py | class | LiteratureGoal | episode function | goal.py GOAL / UNIT / RESULT; messages/internal_summary.py literature_goal_plan |
| goal.py | method | LiteratureGoal.instructions | episode function | goal.py GOAL (the model-facing text is task.py instructions) |
| goal.py | method | LiteratureGoal.planning_context | episode function | messages/internal_summary.py literature_goal_plan (planning_question is GOAL, the old instructions(context)) |
| grading/assay_subscoring.py | class | AssaySubscoring | episode function | task.py grading_execute (the assay-grading repository the required grading saves its sheets in) |
| grading/assay_subscoring.py | method | AssaySubscoring._required_grading_repository | episode function | task.py grading_execute (the repository is used because `assay_grading_population` defaults to true) |
| grading/assay_subscoring.py | method | AssaySubscoring._assay_grading_repository | episode function | task.py grading_execute: LiteratureAssayGradingRepository(ctx.store, ctx.run_id, read_cells=...) (library not carried) |
| grading/experimental_interpretation.py | class | ExperimentalInterpretation | episode function | task.py reason tool, reason_schema, empty_commit |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.reasoning_action_schema | episode function | task.py reason_schema (library required_grading action_schema; source_lead for a leads commission) |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.reasoning_has_task_content | episode function | task.py empty_commit, tested in action (Rejected 'empty_reasoning_commit') |
| grading/experimental_interpretation.py | method | ExperimentalInterpretation.execute_reasoning | episode function | task.py reason (coupled commit + grading sheet + typed investigation_finding in one unit; with a source_lead in one transaction) |
| internal_summary.py | class | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | method | LiteratureSummary.initial_decision_context | episode function | unplaced: root-only `reference_evidence_parent` context (applies only when the binding stands as a root annotation reference-source investigation) |
| internal_summary.py | method | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (literature_assignment, literature_source_custody, own_literature_outcomes, literature_history_meaning, literature_goal_plan, report facts) and task.py decide (context handed to the model); literature_examined_source_inputs and completed work: unplaced (no library module) |
| internal_summary.py | method | LiteratureSummary._owned_population_task_sources | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._population_task_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._concentration_window_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._measurement_comparison_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._summary_precision_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._endpoint_signal_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._controlled_response_bindings | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._gel_bindings | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._gel_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._received_fact_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._native_rate_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._native_rate_domain_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| internal_summary.py | method | LiteratureSummary._native_rate_meaning_display_context | episode function | unplaced: population display context over the family repositories (old Store form, needs the run's flags); not shown to the model |
| received_evidence.py | class | LiteratureReceivedEvidence | episode function | unplaced: receive side of the commissioning head (reached only for roles outside ROLES: received_report_sources / facts / tokens of a head receiving this episode's cells); belongs to the A105 head's read_from_child, not this episode's |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_sources | episode function | unplaced: receive side of the commissioning head (reached only for roles outside ROLES: received_report_sources / facts / tokens of a head receiving this episode's cells); belongs to the A105 head's read_from_child, not this episode's |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_facts | episode function | unplaced: receive side of the commissioning head (reached only for roles outside ROLES: received_report_sources / facts / tokens of a head receiving this episode's cells); belongs to the A105 head's read_from_child, not this episode's |
| received_evidence.py | method | LiteratureReceivedEvidence._complete_requested_received_arrays | episode function | unplaced: receive side of the commissioning head (reached only for roles outside ROLES: received_report_sources / facts / tokens of a head receiving this episode's cells); belongs to the A105 head's read_from_child, not this episode's |
| received_evidence.py | method | LiteratureReceivedEvidence.received_evidence_tokens | episode function | unplaced: receive side of the commissioning head (reached only for roles outside ROLES: received_report_sources / facts / tokens of a head receiving this episode's cells); belongs to the A105 head's read_from_child, not this episode's |
| scientific_records.py | class | LiteratureScientificRecords | episode function | messages/internal_summary.py FAMILIES and the library repositories (library_repository in credit.py / task.py) |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_calibration_recovery_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_observation_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_rate_replicate_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_quantity_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_assay_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_amount_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_optical_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_kinetic_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_interaction_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_ratio_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_binding_model_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_transport_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_figure_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_ratio_source_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_controlled_response_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords.literature_gel_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._endpoint_signal_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._concentration_window_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._measurement_comparison_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._summary_precision_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._rate_grid_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_v2_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._compiled_assay_v3_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._product_coupling_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._measurement_validation_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._ion_discrimination_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._channel_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._completion_time_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._active_site_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._assay_grading_source_cells | episode function | task.py assay_grading_source_cells (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._parent_depletion_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._stoichiometric_balance_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._product_partition_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._binding_interaction_model_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._kinetic_model_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._ratio_source_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._controlled_response_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._gel_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._native_rate_meaning_repository | episode function | already in library: episode_support/literature/storage/experimental_activity_evidence/literature_*_storage.py <Repository>; called through credit.py / task.py library_repository (library not carried) |
| scientific_records.py | method | LiteratureScientificRecords._population_routes | episode function | messages/internal_summary.py FAMILIES (fact source -> requested field, repository family) |
| scoring/experimental_main_sheet.py | class | ExperimentalMainSheet | episode function | credit.py assembled_answers / task.py: LiteratureA105AggregationRepository(ctx.store, ctx.run_id, read_cells=...) (library not carried) |
| scoring/experimental_main_sheet.py | method | ExperimentalMainSheet._a105_aggregation_repository | episode function | credit.py assembled_answers / task.py: LiteratureA105AggregationRepository(ctx.store, ctx.run_id, read_cells=...) (library not carried) |
| source_contracts.py | function | _required_grading_logic | episode function | task.py imports the library's required_grading action_schema / execute directly (already in library: episode_support/literature/grading/.../literature_required_grading.py) |
| source_contracts.py | function | _population_catalog | episode function | task.py population_entries (already in library: episode_support/literature/forms/.../literature_population_catalog.py population_catalog) |
| source_operations.py | class | LiteratureSourceOperations | episode function | task.py admitted / authorize_source_read / run_access_tool / materialize_text_arguments |
| source_operations.py | method | LiteratureSourceOperations._tool_arguments | episode function | task.py admitted and authorize_source_read (population source authorization, BLOCKED-ON-STORE-ACCESS); the page-containment branch is unplaced (a literature assignment names no page) |
| source_operations.py | method | LiteratureSourceOperations._materialize_text_arguments | episode function | task.py materialize_text_arguments |
| source_references.py | class | LiteratureReferences | machinery | reference lookup through services.reference_in_scope / read_record: custody (`records.holds`, `require`) |
| source_references.py | method | LiteratureReferences._require | machinery | services.reference_in_scope / read_record: custody (`records.holds`, `require`) |
| source_references.py | method | LiteratureReferences._artifact | episode function | unplaced: no caller in the old episode files |
| source_references.py | method | LiteratureReferences._within_source | episode function | unplaced: its only callers are the page branches (not reached by a literature assignment) |
| task.py | class | LiteratureOperations | episode function | task.py TOOLS, catalog, offered |
| task.py | method | LiteratureOperations.permitted_common_actions | machinery | action schema of common actions: task.py selection_schema over the episode's own TOOLS and CHILD_SLOTS |
| task.py | method | LiteratureOperations.catalog | episode function | task.py catalog / offered / definitions / population_entries |
| task.py | method | LiteratureOperations.execute | episode function | task.py tools (run_access_tool, run_population, reason, report) |
| task.py | class | LiteratureTask | episode function | task.py decide / action / TOOLS |
| task.py | method | LiteratureTask.next | episode function | task.py decide (the loop, restore, replay, source_failed and delivery handling are the system's) |
| task.py | method | LiteratureTask.apply_response | episode function | task.py action (Rejected with rejection_feedback) |
| task.py | method | LiteratureTask.execute | episode function | task.py tools and ChildCall (validate_report call: messages/final_to_parent.py validate_report; no wait branch) |
| task.py | method | LiteratureTask.finish | machinery | finish(record) / report saving: the system's result (final_to_parent) |
| task_decision.py | class | LiteratureTaskDecision | episode function | task.py decide / action |
| task_decision.py | method | LiteratureTaskDecision.call | episode function | task.py decide (context, tools, instructions, yield table, time accounting; resource/shared/launch contexts and native estimates are not carried) |
| task_decision.py | method | LiteratureTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | method | LiteratureTaskDecision.decision_completion | machinery | model call recording / presentation-aware provider routing: decide returns a ModelRequest |
| task_decision.py | method | LiteratureTaskDecision.conversation_key | machinery | conversation state (README 3a): every ModelRequest carries the full context |
| task_decision.py | method | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange context (README 3a): a lookup is a tool |
| task_decision.py | method | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop (README 3a): not carried; a lookup is a tool |
| task_decision.py | method | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop (README 3a): not carried; a lookup is a tool |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop (README 3a): not carried; a lookup is a tool |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop (README 3a): not carried; a lookup is a tool |
| task_decision.py | method | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop (README 3a): not carried; a lookup is a tool |
| task_instructions.py | function | instructions | episode function | task.py instructions |
| task_state.py | class | LiteratureTaskState | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.__init__ | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.bind_execution_context | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.suspension_changed | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.record_execution_failure | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.restore_checkpoint | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.restore | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.record_effect | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| task_state.py | method | LiteratureTaskState.checkpoint | machinery | checkpoint / restore / record_effect / suspension bookkeeping (README 3e) |
| to_child_evidence_search_strategy_improvement.py | function | to_child | episode function | messages/msg_to_child.py msg_to_child (the assignment travels unchanged in substance) |
| to_child_evidence_search_strategy_improvement.py | function | prepare_request | machinery | expanded_contract_form / child_initial_report_input / role availability / binding.prepare_assignment checks of a commission (rule 1: a wrong commission fails); the assignment is built in messages/msg_to_child.py |
| to_parent.py | class | LiteratureReport | episode function | messages/final_to_parent.py (RETURN_FORM, final_to_parent) |
| to_parent.py | method | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (one field per fact source) |
| to_parent.py | method | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent (+ finding_of) |
| to_parent.py | method | LiteratureReport.current_report_facts | episode function | messages/internal_summary.py report_facts (library not carried: completed work has no module) |
| to_parent.py | method | LiteratureReport._rate_fact_sources | episode function | messages/final_to_parent.py RETURN_FORM fields over messages/internal_summary.py FAMILIES |
| to_parent.py | method | LiteratureReport._rate_facts | episode function | messages/internal_summary.py family_cells (library repositories, library not carried) |
| to_parent.py | method | LiteratureReport.validate_received_report | episode function | messages/final_to_parent.py validate_report (selected families were requested, assessed finding has its sheet, references held) |
| to_parent.py | method | LiteratureReport.resolve | machinery | reference resolver of the report form (README 3b D2): the system admits the result exactly |
| to_parent.py | method | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report, called before the result is returned (validate_form is not built for A105: not called) |
| to_parent.py | method | LiteratureReport.received_form_references | machinery | receipt ledger of received references (README 3b R3): system custody; the `receive_cells` writes into the repositories are not carried (README section 5 item 4) |
| waiting.py | class | LiteratureWaiting | machinery | wait/suspension machinery (supports_wait False): deleted |
| waiting.py | method | LiteratureWaiting.supports_wait | machinery | wait/suspension machinery (supports_wait False): deleted |
| yield_estimator.py | function | validate_yield_bindings | machinery | construction-time check of declared yield bindings (README 3d): the controllers' own checks and the run's settings |
| yield_estimator.py | class | _RemainingCommissionedCredit | machinery | episode-local estimator (README 7b): replaced by CompletionYieldController with target from parent_input |
| yield_estimator.py | method | _RemainingCommissionedCredit.__call__ | machinery | episode-local estimator (README 7b): replaced by CompletionYieldController with target from parent_input |
| yield_estimator.py | method | _RemainingCommissionedCredit.as_record | machinery | episode-local estimator (README 7b): replaced by CompletionYieldController with target from parent_input |
| yield_estimator.py | function | _private_yield_controller | episode function | yield_estimator.py yield_controller (task kind -> accumulation or completion; target = credit_unit times experiments) |
| yield_estimator.py | class | _FiniteLiteratureYieldController | machinery | episode-local controller class (README 7b): replaced by CompletionYieldController |
| yield_estimator.py | method | _FiniteLiteratureYieldController.__init__ | machinery | episode-local controller class (README 7b): replaced by CompletionYieldController |
| yield_estimator.py | method | _FiniteLiteratureYieldController.transitioned | machinery | episode-local controller class (README 7b): replaced by CompletionYieldController |
| yield_estimator.py | class | LiteratureYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py task_key (in the parent input) |
| yield_estimator.py | method | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
