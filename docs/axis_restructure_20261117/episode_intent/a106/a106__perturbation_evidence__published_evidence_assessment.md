# a106 / perturbation_evidence / published_evidence_assessment

Source: this episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/<file>`),
including its own `grading/` and `scoring/`. `tests/` and the child folders are not covered here. The old binding
class is `LiteratureEpisode`, which mixes in the episode's own files plus `InterventionAssessment` and
`InterventionMainSheet`. Its decision source is `LiteratureTask`.

## Purpose (goal, in its own words)

Role `literature` (its only entry role). From `source_contracts._ROLE_INSTRUCTIONS['literature']`:

> Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches
> and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.

`goal.instructions` joins this text with `PERTURBATION_TASK` (`library.literature_perturbation_prompt`) and the A106
subscore `TASK` (`library.literature_a106_subscore`). Module docstring: “A106 intervention specialization of the
ordinary Episode loop … a reading selection is information for an investigation, never a script that this binding
executes.”

## Task and instructions

- `task_instructions.py` is the shared literature composer. It starts from the literature `INSTRUCTIONS`, applies the
  specialist instructions (appended, not replacing), and adds the reasoning commit requirement (reason is permitted),
  tool knowledge, launch instructions, repair guidance for a pending child delivery, wait and native-event guidance,
  and the decision-exchange history note.
- The commissioned task (`goal.task_schema`, version `literature_local_task_v1`, axis `A106`) is one of:
  - `verified_source_leads`;
  - `source_answer` / `assessment`, with `source_refs`;
  - `source_answer` / `screening`, with `examined` spans `{source_ref, artifact_ref, start, end}`.

  Each carries `credit_unit` (> 0, finite) and optional `yield_settings {kind, cutoff ≥ 0, uncertainty_alpha}`.
  The schema states: “A106 score computation is automatic work, not an episode-credit task.”
- `commissioned_task` checks the following:
  - the parent's `literature_task` and `proposed_annotation_ref` are present;
  - the request goal and report contract are present, and the assignment matches the request;
  - the return contract carries the typed source the task needs (`literature_source_lead_dispositions`,
    `changed_assessment_refs` or `literature_screening_answers`) and its components;
  - each screening span has `end > start`;
  - any assigned page stays inside its source and artifact.
- `planning_context` (shown as `literature_goal_plan`) = objective, proposed annotation, commissioned result, the
  progress definition (credit projector record) and the planning question (the instructions).
- `task_decision.decision_completion` routes the model call through the provider's `complete_with_presentation`
  with this binding's `decision_prompt_renderer = render_literature_experimental_prompt`, but only when the provider
  is the original model class.

## What it reads from its parent's assignment

- Parent: `perturbation_evidence` (`commissioning_parent`).
- `assignment_schema` = `{version: 'literature_assignment_v1', question_context_refs, source_refs}` plus:
  - `literature_task` (the task schema above) and `proposed_annotation_ref`. Both are required when the private
    yield binding is on, in which case `credit_unit` stops being required because it is filled from the binding;
  - one `requested_*_components` array (or view/selector array) for each population family: concentration window,
    measurement comparison, summary precision, rate grid, rate observation, calibration recovery, product coupling,
    measurement validation, rate replicate, rate, quantity, assay, ratio, binding, binding model, transport,
    perturbation, perturbation summary, endpoint signal, and so on. Gel components, views and keys appear only when
    gel population is on.
- `prepare_assignment`:
  - with the private yield binding, looks up `yield_bindings[A106:<kind>[:<answer_kind>]]`, rejects a supplied
    credit_unit or yield_settings that differ, and fills them in;
  - validates every `*_refs` reference in scope;
  - requires `proposed_annotation_ref` to equal the parent's (`services.proposed_annotation_for`).

## Children it may commission

| role | child episode | what it sends | what it takes back |
|---|---|---|---|
| `literature_strategy` | `published_evidence_assessment/evidence_search_strategy_improvement` | `to_child_evidence_search_strategy_improvement.prepare_request` sends: the scope (validated inside the parent's), the expanded child return schema plus report declaration, each required return source exactly once, the initial report (validated against the interpretation schema), the role checked as allowed, materialized launch instructions, and the assignment prepared by the child binding with operation key `run:episode:index` | `from_child_…receive_report` reads: the recorded admission references if already admitted, otherwise the child progress (specialist receiver or progress provider), the references in the admitted form plus the binding's received form references, native timing receipts (`runtime_report_attempts.timing_receipts`), and the receipts `child_form`/`report_redelivery` |
| `launch` | `published_evidence_assessment/execution_job_submission` | same steps; the binding path must equal `.../published_evidence_assessment/execution_job_submission`; for an HPC path the return form must contain `execution_handoff_refs` | same admission as above, after checking that the delivered role and binding path match |
| `results` | `published_evidence_assessment/execution_result_acquisition` | same steps; the binding path must equal `.../published_evidence_assessment/execution_result_acquisition` | same admission as above |

`launch` and `results` are offered only when an execution binding is configured
(`analysis_children` → `library.intervention_execution_lookup._execution`). The received intervention analysis rows
(`bvbrc_application_outcomes`) come back through `received_evidence.received_application_rows`.

## Decision state and what the model sees

- Generic decision state, the same as the literature siblings: goal, scope, working state, visible refs, current
  credit and evidence vector, credit binding, pending work, last outcome and feedback, visual evidence, delivery
  status, controller, tools, tool knowledge, job episode options, report facts, requested form, current report
  update. For scientific sources it also shows the proposed annotations and comparisons.
- The episode's own part (`internal_summary.decision_context`):
  - `literature_assignment` and `literature_source_custody` (version, artifact/text/stdout/stderr refs, parent
    source refs);
  - `own_literature_outcomes` (a page of `outcome_page_size` own acquisition/read outcomes) and
    `literature_history_meaning`;
  - `literature_examined_source_inputs` and `received_intervention_analysis_rows`;
  - `literature_experimental_work {aspect: source_experimental_evidence, evidence_axis: A106}`;
  - the return meanings, bindings and display contexts of the enabled families (ratio source, controlled response,
    gel, native rate, native rate domain and meaning, received facts, endpoint signal, summary precision,
    measurement comparison, concentration window), the population task context, and the current report facts;
  - `literature_goal_plan` when a literature task is present.
- `initial_decision_context` returns `reference_evidence_parent` (source custody plus child population operations)
  only for the root annotation role with `reference_parent_sources`. Otherwise it is empty.

## Tools it offers

- Common actions: `tool, reason, child, wait, redeliver_report`.
- Tools (`source_operations.catalog`), filtered from the services catalog:
  - access tools: `state.query`, `source.read`, `source.locate`, `source.sequence.scan`,
    `source.sequence.references`, `source.experimental.records`, `image.view`, `source.archive.members`,
    `source.archive.extract`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`,
    `source.pdf.page`, and `execution.estimate`, which is restricted to the xlsx branches;
  - acquisition tools: `public.literature.search`, `public.literature.read`,
    `public.literature.sequence_identity`, `public.ncbi.search` (database restricted to `pubmed`),
    `public.pmc.versions`, `public.pmc.files`, `public.pmc.asset`, and the experimental database tools;
  - `public.ncbi.entrez`, `public.ncbi.sequence`, `public.ncbi.geo`, `public.ncbi.sra.file`;
  - the enabled population tools (`literature.*.populate`, in `_CATALOG_ORDER`; with a contract information
    profile, each also carries the argument transport);
  - **only in this episode**: `literature.intervention_analysis.contract`, which builds the native adapter and
    requested schema for an existing BV-BRC TnSeq/RNASeq AppService results selector and acquires nothing.
