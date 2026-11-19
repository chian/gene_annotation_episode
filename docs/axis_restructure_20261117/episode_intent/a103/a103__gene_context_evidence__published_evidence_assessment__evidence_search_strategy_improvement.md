# a103/gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/`
(35 files directly in the folder; no `grading/` or `scoring/` subfolder). The child folder
`source_relevance_assessment/` was not read. Nothing from the old shared root was read.

Old binding: class `LiteratureEpisode`,
`binding_path = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'`,
`commissioning_parent = 'gene_context_evidence/published_evidence_assessment'`, role `literature_strategy`,
no entry roles, version `literature_episode_binding_v1`. Decision source: `SourceInvestigationTask`.
Prompt renderer: `render_receiver_prompt`.

## What this episode is for

It works out which literature search approach is productive for the parent's question. In its own words
(`goal.py`):

> For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene
> identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their
> source and scope.
>
> Investigate which search approach is productive. Keep the information objective and evidence context
> separate from a literal provider query. Revise terms or source choices in light of actual search/read
> outcomes; a search child can investigate which returned sources deserve examination.

## Task and instructions

Same as its parent `published_evidence_assessment`. Common actions are `tool`, `child` and
`redeliver_report`. There is no `reason` (raises `a103_literature_reasoning_not_commissioned`) and no
`wait`. The general `INSTRUCTIONS` come first, with the goal above appended and the same extra
paragraphs (`task_instructions.py`, identical text).

## What it reads from its parent's assignment

`from_parent.py`: form `{version: 'strategy_assignment_v1', question_context_refs: [ref], prior_search_refs: [ref]}`.
Every `*_refs` reference must be in scope. `prior_search_refs` must be in namespace `source`, while
`question_context_refs` may be in any namespace. `operation_key` must be non-empty. It also reads
`initial_report`, the report contract, `job_assignment`, `episode_assignment.launch_instructions` and the
scope.

## Children

| Old role | Child episode | Sent | Taken back |
|---|---|---|---|
| `literature_search` | `source_relevance_assessment` | `to_child_source_relevance_assessment.py`: the same envelope as the parent's assembler: goal; message `{scope, initial_report}` with optional `inprocess_completion_order`, `report_contract_declaration`, `job_assignment`, `episode_assignment`, `gene_context_evidence`, `knowledge_inheritance`. The child's assignment form is defined by that child (not read here). | `from_child_source_relevance_assessment.py`: the admitted typed form, with recorded admission refs, progress-provider hand-off, form and received-form references, native timing receipts, receipts and tool attributions (identical text to the parent's receiver). |

## Decision state and what it shows the model

Identical to the parent (`task_state.py`, `decision_state.py`, `decision_inputs.py` with grain
`literature_strategy`, `task_presentation*.py`). The binding block (`internal_summary.py`) is the same
code. It reads `assignment.get('source_refs', [])`, but the strategy form carries `prior_search_refs`, so
`literature_source_custody` is always empty and the prior search sources are not described. This is a
defect in the copy. The carry-over should show the custody of `prior_search_refs`.

## Tools it offers

Same as the parent (`source_operations.py` identical apart from the role): the access and acquisition
tools listed there, `public.ncbi.search` limited to `pubmed`, `execution.estimate` limited to xlsx, and
the received-record restriction for `source.locate` and `source.sequence.*` / `source.experimental.records`.

## How its credit is counted

Credit kind `scientific`, delegated to `services.scientific_credit`. Credit is measured after every
observed outcome and enters the iterator.

## Continuation

`continuation_task` and `yield_controller` return `None`. There is no private estimator, and the old
runner's recorded controller decided continuation.

## What it reports to its parent

No own fact sources. It fills the parent's typed form from the report values (validated by
`to_parent.py`) and saves it once (`report_delivery.py`).

## Differences from its parent and siblings

Byte-identical to `published_evidence_assessment` except for the role string, the assignment version
and field (`strategy_assignment_v1`/`prior_search_refs` instead of
`literature_assignment_v1`/`source_refs`), the one child (`literature_search` instead of
`literature_strategy`), the binding id and parent, `entry_roles = ()`, and no `create_binding_tree`. The
shared `source_contracts.py` copy still carries the instructions for all seven literature roles.

## Files

