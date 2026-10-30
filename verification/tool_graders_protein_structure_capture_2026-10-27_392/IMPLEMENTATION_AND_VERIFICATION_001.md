# Original protein-result byte capture, D2a / 392

This additive handoff implements only 380/RESULT_CAPTURE_CONTRACT_005.md and
uses root's exact shared FileFormat extension in 380/ROOT_CONTRACT_ADDENDUM_006.md.
It does not change permanent direction, scientific calculations, source
publication, receiving-parent authority, prompts, shared binding, credit or the
308-row accounting. The immutable goal attachment SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.

## Delivered ports and custody behavior

`gene_annotation_episode/native_protein_structure_acquisition.py` exports the
six exact contract ports and the two exact capture TypedDicts. It reuses A's
FileIdentity, StructuredIssue and closed issue codes; C's original run-plan,
bundle, manifest definitions and validators; execution_contracts canonical UTF-8;
and materials.artifact_file/artifact_path for streaming storage and retained
artifact verification. It imports no RNA scientific meanings.

The pure qualifier checks target run, original episode, resource, execution,
requested job/digest and the exact workspace-derived operation directory. It
does not read a filesystem or inspect lifecycle state. An invalid/unqualified
plan never populates original_plan and never authorizes opening the bundle.

First capture reads C's actual original local plan. Every producer directory
component and final regular-file descriptor is opened with O_NOFOLLOW; the
shared streaming copier reads a pinned /proc/self/fd handle. A test replaces
the original file or containing directory after opening and confirms that the
capture still receives the opened original bytes. No search for another attempt,
replacement input, retry or native launch is part of capture.

Each validated manifest row retains its original index and exact declaration,
including repeated input roles. Observed identity derives from actual retained
bytes. Changed bytes remain retained with their actual digest/length and
input_digest_mismatch. Missing, linked or non-regular producer files are
unavailable with capture_incomplete. Declared absences remain null observed/issue
rows. Failures are the ordered per-row issues, including identical issues for
distinct missing files. Capture completeness is independent of native success.

The owned absolute result directory receives immutable capture-intent.json and
capture.json using exact execution canonical UTF-8 without a newline. Replay
compares the saved intent first, validates the saved original plan and retained
bundle/files, and never reopens or resolves producer files or reads current
lifecycle state. Incomplete final captures are equally immutable. Missing or
corrupt retained bytes fail explicitly and do not authorize reacquisition.

## Actual bounded verification

The only test invocation was:

```text
.venv/bin/python -B verification/tool_graders_protein_structure_capture_2026-10-27_392/run_bounded.py check001
```

Check001: **64 passed in 412.62 seconds; exit 0.** No failed verification
attempt occurred. The original stdout, stderr, selected request, native resource
receipt and before/after pins remain in check001; no earlier record was replaced.

The launcher copied the project package, method_loop, selected tests, original
fixture helpers/data and shared contracts into a read-only source_snapshot.
Pytest, native workers and imported project modules use that snapshot. Both the
executed snapshot pins and checkout pins remained unchanged. The complete pin
lists cover the snapshot; HANDOFF_SOURCE_PINS_001.json highlights the delivered
files and direct shared dependencies. C's five execution module hashes still
match packet 390's frozen handoff.

The actual local_jobs receipt verifies memory_max=21474836480 (20 GiB),
memory_swap_max=0, runtime_max=infinity, kill_mode=control-group and
oom_policy=kill. The declared scratch budget is 4294967296 bytes (4 GiB),
wall_seconds is null, and observed scratch is 41988096 bytes. Measured service
wall duration is 413.168785167 seconds. Scratch is the existing monitored
allocated-byte limit with possible overshoot plus per-file RLIMIT_FSIZE; this
does not claim a filesystem sandbox or an instantaneous aggregate disk quota.

Tests use actual C-generated reservations, sealed manifests and worker output
for inspection, extraction and comparison of tiny synthetic native-format PDB
inputs. They test both normal native completion and deliberately injected exit 9
after valid output. The injected sitecustomize source is retained read-only in
the test's owned directory. This is a failure fixture, not a biological claim.
The C adapter uses a clearly labeled SimpleNamespace for state-owned assignment
fields; the surrounding PracticalState/Workflow integration is not claimed.