- Reason: when the task is `verified_source_leads`, the reason schema gains `source_lead`. Executing it re-checks
  the witness read, commits the reasoning, then runs `credit.validate_lead`. A failure becomes an `invalid` outcome
  with category `source_lead`. Required grading is not bound here (`_required_grading_repository` → None).
- Populate tools route to their repositories (`scientific_records`), and errors become invalid outcomes.
  `state.query` records are authorized per repository.

## Credit

`credit.LiteratureTaskCredit` (kind `scientific`). Its policy record is `{kind: literature_local_task_v1, task,
credit_unit, unit, revision_credit: false, activity_credit: false, annotation_support: 'separate'}`.

- credit = `credit_unit × len(answers)`. It must be finite and is not bounded.
- Answers:
  - `verified_source_leads`: lead dispositions with `disposition == 'relevant'`, taken from the episode's own
    completed or partial `reason` results (`runtime_actions.result.literature_source_lead`) and from successfully
    admitted child forms whose contract declares the leads source (`runtime_report_attempts`). The latest lead per
    canonical source counts (`FindingIdentity.source`).
  - `assessment`: the first current retained, target-eligible assessment for the proposed annotation whose
    observation is anchored in one of the task's `source_refs`.
  - `screening`: one answer if the episode's own `no_applicable_evidence` reasoning covers every requested span.
