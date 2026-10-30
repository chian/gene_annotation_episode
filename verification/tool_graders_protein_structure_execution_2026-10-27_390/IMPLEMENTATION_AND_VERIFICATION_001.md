# Protein structure local execution handoff, 390

This additive record describes C's implementation and bounded engineering
verification. It does not alter the immutable goal, 380 contracts, inventories,
annotation credit, literature grading or W05. All scientific inputs in this
packet are labeled synthetic native-format fixtures, not biological observations.

## Owned implementation

- `native_protein_structure_contracts.py`: exact closed 380/001 section 9
  requests, bindings, software, jobs, run plans, native unions and manifests;
  003 native-envelope validators; exact command compilation; original identity,
  operation, mode, software, role, SHA/length and path relationships. It imports
  A's scientific definitions and validators, not B's calculator.
- `native_protein_structure_worker.py`: supplied-byte dispatch for inspection,
  sequence extraction, fit/evaluate and supplied/received-transform evaluation.
  It uses A's parsed coordinates, sequence maps, metadata and correspondence,
  then B's sheet builder and calculator. Received components use B's 004 public
  validator without refitting. The worker contains no aligner or acquisition.
- `native_protein_structure_driver.py`: one selected worker process, explicit
  staging, software verification, original controls, complete declared manifest,
  valid partial outputs and one immutable sealed attempt. A started unsealed
  attempt cannot silently rerun. A sealed replay rechecks every retained file.
- `native_protein_structure_local.py`: reservation/readback through the existing
  `native_lifecycle` and `local_jobs`. Preparation does not start work. The actual
  driver and worker commands use the selected Python executable. Requested worker
  argv and durable driver argv remain distinct.
- `native_protein_structure_tool_info.py`: three substantive four-field entries
  for inspection, extraction and comparison; comparison retains two explicit
  scientific modes. Separate closed callable contracts commission launch and
  its configured launch_local child.

Only these five modules, their three assigned test files and this packet were
written by C. Shared episode/resource/practical/communication integration is
owned by root/D and remains outside this handoff.

## Verification receipts

Each `checkNNN` retains selected_request.json, stdout/stderr, the actual local
receipt, source snapshots and before/after source pins. Every pytest invocation,
native subprocess, parser, alignment and calculation ran inside `local_jobs`
with 20 GiB RAM, 4 GiB scratch, wall_seconds=null, zero swap, an owned working
directory, temporary directory and cache. No API or Aurora operation occurred.

| Run | Actual result | Source pins | Meaning |
| --- | --- | --- | --- |
| check001 | 2 collection errors, 0.39 s, exit 2 | unchanged | Invalid dotted imports of hyphenated verification directory; preserved and corrected using import_module. |
| check002 | 32 passed, 1 failed, 29.82 s, exit 1 | unchanged | Nested two-alternative schema exposed reference scoping defect. |
| check003 | 3 passed, 4.22 s, exit 0 | unchanged | Local resource wrapper fixed nested alternatives. |
| check004 | 48 passed, 1 failed, 69.43 s, exit 1 | one unrelated drift | Reverse-orientation fixture used an undeclared label; corrected to fixed_is_reference. |
| check005 | 50 passed, 87.83 s, exit 0 | unchanged | Full suite including received transform without SVD and actual CLI numerical examples. |
| check006 | 1 passed, 2 expected regression failures, 5.57 s, exit 1 | unchanged | Reproduced missing pure action-root path constraint and nested dialect switch bypassing strict Count type. |
| check007 | **52 passed, 79.48 s, exit 0** | **unchanged** | Final complete C suite after both fixes. |

These runs overlap and must not be added as unique tests. Check004's sole drift
was the unimported D-owned `protein_structure_result_views.py`:
`c87afcca0a9b535d2b7886f691d5a8cee726e67f117b23de9c3ec7e1a58de862`
to `194f3b1c8c03f1e80fa784ca4a81d5ac125667d0f9dfd72179cd5b4afa4fa106`.
The runner thereafter pins explicit C/A/B modules and native lifecycle
dependencies rather than unrelated newly created protein files. The original
drift receipt remains unchanged. Final check007 reports no source drift.

Check007 verified memory_max=21474836480, memory_swap_max=0,
runtime_max=infinity, kill_mode=control-group and oom_policy=kill. Its actual
service-wall duration is 79.970103649 s and observed scratch is 6066176 bytes.
The shared runtime describes scratch enforcement as monitored allocated bytes
with possible overshoot plus a per-file RLIMIT_FSIZE; this is not a filesystem
sandbox or a claim of instantaneous aggregate disk enforcement.

## Behaviors actually exercised

