# Concrete implementation workloads after the SAMstat contract

This file assigns future work; none of these implementations was performed in 207. The stable scientific ports are `NATIVE_FIELDS_002.json` and `PARSER_CALCULATOR_PORTS_002.md`. Initial revision 001 remains intact, with corrections explained in `CONTRACT_CORRECTIONS_002.md`. Root reviews the concrete contract before assigning coding work; this is a development handoff, not a new runtime reviewer or approval gate.

Every fresh coding assignment must include the original task constraints and require a full read of `/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`. After substantial external/native study and before translating findings into code, reread the objective and all 16 DESIGN PRINCIPLES verbatim. Before completion or moving to another tool, repeat that reset and reread the current agreed tool contract. Source facts and old tests cannot override user design. No agent edits the original goal, inventory scope, other owners' files or historical evidence.

Local work remains limited to tiny examples within 20 GiB RAM and 4 GiB scratch, no wall-time cap; no global installation, Aurora execution, credentials, guessed deployment version, embedded JavaScript execution, acquisition inside a parser, LLM grader, score DSL, new episode or annotation-credit redesign. Source-executed synthetic evidence is not live BV-BRC execution.

## A. Root-owned shared contract and integration

Exclusive ownership: root, or one explicitly designated integration owner acting under root. Leaf agents do not modify these files concurrently.

Shared implementation paths in the chosen integration candidate:

- `gene_annotation_episode/bvbrc_fastqutils_schemas.json` and the schema/return/selector enum mirrors actually consumed there;
- `bvbrc_fastqutils_metric_specs.py`, `bvbrc_fastqutils_contracts.py`, `bvbrc_fastqutils_identity.py` only if necessary validation changes are justified;
- new `bvbrc_fastqutils_samstat_native.py` with `parse_samstat_html(raw: bytes, *, context: dict) -> dict`;
- existing `bvbrc_fastqutils_native.py`, `bvbrc_fastqutils_resolution.py`, `bvbrc_fastqutils_calculators.py` dispatch;
- metadata/sheet/projection/returns/saved-codec/bundle-adapter files only where the finite additions or compatibility require change;
- dedicated shared integration/compatibility tests.

Root fixes the finite metrics, section/population/axis keys, diagnostics, format acceptance and calculation-request variant from revision 002. There is no need for a new generic series object or shared mutating reader-builder API. Leaf readers may construct existing validated objects with `native_ref`, `population_ref` and existing validators directly. If root elects to introduce reusable construction helpers, publish their exact signatures and return/mutation semantics **before** a leaf depends on them.

Preserve original producer/report qualifiers and input-scope uncertainty. A typed requirement is returned when needed data is absent; it does not launch another job. Generic `samstat_html` may resolve to a supported versioned actual format; a filename never proves successful report format. A supplied version contradiction must not quietly select either version.

Root reported that 208 now contains a closed requested-form grammar/saved generation in addition to the older 198 legacy generation. Preserve both original grammars and original values when adding SAMstat. Do not mutate the historical generation's allowed values to make a new saved result appear old. The 208 dependency and 359-case status is a root report, not a test rerun by 207.

Acceptance includes the actual child-owned FastqUtils AppService/selected Workspace artifact-byte binding, provider consumption, complete sheet, calculation, requested typed return and offline saved-codec closure. Native source execution alone does not satisfy this. Update the adapter dependency manifest with every newly imported module. Run the relevant existing Fastq integration/compatibility suite after changes and package closure checks appropriate to the new dependencies.

## B. Legacy HTML reader

Exclusive new implementation file: `gene_annotation_episode/bvbrc_fastqutils_samstat_legacy.py`.
Exclusive test file: `tests/test_bvbrc_fastqutils_samstat_legacy.py` plus its own copied/derived test fixtures directory. Do not rewrite retained 207 evidence.

Public function: `parse_samstat_html_2_2_3(raw: bytes, *, context: dict) -> dict`.

Use the pinned 2.2.3 output grammar. Parse all emitted literal table and series payloads, including hidden groups, native means/SEM, density estimates, clustered values and optional end/relative sections. Never evaluate JavaScript. Keep actual scalar values and labels; do not infer data from Plotly rendering. Match variable identity and arrays rather than independently sorting names and values. Cross-reference each value to its source bytes and native group.

Required cases:

