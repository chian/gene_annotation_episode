# a102/structural_homology_evidence — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/` (46 files directly in the
folder; no `grading/` or `scoring/` subfolder). Child folders and `tests/` were not read. Nothing from the old
shared root was read; where a behaviour lives there, this page says only what the episode's own file asks of it.

Old binding: class `StructuralHomologyEvidenceEpisode`, `binding_path = 'structural_homology_evidence'`,
`commissioning_parent = 'legacy_annotation'`, role `structural_homology_evidence`, version
`structural_homology_evidence_episode_v10`, axis `A102`. Decision source: `StructuralHomologyEvidenceTask`.

## What this episode is for

The A102 axis head. In its own words (`goal.py`, instruction-entry variant):

> Determine what the supplied target does within the parent's assigned question, scope and constraints. Start
> with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and
> known context. No initial candidate annotation or publicly searchable name is required. Possible functions can
> emerge from the evidence and be compared or revised.

and (`scientific_guidance.py`), placed in front of it:

> A102 owns structural work only. Scientific descendants remain A102. […] Reuse qualified retained alignments.
> Native comparison results automatically populate the A102 numerical sheet before credit inspection; unknown
> functional features do not erase measured native correspondence. Follow up for missing structural cells,
> preserve original scope and model uncertainty, and distinguish fold resemblance from exact function. Novel
> folding requires an explicit configured remote/API/HPC binding; use structure.model_request when it is missing.

When the library's A102 entry is the merged entry the prefix is instead: "A102 owns comparative and experimental
structural evidence. Scientific descendants remain A102. Use either path or both as useful, and return their
separate scientific quantities and shared dependencies."

It is one recursive role: a head may commission another `structural_homology_evidence` episode with a different
thought pattern and tool selection.

## Task and instructions

