# Practical execution: implementation contract, 2026-10-22

This is an additive implementation record. Earlier records remain historical
records. The user's latest instruction authorizes practical endpoint validation
to make future expected credit exactly zero immediately. It does not authorize
rewriting actual credit history or changing scientific stopping behavior.

## Fixed implementation checklist

- [x] P0. Define ownership, data handoffs and endpoint semantics before coding.
- [ ] P1. Structured preparation inventory, canonical digests, explicit mirror
  reconciliation and immutable initial snapshots.
- [ ] P2. Durable practical assignments, working contexts, selected action
  receipts, actual validation results and operational progress projection.
- [ ] P3. Opt-in contextual estimator: validated completion produces an exact
  zero future band, retaining the final signed gain and ordinary controller.
- [ ] P4. Real selected operations, resource episode binding, initial context,
  completion evidence and reconstruction through the shared method_loop.
- [ ] P5. Connected verification of setup/reuse, unsuccessful executed commands,
  replay, endpoint-specific completion and unchanged scientific behavior.
- [ ] P6. Usage instructions and an explicit account of what was actually run.

These item identities are stable. Updates append evidence rather than replacing
the list or silently dropping unfinished items.

## Episode and operation ownership

The existing resource-specific episode owns iterative choices. A command,
directory transition, file write, information request or environment operation
is a selected tool action within the shared method_loop. No tool contains an
autonomous model loop. The caller explicitly binds real execution primitives;
inventory entries cannot create callable tools. Resource selection remains
explicit. API, local compute and HPC retain distinct execution/monitoring
semantics. Preparing a resource is not completing the requested computation.

An executed command with a nonzero exit status is a completed action with an
unsuccessful native outcome. A malformed or never-executed request is feedback,
not an observation. Each completed action has one receipt, validation assessment
and cumulative-credit projection. Replaying it must not execute it again.

## Cross-module contracts

All records are JSON values, serialized with sorted keys, compact separators,
UTF-8 and allow_nan=False for SHA-256. Files containing authoritative receipts
are immutable. Mutable pointers/context use atomic replacement and locking.

### Inventory (owner: inventory implementation)

`execution_inventory.py` owns versioned component/catalog/snapshot validation,
canonical digest computation and explicit local mirror reconciliation.
Components describe environment/software/database/index/prepared_operation,
actual absolute paths, version/identity, dependencies and provenance. Prepared
operations reference a caller-bound tool name plus its actual input contract.
Inventories are descriptions of preparations, not complete episodes.

`reconcile_inventory(local_path, read_remote)` explicitly reads remote bytes
and returns a JSON snapshot containing catalog digest/content, remote status,
comparison outcome and observed time. Unavailability preserves a dated cached
catalog and explicitly reports it. A digest match establishes catalog equality,
not current executable/database usability. Snapshot construction and refresh
are selected caller/actions, never hidden in service construction or model
context reads. The original snapshot is retained for reconstruction.

### Practical records/state/credit (owner: records implementation)

`practical_execution_records.py`, `practical_execution_state.py` and
`practical_execution_credit.py` own the following contract:

* Assignment identity: `version=practical_assignment_v1`, `assignment_id`,
  `resource_kind` (local or hpc), absolute `workspace`, `endpoint`
  (usable_handoff or completed_job_outputs), `requested_job` (argv and explicit
  environment), `progress_requirements`, `completion_keys`, `initial_context`,
  `inventory_snapshot`, and `constraints`. The parent's original typed return
  form remains in the ordinary commission, not an invented free-text report.
* Each progress requirement has a unique stable `key`, explicit nonnegative
  caller-owned `credit`, and a closed predicate specification. These are desired
  facts, not an ordered itinerary or compulsory setup steps. They do not grant
  per-command/file bonuses. Initially satisfied facts establish the baseline.
* Context: revision, absolute cwd and explicit environment overrides. `cd` and
  `export` inside one subprocess do not change later action context.
* Receipt: `version=practical_action_receipt_v1`, `run_id`, `episode_id`,
  `assignment_sha256`, `operation_key`, `tool_name`, exact `arguments`,
  `context_before`, `context_after`, actual `outcome`, `validations`, timestamps.
  A canonical content digest identifies each persisted receipt.
