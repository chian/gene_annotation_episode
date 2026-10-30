# Infernal preparation capture — workload252

Implemented only the new acquisition module, its new tests and this verification
directory under the frozen247/C1 handoff. No existing runtime, dispatch, parser,
calculator, prompt, inventory or scientific observation code was changed.

## Behavior and consumer boundary

The five public APIs match CAPTURE_HANDOFF_001.md. Original bundle qualification
is pure; it validates the original plan, compiler-produced argv/operation/env,
ordered inputs and copies, native failure contexts, and output associations.
Actual capture validates the original local reservation and target before
retaining its manifest and whole selected files in Store. It freezes the exact
target intent before reservation reads and freezes the qualified original plan.

Association identity is direction, role, ordinal and relative path. Repeated
partition inputs remain ordered. A calibration working copy and selected output
share one captured file and one content-addressed artifact, while retaining two
rows with their distinct input/output formats. Input custody uses final measured
bytes; the original bundle keeps expected, staged and final identities. Changed
or partial inputs therefore do not become claims of preserved original inputs.
Root's result implementation must continue to qualify those input identities
before supplying original scientific operands to the pure grader.

Capture completeness describes custody of declared surviving bytes. Producer
failures and absent selected outputs remain in the original bundle. Unexpected
bytes at a selected but declared-absent path are retained as invalid artifacts
with an explicit association/path failure. This is not a recursive inventory of
temporary/cache/unselected files. Safe valid siblings survive other custody
failures. Shared path measurements must agree across all declared associations.

Replay uses only saved capture intent/plan and retained Store bytes. It validates
row order, associations, checksums, sizes and reported failures before accepting
completion. It never reopens the original reservation, starts native work,
invokes a scientific parser, reacquires data or makes a network call. Published
sources are execution provenance with the original attempt identity and unique
auxiliary artifact references; they create no scientific observations or scores.

## Executed verification

The final suite is `capture_002/receipt.json`: **143 passed in110.82seconds**.
Its systemd service-wall interval was111.376073128seconds. It used the existing
`local_jobs.run_local_job` with21474836480bytes RAM,4294967296bytes scratch and
no wall cap. Observed allocated scratch was22958080bytes. All tracked source
hashes, original native records and test identities were unchanged during the
run. `capture_001` is the preserved earlier137-pass run; its count is not added
to the final suite.

The suite includes pure original-bundle validation for all27 retained native
program/modes from producer001. Four cases additionally read the real original
producer003 local reservation, acquire its exact bytes, publish its source and
replay with original reads and acquisition forbidden. These original native
producer files were never moved, modified or deleted. The producer's original
native lifecycle receipts and all exact file hashes are linked by
NATIVE_CAPTURE_EXAMPLES_002.json and its producer index.

| Native case | Native rc | Input/copy/output rows | Selected paths | Distinct byte artifacts | Unique selected bytes | Capture complete |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| cmemit consensus | 0 | 1/0/3 | 4 | 3 | 9732 | true |
| cmcalibrate calibrate | 0 | 1/1/3 | 4 | 4 | 22375 | true |
| cmcalibrate merge_scores | 0 | 3/3/3 | 8 | 6 | 285457 | true |
| cmcalibrate native failure | 1 | 1/1/3 | 4 | 3 | 11192 | true |

Those quantities describe custody, not scientific confidence. In merge_scores,
the partition_scores input rows retain ordinals0,1 and each corresponding working
copy. In calibration, a single output path has both working_copy/models and
output/calibrated_models associations. The failed native calibration retains its
actual returncode1 and failure in the original bundle despite complete custody.

Other tests are explicitly synthetic envelopes or deliberate mutations. They
cover changed request/argv/mode/env/software and original identities; reordered
or repeated roles; input/copy/output path, format, size and digest faults; changed
inputs; partial staging; unavailable original inputs; declared absent versus
unlisted output bytes; symlinks and symlink parents; directories and FIFOs;
duplicate JSON keys and nonfinite manifests; unavailable manifests; partial
custody replay; forged completion/association rows; and retained Store corruption.
Synthetic replay cases actually remove their source reservation directories.
Pure validation tests forbid all filesystem reads, native execution and network.

Final owned implementation hashes:

* acquisition module:68f495297c3eebfeb7637fc402f8b69f29028029b14ece9d2cf3349a3657ae4d
* test module:318b941550255e99d0a46d6591ec91fff5198b5b07dcd26b0b600c19009c5d86

## Limits and handoff

Workload252 ran capture and validation against retained real producer output. It
did not run any new Infernal command or HPC work. Complete episode communication,
practical dispatch and preparation result/grading integration remain root-owned
work and are not established by these tests. This workload supplies no literature
grader, W05 aggregation, function-confidence value or annotation-credit mutation.

Required authoritative context resets were performed after source/native study
and before closure using the original immutable objective and all16 principles;
the exact capture and producer contracts were reread. The full original goal
remains unchanged and broader tool completion is not claimed here.
