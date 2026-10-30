# Rfam native JSON numerical implementation

This workload implements the supplied JSON reader, saved numerical sheet,
separate deterministic calculator, and receiver-selected numerical projection.
It does not mark the fixed remote batch row complete. The original immutable
goal, all sixteen original principles, AGENTS.md, WORKLOADS.md, the complete
Rfam contract and its additive identity/capture clarifications govern the work.
No shared integration, W05, literature, BLAST, Infernal, historical record or
fixed-row accounting file was edited.

## Implemented interfaces

- `gene_annotation_episode/rfam_batch_contracts.py`: exact typed records,
  metric/unit/missing/issue enums, request/selector schemas, explicit calculator
  parameters, identity and source checks, supplied component validation.
- `rfam_batch_inputs.populate_rfam_batch_json_sheet(content, *, input_identity,
  capture, model_metadata=None, alignment_components=None)`: full native
  single-query JSON population, exact original identity, independent scalar
  cells, physical coordinates, duplicate relationships, qualified partials,
  optional exact-source alignment components and retained unbound model metadata.
- `rfam_batch_grader.calculate_rfam_batch_components(sheet, *, parameters)`:
  all retained rows, native quantities, query spans, separate strand sums/unions,
  overlap multiplicity, represented model positions and conditional consensus
  comparisons when supplied. Recalculation makes no acquisition or execution.
- `rfam_batch_views.project_rfam_batch_result(sheet, calculation, *,
  projection, artifact_bindings)`: exact digest/row association checks and
  requested typed measured/unavailable cells only.

Exports used by integration include `REQUEST_SCHEMA`, `SELECTOR_SCHEMA`,
`PARAMETERS`, `RFAM_HIT_METRICS`, `RFAM_QUERY_STRAND_METRICS`,
`RFAM_METRIC_UNITS`, `RFAM_ISSUE_CODES`, `RFAM_MISSING_REASONS`,
`make_issue`, `rfam_digest`, `query_strand_record_key` and named validators.
Digests use `execution_contracts.canonical`. A hit key is the literal artifact
reference followed by its escaped JSON pointer. An alignment bundle must match
the exact native source hash, artifact, original hit, query occurrence, family,
strand and alignment pointer; foreign/duplicate keys never create guessed joins.

Current JSON contains no searched-model digest or release. Even an explicitly
supplied same-accession model remains unbound; display endpoints do not create a
model denominator. Different unbound model versions are retained without a false
length conflict. A claimed single model with conflicting lengths is diagnosed.

## Numerical verification

The most recent completed suite is [run_005/receipt.json](run_005/receipt.json):
**133 tests passed**: 75 numerical/parser/view/composition checks and the
independent alignment worker's 58 checks, run together after tightening shared
component validation. Tests distinguish official documentation bytes, actual
expired native result, new actual native single/multi JSON and explicitly
synthetic changes. They cover complete and empty populations, missing and
invalid independent cells, nonfinite JSON and duplicate keys, exact job/query/
capture identity, wrong references, forward/reverse/boundary coordinates,
duplicate and overlapping rows, count contradictions, interrupted bodies,
unbound/conflicting model records, alignment component composition and
misbinding, partial missing-PP correspondence, and closed projection selection.
The shared component validator additionally rejects repeated/misordered query
or model coordinate positions, PP bounds inconsistent with their native code,
and issues bound to another hit. The earlier run_004 records a harness path
mistake: the extra test path was relative to the isolated job directory, so no
tests ran. The corrected run_005 uses absolute test paths and retains that
earlier failure as a fact.

The complete saved examples are under
[examples_002/examples](examples_002/examples), with their native source hashes
and evidence qualifications in
[manifest.json](examples_002/examples/manifest.json). Each has a full parse
result, numerical sheet, separate calculation and selected projection; alignment
variants also have the exact-source component bundle. These are verification
artifacts with fixture/retained-native references, not production store receipts.

