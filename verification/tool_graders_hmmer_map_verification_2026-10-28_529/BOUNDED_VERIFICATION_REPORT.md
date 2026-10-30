# HMMER alignment-map verification, 2026-10-28

The new GSC, BLOSUM and sampled-PB calculations and the selected
`alimask/alignment_to_model` child-owned paths are verified for explicit
alphabets and the retained Stockholm/Pfam input contract. This does not close
the whole HMMER/Infernal/Rfam R2 group. Native alphabet inference, other declared
alignment grammars, message presentation and remaining resource coverage stay
open. The original user attachment remains authoritative; this is evidence.

## Actual results

`BOUNDED_RESULTS_002.json` is the corrected numerical accounting. There are
252 distinct passing selected tests across the collected follow-ups, plus 34
passing unittest subtests. This is not one fresh 252-test invocation. The first
count of 215 passing reports included 181 tests and 34 subtests.

| Attempt | Actual outcome | Meaning |
|---|---|---|
| check001 | Harness aborted after 151 passing reports | Reporter tried to open a file during a test that intentionally forbids file I/O; no final execution audit. Not used as completed verification. |
| check002 | 181 tests and 34 subtests passed; 7 tests failed | Six fixture format spellings were wrong; one retained native fixture was missing from the snapshot. No production numerical failure demonstrated. |
| check003 | 64 passed | Seven corrected fixture cases and 57 new native-source comparisons. |
| check004 | 6 passed; 1 failed | Three actual weighting-branch Workflow executions/returns/closed replays passed. New publication binding and two native-safety cases passed. Historical replay fixture copied a read-only DB. |
| check005 | 1 passed | Only the failed historical replay case repeated after making its temporary copied state writable. Historical source bytes unchanged. |

Every completed attempt was collected from its original lifecycle handle after
terminal, quiescent status. Source, dependency, standard-library and executable
pins were unchanged. Final execution audits found no outside Python imports or
unbound executable mappings. Native-oracle compiler/header/runtime inputs and
original absolute-path retained fixtures were pinned and unchanged where used.
All execution used the existing lifecycle with 20 GiB RAM, 4 GiB scratch,
zero swap and no wall-time cap. No live API or HPC call occurred.

## Numerical authority and native evidence

The existing `hmmer_alignment_preparation_sheet_v1` feeds
`calculate_hmmer_alignment_preparation_components` and
`reconstruct_alimask_model_map`. Driver preflight uses the same parser and map
calculation. The former private driver map implementation was removed. One
normalizer performs native Kahan summation, division, then scaling. Existing
saved publications and observations were not rewritten.

The 57 diagnostic comparisons compiled original retained Easel sources inside
the selected job: 15 GSC, 16 BLOSUM, 6 normalization, 17 Deal sample arrays and
3 MT streams. Comparisons preserve exact double representations, tree topology,
cluster order and every sampled ordinal. Constructed diagnostic inputs are
engineering fixtures, not biological observations. This source-linked diagnostic
is verification only and is not a production tool or an episode decision.

The three real local Workflow selections used the pinned original `alimask`:

| Selected weights | Input | Shared map and requested parent value |
|---|---|---|
| GSC | `AAAA`, `AAAA`, `C--C`; symfrac 0.6 | Weights 0.75, 0.75, 1.5; model columns [1,4]; returned model-position count 2. |
| BLOSUM | Same three rows and threshold | Same normalized weights and [1,4] map; returned count 2. |
| Sampled PB | 10,000 `A--A` and 40,001 `CCCC` rows; symfrac 0.65 | 50,001 source rows; 10,000 sampled row ordinals; [1,4] map; returned count 2. |

Both requested native-mapping and requested-range checks passed. Scientific
choices were scripted fixtures; execution, acquisition, shared calculation,
requested typed delivery and receipt validation used production paths. Selected
CLI seed 17 remains distinct from this retained producer's effective PB seed
42. Derived sample ordinals are not represented as native-emitted provenance.

Closed replay forbade native launch/status, external connections, acquisition,
parsing and full recalculation, and preserved original forms and histories.
The historical absent-context publication retained the original metadata and
six values `[3,14,12,1,1,null]`. A new publication retained its original source,
producer and configuration association and rejected altered context.

## Limits

Exact conformance is to the retained HMMER 3.4 / Infernal 1.1.5 executable and
Easel sources, not every binary with that version banner. Original compiler
history is not recovered. The new live native Workflow cases cover
alignment-to-model; other native modes retain their prior evidence and share
the numerical implementation. Missing or conflicting context remains unavailable;
it is not replaced with guessed installed-machine metadata. Native undefined
empty-map/after-last-match accesses remain explicit non-execution failures.

Current HMMER production modules match the check004 snapshot. Later root edits
only repaired the copied historical-state test permissions. Source ownership,
complete consumer inspection and the original goal/principles/contract reset
were reviewed before accepting this bounded result. No whole tool-family or
R2 completion is claimed.
