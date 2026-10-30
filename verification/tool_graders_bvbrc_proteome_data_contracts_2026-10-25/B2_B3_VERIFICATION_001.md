# Constructed proteome measurement path

Root implemented B2 `build_native_joins` in the new `bvbrc_proteome_joins.py`.
Fresh worker169 implemented B3 `build_native_sheet`; worker167 delivered B4
`calculate_native_components`; worker168 delivered saved-data validation.
The interfaces and ownership were defined before these assignments in the
existing proposal001/correction002 and additive construction005/ownership006.

The entire immutable goal was reread in this turn (including the initially
truncated middle section), followed by actual contracts, complete relevant
validators/consumers and the separate native-calculation implementation. The
goal's scope and existing historical records were not changed.

## Results actually obtained

- B2 first focused run: 41 passed, 1 failed. The failing test incorrectly
  expected input-index rows in their original parameter order. B1 explicitly
  moves the selected reference first while preserving each original index.
  The expected ordering was corrected; production ordering was not changed to
  accommodate the test. The original log/XML remain retained.
- B2 final focused run: 50 passed in 3.04 seconds. Additional checks cover real
  A/B1 composition, ambiguous duplicate/cross-input IDs, invalid JSON neighbors,
  uncertain TSV layout, source/metadata conflicts, actual full sequence groups,
  partial and complete-invalid sequences, unknown execution witnesses, detached
  results, and no acquisition/parser/execution calls inside join construction.
- Actual A/B1/B2/B3/B4 composition: all 6 checks passed in 1.69 seconds, including
  numerical answers, saved recalculation and retained local rejected links.
- Final combined current-source run: **637 passed in 29.94 seconds**, zero
  failures/errors/skips. Its eight modules comprise 94 native parser tests,
  52 input-contract tests, 185 input-extraction tests, 124 sheet-validation tests,
  50 join tests, 72 sheet-builder tests, 54 calculator tests and 6 composition
  tests. These are overlapping evidence with the focused runs, not 637 new tools
  or a sum to add to those earlier run totals. All recorded source hashes were
  unchanged during the combined run.

The combined receipt is COMBINED_VERIFICATION_001.json, with the actual command,
before/after source hashes and JUnit/log files. Shared validation corrections
were tested against actual constructors: rejected raw source claims stay raw,
admitted sources remain consistent, complete-executed membership cannot be
asserted, and invalid relevant MD5/coordinate claims are rejected.

## Filled example and mathematical check

`run_construction_example_001.py` executed the real A/B1/B2/B3/B4 functions over
explicit synthetic inputs and retained every supplied scientific byte object,
the synthetic original parameter object, supplied parsed values, joined result,
numerical sheet and both calculations in `construction_example_001/`.

Two native reported identity fractions, 0.875 and 0, yield 87.5% and 0% and a
mean of 0.4375 = 7/16. The published legacy subject endpoint-difference fractions
0.75 and 0.5 yield mean 0.625 = 5/8. This legacy endpoint quantity is not renamed
inclusive/all-HSP coverage. Both reference occurrences and both subject
occurrences are explicitly linked; one reference and one subject share a full
sequence but remain separate occurrences.

Identity >=0.6 and endpoint fraction >=0.7 select 1 of the 2 published rows.
Raising only identity to >=0.9 selects 0. Both computations preserve the same
sheet digest and all original native/source data. The tests additionally block
file/network/subprocess access and every parser/constructor during saved-sheet
recalculation. Actual executed-input denominators remain null; supplied record
counts are not substituted for them.

## Packaging and remaining full-tool work

The three new schema assets were absent from pyproject package data. A separate
recorded change adds only those assets; pytest configuration is unchanged.
Agent161 confirmed this packaging setting is outside the original test's frozen
recorded source closure. The wheel was built with pip's isolated backend and
verified with `python -I`: all eight pure modules loaded from the extracted
wheel, all three schema assets were present, and reconstructed joins, sheet,
components and changed-parameter results exactly matched the saved example.
The unavailable `python -m build` entrypoint failure is retained separately.

These tests and examples are synthetic supplied data, not a live native
GenomeComparison job. Full directional reports/HSPs, decoded actual execution
and occurrence witnesses, selected AppService/library/provider/typed-return
integration, installed remote service evidence and complete episode verification
remain required work. Fresh170/171 workers have separate producer-retention and
API-wiring interface proposals, not production implementation claims. The
original GenomeAlignment baseline process and its sources were not changed.
