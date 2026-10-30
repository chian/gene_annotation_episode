# Chromatin complete-file capture component

Implemented the two ports accepted in 441/NATIVE_CAPTURE_007, using the existing
C1 NativeCapture/CapturedInputFile records and C3 producer/worker interfaces.
This is component evidence, not a completed tool or full Workflow verification.
No tally, goal, accounting, scoring, prompt, literature, C1, C2, C3 or shared
runtime source was changed by this workload.

## Implemented behavior

`capture_chromatin_native_files` receives the caller-authenticated original plan,
selected-action receipt reference, writer-closure receipt reference and explicit
driver-start knowledge. It retains only the original attempt's fixed paths with
the actual `native_file_capture` helpers and Store. It preserves the unchanged
plan and one output row per exact `outputs[:-1]` position.

A valid final bundle supplies every exact declaration, including absent roles.
Later missing or changed files remain separate capture outcomes; the original
retained bundle is unchanged. If the final bundle is missing or invalid, each
fixed population seal is retained and checked through C3's exact validator.
Each valid seal supplies only its own five declarations. Independent valid
populations survive a later missing/foreign seal. Undeclared fixed bytes remain
diagnostics; malformed control bytes retain their artifact reference in a
located failure. Conflicting observed headers retain both seals and both sets
of declarations with explicit failures, without selecting a preferred header.

Duplicate keys, nonfinite constants/decoded values, and noncanonical JSON reject.
The actual C3 canonical encoding and its permitted single trailing newline are
accepted. Store failures propagate their shared storage-error codes; they are
not converted into producer absence. `driver_started=False` opens no producer
path and returns not_started. Missing output with unknown start remains
unsealed_attempt.

`validate_chromatin_native_capture` checks the closed record directly, without
constructing a fake worker plan. It checks original-plan equality, fixed output
order, declaration-source/role constraints, outcomes, digest/size relationships,
artifact names, retained Store-path identities and located failures. It reads
no filesystem, process or service and grants no episode authority.

## Source and contract examination

Read the original immutable attachment first and verified SHA256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The original objective and entire 16-principle block were reread verbatim after
the implementation/native examination and before this handoff, followed by the
entire accepted NATIVE_CAPTURE_007 contract. GOAL.md was not read.

Read AGENTS.md, WORKLOADS_001, POPULATION_SEAL_AND_OUTPUT_PATHS_003, the 439
capture/worker handoffs, the expanded grader direction and the fixed chromatin
inventory row. Read EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION and both practical
execution documents. Inspected complete native_file_capture, genomic-overlap
capture (reference only), C3 contracts/driver/local/preparation/result worker,
C1 validators and relevant closed records, Store artifact operations and the
local_jobs/native_lifecycle implementation. C3 confirmed exact ports and its
population-key/normalization validation correction. No record-shape change was
required.

## Actual executable verification

Every executable case ran through existing local_jobs/native_lifecycle under
20 GiB RAM, 4 GiB scratch, zero swap and no wall allocation. Each attempt retains its
original handle, request, immutable source snapshot, copied interpreter,
before/after hashes, stdout/stderr and terminal receipt. Neither attempt was
restarted; both are terminal and quiescent. Source pins and original C3 producer
pins remained unchanged.

| Attempt | Result | Purpose |
|---|---|---|
| check001 | 30 passed in 73.89 s; rc 0 | Complete 30-case capture suite |
| check002 | 3 passed, 27 deselected in 13.44 s; rc 0 | Same three native cases with stronger descriptor-level path and HDF5 guards |

These are 30 distinct cases, not 33. No executable test failure occurred. The
intentional missing, malformed, conflicting and storage-failure fixtures remain
in their original test directories and Store artifacts.

The authored-control cases cover complete capture; declared absence versus
later extra bytes; empty files; same-size digest change; changed size; missing
table with independent-population preservation; missing, truncated, duplicate-key,
NaN, overflowed/nonfinite, noncanonical and invalid-UTF8 final controls; valid
canonical newline; foreign action/input/population/normalization/path seals;
conflicting observed headers; original bundle/copy identity mismatch; explicit
not-started versus unknown; final-file and ancestor-directory symlinks; traversal
rejection before access; actual SQLite query-only Store-write failure; large
file custody; and pure detached validation with 17 cross-field forgeries.
These authored table/control bytes are not claimed as native measurements.

The large-file case retained all 67,108,864 bytes through actual Store helpers,
SHA256 `281e519df3077b557c6b03f5da83c4e8d397219259615dd7c3308f89cae8f2a6`.
Its Python tracemalloc peak during capture was 2,241,810 bytes. This measures
Python allocations for that test, not total process RSS or arbitrary-size JSON
control parsing. Control JSON bodies are decoded in memory; file custody uses
the shared streaming implementation without previews or a new size cap.

## Genuine native-byte and numerical preservation

Separately, the three native cases read C3 check007's closed original raw,
weighted and insulation attempts. Their Cooler inputs were serialized synthetic
source datasets, and their native extraction actually executed through the
bounded lifecycle. This workload did not rerun those extraction jobs or alter
their source files. `fixtures/NATIVE_INPUTS.json` pins each original plan, handle,
producer file and actual terminal observation.

Each case calls this new capture function with real Store, compares every
retained output byte-for-byte with its original fixed producer file, passes the
exact returned record to `build_native_chromatin_worker_plan`, and invokes C3's
finite retained result worker inside the bounded test job. All requested numeric
component fields match the hand-worked expected values, including:

| Native mode | Preserved values |
|---|---|
| Raw contact | raw 6; expected 4; fold 1.5 |
| Precomputed weighted | raw 6; normalized 6; expected 7; fold 0.8571428571428571 |
| Zero contact | raw 0; expected 0; fold undefined (null); weighted zero remains 0 |
| Insulation | five cross sums [5, 1, 5, 1, 5]; z scores approximately [0.81649658, -1.22474487, 0.81649658, -1.22474487, 0.81649658]; boundary flags [false, true, false, true, false] |

check002 guards both Path opening and descriptor-relative os.open calls. Original
input-binding paths are forbidden throughout; producer paths are forbidden once
capture completes. `h5py.File` is disabled during capture and retained work.
All three still pass. Capture performs no scientific calculation; these numeric
checks use the existing C1/C2/C3 worker downstream of the exact new record.

## Remaining boundaries

The caller must authenticate original selected-action authority and terminal/
quiescent writer evidence, keep Store storage stable while read, persist the
detached capture in the existing durable action record, and validate retained
identities on replay. Pure transport validation cannot prove file contents or
receipt authority. This component neither dispatches nor monitors native work,
parses original HDF5, invokes network/LLM, grants credit nor chooses continuation.

Full scientific-library selection, child-owned result-host authority, typed
parent receipt, endpoint/credit and replay behavior remain root C4 integration
work. HIC remains outside this Cooler component. Native fixture receipt labels
are explicit engineering fixtures, not proof of full episode communication.
No full-tool completion or count increment is claimed.

Exact owned file hashes and lengths are in PRODUCTION_PINS.json. The production
capture SHA256 is `82e1da008bbc5a88cc78bbd1cf31e09773e3512fbec802cae82ac79fa664d842`.
