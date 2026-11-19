# Episode intent: `a102/structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission`

Source: this episode's own files at commit `97308b94c` (45 Python files, 2,578 lines, directly in the folder; its
`tests/` folder and its three child folders were not read). Old role name: `launch`. Old class: `ExecutionEpisode`,
task class `LaunchTask`. Old `binding_path`:
`structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission`; old
`commissioning_parent`: `structural_homology_evidence/hpc_work_planning/hpc_allocation_execution`.

## What this episode is for

It chooses on which bound resource to run one permitted concrete execution request, commissions the resource child
that does the running, and returns the usable handoff it receives. Its goal text, verbatim from `goal.py`:

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities,
> recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs,
> constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive its
> requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes this
> launch endpoint with exact zero future credit.

## Task and instructions

One unit is one model-selected action. Permitted actions (`action_policy.py`):

- under an `hpc` ancestor: tool, child, redeliver_report;
- otherwise: tool, reason, child, wait, redeliver_report.

A reasoning commit, where permitted, is admitted against the Store's reasoning schema; an empty commit is refused
(`empty_reasoning_commit`) unless it declares `no_applicable_evidence` or the binding says it has task content.

Instructions (`instructions.py`): the goal text; the reasoning-commit requirement when reasoning is permitted;
tool-knowledge and launch-instruction library text when present; the report-repair paragraph; the wait and
native-event paragraphs when wait is permitted; the exchange-history wording under the exchange protocol. The
episode supplies its whole instructions.

## What it reads from its parent's assignment

Form `execution_launch_assignment_v1` (`from_parent.py`, `parent_input_custody.py`):

| Field | Meaning | Check |
|---|---|---|
| `requests` | One concrete execution request per bound `resource_id` (at least one) | Each validated against its resource: identity, kind, workspace confined to the resource workspace; API requests validated by the API provider; native protein-structure job inputs validated |
| `immutable_input_versions` | The pinned versions of the job's inputs | Validated in scope |
| `constraints` | `allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind` | Decide which resources are permitted |
| `launch_instructions` | A selection from the launch-instruction library | Materialised for children |

Under an `hpc` or `hpc_execution` parent the launch must be the exact launch assignment of one frozen plan in the
owner's ledger, with one reservation per plan and none after the plan is closed (`authenticate_launch`, defined in
the parent's `to_child_execution_job_submission.py`). At its first decision under an HPC parent it is also given
the plan's job (`hpc_execution_job`: plan id, objective, scientific manifest, acceptance, supplied input file).

## Children

Three child slots, one per resource kind (`to_children.py`). A child is allowed only when a bound resource of that
kind is permitted by the assignment's requests and constraints.

| Child (old role) | Folder | What it sends | What it takes back |
|---|---|---|---|
| `launch_api` | `api_job_execution` | A request whose goal refines its own; message with `scope`, `initial_report`, the job or episode assignment (the selected request for that resource; launch instructions materialised), an optional report-contract declaration checked against the contract, and receipt inheritance. | The child's typed form or its redelivery: a recorded admission is reused if present; child progress is received; references in the form are received (handoff, result and receipt references must be qualified); native timing receipts are recorded once; tool attributions are received. |
| `launch_local` | `local_job_execution` | Same envelope. | Same receipt. |
| `launch_hpc` | `hpc_job_execution` | Same envelope. | Same receipt. |

The three `to_child_*` files are the same text with a different docstring, and so are the three `from_child_*`
files.

The resource child "owns iterative execution in the shared loop"; this episode does not run commands itself.

## Decision state and what the model sees

Beyond the common decision fields: the assignment; progress facts so far; at the first decision the resource
capabilities and recorded inventory per bound resource (configured values, availability `unknown`, no probe); and,
when every request is a local protein-structure job, a `selected_execution_task_v1` record with the scientific
parent's question and selected tool info. `decision_inputs.py` adds shared-information context,
`requested_action_history` in an HPC context and execution expectations for role `launch`.

## Tools

| Tool | What it does |
|---|---|
| `execution.capabilities` | Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection. |

(When the context is a protein-structure result context the protein-structure result operations are offered
instead; that branch belongs to the results side.)

## Credit

Credit kind `operational`. Credit = `handoff_unit` × the number of resources for which a usable handoff was newly
received (resources already handed off at the start are excluded). Acquired results earn nothing here (the acquired
fraction is fixed at 0). Rule name `execution_received_records_credit_v1`. At closure the credit view is frozen and
later reads return only the frozen view (`closed_credit.py`).

## Continuation

Settings: `task_yield_profiles['launch:' + classes joined by '+']` = `{cutoff > 0, parameters}`, where each
eligible original request has a class (`yield_estimator.py`):

- API request: `api_<service>[_<algorithm>][_<database>]_handoff`;
- practical request: `practical_<resource kind>[_<native job keys>]_handoff` or `..._outputs` by endpoint;
- anything else: `compact_<version>`.

Estimator: **bounded quality** (old `BoundedYieldController`) with maximum = `handoff_unit` × (eligible original
requests not already handed off at the start). When none remain, the forecast is exact zero and any non-zero
credit is an error. A received usable handoff is the completion target (`completion.py`, proof
`practical_completion_v1` with key `received_usable_handoff`), and the binding also offers the completion estimator (`practical_estimator`) keyed on that proof: "Actual
received usable handoff completes this launch endpoint with exact zero future credit." Without a configured
private yield the old code raises `execution_private_yield_binding_not_enabled`.

## What it reports to its parent

The parent's typed form, built once at closure. Facts it can fill (`to_parent.py`): `execution_handoff_refs`,
`execution_result_refs`, `execution_result_origin` and `execution_completed` (true when a received handoff is
marked complete by the handoff reader). A report field declared from a fact must equal it. Under the HPC parent the
return contract is `hpc_launch_report_form`: one field, `execution_handoff_refs`. When the axis head is the parent
and requires it, the return must carry `execution_handoff_refs`.

## Differences from similar episodes

- A second copy exists at `hpc_work_planning/execution_job_submission`. By blob hash, 38 of 45 files are
  identical; `binding_record.py`, `episode.py`, `execution_contracts.py`, `from_parent.py` and the three
  `to_child_*` files differ.
- Against `execution_result_acquisition` (37 shared file names): real differences are in `goal.py`, `credit.py`,
  `completion.py`, `yield_estimator.py`, `from_parent.py`, `parent_input_custody.py`, `action_policy.py`,
  `internal_summary.py`, `to_parent.py`, `execution_state.py`, `task.py` (reasoning-commit admission) and the
  result acquisition/publication files (reduced to validation here). Files only here: `api_operations.py`,
  `to_children.py`, three `to_child_*` and three `from_child_*` files.
- Against its own child `api_job_execution` (blob hash only): only `__init__.py` and `terminal_execution.py` are
  identical; every other shared file differs, and the child has `child_eligibility.py` and
  `parent_launch_contract.py`.
- It carries result-side text it does not use as a launch episode: `result_selection._target`/`_selector`/`_windows`,
  `retained_result_publication.py`, the `results` branches in `from_parent.initial_references` and
  `to_parent.fact_sources`, and `terminal_execution.py`, which describes the `launch_local`/`launch_hpc` children
  (`exec_command`) rather than this episode.

## Old support modules this episode imports

Where each imported old module is now (looked up in `runs/placement_plan/placement.tsv` and by file name under
`episode_support/`; the modules themselves were not read):