| Measurement | Official documentation JSON | Actual new single JSON |
|---|---:|---:|
| Native score, bits | 104.9 | 104.6 |
| Native E-value | 4.5e-24 | 1.4e-24 |
| Native GC fraction | 0.49 | 0.49 |
| Query span / denominator, nt | 119 / 119 | 119 / 119 |
| Query span fraction | 1.0 | 1.0 |
| Represented model positions, supplied alignment | 119 | 120 |
| Determinate consensus equal / compared | 79 / 119 | 75 / 118 |
| Conditional consensus equal fraction | 0.6638655462184874 | 0.635593220338983 |
| Full searched-model length / model coverage | unavailable | unavailable |

The real single display has one query insertion and two model deletions. These
are retained in its supplied alignment components. Without supplied components,
all correspondence quantities stay explicitly unavailable. Consensus equality is
not physical reference identity or annotation correctness. GC remains the native
rounded 0.49, not the exact whole-query 58/119.

Two duplicated 119 nt hit rows yield sum238, union119 and overlap excess119.
Synthetic intervals1..60 and40..100 yield spans60 and61, sum121, union100 and
overlap excess21. Forward and reverse populations never merge. Incomplete
populations retain observed valid subset values with false completeness.

Both tests and the separately bounded example run reloaded saved sheets before
forbidding filesystem access, sockets, HTTP and subprocess execution; the
recalculated objects matched exactly. No reacquisition or native program rerun
occurred. [examples_002/receipt.json](examples_002/receipt.json) records this run.

## Resource boundary

All test/example execution used the existing `LocalJobPolicy` and
`run_local_job`: 20 GiB RAM, 4 GiB scratch, no wall-time limit. Receipts record
commands, source hashes, output and enforced systemd cgroup memory/swap policy.
Scratch uses the existing monitored allocated-byte limit with possible overshoot
and a hard per-file limit. No local database BLAST, HPC or remote request was
executed by this workload. The transport worker owns the actual native captures.

## Inspected paths and unfinished work

Read complete BLAST pairwise sheet/components and the database sheet/calculation
construction functions as design templates only; no BLAST calculations were
applied to Rfam. Read the complete existing Infernal search reader to assess
the separately captured actual tblout profile. Read the complete separate
Rfam alignment module and current Rfam API service consumer. Publication and
typed episode custody are root-owned integration work and are not established by
these pure-function tests.

The actual multi JSON is a flattened array of six scalar hits with no query
names, sequences, original ordinals, job ID or alignments. This reader retains
its format as unsupported for scientific attribution. It never assigns by hit
order, repeated sequence digest or arbitrary first name. The independently
acquired native tblout retains submitted names and has an observed Infernal1.1.5
SCAN format1 header/footer. A reviewed additive batch/table contract and its
proper occurrence mapping are required before integrating that representation.
No JSON was passed to the existing Infernal table parser.

The fixed row also retains exact unfinished shared integration, complete batch
mapping/format coverage, producer-native richer display coverage, and unknown
searched-model release/digest/length. This workload does not claim production
episode communication or a completed remote batch grader from single-query
support. Native model/file names, program versions and thresholds observed in a
different artifact are not silently inserted into the JSON sheet.

## Additive clarification of planning examples

The planning-only `proposed-single-sheet.json` and
`proposed-single-calculation.json` in contract packet232 used an extra `#`
between artifact reference and JSON pointer. The written contract specifies
literal `artifact_ref + JSON-pointer-to-row`. This implementation, the
alignment worker and the actual examples follow that written rule:
`artifact/hits/family/0`, with no inserted `#`. Root reviewed this discrepancy
and directed preserving the written rule. The planning examples were not edited
or retroactively presented as production parser output.

Root has assigned the separately reviewed batch-table wrapper to a fresh
independent workload. This JSON workload's interfaces and ownership remain
unchanged; it does not implement a second table or alignment parser.

At handoff, the original objective and all sixteen original principles were
reread verbatim, followed by the complete current contract. The immutable goal
SHA256 still equals
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
No production source changed after run_005; subsequent edits only completed
this additive report.