The suite runs real worker subprocesses for inspection, extraction, explicit-map
fit, supplied-transform evaluation and mixed PDB/mmCIF retained-alignment input.
It runs real Biopython alignment separately on extracted synthetic sequences,
retains full native output and the normal full grading artifact, checks both
orientations, and forbids alignment inside the comparison worker. Residue
numbering includes insertion code 10A and disjoint moving numbering, so
correspondence cannot come from equal residue numbers.

Actual durable reservation/start/wait/status/reopen/collect uses the existing
native handle and resource boundary; repeated preparation/status/replay does not
run again. That adapter test uses a clearly labeled SimpleNamespace for the
state-owned fields. It does not pretend to exercise the not-yet-integrated
PracticalState assignment schema or scientific parent commission path.

Failure tests cover extra/wrong roles, duplicate paths, wrong SHA/length, staged
symlinks, selected software mismatch, resource-budget rejection before start,
an unknown started attempt, missing versus zero output length, malformed JSON,
changed sealed bytes, changed mode/software, omitted/extra manifest entries,
duration-kind errors and strict integer types. One deliberate sitecustomize
fault makes the real worker exit 9 at interpreter shutdown after publishing a
valid inventory; the driver retains every output and seals native_status=partial.
This is labeled fault injection, not a biological failure. Unknown-symbol
extraction exits 0 with retained native/map output and absent sequence.txt,
therefore capture is partial rather than a fabricated empty sequence.

## Hand-checkable actual native values

`FILLED_NATIVE_EXAMPLES_001.json` records exact file paths, SHA-256 values,
original bundles, modes, count cells, transformations and full-precision native
quantities from check007. The complete native results, original worker input,
source operands and manifest remain beside those bundles.

- Supplied row-vector rotation `[[0,1,0],[-1,0,0],[0,0,1]]` and translation
  `[3,-2,5]` map four tetrahedral moving points exactly to the fixed points.
  Evaluation uses 4 pairs, SSE=0.0 A² and RMSD=0.0 A. Fit quantities are
  not_applicable, not measured zero.
- A five-pair fixture fits the first four noncoplanar pairs and evaluates only
  the fifth, whose z coordinate differs by 2 A. Fit denominator=4 and evaluation
  denominator=1. The preserved floating output is SSE=3.9999999999999982 A²
  and RMSD=1.9999999999999996 A; the hand calculation is 4 A² and 2 A.
- The mixed PDB/mmCIF fixture retains 3 mapped pairs, 2 available coordinate
  pairs and the declared missing residue. Its fit is nonunique and evaluation
  RMSD is unavailable, not zero. The worker itself completed successfully and
  the native bundle is complete.
- Excluding four zero-occupancy moving CA atoms leaves 4 mapped pairs and 0
  available pairs. Native execution and capture succeed, while scientific RMSD
  remains null with incomplete_evaluation. This distinguishes measured zero
  population from unavailable geometric measurement.

## Embedded schema representation and size

The public document declares Draft 2020-12, includes A's unchanged definitions
plus C envelopes, and uses `allOf: [inner_resource]`. Both complete resources
have local content-derived `$id` values. The inner resource omits redundant
`$schema` and inherits the public dialect, preserving a caller's strict type
validator. Its definitions and original local `#/$defs/...` references remain
unchanged. No external schema fetch, parent schema widening or oneOf weakening
is used.

Actual generated narrowed schemas pass standalone and nested callable-style
operation/arguments and practical-style assignment/requested_job consumers with
two differently narrowed alternatives together. Wrong operation, producer,
type and missing required fields fail inside both parents. The actual pure
bundle validator also rejects an integer-valued float in a Count field. The
earlier failures are retained in check002 and check006.

The check007 inspect schema serializes to 214901 bytes, including 106060 bytes
of outer definitions and a 108645-byte inner resource. Extraction is 214910
bytes. A diagnostic copy without outer definitions still validates under an
enclosing object; those duplicate definitions serve 003's representation rule
rather than runtime reference resolution. Production schemas retain them.
The actual JSON files and schema_measurements.json are under check007's
`test_real_schema_standalone_ne0` retained directory. Model-service tool-schema
size limits and complete registered parent-form consumers were not verified here.

## Remaining root/D integration

Root/D must bind configured operation/mode/software at the actual resource
boundary; authenticate source, extraction, alignment, saved-sheet and transform
custody; register the exact practical requested-job alternative and result/fact
schemas; capture into the store; expose parent-requested typed projections; and
verify received information, duplicate delivery, credit and continuation through
the shared episode path. These C tests do not prove those consumers or any
configured-model investigation. No annotation-confidence or combined scientific
score is introduced. No API/HPC deployment or fixed progress tally is claimed.