| Old module (`root.a102.`...) | Files importing it | Home now |
|---|---|---|
| `a102_execution_bindings` | 1 | no placed home found |
| `acquisition` | 1 | episode_support/acquisition/structural_homology_evidence/acquisition.py |
| `api_service_execution` | 1 | no placed home found |
| `communication` | 2 | no structural_homology_evidence copy found (same-named copies exist for seven other axes under episode_support/forms/AXIS/; top-level method_loop/communication.py exists) |
| `decision_context` | 4 | deleted old-runner module |
| `delivery_counterpart` | 3 | no placed home found |
| `domain` | 2 | episode_support/records/structural_homology_evidence/domain.py |
| `episode_bindings` | 1 | the deleted old per-axis binding table |
| `episode_receipts` | 2 | no structural_homology_evidence copy found (copies exist for two other axes under episode_support/records/AXIS/) |
| `episode_return_records` | 5 | no placed home found |
| `episode_source_failure` | 2 | no placed home found |
| `episode_work_report` | 1 | no placed home found |
| `execution_contracts` | 2 | episode_support/forms/structural_homology_evidence/execution_contracts.py |
| `execution_input_versions` | 1 | no placed home found |
| `execution_progress` | 1 | no placed home found |
| `execution_prompt` | 4 | no placed home found |
| `launch_instructions` | 1 | episode_support/instructions/launch_instructions.py |
| `library.action_contracts` | 1 | no placed home found |
| `library.hpc_handoff_report_contract` | 1 | no placed home found |
| `library.hpc_prompt` | 5 | no placed home found |
| `library.private_policy_call` | 2 | no placed home found |
| `library.report_fact_assembly` | 1 | no placed home found |
| `local_file_capture_results` | 2 | episode_support/records/local_execution/local_file_capture_results.py |
| `method_loop.identities` | 1 | top-level method_loop/identities.py (the only method_loop) |
| `native_file_capture` | 1 | episode_support/records/local_execution/structural_homology_evidence/native_file_capture.py |
| `native_protein_structure_acquisition` | 1 | episode_support/acquisition/protein_structure/native_protein_structure_acquisition.py |
| `native_protein_structure_results` | 3 | no placed home found |
| `native_protein_structure_returns` | 2 | no placed home found |
| `native_protein_structure_tool_info` | 2 | episode_support/tools/protein_structure/native_protein_structure_tool_info.py |
| `numerical` | 3 | old yield code; its names NumericBand, YieldParameters, YieldEstimate, estimate_nonnegative_yield, estimate_bounded_credit_yield are now in top-level yield_control; YieldController/BoundedYieldController are not (controllers there are Accumulation/BoundedQuality/Completion) |
| `practical_execution_operations` | 2 | episode_support/jobs/structural_homology_evidence/practical_execution_operations.py |
| `practical_execution_records` | 2 | episode_support/records/structural_homology_evidence/practical_execution_records.py |
| `practical_execution_state` | 2 | episode_support/jobs/structural_homology_evidence/practical_execution_state.py |
| `practical_receipt_information` | 2 | episode_support/records/practical_receipt_information.py |
| `practical_yield` | 3 | no placed home found; completion with a target is yield_control.CompletionYieldEstimator |
| `protein_structure_contracts` | 1 | episode_support/forms/protein_structure/structural_homology_evidence/protein_structure_contracts.py |
| `protein_structure_operands` | 3 | episode_support/readers/protein_structure/protein_structure_operands.py |
| `protein_structure_result_views` | 2 | episode_support/readers/protein_structure/structural_homology_evidence/protein_structure_result_views.py |
| `protein_structure_selection` | 2 | episode_support/readers/protein_structure/protein_structure_selection.py |
| `providers` | 1 | gene_annotation_episode/model_provider.py (defines ModelCallError) |
| `read_mapping` | 1 | episode_support/readers/sequence_alignment/structural_homology_evidence/read_mapping.py |
| `resource_records` | 1 | episode_support/records/hpc/resource_records.py |
| `runtime` | 15 | the deleted old per-axis runner |
| `runtime_prompt` | 1 | episode_support/instructions/structural_homology_evidence/runtime_prompt.py |
| `state` | 1 | gene_annotation_episode/state.py (the shared Store) |
| `structural_homology_evidence_prompt` | 5 | no placed home found |
| `terminal_execution` | 1 | episode_support/jobs/local_execution/structural_homology_evidence/terminal_execution.py |
| `terminal_scientific_evidence` | 1 | episode_support/findings/structural_homology_evidence/terminal_scientific_evidence.py |

## File by file

Counts are occurrences in the file text. `self.workflow` also covers `source.workflow` and a `workflow` argument;
"BindingContext fields" are attribute reads on the old context object (`context`, `parent`, `child`); "old-runner
callbacks defined" are methods the old runner called on the binding or task. The same rows, one per name and file,
are in `runs/carry_over/calls/a102_04.tsv` (1079 uses in this episode).

