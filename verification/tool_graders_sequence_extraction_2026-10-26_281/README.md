# Extraction numerical workload 281

Implemented only `gene_annotation_episode/sequence_extraction_grader.py`, its
dedicated tests, `knowledge/sequence-extraction.md`, and this verification
directory. Existing sequence producers, mapping arithmetic, ToolRegistry,
source retention, Workflow, libraries/index and progress ledgers were not
edited by this workload. The immutable original goal and full required scope
remain unchanged.

## Public ports and retained data

The frozen 279 contract supplies the exact three public signatures:
`build_extraction_sheet`, `calculate_extraction_scores`, `grade_extraction`.
The root clarified the score container as `{schema, summary, ...}`: required
numerical fields are in `scores.summary`, with no duplicate top-level counts.
`grade_extraction` returns `{sheet, scores}`. The builder retains the complete
actual native result, exact input string, actual parent subject, supplied parent
mapping, effective request, numerical measurements, ordered segment rows,
categorical component states and issues. The calculator reads only that saved
sheet, checks retained-cell relationships, and computes independent numerical
components. It performs no I/O, Store access, native execution, network request,
LLM call, resource choice, annotation scoring or credit assignment.

`segments` stay in request order and carry zero-based request ordinals, original
input intervals, expected and actual output intervals, input/output strings,
literal comparison counts, requested source paths and verified output runs.
`output_segment_order` separately records their traversal in the output. The
request-selected source path is not silently replaced by the subset with
verified actual symbols. An extra or mismatching output symbol does not acquire
an original coordinate. Case-sensitive comparison uses the selected DNA/RNA
complement semantics frozen for `explicit_sequence_view_v1`; no installed
Biopython complement operation is called by the grader or calculator.

Counts of selected input occurrences, distinct input positions, repeated
selections, physical source positions and output symbols remain distinct.
Physical-source unions group by both exact subject identity and original unit.
Scale-three protein ancestry retains original nt/symbol intervals, including
split codons. No protein output-symbol count is labeled a nucleotide count.
Complete numerical definitions, units, formulas, populations, denominators,
ranges, uncertainty and missing behavior are returned in `scores.definitions`.

Unknown original correspondence remains null in source paths and coverage.
`unmapped_output_symbol_count` counts actual output symbols lacking validated
supplied correspondence, so an absent mapping gives the actual output length;
it does not assert absent biological ancestry. `source_segment_count` is the
number of ordered verified physical path pieces, not a count of unique sources.
Malformed native/request top-level schemas and nonfinite/non-JSON operands raise
specific ValueErrors. Partial or inconsistent fields preserve independently
usable measurements. Saved-cell corruption is reported and never silently
repaired into a replacement historical sheet.

## Inspected implementation paths

Read the complete extraction producer and mapping module; the installed
Biopython 1.88 reverse-complement implementations and complement tables; and
the relevant complete ToolRegistry execute/dispatch, `_sequence`, `_derive`,
`_source`, `_grade_supplied_result`, `_grading_values` and `_save` paths. Read
Store sequence mapping, interval mapping, coverage and source-unit consumers,
plus the complete `tool_grading_artifacts.py` custody reader/writer. Existing
sequence-view, source-retention and mapping tests informed the binding limits.
The unchanged mapping module supplies the actual `map_interval`, `slice_path`,
`reverse_path` and `validate_mapping` arithmetic.

The original immutable objective and all 16 design principles, the applicable
AGENTS.md, GOAL.md, episode, estimation, practical execution, task/steering,
tool-grader direction and inventory rows were read. The required original
objective/principles and exact 279 contract were reread after native study and
before handoff. No permanent design record or progress ledger was rewritten.

## Executed verification

All native study, pytest and example-generation processes ran through existing
`local_jobs` with 20 GiB RAM, 4 GiB scratch and no wall cap. No installation,
API, HPC, local database BLAST or configured-model investigation was performed.

