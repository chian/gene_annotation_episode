# Local commission sampling frame: bounded implementation scope 001

This new record fixes a factual component contract before implementation. It
does not adopt a pending/wait estimator, horizon, prior, normalization,
comparability rule, uncertainty method, or continuation combination. The two
existing human meaning questions remain pending. Earlier permanent notes and
the fixed goal remain unchanged.

The active configured_development_002 source pin remains untouched. Implementation
and tests use a separate source copy at
`/tmp/gene-annotation-pending-frame-20261022-001`, based on the preserved 122-file
implementation in `verification/episode_assignment_transport_2026-10-21_001`.
Nothing from that working copy is installed into the active source tree. It
cannot be claimed as a connected runtime/model change.

## Why this component is needed

The current LocalReturnHistory is a valid projection of original C4 admissions
and their parent observations. It is not the population of all commissions.
Estimating report opportunities from only admitted reports would silently omit
running, unpublished, failed and returned-but-unadmitted work. Existing C1 and
public C3 readers supply a factual population without new ledgers, backend APIs,
timestamp migrations, status probes or statistical assumptions.

## Exact coding port

One new implementation file, `gene_annotation_episode/local_commission_frame.py`:

```python
class LocalCommissionFrame:
    def __init__(self, store, journal, backend): ...
    def capture(self, episode_id, *, pending, controller_credit, page_size): ...
```

Construction installs nothing. Store and Journal must share a connection and
the original run identity. `pending` is an exact existing PendingWorkV1 or null.
`controller_credit` is the exact existing source_controller_credit dictionary
or null; no channel/units are inferred. `page_size` is an explicit positive
integer read window, never a population/work cap. All returned data are detached
finite JSON.

The exact top-level output fields are:

```text
version: local_commission_frame_v1
run_id: string
episode_id: string
parent_state_at_store_read: string
controller_credit: object|null
pending_captured_at: UTC text|null
store_read_interval: {started_at: UTC text, finished_at: UTC text}
population_status: complete|unavailable
population_count: nonnegative integer|null
commissions: [CommissionRow]
return_scan: {
  status: complete|incomplete|unavailable,
  next_cursor: nonnegative integer|null,
  exhausted: boolean,
  reads: [{after_cursor, next_cursor, started_at, finished_at}]
}
unmatched_admission_refs: [string]
unavailable_reasons: [coded string]
```

Each CommissionRow has exactly:

```text
original_decision_index: nonnegative integer
handle, operation_key, commission_sha256: string
commission: exact original validated C1 spec
selection: exact original C1 selection
selected_at: original valid UTC text
accounting_status: string|null
pending_status_fact: exact matching supplied PendingWorkV1 item|null
return_presence: observed|not_observed_in_completed_scan|unknown
return_metadata: null|{
  return_id: string, cursor: positive integer,
  returned_at: UTC text,
  outcome: closed|execution_failed|interrupted|null,
  failure_code: string|null,
  read_interval: {started_at: UTC text, finished_at: UTC text}
}
admission_evidence: exact LocalReturnHistory.read_return result|null
representation_attempts: [{
  decision_index: nonnegative integer,
  delivery_ref, child_episode_id, report_contract_sha256: string,
  form_recorded: boolean,
  failure: exact saved diagnostic object|null
}]
unavailable_reasons: [coded string]
```

Nested original C1, pending and admitted E2 records preserve their existing
shapes; this component does not redesign them. UnitRef, original admission ID
and original marginal remain inside admission_evidence, without a second
top-level gain representation. The same evidence identity is one payoff, even
if a future consumer also receives E2 separately.

## Capture, identity and missing-support rules

Join or open one Store read snapshot. Validate the actual parent identity and
enumerate every original C1 row for that parent in original decision order,
regardless of its action/admission/return/observation/parent state. Validate
commission digest, run/parent/path/goal, operation and child identities, and
original action/selection agreement. Conflicting present identities are errors.
An absent legacy C1 table has unavailable population/count, not a fictitious
empty population. An existing empty C1 table establishes an empty population.
Unmatched C4 admissions remain coverage diagnostics, never invented C1 rows.

Use existing LocalReturnHistory.read_return under that Store snapshot for C4/F2
and original parent raw-payoff evidence. Do not refresh a current observation,
derive a missing marginal by subtraction, project current credit, load child
archives, or change E2's sample population. Later report repair attempts retain
their decision indices and original delivery/child linkage; omit their forms.
Do not rewrite an original delivery_failed admission or its original delta.

Read only public backend return_page/load_return. Page from cursor zero in
strictly increasing order, asking for at most the remaining captured population
and the explicit page window. Stop on an empty page or once every captured
commission has a return. Never call backend status, commission, start,
acknowledge, recovery, admission or any controller. A valid page item outside
the captured C1 population makes coverage incomplete with
return_outside_commission_snapshot; it does not acquire an invented index.
Repeated/conflicting handles, nonadvancing cursors or malformed pages are
identity/contract errors. A read failure retains known observations and marks
remaining presence unknown; it does not supply fabricated absence or zeros.

The metadata allowlist is return identity/cursor/original returned_at,
outcome, failure code and the observing page read interval. C3 form, scientific
contents, findings, child credit, archives, pending descendants and unadmitted
record references never enter the output. Validate returned envelope identity
against the original C1 and require its timestamp to equal its page timestamp.
A failed envelope read preserves the observed page identity/time with null
outcome/failure code and a specific unavailable reason.

Record actual UTC read brackets. Public C3 does not expose events.observed_at;
returned_at means envelope production, not exact durable publication or parent
receipt. Store/backend reads are separately bracketed and are not one atomic
cross-database snapshot. A complete scan's absent return is an observation at
that scan, not automatically a statistical censor. No exact historical receipt,
closure or controller-observation time is fabricated.

Use local_commission_frame_identity_conflict for conflicting saved identities
and local_commission_frame_invalid_input for caller/shape errors. Unavailable
reasons include commission_population_unavailable,
controller_credit_binding_unavailable, pending_snapshot_unavailable,
return_scan_unavailable, return_envelope_unavailable,
return_outside_commission_snapshot and report_attempts_unavailable. Preserve
specific existing E2 reasons inside admission_evidence. A backward UTC bracket
is a specific clock-order failure, never a clamped elapsed measurement.

## Parallel ownership and evidence

The implementation worker owns only the new module in the isolated copy. An
independent verification worker owns only new
tests/test_local_commission_frame.py there. Both receive this complete contract;
tests use actual isolated C1/C3/C4/F2 records with synthetic contents. Root owns
review, the isolated copy, verification execution and any later integration.
Existing production files and original test fixtures remain byte-identical.

Verification must cover the complete population and privacy boundary, original
signed payoff/completion order, no writes/status/archive loads, frozen pending
facts, truthful absence/unavailable coverage, returned-but-unadmitted work,
closed parents, delivery repair, pagination, read failures and present identity
conflicts. Existing E2 checks establish that its original projection remains
unchanged. No model/network/native/child execution is authorized by this scope.

Runtime integration and saved-context/reconstruction changes require their own
fixed consumer contract after the numerical meaning is chosen. This component
alone does not complete E, produce an arrival/payoff forecast, alter stopping,
or establish configured scientific child behavior.
