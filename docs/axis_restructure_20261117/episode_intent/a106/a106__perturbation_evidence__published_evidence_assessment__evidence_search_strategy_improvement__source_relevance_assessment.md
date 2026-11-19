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
