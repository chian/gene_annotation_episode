# Episode intent: `a102/structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`

Source: this episode's own files at commit `97308b94c` (41 Python files, 2,486 lines, directly in the folder; it has
no `tests/`, `grading/` or `scoring/` folder). Old role name: `results`. Old class: `ExecutionEpisode`, task class
`ResultsTask`. Old `binding_path`:
`structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`; old
`commissioning_parent`: `structural_homology_evidence/hpc_work_planning/hpc_allocation_execution` (the HPC
allocation that launched the work, not `hpc_work_planning` directly).

This folder is a second copy of `hpc_work_planning/execution_result_acquisition`: by blob, 38 of its 41 files are
identical to that copy, and the other three (`binding_record.py`, `episode.py`, `execution_contracts.py`) differ only
in this episode's own binding path, commissioning parent and the absolute import of its own `terminal_execution`.
Every statement below was checked against this folder's own files; it therefore reads the same as the intent of the
`hpc_work_planning` copy, with this episode's identity.

## What this episode is for

It acquires the results of one already handed-off execution, through that handoff, and returns the acquired
records. Its goal text, verbatim from `goal.py`:

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the
> current resource filesystem: the exact attempt observation does not establish that current file bytes were
> produced by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets
> the returned records. Original work, resource and selector stay fixed. Only actual complete acquisition
> establishes this endpoint.

## Task and instructions

One unit is one model-selected action: a tool call, or a wait when the target is an API service. The task file also
carries a reasoning-commit branch, but the action policy never permits `reason` for this episode. It commissions no
children.

Instructions (`instructions.py`): the goal text; the reasoning-commit requirement only if reasoning were permitted;
tool-knowledge and launch-instruction library text when present; the report-repair paragraph; the wait and
native-event paragraphs when wait is permitted; the exchange-history wording under the exchange protocol. The
episode supplies its whole instructions (`replaces_default_instructions = True`).

## What it reads from its parent's assignment

Form `execution_results_assignment_v1` (`execution_contracts.py`):

| Field | Meaning |
|---|---|
| `handoff_ref` | The original execution handoff; the target (resource, attempt, workspace) is read through it |
| `selector` | What to acquire. One of: native paths (`paths`, or one `path` with `offset`/`limit`); `local_file_source_selector_v1` (files); `protein_structure_result_selector_v1` (when a resource has native protein-structure jobs); an API service result selector |

Admission checks (`from_parent.py`, `result_selection.py`): native paths must lie inside the target's workspace;
`offset`/`limit` need a single `path`; a path may not be named twice; a protein-structure selector needs a
protein-structure target and its selected inputs are validated; an identical commission that already returned is
restored instead of run again (`saved_result_commission.py`). The work, the resource and the selector stay fixed
for the whole episode.

## Children

None (`child_commissioning.py` returns no roles).

## Decision state and what the model sees

State kept per episode: as the other task files (call count, last outcome, feedback, report values and basis).

Shown at each decision: the common decision fields (goal, scope, working state, visible records, credit, credit
rule, elapsed-time view, pending work, last outcome, feedback, deliveries, controller state, tools, report facts,
requested form) plus `internal_summary.py`: the assignment; progress facts so far; the execution target; the target
description (status operations, acquisition operations, provenance); and, for a local protein-structure job, a
`selected_execution_task_v1` record carrying the scientific parent's question and selected tool info. At the first
decision it also sees the resource capabilities and recorded inventory (`resource_information.py`).

The prompt renderer for selected-execution contexts is used only when the context is not HPC, not
published-scientific and not an API launch (`decision_provider.py`).

## Tools

| Target kind | Tools |
|---|---|
| Native local or PBS | `execution.results.status` (observe the exact handed-off attempt once); `execution.results.collect` (observe the attempt and acquire bounded first windows of the requested paths); `execution.results.read` (one selected byte window: `path`, `offset`, `limit` up to 1 MiB, inside the requested paths and interval) |
| API service | The API execution provider's result operations |
| Protein-structure result | The protein-structure result operations |
| Local file source selector | Routed to the local file capture provider |

Each native acquisition keeps intent, observation, window and receipt as immutable files under
`execution-results/<digest of run and episode>/` and publishes the result as a Store source with provider
`episode.execution_result`. Once the assignment is complete, further acquisition is refused
(`execution_results_assignment_already_completed`).

## Credit

Credit kind `operational`. For native path selectors: `acquired_record_unit` times the fraction of requested byte
positions newly covered, where coverage is the union of acquired windows (read boundaries do not matter), positions
already known at the start are excluded, and the fraction is averaged over the requested paths (rule
`execution_received_selector_coverage_credit_v2`). For file-source selectors: `acquired_record_unit` times the count
of newly acquired files (`execution_received_records_credit_v1`). Handoffs earn nothing in this episode (the
handoff count is fixed at 0). API and protein-structure targets take their credit view from their providers.

At closure the credit view is frozen with digests of context, binding, completion, archive, history and receipt
prefix, and later reads return only that frozen view (`closed_credit.py`).

## Continuation

Chosen by selector kind (`yield_estimator.py`); every profile is `{cutoff > 0, parameters}`:

| Case | Profile key | Estimator |
|---|---|---|
| Native selector with at least one path of no fixed length | `native_unbounded_local` or `native_unbounded_hpc` (in `results_yield_profiles`) | Old default `YieldController` estimate (which of the three it was is not visible from this folder) |
| Native selector, all intervals finite | `results:native_finite_<kind>` (in `task_yield_profiles`) | **bounded quality**: maximum = `acquired_record_unit` × (1 − fraction already known at start); exact zero forecast when nothing remains; switches to **completion with a target** once a completion proof is verified |
| API target | `results:api_<service>[_<selector version>]` | **completion with a target** (verified completion proof) |
| Typed selector on local/PBS | `results:typed_<kind>_<selector version>` | **completion with a target** |

The completion target (`completion.py`): a successful exact attempt was observed (state `completed`, return code 0)
and, for every requested path, the acquired windows cover the requested interval from its start without gaps.
Without a configured private yield the old code raises `execution_private_yield_binding_not_enabled`.

## What it reports to its parent

The parent's typed form, built once at closure. Facts it can fill: `execution_handoff_refs`,
`execution_result_refs` (results that carry windows), `execution_file_source_refs`,
`execution_file_capture_outcomes`, the protein-structure facts, `execution_result_origin`
(`current_resource_filesystem`, attempt output version `unverified`, separate reads without an atomic snapshot) and
`execution_completed`. A report field declared from a fact must equal it. When the axis head is the parent and
requires it, the return must carry `execution_result_refs`.

## Differences from similar episodes

- Against `hpc_work_planning/execution_result_acquisition`: only the identity differs (binding id in
  `binding_record.py`, `binding_path` and `commissioning_parent` in `episode.py`, the absolute import path of
  `terminal_execution` in `execution_contracts.py`). The goal, assignment form, tools, credit, completion, continuation
  profiles and report facts are the same text. What makes it a distinct episode is only its place: it is
  commissioned by the allocation episode `hpc_allocation_execution` after that allocation launched the work, whereas
  the other copy is commissioned by `hpc_work_planning`. Nothing in this folder tunes it differently yet.
