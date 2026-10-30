# Native capture component ownership

Additive implementation boundary, 2026-10-27. This splits an already required
host responsibility from the pure retained-result worker. It changes no G1,
G2 or frozen428 record, scientific formula, episode or prompt. Root continues
to own original selected-action authority, actual terminal/quiescent lifecycle
qualification, durable action receipts, worker execution and typed delivery.

Fresh workload433 owns only:

- `gene_annotation_episode/native_genomic_overlap_capture.py`
- `tests/test_native_genomic_overlap_capture.py`
- `verification/tool_graders_genomic_overlap_native_capture_2026-10-27_433/`

## Exact ports and records

```python
capture_genomic_overlap_native_files(store, *, original_plan: dict,
    source_action_receipt_ref: str, writer_closure_receipt_ref: str,
    driver_started: bool | None) -> dict
validate_genomic_overlap_native_capture(value: object, *,
    original_plan: dict) -> dict
```

The caller must first qualify the existing selected original action and actual
terminal/quiescent writer through PracticalReceiptInformation/native_lifecycle.
These functions grant no execution or access authority, perform no lifecycle
observation and create no source record or episode observation. Receipt refs
identify the caller's existing original records; neither function invents one.
`driver_started=False` means actual lifecycle evidence establishes that the
driver never started. Missing files do not establish that fact. True/None mean
started/unknown; neither authorizes an inferred successful or empty result.

The detached returned closed record has exactly:

- version: `genomic_overlap_native_capture_v1`
- original_plan_sha256: canonical `execution_contracts.digest(original_plan)`
- source_action_receipt_ref, writer_closure_receipt_ref: unchanged nonempty refs
- driver_started: the supplied bool or null
- driver_state: `sealed_batch`, `unsealed_attempt` or `not_started`
- batch_file: actual NativeFileIdentity or null, including malformed diagnostic bytes
- batch: frozen428 RetainedFile or null, only for a qualified batch
- files: every frozen428 CapturedInputFile in original OutputSpec order, excluding
  the last batch_manifest spec; all missing entries remain present
- failures: existing G1 Failure records

Use existing fixed G1/G2 record validators. The pure validator returns a detached
record, rejects extra fields and validates plan identity, original output order,
formats, declaration/capture/retained joins and allowed state relations. It does
not read artifacts or grant authority. A retained path is an explicit host path,
not a source of authority. Host action receipts freeze the returned record;
this helper creates no additional receipt registry or replay mechanism.

## Capture algorithm

Validate the entire selected original plan first. Read only its exact original
attempt directory and fixed OutputSpecs. Use `native_file_capture` for every
copy and retention check; never build an artifact_ref from a digest or implement
another copier. Validated original plan paths remain unchanged.

For known never-started execution, return not_started with null captures and
paths, and located unavailable failures tied to the actual supplied closure ref.
Do not acquire imagined driver observations from files that were never produced
by that attempt.

Otherwise capture batch_manifest once. Preserve its actual captured identity
even if its canonical bytes or original request/attempt/semantic joins reject.
A valid G2 batch must have its exact canonical UTF-8 JSON plus one LF and pass
`validate_genomic_overlap_batch_manifest` against the original plan. It supplies
the complete unique ordered declaration array. Capture each declaration once;
shared canonical paths are not duplicated for each pair. Build transport files
with declaration_source=batch and exact captures. For verified identities use
`retained_native_file` to supply the real Store path; a retention failure keeps
the original capture identity but supplies no usable path and a located failure.
The qualified batch supplies driver_state=sealed_batch.

Without a qualified batch, capture every fixed standalone pair seal once and
validate usable seals with `validate_genomic_overlap_independent_pair_manifest`.
They retain declaration_source=none because no batch declared the seal. Combine
their four-role declarations by the original fixed path before capturing role
files. Identical shared declarations join one capture. Conflicting declarations
do not allow choosing either version: retain the fixed-path bytes once as
undeclared diagnostics, use declaration_source=none/capture=null, and record
located original_attempt_mismatch failures for affected comparisons. Their
retained seals remain unchanged for the worker to qualify. Unaffected pairs
remain usable. Original/parsed inputs and other undeclared fixed files are
captured once as declaration_source=none, capture=null, retained actual file or
null. Never create a declaration from observed bytes or expected filenames.
The state is unsealed_attempt, even if one or more independent pair seals exist.

Missing/bad batch qualification and all actual missing/corrupt captures retain
located G1 failures using frozen428 section7. Original source failures use
set_key, pair failures comparison_key, shared canonical failures their set_key;
the worker scopes effects on requested measurements. Preserve original facts.
Missing bytes are not malformed input and cannot establish invalid_input,
analytic empty, a successful pair, zero overlap or an original fingerprint.

## Consuming interfaces

Root's result host will authenticate the original target/action, call this
capture function once inside its selected collect action, freeze its return in
the existing action receipt, and pass batch/files/driver_state/failures directly
to `build_native_genomic_overlap_worker_plan`. Saved-sheet recalculation never
calls this native capture function. Completed action replay uses retained
identities and the frozen capture record; it never recaptures producer paths.
Workload432 reads only these supplied retained paths and keeps all G1/G3a
calculation/selection inside its bounded worker.

## Verification and constraints

Use actual Store capture with retained native427 fixture files copied into an
explicitly synthetic producer-action fixture (label it, no original authority
claim). Verify complete three-set output order and single capture per shared
canonical file, actual identity/path joins, missing/invalid batch, independent
pair seals, conflicting declarations, failed/partial pair files, absent files,
not-started behavior, digest mismatch diagnostics and missing retained bytes.
No bedtools, network, source query, worker execution or model call belongs here.
Root owns selected action, closure proof, full replay and Workflow tests.

All tests run through existing local_jobs with 20 GiB RAM, 4 GiB scratch, zero
swap and no wall allocation; retain readonly source snapshots, pins, attempts,
logs, JUnit and actual receipts. Read complete affected capture, G2 and worker
paths. Read the immutable goal fully; after substantial source/native-output
inspection and before handoff reread its objective and all sixteen principles
verbatim, then accepted418/425/428 and this contract. Preserve permanent records.
Do not edit worker432, shared hooks, prompts, annotation scores or accounting.