| Evidence | Actual result |
| --- | --- |
| `native_study_001` | Five tiny actual sequence-view helper outputs on explicitly synthetic material; Biopython 1.88. |
| `pytest_001` | Initial test collection failed on a missing bracket; no tests ran. Retained as a historical failed attempt. |
| `pytest_002` | 51 dedicated tests passed in 0.32 seconds. |
| `pytest_003` | Final 54 dedicated tests passed in 0.33 seconds; source hashes unchanged during the run. This overlaps the earlier 51 and is not additive coverage. |
| `filled_001` | Nine filled sheet/calculation examples, complete actual native inputs/results, and explicitly labeled corruptions retained. Eighteen exact recalculations from saved canonical/reversed-key JSON passed with native operations, I/O and network forbidden. |

The 54 tests cover DNA/RNA/protein as-is, case/ambiguity/T/U complement
semantics, out-of-order/repeated/overlapping selection, repeated parent paths,
reverse multi-source paths, distinct identity/unit groups, scale-three
split-codon protein ancestry, wrong same-length symbols, truncated/extra/empty
output, missing fields and source mapping, invalid lengths/units/intervals,
contradictory native settings, nonfinite/non-JSON inputs, and altered saved
rows/cells. The saved replay test additionally forbids Store construction.

## Filled numerical examples

| Supplied work | Numerical answer |
| --- | --- |
| `ACGTTGCAA`, segments `[4,7),[0,3),[4,7),[2,5)` | Native `TGCACGTGCGTT`: 12 selected/output occurrences, 7 distinct input positions, 5 repeated selections, selected fraction 7/9, 12 compared, 12 matching, 0 mismatching. Four ordered source pieces cover 7 distinct original positions. |
| Same segments, reverse complement | Native `AACGCACGTGCA`: same counts, reversed segment traversal and original path orientation retained. |
| `AcGtUrYsWkMbDhVn`, DNA/RNA reverse complement | Native `nBdHvKmWsRyAaCgT` / `nBdHvKmWsRyAaCgU`: 16 compared, 16 matching, 0 mismatching. |
| View `[1,3),[1,2)` of actual translated `MKG*` with split ancestry | Native `KGK`: 3 output symbols, 2 distinct protein input positions, 1 repeated selection. Source `contig:a` covers 5 distinct nt and 7 nt occurrences; `contig:z` covers 1 distinct nt and 2 nt occurrences. Four ordered source pieces preserve the split codon. |
| Deliberately corrupt `aCGT` output to `ACGA` | Equal lengths but 4 compared, 2 matching, 2 mismatching and 2 unmapped output symbols; requested source coverage stays separate from the verified `[1,3)` interval. |
| Deliberately truncate `aCGT` output to `aC` | Length difference -2; 2 compared, 2 matching, 0 mismatching. The missing suffix is not counted as a comparison. |
| Omit original mapping | Four actual matches remain measurable; original source paths/coverage and source-segment count are null; 4 output symbols lack validated supplied ancestry. |

## Source identities and remaining boundaries

Final grader SHA-256:
`ac8640c621bbd961919035237ec0707c95661493c25f87beab3ed4922ea459bf`.

Final test SHA-256:
`7661b8e5d2acc2938c2dca51d7b4f7fda9b7a01c24892eaa0e3313e996affb59`.

Unchanged producer SHA-256:
`5ad12f8ef43d33044dd5cd9662cb9b242af241e0f300fac0353c3130842b9634`.

Unchanged mapping SHA-256:
`241195f974b6a8dab6a06434daa47d04bd277c6a584c77a534f30a274fb3c1c3`.

Exact commands, policy, before/after source hashes and native lifecycle receipts
are retained in each run directory. `filled_001/report.json` records its own
then-current test hash (the later three tests do not change the grader or filled
answers). The original objective SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.

This workload establishes pure numerical ports and actual tiny native-helper
compatibility. Root owns ToolRegistry/source publication, tool-library
registration, shared Workflow/typed-return verification and progress updates;
these are not claimed verified by the dedicated tests. Parent mapping identity
and original physical-source content are host-supplied facts: a structurally
valid, same-length mapping with an independently wrong source cannot be
disproved from these operands alone. The calculator never reacquires original
sources or infers them from coincidental lengths. No new functional annotation,
scientific confidence or broader scope completion is claimed.
