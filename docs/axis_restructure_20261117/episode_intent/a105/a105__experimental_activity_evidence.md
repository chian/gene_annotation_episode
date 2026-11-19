# a105/experimental_activity_evidence — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a105/experimental_activity_evidence/<file>`
(only the files directly in this folder; the `published_evidence_assessment/` child is described separately).
Class: `ExperimentalActivityEvidenceEpisode` (mixes 13 private responsibility classes), decision source `ScientificTask`.
`binding_path = 'experimental_activity_evidence'`, `commissioning_parent = 'legacy_annotation'`, role `experimental_activity_evidence`,
`VERSION = 'experimental_activity_evidence_episode_v10'`, `AXIS = 'A105'`.

## What this episode is for (its goal, in its own words)

The A105 axis head: an ordinary scientific episode filled from a parent-selected **evidence axis (A105) + thought
pattern (P...) + actually retrieved tool set**. `goal.py` has two goal texts, chosen by the selected axis entry's version:

- Published instruction entry (`INSTRUCTION_VERSION`): "Determine what the supplied target does within the parent's
  assigned question, scope and constraints. Start with the supplied sequence, selected file contents or snippets ...
  No initial candidate annotation or publicly searchable name is required. Possible functions can emerge from the
  evidence and be compared or revised. Apply the complete selected investigation instructions and thought-pattern
  guidance on every decision ... Selected instructions describe how to investigate; they are not evidence about this
  target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of
  inference ... Missing information remains unknown." Then: choose a tool, commit an interpretation through the
  reasoning action, commission a scoped child with its own typed return, or wait; keep the assigned axis, thought
  pattern and tools; `process.revise` only prepares an alternative selection for a *new* child; "The configured
  controller owns continuation. Waiting and unchanged observations do not manufacture progress."
- Evidence-axis entry (`EVIDENCE_AXIS_VERSION`): "Investigate the parent's assigned scientific problem iteratively ...
  The selected scientific support proposition and operands define the support problem; the thought pattern supplies
  alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts ...
  Library sources are instruction provenance, not scientific evidence about this target ... annotation_support_routes
  describes the actual separately bound annotation policy's kind dispatch ... Metadata itself earns no credit and
  never replaces or filters the actual projectors, annotation formula or continuation rule ... Request the recorded
  experimental_activity_evidence_results source in child forms when their process relationships and existing closed
  credit/yield are needed for steering."

## Task and instructions

`task_instructions.instructions(source, context)` composes, in order:
1. old shared base `runtime_prompt.INSTRUCTIONS` (from `a105.library.literature_investigation_prompt`);
2. the binding's own `instructions(context)` (goal text above), *replacing* the base when
   `replaces_default_instructions` (all selected axis entries are published instruction entries), else appended;
3. `REASONING_COMMIT_REQUIREMENT` when `reason` is permitted; tool-knowledge and launch-instruction texts when present;
4. pending-child-delivery repair text (`redeliver_report`, preserve `current_report_update`);
5. **wait text** (this episode permits `wait`): a `pending_child_` handle names the in-process child; wait with
   `event returned, after_cursor 0, reconsider_at null`; waiting earns no credit;
6. native-event-target text when native event information exists;
7. under the decision-exchange protocol, the base history guidance is replaced by the `request_context` /
   `episode.history view=records` guidance.

`task.py` (`ScientificTask.next/apply_response/execute/finish`): one model decision per unit; invalid selections are
recorded as rejected effects with typed feedback (contract-information errors carry a schema repair hint;
`component_native_return_channels_required` carries required fact sources); an all-empty reasoning commit is rejected
unless the binding says it has task content; every executed tool/reason/wait enters the iterator with its credit
(failed/invalid included, as `ActionFailure` when no outcome is observed); `execute` validates the execution identity
first (`validate_execution_context`); `shared.read_information` retains shared grading results; `finish` builds the
typed form from facts + interpretations.

## What it reads from its parent's assignment