Names: `self.workflow.<m>` = old runner member; `runtime.<x>` = `_live_original_runtime.<x>` (old `root.a103.runtime`); `import:root.a103.<m>` = import from the old shared root; `table:<t>` = old journal/receipt table; `yield:<n>` = old yield name; `BindingContext.<f>` = old binding-context field; `services.<m>` = old binding services callback. Every row is also in `runs/carry_over/calls/a103_06.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names (uses) |
|---|---|---|---|
| `action_policy.py` | 16 | `_role` guard over the seven literature roles; permitted common actions `tool`, `child`, `redeliver_report` (no `reason`, no `wait`) | `BindingContext.role`×1 |
| `binding_record.py` | 8 | binding id `gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement`, `outcome_page_size` | none |
| `call.py` | 79 | one decision call: saved-request reuse, contract-information profile, literature numerical contract freeze, exchange protocol dispatch, history restore on fresh session | `import:root.a103.runtime`×2, `runtime._action_generation_schema`×1, `runtime._ASSIGNMENT_TRANSPORT`×1, `runtime.DECISION_EXCHANGE_PROTOCOL`×5, `runtime._digest`×1, `runtime.instructional_model_context`×1, `runtime._json`×4, `runtime.json`×2, `runtime._recorded_assignment_transport`×1, `runtime.WorkflowError`×5, `self.workflow.contract_information_profile`×1, `self.workflow.decision_exchanges`×1, `self.workflow.decision_protocol`×3, `self.workflow.freeze_contract_information`×1, `self.workflow.freeze_literature_numerical_contracts`×1, `self.workflow.history_preview`×1, `self.workflow.journal`×1, `self.workflow.numerical_contracts`×1, `self.workflow.provider`×1, `self.workflow.provider.has_session`×1, `self.workflow.receipts`×4, `self.workflow.services`×1, `self.workflow.uses_received_record_context`×2, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls`×5 |
| `child_commissioning.py` | 24 | children = `_CHILDREN['literature_strategy']` = (`literature_search`); request assembler and report receiver for that child | none |
| `configuration.py` | 16 | only setting `outcome_page_size` (default 8, positive int); no contract-information profile | none |
| `credit.py` | 16 | credit kind `scientific`; credit view delegated to `services.scientific_credit`; `credit_projector` returns `None` | `services.scientific_credit`×1 |
| `decision_contracts.py` | 35 | exchange envelope schema (`request_context` or `select_action`) and its validation | `import:root.a103.runtime`×2, `runtime.composition_lookup_schema`×2, `runtime.Draft202012Validator`×1, `runtime._object`×3 |
| `decision_exchange.py` | 115 | pending-decision lookup loop: child options, composition information, own-attempt lookups; yield table for the model | `import:root.a103.runtime`×2, `runtime._action_generation_schema`×1, `runtime._category_yield_parameters`×1, `runtime.child_option_information`×1, `runtime.DECISION_CONTEXT_VERSION`×1, `runtime.instructional_model_context`×2, `runtime._json`×2, `runtime.lookup_attempts`×1, `runtime.Mapping`×3, `runtime.model_snapshot`×1, `runtime._plain`×2, `runtime._references_in`×1, `runtime.requested_contract_information`×1, `runtime.schema_failure_diagnostic`×2, `runtime.sqlite3`×1, `runtime.state_frame`×1, `runtime.ValidationError`×4, `runtime.yield_table`×1, `self.workflow.controller_binding`×1, `self.workflow.decision_exchanges`×1, `self.workflow.execute`×1, `self.workflow.journal`×1, `self.workflow.run_id`×1, `self.workflow.services`×1, `self.workflow.store`×2, `self.workflow.store.reference_subset`×1, `self.workflow.validate_contract_information`×1, `table:runtime_model_calls`×2 |
| `decision_inputs.py` | 65 | context additions: resource, shared information, launch library, child options, initial binding context, completed action reports, HPC history, pending work, execution expectations (grain `literature_strategy`), resource/native estimates, native event targets, profile | `import:root.a103.episode_work_report`×2, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×2, `runtime.child_option_information`×1, `runtime.Mapping`×1, `self.workflow.available_child_roles`×1, `self.workflow.binding_context`×2, `self.workflow.episode_bindings`×1, `self.workflow.execution_expectations`×1, `self.workflow.job_episodes`×2, `self.workflow.launch_instructions`×2, `self.workflow.native_estimation_context`×1, `self.workflow.native_event_information`×2, `self.workflow.pending_work`×1, `self.workflow.resource_context`×1, `self.workflow.resource_estimator`×4, `self.workflow.shared_information_context`×1, `self.workflow.store`×2 |
| `decision_provider.py` | 17 | provider dispatch with this episode's prompt renderer; conversation key | `import:root.a103.runtime`×1, `self.workflow.provider`×2, `self.workflow.provider.conversation_key`×1, `self.workflow.specialist`×1 |
| `decision_state.py` | 48 | model inputs: goal, scope, working state, visible refs, credit, evidence vector, controller state (annotation-axis mode trimmed), image.view visual evidence, annotation context, binding block, `_completed_work_axis_results`, available report facts | `import:root.a103.runtime`×2, `runtime.FACT_MEANINGS`×1, `runtime.FACT_SOURCES`×1, `runtime.json`×2, `runtime.Mapping`×3, `runtime._plain`×2, `runtime._references_in`×1, `self.workflow.annotation_context`×1, `self.workflow.binding_context`×1, `self.workflow.catalog`×1, `self.workflow.controller_binding`×1, `self.workflow.delivery_status`×1, `self.workflow.extra_report_sources`×1, `self.workflow.job_episode_options`×1, `self.workflow.journal`×3, `self.workflow.knowledge`×1, `self.workflow.local_outcome_preview`×1, `self.workflow.pending_work`×1, `self.workflow.receipt_projection`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_binding`×1, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×3, `self.workflow.store.reference_subset`×1, `self.workflow.tools`×1, `self.workflow.tools.model_contract_catalog`×1, `self.workflow.working_state`×1, `table:runtime_actions`×2 |
| `episode.py` | 35 | `LiteratureEpisode`; `commissioning_parent='gene_context_evidence/published_evidence_assessment'`, role `literature_strategy`, no entry roles; no `create_binding_tree` | none |
| `from_child_source_relevance_assessment.py` | 45 | receives the `literature_search` child's typed form (same text as the parent's receiver) | `import:root.a103.delivery_counterpart`×1, `import:root.a103.episode_return_records`×1, `import:root.a103.runtime`×2, `runtime._json`×1, `runtime.json`×1, `runtime._references_in`×1, `runtime.WorkflowError`×1, `self.workflow.binding_context`×4, `self.workflow.episode_bindings`×1, `self.workflow.is_job_source`×2, `self.workflow.job_episodes`×2, `self.workflow.native_timing_information`×1, `self.workflow.progress_provider`×4, `self.workflow.receipts`×3, `self.workflow.receive_tool_attributions`×1, `self.workflow.run_id`×6, `self.workflow.specialist`×1, `self.workflow.store`×7, `table:runtime_report_attempts`×2 |
| `from_parent.py` | 34 | assignment form `strategy_assignment_v1` {`question_context_refs`, `prior_search_refs`}; every `*_refs` must be in scope (`prior_search_refs` in namespace `source`); non-empty `operation_key` required | none |
| `goal.py` | 9 | the same A103 prefix + `_ROLE_INSTRUCTIONS['literature_strategy']` | none |
| `__init__.py` | 0 | empty package marker | none |
| `internal_summary.py` | 17 | same block as the parent, but it reads `source_refs`, which the strategy form does not carry, so `literature_source_custody` is always empty | `BindingContext.assignment`×1, `BindingContext.episode_id`×1, `BindingContext.scope`×2, `services.own_outcomes`×1 |
| `received_evidence.py` | 20 | receives no report sources/facts/tokens from children (all empty) | none |
| `report_delivery.py` | 25 | finish: without a report contract returns credit + pending handles + current facts; with one, builds the form from report values + assembled facts once and saves it | `import:root.a103.library.private_policy_call`×1, `import:root.a103.library.report_fact_assembly`×1, `import:root.a103.runtime`×2, `runtime.form_with_facts`×1, `runtime._json`×2, `runtime.json`×1, `runtime.Record`×2, `self.workflow.binding_context`×1, `self.workflow.episode_bindings`×1, `self.workflow.facts`×1, `self.workflow.journal`×2, `self.workflow.pending_handles`×1, `self.workflow.release`×2, `self.workflow.source_credit_view`×1, `table:runtime_forms`×2 |
| `saved_decision_exchange.py` | 81 | authenticates saved exchange requests/history against frozen contract information | `import:root.a103.runtime`×2, `runtime.apply_state_frame`×1, `runtime.CONTRACT_INFORMATION_OPERATIONS`×1, `runtime.DECISION_CONTEXT_VERSION`×1, `runtime.instructional_model_context`×1, `runtime.is_contract_information`×1, `runtime._json`×8, `runtime.json`×1, `runtime.model_snapshot`×1, `runtime._recorded_action_generation_schema`×1, `runtime.requested_contract_information`×1, `runtime.ValidationError`×1, `runtime.WorkflowError`×9, `self.workflow.contract_information_reply`×1, `self.workflow.decision_exchanges`×2, `self.workflow.journal`×1, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls`×1 |
| `scientific_records.py` | 11 | no automatic score judgments; completing one raises `a103_automatic_judgment_unavailable` | none |
| `source_contracts.py` | 26 | shared constants of the literature family as copied into this folder: `VERSION='literature_episode_binding_v1'`, the seven literature `ROLES`, the `_CHILDREN` chain, `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, `_READ_TOOLS`, and all seven `_ROLE_INSTRUCTIONS` texts (this episode uses the `literature` one) | `import:root.a103.communication`×1, `import:root.a103.composition_information`×1, `import:root.a103.domain`×1, `import:root.a103.episode_bindings`×1 |
| `source_interpretation.py` | 14 | no reasoning action: schema `None`, executing reasoning raises `a103_literature_reasoning_not_commissioned` | none |
| `source_operations.py` | 44 | tool catalog: `_ACCESS_TOOLS` + `_ACQUISITION_TOOLS` from the scoped catalog; `public.ncbi.search` restricted to `pubmed`; `execution.estimate` kept only for `source.xlsx.*`; source-location inputs; `source.locate`/`source.sequence.*`/`source.experimental.records` limited to received records | `BindingContext.assignment`×1, `BindingContext.received_record_refs`×1, `BindingContext.scope`×3, `services.execute_tool`×1, `services.tool_catalog`×1 |
| `source_references.py` | 14 | `_require` (in scope or `literature_reference_unavailable`), `resolve` via `reference_in_context` | `BindingContext.role`×1, `services.read_record`×1, `services.reference_in_scope`×1 |
| `task_instructions.py` | 26 | the long general investigation `INSTRUCTIONS`, `REASONING_COMMIT_REQUIREMENT`, and the composer (binding text appended, tool knowledge, launch library, pending-delivery, wait and native-event paragraphs, exchange-protocol history replacement) | `self.workflow.binding_context`×1, `self.workflow.decision_protocol`×1, `self.workflow.is_job_source`×1, `self.workflow.job_episodes`×1, `self.workflow.knowledge`×1, `self.workflow.launch_instructions`×1, `self.workflow.native_event_information`×1, `self.workflow.permits_common_action`×3, `self.workflow.specialist`×1 |
| `task_presentation_policy.py` | 69 | chooses the renderer (HPC, published scientific, API launch, selected execution, monitor, receiver) and keeps per-episode prompt state across decision frames; JSON fallback | `import:root.a103.decision_context`×1, `import:root.a103.execution_prompt`×1, `import:root.a103.gene_context_evidence_prompt`×2, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.library.monitor_prompt`×1, `import:root.a103.native_profile_presentation`×1 |
| `task_presentation.py` | 171 | text prompt: TASK (instructions, assigned work, fixed scope, constraints, parent context/evidence, supplied material, callable Sources table, evidence-axis/thought-pattern/tool guidance, launch manuals, operations and operands, permitted children, child options, requested return, selection operands) + episode steering | `import:root.a103.gene_context_evidence_prompt`×1 |
| `task.py` | 199 | decision loop: replay/restore, model call, admission (`selected`), report-update admission with grain `literature_strategy`, action execution (reason/wait/tool), outcome receipt, automatic scoring, credit after every observed outcome, shared grading retention on `shared.read_information` | `import:root.a103.episode_source_failure`×1, `import:root.a103.library.action_contracts`×1, `import:root.a103.library.private_policy_call`×1, `import:root.a103.providers`×1, `import:root.a103.runtime`×2, `runtime.ActionFailure`×1, `runtime.ContractInformationError`×1, `runtime._decode_recorded_action_response`×1, `runtime.Draft202012Validator`×2, `runtime.EventTargetError`×2, `runtime.inspect`×1, `runtime._json`×5, `runtime.json`×8, `runtime.Mapping`×2, `runtime.nullcontext`×5, `runtime.observes_action_outcome`×1, `runtime.ReportBoundaryError`×1, `runtime.ReportRedelivery`×2, `runtime.schema_failure_diagnostic`×1, `runtime.SourceEnd`×2, `runtime.validate_form`×1, `runtime.ValidationError`×2, `runtime._wait_target_feedback`×2, `runtime.WorkflowError`×2, `self.workflow.action_schema`×1, `self.workflow.automatic_score_updates`×1, `self.workflow.binding_context`×1, `self.workflow.completed_unit`×3, `self.workflow.completions`×3, `self.workflow.controller_value`×2, `self.workflow.decision_exchanges`×3, `self.workflow.delivery_resolution_inputs`×1, `self.workflow.execute`×1, `self.workflow.execution_binding`×7, `self.workflow.inprocess_replay`×4, `self.workflow.journal`×7, `self.workflow.last_observed_credit`×1, `self.workflow.next_return`×1, `self.workflow.pending_work`×1, `self.workflow.perform_selected_wait`×1, `self.workflow.receive_native_outcome`×1, `self.workflow.receive_outcome`×1, `self.workflow.resolve_pending_deliveries`×1, `self.workflow.resolver`×1, `self.workflow.retain_shared_grading_results`×1, `self.workflow.run_id`×3, `self.workflow.selected`×3, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×8, `self.workflow.validate_report`×1, `table:runtime_actions`×8, `table:runtime_episodes`×1, `table:runtime_model_calls`×2 |
| `task_state.py` | 108 | source state: calls, feedback, last outcome, report values (from `initial_report`) and basis; failure recording that still enters the iterator with credit; restore/checkpoint | `import:root.a103.episode_source_failure`×1, `import:root.a103.runtime`×2, `runtime.ActionLeaf`×1, `runtime.EFFECT_VERSION`×1, `runtime.Episode`×1, `runtime.interpretation_schema`×1, `runtime._json`×2, `runtime.json`×4, `runtime._object`×1, `runtime._plain`×1, `runtime.Record`×1, `self.workflow.archive`×1, `self.workflow.completions`×4, `self.workflow.context`×1, `self.workflow.controller_value`×1, `self.workflow.execution_binding`×4, `self.workflow.grains`×1, `self.workflow.inprocess_replay`×7, `self.workflow.journal`×5, `self.workflow.progress_provider`×2, `self.workflow.recover_commissions`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_view`×1, `self.workflow.store`×2, `table:runtime_actions`×5 |
| `task_suspension.py` | 9 | records suspension condition on the execution handle | `self.workflow.execution_backend`×1, `self.workflow.execution_handle`×2 |
| `to_child_source_relevance_assessment.py` | 32 | assembles the `literature_search` child request (same text as the parent's assembler) | `import:root.a103.episode_contract_information`×1, `import:root.a103.runtime`×2, `runtime.ContractInformationError`×1, `runtime.Episode`×2, `runtime.EpisodeGoal`×2, `runtime.EpisodeRequest`×1, `runtime._plain`×3, `runtime.Record`×1, `runtime.validate_saved_fact_form`×1, `self.workflow.context`×2, `self.workflow.grains`×2, `self.workflow.inprocess_completion_order`×2, `self.workflow.launch_instructions`×1, `self.workflow.receipts`×2 |
| `to_parent.py` | 21 | no own fact sources (`fact_sources`/`facts`/`current_report_facts` return `{}`); report validated against the parent's form with this episode's resolver, then `validate_received_report` | `BindingContext.assignment`×1, `BindingContext.scope`×1 |
| `waiting.py` | 8 | `supports_wait = False` | none |
| `yield_estimator.py` | 12 | `continuation_task` and `yield_controller` both return `None` (no private continuation; the runner's recorded controller decides) | none |
