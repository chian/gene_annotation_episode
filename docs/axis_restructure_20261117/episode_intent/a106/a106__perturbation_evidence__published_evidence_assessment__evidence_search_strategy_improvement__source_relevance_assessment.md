# a106 / perturbation_evidence / published_evidence_assessment / evidence_search_strategy_improvement / source_relevance_assessment

Source: this episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/<file>`),
including its own `grading/` and `scoring/`. `tests/` and the child folder `source_evidence_examination/` are not
covered here. The old binding class is `LiteratureEpisode`. Its decision source is `LiteratureTask`.

This episode's files are copies of its parent `evidence_search_strategy_improvement`'s. They differ only in the role
literal, the assignment version and field, the binding path, the commissioning parent and the child. The shared
literature behaviour is described in full in `a106__perturbation_evidence__published_evidence_assessment.md`.

## Purpose (goal, in its own words)

Role `literature_search`. It is not an entry role. From `_ROLE_INSTRUCTIONS['literature_search']`:

> Investigate which returned sources merit examination for the assigned question. Search results are source-discovery
> information. Examine original sources and their conditions before asserting biological evidence. A page child can
> investigate where and how to examine a selected source.

`goal.instructions` = this text + `PERTURBATION_TASK` + the A106 subscore `TASK`.

## Task and instructions

The same literature composer and loop: reason, child, wait and redeliver are permitted, and the model call uses the
literature prompt renderer. The `literature_task` schema and checks are identical.

## What it reads from its parent's assignment

- Parent: `.../published_evidence_assessment/evidence_search_strategy_improvement` (role `literature_strategy`).
- `assignment_schema` = `{version: 'search_assignment_v1', question_context_refs, search_result_refs}`, plus
  `literature_task`, `proposed_annotation_ref` and the requested component arrays.
- `prepare_assignment`: the private yield binding fills credit_unit and yield_settings; references are validated in
  scope; the proposed annotation must equal the parent's.

## Children it may commission

| role | child episode | what it sends | what it takes back |
|---|---|---|---|
| `literature_page` | `.../source_relevance_assessment/source_evidence_examination` | `to_child_source_evidence_examination.prepare_request`: the same steps as its parent's preparer, with role `literature_page` | `from_child_source_evidence_examination.receive_report`: recorded admission / child progress / form references / timing receipts / receipts |

`_CHILDREN['literature_search'] = ('literature_page',)`. There are no execution children.

## Decision state and what the model sees

The same as the other literature episodes. `literature_assignment` is the search assignment. Source custody is
usually empty (`search_result_refs` is not read as `source_refs`).

## Tools it offers

`tool, reason, child, wait, redeliver_report`. Filtered access/acquisition/NCBI tools and the enabled population
tools. No `literature.intervention_analysis.contract`.

## Credit

Identical: `credit_unit × answers`, kind `scientific`, never bounded.

## Continuation

Identical: private yield per task key (accumulation for leads; finite remaining-commissioned-credit, i.e.
completion with a target, for source answers). With no private binding, it returns None.

## What it reports to its parent

The same fact sources and facts (rate/population cells, screening answers, lead dispositions, completed work,
scoring sheets). The report must equal the saved work.

## Differences from similar episodes

- Compared with `evidence_search_strategy_improvement`: the role (`literature_search`), the assignment
  (`search_assignment_v1`, `search_result_refs`) and the child (`literature_page`). Everything else is the same
  text.
- Compared with `published_evidence_assessment`: additionally, no execution children, no intervention analysis
  contract tool, and not an entry role.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `binding_record.py` | 26 | binding identity (`binding_id` = this episode's path) and saved configuration: outcome_page_size, enabled population flags, yield_bindings, reference_parent_sources, contract_information_profile, ratio/controlled-response/gel descriptors and evidence origins | none |
| `configuration.py` | 100 | constructor contract: services, outcome_page_size ≥1, eleven boolean population switches (ratio_source, controlled_response, gel, completion_time, product_partition, active_site, parent_depletion, stoichiometric_balance, compiled_assay, channel, ion_discrimination), evidence origin `reported_source`/`synthetic_fixture`, implementation descriptors that must match, contract information profile, explicit unique reference_parent_sources, private_yield_binding + yield_bindings validated by this episode's yield_estimator; `reference_evidence` entry point | `import a106.composition_information`, 2 imports of `a106.library.literature_*` |
| `credit.py` | 202 | task credit = `credit_unit × number of answers`: verified source leads with disposition `relevant` (own reason results + received child forms, latest per canonical source), or the first retained target-eligible assessment anchored in an assigned source, or a full-coverage `no_applicable_evidence` screening answer; `validate_lead` checks question, source, received inputs, anchored subject and exact witness quote; credit kind `scientific`; credit view through the services' scientific credit projector with the parent assignment | `estimate_score_yield`, `import a106.communication`, `import a106.domain` ×2, `import a106.finding_validity`, `import a106.numerical`, `import a106.scientific_findings`, `runtime_actions` ×4, `runtime_report_attempts` ×2, `services.annotation_task_required`, `services.proposed_annotation_for`, `services.scientific_credit`, `workflow.projection_view`, `workflow.projector_receipt_arguments`, `workflow.scientific_projector_for_context`, `YieldController`, `YieldEstimate`, `YieldParameters`, 2 imports of `a106.library.literature_*` |
| `decision_inputs.py` | 78 | generic runner input assembly (same as other literature episodes) | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `workflow.action_schema`, `workflow.available_child_roles`, `workflow.binding_context`, `workflow.delivery_resolution_inputs`, `workflow.episode_bindings`, `workflow.execution_expectations`, `workflow.launch_instructions` ×2, `workflow.native_estimation_context`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.resource_context`, `workflow.resource_estimator` ×4, `workflow.shared_information_context`, `workflow.waiting_support` |
| `decision_presentation.py` | 33 | generic presentation of completed work and yield table | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_work_report`, `import a106.library.live_runtime_functions`, `import a106.runtime` ×4, `workflow.controller_binding` |
| `decision_state.py` | 59 | generic decision state shown to the model, plus annotation context for scientific sources and specialist decision context | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_actions` ×2, `workflow.annotation_context`, `workflow.binding_context`, `workflow.catalog`, `workflow.controller_binding`, `workflow.delivery_status`, `workflow.extra_report_sources`, `workflow.is_scientific_source`, `workflow.job_episode_options`, `workflow.journal` ×3, `workflow.knowledge`, `workflow.local_outcome_preview`, `workflow.pending_work`, `workflow.receipt_projection`, `workflow.run_id`, `workflow.source_credit_binding`, `workflow.source_credit_view`, `workflow.specialist`, `workflow.store` ×3, `workflow.tools`, `workflow.working_state` |
| `episode.py` | 70 | assembles the binding: role `literature_search` (not an entry role), only child `literature_page`, prompt renderer, 19 source repositories | 1 imports of `a106.library.literature_*` |
| `from_child_source_evidence_examination.py` | 42 | admits the page child's typed form (recorded admission, progress, references, timing, receipts) | `import a106.delivery_counterpart`, `import a106.episode_return_records`, `import a106.runtime`, `runtime_report_attempts` ×2, `workflow.binding_context` ×4, `workflow.episode_bindings`, `workflow.is_job_source` ×2, `workflow.job_episodes` ×2, `workflow.native_timing_information`, `workflow.progress_provider` ×4, `workflow.receipts` ×3, `workflow.run_id` ×6, `workflow.specialist`, `workflow.store` ×7 |
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
| `source_operations.py` | 219 | permitted actions `tool, reason, child, wait, redeliver_report`; reason schema adds `source_lead` for lead tasks; executing a lead checks source access, commits reasoning, then validates the lead; tool catalog = filtered access/acquisition/NCBI/GEO/SRA tools + enabled populations; populate tools route to their repositories; invalid arguments become invalid outcomes; state.query records authorized per repository | `import a106.bvbrc_appservice_adapters`, `import a106.composition_information`, `import a106.domain`, `import a106.library.intervention_execution_lookup`, `import a106.literature_contract_error` ×2, `services.execute_tool`, `services.get`, `services.read_record` ×4, `services.tool_catalog`, `workflow.store`, 2 imports of `a106.library.literature_*` |
| `source_references.py` | 35 | reference scope checks, artifact per representation, within-source ancestry, resolve | `services.read_record`, `services.reference_in_scope` |
| `task_decision.py` | 427 | generic model call; literature decision completion routes through the provider's `complete_with_presentation` with this binding's prompt renderer | `bind_functions` ×3, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.providers` ×2, `import a106.runtime` ×4, `runtime_model_calls` ×8, `services.decision_exchange_instructions`, `workflow.contract_information_profile`, `workflow.contract_information_reply`, `workflow.decision_exchanges` ×4, `workflow.decision_protocol` ×3, `workflow.execute`, `workflow.freeze_contract_information`, `workflow.freeze_literature_numerical_contracts`, `workflow.history_preview`, `workflow.journal` ×3, `workflow.numerical_contracts`, `workflow.provider` ×3, `workflow.receipts` ×4, `workflow.run_id`, `workflow.services`, `workflow.specialist` ×2, `workflow.store` ×2, `workflow.uses_received_record_context` ×2, `workflow.validate_contract_information` ×5 |
| `task_instructions.py` | 24 | generic instruction composer (shared literature text, reason commit requirement, wait/native event/redelivery guidance) | `workflow.binding_context`, `workflow.decision_protocol`, `workflow.knowledge`, `workflow.launch_instructions`, `workflow.native_event_information`, `workflow.permits_common_action` ×3, `workflow.specialist`, 1 imports of `a106.library.literature_*` |
| `task.py` | 215 | generic literature loop with reason/child/wait branches | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_source_failure`, `import a106.library.live_runtime_functions`, `import a106.providers`, `import a106.runtime` ×3, `runtime_actions` ×8, `runtime_episodes`, `runtime_model_calls` ×2, `services.instructions`, `workflow.automatic_score_updates`, `workflow.binding_context` ×2, `workflow.completed_unit` ×3, `workflow.completions` ×3, `workflow.controller_value` ×2, `workflow.decision_exchanges` ×3, `workflow.execute`, `workflow.execution_binding` ×7, `workflow.inprocess_replay` ×4, `workflow.journal` ×7, `workflow.last_observed_credit`, `workflow.next_return`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.reasoning_action_schema`, `workflow.receive_native_outcome`, `workflow.receive_outcome`, `workflow.resolve_pending_deliveries`, `workflow.resolver`, `workflow.retain_shared_grading_results`, `workflow.run_id` ×3, `workflow.selected` ×3, `workflow.services`, `workflow.source_credit_view`, `workflow.specialist` ×2, `workflow.store` ×9, `workflow.validate_report` |
| `task_state.py` | 114 | generic restore/checkpoint/failure recording | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.episode_source_failure`, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `runtime_actions` ×5, `workflow.archive`, `workflow.completions` ×4, `workflow.context`, `workflow.controller_value`, `workflow.execution_binding` ×4, `workflow.grains`, `workflow.inprocess_replay` ×7, `workflow.journal` ×5, `workflow.progress_provider` ×2, `workflow.recover_commissions`, `workflow.run_id`, `workflow.source_credit_view`, `workflow.store` ×2 |
| `to_child_source_evidence_examination.py` | 33 | prepares the `literature_page` child (same steps as the parent's preparer) | `import a106.runtime`, `services.capabilities`, `workflow.annotation_child_roles`, `workflow.available_child_roles`, `workflow.binding_context` ×4, `workflow.child_initial_report_input`, `workflow.episode_bindings` ×3, `workflow.expanded_contract_form`, `workflow.launch_instructions`, `workflow.run_id`, `workflow.services`, `workflow.specialist`, `workflow.store` |
| `to_parent.py` | 185 | report fact sources: rate/population cells, screening answers, lead dispositions; facts at finish; current report facts (completed work, current scoring sheets); report validation against assignment, references and received evidence | `services.read_record` ×3, `workflow.store` ×5, 45 imports of `a106.library.literature_*` |
| `waiting.py` | 37 | generic selected wait | `bind_functions` ×2, `_bind_original_task_runtime_providers` ×2, `import a106.library.live_runtime_functions`, `import a106.runtime` ×3, `workflow.execution_backend`, `workflow.execution_handle` ×2, `workflow.perform_selected_wait` |
| `yield_estimator.py` | 103 | private yield binding per task key: `verified_source_leads` → accumulation controller with cutoff; source answers → finite remaining-commissioned-credit controller (forecast capped by credit_unit − earned, exact zero when earned) | `estimate_score_yield` ×3, `import a106.communication`, `import a106.domain`, `import a106.numerical`, `import a106.numerical.estimate_score_yield`, `YieldController` ×4, `YieldEstimate` ×2, `YieldParameters` ×3 |

## Carried over

Carried over on 19 November 2026 (private binding, ten-file form, with its child episode `source_evidence_examination` carried before it), from the old files at 97308b94c. One row per old function, class and method (`runs/carry_over/functions/a106__perturbation_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment.tsv`). Rows marked "population route not built" are listed in `carry_over_blocked/` under unplaced_old_functions. Rows marked "library candidate" are private functions of this episode that are not in the library yet. The old files of this episode are copies of those of its child `source_evidence_examination` but for the role, the assignment, the child and the acquisition tools; the classification of identical rows follows the child's.

| old file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record() |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() |
| configuration.py | LiteratureConfiguration | machinery | construction-time settings of the old binding; the episode settings are ctx.settings (cost, parameters, tool_registry, knowledge_library_directory); outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py |
| configuration.py | LiteratureConfiguration.__init__ | machinery | construction-time settings of the old binding; the episode settings are ctx.settings (cost, parameters, tool_registry, knowledge_library_directory); outcome_page_size is OUTCOME_PAGE_SIZE in messages/internal_summary.py |
| configuration.py | LiteratureConfiguration.reference_evidence | episode function | not carried: root-only reference_evidence_parent context (not this episode's); see unplaced |
| credit.py | _resolve | episode function | library already has it: episode_support literature.grading.literature_task_credit._resolve (imported by task.py) |
| credit.py | validate_lead | episode function | task.py validate_source_lead (private re-expression on custody; library candidate) |
| credit.py | lead_dispositions | episode function | credit.py lead_dispositions (private re-expression over summary and records, own and child leads in unit order; library candidate) |
| credit.py | _current_assessments | episode function | credit.py current_assessments (library candidate) |
| credit.py | screening_answers | episode function | credit.py screening_answers (library candidate) |
| credit.py | LiteratureTaskCredit | episode function | credit.py (module) |
| credit.py | LiteratureTaskCredit.as_record | episode function | credit.py credit_binding (README 3d: the projector's as_record is episode content) |
| credit.py | LiteratureTaskCredit.__call__ | episode function | credit.py credit (credit_unit times the answers; commission-agreement checks are old-runner receipt checks and are not carried) |
| credit.py | LiteratureTaskCredit._answers | episode function | credit.py answers / assessment_answers (library candidate) |
| credit.py | LiteratureCredit | episode function | credit.py (module) |
| credit.py | LiteratureCredit._scientific_credit_invocation | machinery | services.scientific_credit / projection_view invocation of the old runner |
| credit.py | LiteratureCredit.credit_kind | machinery | credit kind declaration of the old runner |
| credit.py | LiteratureCredit.credit_view | machinery | services.scientific_credit view; credit(summary, records) is called by the system |
| credit.py | LiteratureCredit.credit_projector | episode function | credit.py credit |
| decision_inputs.py | LiteratureDecisionInputs | episode function | task.py decide (context the model is shown) over messages/internal_summary.py; contract-information, resource, shared-information, launch-instruction, pending-work and native-event pieces have no home here (no job, launch or wait); child options are task.py commissions(); see unplaced |
| decision_inputs.py | LiteratureDecisionInputs.decision_inputs | episode function | task.py decide (context the model is shown) over messages/internal_summary.py; contract-information, resource, shared-information, launch-instruction, pending-work and native-event pieces have no home here (no job, launch or wait); child options are task.py commissions(); see unplaced |
| decision_inputs.py | LiteratureDecisionInputs.current_decision_inputs | episode function | task.py decide (context the model is shown) over messages/internal_summary.py; contract-information, resource, shared-information, launch-instruction, pending-work and native-event pieces have no home here (no job, launch or wait); child options are task.py commissions(); see unplaced |
| decision_inputs.py | _a106_original_global_ValueError | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| decision_inputs.py | _a106_original_global_child_option_information | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| decision_inputs.py | _a106_original_global_set | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| decision_presentation.py | prepare_completed_work | episode function | messages/internal_summary.py action_yields (yield_table); the completed-work table belongs to the population route and is not carried |
| decision_presentation.py | decision_yield_table | episode function | messages/internal_summary.py action_yields (yield_table); the completed-work table belongs to the population route and is not carried |
| decision_presentation.py | _bind_original_task_runtime_providers | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| decision_state.py | LiteratureDecisionState | episode function | task.py decide / messages/internal_summary.py internal_summary (the decision state is the summary) |
| decision_state.py | LiteratureDecisionState.decision_state | episode function | task.py decide / messages/internal_summary.py internal_summary (the decision state is the summary) |
| decision_state.py | _bind_original_task_runtime_providers | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| episode.py | LiteratureEpisode | episode function | episode.py class SourceRelevanceAssessment(EpisodeBinding) |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | report-contract information profile (report_form machinery) |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | report-contract information profile (report_form machinery) |
| episode.py | LiteratureEpisode._role | machinery | role check of the old shared binding (role literature_search is now binding_path) |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS (literature_page) |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS (literature_page) |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | context hook of the old runner |
| episode.py | LiteratureEpisode.child_request_preparer | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | LiteratureEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| from_child_source_evidence_examination.py | receive_report | episode function | messages/read_from_child.py read_from_child (the old receipt, progress and timing bookkeeping is the system's custody and is not carried) |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (search_assignment_v1; rate-population properties not declared; see unplaced) |
| from_parent.py | LiteratureAssignment.child_assignment_schema | machinery | the parent's view of its child's assignment schema (README 3b C3): the parent writes the assignment in msg_to_child and the child's own form admits it |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (search_assignment_v1; rate-population properties not declared; see unplaced) |
| from_parent.py | LiteratureAssignment._validate_page | episode function | not carried: checks the page the model chose against the Store (source/artifact in scope and artifact of the representation); it was reached by the child page episode, not by this role's own assignment; a wrong commission fails; see unplaced |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (checks that need no Store); the Store checks (each *_refs in scope, search_result_refs of kind source) are not carried (see unplaced) |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/msg_to_child.py msg_to_child builds the child's assignment; messages/read_from_parent.py ASSIGNMENT_FORM literature_task carries credit_unit (the private-yield-binding fill, the proposed-annotation agreement with the parent and the operation-key requirement are not carried; see unplaced) |
| goal.py | _yield_kind | episode function | yield_estimator.py yield_controller (accumulation for verified_source_leads, completion otherwise) |
| goal.py | _task_key | episode function | messages/read_from_parent.py task_key |
| goal.py | task_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM literature_task and read_from_parent task-kind checks |
| goal.py | _return_sources | machinery | x-source scanning of the parent's report contract (report_form machinery); the child declares its return in RETURN_FORM |
| goal.py | _return_components | machinery | x-source component scanning of the parent's report contract (report_form machinery) |
| goal.py | commissioned_task | episode function | messages/read_from_parent.py read_from_parent (task checks; this role has no assigned page, so the page-confinement checks do not apply); report-contract checks are old report_form machinery |
| goal.py | continuation_task | episode function | messages/read_from_parent.py task_key (parent_input task_key) |
| goal.py | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL (role instruction + PERTURBATION_TASK + A106 sub-score TASK) |
| goal.py | LiteratureGoal.planning_context | episode function | messages/internal_summary.py (credit_binding, task, proposed_annotation_ref) shown by task.py decide |
| grading/intervention_assessment.py | InterventionAssessment | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| grading/intervention_assessment.py | InterventionAssessment._required_grading_repository | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| grading/intervention_assessment.py | InterventionAssessment._intervention_source_cells | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| grading/intervention_assessment.py | InterventionAssessment._intervention_grading_repository | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary.initial_decision_context | episode function | not carried: caller-literature-job context (reference_evidence_parent) is root-only; see unplaced |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (literature_assignment, literature_source_custody over the held sources, own_literature_outcomes with the acquisition and read tools, literature_history_meaning, literature_experimental_work); the examined-source inputs and intervention analysis rows are not carried (see unplaced) |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._concentration_window_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._measurement_comparison_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._summary_precision_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._endpoint_signal_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._controlled_response_bindings | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._gel_bindings | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._gel_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._received_fact_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._native_rate_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._native_rate_domain_display_context | episode function | population route display context not built; not carried; see unplaced |
| internal_summary.py | LiteratureSummary._native_rate_meaning_display_context | episode function | population route display context not built; not carried; see unplaced |
| received_evidence.py | LiteratureReceivedEvidence | machinery | receipt bookkeeping of received report facts / references (README 3b R3, 3e F5): system custody |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | receipt bookkeeping of received report facts / references (README 3b R3, 3e F5): system custody |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | machinery | receipt bookkeeping of received report facts / references (README 3b R3, 3e F5): system custody |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | machinery | receipt bookkeeping of received report facts / references (README 3b R3, 3e F5): system custody |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | machinery | receipt bookkeeping of received report facts / references (README 3b R3, 3e F5): system custody |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | receipt bookkeeping of received report facts / references (README 3b R3, 3e F5): system custody |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py validate_report (answers agree with the saved work, computed from the same summary); the numerical-row checks belong to the population route (see unplaced) |
| received_evidence.py | received_application_rows | episode function | not carried: BV-BRC application return rows need the old execution binding (intervention_execution_lookup); see unplaced |
| report_delivery.py | LiteratureReportDelivery | machinery | report_form machinery: finish builds, saves and releases the report form (README 3b D1/D3); final_to_parent returns the result |
| report_delivery.py | LiteratureReportDelivery.finish | machinery | report_form machinery: finish builds, saves and releases the report form (README 3b D1/D3); final_to_parent returns the result |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| scientific_records.py | LiteratureScientificRecords | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._a106_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._endpoint_signal_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._concentration_window_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._measurement_comparison_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._summary_precision_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._rate_grid_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v2_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._compiled_assay_v3_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._product_coupling_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._measurement_validation_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._ion_discrimination_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._channel_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._completion_time_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._active_site_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._perturbation_operand_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._parent_depletion_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._stoichiometric_balance_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._product_partition_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._binding_interaction_model_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._kinetic_model_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._ratio_source_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._controlled_response_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._gel_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._native_rate_meaning_repository | episode function | population route not built; not carried; see unplaced |
| scientific_records.py | LiteratureScientificRecords._population_routes | episode function | population route not built; not carried; see unplaced |
| scoring/intervention_main_sheet.py | InterventionMainSheet | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| scoring/intervention_main_sheet.py | InterventionMainSheet._a106_subscore_repository | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| scoring/intervention_main_sheet.py | InterventionMainSheet.automatic_score_judgments | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| scoring/intervention_main_sheet.py | InterventionMainSheet.complete_score_judgment | episode function | not carried: the intervention grading / A106 sub-score repository belongs to the population route; see unplaced |
| source_contracts.py | _required_grading_logic | episode function | not carried: it returned the A106 required-grading logic only for a population repository (None by default); no validate_form is called here |
| source_contracts.py | _population_catalog | episode function | population route not built; not carried; see unplaced |
| source_operations.py | LiteratureOperations | episode function | task.py (offered, catalog, selection_schema, reason, run_access_tool) |
| source_operations.py | LiteratureOperations.permitted_common_actions | episode function | task.py selection_schema (tool and child units; reason is a tool; wait and redeliver_report are not carried) |
| source_operations.py | LiteratureOperations.reasoning_action_schema | episode function | task.py reason_schema |
| source_operations.py | LiteratureOperations.reasoning_has_task_content | episode function | task.py action (empty_commit; a source_lead makes a commit valid) |
| source_operations.py | LiteratureOperations.execute_reasoning | episode function | task.py reason tool and validate_source_lead (the required-grading branch is not carried) |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py offered / catalog / DESCRIPTIONS / INPUT_SCHEMAS (access tools, the acquisition tools and the NCBI entrez, sequence, GEO and SRA file tools; population entries not built) |
| source_operations.py | LiteratureOperations.execute | episode function | task.py run_access_tool (the populate branch and literature.intervention_analysis.contract are not carried; see unplaced) |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py admitted (arguments against the offered schema; no page, so no confinement to a page source; the population repository authorizations are not carried) |
| source_operations.py | LiteratureOperations._materialize_text_arguments | episode function | population route not built; not carried; see unplaced |
| source_operations.py | prepare_analysis_contract | episode function | not carried: needs the old BV-BRC execution binding; see unplaced |
| source_references.py | LiteratureReferences | episode function | not carried: its three methods served the page confinement (_within_source), which applies only when the assignment has a page; this role has none; see unplaced |
| source_references.py | LiteratureReferences._require | episode function | not carried: used by _within_source and _validate_page only; see unplaced |
| source_references.py | LiteratureReferences._artifact | episode function | not carried: only _validate_page used it (a Store check of the commission); see unplaced |
| source_references.py | LiteratureReferences._within_source | episode function | not carried: page confinement, applies only with an assigned page; this role has none; see unplaced |
| source_references.py | LiteratureReferences.resolve | machinery | reference_in_context resolver of the old report form (report_form machinery) |
| task.py | LiteratureTask | episode function | task.py decide / action / TOOLS (the loop is the system's) |
| task.py | LiteratureTask.instructions | episode function | task.py instructions |
| task.py | LiteratureTask.next | episode function | task.py decide |
| task.py | LiteratureTask.apply_response | episode function | task.py action |
| task.py | LiteratureTask.execute | episode function | task.py TOOLS and ChildCall (the old wait branch and result bookkeeping are the system's) |
| task.py | _bind_original_task_runtime_providers | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | LiteratureTaskDecision | episode function | task.py decide |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py decide (ModelRequest; the provider call is the system's) |
| task_decision.py | LiteratureTaskDecision.decision_completion | machinery | model-call completion bookkeeping of the old runner |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | conversation state of the old runner (every ModelRequest carries the full context) |
| task_decision.py | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange loop / saved-exchange machinery of the old runner (a lookup is a tool; README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop / saved-exchange machinery of the old runner (a lookup is a tool; README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop / saved-exchange machinery of the old runner (a lookup is a tool; README 3a) |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop / saved-exchange machinery of the old runner (a lookup is a tool; README 3a) |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop / saved-exchange machinery of the old runner (a lookup is a tool; README 3a) |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop / saved-exchange machinery of the old runner (a lookup is a tool; README 3a) |
| task_decision.py | _a106_original_global_DECISION_CONTEXT_VERSION | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_OSError | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_TypeError | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_ValidationError | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_ValueError | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global__action_generation_schema | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global__json | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global__plain | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_child_option_information | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_instructional_model_context | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_isinstance | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_len | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_lookup_attempts | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_model_snapshot | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_requested_contract_information | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_schema_failure_diagnostic | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_sqlite3 | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_state_frame | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_str | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _a106_original_global_type | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_decision.py | _bind_original_task_runtime_providers | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| task_instructions.py | instructions | episode function | task.py instructions |
| task_state.py | LiteratureTaskState | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| task_state.py | LiteratureTaskState.__init__ | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| task_state.py | LiteratureTaskState.record_execution_failure | episode function | task.py run_access_tool (a failed selected operation is returned as a failure_outcome) |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| task_state.py | LiteratureTaskState.restore | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| task_state.py | LiteratureTaskState.record_effect | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| task_state.py | LiteratureTaskState.checkpoint | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| task_state.py | _bind_original_task_runtime_providers | machinery | per-episode state, checkpoint and restore of the old runner (state is the view; resume is the runner's) |
| to_child_source_evidence_examination.py | prepare_request | episode function | messages/msg_to_child.py msg_to_child (the page assignment the model chose, the literature task for the page with this commission's credit unit, the proposed annotation, the scope and the records named for the child) |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (selectable literature_screening_answers and literature_source_lead_dispositions; the population fact sources are not declared) |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | LiteratureReport.current_report_facts | episode function | not carried: literature_completed_work and literature_current_scoring_sheets belong to the population route; see unplaced |
| to_parent.py | LiteratureReport._rate_fact_sources | episode function | population route not built; not carried; see unplaced |
| to_parent.py | LiteratureReport._rate_facts | episode function | population route not built; not carried; see unplaced |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (called before the result is returned) |
| waiting.py | LiteratureWaiting | machinery | wait / suspension machinery of the old runner (no wait action; the controller stops the episode) |
| waiting.py | LiteratureWaiting.supports_wait | machinery | wait / suspension machinery of the old runner (no wait action; the controller stops the episode) |
| waiting.py | LiteratureTaskWaiting | machinery | wait / suspension machinery of the old runner (no wait action; the controller stops the episode) |
| waiting.py | LiteratureTaskWaiting._execute_selected_wait | machinery | wait / suspension machinery of the old runner (no wait action; the controller stops the episode) |
| waiting.py | LiteratureTaskWaiting.suspension_changed | machinery | wait / suspension machinery of the old runner (no wait action; the controller stops the episode) |
| waiting.py | _bind_original_task_runtime_providers | machinery | provider patching of the old runner (bind_functions / original-global rebinding) |
| yield_estimator.py | validate_yield_bindings | machinery | construction-time check of the configured yield declarations (README 3d); the controller validates its cost and parameters when yield_controller builds it |
| yield_estimator.py | _RemainingCommissionedCredit | machinery | estimator of its own (README 7b): replaced by CompletionYieldController with target = credit_unit |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | machinery | estimator of its own (README 7b): replaced by CompletionYieldController with target = credit_unit |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | machinery | estimator record of its own (README 7b) |
| yield_estimator.py | _private_yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | machinery | controller class of its own (README 7b): replaced by CompletionYieldController with target = credit_unit |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | machinery | controller class of its own (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | machinery | transitioned(epoch) of an episode-local controller (deleted) |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py task_key (parent_input task_key) |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller |
