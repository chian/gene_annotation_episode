# a102/structural_homology_evidence/execution_job_submission — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/execution_job_submission/`
(45 files directly in the folder; no `grading/` or `scoring/` subfolder). Its three child folders were not read
(`api_job_execution` and `hpc_job_execution` have their own pages; `local_job_execution` belongs to another
reader). Nothing from the old shared root was read.

Old binding: class `ExecutionEpisode`, `binding_path = 'structural_homology_evidence/execution_job_submission'`,
`commissioning_parent = 'structural_homology_evidence'`, old role `launch`, `replaces_default_instructions = True`,
version `execution_episode_v1`. Decision source: `LaunchTask`.

## What this episode is for

It decides which of the parent's permitted execution requests to hand to which resource, and receives the
handoff. It does not run anything itself. In its own words (`goal.py`, the whole text):

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities,
> recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs,
> constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive its
> requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes this
> launch endpoint with exact zero future credit.

## Task and instructions

- One unit is one model-selected action. Permitted actions (`action_policy.py`):
  - `tool` only, when the context is a native protein-structure results context;
  - `tool`, `child`, `redeliver_report` when any ancestor is the old `hpc` role (no reasoning, no waiting);
  - otherwise `tool`, `reason`, `child`, `wait`, `redeliver_report`.
- Instructions (`instructions.py`): the goal text above replaces the default instructions; then the reasoning
  commit requirement (when reasoning is permitted), tool knowledge, the launch instruction library, the
  `redeliver_report` paragraph for an undelivered child report, the wait paragraphs, the native event targets
  paragraph, and the `request_context` history guidance.

## What it reads from its parent's assignment

Assignment form (`from_parent.py`, version `execution_launch_assignment_v1`):

| Field | Meaning |
|---|---|
| `requests` | at least one concrete request keyed by configured `resource_id`. An API resource uses the API service's own request form; a local or HPC resource uses the practical assignment form with `resource_id`, `resource_kind` and a `requested_job` (generic, or a native protein-structure tool request, or the resource's declared job forms) (`parent_input_custody.py`) |
| `immutable_input_versions` | list of input versions that must still hold |
| `constraints` | may carry `allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind`; they decide which requests are permitted |
| `launch_instructions` | selection from the launch instruction library |

Checks: every request names a bound resource of the right kind with its workspace confined to the configured
workspace; protein-structure job inputs of every request are validated; the input versions are validated. When
the commissioning parent is HPC planning (old roles `hpc`, `hpc_execution`) the launch is authenticated against
that parent (`hpc_work_planning.to_child_execution_job_submission.authenticate_launch`). When the parent is the
head and an annotation task is required, the parent's return form must carry `execution_handoff_refs`.

Initial references: the protein-structure inputs of the requests.

## Children

`to_children.py`: three children, old roles `launch_api`, `launch_local`, `launch_hpc`
(`api_job_execution`, `local_job_execution`, `hpc_job_execution`). A child is allowed only when a configured
resource of its kind is permitted by the assignment's constraints.

| Child | Sent | Taken back |
|---|---|---|
| `api_job_execution` | one of this launch's own requests for an API resource (the child checks it against this parent's recorded assignment), in the same envelope as the others: child goal, scope, initial report, report contract declaration, assignment, knowledge inheritance (`to_child_api_job_execution.py`) | the child's typed form; references in it become received records; progress forms, native timing receipts and tool attributions are received with it (`from_child_api_job_execution.py`) |
| `local_job_execution` | the same, for a local resource | the same |
| `hpc_job_execution` | the same, for an HPC resource | the same |

The three `to_child_*.py` files carry the same text, and so do the three `from_child_*.py` files. What this
episode wants back is a usable handoff: a returned record whose target is one of its own requests
(`received_record_selection.py`, `result_selection._context_target`).

## Decision state and what it shows the model

State kept by the source (`task_state.py`): calls, last outcome, feedback, report values and their basis.

