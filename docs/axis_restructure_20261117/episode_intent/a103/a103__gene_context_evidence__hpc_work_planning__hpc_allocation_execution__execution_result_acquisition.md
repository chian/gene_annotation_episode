# a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/`
(47 files directly in the folder; no `grading/`, `scoring/` or child folders). Nothing from the old
shared root was read. Most of the per-target work (native BLAST, HMMER, masking, utility, database, API,
BV-BRC, UniProt, local file capture) is delegated to objects that `install_primary_result_readers`,
`install_preparation_result_readers`, `APIServiceExecution` and `LocalFileSourceResults` build. Those
come from the old shared root, so this page names only what this folder asks of them.

Old binding: class `ExecutionEpisode`,
`binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'`,
`commissioning_parent = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'`, role `results`,
no entry roles, record version `execution_episode_v1`, `replaces_default_instructions = True`. Decision
source: `ResultsTask`. Prompt renderer: `render_selected_execution_prompt`.

## What this episode is for

It acquires the results of one handed-off execution attempt. Its own words (`goal.py`):

> Acquire the original selected execution results through the original handoff. Choose bounded status or
> requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores.
> Native paths expose the current resource filesystem: the exact attempt observation does not establish
> that current file bytes were produced by that attempt. Separate read windows are not an atomic file
> snapshot. The scientific parent interprets the returned records. Original work, resource and selector
> stay fixed. Only actual complete acquisition establishes this endpoint.

The same binding object also answers questions from a receiving `annotation` or `gene_context_evidence`
context: which result facts that context may request, which received references it can resolve, and
which BLAST jobs it has received (`received_report_facts.py`, `received_reference_custody.py`,
`report_reference_access.py`, `resource_information.py`).

## Task and instructions

- One unit is one tool action, or a wait for an `api_service_assignment_v1` API target
  (`action_policy.py`). It has no reason, child or redelivery actions.
- Instructions (`instructions.py`): the goal text above replaces the default instructions. The reasoning
  requirement is added only if `reason` is permitted, which it never is. Tool knowledge and the launch
  library follow, then the pending-child-delivery paragraph, the wait paragraph (API target only) and the
  native-event paragraph. Under `decision_exchange_v1` the restored-history paragraph is replaced by the
  `request_context` guidance.

## What it reads from its parent's assignment

`from_parent.py` and `execution_contracts.py`: `{version: 'execution_results_assignment_v1', handoff_ref: text, selector: object}`.
The selector takes one of these shapes:

- local file sources: `local_file_source_selector_v1`;
- generic native: `paths` and/or one `path` with `offset`/`limit`, every path confined to the target's
  workspace;
- a typed selector validated by the target's kind: masking, utility, standard or native BLAST database,
  HMMER preparation, HMMER, BLAST, or API.

`prepare_assignment` first restores an original Results commission that was recorded as successfully
returned (`saved_result_commission.py`). Otherwise it resolves the target from a retained masking target,
a retained utility target, or the handoff target read by `job_progress_provider.targets.read_target`. It
then validates the selector and the per-kind inputs (BLAST database, BV-BRC request, MinHash commission).
When the parent is `gene_context_evidence` and an annotation task is required, the parent's form must
request `execution_result_refs` (`required_return_sources`).

## Children

None.

## Decision state and what it shows the model

State (`task_state.py`): the same source state as the other tasks.

Model inputs (`decision_state.py`): the same as the literature task, without annotation-axis mode. It
calls `is_scientific_source` instead of adding annotation context.

The binding's own block (`internal_summary.py`): `execution_assignment`, `execution_progress` (the current
facts), `execution_target` (for local file sources, the files), `execution_target_description` (status
and acquisition operations, provenance), `own_bvbrc_values` for a BV-BRC API target, and
`selected_execution_task` (`selected_execution_context.py`: `selected_execution_task_v1` with the
scientific parent's `scientific_question` and `selected_tool_info`, the request job, endpoint, constraints
and resource, the selector and the result description).

Initial context (`resource_information.py`): `execution_resource_capabilities` (resource id, kind,
availability `unknown`, tool names, workspace/policy/account/python/service/base_url, inventory snapshot,
API configuration facts) and `execution_initial_information`, plus `received_bvbrc_values`. For
receiving roles it adds `received_blast_jobs` (with their meaning) and `received_minhash_values`.

Added before each decision (`decision_inputs.py`): as in the literature task, with execution expectations
for grain `results`.

## Tools it offers

`acquisition_operations.py`, routed by target:

