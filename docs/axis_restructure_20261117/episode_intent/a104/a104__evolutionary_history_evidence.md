# a104/evolutionary_history_evidence — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/` (48 Python files directly in the
folder; no `grading/` or `scoring/` subfolder; `tests/` and child folders not read). Nothing from the old shared root
was read. Where behaviour lives in old shared modules (`a104_credit`, `a104_investigation`,
`evolutionary_history_evidence_reports`, `execution_planning`, the prompt renderers), this page says only what this
episode's own files ask of them.

Old binding: class `EvolutionaryHistoryEvidenceEpisode`, `binding_path = 'evolutionary_history_evidence'`,
`commissioning_parent = 'legacy_annotation'`, role and entry role `evolutionary_history_evidence`, version
`evolutionary_history_evidence_episode_v10`, axis `A104`. Decision source: `ScientificTask`. Prompt renderer:
`present_scientific_context` (published scientific contexts go to `render_evolutionary_history_evidence_prompt`).
`episode.py` also holds two factories that build the execution subtree (job submission, API / local / HPC job
execution, result acquisition) and the HPC subtree (work planning, resource prediction, allocation execution) with the
caller's operands.

## What this episode is for

It investigates the evolutionary-history evidence for a target within its parent's question, iteratively, with one
pinned evidence axis (A104), one thought pattern and one selected tool set. In its own words (`goal.py`, the text used
when the selected axis entry is an evidence-axis instruction entry, the current case):

> Determine what the supplied target does within the parent's assigned question, scope and constraints. Start with
> the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and known
> context. No initial candidate annotation or publicly searchable name is required. Possible functions can emerge from
> the evidence and be compared or revised. Apply the complete selected investigation instructions and thought-pattern
> guidance on every decision. Use actual outcomes and received child results to choose and revise your approach.
> Selected instructions describe how to investigate; they are not evidence about this target. Preserve the measured
> subject, conditions, controls, native measurements, uncertainty and limits of inference when interpreting evidence.
> Missing information remains unknown.
>
> Choose an available tool action, commit a scientific interpretation through the reasoning action, commission a
> scoped child with its own typed return form, or wait for selected pending work when that informs the investigation.
> Use only the selected actual tools and their supplied resource instructions; choose callable operands through the
> declared response contract. Preserve the parent's exact requested result meanings and allowed values. Recorded facts
> come from actual records. Keep inherited information distinct from new findings and completed work distinct from
> attempts. Return valid partial findings and specific failures through the requested form.
>
> Keep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise prepares a
> different thought pattern and/or tool selection for a new child; it does not change this episode or start that
> child. To commission that alternative, copy its selection and revision_origin into a separately selected child
> assignment with the child's job, scope, constraints and typed return. Children own their iterative choices. The
> configured controller owns continuation. Waiting and unchanged observations do not manufacture progress.

The second text in `goal.py` (older support-metadata axis entries) frames the same work as a "scientific support
problem": support metadata and `annotation_support_routes` describe the bound annotation policy, earn no credit, and
never add form fields or scoring axes; children request `evolutionary_history_evidence_results` when process
provenance and closed credit/yield are needed for steering.

Note: the goal text offers "wait", but `child_commissioning.permitted_common_actions` gives only
`tool, reason, child, redeliver_report` — no `wait` for this episode.

## Task and instructions

- One unit is one model-selected action: `tool`, `reason` (commit an interpretation), `child` (episode_child), or
  `redeliver_report`.
- Instructions (`task_instructions.py`): when every `evidence_axis` header of the library is an evidence-axis
  instruction entry (`configuration.replaces_default_instructions`), the goal text above replaces the defaults; else
  it is appended to them. Then: the reasoning-commit requirement (reason is permitted), tool knowledge, the launch
  instruction library, the redelivery paragraph ("When pending_child_delivery is supplied ..."), the wait paragraphs
  only if wait is permitted, the native-event paragraph, and the exchange-protocol replacement of history guidance
  ("Use request_context exchanges for your own attempt metadata ... episode.history tool, view=records ...").
- Action admission (`action_admission.py`): an all-empty reasoning commit is rejected (`empty_reasoning_commit`)
  unless the evidence-processing kind is `no_applicable_evidence` or the binding reports task content; a returned
  `job_child` storage/control failure becomes `job_assignment` feedback; `reads.map` schema failures get parameter
  repair hints; the report update is admitted for grain `evolutionary_history_evidence`.
- Action execution (`action_execution.py`): before any new dispatch the binding's `validate_execution_context` must
  pass (a closed invocation may be inspected, never re-dispatched). Every observed outcome, including invalid or
  failed, is saved with the current credit; `shared.read_information` results keep their shared grading results.
  `task_state.record_execution_failure` turns an exception during an own tool/reason action into a failed action that
  still enters with its credit.

## What it reads from its parent's assignment

`from_parent.py`, `scientific_assignment_contracts.py`:

- Assignment (`_ASSIGNMENT`): `selection` {`version`, `evidence_axis` (A104 option ref of this library),
  `thought_pattern` (`P<n>` option ref), `child_tool_info` [{`name`, `resources` api|local|hpc}]},
  `proposed_annotation_ref` (required when the services say an annotation task is required), `evidence_refs`,
  `constraints`, `context` {`evidence_task`: {`whole_axis_findings`, `A104`, `credit_unit` > 0}, optional
  `a104_task`}, optional `revision_origin`. The recorded assignment materializes each `child_tool_info` entry with its
  description and instructions.
- Checks: selection library id equals this library; axis entry is an instruction entry or evidence-axis entry;
  tool info resolves; proposed annotation is in scope as a `hypothesis`; every evidence ref is in scope; a
  `revision_origin` must match its `process.revise` preparation (same parent invocation, same initial selection
  digest, same proposed selection).
- Invocation: `objective`, `purpose`, closed `report_schema` (requested site projections and molecular fact sources
  are validated), `initial_report` valid against the interpretation schema.
- `prepare_assignment` inherits the parent's proposed annotation (a different one is refused) and requires that the
  parent actually received it.
- Required returns when the annotation task is required: a child directly under the root must request
  `evolutionary_history_evidence_results` and `committed_record_refs`; deeper children `committed_record_refs`.

## Children

`child_commissioning.py`: configured `child_roles` must contain `evolutionary_history_evidence`;
`allowed_children` keeps only `evolutionary_history_evidence` and `hpc` of them. Request assemblers and report
receivers exist for more roles:

| Old role | Child episode | What it sends | What it takes back |
|---|---|---|---|
| `evolutionary_history_evidence` | itself (recursive; the `process.revise` alternative) | goal, scope, typed form, initial report, assignment via `prepare_invocation` (filled process with selection, assignment and invocation digests, mechanics binding), `scientific_invocation_ref`, knowledge inheritance | typed form: recorded admission refs, form refs, conservation/phylogeny `source_ref`s, native timing receipts, tool attributions |
| `hpc` | `hpc_work_planning` | goal, scope, typed form, assignment via the child binding's `prepare_assignment` (the parent's `prepare_child_request` hook passes it unchanged) | typed form as above |
| `launch` | `execution_job_submission` | assembled request; `prepare_parent_request` requires an `execution_handoff_refs` field when launch is under an hpc path | typed form as above |
| `results` | `execution_result_acquisition` | assembled request | typed form as above |
| `literature` | `published_evidence_assessment` | assembled request | typed form as above |
| `monitor` | `execution_progress_assessment` | assignment validated against the monitor contract (target, known observations, requested fields, permitted records); "This parent requests information; it never polls here." Required return `monitoring_progress_refs` when annotation task required | only declared `episode_progress` references, read through the progress provider and received under a content digest |

