# a101/sequence_homology_evidence — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/<file>`
(only files directly in this folder plus `scoring/`; child episode folders and `tests/` are not covered here).
Old binding class: `SequenceHomologyEvidenceEpisode` (`binding_path = 'sequence_homology_evidence'`,
`commissioning_parent = 'legacy_annotation'`, `roles = entry_roles = ('sequence_homology_evidence',)`), decision
source `ScientificInvestigationTask`. Contract version `sequence_homology_evidence_episode_v10`, axis `A101`.

## What it is for (its goal, in its own words)

`goal.py` `scientific_guidance()`:

> A101 owns sequence similarity evidence. For an NCBI BLAST search that may run remotely, use the configured
> Launch API job when available: submit once, return its execution_handoff_refs to this episode, and let a
> separately selected monitor or Results episode check that same RID. The handoff is operational progress, not
> homology evidence. If that RID is waiting and no useful A101 work remains, return the handoff reference and
> current credit to your parent so it can choose another evidence axis. Consider ClusteredNR (nr_clustered_seq)
> for an initial blastx search; choose the database for the scientific question and preserve the selected
> database in the original request.

followed by one of two bodies, chosen by the selected evidence axis entry's `entry_version`:

- **published instruction entry** (`entry_version == INSTRUCTION_VERSION`): "Determine what the supplied target does
  within the parent's assigned question, scope and constraints. Start with the supplied sequence, selected file
  contents or snippets ... No initial candidate annotation or publicly searchable name is required. Possible
  functions can emerge from the evidence ... Choose an available tool action, commit a scientific interpretation
  through the reasoning action, commission a scoped child with its own typed return form, or wait for selected
  pending work ... Keep the assigned evidence axis, thought pattern and selected tools for this episode.
  process.revise prepares a different thought pattern and/or tool selection for a new child; it does not change
  this episode or start that child ... The configured controller owns continuation. Waiting and unchanged
  observations do not manufacture progress."
- **evidence-axis entry** (otherwise): "Investigate the parent's assigned scientific problem iteratively in the
  shared Episode loop. The selected scientific support proposition and operands define the support problem; the
  thought pattern supplies alternatives and outcome-sensitive guidance; the selected real tools supply their exact
  callable contracts ... annotation_support_routes describes the actual separately bound annotation policy's kind
  dispatch ... Metadata itself earns no credit ... Request the recorded sequence_homology_evidence_results source
  in child forms when their process relationships and existing closed credit/yield are needed for steering ..."

`configuration.py` sets `replaces_default_instructions = True` when every evidence_axis header in the library is a
published instruction entry; then the goal text above *replaces* the generic `INSTRUCTIONS` prompt instead of
being appended to it.

## Task and instructions

