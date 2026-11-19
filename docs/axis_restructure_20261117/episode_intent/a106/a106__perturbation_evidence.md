# a106/perturbation_evidence — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/<file>` (only the
files directly in this folder; it has no `grading/` or `scoring/`; child folders and `tests/` are not covered).
Old binding class `PerturbationEvidenceEpisode` (`binding_path = 'perturbation_evidence'`, `commissioning_parent =
'legacy_annotation'`, `roles = entry_roles = ('perturbation_evidence',)`), decision source
`ScientificInvestigationTask`. Contract version `perturbation_evidence_episode_v10`, axis `A106`.

## What it is for (its goal, in its own words)

`goal.py` `instructions()` returns one of two texts, chosen by the selected evidence-axis entry's `entry_version`:

- **published instruction entry** (`entry_version == INSTRUCTION_VERSION`): "Determine what the supplied target does
  within the parent's assigned question, scope and constraints. Start with the supplied sequence, selected file
  contents or snippets, preserving their boundaries, completeness and known context. No initial candidate annotation
  or publicly searchable name is required. Possible functions can emerge from the evidence and be compared or
  revised. ... Selected instructions describe how to investigate; they are not evidence about this target. Preserve
  the measured subject, conditions, controls, native measurements, uncertainty and limits of inference ... Choose an
  available tool action, commit a scientific interpretation through the reasoning action, commission a scoped child
  with its own typed return form, or wait for selected pending work ... Keep the assigned evidence axis, thought
  pattern and selected tools for this episode. process.revise prepares a different thought pattern and/or tool
  selection for a new child; it does not change this episode or start that child ... The configured controller owns
  continuation. Waiting and unchanged observations do not manufacture progress."
- **evidence-axis entry** (otherwise): "Investigate the parent's assigned scientific problem iteratively in the shared
  Episode loop. The selected scientific support proposition and operands define the support problem; the thought
  pattern supplies alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable
  contracts ... Library sources are instruction provenance, not scientific evidence about this target ...
  annotation_support_routes describes the actual separately bound annotation policy's kind dispatch ... Metadata
  itself earns no credit and never replaces or filters the actual projectors, annotation formula or continuation rule
  ... Request the recorded perturbation_evidence_results source in child forms when their process relationships and
  existing closed credit/yield are needed for steering. Only retrieved actual tools are available ... The configured
  controller owns continuation."

`configuration.py` sets `replaces_default_instructions` when every evidence-axis header in the library is an
instruction entry: then the goal text replaces the general INSTRUCTIONS; otherwise it is appended.

## Task and instructions

`task_instructions.py` composes: `INSTRUCTIONS` (imported from the old shared `library/literature_investigation_prompt`,
not an own copy — unlike the launch child which carries its own inline copy) + goal (replace/append) +
`REASONING_COMMIT_REQUIREMENT` when reason is permitted + tool-knowledge instructions + launch-instruction library
instructions + pending_child_delivery repair text + pending_child_ wait text + native_event_targets text (when the
old runner had native event information) + exchange-protocol replacement of the history paragraph.

`task.py` / `task_decision.py` / `task_state.py` (class `ScientificInvestigationTask`): one model decision per unit,
response = `{selection, report_update}`. Reason actions are validated against the reasoning envelope; an all-empty
commit is rejected (`empty_reasoning_commit`) unless `evidence_processing.kind == no_applicable_evidence` or the
binding says the reasoning has task content; rejections create no executed action. A `job_child` selection that
fails in storage/control yields `job_assignment` feedback. Execution: reason -> binding `execute_reasoning` or
`store.commit_reasoning`; wait -> selected wait; tool -> Workflow execute. After an observed outcome: receive native
outcome, receive outcome, automatic score updates (non-wait), credit = projected credit (wait: last observed credit),
retain shared grading results after `shared.read_information`. A failed execution is recorded as a failed outcome and
still enters the iterator with its credit (`record_execution_failure`). Decision exchange protocol lets the model ask
`request_context` lookups (child_options, composition_information, own attempts) before selecting.

## What it reads from its parent's assignment

`scientific_contracts._ASSIGNMENT` (required `selection`, `evidence_refs`, `constraints`, `context`):
- `selection` {version, `evidence_axis` option ref (option_id const `A106`), `thought_pattern` option ref (P#),
  `child_tool_info` [{name, resources api|local|hpc}]}; stored canonical with description+instructions resolved;
- `proposed_annotation_ref` (required when the annotation task is required; must be in scope and received by parent;
  a child inherits it and may not change it);
- `evidence_refs` (each must be in scope); `constraints`; `context.evidence_task` {evidence_axis_task_v1,
  whole_axis_findings, A106, credit_unit > 0}; optional `revision_origin` (from a process.revise preparation, checked
  against the recorded preparation).
Invocation: objective, purpose, closed report_schema (site/restriction projections checked), initial_report.
`initial_references` = evidence_refs + proposed_annotation_ref.

## Children it may commission

`episode.py` child roles come from configuration (`child_roles`, must include `perturbation_evidence`); routes:

| role | child binding | sent (to_child_*) | taken back (from_child_*) |
|---|---|---|---|
| `perturbation_evidence` (recursive) | itself | `prepare_invocation`: assignment as above (+ inherited proposed_annotation_ref, optional revision_origin), objective, purpose, report_schema, initial_report; filled `perturbation_evidence` mechanics record (selection, assignment/invocation digests, binding record); closed-commission replay | typed form; required return sources `perturbation_evidence_results` + `committed_record_refs` (first level) or `committed_record_refs` (deeper) when annotation task required |
| `literature` | `published_evidence_assessment` | scope, schema, initial report, assignment via child `prepare_assignment` | typed form, references received |
| `launch` | `execution_job_submission` | launch assignment (`execution_launch_assignment_v1`), scope, typed form; an HPC launch form must include `execution_handoff_refs` | typed form incl. `execution_handoff_refs` |
| `monitor` | `execution_progress_assessment` | `monitor_assignment_v1` (target_handle, requested_fields, known_progress_refs, permitted record types) | `monitoring_progress_refs` admitted into the progress provider (`receive_progress`); required when annotation task required |
| `results` | `execution_result_acquisition` | results assignment (`execution_results_assignment_v1`: handoff_ref, selector) | typed form incl. acquired results |

## Decision state and what it shows the model

Root (path length 1 or saved annotation_axis_credit) uses `standalone_credit_presentation`; commissioned uses
`commissioned_credit_presentation`. Shown: goal, scope, working_state, visible_record_refs, current_credit,
current_evidence_vector, investigation_progress (retained_finding_count, inactive_dependencies, detail_pages),
credit_binding, time_accounting, pending_work, last_local_outcome + feedback, visual_evidence (latest completed
`image.view`), report_deliveries, controller + controller_binding, tools, tool_knowledge, available_report_facts,
requested purpose/form, current_report_update + basis refs, report_lifecycle, annotation_context, monitoring
information credit, the binding's `decision_context` (`internal_summary.py`: selection, evidence-axis view,
annotation_support_routes, thought pattern fields, child_tool_info, assignment, permitted_children),
completed_action_reports. At root in annotation_axis_credit mode: controller arms/annotation_credits/root_score,
proposed_annotations and annotation_comparisons, and the a101–a104 sheets in completed work. `decision_inputs.py`
adds resource_context, shared_information_context, launch instruction library, child_options, initial binding
context, execution_expectations, resource_tool_estimates, native_execution_expectations, waiting_support,
contract_information_profile.

