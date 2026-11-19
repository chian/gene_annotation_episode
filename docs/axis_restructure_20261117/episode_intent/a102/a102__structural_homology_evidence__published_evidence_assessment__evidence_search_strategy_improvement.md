# Episode intent: `a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement`

Source: this episode's own files at commit `97308b94c` (28 Python files, 1,603 lines, directly in the folder; it has
no `tests/`, `grading/` or `scoring/` folder; `source_relevance_assessment/` is its child's folder and was not read).
Old role name: `literature_strategy`. Old class: `LiteratureEpisode` (fifteen mixins), task class `SourceTask`. Old
`binding_path`: `structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement`;
old `commissioning_parent`: `structural_homology_evidence/published_evidence_assessment`. Not an entry role.

## What this episode is for

It investigates which search approach is productive for its parent's published-evidence question, revising terms
and source choices from actual outcomes, and can hand returned sources to a search child that decides which deserve
examination. Goal text, verbatim from `goal.py`:

> Investigate which search approach is productive. Keep the information objective and evidence context separate
> from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search
> child can investigate which returned sources deserve examination.
> This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted child forms
> inform later choices; no child order, reading quota or complete-document requirement is prescribed. A one-off
> search/read is an ordinary tool. A supplied reading selector is context, not an automatically executed action.
> Preserve the source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors.
> Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications can
> advance the investigation. Commit interpretations with the common reasoning action and update only the parent's
> declared typed form in that same work call. Navigation, byte coverage and repeated reading earn no scientific
> credit by themselves. The commissioned task's own yield settings guide continuation.

## Task and instructions

One unit is one model-selected action of kind `tool`, `reason` (a reasoning commit, optionally with a
`source_lead`), `child` (commission the search child) or `redeliver_report`. It does not support waiting.

Instructions (`task_instructions.py`, the same text as its parent's): default (or job) instructions with this goal
appended; the reasoning-commit requirement; tool-knowledge and launch-instruction text when present; the pending-child
redelivery paragraph; wait and native-event paragraphs only when wait is permitted (never, here); the
exchange-history wording under the exchange protocol.

Construction settings (`episode.py`): the same as its parent's (`outcome_page_size` default 8,
`structure_population`, `reference_parent_sources`, `contract_information_profile`, `private_yield_binding`,
`yield_bindings`) and the same `reference_evidence` entry; no `create_binding_tree`.

## What it reads from its parent's assignment

Form `strategy_assignment_v1` (`from_parent.py`):

| Field | Meaning |
|---|---|
| `version` | `strategy_assignment_v1` |
| `question_context_refs` | References that state the question context (must be in scope) |
| `prior_search_refs` | Earlier search results/sources the strategy starts from (must be in-scope sources) |
| `literature_task` | The commissioned literature task; required with the private yield binding, `credit_unit` filled from the declaration |
| `proposed_annotation_ref` | Required with the private yield binding; must equal the parent's |
| requested structure components | The field named by the old `a102_literature_bindings.REQUESTED` |

`prepare_assignment` fills `credit_unit` and `yield_settings` (`kind`, `cutoff`, `uncertainty_alpha`) from the
declaration keyed by the task and refuses a supplied mismatch, exactly as its parent's copy.

## Children