| Old file | Lines | This episode's own intent in it | Old-runner names used (name×uses) |
|---|---|---|---|
| `__init__.py` | 0 | Nothing (package marker). | none |
| `action_policy.py` | 13 | Permitted actions: under an `hpc` ancestor tool, child, redeliver_report; otherwise tool, reason, child, wait, redeliver_report. | **BindingContext fields**: `path`; **old-runner callbacks defined**: `permitted_common_actions`; **per-axis providers**: `self.native_protein_structure_results` |
| `api_operations.py` | 25 | Its one tool, `execution.capabilities` (read the caller-bound resource configuration and recorded inventory; no discovery, no selection). | **BindingContext fields**: `assignment`; **imports from old `root.a102`**: `native_file_capture`, `native_protein_structure_results`; **old-runner callbacks defined**: `catalog`, `execute`; **per-axis providers**: `self.local_file_sources`, `self.native_protein_structure_results` |
| `binding_record.py` | 8 | Its configuration record (same fields as the results episode, its own binding id). | **old-runner callbacks defined**: `as_record` |
| `closed_credit.py` | 116 | Freezing and re-reading the closed credit view; same text as the results episode apart from names. | **BindingContext fields**: `as_record`×2, `episode_id`×8, `role`; **imports from old `root.a102`**: `episode_receipts`, `episode_return_records`×3; **old support classes**: `EpisodeReceipts`×2, `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_episodes`×2, `runtime_forms`×3, `runtime_observations`, `runtime_receipt_inheritance`×2, `runtime_record_receipts`×2 |
| `completion.py` | 79 | When the launch is complete: an action's outcome carries a reference to a usable handoff matching its assignment; the completion proof (`practical_completion_v1`, key `received_usable_handoff`) and its verification. | **BindingContext fields**: `assignment`×2, `episode_id`×7, `run_id`×3, `scope`; **imports from old `root.a102`**: `episode_return_records`, `method_loop.identities`, `numerical`, `practical_yield`; **old-runner callbacks defined**: `completion_for_action`, `verify_completion`; **per-axis providers**: `self.job_progress_provider`×2, `self.native_protein_structure_results`×6; **journal/receipt tables**: `runtime_actions`, `runtime_observations`; **old yield names**: `ESTIMATOR_VERSION`×2, `NumericBand`×2 |
| `configuration.py` | 61 | Settings and checks; same text as the results episode apart from names (resources, units, log selection, yield profiles, per-resource providers). | **imports from old `root.a102`**: `api_service_execution`, `execution_progress`, `native_protein_structure_results`, `native_protein_structure_returns`, `numerical`; **per-axis providers**: `self.api_execution`×2, `self.job_progress_provider`, `self.local_file_sources`, `self.native_protein_structure_results`, `self.native_protein_structure_returns`, `self._practical`×2, `self.tool_registry`; **old support classes**: `APIServiceExecution`×2, `ExecutionProgressProvider`×2, `LocalFileSourceResults`×2, `NativeProteinStructureResults`×2, `NativeProteinStructureReturns`×2; **old yield names**: `YieldController`×3, `YieldParameters`×3 |
| `credit.py` | 31 | Credit kind `operational`. Credit = handoff_unit times the number of resources with a newly received usable handoff (resources already handed off at the start excluded). Acquired results earn nothing here. | **old-runner callbacks defined**: `credit_kind`, `credit_view`, `project_credit`; **per-axis providers**: `self.job_progress_provider`, `self.native_protein_structure_results`×2 |
| `decision_contracts.py` | 128 | Nothing of its own (exchange envelope and saved-exchange validation). | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`×2, `structural_homology_evidence_prompt`×2; **old-runner callbacks defined**: `exchange_response`, `exchange_schema`, `interpretation_context`, `validate_contract_exchange_history`, `validate_contract_exchange_request`; **old runtime**: `apply_state_frame`, `composition_lookup_schema`×2, `CONTRACT_INFORMATION_OPERATIONS`, `DECISION_CONTEXT_VERSION`, `Draft202012Validator`, `instructional_model_context`, `is_contract_information`, `_json`×8, `json`, `Mapping`×2, `model_snapshot`, `_object`×3, `_recorded_action_generation_schema`, `_references_in`, `requested_contract_information`, `ValidationError`, `WorkflowError`×9; **self.workflow**: `contract_information_reply`, `decision_exchanges`×2, `journal`, `store`×2, `validate_contract_information`×2; **journal/receipt tables**: `runtime_model_calls`; **old yield names**: `_category_yield_parameters`, `yield_table` |
| `decision_exchange.py` | 108 | Nothing of its own (request_context/select_action exchange loop). | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`×2, `structural_homology_evidence_prompt`×2; **old-runner callbacks defined**: `exchange_decision`; **old runtime**: `_action_generation_schema`, `_category_yield_parameters`, `child_option_information`, `DECISION_CONTEXT_VERSION`, `instructional_model_context`×2, `_json`×2, `lookup_attempts`, `Mapping`, `model_snapshot`, `_plain`×2, `requested_contract_information`, `schema_failure_diagnostic`×2, `sqlite3`, `state_frame`, `ValidationError`×4, `yield_table`; **self.workflow**: `controller_binding`, `decision_exchanges`, `execute`, `journal`, `run_id`, `services`, `validate_contract_information`; **journal/receipt tables**: `runtime_model_calls`×2; **old yield names**: `_category_yield_parameters`×2, `yield_table`×2 |
| `decision_inputs.py` | 58 | Additions to each decision; execution expectations are for role `launch`. | **imports from old `root.a102`**: `episode_work_report`×2, `library.hpc_prompt`, `runtime`×2; **old-runner callbacks defined**: `decision_inputs`; **old runtime**: `child_option_information`, `Mapping`; **self.workflow**: `available_child_roles`, `binding_context`, `episode_bindings`, `execution_expectations`, `is_job_source`, `job_episodes`×2, `launch_instructions`×2, `native_estimation_context`, `pending_work`, `permits_common_action`, `resource_context`, `resource_estimator`×5, `shared_information_context`, `waiting_support` |
| `decision_provider.py` | 20 | Selected-execution prompt renderer under the same context test as the results episode. | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`, `structural_homology_evidence_prompt`×2; **old-runner callbacks defined**: `complete_decision`; **old provider interface**: `complete_with_presentation`, `prompt_renderer`; **self.workflow**: `provider`, `specialist`; **old yield names**: `_category_yield_parameters`, `yield_table` |
| `decision_state.py` | 45 | What the model is shown; same text as the results episode apart from names. | **imports from old `root.a102`**: `runtime`×2; **old-runner callbacks defined**: `decision_state`; **old runtime**: `FACT_MEANINGS`, `FACT_SOURCES`, `json`×2, `Mapping`×3, `_plain`×2, `_references_in`; **self.workflow**: `binding_context`, `catalog`, `controller_binding`, `delivery_status`, `extra_report_sources`, `is_scientific_source`, `job_episode_options`, `journal`×3, `knowledge`, `local_outcome_preview`, `pending_work`, `receipt_projection`, `run_id`, `source_credit_binding`, `source_credit_view`, `specialist`, `store`×3, `tools`, `working_state`; **journal/receipt tables**: `runtime_actions`×2 |
| `episode.py` | 38 | The binding: path, parent `hpc_allocation_execution`, role `launch`, no entry role, supplies its whole instructions, selected-execution prompt renderer. | **imports from old `root.a102`**: `structural_homology_evidence_prompt`; **old binding attributes**: `binding_path`, `commissioning_parent`, `decision_prompt_renderer`, `decision_source_type`, `entry_roles`, `replaces_default_instructions`, `roles` |
| `execution_contracts.py` | 47 | Forms and constants; same as the results episode except that it imports its own `terminal_execution`. `execution_launch_assignment_v1` and the `execution.capabilities` tool are the launch parts. | **absolute imports inside the episode tree**: `structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.terminal_execution`; **imports from old `root.a102`**: `a102_execution_bindings`, `communication`, `domain`, `execution_contracts`, `launch_instructions`, `local_file_capture_results`, `native_protein_structure_acquisition`, `practical_execution_operations`, `practical_execution_records`, `practical_execution_state`, `practical_receipt_information`, `resource_records`; **old support classes**: `LocalFileSourceResults`, `PracticalReceiptInformation` |
| `execution_state.py` | 41 | Start-up: admit the launch assignment, check protein-structure job inputs and the immutable input versions. | **BindingContext fields**: `assignment`×4, `episode_id`×2, `role`, `run_id`×2, `scope`×3; **imports from old `root.a102`**: `protein_structure_operands`; **old-runner callbacks defined**: `initialize`; **per-axis providers**: `self.api_execution`, `self.local_file_sources`×2, `self.native_protein_structure_returns`, `self._practical` |
| `from_child_api_job_execution.py` | 45 | Receipt of the API child's typed form or redelivery: recorded admission reuse, child progress, received references, native timing receipts, tool attributions. The three `from_child_*` files differ only in the docstring. | **imports from old `root.a102`**: `delivery_counterpart`, `episode_return_records`, `runtime`×2; **old runtime**: `_json`, `json`, `_references_in`, `WorkflowError`; **self.workflow**: `binding_context`×4, `episode_bindings`, `is_job_source`×2, `job_episodes`×2, `native_timing_information`, `progress_provider`×4, `receipts`×3, `receive_tool_attributions`, `run_id`×6, `specialist`, `store`×7; **old support classes**: `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_report_attempts`×2 |
| `from_child_hpc_job_execution.py` | 45 | Same as the API receiver; docstring names `launch_hpc`. | **imports from old `root.a102`**: `delivery_counterpart`, `episode_return_records`, `runtime`×2; **old runtime**: `_json`, `json`, `_references_in`, `WorkflowError`; **self.workflow**: `binding_context`×4, `episode_bindings`, `is_job_source`×2, `job_episodes`×2, `native_timing_information`, `progress_provider`×4, `receipts`×3, `receive_tool_attributions`, `run_id`×6, `specialist`, `store`×7; **old support classes**: `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_report_attempts`×2 |
| `from_child_local_job_execution.py` | 45 | Same as the API receiver; docstring names `launch_local`. | **imports from old `root.a102`**: `delivery_counterpart`, `episode_return_records`, `runtime`×2; **old runtime**: `_json`, `json`, `_references_in`, `WorkflowError`; **self.workflow**: `binding_context`×4, `episode_bindings`, `is_job_source`×2, `job_episodes`×2, `native_timing_information`, `progress_provider`×4, `receipts`×3, `receive_tool_attributions`, `run_id`×6, `specialist`, `store`×7; **old support classes**: `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_report_attempts`×2 |
| `from_parent.py` | 50 | Admission of the parent's assignment: `execution_launch_assignment_v1` with one request per bound resource, immutable input versions, constraints and a launch-instruction selection; under an `hpc`/`hpc_execution` parent the launch must be the exact planned one (`authenticate_launch`); return source `execution_handoff_refs` when the axis head requires it. | **BindingContext fields**: `assignment`×2, `path`, `role`×5; **absolute imports inside the episode tree**: `structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.to_child_execution_job_submission`; **imports from old `root.a102`**: `protein_structure_operands`×3; **old-runner callbacks defined**: `assignment_schema`, `child_assignment_schema`, `initial_references`, `prepare_assignment`, `required_return_sources`; **per-axis providers**: `self.native_protein_structure_results`, `self.native_protein_structure_returns`×3; **self.services**: `annotation_task_required` |
| `goal.py` | 8 | The goal text (choose which permitted concrete request to commission on an explicit resource; the resource child owns iterative execution; a received usable handoff completes the launch with exact zero future credit). | **old-runner callbacks defined**: `instructions` |
| `instructions.py` | 23 | Instruction text; same composition as the results episode. | **imports from old `root.a102`**: `runtime_prompt`×2; **old-runner callbacks defined**: `instructions`; **old runtime_prompt**: `DECISION_EXCHANGE_PROTOCOL`, `INSTRUCTIONS`×3, `REASONING_COMMIT_REQUIREMENT`; **self.workflow**: `binding_context`, `decision_protocol`, `knowledge`, `launch_instructions`, `native_event_information`, `permits_common_action`×3, `specialist` |
| `internal_summary.py` | 27 | Per-decision summary: assignment, progress facts, and the scientific parent's question and selected tool info when every request is a local protein-structure job. | **BindingContext fields**: `assignment`×2; **old-runner callbacks defined**: `decision_context`; **self.services**: `scientific_parent_task` |
| `parent_input_custody.py` | 67 | The per-resource request form (resource id and kind fixed, requested job alternatives), whether a resource is permitted by the assignment's constraints, validation of each request and of input versions. | **imports from old `root.a102`**: `execution_input_versions`, `native_protein_structure_tool_info`; **per-axis providers**: `self.api_execution`×3, `self._practical` |
| `received_record_selection.py` | 35 | Which received records count (handoffs matching one of its requests); same text as the results episode apart from names. | **BindingContext fields**: `assignment`, `role`, `scope`×2; **per-axis providers**: `self.api_execution`×2, `self.job_progress_provider` |
| `received_records.py` | 37 | Report facts the axis head or root may receive; same text as the results episode apart from base-class order. | **BindingContext fields**: `request`, `role`; **imports from old `root.a102`**: `protein_structure_result_views`; **old-runner callbacks defined**: `received_report_closure_facts`, `received_report_facts`, `received_report_sources`; **per-axis providers**: `self.local_file_sources`×2, `self.native_protein_structure_returns` |
| `received_reference_custody.py` | 35 | Resolution and validation of references received in typed forms; same text apart from names. | **BindingContext fields**: `role`; **old-runner callbacks defined**: `received_form_references`, `resolve_received_reference`, `validate_received_report`; **per-axis providers**: `self.local_file_sources`×3, `self.native_protein_structure_returns`×3 |
| `report_delivery.py` | 25 | Closure; same as the results episode. | **imports from old `root.a102`**: `library.private_policy_call`, `library.report_fact_assembly`, `runtime`×2; **old-runner callbacks defined**: `finish`; **old runtime**: `form_with_facts`, `_json`×2, `json`, `Record`×2; **self.workflow**: `binding_context`, `episode_bindings`, `facts`, `journal`×2, `pending_handles`, `release`×2, `source_credit_view`; **journal/receipt tables**: `runtime_forms`×2 |
| `report_reference_access.py` | 45 | Which references the report may cite; same text apart from names. | **BindingContext fields**: `role`, `scope`×4; **imports from old `root.a102`**: `episode_bindings`×2; **old-runner callbacks defined**: `resolve`; **per-axis providers**: `self.api_execution`×2, `self.job_progress_provider`×2, `self.local_file_sources`; **old support classes**: `PracticalReceiptInformation`×2 |
| `resource_information.py` | 82 | Resource description, capabilities and tool contracts with commission routes; same text apart from names. | **imports from old `root.a102`**: `native_protein_structure_tool_info`; **old-runner callbacks defined**: `capabilities`, `initial_decision_context`, `resource_tool_contracts`; **per-axis providers**: `self.api_execution`×4, `self.local_file_sources`, `self.tool_registry`×2 |
| `result_selection.py` | 75 | Result-side target and selector code carried in a launch episode; only `_selection` and `_context_target` (role `launch` branch) are its own. | **BindingContext fields**: `assignment`×3, `episode_id`×7, `role`×3, `scope`×3; **imports from old `root.a102`**: `episode_receipts`, `protein_structure_selection`; **per-axis providers**: `self.api_execution`, `self.job_progress_provider`, `self.local_file_sources`; **self.services**: `record_selection`; **old support classes**: `EpisodeReceipts`×2; **journal/receipt tables**: `runtime_actions`, `runtime_receipt_inheritance`×2 |
| `retained_protein_reader.py` | 94 | Protected protein-structure reference handling; same text apart from names. | **BindingContext fields**: `assignment`, `role`, `run_id`, `scope`; **imports from old `root.a102`**: `execution_contracts`, `native_protein_structure_results`, `native_protein_structure_returns`, `protein_structure_contracts`, `protein_structure_operands`, `protein_structure_selection`, `state`; **old-runner callbacks defined**: `retained_protein_structure_reader`; **per-axis providers**: `self.job_progress_provider`, `self.native_protein_structure_results`×2, `self.native_protein_structure_returns`×2; **old support classes**: `NativeProteinStructureResults`×2, `NativeProteinStructureReturns`×2; **journal/receipt tables**: `runtime_episodes` |
| `retained_result_acquisition.py` | 19 | Only the check that an operation key names a recorded tool action; the acquisition itself is absent here. | **journal/receipt tables**: `runtime_actions` |
| `retained_result_publication.py` | 53 | Result-body validation and reading; no publication (it publishes no result). | **per-axis providers**: `self.job_progress_provider`, `self.local_file_sources`; **journal/receipt tables**: `runtime_episodes` |
| `task.py` | 236 | The decision loop; unlike the results episode, a reasoning commit is admitted against the reasoning schema and an empty commit is refused unless the binding says it has task content; report grain name `launch`; attaches the HPC handoff return-contract validator. | **imports from old `root.a102`**: `episode_source_failure`, `library.action_contracts`, `library.hpc_handoff_report_contract`, `library.private_policy_call`, `providers`, `read_mapping`, `runtime`×2; **old binding attributes**: `hpc_handoff_report_validator`, `instruction_composer`; **old-runner callbacks defined**: `apply_response`, `execute`, `next`; **old runtime**: `AcquisitionError`×2, `ActionFailure`, `ContractError`, `ContractInformationError`, `_decode_recorded_action_response`, `Draft202012Validator`×3, `EventTargetError`×2, `inspect`, `_json`×5, `json`×8, `Mapping`×3, `nullcontext`×5, `observes_action_outcome`, `ReportBoundaryError`, `ReportRedelivery`×2, `schema_failure_diagnostic`, `SourceEnd`×2, `sqlite3`×2, `subprocess`×2, `validate_form`, `ValidationError`×3, `_wait_target_feedback`×2, `WorkflowError`×2; **self.workflow**: `action_schema`, `automatic_score_updates`, `binding_context`×2, `completed_unit`×3, `completions`×3, `controller_value`×2, `decision_exchanges`×3, `delivery_resolution_inputs`, `execute`, `execution_binding`×7, `inprocess_replay`×4, `journal`×7, `last_observed_credit`, `next_return`, `pending_work`, `perform_selected_wait`, `permits_common_action`, `reasoning_action_schema`, `receive_native_outcome`, `receive_outcome`, `resolve_pending_deliveries`, `resolver`, `retain_shared_grading_results`, `run_id`×3, `selected`×3, `source_credit_view`, `specialist`×2, `store`×9, `validate_report`; **journal/receipt tables**: `runtime_actions`×8, `runtime_episodes`, `runtime_model_calls`×2 |
| `task_decision.py` | 89 | The model call; same text apart from names. | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`×2, `structural_homology_evidence_prompt`×2; **old-runner callbacks defined**: `call`, `conversation_key`, `instructions`; **old provider interface**: `has_session`×3; **old runtime**: `_action_generation_schema`, `_ASSIGNMENT_TRANSPORT`, `DECISION_EXCHANGE_PROTOCOL`×5, `_digest`, `instructional_model_context`, `_json`×4, `json`×2, `_recorded_assignment_transport`, `WorkflowError`×5; **self.workflow**: `contract_information_profile`, `decision_exchanges`, `decision_protocol`×3, `freeze_contract_information`, `freeze_literature_numerical_contracts`, `history_preview`, `is_job_source`×2, `journal`, `numerical_contracts`, `provider`×2, `receipts`×4, `services`, `uses_received_record_context`×2, `validate_contract_information`×2; **journal/receipt tables**: `runtime_model_calls`×5; **old yield names**: `_category_yield_parameters`, `yield_table` |
| `task_state.py` | 108 | Per-episode decision state and restore/checkpoint; same text apart from names. | **imports from old `root.a102`**: `episode_source_failure`, `runtime`×2; **old-runner callbacks defined**: `bind_execution_context`, `checkpoint`, `record_effect`, `record_execution_failure`, `restore`, `restore_checkpoint`; **old runtime**: `ActionLeaf`, `EFFECT_VERSION`, `Episode`, `interpretation_schema`, `_json`×2, `json`×4, `_object`, `_plain`, `Record`; **self.workflow**: `archive`, `completions`×4, `context`, `controller_value`, `execution_binding`×4, `grains`, `inprocess_replay`×7, `journal`×5, `progress_provider`×2, `recover_commissions`, `run_id`, `source_credit_view`, `store`×2; **journal/receipt tables**: `runtime_actions`×5 |
| `terminal_execution.py` | 242 | Terminal behaviour for the `launch_local`/`launch_hpc` roles (`exec_command`, its instructions, receipts, completion); used here to build per-resource operations and validate requests. Byte-identical to the results episode's copy. | **BindingContext fields**: `assignment`×9, `episode_id`×4, `role`, `run_id`×5; **imports from old `root.a102`**: `acquisition`, `communication`, `domain`, `practical_execution_operations`, `practical_execution_records`, `practical_execution_state`, `practical_receipt_information`×3, `practical_yield`, `terminal_execution`, `terminal_scientific_evidence`×2; **old-runner callbacks defined**: `allowed_children`, `as_record`, `assignment_schema`, `catalog`, `child_roles`, `completion_for_action`, `credit_kind`, `credit_view`, `decision_context`, `execute`, `facts`, `fact_sources`, `initial_decision_context`, `initialize`, `instructions`, `permitted_common_actions`, `practical_estimator`, `prepare_assignment`, `resolve`, `validate_report`; **self.services**: `workflow`; **self.workflow**: `launch_instructions`; **old support classes**: `PracticalReceiptInformation`×6, `PracticalState`×2, `TerminalExecution`×2; **old yield names**: `PracticalYieldEstimator`×2 |
| `to_child_api_job_execution.py` | 34 | The request sent to a child: goal refined from its own, message with scope, initial report, job or episode assignment (launch instructions materialised), optional report-contract declaration, receipt inheritance. The three `to_child_*` files differ only in the docstring. | **imports from old `root.a102`**: `runtime`; **old runtime**: `ContractInformationError`, `Episode`×2, `EpisodeGoal`×2, `EpisodeRequest`, `_plain`×3, `Record`, `validate_saved_fact_form`; **self.workflow**: `context`×2, `grains`×2, `inprocess_completion_order`×2, `launch_instructions`, `receipts`×2 |
| `to_child_hpc_job_execution.py` | 34 | Same as the API request; docstring names `launch_hpc`. | **imports from old `root.a102`**: `runtime`; **old runtime**: `ContractInformationError`, `Episode`×2, `EpisodeGoal`×2, `EpisodeRequest`, `_plain`×3, `Record`, `validate_saved_fact_form`; **self.workflow**: `context`×2, `grains`×2, `inprocess_completion_order`×2, `launch_instructions`, `receipts`×2 |
| `to_child_local_job_execution.py` | 34 | Same as the API request; docstring names `launch_local`. | **imports from old `root.a102`**: `runtime`; **old runtime**: `ContractInformationError`, `Episode`×2, `EpisodeGoal`×2, `EpisodeRequest`, `_plain`×3, `Record`, `validate_saved_fact_form`; **self.workflow**: `context`×2, `grains`×2, `inprocess_completion_order`×2, `launch_instructions`, `receipts`×2 |
| `to_children.py` | 42 | Its three children (`launch_api`, `launch_local`, `launch_hpc`), which are allowed (a bound resource of that kind permitted by the assignment), and which receiver and request assembler each uses. | **BindingContext fields**: `assignment`, `role`; **old-runner callbacks defined**: `allowed_children`, `child_report_receiver`, `child_request_assembler`, `child_roles` |
| `to_parent.py` | 47 | The facts reported: handoff refs, result refs, result origin, `execution_completed` (a received handoff whose reader marks it complete); report must agree with recorded facts. | **BindingContext fields**: `scope`; **imports from old `root.a102`**: `local_file_capture_results`, `protein_structure_result_views`×2; **old-runner callbacks defined**: `facts`, `fact_sources`, `validate_report`; **per-axis providers**: `self.job_progress_provider`, `self.local_file_sources`×2, `self.native_protein_structure_results`×2, `self.native_protein_structure_returns`; **old support classes**: `PracticalReceiptInformation` |
| `waiting.py` | 9 | Records the suspension condition and passes it to the external executor. | **old-runner callbacks defined**: `suspension_changed`; **self.workflow**: `execution_backend`, `execution_handle`×2 |
| `yield_estimator.py` | 75 | Continuation: the class of each original request (API service/algorithm/database, or practical kind/native job/endpoint) selects profile `launch:<classes joined by +>`; a bounded controller whose maximum is handoff_unit times eligible requests not already handed off; exact zero forecast when none remain; the completion estimator on a verified handoff. | **BindingContext fields**: `assignment`, `role`, `scope`; **imports from old `root.a102`**: `numerical`, `practical_yield`; **old-runner callbacks defined**: `practical_estimator`, `yield_controller`; **per-axis providers**: `self.job_progress_provider`; **old yield names**: `BoundedYieldController`×2, `NumericBand`×2, `PracticalYieldEstimator`×2, `YieldController`×2, `YieldEstimate`×2, `YieldParameters`×3 |