## Tools it offers

Common tools (`_COMMON_TOOLS`): process.search/entry/sources/tools, knowledge.search/entry/read, episode.history,
episode.credit, episode.annotation_score, episode.monitoring_information, episode.estimate_wait,
shared.request_information/publish_information/resolve_information_need/read_information/list_information.
Own: the selected actual tools (direct invocation routes only), `process.revise`, `process.execution` (read-only
execution planning, scientific_credit 0). Resource tool contracts are read from its launch->launch_api and results
children. Common actions: tool, reason, child, wait, redeliver_report.

## How its credit is counted

Credit kind `scientific`. Projector `ScientificFindingProgress(FindingProgressPolicy(credit_unit))` from the
assignment's `context.evidence_task` (credit = retained A106 findings x credit_unit), only when the axis entry is an
instruction or evidence-axis entry. credit_view goes through `services.scientific_credit(_for)` with the assignment
(goal, scope, purpose, schema, initial_report, proposed_annotation_ref). Unbounded; no rescaling.

## Continuation

`yield_estimator.py`: task key `A106:whole_axis_findings`; declaration `yield_bindings[task]` {kind, cutoff,
parameters{uncertainty_alpha}, credit_definition}; credit_definition digest must equal the projector record and
`projector.yield_method` must equal kind. kind `accumulation` -> YieldController(cutoff); `bounded_quality` ->
BoundedYieldController(cutoff, projector.native_score_maximum); `completion` -> CompletionYieldController(cutoff).
Without yield_bindings the old runner's recorded controller was used.

## What it reports to its parent

Fact source `perturbation_evidence_results` (plus library/tool-library report sources): own closed process result
(version, invocation_ref, parent_invocation_ref, origin_kind ordinary_child|approach_revision, preparation ref,
selection, initial_credit, credit, credit_kind, credit_binding_ref, completed_actions, episode_yield,
proposed_annotation_ref) merged own-first with received child results (same invocation cannot change body).
`validate_report` requires those fields to equal the frozen closing facts. `finish` fills the typed form once
(unreported root: credit + pending_handles + report facts).

## Differences from siblings

Unlike its execution children it has a reason action, a science-library selection (axis/thought pattern/tools),
recursive self-children with approach revision, and finding-unit credit. The launch child has inline INSTRUCTIONS and
operational credit; the monitor has information credit and no reason action.