- One unit is one model-selected action: a tool action, a reasoning commit, a child commission, a wait, or a
  redelivery of a child's report (`child_commissioning.py`: `('tool', 'reason', 'child', 'wait',
  'redeliver_report')`).
- Instruction text (`goal.py`) has two variants chosen by the selected evidence-axis entry's version.
  - Instruction entry: the text quoted above, then: apply the selected investigation instructions and
    thought-pattern guidance on every decision; selected instructions are how to investigate, not evidence about
    the target; "Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits
    of inference when interpreting evidence. Missing information remains unknown."; use only the selected actual
    tools; keep inherited information distinct from new findings and completed work distinct from attempts;
    "Return valid partial findings and specific failures through the requested form."; "Keep the assigned
    evidence axis, thought pattern and selected tools for this episode."; "Children own their iterative choices.
    The configured controller owns continuation. Waiting and unchanged observations do not manufacture progress."
  - Support-proposition entry: "Investigate the parent's assigned scientific problem iteratively in the shared
    Episode loop. […] The selection is no prescribed sequence or automatic compatibility verdict. Library sources
    are instruction provenance, not scientific evidence about this target. […] Metadata itself earns no credit
    and never replaces or filters the actual projectors, annotation formula or continuation rule."
- `task_instructions.py` composes the full text: default instructions, then the binding's (which replace the
  default when every evidence-axis entry in the library is an instruction entry), the reasoning commit
  requirement, tool knowledge, the launch instruction library, a paragraph on repairing an undelivered child
  report with `redeliver_report`, the wait paragraphs, the native event targets paragraph, and guidance on using
  `request_context` for its own history.

## What it reads from its parent's assignment

Assignment form (`scientific_contracts.py`, `_ASSIGNMENT`; required: `selection`, `evidence_refs`, `constraints`,
`context`):

| Field | Meaning |
|---|---|
| `selection.evidence_axis` | option reference, slot `evidence_axis`, `option_id` fixed to `A102` |
| `selection.thought_pattern` | option reference, slot `thought_pattern`, id `P<n>` |
| `selection.child_tool_info` | unique list of `{name, resources}` with `resources` in `api`, `local`, `hpc` |
| `proposed_annotation_ref` | "The proposed annotation this task evaluates." Optional in the form; required when an annotation task is required |
| `evidence_refs` | unique record references |
| `constraints` | record |
| `context.evidence_task` | `{version: evidence_axis_task_v1, kind: whole_axis_findings, evidence_axis: A102, credit_unit > 0}` — "Use the finding unit in the explicitly configured credit definition for this exact task; do not select or change its cutoff." |
| `context.a102_task` | read by `task_projector.py` and `yield_estimator.py` (a named A102 sub-task; not declared in `_ASSIGNMENT`) |
| `revision_origin` | present when the commission came from the parent's `process.revise` |

Checks (`from_parent.py`): the selection belongs to this library and resolves to an instruction or evidence-axis
entry; the tool info resolves; every evidence reference and the proposed annotation are inside the assigned scope;
the proposed annotation was received by the parent and a descendant may not change it
(`child_proposed_annotation_differs_from_original_task`); a `revision_origin` must match the parent's recorded
`process.revise` preparation. The invocation it accepts is `{objective, purpose, report_schema, initial_report}`.

From the request it also reads the report contract (purpose and typed form) and `initial_report` (its report
starts from it).

## Children

Children are the configured `child_roles` (must include its own role). `child_message_owners.py` names eight:

| Old role | Child episode | Sent | Taken back |
|---|---|---|---|
| `structural_homology_evidence` | itself (recursive) | assignment with the selection and `revision_origin` from `process.revise`; goal, purpose, typed return form and initial report chosen by the model | typed form; when an annotation task is required it must carry `committed_record_refs` (and `structural_homology_evidence_results` for a direct child of the root) |
| `literature` | `published_evidence_assessment` | assignment as selected; this parent's own request envelope (`to_child_published_evidence_assessment.assemble_request`) | typed form through this parent's own receiver (`from_child_published_evidence_assessment.receive_report`): form references, progress forms, native timing receipts, tool attributions |
| `launch` | `execution_job_submission` | launch assignment as selected | typed form; `execution_handoff_refs` required by that child when an annotation task is required |
| `results` | `execution_result_acquisition` | results assignment as selected | typed form |
| `launch` | `resource_work_submission` | as selected | typed form |
| `results` | `resource_result_acquisition` | as selected | typed form |
| `hpc` | `hpc_work_planning` | as selected | typed form |
| `monitor` | `execution_progress_assessment` | assignment validated against the monitor's own form ("This parent requests information; it never polls here.") | typed form; `monitoring_progress_refs` required when an annotation task is required; only `episode_progress` references in the form grant received monitoring observations |

For every child (`to_child_*.py`, same text in each): the model supplies the goal, purpose, a typed return form
and an initial report; each return the child requires must appear in the form exactly once; the initial report
must fit the form; the role must be allowed. For every return (`from_child_*.py`, same text in each): the form is
admitted against the report contract; a failed admission is recorded and becomes feedback the parent repairs with
`redeliver_report`, reusing the child's saved facts; admitted references become received records.

The old roles `launch` and `results` each have two homes (execution and resource); `child_message_owners.py`
requires exactly one candidate to match.

## Decision state and what it shows the model

State kept by the source (`task_state.py`): number of calls, last outcome and its index, feedback, current report
values (from `initial_report`) and the records they rest on.

Model inputs (`task.py`): goal, scope, working state, visible record references, current credit, current evidence
vector, credit binding, time accounting, pending work, last outcome, feedback, visual evidence from the last
`image.view`, child report deliveries, controller state, tools, tool knowledge, job options, available report
facts, requested report purpose and form, current report update and its basis, child reports; for a scientific
source the proposed-annotation context.

The binding's own block (`internal_summary.py`, key `structural_homology_evidence`): the selection, digest of the
initial selection, the evidence-axis view, annotation support routes (not for instruction entries), the thought
pattern (`id, name, description, use_when, live_alternatives, decision_guidance, outcome_contingencies, boundary`),
the selected tool info, the assignment, the permitted children. `received_structural_context.py` adds
`received_structural_evidence` for the merged entry.

Added before each decision (`decision_delivery.py`): resource context, shared information, launch instruction
library and selected launch instructions, child options, completed action reports, pending work, execution
expectations, resource estimates, waiting support, and restored history when the provider session is new.
Before selecting, the model may ask for context (`request_context`: child options, composition information, its
own earlier attempts); that creates no unit.

Presentation (`decision_presentation.py`): a text prompt, with the renderer chosen by what the context is (HPC,
published scientific, API launch, selected execution, monitor, otherwise receiver).

Admission (`task.py`): an empty reasoning commit is refused unless it declares `no_applicable_evidence`; a
response that fails admission gives feedback and no unit; the report update is admitted separately so an invalid
report does not lose the selected work.

## Tools it offers

`operations.py`:

- the tools in `selection.child_tool_info` whose route is direct, resolved against the actual tool catalog for the
  scope (a tool reachable only by commission is not offered directly; `scientific_commission_catalog.py` lists
  those from the launch and results children);
- `process.revise` — "Prepare a different thought pattern and/or selected actual tools for a new child
  investigating the same evidence axis. […] Changes no current process, starts no child and records no biological
  observation.";
- the execution-planning catalog from the old shared root (its contents were not read; `operations.py` handles
  `process.execution` as a read and authenticates `execution.estimate` for `sequence.align`);
- the common tools (`scientific_contracts._COMMON_TOOLS`): `process.search, process.entry, process.sources,
  process.tools, knowledge.search, knowledge.entry, knowledge.read, episode.history, episode.credit,
  episode.annotation_score, episode.monitoring_information, episode.estimate_wait, shared.request_information,
  shared.publish_information, shared.resolve_information_need, shared.read_information, shared.list_information`.

A selected tool may not use a common tool name or `process.revise`. `sequence.align` and source/material tools
have their operands authenticated first; `structure.*`, `result.blast.hsp` and `source.locate` may read only
records this episode has received.

## How its credit is counted

Credit kind `scientific`. `credit.py` selects a projector from the assignment (`task_projector.py`):

- library entry not merged: structural credit (`A102StructuralCredit`);
- merged and `context.a102_task.name` is `functional_feature_geometry`, `functional_contrast`,
  `reference_attribution`, `local_trait_attribution` or `interface_constraints`: the matching credit class;
- otherwise the projector of the assignment (`credit_projector(assigned)`).

The credit view itself comes from `services.scientific_credit` (old shared root, not read). In this folder:
credit is measured after every observed outcome and enters the iterator; a wait carries the previous credit; a
failed action still enters with its credit (`task.py`, `task_state.py`). A proposed annotation is required when
yield bindings are configured.

## Continuation

`yield_estimator.py`. The continuation task is `A102:{a102_task name}` when the assignment names one, else
`A102:{projector kind}`. Its declaration in `yield_bindings` has exactly `kind`, `cutoff`, `parameters`
(`uncertainty_alpha` only) and `credit_definition`. The declaration must exist, its `credit_definition` must equal
the projector's record, and the projector's `yield_method` must equal `kind`:

| `kind` | Old controller | Settings |
|---|---|---|
| `accumulation` | `YieldController` | cutoff, `uncertainty_alpha` |
| `bounded_quality` | `BoundedYieldController` | cutoff, maximum = `projector.native_score_maximum`, `uncertainty_alpha` |
| `completion` | `CompletionYieldController` | cutoff, `uncertainty_alpha` |

All three of today's estimators are used, chosen per commissioned task. With no `yield_bindings` the old binding
returned `None` and left continuation to the workflow's recorded controller.

## What it reports to its parent

`to_parent.py`, `report_delivery.py`, `report_validation.py`, `report_integrity.py`, `report_snapshot.py`:

- the typed form the parent asked for: the model's report values plus facts;
- fact sources: `structural_homology_evidence_results` (its own process result merged with those received from
  children), alignment-site results (requested projections, read in pages of 64), protein-structure action facts
  (received and own);
- the report must equal the frozen process results, frozen site results and frozen protein-structure action
  facts; a structural report's `comparative_status` and `experimental_status` may not differ from the delivered
  structural evidence;
- the completion snapshot carries initial credit, credit, controller credit, episode yield and the parent
  invocation reference;
- without a report contract the result is `{credit, pending_handles}` plus current facts.

## How it differs from similar episodes

- It is the only one of these four with scientific credit, a reasoning action, a recursive child and
  `process.revise`; the three execution episodes below it have operational credit.
- It keeps its decision call, context additions and exchange loop in one 348-line `decision_delivery.py`;
  `execution_job_submission` splits the same text over `task_decision.py`, `decision_inputs.py`,
  `decision_state.py`, `decision_contracts.py`, `decision_exchange.py` and `decision_provider.py`.
- It validates the execution context before a new model call (`decision_delivery.py`) and before executing
  (`task.py`) (`validate_execution_context`: a closed request permits replay, never new dispatch); the execution
  episodes do not.
- Six `to_child_*.py` and six `from_child_*.py` files carry the same text; `execution_progress_assessment` and
  `published_evidence_assessment` have additions (above).

## Points the carry-over has to settle (seen in these files)

- The model declares each child's typed return form and initial report at commission time; the contract has the
  child declare `return_form` and the parent may commission a `report_form`.
- `redeliver_report` and `wait` are actions of the old runner; the contract's decision-source pattern lists
  reasoning commit, tool action and child commission.
- The `request_context` exchange inside one decision has no counterpart named in the contract.
- Replay of closed commissions, receipts, staged completions and checkpoints (most of `from_parent.py`'s closed
  branch, `saved_scientific_state.py`, `task_state.py`, `decision_delivery.py`) is old-runner machinery that the
  new journal and recorder replace.
- `episode.py` constructs thirteen child bindings in `create_*_bindings`; the contract has a home factory do this.

## Old-runner names (totals for this episode)

| Group | Distinct names | Uses |
|---|---|---|
| `self.workflow.<member>` | 86 | 529 |
| BindingContext (`binding_context`), receipts, return records, `UnitRef`, raw `store.db.execute`, `_ready_owned_child` | 5 | 86 |
| imports from old `root.a102` shared modules (incl. `runtime`, `providers`, `communication`, `decision_context`, `episode_bindings`, `episode_journal`, `composition_information`) | 39 | 100 |
| old `services.<member>` (services held the Workflow) | 27 | 53 |
| old binding registry members | 5 | 28 |
| old journal and receipt tables | 5 | 64 |
| old yield names | 4 | 20 |
| symbols through `runtime`, `runtime_prompt`, `providers` | 68 | 289 |

Counted mechanically from the files at `97308b94c`; every row (name, file, uses, purpose) is in `runs/carry_over/calls/a102_01.tsv`. In `from_child_*.py` and `to_child_*.py` the first parameter `self` is the old Workflow, so `self.x` there is counted as `self.workflow.x`; `workflow.x` and `source.workflow.x` are counted the same way. Attribute reads on the old context object (`context.role`, `.path`, `.assignment`, `.scope`, `.request`) are not counted separately.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty | none |
| `child_commissioning.py` | 29 | permitted actions tool/reason/child/wait/redeliver_report; allowed children = configured child roles; monitor child request is validated against the monitor form and its progress is received through this parent's own receiver | none |
| `child_message_owners.py` | 102 | names the eight child homes per old role (self, literature, two launch, two results, hpc, monitor) and selects that child's to/from module; exactly one candidate per role | `EpisodeBindingRegistry` 1, `import root.a102.episode` 1, `import root.a102.runtime` 1, `registry._by_path` 16, `registry._by_role` 8, `self.workflow.episode_bindings` 1, `self.workflow.structural_homology_evidence_binding` 1 |
| `configuration.py` | 9 | exposes the frozen contract-information profile to annotation/self parents | none |
| `credit.py` | 25 | credit kind scientific; projector chosen from the assignment (task_projector); proposed annotation required when yield bindings exist | `import root.a102.structural_homology_evidence.task_projector` 1, `services.scientific_credit` 1 |
| `decision_delivery.py` | 348 | one decision call: adds resource/shared/launch-instruction/child-option/completed-work/pending/expectation/estimate/waiting context; request_context exchange loop (child options, composition information, own attempts); validates execution context before a new call | `binding_context` 2, `import root.a102.episode_work_report` 2, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `runtime._action_generation_schema` 2, `runtime.apply_state_frame` 1, `runtime._ASSIGNMENT_TRANSPORT` 1, `runtime._category_yield_parameters` 1, `runtime.child_option_information` 2, `runtime.composition_lookup_schema` 2, `runtime.CONTRACT_INFORMATION_OPERATIONS` 1, `runtime.DECISION_CONTEXT_VERSION` 2, `runtime.DECISION_EXCHANGE_PROTOCOL` 5, `runtime._digest` 1, `runtime.Draft202012Validator` 1, `runtime.instructional_model_context` 4, `runtime.is_contract_information` 1, `runtime._json` 14, `runtime.lookup_attempts` 1, `runtime.Mapping` 4, `runtime.model_snapshot` 2, `runtime._object` 3, `runtime._plain` 2, `runtime._recorded_action_generation_schema` 1, `runtime._recorded_assignment_transport` 1, `runtime._references_in` 1, `runtime.requested_contract_information` 2, `runtime.schema_failure_diagnostic` 2, `runtime.sqlite3` 1, `runtime.state_frame` 1, `runtime.ValidationError` 5, `runtime.WorkflowError` 14, `runtime.yield_table` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 2, `self.workflow.contract_information_profile` 1, `self.workflow.contract_information_reply` 1, `self.workflow.controller_binding` 1, `self.workflow.decision_exchanges` 4, `self.workflow.decision_protocol` 3, `self.workflow.episode_bindings` 1, `self.workflow.execute` 1, `self.workflow.execution_expectations` 1, `self.workflow.freeze_contract_information` 1, `self.workflow.freeze_literature_numerical_contracts` 1, `self.workflow.history_preview` 1, `self.workflow.is_job_source` 3, `self.workflow.job_episodes` 2, `self.workflow.journal` 3, `self.workflow.launch_instructions` 2, `self.workflow.native_estimation_context` 1, `self.workflow.numerical_contracts` 1, `self.workflow.pending_work` 1, `self.workflow.permits_common_action` 1, `self.workflow.provider` 3, `self.workflow.receipts` 4, `self.workflow.resource_context` 1, `self.workflow.resource_estimator` 5, `self.workflow.run_id` 1, `self.workflow.services` 2, `self.workflow.shared_information_context` 1, `self.workflow.specialist` 1, `self.workflow.store` 2, `self.workflow.structural_homology_evidence_binding` 1, `self.workflow.uses_received_record_context` 2, `self.workflow.validate_contract_information` 5, `self.workflow.waiting_support` 1, `table runtime_model_calls` 8 |
| `decision_presentation.py` | 59 | text prompt; renderer chosen by context kind (HPC, published scientific, API launch, selected execution, monitor, receiver) | `import root.a102.library.hpc_prompt` 1, `import root.a102.library.monitor_prompt` 1, `import root.a102.providers` 2, `import root.a102.receiver_prompt` 1, `import root.a102.structural_homology_evidence_prompt` 1, `providers.apply_state_frame` 3, `providers.DECISION_CONTEXT_VERSION` 1, `providers.is_api_launch_context` 2, `providers.is_published_scientific_context` 2, `providers._ordinary_runtime_receiver_context` 1, `providers.render_api_launch_prompt` 1, `providers.render_structural_homology_evidence_prompt` 1, `providers.text_instructions` 1 |
| `episode.py` | 107 | binding identity, construction checks (child roles incl. itself, library, tool library, tool retrieval, contract profile, yield_bindings with kind/cutoff/parameters{uncertainty_alpha}/credit_definition); constructs execution/HPC/resource child bindings | `import root.a102.composition_information` 1, `import root.a102.numerical` 1, `import root.a102.scientific_tool_retrieval` 1, `BoundedYieldController` 2, `CompletionYieldController` 2, `YieldController` 2, `YieldParameters` 2 |
| `from_child_execution_job_submission.py` | 26 | admit launch child's typed form; failed admission recorded and fed back for redeliver_report | `import root.a102.runtime` 1, `runtime._digest` 1, `runtime.Record` 2, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `self.workflow.delivery_feedback` 1, `self.workflow.journal` 1, `self.workflow.receive_form` 1, `self.workflow.run_id` 2, `self.workflow.save_attempt` 2, `self.workflow.store` 1, `store.db.execute` 1, `table runtime_actions` 1, `table runtime_report_attempts` 1 |
| `from_child_execution_progress_assessment.py` | 48 | admit monitor form; only episode_progress references grant received observations | `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.method_loop.durable` 1, `import root.a102.runtime` 1, `runtime._digest` 1, `runtime.Record` 2, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `self.workflow.delivery_feedback` 1, `self.workflow.journal` 1, `self.workflow.receive_form` 1, `self.workflow.run_id` 2, `self.workflow.save_attempt` 2, `self.workflow.store` 1, `store.db.execute` 1, `table runtime_actions` 1, `table runtime_report_attempts` 1 |
| `from_child_execution_result_acquisition.py` | 26 | admit execution results child's typed form (same text as other admissions) | `import root.a102.runtime` 1, `runtime._digest` 1, `runtime.Record` 2, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `self.workflow.delivery_feedback` 1, `self.workflow.journal` 1, `self.workflow.receive_form` 1, `self.workflow.run_id` 2, `self.workflow.save_attempt` 2, `self.workflow.store` 1, `store.db.execute` 1, `table runtime_actions` 1, `table runtime_report_attempts` 1 |
| `from_child_hpc_work_planning.py` | 26 | admit HPC planning child's typed form (same text) | `import root.a102.runtime` 1, `runtime._digest` 1, `runtime.Record` 2, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `self.workflow.delivery_feedback` 1, `self.workflow.journal` 1, `self.workflow.receive_form` 1, `self.workflow.run_id` 2, `self.workflow.save_attempt` 2, `self.workflow.store` 1, `store.db.execute` 1, `table runtime_actions` 1, `table runtime_report_attempts` 1 |
| `from_child_published_evidence_assessment.py` | 85 | own receiver for literature child: received references, progress forms, native timing receipts, tool attributions; selects itself only for the literature child | `binding_context` 4, `EpisodeBindingRegistry` 2, `EpisodeReturnRecords` 2, `import root.a102.delivery_counterpart` 2, `import root.a102.episode_bindings` 1, `import root.a102.episode_journal` 1, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime._digest` 1, `runtime._json` 1, `runtime.Record` 2, `runtime._references_in` 1, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `runtime.WorkflowError` 1, `self.workflow.binding_context` 4, `self.workflow.delivery_feedback` 1, `self.workflow.episode_bindings` 3, `self.workflow.is_job_source` 2, `self.workflow.job_episodes` 2, `self.workflow.journal` 1, `self.workflow.native_timing_information` 1, `self.workflow.progress_provider` 4, `self.workflow.receipts` 3, `self.workflow.receive_form` 1, `self.workflow.receive_tool_attributions` 1, `self.workflow.run_id` 8, `self.workflow.save_attempt` 2, `self.workflow.specialist` 1, `self.workflow.store` 8, `store.db.execute` 3, `table runtime_actions` 1, `table runtime_report_attempts` 3 |
| `from_child_resource_result_acquisition.py` | 26 | admit resource results child's typed form (same text) | `import root.a102.runtime` 1, `runtime._digest` 1, `runtime.Record` 2, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `self.workflow.delivery_feedback` 1, `self.workflow.journal` 1, `self.workflow.receive_form` 1, `self.workflow.run_id` 2, `self.workflow.save_attempt` 2, `self.workflow.store` 1, `store.db.execute` 1, `table runtime_actions` 1, `table runtime_report_attempts` 1 |
| `from_child_resource_work_submission.py` | 26 | admit resource launch child's typed form (same text) | `import root.a102.runtime` 1, `runtime._digest` 1, `runtime.Record` 2, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `self.workflow.delivery_feedback` 1, `self.workflow.journal` 1, `self.workflow.receive_form` 1, `self.workflow.run_id` 2, `self.workflow.save_attempt` 2, `self.workflow.store` 1, `store.db.execute` 1, `table runtime_actions` 1, `table runtime_report_attempts` 1 |
| `from_child_structural_homology_evidence.py` | 26 | admit recursive A102 child's typed form (same text) | `import root.a102.runtime` 1, `runtime._digest` 1, `runtime.Record` 2, `runtime.ReportBoundaryError` 1, `runtime.ReportDeliveryError` 2, `self.workflow.delivery_feedback` 1, `self.workflow.journal` 1, `self.workflow.receive_form` 1, `self.workflow.run_id` 2, `self.workflow.save_attempt` 2, `self.workflow.store` 1, `store.db.execute` 1, `table runtime_actions` 1, `table runtime_report_attempts` 1 |
| `from_parent.py` | 152 | assignment form; selection/library/tool checks; scope checks of evidence and proposed annotation; proposed annotation inherited and fixed; revision_origin authenticated; filled-process record; required child returns (results + committed_record_refs) | `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `self.workflow.journal` 1, `self.workflow.run_id` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.annotation_task_required` 3, `services.proposed_annotation_for` 1, `services.reference_in_scope` 2, `services.scientific_preparation` 2, `services.workflow` 1, `table runtime_actions` 1 |
| `goal.py` | 16 | instruction text in two variants (instruction entry / support-proposition entry) preceded by scientific_guidance | `import root.a102.structural_homology_evidence.scientific_guidance` 1 |
| `internal_summary.py` | 35 | binding block shown to the model: selection, axis view, support routes, thought pattern fields, tools, assignment, permitted children; received structural evidence | `import root.a102.structural_homology_evidence.received_structural_context` 1, `services.scientific_support_routes` 1, `services.workflow` 1 |
| `operations.py` | 97 | tool catalog: selected direct tools + process.revise + execution planning; operand authentication; process.revise prepares a child selection with revision_origin | `import root.a102.execution_planning` 2, `services.authenticate_source_byte_operands` 1, `services.authenticate_structure_alignment_operands` 2, `services.execute_tool` 1, `services.tool_catalog` 2, `services.tool_information_catalog` 1, `services.workflow` 1 |
| `received_evidence.py` | 32 | protein-structure action facts the annotation parent may receive; validates received structural reports; resolves protein references | `import root.a102.protein_structure_action_records` 1, `import root.a102.structural_homology_evidence.report_validation` 1, `services.protein_structure_action_received_facts` 1, `services.protein_structure_reference_access` 1 |
| `received_structural_context.py` | 17 | received_structural_evidence for the merged A102 entry | `import root.a102.domain` 1, `import root.a102.literature_structure_storage` 1, `self.workflow.run_id` 1, `self.workflow.store` 2 |
| `report_delivery.py` | 25 | final form = report values + facts, saved once; result without contract = credit + pending handles | `binding_context` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.library.report_fact_assembly` 1, `import root.a102.runtime` 2, `runtime.form_with_facts` 1, `runtime._json` 2, `runtime.Record` 2, `self.workflow.binding_context` 1, `self.workflow.episode_bindings` 1, `self.workflow.facts` 1, `self.workflow.journal` 2, `self.workflow.pending_handles` 1, `self.workflow.release` 2, `self.workflow.source_credit_view` 1, `table runtime_forms` 2 |
| `report_integrity.py` | 16 | report protein-action fields must equal frozen facts | `services.protein_structure_action_frozen_facts` 1 |
| `report_snapshot.py` | 9 | completion snapshot: initial credit, credit, controller credit, episode yield, parent invocation | `services.scientific_parent_invocation` 1, `table runtime_episodes` 1 |
| `report_validation.py` | 49 | structural report statuses must match delivered evidence; investigation report resolution | `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.literature_structure_storage` 1, `import root.a102.structural_homology_evidence_records` 1, `self.workflow.run_id` 1, `self.workflow.store` 3, `services.record_selection` 1, `services.workflow` 2 |
| `saved_scientific_state.py` | 56 | closed-request restoration; filled-request identity checks; a closed request permits replay never new dispatch | `services.scientific_closed_request` 1, `services.scientific_parent_preparation` 1, `services.scientific_saved_request` 1 |
| `scientific_commission_catalog.py` | 122 | commission-routed tool contracts declared by the launch/results children, validated against their homes | `import root.a102.resource_tool_information` 1, `registry._child_binding` 2, `registry.for_binding_path` 1, `registry.roles` 1 |
| `scientific_contracts.py` | 59 | constants: version, axis A102, role, common tools, assignment/selection/revision schemas, evidence_task form | `import root.a102.alignment_site_returns` 1, `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.episode_bindings` 1, `import root.a102.evidence_axis_contracts` 1, `import root.a102.evidence_axis_instructions` 1, `import root.a102.protein_structure_action_records` 1, `import root.a102.scientific_support_metadata` 1, `import root.a102.structural_homology_evidence_library` 1, `import root.a102.structural_homology_evidence_records` 1, `import root.a102.structural_homology_evidence_reports` 1 |
| `scientific_guidance.py` | 18 | A102 guidance prefix (structural only, or merged comparative+experimental) | none |
| `source_references.py` | 20 | resolve scientific namespaces; initial references = evidence refs + proposed annotation | `services.scientific_reference` 1 |
| `task.py` | 271 | decision source: next/apply_response/execute; model inputs; empty reasoning commit refused; report update admitted separately; credit measured after each observed outcome | `binding_context` 4, `_execution_context._ready_owned_child` 1, `import root.a102.episode_source_failure` 1, `import root.a102.library.action_contracts` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.providers` 1, `import root.a102.read_mapping` 1, `import root.a102.runtime` 2, `runtime.AcquisitionError` 2, `runtime.ActionFailure` 1, `runtime.ContractError` 1, `runtime.ContractInformationError` 1, `runtime._decode_recorded_action_response` 1, `runtime.Draft202012Validator` 3, `runtime.EventTargetError` 2, `runtime.FACT_MEANINGS` 1, `runtime.FACT_SOURCES` 1, `runtime.inspect` 1, `runtime._json` 5, `runtime.Mapping` 6, `runtime.nullcontext` 5, `runtime.observes_action_outcome` 1, `runtime._plain` 2, `runtime._references_in` 1, `runtime.ReportBoundaryError` 1, `runtime.ReportRedelivery` 2, `runtime.schema_failure_diagnostic` 1, `runtime.SourceEnd` 2, `runtime.sqlite3` 2, `runtime.subprocess` 2, `runtime.validate_form` 1, `runtime.ValidationError` 3, `runtime._wait_target_feedback` 2, `runtime.WorkflowError` 2, `self.workflow.action_schema` 1, `self.workflow.annotation_context` 1, `self.workflow.automatic_score_updates` 1, `self.workflow.binding_context` 4, `self.workflow.catalog` 1, `self.workflow.completed_unit` 3, `self.workflow.completions` 3, `self.workflow.controller_binding` 1, `self.workflow.controller_value` 2, `self.workflow.decision_exchanges` 3, `self.workflow.delivery_resolution_inputs` 1, `self.workflow.delivery_status` 1, `self.workflow.execute` 1, `self.workflow.execution_binding` 7, `self.workflow.extra_report_sources` 1, `self.workflow.inprocess_replay` 4, `self.workflow.is_scientific_source` 1, `self.workflow.job_episode_options` 1, `self.workflow.journal` 10, `self.workflow.knowledge` 1, `self.workflow.last_observed_credit` 1, `self.workflow.local_outcome_preview` 1, `self.workflow.next_return` 1, `self.workflow.pending_work` 2, `self.workflow.perform_selected_wait` 1, `self.workflow.permits_common_action` 1, `self.workflow.reasoning_action_schema` 1, `self.workflow.receipt_projection` 1, `self.workflow.receive_native_outcome` 1, `self.workflow.receive_outcome` 1, `self.workflow.resolve_pending_deliveries` 1, `self.workflow.resolver` 1, `self.workflow.retain_shared_grading_results` 1, `self.workflow.run_id` 4, `self.workflow.selected` 3, `self.workflow.source_credit_binding` 1, `self.workflow.source_credit_view` 2, `self.workflow.specialist` 3, `self.workflow.store` 12, `self.workflow.structural_homology_evidence_binding` 1, `self.workflow.tools` 1, `self.workflow.validate_report` 1, `self.workflow.working_state` 1, `table runtime_actions` 10, `table runtime_episodes` 1, `table runtime_model_calls` 2 |
| `task_instructions.py` | 26 | instruction composition (default/replacement, reasoning, knowledge, launch library, redelivery, wait, native events, request_context) | `binding_context` 1, `import root.a102.runtime_prompt` 2, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL` 1, `runtime_prompt.INSTRUCTIONS` 4, `runtime_prompt.REASONING_COMMIT_REQUIREMENT` 1, `self.workflow.binding_context` 1, `self.workflow.decision_protocol` 1, `self.workflow.is_job_source` 1, `self.workflow.job_episodes` 1, `self.workflow.knowledge` 1, `self.workflow.launch_instructions` 1, `self.workflow.native_event_information` 1, `self.workflow.permits_common_action` 3, `self.workflow.specialist` 1 |
| `task_projector.py` | 28 | credit projector per A102 task (structural, or merged named tasks) | `import root.a102.communication` 1, `import root.a102.domain` 1 |
| `task_state.py` | 108 | source state; failure recorded as a failed unit with its credit; restore/checkpoint | `import root.a102.episode_source_failure` 1, `import root.a102.runtime` 2, `runtime.ActionLeaf` 1, `runtime.EFFECT_VERSION` 1, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime._object` 1, `runtime._plain` 1, `runtime.Record` 1, `self.workflow.archive` 1, `self.workflow.completions` 4, `self.workflow.context` 1, `self.workflow.controller_value` 1, `self.workflow.execution_binding` 4, `self.workflow.grains` 1, `self.workflow.inprocess_replay` 7, `self.workflow.journal` 5, `self.workflow.progress_provider` 2, `self.workflow.recover_commissions` 1, `self.workflow.run_id` 1, `self.workflow.source_credit_view` 1, `self.workflow.store` 2, `table runtime_actions` 5 |
| `task_waiting.py` | 9 | suspension condition forwarded to execution backend | `self.workflow.execution_backend` 1, `self.workflow.execution_handle` 2 |
| `to_child_execution_job_submission.py` | 48 | prepare child request: model-chosen goal, purpose, typed form, initial report; required returns present once; role allowed (same text in six files) | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime.ContractError` 2, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime.validate_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 1, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 1, `self.workflow.journal` 2, `self.workflow.launch_instructions` 1, `self.workflow.run_id` 3, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_child_execution_progress_assessment.py` | 65 | monitor assignment validated against monitor form; monitoring_progress_refs required when annotation task required; plus the common preparation | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime.ContractError` 2, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime.validate_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 1, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 1, `self.workflow.journal` 2, `self.workflow.launch_instructions` 1, `self.workflow.run_id` 3, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_child_execution_result_acquisition.py` | 48 | common child request preparation (same text) | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime.ContractError` 2, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime.validate_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 1, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 1, `self.workflow.journal` 2, `self.workflow.launch_instructions` 1, `self.workflow.run_id` 3, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_child_hpc_work_planning.py` | 48 | common child request preparation (same text) | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime.ContractError` 2, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime.validate_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 1, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 1, `self.workflow.journal` 2, `self.workflow.launch_instructions` 1, `self.workflow.run_id` 3, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_child_published_evidence_assessment.py` | 76 | own request envelope for literature child (goal, scope, initial report, declaration, assignment, invocation ref, knowledge inheritance) + common preparation | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `import root.a102.structural_homology_evidence_records` 1, `runtime.ContractError` 2, `runtime.ContractInformationError` 1, `runtime.Episode` 3, `runtime.EpisodeGoal` 2, `runtime.EpisodeRequest` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime._plain` 3, `runtime.Record` 1, `runtime.validate_form` 1, `runtime.validate_saved_fact_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 3, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 3, `self.workflow.inprocess_completion_order` 2, `self.workflow.journal` 2, `self.workflow.launch_instructions` 2, `self.workflow.receipts` 2, `self.workflow.run_id` 4, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 2, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_child_resource_result_acquisition.py` | 48 | common child request preparation (same text) | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime.ContractError` 2, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime.validate_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 1, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 1, `self.workflow.journal` 2, `self.workflow.launch_instructions` 1, `self.workflow.run_id` 3, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_child_resource_work_submission.py` | 48 | common child request preparation (same text) | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime.ContractError` 2, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime.validate_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 1, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 1, `self.workflow.journal` 2, `self.workflow.launch_instructions` 1, `self.workflow.run_id` 3, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_child_structural_homology_evidence.py` | 48 | common preparation; for itself prepares a filled invocation (closed commission reuse) | `binding_context` 5, `EpisodeReturnRecords` 2, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 1, `runtime.ContractError` 2, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime.parse_json_object` 1, `runtime.validate_form` 1, `self.workflow.annotation_child_roles` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 5, `self.workflow.child_initial_report_input` 1, `self.workflow.context` 1, `self.workflow.episode_bindings` 3, `self.workflow.expanded_contract_form` 1, `self.workflow.grains` 1, `self.workflow.journal` 2, `self.workflow.launch_instructions` 1, `self.workflow.run_id` 3, `self.workflow.services` 2, `self.workflow.specialist` 1, `self.workflow.store` 1, `self.workflow.structural_homology_evidence_binding` 1, `services.capabilities` 1, `services.scientific_closed_request` 1, `table runtime_actions` 1, `table runtime_episodes` 1 |
| `to_parent.py` | 66 | fact sources and facts (process results, site projections paged by 64, protein action facts); report validation against frozen results | `import root.a102.structural_homology_evidence_reports` 1, `import root.a102.structural_homology_evidence.report_validation` 1, `services.alignment_site_frozen_facts` 1, `services.alignment_site_own_action_results` 1, `services.protein_structure_action_own_facts` 1, `services.protein_structure_action_received_facts` 1, `services.scientific_frozen_results` 1, `services.scientific_received_results` 1 |
| `yield_estimator.py` | 54 | continuation task A102:<task>; declaration must match credit definition and yield method; accumulation/bounded_quality/completion | `import root.a102.numerical` 3, `BoundedYieldController` 2, `CompletionYieldController` 2, `YieldController` 2, `YieldParameters` 6 |