- generic native local/HPC (`execution_contracts.native_result_operation_catalog`):
  - `execution.results.status`: "Observe the exact handed-off physical attempt once."
  - `execution.results.collect`: "Observe the original attempt and acquire bounded first windows of the
    requested paths." Each window is `min(log_window_bytes, 1 MiB, requested length)`.
  - `execution.results.read`: "Acquire one selected bounded byte window within the original requested
    paths and interval." Operands `path`, `offset`, `limit` ≤ 1 MiB.
- native BLAST masking, BLAST utility, standard BLAST database, native BLAST database, HMMER preparation,
  HMMER, BLAST: each target's own catalog (old shared modules).
- API targets: `api_execution.catalog(context)`.
- local file sources: `local_file_sources.execute`.

`retained_result_acquisition.py` (generic native): the selected action must match the saved action. Reads
must stay inside the selector windows. It refuses after a completed proof
(`execution_results_assignment_already_completed`). Each step is recorded in an immutable file (intent,
observation, one file per window, receipt) under `execution-results/<digest(run, episode)>/`. Unavailable
files are recorded as failures and do not raise. Each result is published as an `episode.execution_result`
Source. Argument and target errors return an `invalid` outcome.

`terminal_execution.py` carries `TerminalExecutionBehavior` and `exec_command` (the launch-side terminal
behaviour). This episode builds one per local/HPC resource as `_practical[resource_id]` and uses it
through `_delegate`. It does not offer `exec_command` as a Results tool.

## How its credit is counted

Credit kind `operational` (`credit.py`):

- If a closed operational credit view was saved in the closing facts (`closed_credit.py`), that exact
  view is returned. It is authenticated against the context, binding, completion, archive, observation
  history and receipt prefix, and is never re-projected.
- Otherwise the target's own credit view is used: masking, utility, standard or native BLAST database,
  HMMER preparation, BLAST, HMMER, or API (`api_execution.credit_view`).
- Generic native: `credit = handoff_unit × 0 + acquired_record_unit × f`, where `f` is the mean over the
  requested paths of the newly covered fraction of requested byte positions. Positions already in the
  initial known references do not count (`selector_coverage_credit.py`). Each byte position is credited
  once, however the reads are split.
- Local file sources: `credit = acquired_record_unit × count of new file acquisitions`.

The view also reports `new_handoff_count`, `new_acquired_record_count` and either
`new_acquired_selector_fraction` or `new_file_acquisition_count`. It carries the binding version
`execution_received_selector_coverage_credit_v2` or the records version. `handoff_count` is hard-coded to
0, so `handoff_unit` is configured but never earns credit here.

## Continuation

`yield_estimator.py`, which requires `require_private_yield`:

| Target | Profile key | Old controller | Settings |
|---|---|---|---|
| native local/HPC, selector with any unbounded window | `results_yield_profiles['native_unbounded_<kind>']` | `YieldController` | cutoff, parameters |
| native local/HPC, finite windows | `task_yield_profiles['results:native_finite_<kind>']` | `YieldController` with an estimate function: the practical endpoint when it is verified; exact zero when no uncredited bytes remain; otherwise `estimate_bounded_credit_yield` with `maximum_credit = acquired_record_unit × (1 − originally covered fraction)` | cutoff, parameters |
| API | `task_yield_profiles['results:api_<service>[_<selector version>]']` | `YieldController` + `PracticalYieldEstimator(verify_completion)` | cutoff, parameters |
| typed native selector | `task_yield_profiles['results:typed_<kind>_<version>']` | `YieldController` + `PracticalYieldEstimator` | cutoff, parameters |

In today's terms, finite native windows use the bounded-quality estimator with the remaining coverage
credit as its maximum. Targets with a verifiable endpoint (API, typed, local files) use completion with a
target, where the target is the verified practical completion proof
(`completion.py`/`result_completion.py`: every requested path covered by windows of a completed, rc=0
observation, or the target-kind proof). Unbounded native windows use accumulation. A missing profile
raises; nothing falls back.

## What it reports to its parent

`to_parent.py`. The fact sources are:

- `execution_handoff_refs`, `execution_result_refs`;
- `execution_completed` (verified endpoint only: "Yielding alone is false");
- `execution_result_origin` (current-file windows, original producer output or received saved data);
- `execution_blast_hsps` (all published HSPs: no ranking or top-N);
- `execution_file_source_refs`, `execution_file_capture_outcomes`;
- the masking, BLAST utility, HMMER, BLAST pairwise, standard and native BLAST database, HMMER
  preparation, UniProt, BV-BRC data, MinHash and appservice families;
