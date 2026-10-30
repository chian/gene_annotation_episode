# Shared fluorescence sheet and validation implementation

This packet implements only the assigned shared data contracts and sheet builder
for `perform_facs_cell_sorting` and
`analyze_cytokine_production_in_cd4_tcells`. It does not complete either operation.
Original goal authority is the user attachment; no goal file was read or written.

The frozen contract is packet557 `CORE_CONTRACT_001.md`, plus its additive port
clarifications002–005. `source-audit.json` records the exact input and owned-file
hashes, import inspection, AST checks and test execution limitation.
`changes.patch` is the exact addition diff for the three owned source/test files.

## Consumer examples

`tests/test_fluorescence_event_sheet.py` supplies these explicit synthetic
fixture constructors for consumers and the bounded verification runner:

- `parsed_fixture()` returns an `EventParseResult`: original event ordinals
  `[0,1,2]`, values `[90,100,100]`, explicit supplied-predicted origin, one sample,
  an as-supplied domain, exact channel identity and separately retained analyte
  association artifact.
- `sheet_fixture()` joins that batch with an explicit inclusive threshold100.
- `components_fixture(sheet)` supplies a manually specified component bundle:
  selected ordinals `[1,2]`, rejected `[0]`; population cells
  retained3, parent3, parent-unknown0, evaluable3, selected2, rejected1,
  unknown-gate0; selected fraction `2/3`, percent `66.66666666666666`.
  This fixture does not import or call the numerical calculator.
- `derived_fixture(primary, partial=True)` supplies correspondence from prepared
  source rows0/1 to original events0/2 while retaining only prepared row0.
  Original event1 and the unobserved prepared row remain missing evidence.

These examples are deliberately synthetic contract fixtures, not scientific
measurements. Their validity is to be checked by the root runner; the owner has
not executed the tests or imported application code on the host.

## Verification boundary

Exact selector: `tests/test_fluorescence_event_sheet.py`.

The owner performed standard-library source, AST, hash and file checks only.
No pytest, application/scientific import, native program, dependency install,
network acquisition or scientific analysis was run by this lane. Tests are
unrun until the root agent records a bounded-run result.

Validators preserve their original input objects. The builder deep-copies the
joined saved sheet. Validators inspect represented relationships and pointer
resolution, and never recalculate gate membership or scientific numeric values.
Artifact custody, actual calculators, authentic FCS parsing, configured execution,
the real child-owned result path, requested returns and closed replay remain
separate obligations.