## File by file
| old file | lines | own intent | old-runner names (uses) |
|---|---|---|---|
| __init__.py | 0 | empty package marker | none |
| alternate_process_selection.py | 10 | process.revise: builds a new child selection keeping the original evidence axis, with a new thought_pattern and resolved child_tool_info | none |
| binding_record.py | 8 | as_record identity: version perturbation_evidence_episode_v10, binding_id, library/tool_library records, child_roles, optional tool_retrieval, contract_information_profile, yield_bindings | none |
| child_message_owners.py | 30 | routes the recursive perturbation_evidence->perturbation_evidence exchange to this episode's own to_child/from_child functions (identity checks only) | `import:runtime` x1, `workflow.episode_bindings` x1, `workflow.perturbation_evidence_binding` x1 |
| commissioned_credit_presentation.py | 60 | decision state for a commissioned (non-root) A106 episode: goal, scope, working_state, visible refs, current credit + axis components, investigation_progress, pending work, last outcome/feedback, visual_evidence (last image.view), deliveries, controller, tools, tool knowledge, report facts, requested form, current report; annotation_context; completed_action_reports; yield table from own journal | `bind_functions` x2, `binding_context` x1, `import:episode_work_report` x1, `import:library.live_runtime_functions` x1, `import:runtime` x3, `self.workflow.annotation_context` x1, `self.workflow.binding_context` x1, `self.workflow.catalog` x1, `self.workflow.controller_binding` x2, `self.workflow.delivery_status` x1, `self.workflow.extra_report_sources` x1, `self.workflow.is_scientific_source` x1, `self.workflow.journal` x2, `self.workflow.knowledge` x1, `self.workflow.local_outcome_preview` x1, `self.workflow.pending_work` x1, `self.workflow.receipt_projection` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_binding` x1, `self.workflow.source_credit_view` x1, `self.workflow.specialist` x1, `self.workflow.store` x3, `self.workflow.tools` x1, `self.workflow.working_state` x1, `table:runtime_actions` x1 |
| completion_snapshot.py | 4 | closing snapshot: initial_credit, credit, controller_credit, episode_yield, parent_invocation_ref | `services.scientific_parent_invocation` x1, `table:runtime_episodes` x1, `workflow.journal` x1, `workflow.services` x1, `workflow.source_controller_credit` x1 |
| configuration.py | 39 | construction: library, tool_library, child_roles (must include perturbation_evidence), replaces_default_instructions when every evidence-axis entry is an instruction entry, tool_retrieval, contract_information_profile, per-task yield_bindings validated against the three estimator kinds (accumulation, bounded_quality, completion) with uncertainty_alpha + cutoff + credit_definition | `import:composition_information` x1, `import:numerical` x1, `import:scientific_tool_retrieval` x1 |
| credit.py | 59 | credit kind 'scientific'; credit projector = ScientificFindingProgress(FindingProgressPolicy(credit_unit)) from assignment.context.evidence_task (evidence_axis_task_v1, whole_axis_findings, A106); requires proposed_annotation_ref when yield bindings present; credit_view via services.scientific_credit(_for) with assignment/purpose/schema/initial_report | `import:communication` x1, `import:domain` x1, `import:investigation_progress` x1, `services.annotation_task_required` x1, `services.proposed_annotation_for` x1, `services.scientific_credit` x1, `services.scientific_credit_for` x1, `services.workflow` x1, `workflow.projection_view` x1, `workflow.projector_receipt_arguments` x1, `workflow.scientific_projector_for_context` x1 |
| decision_inputs.py | 62 | adds to model context: resource_context, shared_information_context, launch_instruction_library + selected_launch_instructions, child_options, initial binding context, completed work, pending_work, execution_expectations, resource_tool_estimates (job/native), native_execution_expectations, waiting_support, contract_information_profile | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.available_child_roles` x1, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.execution_expectations` x1, `self.workflow.is_job_source` x1, `self.workflow.job_episodes` x2, `self.workflow.launch_instructions` x2, `self.workflow.native_estimation_context` x1, `self.workflow.pending_work` x1, `self.workflow.permits_common_action` x1, `self.workflow.resource_context` x1, `self.workflow.resource_estimator` x5, `self.workflow.shared_information_context` x1, `self.workflow.waiting_support` x1 |
| decision_state.py | 16 | chooses standalone presentation at root (path len 1 or saved annotation_axis_credit) else commissioned presentation | none |
| episode.py | 102 | binds the head: role perturbation_evidence, children literature/launch/monitor/results/perturbation_evidence (recursive), common actions tool/reason/child/wait/redeliver_report; maps each child role to its own to_child/from_child functions; monitor request goes through prepare_monitor_request; constructs the three execution bindings | `import:perturbation_evidence.execution_job_submission.api_job_execution.episode` x1, `import:perturbation_evidence.execution_job_submission.episode` x1, `import:perturbation_evidence.execution_result_acquisition.episode` x1, `services.workflow` x1 |
| execution_planning.py | 36 | process.execution tool: execution recipe for a selected tool/resource, resource context, age-weighted timing history per profile, HPC commissions; operational planning only, scientific_credit 0 | `import:execution_contracts` x1, `import:execution_memory` x1, `import:execution_planning` x1, `services.workflow` x1, `workflow.episode_bindings` x2, `workflow.resource_context` x1 |
| from_child_execution_job_submission.py | 81 | admits launch child's typed return (role launch, binding path perturbation_evidence/execution_job_submission), records receipts, progress forms, native timing receipts | `bind_functions` x2, `binding_context` x4, `import:delivery_counterpart` x2, `import:episode_return_records` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `table:runtime_actions` x1, `table:runtime_report_attempts` x3, `workflow.binding_context` x4, `workflow.episode_bindings` x2, `workflow.is_job_source` x2, `workflow.job_episodes` x2, `workflow.native_timing_information` x1, `workflow.progress_provider` x4, `workflow.receipts` x3, `workflow.run_id` x6, `self.delivery_feedback (Workflow)` x1, `self.journal (Workflow)` x1, `self.receive_form (Workflow)` x1, `self.run_id (Workflow)` x2, `self.save_attempt (Workflow)` x2, `self.store (Workflow)` x1, `workflow.specialist` x1, `workflow.store` x7 |
| from_child_execution_progress_assessment.py | 100 | receive_progress: admits episode_progress references from the monitor's typed form into the progress provider; plus same admit/receive for role monitor | `bind_functions` x2, `binding_context` x4, `import:communication` x1, `import:delivery_counterpart` x2, `import:domain` x1, `import:episode_return_records` x1, `import:library.live_runtime_functions` x1, `import:method_loop.durable` x1, `import:runtime` x2, `table:runtime_actions` x1, `table:runtime_report_attempts` x3, `workflow.binding_context` x4, `workflow.episode_bindings` x2, `workflow.is_job_source` x2, `workflow.job_episodes` x2, `workflow.native_timing_information` x1, `workflow.progress_provider` x4, `workflow.receipts` x3, `workflow.run_id` x6, `self.delivery_feedback (Workflow)` x1, `self.journal (Workflow)` x1, `self.receive_form (Workflow)` x1, `self.run_id (Workflow)` x2, `self.save_attempt (Workflow)` x2, `self.store (Workflow)` x1, `workflow.specialist` x1, `workflow.store` x7 |
| from_child_execution_result_acquisition.py | 81 | admits results child's typed return (role results) | `bind_functions` x2, `binding_context` x4, `import:delivery_counterpart` x2, `import:episode_return_records` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `table:runtime_actions` x1, `table:runtime_report_attempts` x3, `workflow.binding_context` x4, `workflow.episode_bindings` x2, `workflow.is_job_source` x2, `workflow.job_episodes` x2, `workflow.native_timing_information` x1, `workflow.progress_provider` x4, `workflow.receipts` x3, `workflow.run_id` x6, `self.delivery_feedback (Workflow)` x1, `self.journal (Workflow)` x1, `self.receive_form (Workflow)` x1, `self.run_id (Workflow)` x2, `self.save_attempt (Workflow)` x2, `self.store (Workflow)` x1, `workflow.specialist` x1, `workflow.store` x7 |
| from_child_perturbation_evidence.py | 94 | admits the recursive perturbation_evidence child's typed return (saved attempt reuse, receipts, progress, timing) | `binding_context` x4, `import:delivery_counterpart` x1, `import:episode_return_records` x1, `import:runtime` x1, `_runtime._digest` x1, `_runtime._json` x1, `_runtime.json` x5, `_runtime.Record` x2, `_runtime._references_in` x1, `_runtime.ReportBoundaryError` x1, `_runtime.ReportDeliveryError` x2, `_runtime.WorkflowError` x1, `table:runtime_actions` x1, `table:runtime_report_attempts` x3, `self.binding_context (Workflow)` x4, `self.delivery_feedback (Workflow)` x1, `self.episode_bindings (Workflow)` x1, `self.is_job_source (Workflow)` x2, `self.job_episodes (Workflow)` x2, `self.journal (Workflow)` x1, `self.native_timing_information (Workflow)` x1, `self.progress_provider (Workflow)` x4, `self.receipts (Workflow)` x3, `self.receive_form (Workflow)` x1, `self.run_id (Workflow)` x8, `self.save_attempt (Workflow)` x2, `self.specialist (Workflow)` x1, `self.store (Workflow)` x8 |
| from_child_published_evidence_assessment.py | 77 | admits the literature child's typed return | `bind_functions` x2, `binding_context` x4, `import:delivery_counterpart` x1, `import:episode_return_records` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `table:runtime_actions` x1, `table:runtime_report_attempts` x3, `workflow.binding_context` x4, `workflow.episode_bindings` x1, `workflow.is_job_source` x2, `workflow.job_episodes` x2, `workflow.native_timing_information` x1, `workflow.progress_provider` x4, `workflow.receipts` x3, `workflow.run_id` x6, `self.delivery_feedback (Workflow)` x1, `self.journal (Workflow)` x1, `self.receive_form (Workflow)` x1, `self.run_id (Workflow)` x2, `self.save_attempt (Workflow)` x2, `self.store (Workflow)` x1, `workflow.specialist` x1, `workflow.store` x7 |
| from_parent.py | 196 | assignment schema (selection{evidence_axis A106, thought_pattern, child_tool_info}, proposed_annotation_ref, evidence_refs, constraints, context.evidence_task, revision_origin); validates selection against library; invocation (objective, purpose, report_schema, initial_report) incl. site/restriction projections; prepare_invocation for recursive child incl. closed-commission replay; validate_context identity checks; initial_references = evidence_refs + proposed_annotation_ref | `import:episode_composition` x1, `import:episode_return_records` x1, `import:library.retained_input_authority.alignment_site_returns` x1, `import:library.retained_input_authority.restriction_mapping_returns` x1, `services.annotation_task_required` x2, `services.proposed_annotation_for` x1, `services.reference_in_scope` x2, `services.scientific_parent_preparation` x1, `services.scientific_preparation` x2, `services.scientific_saved_request` x2, `services.workflow` x1, `table:runtime_actions` x1, `workflow.journal` x1, `workflow.perturbation_evidence_binding` x1, `workflow.run_id` x1, `workflow.store` x1 |
| goal.py | 14 | the episode's goal text (two versions: instruction entry vs evidence-axis entry) | none |
| incoming_message_owners.py | 130 | routes the four nonrecursive child returns (launch, monitor, results, literature) to this episode's from_child admit_return (identity checks only) | none |
| internal_summary.py | 26 | decision_context: selection, initial_selection_sha256, evidence_axis view (instruction or evidence-axis), annotation_support_routes (non-instruction entry), thought_pattern fields, child_tool_info, assignment, permitted_children | `services.scientific_support_routes` x1 |
| process_state.py | 61 | restore_closed_process / restore_saved_process: authenticate a closed or saved request's mechanics identity on replay | `import:episode_composition` x1, `services.scientific_closed_request` x1, `services.scientific_saved_request` x1 |
| report_delivery.py | 34 | finish: unreported root returns credit + pending_handles + report facts; otherwise fills the parent's typed form from facts + interpretations and saves it once | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.facts` x1, `self.workflow.journal` x2, `self.workflow.pending_handles` x1, `self.workflow.release` x2, `self.workflow.source_credit_view` x1, `table:runtime_forms` x2 |
| scientific_contracts.py | 55 | contract constants: VERSION, AXIS A106, ROLE, _COMMON_TOOLS list, schemas (_ASSIGNMENT, _EVIDENCE_TASK, _SELECTION, _REVISION_ORIGIN, _REVISION_ARGUMENTS), scientific namespaces | `import:communication` x1, `import:domain` x1, `import:episode_bindings` x1, `import:evidence_axis_contracts` x1, `import:evidence_axis_instructions` x1, `import:perturbation_evidence_library` x1, `import:perturbation_evidence_records` x1, `import:perturbation_evidence_reports` x1, `import:scientific_support_metadata` x1 |
| scientific_operations.py | 34 | execute own tools: process.execution, process.revise (child selection + revision_origin), byte-operand authentication for material/source tools, else services.execute_tool; invalid outcomes returned with feedback | `services.authenticate_source_byte_operands` x1, `services.execute_tool` x1 |
| standalone_credit_presentation.py | 76 | decision state at root: like commissioned, plus annotation_axis_credit mode (controller arms, annotation credits, root_score, proposed_annotations, comparisons), a101-a104 sheets/target_sheets/tool_attachments into completed work; annotation-axis yield table | `bind_functions` x2, `binding_context` x1, `import:episode_work_report` x1, `import:library.live_runtime_functions` x1, `import:runtime` x3, `self.workflow.annotation_context` x1, `self.workflow.binding_context` x1, `self.workflow.catalog` x1, `self.workflow.controller_binding` x2, `self.workflow.delivery_status` x1, `self.workflow.extra_report_sources` x1, `self.workflow.is_scientific_source` x1, `self.workflow.journal` x3, `self.workflow.knowledge` x1, `self.workflow.local_outcome_preview` x1, `self.workflow.pending_work` x1, `self.workflow.receipt_projection` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_binding` x1, `self.workflow.source_credit_view` x1, `self.workflow.specialist` x1, `self.workflow.store` x3, `self.workflow.tools` x1, `self.workflow.working_state` x1, `table:runtime_actions` x2 |
| task.py | 228 | decision loop: next (replay/resume, model call, source failure), apply_response (reason envelope + empty-commit rejection, job_child failure feedback, action contract feedback, report_update admission), execute (reason via commit_reasoning, wait, tool; receive outcomes, automatic score updates, credit after action, shared grading retention) | `bind_functions` x2, `binding_context` x3, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:providers` x1, `import:runtime` x2, `self.workflow.action_schema` x1, `self.workflow.automatic_score_updates` x1, `self.workflow.binding_context` x3, `self.workflow.completed_unit` x3, `self.workflow.completions` x3, `self.workflow.controller_value` x2, `self.workflow.decision_exchanges` x3, `self.workflow.delivery_resolution_inputs` x1, `self.workflow.execute` x1, `self.workflow.execution_binding` x7, `self.workflow.inprocess_replay` x4, `self.workflow.journal` x7, `self.workflow.last_observed_credit` x1, `self.workflow.next_return` x1, `self.workflow.pending_work` x1, `self.workflow.permits_common_action` x1, `self.workflow.perturbation_evidence_binding` x1, `self.workflow.reasoning_action_schema` x1, `self.workflow.receive_native_outcome` x1, `self.workflow.receive_outcome` x1, `self.workflow.resolve_pending_deliveries` x1, `self.workflow.resolver` x1, `self.workflow.retain_shared_grading_results` x1, `self.workflow.run_id` x3, `self.workflow.selected` x3, `self.workflow.services` x1, `self.workflow.source_credit_view` x1, `self.workflow.specialist` x2, `self.workflow.store` x9, `self.workflow.validate_report` x1, `services.instructions` x1, `table:runtime_actions` x8, `table:runtime_episodes` x1, `table:runtime_model_calls` x2 |
| task_decision.py | 292 | model call recording, decision-exchange protocol (request_context lookups: child_options, composition_information, own attempts), contract-information freezing/validation, literature numerical contracts | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.contract_information_profile` x1, `self.workflow.contract_information_reply` x1, `self.workflow.decision_exchanges` x4, `self.workflow.decision_protocol` x3, `self.workflow.execute` x1, `self.workflow.freeze_contract_information` x1, `self.workflow.freeze_literature_numerical_contracts` x1, `self.workflow.history_preview` x1, `self.workflow.is_job_source` x2, `self.workflow.journal` x3, `self.workflow.numerical_contracts` x1, `self.workflow.perturbation_evidence_binding` x1, `self.workflow.provider` x4, `self.workflow.receipts` x4, `self.workflow.run_id` x1, `self.workflow.services` x1, `self.workflow.store` x2, `self.workflow.uses_received_record_context` x2, `self.workflow.validate_contract_information` x5, `services.decision_exchange_instructions` x1, `table:runtime_model_calls` x8 |
| task_instructions.py | 24 | composes instructions: library INSTRUCTIONS + goal (replace or append), reasoning commit requirement, tool knowledge, launch instructions, pending_child_delivery repair, wait guidance, native event guidance, exchange-protocol history guidance | `binding_context` x1, `import:library.literature_investigation_prompt` x1, `source.workflow.binding_context` x1, `source.workflow.decision_protocol` x1, `source.workflow.knowledge` x1, `source.workflow.launch_instructions` x1, `source.workflow.native_event_information` x1, `source.workflow.permits_common_action` x3, `source.workflow.specialist` x1 |
| task_state.py | 115 | per-episode decision state: calls, feedback, last outcome, report_values (initial_report), report_basis, restore/checkpoint, record_effect, record_execution_failure (failed tool/reason becomes an observed outcome) | `bind_functions` x2, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.archive` x1, `self.workflow.completions` x4, `self.workflow.controller_value` x1, `self.workflow.execution_binding` x4, `self.workflow.inprocess_replay` x7, `self.workflow.journal` x5, `self.workflow.progress_provider` x2, `self.workflow.recover_commissions` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_view` x1, `self.workflow.store` x2, `table:runtime_actions` x5, `workflow.context` x1, `workflow.grains` x1 |
| to_child_execution_job_submission.py | 32 | prepares launch child commission: scope, return form, required return sources, hpc handoff fact requirement, initial report, launch instructions, child assignment | `binding_context` x4, `import:runtime` x1, `services.capabilities` x1, `workflow.annotation_child_roles` x1, `workflow.available_child_roles` x1, `workflow.binding_context` x4, `workflow.child_initial_report_input` x1, `workflow.episode_bindings` x3, `workflow.expanded_contract_form` x1, `workflow.launch_instructions` x1, `workflow.run_id` x1, `workflow.services` x1, `workflow.specialist` x1, `workflow.store` x1 |
| to_child_execution_progress_assessment.py | 43 | prepare_request validates monitor assignment (monitor_assignment_v1); required_return_sources monitoring_progress_refs when annotation task required; prepare_commission for role monitor | `binding_context` x4, `import:communication` x1, `import:domain` x1, `import:runtime` x1, `services.annotation_task_required` x1, `services.capabilities` x1, `workflow.annotation_child_roles` x1, `workflow.available_child_roles` x1, `workflow.binding_context` x4, `workflow.child_initial_report_input` x1, `workflow.episode_bindings` x3, `workflow.expanded_contract_form` x1, `workflow.launch_instructions` x1, `workflow.run_id` x1, `workflow.services` x1, `workflow.specialist` x1, `workflow.store` x1 |
| to_child_execution_result_acquisition.py | 29 | prepares results child commission | `binding_context` x4, `import:runtime` x1, `services.capabilities` x1, `workflow.annotation_child_roles` x1, `workflow.available_child_roles` x1, `workflow.binding_context` x4, `workflow.child_initial_report_input` x1, `workflow.episode_bindings` x3, `workflow.expanded_contract_form` x1, `workflow.launch_instructions` x1, `workflow.run_id` x1, `workflow.services` x1, `workflow.specialist` x1, `workflow.store` x1 |
| to_child_perturbation_evidence.py | 61 | prepares the recursive perturbation_evidence child: prepare_invocation with objective/purpose/schema/initial_report, closed-commission replay | `binding_context` x5, `import:episode_return_records` x1, `import:runtime` x1, `_runtime.ContractError` x1, `_runtime.Episode` x1, `_runtime.interpretation_schema` x1, `_runtime._json` x2, `_runtime.json` x2, `_runtime.parse_json_object` x1, `_runtime.validate_form` x1, `services.capabilities` x1, `services.scientific_closed_request` x1, `table:runtime_actions` x1, `table:runtime_episodes` x1, `self.annotation_child_roles (Workflow)` x1, `self.available_child_roles (Workflow)` x1, `self.binding_context (Workflow)` x5, `self.child_initial_report_input (Workflow)` x1, `self.context (Workflow)` x1, `self.episode_bindings (Workflow)` x3, `self.expanded_contract_form (Workflow)` x1, `self.grains (Workflow)` x1, `self.journal (Workflow)` x2, `self.launch_instructions (Workflow)` x1, `self.perturbation_evidence_binding (Workflow)` x1, `self.run_id (Workflow)` x3, `self.services (Workflow)` x2, `self.specialist (Workflow)` x1, `self.store (Workflow)` x1 |
| to_child_published_evidence_assessment.py | 33 | prepares literature child commission | `binding_context` x4, `import:runtime` x1, `services.capabilities` x1, `workflow.annotation_child_roles` x1, `workflow.available_child_roles` x1, `workflow.binding_context` x4, `workflow.child_initial_report_input` x1, `workflow.episode_bindings` x3, `workflow.expanded_contract_form` x1, `workflow.launch_instructions` x1, `workflow.run_id` x1, `workflow.services` x1, `workflow.specialist` x1, `workflow.store` x1 |
| to_parent.py | 163 | required return sources (perturbation_evidence_results + committed_record_refs at root child, committed_record_refs deeper); fact sources from library/tool library; facts = perturbation_evidence_results (own closed process result + received, merged own-first); reference resolution; validate_report checks results against frozen closing facts | `import:method_loop.durable` x1, `import:method_loop.episode` x1, `import:perturbation_evidence_provenance` x1, `import:perturbation_evidence_records` x1, `import:perturbation_evidence_reports` x2, `services.annotation_task_required` x1, `services.scientific_frozen_results` x1, `services.scientific_frozen_results_for` x1, `services.scientific_received_results` x1, `services.scientific_received_results_for` x1, `services.scientific_reference` x1, `table:runtime_forms` x1 |
| tool_selection.py | 84 | tool catalog = resolved selected tools (direct only) + process.revise + process.execution; common tool names; resource tool contracts read from launch->launch_api and results children | `import:resource_tool_information` x1, `services.tool_catalog` x3, `services.tool_information_catalog` x1, `services.tool_information_catalog_for` x1, `services.workflow` x2, `workflow.episode_bindings` x1 |
| waiting.py | 30 | suspension_changed and selected wait execution with failure feedback | `bind_functions` x2, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.execution_backend` x1, `self.workflow.execution_handle` x2, `self.workflow.perform_selected_wait` x1 |
| yield_estimator.py | 49 | continuation task A106:whole_axis_findings; yield controller chosen from yield_bindings[task]: accumulation -> YieldController, bounded_quality -> BoundedYieldController(native_score_maximum), completion -> CompletionYieldController; checks credit_definition digest and projector.yield_method match | `import:numerical` x3 |