| Slot (old role) | Child | What it sends | What it takes back |
|---|---|---|---|
| `literature_search` | `evidence_search_strategy_improvement/source_relevance_assessment` | A child goal refining its own; a message with scope, initial report, optional report-contract declaration, job and episode assignments, structural-homology context and knowledge inheritance (`to_child_source_relevance_assessment.py`, same text as the parent's `to_child_…`); the assignment form the child declares in its own folder | The child's typed form; its references, structure cells, native timing receipts and tool attributions recorded as received (`from_child_source_relevance_assessment.py`, same text as the parent's `from_child_…`) |

## Decision state and what the model sees

The same fields as its parent (`task.py`, `decision_delivery.py`): the common decision fields, the annotation-axis
credit branch, resource and shared-information context, launch-instruction library, child options, completed action
reports, execution expectations captured for `literature_strategy`, resource estimates, contract-information
profile, frozen literature numerical contracts.

Its summary (`internal_summary.py`) is its parent's text: `literature_assignment`, `literature_source_custody`,
`own_literature_outcomes` (first `outcome_page_size`), their meaning, and with structure population the
experimental-work record, its own population sheets and latest failed population attempt. Because the custody list
is read from `source_refs` (or a `page`), and its own form carries `prior_search_refs` instead, the custody shown is
empty: the prior search sources are visible only as the assignment itself.

Presentation: the same text-TASK renderer selection and per-(episode, role) prompt state as its parent
(`decision_presentation.py` and `presentation_selection.py` are byte-identical to the parent's).

## Tools

The same catalog as its parent (`source_operations.py`, `source_contracts.py`): the access tools, the public
literature/NCBI(`pubmed`)/PMC and experiment-database acquisition tools, `execution.estimate` for xlsx only, and
`literature.structure.populate` with structure population; page confinement, received-record limits and `invalid`
outcomes on argument errors; reasoning commits with a `source_lead` for `verified_source_leads` tasks.

## Credit

Credit kind `scientific`; view from the old services' `scientific_credit`; projector the old `LiteratureTaskCredit`;
the credit unit from the yield declaration of the commissioned task. Same text as its parent.

## Continuation

Same as its parent: none of its own without the private binding; with it, the declaration for
`continuation_task(context)` builds the old `_private_yield_controller`; a missing declaration raises. The estimator
behind each declared `kind` is in the old support module.

## What it reports to its parent

Same facts as its parent's copy: screening answers for a screening task, lead dispositions for a
`verified_source_leads` task, and structure cells with structure population; the report must equal saved work.

## Differences from similar episodes

- Against its parent `published_evidence_assessment`: by text, only the role (`literature_strategy`), binding path
  and parent, entry role (none), the goal's first paragraph (search approach instead of evidence question), the
  assignment version and field (`strategy_assignment_v1` / `prior_search_refs` instead of `literature_assignment_v1`
  / `source_refs`), the child slot (`literature_search` instead of `literature_strategy`), the execution-expectation
  and report grain names, and the absence of `create_binding_tree`. Every other file differs only in its docstring;
  `decision_presentation.py`, `presentation_selection.py`, `source_contracts.py`, `task_instructions.py` and the
  child request/receive texts are identical.
- Because the summary was copied unchanged, the strategy episode does not show custody of its `prior_search_refs`
  (see above): a place where its own tuning was not yet done.

## Old support modules this episode imports

The same modules, from the same files, as its parent (see
`a102__structural_homology_evidence__published_evidence_assessment.md`): `a102_literature_bindings`,
`communication`, `composition_information`, `delivery_counterpart`, `domain`, `episode_bindings`,
`episode_return_records`, `episode_source_failure`, `episode_work_report`, `experimental_database_acquisition`,
`library.action_contracts`, `library.hpc_prompt`, `library.literature_assay_inputs`, `library.monitor_prompt`,
`library.private_policy_call`, `library.report_fact_assembly`, `literature_contract_error`,
`literature_sheet_updates`, `literature_structure_storage`, `literature_task_credit`, `literature_task_selection`,
`method_loop.durable`, `providers`, `read_mapping`, `receiver_prompt`, `runtime`, `runtime_prompt`,
`structural_homology_evidence_prompt`. It has no absolute import inside the episode tree.

## File by file

Counts are occurrences in the file text. `self.workflow` also covers `source.workflow`, `self.services.workflow`
and a `workflow` argument; "BindingContext fields" are attribute reads on the old context object; "old-runner
callbacks defined" are methods the old runner called on the binding or task; "old providers module" are names
taken from the old `root.a102.providers`. The same rows, one per name and file, are in
`runs/carry_over/calls/a102_06.tsv` (416 rows, 731 uses in this episode).

| Old file | Lines | This episode's own intent in it | Old-runner names used (name×uses) |
|---|---|---|---|
| `__init__.py` | 0 | Nothing (package marker). | none |
| `binding_record.py` | 8 | Its configuration record (`literature_episode_binding_v1`, binding id `.../evidence_search_strategy_improvement`): `outcome_page_size`, `structure_population`. | **old-runner callbacks defined**: `as_record` |
| `child_commissioning.py` | 12 | The one child role it may commission: `literature_search` (source_relevance_assessment). | **BindingContext fields**: `role`×2; **old-runner callbacks defined**: `allowed_children`, `child_roles` |
| `configuration.py` | 13 | On-demand contract information is offered to this role (and to a root `annotation` context when reference parent sources are configured). | **BindingContext fields**: `path`, `role`×2; **old-runner callbacks defined**: `contract_information_configuration`, `contract_information_profile` |
| `credit.py` | 17 | Credit kind `scientific`; the credit view is the old services' scientific credit; the projector is the old `LiteratureTaskCredit` over this binding and context. | **BindingContext fields**: `role`×2; **imports from old `root.a102`**: `literature_task_credit`; **old-runner callbacks defined**: `credit_kind`, `credit_projector`, `credit_view`; **self.services**: `scientific_credit`; **old support classes**: `LiteratureTaskCredit`×2 |
| `decision_delivery.py` | 346 | The model call and exchange protocol (old runner). Its own parts: execution expectations captured for role `literature_strategy`; completed action reports unless the annotation-axis credit mode applies; literature numerical contracts frozen with the decision when no contract-information profile is used. | **imports from old `root.a102`**: `episode_work_report`×2, `library.hpc_prompt`, `runtime`×2; **old-runner callbacks defined**: `call`, `complete_decision`, `conversation_key`, `exchange_decision`, `exchange_response`, `exchange_schema`, `instructions`, `interpretation_context`, `validate_contract_exchange_history`, `validate_contract_exchange_request`; **old provider interface**: `complete_with_presentation`, `has_session`×3, `prompt_renderer`; **old runtime**: `_action_generation_schema`×2, `apply_state_frame`, `_ASSIGNMENT_TRANSPORT`, `_category_yield_parameters`, `child_option_information`×2, `composition_lookup_schema`×2, `CONTRACT_INFORMATION_OPERATIONS`, `DECISION_CONTEXT_VERSION`×2, `DECISION_EXCHANGE_PROTOCOL`×5, `_digest`, `Draft202012Validator`, `instructional_model_context`×4, `is_contract_information`, `_json`×14, `json`×3, `lookup_attempts`, `Mapping`×4, `model_snapshot`×2, `_object`×3, `_plain`×2, `_recorded_action_generation_schema`, `_recorded_assignment_transport`, `_references_in`, `requested_contract_information`×2, `schema_failure_diagnostic`×2, `sqlite3`, `state_frame`, `ValidationError`×5, `WorkflowError`×14, `yield_table`; **self.workflow**: `available_child_roles`, `binding_context`, `contract_information_profile`, `contract_information_reply`, `controller_binding`, `decision_exchanges`×4, `decision_protocol`×3, `episode_bindings`, `execute`, `execution_expectations`, `freeze_contract_information`, `freeze_literature_numerical_contracts`, `history_preview`, `is_job_source`×3, `job_episodes`×2, `journal`×3, `launch_instructions`×2, `native_estimation_context`, `numerical_contracts`, `pending_work`, `permits_common_action`, `provider`×3, `provider.conversation_key`, `provider.has_session`, `receipts`×4, `resource_context`, `resource_estimator`×5, `run_id`, `services`×2, `shared_information_context`, `specialist`, `store`×2, `store.reference_subset`, `uses_received_record_context`×2, `validate_contract_information`×5, `waiting_support`; **journal/receipt tables**: `runtime_model_calls`×8; **old yield names**: `_category_yield_parameters`×2, `yield_table`×2 |
| `decision_presentation.py` | 43 | Prompt rendering: a text TASK prompt when the context is HPC, published-scientific, monitor, API launch, selected execution or ordinary receiver context, otherwise the context as JSON; keeps a prompt state per (episode, role) across decision updates and lookups. | **imports from old `root.a102`**: `providers`×2; **old-runner callbacks defined**: `present_source_decision`; **old provider interface**: `provider_presentation`, `scientific_prompt_states`×4; **old providers module**: `apply_state_frame`×3, `DECISION_CONTEXT_VERSION`, `deepcopy`, `json`, `text_instructions` |
| `episode.py` | 89 | The binding: path `structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement`, parent `published_evidence_assessment`, role `literature_strategy`, no entry role; same settings and `reference_evidence` entry as its parent; permitted actions `tool`, `reason`, `child`, `redeliver_report`; child receiver and request assembler for `literature_search`; no `create_binding_tree`. | **BindingContext fields**: `role`; **imports from old `root.a102`**: `literature_task_credit`; **old binding attributes**: `binding_path`, `commissioning_parent`, `decision_prompt_renderer`, `decision_source_type`, `entry_roles`, `roles`; **old-runner callbacks defined**: `child_report_receiver`, `child_request_assembler`, `permitted_common_actions`, `reference_evidence`; **old yield names**: `validate_yield_bindings`×2 |
| `from_child_source_relevance_assessment.py` | 45 | Receiving the search child's typed form: recorded admission refs on replay, progress-provider receipt, references in the form plus structure cells received, native timing receipts, tool attributions; all recorded as received by this episode. Nothing specific to the child beyond the role name. | **imports from old `root.a102`**: `delivery_counterpart`, `episode_return_records`, `runtime`×2; **old-runner callbacks defined**: `receive_report`; **old runtime**: `_json`, `json`, `_references_in`, `WorkflowError`; **self.workflow**: `binding_context`×4, `episode_bindings`, `is_job_source`×2, `job_episodes`×2, `native_timing_information`, `progress_provider`×4, `receipts`×3, `receive_tool_attributions`, `run_id`×6, `specialist`, `store`×7; **old support classes**: `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_report_attempts`×2 |
| `from_parent.py` | 72 | Assignment form `strategy_assignment_v1`: `question_context_refs`, `prior_search_refs`, `literature_task` (task schema; `credit_unit` filled from the yield declaration under the private binding), `proposed_annotation_ref` (required with the private binding), and the requested structure components. Every `_refs` entry must be in scope (`prior_search_refs` as sources). Preparing the assignment fills `credit_unit` and `yield_settings` (kind, cutoff, uncertainty_alpha) from the declaration keyed by the task, refuses a supplied mismatch, and requires the parent's proposed annotation. | **BindingContext fields**: `assignment`; **imports from old `root.a102`**: `a102_literature_bindings`, `literature_task_credit`×2; **old-runner callbacks defined**: `assignment_schema`, `child_assignment_schema`, `prepare_assignment`; **self.services**: `proposed_annotation_for` |
| `goal.py` | 8 | The goal text: investigate which search approach is productive; keep the information objective and evidence context separate from a literal provider query; revise terms or source choices from actual search/read outcomes; a search child can investigate which returned sources deserve examination; plus the shared literature paragraph (no prescribed child order, reading quota or complete-document requirement; keep the source's subject, conditions, representation, version and byte anchors; separate source claims from applicability to the target; negative findings count; navigation and repeated reading earn no scientific credit). | **BindingContext fields**: `role`; **old-runner callbacks defined**: `instructions` |
| `internal_summary.py` | 83 | Per-decision summary (same text as its parent): the admitted assignment, custody of the assigned sources read from `source_refs`, which its own `strategy_assignment_v1` does not carry, so its custody list is empty (its form has no `source_refs`; the `page` branch serves the page role), its own literature outcome metadata (first `outcome_page_size` acquisition/read outcomes) and their meaning; with structure population also the experimental-work record, its own completed population sheets (read-only metadata) and the latest failed population attempt. A root-level reference-evidence context when reference parent sources are configured. | **BindingContext fields**: `assignment`, `episode_id`×4, `path`, `received_record_refs`×2, `role`×2, `run_id`×5, `scope`×4; **imports from old `root.a102`**: `literature_task_selection`; **old-runner callbacks defined**: `decision_context`, `initial_decision_context`; **self.services**: `own_outcomes`, `workflow`×2; **self.workflow**: `run_id`×2, `store`×2; **journal/receipt tables**: `runtime_actions`×2 |
| `presentation_selection.py` | 30 | Which text renderer applies, in predicate order: HPC, published scientific, API launch, selected execution, monitor, receiver. | **imports from old `root.a102`**: `library.hpc_prompt`, `library.monitor_prompt`, `providers`×2, `receiver_prompt`, `structural_homology_evidence_prompt`; **old providers module**: `is_api_launch_context`×2, `is_published_scientific_context`×2, `_ordinary_runtime_receiver_context`, `render_api_launch_prompt`, `render_structural_homology_evidence_prompt` |
| `received_evidence.py` | 73 | Received report facts and cells from children (structure population routes), filling requested empty arrays; references received in a form; received-cell tokens; checking a returned form: screening answers and lead dispositions must equal the saved work, structure cells must be received and requested. | **BindingContext fields**: `assignment`×2, `episode_id`, `received_record_refs`, `request`, `role`×2, `run_id`; **imports from old `root.a102`**: `literature_sheet_updates`, `literature_task_credit`, `method_loop.durable`; **old-runner callbacks defined**: `received_evidence_tokens`, `received_form_references`, `received_report_facts`, `received_report_sources`, `validate_received_report`; **self.services**: `record_selection`, `workflow`×2; **self.workflow**: `store`×2 |
| `report_delivery.py` | 25 | Closure: typed form built once from saved facts and last interpretation (same text as the other A102 copies). | **imports from old `root.a102`**: `library.private_policy_call`, `library.report_fact_assembly`, `runtime`×2; **old-runner callbacks defined**: `finish`; **old runtime**: `form_with_facts`, `_json`×2, `json`, `Record`×2; **self.workflow**: `binding_context`, `episode_bindings`, `facts`, `journal`×2, `pending_handles`, `release`×2, `source_credit_view`; **journal/receipt tables**: `runtime_forms`×2 |
| `source_contracts.py` | 38 | Its constants: role list of the seven literature roles, assignment fragments (window, table, page), the access tools (state query, source read/locate/sequence/experimental records, image view, archive, xlsx, pdf, `execution.estimate`), the acquisition tools (public literature search/read/sequence identity, NCBI search, PMC versions/files/asset, experiment-database tools), the read tools, `literature.structure.populate`. | **imports from old `root.a102`**: `a102_literature_bindings`, `communication`, `composition_information`, `domain`, `episode_bindings`, `experimental_database_acquisition` |
| `source_interpretation.py` | 43 | A reasoning commit may carry a `source_lead` when the task kind is `verified_source_leads`; the lead's witness window is read-checked and validated with the commit. | **BindingContext fields**: `assignment`, `episode_id`, `run_id`, `scope`; **imports from old `root.a102`**: `literature_contract_error`, `literature_task_credit`×3; **old-runner callbacks defined**: `execute_reasoning`, `reasoning_action_schema`, `reasoning_has_task_content`; **self.services**: `workflow`; **self.workflow**: `store`; **old support classes**: `ExperimentalContractError`×2 |
| `source_operations.py` | 94 | Its tools: the access and acquisition tools from the services catalog, NCBI search limited to `pubmed`, `execution.estimate` only for xlsx sheets/rows, and `literature.structure.populate` with structure population; argument checks; page confinement (reading outside an assigned page source is refused); text-witness inputs materialised for population. | **BindingContext fields**: `assignment`, `received_record_refs`, `role`×2, `scope`×6; **imports from old `root.a102`**: `composition_information`, `library.literature_assay_inputs`, `literature_contract_error`; **old-runner callbacks defined**: `catalog`, `execute`; **self.services**: `execute_tool`, `tool_catalog`; **old support classes**: `ExperimentalContractError`×2 |
| `source_references.py` | 35 | Scope checks for references, choice of artifact by representation, ancestry check that a source lies within an assigned root source, reference resolution. | **BindingContext fields**: `role`; **old-runner callbacks defined**: `resolve`; **self.services**: `read_record`, `reference_in_scope` |
| `structural_sheet_operations.py` | 17 | Access to the structure-sheet repository and the population route (when structure population is on). | **imports from old `root.a102`**: `a102_literature_bindings`, `literature_structure_storage`; **old-runner callbacks defined**: `literature_structure_repository`; **self.services**: `workflow`×2; **self.workflow**: `run_id`, `store`; **old support classes**: `LiteratureStructureRepository`×2 |
| `task.py` | 269 | The decision loop (old runner) with child delivery resolution, ready owned children, reasoning commits with lead content, job-child failure feedback; report grain name `literature_strategy`. | **imports from old `root.a102`**: `episode_source_failure`, `library.action_contracts`, `library.private_policy_call`, `providers`, `read_mapping`, `runtime`×2; **old binding attributes**: `instruction_composer`; **old-runner callbacks defined**: `apply_response`, `execute`, `next`; **old runtime**: `AcquisitionError`×2, `ActionFailure`, `ContractError`, `ContractInformationError`, `_decode_recorded_action_response`, `Draft202012Validator`×3, `EventTargetError`×2, `FACT_MEANINGS`, `FACT_SOURCES`, `inspect`, `_json`×5, `json`×10, `Mapping`×6, `nullcontext`×5, `observes_action_outcome`, `_plain`×2, `_references_in`, `ReportBoundaryError`, `ReportRedelivery`×2, `schema_failure_diagnostic`, `SourceEnd`×2, `sqlite3`×2, `subprocess`×2, `validate_form`, `ValidationError`×3, `_wait_target_feedback`×2, `WorkflowError`×2; **self.workflow**: `action_schema`, `annotation_context`, `automatic_score_updates`, `binding_context`×3, `catalog`, `completed_unit`×3, `completions`×3, `controller_binding`, `controller_value`×2, `decision_exchanges`×3, `delivery_resolution_inputs`, `delivery_status`, `execute`, `execution_binding`×7, `extra_report_sources`, `inprocess_replay`×4, `is_scientific_source`, `job_episode_options`, `journal`×10, `knowledge`, `last_observed_credit`, `local_outcome_preview`, `next_return`, `pending_work`×2, `perform_selected_wait`, `permits_common_action`, `reasoning_action_schema`, `receipt_projection`, `receive_native_outcome`, `receive_outcome`, `resolve_pending_deliveries`, `resolver`, `retain_shared_grading_results`, `run_id`×4, `selected`×3, `source_credit_binding`, `source_credit_view`×2, `specialist`×3, `store`×12, `store.reference_subset`, `tools`, `tools.model_contract_catalog`, `validate_report`, `working_state`; **journal/receipt tables**: `runtime_actions`×10, `runtime_episodes`, `runtime_model_calls`×2 |
| `task_instructions.py` | 26 | Instruction composer: default or job instructions plus this goal, the reasoning-commit requirement, tool knowledge, launch instructions, the pending-child redelivery paragraph, wait and native-event paragraphs when wait is allowed, exchange-history wording. | **imports from old `root.a102`**: `runtime_prompt`×2; **old-runner callbacks defined**: `compose_instructions`; **old runtime_prompt**: `DECISION_EXCHANGE_PROTOCOL`, `INSTRUCTIONS`×4, `REASONING_COMMIT_REQUIREMENT`; **self.workflow**: `binding_context`, `decision_protocol`, `is_job_source`, `job_episodes`, `knowledge`, `launch_instructions`, `native_event_information`, `permits_common_action`×3, `specialist` |
| `task_state.py` | 108 | Per-episode decision state and restore/checkpoint; unfinished own actions of kind `tool` or `reason`. | **imports from old `root.a102`**: `episode_source_failure`, `runtime`×2; **old-runner callbacks defined**: `bind_execution_context`, `checkpoint`, `record_effect`, `record_execution_failure`, `restore`, `restore_checkpoint`; **old runtime**: `ActionLeaf`, `EFFECT_VERSION`, `Episode`, `interpretation_schema`, `_json`×2, `json`×4, `_object`, `_plain`, `Record`; **self.workflow**: `archive`, `completions`×4, `context`, `controller_value`, `execution_binding`×4, `grains`, `inprocess_replay`×7, `journal`×5, `progress_provider`×2, `recover_commissions`, `run_id`, `source_credit_view`, `store`×2; **journal/receipt tables**: `runtime_actions`×5 |
| `task_waiting.py` | 9 | Records the suspension condition and passes it to the external executor. | **old-runner callbacks defined**: `suspension_changed`; **self.workflow**: `execution_backend`, `execution_handle`×2 |
| `to_child_source_relevance_assessment.py` | 29 | Building the search child's request: child goal refining its own, message with scope, initial report, report-contract declaration, job and episode assignments, structural-homology context and knowledge inheritance. Nothing specific to the child beyond the call. | **imports from old `root.a102`**: `runtime`×2; **old-runner callbacks defined**: `assemble_request`; **old runtime**: `ContractInformationError`, `Episode`×2, `EpisodeGoal`×2, `EpisodeRequest`, `_plain`×3, `Record`, `validate_saved_fact_form`; **self.workflow**: `context`×2, `grains`×2, `inprocess_completion_order`×2, `launch_instructions`, `receipts`×2 |
| `to_parent.py` | 41 | Report facts: screening answers when the task's answer kind is `screening`; lead dispositions when the task kind is `verified_source_leads`; with structure population, structure cells from committed and received sources; a report must pass assignment, form and received-report checks. | **BindingContext fields**: `assignment`×4, `received_record_refs`, `role`×2, `scope`; **imports from old `root.a102`**: `a102_literature_bindings`, `literature_task_credit`×2; **old-runner callbacks defined**: `current_report_facts`, `facts`, `fact_sources`, `validate_report`; **self.services**: `read_record`, `workflow`×2; **self.workflow**: `store`×2 |
| `waiting.py` | 8 | It does not support waiting (`supports_wait` is false). | **old-runner callbacks defined**: `supports_wait` |
| `yield_estimator.py` | 22 | Continuation: without the private binding none of its own; with it, the declaration keyed by the commissioned literature task (`continuation_task`) builds the old literature yield controller; a missing declaration raises. | **BindingContext fields**: `role`×2; **imports from old `root.a102`**: `literature_task_credit`×2; **old-runner callbacks defined**: `continuation_task`, `yield_controller`; **old yield names**: `_private_yield_controller`×2 |