## Carried over

The old files could not be read: this checkout has no git history (`git show 97308b94c:<path>` fails, "not a git repository"). Every row is classified from this record's own description of the old files and from `runs/carry_over/calls/a102_04.tsv`; no old body was read, so rows marked "reconstructed" were rebuilt from the description above. "unplaced" rows are listed in `carry_over_blocked/`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| `action_policy.py` | `LaunchActionPolicy` | episode function | task.py `offered`, `action` (under the HPC ancestors: tool and child only; the old `reason`, `wait`, `redeliver_report` are not offered) |
| `action_policy.py` | `LaunchActionPolicy.permitted_common_actions` | episode function | task.py `offered`, `action` (under the HPC ancestors: tool and child only; the old `reason`, `wait`, `redeliver_report` are not offered) |
| `api_operations.py` | `LaunchApiOperations` | episode function | task.py `execution_capabilities` (tool), `capabilities`, `TOOLS` |
| `api_operations.py` | `LaunchApiOperations.catalog` | episode function | task.py `execution_capabilities` (tool), `capabilities`, `TOOLS` |
| `api_operations.py` | `LaunchApiOperations.execute` | episode function | task.py `execution_capabilities` (tool), `capabilities`, `TOOLS` |
| `binding_record.py` | `LaunchBindingRecord` | machinery | binding's own as_record(): settings and declared services are journaled by the system (README 3e) |
| `binding_record.py` | `LaunchBindingRecord.as_record` | machinery | binding's own as_record(): settings and declared services are journaled by the system (README 3e) |
| `closed_credit.py` | `LaunchClosedCredit` | machinery | frozen closed credit view over old journal/receipt tables; `credit.py` is the credit and the system hands `completion['credit']` |
| `closed_credit.py` | `LaunchClosedCredit._closed_credit_carrier` | machinery | frozen closed credit view over old journal/receipt tables; `credit.py` is the credit and the system hands `completion['credit']` |
| `closed_credit.py` | `LaunchClosedCredit._closed_credit_receipts` | machinery | frozen closed credit view over old journal/receipt tables; `credit.py` is the credit and the system hands `completion['credit']` |
| `closed_credit.py` | `LaunchClosedCredit._closed_credit_value` | machinery | frozen closed credit view over old journal/receipt tables; `credit.py` is the credit and the system hands `completion['credit']` |
| `closed_credit.py` | `LaunchClosedCredit._closed_credit_facts` | machinery | frozen closed credit view over old journal/receipt tables; `credit.py` is the credit and the system hands `completion['credit']` |
| `closed_credit.py` | `LaunchClosedCredit._closed_operational_credit_view` | machinery | frozen closed credit view over old journal/receipt tables; `credit.py` is the credit and the system hands `completion['credit']` |
| `completion.py` | `LaunchCompletion` | machinery | completion proof `practical_completion_v1` and its verification as a controller input (README 3d, 7b): the bounded controller of `yield_estimator.py` stops the Episode; reads runtime_actions/observations |
| `completion.py` | `LaunchCompletion._proof_for_action` | machinery | completion proof `practical_completion_v1` and its verification as a controller input (README 3d, 7b): the bounded controller of `yield_estimator.py` stops the Episode; reads runtime_actions/observations |
| `completion.py` | `LaunchCompletion.completion_for_action` | machinery | completion proof `practical_completion_v1` and its verification as a controller input (README 3d, 7b): the bounded controller of `yield_estimator.py` stops the Episode; reads runtime_actions/observations |
| `completion.py` | `LaunchCompletion._closed_completion_verdict` | machinery | completion proof `practical_completion_v1` and its verification as a controller input (README 3d, 7b): the bounded controller of `yield_estimator.py` stops the Episode; reads runtime_actions/observations |
| `completion.py` | `LaunchCompletion.verify_completion` | machinery | completion proof `practical_completion_v1` and its verification as a controller input (README 3d, 7b): the bounded controller of `yield_estimator.py` stops the Episode; reads runtime_actions/observations |
| `configuration.py` | `LaunchConfiguration` | machinery | values the run sets: `ctx.settings` (`resources`, `initial_information`, `task_yield_profiles`, optional `launch_instruction_directory`); providers it built are deleted (README 3d, 3c) |
| `configuration.py` | `LaunchConfiguration.__init__` | machinery | values the run sets: `ctx.settings` (`resources`, `initial_information`, `task_yield_profiles`, optional `launch_instruction_directory`); providers it built are deleted (README 3d, 3c) |
| `credit.py` | `LaunchCredit` | episode function | credit.py `credit` |
| `credit.py` | `LaunchCredit.credit_kind` | machinery | `credit_kind` is deleted (README 3d) |
| `credit.py` | `LaunchCredit.project_credit` | episode function | credit.py `credit` |
| `credit.py` | `LaunchCredit._live_project_credit` | episode function | credit.py `credit` |
| `credit.py` | `LaunchCredit.credit_view` | episode function | messages/internal_summary.py `internal_summary` (progress facts) and credit.py `credit` |
| `decision_contracts.py` | `LaunchTaskDecisionContracts` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_contracts.py` | `LaunchTaskDecisionContracts.interpretation_context` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_contracts.py` | `LaunchTaskDecisionContracts.exchange_schema` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_contracts.py` | `LaunchTaskDecisionContracts.exchange_response` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_contracts.py` | `LaunchTaskDecisionContracts.validate_contract_exchange_request` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_contracts.py` | `LaunchTaskDecisionContracts.validate_contract_exchange_history` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_exchange.py` | `LaunchTaskDecisionExchange` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_exchange.py` | `LaunchTaskDecisionExchange.exchange_decision` | machinery | decision-exchange loop (README 3a): a lookup is a tool, the exchange is deleted |
| `decision_inputs.py` | `LaunchDecisionInputs` | episode function | task.py `decide` (context: assignment, progress, first-decision capabilities, `hpc_execution_job`); shared-information context, `requested_action_history` and execution expectations: see unplaced/BLOCKED-ON-JOB-SERVICE estimate_table |
| `decision_inputs.py` | `LaunchDecisionInputs.decision_inputs` | episode function | task.py `decide` (context: assignment, progress, first-decision capabilities, `hpc_execution_job`); shared-information context, `requested_action_history` and execution expectations: see unplaced/BLOCKED-ON-JOB-SERVICE estimate_table |
| `decision_provider.py` | `LaunchTaskDecisionProvider` | episode function | task.py `decide` (`ModelRequest`) and `selected_execution_task` (the selected-execution context; the old renderer lived in the shared root and is not read) |
| `decision_provider.py` | `LaunchTaskDecisionProvider.complete_decision` | episode function | task.py `decide` (`ModelRequest`) and `selected_execution_task` (the selected-execution context; the old renderer lived in the shared root and is not read) |
| `decision_state.py` | `LaunchDecisionState` | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` |
| `decision_state.py` | `LaunchDecisionState.decision_state` | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` |
| `episode.py` | `ExecutionEpisode` | episode function | episode.py `ExecutionJobSubmission` |
| `execution_contracts.py` | `launch_operation_catalog` | episode function | task.py `execution_capabilities`, `TOOLS`, `offered` |
| `execution_contracts.py` | `native_result_operation_catalog` | unplaced | results-side operation catalog / outcome shape (belongs to execution_result_acquisition) |
| `execution_contracts.py` | `_outcome` | unplaced | results-side operation catalog / outcome shape (belongs to execution_result_acquisition) |
| `execution_state.py` | `LaunchExecutionState` | episode function | messages/read_from_parent.py `read_from_parent` |
| `execution_state.py` | `LaunchExecutionState._delegate` | machinery | old per-axis provider delegation (README 3c) |
| `execution_state.py` | `LaunchExecutionState._practical_context` | machinery | old per-axis provider delegation (README 3c) |
| `execution_state.py` | `LaunchExecutionState.initialize` | episode function | messages/read_from_parent.py `read_from_parent` (admission of the launch assignment) |
| `execution_state.py` | `LaunchExecutionState._result_directory` | unplaced | results-side directory of retained results (belongs to execution_result_acquisition) |
| `from_child_api_job_execution.py` | `receive_report` | episode function | messages/read_from_child.py `read_from_child` (the receipt bookkeeping of the old receiver is the system's custody, README 3b R1, R3, R5) |
| `from_child_hpc_job_execution.py` | `receive_report` | episode function | messages/read_from_child.py `read_from_child` (the receipt bookkeeping of the old receiver is the system's custody, README 3b R1, R3, R5) |
| `from_child_local_job_execution.py` | `receive_report` | episode function | messages/read_from_child.py `read_from_child` (the receipt bookkeeping of the old receiver is the system's custody, README 3b R1, R3, R5) |
| `from_parent.py` | `LaunchFromParent` | episode function | messages/read_from_parent.py |
| `from_parent.py` | `LaunchFromParent.required_return_sources` | episode function | messages/final_to_parent.py `RETURN_FORM` (`execution_handoff_refs` is a selectable field) |
| `from_parent.py` | `LaunchFromParent.child_assignment_schema` | episode function | messages/msg_to_child.py `msg_to_child` (the parent writes the child's assignment) |
| `from_parent.py` | `LaunchFromParent.assignment_schema` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` |
| `from_parent.py` | `LaunchFromParent.prepare_assignment` | episode function | messages/read_from_parent.py `read_from_parent` |
| `from_parent.py` | `LaunchFromParent.initial_references` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` fields `input_refs` and `already_handed_off` (new fields); records held come from custody |
| `goal.py` | `LaunchGoal` | episode function | goal.py |
| `goal.py` | `LaunchGoal.instructions` | episode function | goal.py |
| `instructions.py` | `instructions` | episode function | task.py `INSTRUCTIONS`, `decide` |
| `internal_summary.py` | `LaunchInternalSummary` | episode function | messages/internal_summary.py `internal_summary` and task.py `selected_execution_task` |
| `internal_summary.py` | `LaunchInternalSummary._with_selected_execution_task` | episode function | messages/internal_summary.py `internal_summary` and task.py `selected_execution_task` |
| `internal_summary.py` | `LaunchInternalSummary.decision_context` | episode function | messages/internal_summary.py `internal_summary` and task.py `selected_execution_task` |
| `parent_input_custody.py` | `LaunchParentInputCustody` | episode function | messages/read_from_parent.py |
| `parent_input_custody.py` | `LaunchParentInputCustody._versions` | unplaced | validation of the immutable input versions through the old `execution_input_versions` module (no placed home; reads the Store); the versions ride in the assignment unchanged |
| `parent_input_custody.py` | `LaunchParentInputCustody._permitted` | episode function | messages/read_from_parent.py `permitted` (reconstructed from the intent record) |
| `parent_input_custody.py` | `LaunchParentInputCustody._request_schema` | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (`requests` list) and `read_from_parent` (practical requests through `validate_assignment`) |
| `parent_input_custody.py` | `LaunchParentInputCustody._validate_request` | episode function | messages/read_from_parent.py `read_from_parent` (practical requests: library `validate_assignment`); API-provider and native protein-structure input validation: unplaced |
| `parent_input_custody.py` | `LaunchParentInputCustody._launch` | unplaced | `authenticate_launch` against the HPC parent's ledger: reads the parent's own ledger (README 5 item 14); a wrong commission fails (rule 1) |
| `parent_input_custody.py` | `LaunchParentInputCustody._constraints` | episode function | messages/read_from_parent.py `permitted` |
| `received_record_selection.py` | `LaunchReceivedRecordSelection` | machinery | selection of received records by the old receipt tables: custody (README 3c, F2); `credit.py` asks `records.holds` |
| `received_record_selection.py` | `LaunchReceivedRecordSelection._received` | machinery | selection of received records by the old receipt tables: custody (README 3c, F2); `credit.py` asks `records.holds` |
| `received_records.py` | `LaunchReceivedRecords` | episode function | messages/final_to_parent.py `RETURN_FORM`, `facts` (the report facts the parent may select) |
| `received_records.py` | `LaunchReceivedRecords.received_report_sources` | episode function | messages/final_to_parent.py `RETURN_FORM`, `facts` (the report facts the parent may select) |
| `received_records.py` | `LaunchReceivedRecords.received_report_facts` | episode function | messages/final_to_parent.py `RETURN_FORM`, `facts` (the report facts the parent may select) |
| `received_records.py` | `LaunchReceivedRecords.received_report_closure_facts` | episode function | messages/final_to_parent.py `RETURN_FORM`, `facts` (the report facts the parent may select) |
| `received_reference_custody.py` | `LaunchReceivedReferenceCustody` | machinery | reference resolution and validation of received forms: custody (README 3b R1, R3, F4) |
| `received_reference_custody.py` | `LaunchReceivedReferenceCustody.resolve_received_reference` | machinery | reference resolution and validation of received forms: custody (README 3b R1, R3, F4) |
| `received_reference_custody.py` | `LaunchReceivedReferenceCustody.validate_received_report` | machinery | reference resolution and validation of received forms: custody (README 3b R1, R3, F4) |
| `received_reference_custody.py` | `LaunchReceivedReferenceCustody.received_form_references` | machinery | reference resolution and validation of received forms: custody (README 3b R1, R3, F4) |
| `report_delivery.py` | `LaunchReportDelivery` | machinery | saving and releasing the report form (README 3b D1, D3): the result is `final_to_parent` |
| `report_delivery.py` | `LaunchReportDelivery.finish` | machinery | saving and releasing the report form (README 3b D1, D3): the result is `final_to_parent` |
| `report_reference_access.py` | `LaunchReportReferenceAccess` | machinery | resolver of references a report may cite: custody (README 3b D2) |
| `report_reference_access.py` | `LaunchReportReferenceAccess.resolve` | machinery | resolver of references a report may cite: custody (README 3b D2) |
| `resource_information.py` | `LaunchResourceInformation` | episode function | task.py `capabilities` |
| `resource_information.py` | `LaunchResourceInformation._resource_information` | episode function | task.py `capabilities` |
| `resource_information.py` | `LaunchResourceInformation.initial_decision_context` | episode function | task.py `decide` (first decision) |
| `resource_information.py` | `LaunchResourceInformation.capabilities` | episode function | task.py `capabilities`, `execution_capabilities` |
| `resource_information.py` | `LaunchResourceInformation.resource_tool_contracts` | unplaced | commissionable launch/results operation contracts per resource (API operation catalog, native protein-structure tool contracts through `protein_structure_tool_contracts`); the parent writes its own text over its own slots; API catalog has no placed home |
| `result_selection.py` | `LaunchResultSelection` | unplaced | results-side target, selector and window code carried in a launch copy (belongs to execution_result_acquisition) |
| `result_selection.py` | `LaunchResultSelection._target` | unplaced | results-side target, selector and window code carried in a launch copy (belongs to execution_result_acquisition) |
| `result_selection.py` | `LaunchResultSelection._selector` | unplaced | results-side target, selector and window code carried in a launch copy (belongs to execution_result_acquisition) |
| `result_selection.py` | `LaunchResultSelection._windows` | unplaced | results-side target, selector and window code carried in a launch copy (belongs to execution_result_acquisition) |
| `result_selection.py` | `LaunchResultSelection._selection` | machinery | reads runtime_actions and receipt-inheritance tables to select received records: custody (README 3c, F2) |
| `result_selection.py` | `LaunchResultSelection._context_target` | machinery | reads runtime_actions and receipt-inheritance tables to select received records: custody (README 3c, F2) |
| `retained_protein_reader.py` | `LaunchRetainedProteinReader` | unplaced | protein-structure result custody of the results side (belongs to execution_result_acquisition) |
| `retained_protein_reader.py` | `LaunchRetainedProteinReader.retained_protein_structure_reader` | unplaced | protein-structure result custody of the results side (belongs to execution_result_acquisition) |
| `retained_protein_reader.py` | `LaunchRetainedProteinReader._protein_reference_access` | unplaced | protein-structure result custody of the results side (belongs to execution_result_acquisition) |
| `retained_protein_reader.py` | `LaunchRetainedProteinReader._retained_protein_result` | unplaced | protein-structure result custody of the results side (belongs to execution_result_acquisition) |
| `retained_result_acquisition.py` | `LaunchRetainedResultAcquisition` | machinery | check that an operation key names a recorded tool action: the system's attempts journal |
| `retained_result_acquisition.py` | `LaunchRetainedResultAcquisition._selected_result_action` | machinery | check that an operation key names a recorded tool action: the system's attempts journal |
| `retained_result_publication.py` | `LaunchRetainedResultPublication` | unplaced | results-side result-body validation and reading (belongs to execution_result_acquisition) |
| `retained_result_publication.py` | `LaunchRetainedResultPublication._validate_result_body` | unplaced | results-side result-body validation and reading (belongs to execution_result_acquisition) |
| `retained_result_publication.py` | `LaunchRetainedResultPublication._read_result` | unplaced | results-side result-body validation and reading (belongs to execution_result_acquisition) |
| `task.py` | `LaunchTask` | episode function | task.py |
| `task.py` | `LaunchTask.next` | episode function | task.py `decide` |
| `task.py` | `LaunchTask.apply_response` | episode function | task.py `action` (reasoning-commit admission and empty-commit refusal are not carried: `reason` is not offered under the HPC ancestors) |
| `task.py` | `LaunchTask.execute` | machinery | the loop executes the unit; the `tool` branch is `execution_capabilities`, the `child` branch is `ChildCall`; `wait`, `redeliver_report` are gone |
| `task_decision.py` | `LaunchTaskDecision` | episode function | task.py `decide` |
| `task_decision.py` | `LaunchTaskDecision.call` | episode function | task.py `decide` |
| `task_decision.py` | `LaunchTaskDecision.instructions` | episode function | task.py `INSTRUCTIONS` |
| `task_decision.py` | `LaunchTaskDecision.conversation_key` | machinery | conversation state (README 3a): every `ModelRequest` carries the full context |
| `task_state.py` | `LaunchTaskState` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `task_state.py` | `LaunchTaskState.__init__` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `task_state.py` | `LaunchTaskState.bind_execution_context` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `task_state.py` | `LaunchTaskState.record_execution_failure` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `task_state.py` | `LaunchTaskState.restore_checkpoint` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `task_state.py` | `LaunchTaskState.restore` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `task_state.py` | `LaunchTaskState.record_effect` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `task_state.py` | `LaunchTaskState.checkpoint` | machinery | per-episode decision state, restore and checkpoint (README 3e): the view and the journal |
| `terminal_execution.py` | `operation_catalog` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.__init__` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior._operations` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior._assignment` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior._state_directory` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.initialize` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.state` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.as_record` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.child_roles` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.credit_kind` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.assignment_schema` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.permitted_common_actions` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.allowed_children` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.prepare_assignment` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.initial_decision_context` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior._resource_information` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior._resource_instructions` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.instructions` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.decision_context` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.catalog` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.execute` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.completion_for_action` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.practical_estimator` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.fact_sources` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.facts` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.resolve` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `terminal_execution.py` | `TerminalExecutionBehavior.validate_report` | unplaced | ('episode function', 'messages/final_to_parent.py `validate_report`') |
| `terminal_execution.py` | `TerminalExecutionBehavior.credit_view` | unplaced | terminal behaviour of the `launch_local`/`launch_hpc` children (`exec_command`, receipts, completion): carried by local_job_execution and hpc_job_execution; the one own method `validate_report` is messages/final_to_parent.py `validate_report` |
| `to_child_api_job_execution.py` | `assemble_request` | episode function | messages/msg_to_child.py `msg_to_child` (report-contract declaration and receipt inheritance are old-runner machinery) |
| `to_child_hpc_job_execution.py` | `assemble_request` | episode function | messages/msg_to_child.py `msg_to_child` (report-contract declaration and receipt inheritance are old-runner machinery) |
| `to_child_local_job_execution.py` | `assemble_request` | episode function | messages/msg_to_child.py `msg_to_child` (report-contract declaration and receipt inheritance are old-runner machinery) |
| `to_children.py` | `LaunchToChildren` | episode function | task.py `CHILD_SLOTS` |
| `to_children.py` | `LaunchToChildren.child_roles` | episode function | task.py `CHILD_SLOTS` |
| `to_children.py` | `LaunchToChildren.allowed_children` | episode function | task.py `offered` (permitted resources) and `CHILD_SLOTS` |
| `to_children.py` | `LaunchToChildren.child_report_receiver` | episode function | messages/read_from_child.py `read_from_child` |
| `to_children.py` | `LaunchToChildren.child_request_assembler` | episode function | messages/msg_to_child.py `msg_to_child` |
| `to_parent.py` | `LaunchToParent` | episode function | messages/final_to_parent.py |
| `to_parent.py` | `LaunchToParent.fact_sources` | episode function | messages/final_to_parent.py `RETURN_FORM` |
| `to_parent.py` | `LaunchToParent.facts` | episode function | messages/final_to_parent.py `facts` |
| `to_parent.py` | `LaunchToParent._live_facts` | episode function | messages/final_to_parent.py `facts` |
| `to_parent.py` | `LaunchToParent.validate_report` | episode function | messages/final_to_parent.py `validate_report` |
| `waiting.py` | `LaunchWaiting` | machinery | wait/suspension machinery (README 3b) |
| `waiting.py` | `LaunchWaiting.suspension_changed` | machinery | wait/suspension machinery (README 3b) |
| `yield_estimator.py` | `ExecutionEpisodeYield` | episode function | yield_estimator.py |
| `yield_estimator.py` | `ExecutionEpisodeYield._request_yield_class` | episode function | messages/read_from_parent.py `request_yield_class` |
| `yield_estimator.py` | `ExecutionEpisodeYield._task_yield_profile` | episode function | yield_estimator.py `yield_controller` (profile `launch:<classes>`) |
| `yield_estimator.py` | `ExecutionEpisodeYield.yield_controller` | episode function | yield_estimator.py `yield_controller` |
| `yield_estimator.py` | `ExecutionEpisodeYield._launch_yield_controller` | episode function | yield_estimator.py `yield_controller` (BoundedQualityYieldController) |
| `yield_estimator.py` | `ExecutionEpisodeYield.practical_estimator` | machinery | completion estimator keyed on the completion proof: not a controller input (README 5 item 5, 7b) |