- Against its sibling `hpc_allocation_execution/execution_job_submission` (same parent, same file layout): the texts
  that carry real difference are `goal.py`, `credit.py` (byte coverage here; handoff count there), `completion.py`
  (covered intervals here; a received usable handoff there), `yield_estimator.py`, `from_parent.py`,
  `action_policy.py`, `internal_summary.py`, `to_parent.py`, `execution_state.py`, `retained_result_acquisition.py`
  and `retained_result_publication.py`. `terminal_execution.py` is byte-identical in all three folders
  (blob `6d03b74`).
- Files only in the results copies: `acquisition_operations.py`, `child_commissioning.py`, `report_fields.py`,
  `saved_result_commission.py`.
- It carries launch-side text it does not use as a results episode: `parent_input_custody.py` (`_launch`,
  `_validate_request`), the `launch` and `launch_*` role branches in `from_parent.initial_references`,
  `result_selection._context_target` and `report_reference_access.resolve`, and the whole of
  `terminal_execution.py` apart from building per-resource operations.

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
| `domain` | 2 | episode_support/records/structural_homology_evidence/domain.py |
| `episode_bindings` | 1 | the deleted old per-axis binding table |
| `episode_receipts` | 3 | no structural_homology_evidence copy found (copies exist for two other axes under episode_support/records/AXIS/) |
| `episode_return_records` | 3 | no placed home found |
| `episode_source_failure` | 2 | no placed home found |
| `episode_work_report` | 1 | no placed home found |
| `execution_contracts` | 2 | episode_support/forms/structural_homology_evidence/execution_contracts.py |
| `execution_progress` | 1 | no placed home found |
| `execution_prompt` | 4 | no placed home found |
| `launch_instructions` | 1 | episode_support/instructions/launch_instructions.py |
| `library.action_contracts` | 1 | no placed home found |
| `library.hpc_prompt` | 5 | no placed home found |
| `library.private_policy_call` | 2 | no placed home found |
| `library.report_fact_assembly` | 1 | no placed home found |
| `local_file_capture_results` | 3 | episode_support/records/local_execution/local_file_capture_results.py |
| `method_loop.identities` | 1 | top-level method_loop/identities.py (the only method_loop) |
| `native_file_capture` | 1 | episode_support/records/local_execution/structural_homology_evidence/native_file_capture.py |
| `native_protein_structure_acquisition` | 1 | episode_support/acquisition/protein_structure/native_protein_structure_acquisition.py |
| `native_protein_structure_results` | 3 | no placed home found |
| `native_protein_structure_returns` | 2 | no placed home found |
| `native_protein_structure_tool_info` | 1 | episode_support/tools/protein_structure/native_protein_structure_tool_info.py |
| `numerical` | 3 | old yield code; its names NumericBand, YieldParameters, YieldEstimate, estimate_nonnegative_yield, estimate_bounded_credit_yield are now in top-level yield_control; YieldController/BoundedYieldController are not (controllers there are Accumulation/BoundedQuality/Completion) |
| `practical_execution_operations` | 2 | episode_support/jobs/structural_homology_evidence/practical_execution_operations.py |
| `practical_execution_records` | 2 | episode_support/records/structural_homology_evidence/practical_execution_records.py |
| `practical_execution_state` | 2 | episode_support/jobs/structural_homology_evidence/practical_execution_state.py |
| `practical_receipt_information` | 2 | episode_support/records/practical_receipt_information.py |
| `practical_yield` | 3 | no placed home found; completion with a target is yield_control.CompletionYieldEstimator |
| `protein_structure_contracts` | 1 | episode_support/forms/protein_structure/structural_homology_evidence/protein_structure_contracts.py |
| `protein_structure_execution_information` | 1 | no placed home found |
| `protein_structure_operands` | 2 | episode_support/readers/protein_structure/protein_structure_operands.py |
| `protein_structure_result_views` | 3 | episode_support/readers/protein_structure/structural_homology_evidence/protein_structure_result_views.py |
| `protein_structure_selection` | 3 | episode_support/readers/protein_structure/protein_structure_selection.py |
| `providers` | 1 | gene_annotation_episode/model_provider.py (defines ModelCallError) |
| `read_mapping` | 1 | episode_support/readers/sequence_alignment/structural_homology_evidence/read_mapping.py |
| `resource_records` | 1 | episode_support/records/hpc/resource_records.py |
| `runtime` | 9 | the deleted old per-axis runner |
| `runtime_prompt` | 1 | episode_support/instructions/structural_homology_evidence/runtime_prompt.py |
| `state` | 1 | gene_annotation_episode/state.py (the shared Store) |
| `structural_homology_evidence_prompt` | 5 | no placed home found |
| `terminal_execution` | 1 | episode_support/jobs/local_execution/structural_homology_evidence/terminal_execution.py |
| `terminal_scientific_evidence` | 1 | episode_support/findings/structural_homology_evidence/terminal_scientific_evidence.py |

## File by file

Counts are occurrences in the file text. `self.workflow` also covers `source.workflow`, a `workflow` argument and
`getattr(self.workflow…, '<name>')`; "BindingContext fields" are attribute reads on the old context object
(`context`, `parent`, `child`); "old-runner callbacks defined" are methods the old runner called on the binding or
task. The same rows, one per name and file, are in `runs/carry_over/calls/a102_06.tsv` (575 rows, 937 uses in this
episode).

