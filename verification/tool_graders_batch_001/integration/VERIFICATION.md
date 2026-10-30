# B001 publication and episode-return verification

2026-10-24. This record covers the two new integration test files and the saved
examples in this directory. It does not reduce the authoritative tool-grader
goal or mark unrelated modes and resource bindings complete.

## Executed checks

From `/home/chia/repos/gene_annotation_episode`:

```text
.venv/bin/python -m pytest -q tests/test_tool_grading_publication.py tests/test_tool_grading_child_returns.py --basetemp=/tmp/b001-tool-grading-integration-051 --junitxml=verification/tool_graders_batch_001/integration/pytest-results.xml
29 passed in 116.55s (0:01:56)
```

After root identified and guarded legacy identity projection when an alignment
has zero paired positions, the additional focused check was run separately:

```text
.venv/bin/python -m pytest -q tests/test_tool_grading_publication.py -k valid_gap_only_native_fixture --junitxml=verification/tool_graders_batch_001/integration/gap-only-pytest-results.xml
1 passed, 23 deselected in 1.73s

.venv/bin/python verification/tool_graders_batch_001/integration/recalculate_examples.py
9 saved examples checked; 12 grading results recalculated
Changed Q0/Q40/Q41 counts: 16000, 15999, 0 (denominator 16000)
```

The gap-only fixture was captured from actual Biopython 1.88
`align_pair('A', 'T', molecule='dna', mode='global', gap_open=0, gap_extend=0)`.
These gap costs are not exposed by the current ToolRegistry invocation; the
fixture is injected at the existing native-worker seam to check publication.
It preserves the native fallback `identity_fraction=0.0` in source bytes, while
the typed observation omits both legacy and derived paired-position identity.
The saved grader reports `paired_identity=null` with denominator zero.
All-column identity remains the meaningful `0/2=0`. Native bytes, one semantic
observation, one selected operation and replay are checked.

The 23 publication cases execute real bounded local Biopython alignment and
Pyrodigal meta prediction, inspect actual supplied sequence/FASTQ members, test
custody conflicts, and inject explicit grading-input failures. The six Workflow
cases exercise all five selected local operations and offline API BLAST result
acquisition. The continuation estimates and decisions are scripted engineering
fixtures. Scientific credit is an explicitly zero test projector; this verifies
the absence of extra accounting events, not an annotation-credit formula.

Root scientific execution tools remain unavailable. Local work is selected by a
three-slot scientific-process child. The parent receives a typed
`committed_record_refs` form; receipt-qualified observations carry the existing
and newly calculated numerical fields. Every local case has one child action,
one child controller observation, one parent child action and one parent
controller observation. Read batches have two semantic observations but still
one completed action per episode. Replaying the exact operation and redelivering
the admitted form leave both observations and receipt counts unchanged.

The matching library parent row contains name, description and local resource.
The selected child receives the full corresponding pairwise, gene-prediction,
or composition/quality instructions. Complete grading sheets are source
auxiliary artifacts; they do not appear in parent working-state content.

## Checkable numerical examples

| Example | Observed/calculated numbers |
| --- | --- |
| Real global DNA self-alignment | 8 paired positions, 8 identities, score 16, identity 1, coverage 1 |
| Real local alignment with unaligned flanks | 8 paired positions from a 12-nt query, query interval `[2,10)`, paired coverage `8/12` |
| Real global alignment with a gap | 11 alignment columns, 10 paired/identical positions, 1 reference gap; paired identity 1; alignment identity and query paired coverage `10/11`; native score 10 |
| Real meta prediction, code 11 | 1 candidate; relative interval `[2,305)`, parent interval `[15,318)` at input offset 13; 303 nt; 101 aa; both boundaries partial; 0 internal/terminal stops |
| Meta prediction summary | Coding union 303 nt / submitted 306 nt = `0.9901960784313726`; native score `51.84391561353229`; native gene-prediction confidence `99.99933317172413` percent |
| Identical 8-nt reads with distinct quality | First mean Phred 35 and expected errors 1.0007; second mean Phred 0 and expected errors 8; both GC 4/8 |
| Full 16,000-nt FASTQ member, beyond preview length | 15,999 Q40 bases plus one Q0 base; mean Phred `39.9975`; expected errors `2.5999`; recalculated Q0/Q40/Q41 counts `16000/15999/0` |
| Offline API BLAST typed HSP fixture | Bitscore 31.5; alignment score 60; E-value `1e-5`; query/reference coverage 1; native-reported identity `6/8 = 0.75` |

