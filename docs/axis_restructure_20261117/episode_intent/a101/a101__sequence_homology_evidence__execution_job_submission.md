# a101/sequence_homology_evidence/execution_job_submission — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/<file>`
(files directly in this folder only; child folders `api_job_execution`, `hpc_job_execution`, `local_job_execution`
and `tests/` are not covered here). Old binding class `ExecutionEpisode` (`binding_path =
'sequence_homology_evidence/execution_job_submission'`, `commissioning_parent = 'sequence_homology_evidence'`,
`roles = entry_roles = ('launch',)`, `replaces_default_instructions = True`), decision source `OperationalTask`.
Contract version `execution_episode_v1`; launch assignment version `execution_launch_assignment_v1`. The A101
parent calls this the **Launch** episode (role `launch`).

## What it is for (its goal, in its own words)

`goal.py`:

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities,
> recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs,
> constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive its
> requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff completes this
> launch endpoint with exact zero future credit.

It is a router: it chooses which resource child (api / local / hpc) runs which of the parent's requests, and is
done when every eligible request has a usable handoff.

## Task and instructions

Because `replaces_default_instructions = True`, the goal text replaces the generic prompt. `task_instructions.py`
holds its own inlined copy of `INSTRUCTIONS`, `REASONING_COMMIT_REQUIREMENT` and `DECISION_EXCHANGE_PROTOCOL`
(the head imports these from the old shared library) and the same composition rules as the head: reasoning commit
paragraph if `reason` is permitted, tool-knowledge and launch-library paragraphs, redelivery paragraph, the
in-process wait paragraph, native-event paragraph, exchange-protocol replacement.

`task.py` (`OperationalTask`): same decision/admission/execution loop as the head with three differences: no
job_child storage/subprocess failure arm, no closed-request execution guard before executing, and the reasoning
path is kept (launch may `reason`). `task_decision.py`: same model-call/exchange protocol as the head, except the
`decision_input` receipt is not skipped for job sources, and the exchange yield table is computed inline
(`annotation_axis_yield_table_v1` from controller arms for annotation-axis credit, else `yield_table` with the
controller's category yield parameters). `task_state.py`: identical rules to the head's.

## What it reads from its parent's assignment

`from_parent.py` / `from_parent_launch.py` (closed schema):

| Field | Meaning |
|---|---|
| `version` | const `execution_launch_assignment_v1`. |
| `requests` | Object keyed by configured `resource_id` (≥1). Each value is that resource's request schema: API resources use the API service's own assignment schema; local/HPC use the practical `ASSIGNMENT_SCHEMA` with `resource_id` const, `resource_kind` const and `requested_job` (generic, or native_blast / native_blast_masking / native_blast_utility / native_blast_database / native_blast_standard_database / native_hmmer / native_hmmer_preparation alternatives). A request may instead be a `BLAST_GRADED_REQUEST` (BLAST database grader return: `query_subject_ref`, optional `database`, `return_type`) for an `ncbi_blast` API resource. |
| `immutable_input_versions` | Input version records, validated against scope. |
| `constraints` | `allowed_resource_ids`, `allowed_kinds`, `resource_id`, `kind` — which requests are permitted. |
| `launch_instructions` | Pinned launch-instruction selection. |

`prepare_assignment` also: authenticates an HPC-parent launch (`hpc_launch_authentication`), validates masking and
utility input references against the parent, input versions, and native/standard BLAST database job inputs.
`initial_references` = masking and utility input refs of each request.

## Children it may commission

`child_roles` = `ROLE_KINDS` = `launch_api` (api), `launch_local` (local), `launch_hpc` (hpc). `allowed_children`
keeps only roles whose kind matches a configured resource the assignment permits.

| Role | Child binding | Sends | Takes back |
|---|---|---|---|
| `launch_api` | `.../execution_job_submission/api_job_execution` | `to_child_api_job_execution.prepare_commission`: scope, expanded return form, initial report, child's `prepare_assignment` of one selected request (the child re-checks it against this Launch assignment). | `from_child_api_job_execution.receive_report`: role/binding-path guard, recorded-admission refs, progress provider form receipt, form refs + `received_form_references`, native timing receipts (`runtime_report_attempts.timing_receipts`), receipts `child_form`/`report_redelivery`, tool attributions. |
| `launch_hpc` | `.../hpc_job_execution` | `to_child_hpc_job_execution.prepare_commission` (adds: an HPC launch beneath an `hpc` ancestor must request `execution_handoff_refs`). A frozen HPC launch exposes only its already authorized HPC request (`child_assignment_schema` enum). | `from_child_hpc_job_execution.receive_report` (same custody). |
| `launch_local` | `.../local_job_execution` | `to_child_local_job_execution.prepare_commission`. | `from_child_local_job_execution.receive_report`. |

## Decision state and what it shows the model

`decision_state.py`: one presentation (equal to the head's standalone presentation, plus `job_episode_options`;
it never adds `annotation_context`). `internal_summary.py` `initial_decision_context`:
`execution_resource_capabilities` (per resource: id, kind, availability `unknown`, tool names, workspace/policy/
account/python/service/base_url, inventory snapshot, API configuration facts), `execution_initial_information`,
`received_bvbrc_values`; for annotation/A101 contexts with an `ncbi_blast` service, `received_blast_jobs` (root
sees per-annotation/axis/subject summaries; the scientific owner sees its original handles) and their meaning
text ("Waiting earns no scientific credit"); `received_minhash_values` when MinHash is configured.
`decision_context`: `execution_assignment`, `execution_progress` (= its own facts) and, for an `ebi_hmmer` API
request or a single native BLAST/HMMER job, `selected_execution_task` (scientific question and selected tool info
from the scientific parent, requests with resource info). `decision_inputs.py`: as the head, without the
job-source resource estimate branch, and with its own completed_action_reports rule.

## Tools it offers

`permitted_common_actions = ('tool', 'reason', 'child', 'wait', 'redeliver_report')`, reduced to `('tool',
'child', 'redeliver_report')` when any ancestor is `hpc`. Its own catalog is `launch_operation_catalog()`:
`execution.capabilities` — read the caller-bound resource configuration and recorded inventory; no discovery or
selection. `execute` returns `initial_decision_context` as that tool's result (the remaining dispatch below it in
`execution_operations.execute` is unreachable in this copy; the `'launch' in ROLE_KINDS` branches are always
false). `resource_tool_contracts()` declares, for every resource, the launch and results operations as
`commission` routes (entry role → resource role), homology API contracts, BV-BRC proteome tool contracts, native
and preparation operation contracts — these are offered to the scientific parent as selectable tools routed
through this Launch.