| Old file | Lines | This episode's own intent in it | Old-runner names used (name×uses) |
|---|---|---|---|
| `__init__.py` | 0 | Nothing (package marker). | none |
| `acquisition_operations.py` | 37 | Which tools are offered and how a call is routed: protein-structure result tools, API result tools, or the three native tools (`execution.results.status`, `.collect`, `.read`); local file sources and protein-structure results take precedence; argument errors become an `invalid` outcome. | **BindingContext fields**: `assignment`×3; **imports from old `root.a102`**: `native_file_capture`, `native_protein_structure_results`; **old-runner callbacks defined**: `catalog`, `execute`; **per-axis providers**: `self.api_execution`×2, `self.local_file_sources`×3, `self.native_protein_structure_results`×3 |
| `action_policy.py` | 13 | Permitted actions: `tool` only; `tool` and `wait` for an API service target (`api_service_assignment_v1`). | **old-runner callbacks defined**: `permitted_common_actions`; **per-axis providers**: `self.native_protein_structure_results` |
| `binding_record.py` | 8 | Its configuration record: resources, initial information, the two credit units, log window and roles, yield profiles. | **old-runner callbacks defined**: `as_record` |
| `child_commissioning.py` | 11 | It commissions no children (leaf). | **old-runner callbacks defined**: `allowed_children`, `child_roles` |
| `closed_credit.py` | 116 | Freezing the credit view at closure and re-reading only that frozen view afterwards, with digests of context, binding, completion, archive, history and receipt prefix. Almost entirely old journal/receipt custody. | **BindingContext fields**: `as_record`×2, `episode_id`×8, `role`; **imports from old `root.a102`**: `episode_receipts`, `episode_return_records`×3; **old support classes**: `EpisodeReceipts`×2, `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_episodes`×2, `runtime_forms`×3, `runtime_observations`, `runtime_receipt_inheritance`×2, `runtime_record_receipts`×2 |
| `completion.py` | 116 | When the acquisition is complete: a successful exact attempt was observed and every requested byte interval of every requested path is covered without gaps; the completion proof (`practical_completion_v1`, endpoint `usable_handoff`) and its verification. | **BindingContext fields**: `assignment`×4, `episode_id`×8, `run_id`×4, `scope`; **imports from old `root.a102`**: `episode_return_records`, `method_loop.identities`, `numerical`, `practical_yield`; **old-runner callbacks defined**: `completion_for_action`, `verify_completion`; **per-axis providers**: `self.api_execution`×2, `self.local_file_sources`×3, `self.native_protein_structure_results`×7; **journal/receipt tables**: `runtime_actions`×2, `runtime_observations`; **old yield names**: `ESTIMATOR_VERSION`×2, `NumericBand`×2 |
| `configuration.py` | 61 | Settings and checks: resources (local, pbs_ssh, api), initial inventory, `handoff_unit` and `acquired_record_unit` (> 0), log window bytes and log roles, `results_yield_profiles` (only `native_unbounded_local` / `native_unbounded_hpc`), `task_yield_profiles` (each {cutoff > 0, parameters}); builds the per-resource providers. | **imports from old `root.a102`**: `api_service_execution`, `execution_progress`, `native_protein_structure_results`, `native_protein_structure_returns`, `numerical`; **per-axis providers**: `self.api_execution`×2, `self.job_progress_provider`, `self.local_file_sources`, `self.native_protein_structure_results`, `self.native_protein_structure_returns`, `self._practical`×2, `self.tool_registry`; **old support classes**: `APIServiceExecution`×2, `ExecutionProgressProvider`×2, `LocalFileSourceResults`×2, `NativeProteinStructureResults`×2, `NativeProteinStructureReturns`×2; **old yield names**: `YieldController`×3, `YieldParameters`×3 |
| `credit.py` | 65 | Credit kind `operational`. Credit = acquired_record_unit times the fraction of requested byte positions newly covered (union of windows, positions already known at the start excluded), averaged over requested paths; for file-source selectors, acquired_record_unit times the count of newly acquired files. Handoffs earn nothing here (handoff_count fixed at 0). | **BindingContext fields**: `assignment`; **old-runner callbacks defined**: `credit_kind`, `credit_view`, `project_credit`; **per-axis providers**: `self.api_execution`, `self.job_progress_provider`, `self.local_file_sources`, `self.native_protein_structure_results`×2 |
| `decision_contracts.py` | 127 | Nothing of its own (exchange envelope and saved-exchange validation; same text as launch). | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`×2, `structural_homology_evidence_prompt`; **old-runner callbacks defined**: `exchange_response`, `exchange_schema`, `interpretation_context`, `validate_contract_exchange_history`, `validate_contract_exchange_request`; **old runtime**: `apply_state_frame`, `composition_lookup_schema`×2, `CONTRACT_INFORMATION_OPERATIONS`, `DECISION_CONTEXT_VERSION`, `Draft202012Validator`, `instructional_model_context`, `is_contract_information`, `_json`×8, `json`, `Mapping`×2, `model_snapshot`, `_object`×3, `_recorded_action_generation_schema`, `_references_in`, `requested_contract_information`, `ValidationError`, `WorkflowError`×9; **self.workflow**: `contract_information_reply`, `decision_exchanges`×2, `journal`, `store`×2, `store.reference_subset`, `validate_contract_information`×2; **journal/receipt tables**: `runtime_model_calls`; **old yield names**: `_category_yield_parameters`, `yield_table` |
| `decision_exchange.py` | 107 | Nothing of its own (request_context/select_action exchange loop). | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`×2, `structural_homology_evidence_prompt`; **old-runner callbacks defined**: `exchange_decision`; **old runtime**: `_action_generation_schema`, `_category_yield_parameters`, `child_option_information`, `DECISION_CONTEXT_VERSION`, `instructional_model_context`×2, `_json`×2, `lookup_attempts`, `Mapping`, `model_snapshot`, `_plain`×2, `requested_contract_information`, `schema_failure_diagnostic`×2, `sqlite3`, `state_frame`, `ValidationError`×4, `yield_table`; **self.workflow**: `controller_binding`, `decision_exchanges`, `execute`, `journal`, `run_id`, `services`, `validate_contract_information`; **journal/receipt tables**: `runtime_model_calls`×2; **old yield names**: `_category_yield_parameters`×2, `yield_table`×2 |
| `decision_inputs.py` | 58 | Additions to each decision: resource context, shared-information context, launch-instruction library, child options, completed-action reports, `requested_action_history` in an HPC context, pending work, execution expectations for role `results`, resource estimates (job-source aware), waiting support. | **imports from old `root.a102`**: `episode_work_report`×2, `library.hpc_prompt`, `runtime`×2; **old-runner callbacks defined**: `decision_inputs`; **old runtime**: `child_option_information`, `Mapping`; **self.workflow**: `available_child_roles`, `binding_context`, `episode_bindings`, `execution_expectations`, `is_job_source`, `job_episodes`×2, `launch_instructions`×2, `native_estimation_context`, `pending_work`, `permits_common_action`, `resource_context`, `resource_estimator`×5, `shared_information_context`, `waiting_support` |
| `decision_provider.py` | 19 | Uses the selected-execution prompt renderer only for a selected execution context that is not HPC, not published-scientific and not API launch. | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`, `structural_homology_evidence_prompt`; **old-runner callbacks defined**: `complete_decision`; **old provider interface**: `complete_with_presentation`, `prompt_renderer`; **self.workflow**: `provider`, `specialist`; **old yield names**: `_category_yield_parameters`, `yield_table` |
| `decision_state.py` | 45 | What the model is shown: the same fields as the monitor; the `monitoring_information_credit` branch is present but is not a results concern. | **imports from old `root.a102`**: `runtime`×2; **old-runner callbacks defined**: `decision_state`; **old runtime**: `FACT_MEANINGS`, `FACT_SOURCES`, `json`×2, `Mapping`×3, `_plain`×2, `_references_in`; **self.workflow**: `binding_context`, `catalog`, `controller_binding`, `delivery_status`, `extra_report_sources`, `is_scientific_source`, `job_episode_options`, `journal`×3, `knowledge`, `local_outcome_preview`, `pending_work`, `receipt_projection`, `run_id`, `source_credit_binding`, `source_credit_view`, `specialist`, `store`×3, `store.reference_subset`, `tools`, `tools.model_contract_catalog`, `working_state`; **journal/receipt tables**: `runtime_actions`×2 |
| `episode.py` | 38 | The binding: path `structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`, parent `hpc_work_planning/hpc_allocation_execution`, role `results`, no entry role, supplies its whole instructions, selected-execution prompt renderer. | **imports from old `root.a102`**: `structural_homology_evidence_prompt`; **old binding attributes**: `binding_path`, `commissioning_parent`, `decision_prompt_renderer`, `decision_source_type`, `entry_roles`, `replaces_default_instructions`, `roles` |
| `execution_contracts.py` | 47 | Its forms and constants: `execution_results_assignment_v1` (handoff_ref, selector), native selector (paths, or path with offset/limit), the three native tools, the acquisition-origin statement (current filesystem, attempt output version unverified, separate reads are not an atomic snapshot), outcome shape. | **absolute imports inside the episode tree**: `hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.terminal_execution`; **imports from old `root.a102`**: `a102_execution_bindings`, `communication`, `domain`, `execution_contracts`, `launch_instructions`, `local_file_capture_results`, `native_protein_structure_acquisition`, `practical_execution_operations`, `practical_execution_records`, `practical_execution_state`, `practical_receipt_information`, `resource_records`; **old support classes**: `LocalFileSourceResults`, `PracticalReceiptInformation` |
| `execution_state.py` | 39 | Start-up: admit the selector against the target, check protein-structure inputs, create the immutable result directory `execution-results/<digest>` with `assignment.json`. | **BindingContext fields**: `assignment`×4, `episode_id`×2, `role`, `run_id`×2, `scope`; **old-runner callbacks defined**: `initialize`; **per-axis providers**: `self.api_execution`×2, `self.local_file_sources`×2, `self._practical` |
| `from_parent.py` | 57 | Admission of the parent's assignment: results form with selector variants (local file source, protein-structure result), reuse of an already returned identical commission, target lookup through the handoff, file-source admission, protein-structure input checks; return source `execution_result_refs` when the axis head requires it. | **BindingContext fields**: `assignment`×2, `path`, `role`×5; **imports from old `root.a102`**: `protein_structure_operands`×3, `protein_structure_selection`; **old-runner callbacks defined**: `assignment_schema`, `child_assignment_schema`, `initial_references`, `prepare_assignment`, `required_return_sources`; **per-axis providers**: `self.job_progress_provider`, `self.local_file_sources`, `self.native_protein_structure_results`, `self.native_protein_structure_returns`×3; **self.services**: `annotation_task_required` |
| `goal.py` | 9 | The goal text (acquire the selected results through the original handoff; bounded status or file/page reads; keep partial bytes and native scores; only actual complete acquisition is the endpoint). | **old-runner callbacks defined**: `instructions` |
| `instructions.py` | 23 | Instruction text: goal, reasoning-commit requirement when allowed, tool knowledge, launch instructions, report-repair, wait and native-event guidance, exchange-history wording. | **imports from old `root.a102`**: `runtime_prompt`×2; **old-runner callbacks defined**: `instructions`; **old runtime_prompt**: `DECISION_EXCHANGE_PROTOCOL`, `INSTRUCTIONS`×3, `REASONING_COMMIT_REQUIREMENT`; **self.workflow**: `binding_context`, `decision_protocol`, `knowledge`, `launch_instructions`, `native_event_information`, `permits_common_action`×3, `specialist` |
| `internal_summary.py` | 40 | Per-decision summary: assignment, progress facts, target and target description (file sources, retained protein result or handoff target), and the scientific parent's question and selected tool info when the job is a local protein-structure job. | **BindingContext fields**: `assignment`×3, `scope`×2; **imports from old `root.a102`**: `local_file_capture_results`, `protein_structure_execution_information`; **old-runner callbacks defined**: `decision_context`; **per-axis providers**: `self.job_progress_provider`, `self.local_file_sources`; **self.services**: `scientific_parent_task` |
| `parent_input_custody.py` | 39 | Checks of a launch request against the bound resource (kind, identity, workspace confinement) and of resource constraints. Launch-side code carried in a results episode. | **per-axis providers**: `self.api_execution`×2, `self._practical` |
| `received_record_selection.py` | 35 | Which received records count: result sources whose assignment equals its own; handoffs that are returnable and match its target. | **BindingContext fields**: `assignment`, `role`, `scope`×2; **per-axis providers**: `self.api_execution`×2, `self.job_progress_provider` |
| `received_records.py` | 37 | Report facts the axis head or root may receive from it (file sources, capture outcomes, protein-structure facts). | **BindingContext fields**: `request`, `role`; **imports from old `root.a102`**: `protein_structure_result_views`; **old-runner callbacks defined**: `received_report_closure_facts`, `received_report_facts`, `received_report_sources`; **per-axis providers**: `self.local_file_sources`×2, `self.native_protein_structure_returns` |
| `received_reference_custody.py` | 37 | Resolution and validation of references received by the parent in the typed form (handoff, result and receipt references must be qualified). | **BindingContext fields**: `role`; **old-runner callbacks defined**: `received_form_references`, `resolve_received_reference`, `validate_received_report`; **per-axis providers**: `self.local_file_sources`×3, `self.native_protein_structure_returns`×3 |
| `report_delivery.py` | 25 | Closure: typed form built once from saved facts and last interpretation; same as the monitor's. | **imports from old `root.a102`**: `library.private_policy_call`, `library.report_fact_assembly`, `runtime`×2; **old-runner callbacks defined**: `finish`; **old runtime**: `form_with_facts`, `_json`×2, `json`, `Record`×2; **self.workflow**: `binding_context`, `episode_bindings`, `facts`, `journal`×2, `pending_handles`, `release`×2, `source_credit_view`; **journal/receipt tables**: `runtime_forms`×2 |
| `report_fields.py` | 19 | The report facts it offers: file source refs, capture outcomes, protein-structure facts, handoff refs, result refs, `execution_completed`, `execution_result_origin`. | **imports from old `root.a102`**: `local_file_capture_results`, `protein_structure_result_views`; **old-runner callbacks defined**: `fact_sources`; **old support classes**: `PracticalReceiptInformation` |
| `report_reference_access.py` | 47 | Which references the report may cite, by namespace (execution handle, practical receipt, file source, execution result with windows, handoff, API, scope subject). | **BindingContext fields**: `role`, `scope`×4; **imports from old `root.a102`**: `episode_bindings`×2; **old-runner callbacks defined**: `resolve`; **per-axis providers**: `self.api_execution`×2, `self.job_progress_provider`×2, `self.local_file_sources`; **old support classes**: `PracticalReceiptInformation`×2 |
| `resource_information.py` | 82 | Resource description shown at the first decision, configured capabilities (no probe), and the tool contracts with their commission routes per resource. | **imports from old `root.a102`**: `native_protein_structure_tool_info`; **old-runner callbacks defined**: `capabilities`, `initial_decision_context`, `resource_tool_contracts`; **per-axis providers**: `self.api_execution`×4, `self.local_file_sources`, `self.tool_registry`×2 |
| `result_selection.py` | 75 | Target lookup, selector admission (paths confined to the workspace; offset/limit only with a single path), requested windows, the known/initial record selection, and target-versus-assignment checks. | **BindingContext fields**: `assignment`×3, `episode_id`×7, `role`×3, `scope`×3; **imports from old `root.a102`**: `episode_receipts`, `protein_structure_selection`; **per-axis providers**: `self.api_execution`, `self.job_progress_provider`, `self.local_file_sources`; **self.services**: `record_selection`; **old support classes**: `EpisodeReceipts`×2; **journal/receipt tables**: `runtime_actions`, `runtime_receipt_inheritance`×2 |
| `retained_protein_reader.py` | 94 | Read authority for retained protein-structure results and the rule that protected protein references never fall through to ordinary resolution. | **BindingContext fields**: `assignment`, `role`, `run_id`, `scope`; **imports from old `root.a102`**: `execution_contracts`, `native_protein_structure_results`, `native_protein_structure_returns`, `protein_structure_contracts`, `protein_structure_operands`, `protein_structure_selection`, `state`; **old-runner callbacks defined**: `retained_protein_structure_reader`; **per-axis providers**: `self.job_progress_provider`, `self.native_protein_structure_results`×2, `self.native_protein_structure_returns`×2; **old support classes**: `NativeProteinStructureResults`×2, `NativeProteinStructureReturns`×2; **journal/receipt tables**: `runtime_episodes` |
| `retained_result_acquisition.py` | 70 | The native acquisition itself: observe the attempt once, read each requested window, keep intent, observation, window and receipt files immutable, refuse work after completion, publish the result source. | **BindingContext fields**: `assignment`×3, `episode_id`×4, `run_id`, `scope`; **per-axis providers**: `self.job_progress_provider`×2; **journal/receipt tables**: `runtime_actions`×2 |
| `retained_result_publication.py` | 59 | Publishing a result as a Store source (`episode.execution_result`) and re-validating a result body against target, selector, windows and the saved receipt. | **BindingContext fields**: `episode_id`, `run_id`, `scope`; **per-axis providers**: `self.job_progress_provider`, `self.local_file_sources`; **journal/receipt tables**: `runtime_episodes` |
| `saved_result_commission.py` | 45 | Restoring a successfully returned original results commission instead of commissioning it again. | **BindingContext fields**: `assignment`×2, `episode_id`×4, `path`×3, `request`, `role`, `scope`; **imports from old `root.a102`**: `episode_receipts`, `episode_return_records`; **old support classes**: `EpisodeReceipts`×2, `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_actions`, `runtime_episodes`, `runtime_report_attempts` |
| `task.py` | 223 | The decision loop, as in the monitor, with reasoning-commit, job-child failure feedback, `reads.map` parameter feedback, automatic score updates and shared-grading retention branches. Report grain name `results`. | **imports from old `root.a102`**: `episode_source_failure`, `library.action_contracts`, `library.private_policy_call`, `providers`, `read_mapping`, `runtime`×2; **old binding attributes**: `instruction_composer`; **old-runner callbacks defined**: `apply_response`, `execute`, `next`; **old runtime**: `AcquisitionError`×2, `ActionFailure`, `ContractError`, `ContractInformationError`, `_decode_recorded_action_response`, `Draft202012Validator`×2, `EventTargetError`×2, `inspect`, `_json`×5, `json`×8, `Mapping`×2, `nullcontext`×5, `observes_action_outcome`, `ReportBoundaryError`, `ReportRedelivery`×2, `schema_failure_diagnostic`, `SourceEnd`×2, `sqlite3`×2, `subprocess`×2, `validate_form`, `ValidationError`×3, `_wait_target_feedback`×2, `WorkflowError`×2; **self.workflow**: `action_schema`, `automatic_score_updates`, `binding_context`, `completed_unit`×3, `completions`×3, `controller_value`×2, `decision_exchanges`×3, `delivery_resolution_inputs`, `execute`, `execution_binding`×7, `inprocess_replay`×4, `journal`×7, `last_observed_credit`, `next_return`, `pending_work`, `perform_selected_wait`, `permits_common_action`, `receive_native_outcome`, `receive_outcome`, `resolve_pending_deliveries`, `resolver`, `retain_shared_grading_results`, `run_id`×3, `selected`×3, `source_credit_view`, `specialist`, `store`×8, `validate_report`; **journal/receipt tables**: `runtime_actions`×8, `runtime_episodes`, `runtime_model_calls`×2 |
| `task_decision.py` | 88 | The model call; also freezes literature numerical contracts (not a results concern). | **imports from old `root.a102`**: `decision_context`, `execution_prompt`, `library.hpc_prompt`, `runtime`×2, `structural_homology_evidence_prompt`; **old-runner callbacks defined**: `call`, `conversation_key`, `instructions`; **old provider interface**: `has_session`×3; **old runtime**: `_action_generation_schema`, `_ASSIGNMENT_TRANSPORT`, `DECISION_EXCHANGE_PROTOCOL`×5, `_digest`, `instructional_model_context`, `_json`×4, `json`×2, `_recorded_assignment_transport`, `WorkflowError`×5; **self.workflow**: `contract_information_profile`, `decision_exchanges`, `decision_protocol`×3, `freeze_contract_information`, `freeze_literature_numerical_contracts`, `history_preview`, `is_job_source`×2, `journal`, `numerical_contracts`, `provider`×2, `provider.conversation_key`, `provider.has_session`, `receipts`×4, `services`, `uses_received_record_context`×2, `validate_contract_information`×2; **journal/receipt tables**: `runtime_model_calls`×5; **old yield names**: `_category_yield_parameters`, `yield_table` |
| `task_state.py` | 108 | Per-episode decision state and restore/checkpoint; same as the monitor's. | **imports from old `root.a102`**: `episode_source_failure`, `runtime`×2; **old-runner callbacks defined**: `bind_execution_context`, `checkpoint`, `record_effect`, `record_execution_failure`, `restore`, `restore_checkpoint`; **old runtime**: `ActionLeaf`, `EFFECT_VERSION`, `Episode`, `interpretation_schema`, `_json`×2, `json`×4, `_object`, `_plain`, `Record`; **self.workflow**: `archive`, `completions`×4, `context`, `controller_value`, `execution_binding`×4, `grains`, `inprocess_replay`×7, `journal`×5, `progress_provider`×2, `recover_commissions`, `run_id`, `source_credit_view`, `store`×2; **journal/receipt tables**: `runtime_actions`×5 |
| `terminal_execution.py` | 242 | A launch-role terminal behaviour (`exec_command` on `launch_local`/`launch_hpc`), used here only to build per-resource operations and validate assignments. Byte-identical to the launch episode's copy and to the `hpc_work_planning/execution_result_acquisition` copy. | **BindingContext fields**: `assignment`×9, `episode_id`×4, `role`, `run_id`×5; **imports from old `root.a102`**: `acquisition`, `communication`, `domain`, `practical_execution_operations`, `practical_execution_records`, `practical_execution_state`, `practical_receipt_information`×3, `practical_yield`, `terminal_execution`, `terminal_scientific_evidence`×2; **old-runner callbacks defined**: `allowed_children`, `as_record`, `assignment_schema`, `catalog`, `child_roles`, `completion_for_action`, `credit_kind`, `credit_view`, `decision_context`, `execute`, `facts`, `fact_sources`, `initial_decision_context`, `initialize`, `instructions`, `permitted_common_actions`, `practical_estimator`, `prepare_assignment`, `resolve`, `validate_report`; **self.services**: `workflow`; **self.workflow**: `launch_instructions`; **old support classes**: `PracticalReceiptInformation`×6, `PracticalState`×2, `TerminalExecution`×2; **old yield names**: `PracticalYieldEstimator`×2 |
| `to_parent.py` | 37 | The facts reported: handoff refs, result refs (those with windows), file source refs, capture outcomes, result origin, `execution_completed`; report must agree with recorded facts. | **imports from old `root.a102`**: `protein_structure_result_views`; **old-runner callbacks defined**: `facts`, `validate_report`; **per-axis providers**: `self.api_execution`, `self.job_progress_provider`, `self.local_file_sources`×2, `self.native_protein_structure_results`×2, `self.native_protein_structure_returns`; **old support classes**: `PracticalReceiptInformation` |
| `waiting.py` | 9 | Records the suspension condition and passes it to the external executor. | **old-runner callbacks defined**: `suspension_changed`; **self.workflow**: `execution_backend`, `execution_handle`×2 |
| `yield_estimator.py` | 79 | Continuation by selector kind: unbounded native selector uses profile `native_unbounded_<kind>`; finite native selector uses profile `results:native_finite_<kind>` with a bounded estimate whose maximum is acquired_record_unit times the uncredited fraction, exact zero when nothing remains, and the completion estimator once a completion proof is verified; API and typed selectors use `results:api_<service>[_<selector version>]` or `results:typed_<kind>_<selector version>` with the completion estimator. | **BindingContext fields**: `assignment`, `role`; **imports from old `root.a102`**: `numerical`, `practical_yield`×2; **old-runner callbacks defined**: `practical_estimator`, `yield_controller`; **old yield names**: `estimate_bounded_credit_yield`×2, `NumericBand`×2, `PracticalYieldEstimator`×5, `YieldController`×4, `YieldEstimate`×2, `YieldParameters`×4 |

## Carried over

Carried over on 19 November 2026 to the ten-file form (episode.py `ExecutionResultAcquisition`; files `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `messages/read_from_parent.py`, `messages/internal_summary.py`, `messages/final_to_parent.py`; no children, so no `msg_to_child.py` or `read_from_child.py`). One row per old function, class or method of `runs/carry_over/functions/` for this episode. "machinery" rows are old-runner machinery and are not carried; "episode function" rows are placed in the file named; rows marked "(unplaced)" could not be placed and are listed in `docs/axis_restructure_20261117/carry_over_blocked/` with their reason. Old library modules the episode imported were already in `episode_support/` (called as written: `forms/structural_homology_evidence/execution_contracts.py` `canonical`, `obj`, `checked`; `jobs/structural_homology_evidence/practical_execution_operations.py` `confined`; `instructions/launch_instructions.py`; `tools/tool_knowledge.py`; `model_exchange/*`; `records/progress_views.py`; `records/structural_homology_evidence/domain.py`) or have no home (listed as unplaced). Functions of the old files that no library holds stay in the episode file that uses them (library candidates): `task.py` `requested_windows`, `validate_result_body`, `acquire`; `credit.py` `covered`, `selector_progress`; `messages/internal_summary.py` `uncovered_paths`, `facts`; `messages/read_from_parent.py` `windows`, `native_selector`.

