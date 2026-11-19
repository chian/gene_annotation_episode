# a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/execution_job_submission/<file>`
(only the 48 files directly in this folder; it has no `grading/` or `scoring/` subfolder; the child folders
`api_job_execution/`, `hpc_job_execution/`, `local_job_execution/` have their own documents).
Old binding class: `ExecutionEpisode` (`binding_path = 'evolutionary_history_evidence/hpc_work_planning/execution_job_submission'`,
`commissioning_parent = 'evolutionary_history_evidence/hpc_work_planning'`, `roles = ('launch',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `LaunchTask`, prompt renderer `present_execution_context`.
Binding version `execution_episode_v1`; assignment version `execution_launch_assignment_v1`.

## What it is for (its goal, in its own words)

`goal.py` `LaunchGoal.instructions()`:

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded
> inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and
> pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed
> handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with
> exact zero future credit.

So this is the *launch* episode of A104 HPC work planning: it holds a map of concrete execution requests (one per bound
resource) and commissions the resource child (API, local or HPC) that executes one of them; it does not run jobs
itself. Its endpoint is a received usable handoff from a child.

## Task and instructions

`task_instructions.py` composes the model instructions (via the old runner):
1. Start from the generic `INSTRUCTIONS` (old `runtime_prompt`) or a job episode's instructions; because
   `replaces_default_instructions = True`, the goal text above **replaces** them.
2. `REASONING_COMMIT_REQUIREMENT` when `reason` is permitted.
3. Tool-knowledge and launch-instruction-library instructions when those inputs are in the context.
4. The fixed `pending_child_delivery` -> `redeliver_report` repair paragraph.
5. When `wait` is permitted: the in-process `pending_child_` wait paragraph (event `returned`, `after_cursor 0`,
   `reconsider_at null`; waiting earns no scientific credit).
6. When native event targets are configured and `wait` is permitted: the native_event_targets paragraph.
7. Under `decision_exchange_v1` the "fresh provider conversation" history guidance is replaced by the
   request_context / `episode.history view=records` paragraph.

`task.py` (`LaunchTask`): one model decision per unit. `next()` ends with `SourceEnd('source_failed')` after a recorded
source failure, replays recorded units, otherwise assembles the decision context and action schema, calls the model and
applies its response. `child_return_form_policy = HPC_HANDOFF_RETURN_POLICY` is specific to this launch task (the
resource children do not set it). `task_action.py` validates the selection, rejects an all-empty reasoning commit
(unless `evidence_processing.kind = no_applicable_evidence` or the binding says it has task content), admits the
report update with grain `launch`, and executes tool / reason / wait actions; every executed outcome (including failed)
is saved with its credit for the iterator.

Permitted common actions (`episode.py`): under any ancestor with role `hpc` -> `tool`, `child`, `redeliver_report`;
otherwise `tool`, `reason`, `child`, `wait`, `redeliver_report`.

## What it reads from its parent's assignment

`from_parent.py` `assignment_schema('launch')`:

- `version`: const `execution_launch_assignment_v1`;
- `requests`: object keyed by every bound `resource_id` (min 1, no others); each value is that resource's concrete
  launch request schema (`launch_request_schema(_request_schema(...))`): for an API resource the service's own
  assignment schema; for local/pbs_ssh the practical `ASSIGNMENT_SCHEMA` with const `resource_id`/`resource_kind` and a
  `requested_job` anyOf of the generic job and the resource's native/preparation job schemas
  (native_blast, native_blast_masking, native_blast_utility, native_blast_database,
  native_blast_standard_database, native_hmmer, native_hmmer_preparation); a BLAST graded request
  (`BLAST_GRADED_REQUEST_VERSION`) must name an `ncbi_blast` resource;
- `immutable_input_versions`: array of `INPUT_VERSION_SCHEMA`;
- `constraints`: object (`allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind`);
- `launch_instructions`: the launch-instruction library `SELECTION_SCHEMA`.

`prepare_assignment` authenticates a launch coming from an `hpc` / `hpc_execution` parent
(`to_child_execution_job_submission.authenticate_launch` of the parent), validates every request in scope, the masking
and BLAST utility inputs, the immutable input versions and native BLAST database job inputs. `launch_state.initialize`
repeats these checks and the BLAST graded-request requirement at episode start.

## Children it may commission

`child_roles('launch') = ('launch_api', 'launch_local', 'launch_hpc')`. `allowed_children` keeps only the roles for
which some bound resource of that kind is permitted by the assignment (`_permitted`: in `requests` and allowed by the
constraints).

| Child slot | Child episode | What it sends (`to_child_*.py`) | What it takes back (`from_child_*.py`) |
|---|---|---|---|
| `launch_api` | `.../execution_job_submission/api_job_execution` | Child goal refining this goal with the child's report contract; message `{scope, initial_report, inprocess_completion_order?, report_contract_declaration? (validated saved fact form), job_assignment?, episode_assignment? (launch_instructions materialized), evolutionary_history_evidence?, knowledge_inheritance? (receipt binding)}`. The child's assignment is one concrete API request chosen from this episode's `requests`. | The typed form: recorded admission references reused; progress provider (or the binding's `receive_child_progress[_for_role]`) receives the form; references in the form + registry-received references + native timing refs are recorded as receipts (`child_form` / `report_redelivery`) with tool attributions. |
| `launch_local` | `.../execution_job_submission/local_job_execution` | Same request assembly. Assignment: one practical local request. | Same receiving body. |
| `launch_hpc` | `.../execution_job_submission/hpc_job_execution` | Same request assembly. Assignment: one practical PBS/HPC request. | Same receiving body. |

The three `to_child_*` files are identical apart from their docstrings, and so are the three `from_child_*` files.
What this episode credits from a child is the child's usable handoff (`execution_handoff_refs`).

## Decision state and what it shows the model

`decision_context.py` (old-runner body) shows: goal, scope, working_state, visible_record_refs, current_credit,
current_evidence_vector, credit_binding, time_accounting, pending_work, last_local_outcome, feedback, visual_evidence,
report_deliveries, controller state and binding, tools, tool_knowledge, job_episode_options, available_report_facts,
requested_report_purpose/form, current_report_update/basis, report_lifecycle, then this binding's own
`decision_context`.

This binding's own part (`internal_summary.py`): `execution_assignment` (the launch assignment), `execution_progress`
(the report facts below) and, when every request is an `ebi_hmmer` API request or exactly one A104 native job,
`selected_execution_task` = {scientific question and selected tool info from the scientific parent task, and per
request: resource_id, resource_kind, endpoint, constraints, job view (native HMMER jobs in their scientific view),
resource information}.

`task_decision.py` additionally adds resource context, shared-information context, the launch instruction library and
selected launch instructions, child options, the binding's initial decision context (`initial_decision_context`:
execution resource capabilities, initial inventory, received BV-BRC values), completed action reports, requested action
history in HPC contexts, pending work, execution expectations for role `launch` (with job execution options), resource
tool estimates, native event targets and waiting support.

## Tools it offers

`capability_operations.py`: one own tool, `execution.capabilities` (read the actual caller-bound resource configuration
and already recorded inventory; no discovery or selection). It returns `initial_decision_context`. The resource tools
(`exec_command`, API operations, result operations) belong to the children; `resource_information.resource_tool_contracts`
declares them with an `invocation_route` of kind `commission` so the model sees which child slot carries each tool.

## How its credit is counted

`credit.py`: credit kind `operational`. Live credit =
`handoff_unit` x (number of distinct `resource_id`s with a **usable** received handoff that were not already among the
initial known references). The `acquired_record_unit` term is present but its multiplier is fixed at `0.0` (and the
`mixed` branch is dead), so acquired records earn nothing here. The binding record is
`execution_received_records_credit_v1` (qualification: original request resource scope, selector, and actual received
unique information). Once the episode has closed (`closed_credit.py`) the projected view is frozen in the report facts as
`execution_closed_operational_credit_v1` and only that view is returned. Credit is not bounded or rescaled.

Completion (`completion.py`): an action's completed result that names a usable handoff target in context gives the
proof `practical_completion_v1` with endpoint `usable_handoff` and validation key `received_usable_handoff`.

## Continuation (yield estimator and settings)

`yield_estimator.py` `_launch_yield_controller` (requires `require_private_yield = True`):

- Eligible requests = `requests` permitted by the constraints; already received = eligible resource_ids whose usable
  handoff is among the initial known references.
- If some remain: task yield profile `launch:` + `'+'.join(sorted(request classes of eligible requests))`, where a
  request class is `api_<service>[_<algorithm>][_<database>]_handoff`, `practical_<kind>[_native_*]_handoff|outputs`
  or `compact_<version>`. Old controller: `BoundedYieldController(epoch, initial_credit, profile.cutoff,
  remaining = len(eligible - already_received) * handoff_unit, YieldParameters(**profile.parameters))`.
  In the new set of three this is **completion with a target** (target = the remaining uncredited original requests
  x handoff_unit).
- If none remain: exact zero forecast (`launch_original_request_exhaustion_v1`); any non-zero initial or later credit
  raises.

Settings (`configuration.py`): `task_yield_profiles` = {key -> {cutoff > 0, parameters}}; `results_yield_profiles`
(only `native_unbounded_local` / `native_unbounded_hpc`, used by the results role elsewhere); `handoff_unit`,
`acquired_record_unit` (positive finite); `log_window_bytes`, `log_roles`; resources and initial inventory.

## What it reports to its parent

`report_facts.py` / `report_fields.py`: `execution_handoff_refs` (qualified original handoffs), `execution_result_refs`,
`execution_file_source_refs`, `execution_file_capture_outcomes`, `execution_result_origin`, `execution_blast_hsps`,
`execution_completed`, empty lists for every native result family source (HMMER, masking, utility, BLAST database,
standard BLAST database, HMMER preparation, BLAST pairwise), `bvbrc_appservice_support_refs` with AppService, plus the
closed-credit fact. `to_parent.validate_report` requires every `x-source` field to equal the recorded fact.
`required_return_sources` adds `execution_handoff_refs` when the parent is the A104 head and an annotation task is
required. `received_reports.py` also supplies report sources/facts when the receiving role is `annotation` /
`evolutionary_history_evidence` (forwarding of execution file sources, masking, utility, UniProt, BLAST, HMMER, BV-BRC
families).

## Differences from similar episodes

- vs its resource children: this is the only one with child slots, `reason`/`wait`/`child`/`redeliver_report`
  actions (outside HPC ancestry), `execution.capabilities` as its own tool, `HPC_HANDOFF_RETURN_POLICY`, a credit
  counted per resource_id over the request map, and a target-bounded continuation.
- A101 has an episode with the same name (`a101/sequence_homology_evidence/execution_job_submission`); its code was
  not read here. A104-specific content visible in this episode: the native job set (BLAST, masking, utility, BLAST
  database, standard BLAST database, HMMER, HMMER preparation), BLAST graded requests, BV-BRC AppService / phylogeny /
  proteome returns, the native result owner `evolutionary_history_evidence/hpc_work_planning/execution_result_acquisition`,
  and authentication of a launch commissioned from an `hpc` parent.
- Resource kinds bound here: `local`, `pbs_ssh` (hpc), `hmmer_api` and `api` (api).

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| `binding_record.py` | 8 | `as_record()`: binding id `evolutionary_history_evidence/hpc_work_planning/execution_job_submission`, version `execution_episode_v1`, and the full configuration (resources, initial_information, handoff_unit, acquired_record_unit, log window/roles, require_private_yield, results/task yield profiles). Used in closed-credit digests. | none |
| `capability_operations.py` | 19 | Own tool catalog: the single `execution.capabilities` operation (read caller-bound resource configuration and recorded inventory; no discovery or selection); executing it returns `initial_decision_context`. | none |
| `closed_credit.py` | 117 | Closed operational credit: once the episode has closed, freeze the projected credit view inside the report facts (`execution_closed_operational_credit_v1`) together with digests of context, binding, completion, archive, observation history and the receipt prefix; later reads return only that frozen view, never a reprojection. | `import:episode_receipts` (1), `import:episode_return_records` (3), `name:EpisodeReceipts` (1), `name:EpisodeReturnRecords` (1), `name:_same` (3), `table:runtime_episodes` (2), `table:runtime_forms` (3), `table:runtime_observations` (1), `table:runtime_receipt_inheritance` (2), `table:runtime_record_receipts` (2) |
| `completion.py` | 72 | Completion proof: an action completes the launch when its completed result names at least one record that reads as a usable handoff target in context; proof `practical_completion_v1` with endpoint `usable_handoff`, validation key `received_usable_handoff`. `verify_completion` also accepts one recorded estimator observation with exact-zero next gain for a closed episode. | `import:numerical` (1), `import:practical_yield` (1), `import:episode_return_records` (1), `import:method_loop.identities` (1), `name:ESTIMATOR_VERSION` (1), `name:NumericBand` (1), `name:_same` (4), `name:UnitRef` (1), `table:runtime_actions` (1), `table:runtime_observations` (1) |
| `configuration.py` | 65 | Construction settings and their validation: explicit resource map (kinds local / pbs_ssh / hmmer_api / api), initial inventory bound to resources, positive finite handoff_unit and acquired_record_unit, log_window_bytes and log_roles, require_private_yield, results_yield_profiles (only native_unbounded_local / native_unbounded_hpc) and task_yield_profiles (each {cutoff, parameters}); only A104 native_* job keys allowed; builds per-resource TerminalExecutionBehavior, the API record access, BV-BRC phylogeny returns, the execution progress provider (native result owner `.../execution_result_acquisition`), local file sources, result readers and protected readers. | `import:numerical` (1), `name:YieldController` (2), `name:YieldParameters` (2) |
| `contracts.py` | 59 | Shared constants of this episode: VERSION, LAUNCH_VERSION `execution_launch_assignment_v1`, RESULTS_VERSION, RESULT_PROVIDER `episode.execution_result`, ROLES, KINDS, ROLE_KINDS {launch_api: api, launch_local: local, launch_hpc: hpc}, NATIVE_RESULT_ORIGIN, selector schemas, `launch_operation_catalog`, `native_result_operation_catalog`, `_outcome`; re-exports old shared A104 support names. | `import:communication` (1) |
| `credit.py` | 38 | Credit kind `operational`. Live credit = handoff_unit x number of distinct resource_ids with a usable received handoff not already in the initial known references (+ acquired_record_unit x 0: acquired_fraction is fixed 0.0 and the mixed branch is dead). Returns closed view when one exists. | none |
| `decision_context.py` | 54 | Assembles the model's decision context (goal, scope, working_state, visible refs, current credit, credit binding, time accounting, pending work, last outcome, feedback, visual evidence, deliveries, controller state, tools, tool knowledge, job options, available report facts, requested form, current report) and merges the binding's own `decision_context`. Generic old-runner body; role-specific only in its class name. | `self.workflow.binding_context` (1), `self.workflow.catalog` (1), `self.workflow.controller_binding` (1), `self.workflow.delivery_status` (1), `self.workflow.extra_report_sources` (1), `self.workflow.is_scientific_source` (1), `self.workflow.job_episode_options` (1), `self.workflow.journal` (3), `self.workflow.knowledge` (1), `self.workflow.local_outcome_preview` (1), `self.workflow.pending_work` (1), `self.workflow.receipt_projection` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_binding` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (3), `self.workflow.tools` (1), `self.workflow.working_state` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:FACT_MEANINGS` (1), `name:FACT_SOURCES` (1), `name:_references_in` (1), `table:runtime_actions` (2) |
| `decision_contracts.py` | 133 | Exchange-protocol support: interpretation context from received lookups, exchange schema (request_context or select_action), response envelope check, validation of recorded contract-information exchanges. Generic old-runner body. | `self.workflow.contract_information_reply` (1), `self.workflow.decision_exchanges` (2), `self.workflow.journal` (1), `self.workflow.store` (2), `self.workflow.validate_contract_information` (2), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:apply_state_frame` (1), `name:bind_functions` (1), `name:composition_lookup_schema` (2), `name:CONTRACT_INFORMATION_OPERATIONS` (1), `name:DECISION_CONTEXT_VERSION` (1), `name:instructional_model_context` (1), `name:is_contract_information` (1), `name:model_snapshot` (1), `name:_recorded_action_generation_schema` (1), `name:_references_in` (1), `name:requested_contract_information` (1), `name:WorkflowError` (9), `table:runtime_model_calls` (1) |
| `decision_exchange.py` | 113 | The request_context/select_action exchange loop for one decision. Generic old-runner body. | `self.workflow.controller_binding` (1), `self.workflow.decision_exchanges` (1), `self.workflow.execute` (1), `self.workflow.journal` (1), `self.workflow.run_id` (1), `self.workflow.services` (1), `self.workflow.validate_contract_information` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:_action_generation_schema` (1), `name:bind_functions` (1), `name:_category_yield_parameters` (1), `name:child_option_information` (1), `name:DECISION_CONTEXT_VERSION` (1), `name:instructional_model_context` (2), `name:lookup_attempts` (1), `name:model_snapshot` (1), `name:requested_contract_information` (1), `name:schema_failure_diagnostic` (2), `name:state_frame` (1), `name:yield_table` (1), `table:runtime_model_calls` (2) |
| `decision_provider.py` | 60 | Chooses the model completion call, routing through `complete_with_presentation` with this binding's prompt renderer when the provider is the original one. Generic old-runner body. | `self.workflow.provider` (1), `self.workflow.specialist` (2), `import:runtime` (1), `import:providers` (2), `import:root.providers` (1), `name:_ORIGINAL_DECLARED_PRESENTATION` (1), `name:_ORIGINAL_MODEL_COMPLETE` (2), `name:_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION` (2), `name:_ORIGINAL_MODEL_INSTANCE_DICT` (3) |
| `episode.py` | 79 | Binding class `ExecutionEpisode`: binding_path, commissioning_parent `evolutionary_history_evidence/hpc_work_planning`, roles ('launch',), no entry roles, replaces default instructions; child roles = launch_api/launch_local/launch_hpc; `allowed_children` = roles whose bound resource kind is permitted by the assignment; `permitted_common_actions` = tool, child, redeliver_report under an `hpc` ancestor, else tool, reason, child, wait, redeliver_report; `required_return_sources` = execution_handoff_refs when parent is the A104 head and an annotation task is required; per-child request assembler and report receiver. | none |
| `from_child_api_job_execution.py` | 44 | Receives the api_job_execution typed form: reuse recorded admission references, feed the progress provider (or the binding's child-progress hooks), collect form references, registry-received references and native timing refs, and record receipts (child_form / report_redelivery) plus tool attributions. | `workflow.binding_context` (4), `workflow.episode_bindings` (1), `workflow.is_job_source` (2), `workflow.job_episodes` (2), `workflow.native_timing_information` (1), `workflow.progress_provider` (4), `workflow.receipts` (3), `workflow.receive_tool_attributions` (1), `workflow.run_id` (6), `workflow.specialist` (1), `workflow.store` (7), `import:runtime` (1), `import:episode_return_records` (1), `import:delivery_counterpart` (1), `name:child_role_for_delivery` (1), `name:EpisodeReturnRecords` (1), `name:_references_in` (1), `name:WorkflowError` (1), `table:runtime_report_attempts` (2) |
| `from_child_hpc_job_execution.py` | 44 | Same receiving body for hpc_job_execution. | `workflow.binding_context` (4), `workflow.episode_bindings` (1), `workflow.is_job_source` (2), `workflow.job_episodes` (2), `workflow.native_timing_information` (1), `workflow.progress_provider` (4), `workflow.receipts` (3), `workflow.receive_tool_attributions` (1), `workflow.run_id` (6), `workflow.specialist` (1), `workflow.store` (7), `import:runtime` (1), `import:episode_return_records` (1), `import:delivery_counterpart` (1), `name:child_role_for_delivery` (1), `name:EpisodeReturnRecords` (1), `name:_references_in` (1), `name:WorkflowError` (1), `table:runtime_report_attempts` (2) |
| `from_child_local_job_execution.py` | 44 | Same receiving body for local_job_execution. | `workflow.binding_context` (4), `workflow.episode_bindings` (1), `workflow.is_job_source` (2), `workflow.job_episodes` (2), `workflow.native_timing_information` (1), `workflow.progress_provider` (4), `workflow.receipts` (3), `workflow.receive_tool_attributions` (1), `workflow.run_id` (6), `workflow.specialist` (1), `workflow.store` (7), `import:runtime` (1), `import:episode_return_records` (1), `import:delivery_counterpart` (1), `name:child_role_for_delivery` (1), `name:EpisodeReturnRecords` (1), `name:_references_in` (1), `name:WorkflowError` (1), `table:runtime_report_attempts` (2) |
| `from_parent.py` | 47 | Admitted assignment: `execution_launch_assignment_v1` with `requests` keyed by every bound resource_id (each its concrete launch request schema), `immutable_input_versions`, `constraints`, `launch_instructions`. `prepare_assignment` authenticates a launch coming from an `hpc`/`hpc_execution` parent, validates every request (BLAST graded-request variant must name an ncbi_blast resource), masking/utility inputs, input versions and native BLAST database job inputs. | none |
| `goal.py` | 7 | Own goal text: "Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with exact zero future credit." | none |
| `__init__.py` | 0 | Empty package marker. | none |
| `internal_summary.py` | 43 | Episode-specific decision context: `execution_assignment`, `execution_progress` (= report facts), and `selected_execution_task` (scientific question and selected tool info from the scientific parent task, each request's resource, kind, endpoint, constraints and job view) when every request is an ebi_hmmer API or exactly one A104 native job. | none |
| `launch_state.py` | 15 | `initialize`: validate the launch assignment in scope, the BLAST graded-request requirement, masking/utility inputs and immutable input versions. | none |
| `native_receipt_support.py` | 13 | `_delegate`: the per-resource TerminalExecutionBehavior for the assignment's resource_id; `_practical_context` identity. | none |
| `presentation.py` | 60 | `present_execution_context`: choose the text renderer (HPC, published scientific, API launch, selected execution, monitor, receiver) for the decision state, keeping per-episode prompt state across bootstrap/update/lookup frames. | `import:providers` (1), `import:receiver_prompt` (1), `name:apply_state_frame` (3), `name:DECISION_CONTEXT_VERSION` (1), `name:is_api_launch_context` (2), `name:is_published_scientific_context` (2), `name:_ordinary_runtime_receiver_context` (1), `name:render_api_launch_prompt` (1), `name:render_evolutionary_history_evidence_prompt` (1), `name:render_receiver_prompt` (1), `name:text_instructions` (1) |
| `protected_reference_access.py` | 100 | Installs protected readers (protein structure, fluorescence, expression NMF, ATAC, chromatin) and classifies their references before ordinary resolution so a protected denial cannot fall through. | `import:communication` (1) |
| `received_records.py` | 57 | Which references this episode has received (`known_record_refs`, `initial_known_record_refs`) and, from them, the usable handoffs and result bodies that belong to this context. | `import:episode_receipts` (1), `name:EpisodeReceipts` (1), `table:runtime_actions` (1), `table:runtime_receipt_inheritance` (2) |
| `received_reference_access.py` | 81 | Resolves references in received reports across masking, utility, BLAST/HMMER, UniProt, BV-BRC namespaces. | none |
| `received_report_admission.py` | 93 | Validates received child reports through each result family's returns host and collects the admitted references; every handoff/result/receipt reference must resolve in its namespace. | none |
| `received_reports.py` | 113 | Report sources and facts this binding supplies when the receiving role is `annotation`/`evolutionary_history_evidence` (file sources, masking, utility, UniProt, native BLAST database, HMMER preparation, BLAST pairwise, BV-BRC); `initial_references` for launch / launch_local / results. | none |
| `report_delivery.py` | 32 | `finish`: without a report contract return credit, pending handles and registry report facts; with one, fill the form from facts and interpretations once and save it. Generic old-runner body. | `self.workflow.binding_context` (1), `self.workflow.episode_bindings` (1), `self.workflow.facts` (1), `self.workflow.journal` (2), `self.workflow.pending_handles` (1), `self.workflow.release` (2), `self.workflow.source_credit_view` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:form_with_facts` (1), `name:Record` (2), `table:runtime_forms` (2) |
| `report_facts.py` | 35 | Report facts: empty lists for every native family source, `execution_handoff_refs`, `execution_result_refs`, file source refs, result origin, `execution_completed` (any handoff read as completed), plus closed-credit facts. | none |
| `report_fields.py` | 51 | Report fact sources offered to the commissioning parent with their meanings and schemas (HMMER, masking, utility, UniProt, BLAST database, HMMER preparation, BLAST pairwise, AppService, BV-BRC data, terminal practical receipts for launch_local/launch_hpc, execution_handoff_refs, execution_result_refs, execution_completed, execution_result_origin, execution_blast_hsps, BLAST graded return). | none |
| `report_reference_access.py` | 129 | `resolve`: reference resolution for this episode's report across all A104 result namespaces. | `import:episode_bindings` (2), `name:reference_in_context` (2) |
| `request_validation.py` | 53 | Concrete request schema per resource (API service schema or practical ASSIGNMENT_SCHEMA with resource_id/resource_kind consts and requested_job alternatives), request validation (resource bound, kind, workspace confinement, operations validator), constraint checks, `_permitted` (allowed_resource_ids / allowed_kinds / resource_id / kind), input-version validation. | none |
| `resource_information.py` | 88 | Per-resource information shown to the model (kind, availability unknown, tool names, workspace, policy, account, service, base_url, inventory snapshot, API configuration facts), `initial_decision_context` (capabilities, initial information, received BV-BRC values, received BLAST jobs for annotation roles), `capabilities`, and `resource_tool_contracts` (launch and results operations per resource routed by commission, plus homology API and proteome tool contracts and native operation contracts). | none |
| `resource_return_support.py` | 20 | Service probes: has AppService, has UniProt, AppService fact sources, whether BV-BRC reports are forwarded. | none |
| `retained_result_receipts.py` | 171 | Results-role support: handoff target of the assignment, selector validation per native family, result directories, recorded selected result actions, result-body validation and reading, context-target matching. | `table:runtime_actions` (1), `table:runtime_episodes` (1) |
| `scientific_inputs.py` | 54 | Masking and BLAST utility input validation and retained-target / reference-access helpers. | none |
| `task_action.py` | 159 | Applies a model response (selection validation, empty reasoning-commit rejection, report-update admission with grain `launch`) and executes the selected tool/reason/wait action, saving the outcome and credit for the iterator. Generic old-runner body. | `self.workflow.automatic_score_updates` (1), `self.workflow.binding_context` (2), `self.workflow.completions` (1), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.execute` (1), `self.workflow.execution_binding` (5), `self.workflow.journal` (3), `self.workflow.last_observed_credit` (1), `self.workflow.pending_work` (1), `self.workflow.perform_selected_wait` (1), `self.workflow.permits_common_action` (1), `self.workflow.reasoning_action_schema` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolver` (1), `self.workflow.retain_shared_grading_results` (1), `self.workflow.run_id` (2), `self.workflow.selected` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (2), `self.workflow.store` (6), `self.workflow.validate_report` (1), `import:runtime` (2), `import:library.live_runtime_functions` (1), `name:AcquisitionError` (2), `name:ActionFailure` (1), `name:bind_functions` (1), `name:ContractError` (1), `name:ContractInformationError` (1), `name:_decode_recorded_action_response` (1), `name:EventTargetError` (2), `name:observes_action_outcome` (1), `name:ReportBoundaryError` (1), `name:ReportRedelivery` (2), `name:schema_failure_diagnostic` (1), `name:_wait_target_feedback` (2), `name:WorkflowError` (1), `table:runtime_actions` (6), `table:runtime_model_calls` (1) |
| `task_decision.py` | 154 | Makes one model call with the assembled context (resource context, launch instruction library, selected launch instructions, child options, initial binding context, completed action reports, requested action history for HPC context, pending work, execution expectations for role `launch`, resource estimates, native event targets, waiting support). Generic old-runner body except the role name. | `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.contract_information_profile` (1), `self.workflow.decision_exchanges` (1), `self.workflow.decision_protocol` (3), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.freeze_literature_numerical_contracts` (1), `self.workflow.history_preview` (1), `self.workflow.is_job_source` (3), `self.workflow.job_episodes` (4), `self.workflow.journal` (1), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.numerical_contracts` (1), `self.workflow.pending_work` (1), `self.workflow.permits_common_action` (1), `self.workflow.provider` (2), `self.workflow.receipts` (4), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (5), `self.workflow.services` (1), `self.workflow.shared_information_context` (1), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (2), `self.workflow.waiting_support` (1), `import:runtime` (2), `import:episode_work_report` (2), `import:library.live_runtime_functions` (1), `name:_action_generation_schema` (1), `name:_ASSIGNMENT_TRANSPORT` (1), `name:bind_functions` (1), `name:child_option_information` (1), `name:completed_action_reports` (2), `name:DECISION_EXCHANGE_PROTOCOL` (5), `name:instructional_model_context` (1), `name:_recorded_assignment_transport` (1), `name:requested_action_history` (2), `name:WorkflowError` (5), `table:runtime_model_calls` (5) |
| `task_instructions.py` | 35 | Instruction composition: the goal text replaces the generic default; adds reasoning-commit requirement, tool-knowledge and launch-instruction library text, redeliver_report repair paragraph, wait paragraph, native-event paragraph, exchange-protocol replacement. | `workflow.binding_context` (1), `workflow.decision_protocol` (1), `workflow.is_job_source` (1), `workflow.job_episodes` (1), `workflow.knowledge` (1), `workflow.launch_instructions` (1), `workflow.native_event_information` (1), `workflow.permits_common_action` (3), `workflow.specialist` (1), `import:runtime_prompt` (2), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:DECISION_EXCHANGE_PROTOCOL` (1), `name:INSTRUCTIONS` (3), `name:REASONING_COMMIT_REQUIREMENT` (1) |
| `task.py` | 100 | `LaunchTask.next`: one decision per unit, with source_failed ending, replay of recorded units, model call and response application; `child_return_form_policy = HPC_HANDOFF_RETURN_POLICY` (own to this launch task). | `self.workflow.action_schema` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (2), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execution_binding` (2), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (4), `self.workflow.next_return` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.run_id` (1), `self.workflow.selected` (2), `self.workflow.store` (3), `import:runtime` (2), `import:providers` (1), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:bind_functions` (1), `name:ModelCallError` (1), `name:record_source_failure` (1), `name:SourceEnd` (2), `name:WorkflowError` (1), `table:runtime_actions` (2), `table:runtime_episodes` (1), `table:runtime_model_calls` (1) |
| `task_state.py` | 117 | Per-episode task state: identity, call index, feedback, last outcome, report values/basis, restore/checkpoint/effect recording, execution-failure recording. Generic old-runner body. | `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `workflow.context` (1), `workflow.grains` (1), `import:runtime` (2), `import:episode_source_failure` (1), `import:library.live_runtime_functions` (1), `name:ActionLeaf` (1), `name:bind_functions` (1), `name:EFFECT_VERSION` (1), `name:Episode` (1), `name:interpretation_schema` (1), `name:Record` (1), `name:record_source_failure` (1), `table:runtime_actions` (5) |
| `task_waiting.py` | 9 | `suspension_changed`: pass a wait dependency to the detached execution backend. | `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2) |
| `terminal_validation.py` | 67 | `operation_catalog(kind)` (single `exec_command` tool for local/hpc) and a TerminalExecutionBehavior used for request validation and practical-receipt resolution. | `import:communication` (1) |
| `to_child_api_job_execution.py` | 30 | Builds the child request: path, child goal refining this goal with the child report contract, message {scope, initial_report, inprocess_completion_order, report_contract_declaration (validated saved fact form), job_assignment, episode_assignment (launch instructions materialized), evolutionary_history_evidence, knowledge_inheritance}. | `workflow.context` (2), `workflow.evolutionary_history_evidence_binding` (1), `workflow.grains` (2), `workflow.inprocess_completion_order` (2), `workflow.launch_instructions` (1), `workflow.receipts` (2), `import:runtime` (1), `import:episode_contract_information` (1), `name:ContractInformationError` (1), `name:Episode` (2), `name:EpisodeGoal` (2), `name:EpisodeRequest` (1), `name:Record` (1), `name:validate_saved_fact_form` (1) |
| `to_child_hpc_job_execution.py` | 30 | Same request assembly for hpc_job_execution. | `workflow.context` (2), `workflow.evolutionary_history_evidence_binding` (1), `workflow.grains` (2), `workflow.inprocess_completion_order` (2), `workflow.launch_instructions` (1), `workflow.receipts` (2), `import:runtime` (1), `import:episode_contract_information` (1), `name:ContractInformationError` (1), `name:Episode` (2), `name:EpisodeGoal` (2), `name:EpisodeRequest` (1), `name:Record` (1), `name:validate_saved_fact_form` (1) |
| `to_child_local_job_execution.py` | 30 | Same request assembly for local_job_execution. | `workflow.context` (2), `workflow.evolutionary_history_evidence_binding` (1), `workflow.grains` (2), `workflow.inprocess_completion_order` (2), `workflow.launch_instructions` (1), `workflow.receipts` (2), `import:runtime` (1), `import:episode_contract_information` (1), `name:ContractInformationError` (1), `name:Episode` (2), `name:EpisodeGoal` (2), `name:EpisodeRequest` (1), `name:Record` (1), `name:validate_saved_fact_form` (1) |
| `to_parent.py` | 31 | `validate_report`: check masking/utility returns and UniProt frozen facts, validate the form and require every x-source field to equal the recorded fact. | none |
| `yield_estimator.py` | 67 | Continuation for role launch: task yield profile key `launch:` + sorted request classes; bounded by remaining original requests not yet received x handoff_unit; exact zero when every eligible request was already in the initial handoffs. | `import:numerical` (1), `import:practical_yield` (1), `name:BoundedYieldController` (1), `name:NumericBand` (1), `name:PracticalYieldEstimator` (1), `name:YieldController` (1), `name:YieldEstimate` (1), `name:YieldParameters` (2) |
