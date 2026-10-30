# Workload 037: detached optical saved-field validation

Synthetic engineering work only. The larger literature goal, A105 scoring sheet,
other nine axes and configured literature execution remain incomplete. This work
adds no scoring component, A101/target transfer, W05 aggregation, paper reading,
scientific packet, model call, TASK change, episode behavior, service wiring,
controller observation, deployment or scientific run.

## Ownership and interface

Root accepted the concrete interface and released coding before any edits.
Coordination with workload036 established these unchanged interfaces:

- `validate_optical_extraction(extraction)` returns a detached validated copy of
  the exact frozen035 extraction, without changing its version or shape.
- `validate_optical_selection(selection, extraction)` validates the extraction
  and its full inverse enrichment against the supplied original selection, then
  returns a detached validated copy of that selection.
- `VERSION = "a105_optical_saved_validation_v1"`; `ERROR_CODES` is a finite tuple
  of `ExperimentalContractError.code` values. Errors retain a specific field.

Only the NEW module, NEW test and this NEW037 artifact directory were written.
Workload036 owns storage, original selected operation/request/signature/outcome
identity, scope/source authorization, real source metadata/artifact/representation
custody and saved033 cell validation. It will consume the two validators after
new035 extraction and during saved reconstruction. Root owns that integration's
review and wider release; this receipt does not establish its execution.

## Checks and boundaries

The validator checks every required closed structure, finite enum/numeric field,
enriched witness width and UTF8 validity, consistent source/representation/artifact
bindings, overlapping saved witness bytes, exact numerical selector substrings,
absolute UTF8 token identities, physical and semantic owner identities, finite
unit conversions, source/derived origins, qualification/reason consistency,
canonical input snapshots, local connected reuse groups, covariance owners/order/
raw units/status/native and canonical matrix snapshots, covariance PSD/scaling/
shared rows, exact first-use source roster and frozen lexical dependency record.
Numeric booleans do not compare equal to zero/one. Local groups do not establish
independence. Unknown covariance is retained even when a matrix was supplied.

This is saved-field integrity, not scientific truth or reacquisition. Lexical
relation/approximation classifications were established by035 using source
context at population time. No validator invocation re-proves unseen surrounding
text, omitted units, complete source boundaries, scientific meanings or the
original covariance JSON bytes. Such missing external information is not silently
invented. No035 reader,033 calculator, `_number`, `_field_contexts`, source
callback, artifact read, runtime/model/history/controller is called. Local
literal arithmetic and the frozen finite unit vocabulary validate existing saved
relationships; they do not produce new cells.

## Read provenance

Read the full supplied goal attachment:
`/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt`.
Read root `AGENTS.md`, `GOAL.md`, complete `docs/EPISODE_STRUCTURE.md`, complete
`docs/TIME_AWARE_ESTIMATION.md`, and complete
`docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md` including
corrections. An initial combined authority output truncated its middle;
EPISODE_STRUCTURE and TIME_AWARE_ESTIMATION were subsequently read completely in
untruncated separate/sequential portions. No execution/estimation/prompt behavior
was changed. Read the per-paper review AGENTS instructions; no paper or retained
paper-specific packet was opened, so no post-paper reset is claimed or needed.

Read the complete frozen389-line035 module and complete507-line035 tests;
complete202-line033 calculator; existing detached native validators and selection
consumer (native module430–672, plus original reader/lexical implementation,
with the truncated300–430 portion repaired in a separate read); complete amount
validators/inverse selection (amount module449–582); complete amount storage
consumer; assay `_Sources`/witness/schema/measurement path (module1–220); complete
experimental contracts; and domain `canonical`/`identity`/reference schema.
036's exact interface and saved-only responsibility split were received directly
in coordination messages. No scientific source or service was accessed.

## Actual commands and results

Inspection used `cat`, sequential `sed -n` portions, `rg`/`rg --files`, `wc -l`,
and `sha256sum` on the above paths. `git status --short` reported that this
workspace is not a Git repository. File editing used shell heredocs and the local
venv Python for the new037 files only. One attempted `python -` edit failed
because bare `python` is unavailable; it was repeated using `.venv/bin/python`.

Initial command:

```
.venv/bin/python -m pytest -q tests/test_literature_optical_validation.py
```

Result:129 passed,1 failed. The failure was a test mutation assigning `[]` to a
known-covariance reason list already equal to `[]`; it did not alter the record.
No validator change was required. An intermediate combined run before the edit
took effect reported322 passed,1 failed for that same no-op test. The test now
assigns an invented reason, actually testing rejection.

Final command:

```
.venv/bin/python -m pytest -q tests/test_literature_optical_validation.py tests/test_literature_optical_inputs.py tests/test_literature_optical_calculations.py
```

Result: **323 passed in1.84s** =130new037 +193unchanged035/033 checks.
The new checks include closed/missing fields at every saved structure, forged
number/unit/key/origin/qualification/context/selection/roster/dependency fields,
UTF8 widths/token positions, censored and approximate operands, unknown and
missing quantities/units/measurements, conflicting witnesses, covariance native
and canonical snapshots, alias cancellation/reuse, and forbidden population,
source, parser, calculator and filesystem access during validation. Only fixture
construction invokes035/033-related helpers before access is disabled.

No additional broad suite, configured-model inference, actual science,
persistence/delivery through036, or complete goal execution is claimed.

## Frozen release hashes

```
4340cce4a7a659d167b15fcb707b646bd13f8d213e36e0957a454cc02eb54425  gene_annotation_episode/literature_optical_validation.py (431lines)
f7ab3b4cbe7ed42f4d1927e2d224053bb26133c83409d1fd3121e1dcca235563  tests/test_literature_optical_validation.py (316lines)
6e956a39196800d2fe2e4e841a913f40ae4f2d1c44c1fd54fc6abdc6afd6b474  gene_annotation_episode/literature_optical_inputs.py (unchanged)
f4ab7050034aa6c1cbe61a5b7f3580953f05d77895936ecb4ddeb3adaebaaa78  tests/test_literature_optical_inputs.py (unchanged)
1242c0e58e83a1ef4e4e8f25bbf94737b33dc706e61794c6ff98b87ce3c5740e  gene_annotation_episode/literature_optical_calculations.py (unchanged)
```