- Before counting, the commission must match exactly: run, episode, scope, goal, purpose, schema and initial report.
  The annotation must be in scope and rooted in a scope subject.
- The view goes through `services.scientific_credit_for` / `scientific_credit` with the parent's assignment
  (`_scientific_credit_invocation`: projector, receipt arguments, projection view).

## Continuation

- `yield_estimator.LiteratureYield`. With no `private_yield_binding`, `yield_controller` returns None, and the old
  runner then used its default controller.
- The key is `A106:verified_source_leads`, `A106:source_answer:assessment` or `A106:source_answer:screening`. Each
  declaration `{credit_unit, kind, cutoff, uncertainty_alpha}` is validated at construction, and its kind must match
  the key.
- `verified_source_leads` → `YieldController(epoch, initial, cutoff, YieldParameters(uncertainty_alpha))`, which is
  **accumulation**.
- Source answers → `_FiniteLiteratureYieldController`. Its forecast is `estimate_score_yield`, with the band capped
  by `credit_unit − earned`, and exact zero once everything requested is earned. This is **completion with a
  target** (target = `credit_unit`).

## What it reports to its parent

- Fact sources: the rate and population cell sources (`_rate_fact_sources`), `literature_screening_answers` and
  `literature_source_lead_dispositions`.
- Facts at finish:
  - rate facts over the committed record refs;
  - `literature_completed_work`, and `literature_current_scoring_sheets` when any exist;
  - screening answers for a screening task, and lead dispositions for a lead task.
- `validate_report` re-validates the assignment, resolves references, and checks received evidence: lead and
  screening fields must equal the saved work (`literature_task_answer_differs_from_saved`), and cells must match
  receipts.
- Scoring: `automatic_score_judgments` and `complete_score_judgment` on the A106 subscore sheet repository.

## Differences from similar episodes

- `published_evidence_assessment`, `evidence_search_strategy_improvement` and `source_relevance_assessment` are
  near-copies. What differs: the role name (and so the role instruction and the assignment version/field), the
  binding path and commissioning parent, the children, and whether the role is an entry role. In addition:
  - only this episode has the execution children (`launch`/`results`), `create_binding_tree` and
    `create_execution_bindings`;
  - only this episode has the `literature.intervention_analysis.contract` tool and its `contract_catalog` /
    `prepare_analysis_contract`;
  - only this episode is an entry role (`entry_roles = ('literature',)`; the descendants have `()`).