Prediction confidence is the native gene-calling quantity, not function
annotation accuracy. The BLAST provider fixture retains its original reported
identity count 6 even though the added alignment strings have seven literal
matches. This case checks exact custody and existing typed HSP projection, not
internal consistency of an actual BLAST run. Its native output and complete
grader result remain available for inspection.

`example_summary.json` records the actual numerical observation arrays and
episode action counts. Nine full example JSON files retain source records,
filled grading results, observations, selected outcomes, and requested forms.
The adjacent `*.native.json`/`*.native.jsonl` files are exact copies of the
already retained source-artifact bytes, with SHA-256 recorded in the examples.
For `genes.predict`, the ordinary source representation contains parent-shifted
publication coordinates; its full numerical sheet preserves the complete
unshifted worker result and both coordinate systems. These examples do not
claim byte-for-byte preservation of the worker's original serialization.

## Failure and missing-data checks

- Explicit no-alignment yields zero paired positions and null identity. The
  numeric observation omits unknown identity rather than publishing zero.
- DNA/RNA GC uses unambiguous denominators. Protein and unspecified molecules
  have no nucleotide GC interpretation. Missing quality stays unknown.
- Two reads with the same identifier and sequence retain distinct source-member
  identities and quality arrays. The 16,000-base test uses all original quality
  characters and verifies the caller's original FASTQ bytes.
- A grading artifact with a wrong provider or wrong native-artifact reference
  is rejected as `tool_grading_source_custody_mismatch`.
- Injected grader `ValueError` preserves native alignment, prediction,
  inspection, and offline BLAST results; full grading failure bundles contain
  null sheets/scores and the exact cause. Selected results are partial with
  explicit `grading_input` feedback. One failed read grader preserves the
  valid neighbor and both native member observations.
- Reopened sheets recalculate without acquisition. Changed quality thresholds
  recalculate from the saved full member and leave the original sheet unchanged.

The verification found missing grading-failure feedback in ordinary publication
and then the API publication boundary's missing failure collector. Root fixed
those production paths; this worker changed only its assigned test/evidence
files. The final 29-case run includes the fixes.

## Inspection and coverage limits

Inspected the relevant native worker and `sequence_ops` functions; ToolRegistry
sequence/read inspection, alignment, derivation, source/observation publication,
operation replay, `_save` and failure propagation; explicit grading-artifact
custody; numerical observation contracts; material member and quality custody;
scientific tool-information resolution and child construction; Workflow typed
fact construction, form admission, receipt selection and result accounting;
and BLAST API acquisition/publication and typed HSP projection consumers.

The local algorithm tests cover six pairwise molecule/mode combinations plus
nontrivial DNA geometry. The full child-return path uses global DNA alignments,
meta gene prediction, sequence inspection and original-read inspection/alignment.
Single-mode Pyrodigal and RNA/protein/local pairwise child-return variants are
not exercised by these boundary tests; their separate pure/native grader tests
are outside this record.

The Workflow tests use the ordinary shared-loop child execution and persisted
forms/receipts, without the detached-process execution binding. They do not
establish detached host recovery, configured-model scientific investigation,
HPC deployment, live API availability, or W05 annotation-credit aggregation.
BLAST uses the existing synthetic offline provider fixture; the two root actions
commission launch and results, with one results-child action and observation.
No external request, live submission, local database BLAST, or separate pending
NCBI job was observed or touched.