| old file | name | kind | class | new place or reason |
|---|---|---|---|---|
| acquisition_operations.py | ResultsAcquisitionOperations | class | episode function | task.py tools (acquire) |
| acquisition_operations.py | ResultsAcquisitionOperations.catalog | method | episode function | task.py operation_catalog / CATALOG (native branch; protein-structure and API catalogs not carried: library without a home) |
| acquisition_operations.py | ResultsAcquisitionOperations.execute | method | episode function | task.py acquire via TOOLS (native branch; an argument error is an invalid outcome; local-file, protein-structure and API branches not carried) |
| action_policy.py | ResultsActionPolicy | class | episode function | task.py action (tool only) |
| action_policy.py | ResultsActionPolicy.permitted_common_actions | method | episode function | task.py action (tool only; the wait action of an API target is wait machinery and API targets are not carried) |
| binding_record.py | ResultsBindingRecord | class | machinery | the binding's own as_record() (binding identity record) |
| binding_record.py | ResultsBindingRecord.as_record | method | machinery | the binding's own as_record() (binding identity record) |
| child_commissioning.py | ResultsChildCommissioning | class | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_commissioning.py | ResultsChildCommissioning.child_roles | method | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_commissioning.py | ResultsChildCommissioning.allowed_children | method | episode function | task.py CHILD_SLOTS = {} |
| closed_credit.py | ResultsClosedCredit | class | machinery | closed credit view pinned in the old journal tables (runtime_* re-validation, EpisodeReceipts); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_carrier | method | machinery | closed credit view pinned in the old journal tables (runtime_* re-validation, EpisodeReceipts); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_receipts | method | machinery | closed credit view pinned in the old journal tables (runtime_* re-validation, EpisodeReceipts); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_value | method | machinery | closed credit view pinned in the old journal tables (runtime_* re-validation, EpisodeReceipts); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_facts | method | machinery | closed credit view pinned in the old journal tables (runtime_* re-validation, EpisodeReceipts); the system hands completion['credit'] to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_operational_credit_view | method | machinery | closed credit view pinned in the old journal tables (runtime_* re-validation, EpisodeReceipts); the system hands completion['credit'] to final_to_parent |
| completion.py | ResultsCompletion | class | episode function | messages/internal_summary.py uncovered_paths (class; its proof methods are machinery) |
| completion.py | ResultsCompletion._native_results_complete | method | episode function | messages/internal_summary.py uncovered_paths (completed = no uncovered path) |
| completion.py | ResultsCompletion._proof_for_action | method | machinery | practical completion proof built from runtime_actions rows (controller input) |
| completion.py | ResultsCompletion.completion_for_action | method | machinery | completion proof as controller input |
| completion.py | ResultsCompletion._closed_completion_verdict | method | machinery | reuse of recorded estimator history (runtime_observations) |
| completion.py | ResultsCompletion.verify_completion | method | machinery | PracticalYieldEstimator verification callback (completion proof) |
| configuration.py | ResultsConfiguration | class | episode function | settings (ctx.settings / settings) and ASSIGNMENT_FORM acquired_record_unit |
| configuration.py | ResultsConfiguration.__init__ | method | episode function | values -> settings (log_window_bytes in task.py, yield profiles in yield_estimator.py), acquired_record_unit -> ASSIGNMENT_FORM; resources / provider / reader construction -> unplaced (job access service not provided) |
| credit.py | ResultsCredit | class | episode function | credit.py |
| credit.py | ResultsCredit._generic_result_selector_progress | method | episode function | credit.py selector_progress |
| credit.py | ResultsCredit.credit_kind | method | machinery | credit_kind (deleted) |
| credit.py | ResultsCredit.project_credit | method | episode function | credit.py credit |
| credit.py | ResultsCredit._live_project_credit | method | episode function | credit.py credit (native selector branch; local-file mixed, protein-structure and API views not carried) |
| credit.py | ResultsCredit.credit_view | method | episode function | credit.py credit |
| decision_contracts.py | ResultsTaskDecisionContracts | class | machinery | decision-exchange loop (contract-information exchange, saved-exchange checks) |
| decision_contracts.py | ResultsTaskDecisionContracts.interpretation_context | method | machinery | decision-exchange loop (contract-information exchange, saved-exchange checks) |
| decision_contracts.py | ResultsTaskDecisionContracts.exchange_schema | method | machinery | decision-exchange loop (contract-information exchange, saved-exchange checks) |
| decision_contracts.py | ResultsTaskDecisionContracts.exchange_response | method | machinery | decision-exchange loop (contract-information exchange, saved-exchange checks) |
| decision_contracts.py | ResultsTaskDecisionContracts.validate_contract_exchange_request | method | machinery | decision-exchange loop (contract-information exchange, saved-exchange checks) |
| decision_contracts.py | ResultsTaskDecisionContracts.validate_contract_exchange_history | method | machinery | decision-exchange loop (contract-information exchange, saved-exchange checks) |
| decision_exchange.py | ResultsTaskDecisionExchange | class | machinery | decision-exchange loop (exchange_decision) |
| decision_exchange.py | ResultsTaskDecisionExchange.exchange_decision | method | machinery | decision-exchange loop (exchange_decision) |
| decision_inputs.py | ResultsDecisionInputs | class | episode function | task.py decide (context) |
| decision_inputs.py | ResultsDecisionInputs.decision_inputs | method | episode function | task.py decide (context) |
| decision_provider.py | ResultsTaskDecisionProvider | class | episode function (unplaced) | not placed, raises or absent: renderer render_selected_execution_prompt (see complete_decision) |
| decision_provider.py | ResultsTaskDecisionProvider.complete_decision | method | episode function (unplaced) | not placed, raises or absent: renderer render_selected_execution_prompt for selected execution contexts (lived in the old shared root; not read) |
| decision_state.py | ResultsDecisionState | class | episode function | task.py decide / messages/internal_summary.py |
| decision_state.py | ResultsDecisionState.decision_state | method | episode function | task.py decide / messages/internal_summary.py |
| episode.py | ExecutionEpisode | class | episode function | episode.py ExecutionResultAcquisition |
| execution_contracts.py | launch_operation_catalog | function | episode function (unplaced) | not placed, raises or absent: execution.capabilities is an operation of the launch role, not of results |
| execution_contracts.py | native_result_operation_catalog | function | episode function | task.py CATALOG / operation_catalog |
| execution_contracts.py | _outcome | function | episode function | task.py _outcome |
| execution_state.py | ResultsExecutionState | class | episode function | messages/read_from_parent.py / task.py |
| execution_state.py | ResultsExecutionState._delegate | method | episode function (unplaced) | not placed, raises or absent: returns the launch-role terminal delegate; unused by results |
| execution_state.py | ResultsExecutionState.initialize | method | episode function | messages/read_from_parent.py native_selector (selector check at admission; target-dependent check in task.py acquire); local-file, protein-structure and API initialisation not carried |
| execution_state.py | ResultsExecutionState._result_directory | method | machinery | immutable assignment.json / result directory files (the system journal and ctx.operation_key replace them) |
| from_parent.py | ResultsFromParent | class | episode function | messages/read_from_parent.py |
| from_parent.py | ResultsFromParent.required_return_sources | method | episode function | messages/final_to_parent.py RETURN_FORM (execution_result_refs stays selectable: the rule applied only under the axis head parent) |
| from_parent.py | ResultsFromParent.child_assignment_schema | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | ResultsFromParent.assignment_schema | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | ResultsFromParent.prepare_assignment | method | episode function | messages/read_from_parent.py read_from_parent (restoring a recorded commission is machinery; target-dependent checks in task.py; local-file and protein-structure admission not carried) |
| from_parent.py | ResultsFromParent.initial_references | method | episode function | messages/read_from_parent.py ASSIGNMENT_FORM handoff_ref and known_result_refs (record_refs: the system writes the commissioned receipts) |
| goal.py | ResultsGoal | class | episode function | goal.py GOAL / task.py instructions |
| goal.py | ResultsGoal.instructions | method | episode function | goal.py GOAL |
| instructions.py | instructions | function | episode function | task.py instructions |
| internal_summary.py | ResultsInternalSummary | class | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | ResultsInternalSummary._with_selected_execution_task | method | episode function (unplaced) | not placed, raises or absent: selected_execution_task for a local native protein-structure target (scientific_parent_task callback; protein-structure library has no home) |
| internal_summary.py | ResultsInternalSummary.decision_context | method | episode function | messages/internal_summary.py internal_summary + task.py decide (target description from the job-progress provider not carried) |
| parent_input_custody.py | ResultsParentInputCustody | class | episode function (unplaced) | not placed, raises or absent: launch-role re-validation of the launch request (class) |
| parent_input_custody.py | ResultsParentInputCustody._validate_request | method | episode function (unplaced) | not placed, raises or absent: launch-role re-validation of the launch request behind the handoff (reads old resource tables) |
| parent_input_custody.py | ResultsParentInputCustody._launch | method | episode function (unplaced) | not placed, raises or absent: launch-role re-validation of the launch request behind the handoff (reads old resource tables) |
| parent_input_custody.py | ResultsParentInputCustody._constraints | method | episode function (unplaced) | not placed, raises or absent: launch-role re-validation of the launch request behind the handoff (reads old resource tables) |
| received_record_selection.py | ResultsReceivedRecordSelection | class | episode function | messages/internal_summary.py internal_summary (results among the known records) |
| received_record_selection.py | ResultsReceivedRecordSelection._received | method | episode function | messages/internal_summary.py internal_summary (results among the known records) |
| received_records.py | ResultsReceivedRecords | class | episode function (unplaced) | not placed, raises or absent: parent-side reading of received report facts (annotation / structural head roles) |
| received_records.py | ResultsReceivedRecords.received_report_sources | method | episode function (unplaced) | not placed, raises or absent: parent-side reading of received report facts (annotation / structural head roles) |
| received_records.py | ResultsReceivedRecords.received_report_facts | method | episode function (unplaced) | not placed, raises or absent: parent-side reading of received report facts (annotation / structural head roles) |
| received_records.py | ResultsReceivedRecords.received_report_closure_facts | method | episode function (unplaced) | not placed, raises or absent: parent-side hook, returned {} |
| received_reference_custody.py | ResultsReceivedReferenceCustody | class | machinery | received-reference custody and typed-report admission (receipts, record admission) |
| received_reference_custody.py | ResultsReceivedReferenceCustody.resolve_received_reference | method | machinery | received-reference custody and typed-report admission (receipts, record admission) |
| received_reference_custody.py | ResultsReceivedReferenceCustody.validate_received_report | method | machinery | received-reference custody and typed-report admission (receipts, record admission) |
| received_reference_custody.py | ResultsReceivedReferenceCustody.received_form_references | method | machinery | received-reference custody and typed-report admission (receipts, record admission) |
| report_delivery.py | ResultsReportDelivery | class | machinery | report finish / delivery (form saving, pending handles, release) |
| report_delivery.py | ResultsReportDelivery.finish | method | machinery | report finish / delivery (form saving, pending handles, release) |
| report_fields.py | ResultsReportFields | class | episode function | messages/final_to_parent.py RETURN_FORM |
| report_fields.py | ResultsReportFields.fact_sources | method | episode function | messages/final_to_parent.py RETURN_FORM |
| report_reference_access.py | ResultsReportReferenceAccess | class | machinery | report reference resolver (class) |
| report_reference_access.py | ResultsReportReferenceAccess.resolve | method | machinery | report reference resolver (resolve for validate_form; reference_in_context over the old services) |
| resource_information.py | ResultsResourceInformation | class | episode function | task.py resource_information |
| resource_information.py | ResultsResourceInformation._resource_information | method | episode function | task.py resource_information |
| resource_information.py | ResultsResourceInformation.initial_decision_context | method | episode function | task.py decide (execution_resource_capabilities) / resource_information |
| resource_information.py | ResultsResourceInformation.capabilities | method | episode function | task.py resource_information (tool_names; configured availability probe-free) |
| resource_information.py | ResultsResourceInformation.resource_tool_contracts | method | episode function (unplaced) | not placed, raises or absent: commission routes of launch and results operations per resource, for the parent roles |
| result_selection.py | ResultsResultSelection | class | episode function | messages/read_from_parent.py / task.py |
| result_selection.py | ResultsResultSelection._target | method | episode function | task.py handoff_target (BLOCKED-ON-JOB-SERVICE) |
| result_selection.py | ResultsResultSelection._selector | method | episode function | messages/read_from_parent.py native_selector (workspace confinement in task.py acquire) |
| result_selection.py | ResultsResultSelection._windows | method | episode function | messages/read_from_parent.py windows |
| result_selection.py | ResultsResultSelection._selection | method | machinery | receipt selection of the known records (record_selection callback, runtime_receipt_inheritance, runtime_actions) |
| result_selection.py | ResultsResultSelection._context_target | method | machinery | target-vs-assignment identity checks over the old receipts and the launch roles |
| retained_protein_reader.py | ResultsRetainedProteinReader | class | episode function (unplaced) | not placed, raises or absent: protein-structure custody (selector not carried) |
| retained_protein_reader.py | ResultsRetainedProteinReader.retained_protein_structure_reader | method | episode function (unplaced) | not placed, raises or absent: protein-structure custody (selector not carried) |
| retained_protein_reader.py | ResultsRetainedProteinReader._protein_reference_access | method | episode function (unplaced) | not placed, raises or absent: protein-structure custody (selector not carried) |
| retained_protein_reader.py | ResultsRetainedProteinReader._retained_protein_result | method | episode function (unplaced) | not placed, raises or absent: protein-structure custody (selector not carried) |
| retained_result_acquisition.py | ResultsRetainedResultAcquisition | class | episode function | task.py acquire |
| retained_result_acquisition.py | ResultsRetainedResultAcquisition._selected_result_action | method | machinery | saved selected action row check (runtime_actions) |
| retained_result_acquisition.py | ResultsRetainedResultAcquisition._execute_native_results | method | episode function | task.py acquire / requested_windows |
| retained_result_publication.py | ResultsRetainedResultPublication | class | episode function | task.py acquire / validate_result_body |
| retained_result_publication.py | ResultsRetainedResultPublication._publish_result | method | episode function | task.py acquire (ctx.store.artifact of the validated body) |
| retained_result_publication.py | ResultsRetainedResultPublication._validate_result_body | method | episode function | task.py validate_result_body (scope, saved action row, episode row and receipt-file checks are machinery) |
| retained_result_publication.py | ResultsRetainedResultPublication._read_result | method | episode function | messages/internal_summary.py internal_summary (records.get_artifact and version check of a known result) |
| saved_result_commission.py | ResultsSavedResultCommission | class | machinery | restoring a recorded results commission from receipts and report attempts (EpisodeReceipts, EpisodeReturnRecords, runtime_report_attempts) |
| saved_result_commission.py | ResultsSavedResultCommission._recorded_results_assignment | method | machinery | restoring a recorded results commission from receipts and report attempts (EpisodeReceipts, EpisodeReturnRecords, runtime_report_attempts) |
| task.py | ResultsTask | class | episode function | task.py decide / action / tools |
| task.py | ResultsTask.next | method | episode function | task.py decide (the loop is the system's) |
| task.py | ResultsTask.apply_response | method | episode function | task.py action |
| task.py | ResultsTask.execute | method | episode function | task.py tools (acquire) |
| task_decision.py | ResultsTaskDecision | class | episode function | task.py instructions (class; call and conversation_key are machinery) |
| task_decision.py | ResultsTaskDecision.call | method | machinery | model call, decision protocol, saved decision inputs (decision-exchange loop) |
| task_decision.py | ResultsTaskDecision.instructions | method | episode function | task.py instructions |
| task_decision.py | ResultsTaskDecision.conversation_key | method | machinery | model call, decision protocol, saved decision inputs (decision-exchange loop) |
| task_state.py | ResultsTaskState | class | machinery | task state restore / checkpoint / record_effect (checkpoint, restore, journal) |
| task_state.py | ResultsTaskState.__init__ | method | machinery | task state restore / checkpoint / record_effect (checkpoint, restore, journal) |
| task_state.py | ResultsTaskState.bind_execution_context | method | machinery | task state restore / checkpoint / record_effect (checkpoint, restore, journal) |
| task_state.py | ResultsTaskState.record_execution_failure | method | machinery | record_execution_failure (a tool returns its failure as its outcome) |
| task_state.py | ResultsTaskState.restore_checkpoint | method | machinery | task state restore / checkpoint / record_effect (checkpoint, restore, journal) |
| task_state.py | ResultsTaskState.restore | method | machinery | task state restore / checkpoint / record_effect (checkpoint, restore, journal) |
| task_state.py | ResultsTaskState.record_effect | method | machinery | task state restore / checkpoint / record_effect (checkpoint, restore, journal) |
| task_state.py | ResultsTaskState.checkpoint | method | machinery | task state restore / checkpoint / record_effect (checkpoint, restore, journal) |
| terminal_execution.py | operation_catalog | function | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior | class | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior._operations | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior._assignment | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | method | machinery | practical state files |
| terminal_execution.py | TerminalExecutionBehavior.initialize | method | machinery | practical state initialisation (state files) |
| terminal_execution.py | TerminalExecutionBehavior.state | method | machinery | practical state files |
| terminal_execution.py | TerminalExecutionBehavior.as_record | method | machinery | the binding's own as_record() |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.instructions | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.catalog | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.execute | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | method | machinery | completion proof as controller input |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | method | machinery | PracticalYieldEstimator |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.facts | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.resolve | method | episode function (unplaced) | not placed, raises or absent: launch-role terminal behaviour (exec_command on the launch resource), not used by a results episode |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | method | machinery | report validation of the launch role |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | method | machinery | credit_view delegate of the launch role |
| to_parent.py | ResultsToParent | class | episode function | messages/final_to_parent.py |
| to_parent.py | ResultsToParent.facts | method | episode function | messages/final_to_parent.py facts (from the summary) / messages/internal_summary.py facts; the closed-credit facts are machinery |
| to_parent.py | ResultsToParent._live_facts | method | episode function | messages/internal_summary.py facts (native target; protein-structure and API facts not carried) |
| to_parent.py | ResultsToParent.validate_report | method | episode function | messages/final_to_parent.py validate_report (validate_form: NotImplementedError validate_form_not_built:A102) |
| waiting.py | ResultsWaiting | class | machinery | wait / suspension machinery (suspension_changed) |
| waiting.py | ResultsWaiting.suspension_changed | method | machinery | wait / suspension machinery (suspension_changed) |
| yield_estimator.py | ExecutionEpisodeYield | class | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | method | episode function | yield_estimator.py (profile lookup in yield_controller) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | method | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._results_yield_controller | method | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | method | machinery | PracticalYieldEstimator |
