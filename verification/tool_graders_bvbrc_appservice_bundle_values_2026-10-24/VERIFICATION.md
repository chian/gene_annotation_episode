# Pure AppService acquisition and artifact-bundle values

This component implements only two deterministic constructors in
`gene_annotation_episode/bvbrc_appservice_bundle_values.py`. It adds no network
operation, Store lookup, publication, scientific parser, score, episode, prompt,
retry, resource decision or controller observation. Root owns the consuming
custody, executor and publication paths.

## Exact interfaces

```python
build_acquisition_value(prepared, event, snapshot, *, common_receipt,
                        publication_inputs, acquisition_receipt_ref)
# -> {contract: "AcquisitionReceipt" | "CommonReceipt", value, diagnostics}

build_artifact_bundle(publication_inputs, *, original_task, acquisitions,
                      input_bindings, query_bindings)
# -> existing ArtifactBundle
```

The first function consumes actual C4 `PreparedOperation`, `Event`,
`SourceSnapshot`, host-retained `CommonReceipt`/`SnapshotBinding`, and frozen
`PublicationInputs`. The acquisition's own reference is explicitly supplied by
the host, including its explicit provisional-reference codec before persistence.
No identifier is manufactured here. A selection, mapping or schema conflict
returns the common retained source plus a closed diagnostic. Absent bytes do not
become an artifact. A failed HTTP response keeps its exact body in a failed
acquisition receipt; it is excluded from the bundle's artifact members.

All selected requirement IDs must exist and agree with the exact selected role,
format and non-null `exact_object`. No first-requirement fallback exists.
Source, artifact, byte count and digest come only from the supplied snapshot
binding and are checked against actual supplied bytes. Task/object/capability
relations come from the bound resolved download. Declared producer-rule and
transformation evidence must match frozen `SourceEvidence` exactly; a producer
source must be one of the host-frozen source references. Membership is a pure
relationship check, not a substitute for host custody or an evidence interpreter.

The second function consumes an ordered list of exactly
`{receipt_ref, receipt: AcquisitionReceipt}`. The first-occurrence references
must equal the frozen prior list followed by the current acquisition, when a
current mapping exists. A prior receipt's publication digest belongs to its own
historical envelope, which the host authenticates; only the current receipt's
publication digest is compared with the current inputs. Wrong handoff,
request, selector, selected arguments, source/digest, task or changed dependency
set is rejected. Input bindings are the exact original request's bindings.
Query bindings are explicit supplied records validated by the existing bundle
contract; none are inferred from titles, paths or taxa.

`acquisition_receipt_refs` is unique under the existing schema. Distinct receipt
references for duplicate bytes all remain. A repeated exact reference also
retains its repeated artifact entry and a duplicate diagnostic. A repeated ref
with a changed receipt is rejected. Changing a metadata receipt does not make
the same task/object/range/bytes independent. Unselected support acquisitions
remain in the receipt provenance but cannot satisfy an output requirement.

## Status and quantities

`AcquisitionReceipt.status` preserves `qualify_download.status`, which describes
the native transfer/representation. In particular, a valid HTTP 206 slice may
have status `ok` and `object_complete=no`. Original HTTP status, body
completeness, requested and observed range, observed total size, exact bytes and
digest remain distinct. No response is truncated to fit a request. Explicit
zero bytes with complete length zero is different from missing or truncated
bytes. Unknown object size is never replaced with the received byte count.

`ArtifactBundle.status=ok` means every required artifact is present as a
successful complete object under the original declared selection. It does not
validate native scientific format or imply completion of `requested_projection`.
That endpoint requires the separate scientific adapter and original typed
projection checks. Unknown producer byte version and weaker task associations
remain exact qualifications; they are not universal completion gates. Stronger
scientific assertions require the corresponding separately supplied evidence.

Missing required outputs use `kind=output_bytes` and exactly these reason codes:
`output_bytes_missing`, `download_failed`, `download_invalid`,
`download_incomplete`, `object_completeness_unproven`. Optional requirements do
not become mandatory. Supplied scientific metadata is copied from the original
frozen `PublicationInputs.supplied_evidence`.

Concrete synthetic examples in `EXAMPLES.json`:

| Supplied observation | Exact constructor result |
| --- | --- |
| 200 body `abcdef` ignores requested bytes 2–4 | All 6 bytes retained, status 200, requested range `[2,4]`, no observed 206 range, complete object. |
| Incomplete 206 bytes `cd` for declared range 2–4 of 6 | 2 actual bytes, body incomplete, declared range retained, object incomplete, partial acquisition. |
| Complete 200 empty body with length zero | 0 bytes, complete object, usable required artifact. |
| No acquired required object | No artifact, missing `output_bytes`, partial bundle. |
| First of two selected required outputs | Partial bundle, only `r2` missing. |
| Later selected second required output with frozen first receipt | Both retained, bundle `ok`; earlier partial remains unchanged. |

These are operational measurements and validation facts. No annotation
confidence is calculated.

## Inspected and verified scope

Read the immutable authoritative attachment in full, `AGENTS.md`, `GOAL.md`,
`EPISODE_STRUCTURE.md`, `TIME_AWARE_ESTIMATION.md`, relevant library/grader design
instructions, the BV-BRC inventory rows, the complete current AppService
execution proposal and service-input/host-parts contracts. Read the full runtime
contract and native reader modules and C4b service; inspected the relevant
support-receipt, record-retention, manifest/capability-binding and actual host
acquisition handoff paths. The established BLAST parser/sheet/calculator
separation was used as a boundary reference; no BLAST behavior changed.

Tests use actual C4b `prepare`/`decode` with explicitly synthetic native download
snapshots and schema validation. Sockets are disabled. Saved-value replay also
disables Store reads. Verification includes missing, zero, partial, failed and
unknown completeness; 200 ignored Range; 206 incomplete and valid slices;
impossible ranges; wrong object/task/selector/source; exact producer provenance;
multiple sequential required outputs; support/unselected exclusion; changed
dependencies; explicit query associations; retained duplicate receipts; role
and format conflicts; preservation of weak/unknown producer identity; and no
implied scientific projection completion.

Run the focused tests and regenerate examples with:

```bash
.venv/bin/python -m pytest -q tests/test_bvbrc_appservice_bundle_values.py
.venv/bin/python verification/tool_graders_bvbrc_appservice_bundle_values_2026-10-24/write_examples.py
```

Exact test output, elapsed time and source hashes are recorded in
`VERIFICATION.json`. This component verification does not establish real host
custody, published receipt persistence, native producer output, live BV-BRC
access, scientific grading, practical completion or full episode communication.
