# BLAST selected-column implementation and verification

Workload 286 implements the supplied-HSP numerical reader and calculator from
the frozen 284 contract and preserved 282 review. It does not implement host
receipt admission, operation-artifact custody, typed episode returns, knowledge
index registration, annotation scoring, W05 or literature work. Root owns those
applicable integration paths. The original immutable goal and all sixteen
principles remain the authority.

Owned production files are `blast_hsp_site_inputs.py`,
`blast_hsp_site_calculators.py`, the new `blast_hsp_column_correspondence` helper
in `blast_pairwise_grader.py`, and `knowledge/blast-hsp-columns.md`. Tests are
in `tests/test_blast_hsp_sites.py`. Existing function bodies in the pairwise
grader are unchanged; the before snapshot and AST audit record that fact.
The shared `map_operand_interval` leaf belongs to workload 285.

The parser retains the complete supplied native HSP, native version, actual
locator, supplied operand identities/lengths, whole-HSP scores, requested and
realized windows, all selected native symbols and checked coordinate intervals.
Frames/strands remain native supplied values. Directions are nullable integers;
a single nucleotide with equal endpoints uses its reported strand, or remains
unknown when no strand is reported. Native case is retained; equality compares
uppercase native symbols literally, without resolving ambiguity.

The calculator validates saved relationships against the native facts already
inside the sheet, then calculates from the populated measurements. It makes no
file, network, subprocess or model calls. It rejects altered rows, selectors,
counts, units, availability or inherited-score projections. This checks internal
consistency, not external authenticity: only the host can authenticate the actual
subject/source/receipt, including a same-length wrong operand.

| Component | Formula and population | Unit / denominator |
| --- | --- | --- |
| `window_alignment_columns` | Realized selected column count | columns |
| `paired_columns` | Two nongap native symbols in a selected column | columns |
| `identical_pairs` | Equal uppercase symbols among selected pairs | pairs |
| `substituted_pairs` | Paired minus identical | pairs |
| `query_gap_columns` | Selected column with query `-` | columns |
| `reference_gap_columns` | Selected column with reference `-` | columns |
| `paired_identity` | Identical / paired | fraction; paired columns |
| `alignment_identity` | Identical / all selected columns | fraction; columns including gaps |
| `query_paired_units` | Size of union of selected checked paired query intervals | native aa or nt |
| `reference_paired_units` | Size of union of selected checked paired reference intervals | native aa or nt |
| `query_paired_coverage` | Query paired units / full native query length | fraction; full query in native units |
| `reference_paired_coverage` | Reference paired units / full native reference length | fraction; full reference in native units |

All intervals are zero-based half-open bounds in the original operands, with
orientation separate. Translation consumes three nt per aligned aa on each
translated operand. Original derivation segments remain ordered and separate,
including split codons and repeated segments. They are not merged into local
coverage. Native scores and reported counts are whole-HSP inherited quantities,
unused in selected-window ratios. These literal quantities have no fabricated
statistical uncertainty, confidence score or annotation credit.

Missing strings yield null counts and no realized window. Unequal, malformed
or double-gap strings remain incompatible. Valid strings can retain counts
when endpoints, frame, phase, supplied length, reported extent or midline are
incompatible; positional units/coverage then remain null. An available empty
terminal page has zero counts/units and null identity; ratios retain explicit
numerators/denominators, with null value for unavailable inputs or zero
denominator. Missing original ancestry does not erase valid local geometry.

## Executed evidence

All tests used the repository `.venv/bin/python` through the existing
`gene_annotation_episode.local_jobs.run_local_job`, with 20 GiB RAM,
4 GiB scratch and no wall-time cap. Each run directory retains command,
resource policy, native lifecycle records, stdout/stderr, JUnit output and
before/after source hashes.

- `attempt_001`: 250 passed, one failed. The failing fixture expected a filename
  string for existing parser archive metadata; the parser correctly returned
  `{ordinal:1,name:"DTKE1D4G016_1.json"}`. The test expectation was corrected.
- `attempt_002`: 251 passed.
- `attempt_003`: 255 passed: 71 new selected-column tests, 39 existing pairwise
  tests, 29 existing BLAST format tests, 32 database grader tests and 84 explicit
  association tests. No source changed during this run.
- `examples_001`: retained 16 full populated example/scores artifacts and their
  compact index. No source changed during capture.
- `attempt_004`: 258 passed, including three additional effective-coordinate-unit
  ancestry checks. The suite has 74 selected-column tests and the same 184
  existing BLAST regressions. No source changed during this final test run.
- `examples_002`: final capture adds the three effective-unit ancestry examples
  for 19 full sheet/score artifacts; the earlier capture remains preserved.

Synthetic checks cover all five supported programs; both directions and
translated frame phase; gaps; source/operand validation; native zero; missing
lengths; malformed/truncated traceback; whole-HSP extent/midline conflict;
native count disagreement; empty terminal and gap-only pages; original split
codons/repeated segments; nonfinite input; saved-sheet tampering; no mutation;
and recalculation with file/network/subprocess entry points blocked.

The retained local BLASTP 2.17.0+ pairwise result uses `results.bl2seq`, with its
public 253-aa query and explicitly synthetic deletion/substitution reference.
It yields 253 columns, 243 paired, 238 identical, five substitutions and ten
reference-gap columns. Paired identity is 238/243; query paired coverage is
243/253; reference paired coverage is 243/243. Its bit score remains 486.878,
raw score 1252 and E-value zero.

The retained actual API result is the original ZIP at
`verification/w04_blast_graders_2026-10-24_001/live_api/result.body`, SHA256
`38908947ffab7a09a8260c6c6933b53cd35c066a3630e5e072c61be0a51c771f`.
Its real member `DTKE1D4G016_1.json` contains one database search with seven
hits/seven HSPs. Each is extracted independently at its actual native ordinal.
The second HSP has 86 columns, 71 pairs, 31 identical pairs, 40 substitutions,
four query gaps and 11 reference gaps. Equal strings in the last two HSPs
remain separate observations/locators; no independence or combined score is
inferred. The `retained_*` labels in these pure fixtures are explicit local test
identities, not invented host observations or RID receipts.

The reviewed reverse blastn selection has four columns, two pairs, two identical
pairs and one gap on each operand: paired identity 1, alignment identity 1/2,
query coverage 2/12 and reference coverage 2/18. The reverse blastx example has
query intervals `[9,12)`, `[6,9)`, `[3,6)` and three aa pairs: query coverage
9/12, reference coverage 3/5, identity 1. The split-codon example retains ordered
original segments `[3,4)` and `[8,10)` rather than a fabricated contiguous codon.

No new native BLAST process, database search, installation, API request, HPC
execution or model call was performed. This workload verifies supplied-data
formats/components and saved recalculation. Actual host authorization, custody,
selected-child execution, typed receiving-episode admission, replay and credit
must be verified by root before the fixed operation row is called complete.