Only the first two are reachable through this binding's `allowed_children`; the others are reachable only through
an `annotation_child_roles` override or as job children. A failed child becomes a failed own action with the current
credit (`receive_parent_child_failure`).

## Decision state and what it shows the model

- Source state (`task_state.py`): calls, feedback, last outcome, report values (initially the parent's
  `initial_report`) and basis refs, restore/checkpoint.
- Context (`decision_context.py`, `decision_inputs.py`): goal, scope, working state, visible record refs, current
  credit, current evidence vector, investigation progress (retained finding count, inactive dependencies, detail
  pages) when receipt projection applies, credit binding, time accounting, pending work, last local outcome,
  feedback, visual evidence (last `image.view`), report deliveries, controller state and binding, tools, tool
  knowledge, job episode options, available report facts, requested purpose and form, current report and basis, the
  report-lifecycle sentence; annotation context; resource context, shared information context, launch instruction
  library and selected instructions, child options, completed action reports, execution expectations, resource tool
  estimates, native execution expectations, native event targets, contract-information profile. In
  annotation-axis-credit mode the working state and child reports are hidden and child outcomes are reduced to counts.
- Own block (`internal_summary.py`, key `evolutionary_history_evidence`): `selection`, `initial_selection_sha256`,
  `evidence_axis` view (or `annotation` + `annotation_support_routes` for the older entries), `thought_pattern`
  fields `id, name, description, use_when, live_alternatives, decision_guidance, outcome_contingencies, boundary`,
  `child_tool_info` (or resolved `tools`), the assignment, `permitted_children`. No component scoring facts.

## Tools

`tool_selection.py`, `scientific_operations.py`:

- The resolved selected tools whose route is direct (no `instructions` or `invocation_route` shown), plus
  `process.revise` and the execution-planning catalog (`process.execution`). Common tools available besides:
  `process.search/entry/sources/tools`, `knowledge.search/entry/read`, `episode.history/credit/annotation_score/
  monitoring_information/estimate_wait`, `shared.request_information/publish_information/resolve_information_need/
  read_information/list_information`. A selected tool may not reuse a common name.
- `sequence.align` is refused: `a104_new_sequence_comparison_requires_shared_parent`.
- `process.execution` reads execution planning. `material.from_source/parse/read`, `source.read/locate` first
  authenticate their source byte operands. `process.revise` returns a child selection and `revision_origin` and
  changes nothing else. Everything else goes to the services' tool execution, with the received refs as permitted
  refs for `result.blast.hsp` and `source.locate`.

## Credit

`credit.py`, `task_projector.py`: kind `scientific`. The projector is chosen from the original assignment's
`context.a104_task` name: `panel_identity` → `A104PanelIdentityCredit`, `alignment_suitability` →
`A104AlignmentSuitabilityCredit`, `robustness` → `A104RobustnessCredit`, otherwise (or no task)
`A104EvolutionaryCredit`; only for instruction-version axis entries. With yield bindings a proposed annotation is
required. The credit view comes from the services' scientific credit.

## Continuation

`yield_estimator.py`, `configuration.py`: the task key is `A104:<a104_task name>` or `A104:<projector kind>`. The
configured declaration for that key fixes `kind`, `cutoff`, `parameters` {`uncertainty_alpha`} and
`credit_definition`; the definition must equal the projector's record and the projector's `yield_method` must equal
the kind. `accumulation` → accumulation estimator; `bounded_quality` → bounded quality with
`projector.native_score_maximum` as the bound; `completion` → completion with a target (the cutoff). Without yield
bindings no controller is supplied. These map one-to-one onto the three `yield_control/` estimators.

## What it reports to its parent

`to_parent.py`, `report_delivery.py`, `report_integrity.py`:

- Fact sources: the library's process report sources, the A104 investigation sources, alignment-site sources and
  molecular fact sources (protein conservation, protein phylogeny).
- Facts: `evolutionary_history_evidence_results` (own process result merged with received ones, projected), the A104
  record source (received records, committed refs) when requested, each requested site projection paged 64 records at
  a time from its own actions, molecular facts merged received + own.
- Validation: form references resolve; molecular returns equal the frozen facts; the A104 axis report rules; site
  returns equal the frozen site facts; `evolutionary_history_evidence_results` equal the frozen process results.
- Finish: the form is built once from the report values and facts and saved; with no report contract the result is
  credit, pending handles and current report facts.

## Differences from similar episodes

- Unlike its execution descendants it has `reason` and children, a scientific (not operational) credit and a
  per-task yield declaration chosen by `a104_task`; it has no `wait`.
- A104-specific: `sequence.align` refused; molecular returns (conservation/phylogeny) admitted and checked against
  frozen facts; task projectors panel identity / alignment suitability / robustness / evolutionary.
- `allowed_children` names only itself and `hpc`, while assemblers exist for launch, results, literature and
  monitor.

## Files