Model inputs (`decision_state.py`): the same fields as the head's (goal, scope, working state, visible records,
current credit, credit binding, time accounting, pending work, last outcome, feedback, deliveries, controller
state, tools, tool knowledge, job options, available report facts, requested form, current report update).

The binding's own block (`internal_summary.py`):

- `execution_assignment`: the assignment;
- `execution_progress`: its current facts (handoffs, results, completed);
- `selected_execution_task`, only when every request is a local native protein-structure job: the parent's
  scientific question and selected tool info, each request (resource, endpoint, constraints, job, resource
  information), the constraints and the result description.

Initial context (`resource_information.py`): `execution_resource_capabilities` (per resource: id, kind,
availability `unknown` from caller configuration, tool names, workspace, policy, account, service, inventory
snapshot, API configuration facts) and `execution_initial_information` (the recorded inventory).

Added before each decision (`decision_inputs.py`): the same additions as the head, with execution expectations
captured for `launch`.

Presentation (`decision_provider.py`, `episode.py`): `render_selected_execution_prompt` is used only for a
selected-execution context that is not HPC, published scientific or API launch.

## Tools it offers

Its own catalog is one tool (`execution_contracts.launch_operation_catalog`):

- `execution.capabilities` — "Read the actual caller-bound resource configuration and already recorded inventory;
  no discovery or selection." Executing it returns the initial resource information.