## How its credit is counted

`credit.py`: kind `operational`. A closed episode returns only its original closed credit snapshot
(`execution_closed_operational_credit_v1`, checked against runtime_episodes completion/archive, observation
history digest and the receipt-inheritance prefix). Live credit: native result readers first (masking, utility,
standard database, database, HMMER preparation, BLAST, HMMER) when their target applies; otherwise
`credit = handoff_unit × (number of distinct resource_ids with a usable handoff that were not already in the
initial known refs)` (+ `acquired_record_unit × 0`), binding `execution_received_records_credit_v1`. Completion
proof: a completed action whose record refs include a usable handoff target → `practical_completion_v1`
(endpoint `usable_handoff`, key `received_usable_handoff`).

## Continuation (yield estimator and settings)

`yield_estimator.py` (requires `require_private_yield`): remaining = (eligible requests − requests already handed
off in the initial refs) × `handoff_unit`. If remaining > 0: **bounded quality** estimator (BoundedYieldController)
with max = remaining and the task profile `launch:<sorted request classes joined by +>` (`{cutoff, parameters}` from
`task_yield_profiles`). Request class = `api_<service>[_<algorithm>][_<database>]_handoff`, `compact_<version>`, or
`practical_<kind>_<native...>_{handoff|outputs}`. If nothing remains: accumulation estimator with cutoff 0 and an
exact-zero forecast (`launch_original_request_exhaustion_v1`), nonzero initial credit is an error.
Configuration (`configuration.py`): explicit `resources` (kinds local / pbs_ssh / hmmer_api / api; only A101
native_* bindings allowed), `initial_information`, positive `handoff_unit` and `acquired_record_unit`,
`log_window_bytes`, `log_roles`, `require_private_yield`, `results_yield_profiles`
(native_unbounded_local/hpc), `task_yield_profiles`; it builds terminal execution behaviours per local/HPC
resource, the API service execution, the execution progress provider, local file sources, and all retained-input
result/return readers (flux balance, protein structure, fluorescence, expression NMF, ATAC, chromatin).

## What it reports to its parent