`task_instructions.py` composes the model instructions:
1. base `INSTRUCTIONS` from the old shared `library/literature_investigation_prompt` (the long generic
   "iterative scientific annotation improvement, not a tool itinerary" prompt; a copy is inlined in the
   execution_job_submission episode's own `task_instructions.py`), replaced or extended by the goal text;
2. `REASONING_COMMIT_REQUIREMENT` when `reason` is permitted (an all-empty commit is rejected before acquisition
   unless `evidence_processing.kind=no_applicable_evidence`);
3. tool-knowledge instructions and launch-instruction-library instructions when those inputs are present;
4. the fixed `pending_child_delivery` → `redeliver_report` repair paragraph;
5. when `wait` is permitted, the in-process `pending_child_` wait paragraph (event `returned`, `after_cursor 0`,
   `reconsider_at null`; waiting earns no credit);
6. when native event targets are configured and `wait` permitted, the native_event_targets paragraph;
7. under the `decision_exchange_v1` protocol, the "fresh provider conversation / restored_episode_history"
   paragraph is replaced by the request_context / `episode.history view=records` paragraph.

`task.py` (`ScientificInvestigationTask`): one decision per unit. `next()` replays saved model calls/actions,
builds `decision_state(view)` and `action_schema`, calls the model (`call`), and `apply_response()` admits the
selection: a `reason` selection is validated against the reasoning envelope and rejected if every commit section
is empty (unless the binding says it has task content); other selections against the action schema. Rejections
become typed feedback (action_contract, contract_error with repair text for `closed_top_level_form_required`,
`component_native_return_channels_required` fact-source repair, BV-BRC MinHash `results` input_detail,
`reads.map` parameter feedback) and record a `rejected` effect without an executed unit. A job_child storage /
subprocess / acquisition error becomes `job_assignment` feedback (this exception arm exists only in this head
episode, not in execution_job_submission/api/hpc). The report_update is admitted against the interpretation
schema and validated; it is kept as `report_values` with its `report_basis` refs. `execute()` runs `reason`
(binding `execute_reasoning` or `store.commit_reasoning`, with `account_invocation` when interpretation_accounts
are present), `wait`, or a tool; it appends `pending_work_after_action`; failed/invalid outcomes still enter the
iterator; credit is read after automatic score updates (a wait carries the last observed credit); a
`shared.read_information` tool retains shared grading results; an outcome that is not an observed action outcome
raises `ActionFailure`. The head (unlike its children) calls `validate_execution_context` before executing and
before each new model call, so a closed request can be inspected/replayed but never dispatches new work.

`task_decision.py` (`ScientificTaskDecision`): model call with saved request/response replay, contract-information
profile freeze/validation, literature numerical contract freeze, decision-exchange protocol (`request_context`
lookups of `child_options`, `composition_information`, or own attempts; `select_action` ends the exchange),
receipts of `visible_record_refs` as `decision_input` (skipped for job sources and received-record contexts),
`restored_episode_history` for a fresh provider session. The exchange yield table comes from the credit
presentation (standalone vs commissioned).

`task_state.py`: per-episode state (calls, feedback, last outcome, report values/basis, restore/checkpoint,
`record_execution_failure` turns an unexpected execution exception into a failed outcome that still enters the
iterator with its credit).

## What it reads from its parent's assignment

`from_parent.py` + `scientific_contracts._ASSIGNMENT` (closed schema):

| Field | Meaning |
|---|---|
| `selection` (required) | `version` = `SELECTION_VERSION`; `evidence_axis` option ref (slot `evidence_axis`, option_id const `A101`, library_id, entry_sha256); `thought_pattern` option ref (`P<n>`); `child_tool_info` = unique list of `{name, resources: api/local/hpc}` (recorded form adds `description`, `instructions`). |
| `proposed_annotation_ref` | The proposed annotation this task evaluates. Required when the services say an annotation task is required; inherited from the parent and must equal it; must have been received by the parent and be in scope (`hypothesis`). |
| `evidence_refs` (required) | Unique in-scope references the parent supplies. |
| `constraints` (required) | Free object. |
| `context` (required) | May carry `evidence_task` (`evidence_axis_task_v1`, kind `whole_axis_findings`, axis `A101`, `credit_unit` > 0) and the original task name `a101_task`. |
| `revision_origin` | `sequence_homology_evidence_revision_origin_v1` with `parent_invocation_ref` and `preparation_operation_ref`; validated against the parent's recorded `process.revise` preparation (selection digest, proposal, arguments). |

Also from the request: `goal.objective`, `report_contract.decision` (purpose), `report_contract.measurements.schema`
(closed report schema; requested alignment-site projections are checked), `message.initial_report`,
`message.scope`, `message.scientific_invocation_ref` and `message.sequence_homology_evidence` (the filled-process
record: selection, assignment digest, invocation digest and this binding's `as_record()`; all are re-verified on
every `validate_context`). The selection's library must be this binding's library; the axis entry must be an
instruction or evidence-axis entry; tools are resolved through the tool library against the scope's information
catalog. `initial_references` = evidence_refs + proposed_annotation_ref.

## Children it may commission

Child roles are configured (`child_roles`, must include itself). `episode.py` maps (role, binding path) to its own
preparer/receiver:

| Role | Child binding | Sends (to_child_*) | Takes back (from_child_*) |
|---|---|---|---|
| `sequence_homology_evidence` | itself (recursive) | `to_child_sequence_homology_evidence.prepare_request`: expanded return form, initial report, then `prepare_invocation` with `{objective: goal, purpose, report_schema, initial_report}`; a completed earlier commission with a closed child request is re-authenticated (`closed_context`) instead of re-prepared. Returns the assignment and the filled-process record. A child must request `sequence_homology_evidence_results` + `committed_record_refs` when the parent is the root and an annotation task is required, else `committed_record_refs`. | `from_child_sequence_homology_evidence`: `admit_return` admits the child form once per `delivery_ref` (saved attempt, failure kept), then `receive_report` takes its record refs into receipts (`child_form` / `report_redelivery`), progress provider forms, native timing receipts and tool attributions. |
| `literature` | `published_evidence_assessment` | `to_child_published_evidence_assessment.prepare_request`: scope, expanded form, initial report, child's `prepare_assignment` of the selection's assignment. | `from_child_published_evidence_assessment.receive_report` (same receipt custody, without the binding-path guard). |
| `launch` | `execution_job_submission` | `to_child_execution_job_submission.prepare_commission`: as above; binding path must be `sequence_homology_evidence/execution_job_submission`; an HPC launch must request `execution_handoff_refs`. Launch requires `execution_handoff_refs` back when the parent is this episode and an annotation task is required. | `from_child_execution_job_submission.receive_report` + `admit_return` (handoff refs into receipts). |
| `launch` | `resource_work_submission` | `to_child_resource_work_submission.prepare_commission` (same shape). | `from_child_resource_work_submission`. |
| `monitor` | `execution_progress_assessment` | `to_child_execution_progress_assessment.prepare_commission`; the assignment is first passed through `prepare_request` (validated against the child's `_ASSIGNMENT`); the child must return `monitoring_progress_refs` when an annotation task is required. | `from_child_execution_progress_assessment.receive_progress`: reads every `episode_progress` reference through the progress provider and records them once under a content digest of form+schema+scope; plus the ordinary `receive_report`. |
| `results` | `execution_result_acquisition` | `to_child_execution_result_acquisition.prepare_commission`. | `from_child_execution_result_acquisition`. |
| `results` | `resource_result_acquisition` | `to_child_resource_result_acquisition.prepare_commission`. | `from_child_resource_result_acquisition`. |

`process.revise` prepares (but never starts) an alternative child selection: same evidence axis, a different
thought pattern and/or tool set; the child assignment must copy `selection` and `revision_origin`.

## Decision state and what it shows the model

`decision_state.py` picks the presentation: **standalone** (`StandaloneScientificPresentation`) when the episode is
the run root or the current credit is `annotation_axis_credit`, else **commissioned**. Both show: goal, scope,
working_state, visible_record_refs, current_credit, current_evidence_vector (axis components),
investigation_progress (retained_finding_count, inactive_dependencies, detail_pages) when receipts are projected,
credit_binding, time_accounting, pending_work, last_local_outcome, feedback, visual_evidence (last `image.view`),
report_deliveries, controller state and binding, tools, tool_knowledge, available_report_facts, requested purpose
and form, current_report_update and basis, report_lifecycle, monitoring information credit, annotation context,
and this binding's `decision_context` (`internal_summary.py`): `sequence_homology_evidence` = {selection,
initial_selection_sha256, evidence_axis (instruction view) or annotation view, annotation_support_routes (for
non-published entries), thought_pattern (id, name, description, use_when, live_alternatives, decision_guidance,
outcome_contingencies, boundary), child_tool_info or tools, assignment, permitted_children}. Standalone with
annotation-axis credit instead hides working state and child reports and shows proposed_annotations,
annotation_comparisons and the controller's arms/annotation_credits/root_score/decision.

`decision_inputs.py` adds per call: resource_context, shared_information_context, launch_instruction_library and
selected_launch_instructions, child_options, the binding's `initial_decision_context`, completed_action_reports,
requested_action_history (HPC contexts), pending_work, execution_expectations and job_execution_options, resource
tool estimates (job-source and context estimates), native execution expectations, native_event_targets,
waiting_support, contract_information_profile.

## Tools it offers

`permitted_common_actions = ('tool', 'reason', 'child', 'wait', 'redeliver_report')`.
Common tools (`_COMMON_TOOLS`): process.search/entry/sources/tools, knowledge.search/entry/read, episode.history,
episode.credit, episode.annotation_score, episode.monitoring_information, episode.estimate_wait,
shared.request_information/publish_information/resolve_information_need/read_information/list_information.
Own catalog (`tool_selection.py`): the selection's direct-route tools resolved from the tool library (selected
tools may not reuse a common tool name), `process.revise`, and (`execution_planning.py`) `process.execution`
(reads a selected tool/resource pair's execution recipe, resource context, available HPC commissions and up to 64
age-weighted timing observations per profile; operational planning only, scientific_credit 0).
`scientific_operations.py` executes `process.execution`, `process.revise`, authenticates source byte operands for
material/source tools, passes `permitted_record_refs` to `result.blast.hsp` and `source.locate`, and dispatches the
rest to the services' tool executor. Argument/reference errors return `invalid` outcomes (which still enter the
iterator).

