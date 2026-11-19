# a103/gene_context_evidence — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/<file>`,
only the 36 files directly in the folder (1988 lines). It has no `grading/` or `scoring/` subfolder; its
`tests/` folder and child folders were not read. Old-runner names are listed per file below and in
`runs/carry_over/calls/a103_01.tsv`.

## What it is for (its goal, in its own words)

The A103 scientific (gene-context) evidence episode. It is a recursive role: the parent picks the evidence
axis (always `A103`), a thought pattern (`P…`) and the actual tools, and this episode investigates on its own.
For a published-instruction axis entry (`goal.py`), its goal text is the A103 guidance (`scientific_guidance.py`) followed by:

> "Determine what the supplied target does within the parent's assigned question, scope and constraints.
> Start with the supplied sequence, selected file contents or snippets, preserving their boundaries,
> completeness and known context. No initial candidate annotation or publicly searchable name is required.
> Possible functions can emerge from the evidence and be compared or revised. … Missing information remains
> unknown. Choose an available tool action, commit a scientific interpretation through the reasoning action,
> commission a scoped child with its own typed return form, or wait for selected pending work … Keep the
> assigned evidence axis, thought pattern and selected tools for this episode. process.revise prepares a
> different thought pattern and/or tool selection for a new child; it does not change this episode or start
> that child. … The configured controller owns continuation. Waiting and unchanged observations do not
> manufacture progress."

The A103 guidance prefix:

> "A103 owns gene-context work. Scientific descendants remain A103. Use available shared operations to send
> the immediate parent specific missing operands or useful received evidence … Context measurements are
> automatically graded at publication/receipt. Each target/locus, neighboring component, domain and regulatory
> footprint retains its own attribution. An identity score, source label or fetched record alone is not an
> association score. Unknown flanks and unevaluated detections are not absence. Preserve optional modules,
> paralogs and related sampling. Use one small local job at a time, current resource_context and admission
> feedback. Root/owner credit comes from actual measured context, not narrative judgments."

A second goal text covers legacy support-metadata axis entries (`entry_version` not the instruction version).
It explains annotation_support_routes and says metadata earns no credit.

## Task and instructions

- `instructions.py`: the binding's own instructions replace the default instructions when every evidence_axis
  entry in the library has the published-instruction version (`replaces_default_instructions`). Otherwise
  they are appended. The file then appends the reasoning-commit requirement (reason is permitted), tool knowledge
  instructions, launch-library instructions, the pending_child_delivery repair paragraph (`redeliver_report`),
  the in-process wait paragraph (wait on a `pending_child_` handle, event `returned`, cursor 0; waiting earns no
  credit), native-event-target guidance when configured, and the exchange-protocol replacement of history guidance
  (`request_context` exchanges; read past outcomes with `episode.history`).
- `task.py`: one decision per iteration. An empty reasoning commit is rejected unless it is
  `no_applicable_evidence` or the binding finds task content in it. A `reason` action goes to the binding's
  `execute_reasoning` or `Store.commit_reasoning`. `wait` goes to the wait performer, `tool` goes to tool
  execution. After an observed outcome come automatic score updates, then credit from the source credit view.
  A wait carries the last observed credit. `shared.read_information` retains shared grading results. A failed or
  invalid returned tool/reason action still enters the iterator with its credit (`task_state.record_execution_failure`).
- `tool_policy.py`: `sequence.align` is refused (`a103_new_sequence_comparison_requires_shared_parent`).

## What it reads from its parent's assignment

`contracts.py` / `from_parent.py`:

| Field | Meaning |
|---|---|
| `selection` (required) | `{version, evidence_axis (option ref, option_id const A103), thought_pattern (option ref P…), child_tool_info [{name, resources: api/local/hpc}]}`. It is checked against the library id and entries (instruction or evidence-axis version) and resolved through the tool library. |
| `proposed_annotation_ref` | The proposed annotation this task evaluates. It must be in scope as a `hypothesis` and must have been received by the parent. It is inherited from the parent's task and cannot differ. It is required when `services.annotation_task_required()` or when yield_bindings exist. |
| `evidence_refs` (required) | References in scope. With the proposed annotation they are the episode's initial references. |
| `constraints` (required) | Free object. |
| `context` (required) | May carry `evidence_task` (`evidence_axis_task_v1`, `whole_axis_findings`, `A103`, `credit_unit` > 0) and `a103_task.name` (used for the continuation task name). |
| `revision_origin` | When present, the `process.revise` preparation must match the parent invocation, the operation ref and the proposed selection exactly. |

Invocation (`_invocation`): `{objective, purpose, report_schema (closed), initial_report}`, plus the scope. The
filled process record is `filled_gene_context_evidence_v1` (selection, assignment digest, invocation digest,
mechanics binding). `validate_context` re-checks every identity. A closed request can be inspected or replayed
but never dispatched again (`validate_execution_context`).

## Children it may commission

| Child | How | What it sends | What it takes back |
|---|---|---|---|
| `gene_context_evidence` (recursive A103) | `child_message_owners` → `to_child_gene_context_evidence` / `from_child_gene_context_evidence` | Expanded typed return form, initial report, `prepare_invocation` (assignment as above, objective, purpose, report schema). Required return sources when an annotation task is required: `gene_context_evidence_results` + `committed_record_refs` for a top-level parent, `committed_record_refs` when nested. | The admitted typed form (saved admission attempt reused, failures saved), then the references received from the form. |
| `literature` (published_evidence_assessment) | `to/from_child_published_evidence_assessment`; also accepts the standalone LiteratureEpisode type | Child assignment via the child binding's `prepare_assignment` | Same admission logic as above (the two files are byte-identical apart from the docstring). |
| `monitor` (execution_progress_assessment) | `to_child_execution_progress_assessment` / `from_child_…`, `from_children` | Assignment validated against the monitor's `_ASSIGNMENT` and passed on unchanged. Requires `monitoring_progress_refs` when an annotation task is required. | Only the `episode_progress` references declared in the typed form, received under a digest of form + schema + scope. |
| `launch` / `results` execution and resource children | `episode.py` factories (execution_job_submission, api/local/hpc_job_execution, execution_result_acquisition; resource_work_submission + api/local/hpc + resource_result_acquisition), `scientific_commission_catalog.py` | Offered as commission routes in the tool catalog (`resource_tool_contracts` of the registered child owners) | The child's handoff/result facts (see the execution_job_submission doc). |
| `hpc` (hpc_work_planning → hpc_resource_prediction, hpc_allocation_execution) | `create_hpc_bindings` | — | — |