`resource_information.resource_tool_contracts` declares, for the head, the operations reachable by commission
through this episode: per resource the launch operations (the API service's, or `exec_command` for local/HPC) and
the results operations (`execution.results.status`, `execution.results.collect`, `execution.results.read`), each
with its route `{entry_role, resource_id, resource_role}`, plus native protein-structure tools.

## How its credit is counted

Credit kind `operational` (`credit.py`):

`credit = handoff_unit × (number of distinct resources with a usable handoff that was not already among the
episode's initial records)`

The `acquired_record_unit` term is multiplied by zero in this episode. `handoff_unit` and `acquired_record_unit`
are construction settings and must be positive finite numbers; nothing bounds or rescales the result. The view
also reports `new_handoff_count` and the credit binding (`execution_received_records_credit_v1`). When the
episode has closed, the view captured at close is returned instead (`closed_credit.py`: "later delivery never
reprices it").

Completion (`completion.py`): an action completes the launch when it completed and one of its returned records is
a usable handoff for one of this launch's requests (endpoint `usable_handoff`, validation key
`received_usable_handoff`).

## Continuation

`yield_estimator.py`, old `BoundedYieldController` (today's bounded-quality estimator):

- each request gets a yield class from its form: `api_{service}[_{algorithm}][_{database}]_handoff`, or
  `practical_{resource_kind}[_{native_*}]_{handoff|outputs}`;
- the profile `launch:{classes of the eligible requests, sorted, joined by +}` must exist in
  `task_yield_profiles`; it gives `cutoff` (above zero) and `parameters`;
- maximum = (eligible requests whose resource did not already have a usable handoff among the initial records) ×
  `handoff_unit`;
- when nothing remains: an old `YieldController` with cutoff 0 and a custom estimate that is exactly zero
  (`launch_original_request_exhaustion_v1`) and raises if any credit is observed; a non-zero initial credit
  raises.

`private_yield_binding` must be enabled or the controller raises. `practical_estimator` (exact zero future gain
once completion is verified) is also offered to the old runner.

## What it reports to its parent

`to_parent.py`:

- `execution_handoff_refs`: "Authenticated original execution handoffs available to this episode."
- `execution_result_refs`: "Actual requested A102 result acquisitions available to this episode."
- `execution_completed`: whether any received handoff is complete;
- `execution_result_origin`: acquisition semantics of a retained result, or null;
- `execution_file_source_refs`, `execution_file_capture_outcomes`, and the protein-structure fact sources (empty
  lists unless they apply).

Any report field bound to a fact must equal the recorded fact
(`execution_report_disagrees_with_recorded_facts`). `received_records.py` also says what the annotation root or
the head may receive from it: file sources, capture outcomes, protein-structure facts.

## How it differs from similar episodes

- Against its children `api_job_execution` and `hpc_job_execution`: it is the only one with children, a
  reasoning action and waiting (outside an HPC ancestor); it runs nothing; its credit counts handoffs received
  from children, theirs comes from the resource's own execution state; its continuation is bounded quality with a
  maximum from the remaining requests, theirs is accumulation with a completion estimate; it alone can require
  `execution_handoff_refs` in the parent's form.
- Much of its text is shared with those two children file for file (see their pages): `configuration.py`,
  `closed_credit.py`, `resource_information.py`, `result_selection.py`, `retained_*.py`, `received_*.py`,
  `report_*.py`, `task_state.py`, `decision_state.py`, `decision_contracts.py`, `decision_exchange.py` differ from the `api_job_execution` copies only in class
  prefix. Several of these serve the old `results` role (`_target`, `_selector`, `_read_result`, result
  publication), which is the sibling `execution_result_acquisition`, not this launch role.
- Against the head: operational credit instead of scientific; no `process.revise`; the decision call is split
  over six files instead of one.
- `terminal_execution.py` (242 lines) is the local/HPC command behaviour; this episode constructs one per
  local/HPC resource only to validate requests and list capabilities.

## Points the carry-over has to settle (seen in these files)

- The no-remaining-requests case uses a custom estimate function on the accumulation controller, and
  `practical_estimator` is a further estimator-shaped object; only the three yield estimators exist now.
- The closed-credit capture, completion-history verdict and record selection read old journal and receipt tables
  directly (`runtime_actions`, `runtime_episodes`, `runtime_forms`, `runtime_observations`,
  `runtime_receipt_inheritance`, `runtime_record_receipts`).
- `from_parent.py` imports `authenticate_launch` from another episode's folder (`hpc_work_planning`).
- `redeliver_report` and `wait` are actions of the old runner.

## Old-runner names (totals for this episode)

| Group | Distinct names | Uses |
|---|---|---|
| `self.workflow.<member>` | 78 | 323 |
| BindingContext (`binding_context`), receipts, return records, `UnitRef`, raw `store.db.execute`, `_ready_owned_child` | 6 | 52 |
| imports from old `root.a102` shared modules (incl. `runtime`, `providers`, `communication`, `decision_context`, `episode_bindings`, `episode_journal`, `composition_information`) | 46 | 129 |
| old `services.<member>` (services held the Workflow) | 3 | 3 |
| old journal and receipt tables | 9 | 55 |
| old yield names | 7 | 25 |
| symbols through `runtime`, `runtime_prompt`, `providers` | 58 | 192 |

Counted mechanically from the files at `97308b94c`; every row (name, file, uses, purpose) is in `runs/carry_over/calls/a102_01.tsv`. In `from_child_*.py` and `to_child_*.py` the first parameter `self` is the old Workflow, so `self.x` there is counted as `self.workflow.x`; `workflow.x` and `source.workflow.x` are counted the same way. Attribute reads on the old context object (`context.role`, `.path`, `.assignment`, `.scope`, `.request`) are not counted separately.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty | none |
| `action_policy.py` | 13 | tool only for native protein results; tool/child/redeliver under an HPC ancestor; else tool/reason/child/wait/redeliver | none |
| `api_operations.py` | 25 | own catalog execution.capabilities (or native protein result catalog); executing returns initial resource information | `import root.a102.native_file_capture` 1, `import root.a102.native_protein_structure_results` 1 |
| `binding_record.py` | 8 | binding identity record with resources, units, log window/roles, yield profiles | none |
| `closed_credit.py` | 116 | captures credit view at close; closed view returned unchanged afterwards | `EpisodeReceipts` 2, `EpisodeReturnRecords` 2, `import root.a102.episode_receipts` 1, `import root.a102.episode_return_records` 3, `store.db.execute` 5, `table runtime_episodes` 2, `table runtime_forms` 3, `table runtime_observations` 1, `table runtime_receipt_inheritance` 2, `table runtime_record_receipts` 2, `table sqlite_master` 2 |
| `completion.py` | 79 | completion proof: completed action returning a usable handoff for one of its requests; verification via recorded history | `import root.a102.episode_return_records` 1, `import root.a102.method_loop.identities` 1, `import root.a102.numerical` 1, `import root.a102.practical_yield` 1, `store.db.execute` 2, `table runtime_actions` 1, `table runtime_observations` 1, `UnitRef` 2, `ESTIMATOR_VERSION` 2, `NumericBand` 2 |
| `configuration.py` | 61 | construction settings: resources, inventory, handoff_unit, acquired_record_unit (positive), log window/roles, private yield flag, results/task yield profiles; builds per-resource executors | `import root.a102.api_service_execution` 1, `import root.a102.execution_progress` 1, `import root.a102.native_protein_structure_results` 1, `import root.a102.native_protein_structure_returns` 1, `import root.a102.numerical` 1, `YieldController` 3, `YieldParameters` 3 |
| `credit.py` | 31 | operational credit = handoff_unit x new resources with usable handoff | none |
| `decision_contracts.py` | 128 | request_context exchange envelope and replay checks | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 2, `runtime.apply_state_frame` 1, `runtime.composition_lookup_schema` 2, `runtime.CONTRACT_INFORMATION_OPERATIONS` 1, `runtime.DECISION_CONTEXT_VERSION` 1, `runtime.Draft202012Validator` 1, `runtime.instructional_model_context` 1, `runtime.is_contract_information` 1, `runtime._json` 8, `runtime.Mapping` 2, `runtime.model_snapshot` 1, `runtime._object` 3, `runtime._recorded_action_generation_schema` 1, `runtime._references_in` 1, `runtime.requested_contract_information` 1, `runtime.ValidationError` 1, `runtime.WorkflowError` 9, `self.workflow.contract_information_reply` 1, `self.workflow.decision_exchanges` 2, `self.workflow.journal` 1, `self.workflow.store` 2, `self.workflow.validate_contract_information` 2, `table runtime_model_calls` 1 |
| `decision_exchange.py` | 108 | request_context exchange loop | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 2, `runtime._action_generation_schema` 1, `runtime._category_yield_parameters` 1, `runtime.child_option_information` 1, `runtime.DECISION_CONTEXT_VERSION` 1, `runtime.instructional_model_context` 2, `runtime._json` 2, `runtime.lookup_attempts` 1, `runtime.Mapping` 1, `runtime.model_snapshot` 1, `runtime._plain` 2, `runtime.requested_contract_information` 1, `runtime.schema_failure_diagnostic` 2, `runtime.sqlite3` 1, `runtime.state_frame` 1, `runtime.ValidationError` 4, `runtime.yield_table` 1, `self.workflow.controller_binding` 1, `self.workflow.decision_exchanges` 1, `self.workflow.execute` 1, `self.workflow.journal` 1, `self.workflow.run_id` 1, `self.workflow.services` 1, `self.workflow.validate_contract_information` 1, `table runtime_model_calls` 2 |
| `decision_inputs.py` | 58 | context additions before a decision (expectations captured for launch) | `binding_context` 1, `import root.a102.episode_work_report` 2, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `runtime.child_option_information` 1, `runtime.Mapping` 1, `self.workflow.available_child_roles` 1, `self.workflow.binding_context` 1, `self.workflow.episode_bindings` 1, `self.workflow.execution_expectations` 1, `self.workflow.is_job_source` 1, `self.workflow.job_episodes` 2, `self.workflow.launch_instructions` 2, `self.workflow.native_estimation_context` 1, `self.workflow.pending_work` 1, `self.workflow.permits_common_action` 1, `self.workflow.resource_context` 1, `self.workflow.resource_estimator` 5, `self.workflow.shared_information_context` 1, `self.workflow.waiting_support` 1 |
| `decision_provider.py` | 20 | selected-execution prompt renderer when applicable | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 1, `import root.a102.structural_homology_evidence_prompt` 2, `self.workflow.provider` 1, `self.workflow.specialist` 1 |
| `decision_state.py` | 45 | model inputs assembled from state and controller | `binding_context` 1, `import root.a102.runtime` 2, `runtime.FACT_MEANINGS` 1, `runtime.FACT_SOURCES` 1, `runtime.Mapping` 3, `runtime._plain` 2, `runtime._references_in` 1, `self.workflow.binding_context` 1, `self.workflow.catalog` 1, `self.workflow.controller_binding` 1, `self.workflow.delivery_status` 1, `self.workflow.extra_report_sources` 1, `self.workflow.is_scientific_source` 1, `self.workflow.job_episode_options` 1, `self.workflow.journal` 3, `self.workflow.knowledge` 1, `self.workflow.local_outcome_preview` 1, `self.workflow.pending_work` 1, `self.workflow.receipt_projection` 1, `self.workflow.run_id` 1, `self.workflow.source_credit_binding` 1, `self.workflow.source_credit_view` 1, `self.workflow.specialist` 1, `self.workflow.store` 3, `self.workflow.tools` 1, `self.workflow.working_state` 1, `table runtime_actions` 2 |
| `episode.py` | 38 | binding identity: path, parent, role launch, replaces default instructions, renderer | `import root.a102.structural_homology_evidence_prompt` 1 |
| `execution_contracts.py` | 47 | constants and launch/result operation catalogs | `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.execution_contracts` 1, `import root.a102.launch_instructions` 1, `import root.a102.local_file_capture_results` 1, `import root.a102.native_protein_structure_acquisition` 1, `import root.a102.practical_execution_operations` 1, `import root.a102.practical_execution_records` 1, `import root.a102.practical_execution_state` 1, `import root.a102.practical_receipt_information` 1, `import root.a102.resource_records` 1 |
| `execution_state.py` | 41 | initialize: validates launch, protein inputs, input versions; results directory manifest | `import root.a102.protein_structure_operands` 1 |
| `from_child_api_job_execution.py` | 45 | receive API child's form: references, progress, timing receipts, attributions | `binding_context` 4, `EpisodeReturnRecords` 2, `import root.a102.delivery_counterpart` 1, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 2, `runtime._json` 1, `runtime._references_in` 1, `runtime.WorkflowError` 1, `self.workflow.binding_context` 4, `self.workflow.episode_bindings` 1, `self.workflow.is_job_source` 2, `self.workflow.job_episodes` 2, `self.workflow.native_timing_information` 1, `self.workflow.progress_provider` 4, `self.workflow.receipts` 3, `self.workflow.receive_tool_attributions` 1, `self.workflow.run_id` 6, `self.workflow.specialist` 1, `self.workflow.store` 7, `store.db.execute` 2, `table runtime_report_attempts` 2 |
| `from_child_hpc_job_execution.py` | 45 | receive HPC child's form (same text) | `binding_context` 4, `EpisodeReturnRecords` 2, `import root.a102.delivery_counterpart` 1, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 2, `runtime._json` 1, `runtime._references_in` 1, `runtime.WorkflowError` 1, `self.workflow.binding_context` 4, `self.workflow.episode_bindings` 1, `self.workflow.is_job_source` 2, `self.workflow.job_episodes` 2, `self.workflow.native_timing_information` 1, `self.workflow.progress_provider` 4, `self.workflow.receipts` 3, `self.workflow.receive_tool_attributions` 1, `self.workflow.run_id` 6, `self.workflow.specialist` 1, `self.workflow.store` 7, `store.db.execute` 2, `table runtime_report_attempts` 2 |
| `from_child_local_job_execution.py` | 45 | receive local child's form (same text) | `binding_context` 4, `EpisodeReturnRecords` 2, `import root.a102.delivery_counterpart` 1, `import root.a102.episode_return_records` 1, `import root.a102.runtime` 2, `runtime._json` 1, `runtime._references_in` 1, `runtime.WorkflowError` 1, `self.workflow.binding_context` 4, `self.workflow.episode_bindings` 1, `self.workflow.is_job_source` 2, `self.workflow.job_episodes` 2, `self.workflow.native_timing_information` 1, `self.workflow.progress_provider` 4, `self.workflow.receipts` 3, `self.workflow.receive_tool_attributions` 1, `self.workflow.run_id` 6, `self.workflow.specialist` 1, `self.workflow.store` 7, `store.db.execute` 2, `table runtime_report_attempts` 2 |
| `from_parent.py` | 50 | launch assignment form; HPC-parent authentication; protein input and version checks; requires execution_handoff_refs from head under annotation task | `import root.a102.protein_structure_operands` 3, `services.annotation_task_required` 1 |
| `goal.py` | 8 | goal text: choose which permitted request to commission on which resource | none |
| `instructions.py` | 23 | instruction composition (goal replaces default) | `binding_context` 1, `import root.a102.runtime_prompt` 2, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL` 1, `runtime_prompt.INSTRUCTIONS` 3, `runtime_prompt.REASONING_COMMIT_REQUIREMENT` 1, `self.workflow.binding_context` 1, `self.workflow.decision_protocol` 1, `self.workflow.knowledge` 1, `self.workflow.launch_instructions` 1, `self.workflow.native_event_information` 1, `self.workflow.permits_common_action` 3, `self.workflow.specialist` 1 |
| `internal_summary.py` | 27 | execution_assignment, execution_progress, selected_execution_task for local protein jobs | `services.scientific_parent_task` 1 |
| `parent_input_custody.py` | 67 | request schemas per resource; request validation; constraints decide permitted requests | `import root.a102.execution_input_versions` 1, `import root.a102.native_protein_structure_tool_info` 1 |
| `received_record_selection.py` | 35 | selects received handoffs/results that belong to its own requests | none |
| `received_records.py` | 37 | facts the annotation/head parent may receive from it | `import root.a102.protein_structure_result_views` 1 |
| `received_reference_custody.py` | 35 | received reference resolution and admission of handoff/result references | none |
| `report_delivery.py` | 25 | final form = report values + facts | `binding_context` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.library.report_fact_assembly` 1, `import root.a102.runtime` 2, `runtime.form_with_facts` 1, `runtime._json` 2, `runtime.Record` 2, `self.workflow.binding_context` 1, `self.workflow.episode_bindings` 1, `self.workflow.facts` 1, `self.workflow.journal` 2, `self.workflow.pending_handles` 1, `self.workflow.release` 2, `self.workflow.source_credit_view` 1, `table runtime_forms` 2 |
| `report_reference_access.py` | 45 | reference resolution for its report | `import root.a102.episode_bindings` 2 |
| `resource_information.py` | 82 | initial context (resource capabilities, inventory); resource_tool_contracts for the head | `import root.a102.native_protein_structure_tool_info` 1 |
| `result_selection.py` | 75 | results target/selector/windows; receiver selection; handoff-to-request match | `EpisodeReceipts` 2, `import root.a102.episode_receipts` 1, `import root.a102.protein_structure_selection` 1, `services.record_selection` 1, `store.db.execute` 3, `table runtime_actions` 1, `table runtime_receipt_inheritance` 2, `table sqlite_master` 1 |
| `retained_protein_reader.py` | 94 | retained protein structure reader; protected protein references | `import root.a102.execution_contracts` 1, `import root.a102.native_protein_structure_results` 1, `import root.a102.native_protein_structure_returns` 1, `import root.a102.protein_structure_contracts` 1, `import root.a102.protein_structure_operands` 1, `import root.a102.protein_structure_selection` 1, `import root.a102.state` 1, `store.db.execute` 1, `table runtime_episodes` 1 |
| `retained_result_acquisition.py` | 19 | selected result action lookup | `store.db.execute` 1, `table runtime_actions` 1 |
| `retained_result_publication.py` | 53 | result receipt validation and reading | `store.db.execute` 1, `table runtime_episodes` 1 |
| `task.py` | 233 | decision source (same as head except no execution-context check, grain launch) | `binding_context` 2, `_execution_context._ready_owned_child` 1, `import root.a102.episode_source_failure` 1, `import root.a102.library.action_contracts` 1, `import root.a102.library.private_policy_call` 1, `import root.a102.providers` 1, `import root.a102.read_mapping` 1, `import root.a102.runtime` 2, `runtime.AcquisitionError` 2, `runtime.ActionFailure` 1, `runtime.ContractError` 1, `runtime.ContractInformationError` 1, `runtime._decode_recorded_action_response` 1, `runtime.Draft202012Validator` 3, `runtime.EventTargetError` 2, `runtime.inspect` 1, `runtime._json` 5, `runtime.Mapping` 3, `runtime.nullcontext` 5, `runtime.observes_action_outcome` 1, `runtime.ReportBoundaryError` 1, `runtime.ReportRedelivery` 2, `runtime.schema_failure_diagnostic` 1, `runtime.SourceEnd` 2, `runtime.sqlite3` 2, `runtime.subprocess` 2, `runtime.validate_form` 1, `runtime.ValidationError` 3, `runtime._wait_target_feedback` 2, `runtime.WorkflowError` 2, `self.workflow.action_schema` 1, `self.workflow.automatic_score_updates` 1, `self.workflow.binding_context` 2, `self.workflow.completed_unit` 3, `self.workflow.completions` 3, `self.workflow.controller_value` 2, `self.workflow.decision_exchanges` 3, `self.workflow.delivery_resolution_inputs` 1, `self.workflow.execute` 1, `self.workflow.execution_binding` 7, `self.workflow.inprocess_replay` 4, `self.workflow.journal` 7, `self.workflow.last_observed_credit` 1, `self.workflow.next_return` 1, `self.workflow.pending_work` 1, `self.workflow.perform_selected_wait` 1, `self.workflow.permits_common_action` 1, `self.workflow.reasoning_action_schema` 1, `self.workflow.receive_native_outcome` 1, `self.workflow.receive_outcome` 1, `self.workflow.resolve_pending_deliveries` 1, `self.workflow.resolver` 1, `self.workflow.retain_shared_grading_results` 1, `self.workflow.run_id` 3, `self.workflow.selected` 3, `self.workflow.source_credit_view` 1, `self.workflow.specialist` 2, `self.workflow.store` 9, `self.workflow.validate_report` 1, `table runtime_actions` 8, `table runtime_episodes` 1, `table runtime_model_calls` 2 |
| `task_decision.py` | 89 | decision call | `import root.a102.decision_context` 1, `import root.a102.execution_prompt` 1, `import root.a102.library.hpc_prompt` 1, `import root.a102.runtime` 2, `import root.a102.structural_homology_evidence_prompt` 2, `runtime._action_generation_schema` 1, `runtime._ASSIGNMENT_TRANSPORT` 1, `runtime.DECISION_EXCHANGE_PROTOCOL` 5, `runtime._digest` 1, `runtime.instructional_model_context` 1, `runtime._json` 4, `runtime._recorded_assignment_transport` 1, `runtime.WorkflowError` 5, `self.workflow.contract_information_profile` 1, `self.workflow.decision_exchanges` 1, `self.workflow.decision_protocol` 3, `self.workflow.freeze_contract_information` 1, `self.workflow.freeze_literature_numerical_contracts` 1, `self.workflow.history_preview` 1, `self.workflow.is_job_source` 2, `self.workflow.journal` 1, `self.workflow.numerical_contracts` 1, `self.workflow.provider` 2, `self.workflow.receipts` 4, `self.workflow.services` 1, `self.workflow.uses_received_record_context` 2, `self.workflow.validate_contract_information` 2, `table runtime_model_calls` 5 |
| `task_state.py` | 108 | source state, failure as unit, restore/checkpoint | `import root.a102.episode_source_failure` 1, `import root.a102.runtime` 2, `runtime.ActionLeaf` 1, `runtime.EFFECT_VERSION` 1, `runtime.Episode` 1, `runtime.interpretation_schema` 1, `runtime._json` 2, `runtime._object` 1, `runtime._plain` 1, `runtime.Record` 1, `self.workflow.archive` 1, `self.workflow.completions` 4, `self.workflow.context` 1, `self.workflow.controller_value` 1, `self.workflow.execution_binding` 4, `self.workflow.grains` 1, `self.workflow.inprocess_replay` 7, `self.workflow.journal` 5, `self.workflow.progress_provider` 2, `self.workflow.recover_commissions` 1, `self.workflow.run_id` 1, `self.workflow.source_credit_view` 1, `self.workflow.store` 2, `table runtime_actions` 5 |
| `terminal_execution.py` | 242 | local/HPC command behaviour (exec_command); used here to validate requests and list capabilities | `import root.a102.acquisition` 1, `import root.a102.communication` 1, `import root.a102.domain` 1, `import root.a102.practical_execution_operations` 1, `import root.a102.practical_execution_records` 1, `import root.a102.practical_execution_state` 1, `import root.a102.practical_receipt_information` 3, `import root.a102.practical_yield` 1, `import root.a102.terminal_execution` 1, `import root.a102.terminal_scientific_evidence` 2, `PracticalYieldEstimator` 2 |
| `to_child_api_job_execution.py` | 34 | request envelope for API child (same text in three files) | `import root.a102.runtime` 1, `runtime.ContractInformationError` 1, `runtime.Episode` 2, `runtime.EpisodeGoal` 2, `runtime.EpisodeRequest` 1, `runtime._plain` 3, `runtime.Record` 1, `runtime.validate_saved_fact_form` 1, `self.workflow.context` 2, `self.workflow.grains` 2, `self.workflow.inprocess_completion_order` 2, `self.workflow.launch_instructions` 1, `self.workflow.receipts` 2 |
| `to_child_hpc_job_execution.py` | 34 | request envelope for HPC child | `import root.a102.runtime` 1, `runtime.ContractInformationError` 1, `runtime.Episode` 2, `runtime.EpisodeGoal` 2, `runtime.EpisodeRequest` 1, `runtime._plain` 3, `runtime.Record` 1, `runtime.validate_saved_fact_form` 1, `self.workflow.context` 2, `self.workflow.grains` 2, `self.workflow.inprocess_completion_order` 2, `self.workflow.launch_instructions` 1, `self.workflow.receipts` 2 |
| `to_child_local_job_execution.py` | 34 | request envelope for local child | `import root.a102.runtime` 1, `runtime.ContractInformationError` 1, `runtime.Episode` 2, `runtime.EpisodeGoal` 2, `runtime.EpisodeRequest` 1, `runtime._plain` 3, `runtime.Record` 1, `runtime.validate_saved_fact_form` 1, `self.workflow.context` 2, `self.workflow.grains` 2, `self.workflow.inprocess_completion_order` 2, `self.workflow.launch_instructions` 1, `self.workflow.receipts` 2 |
| `to_children.py` | 42 | children launch_api/launch_local/launch_hpc allowed when a permitted resource of that kind exists; selects receivers and envelopes | none |
| `to_parent.py` | 47 | fact sources/facts: handoff refs, result refs, completed, origin, file sources; report must equal facts | `import root.a102.local_file_capture_results` 1, `import root.a102.protein_structure_result_views` 2 |
| `waiting.py` | 9 | suspension forwarded to backend | `self.workflow.execution_backend` 1, `self.workflow.execution_handle` 2 |
| `yield_estimator.py` | 75 | bounded controller with maximum = remaining eligible requests x handoff_unit; exact-zero when none remain | `import root.a102.numerical` 1, `import root.a102.practical_yield` 1, `BoundedYieldController` 2, `NumericBand` 2, `PracticalYieldEstimator` 2, `YieldController` 2, `YieldEstimate` 2, `YieldParameters` 3 |