`_ASSIGNMENT` (scientific_contracts.py) — required `selection`, `evidence_refs`, `constraints`, `context`:
- `selection`: `{version: SELECTION_VERSION, evidence_axis: option ref (slot evidence_axis, option_id const 'A105'),
  thought_pattern: option ref (P<n>), child_tool_info: [{name, resources: api|local|hpc}]}`; recorded form
  materialises `child_tool_info` with `description` + `instructions`. Library id must equal this binding's library;
  axis entry must be an instruction or evidence-axis entry (`scientific_support_metadata_required` otherwise).
- `proposed_annotation_ref` (in scope, namespace `hypothesis`; required when `annotation_task_required`; inherited from
  parent and must not differ).
- `evidence_refs` (each in scope).
- `context.evidence_task = {version evidence_axis_task_v1, kind whole_axis_findings, evidence_axis A105,
  credit_unit > 0}` — the credit unit of the configured credit definition ("do not select or change its cutoff").
- optional `revision_origin` (`experimental_activity_evidence_revision_origin_v1`, parent invocation ref, preparation
  operation ref) — authenticated against the parent's `process.revise` preparation.
Invocation: `{objective, purpose, report_schema (closed), initial_report}`; the filled request carries
`filled_experimental_activity_evidence_v1 {selection, assignment_sha256, invocation_sha256, mechanics_binding}`.

## Children it may commission

`child_roles` = configured tuple, must include its own role; `child_request_preparer` / `child_report_receiver`:

| child role | folder | what it sends | what it takes back |
|---|---|---|---|
| `experimental_activity_evidence` (recursive copy of itself) | self | `prepare_invocation(...)`: validated scope, expanded child return schema (required return sources must appear exactly once), validated initial report, assignment (selection may be a `process.revise` alternative with `revision_origin`), filled process record | admitted typed form; references from the form, plus `episode_bindings.received_form_references` (old table) and native timing receipts; receipts inherited as `child_form` |
| `literature` → `published_evidence_assessment` | child | `binding.prepare_assignment(...)` of the literature binding with the parent's selection assignment (literature task, refs, requested components) | same admission path; the literature binding's own `received_form_references` turns population cells into this episode's record refs |

Both `from_child_*` files are byte-identical apart from their docstring; both also carry a copy of the old workflow
`admit_return` (saved attempt / delivery feedback / redelivery).

## Decision state and what it shows the model

`decision_inputs.build_decision_inputs` + `ScientificTaskDecision.call`: goal, scope, working_state, visible_record_refs,
current_credit, current_evidence_vector (axis components), investigation_progress (retained_finding_count,
inactive_dependencies, detail_pages) when receipt projection, credit_binding, time_accounting, pending_work,
last_local_outcome, feedback, visual_evidence (last `image.view`), report_deliveries, controller, controller_binding,
tools, tool_knowledge, job_episode_options, available_report_facts, requested_report_purpose/form,
current_report_update/basis, report_lifecycle; plus annotation context for scientific sources; native timing
(`monitoring_information_credit`); the binding's `decision_context` →
`experimental_activity_evidence {selection, initial_selection_sha256, evidence_axis|annotation view,
annotation_support_routes (non-published entries), thought_pattern (id, name, description, use_when,
live_alternatives, decision_guidance, outcome_contingencies, boundary), child_tool_info|tools, assignment,
permitted_children}`; call adds resource_context, shared_information_context, launch_instruction_library,
selected_launch_instructions, child_options, completed_action_reports, execution_expectations,
resource_tool_estimates, native_execution_expectations, **waiting_support**, contract_information_profile.
`standalone_presentation`: a head built directly with an injected root projector (credit mode
`annotation_axis_credit`) shows the root-shaped frame (arms, annotation_credits, root_score) and a root yield table.

## Tools it offers