- `from_parent.assignment_schema` indexes the role table with the episode's own role literal. Here it is
  `('literature_assignment_v1', 'source_refs')`.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `binding_record.py` | 26 | binding identity (`binding_id` = this episode's path) and saved configuration: outcome_page_size, enabled population flags, yield_bindings, reference_parent_sources, contract_information_profile, ratio/controlled-response/gel descriptors and evidence origins | none |
| `configuration.py` | 100 | constructor contract: services, outcome_page_size ≥1, eleven boolean population switches (ratio_source, controlled_response, gel, completion_time, product_partition, active_site, parent_depletion, stoichiometric_balance, compiled_assay, channel, ion_discrimination), evidence origin `reported_source`/`synthetic_fixture`, implementation descriptors that must match, contract information profile, explicit unique reference_parent_sources, private_yield_binding + yield_bindings validated by this episode's yield_estimator; `reference_evidence` entry point | `import a106.composition_information`, 2 imports of `a106.library.literature_*` |
| `credit.py` | 202 | task credit = `credit_unit × number of answers`: verified source leads with disposition `relevant` (own reason results + received child forms, latest per canonical source), or the first retained target-eligible assessment anchored in an assigned source, or a full-coverage `no_applicable_evidence` screening answer; `validate_lead` checks question, source, received inputs, anchored subject and exact witness quote; credit kind `scientific`; credit view through the services' scientific credit projector with the parent assignment | `estimate_score_yield`, `import a106.communication`, `import a106.domain` ×2, `import a106.finding_validity`, `import a106.numerical`, `import a106.scientific_findings`, `runtime_actions` ×4, `runtime_report_attempts` ×2, `services.annotation_task_required`, `services.proposed_annotation_for`, `services.scientific_credit`, `workflow.projection_view`, `workflow.projector_receipt_arguments`, `workflow.scientific_projector_for_context`, `YieldController`, `YieldEstimate`, `YieldParameters`, 2 imports of `a106.library.literature_*` |
| `decision_inputs.py` | 78 | generic runner input assembly (same as other literature episodes) | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `workflow.action_schema`, `workflow.available_child_roles`, `workflow.binding_context`, `workflow.delivery_resolution_inputs`, `workflow.episode_bindings`, `workflow.execution_expectations`, `workflow.launch_instructions` ×2, `workflow.native_estimation_context`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.resource_context`, `workflow.resource_estimator` ×4, `workflow.shared_information_context`, `workflow.waiting_support` |
| `decision_presentation.py` | 33 | generic presentation of completed work and yield table | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_work_report`, `import a106.library.live_runtime_functions`, `import a106.runtime` ×4, `workflow.controller_binding` |
| `decision_state.py` | 59 | generic decision state shown to the model, plus annotation context for scientific sources and specialist decision context | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_actions` ×2, `workflow.annotation_context`, `workflow.binding_context`, `workflow.catalog`, `workflow.controller_binding`, `workflow.delivery_status`, `workflow.extra_report_sources`, `workflow.is_scientific_source`, `workflow.job_episode_options`, `workflow.journal` ×3, `workflow.knowledge`, `workflow.local_outcome_preview`, `workflow.pending_work`, `workflow.receipt_projection`, `workflow.run_id`, `workflow.source_credit_binding`, `workflow.source_credit_view`, `workflow.specialist`, `workflow.store` ×3, `workflow.tools`, `workflow.working_state` |
| `episode.py` | 103 | assembles the binding: role `literature` (entry role), children `literature_strategy` + `launch`/`results` when execution is configured, prompt renderer, 19 source repositories; `create_binding_tree` builds this and its six literature descendants; `create_execution_bindings` builds its three execution children | 1 imports of `a106.library.literature_*` |
| `from_child_evidence_search_strategy_improvement.py` | 42 | admits the strategy child's typed form: recorded admission, progress provider, references from the form, timing receipts, receipts | `import a106.delivery_counterpart`, `import a106.episode_return_records`, `import a106.runtime`, `runtime_report_attempts` ×2, `workflow.binding_context` ×4, `workflow.episode_bindings`, `workflow.is_job_source` ×2, `workflow.job_episodes` ×2, `workflow.native_timing_information`, `workflow.progress_provider` ×4, `workflow.receipts` ×3, `workflow.run_id` ×6, `workflow.specialist`, `workflow.store` ×7 |
| `from_child_execution_job_submission.py` | 46 | admits the launch child's form after checking the delivered role/binding path | `import a106.delivery_counterpart` ×2, `import a106.episode_return_records`, `import a106.runtime`, `runtime_report_attempts` ×2, `workflow.binding_context` ×4, `workflow.episode_bindings` ×2, `workflow.is_job_source` ×2, `workflow.job_episodes` ×2, `workflow.native_timing_information`, `workflow.progress_provider` ×4, `workflow.receipts` ×3, `workflow.run_id` ×6, `workflow.specialist`, `workflow.store` ×7 |
| `from_child_execution_result_acquisition.py` | 46 | admits the results child's form after checking the delivered role/binding path | `import a106.delivery_counterpart` ×2, `import a106.episode_return_records`, `import a106.runtime`, `runtime_report_attempts` ×2, `workflow.binding_context` ×4, `workflow.episode_bindings` ×2, `workflow.is_job_source` ×2, `workflow.job_episodes` ×2, `workflow.native_timing_information`, `workflow.progress_provider` ×4, `workflow.receipts` ×3, `workflow.run_id` ×6, `workflow.specialist`, `workflow.store` ×7 |
| `from_parent.py` | 168 | parent assignment schema (version + question_context_refs + one ref list per role) plus `literature_task` (goal task schema) and `proposed_annotation_ref`, and the requested component arrays of every population family; prepare_assignment fills credit_unit and yield_settings from the private yield binding, validates refs in scope and checks the proposed annotation equals the parent's | 41 imports of `a106.library.literature_*` |
| `goal.py` | 104 | the commission: task schema (`verified_source_leads`, `source_answer:assessment` with source_refs, `source_answer:screening` with examined spans), `commissioned_task` checks it against the parent's return contract and assigned page; continuation key `A106:<kind>[:<answer_kind>]`; instructions = role instruction + perturbation task + A106 subscore task; planning context | `estimate_score_yield`, `import a106.communication`, `import a106.domain`, `import a106.numerical`, `YieldController`, `YieldEstimate`, `YieldParameters`, 2 imports of `a106.library.literature_*` |
| `grading/__init__.py` | 1 | package marker | none |
| `grading/intervention_assessment.py` | 33 | intervention grading: reads source cells for a grading sheet from received application rows, controlled-response, gel or any population route; `_required_grading_repository` returns None (no required grading binding here) | `workflow.run_id`, `workflow.store`, 1 imports of `a106.library.literature_*` |
| `__init__.py` | 0 | empty package marker | none |
| `internal_summary.py` | 306 | what the model sees: assignment, source custody, own literature outcome page (`outcome_page_size`), examined source inputs, received intervention analysis rows, experimental-work aspect, return meanings/bindings and display contexts of every enabled population family, population task context, current report facts, goal plan when a literature_task is present; reference-evidence-parent context at the root only | `runtime_actions` ×2, `services.own_outcomes`, `services.read_record` ×5, `workflow.run_id` ×2, `workflow.store` ×4, 11 imports of `a106.library.literature_*` |
| `received_evidence.py` | 269 | what this episode reads back from children: received cells per population family (requested empty arrays filled), received form references, received evidence tokens, validates a received report (lead/screening answers must equal saved work; cells must match receipts); `received_application_rows` | `import a106.domain` ×2, `import a106.library.intervention_execution_lookup`, `import a106.method_loop.durable`, `services.record_selection` ×3, `workflow.store` ×2, 17 imports of `a106.library.literature_*` |
| `report_delivery.py` | 33 | generic finish: saves form with facts and releases | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_forms` ×2, `workflow.binding_context`, `workflow.episode_bindings`, `workflow.facts`, `workflow.journal` ×2, `workflow.pending_handles`, `workflow.release` ×2, `workflow.source_credit_view` |
| `scientific_records.py` | 223 | repository factories for each population/model family (endpoint signal, concentration window, measurement comparison, summary precision, rate grid, compiled assay v1-v3, product coupling, measurement validation, ion discrimination, channel, completion time, active site, perturbation operand, parent depletion, stoichiometric balance, product partition, binding interaction, kinetic model, ratio source, controlled response, gel, native rate meaning) and the population route table | `import a106.library`, `workflow.run_id` ×18, `workflow.store` ×18, 41 imports of `a106.library.literature_*` |
| `scoring/__init__.py` | 1 | package marker | none |
| `scoring/intervention_main_sheet.py` | 13 | A106 subscore sheet repository; automatic score judgments prepared and completed after actions | `workflow.run_id`, `workflow.store`, 1 imports of `a106.library.literature_*` |
| `source_contracts.py` | 51 | A106 contract constants: ROLES chain, `_CHILDREN` chain, assignment shapes (window/table/page), access/acquisition/read tool lists, `_ROLE_INSTRUCTIONS` per role, population catalog order and selection | `import a106.communication`, `import a106.composition_information`, `import a106.domain`, `import a106.episode_bindings`, `import a106.experimental_database_acquisition`, `import a106.library`, 2 imports of `a106.library.literature_*` |
| `source_operations.py` | 243 | permitted actions `tool, reason, child, wait, redeliver_report`; reason schema adds `source_lead` for lead tasks; tool catalog = filtered access/acquisition/NCBI/GEO/SRA tools + enabled populations + `literature.intervention_analysis.contract` (local, builds a BV-BRC TnSeq/RNASeq results selector schema); populate tools route to repositories; invalid arguments become invalid outcomes | `import a106.bvbrc_appservice_adapters`, `import a106.bvbrc_intervention_contracts`, `import a106.composition_information`, `import a106.domain`, `import a106.library.intervention_execution_lookup`, `import a106.literature_contract_error` ×2, `services.execute_tool`, `services.get`, `services.items`, `services.read_record` ×4, `services.tool_catalog`, `workflow.store`, 2 imports of `a106.library.literature_*` |
| `source_references.py` | 35 | reference scope checks, artifact per representation, within-source ancestry, resolve | `services.read_record`, `services.reference_in_scope` |
| `task_decision.py` | 427 | generic model call; literature decision completion routes through the provider's `complete_with_presentation` with this binding's prompt renderer | `bind_functions` ×3, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.providers` ×2, `import a106.runtime` ×4, `runtime_model_calls` ×8, `services.decision_exchange_instructions`, `workflow.contract_information_profile`, `workflow.contract_information_reply`, `workflow.decision_exchanges` ×4, `workflow.decision_protocol` ×3, `workflow.execute`, `workflow.freeze_contract_information`, `workflow.freeze_literature_numerical_contracts`, `workflow.history_preview`, `workflow.journal` ×3, `workflow.numerical_contracts`, `workflow.provider` ×3, `workflow.receipts` ×4, `workflow.run_id`, `workflow.services`, `workflow.specialist` ×2, `workflow.store` ×2, `workflow.uses_received_record_context` ×2, `workflow.validate_contract_information` ×5 |
| `task_instructions.py` | 24 | generic instruction composer (shared literature text, reason commit requirement, wait/native event/redelivery guidance) | `workflow.binding_context`, `workflow.decision_protocol`, `workflow.knowledge`, `workflow.launch_instructions`, `workflow.native_event_information`, `workflow.permits_common_action` ×3, `workflow.specialist`, 1 imports of `a106.library.literature_*` |
| `task.py` | 215 | generic literature loop with reason/child/wait branches | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_source_failure`, `import a106.library.live_runtime_functions`, `import a106.providers`, `import a106.runtime` ×3, `runtime_actions` ×8, `runtime_episodes`, `runtime_model_calls` ×2, `services.instructions`, `workflow.automatic_score_updates`, `workflow.binding_context` ×2, `workflow.completed_unit` ×3, `workflow.completions` ×3, `workflow.controller_value` ×2, `workflow.decision_exchanges` ×3, `workflow.execute`, `workflow.execution_binding` ×7, `workflow.inprocess_replay` ×4, `workflow.journal` ×7, `workflow.last_observed_credit`, `workflow.next_return`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.reasoning_action_schema`, `workflow.receive_native_outcome`, `workflow.receive_outcome`, `workflow.resolve_pending_deliveries`, `workflow.resolver`, `workflow.retain_shared_grading_results`, `workflow.run_id` ×3, `workflow.selected` ×3, `workflow.services`, `workflow.source_credit_view`, `workflow.specialist` ×2, `workflow.store` ×9, `workflow.validate_report` |
| `task_state.py` | 114 | generic restore/checkpoint/failure recording | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_source_failure`, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_actions` ×5, `workflow.archive`, `workflow.completions` ×4, `workflow.context`, `workflow.controller_value`, `workflow.execution_binding` ×4, `workflow.grains`, `workflow.inprocess_replay` ×7, `workflow.journal` ×5, `workflow.progress_provider` ×2, `workflow.recover_commissions`, `workflow.run_id`, `workflow.source_credit_view`, `workflow.store` ×2 |
| `to_child_evidence_search_strategy_improvement.py` | 33 | prepares the `literature_strategy` child: scope within parent, child return schema, required return sources, initial report, role allowed, child prepare_assignment | `import a106.runtime`, `services.capabilities`, `workflow.annotation_child_roles`, `workflow.available_child_roles`, `workflow.binding_context` ×4, `workflow.child_initial_report_input`, `workflow.episode_bindings` ×3, `workflow.expanded_contract_form`, `workflow.launch_instructions`, `workflow.run_id`, `workflow.services`, `workflow.specialist`, `workflow.store` |
| `to_child_execution_job_submission.py` | 39 | prepares the `launch` child (binding path must be `.../published_evidence_assessment/execution_job_submission`); `analysis_children` offers `launch` and `results` only when an execution binding is configured | `import a106.library.intervention_execution_lookup`, `import a106.runtime`, `services.capabilities`, `workflow.annotation_child_roles`, `workflow.available_child_roles`, `workflow.binding_context` ×4, `workflow.child_initial_report_input`, `workflow.episode_bindings` ×3, `workflow.expanded_contract_form`, `workflow.launch_instructions`, `workflow.run_id`, `workflow.services`, `workflow.specialist`, `workflow.store` |
| `to_child_execution_result_acquisition.py` | 29 | prepares the `results` child (binding path must be `.../published_evidence_assessment/execution_result_acquisition`) | `import a106.runtime`, `services.capabilities`, `workflow.annotation_child_roles`, `workflow.available_child_roles`, `workflow.binding_context` ×4, `workflow.child_initial_report_input`, `workflow.episode_bindings` ×3, `workflow.expanded_contract_form`, `workflow.launch_instructions`, `workflow.run_id`, `workflow.services`, `workflow.specialist`, `workflow.store` |
| `to_parent.py` | 185 | report fact sources: rate/population cells, screening answers, lead dispositions; facts at finish; current report facts (completed work, current scoring sheets); report validation against assignment, references and received evidence | `services.read_record` ×3, `workflow.store` ×5, 45 imports of `a106.library.literature_*` |
| `waiting.py` | 37 | generic selected wait | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `workflow.execution_backend`, `workflow.execution_handle` ×2, `workflow.perform_selected_wait` |
| `yield_estimator.py` | 103 | private yield binding per task key: `verified_source_leads` → accumulation controller with cutoff; source answers → finite remaining-commissioned-credit controller (forecast capped by credit_unit − earned, exact zero when earned) | `estimate_score_yield` ×3, `import a106.communication`, `import a106.domain`, `import a106.numerical`, `import a106.numerical.estimate_score_yield`, `YieldController` ×4, `YieldEstimate` ×2, `YieldParameters` ×3 |