`child_policy.py` limits allowed_children to `{gene_context_evidence, literature}` within the configured
child_roles. The execution, resource and HPC children are reached through commission routes and factories, not through this list.

## Decision state and what it shows the model

`task.py` assembles: goal, scope, working_state, visible_record_refs, current_credit, current_evidence_vector
(axis components), investigation_progress (retained finding count, inactive dependencies, detail pages, when a
receipt projection exists), credit_binding, **time_accounting (journal elapsed view)**, pending_work,
last_local_outcome, feedback, visual_evidence (last `image.view`), report_deliveries, controller,
controller_binding, tools, tool_knowledge, job_episode_options, available_report_facts, requested purpose/form,
current_report_update/basis and report_lifecycle. When credit is `annotation_axis_credit`, working state and child
reports are hidden; the context shows proposed_annotations, annotation_comparisons and the controller's
arms/annotation_credits/root_score/decision, and a child outcome is shown only as counts. It also carries
monitoring information credit and `_completed_work_axis_results` (a103_sheet, target_sheets, tool_attachments,
source_contributions) for completed_action_reports.
`internal_summary.py` adds `gene_context_evidence` = {selection, initial_selection_sha256, evidence_axis
instruction view (or annotation view + annotation_support_routes), thought_pattern fields, child_tool_info,
assignment, permitted_children}. The initial context adds `received_gene_context_execution` (A103/A107 axes
with A103 execution resources). `decision_delivery.py` adds the resource, shared-information,
launch-instruction, child-option, completed-work, HPC-history, execution-expectation, estimate, native-event and waiting inputs.
`decision_presentation.py` renders through the published scientific prompt (or HPC, monitor, API launch,
selected execution, or receiver prompt).

## Tools it offers

Common tools (`_COMMON_TOOLS`): process.search/entry/sources/tools, knowledge.search/entry/read, episode.history,
episode.credit, episode.annotation_score, episode.monitoring_information, episode.estimate_wait,
shared.request_information/publish_information/resolve_information_need/read_information/list_information.
Own tools (`operations.py`) are the parent-selected `child_tool_info` tools with direct routes, resolved from the tool library.
A selected tool may not reuse a common tool name. `process.revise` (prepare a new child selection + revision_origin) and
`process.execution` from `execution_planning` are added. `material.*`/`source.read`/`source.locate` need authenticated source bytes.
`context.*`, `reference.neighborhood`, `result.blast.hsp` and `source.locate` receive the permitted received refs.
`sequence.align` is refused.

## How its credit is counted

`credit.py`: credit kind `scientific`. The projector is `A103ContextCredit` (`task_projector.py`; old module
`a103_credit`, now placed at `episode_support/grading/gene_context_evidence/credit.py`). It is used only for
published-instruction axis entries. Legacy metadata axes have no projector. The credit view itself comes from
`services.scientific_credit(context, receiver_selection)`. Credit is read after each observed action, following
automatic score updates. Annotation-axis credit is shown only as root_score. Credit is not clamped anywhere in these files.

## Continuation (yield estimator and settings)

`yield_estimator.py` + `configuration.py`: the continuation task is `A103:<assignment.context.a103_task.name>`,
or `A103:<projector kind>`. With `yield_bindings` configured, the declaration for that task fixes `kind`, `cutoff`,
`parameters` (`uncertainty_alpha` only) and `credit_definition`. The credit definition must equal the projector
record by digest, and the projector's `yield_method` must equal the kind.
accumulation → YieldController, bounded_quality → BoundedYieldController (maximum =
`projector.native_score_maximum`), completion → CompletionYieldController. Without yield_bindings no private
controller is returned (the old recorded controller contract applies). These are the three yield_control kinds.

## What it reports to its parent

`to_parent.py`: the fact sources are the process report sources (library + tool library) plus the A103 context
sources (`a103_investigation.context_fact_sources`). The facts are `gene_context_evidence_results` (own process result
+ received results, projected and merged) and the context-record source (received + committed context
records) when the form asks for it. `validate_report` checks the form and references (scientific namespaces
first), then the A103 measurement report (`report_validation.py`), and requires each `gene_context_evidence_results`
field to equal the frozen results. `report_delivery.py` saves the form once from facts + interpretations.
`report_snapshot.py` adds initial_credit, credit, controller_credit, episode_yield and parent_invocation_ref.

## Differences from similar episodes

- Compared with a101/sequence_homology_evidence, the yield_estimator logic is the same. The credit projector
  differs: A101 uses `A101SequenceCredit` (native_correspondence_credit), A103 uses `A103ContextCredit`. A103
  adds `scientific_guidance.py`, `tool_policy.py` (sequence.align refused), `child_policy.py`
  ({gene_context_evidence, literature}), `received_execution_context.py` (A103/A107), `received_context_report.py`
  and `report_validation.py` (A103 measurement report). A101 instead has direct to/from_child files for
  execution, resource and result children.
- A103 keeps a single 360-line `decision_delivery.py` and a 275-line `task.py`. A101 splits the same
  mechanics into decision_inputs/decision_state/task_decision/task_instructions.
- The two child exchanges (`to_child_gene_context_evidence` and `to_child_published_evidence_assessment`; likewise
  the two `from_child_*`) are byte-identical apart from the docstring.
- Notes for carry-over: `task.py` shows `time_accounting` (an elapsed view) to the model. This is display only, not a
  limit. "Use one small local job at a time" is guidance text, not enforcement.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (name×uses) |
