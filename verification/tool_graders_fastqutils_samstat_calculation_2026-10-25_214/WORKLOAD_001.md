# SAMstat report-bin calculation and deterministic result integration

Read the COMPLETE authoritative goal at
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`
and AGENTS.md before work. Reread the goal objective and ALL16 design principles
verbatim after substantial native/source examination, before implementing its
meaning and before finishing. Then reread207 PARSER_CALCULATOR_PORTS_002.md and
NATIVE_FIELDS_002.json. No literature/annotation-score work, new episodes, model
calls, retries, resource choice or scientific credit changes.

## Exact owned files and consumers

Work in212/candidate. Own new `bvbrc_fastqutils_samstat_mapping.py` and
`tests/test_bvbrc_fastqutils_samstat_mapping.py` plus dedicated test fixtures.
Own necessary changes to `bvbrc_fastqutils_resolution.py`,
`bvbrc_fastqutils_calculators.py` and `bvbrc_fastqutils_projection.py` only.
Evidence/scripts belong to214. Shared212 schemas/specs, native dispatch, current
parser, legacy213 parser and their tests are read-only. Root separately owns
composition with211SRA and production application. Never edit old receipts or
running202 tests. Coordinate an exact missing shared contract with root/212.

The public function is exactly:
`calculate_samstat_report_mapping(sheet:dict, *, job:dict,
parameters_sha256:str)->list[dict]`.

Its caller is calculate_fastqutils, which validates the saved sheet/job operands
and accumulates typed components/requirements. resolve_calculation_inputs must
resolve the new `samstat_report_mapping_v1` request BEFORE the old consistency
fallback. The request's populations array contains1or2 exact PopulationSelectors.
The resolved CalculationBinding retains selected population refs, every actual
count operand, existing state/diagnostic/requirement fields; all comparison,
quality, read-key and lineage options are null/empty. No new job shape.

## Scientific arithmetic and identity

Use only `samstat_report_records` populations and exact native bin count cells
from the same artifact/version: ge30 axis[30,255],10_29[10,29],0_9[0,9],
unmapped native_label='Unmapped' with null bounds. Four counts are required per
selected stratum. Optional native alignment_total must equal their sum. Native
rounded percentages, display counts and all other metric families are not
arithmetic operands. Preserve all used count refs. A hand-made binding may not
hide contradictory/duplicate native counts already in its selected population.

Input alignment mode is established by actual native labels: legacy section
samstat_summary, kind native_label, value Mapping statistics; current locator
field input_format and value SAM/BAM. Legacy File statistics/current FASTQ/FASTA
are incompatible. Unknown input kind stays unknown; the newly identified modern
empty report has an unclassified reported_item_count with no population and
cannot supply alignment bins. Never infer mode from paths.

One selected population can be report-wide0 or mate1/2. Two populations must be
actual disjoint mate1and2 from the same document, with mutual disjoint_from_refs.
Reject duplicate selectors resolving to the same identity, all+mate overlap,
cross-document sums, incompatible versions or malformed/contradictory bins.
Do not infer molecule/read-pair identity from alignment record counts.

For sum T of all four bins over selected disjoint strata, unmapped U and native
high-bin H, return EXACTLY two ordinary Component rows:
- samstat_report_mapped_record_fraction: numerator=T-U, denominator=T, value=(T-U)/T;
- samstat_report_ge30_record_fraction: numerator=H, denominator=T, value=H/T.

Each uses method samstat_report_mapping_v1, unit fraction, meaning
native_report_derived, uncertainty not_estimated, threshold null, supplied
parameter hash, exact saved-sheet identity and existing canonical component_ref.
Encoding/lineage bases are null. The existing generic retention._component
constructor may be reused because it chooses these metadata from component_spec;
do NOT reuse retention's population/lineage arithmetic checks.

Unknown original input completeness does not prevent a fraction of the reported
records: return available with samstat_input_scope_unproven and
samstat_report_population_only. Preserve samstat_mapq255_merged. An observed
prefix or truncated retained report gives a finite partial component only if
all selected bins survive; never claim a complete original experiment. T=0 is
undefined/null; missing bin is missing/truncated/null; conflicts are
incompatible/null. Retain available operands and exact failure qualifications.

## Two existing integration gaps to resolve carefully

1. Document selection: a generic samstat_html selection can accept one declared
   supported versioned format, and a versioned selection can accept a generic
   artifact declaration subject to actual-byte version validation. Conflicting
   versioned declarations remain incompatible. Preserve the original declared
   binding and saved-codec checks; do not silently discard member format/version
   constraints. Read the complete resolve_documents/consume_bundle/saved-codec
   path before deciding whether a further shared handoff is necessary.

2. Missing-value projection: its current target_refs contain document_ref only,
   while the current parser's caller-failure and unavailable-SVG requirements
   affect artifact refs. A complete recognized error report must not lose its
   failure cause merely because parse_scope=complete. Propagate
   samstat_caller_failure/native_execution_evidence to absent requested scientific
   measurements. Propagate samstat_svg_values_not_retained only to relevant
   requested SAMstat plot measurements, not unrelated metadata/categories or
   every legitimate empty selection. Do not turn a partial parser into a hidden
   completion gate. Preserve pre-existing empty-population and typed-state behavior.

## Verification

Use actual retained207 native reports through the new leaf parsers and ordinary
metadata/sheet functions; no fake already-completed provider results as path
proof. Legacy R1+R2: mapped10/11,ge30 5/11. Current all: mapped9/10,ge30 4/10.
Test current each-mate and legacy each-mate selections, zero, missing/duplicate
bin, total conflict, wrong mode, unknown mode, overlap, cross-document, native
prefix and partial transfer. Keep exact operand refs and original values.

Verify typed provider returns and saved-sheet recalculation without parsing,
network, subprocess or native source files. Select different explicit strata
using the same saved sheet; preserve old components/parameter hashes. Verify
caller-error and unavailable-SVG requested absences carry the correct reasons.
Also run the affected original resolution/calculator/projection tests, but no
duplicate full359-case run while shared readers are active. Freeze inputs or
record any concurrently changed shared path honestly; final root composition
will provide the immutable complete test scope.

20GiB RAM/4GiB scratch, no wall-time cap, no global install or live service use.
Return actual files, numerical examples, failures retained, passed cases and
remaining limits. This work does not prove production application, live BV-BRC
or full method_loop integration.