- the BLAST grader return (`BLAST_GRADED_RETURN_SOURCE`, the full grader sheet) when an NCBI BLAST
  service is bound.

Live facts are chosen per target kind (`_live_facts`), merged with the closed-credit facts. Every report
field that names a fact source must equal the fact (`execution_report_disagrees_with_recorded_facts`). A
closed UniProt result's frozen facts take precedence. `report_delivery.py` saves the form once.

## Differences from similar episodes

- It is the largest of the four, with 33 mixins. It acts as a router: nearly every method branches on the
  target kind and delegates to a per-kind host object.
- It replaces the default instructions like `hpc_resource_prediction`. Unlike that episode it allows
  `wait` for API targets and has per-target yield profiles, not one commission binding.
- Its `task.py` adds feedback the literature task lacks: job-assignment storage errors
  (`job_child`), `component_native_return_channels_required`, `input_detail` and `reads.map` parameter
  schema failures.
- The same binding provides received-facts and reference custody for the receiving
  `annotation`/`gene_context_evidence` roles. That cross-role duty belongs to the parent in a private
  layout and should move when carried over.

## Files

Names: `self.workflow.<m>` = old runner member; `runtime.<x>` = `_live_original_runtime.<x>` (old `root.a103.runtime`); `import:root.a103.<m>` = import from the old shared root; `table:<t>` = old journal/receipt table; `yield:<n>` = old yield name; `BindingContext.<f>` = old binding-context field; `services.<m>` = old binding services callback. Every row is also in `runs/carry_over/calls/a103_06.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names (uses) |
|---|---|---|---|
| `acquisition_operations.py` | 74 | tool catalog and execution routed by target kind (masking, utility, standard/native BLAST database, API, HMMER preparation, HMMER, BLAST, generic native) | `BindingContext.assignment`×6, `import:root.a103.native_blast_database_results`×1, `import:root.a103.native_blast_masking_results`×1, `import:root.a103.native_blast_results`×1, `import:root.a103.native_blast_standard_database_results`×1, `import:root.a103.native_blast_utility_results`×1, `import:root.a103.native_file_capture`×1, `import:root.a103.native_hmmer_preparation_results`×1, `import:root.a103.native_hmmer_results`×1 |
| `action_policy.py` | 10 | common actions: `tool` + `wait` for an `api_service_assignment_v1` API target, else `tool` only | none |
| `binding_record.py` | 8 | binding record `execution_episode_v1` with resources, initial information, credit units, log window/roles, yield profiles | none |
| `child_commissioning.py` | 11 | no children | none |
| `closed_completion.py` | 32 | reuses an endpoint verification recorded once in the saved observations | `BindingContext.assignment`×1, `BindingContext.episode_id`×4, `import:root.a103.episode_return_records`×1, `import:root.a103.method_loop.identities`×1, `import:root.a103.numerical`×1, `import:root.a103.practical_yield`×1, `table:runtime_observations`×1, `yield:NumericBand`×2 |
| `closed_credit.py` | 116 | freezes the operational credit view into the closing facts and later returns exactly that view, authenticated against completion, archive, history and receipt prefix | `BindingContext.as_record`×2, `BindingContext.episode_id`×8, `BindingContext.role`×1, `import:root.a103.episode_receipts`×1, `import:root.a103.episode_return_records`×3, `table:runtime_episodes`×2, `table:runtime_forms`×3, `table:runtime_observations`×1, `table:runtime_receipt_inheritance`×2, `table:runtime_record_receipts`×2 |
| `completion.py` | 57 | practical completion proof per target kind; `verify_completion` (saved verdict first) | none |
| `configuration.py` | 64 | settings: resources (kinds local/pbs_ssh/hmmer_api/api), initial information, tool registry, `handoff_unit`, `acquired_record_unit` (> 0), `log_window_bytes`, `log_roles`, `require_private_yield`, `results_yield_profiles` (`native_unbounded_local`/`_hpc`), `task_yield_profiles`; builds per-resource terminal behaviour, API execution, progress provider, local file sources, native result readers | `import:root.a103.api_service_execution`×1, `import:root.a103.execution_progress`×1, `import:root.a103.numerical`×1, `services.read_received_molecular_input`×1, `yield:YieldController`×3, `yield:YieldParameters`×3 |
| `credit.py` | 49 | credit kind `operational`; closed view if saved, else per-target credit view (native masking/utility/database/HMMER/BLAST, API); generic: `acquired_record_unit` × new selector byte coverage fraction (or × count of new file acquisitions for local file sources); handoff count fixed at 0 | none |
| `decision_contracts.py` | 39 | exchange envelope schema and validation | `import:root.a103.decision_context`×1, `import:root.a103.execution_prompt`×1, `import:root.a103.gene_context_evidence_prompt`×1, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×2, `runtime.composition_lookup_schema`×2, `runtime.Draft202012Validator`×1, `runtime._object`×3 |
| `decision_exchange.py` | 119 | pending-decision lookup loop | `import:root.a103.decision_context`×1, `import:root.a103.execution_prompt`×1, `import:root.a103.gene_context_evidence_prompt`×1, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×2, `runtime._action_generation_schema`×1, `runtime._category_yield_parameters`×1, `runtime.child_option_information`×1, `runtime.DECISION_CONTEXT_VERSION`×1, `runtime.instructional_model_context`×2, `runtime._json`×2, `runtime.lookup_attempts`×1, `runtime.Mapping`×3, `runtime.model_snapshot`×1, `runtime._plain`×2, `runtime._references_in`×1, `runtime.requested_contract_information`×1, `runtime.schema_failure_diagnostic`×2, `runtime.sqlite3`×1, `runtime.state_frame`×1, `runtime.ValidationError`×4, `runtime.yield_table`×1, `self.workflow.controller_binding`×1, `self.workflow.decision_exchanges`×1, `self.workflow.execute`×1, `self.workflow.journal`×1, `self.workflow.run_id`×1, `self.workflow.services`×1, `self.workflow.store`×2, `self.workflow.store.reference_subset`×1, `self.workflow.validate_contract_information`×1, `table:runtime_model_calls`×2 |
| `decision_inputs.py` | 69 | context additions; execution expectations grain `results` | `import:root.a103.episode_work_report`×2, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×2, `runtime.child_option_information`×1, `runtime.Mapping`×1, `self.workflow.available_child_roles`×1, `self.workflow.binding_context`×2, `self.workflow.episode_bindings`×1, `self.workflow.execution_expectations`×1, `self.workflow.is_job_source`×1, `self.workflow.job_episodes`×4, `self.workflow.launch_instructions`×2, `self.workflow.native_estimation_context`×1, `self.workflow.native_event_information`×2, `self.workflow.pending_work`×1, `self.workflow.permits_common_action`×1, `self.workflow.resource_context`×1, `self.workflow.resource_estimator`×5, `self.workflow.shared_information_context`×1, `self.workflow.store`×2, `self.workflow.waiting_support`×1 |
| `decision_provider.py` | 21 | provider dispatch with prompt renderer | `import:root.a103.decision_context`×1, `import:root.a103.execution_prompt`×1, `import:root.a103.gene_context_evidence_prompt`×1, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×1, `self.workflow.provider`×2, `self.workflow.provider.conversation_key`×1, `self.workflow.specialist`×1 |
| `decision_state.py` | 45 | model inputs; calls `is_scientific_source` instead of annotation context | `import:root.a103.runtime`×2, `runtime.FACT_MEANINGS`×1, `runtime.FACT_SOURCES`×1, `runtime.json`×2, `runtime.Mapping`×3, `runtime._plain`×2, `runtime._references_in`×1, `self.workflow.binding_context`×1, `self.workflow.catalog`×1, `self.workflow.controller_binding`×1, `self.workflow.delivery_status`×1, `self.workflow.extra_report_sources`×1, `self.workflow.is_scientific_source`×1, `self.workflow.job_episode_options`×1, `self.workflow.journal`×3, `self.workflow.knowledge`×1, `self.workflow.local_outcome_preview`×1, `self.workflow.pending_work`×1, `self.workflow.receipt_projection`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_binding`×1, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×3, `self.workflow.store.reference_subset`×1, `self.workflow.tools`×1, `self.workflow.tools.model_contract_catalog`×1, `self.workflow.working_state`×1, `table:runtime_actions`×2 |
| `episode.py` | 47 | `ExecutionEpisode` composed from 33 mixins; role `results`, `commissioning_parent='gene_context_evidence/hpc_work_planning/hpc_allocation_execution'`, `replaces_default_instructions=True`, selected-execution prompt renderer | `import:root.a103.gene_context_evidence_prompt`×1 |
| `execution_contracts.py` | 54 | constants: versions, roles, kinds, schemas (`RESULTS_SCHEMA`, native selector, `FILE_LIMIT` 1 MiB), `NATIVE_RESULT_ORIGIN`, native result operations `execution.results.status/collect/read`, `_outcome` | `import:root.a103.a103_execution_bindings`×1, `import:root.a103.a103_homology_execution`×1, `import:root.a103.communication`×1, `import:root.a103.domain`×1, `import:root.a103.execution_contracts`×1, `import:root.a103.launch_instructions`×1, `import:root.a103.local_file_capture_results`×1, `import:root.a103.native_blast_acquisition`×1, `import:root.a103.native_blast_database_acquisition`×1, `import:root.a103.native_blast_masking_acquisition`×1, `import:root.a103.native_blast_standard_database_acquisition`×1, `import:root.a103.native_blast_utility_acquisition`×1, `import:root.a103.native_hmmer_acquisition`×1, `import:root.a103.native_hmmer_preparation_acquisition`×1, `import:root.a103.practical_execution_operations`×1, `import:root.a103.practical_execution_records`×1, `import:root.a103.practical_execution_state`×1, `import:root.a103.practical_receipt_information`×1, `import:root.a103.resource_records`×1 |
| `execution_state.py` | 47 | `initialize`: validates selector, requires the BLAST grader typed return when the target needs it, initial refs for masking/utility, API initialize, immutable result directory `execution-results/<digest(run, episode)>/assignment.json`; `_delegate` to API or terminal behaviour | `BindingContext.assignment`×6, `BindingContext.episode_id`×2, `BindingContext.request`×1, `BindingContext.role`×1, `BindingContext.run_id`×2, `BindingContext.scope`×2 |
| `from_parent.py` | 52 | assignment `execution_results_assignment_v1` {`handoff_ref`, `selector`} with local-file and native selector conditions; target resolution (retained masking/utility target or handoff target); per-kind input validation; restores a recorded results commission; `execution_result_refs` required back to `gene_context_evidence` when an annotation task is required | `import:root.a103.bvbrc_data_host`×1, `import:root.a103.native_blast_database_result_publication`×1, `import:root.a103.native_blast_standard_database_result_publication`×1, `services.annotation_task_required`×1 |
| `goal.py` | 9 | the Results goal text (acquire original selected results through the handoff; bounded status/file reads; preserve partial bytes and native scores; current filesystem, not attempt-produced bytes; windows not atomic; parent interprets; only complete acquisition is the endpoint) | none |
| `initial_input_references.py` | 31 | authenticates inherited initial references | `BindingContext.assignment`×2, `BindingContext.role`×3, `import:root.a103.native_blast_database_result_publication`×1, `import:root.a103.native_blast_standard_database_result_publication`×1 |
| `__init__.py` | 0 | empty package marker | none |
| `instructions.py` | 23 | composer: binding goal (replaces default), reasoning requirement if permitted, tool knowledge, launch library, pending-delivery, wait and native-event paragraphs, exchange-protocol history replacement | `import:root.a103.runtime_prompt`×2, `runtime_prompt.DECISION_EXCHANGE_PROTOCOL`×1, `runtime_prompt.INSTRUCTIONS`×3, `runtime_prompt.REASONING_COMMIT_REQUIREMENT`×1, `self.workflow.binding_context`×1, `self.workflow.decision_protocol`×1, `self.workflow.knowledge`×1, `self.workflow.launch_instructions`×1, `self.workflow.native_event_information`×1, `self.workflow.permits_common_action`×3, `self.workflow.specialist`×1 |
| `internal_summary.py` | 20 | model block: `execution_assignment`, `execution_progress` (facts), `execution_target`, its description (status/acquisition operations), BV-BRC own values, `selected_execution_task` | `BindingContext.assignment`×2, `BindingContext.scope`×1, `import:root.a103.bvbrc_data_host`×1, `import:root.a103.local_file_capture_results`×1 |
| `parent_input_custody.py` | 49 | launch request validation (`_permitted`, `_validate_request`, `_launch`, `_constraints`) used by target checks | none |
| `received_records.py` | 52 | `_received` handoffs and results from known refs; appservice/UniProt presence; forwarding rules | `BindingContext.assignment`×1, `BindingContext.role`×1, `BindingContext.scope`×2, `import:root.a103.bvbrc_homology_returns`×1 |
| `received_reference_custody.py` | 160 | resolves received references for own and parent receiving contexts (local files, masking, utility, UniProt, BLAST/HMMER returns, appservice); validates received reports; received form references | `BindingContext.role`×10, `import:root.a103.bvbrc_homology_returns`×1, `import:root.a103.hmmer_native_result_views`×1 |
| `received_report_facts.py` | 103 | fact sources and facts this binding supplies to a receiving `annotation`/`gene_context_evidence` parent | `BindingContext.request`×2, `BindingContext.role`×11, `import:root.a103.blast_pairwise_result_views`×1, `import:root.a103.blast_utility_result_views`×1, `import:root.a103.bvbrc_data_views`×1, `import:root.a103.bvbrc_minhash_views`×1, `import:root.a103.hmmer_preparation_result_views`×1, `import:root.a103.native_blast_database_result_views`×1, `import:root.a103.native_blast_standard_database_result_views`×1, `import:root.a103.sequence_masking_result_views`×1, `import:root.a103.uniprot_return_contracts`×1 |
| `report_delivery.py` | 25 | finish: form from report values + assembled facts, saved once | `import:root.a103.library.private_policy_call`×1, `import:root.a103.library.report_fact_assembly`×1, `import:root.a103.runtime`×2, `runtime.form_with_facts`×1, `runtime._json`×2, `runtime.json`×1, `runtime.Record`×2, `self.workflow.binding_context`×1, `self.workflow.episode_bindings`×1, `self.workflow.facts`×1, `self.workflow.journal`×2, `self.workflow.pending_handles`×1, `self.workflow.release`×2, `self.workflow.source_credit_view`×1, `table:runtime_forms`×2 |
| `report_reference_access.py` | 115 | report reference resolution for own and supported foreign contexts | `BindingContext.role`×12, `BindingContext.scope`×4, `import:root.a103.bvbrc_data_views`×1, `import:root.a103.bvbrc_homology_returns`×1, `import:root.a103.episode_bindings`×2, `import:root.a103.hmmer_preparation_result_views`×1, `import:root.a103.native_blast_database_results`×1, `import:root.a103.native_blast_standard_database_results`×1 |
| `resource_information.py` | 86 | resource information (kind, availability, tool names, workspace/policy/account, inventory, API configuration facts); initial decision context (capabilities, initial information, received BV-BRC values, received BLAST jobs, MinHash values); capabilities; resource tool contracts for launch/results commission routes | `BindingContext.role`×3 |
| `result_completion.py` | 84 | native completion: every requested path fully covered by windows of a completed rc=0 observation; builds `practical_completion_v1` proof | `BindingContext.assignment`×3, `BindingContext.episode_id`×4, `BindingContext.run_id`×4, `BindingContext.scope`×1, `table:runtime_actions`×2 |
| `result_selection.py` | 116 | `_target`, `_selector` per target kind, `_windows`, `_selection` (known/initial refs from services, receipts or own actions), `_context_target` checks | `BindingContext.assignment`×3, `BindingContext.episode_id`×7, `BindingContext.role`×3, `BindingContext.scope`×6, `import:root.a103.blast_pairwise_result_views`×1, `import:root.a103.blast_utility_result_views`×1, `import:root.a103.episode_receipts`×1, `import:root.a103.hmmer_native_result_views`×1, `import:root.a103.hmmer_preparation_result_views`×1, `import:root.a103.native_blast_database_result_views`×1, `import:root.a103.native_blast_standard_database_result_views`×1, `import:root.a103.sequence_masking_result_views`×1, `services.record_selection`×1, `table:runtime_actions`×1, `table:runtime_receipt_inheritance`×2 |
| `retained_masking_reader.py` | 29 | retained masking selector/target/reference access | `import:root.a103.sequence_masking_result_views`×1 |
| `retained_result_acquisition.py` | 70 | generic native `execution.results.status/collect/read`: checks the selected action, selector windows, refuses after completion, immutable intent/observation/window/receipt files, publishes the result | `BindingContext.assignment`×3, `BindingContext.episode_id`×4, `BindingContext.run_id`×1, `BindingContext.scope`×1, `table:runtime_actions`×2 |
| `retained_result_publication.py` | 59 | publishes/validates/reads `episode.execution_result` Sources | `BindingContext.episode_id`×1, `BindingContext.run_id`×1, `BindingContext.scope`×1, `table:runtime_episodes`×1 |
| `retained_utility_reader.py` | 29 | retained BLAST utility selector/target/reference access | `import:root.a103.blast_utility_result_views`×1 |
| `saved_decision_exchange.py` | 85 | authenticates saved exchanges | `import:root.a103.decision_context`×1, `import:root.a103.execution_prompt`×1, `import:root.a103.gene_context_evidence_prompt`×1, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×2, `runtime.apply_state_frame`×1, `runtime.CONTRACT_INFORMATION_OPERATIONS`×1, `runtime.DECISION_CONTEXT_VERSION`×1, `runtime.instructional_model_context`×1, `runtime.is_contract_information`×1, `runtime._json`×8, `runtime.json`×1, `runtime.model_snapshot`×1, `runtime._recorded_action_generation_schema`×1, `runtime.requested_contract_information`×1, `runtime.ValidationError`×1, `runtime.WorkflowError`×9, `self.workflow.contract_information_reply`×1, `self.workflow.decision_exchanges`×2, `self.workflow.journal`×1, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls`×1 |
| `saved_result_commission.py` | 45 | restores an original successfully returned Results commission from saved attempts | `import:root.a103.episode_receipts`×1, `import:root.a103.episode_return_records`×1, `table:runtime_actions`×1, `table:runtime_episodes`×1, `table:runtime_report_attempts`×1 |
| `selected_execution_context.py` | 38 | `selected_execution_task_v1`: scientific question and tool info from the scientific parent, the request (job, endpoint, constraints, resource), selector, result description | `BindingContext.assignment`×1, `import:root.a103.native_profile_presentation`×1, `services.scientific_parent_task`×1 |
| `selector_coverage_credit.py` | 34 | fraction of requested byte positions newly covered (not in initial refs), averaged over requested paths | `BindingContext.assignment`×1 |
| `task_decision.py` | 83 | call composing the decision mixins | `import:root.a103.decision_context`×1, `import:root.a103.execution_prompt`×1, `import:root.a103.gene_context_evidence_prompt`×1, `import:root.a103.library.hpc_prompt`×1, `import:root.a103.runtime`×2, `runtime._action_generation_schema`×1, `runtime._ASSIGNMENT_TRANSPORT`×1, `runtime.DECISION_EXCHANGE_PROTOCOL`×5, `runtime._digest`×1, `runtime.instructional_model_context`×1, `runtime._json`×4, `runtime.json`×2, `runtime._recorded_assignment_transport`×1, `runtime.WorkflowError`×5, `self.workflow.contract_information_profile`×1, `self.workflow.decision_exchanges`×1, `self.workflow.decision_protocol`×3, `self.workflow.freeze_contract_information`×1, `self.workflow.freeze_literature_numerical_contracts`×1, `self.workflow.history_preview`×1, `self.workflow.is_job_source`×2, `self.workflow.journal`×1, `self.workflow.numerical_contracts`×1, `self.workflow.provider`×1, `self.workflow.provider.has_session`×1, `self.workflow.receipts`×4, `self.workflow.services`×1, `self.workflow.uses_received_record_context`×2, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls`×5 |
| `task.py` | 229 | decision loop; extra feedback for job-assignment storage errors, component native return channels, input detail, `reads.map` schema failures; report grain `results` | `import:root.a103.episode_source_failure`×1, `import:root.a103.library.action_contracts`×1, `import:root.a103.library.private_policy_call`×1, `import:root.a103.providers`×1, `import:root.a103.read_mapping`×1, `import:root.a103.runtime`×2, `runtime.AcquisitionError`×2, `runtime.ActionFailure`×1, `runtime.ContractError`×2, `runtime.ContractInformationError`×1, `runtime._decode_recorded_action_response`×1, `runtime.Draft202012Validator`×2, `runtime.EventTargetError`×2, `runtime.inspect`×1, `runtime._json`×5, `runtime.json`×8, `runtime.Mapping`×9, `runtime.nullcontext`×5, `runtime.observes_action_outcome`×1, `runtime._plain`×1, `runtime.ReportBoundaryError`×1, `runtime.ReportRedelivery`×2, `runtime.schema_failure_diagnostic`×1, `runtime.SourceEnd`×2, `runtime.sqlite3`×2, `runtime.subprocess`×2, `runtime.validate_form`×1, `runtime.ValidationError`×3, `runtime._wait_target_feedback`×2, `runtime.WorkflowError`×2, `self.workflow.action_schema`×1, `self.workflow.automatic_score_updates`×1, `self.workflow.binding_context`×1, `self.workflow.completed_unit`×3, `self.workflow.completions`×3, `self.workflow.controller_value`×2, `self.workflow.decision_exchanges`×3, `self.workflow.delivery_resolution_inputs`×1, `self.workflow.execute`×1, `self.workflow.execution_binding`×7, `self.workflow.inprocess_replay`×4, `self.workflow.journal`×7, `self.workflow.last_observed_credit`×1, `self.workflow.next_return`×1, `self.workflow.pending_work`×1, `self.workflow.perform_selected_wait`×1, `self.workflow.permits_common_action`×1, `self.workflow.receive_native_outcome`×1, `self.workflow.receive_outcome`×1, `self.workflow.resolve_pending_deliveries`×1, `self.workflow.resolver`×1, `self.workflow.retain_shared_grading_results`×1, `self.workflow.run_id`×3, `self.workflow.selected`×3, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×8, `self.workflow.validate_report`×1, `table:runtime_actions`×8, `table:runtime_episodes`×1, `table:runtime_model_calls`×2 |
| `task_state.py` | 108 | source state, failure recording, restore/checkpoint | `import:root.a103.episode_source_failure`×1, `import:root.a103.runtime`×2, `runtime.ActionLeaf`×1, `runtime.EFFECT_VERSION`×1, `runtime.Episode`×1, `runtime.interpretation_schema`×1, `runtime._json`×2, `runtime.json`×4, `runtime._object`×1, `runtime._plain`×1, `runtime.Record`×1, `self.workflow.archive`×1, `self.workflow.completions`×4, `self.workflow.context`×1, `self.workflow.controller_value`×1, `self.workflow.execution_binding`×4, `self.workflow.grains`×1, `self.workflow.inprocess_replay`×7, `self.workflow.journal`×5, `self.workflow.progress_provider`×2, `self.workflow.recover_commissions`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_view`×1, `self.workflow.store`×2, `table:runtime_actions`×5 |
| `terminal_execution.py` | 242 | `TerminalExecutionBehavior` + `operation_catalog` (`exec_command`) for local/HPC resources: execution-agent instructions, receipts, completion proof, practical facts; used as `_practical[resource_id]` | `BindingContext.assignment`×9, `BindingContext.episode_id`×4, `BindingContext.role`×1, `BindingContext.run_id`×5, `import:root.a103.acquisition`×1, `import:root.a103.communication`×1, `import:root.a103.domain`×1, `import:root.a103.practical_execution_operations`×1, `import:root.a103.practical_execution_records`×1, `import:root.a103.practical_execution_state`×1, `import:root.a103.practical_receipt_information`×3, `import:root.a103.practical_yield`×1, `import:root.a103.terminal_execution`×1, `import:root.a103.terminal_scientific_evidence`×2, `yield:PracticalYieldEstimator`×2 |
| `to_parent.py` | 120 | fact sources (handoff/result refs, completed, origin, HSPs, file sources/outcomes, masking, utility, UniProt, BLAST/HMMER families, BV-BRC, MinHash, BLAST grader return) and live facts per target kind; report fields must equal facts | `BindingContext.scope`×1, `import:root.a103.blast_pairwise_result_views`×2, `import:root.a103.blast_result_views`×1, `import:root.a103.blast_utility_result_views`×2, `import:root.a103.bvbrc_data_views`×1, `import:root.a103.bvbrc_minhash_views`×1, `import:root.a103.hmmer_native_result_views`×2, `import:root.a103.hmmer_preparation_result_views`×2, `import:root.a103.local_file_capture_results`×1, `import:root.a103.native_blast_database_results`×1, `import:root.a103.native_blast_database_result_views`×1, `import:root.a103.native_blast_standard_database_results`×1, `import:root.a103.native_blast_standard_database_result_views`×1, `import:root.a103.native_hmmer_acquisition`×1, `import:root.a103.sequence_masking_result_views`×2, `import:root.a103.uniprot_return_contracts`×2 |
| `waiting.py` | 9 | records suspension on the execution handle | `self.workflow.execution_backend`×1, `self.workflow.execution_handle`×2 |
| `yield_estimator.py` | 79 | finite native selector: `YieldController` with `results:native_finite_<kind>` profile and a bounded-credit estimate with maximum = remaining `acquired_record_unit` × uncovered fraction (exact zero when nothing remains, practical endpoint when verified); unbounded native windows: `native_unbounded_<kind>` profile; typed/API targets: `results:typed_<kind>_<version>` or `results:api_<service>[_<version>]` with `PracticalYieldEstimator` | `BindingContext.assignment`×1, `BindingContext.role`×1, `import:root.a103.numerical`×1, `import:root.a103.practical_yield`×2, `yield:estimate_bounded_credit_yield`×2, `yield:NumericBand`×2, `yield:PracticalYieldEstimator`×5, `yield:YieldController`×4, `yield:YieldEstimate`×2, `yield:YieldParameters`×4 |
