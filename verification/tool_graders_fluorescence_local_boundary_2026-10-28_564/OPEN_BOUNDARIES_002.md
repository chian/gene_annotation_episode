# Coordinator review: boundaries that are not frozen

`INTEGRATION_PROPOSAL_001.md` is preserved as the original proposal. It is not a
code-ready or frozen implementation contract. The existing fluorescence core
ports and contract557/001–007 remain established independently. The new local
job, capture, context and return declarations in001 are proposed shapes for
coordinator review, not authorization for independent owners to fill gaps with
their own incompatible records.

The complete source/consumer trace, exact source hashes, current inventory
distinctions and shared-routing edit targets are usable evidence now. The
following concrete seams still need to be settled by the coordinator before
parallel coding depends on them.

## Correct worker/process boundary

The NMF source has these distinct interfaces:

```python
# expression_nmf_result_worker.py: runs INSIDE the selected subprocess
execute_expression_nmf_worker(plan) -> dict
# Returns its validated worker-result document, writes worker-result.json and
# declares output artifact roles/digests. It does not create a subprocess.

# native_expression_nmf_preparation.py: owning host orchestration
prepare_expression_nmf_result_worker(store, *, plan, policy) -> dict
validate_prepared_expression_nmf_worker(store, value, *, plan) -> dict
# The first uses the existing bounded native lifecycle, persists intent,
# resumes the same worker handle, proves closure, and captures exact outputs.
# The second authenticates this prepared capture against the selected plan.
```

`NativeExpressionNMFResults._worker` calls the prepare port through one finite
thread task, validates its prepared capture, and reads the authenticated
execution receipt. Its actual prepared-capture keys are:

```text
{version, plan_file, execution_receipt_file, worker_result_file,
 result, outputs, failures}
```

This corrects001's sentence suggesting that
`execute_expression_nmf_worker(plan)` itself runs a subprocess. Likewise001's
proposed `execute_fluorescence_worker(plan) -> WorkerCapture` conflates two
different layers. The subprocess entry should return `WorkerResult`; bounded
host preparation should produce the separately authenticated capture. The
precise fluorescence equivalents of prepare/validate, their execution receipt,
pin snapshot, declared-output shape and capture fields were not fully declared
in001. They must be frozen together. `PORTS_001.json` retains the original entry
as proposal evidence; it must not be used as an implementation signature without
this correction.

Do not merely copy001's shorter `WorkerCapture` object and omit the NMF analogue's
actual plan file, worker result file, execution receipt and declared-output
authentication. Do not copy NMF's fit eligibility, factor dimensions, fit-call
count, NMF dependency closure or native-success predicates into fluorescence.

## Producer/consumer authentication fields

The native-driver manifest, original capture, worker result and prepared capture
cross different owners. Before assigning those owners, freeze the exact fields
and comparisons for:

- Original selected run/episode/resource/action/attempt identity and immutable
  request/plan digest; worker-result plan digest and exact frozen selector.
- Ordered event/support input indices, original input identities, requested
  parser and source/sample/channel/domain bindings; resulting parser batch
  identities and actual parser extent. The native parser may append observed
  metadata and names, so authentication must state the allowed observed fields
  rather than compare every returned Source byte-for-byte with its skeleton.
- Every declared output role, relative path, format, presence/absence, size/hash
  and captured identity; actual terminal/quiescent execution and software pins.
- Partial survival when a manifest or later batch is absent. A retained batch
  still needs its exact source/binding relationship verified before admission.
- The distinction between execution-control canonical digests and fluorescence
  core canonical bytes. Neither digest implementation should be globally changed.

001 names these required relationships but its manifest/WorkerResult tables are
not a complete final authentication contract. No owner should silently choose
additional fields or assume a source filename, Store object or digest alone
supplies producer authority.

## Durable result receipt

The source trace identifies the complete NMF receipt implementation and all
consumers, but001 does not enumerate an exact closed fluorescence result-receipt
shape. The coordinator must freeze that shape with the producer/capture records
above: original commission and selected action intent; received saved-sheet
origin or original native handoff; observation/writer closure; worker controls;
qualified files; requested fact publication; acquired-original identity; practical
delivery proof; and frozen received-prefix witnesses for closed replay.

`FluorescenceResultReceipts.validate`, publication, staged recovery and completed
replay must agree with the same fields. Independent custody/result owners cannot
invent different receipt layouts merely because the analogous method names
were listed. This is a specific cross-owner contract gap, not a whole-family
blocker or a request to restart completed core work.

## Native-report and preparation obligations

The raw/supplied native-report reader and authentication boundary remains
unfinished. `native_reports` cannot be treated as verified native observations
just because a planner supplies values, locations and a retained file hash.
The coordinator must identify an actual supplied typed-record custody path or
freeze a concrete deterministic reader for the selected native report format.
Until that exists, native report comparison is not an integrated capability;
jobs with no native report comparisons remain independently implementable.
This is an implementation requirement. It introduces no runtime approval,
reviewer, scientific acceptance gate or extra model call.

Actual preprocessing also remains unfinished, separate from encoded FCS and
already supplied prepared CSV/snapshot domains. No automatic compensation,
gain/log/time scaling, guessed parameter default or fallback is authorized by
these proposed local bindings. Required parameter evidence and the derived-domain
output/correspondence contract must be defined for any later selected preparation.

The new metadata-context projection is also a proposal: the coordinator must
decide its requested field contract and file ownership before treating it as
settled. Concrete model-facing instructions and rendering still need the user's
running review. No text was drafted or coded in this packet.

This additive note closes the review assignment by distinguishing established
interfaces, concrete proposed ports and these remaining coordinator decisions.
It does not claim that production integration, native execution, typed parent
delivery or closed replay has been run.