`_COMMON_TOOLS` (process.search/entry/sources/tools, knowledge.search/entry/read, episode.history/credit/
annotation_score/monitoring_information/estimate_wait, shared.request/publish/resolve/read/list_information) + the
selected tools with a direct invocation route + `process.revise` (prepare a different thought pattern and/or tools for
a new child; no current change, no observation) + `process.execution` (execution recipe/timing history for a
selected tool/resource pair; `evidence_role operational_planning_only`, `scientific_credit 0`). `material.*`/`source.*`
byte operands are authenticated; `process.tools` goes to the tool retriever. Common actions: tool, reason, child, wait,
redeliver_report.

## How its credit is counted

`credit_projector` → `ScientificFindingProgress(FindingProgressPolicy(credit_unit))` for the original
`whole_axis_findings` A105 task (none if the axis entry is neither instruction nor evidence-axis). Credit = the
projector's scalar over retained findings (finding_unit × count); unbounded. Requires the proposed annotation when yield
bindings are configured.

## Continuation

`continuation_task` = `A105:whole_axis_findings`. Declaration `{kind, cutoff, parameters: {uncertainty_alpha},
credit_definition}`; `credit_definition` digest must equal the projector record and `projector.yield_method` must equal
`kind`. Kinds map onto the three estimators: `accumulation`, `bounded_quality` (maximum = `projector.native_score_maximum`),
`completion`. Old route returned `None` (recorded controller) when no declaration — must become an explicit error.

## What it reports to its parent