|---|---|---|---|
| child_message_owners.py | 53 | Names exactly two child exchanges this parent owns: recursive `gene_context_evidence` (to/from_child_gene_context_evidence) and `literature` (published_evidence_assessment, private or standalone LiteratureEpisode). Any other role gets no exchange. | import:published_evidence_assessment.episode×1, import:runtime×1, wf.episode_bindings×1, wf.gene_context_evidence_binding×1 |
| child_policy.py | 5 | Allowed child roles = configured child_roles ∩ {gene_context_evidence, literature}. | none |
| configuration.py | 52 | Operands: services, A/P library, tool_library, child_roles (must contain gene_context_evidence, unique), tool_retrieval, contract_information_profile, yield_bindings keyed `A103:<task>` with kind ∈ {accumulation, bounded_quality, completion}, cutoff, parameters {uncertainty_alpha}, non-empty credit_definition. replaces_default_instructions when every evidence_axis entry is the published-instruction version. Permitted actions: tool, reason, child, wait, redeliver_report. | BindingContext.role×1, import:composition_information×1, import:numerical×1, import:scientific_tool_retrieval×1, yield:BoundedYieldController×2, yield:CompletionYieldController×2, yield:YieldController×2, yield:YieldParameters×2 |
| contracts.py | 57 | VERSION gene_context_evidence_episode_v10, AXIS A103, ROLE gene_context_evidence; the common tool names; assignment schema (selection = evidence_axis ref fixed to A103 + thought_pattern ref + child_tool_info {name, resources api/local/hpc}; proposed_annotation_ref; evidence_refs; constraints; context.evidence_task {whole_axis_findings, A103, credit_unit>0}; revision_origin); process.revise arguments schema. | import:communication×1, import:domain×1, import:episode_bindings×1, import:evidence_axis_contracts×1, import:evidence_axis_instructions×1, import:gene_context_evidence_library×1, import:gene_context_evidence_records×1, import:gene_context_evidence_reports×1, import:scientific_support_metadata×1 |
| credit.py | 25 | Credit kind `scientific`. Projector = A103ContextCredit (via task_projector) only when the axis entry is the published-instruction version; with yield_bindings a proposed_annotation_ref is mandatory. credit_view delegates to services.scientific_credit. | BindingContext.assignment×2, BindingContext.role×1, svc.scientific_credit×1 |
| decision_delivery.py | 360 | The model call: replays saved calls, then adds resource_context, shared_information_context, launch_instruction_library, selected_launch_instructions, child_options, binding initial context, completed_action_reports, requested_action_history (HPC context), pending_work, execution_expectations / job_execution_options, resource_tool_estimates, native_execution_expectations, native_event_targets, waiting_support; freezes contract information / literature numerical contracts; exchange protocol (request_context lookups vs select_action). Own intent is the list of decision inputs; the rest is old-runner replay mechanics. | import:episode_work_report×2, import:library.hpc_prompt×1, import:runtime×2, runtime._action_generation_schema×2, runtime.apply_state_frame×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime._category_yield_parameters×1, runtime.child_option_information×2, runtime.composition_lookup_schema×2, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×2, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.Draft202012Validator×1, runtime.instructional_model_context×4, runtime.is_contract_information×1, runtime._json×14, runtime.json×3, runtime.lookup_attempts×1, runtime.Mapping×4, runtime.model_snapshot×2, runtime._object×3, runtime._plain×2, runtime._recorded_action_generation_schema×1, runtime._recorded_assignment_transport×1, runtime._references_in×1, runtime.requested_contract_information×2, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×5, runtime.WorkflowError×14, runtime.yield_table×1, wf.available_child_roles×1, wf.binding_context×3, wf.contract_information_profile×1, wf.contract_information_reply×1, wf.controller_binding×1, wf.decision_exchanges×4, wf.decision_protocol×3, wf.episode_bindings×1, wf.execute×1, wf.execution_expectations×1, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.gene_context_evidence_binding×1, wf.history_preview×1, wf.is_job_source×3, wf.job_episodes×4, wf.journal×3, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.numerical_contracts×1, wf.pending_work×1, wf.permits_common_action×1, wf.provider×3, wf.provider.conversation_key×1, wf.provider.has_session×1, wf.receipts×4, wf.resource_context×1, wf.resource_estimator×5, wf.run_id×1, wf.services×2, wf.shared_information_context×1, wf.specialist×1, wf.store×4, wf.store.reference_subset×1, wf.uses_received_record_context×2, wf.validate_contract_information×5, wf.waiting_support×1, table:runtime_model_calls×8 |
| decision_presentation.py | 59 | Chooses which prompt renderer presents the decision (HPC, published scientific A103 prompt, monitor, API launch, selected execution, native profile receiver, ordinary receiver) and keeps the per-episode prompt state across decision_bootstrap / decision_update / decision_lookup_result frames. | import:gene_context_evidence_prompt×1, import:library.hpc_prompt×1, import:library.monitor_prompt×1, import:native_profile_presentation×1, import:providers×2, import:receiver_prompt×1, providers.apply_state_frame×3, providers.DECISION_CONTEXT_VERSION×1, providers.deepcopy×1, providers.is_api_launch_context×2, providers.is_published_scientific_context×2, providers.json×1, providers._ordinary_runtime_receiver_context×1, providers.render_api_launch_prompt×1, providers.render_gene_context_evidence_prompt×1, providers.text_instructions×1 |
| episode.py | 59 | Composes the A103 binding (binding_path gene_context_evidence, commissioning_parent legacy_annotation, roles = entry_roles = (gene_context_evidence,)); as_record descriptor; resource_information_catalog; factories for the execution children (launch, launch_api, launch_local, launch_hpc, results), HPC children (hpc_work_planning, hpc_resource_prediction, hpc_allocation_execution) and resource children (resource launch/api/local/hpc, resource results). Task class = GeneContextEvidenceTask, renderer = present_scientific_task. | none |
| from_child_execution_progress_assessment.py | 23 | Receives monitor (execution_progress_assessment) progress observations: only references in the typed form's `episode_progress` namespace are read and received, keyed by a content digest of form+schema+scope. | BindingContext.episode_id×3, BindingContext.scope×2, import:communication×1, import:domain×1, import:method_loop.durable×1 |
| from_child_gene_context_evidence.py | 26 | Admits a recursive A103 child's typed return: reuse a saved admission attempt (or its failure), else admit via the report contract and save the attempt; then receive the form's references (redelivery when the index differs). | import:runtime×1, runtime._digest×1, runtime.json×4, runtime.Record×2, runtime.ReportBoundaryError×1, runtime.ReportDeliveryError×2, wf.delivery_feedback×1, wf.journal×1, wf.receive_form×1, wf.run_id×2, wf.save_attempt×2, wf.store×1, table:runtime_actions×1, table:runtime_report_attempts×1 |
| from_child_published_evidence_assessment.py | 26 | Same admission logic for the literature child (published_evidence_assessment). Byte-identical apart from its docstring to from_child_gene_context_evidence. | import:runtime×1, runtime._digest×1, runtime.json×4, runtime.Record×2, runtime.ReportBoundaryError×1, runtime.ReportDeliveryError×2, wf.delivery_feedback×1, wf.journal×1, wf.receive_form×1, wf.run_id×2, wf.save_attempt×2, wf.store×1, table:runtime_actions×1, table:runtime_report_attempts×1 |
| from_children.py | 11 | Routes progress receipt only for role `monitor` to from_child_execution_progress_assessment. | none |
| from_parent.py | 209 | Admission of the parent's assignment and invocation: assignment/child schema (proposed_annotation_ref required when services say so); selection validation against the library (instruction or evidence-axis entry) and tool library; evidence_refs and proposed annotation must be in scope; invocation {objective, purpose, report_schema, initial_report}; required return sources; process.revise origin validation; closed-commission reconstruction; filled process record (filled_gene_context_evidence_v1); identity checks in validate_context; closed requests allow inspection, never new dispatch; initial_references = evidence_refs + proposed annotation. | BindingContext.assignment×7, BindingContext.episode_id×3, BindingContext.path×7, BindingContext.received_record_refs×1, BindingContext.request×3, BindingContext.role×4, BindingContext.run_id×7, BindingContext.scope×5, import:episode_return_records×1, svc.annotation_task_required×2, svc.proposed_annotation_for×1, svc.reference_in_scope×2, svc.scientific_closed_request×1, svc.scientific_parent_preparation×1, svc.scientific_preparation×2, svc.scientific_saved_request×1, svc.workflow×1, wf.gene_context_evidence_binding×1, wf.journal×1, wf.run_id×1, wf.store×1, table:runtime_actions×1 |
| goal.py | 16 | The episode's goal text (two variants: published-instruction axis, prefixed by scientific_guidance; legacy support-metadata axis). | BindingContext.assignment×1 |
| __init__.py | 0 | Empty package marker. | none |
| instructions.py | 25 | Instruction composition: specialist instructions replace or extend the default, plus reasoning-commit requirement, tool knowledge, launch library, pending_child_delivery repair, in-process wait, native event targets, and exchange-protocol history replacement text. | import:runtime_prompt×2, runtime_prompt.DECISION_EXCHANGE_PROTOCOL×1, runtime_prompt.INSTRUCTIONS×4, runtime_prompt.REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×1, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| internal_summary.py | 35 | Decision context shown to the model: selection, initial selection digest, evidence_axis (instruction view) or annotation view + annotation_support_routes, thought_pattern fields (id, name, description, use_when, live_alternatives, decision_guidance, outcome_contingencies, boundary), child_tool_info or tools, assignment, permitted_children; initial context adds received_gene_context_execution. | BindingContext.assignment×2, BindingContext.role×1, svc.scientific_support_routes×1, svc.workflow×1 |
| operations.py | 86 | Tool catalog = parent-selected tools resolved through the tool library (direct routes), plus process.revise and execution_planning catalog (process.execution); validates names (no common-tool names), arguments, source-byte operands; process.revise returns a child selection + revision_origin without starting anything; other tools go to services.execute_tool (context./reference./source.locate get permitted_record_refs). | BindingContext.assignment×1, BindingContext.path×1, BindingContext.received_record_refs×1, BindingContext.run_id×1, BindingContext.scope×5, import:execution_planning×2, svc.authenticate_source_byte_operands×1, svc.execute_tool×1, svc.tool_catalog×2, svc.tool_information_catalog×1, svc.workflow×1 |
| received_context_report.py | 16 | Adds the A103 context-record report source (received_context_records of received + committed refs) when the parent's form asks for it. | BindingContext.received_record_refs×1, BindingContext.scope×1, import:a103_investigation×1, import:communication×1, import:domain×1, wf.store×1 |
| received_execution_context.py | 11 | For annotation or A103/A107 axis episodes with A103 execution resources configured, shows received_gene_context_execution findings from received records. | BindingContext.assignment×1, BindingContext.received_record_refs×1, BindingContext.role×1, import:a103_hpc×1, wf.store×1, wf.tools×1 |
| report_delivery.py | 25 | finish(): with no report contract returns credit + pending handles + current report facts; else builds the form from facts + interpretations once and saves it. | import:library.private_policy_call×1, import:library.report_fact_assembly×1, import:runtime×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, wf.binding_context×1, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1, table:runtime_forms×2 |
| report_snapshot.py | 5 | Completion snapshot adds initial_credit, credit, controller_credit, episode_yield, parent_invocation_ref. | svc.scientific_parent_invocation×1, table:runtime_episodes×1 |
| report_validation.py | 17 | For A103 returns whose form equals the measurement report schema, resolves the measurement report against the Store in scope. | BindingContext.assignment×1, BindingContext.scope×1, import:a103_investigation×1, import:communication×1, import:domain×1, wf.store×1 |
| scientific_commission_catalog.py | 124 | Declares this owner's commission edges (OWNERS table: gene_context_evidence and its launch/results/launch_api/launch_local/launch_hpc private children) and validates each child's resource_tool_contracts and routes; only registered owners and their declared native children identify a route. | import:resource_tool_information×1 |
| scientific_guidance.py | 13 | A103-specific guidance prefix (gene-context ownership, attribution per locus/neighbour/domain/regulatory footprint, unknown flanks are not absence, one small local job at a time, credit from measured context). | none |
| task_projector.py | 6 | original_task_projector(assignment) = A103ContextCredit(). | import:a103_credit×1 |
| task.py | 275 | The decision loop: replay/restore, decision context assembly (goal, scope, working_state, visible refs, current credit / evidence vector, investigation_progress, credit_binding, time_accounting, pending_work, last outcome, feedback, visual_evidence, deliveries, controller, tools, tool_knowledge, job options, report facts, requested form, current report), annotation-axis variant, completed-work axis results (a103_sheet, target_sheets, tool_attachments, source_contributions); response admission (empty reasoning commit rejected, job_child storage failures, schema/contract feedback, reads.map parameter feedback, minhash selector detail); execute (reason via specialist or Store.commit_reasoning, wait, tool), automatic score updates, credit after each observed outcome, shared.read_information grading retention. | import:episode_source_failure×1, import:library.action_contracts×1, import:library.private_policy_call×1, import:providers×1, import:read_mapping×1, import:runtime×2, runtime.AcquisitionError×2, runtime.ActionFailure×1, runtime.ContractError×2, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×3, runtime.EventTargetError×2, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.inspect×1, runtime._json×5, runtime.json×10, runtime.Mapping×12, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime._plain×3, runtime._references_in×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.sqlite3×2, runtime.subprocess×2, runtime.validate_form×1, runtime.ValidationError×3, runtime._wait_target_feedback×2, runtime.WorkflowError×2, wf.action_schema×1, wf.annotation_context×1, wf.automatic_score_updates×1, wf.binding_context×4, wf.catalog×1, wf.completed_unit×3, wf.completions×3, wf.controller_binding×1, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.delivery_status×1, wf.execute×1, wf.execution_binding×7, wf.extra_report_sources×1, wf.gene_context_evidence_binding×1, wf.inprocess_replay×4, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×10, wf.knowledge×1, wf.last_observed_credit×1, wf.local_outcome_preview×1, wf.next_return×1, wf.pending_work×2, wf.perform_selected_wait×1, wf.permits_common_action×1, wf.reasoning_action_schema×1, wf.receipt_projection×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×4, wf.selected×3, wf.source_credit_binding×1, wf.source_credit_view×2, wf.specialist×3, wf.store×12, wf.store.reference_subset×1, wf.tools×1, wf.tools.model_contract_catalog×1, wf.validate_report×1, wf.working_state×1, table:runtime_actions×10, table:runtime_episodes×1, table:runtime_model_calls×2 |
| task_state.py | 108 | Per-run decision state (calls, feedback, last outcome, report values/basis, interpret_schema) and the old checkpoint/restore/effect recording; failed tool/reason actions still enter the iterator with credit and controller value. | import:episode_source_failure×1, import:runtime×2, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, wf.archive×1, wf.completions×4, wf.context×1, wf.controller_value×1, wf.execution_binding×4, wf.grains×1, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2, table:runtime_actions×5 |
| to_child_execution_progress_assessment.py | 18 | Monitor request: validate the assignment against execution_progress_assessment's schema and pass it unchanged; requires monitoring_progress_refs when annotation task required. | import:communication×1, import:domain×1, svc.annotation_task_required×1 |
| to_child_gene_context_evidence.py | 45 | Request to a recursive A103 child: expanded return form, required return sources, initial report, role allowed, launch instructions, prepare_invocation (or closed context reconstruction). | import:episode_return_records×1, import:runtime×1, runtime.ContractError×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×2, runtime.parse_json_object×1, runtime.validate_form×1, svc.capabilities×1, svc.scientific_closed_request×1, wf.annotation_child_roles×1, wf.available_child_roles×1, wf.binding_context×5, wf.child_initial_report_input×1, wf.context×1, wf.episode_bindings×3, wf.expanded_contract_form×1, wf.gene_context_evidence_binding×1, wf.grains×1, wf.journal×2, wf.launch_instructions×1, wf.run_id×3, wf.services×2, wf.specialist×1, wf.store×1, table:runtime_actions×1, table:runtime_episodes×1 |
| to_child_published_evidence_assessment.py | 45 | Request to the literature child; byte-identical body to to_child_gene_context_evidence (literature branch goes through prepare_assignment, optionally via prepare_child_request). | import:episode_return_records×1, import:runtime×1, runtime.ContractError×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×2, runtime.parse_json_object×1, runtime.validate_form×1, svc.capabilities×1, svc.scientific_closed_request×1, wf.annotation_child_roles×1, wf.available_child_roles×1, wf.binding_context×5, wf.child_initial_report_input×1, wf.context×1, wf.episode_bindings×3, wf.expanded_contract_form×1, wf.gene_context_evidence_binding×1, wf.grains×1, wf.journal×2, wf.launch_instructions×1, wf.run_id×3, wf.services×2, wf.specialist×1, wf.store×1, table:runtime_actions×1, table:runtime_episodes×1 |
| to_children.py | 27 | child_roles; allowed_children via child_policy; prepare_child_request for monitor; required return sources (top-level: gene_context_evidence_results + committed_record_refs; nested: committed_record_refs) when annotation task required. | BindingContext.path×1, svc.annotation_task_required×1 |
| tool_policy.py | 7 | Rejects `sequence.align` (new sequence comparison must go through the shared parent). | import:domain×1 |
| to_parent.py | 59 | Report: fact sources (process report sources + A103 context sources); facts = gene_context_evidence_results (own + received, projected) + received context report facts; resolves scientific namespaces; validate_report checks form, A103 measurement report and that gene_context_evidence_results equal frozen results. | BindingContext.request×1, import:a103_investigation×1, import:gene_context_evidence_reports×1, svc.scientific_frozen_results×1, svc.scientific_received_results×1, svc.scientific_reference×1 |
| waiting.py | 9 | Record suspension condition and forward it to the execution backend. | wf.execution_backend×1, wf.execution_handle×2 |
| yield_estimator.py | 51 | Continuation task name `A103:<context.a103_task.name>` or `A103:<projector kind>`; yield controller chosen from the declaration: accumulation → YieldController, bounded_quality → BoundedYieldController (max = projector.native_score_maximum), completion → CompletionYieldController; credit definition digest and projector yield_method must match. No yield_bindings → no private controller. | BindingContext.assignment×1, BindingContext.role×1, import:numerical×3, yield:BoundedYieldController×2, yield:CompletionYieldController×2, yield:YieldController×2, yield:YieldParameters×6 |

