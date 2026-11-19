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

## Carried over

Carried 19 November 2026 into the ten-file form (`goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/*`). One row per row of `runs/carry_over/functions/a101__sequence_homology_evidence__execution_job_submission.tsv` (203 rows: 71 machinery, 132 episode function; an episode-function row whose place says "not placed" is also in `carry_over_blocked/a101__sequence_homology_evidence__execution_job_submission.md`). "machinery" = old-runner machinery, not carried (reason given); "episode function" = placed in the file named. The folder was a hook-era port (`submission_source.py` and a class on `JobSubmissionBinding`); both were deleted first. Old code was read with `git --git-dir=<the disk clone>/.git show 97308b94c:<path>` because the working tree has no `.git`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | OperationalBindingRecord | machinery | old binding_record.py: the binding's own as_record() and run record (README 3e) |
| binding_record.py | OperationalBindingRecord.as_record | machinery | old binding_record.py: the binding's own as_record() and run record (README 3e) |
| blast_pending_work.py | BlastPendingWork | episode function | not placed (unplaced_old_functions): unresolved annotation-axis credit of pending BLAST jobs; it returned {} for any role but the annotation root, so never for this launch, and its received-job source (api_execution.received_blast_jobs) is the job_access service (BLOCKED-ON-JOB-SERVICE) |
| blast_pending_work.py | BlastPendingWork.annotation_axis_yield_context | episode function | not placed (unplaced_old_functions): unresolved annotation-axis credit of pending BLAST jobs; it returned {} for any role but the annotation root, so never for this launch, and its received-job source (api_execution.received_blast_jobs) is the job_access service (BLOCKED-ON-JOB-SERVICE) |
| blast_received_context.py | BlastReceivedContext | machinery | reads runtime_episodes through store.db to find the annotation and axis owning a BLAST launch (old runner table, README 3e); used only for the received_blast_jobs context of the annotation and A101 head roles, not of this launch |
| blast_received_context.py | BlastReceivedContext._blast_scientific_owner | machinery | reads runtime_episodes through store.db to find the annotation and axis owning a BLAST launch (old runner table, README 3e); used only for the received_blast_jobs context of the annotation and A101 head roles, not of this launch |
| blast_request_custody.py | BlastRequestCustody | episode function | not placed (unplaced_old_functions): the BLAST database grader request custody (query sha256 and database of the graded request against the selected API request) needs library.blast_return_contracts (no module in the library) and a sequence read through the old tool registry; it is the child's check of its commission (rule 1) |
| blast_request_custody.py | BlastRequestCustody._blast_launch_requirement | episode function | not placed (unplaced_old_functions): the BLAST database grader request custody (query sha256 and database of the graded request against the selected API request) needs library.blast_return_contracts (no module in the library) and a sequence read through the old tool registry; it is the child's check of its commission (rule 1) |
| blast_request_custody.py | BlastRequestCustody._validate_blast_launch_selection | episode function | not placed (unplaced_old_functions): the BLAST database grader request custody (query sha256 and database of the graded request against the selected API request) needs library.blast_return_contracts (no module in the library) and a sequence read through the old tool registry; it is the child's check of its commission (rule 1) |
| configuration.py | OperationalConfiguration | episode function | task.py KINDS, ALLOWED_NATIVE, _resources (checks of the configured resources and the inventory); read_from_parent.py handoff_unit and acquired_record_unit (new fields, positive and finite); yield_estimator.py task_yield_profiles; log_window_bytes, log_roles, require_private_yield, results_yield_profiles and every provider it built (api_execution, job_progress_provider, local_file_sources, native result and return readers, retained-input readers) are old-runner or service machinery, not carried |
| configuration.py | OperationalConfiguration.__init__ | episode function | task.py KINDS, ALLOWED_NATIVE, _resources (checks of the configured resources and the inventory); read_from_parent.py handoff_unit and acquired_record_unit (new fields, positive and finite); yield_estimator.py task_yield_profiles; log_window_bytes, log_roles, require_private_yield, results_yield_profiles and every provider it built (api_execution, job_progress_provider, local_file_sources, native result and return readers, retained-input readers) are old-runner or service machinery, not carried |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed credit view over runtime_episodes/runtime_observations (README 3e); the system hands the credit to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | receipt prefix over runtime_record_receipts / runtime_receipt_inheritance (README 3e F1) |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | closed credit view check (closed_credit machinery) |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed credit facts captured in runtime_forms (report_form machinery) |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed credit view re-validated against runtime_* tables |
| credit.py | ExecutionEpisodeCredit.project_credit | machinery | selects the closed view or the live projection; the live projection is credit.py credit, the closed branch is machinery |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (formula unchanged: handoff_unit x new handoff resources + acquired_record_unit x 0.0; the native result readers tried first applied to the results role only) |
| credit.py | ExecutionEpisodeCredit.credit_view | machinery | credit view record (README 3d): credit returns the number |
| credit.py | ExecutionEpisodeCredit._proof_for_action | machinery | completion proof read from runtime_actions rows and the job progress provider's targets (README 3d: completion_for_action deleted). BLOCKED-ON-JOB-SERVICE: handoff record kind (usable_handoff re-read) |
| credit.py | ExecutionEpisodeCredit.completion_for_action | machinery | completion_for_action deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit._closed_completion_verdict | machinery | reads runtime_observations of the old controller (README 3d: closed completion verdicts deleted) |
| credit.py | ExecutionEpisodeCredit.verify_completion | machinery | verify_completion deleted (README 3d) |
| decision_inputs.py | OperationalDecisionInputs | episode function | task.py _context |
| decision_inputs.py | OperationalDecisionInputs.decision_inputs | episode function | task.py _context (launch_instruction_library, selected_launch_instructions, completed_action_reports from the launch reports); resource_context, shared_information_context, child_options (the permitted-requests text replaces it), requested_action_history, pending_work, execution_expectations, resource_tool_estimates, native_execution_expectations, native_event_targets, waiting_support and contract_information_profile come from old-runner services and are not carried |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | provider patching (README 3a) |
| decision_state.py | OperationalDecisionState | machinery | old generic decision state (working state, journal reads, pending work, report deliveries, credit view, report lifecycle); the controller table is view.controller_state (messages/internal_summary.py 'controller') |
| decision_state.py | OperationalDecisionState.decision_state | machinery | old generic decision state (working state, journal reads, pending work, report deliveries, credit view, report lifecycle); the controller table is view.controller_state (messages/internal_summary.py 'controller') |
| decision_state.py | _bind_original_task_runtime_providers | machinery | provider patching (README 3a) |
| episode.py | ExecutionEpisode | episode function | episode.py ExecutionJobSubmission |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | ExecutionEpisode.allowed_children | episode function | messages/read_from_parent.py read_from_parent (permitted: which requests may be commissioned on which slot) and task.py _schema (only permitted slots are offered) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py decide/action: tool and child only; reason (nothing to commit), wait and redeliver_report are not carried (contract_misfits) |
| episode.py | ExecutionEpisode.context_hook_applies | machinery | old context-hook registry predicate by role |
| episode.py | ExecutionEpisode.child_request_preparer_for_binding | episode function | messages/msg_to_child.py msg_to_child (one branch per slot) |
| episode.py | ExecutionEpisode.child_report_receiver_for_binding | episode function | messages/read_from_child.py read_from_child |
| execution_contracts.py | launch_operation_catalog | episode function | task.py TOOLS execution_capabilities (CAPABILITIES_DESCRIPTION) |
| execution_contracts.py | native_result_operation_catalog | episode function | not placed (unplaced_old_functions): execution.results.status/collect/read are operations of the results role (execution_result_acquisition); this episode offers no results tools |
| execution_contracts.py | _outcome | machinery | old runtime outcome envelope (status, record_refs, changed_record_refs, feedback); a tool returns its value and the system journals the unit outcome |
| execution_operations.py | OperationalOperations | episode function | task.py execution_capabilities and TOOLS |
| execution_operations.py | OperationalOperations._resource_information | episode function | task.py execution_capabilities (per-resource capability entry) |
| execution_operations.py | OperationalOperations.capabilities | episode function | task.py execution_capabilities (tool_names of each resource) |
| execution_operations.py | OperationalOperations.resource_tool_contracts | episode function | not placed (unplaced_old_functions): the per-resource launch/results operation contracts with commission routes need api_execution.operation_contracts, homology_api_contracts, the BV-BRC proteome tool info and the native *_tool_info modules, none in the library; the model is shown the permitted requests and the resource capabilities |
| execution_operations.py | OperationalOperations.catalog | episode function | task.py _context 'tools' (the one operation execution_capabilities); the result-role catalogs belong to execution_result_acquisition |
| execution_operations.py | OperationalOperations.execute | episode function | task.py execution_capabilities (the one reachable branch, which returned initial_decision_context); the dispatch below it was unreachable for the launch role and is the results role's |
| execution_operations.py | OperationalOperations._has_appservice | episode function | not placed (unplaced_old_functions): gates the BV-BRC AppService fact sources, which no library module places |
| execution_operations.py | OperationalOperations._has_uniprot | episode function | not placed (unplaced_old_functions): gates the UniProt fact sources (results role only) |
| execution_operations.py | OperationalOperations._appservice_sources | episode function | not placed (unplaced_old_functions): BV-BRC AppService fact sources (library.bvbrc_*_return_values, retained_input_authority.bvbrc_*_returns) have no library module |
| execution_state.py | OperationalExecutionState | machinery | old per-role execution state over runtime_* tables and the receipts ledger |
| execution_state.py | OperationalExecutionState._delegate | machinery | picked the API or practical delegate of a child role; the children are the child folders api_job_execution, hpc_job_execution and local_job_execution |
| execution_state.py | OperationalExecutionState._practical_context | machinery | identity function of the old context |
| execution_state.py | OperationalExecutionState.initialize | episode function | messages/read_from_parent.py read_from_parent (the _launch validation) and task.py _bound; the BLAST graded launch requirement, masking/utility input checks and input versions are checks of a commission (rule 1, unplaced) |
| execution_state.py | OperationalExecutionState._check_parent_inputs | machinery | reads the parent's request from runtime_episodes (store.db) to re-check masking, utility, version and native database inputs: a child's check of its commission against old runner tables (rule 1) |
| execution_state.py | OperationalExecutionState.state | machinery | raised practical_resource_role_required for the launch: the launch has no practical state |
| execution_state.py | OperationalExecutionState._target | episode function | not placed (unplaced_old_functions): read the handoff target of the results role (execution_result_acquisition) |
| execution_state.py | OperationalExecutionState._selection | machinery | the receipts ledger and runtime_receipt_inheritance / runtime_actions reads (store.db, EpisodeReceipts, record_selection); its initial_known_record_refs is the new field received_handoff_resources of read_from_parent.py |
| execution_state.py | OperationalExecutionState._context_target | episode function | not placed (unplaced_old_functions): re-read of the handoff target against the assignment and, for a BLAST graded request, of the submitted query sha256; BLOCKED-ON-JOB-SERVICE: handoff record kind (job_progress_provider.targets, api_execution._read_handoff) |
| from_child_api_job_execution.py | receive_report | machinery | records references in the old receipts ledger, feeds the progress provider and the timing-receipt table (README 3b R1, R3, R5); what the parent takes from the return is messages/read_from_child.py read_from_child |
| from_child_hpc_job_execution.py | receive_report | machinery | records references in the old receipts ledger, feeds the progress provider and the timing-receipt table (README 3b R1, R3, R5); what the parent takes from the return is messages/read_from_child.py read_from_child |
| from_child_local_job_execution.py | receive_report | machinery | records references in the old receipts ledger, feeds the progress provider and the timing-receipt table (README 3b R1, R3, R5); what the parent takes from the return is messages/read_from_child.py read_from_child |
| from_parent.py | OperationalAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | OperationalAssignment.child_assignment_schema | machinery | child assignment schema (its frozen-HPC branch applies only beneath an hpc ancestor, which this episode does not have); each child declares its own ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | OperationalAssignment._permitted | episode function | messages/read_from_parent.py _permitted |
| from_parent.py | OperationalAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (the _launch validation); the commission checks (authenticate_launch under an hpc parent, masking/utility/native/standard BLAST database job inputs, input versions) are checks of a commission and are not carried (rule 1) |
| from_parent.py | OperationalAssignment._request_schema | episode function | messages/read_from_parent.py _request (validate_assignment / validate_api_assignment of the library); the per-resource requested_job alternatives built from the configured resources and native *_tool_info modules are not placed |
| from_parent.py | OperationalAssignment._validate_request | episode function | messages/read_from_parent.py _request (closed request, resource identity) and task.py _bound (kind against the configured resource, transport validate_assignment) |
| from_parent.py | OperationalAssignment._launch | episode function | messages/read_from_parent.py read_from_parent and _request (the BLAST graded request raises unplaced) |
| from_parent.py | OperationalAssignment._constraints | episode function | messages/read_from_parent.py _constraints |
| from_parent.py | OperationalAssignment.initial_references | machinery | initial references of the old receipts ledger (README 3b P2, F1); the job inputs travel as record_refs (read_from_parent.py, msg_to_child.py) |
| from_parent_launch.py | LaunchParentAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the same closed launch schema) |
| from_parent_launch.py | LaunchParentAssignment._parent_launch_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the same closed launch schema) |
| goal.py | OperationalGoal | episode function | goal.py GOAL (text unchanged) and task.py decide |
| goal.py | OperationalGoal.instructions | episode function | goal.py GOAL (text unchanged) and task.py decide |
| internal_summary.py | OperationalSummary | episode function | messages/internal_summary.py internal_summary and task.py _context |
| internal_summary.py | OperationalSummary.initial_decision_context | episode function | task.py execution_capabilities (execution_resource_capabilities, execution_initial_information, received_bvbrc_values); received_blast_jobs and received_minhash_values were shown only to the annotation and A101 head roles, not to the launch (not placed) |
| internal_summary.py | OperationalSummary._with_selected_execution_task | episode function | task.py _selected_execution_task (the HMMER scientific job view is unplaced and raises) |
| internal_summary.py | OperationalSummary.decision_context | episode function | messages/internal_summary.py (execution_progress) and task.py _context (execution_assignment, execution_progress, selected_execution_task) |
| native_input_custody.py | NativeInputCustody | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._masking_selector | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._masking_inputs | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._retained_masking_target | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._masking_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._utility_selector | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._utility_inputs | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._retained_utility_target | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._utility_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._versions | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._recorded_results_assignment | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._selector | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._protein_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._atac_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._chromatin_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._flux_balance_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._fluorescence_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._expression_nmf_reference_access | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._atac_inputs | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._macs2_peak_inputs | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._lumpy_inputs | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._expression_nmf_inputs | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._fluorescence_inputs | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| native_input_custody.py | NativeInputCustody._matches_flux_balance_assignment | episode function | not placed (unplaced_old_functions): custody of masking, utility, ATAC, MACS2, LUMPY, NMF, fluorescence and flux-balance inputs and the retained-input reference access of the results role; for the launch they were checks of a commission's inputs against the old Store and receipts ledger (rule 1); inputs travel as record_refs |
| received_evidence.py | ReceivedOperationalEvidence | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| received_evidence.py | ReceivedOperationalEvidence._received | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| received_evidence.py | ReceivedOperationalEvidence.received_report_sources | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| received_evidence.py | ReceivedOperationalEvidence.received_report_facts | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| received_evidence.py | ReceivedOperationalEvidence.received_report_closure_facts | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| received_evidence.py | ReceivedOperationalEvidence.resolve_received_reference | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| received_evidence.py | ReceivedOperationalEvidence.validate_received_report | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| received_evidence.py | ReceivedOperationalEvidence.received_form_references | machinery | received handoffs/results admission, resolution and validation over the old receipts ledger and the per-axis readers (README 3b R1, R3): the system admits the child's result against its own form and custody is the system's |
| report_delivery.py | OperationalReportDelivery | machinery | report_form / report delivery machinery (README 3b D1): saving the form, runtime_forms, release |
| report_delivery.py | OperationalReportDelivery.finish | machinery | report_form / report delivery machinery (README 3b D1): saving the form, runtime_forms, release |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | report_form / report delivery machinery (README 3b D1): saving the form, runtime_forms, release |
| result_acquisition.py | OperationalResultAcquisition | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._result_directory | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._windows | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._selected_result_action | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._execute_native_results | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._publish_result | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._validate_result_body | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._read_result | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._generic_result_selector_progress | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| result_acquisition.py | OperationalResultAcquisition._native_results_complete | episode function | not placed (unplaced_old_functions): results role (result directory, windows, selected result action, publish/read result, byte-window progress, native completeness): carried by execution_result_acquisition |
| task.py | OperationalTask | machinery | old decision machine |
| task.py | OperationalTask.instructions | episode function | task.py decide (instruction text) |
| task.py | OperationalTask.next | machinery | old decision loop: replay, completions, pending deliveries, source failure (README 3a, 3b R2, 3e) |
| task.py | OperationalTask.apply_response | episode function | task.py action (decode, validate against the selection schema, Rejected); the report_update validation and the delivery-resolution path belong to the old parent-written report form and are not carried |
| task.py | OperationalTask.execute | machinery | old action execution with runtime_actions rows, waits, automatic score updates, controller_value (README 3a, 3e, 3d) |
| task.py | _bind_original_task_runtime_providers | machinery | provider patching (README 3a) |
| task_decision.py | OperationalTaskDecision | episode function | task.py decide (see call and instructions) |
| task_decision.py | OperationalTaskDecision.call | episode function | task.py decide and _context (launch_instruction_library, selected_launch_instructions, completed_action_reports); the saved-call, session, restored-history, receipts and journal parts are machinery |
| task_decision.py | OperationalTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | OperationalTaskDecision.interpretation_context | machinery | decision-exchange lookup results; a lookup is a tool (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | OperationalTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.validate_contract_exchange_history | machinery | saved-request check of the decision exchange (README 3a) |
| task_decision.py | OperationalTaskDecision.exchange_decision | machinery | decision-exchange loop; its lookups into the knowledge and launch-instruction libraries are the tools knowledge_lookup and launch_instruction_lookup in task.py |
| task_decision.py | _bind_original_task_runtime_providers | machinery | provider patching (README 3a) |
| task_instructions.py | instructions | episode function | task.py decide (GOAL, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, ANSWER_INSTRUCTION); the reasoning-commit, pending_child_delivery, wait, native-event-target and decision-exchange paragraphs describe actions that no longer exist and are not carried |
| task_state.py | OperationalTaskState | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | OperationalTaskState.__init__ | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | OperationalTaskState.bind_execution_context | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | OperationalTaskState.record_execution_failure | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | OperationalTaskState.restore_checkpoint | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | OperationalTaskState.restore | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | OperationalTaskState.record_effect | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | OperationalTaskState.checkpoint | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| task_state.py | _bind_original_task_runtime_providers | machinery | source state, restore, checkpoint, record_effect (README 3e) |
| terminal_execution.py | operation_catalog | episode function | child folders (hpc_job_execution, local_job_execution): the exec_command catalog of a resource role; this launch does not use it |
| terminal_execution.py | TerminalExecutionBehavior | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | task.py _bound (TerminalExecution(...).validate_assignment of the library, called with the configured resource) |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | task.py _bound (validate_assignment of the request against the configured resource) |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.initialize | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.state | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.as_record | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | child folders (hpc_job_execution, local_job_execution): the resource behaviour of the launch_local and launch_hpc roles is carried by those child episodes; the launch role never used it (execution_state.state raised practical_resource_role_required) |
| to_child_api_job_execution.py | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (slot launch_api); the scope validation, expanded return form, initial report and report-contract declaration are old-runner machinery |
| to_child_hpc_job_execution.py | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (slot launch_hpc); execution_handoff_refs is selected on every commission (the old rule: an HPC launch beneath an hpc ancestor must request it); the old runner envelope is machinery |
| to_child_local_job_execution.py | prepare_commission | episode function | messages/msg_to_child.py msg_to_child (slot launch_local); the old runner envelope is machinery |
| to_parent.py | OperationalReport | episode function | messages/final_to_parent.py |
| to_parent.py | OperationalReport.required_return_sources | episode function | messages/msg_to_child.py SELECTION (execution_handoff_refs, execution_completed selected on every commission); the old rule applied only when the commissioner was the A101 head with an annotation task required, so no field is required in RETURN_FORM (contract_misfits) |
| to_parent.py | OperationalReport._forwards_bvbrc_reports | episode function | not placed (unplaced_old_functions): true only for the annotation and A101 head roles, false for the launch |
| to_parent.py | OperationalReport._forwards_minhash_reports | episode function | not placed (unplaced_old_functions): true only for the annotation and A101 head roles, false for the launch |
| to_parent.py | OperationalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (every source a form can name; the dotted masking and utility sources, the AppService and UniProt sources are not declared) |
| to_parent.py | OperationalReport.facts | episode function | messages/final_to_parent.py facts and final_to_parent (the closed credit facts are the system's completion['credit']) |
| to_parent.py | OperationalReport._live_facts | episode function | messages/final_to_parent.py facts (handoff refs from the launch child reports; every result and array family source empty); the native results readers' facts belong to the results role |
| to_parent.py | OperationalReport.resolve | episode function | messages/final_to_parent.py _resolver (the launch's own execution_handoff namespace); the reference access of the results role, the retained-input readers and the API return hosts are not placed |
| to_parent.py | OperationalReport.validate_report | episode function | messages/final_to_parent.py validate_report and validate_form (called by final_to_parent before it returns) |
| waiting.py | OperationalTaskWaiting | machinery | wait/suspension machinery (README 3b): perform_selected_wait, execution_handle, execution_backend |
| waiting.py | OperationalTaskWaiting._execute_selected_wait | machinery | wait/suspension machinery (README 3b): perform_selected_wait, execution_handle, execution_backend |
| waiting.py | OperationalTaskWaiting.suspension_changed | machinery | wait/suspension machinery (README 3b): perform_selected_wait, execution_handle, execution_backend |
| waiting.py | _bind_original_task_runtime_providers | machinery | wait/suspension machinery (README 3b): perform_selected_wait, execution_handle, execution_backend |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py _yield_class |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _task_yield_profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._launch_yield_controller | episode function | yield_estimator.py yield_controller (BoundedQualityYieldController, maximum = requests without a handoff x handoff_unit; the exact-zero estimator no_remaining_requests is not carried: such a launch raises) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator over a completion proof (README 3d, 7b): deleted |
| yield_estimator.py | ExecutionEpisodeYield._private_practical_estimator | machinery | PracticalYieldEstimator over a completion proof (README 3d, 7b): deleted |