`required_return_sources`: under an annotation task, a root parent (path length 1) must request
`experimental_activity_evidence_results` and `committed_record_refs`; deeper parents `committed_record_refs`.
`facts`: `experimental_activity_evidence_results` = own process result merged with received child results (projected
through library/tool library). `validate_report`: form validated; process-result fields must equal the frozen closing
results (`runtime_forms`). `report_snapshot`: completion snapshot adds initial_credit, credit, controller_credit,
episode_yield, parent_invocation_ref.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | — | — |
| `binding_record.py` | 8 | record: version, binding_id, library, tool_library, child_roles, tool_retrieval, contract profile, yield_bindings | — |
| `configuration.py` | 40 | child roles must include own role; `replaces_default_instructions`; tool retrieval config; yield declaration validation (three kinds) | imports `a105.composition_information:CONTRACT_INFORMATION_PROFILE`, `a105.numerical:{YieldController,BoundedYieldController,CompletionYieldController,YieldParameters}`, `a105.scientific_tool_retrieval:configuration` |
| `credit.py` | 61 | whole-axis finding projector with `credit_unit`; `credit_kind` scientific | `services.workflow`→`workflow.scientific_projector_for_context/projector_receipt_arguments/projection_view`; `self.services.{proposed_annotation_for, annotation_task_required, scientific_credit, scientific_credit_for}`; imports `..communication:plain`, `..investigation_progress` |
| `decision_inputs.py` | 35 | what the model sees (list above) | `self.workflow.{store×3, working_state, journal×2, run_id, local_outcome_preview, source_credit_view, receipt_projection, source_credit_binding, pending_work, delivery_status, controller_binding, catalog, knowledge, job_episode_options, extra_report_sources, is_scientific_source, specialist, binding_context, tools}`; table `runtime_actions`; runtime `{FACT_MEANINGS, FACT_SOURCES, Mapping, _references_in, json}` |
| `episode.py` | 58 | composition; permitted actions incl. wait; child preparer/receiver maps (`experimental_activity_evidence`, `literature`) | — (only own modules) |
| `execution_planning.py` | 31 | `process.execution` catalog + read (operational planning, no credit) | `services.workflow`→`workflow.resource_context`; imports `..execution_planning:memory_for`, `..execution_memory:validate_profile`, `..execution_contracts:obj` |
| `from_child_experimental_activity_evidence.py` | 62 | admit a recursive child's form and turn it into record refs | `workflow.{receipts×3, is_job_source×2, store×7, run_id×5, binding_context×3, progress_provider×2, specialist, journal, episode_bindings, native_timing_information, job_episodes×2}`; tables `runtime_actions`, `runtime_report_attempts`; runtime `{_references_in, json, _json, _digest, Record, ReportDeliveryError, ReportBoundaryError, WorkflowError}`; `a105.episode_return_records:EpisodeReturnRecords`; `episode_journal:WorkflowError`; workflow-as-self `admit_return` (`self.journal`, `self.store`, `self.save_attempt`, `self.delivery_feedback`, `self.receive_form`) |
| `from_child_published_evidence_assessment.py` | 62 | same admission for the literature child | identical to the file above |
| `from_parent.py` | 182 | assignment schema, selection/assignment validation, revision-origin authentication, invocation + filled record, context validation | `self.services.{reference_in_scope, scientific_preparation, scientific_parent_preparation, proposed_annotation_for, annotation_task_required, scientific_saved_request}`; `workflow.{experimental_activity_evidence_binding, run_id, store, journal}`; table `runtime_actions`; `a105.episode_return_records:EpisodeReturnRecords`; `a105.episode_composition:scientific_binding_compatible` |
| `goal.py` | 14 | the two goal texts | — |
| `internal_summary.py` | 26 | `decision_context` (selection, axis/thought view, tools, permitted children) | `self.services.scientific_support_routes` |
| `invocation_state.py` | 98 | restore exact saved/closed request mechanics | `BindingContext` (`receiving_context`), `services.workflow`→`workflow.journal/run_id`, `journal.row/run_id`, table `runtime_episodes`, `method_loop.identities:EpisodeRef`, `a105.episode_composition:scientific_binding_compatible` |
| `library_operations.py` | 14 | `process.tools` retrieval and library dispatch | `workflow.{scientific_library_available, binding_context, services.execute_scientific_library}`; `..library.scientific_catalog_operations:retrieve_tools` |
| `library_services.py` | 38 | library/retriever catalogs, support routes, provenance and retriever construction | imports `..experimental_activity_evidence_library`, `..scientific_tool_library`, `..scientific_support_metadata`, `..experimental_activity_evidence_provenance`, `..scientific_tool_retrieval` |
| `presentation_fields.py` | 29 | commissioned frame: own form + child forms; native timing kept separate from finding credit | `source.workflow.annotation_context`; runtime `_plain` |
| `report_snapshot.py` | 5 | completion snapshot fields | workflow-as-self `self.journal.row('runtime_episodes')`, `self.source_controller_credit`, `self.services.scientific_parent_invocation` |
| `scientific_contracts.py` | 57 | ROLE/AXIS/version; `_COMMON_TOOLS`; assignment/selection/evidence-task schemas | imports `a105.communication`, `communication:ReportBoundaryError`, `a105.domain`, `a105.episode_bindings:reference_in_context`, `a105.experimental_activity_evidence_records`, `a105.experimental_activity_evidence_reports`, `a105.scientific_support_metadata`, `a105.evidence_axis_contracts`, `a105.evidence_axis_instructions`, `a105.experimental_activity_evidence_library` |
| `scientific_operations.py` | 94 | tool catalog, `process.revise`, `process.execution`, tool execution | `self.services.{tool_catalog×2, tool_information_catalog, authenticate_source_byte_operands, execute_tool}` |
| `source_references.py` | 20 | reference resolution in scientific namespaces; initial refs = evidence refs + proposed annotation | `self.services.scientific_reference`; `reference_in_context` (episode_bindings) |
| `standalone_presentation.py` | 38 | root-shaped presentation for a directly-built head | `source.workflow.journal`; table `runtime_actions`; runtime `{Mapping, json, yield_table}` |
| `task.py` | 225 | decision/apply/execute/finish loop (see above) | ~45 distinct `self.workflow.*` (execution_binding×7, journal×9, store×9, completions, inprocess_replay, selected, completed_unit, next_return, resolve_pending_deliveries, delivery_resolution_inputs, action_schema, permits_common_action, reasoning_action_schema, specialist, binding_context, execute, receive_outcome, receive_native_outcome, automatic_score_updates, source_credit_view, last_observed_credit, retain_shared_grading_results, controller_value, facts, release, pending_handles, episode_bindings, resolver, validate_report, experimental_activity_evidence_binding ...); journal tables `runtime_actions/model_calls/episodes/forms`; ~25 runtime names; `provider_errors:ModelCallError`, `episode_source_failure`, `task_action_units:ActionFailure`, `episode_contract_information:ContractInformationError` |
| `task_decision.py` | 329 | model call, saved-request replay, decision-exchange protocol (request_context lookups: child_options, composition_information, own attempts) | `self.workflow.{journal, provider×4, decision_exchanges×4, decision_protocol×3, validate_contract_information×5, contract_information_reply, freeze_contract_information, freeze_literature_numerical_contracts, numerical_contracts, receipts×4, resource_context, shared_information_context, launch_instructions, available_child_roles, episode_bindings, execution_expectations, resource_estimator×4, native_estimation_context, waiting_support, history_preview, services.instructions, services.decision_exchange_instructions, controller_binding, execute ...}`; `exchanges.*`; table `runtime_model_calls×8`; ~30 runtime names |
| `task_instructions.py` | 28 | instruction composition incl. wait and native-event text | `runtime_prompt.*`; `source.workflow.{specialist, binding_context, permits_common_action×3, knowledge, launch_instructions, native_event_information, decision_protocol, is_job_source}` |
| `task_state.py` | 108 | per-episode state; failure becomes a failed outcome entering the iterator | `workflow.{context, grains, execution_handle, execution_backend, archive, store, run_id, journal×5, source_credit_view, controller_value, execution_binding×4, completions×4, inprocess_replay×7, recover_commissions, progress_provider}`; table `runtime_actions`; runtime `{Episode, Record, ActionLeaf, EFFECT_VERSION, ...}` |
| `to_child_experimental_activity_evidence.py` | 42 | recursive child request (see children) | `workflow.{store, expanded_contract_form, episode_bindings×3, binding_context×3, child_initial_report_input, specialist, available_child_roles, annotation_child_roles, services.capabilities, launch_instructions, journal, context, grains, run_id, services}`; tables `runtime_actions`, `runtime_episodes`; `EpisodeReturnRecords` |
| `to_child_published_evidence_assessment.py` | 33 | literature child request via `prepare_assignment` | same family of `workflow.*` names |
| `to_parent.py` | 84 | required return sources, facts, report validation against frozen results | `self.services.{annotation_task_required, scientific_received_results(_for), scientific_frozen_results(_for)}`; `ReportBoundaryError`; table `runtime_forms`; `..experimental_activity_evidence_provenance:_detached,_load` |
| `waiting.py` | 12 | selected wait; unavailable target → failed outcome | `self.workflow.perform_selected_wait`; runtime `EventTargetError, _wait_target_feedback` |
| `yield_estimator.py` | 47 | task key + three-kind controller binding | `a105.numerical:{YieldController, BoundedYieldController, CompletionYieldController, YieldParameters}` |

Full counts: `runs/carry_over/calls/a105_01.tsv`.

## Differences from similar episodes

- Unlike its `published_evidence_assessment` child: this head is filled from an **A/P/tool selection** (evidence axis
  + thought pattern + retrieved tools, `process.revise`, `process.execution`, `process.tools`); its credit is the
  whole-axis finding projector, not a literature task count; it permits **wait** (child does not); its continuation
  task is a single `A105:whole_axis_findings` with three possible kinds (child: six task keys, two kinds); it reports
  `experimental_activity_evidence_results` (child: population cells, screening answers, source leads).
- Decision source differs from the child: `call` adds `waiting_support`, validates the execution identity before each
  new model call, and calls `provider.complete` directly (the child uses its presentation-aware
  `decision_completion` with `render_literature_experimental_prompt`).
- It commissions a recursive copy of itself; the literature chain below does not recurse.
