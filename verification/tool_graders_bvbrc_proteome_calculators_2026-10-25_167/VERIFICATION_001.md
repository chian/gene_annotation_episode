# B4 calculator verification

Implemented `calculate_native_components(sheet, *, parameters)` in the new
`gene_annotation_episode/bvbrc_proteome_calculators.py`, with independent tests
in `tests/test_bvbrc_proteome_calculators.py`. Only those files and this dedicated
verification directory were edited by this workload.

The real shared validation boundary is used for NativeSheet,
NativeCalculationParameters and NativeComponentsResult. No validation stub or
production denominator claiming an unavailable witness was introduced.

## Actual runs

| Receipt | Actual result |
| --- | --- |
| `pytest_001.log` / XML | Collection failed because the separately owned sheet-contract module had not yet been delivered. No calculator test ran. This failure remains retained. |
| `pytest_002.log` / XML | 50 passed in 2.38 seconds after the real validator was delivered. |
| `pytest_003.log` / XML | 54 passed in 2.54 seconds after adding unresolved sequence-group and alternate-representation cases. |
| `RECALCULATION_RECEIPT_001.json` | Separate actual public-function calculation/recalculation of the historical synthetic saved sheet, with stable dependency hashes before/after. |

The focused command was `python3 -m pytest -q
tests/test_bvbrc_proteome_calculators.py --junitxml=<receipt>.xml`, with each
run's output retained in its own log. No other running test process was stopped
or restarted. No scientific program was run.

The 54 tests cover independent numerical checks against the historical filled
sheet and expected component example, inclusive Decimal thresholds, native
lexeme precision beyond binary-float equality, real zero, omitted/null/blank/
invalid cells, unrelated invalid lengths, uncertain TSV layout, known-failure
plus unknown conjunction, disabled filters versus empty category lists,
explicit native categories, source completeness, name-only and explicitly
missing tracks, materialized blank blocks, supplied occurrence joins, distinct
subjects, demonstrated and unresolved sequence groups, multiple-reference
subjects, duplicate bound pairs, equal/conflicting alternate representations,
invalid parameter and source/key contracts, unavailable execution witnesses,
detached results, unchanged saved sheets and recalculation.

The no-IO test warms static package schema initialization, then blocks file
reads, socket creation, subprocess execution, the native parser, input readers
and BLAST functions during repeated calculation with changed parameters.
The calculator has no acquisition, Store, model or execution imports/calls.

## Concrete values

For the unchanged historical synthetic sheet, identity percentages are
`87.5, 0, 87.5` and native endpoint-difference percentages are `99, 50, 99`.
The comparison-4 identity summary is `(0 + 0.875) / 2 = 0.4375` and its native
endpoint-difference mean is `(0.5 + 0.99) / 2 = 0.745`. The latter is not an
inclusive or all-HSP coverage measurement.

Thresholds identity >= 0.6 and endpoint difference >= 0.7 produce
`pass, fail, pass`. Changing only identity threshold to 0.9 produces
`fail, fail, fail`. Both calculations retain sheet digest
`d9788a02e5fdacbabb938036895bbcdb6e669cc0178abb8fe3dbba72be2056e0`;
the input sheet and first calculation remain unchanged. Every exact executed
input denominator remains null, as do no-published-reference counts and
input-population fractions.

The known-four-input example in NUMERICAL_EXAMPLES_001.json was checked with
literal rational arithmetic: identity mean `1/2`, endpoint mean `56/75`,
conditional ratios `3/4`, `2/4`, and `0/4`. The standalone ratio helper also
preserves `0/0` as `zero_denominator`. These conditional arithmetic tests do
not create a production execution witness.

## Evidence scope and remaining work

All scientific-looking values used here are **synthetic contract examples** or
variants of the already recorded synthetic A projection. Generated calculator
outputs are saved as CALCULATED_COMPONENTS_001.json and
RECALCULATED_COMPONENTS_001.json, each explicitly carrying that origin.
This task did not test retained native BV-BRC output, execute the live service,
run a new native analysis, bind B3/application publication, or verify episode
communication. Root owns those later consumers and integration.

Full GenomeComparison remains incomplete. Its legacy first-HSP, rounded-fraction
producer does not retain complete directional reports/all HSPs. The qualified
executed-input and occurrence-witness interfaces remain unavailable. Live
service/version evidence and a complete selected-tool-to-receiver verification
are also unfinished. No annotation/evidence-axis/W05 change was made.

The complete authoritative objective and sixteen design principles were reread
verbatim, followed by the accepted B4 contract and correction002 boundary before
this handoff. The immutable objective and frozen schema hashes are recorded in
INPUT_HASHES_001.json. Source/dependency hashes for the separate recalculation
are recorded in RECALCULATION_RECEIPT_001.json; final artifact hashes are in
ARTIFACT_HASHES_001.json.
