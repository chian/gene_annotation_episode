# a101/sequence_homology_evidence/execution_job_submission/api_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/api_job_execution/<file>`
(files directly in this folder; `tests/` not covered). Old binding class `ExecutionEpisode` (`binding_path =
'sequence_homology_evidence/execution_job_submission/api_job_execution'`, `commissioning_parent =
'sequence_homology_evidence/execution_job_submission'`, `roles = ('launch_api',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `OperationalTask`. A leaf: it commissions no children.

## What it is for (its goal, in its own words)

`goal.py` (the service name comes from the validated assignment):

> Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs,
> request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or
> repair from the actual available operations and received outcomes. Distinguish an immediate returned response
> from a service job that continues remotely. Preserve the actual request or job identity and submission
> uncertainty; a missing reply does not establish that no job was created. Establish the requested usable
> monitoring/results handoff from recorded service facts. The configured controller governs continuation;
> verified original handoff completion gives exact zero future credit.

For A101 this is where an NCBI BLAST (or EBI HMMER, BV-BRC, UniProt ...) request is submitted once and a usable
RID/job handoff is established for later monitor/results episodes.

## Task and instructions

`task_instructions.py` is identical to the Launch parent's (inlined INSTRUCTIONS copy, same composition rules);
with `replaces_default_instructions` the goal text above replaces the generic prompt. `task.py`: the Launch loop
**without the reasoning path** (every selection is validated against the action schema; no `reason` execution);
`wait` and tool execution remain. `task_decision.py`, `task_state.py`, `report_delivery.py`, `decision_state.py`
are the Launch parent's rules (separate copies).

## What it reads from its parent's assignment

`from_parent.py`: the assignment is exactly one request for one configured API resource (`anyOf` the API
resources' request schemas with `resource_id` const and required). `prepare_assignment`:
- validates through the API service (`api_execution.validate_assignment(..., scope)`), and that the resource kind
  is `api`;
- requires the commissioning parent role `launch` and re-reads the parent's Launch assignment;
- for a BLAST graded request in the parent, `_validate_blast_launch_selection`: the selected resource must be a
  permitted request of the parent; service must be `ncbi_blast`; the prepared query's sequence digest must equal
  the parent's `query_subject_ref` sequence; a parent-stated database must be kept;
- masking/utility input references, the parent's immutable input versions, native and standard BLAST database
  job inputs.
`initial_references` = none. On `initialize`, `_check_parent_inputs` re-reads the parent Launch request from
`runtime_episodes` and repeats the input checks, and `_validate_blast_api_parent_request` (own
`blast_request_custody.py`) binds the selected BLAST search to the parent's query digest and database.

## Children it may commission

None (`child_roles` and `allowed_children` return `()`).

## Decision state and what it shows the model

Same presentation as the Launch parent (incl. `job_episode_options`). `internal_summary.py`:
`initial_decision_context` = resource capabilities, initial information, received BV-BRC values and MinHash
values (no received_blast_jobs block — that branch is `pass` here). `decision_context` = `execution_assignment`,
`execution_progress` (its facts), plus `api_execution.decision_context(context, view)` when the service provides
one, plus `selected_execution_task` for an `ebi_hmmer` request (from the single request). `decision_inputs.py`:
as the Launch parent, including `waiting_support`.

## Tools it offers

`permitted_common_actions` = `('tool', 'wait')` for an `api_service_assignment_v1` request, else `('tool',)`.
Catalog and execution are delegated to the API service execution (`_delegate` → `self.api_execution`;
`api_execution.catalog(context)` / `.execute(...)`), i.e. the configured service's prepare/submit/status/result
operations. The non-API catalog branches (native database/HMMER/BLAST result catalogs) remain in the copy but are
not reached for the `launch_api` role.

## How its credit is counted

`credit.py`: kind `operational`; the same closed-credit snapshot rules as the Launch parent (role `launch_api`).
Live credit: native result readers if they apply, otherwise `api_execution.credit_view(context,
receiver_selection)` (the service's handoff/acquired-record credit with the configured `handoff_unit` and
`acquired_record_unit`). Completion: delegated to `api_execution.completion_for_action`; verification to
`api_execution.verify_completion(context, proof)` (after the closed-history verdict).

## Continuation (yield estimator and settings)

`yield_estimator.py` (requires `require_private_yield`): **accumulation** estimator
(`YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters))`) with
`estimate_with_context=PracticalYieldEstimator(verify_completion)` (a verified completion proof forecasts exact
zero). Profile key `launch_api:<request class>` from `task_yield_profiles`; request class =
`api_<service>[_<algorithm>][_<database>]_handoff` for `api_execution_assignment_v1` / `api_service_assignment_v1`,
else `compact_<version>`.

## What it reports to its parent

`to_parent.py`: no required return sources (the Launch parent's `execution_handoff_refs` requirement is `pass`
here). Fact sources: the Launch parent's set. Facts: `api_execution.facts(context, completion_snapshot)` over empty
native defaults, with `execution_result_origin = None`, plus the closed credit snapshot.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| goal.py | 11 | Service-specific execution goal text. | none. |
| task_instructions.py | 26 | Same inlined prompt copy as Launch. | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol`. |
| configuration.py | 119 | Same configuration as Launch (separate copy). | as Launch: `numerical`, `api_service_execution`, `execution_progress`, `retained_input_authority` readers. |
| binding_record.py | 8 | `as_record()` (binding_id differs). | none. |
| execution_contracts.py | 59 | Same contracts; imports `api_job_execution.terminal_execution`. | as Launch. |
| from_parent.py | 112 | One API request; parent role must be `launch`; BLAST selection check against parent. | `hpc_launch_authentication` (guarded off by `and False`), native database publication validators. |
| from_parent_launch.py | 9 | Parent Launch form schema (for re-reading the parent). | none. |
| blast_request_custody.py | 61 | Launch's BLAST custody plus `_validate_blast_api_parent_request` (query digest, database, service). | `self.tool_registry._check_sequence_operand/_sequence`, `api_execution.services[...].prepare('api.blast.prepare')`. |
| execution_state.py | 89 | Delegate = api_execution; parent input re-check; BLAST parent request check on initialize. | `self.store.db` on `runtime_episodes`, `runtime_actions`, `runtime_receipt_inheritance`×2; `self.services.record_selection`; `episode_receipts`. |
| execution_operations.py | 174 | Catalog/execute delegated to the API service. | as Launch plus native result catalog imports. |
| native_input_custody.py | 313 | Same input custody as Launch. | as Launch. |
| received_evidence.py | 351 | Same received-evidence rules. | as Launch. |
| result_acquisition.py | 209 | Same result acquisition. | `self.store.db` on `runtime_actions`×2, `runtime_episodes`. |
| terminal_execution.py | 242 | Same TerminalExecutionBehavior copy (unused for api role). | as Launch. |
| internal_summary.py | 55 | API decision context hook; no BLAST job summaries. | `self.services.scientific_parent_task`; `library.native_profile_presentation`. |
| decision_inputs.py | 78 | Per-call inputs incl. waiting_support. | as Launch. |
| decision_state.py | 55 | Same presentation. | as Launch. |
| task.py | 220 | Loop without reasoning. | as Launch minus `.reasoning_action_schema`, `.specialist`, `store.commit_reasoning`. |
| task_decision.py | 294 | Model-call/exchange rules. | as Launch. |
| task_state.py | 115 | Per-episode state. | as Launch. |
| waiting.py | 31 | Selected wait and suspension. | `self.workflow.perform_selected_wait`, `.execution_handle`×2, `.execution_backend`. |
| report_delivery.py | 34 | Final form fill. | as Launch (`runtime_forms`×2). |
| credit.py | 260 | API credit view / completion / verification delegated to the service. | `self.store.db` on `runtime_episodes`×2, `runtime_observations`×2, `runtime_receipt_inheritance`×2, `runtime_record_receipts`×2, `runtime_forms`×3, `runtime_actions`×2; `episode_receipts`, `episode_return_records`, `method_loop.identities`, `numerical.NumericBand`, `practical_yield`. |
| yield_estimator.py | 58 | Accumulation + practical completion forecast, key `launch_api:<class>`. | imports `numerical.YieldController, YieldParameters`, `practical_yield.PracticalYieldEstimator`×3. |
| to_parent.py | 284 | Facts from the API service. | as Launch (`library.*` views, `episode_bindings`). |
| episode.py | 56 | Identity, no children, actions (`tool`, `wait` for service assignments), `context_hook_applies` only for `launch_api`. | old registry declarations (`binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `decision_source_type`, `_private_practical_estimator_owner`). |

## Differences from similar episodes

- vs Launch parent: one request instead of a request map; no children; no `reason`; accumulation (not bounded)
  estimator; credit/facts/catalog delegated to the API service; no required return; parent must be `launch`.
- vs `hpc_job_execution`: keeps `wait` (for service assignments) and its waiting/decision `waiting_support`
  inputs, validates the BLAST selection against the parent (HPC does not), delegates to `api_execution` instead of
  a TerminalExecutionBehavior, own goal text instead of the terminal instructions, own `blast_request_custody.py`.
