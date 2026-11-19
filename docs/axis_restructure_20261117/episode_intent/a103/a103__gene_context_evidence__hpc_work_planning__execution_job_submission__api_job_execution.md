# a103 / gene_context_evidence / hpc_work_planning / execution_job_submission / api_job_execution

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/execution_job_submission/api_job_execution/<file>` (files directly in the folder; no grading/ or scoring/ subfolder; `tests/` not read). Old role: `launch_api`. `binding_path = '.../execution_job_submission/api_job_execution'`, `commissioning_parent = 'gene_context_evidence/hpc_work_planning/execution_job_submission'`, `roles = ('launch_api',)`, `entry_roles = ()`, `replaces_default_instructions = True`, renderer `render_api_job_prompt` (presentation `present_api_job_task`).

## Purpose (goal, in its own words)

`goal.py` `APIJobGoal.instructions` (service taken from the validated assignment):

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair from the actual available operations and received outcomes. Distinguish an immediate returned response from a service job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply does not establish that no job was created. Establish the requested usable monitoring/results handoff from recorded service facts. The configured controller governs continuation; verified original handoff completion gives exact zero future credit.

It runs one API service request (for example NCBI BLAST, EBI HMMER, BV-BRC services) chosen by the launch parent, one operation per turn, until a usable monitoring/results handoff is recorded.

## Task and instructions

- `instructions.py`: the binding's goal, tool-knowledge instructions, launch-instruction-library instructions, the pending_child_delivery repair paragraph, the `pending_child_` wait paragraph when wait is permitted, the native_event_targets paragraph when available, and the exchange-protocol history rewrite. Unlike the launch parent and the native children it does not append `REASONING_COMMIT_REQUIREMENT` (no reason action).
- `task.py` (`APIJobTask`): same loop as the parent, but the reasoning-commit emptiness check is removed (selection validated against the selection schema unless it is a permitted reason action), no `_validate_hpc_launch_report_contract`, and report updates validated with `grain='launch_api'`.

## What it reads from its parent's assignment

`from_parent.py` `APIJobAssignment`:
- `child_assignment_schema(parent, role)` = `assignment_schema(role)` = `anyOf` of the selected request schemas of every configured resource whose kind is `api` (`{'not': {}}` if none). Each request schema is `api_execution.assignment_schema(resource_id)` with `resource_id` const and required.
- `prepare_assignment`: validate the request; `api_execution.validate_assignment(selected, scope=scope)`; resource kind must be `api` (`execution_resource_kind_conflict`); parent role must be `launch` (`resource_child_role_owned_by_launch`); re-validate the parent's original launch assignment (`parent_launch_contract.parent_launch_schema`, independent of this child's role) and check the BLAST launch selection against it (`_validate_blast_launch_selection`); masking/utility inputs; immutable input versions of the parent launch; native BLAST database / standard database input validation.
- `operations._check_parent_inputs` (on initialize and every execute): reads the parent's saved request (`runtime_episodes` by path), re-validates its launch assignment, `_validate_blast_api_parent_request`, masking/utility inputs, immutable versions and BLAST database inputs; missing parent row raises `execution_original_launch_assignment_unavailable`.
- `required_return_sources` returns `()` (the parent's version returns `execution_handoff_refs` for launch).

## Children

None: `child_eligibility.py` returns `()` for `child_roles` and `allowed_children`.

## Decision state and what it shows the model

`decision_state.py` and `decision_inputs.py` are the parent's copies (the latter with `launch_api` as the execution-expectations role). The binding's `decision_context` (`internal_summary.py`) gives `execution_assignment`, `execution_progress` (its facts), plus whatever `api_execution.decision_context(context, view)` adds, plus `selected_execution_task` built from the single assignment when the scientific parent task is available and the request is `ebi_hmmer` (API branch) — other API services return the value without a selected task.

`decision_presentation.py` (413 lines, specific to this episode) holds the API launch prompt: `is_api_launch_context` (assignment version `api_service_assignment_v1` with request, service matching `api_service`, and an `api_request`), `select_profile_api_execution_values` (keeps `service, subject_ref, algorithm, database, parameters, page_size` of an `api_execution_assignment_v1`), and `render_api_launch_prompt` = TASK + STEERING:
- TASK: Scientific QUESTION (root objective, or the selected execution task's question), Assigned job, Assigned scope, Selected API work (`resource_id, service, endpoint`), Parent constraints, parent-selected tool guidance, Configured resource, Exact assigned scientific request, Execution method and decision rules (instructions), each callable operation with its instructions and argument schema, selected resource instructions, information requested by the parent, the requested controlled JSON return and the meaning of requested recorded facts.
- STEERING: completed action reports, pending child delivery, own action categories table (completed, observed signed yield, expected next yield, uncertainty, uncompleted attempts), current operational continuation (completed actions, credit, expected next gain, uncertainty, continuation cost, controller decision), yield information limits, original handoff completion (`api_execution_completed`), recorded own API outcomes (errors shown in full via `is_api_error_return`), latest own action (complete returned error when failed), complete returned feedback, own pending work, and lookup results ("Requested information; continue the same decision").
- Operational facts are filtered by `_CODE_FIELDS`, `_NUMBER_FIELDS`, `_BOOLEAN_FIELDS`, measurement names/units.
- `render_api_job_prompt` / `present_api_job_task` pick a renderer in this order: HPC, published scientific, API launch, selected execution, monitor, receiver.

## Tools it offers

`operations.py`: the catalog and execution are delegated to `api_execution` (`_delegate` returns `api_execution` for role `launch_api`): the configured service's own operation contracts. Execution first runs `_check_parent_inputs`.

Action policy: `('tool', 'wait')` when the assignment version is `api_service_assignment_v1` (a remote service job may continue and be waited on), else `('tool',)`.

## Credit

`credit.py`: kind `operational`; closed view if saved; else a native result family's view if one applies; otherwise `api_execution.credit_view(context, receiver_selection)` (the parent instead counts usable handoffs per resource). Unbounded.

`completion.py`: `completion_for_action` = native family proofs, else `_delegate(context).completion_for_action(...)` (the API execution's own proof); `verify_completion` = closed recorded verdict, else native family, else `api_execution.verify_completion(context, proof)`. The parent's `_proof_for_action` (usable-handoff proof from `runtime_actions`) is absent here.

## Continuation (yield estimator and settings)

`yield_estimator.py` `_launch_api_yield_controller` (requires `require_private_yield=True`): profile key `'launch_api:' + request_class`, where the class is `api_<service>[_<algorithm>][_<database>]_handoff` (or `compact_<version>`). Uses old `YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(verify_completion))` — gives exact zero once a verified completion proof exists. Settings: `task_yield_profiles['launch_api:<class>'] = {cutoff > 0, parameters}`. In the new layout this corresponds to the completion-with-a-target estimator (inferred).

## What it reports to its parent

`to_parent.py` `APIJobReport`: same fact-source catalogue as the parent (no terminal practical sources). `_live_facts`: a native family's facts if one applies; otherwise `{**native_empty, **api_execution.facts(context, completion_snapshot), 'execution_result_origin': None}`. Closed credit facts are merged. `validate_report` as in the parent (recorded `x-source` facts must match). `report_delivery.py` is the parent's copy.

## Configuration

`configuration.py` is the parent's `LaunchConfiguration` body under the name `APIJobConfiguration` (same parameters and validation). `binding_record.py` uses `binding_id = '.../execution_job_submission/api_job_execution'`, `VERSION = 'execution_episode_v1'`.

## Differences from sibling/similar episodes

- Only API child: own 413-line prompt renderer; `wait` permitted for `api_service_assignment_v1`; credit, completion, verification and facts delegated to `api_execution`; checks the parent's BLAST launch selection (`_validate_blast_launch_selection`, `_validate_blast_api_parent_request`); goal text names the service and stresses submission uncertainty.
- vs hpc/local: no `terminal_*.py` split (single `terminal_execution.py`, byte-identical to the parent's); no `REASONING_COMMIT_REQUIREMENT` in instructions; `selected_execution_task` filled (hpc returns it empty).
- vs parent: no children, no `execution.capabilities` tool, no handoff-count credit, `required_return_sources` empty.

## File by file

`wf.` = `self.workflow.` / `source.workflow.`. Imports are old shared-root modules (not read).

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `goal.py` | 10 | API job goal (quoted). | — |
| `instructions.py` | 20 | Same paragraphs as parent minus reasoning requirement. | wf.specialist, wf.binding_context, wf.knowledge, wf.launch_instructions, wf.permits_common_action×2, wf.native_event_information, wf.decision_protocol; runtime_prompt.INSTRUCTIONS×3, .DECISION_EXCHANGE_PROTOCOL; import runtime_prompt |
| `task.py` | 226 | Loop with grain `launch_api`, no empty-reasoning check. | as parent task.py minus wf.reasoning_action_schema / one wf.specialist / one wf.binding_context: wf.journal×7, wf.store×8, wf.execution_binding×7, wf.inprocess_replay×4, wf.completions×3, wf.completed_unit×3, wf.selected×3, wf.decision_exchanges×3, wf.run_id×3, wf.controller_value×2, ... ; runtime.*; ModelCallError; record_source_failure; tables runtime_actions×8, runtime_model_calls×2, runtime_episodes; imports runtime, providers, episode_source_failure, library.action_contracts, library.private_policy_call, read_mapping |
| `task_state.py` | 108 | Generic. | same as parent task_state.py |
| `decision_state.py` | 45 | Generic copy. | same as parent decision_state.py |
| `decision_inputs.py` | 70 | Execution expectations for `launch_api`. | same as parent decision_inputs.py |
| `decision_presentation.py` | 413 | API launch TASK/STEERING prompt (above). | providers.apply_state_frame×3, is_published_scientific_context×2, render_gene_context_evidence_prompt, _ordinary_runtime_receiver_context, DECISION_CONTEXT_VERSION, text_instructions, deepcopy, json; imports api_error_feedback, gene_context_evidence_prompt, execution_contracts, episode_work_report, library.hpc_prompt, library.monitor_prompt, native_profile_presentation, receiver_prompt, providers |
| `decision_delivery.py` | 82 | Generic. | same as parent |
| `decision_exchange.py` | 116 | Generic. | same as parent |
| `saved_decision_exchange.py` | 82 | Generic. | same as parent |
| `decision_contracts.py` | 36 | Generic. | same as parent |
| `decision_provider.py` | 18 | Dispatch with this renderer. | wf.provider×2, wf.specialist; import runtime |
| `waiting.py` | 9 | Generic suspension (used by its `wait`). | wf.execution_handle×2, wf.execution_backend |
| `report_delivery.py` | 25 | Generic finish. | same as parent |
| `episode.py` | 32 | Composition, role `launch_api`, renderer. | — |
| `action_policy.py` | 12 | tool (+wait for service assignments). | — |
| `binding_record.py` | 9 | Binding record. | — |
| `child_eligibility.py` | 12 | No children. | — |
| `parent_launch_contract.py` | 8 | Parent launch schema independent of this child's role. | — |
| `configuration.py` | 65 | Same as parent. | YieldController×3, YieldParameters×3; imports numerical, api_service_execution, execution_progress |
| `contracts.py` | 59 | Same constants; imports own terminal_execution. | same shared-root imports as parent |
| `from_parent.py` | 128 | API assignment schema and parent-checked preparation. | imports native_blast_database_result_publication, native_blast_standard_database_result_publication |
| `operations.py` | 56 | Delegation to api_execution; parent input checks. | table runtime_episodes; imports native_blast_*_result_publication, native_blast_masking_results, native_blast_utility_results |
| `internal_summary.py` | 124 | api_execution decision context; single-request selected task. | import native_profile_presentation; `self.services.scientific_parent_task` |
| `credit.py` | 39 | Credit delegated to api_execution. | — |
| `closed_credit.py` | 117 | Identical to parent. | same as parent |
| `completion.py` | 65 | Delegated completion/verification. | UnitRef×2, NumericBand×2, ESTIMATOR_VERSION×2; table runtime_observations; imports method_loop.identities, episode_return_records, numerical, practical_yield |
| `yield_estimator.py` | 50 | `launch_api:<class>` profile + completion estimator. | YieldController×2, YieldParameters×2, PracticalYieldEstimator×4; imports numerical, practical_yield |
| `to_parent.py` | 118 | API facts with null result origin. | result-view module imports (as parent) |
| `received_information.py` | 113 | Same as parent. | result-view imports |
| `received_record_selection.py` | 35 | Same as parent. | — |
| `received_reference_custody.py` | 160 | Same as parent. | imports bvbrc_homology_returns, hmmer_native_result_views |
| `report_reference_access.py` | 115 | Same as parent. | imports episode_bindings and result modules |
| `result_records.py` | 260 | Same as parent. | EpisodeReceipts×2; tables runtime_actions×2, runtime_episodes, runtime_receipt_inheritance×2; imports episode_receipts, execution_input_versions, result views |
| `terminal_execution.py` | 185 | Byte-identical to parent's single-class terminal behaviour (built for any local/HPC resources configured alongside). | PracticalYieldEstimator×2; imports practical_execution_*, terminal_execution, terminal_scientific_evidence, practical_receipt_information, practical_yield |

Per-use counts: `runs/carry_over/calls/a103_03.tsv`.