## Carried over

Old file | name | kind | new place or machinery reason
--- | --- | --- | ---
alternate_process_selection.py | AlternateProcessSelection | episode function | task.py process_revise (the class is dissolved into functions)
alternate_process_selection.py | AlternateProcessSelection._proposed_selection | episode function | task.py proposed_selection (library candidate: the same selection arithmetic is in every axis head)
binding_record.py | ScientificBindingRecord | machinery | binding_record.py is not carried (README 3e)
binding_record.py | ScientificBindingRecord.as_record | machinery | the binding's own as_record(); deleted (README 3e)
child_message_owners.py | exchange_for_child | machinery | routes the recursive exchange to this episode functions through the binding registry (identity checks only, README 3b C1)
commissioned_credit_presentation.py | CommissionedScientificPresentation | episode function | messages/internal_summary.py internal_summary (the decision state of a commissioned episode)
commissioned_credit_presentation.py | CommissionedScientificPresentation.decision_state | episode function | messages/internal_summary.py internal_summary (credit binding, investigation_progress, own_outcomes, last_local_outcome, held_record_refs, child_reports, report) and task.py decide (tools, tool knowledge, time_accounting); the old deliveries, controller_binding, pending_work, working_state and annotation_context are the old runner and are not carried
commissioned_credit_presentation.py | CommissionedScientificPresentation.completed_work | episode function | messages/internal_summary.py own_outcomes (outcome_page) and child_reports
commissioned_credit_presentation.py | CommissionedScientificPresentation.exchange_yield_table | episode function | messages/internal_summary.py action_yields (yield_table over view.controller_state)
commissioned_credit_presentation.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
completion_snapshot.py | completion_snapshot | machinery | closing snapshot read from runtime_episodes and the old controller (initial_credit, credit, controller_credit, episode_yield, parent_invocation_ref); the system hands the credit in completion (README 3b D1)
configuration.py | ScientificConfiguration | episode function | settings (ctx.settings) and constants of the files that use them: task.py process_library, tool_library, replaces_default_instructions, offered_slots; the class itself is deleted
configuration.py | ScientificConfiguration.__init__ | episode function | library and tool_library -> task.py process_library / tool_library (the frozen directories named by settings); child_roles -> task.py offered_slots (settings child_roles); replaces_default_instructions -> task.py replaces_default_instructions; tool_retrieval -> settings tool_registry; contract_information_profile and the yield_bindings validation are configuration checks of the old runner (README 5 item 16, 3d) and are not carried
credit.py | original_task_projector | episode function | credit.py finding_progress (FindingProgressPolicy from the evidence task) and messages/read_from_parent.py evidence_task (the check of context.evidence_task)
credit.py | PerturbationEvidenceCredit | episode function | credit.py credit
credit.py | PerturbationEvidenceCredit._scientific_credit_invocation | machinery | assembled the arguments of workflow.projection_view / projector_receipt_arguments for services.scientific_credit; credit is computed over held records now (README 3d)
credit.py | PerturbationEvidenceCredit.credit_kind | machinery | 'scientific' kind label; credit_kind is deleted (README 3d)
credit.py | PerturbationEvidenceCredit.credit_projector | episode function | credit.py finding_progress (the projector ScientificFindingProgress, over the library function project_finding_progress); the proposed-annotation requirement is messages/read_from_parent.py read_from_parent
credit.py | PerturbationEvidenceCredit.credit_view | episode function | credit.py credit (replaces services.scientific_credit)
decision_inputs.py | ScientificDecisionInputs | episode function | task.py decide (the context of the model request)
decision_inputs.py | ScientificDecisionInputs.decision_inputs | episode function | task.py decide: launch_instruction_library, tool_knowledge, child_options. resource_context, shared_information_context, execution_expectations, resource_tool_estimates, native_execution_expectations, waiting_support and pending_work come from job services and actions that are not built or no longer exist; not carried (BLOCKED-ON-JOB-SERVICE for the first five)
decision_inputs.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
decision_state.py | ScientificDecisionState | episode function | messages/internal_summary.py internal_summary (one presentation)
decision_state.py | ScientificDecisionState.credit_presentation | machinery | chose the standalone or commissioned presentation class by path length and by the saved annotation_axis_credit mode (saved-credit compatibility of the old runner); not carried
decision_state.py | ScientificDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary
episode.py | create_execution_bindings | machinery | home factory constructing the three execution bindings; there is no table or list of bindings (AGENTS.md)
episode.py | PerturbationEvidenceEpisode | episode function | episode.py PerturbationEvidence (the one class)
episode.py | PerturbationEvidenceEpisode.contract_information_profile | machinery | contract-information freezing for commissioning parents (README 5 item 16); not carried
episode.py | PerturbationEvidenceEpisode._role | machinery | role guard of the shared per-role class; the role is its own episode now
episode.py | PerturbationEvidenceEpisode.child_roles | episode function | task.py CHILD_SLOTS and offered_slots
episode.py | PerturbationEvidenceEpisode.permitted_common_actions | episode function | task.py offered / selection_schema: the model is offered tools, reason and child commissions; 'wait' and 'redeliver_report' are not carried
episode.py | PerturbationEvidenceEpisode.allowed_children | episode function | task.py offered_slots (settings child_roles) over CHILD_SLOTS
episode.py | PerturbationEvidenceEpisode._component_scoring_facts | machinery | returned {}: A106 has no component scoring facts; a hook of the old report machinery
episode.py | PerturbationEvidenceEpisode.current_report_facts | machinery | returned {} (the old report hook); not carried
episode.py | PerturbationEvidenceEpisode.initial_decision_context | machinery | returned {} (the old initial binding-context hook); not carried
episode.py | PerturbationEvidenceEpisode._validate_component_axis_report | machinery | returned None (the old component-axis report hook); not carried
episode.py | PerturbationEvidenceEpisode.prepare_child_request | episode function | messages/msg_to_child.py monitor (the monitor assignment passes through; its monitor_assignment_v1 schema check is a check of a commission and is the child read_from_parent); other roles passed the assignment unchanged
episode.py | PerturbationEvidenceEpisode.receive_child_progress_for_role | machinery | admitted the monitor delivered progress references into the old progress provider (README 3b R5); the delivered snapshots travel in the monitor return and read_from_child keeps them
episode.py | PerturbationEvidenceEpisode.child_request_preparer | machinery | binding lookup of the preparer by role (README 3b C1)
episode.py | PerturbationEvidenceEpisode.child_report_receiver | machinery | binding lookup of the receiver by role (README 3b C1)
episode.py | PerturbationEvidenceEpisode.child_request_preparer_for_binding | episode function | task.py CHILD_SLOTS (role -> child binding path) and messages/msg_to_child.py COMMISSIONS (role -> preparer)
episode.py | PerturbationEvidenceEpisode.child_report_receiver_for_binding | episode function | task.py CHILD_SLOTS and messages/read_from_child.py read_from_child (branch on slot)
execution_planning.py | catalog | episode function | task.py catalog (the process_execution entry: description, input schema)
execution_planning.py | read | episode function | task.py process_execution (resolves the selected tool, then raises NotImplementedError BLOCKED-ON-JOB-SERVICE for the execution memory, resource context and HPC commissions)
from_child_execution_job_submission.py | receive_report | episode function | messages/read_from_child.py read_from_child (launch)
from_child_execution_job_submission.py | admit_return | machinery | admitted the child return through the receipts ledger and saved attempts (README 3b R1)
from_child_execution_job_submission.py | _bind_incoming_runtime | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
from_child_execution_progress_assessment.py | receive_progress | episode function | messages/read_from_child.py read_from_child (monitor: progress_snapshots); the provider admission is machinery (README 3b R5)
from_child_execution_progress_assessment.py | receive_report | episode function | messages/read_from_child.py read_from_child (monitor)
from_child_execution_progress_assessment.py | admit_return | machinery | admitted the child return through the receipts ledger and saved attempts (README 3b R1)
from_child_execution_progress_assessment.py | _bind_incoming_runtime | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
from_child_execution_result_acquisition.py | receive_report | episode function | messages/read_from_child.py read_from_child (results)
from_child_execution_result_acquisition.py | admit_return | machinery | admitted the child return through the receipts ledger and saved attempts (README 3b R1)
from_child_execution_result_acquisition.py | _bind_incoming_runtime | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
from_child_perturbation_evidence.py | admit_return | machinery | admitted the child return through the saved attempt, receipts and progress (README 3b R1, R3)
from_child_perturbation_evidence.py | receive_report | episode function | messages/read_from_child.py read_from_child (perturbation_evidence)
from_child_published_evidence_assessment.py | receive_report | episode function | messages/read_from_child.py read_from_child (literature)
from_child_published_evidence_assessment.py | admit_return | machinery | admitted the child return through the receipts ledger and saved attempts (README 3b R1)
from_child_published_evidence_assessment.py | _bind_incoming_runtime | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
from_parent.py | ScientificAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent
from_parent.py | ScientificAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of the old _ASSIGNMENT, same names)
from_parent.py | ScientificAssignment.child_assignment_schema | episode function | messages/read_from_parent.py: the 'proposed_annotation_ref required when the annotation task is required' addition is the check in read_from_parent; the parent-side child schema itself is not carried (README 3b C3)
from_parent.py | ScientificAssignment._selection | episode function | task.py selection_checked (library candidate) used by process_revise; messages/read_from_parent.py validate_selection (shape). The library-side resolution of the selection is a check of a commission and is not made when the assignment is read
from_parent.py | ScientificAssignment._assignment | episode function | messages/read_from_parent.py read_from_parent (the checks of the assignment itself: evidence task, selection and revision-origin shape, evidence reference pattern); the commission checks (reference_in_scope, tool resolution, filled identity) are not carried (rule 1)
from_parent.py | ScientificAssignment._invocation | episode function | messages/msg_to_child.py (objective and message are the old invocation objective and purpose); the report_schema and initial_report have no place: the child declares its return form
from_parent.py | ScientificAssignment.prepare_assignment | episode function | messages/msg_to_child.py own_kind (the proposed annotation a child inherits); its checks of the commission are not carried (rule 1)
from_parent.py | ScientificAssignment._validate_origin | machinery | checked the revision origin against the parent recorded preparation (journal read); a check of a commission, not carried (rule 1)
from_parent.py | ScientificAssignment.prepare_invocation | episode function | messages/msg_to_child.py own_kind; the closed-commission replay of the old method is the system resume (README 3b C5)
from_parent.py | ScientificAssignment.validate_context | machinery | filled-process identity checks of the old request (digests, saved request); the system compares a rebuilt commission with its record
from_parent.py | ScientificAssignment.validate_execution_context | machinery | historical-closure and mechanics-binding identity checks of the old runner; not carried
from_parent.py | ScientificAssignment._original_selection | episode function | parent_input['selection'] (messages/read_from_parent.py)
from_parent.py | ScientificAssignment.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM: evidence_refs and received_record_refs are record_refs fields (custody entry/commissioned receipts)
goal.py | ScientificGoal | episode function | goal.py GOAL and EVIDENCE_AXIS_GOAL
goal.py | ScientificGoal.instructions | episode function | goal.py GOAL / EVIDENCE_AXIS_GOAL (the two texts) and task.py entry_of / decide (the choice by entry_version)
incoming_message_owners.py | _static | machinery | routing of the incoming prepared request through the binding registry (identity checks only)
incoming_message_owners.py | _state | machinery | routing of the incoming prepared request through the binding registry (identity checks only)
incoming_message_owners.py | _current_class | machinery | routing of the incoming prepared request through the binding registry (identity checks only)
incoming_message_owners.py | admission_for_prepared_request | machinery | admitted the four non-recursive child returns through the old admission path (README 3b R1)
internal_summary.py | ScientificSummary | episode function | messages/internal_summary.py internal_summary
internal_summary.py | ScientificSummary.decision_context | episode function | task.py decide (the selected entries, thought pattern, resolved tools, permitted children: read from the frozen libraries, which are files outside the Store) and messages/internal_summary.py (the assignment); annotation_support_routes of an evidence-axis entry raises NotImplementedError BLOCKED-ON-SUPPORT-ROUTES
process_state.py | PerturbationEvidenceState | machinery | restore of a closed or saved process request (replay authentication); the system restores the view
process_state.py | PerturbationEvidenceState.restore_closed_process | machinery | replay authentication of a closed request (README 3e F8)
process_state.py | PerturbationEvidenceState.restore_saved_process | machinery | replay authentication of a saved request (README 3e F8)
report_delivery.py | ScientificReportDelivery | episode function | messages/final_to_parent.py final_to_parent
report_delivery.py | ScientificReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (the filled facts); saving the form once (runtime_forms), release and pending_handles are machinery and not carried (README 3b D1, D3)
report_delivery.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
scientific_contracts.py | _object | machinery | closed-JSON admission of a value with its digest; the forms admit closed JSON (RecordForm)
scientific_contracts.py | _ref_schema | episode function | task.py THOUGHT_REF (private copy of the option reference schema of the revision arguments)
scientific_operations.py | ScientificOperations | episode function | task.py tools process_revise, process_execution, selected_tool
scientific_operations.py | ScientificOperations.execute | episode function | task.py process_revise (the revision), process_execution (planning read, BLOCKED-ON-JOB-SERVICE) and selected_tool (services.execute_tool -> ToolRegistry.execute_async; the byte-operand authentication is not carried)
standalone_credit_presentation.py | StandaloneScientificPresentation | episode function | messages/internal_summary.py internal_summary (the part shared with the commissioned presentation); the annotation_axis_credit mode (arms, annotation credits, comparisons, a101-a104 sheets) is the root episode and is not this one
standalone_credit_presentation.py | StandaloneScientificPresentation.decision_state | episode function | messages/internal_summary.py internal_summary (shared part); root-only annotation_axis_credit mode not carried
standalone_credit_presentation.py | StandaloneScientificPresentation.completed_work | episode function | messages/internal_summary.py own_outcomes and child_reports; the root sheets are not carried
standalone_credit_presentation.py | StandaloneScientificPresentation.exchange_yield_table | episode function | messages/internal_summary.py action_yields
standalone_credit_presentation.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
task.py | ScientificInvestigationTask | episode function | task.py decide, action and TOOLS
task.py | ScientificInvestigationTask.instructions | episode function | task.py instructions (called in decide)
task.py | ScientificInvestigationTask.next | episode function | task.py decide (the model request); replay, resume and the source_failed end are the system
task.py | ScientificInvestigationTask.apply_response | episode function | task.py action (validation of the answer against the schema, the empty-commit rejection, the held-reference rejection, Rejected feedback)
task.py | ScientificInvestigationTask.execute | episode function | task.py tools reason, selected_tool, process_*; wait and redeliver_report are not carried; receive_outcome, automatic score updates and shared grading retention are the old runner
task.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
task_decision.py | ScientificTaskDecision | episode function | task.py decide (the request) and action
task_decision.py | ScientificTaskDecision.call | episode function | task.py decide returns ModelRequest(REASONING, instructions, context, generation_schema(...)); recording and saved-request reconstruction are the system
task_decision.py | ScientificTaskDecision.conversation_key | machinery | provider conversation state (README 3a); every ModelRequest carries the full context
task_decision.py | ScientificTaskDecision.interpretation_context | machinery | extended visible_record_refs from the lookup results of the decision exchange; the exchange is not carried (a lookup is a tool)
task_decision.py | ScientificTaskDecision.exchange_schema | machinery | decision-exchange envelope (README 3a)
task_decision.py | ScientificTaskDecision.exchange_response | machinery | decision-exchange envelope (README 3a)
task_decision.py | ScientificTaskDecision.validate_contract_exchange_request | machinery | saved-request check (README 3a)
task_decision.py | ScientificTaskDecision.validate_contract_exchange_history | machinery | saved-request check (README 3a)
task_decision.py | ScientificTaskDecision.exchange_decision | machinery | the decision-exchange loop (README 3a)
task_decision.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
task_instructions.py | instructions | episode function | task.py instructions
task_state.py | ScientificTaskState | machinery | per-episode decision state, checkpoint and restore of the old loop; the loop holds the state
task_state.py | ScientificTaskState.__init__ | machinery | per-episode decision state of the old loop (calls, feedback, report_values: the report is the report tool outcome)
task_state.py | ScientificTaskState.bind_execution_context | machinery | binding of the old execution context
task_state.py | ScientificTaskState.record_execution_failure | episode function | task.py selected_tool (a failed selected operation is returned as failure_outcome, which enters the iterator)
task_state.py | ScientificTaskState.restore_checkpoint | machinery | checkpoint restore (README 3e)
task_state.py | ScientificTaskState.restore | machinery | restore of the old loop (README 3e)
task_state.py | ScientificTaskState.record_effect | machinery | record_effect: the system journals each unit (README 3e F6)
task_state.py | ScientificTaskState.checkpoint | machinery | checkpoint (README 3e)
task_state.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
to_child_execution_job_submission.py | prepare_commission | episode function | messages/msg_to_child.py launch
to_child_execution_progress_assessment.py | prepare_request | episode function | messages/msg_to_child.py monitor (the monitor_assignment_v1 schema check is the child read_from_parent)
to_child_execution_progress_assessment.py | required_return_sources | episode function | messages/msg_to_child.py REQUIRED['monitor'] (selection) and task.py REQUIRED_FACTS
to_child_execution_progress_assessment.py | prepare_commission | episode function | messages/msg_to_child.py monitor
to_child_execution_result_acquisition.py | prepare_commission | episode function | messages/msg_to_child.py results
to_child_perturbation_evidence.py | prepare_request | episode function | messages/msg_to_child.py own_kind
to_child_published_evidence_assessment.py | prepare_request | episode function | messages/msg_to_child.py literature
to_parent.py | build_process_result | episode function | messages/final_to_parent.py process_results (BLOCKED: validate_process_result, project_process_result and credit_binding_ref of the old perturbation_evidence_reports are not placed; raises NotImplementedError when perturbation_evidence_results is selected)
to_parent.py | merge_process_results | episode function | messages/final_to_parent.py process_results (own-first merge; BLOCKED with build_process_result)
to_parent.py | ScientificReport | episode function | messages/final_to_parent.py RETURN_FORM and final_to_parent
to_parent.py | ScientificReport.required_return_sources | episode function | messages/msg_to_child.py REQUIRED['perturbation_evidence'] (what this parent selects from its own children); the old path-length rule is not carried
to_parent.py | ScientificReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (perturbation_evidence_results, committed_record_refs; report_sources(library, tool_library) is not placed: unplaced)
to_parent.py | ScientificReport.facts | episode function | messages/final_to_parent.py facts
to_parent.py | ScientificReport.resolve | machinery | resolved a reference by namespace through the old receipts and scientific_reference service; holding a record is records.holds (README 3b D2)
to_parent.py | ScientificReport.validate_report | episode function | messages/final_to_parent.py validate_report (called before the result is returned); the axis validate_form step of the parent-written form has no object
to_parent.py | private_received_results | machinery | read the received results from the old provenance store under read_snapshot (SQL over runtime tables)
to_parent.py | private_frozen_results | machinery | read the frozen closing results from runtime_forms (SQL); the facts are built from the summary
tool_selection.py | ScientificToolSelection | episode function | task.py direct_tools, catalog, selected_catalog
tool_selection.py | ScientificToolSelection._information_catalog | machinery | services.tool_information_catalog(_for): the old runner tool catalog service; the frozen tool library is read without an availability check
tool_selection.py | ScientificToolSelection._closed_tool_resolution | machinery | closed-process replay of the tool resolution (restore_closed_process)
tool_selection.py | ScientificToolSelection._tool_resolution_for | episode function | task.py direct_tools (ScientificToolLibrary.resolve_invocations without the available catalog)
tool_selection.py | ScientificToolSelection._tool_resolution | episode function | task.py direct_tools (the common-tool name collision check is not carried: the selected library names travel inside the selected_tool arguments)
tool_selection.py | ScientificToolSelection.catalog | episode function | task.py direct_tools and catalog (process_revise description by entry version, process_execution entry)
tool_selection.py | ScientificToolSelection.common_tool_names | machinery | the list of common tool names of the old catalog; the tools are static names of TOOLS now
tool_selection.py | ScientificToolSelection._resource_information_catalog | episode function | UNPLACED: read the contracts of the launch and results children resource tools through resource_tool_information (bound_resource_tool_contracts, tool_information_contracts), old shared root, not placed; the availability check of the selected tools against them is not made
waiting.py | ScientificWaiting | machinery | wait machinery (README 3b)
waiting.py | ScientificWaiting.suspension_changed | machinery | suspension of the old runner (README 3b)
waiting.py | ScientificWaiting._execute_selected_wait | machinery | the wait action; not carried (README 3b)
waiting.py | _bind_scientific_runtime_providers | machinery | provider patching (`_bind_scientific_runtime_providers` / `bind_functions` onto the old runtime module); not carried (README 3a, 3e)
yield_estimator.py | PerturbationEvidenceYield | episode function | yield_estimator.py yield_controller
yield_estimator.py | PerturbationEvidenceYield.private_yield_binding | machinery | whether the old private yield declarations were configured; the controller is always built
yield_estimator.py | PerturbationEvidenceYield.continuation_task | episode function | yield_estimator.py TASK and messages/read_from_parent.py task_key (A106:whole_axis_findings)
yield_estimator.py | PerturbationEvidenceYield.yield_controller | episode function | yield_estimator.py yield_controller (AccumulationYieldController, README 7b)