- Mixed SAM/BAM: R1 `[5,2,2,1]`, R2 `[0,1,0,0]`; secondary excluded, supplementary retained; MAPQ255 remains inside first bin.
- The report-wide 11-record sentence and per-mate totals are separate native observations; repeated totals are not independent data.
- Exact count table versus five-decimal native fractions; empty SAM has zero counts and literal `-nan` fractions.
- 1002-record pair-flag sentences show `1K` without exact paired counts; report total includes exact 1002. Preserve display precision and units.
- FASTX sequence counts and its misleading “Unmapped” names do not become alignment outcomes. Retain the observed pinned FASTX quality-offset defect as native index values, not valid Phred summaries.
- Two SAM Q0/Q40 bases yield mean 20 and SEM 14.142136; missing QUAL is absent, not Q0. Position zero means without n remain qualified as coverage unknown.
- Lengths 4,8,8 have KDE values 0.090324 and 0.169574. Alignment length excludes soft clips. Single-length density spike 1 is a native fallback.
- 300-bp position clusters have native rounded mean counts; preserve text axis labels and do not recover original unclustered totals.
- Exact x/y/error-array cardinality, mismatched/duplicate groups, malformed one-block recovery, truncated transfer, malicious executable text and unsupported versions.
- Legacy prefix request 10 produces a native 10000-record chunk; malformed SAM can produce a closed first-record report with exit 0 and stderr warning. Reader never turns report closure into proven original-input completeness.

Optional missing-QUAL SAM end/relative behavior was only source-inspected, not executed here. Do not silently claim native validation for it; retain the limitation or add a separately receipted tiny native case before assigning stronger semantics.

## C. Current HTML and caller-failure readers

Exclusive new implementation file: `gene_annotation_episode/bvbrc_fastqutils_samstat_svg.py`.
Exclusive test file: `tests/test_bvbrc_fastqutils_samstat_svg.py` and its own copied/derived fixtures.

Public functions: `parse_samstat_html_2_5_0(raw: bytes, *, context: dict) -> dict` and `parse_samstat_bvbrc_error_html(raw: bytes, *, context: dict) -> dict`.

Read actual text/card/table/notes/footer/accessible descriptions. Native per-position/length/quality/error/identity arrays are not embedded in these SVG reports. Preserve unavailable plot data as such; no path geometry inversion, chart-axis tick sampling, guessed zero histogram bins or optional JSON substitution. The caller does not request JSON.

Required cases:

- Mixed SAM/BAM: 10 primary contributing records, 50 full-sequence bases, mapping bins `[4,3,2,1]`, R1 `[4,2,2,1]`, R2 `[0,1,0,0]`; secondary and supplementary each excluded count 1.
- Native Mean Q16.2 stays 16.2 despite optional separately acquired JSON16.1541. Q0/Q40 native mean is 3.0, not legacy arithmetic20.
- 10001-record main `10.0 k` plus exact sublabel `10,001`; exact cardinality uses the sublabel while original display remains retained.
- Native 10123/10987-base reads produce rounded median10.1kb and N5011.0kb; do not recover their exact individual lengths from display. Exact total bases21110 is separately present.
- Empty input, absent SEQ (`Bases n/a`), absent QUAL, conditional missing-identity/mismatch notes, clipping15.4% and gap-compressed identity80.0%.
- Repeated global range descriptions in R1/R2 figures preserve global scope. Legends and count columns remain distinct representations, not independently summable counts.
- Native prefix10 stays prefix10. Truncated table retains independent valid summary cells.
- Source-produced caller stub has return code1 and falsely says “segfault”; preserve failed/null measurement, error details, source binding and the failure format. It is not an empty successful report.

## D. Report-bin calculator

Exclusive new implementation file: `gene_annotation_episode/bvbrc_fastqutils_samstat_mapping.py`.
Exclusive test file: `tests/test_bvbrc_fastqutils_samstat_mapping.py` with source-bound saved-sheet fixtures created from the reader contract.

Public function: `calculate_samstat_report_mapping(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]`.

Implement only the ordinary two-component calculation in revision002: mapped contributing-record fraction and native ge30-bin contributing-record fraction. Preserve explicit native denominator, integer numerator, count operand refs, population refs, version and parameter/sheet identities. Do not reuse the distinct-read correspondence calculator or invent independent observations, confidence, read-pair totals or molecule counts.

Required cases:

- Legacy selected R1+R2 gives mapped10/11 and ge30 5/11; current all population gives9/10 and4/10.
- Zero denominator undefined; missing bin missing/truncated; overlapping all+mate or cross-document populations incompatible; duplicate count operands or conflicting native totals incompatible.
- FASTX “Unmapped” is incompatible. MAPQ255 cannot be removed from the high bin or assigned calibrated confidence.
- A declared prefix returns a finite partial component when the full selected bin table exists; incomplete or unknown original consumption never becomes full-input mapping coverage.
- Exact rounded native percentages are retained but not operands. Legacy density, quality means/SEM and display counts cannot masquerade as cardinality inputs.
- Offline recalculation from the saved sheet and explicit parameters only, with no native executable, source checkout, network or input reacquisition. The original saved return remains immutable.

## Handoff and completion evidence

Each leaf returns its owned paths, exact implemented public signatures, field families supported, native fixtures actually consumed, numerical assertions, negative/partial cases, unverified modes, and required root-owned enum/dispatch/compatibility changes. Tests that construct a fake completed provider result do not establish the actual path. Root assembles and verifies that path once the modules and shared finite contracts agree.

No completion claim for FastqUtils, SAMstat deployment, live service execution or the full original inventory follows from this contract-only workload.