Name abbreviations: `wf.X` = old `self.workflow.X` / `source.workflow.X` / `workflow.X`; `wf(self).X` = a parent-runtime function bound into the old workflow namespace using `self.X`; `BC.X` = old `BindingContext` field; `services.X` = old binding services; `SelectionView.X` = old selection view; `tbl:` = old journal/receipt/provider table; `imp:` = import from old `root.a104.<module>`; `lrf.` = `library.live_runtime_functions` rebinding into the old runtime namespace; bare names are old runtime/provider/numerical names. Counts are uses in that file. Full rows: `runs/carry_over/calls/a104_01.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `action_admission.py` | 103 | admits one model response: decodes selection, rejects an empty reasoning commit unless the binding says it has task content, job_child storage/control failures become feedback, reads.map parameter-schema repair hints, validates report_update for grain evolutionary_history_evidence and keeps its basis refs (decision-source text shared by all A104 scientific episodes) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:read_mapping×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _decode_recorded_action_response×1, ReportRedelivery×2, _wait_target_feedback×1, tbl:runtime_actions×1, tbl:runtime_model_calls×1, wf.binding_context×2, wf.decision_exchanges×3, wf.execution_binding×1, wf.journal×2, wf.permits_common_action×1, wf.reasoning_action_schema×1, wf.resolver×1, wf.selected×1, wf.specialist×1, wf.store×2, wf.validate_report×1 |
| `action_execution.py` | 89 | executes the selected unit (reason / wait / tool), revalidates this episode's execution identity before new dispatch, stores outcome then credit, retains shared grading results after shared.read_information, raises ActionFailure for unobserved outcomes (shared decision-source text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionFailure×1, observes_action_outcome×1, _wait_target_feedback×1, WorkflowError×1, tbl:runtime_actions×5, wf.automatic_score_updates×1, wf.binding_context×4, wf.completions×1, wf.controller_value×2, wf.evolutionary_history_evidence_binding×1, wf.execute×1, wf.execution_binding×4, wf.journal×1, wf.last_observed_credit×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.retain_shared_grading_results×1, wf.run_id×2, wf.source_credit_view×1, wf.specialist×1, wf.store×4 |
| `binding_record.py` | 8 | binding identity record: version evolutionary_history_evidence_episode_v10, library record, tool library record, child_roles, optional tool_retrieval, contract_information_profile, yield_bindings | none |
| `child_commissioning.py` | 81 | own child set: allowed_child_roles keeps only evolutionary_history_evidence and hpc of the configured child_roles; permitted actions tool, reason, child, redeliver_report (no wait); request assemblers for monitor, evolutionary_history_evidence, hpc, launch, results, literature; monitor assignment prepared and monitor progress received specially | imp:a104_credit×1, imp:a104_investigation×2, imp:communication×1, imp:domain×1 |
| `completion_snapshot.py` | 5 | completion operands: initial_credit, credit, controller_credit, episode_yield, parent_invocation_ref | tbl:runtime_episodes×1, wf.journal×1, wf.services×1, wf.source_controller_credit×1 |
| `configuration.py` | 43 | constructor: child_roles must be unique non-empty and include evolutionary_history_evidence; library and tool library records; replaces_default_instructions when every evidence_axis header is an evidence-axis instruction entry; tool_retrieval; contract_information_profile; per-task yield_bindings checked (kind accumulation / bounded_quality / completion, cutoff, parameters {uncertainty_alpha}, credit_definition) | BC.role×1, imp:composition_information×1, imp:numerical×1, imp:scientific_tool_retrieval×1, BoundedYieldController×2, CompletionYieldController×2, CONTRACT_INFORMATION_PROFILE×2, YieldController×2, YieldParameters×2 |
| `credit.py` | 24 | credit kind scientific; projector chosen from the original task (task_projector) only for instruction-version axis entries; proposed_annotation_ref required when yield bindings exist; credit view from services.scientific_credit | BC.assignment×2, BC.role×1, services.scientific_credit×1 |
| `decision_context.py` | 58 | assembles the decision context (goal, scope, working state, visible refs, current credit, evidence vector, investigation progress, credit binding, time accounting, pending work, last outcome, feedback, visual evidence, deliveries, controller, tools, tool knowledge, job options, report facts, requested form, current report); annotation-axis-credit mode hides state and child reports; adds annotation context and the binding's own decision_context; carries completed axis sheets forward | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, FACT_MEANINGS×1, FACT_SOURCES×1, _references_in×1, SelectionView.child_reports×2, SelectionView.controller_state×1, SelectionView.model_inputs×1, tbl:runtime_actions×2, wf.annotation_context×1, wf.binding_context×2, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.is_scientific_source×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.tools×1, wf.working_state×1 |
| `decision_contracts.py` | 134 | decision-exchange envelope (request_context lookup vs select_action) and replay validation of saved exchanges and frozen contract information (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, apply_state_frame×1, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×1, is_contract_information×1, model_snapshot×1, _references_in×1, requested_contract_information×1, WorkflowError×9, tbl:runtime_model_calls×1, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.store×2, wf.validate_contract_information×2 |
| `decision_delivery.py` | 100 | one model decision call: replays a saved call, otherwise builds inputs, freezes literature numerical contracts or contract information, records decision-input receipts, runs the exchange protocol or a direct completion (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _ASSIGNMENT_TRANSPORT×1, DECISION_EXCHANGE_PROTOCOL×5, instructional_model_context×1, _recorded_assignment_transport×1, WorkflowError×5, tbl:runtime_model_calls×5, wf.binding_context×2, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.evolutionary_history_evidence_binding×1, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.is_job_source×2, wf.journal×1, wf.numerical_contracts×1, wf.provider×2, wf.receipts×4, wf.services×1, wf.uses_received_record_context×2, wf.validate_contract_information×2 |
| `decision_exchange.py` | 114 | request_context exchange loop for one pending decision: child_options, composition_information and own-attempt lookups, state frames, retries (shared text) | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, _action_generation_schema×1, _category_yield_parameters×1, child_option_information×1, DECISION_CONTEXT_VERSION×1, instructional_model_context×2, lookup_attempts×1, model_snapshot×1, requested_contract_information×1, state_frame×1, yield_table×1, tbl:runtime_model_calls×2, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.run_id×1, wf.services×1, wf.validate_contract_information×1 |
| `decision_inputs.py` | 78 | decision inputs: resource context, shared information, launch instruction library and selected instructions, child options, binding initial context, completed action reports, HPC requested action history, execution expectations / job options, resource tool estimates, native expectations, native event targets, waiting support, contract profile (shared text) | imp:root.a104×1, imp:episode_work_report×2, imp:library.hpc_prompt×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, child_option_information×1, completed_action_reports×3, requested_action_history×3, wf.available_child_roles×1, wf.binding_context×4, wf.episode_bindings×1, wf.execution_expectations×1, wf.is_job_source×1, wf.job_episodes×4, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.pending_work×1, wf.permits_common_action×1, wf.resource_context×1, wf.resource_estimator×5, wf.shared_information_context×1, wf.store×2, wf.waiting_support×1 |
| `decision_provider.py` | 61 | routes the decision to the provider with this binding's prompt renderer when the provider is the original model class (shared text) | imp:providers×2, imp:runtime×1, imp:root.providers×1, _ORIGINAL_DECLARED_PRESENTATION×2, _ORIGINAL_MODEL_COMPLETE×3, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION×3, _ORIGINAL_MODEL_INSTANCE_DICT×4, wf.provider×1, wf.specialist×2 |
| `episode.py` | 51 | assembles the head binding from its mixins; binding_path evolutionary_history_evidence, commissioning_parent legacy_annotation, roles/entry_roles (evolutionary_history_evidence,), prompt renderer present_scientific_context; also factories create_execution_bindings (job submission, api, local, hpc job execution, result acquisition) and create_hpc_bindings (hpc work planning, resource prediction, allocation execution) | none |
| `from_child_evolutionary_history_evidence.py` | 87 | receives a recursive child's typed form: recorded admission refs, child progress, form refs, received_form_references, native timing receipts, receipts and tool attributions; also the parent-side admit_parent_return and receive_parent_child_failure (failed child becomes a failed action with current credit) | imp:.. (parent package)×1, imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, lrf.bind_functions×1, lrf._bind_parent_runtime×2, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, ReportDeliveryError×2, WorkflowError×1, tbl:runtime_actions×3, tbl:runtime_report_attempts×3, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf(self).controller_value×1, wf(self).delivery_feedback×1, wf(self).journal×3, wf(self).receive_form×1, wf(self).run_id×2, wf(self).save_attempt×2, wf(self).source_credit_view×1, wf(self).store×1, wf.specialist×1, wf.store×7 |
| `from_child_execution_job_submission.py` | 44 | receives the launch child's typed form (same receive_report text) | imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, WorkflowError×1, tbl:runtime_report_attempts×2, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf.specialist×1, wf.store×7 |
| `from_child_execution_progress_assessment.py` | 23 | receives a monitor form: only declared episode_progress references are read through the progress provider and received under a content digest | BC.episode_id×3, BC.scope×2, imp:communication×1, imp:domain×1, imp:method_loop.durable×1 |
| `from_child_execution_result_acquisition.py` | 44 | receives the results child's typed form (same receive_report text) | imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, WorkflowError×1, tbl:runtime_report_attempts×2, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf.specialist×1, wf.store×7 |
| `from_child_hpc_work_planning.py` | 87 | receives the hpc child's typed form (same receive_report text) plus admit_parent_return / receive_parent_child_failure | imp:.. (parent package)×1, imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, lrf.bind_functions×1, lrf._bind_parent_runtime×2, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, ReportDeliveryError×2, WorkflowError×1, tbl:runtime_actions×3, tbl:runtime_report_attempts×3, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf(self).controller_value×1, wf(self).delivery_feedback×1, wf(self).journal×3, wf(self).receive_form×1, wf(self).run_id×2, wf(self).save_attempt×2, wf(self).source_credit_view×1, wf(self).store×1, wf.specialist×1, wf.store×7 |
| `from_child_published_evidence_assessment.py` | 44 | receives the literature child's typed form (same receive_report text) | imp:delivery_counterpart×1, imp:episode_return_records×1, imp:runtime×1, child_role_for_delivery×2, EpisodeReturnRecords×2, _references_in×1, WorkflowError×1, tbl:runtime_report_attempts×2, wf.binding_context×8, wf.episode_bindings×1, wf.is_job_source×2, wf.job_episodes×2, wf.native_timing_information×1, wf.progress_provider×4, wf.receipts×3, wf.receive_tool_attributions×1, wf.run_id×6, wf.specialist×1, wf.store×7 |
| `from_parent.py` | 153 | assignment schema; adds proposed_annotation_ref as required when annotation task required; validates selection against own library, axis entry, tool info; validates evidence refs, proposed annotation, revision origin; invocation (objective, purpose, closed report_schema, initial_report); prepare_assignment inherits the parent's proposed annotation; prepare_invocation for closed replay or a new filled process; required_return_sources | BC.assignment×1, BC.episode_id×3, BC.path×6, BC.received_record_refs×1, BC.request×1, BC.role×1, BC.run_id×6, BC.scope×2, imp:episode_return_records×1, EpisodeReturnRecords×2, services.annotation_task_required×3, services.proposed_annotation_for×1, services.reference_in_scope×2, services.scientific_preparation×2, services.workflow×1, tbl:runtime_actions×1, wf.evolutionary_history_evidence_binding×1, wf.journal×1, wf.run_id×1, wf.store×1 |
| `goal.py` | 14 | the goal/instructions text (two versions: evidence-axis instruction entries vs older support-metadata entries) | BC.assignment×1 |
| `internal_summary.py` | 39 | own decision block evolutionary_history_evidence (selection, initial_selection_sha256, evidence_axis or annotation view, annotation_support_routes, thought pattern fields, child_tool_info or tools, assignment, permitted_children); no component scoring facts | BC.assignment×2, BC.role×1, services.scientific_support_routes×1, services.workflow×1 |
| `presentation.py` | 41 | presentation state machine for decision frames (bootstrap / update / lookup) and text rendering | imp:providers×1, apply_state_frame×3, DECISION_CONTEXT_VERSION×1, text_instructions×1 |
| `presentation_selection.py` | 30 | which text renderer applies: hpc, published scientific (evolutionary prompt), api launch, selected execution, monitor, receiver | imp:evolutionary_history_evidence_prompt×2, imp:library.hpc_prompt×1, imp:library.monitor_prompt×1, imp:native_profile_presentation×1, imp:providers×1, imp:receiver_prompt×1, is_api_launch_context×2, is_published_scientific_context×2, _ordinary_runtime_receiver_context×1, render_api_launch_prompt×1, render_evolutionary_history_evidence_prompt×1 |
| `received_evidence.py` | 36 | received report sources/facts for role annotation (molecular facts); received_form_references validates protein_conservation_outcomes and protein_phylogeny_outcomes returns and takes their source refs | BC.request×1, BC.role×2, imp:protein_conservation_result_contracts×1, imp:protein_phylogeny_result_contracts×1, services.molecular_received_facts×1 |
| `report_delivery.py` | 32 | finish: no report contract gives credit, pending handles and current report facts; otherwise the saved or newly built form_with_facts saved once | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, form_with_facts×1, tbl:runtime_forms×2, wf.binding_context×2, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| `report_integrity.py` | 22 | return must agree with frozen molecular facts (literal conservation, native protein phylogeny) | services.molecular_frozen_facts×1 |
| `restore_binding.py` | 47 | rebuilds the pinned binding from this run's scientific-process-library and scientific-tool-library directories for descriptor versions v5 to v10 | scientific_binding_compatible×2 |
| `saved_scientific_state.py` | 99 | identity of closed and saved requests; validate_context; validate_execution_context permits inspection of a closed invocation, never new dispatch | BC.assignment×3, BC.path×2, BC.request×4, BC.role×3, BC.run_id×1, BC.scope×4, imp:episode_composition×2, scientific_binding_compatible×4, services.scientific_closed_request×1, services.scientific_parent_preparation×1, services.scientific_saved_request×3 |
| `scientific_assignment_contracts.py` | 59 | constants and schemas: VERSION, AXIS A104, ROLE, common tool names, reference patterns, scientific namespaces, option-ref / selection / revision-origin / evidence_task / assignment schemas | imp:alignment_site_returns×1, imp:communication×1, imp:domain×1, imp:episode_bindings×1, imp:evidence_axis_contracts×1, imp:evidence_axis_instructions×1, imp:evolutionary_history_evidence_library×1, imp:evolutionary_history_evidence_records×1, imp:evolutionary_history_evidence_reports×1, imp:evolutionary_result_facts×1, imp:scientific_support_metadata×1 |
| `scientific_operations.py` | 45 | tool execution: sequence.align refused (a104_new_sequence_comparison_requires_shared_parent), process.execution reads execution planning, source-byte authentication for material/source tools, process.revise prepares a child selection and revision_origin, others go to services.execute_tool (permitted_record_refs for result.blast.hsp and source.locate) | BC.assignment×1, BC.path×1, BC.received_record_refs×1, BC.run_id×1, BC.scope×2, imp:a104_credit×1, imp:a104_investigation×2, imp:communication×1, imp:domain×1, imp:execution_planning×1, services.authenticate_source_byte_operands×1, services.execute_tool×1 |
| `source_references.py` | 20 | resolves scientific namespaces then ordinary references; initial references are evidence_refs plus the proposed annotation | BC.assignment×3, BC.role×1, reference_in_context×1, services.scientific_reference×1 |
| `task.py` | 101 | decision-source next(): replay and completion slots, unfinished own actions, ready owned children, model call, source failure on ModelCallError (shared text) | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:providers×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ModelCallError×2, record_source_failure×2, SourceEnd×2, WorkflowError×1, SelectionView.units_consumed×4, tbl:runtime_actions×2, tbl:runtime_episodes×1, tbl:runtime_model_calls×1, wf.action_schema×1, wf.completed_unit×3, wf.completions×2, wf.delivery_resolution_inputs×1, wf.execution_binding×2, wf.inprocess_replay×4, wf.journal×4, wf.next_return×1, wf.resolve_pending_deliveries×1, wf.run_id×1, wf.selected×2, wf.store×3 |
| `task_instructions.py` | 36 | default instruction composition: binding text replaces defaults, reasoning-commit requirement, tool knowledge, launch library, redelivery paragraph, wait paragraphs, native events, exchange-protocol history guidance | imp:root.a104×1, imp:library.live_runtime_functions×1, imp:runtime_prompt×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, DECISION_EXCHANGE_PROTOCOL×1, REASONING_COMMIT_REQUIREMENT×1, wf.binding_context×2, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| `task_projector.py` | 16 | original task projector: context.a104_task name in TASKS selects A104PanelIdentityCredit / A104AlignmentSuitabilityCredit / A104RobustnessCredit, otherwise A104EvolutionaryCredit | imp:a104_credit×1, imp:a104_investigation×2, imp:communication×1, imp:domain×1 |
| `task_state.py` | 117 | source state: identity, calls, feedback, last outcome, report values/basis, restore/checkpoint, record_execution_failure (failed own tool/reason action still enters with credit) | imp:root.a104×1, imp:episode_source_failure×1, imp:library.live_runtime_functions×1, imp:runtime×1, lrf.bind_functions×2, lrf._bind_preserved_runtime_providers×2, ActionLeaf×1, EFFECT_VERSION×1, Episode.identity×1, record_source_failure×2, tbl:runtime_actions×5, wf.archive×1, wf.completions×4, wf.context×1, wf.controller_value×1, wf.execution_binding×4, wf.grains×1, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2 |
| `task_waiting.py` | 9 | suspension notice to the execution backend | wf.execution_backend×1, wf.execution_handle×2 |
| `to_child_evolutionary_history_evidence.py` | 93 | request assembly for a recursive child (adds scientific_invocation_ref and knowledge inheritance) and the parent-side prepare_parent_request (required return sources, hpc launch handoff field, initial report validation, closed-commission replay, prepare_invocation or prepare_child_request + prepare_assignment, job_child assignment) | imp:.. (parent package)×1, imp:evolutionary_history_evidence_records×1, imp:runtime×1, lrf.bind_functions×1, lrf._bind_parent_runtime×2, EpisodeGoal×2, Episode.identity×3, EpisodeRequest×1, EpisodeReturnRecords×2, validate_saved_fact_form×1, services.capabilities×1, services.scientific_closed_request×1, tbl:runtime_actions×1, tbl:runtime_episodes×1, wf.binding_context×5, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2, wf.run_id×1, wf(self).annotation_child_roles×1, wf(self).available_child_roles×1, wf(self).binding_context×5, wf(self).child_initial_report_input×1, wf(self).context×1, wf(self).episode_bindings×3, wf(self).evolutionary_history_evidence_binding×1, wf(self).expanded_contract_form×1, wf(self).grains×1, wf(self).job_episodes×1, wf(self).journal×2, wf(self).launch_instructions×1, wf(self).resolver×1, wf(self).run_id×4, wf(self).services×2, wf(self).specialist×1, wf(self).store×2, wf(self).validate_report×1 |
| `to_child_execution_job_submission.py` | 30 | request assembly for the launch child (no invocation ref) | imp:episode_contract_information×1, imp:runtime×1, EpisodeGoal×2, Episode.identity×2, EpisodeRequest×1, validate_saved_fact_form×1, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2 |
| `to_child_execution_progress_assessment.py` | 48 | monitor request: assignment validated against the monitor contract; required return monitoring_progress_refs when annotation task required; request assembly | imp:communication×1, imp:domain×1, imp:episode_contract_information×1, imp:runtime×1, EpisodeGoal×2, Episode.identity×2, EpisodeRequest×1, validate_saved_fact_form×1, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2 |
| `to_child_execution_result_acquisition.py` | 30 | request assembly for the results child | imp:episode_contract_information×1, imp:runtime×1, EpisodeGoal×2, Episode.identity×2, EpisodeRequest×1, validate_saved_fact_form×1, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2 |
| `to_child_hpc_work_planning.py` | 91 | request assembly for the hpc child plus a copy of prepare_parent_request | imp:.. (parent package)×1, imp:runtime×1, lrf.bind_functions×1, lrf._bind_parent_runtime×2, EpisodeGoal×2, Episode.identity×3, EpisodeRequest×1, EpisodeReturnRecords×2, validate_saved_fact_form×1, services.capabilities×1, services.scientific_closed_request×1, tbl:runtime_actions×1, tbl:runtime_episodes×1, wf.binding_context×5, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2, wf(self).annotation_child_roles×1, wf(self).available_child_roles×1, wf(self).binding_context×5, wf(self).child_initial_report_input×1, wf(self).context×1, wf(self).episode_bindings×3, wf(self).evolutionary_history_evidence_binding×1, wf(self).expanded_contract_form×1, wf(self).grains×1, wf(self).job_episodes×1, wf(self).journal×2, wf(self).launch_instructions×1, wf(self).resolver×1, wf(self).run_id×4, wf(self).services×2, wf(self).specialist×1, wf(self).store×2, wf(self).validate_report×1 |
| `to_child_published_evidence_assessment.py` | 29 | request assembly for the literature child | imp:runtime×1, EpisodeGoal×2, Episode.identity×2, EpisodeRequest×1, validate_saved_fact_form×1, wf.context×2, wf.evolutionary_history_evidence_binding×1, wf.grains×2, wf.inprocess_completion_order×2, wf.launch_instructions×1, wf.receipts×2 |
| `to_parent.py` | 82 | fact sources and facts: evolutionary_history_evidence_results, received A104 records, alignment-site projections paged 64 at a time, molecular facts; validate_report against frozen site, molecular and process results and the A104 axis report rules | BC.received_record_refs×1, BC.request×1, BC.scope×1, imp:a104_credit×1, imp:a104_investigation×3, imp:a104_scientific_report_validation×1, imp:communication×1, imp:domain×1, imp:evolutionary_history_evidence_reports×1, services.alignment_site_frozen_facts×1, services.alignment_site_own_action_results×1, services.molecular_own_facts×1, services.molecular_received_facts×1, services.scientific_frozen_results×1, services.scientific_received_results×1, wf.store×1 |
| `tool_selection.py` | 64 | tool catalog: resolved selected direct tools (no instructions or routes), process.revise with its description, execution planning catalog; common tool names; proposed selection for process.revise | BC.assignment×1, BC.scope×3, imp:execution_planning×1, services.tool_catalog×2, services.tool_information_catalog×1, services.workflow×1 |
| `yield_estimator.py` | 54 | continuation: task key A104:<a104_task name or projector kind>; declaration must match projector record and yield_method; accumulation, bounded_quality (with projector.native_score_maximum) or completion controller; none without yield bindings | BC.assignment×1, BC.role×1, imp:numerical×3, BoundedYieldController×2, CompletionYieldController×2, YieldController×2, YieldParameters×6 |

## Carried over

Every row of `runs/carry_over/functions/a104__evolutionary_history_evidence.tsv` (156 rows). Machinery is not carried (reason given). Episode functions are in the ten files of `gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/`; a function that is not specific to this episode and not yet in the library is a library candidate where marked. Class rows of the old mix-ins are machinery (replaced by the one class of `episode.py`). Library modules found by `find`: `grading/evolutionary_history_evidence/credit.py` (projectors), `jobs/evolutionary_history_evidence/process_options.py`, `records/evolutionary_history_evidence/{construction_records,domain}.py`, `instructions/evolutionary_history_evidence/*`, `instructions/launch_instructions.py`, `tools/tool_knowledge.py`, `tools/tool_catalog.py`, `tools/evolutionary_history_evidence/tools.py` (`ToolRegistry`, old form: library not carried), `model_exchange/evolutionary_history_evidence/action_transport.py`, `model_exchange/rejection_feedback.py`, `records/progress_views.py`, `configuration/yield_declarations.py`, `forms/phylogeny/*` (already in library). Old shared-root modules with no module in the library (`a104_investigation`, `evolutionary_history_evidence_reports`, `alignment_site_returns`, `evolutionary_result_facts`, `scientific_tool_retrieval`, `execution_planning`, `composition_information`, `numerical`, `a104_scientific_report_validation`, `scientific_support_metadata`) are not read; where this episode used one the use raises or the feature is not offered (see the blocked file `docs/axis_restructure_20261117/carry_over_blocked/a104__evolutionary_history_evidence.md`).

New fields the final form needs: `new field: a104/evolutionary_history_evidence scope`, `new field: a104/evolutionary_history_evidence record_refs`; `evidence_refs` is a `record_refs` field where the old schema had reference text.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| `action_admission.py` | `ScientificTaskAdmission` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `action_admission.py` | `ScientificTaskAdmission.apply_response` | episode function | task.py `action` (decode, schema validation, `empty_reasoning_commit` rejection kept; `Rejected(rejection_feedback(...))`) and `_unit`; not carried from it: the exchange decode, the delivery-resolution and report_update checks, the job_child feedback, the `reads.map` repair hint (A104 has no `reads.map` selected here), the redelivery |
| `action_admission.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `action_execution.py` | `ScientificTaskExecution` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `action_execution.py` | `ScientificTaskExecution.execute` | episode function | task.py tools `selected_tool`, `reason`, `report`, `process_lookup`, `knowledge_lookup`, `process_revise` and `ChildCall` for a child; not carried: `validate_execution_context`, `ActionFailure`, the outcome and credit saving, `receive_outcome`; `retain_shared_grading_results` after `shared.read_information` (no module; the tool is not offered) |
| `action_execution.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `binding_record.py` | `ScientificBindingRecord` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `binding_record.py` | `ScientificBindingRecord.as_record` | machinery | the binding's own as_record() (README 3e); deleted |
| `child_commissioning.py` | `allowed_child_roles` | episode function | task.py `OFFERED_CHILDREN` (the children the model is offered: this episode and hpc) |
| `child_commissioning.py` | `permitted_common_actions` | episode function | task.py `decision_schema` (the action kinds tool, reason, child; `redeliver_report` is not carried) and the new `report` kind |
| `child_commissioning.py` | `ScientificChildCommissioning` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `child_commissioning.py` | `ScientificChildCommissioning.child_roles` | episode function | task.py `CHILD_SLOTS` (the old role names are the slot names) |
| `child_commissioning.py` | `ScientificChildCommissioning.permitted_common_actions` | episode function | task.py `decision_schema` |
| `child_commissioning.py` | `ScientificChildCommissioning.allowed_children` | episode function | task.py `OFFERED_CHILDREN` |
| `child_commissioning.py` | `ScientificChildCommissioning.prepare_child_request` | episode function | messages/msg_to_child.py (the assignment passes unchanged; the monitor's validation against the monitor contract is a check of a commission and is not carried) |
| `child_commissioning.py` | `ScientificChildCommissioning.receive_child_progress_for_role` | machinery | progress provider channel (README 3b R5); the monitor returns its observations in typed fields |
| `child_commissioning.py` | `ScientificChildCommissioning.child_request_assembler` | episode function | messages/msg_to_child.py (one branch per slot) |
| `child_commissioning.py` | `ScientificChildCommissioning.child_report_receiver` | episode function | messages/read_from_child.py |
| `completion_snapshot.py` | `completion_snapshot` | machinery | completion operands read from the runtime tables; the system's `completion` (ended_by, units_consumed, credit) handed to final_to_parent |
| `configuration.py` | `ScientificConfiguration` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `configuration.py` | `ScientificConfiguration.__init__` | episode function | child_roles check -> task.py `CHILD_SLOTS`; replaces_default_instructions -> task.py `decide`; yield_bindings check -> yield_estimator.py `validate_yield_bindings`; `tool_retrieval` configuration -> unplaced (`scientific_tool_retrieval`, no module); contract_information_profile not carried (frozen contract information, README 5 item 16); the library and tool-library records are the frozen directories read from the settings |
| `configuration.py` | `ScientificConfiguration.contract_information_profile` | machinery | frozen contract information of the decision exchange (README 5 item 16); the exchange is not carried |
| `credit.py` | `EvolutionaryHistoryEvidenceCredit` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `credit.py` | `EvolutionaryHistoryEvidenceCredit.credit_kind` | machinery | credit_kind is deleted (README 3d) |
| `credit.py` | `EvolutionaryHistoryEvidenceCredit.credit_projector` | episode function | credit.py `credit_projector` (the projector of the commissioned task; the instruction-version gate is `yield_estimator.py`; the proposed-annotation requirement is `yield_estimator.py`) |
| `credit.py` | `EvolutionaryHistoryEvidenceCredit.credit_view` | episode function | credit.py `credit_view` and `credit` (the projector over `records`) |
| `decision_context.py` | `ScientificTaskContext` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `decision_context.py` | `ScientificTaskContext.assemble_decision_context` | episode function | messages/internal_summary.py (working state, visible record refs, credit view, credit binding, last outcome, feedback, controller) and task.py `decide` (the context sent to the model); not carried: annotation-axis-credit mode, annotation context, `image.view` visual evidence rows (read from `runtime_actions`), `available_report_facts`, `completed_work_axis_results` |
| `decision_context.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `decision_contracts.py` | `ScientificDecisionDeliveryContracts` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `decision_contracts.py` | `ScientificDecisionDeliveryContracts.interpretation_context` | machinery | decision-exchange envelope and replay validation of saved exchanges and frozen contract information (no exchange inside a decision, README 3a) |
| `decision_contracts.py` | `ScientificDecisionDeliveryContracts.exchange_schema` | machinery | decision-exchange envelope and replay validation of saved exchanges and frozen contract information (no exchange inside a decision, README 3a) |
| `decision_contracts.py` | `ScientificDecisionDeliveryContracts.exchange_response` | machinery | decision-exchange envelope and replay validation of saved exchanges and frozen contract information (no exchange inside a decision, README 3a) |
| `decision_contracts.py` | `ScientificDecisionDeliveryContracts.validate_contract_exchange_request` | machinery | decision-exchange envelope and replay validation of saved exchanges and frozen contract information (no exchange inside a decision, README 3a) |
| `decision_contracts.py` | `ScientificDecisionDeliveryContracts.validate_contract_exchange_history` | machinery | decision-exchange envelope and replay validation of saved exchanges and frozen contract information (no exchange inside a decision, README 3a) |
| `decision_contracts.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `decision_delivery.py` | `ScientificDecisionDelivery` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `decision_delivery.py` | `ScientificDecisionDelivery.call` | machinery | one model decision call with replay, receipts and the exchange protocol; `decide` returns a ModelRequest and the system records it |
| `decision_delivery.py` | `ScientificDecisionDelivery.instructions` | episode function | task.py `compose_instructions` |
| `decision_delivery.py` | `ScientificDecisionDelivery.conversation_key` | machinery | conversation state (README 3a: deleted) |
| `decision_delivery.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `decision_exchange.py` | `ScientificDecisionDeliveryExchange` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `decision_exchange.py` | `ScientificDecisionDeliveryExchange.exchange_decision` | machinery | the request_context exchange loop (README 3a: a lookup is a tool; the loop is not carried) |
| `decision_exchange.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `decision_inputs.py` | `ScientificDecisionDeliveryInputs` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `decision_inputs.py` | `ScientificDecisionDeliveryInputs.decision_inputs` | episode function | task.py `decide` (launch instruction library, tool knowledge) and messages/internal_summary.py; not carried: resource context, shared information context, child option information (replaced by `CHILD_PURPOSE`), execution expectations, resource tool estimates, native expectations, native event targets, waiting support, contract profile (no service or module for them; README 5 items 16, 19) |
| `decision_inputs.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `decision_provider.py` | `ScientificDecisionDeliveryProvider` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `decision_provider.py` | `ScientificDecisionDeliveryProvider.decision_completion` | machinery | routes the decision to the provider with the prompt renderer by patching `complete` (provider patching) |
| `episode.py` | `EvolutionaryHistoryEvidenceEpisode` | episode function | episode.py: the one class `EvolutionaryHistoryEvidence(EpisodeBinding)` |
| `episode.py` | `EvolutionaryHistoryEvidenceEpisode._role` | machinery | role check of the old shared binding (each role is its own episode) |
| `episode.py` | `create_execution_bindings` | machinery | home factory building the execution subtree with the caller's operands; no table or list of bindings is written (AGENTS.md) |
| `episode.py` | `create_hpc_bindings` | machinery | home factory building the hpc subtree; no table or list of bindings is written |
| `from_child_evolutionary_history_evidence.py` | `receive_report` | episode function | messages/read_from_child.py (the report; the recorded admission references, native timing receipts, tool attributions and form references are custody) |
| `from_child_evolutionary_history_evidence.py` | `admit_parent_return` | machinery | attempts table, delivery refs and saved admissions (README 3b R1) |
| `from_child_evolutionary_history_evidence.py` | `receive_parent_child_failure` | machinery | a failed child becoming a failed own action (README 3a: a failed child fails the run) |
| `from_child_evolutionary_history_evidence.py` | `_bind_parent_runtime` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `from_child_execution_job_submission.py` | `receive_report` | episode function | messages/read_from_child.py `read_from_child` (the same report text for every child; the references and receipts are custody) |
| `from_child_execution_progress_assessment.py` | `receive_progress` | machinery | progress provider channel (README 3b R5) |
| `from_child_execution_result_acquisition.py` | `receive_report` | episode function | messages/read_from_child.py `read_from_child` (the same report text for every child; the references and receipts are custody) |
| `from_child_hpc_work_planning.py` | `receive_report` | episode function | messages/read_from_child.py `read_from_child` (the same report text for every child; the references and receipts are custody) |
| `from_child_hpc_work_planning.py` | `admit_parent_return` | machinery | attempts table, delivery refs and saved admissions (README 3b R1) |
| `from_child_hpc_work_planning.py` | `receive_parent_child_failure` | machinery | a failed child becoming a failed own action |
| `from_child_hpc_work_planning.py` | `_bind_parent_runtime` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `from_child_published_evidence_assessment.py` | `receive_report` | episode function | messages/read_from_child.py `read_from_child` (the same report text for every child; the references and receipts are custody) |
| `from_parent.py` | `ScientificFromParent` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `from_parent.py` | `ScientificFromParent.assignment_schema` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (selection, proposed_annotation_ref, evidence_refs, constraints, context, revision_origin; new fields scope and record_refs) |
| `from_parent.py` | `ScientificFromParent.child_assignment_schema` | episode function | the proposed-annotation requirement when the annotation task is required: yield_estimator.py (`scientific_task_proposed_annotation_required`); `proposed_annotation_ref` is optional in `ASSIGNMENT_FORM` |
| `from_parent.py` | `ScientificFromParent._selection` | episode function | messages/read_from_parent.py `read_from_parent` (`validate_selection`); the resolution against the frozen libraries is task.py `process_revise` and yield_estimator.py |
| `from_parent.py` | `ScientificFromParent._assignment` | episode function | messages/read_from_parent.py `read_from_parent` (schema, selection, revision_origin); scope checks of the proposed annotation and evidence refs are custody |
| `from_parent.py` | `ScientificFromParent._invocation` | episode function | messages/read_from_parent.py (purpose and initial_report); the closed report_schema is not carried (the parent selects fields) |
| `from_parent.py` | `ScientificFromParent.prepare_assignment` | episode function | messages/msg_to_child.py (own slot: the proposed annotation is inherited; the refusal of a different one and the received-by-parent check are checks of a commission and are not carried) |
| `from_parent.py` | `ScientificFromParent._validate_origin` | machinery | check of a commission's revision origin against the parent's journal (rule 1: a wrong commission fails) |
| `from_parent.py` | `ScientificFromParent.prepare_invocation` | episode function | messages/msg_to_child.py (the filled process with its digests, the closed-commission replay and the mechanics binding are not carried) |
| `from_parent.py` | `ScientificFromParent.required_return_sources` | episode function | messages/msg_to_child.py (`committed_record_refs` always, `evolutionary_history_evidence_results` when `path_depth == 1`, `monitoring_progress_refs` for the monitor) |
| `goal.py` | `ScientificGoal` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `goal.py` | `ScientificGoal.instructions` | episode function | goal.py `GOAL` (the evidence-axis instruction text; the second text for older support-metadata entries is not carried: such an entry has no credit projector, so no controller can be built, see yield_estimator.py) and task.py `compose_instructions` |
| `internal_summary.py` | `ScientificInternalSummary` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `internal_summary.py` | `ScientificInternalSummary.decision_context` | episode function | messages/internal_summary.py (selection, initial_selection_sha256, assignment, permitted_children) and task.py `decide` (axis view, thought pattern, child_tool_info, which need the frozen libraries) |
| `internal_summary.py` | `ScientificInternalSummary._component_scoring_facts` | episode function | returns {}: no component scoring facts; nothing to carry |
| `internal_summary.py` | `ScientificInternalSummary.current_report_facts` | episode function | returns {}: no component scoring facts; nothing to carry |
| `internal_summary.py` | `ScientificInternalSummary.initial_decision_context` | episode function | returns {}: no component scoring facts; nothing to carry |
| `presentation.py` | `present_scientific_context` | episode function | task.py `decide` (the context is sent as a structured mapping; the state machine of decision frames is conversation state and is not carried; the text renderer `render_evolutionary_history_evidence_prompt` of the old providers has no module: unplaced) |
| `presentation_selection.py` | `task_presentation_selection` | episode function | task.py `decide` (the one presentation of this episode; the hpc, monitor, api-launch, selected-execution and receiver renderers belong to other episodes) |
| `received_evidence.py` | `ScientificReceivedEvidence` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `received_evidence.py` | `ScientificReceivedEvidence.received_report_sources` | episode function | messages/final_to_parent.py `RETURN_FORM` (`protein_conservation_outcomes`, `protein_phylogeny_outcomes`); these were sources of role annotation (the root) received from a head |
| `received_evidence.py` | `ScientificReceivedEvidence.received_report_facts` | episode function | unplaced: `evolutionary_result_facts.merge_molecular_facts` and `services.molecular_received_facts` have no module; it served role annotation (the root) |
| `received_evidence.py` | `ScientificReceivedEvidence.validate_received_report` | episode function | messages/final_to_parent.py `validate_report` (the frozen molecular facts are unplaced: `evolutionary_result_facts.validate_frozen_molecular_return`) |
| `received_evidence.py` | `ScientificReceivedEvidence.received_form_references` | episode function | messages/read_from_child.py (`molecular_source_refs` from `validate_conservation_return` and `validate_phylogeny_return`, already in library) |
| `report_delivery.py` | `ScientificReportDelivery` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `report_delivery.py` | `ScientificReportDelivery.finish` | machinery | saving the form once, `form_with_facts`, release and pending handles (README 3b D1); the facts are `final_to_parent` |
| `report_delivery.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `report_integrity.py` | `ScientificReportIntegrity` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `report_integrity.py` | `ScientificReportIntegrity._validate_component_axis_report` | episode function | returns None: nothing to carry |
| `report_integrity.py` | `ScientificReportIntegrity._validate_molecular_report` | episode function | messages/final_to_parent.py `final_to_parent` / `validate_report` (the frozen molecular facts have no module: selecting `protein_conservation_outcomes` or `protein_phylogeny_outcomes` raises `unplaced:evolutionary_result_facts.molecular_own_facts`) |
| `restore_binding.py` | `restore_scientific_binding` | machinery | rebuilds the pinned binding from a run's library directories for old descriptor versions (restore); nothing replaces it |
| `saved_scientific_state.py` | `ScientificSavedScientificState` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `saved_scientific_state.py` | `ScientificSavedScientificState.restore_closed_process` | machinery | restore of a closed process (checkpoint/restore) |
| `saved_scientific_state.py` | `ScientificSavedScientificState.restore_saved_process` | machinery | restore of a saved process (checkpoint/restore) |
| `saved_scientific_state.py` | `ScientificSavedScientificState.validate_context` | machinery | identity check of the old binding context against saved requests |
| `saved_scientific_state.py` | `ScientificSavedScientificState.validate_execution_context` | machinery | old runner's closed-invocation guard (no dispatch for a closed invocation); the system does not dispatch for a closed unit |
| `scientific_assignment_contracts.py` | `_object` | machinery | closed-JSON check of a value; the admission of a `RecordForm` and `validate_selection` (which plain the value) do it |
| `scientific_assignment_contracts.py` | `_ref_schema` | episode function | task.py `_ref_schema` (private copy; library candidate); the schemas built with it are in task.py (`REVISION_ARGUMENTS`, `_CANONICAL_SELECTION`) and messages/read_from_parent.py |
| `scientific_operations.py` | `validate_tool_name` | episode function | task.py `validate_tool_name` (library candidate) |
| `scientific_operations.py` | `ScientificScientificOperations` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `scientific_operations.py` | `ScientificScientificOperations.execute` | episode function | task.py tools `selected_tool` (registry execution; `sequence.align` refused as an `invalid` outcome), `process_revise`; `process.execution` (`execution_planning.read`) is unplaced and not offered; `authenticate_source_byte_operands` is custody (README 3e F3) |
| `source_references.py` | `ScientificSourceReferences` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `source_references.py` | `ScientificSourceReferences.resolve` | machinery | reference resolution through the services ledger; custody (`records.holds`) |
| `source_references.py` | `ScientificSourceReferences.initial_references` | episode function | messages/read_from_parent.py (`evidence_refs`, `record_refs` fields: the evidence and the proposed annotation named in custody) |
| `task.py` | `ScientificTask` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `task.py` | `ScientificTask.next` | machinery | decision-source loop: replay and completion slots, unfinished own actions, ready owned children, source failure; the loop is the system's, the model call is `decide` and `action` |
| `task.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `task_instructions.py` | `compose_instructions` | episode function | task.py `compose_instructions` (library candidate) |
| `task_instructions.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `task_projector.py` | `original_task_projector` | episode function | credit.py `credit_projector` (the three named tasks select their projector, any other name is `A104EvolutionaryCredit`; the old check of the name against `TASKS` and of `allowed_tasks` was a commission check and is not carried) |
| `task_state.py` | `ScientificTaskState` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `task_state.py` | `ScientificTaskState.__init__` | machinery | source state (calls, feedback, last outcome, report values); the state is the summary (`internal_summary`) |
| `task_state.py` | `ScientificTaskState.bind_execution_context` | machinery | binding of the old execution context |
| `task_state.py` | `ScientificTaskState.record_execution_failure` | machinery | a tool returns its failure as its outcome (README 3c) |
| `task_state.py` | `ScientificTaskState.restore_checkpoint` | machinery | checkpoint/restore |
| `task_state.py` | `ScientificTaskState.restore` | machinery | checkpoint/restore |
| `task_state.py` | `ScientificTaskState.record_effect` | machinery | `record_effect` (README 3 deleted names) |
| `task_state.py` | `ScientificTaskState.checkpoint` | machinery | checkpoint/restore |
| `task_state.py` | `_bind_preserved_runtime_providers` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `task_waiting.py` | `ScientificTaskWaiting` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `task_waiting.py` | `ScientificTaskWaiting.suspension_changed` | machinery | suspension notice to the execution backend (wait/suspension machinery) |
| `to_child_evolutionary_history_evidence.py` | `assemble_request` | episode function | messages/msg_to_child.py own slot (objective, message {purpose, initial_report}); EpisodeGoal, EpisodeRequest, identity, scientific_invocation_ref, knowledge inheritance and inprocess_completion_order are the system's |
| `to_child_evolutionary_history_evidence.py` | `prepare_parent_request` | episode function | messages/msg_to_child.py own slot (assignment, required return sources, record passing); the form expansion, closed-commission replay and checks are not carried |
| `to_child_evolutionary_history_evidence.py` | `_bind_parent_runtime` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `to_child_execution_job_submission.py` | `assemble_request` | episode function | messages/msg_to_child.py `launch` slot |
| `to_child_execution_progress_assessment.py` | `prepare_request` | episode function | messages/msg_to_child.py `monitor` slot (the assignment passes as written; its validation is a check of a commission and is not carried) |
| `to_child_execution_progress_assessment.py` | `required_return_sources` | episode function | messages/msg_to_child.py (`monitoring_progress_refs` is always selected for the monitor) |
| `to_child_execution_progress_assessment.py` | `assemble_request` | episode function | messages/msg_to_child.py `monitor` slot |
| `to_child_execution_result_acquisition.py` | `assemble_request` | episode function | messages/msg_to_child.py `results` slot |
| `to_child_hpc_work_planning.py` | `assemble_request` | episode function | messages/msg_to_child.py `hpc` slot |
| `to_child_hpc_work_planning.py` | `prepare_parent_request` | episode function | messages/msg_to_child.py `hpc` slot (copy of the own-slot function; the assignment is the child's own) |
| `to_child_hpc_work_planning.py` | `_bind_parent_runtime` | machinery | provider patching (rebinding into the old runtime namespace); nothing replaces it |
| `to_child_published_evidence_assessment.py` | `assemble_request` | episode function | messages/msg_to_child.py `literature` slot |
| `to_parent.py` | `received_report_facts` | episode function | messages/final_to_parent.py `final_to_parent` (`committed_record_refs` from the summary; the old `received_records(store, ...)` is held records) |
| `to_parent.py` | `ScientificToParent` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `to_parent.py` | `ScientificToParent.fact_sources` | episode function | messages/final_to_parent.py `RETURN_FORM` (committed_record_refs, evolutionary_history_evidence_results, protein_conservation_outcomes, protein_phylogeny_outcomes; the alignment-site sources and the rest of the library report sources have no module: unplaced) |
| `to_parent.py` | `ScientificToParent.facts` | episode function | messages/final_to_parent.py `final_to_parent` (process results, the site projections paged 64 at a time and the molecular facts raise `unplaced:...` where the old code built them) |
| `to_parent.py` | `ScientificToParent.validate_report` | episode function | messages/final_to_parent.py `validate_report` (called before the result is returned) |
| `tool_selection.py` | `ScientificToolSelection` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `tool_selection.py` | `ScientificToolSelection._information_catalog` | machinery | tool catalog of the services for availability against the registry; the frozen tool library is read without it |
| `tool_selection.py` | `ScientificToolSelection._closed_tool_resolution` | machinery | closed-invocation resolution (restore) |
| `tool_selection.py` | `ScientificToolSelection._tool_resolution_for` | episode function | task.py `_resolved_tools` (the closed-invocation branch is restore and is not carried) |
| `tool_selection.py` | `ScientificToolSelection._tool_resolution` | episode function | task.py `_resolved_tools` (library candidate) |
| `tool_selection.py` | `ScientificToolSelection.catalog` | episode function | task.py `selected_tool_entries`, `_common_entries`, `decision_schema` (`process.execution` entries are unplaced) |
| `tool_selection.py` | `ScientificToolSelection.common_tool_names` | episode function | task.py `COMMON_TOOL_NAMES` |
| `tool_selection.py` | `ScientificToolSelection._original_selection` | episode function | messages/read_from_parent.py (`validate_selection`) |
| `tool_selection.py` | `ScientificToolSelection._proposed_selection` | episode function | task.py `process_revise` |
| `yield_estimator.py` | `EvolutionaryHistoryEvidenceYield` | machinery | mix-in class of the old episode, composed in the old episode.py; replaced by the one class of episode.py (no base class for bindings, no mix-in) |
| `yield_estimator.py` | `EvolutionaryHistoryEvidenceYield.private_yield_binding` | machinery | whether yield bindings are configured; a controller is mandatory now |
| `yield_estimator.py` | `EvolutionaryHistoryEvidenceYield.continuation_task` | episode function | yield_estimator.py `continuation_task` |
| `yield_estimator.py` | `EvolutionaryHistoryEvidenceYield.yield_controller` | episode function | yield_estimator.py `yield_controller` (accumulation, bounded_quality with `native_score_maximum`, completion with the `maximum_credit` of the credit definition) |