`to_parent.py`: required return `execution_handoff_refs` when the parent is A101 and an annotation task is
required. Fact sources: native HMMER/BLAST/masking/utility/database/preparation fact sources, UniProt and
appservice sources (results role), BV-BRC data and MinHash sources, `execution_handoff_refs`,
`execution_result_refs`, `execution_completed`, `execution_result_origin`, `execution_blast_hsps`, and the BLAST
grader return source for an `ncbi_blast` results role. Facts (live): `execution_handoff_refs` (sorted usable
handoffs), result refs, file sources, capture outcomes, appservice support refs, plus the closed credit snapshot
captured once at closing. `received_evidence.py` validates/resolves received handoffs and results for parents
(`received_report_facts`, `received_report_closure_facts`, `resolve_received_reference`, `received_form_references`).
`report_delivery.py`: same as the head.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| goal.py | 9 | Launch goal text. | none. |
| task_instructions.py | 26 | Own inlined copy of INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, DECISION_EXCHANGE_PROTOCOL; composition rules. | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol`. |
| configuration.py | 119 | Resource/unit/log/yield-profile configuration and reader construction. | imports `numerical.YieldController/YieldParameters`, `api_service_execution`, `execution_progress`, `library.retained_input_authority.*` readers. |
| binding_record.py | 8 | `as_record()` identity. | none. |
| execution_contracts.py | 59 | Versions, ROLES, KINDS, ROLE_KINDS, results schema, launch/native result catalogs, `_outcome`. | imports `communication`, `domain`, `execution_contracts`, `launch_instructions`, `practical_execution_*`, `practical_receipt_information`, `resource_records`, native acquisition predicates, `local_file_capture_results`, `library.blast_return_contracts`, `a101_execution_bindings`. |
| from_parent.py | 107 | Launch assignment admission, request schemas, permission rule, HPC frozen launch. | imports `hpc_launch_authentication`, `native_blast_database_result_publication`, `native_blast_standard_database_result_publication`. |
| from_parent_launch.py | 9 | Parent Launch form schema. | none. |
| blast_request_custody.py | 43 | BLAST grader request: query sequence digest and database bound to the parent request. | imports `communication`, `execution_contracts`, `library.blast_return_contracts`; `self.tool_registry._check_sequence_operand/_sequence`. |
| blast_received_context.py | 32 | Recover the annotation and axis that own a BLAST launch. | `self.store.db` on `runtime_episodes`×2 (path, request); import `library.blast_axis_summaries`. |
| blast_pending_work.py | 31 | Unresolved annotation-axis credit for pending BLAST jobs at the root. | imports `communication`, `execution_contracts`, `library.blast_return_contracts`. |
| execution_state.py | 108 | Delegate choice, parent input checks, target/selection, context target. | `self.store.db` on `runtime_episodes`, `runtime_actions`, `runtime_receipt_inheritance`×2; `self.services.record_selection`; `episode_receipts`; native database publication validators. |
| native_input_custody.py | 313 | Masking/utility/ATAC/MACS2/LUMPY/NMF/fluorescence/flux-balance input custody; recorded Results commission restore; selectors. | `episode_receipts`, `episode_return_records`, `execution_input_versions`, many `library.*` result views and `retained_input_authority` operands. |
| received_evidence.py | 351 | Received handoffs/results, received report facts, reference resolution, received form refs. | many `library.*` view/return-value imports. |
| result_acquisition.py | 209 | Result directory, windows, selected result action, publish/read result, byte-window progress, native completeness. | `self.store.db` on `runtime_actions`×2, `runtime_episodes`. |
| terminal_execution.py | 242 | `TerminalExecutionBehavior` (exec_command) used for local/HPC delegates; identical copy in api/hpc children. | imports `acquisition`, `communication`, `domain`, `practical_execution_*`, `practical_receipt_information`×3, `practical_yield`, `terminal_execution`, `terminal_scientific_evidence`×2; `services.workflow.launch_instructions`. |
| execution_operations.py | 151 | Resource information, capabilities, resource tool contracts, launch catalog, execute. | imports `bvbrc_proteome_tool_info`, BV-BRC return values, native result catalogs, `native_file_capture`. |
| internal_summary.py | 58 | Initial decision context, selected execution task, decision context. | `self.services.scientific_parent_task`; `library.native_profile_presentation`. |
| decision_inputs.py | 78 | Per-call inputs (see head). | `self.workflow.resource_context`, `.shared_information_context`, `.launch_instructions`×2, `.available_child_roles`, `.episode_bindings.initial_decision_context`, `.binding_context`×2, `.execution_expectations`, `.job_episodes`×2, `.store`×2, `.resource_estimator`×4, `.native_estimation_context`, `.native_event_information`×2, `.permits_common_action`, `.waiting_support`, `.pending_work`; `episode_work_report`×2, `hpc_prompt`. |
| decision_state.py | 55 | Single presentation incl. `job_episode_options`. | `self.workflow.store`×3, `.working_state`, `.journal`×3 (`runtime_actions`×2), `.run_id`, `.local_outcome_preview`, `.source_credit_view`, `.receipt_projection`, `.source_credit_binding`, `.pending_work`, `.delivery_status`, `.controller_binding`, `.catalog`, `.knowledge`, `.job_episode_options`, `.extra_report_sources`, `.specialist`, `.binding_context`, `.tools`. |
| task.py | 239 | Loop rules (see Task). | as the head's task.py without `sequence_homology_evidence_binding`. |
| task_decision.py | 294 | Model-call/exchange rules. | as the head's plus `.controller_binding`; no `.is_job_source`. |
| task_state.py | 115 | Per-episode state. | as the head's. |
| waiting.py | 31 | Selected wait; suspension registration. | `self.workflow.perform_selected_wait`, `.execution_handle`×2, `.execution_backend`. |
| report_delivery.py | 34 | Final form fill. | as the head's (`runtime_forms`×2). |
| credit.py | 275 | Operational credit and completion proof (see above). | `self.store.db`×8 on `runtime_episodes`×2, `runtime_observations`×2, `runtime_receipt_inheritance`×2, `runtime_record_receipts`×2, `runtime_forms`×3, `runtime_actions`; `episode_receipts.EpisodeReceipts`, `episode_return_records`, `method_loop.identities.UnitRef`, `numerical.NumericBand`, `practical_yield.ESTIMATOR_VERSION`. |
| yield_estimator.py | 76 | Launch remaining-request bounded estimator; exhaustion forecast. | imports `numerical.BoundedYieldController, NumericBand, YieldController, YieldEstimate, YieldParameters`, `practical_yield.PracticalYieldEstimator`×2. |
| to_parent.py | 288 | Return sources, fact sources, facts, resolve, validate_report. | many `library.*` view imports, `local_file_capture_results`, `native_*_results.empty_facts`, `native_hmmer_acquisition.ORIGIN`, `episode_bindings`×2. |
| episode.py | 68 | Identity, child roles, allowed children, permitted actions (hpc ancestor drops reason/wait), `context_hook_applies`, (role, binding path) → preparer/receiver map. | old registry declarations (`binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `decision_source_type`, `_private_practical_estimator_owner`). |
| to_child_api_job_execution.py / to_child_local_job_execution.py | 29 each | Commission one API / local resource child. | `workflow.store.validate_scope`, `.expanded_contract_form`, `.episode_bindings.for_child`×2/`.entry_roles`, `.binding_context`×4, `.child_initial_report_input`, `.specialist`, `.available_child_roles`, `.annotation_child_roles`, `.services.capabilities`, `.launch_instructions.materialize`, `.run_id`. |
| to_child_hpc_job_execution.py | 32 | HPC child; must request execution_handoff_refs under an hpc ancestor. | same set. |
| from_child_api_job_execution.py / _hpc_ / _local_ | 47 each | Typed custody of the resource child's handoff form. | `workflow.receipts`×3, `.is_job_source`×2, `.store`×7 (`runtime_report_attempts`×2), `.progress_provider`×4, `.specialist`, `.binding_context`×4, `.episode_bindings`×2, `.native_timing_information`, `.job_episodes`×2, `.receive_tool_attributions`, `.run_id`×6; `delivery_counterpart`×2, `EpisodeReturnRecords`. |

## Differences from similar episodes

- vs the A101 head: operational (not scientific) credit, router goal, `execution.capabilities` only, inlined prompt
  copy, single presentation with `job_episode_options`, no `process.*` tools, no closed-request execution guard.
- vs its api/hpc children: it is the only one with children, the only one that holds a multi-request `requests`
  map, uses the BoundedYieldController over remaining requests (children use an accumulation estimator with a
  practical completion forecast), and has BLAST received/pending context for the root and the scientific owner.
- Parallel family `resource_work_submission` exists under the same parent (documented separately).