* Each validation records `key`, `satisfied` (boolean), closed `predicate`,
  actual evidence references/values and `checked_at`. The executor supplies
  actual facts; a model cannot claim that its own work passed.
* Projection sums currently satisfied requirement credits, once per key.
  Initially satisfied facts are initial cumulative credit, not a new action.
  Repeated facts gain zero. Losses remain signed deltas at the controller.
* Completion requires the endpoint's actual requested-job identity and all
  original `completion_keys`; no model-supplied completed flag is accepted.

`PracticalState(directory, run_id, episode_id, assignment)` exposes assignment
identity, `context()`, `receipts()`, `begin(operation_key,tool_name,arguments)`,
`finish(operation_key,outcome,validations,context_after=None)`, `credit_view()`,
`completion_proof()` and `verify_completion(proof)`. `begin` freezes intent;
conflicting reuse rejects. An unfinished intent is explicit recovery work, not
permission to repeat an uncertain side effect. `finish` is idempotent for the
same content. Source validators only inspect actual selected-action facts.

The completion proof has exactly `version=practical_completion_v1`, `run_id`,
`episode_id`, `assignment_sha256`, `endpoint`, `operation_key`,
`receipt_sha256` and `validation_keys`. It is derived from a persisted receipt
and verified against that state, never reconstructed from today's environment.

### Terminal estimation (owner: estimator implementation)

`practical_yield.py` exports `PracticalYieldEstimator(verify_completion,
base_estimate=estimate_score_yield)`, a callback with signature
`(raw_signed_history, parameters, aligned_original_contexts) -> YieldEstimate`.
The base estimator runs unchanged unless the latest context carries a verified
completion proof. The context key is `practical_completion`; its value is the
proof above, augmented by runtime with `unit_ref` and `action_index`. Runtime
captures these actual identities and preserves the context for replay.

The verifier receives the proof without those two runtime fields and checks
its authoritative receipt. The estimator checks the context's actual unit and
action relationship. Valid completion returns `NumericBand.exact(0)` even before
the minimum fit window; the number and values of observations are unchanged.
The existing controller comparison then closes the episode normally. A separate
typed task-completion fact distinguishes this from yielding with partial work.
The new estimator version is opt-in. The default scientific estimator, global
version and completed scientific histories are not changed.

## Integration ownership and dependencies

Root owns operation implementations, runtime/context wiring, binding/caller
composition, reconstruction and connected tests. Inventory and state/credit
implementations do not edit runtime. The estimator depends only on the proof
contract, not inventory or executor code. Inventory is independent of receipts.
Root can implement real operations and integration against these contracts
while all three modules are built in parallel; file ownership is exclusive.

Aurora storage remains `/lus/flare/projects/BioReason-Aurora-Test`; new PBS
charges are `EpiCalib`. Home receives only the existing small directory index.
No live scientific investigation or unrelated old run is modified by tests.

## Integration refinements recorded during verification

These clarify concrete handoffs without changing episode ownership or the
original checklist. Missing facts in an action outcome are unknown, not evidence
that an earlier fact became false. Exact new observations can still invalidate
a fact and produce a signed loss. Completion freezes the original assignment
against new work, while original-action replay remains valid.

Actual diagnostic log windows and selected file byte reads must be available to
the next decision. Safe filesystem/catalog failures are recorded for repair;
unconfirmed native side effects retain their original uncertain identity. An
explicit retry names a confirmed failed execution and creates a new attempt;
recovery of an old selection never resubmits it.

The status/result operation input now also permits `receipt_ref`, identifying
an actual scoped Store receipt from an earlier launch. The receiver validates
its original job, resource, scope and execution identity, reopens that original
read-only native target, and records the new observation in the receiving
episode. It does not reopen the closed launch's controller or add work/credit
to its history. This supplies a usable handoff across episode closure without
inventing a new episode kind or a separate execution workflow.

## Completion record

P0 through P6 are implemented and verified within the scope above. The original
planning checklist is preserved rather than rewritten. Its full updated copy,
captured test evidence, actual execution scope and deployment/interface limits
are in [PRACTICAL_EXECUTION_VERIFICATION_2026-10-22_001.md](PRACTICAL_EXECUTION_VERIFICATION_2026-10-22_001.md).
In particular, a new live ALCF run and general recursive PBS monitoring are not
claimed by this practical binding.
