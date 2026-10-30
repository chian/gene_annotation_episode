# Native chromatin capture handoff

Additive implementation contract; the original user attachment remains the
goal. This subdivides root C4 from WORKLOADS_001 without changing scientific
fields, allowed episode relationships, credit, continuation or resources.

Exclusive production file: `native_chromatin_interaction_capture.py`.
Exclusive test: `tests/test_native_chromatin_interaction_capture.py`.
Evidence packet: `verification/tool_graders_chromatin_native_capture_2026-10-27_446`.
Do not edit C1/C2/C3, shared runtime, other tool, scoring or literature files.

## Exact ports

`capture_chromatin_native_files(store, *, original_plan: dict,
source_action_receipt_ref: str, writer_closure_receipt_ref: str,
driver_started: bool | None) -> dict`

`validate_chromatin_native_capture(value: object, *, original_plan: dict) -> dict`

The return is the existing C1 `NativeCapture`, with exactly these fields:
`original_plan`, `source_action_receipt_ref`, `writer_closure_receipt_ref`,
`driver_state`, `bundle`, `files`, `failures`. The plan is the unchanged C3
`RunPlan`. `files` is one `CapturedInputFile` per `plan.outputs[:-1]`, in that
exact order. The final output is the native bundle and has its own `bundle`
slot. Every row retains its exact `OutputSpec`, declaration source
(`bundle`, `population`, `none`), actual `NativeFileCapture` or null, and actual
`RetainedFile` or null. No invented additional capture record is needed.

The pure validator checks closed types, exact original-plan identity, output
order/roles/paths, permitted declaration sources, all capture-state/digest/size
relationships, actual artifact naming, retained-path consistency, and failure
locations within the selected job. It reads no file, polls no process and grants
no authority. It must not manufacture a worker directory or use a fake worker
plan to validate this record.

## Ownership and acquisition

The result host authenticates the original action and terminal/quiescent writer
evidence before calling capture. These supplied receipt references record that
handoff; this helper does not authenticate episode receipt authority or own a
model decision. `driver_started=False` requires affirmative caller-held evidence
that this exact driver never started. Missing output does not establish that.
For that false case, return `not_started`, no captured files, and actual located
unavailability without opening producer paths. Otherwise absent/invalid final
bundle means `unsealed_attempt`, not `not_started`.

Use existing `native_file_capture` complete-file custody functions and actual
Store. Read only fixed paths under the original attempt directory. Never read
original input-binding paths, software paths, services, native lifecycle or a
different attempt. Hash/size mismatch preserves actual captured bytes and its
typed failure; it cannot use those bytes as the declared scientific table.
Storage failures are not producer absence and must not be silently recoded.

Capture and validate the final bundle against the unchanged C3 plan first.
When valid, authenticate each exact declaration and preserve capture results for
every output, including explicitly absent roles. The original bundle remains
unchanged when a later table is missing. Current loss is represented separately.

If the final bundle cannot qualify, independently retain and validate each fixed
population seal through C3's `validate_chromatin_population_seal`. The current
seal includes441/003's native header. Each seal can authenticate only its own
five table roles. Preserve earlier valid populations when later work failed.
Conflicting claims must remain explicit; do not choose a favorable declaration.
Other fixed output bytes, including input copies and logs, may be retained as
undeclared diagnostic bytes, with no invented scientific interpretation.
Invalid control bytes remain retained with their artifact reference in the
failure record even when they cannot occupy the valid `bundle` slot.

Strict control decoding rejects duplicate keys, nonfinite values and altered
canonical encodings. Call C3's existing exact plan/bundle/seal validators. A
closed shape alone does not authenticate a manifest. No parsing of original
HDF5, numerical calculation, process dispatch, credit or episode action is added.

## Consumer

Root's result host persists the detached capture in its existing durable action
record. C3 `build_native_chromatin_worker_plan` consumes `original_plan`, `bundle`,
`files`, source/closure receipt references, `driver_state` and `failures`, plus
the host-selected worker directory and the parent's `ResultSelector`.
The worker opens only retained paths. Replay validates saved records/retained
identities and does not recapture producer files. The complete results host and
its authority/credit handling are separate work.

## Verification

Use actual Store bytes and existing bounded local_jobs/native_lifecycle for
tests:20GiB RAM,4GiB scratch,zero swap,no wall allocation. Preserve immutable
source/binary pins, all failures and original native handles.

Check valid complete bundle, undeclared/absent/empty files, wrong hash or size,
missing table with other populations preserved, missing/malformed final bundle
with valid earlier seals, conflicting/foreign seals, source identity mismatch,
duplicate JSON keys, false not-started versus unknown, producer symlink and path
escape rejection, bounded handling of large retained files, actual storage
failure propagation and pure validation without filesystem access. Verify the
produced record passes C3's actual worker-plan constructor. Label authored
manifest/table fixtures separately from genuine executed native output.

Do not claim tool completion or increment counts. Report an interface gap to
root and C3 instead of changing another owner's record shape.