The suite covers ordered repeated metadata roles; absent sequence output;
changed, missing, symlinked and non-regular files; unsealed, malformed and foreign
manifests; plan/target/operation-directory mismatches; strict Count/boolean and
undeclared-field rejection; Unicode canonical bytes; duplicate JSON keys,
nonfinite/overflowed numbers and invalid UTF-8; producer-deleted replay; lost
and tampered retained artifacts/metadata; conflicting or missing saved intent;
noncanonical final capture; and descriptor substitution after the original open.

Network calls are patched to fail. Capture/replay checks patch scientific
calculators, scientific native dispatch and native preparation/start/status
operations to fail. Replay additionally patches the original-plan reader,
producer-file opener, native-handle read, and producer path opens/resolution.
Store.put is forbidden in the complete capture checks to establish that this
boundary publishes no scientific/source records. No network, model, API, HPC or
Aurora operation was run.

## Filled examples from actual retained captures

FILLED_CAPTURE_EXAMPLES_001.json contains eight complete original target,
bundle and capture records, their original example paths and hashes, with
separate summaries. The underlying retained Store bytes remain in check001.

| Actual case | Manifest rows | Verified | Declared absent | Mismatch | Unavailable | Capture complete |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Inspection | 6 | 6 | 0 | 0 | 0 | true |
| Extraction | 8 | 8 | 0 | 0 | 0 | true |
| Comparison | 8 | 8 | 0 | 0 | 0 | true |
| Replay after producer deletion | 8 | 8 | 0 | 0 | 0 | true |
| Native partial, absent sequence | 8 | 7 | 1 | 0 | 0 | true |
| Native partial, actual exit 9 | 6 | 6 | 0 | 0 | 0 | true |
| Changed native result | 6 | 5 | 0 | 1 | 0 | false |
| Two missing metadata inputs | 10 | 8 | 0 | 0 | 2 | false |

Inspection retained a 365-byte synthetic PDB input, a 5324-byte original plan,
a 3421-byte worker input, an 18386-byte native result, 2052-byte stdout and
zero-byte stderr. Zero-byte stderr is present/verified, not absent. Its complete
12275-byte bundle has SHA-256
`f073c4961ebca258a058ab9e68f277f4040e676fc2760b0eb97f66bc9a712f79`.

The changed native-result row remains index 3 and retains the original expected
18386-byte identity
`43a3d40f9dcada7b154f1238f3f9e05ab3a7c302357a1ff7249844a39d5afb2f`
alongside the actually captured 22-byte identity
`eaf495efe11e39981357ee1d149bbc2d521c92ef0142f44c52936ba0df6d0afb`.
Its outcome is digest_mismatch with a capture-stage input_digest_mismatch issue.
These changed bytes cannot become a verified scientific input.

## Source pins and remaining consumers

Delivered implementation SHA-256:
`bf29e5789029f3f92a6bdeaf61ab7245fefd22f513e7a691c6db10a19f118635`.

Delivered test SHA-256:
`a500a7ba62329061118a30788bf985bb664c9cbbb09e5879edc4639817d68056`.

Bounded launcher SHA-256:
`27e266edf5f41e2b7a279016a4044c24808eead8ca5ee0a6caa9c775e38b7377`.

Shared A contract SHA-256 used by this run:
`1067a8785e6a1062893f2f5a95c1f7c404387396c9576b52db3eee2b0cfbb31e`.

Root's later NativeProteinStructureResults.execute must call the capture port
inside the selected execution.results.collect action. Publication/preparation
must pass only outcome=verified retained paths/identities to its bounded result
worker, and receipt validation must use validate_protein_structure_capture.
Those actual consumers, scientific native parsing/calculation, source authority,
parent forms/communication, credit and continuation are unverified here. This
handoff makes no full protein capability or complete episode-path claim.

The authoritative objective and all sixteen design principles were read
verbatim initially, after source/native study, and again after examining the
actual retained output and before handoff; contract 005 was reread with them.