## How its credit is counted

`credit.py`: kind `scientific`; projector `A101SequenceCredit` (`native_correspondence_credit.py` +
`scoring/native_correspondence.py`) when the axis entry is an instruction or evidence-axis entry; with private
yield bindings a `proposed_annotation_ref` is required. Projector record: kind
`a101_native_sequence_correspondence`, sheet `convention_015_native_correspondence`, supported algorithms
blastp/phmmer/hmmsearch/hmmscan, inverse bit scales from `a101_scoring.SCALES`, receipt =
explicit_known_record_refs, target aggregation = supplied-scope length-weighted mean, function-specific support
separate/unknown without grounded inputs, interpretation = dimensionless native correspondence (not a function
probability), duplicates = per-position max (not sum of hits or assertions). It requires episode receipts and
known record refs; `yield_method = 'bounded_quality'`, `native_score_maximum = 1.0`. The scorer routes native
grading only for tool observations whose source is native BLAST / phmmer or carries a BLAST or HMMER grading
sheet, within the receipt-known references and the scope's target segments. The credit view itself comes from the
services' `scientific_credit`.

## Continuation (yield estimator and settings)

`yield_estimator.py`: task key `A101:<context.a101_task.name>` or `A101:<projector kind>`. Each task key needs an
explicit declaration `{kind, cutoff, parameters: {uncertainty_alpha}, credit_definition}`; the declaration's
`credit_definition` must equal the projector record by digest and its `kind` must equal the projector's
`yield_method`. Kinds: `accumulation` → YieldController(cutoff), `bounded_quality` → BoundedYieldController(cutoff,
projector.native_score_maximum), `completion` → CompletionYieldController(cutoff). With A101SequenceCredit this is
the **bounded quality** estimator with max 1.0. Without yield bindings no private controller is returned.

## What it reports to its parent

