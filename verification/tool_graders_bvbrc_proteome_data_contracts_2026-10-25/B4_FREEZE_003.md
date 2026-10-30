# Accepted native-summary calculation workload

Root reviewed proposal001 and correction002. The B4 formula table, explicit
parameter meanings, missingness conjunction, fractions/percent units and typed
NativeComponents result are accepted for independent implementation. The
immutable goal still requires complete directional reports and actual execution
evidence; this native-summary calculator is one component, not a complete tool.

Fresh B4 ownership: new `gene_annotation_episode/bvbrc_proteome_calculators.py`,
`tests/test_bvbrc_proteome_calculators.py`, and its dedicated verification folder.
Public signature remains `calculate_native_components(sheet: dict, *,
parameters: dict) -> dict`, returning NativeComponentsResult.

Exact handoff definitions are in DATA_SHAPES_PROPOSAL_002.json (SHA256
739ee63e0e6eea56398c8482a1143dec8b7f7f073041de3edfa4a06af654d9ae), with
REVIEW_CORRECTION_002.md overriding proposal001. Root will provide the separate
new `bvbrc_proteome_sheet_contracts` module with
`proteome_sheet_schema(name)` and `validate_proteome_sheet_data(name, value)`;
errors use the existing ProteomeDataError code/path boundary. B4 imports these
for NativeSheet, NativeCalculationParameters and NativeComponentsResult. Its
implementation and independent test construction can proceed from the frozen
shapes before this integration dependency is delivered. No validation bypass.

B4 consumes an already populated sheet. It cannot create joins, decode outputs,
select a primary file, derive an executed-input witness, run software, fetch
metadata, change inputs, manufacture source records or rewrite old components.
Its output stores the exact source-sheet digest and explicit parameters. Parsed
legacy values remain unmodified. Thresholds use Decimal lexemes; summaries use
the declared available populations and separate missing states.

Correction002 means locator-only execution/occurrence claims are insufficient.
Full executed-input denominators are not currently admissible. B4 must not
promote visible rows, supplied FASTA counts or plausible pointers into them.
Known-denominator examples in proposal001 are conditional arithmetic examples
for the future qualified interface. Standalone ratio arithmetic may be tested
with explicit numbers; do not manufacture a production sheet claiming an
execution witness the current interface cannot represent.

Required tests: actual supplied native-cell fractions and decimals; true zero;
missing, blank, omitted, invalid and uncertain-layout cells separately; explicit
postfilter pass/fail/unknown, including a known failure plus unknown condition;
partial and name-only tracks; duplicate bound pairs and sequence groups;
wrong source/keys/parameters; recalculation with changed explicit thresholds
without mutation; no parsing/network/native execution. Reuse proposal001's
synthetic filled native sheet honestly, preserving its zero unknown input
denominators. It is not retained output from the BV-BRC service.

Root separately owns shared sheet contracts, B2/B3 implementation assignment,
publication/typed-return binding, package data and accounting. The calculator
does not change evidence-axis scoring, library prompts or episode behavior.