## Carried over

Old files at `97308b94c`, `gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/`. One row per row of `runs/carry_over/functions/a103__gene_context_evidence.tsv` (old file, kind, name); then machinery or episode function, and the new place or the reason it is not carried. New places are files of `gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/` unless a library path is given.

| old file | kind | name | class | new place or reason |
|---|---|---|---|---|
| child_message_owners.py | function | exchange_for_child | machinery | old registry lookup of the two child message exchanges (README 3b C1); each slot is a branch of messages/msg_to_child.py and read_from_child.py |
| child_policy.py | function | allowed_child_roles | episode function | task.py CHILD_SLOTS and offered() (the slots the model is offered; the old filter {gene_context_evidence, literature} grew to the eight slots of the job) |
| configuration.py | class | ScientificConfiguration | episode function | values became settings (task.py, yield_estimator.py read ctx.settings / settings); see the rows of its methods |
| configuration.py | method | ScientificConfiguration.__init__ | episode function | library and tool_library -> settings library_directory / tool_library_directory read in task.py; child_roles -> task.py CHILD_SLOTS; yield_bindings -> settings yield_bindings checked in yield_estimator.py (checked_yield_declaration, open_yield_controller); tool_retrieval and contract_information_profile -> unplaced (scientific_tool_retrieval, composition_information have no library module) |
| configuration.py | method | ScientificConfiguration.contract_information_profile | machinery | contract-information freezing for scientific parents (README 5 item 16: content only in the old shared root); not carried |
| configuration.py | method | ScientificConfiguration._role | machinery | role binding check: each role is its own episode now (README 3a BindingContext.role) |
| configuration.py | method | ScientificConfiguration.permitted_common_actions | episode function | task.py offered() / action() (tool, reason and child kept; wait and redeliver_report are machinery, not carried) |
| contracts.py | function | _object | episode function | already in library: episode_support/records/gene_context_evidence/construction_records.py (_plain, validate_*) and the closed JSON of the form fields |
| contracts.py | function | _ref_schema | episode function | already in library: episode_support/records/gene_context_evidence/construction_records.py validate_option_ref (called through validate_selection in messages/read_from_parent.py) |
| credit.py | class | GeneContextEvidenceCredit | episode function | credit.py credit / credit_view |
| credit.py | method | GeneContextEvidenceCredit.credit_kind | machinery | credit kind label of the old credit view; deleted (README 3d credit_kind) |
| credit.py | method | GeneContextEvidenceCredit.credit_projector | episode function | credit.py credit_view (A103ContextCredit from the library); the mandatory proposed annotation -> messages/read_from_parent.py read_from_parent |
| credit.py | method | GeneContextEvidenceCredit.credit_view | episode function | credit.py credit_view (the number is credit; the components are shown by messages/internal_summary.py) |
| decision_delivery.py | class | ScientificDecisionDelivery | machinery | the old decision machine; its decision inputs are carried in task.py decide (rows below) |
| decision_delivery.py | method | ScientificDecisionDelivery.call | episode function | decision inputs -> task.py decide / present (goal, scope, tools, tool_knowledge, launch library listing, child options as CHILD_ASSIGNMENTS, controller table, feedback); replay of saved calls is machinery; resource_context, shared_information_context, completed/requested action reports, pending_work, execution expectations, resource and native estimates, native event targets, waiting support, contract-information freezing: no home (unplaced) |
| decision_delivery.py | method | ScientificDecisionDelivery.instructions | episode function | task.py instructions |
| decision_delivery.py | method | ScientificDecisionDelivery.conversation_key | machinery | conversation state (README 3a); every ModelRequest carries the full context |
| decision_delivery.py | method | ScientificDecisionDelivery.interpretation_context | machinery | request_context exchange (README 3a); a lookup is a tool |
| decision_delivery.py | method | ScientificDecisionDelivery.exchange_schema | machinery | decision exchange loop |
| decision_delivery.py | method | ScientificDecisionDelivery.exchange_response | machinery | decision exchange loop |
| decision_delivery.py | method | ScientificDecisionDelivery.validate_contract_exchange_request | machinery | saved-request check of the decision exchange (README 3a) |
| decision_delivery.py | method | ScientificDecisionDelivery.validate_contract_exchange_history | machinery | saved-request check of the decision exchange (README 3a) |
| decision_delivery.py | method | ScientificDecisionDelivery.exchange_decision | machinery | decision exchange loop (exchange_decision); replaced by decide / action |
| decision_delivery.py | method | ScientificDecisionDelivery.complete_decision | machinery | replaced by decide returning a ModelRequest |
| decision_presentation.py | function | present_scientific_task | episode function | task.py present (the published scientific A103 prompt rendering over this episode's summary); the prompt-state frames and the HPC, monitor, API-launch, selected-execution and receiver renderers are machinery or belong to the children |
| episode.py | class | GeneContextEvidenceEpisode | episode function | episode.py class GeneContextEvidence (the one class, members from the ten files) |
| episode.py | method | GeneContextEvidenceEpisode.as_record | machinery | the binding's own as_record (binding_record.py); deleted |
| episode.py | method | GeneContextEvidenceEpisode.resource_information_catalog | machinery | link-time declaration and check of the commission routes against the children (scientific_commission_catalog); a wrong commission fails, nothing checks names across episodes |
| episode.py | function | create_execution_bindings | machinery | home factory / table of bindings; the registry is built by the caller of link |
| episode.py | function | create_hpc_bindings | machinery | home factory / table of bindings; the registry is built by the caller of link |
| episode.py | function | create_resource_bindings | machinery | home factory / table of bindings; the registry is built by the caller of link |
| from_child_execution_progress_assessment.py | function | receive_progress | machinery | monitor progress receipt through the old progress provider (README 3b R5); the monitor returns its fields and messages/read_from_child.py takes them |
| from_child_gene_context_evidence.py | function | admit_return | machinery | admission of the child return, saved attempts, receipts (README 3b R1); the system admits the result against the child form; messages/read_from_child.py read_from_child takes it |
| from_child_published_evidence_assessment.py | function | admit_return | machinery | admission of the child return, saved attempts, receipts (README 3b R1); messages/read_from_child.py read_from_child takes it |
| from_children.py | class | ScientificChildReturns | machinery | routing of the monitor progress receipt (README 3b R5) |
| from_children.py | method | ScientificChildReturns.receive_child_progress_for_role | machinery | monitor progress receipt (README 3b R5); the monitor fields are read in messages/read_from_child.py |
| from_parent.py | class | ScientificAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent; see the rows of its methods |
| from_parent.py | method | ScientificAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | ScientificAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the proposed annotation made required in read_from_parent) |
| from_parent.py | method | ScientificAssignment._selection | episode function | messages/read_from_parent.py read_from_parent (validate_selection, axis A103); the resolution against the option library and the tool library -> task.py process_library and tool_catalog |
| from_parent.py | method | ScientificAssignment._assignment | episode function | messages/read_from_parent.py read_from_parent (selection, revision_origin, evidence_task value checks); the in-scope reference checks of the old commission are custody (record_refs fields) |
| from_parent.py | method | ScientificAssignment._invocation | episode function | objective and purpose -> messages/msg_to_child.py (ChildMessage objective, message purpose); the report_schema and initial_report are machinery (the parent writes no return form) |
| from_parent.py | method | ScientificAssignment.prepare_assignment | episode function | messages/msg_to_child.py msg_to_child (the proposed annotation inherited from this episode's own task); the received-by-parent check is custody |
| from_parent.py | method | ScientificAssignment._validate_origin | machinery | reads the old runner's recorded preparation (scientific_preparation, runtime tables); only the value shape is checked, in messages/read_from_parent.py (validate_revision_origin) |
| from_parent.py | method | ScientificAssignment.prepare_invocation | machinery | closed-commission reconstruction from runtime_actions and the filled-process digests; the commission itself -> messages/msg_to_child.py |
| from_parent.py | method | ScientificAssignment.restore_closed_process | machinery | restore of a closed request (checkpoint/restore, README 3e) |
| from_parent.py | method | ScientificAssignment.validate_context | machinery | identity re-checks of the filled process record (digests, mechanics_binding, as_record) |
| from_parent.py | method | ScientificAssignment.validate_execution_context | machinery | closed request inspect/replay guard (recorded replay is the system's) |
| from_parent.py | method | ScientificAssignment._original_selection | episode function | messages/read_from_parent.py read_from_parent (parent_input selection) |
| from_parent.py | method | ScientificAssignment._proposed_selection | episode function | task.py process_revise (the proposed child selection) |
| from_parent.py | method | ScientificAssignment.initial_references | machinery | custody: evidence_refs and proposed_annotation_ref are record_refs fields of ASSIGNMENT_FORM (README 3b P2) |
| goal.py | class | ScientificGoal | episode function | goal.py GOAL |
| goal.py | method | ScientificGoal.instructions | episode function | goal.py GOAL (the published-instruction variant, with scientific_guidance first); the legacy support-metadata variant is not carried: its continuation raised scientific_task_credit_not_declared, so it could not run |
| instructions.py | function | instructions | episode function | task.py instructions (goal, reasoning-commit requirement, tool knowledge, launch library; the redeliver_report, wait, native-event and exchange paragraphs describe removed actions) |
| internal_summary.py | class | ScientificSummary | episode function | messages/internal_summary.py internal_summary and task.py process_library |
| internal_summary.py | method | ScientificSummary.decision_context | episode function | selection, evidence axis view, thought pattern fields, child tool info -> task.py process_library (outcome) and present; assignment and the permitted children -> messages/internal_summary.py (assignment) and task.py CHILD_SLOTS |
| internal_summary.py | method | ScientificSummary.initial_decision_context | episode function | received_gene_context_execution (a103_hpc.execution_findings) has no library module: not shown (unplaced) |
| operations.py | class | ScientificOperations | episode function | task.py TOOLS (operation, process_revise, process_library, tool_catalog, lookups, reason, report) |
| operations.py | method | ScientificOperations._information_catalog | episode function | task.py _available (the registry catalog the tool library compares selections with) |
| operations.py | method | ScientificOperations._closed_tool_resolution | machinery | resolution of a closed request's frozen contracts (restore_closed_process) |
| operations.py | method | ScientificOperations._tool_resolution_for | episode function | task.py tool_catalog (ScientificToolLibrary.resolve_invocations) |
| operations.py | method | ScientificOperations._tool_resolution | episode function | task.py tool_catalog (resolution and the reserved-name check) |
| operations.py | method | ScientificOperations.catalog | episode function | task.py tool_catalog (direct routes) and offered() (process.revise); process.execution (execution_planning.catalog) has no library module: unplaced |
| operations.py | method | ScientificOperations.common_tool_names | episode function | task.py RESERVED_NAMES |
| operations.py | method | ScientificOperations.execute | episode function | task.py operation, process_revise (and action); source-byte operand authentication is machinery (custody); process.execution unplaced |
| received_context_report.py | function | received_report_facts | episode function | messages/final_to_parent.py (a103_received_context_records; raises unplaced:a103_investigation.received_context_records when selected) |
| received_execution_context.py | function | received_execution_context | episode function | no library module (a103_hpc.execution_findings): not shown to the model (unplaced) |
| report_delivery.py | class | ScientificReportDelivery | machinery | report form machinery (runtime_forms, form_with_facts, release); the result is messages/final_to_parent.py final_to_parent |
| report_delivery.py | method | ScientificReportDelivery.finish | machinery | report saving and release (README 3b D1, D3); messages/final_to_parent.py final_to_parent |
| report_snapshot.py | function | complete_scientific_snapshot | machinery | completion snapshot (initial credit, controller credit, episode yield, parent invocation) is recorded by the system |
| report_validation.py | function | validate_axis_report | episode function | no library module (a103_investigation.measurement_report_schema, resolve_measurement_report); the old form it checked no longer exists (unplaced) |
| scientific_commission_catalog.py | function | _declarations | machinery | link-time declaration/check of the children's resource_tool_contracts and routes (a check of names across episodes; rule 1) |
| scientific_commission_catalog.py | function | _registered | machinery | registry check of owners (binding table) |
| scientific_commission_catalog.py | function | resource_information_catalog | machinery | link-time commission route catalog over the registry; not carried |
| scientific_guidance.py | function | scientific_guidance | episode function | goal.py GOAL (first paragraph) |
| task.py | class | GeneContextEvidenceTask | episode function | task.py decide, action and TOOLS; see the rows of its methods |
| task.py | method | GeneContextEvidenceTask.next | episode function | task.py decide (context assembly, lookups first) and messages/internal_summary.py; replay/restore, journal rows, pending deliveries, SourceEnd, source failure recording are machinery |
| task.py | method | GeneContextEvidenceTask.apply_response | episode function | task.py action (operation offered, closed JSON operands, empty_reasoning_commit rejected, reads.map parameter feedback in the operation tool, held records of a child commission); job_child storage feedback, redelivery, record_effect are machinery |
| task.py | method | GeneContextEvidenceTask.execute | episode function | task.py tools: reason (commit_reasoning with ctx.operation_key), operation (registry), report; wait, journal rows, automatic score updates, credit after each outcome (the system prices every unit) and the failure-enters-the-iterator rule (a failed operation is returned as an outcome) are machinery |
| task_projector.py | function | original_task_projector | episode function | credit.py credit_view and yield_estimator.py (A103ContextCredit) |
| task_state.py | class | ScientificTaskState | machinery | per-run decision state, checkpoint and restore (README 3e) |
| task_state.py | method | ScientificTaskState.__init__ | machinery | decision state kept between calls; the view and summary hold it |
| task_state.py | method | ScientificTaskState.bind_execution_context | machinery | old execution context binding |
| task_state.py | method | ScientificTaskState.record_execution_failure | episode function | a failed selected operation is the unit's outcome: task.py operation returns failure_outcome (library tools/unit_outcomes.py); the journal rows and controller value are the system's |
| task_state.py | method | ScientificTaskState.restore_checkpoint | machinery | checkpoint/restore (README 3e) |
| task_state.py | method | ScientificTaskState.restore | machinery | checkpoint/restore, recover_commissions (README 3b C5, 3e) |
| task_state.py | method | ScientificTaskState.record_effect | machinery | record_effect (README 3e F6) |
| task_state.py | method | ScientificTaskState.checkpoint | machinery | checkpoint (README 3e) |
| to_child_execution_progress_assessment.py | function | prepare_request | episode function | messages/msg_to_child.py msg_to_child (slot execution_progress_assessment: the assignment passed on unchanged) |
| to_child_execution_progress_assessment.py | function | required_return_sources | episode function | messages/msg_to_child.py required_return_sources (monitoring_progress_refs) |
| to_child_gene_context_evidence.py | function | prepare_request | episode function | messages/msg_to_child.py msg_to_child (slot gene_context_evidence); the expanded return form, initial report and closed-commission reconstruction are machinery |
| to_child_published_evidence_assessment.py | function | prepare_request | episode function | messages/msg_to_child.py msg_to_child (slot published_evidence_assessment, a private copy of the same body) |
| to_children.py | class | ScientificChildRequests | episode function | messages/msg_to_child.py and task.py CHILD_SLOTS; see the rows of its methods |
| to_children.py | method | ScientificChildRequests.child_roles | episode function | task.py CHILD_SLOTS |
| to_children.py | method | ScientificChildRequests.allowed_children | episode function | task.py CHILD_SLOTS and offered() |
| to_children.py | method | ScientificChildRequests.prepare_child_request | episode function | messages/msg_to_child.py msg_to_child |
| to_children.py | method | ScientificChildRequests.required_return_sources | episode function | messages/msg_to_child.py required_return_sources (top-level: gene_context_evidence_results and committed_record_refs; nested: committed_record_refs) |
| to_parent.py | class | ScientificReport | episode function | messages/final_to_parent.py RETURN_FORM, final_to_parent, validate_report |
| to_parent.py | method | ScientificReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (selectable fields under the old fact source names) |
| to_parent.py | method | ScientificReport.facts | episode function | messages/final_to_parent.py final_to_parent; gene_context_evidence_results (build/merge/project_process_result) and a103_received_context_records have no library module and raise unplaced when selected |
| to_parent.py | method | ScientificReport.resolve | machinery | receipt-ledger reference resolver (README 3b D2); held records are asked with records.holds (summary report_sources_held) |
| to_parent.py | method | ScientificReport.validate_report | episode function | messages/final_to_parent.py validate_report (finding form and held references); the measurement-report resolution and the frozen-results equality are not carried |
| tool_policy.py | function | validate_tool_name | episode function | task.py operation (sequence.align refused, a103_new_sequence_comparison_requires_shared_parent) |
| waiting.py | class | ScientificWaiting | machinery | wait/suspension machinery (README 3b) |
| waiting.py | method | ScientificWaiting.suspension_changed | machinery | wait/suspension machinery (README 3b) |
| yield_estimator.py | class | GeneContextEvidenceYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | GeneContextEvidenceYield.private_yield_binding | episode function | yield_estimator.py (a declaration is always required: checked_yield_declaration) |
| yield_estimator.py | method | GeneContextEvidenceYield.continuation_task | episode function | yield_estimator.py (task name A103:<a103_task_name> or A103:<projector kind>; the name is read by messages/read_from_parent.py) |
| yield_estimator.py | method | GeneContextEvidenceYield.yield_controller | episode function | yield_estimator.py yield_controller (bounded quality: checked_yield_declaration, open_yield_controller with the projector maximum) |