`to_parent.py`: required return sources (`sequence_homology_evidence_results` + `committed_record_refs` for a
root-level parent of an annotation task, else `committed_record_refs`); fact sources = the library/tool-library
report sources plus alignment-site fact sources; facts = `sequence_homology_evidence_results` (own process result
from the completion snapshot merged with received child process results, projected) plus every requested
alignment-site projection, paged 64 at a time from own action results. `validate_report` checks references, frozen
site returns, and that every `sequence_homology_evidence_results` field equals the frozen process result by
digest. `report_delivery.py`: without a report contract returns `{credit, pending_handles, ...current report
facts}`; with one fills the form once from facts + `report_values` and saves it. `completion_report.py` adds
initial_credit, credit, controller_credit, episode_yield and parent_invocation_ref to the completion snapshot.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| goal.py | 18 | A101 guidance text and the two goal bodies (instruction vs evidence-axis entry). | `self.library`, `self.validate_context` (binding mixins) only. |
| task_instructions.py | 24 | Instruction composition order and the redelivery / wait / native-event / exchange paragraphs. | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol`; import `library.literature_investigation_prompt`. |
| configuration.py | 39 | Child roles must include itself; library/tool library records; replaces_default_instructions rule; per-task yield declarations {kind, cutoff, parameters{uncertainty_alpha}, credit_definition} validated by constructing the controller. | imports `scientific_tool_retrieval.configuration`, `composition_information.CONTRACT_INFORMATION_PROFILE`, `numerical.{Bounded,Completion,}YieldController, YieldParameters`. |
| binding_record.py | 8 | `as_record()` identity (version, library, tool library, child roles, tool retrieval, profile, yield bindings). | none. |
| scientific_contracts.py | 58 | Assignment / selection / revision-origin / evidence-task schemas, axis A101, common tool names, scientific namespaces. | imports `communication`, `domain`, `episode_bindings.reference_in_context`, `sequence_homology_evidence_records`, `sequence_homology_evidence_reports`, `scientific_support_metadata`, `evidence_axis_contracts`, `evidence_axis_instructions`, `sequence_homology_evidence_library`, `library.alignment_site_returns`. |
| from_parent.py | 182 | Assignment admission, proposed-annotation inheritance, revision-origin check, filled-process record, closed-commission re-authentication, execution-context guard. | `self.services.annotation_task_required`×2, `.proposed_annotation_for`, `.reference_in_scope`×2, `.scientific_preparation`×2, `.scientific_parent_preparation`, `.scientific_saved_request`, `.workflow` → `workflow.sequence_homology_evidence_binding`, `workflow.store`, `workflow.journal.row('runtime_actions')`, `workflow.run_id`; `EpisodeReturnRecords` (episode_return_records). |
| process_state.py | 29 | Restore a closed request's recorded filled process and require identity. | `self.services.scientific_closed_request`. |
| alternate_process_selection.py | 10 | `process.revise` proposal: same axis, new thought pattern + tools. | none. |
| tool_selection.py | 59 | Own catalog: direct tools, `process.revise` description (two wordings), `process.execution`; tool retriever. | `self.services.tool_information_catalog`, `.tool_catalog`×2, `.workflow`; import `scientific_tool_retrieval.ScientificToolRetriever`. |
| execution_planning.py | 36 | `process.execution` recipe/timing read (64 observations per profile, max 8 profiles). | `workflow.episode_bindings.roles/for_role('hpc')`, `workflow.resource_context`; imports `..execution_planning.memory_for`, `..execution_memory.validate_profile`, `..execution_contracts.obj`. |
| scientific_operations.py | 34 | Execute `process.execution`, `process.revise`, source byte authentication, record-ref permissions. | `self.services.authenticate_source_byte_operands`, `.execute_tool`. |
| internal_summary.py | 26 | The `sequence_homology_evidence` decision context block. | `self.services.scientific_support_routes`. |
| decision_state.py | 16 | Standalone vs commissioned presentation choice. | none directly. |
| standalone_credit_presentation.py | 76 | Root/annotation-axis presentation (proposed_annotations, comparisons, arms). | `self.workflow.store`×3, `.working_state`, `.journal`×3 (`runtime_actions`), `.run_id`, `.local_outcome_preview`, `.source_credit_view`, `.receipt_projection`, `.source_credit_binding`, `.pending_work`, `.delivery_status`, `.controller_binding`×2, `.catalog`, `.knowledge`, `.extra_report_sources`, `.is_scientific_source`, `.annotation_context`, `.specialist`, `.binding_context`, `.tools`; `FACT_MEANINGS/FACT_SOURCES/_references_in/_category_yield_parameters/yield_table` from runtime; `episode_work_report.completed_action_reports`; `live_runtime_functions.bind_functions`. |
| commissioned_credit_presentation.py | 60 | Commissioned presentation (always shows child reports). | same set as standalone (journal×2). |
| decision_inputs.py | 77 | Per-call context additions listed above. | `self.workflow.resource_context`, `.shared_information_context`, `.launch_instructions`×2, `.available_child_roles`, `.episode_bindings.initial_decision_context`, `.binding_context`×2, `.execution_expectations`, `.job_episodes`×4, `.store`×2, `.resource_estimator`×5, `.is_job_source`, `.native_estimation_context`, `.native_event_information`×2, `.permits_common_action`, `.waiting_support`, `.pending_work`; runtime `child_option_information`; `hpc_prompt.is_hpc_context`; `episode_work_report.requested_action_history`; `bind_functions`. |
| task.py | 248 | Decision/admission/execution rules above (head-only job_child failure arm and execution-context guard). | `self.workflow.journal`×7 (`runtime_episodes`, `runtime_actions`×8, `runtime_model_calls`×2), `.inprocess_replay`×4, `.execution_binding`×7, `.completions`×3, `.completed_unit`×3, `.selected`×3, `.next_return`, `.resolve_pending_deliveries`, `.action_schema`, `.delivery_resolution_inputs`, `.decision_exchanges`×3, `.permits_common_action`, `.reasoning_action_schema`, `.store`×9, `.specialist`×2, `.binding_context`×3, `.resolver`, `.validate_report`, `.sequence_homology_evidence_binding`, `.run_id`×3, `.execute`, `.pending_work`, `.receive_native_outcome`, `.receive_outcome`, `.automatic_score_updates`, `.last_observed_credit`, `.source_credit_view`, `.retain_shared_grading_results`, `.controller_value`×2, `.services`; `providers.ModelCallError`; `episode_source_failure.record_source_failure`; `library.read_mapping_values`; many runtime names (SourceEnd, ActionFailure, ReportRedelivery, ...). |
| task_decision.py | 292 | Model-call / exchange protocol rules. | `self.workflow.journal`×3 (`runtime_model_calls`×8), `.contract_information_profile`, `.validate_contract_information`×5, `.numerical_contracts`, `.decision_protocol`×3, `.decision_exchanges`×4, `.freeze_literature_numerical_contracts`, `.freeze_contract_information`, `.receipts`×4, `.is_job_source`×2, `.uses_received_record_context`×2, `.provider`×4, `.history_preview`, `.store`×2, `.execute`, `.contract_information_reply`, `.services.decision_exchange_instructions`, `.sequence_homology_evidence_binding`, `.binding_context`; runtime `yield_table`, `_category_yield_parameters`, `child_option_information`, `composition_lookup_schema`, `lookup_attempts`, `state_frame`, `model_snapshot`. |
| task_state.py | 115 | Per-episode state, restore, failure-as-outcome. | `self.workflow.context`, `.grains`, `.archive`, `.journal`×5 (`runtime_actions`×5), `.store`×2, `.source_credit_view`, `.controller_value`, `.execution_binding`×4, `.completions`×4, `.inprocess_replay`×7, `.recover_commissions`, `.progress_provider`×2, `.run_id`; runtime `Episode.identity`, `ActionLeaf`, `EFFECT_VERSION`; `episode_source_failure`. |
| waiting.py | 30 | Selected wait; event-target failure becomes a failed outcome. | `self.workflow.perform_selected_wait`, `.execution_handle`×2, `.execution_backend`; runtime `EventTargetError`, `_wait_target_feedback`. |
| report_delivery.py | 34 | Final result / form fill. | `self.workflow.source_credit_view`, `.pending_handles`, `.episode_bindings.current_report_facts`, `.binding_context`, `.release`×2, `.journal`×2 (`runtime_forms`), `.facts`; runtime `form_with_facts`, `Record`. |
| completion_report.py | 14 | Completion snapshot fields (initial_credit, credit, controller_credit, episode_yield, parent_invocation_ref). | Workflow method: `self.journal.row('runtime_episodes')`, `self.source_controller_credit`, `self.services.scientific_parent_invocation`. |
| credit.py | 27 | Scientific credit kind; A101SequenceCredit projector; proposed annotation required with yield bindings. | `self.services.scientific_credit`. |
| native_correspondence_credit.py | 19 | Projector record and bounded_quality / max 1.0. | imports `library.a101_scoring.VERSION, SCALES`. |
| scoring/native_correspondence.py | 193 | Native sequence-correspondence sheet routing (A101 sheet). | imports `library.a101_scoring`, `tool_grading_artifacts`, `component_assessment_dependencies`, `evidence_geometry`, `library.a101_contribution`; no workflow members. |
| yield_estimator.py | 54 | Task key rule and estimator choice (see above). | imports `numerical.YieldController / BoundedYieldController / CompletionYieldController / YieldParameters` (old yield names). |
| to_parent.py | 76 | Return sources, facts, report validation. | `self.services.annotation_task_required`, `.scientific_received_results`, `.alignment_site_own_action_results`, `.scientific_reference`, `.alignment_site_frozen_facts`, `.scientific_frozen_results`; import `sequence_homology_evidence_reports.project_process_result`. |
| episode.py | 99 | Binding identity, permitted actions, (role, binding path) → own preparer/receiver map, monitor request/progress hooks; also builds sibling execution/resource bindings. | `binding_path`, `commissioning_parent='legacy_annotation'`, `roles`, `entry_roles`, `decision_source_type` (old registry declarations). |
| to_child_sequence_homology_evidence.py | 61 | Recursive child invocation (objective, purpose, report schema, initial report; closed child re-authentication). | runner-as-self: `self.expanded_contract_form`, `.episode_bindings.for_child`×3/`.entry_roles`, `.binding_context`×5, `.child_initial_report_input`, `.specialist`, `.available_child_roles`, `.annotation_child_roles`, `.services.capabilities`, `.launch_instructions`, `.sequence_homology_evidence_binding`, `.journal`×2 (`runtime_actions`, `runtime_episodes`), `.context`, `.grains`, `.store`; `_runtime.Episode.identity`; `EpisodeReturnRecords`; `services.scientific_closed_request`. |
| to_child_published_evidence_assessment.py | 33 | Literature child commission. | `workflow.store.validate_scope`, `.expanded_contract_form`, `.episode_bindings.for_child`×2/`.entry_roles`, `.binding_context`×4, `.child_initial_report_input`, `.specialist`, `.available_child_roles`, `.annotation_child_roles`, `.services.capabilities`, `.launch_instructions.materialize`, `.run_id`. |
| to_child_execution_job_submission.py | 32 | Launch child commission; HPC launch must request execution_handoff_refs. | same set as above. |
| to_child_execution_progress_assessment.py | 43 | Monitor request validation + commission; monitoring_progress_refs requirement. | same set; imports `communication.plain`, `domain.validate_schema`, child `contracts._ASSIGNMENT`. |
| to_child_execution_result_acquisition.py | 29 | Results child commission. | same set. |
| to_child_resource_result_acquisition.py | 29 | Results (resource) child commission. | same set. |
| to_child_resource_work_submission.py | 32 | Launch (resource) child commission. | same set. |
| from_child_sequence_homology_evidence.py | 96 | Recursive child admission and receipt custody. | runner-as-self: `self.journal` (`runtime_actions`), `self.store.db` (`runtime_report_attempts`×3), `.save_attempt`×2, `.delivery_feedback`, `.receive_form`, `.receipts`×3, `.is_job_source`×2, `.binding_context`×4, `.progress_provider`×4, `.specialist`, `.episode_bindings.received_form_references`, `.native_timing_information`, `.job_episodes`×2, `.receive_tool_attributions`; `delivery_counterpart`, `EpisodeReturnRecords`, `_runtime.*`. |
| from_child_published_evidence_assessment.py | 78 | Literature child receipt custody. | `workflow.receipts`×3, `.is_job_source`×2, `.store`×7 (`runtime_report_attempts`×3), `.progress_provider`×4, `.specialist`, `.binding_context`×4, `.episode_bindings`, `.native_timing_information`, `.job_episodes`×2, `.receive_tool_attributions`, `.run_id`×6; `admit_return` as Workflow method; `EpisodeReturnRecords`; `bind_functions`. |
| from_child_execution_job_submission.py / _execution_result_acquisition.py / _resource_result_acquisition.py / _resource_work_submission.py | 82 each | Same custody with a guard that the delivered role/binding path is that child. | same set + `delivery_counterpart.child_role_for_delivery`×2. |
| from_child_execution_progress_assessment.py | 101 | `receive_progress` of episode_progress refs; ordinary custody. | same set + `provider.read_progress`, `provider._receive_progress`; `method_loop.durable.content_digest`. |
| child_message_owners.py | 30 | Recursive-exchange routing only for this exact binding. | `runtime.Workflow`, `runtime.EpisodeBindingRegistry`, `workflow.sequence_homology_evidence_binding`, `workflow.episode_bindings._by_path/_by_role`. |
| incoming_message_owners.py | 108 | Route table: (launch, execution_job_submission), (monitor, execution_progress_assessment), (results, execution_result_acquisition), (launch, resource_work_submission), (results, resource_result_acquisition), (literature, published_evidence_assessment). | old Workflow/EpisodeBindingRegistry/`_by_role`/`_by_path` instance state introspection; `..child_message_owners`. |

## Differences from similar episodes

- Compared with its execution children it is the only one with `reason`, the scientific credit projector, the
  `process.*` tools, the closed-request execution guard, the job_child failure arm, and two credit presentations.
- Two different `launch` and `results` children (execution vs resource families) share a role name; it
  distinguishes them by binding path.
- It also builds its sibling execution/resource bindings (`create_execution_bindings`, `create_resource_bindings`)
  with the same construction arguments.

## Carried over

Carried over on 19 November 2026 into the private binding `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/` (ten files: `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/{read_from_parent,msg_to_child,read_from_child,internal_summary,final_to_parent}.py`). One row per row of `runs/carry_over/functions/a101__sequence_homology_evidence.tsv`. The list of what could not be placed is in `docs/axis_restructure_20261117/carry_over_blocked/a101__sequence_homology_evidence.md`.

| old file | kind | name | machinery or episode function | new place (file and name, or library path) or machinery reason |
|---|---|---|---|---|
| alternate_process_selection.py | class | AlternateProcessSelection | episode function | task.py process_revise (the proposed selection of process.revise) |
| alternate_process_selection.py | method | AlternateProcessSelection._proposed_selection | episode function | task.py process_revise (the proposed selection of process.revise) |
| binding_record.py | class | ScientificBindingRecord | machinery | binding_record.py / the binding's own as_record() |
| binding_record.py | method | ScientificBindingRecord.as_record | machinery | binding_record.py / the binding's own as_record() |
| child_message_owners.py | function | exchange_for_child | machinery | recursive-exchange routing by workflow/registry introspection; slots are CHILD_SLOTS |
| commissioned_credit_presentation.py | class | CommissionedScientificPresentation | episode function | messages/internal_summary.py internal_summary and task.py decide (commissioned presentation) |
| commissioned_credit_presentation.py | method | CommissionedScientificPresentation.decision_state | episode function | messages/internal_summary.py internal_summary; task.py decide (context) |
| commissioned_credit_presentation.py | method | CommissionedScientificPresentation.completed_work | episode function | messages/internal_summary.py internal_summary (units, child_reports) |
| commissioned_credit_presentation.py | method | CommissionedScientificPresentation.exchange_yield_table | episode function | messages/internal_summary.py internal_summary (action_yields via yield_table) |
| commissioned_credit_presentation.py | function | _bind_scientific_runtime_providers | machinery | provider patching (_bind_*_runtime_providers) |
| completion_report.py | function | enrich_completion_snapshot | machinery | completion snapshot: the system hands completion to final_to_parent; credit is completion['credit'] |
| completion_report.py | function | _bind_original_runtime | machinery | completion snapshot: the system hands completion to final_to_parent; credit is completion['credit'] |
| configuration.py | class | ScientificConfiguration | episode function | task.py CHILD_SLOTS, replaces_default_instructions; yield_estimator.py (declaration check); settings |
| configuration.py | method | ScientificConfiguration.__init__ | episode function | task.py CHILD_SLOTS (child roles incl. itself), replaces_default_instructions (library candidate); yield_estimator.py yield_controller (declaration check); library/tool-library records as_record() and tool retrieval/contract profile: machinery (settings directories) |
| credit.py | function | original_task_projector | episode function | credit.py A101SequenceCredit (credit) |
| credit.py | class | SequenceHomologyEvidenceCredit | episode function | credit.py credit |
| credit.py | method | SequenceHomologyEvidenceCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | method | SequenceHomologyEvidenceCredit.credit_projector | episode function | credit.py credit; messages/read_from_parent.py (proposed annotation required) |
| credit.py | method | SequenceHomologyEvidenceCredit.credit_view | episode function | credit.py credit (services.scientific_credit replaced by the projector over records) |
| decision_inputs.py | class | ScientificDecisionInputs | episode function | task.py decide (context additions) |
| decision_inputs.py | method | ScientificDecisionInputs.decision_inputs | episode function | task.py decide; the resource/estimate/native-event/waiting/job-episode inputs have no module: unplaced |
| decision_inputs.py | function | _bind_scientific_runtime_providers | machinery | provider patching (_bind_*_runtime_providers) |
| decision_state.py | class | ScientificDecisionState | episode function | messages/internal_summary.py internal_summary (one presentation; the standalone proposed-annotation view is the root's) |
| decision_state.py | method | ScientificDecisionState.credit_presentation | episode function | messages/internal_summary.py internal_summary (one presentation; the standalone proposed-annotation view is the root's) |
| decision_state.py | method | ScientificDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (one presentation; the standalone proposed-annotation view is the root's) |
| episode.py | function | create_execution_bindings | machinery | home factory of sibling bindings |
| episode.py | function | create_resource_bindings | machinery | home factory of sibling bindings |
| episode.py | class | SequenceHomologyEvidenceEpisode | episode function | episode.py SequenceHomologyEvidence |
| episode.py | method | SequenceHomologyEvidenceEpisode.contract_information_profile | machinery | contract-information freezing (README 5 item 16) |
| episode.py | method | SequenceHomologyEvidenceEpisode._role | machinery | role check of the old single-role registry |
| episode.py | method | SequenceHomologyEvidenceEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | method | SequenceHomologyEvidenceEpisode.prepare_child_request | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | method | SequenceHomologyEvidenceEpisode.receive_child_progress_for_role | machinery | progress provider receipt (the monitor returns monitoring_progress_refs) |
| episode.py | method | SequenceHomologyEvidenceEpisode.permitted_common_actions | episode function | task.py decide / action (tool, reason, child; wait and redeliver_report are not carried) |
| episode.py | method | SequenceHomologyEvidenceEpisode.allowed_children | episode function | task.py CHILD_SLOTS |
| episode.py | method | SequenceHomologyEvidenceEpisode.child_request_preparer | episode function | messages/msg_to_child.py ASSIGNMENTS |
| episode.py | method | SequenceHomologyEvidenceEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| episode.py | method | SequenceHomologyEvidenceEpisode.child_request_preparer_for_binding | episode function | messages/msg_to_child.py ASSIGNMENTS |
| episode.py | method | SequenceHomologyEvidenceEpisode.child_report_receiver_for_binding | episode function | messages/read_from_child.py read_from_child |
| execution_planning.py | function | catalog | episode function | task.py process_execution (declared; raises unplaced inputs) |
| execution_planning.py | function | read | episode function | task.py process_execution (raises NotImplementedError: memory_for / resource_context / hpc commissions have no home) |
| from_child_execution_job_submission.py | function | receive_report | episode function | receipt custody of the child form; the report is read in messages/read_from_child.py read_from_child |
| from_child_execution_job_submission.py | function | admit_return | machinery | admit_return / saved report attempts (the system admits the result against the child's form) |
| from_child_execution_job_submission.py | function | _bind_incoming_runtime | machinery | provider patching (_bind_incoming_runtime) |
| from_child_execution_progress_assessment.py | function | receive_progress | machinery | progress provider receipt (monitoring_progress_refs is a field of the monitor's return) |
| from_child_execution_progress_assessment.py | function | receive_report | episode function | receipt custody of the child form; the report is read in messages/read_from_child.py read_from_child |
| from_child_execution_progress_assessment.py | function | admit_return | machinery | admit_return / saved report attempts (the system admits the result against the child's form) |
| from_child_execution_progress_assessment.py | function | _bind_incoming_runtime | machinery | provider patching (_bind_incoming_runtime) |
| from_child_execution_result_acquisition.py | function | receive_report | episode function | receipt custody of the child form; the report is read in messages/read_from_child.py read_from_child |
| from_child_execution_result_acquisition.py | function | admit_return | machinery | admit_return / saved report attempts (the system admits the result against the child's form) |
| from_child_execution_result_acquisition.py | function | _bind_incoming_runtime | machinery | provider patching (_bind_incoming_runtime) |
| from_child_published_evidence_assessment.py | function | receive_report | episode function | receipt custody of the child form; the report is read in messages/read_from_child.py read_from_child |
| from_child_published_evidence_assessment.py | function | admit_return | machinery | admit_return / saved report attempts (the system admits the result against the child's form) |
| from_child_published_evidence_assessment.py | function | _bind_incoming_runtime | machinery | provider patching (_bind_incoming_runtime) |
| from_child_resource_result_acquisition.py | function | receive_report | episode function | receipt custody of the child form; the report is read in messages/read_from_child.py read_from_child |
| from_child_resource_result_acquisition.py | function | admit_return | machinery | admit_return / saved report attempts (the system admits the result against the child's form) |
| from_child_resource_result_acquisition.py | function | _bind_incoming_runtime | machinery | provider patching (_bind_incoming_runtime) |
| from_child_resource_work_submission.py | function | receive_report | episode function | receipt custody of the child form; the report is read in messages/read_from_child.py read_from_child |
| from_child_resource_work_submission.py | function | admit_return | machinery | admit_return / saved report attempts (the system admits the result against the child's form) |
| from_child_resource_work_submission.py | function | _bind_incoming_runtime | machinery | provider patching (_bind_incoming_runtime) |
| from_child_sequence_homology_evidence.py | function | admit_return | machinery | admit_return / saved report attempts (the system admits the result against the child's form) |
| from_child_sequence_homology_evidence.py | function | receive_report | episode function | receipt custody of the child form; the report is read in messages/read_from_child.py read_from_child |
| from_parent.py | class | ScientificAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | method | ScientificAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | ScientificAssignment.child_assignment_schema | episode function | messages/msg_to_child.py _recursive (proposed annotation inherited) and ASSIGNMENT_FORM |
| from_parent.py | method | ScientificAssignment._selection | episode function | messages/read_from_parent.py read_from_parent (validate_selection; library/tool resolution is machinery) |
| from_parent.py | method | ScientificAssignment._assignment | episode function | messages/read_from_parent.py read_from_parent (value checks); scope/reference-in-scope checks are custody |
| from_parent.py | method | ScientificAssignment._invocation | machinery | invocation record of the parent-written report form (report_form machinery) |
| from_parent.py | method | ScientificAssignment.prepare_assignment | episode function | messages/msg_to_child.py _recursive |
| from_parent.py | method | ScientificAssignment._validate_origin | machinery | validation against the parent's recorded preparation (journal rows) |
| from_parent.py | method | ScientificAssignment.prepare_invocation | episode function | messages/msg_to_child.py _recursive; the closed-context re-authentication is machinery (journal) |
| from_parent.py | method | ScientificAssignment.validate_context | machinery | filled-process re-verification of the request (journal) |
| from_parent.py | method | ScientificAssignment.validate_execution_context | machinery | closed-request execution guard (journal) |
| from_parent.py | method | ScientificAssignment._original_selection | episode function | messages/read_from_parent.py parent_input['selection'] |
| from_parent.py | method | ScientificAssignment.initial_references | episode function | messages/read_from_parent.py (evidence_refs and proposed_annotation_refs record_refs fields) |
| goal.py | function | scientific_guidance | episode function | goal.py GOAL |
| goal.py | class | ScientificGoal | episode function | task.py instructions |
| goal.py | method | ScientificGoal.instructions | episode function | task.py instructions (INSTRUCTION_ENTRY_BODY, EVIDENCE_AXIS_BODY) |
| incoming_message_owners.py | function | admission_for_prepared_request | machinery | route table of (role, binding path) admissions; slots are CHILD_SLOTS |
| internal_summary.py | class | ScientificSummary | episode function | messages/internal_summary.py internal_summary; task.py decide (library entries from settings) |
| internal_summary.py | method | ScientificSummary.decision_context | episode function | messages/internal_summary.py internal_summary; task.py decide (library entries from settings) |
| native_correspondence_credit.py | class | A101SequenceCredit | episode function | credit.py A101SequenceCredit (private copy of the projector; base class already in library: grading/sequence_alignment/native_correspondence.py) |
| native_correspondence_credit.py | method | A101SequenceCredit.as_record | episode function | credit.py A101SequenceCredit (private copy of the projector; base class already in library: grading/sequence_alignment/native_correspondence.py) |
| native_correspondence_credit.py | method | A101SequenceCredit.__call__ | episode function | credit.py A101SequenceCredit (private copy of the projector; base class already in library: grading/sequence_alignment/native_correspondence.py) |
| process_state.py | class | SequenceHomologyEvidenceState | machinery | restore of a closed request's filled process (journal) |
| process_state.py | method | SequenceHomologyEvidenceState.restore_closed_process | machinery | restore of a closed request's filled process (journal) |
| report_delivery.py | class | ScientificReportDelivery | episode function | messages/final_to_parent.py final_to_parent |
| report_delivery.py | method | ScientificReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (facts and credit; saving the form and releasing are machinery) |
| report_delivery.py | function | _bind_scientific_runtime_providers | machinery | provider patching (_bind_*_runtime_providers) |
| scientific_contracts.py | function | _object | machinery | closed-JSON copy of a record (the system journals closed JSON) |
| scientific_contracts.py | function | _ref_schema | episode function | task.py _THOUGHT_REF / REVISION_ARGUMENTS (option reference schema) |
| scientific_operations.py | class | ScientificOperations | episode function | task.py execute_selected_tool, process_revise, process_execution |
| scientific_operations.py | method | ScientificOperations.execute | episode function | task.py execute_selected_tool, process_revise, process_execution |
| scoring/native_correspondence.py | function | _known | episode function | already in library: gene_annotation_episode/episodic_workflow/episode_support/grading/sequence_alignment/native_correspondence.py (same name) |
| scoring/native_correspondence.py | function | _regions | episode function | already in library: gene_annotation_episode/episodic_workflow/episode_support/grading/sequence_alignment/native_correspondence.py (same name) |
| scoring/native_correspondence.py | class | NativeCorrespondenceScoring | episode function | already in library: gene_annotation_episode/episodic_workflow/episode_support/grading/sequence_alignment/native_correspondence.py (same name) |
| scoring/native_correspondence.py | method | NativeCorrespondenceScoring._annotation_measurements | episode function | already in library: gene_annotation_episode/episodic_workflow/episode_support/grading/sequence_alignment/native_correspondence.py (same name) |
| scoring/native_correspondence.py | method | NativeCorrespondenceScoring.annotation_contribution | episode function | already in library: gene_annotation_episode/episodic_workflow/episode_support/grading/sequence_alignment/native_correspondence.py (same name) |
| scoring/native_correspondence.py | method | NativeCorrespondenceScoring.read_details | episode function | already in library: gene_annotation_episode/episodic_workflow/episode_support/grading/sequence_alignment/native_correspondence.py (same name) |
| standalone_credit_presentation.py | class | StandaloneScientificPresentation | episode function | messages/internal_summary.py internal_summary / task.py decide; the standalone proposed_annotations, annotation_comparisons and arms are the root episode's (unplaced here) |
| standalone_credit_presentation.py | method | StandaloneScientificPresentation.decision_state | episode function | messages/internal_summary.py internal_summary / task.py decide; the standalone proposed_annotations, annotation_comparisons and arms are the root episode's (unplaced here) |
| standalone_credit_presentation.py | method | StandaloneScientificPresentation.completed_work | episode function | messages/internal_summary.py internal_summary / task.py decide; the standalone proposed_annotations, annotation_comparisons and arms are the root episode's (unplaced here) |
| standalone_credit_presentation.py | method | StandaloneScientificPresentation.exchange_yield_table | episode function | messages/internal_summary.py internal_summary / task.py decide; the standalone proposed_annotations, annotation_comparisons and arms are the root episode's (unplaced here) |
| standalone_credit_presentation.py | function | _bind_scientific_runtime_providers | machinery | provider patching (_bind_*_runtime_providers) |
| task.py | class | ScientificInvestigationTask | episode function | task.py decide, action and tools |
| task.py | method | ScientificInvestigationTask.instructions | episode function | task.py instructions |
| task.py | method | ScientificInvestigationTask.next | episode function | task.py decide (the loop and replays are the system's) |
| task.py | method | ScientificInvestigationTask.apply_response | episode function | task.py action (reasoning-content rejection, schema admission; report_update is not carried); the job_child failure arm and contract_error repair hints: unplaced |
| task.py | method | ScientificInvestigationTask.execute | episode function | task.py reason, execute_selected_tool, process_revise (wait: not carried) |
| task.py | function | _bind_scientific_runtime_providers | machinery | provider patching (_bind_*_runtime_providers) |
| task_decision.py | class | ScientificTaskDecision | episode function | task.py decide |
| task_decision.py | method | ScientificTaskDecision.call | episode function | task.py decide (ModelRequest; recording and replay are the system's) |
| task_decision.py | method | ScientificTaskDecision.conversation_key | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | method | ScientificTaskDecision.interpretation_context | machinery | decision-exchange lookup context |
| task_decision.py | method | ScientificTaskDecision.exchange_schema | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | method | ScientificTaskDecision.exchange_response | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | method | ScientificTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | method | ScientificTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | method | ScientificTaskDecision.exchange_decision | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | function | _bind_scientific_runtime_providers | machinery | provider patching (_bind_*_runtime_providers) |
| task_instructions.py | function | instructions | episode function | task.py instructions |
| task_state.py | class | ScientificTaskState | machinery | per-episode state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | method | ScientificTaskState.__init__ | machinery | per-episode state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | method | ScientificTaskState.bind_execution_context | machinery | per-episode state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | method | ScientificTaskState.record_execution_failure | episode function | task.py execute_selected_tool (failure as an outcome: failure_outcome) |
| task_state.py | method | ScientificTaskState.restore_checkpoint | machinery | per-episode state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | method | ScientificTaskState.restore | machinery | per-episode state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | method | ScientificTaskState.record_effect | machinery | per-episode state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | method | ScientificTaskState.checkpoint | machinery | per-episode state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | function | _bind_scientific_runtime_providers | machinery | provider patching (_bind_*_runtime_providers) |
| to_child_execution_job_submission.py | function | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (ASSIGNMENTS entry of the slot) |
| to_child_execution_progress_assessment.py | function | prepare_request | episode function | messages/msg_to_child.py _monitor |
| to_child_execution_progress_assessment.py | function | required_return_sources | episode function | messages/msg_to_child.py msg_to_child (selection: monitoring_progress_refs) |
| to_child_execution_progress_assessment.py | function | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (ASSIGNMENTS entry of the slot) |
| to_child_execution_result_acquisition.py | function | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (ASSIGNMENTS entry of the slot) |
| to_child_published_evidence_assessment.py | function | prepare_request | episode function | messages/msg_to_child.py msg_to_child (ASSIGNMENTS entry of the slot) |
| to_child_resource_result_acquisition.py | function | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (ASSIGNMENTS entry of the slot) |
| to_child_resource_work_submission.py | function | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (ASSIGNMENTS entry of the slot) |
| to_child_sequence_homology_evidence.py | function | prepare_request | episode function | messages/msg_to_child.py msg_to_child (ASSIGNMENTS entry of the slot) |
| to_parent.py | class | ScientificReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | ScientificReport.required_return_sources | episode function | messages/msg_to_child.py (the parent's selection) and final_to_parent.py RETURN_FORM |
| to_parent.py | method | ScientificReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (library report_sources and alignment-site sources: unplaced) |
| to_parent.py | method | ScientificReport.facts | episode function | messages/final_to_parent.py final_to_parent (process result: raises unplaced) |
| to_parent.py | method | ScientificReport.resolve | machinery | form reference resolver (report_form machinery) |
| to_parent.py | method | ScientificReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| tool_selection.py | class | ScientificToolSelection | episode function | task.py selected_tools / selection_schema |
| tool_selection.py | method | ScientificToolSelection._information_catalog | machinery | services.tool_catalog callback |
| tool_selection.py | method | ScientificToolSelection._closed_tool_resolution | machinery | closed-request restore (journal) |
| tool_selection.py | method | ScientificToolSelection._tool_resolution_for | episode function | task.py selected_tools (tool library resolve_invocations) |
| tool_selection.py | method | ScientificToolSelection._tool_resolution | episode function | task.py selected_tools (common tool name check) |
| tool_selection.py | method | ScientificToolSelection.catalog | episode function | task.py selected_tools, DESCRIPTIONS[process_revise], selection_schema |
| tool_selection.py | method | ScientificToolSelection.create_tool_retriever | machinery | tool retriever service (scientific_tool_retrieval has no home): unplaced |
| tool_selection.py | method | ScientificToolSelection.common_tool_names | episode function | task.py COMMON_TOOLS |
| waiting.py | class | ScientificWaiting | machinery | wait/suspension machinery (the wait action is not carried) |
| waiting.py | method | ScientificWaiting.suspension_changed | machinery | wait/suspension machinery (the wait action is not carried) |
| waiting.py | method | ScientificWaiting._execute_selected_wait | machinery | wait/suspension machinery (the wait action is not carried) |
| waiting.py | function | _bind_scientific_runtime_providers | machinery | wait/suspension machinery (the wait action is not carried) |
| yield_estimator.py | class | SequenceHomologyEvidenceYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | SequenceHomologyEvidenceYield.private_yield_binding | machinery | switch for private bindings (this head always has them) |
| yield_estimator.py | method | SequenceHomologyEvidenceYield.continuation_task | episode function | messages/read_from_parent.py (yield_task key); yield_estimator.py |
| yield_estimator.py | method | SequenceHomologyEvidenceYield.yield_controller | episode function | yield_estimator.py yield_controller (BoundedQualityYieldController) |
