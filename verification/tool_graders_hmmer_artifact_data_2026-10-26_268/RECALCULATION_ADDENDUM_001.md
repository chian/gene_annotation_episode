# Canonical JSON recalculation correction

Root corrected one production defect discovered by the complete HMMER
Workflow tests in workload277. `_optional_values` used dictionary insertion
order for model-position annotation names. Saving a numerical sheet with sorted
JSON keys therefore changed the order of `optional_fields` during recalculation.
The field values and native model positions were unchanged, but exact saved
result equality failed.

The calculator now explicitly sorts annotation names within each original
position. It preserves original header order, position order, values, references,
numerical formulas and parameters. No output list is normalized by the test,
no native analysis is repeated and no saved historical result is rewritten.

Ten regression cases use retained native conversion output (current ASCII and
annotated revisions 3/a through 3/f) and single/indexed/unindexed model retrieval.
Each compares the full original calculation against recalculation after both
canonical JSON storage and reversal of every JSON object's key order. The
tests prohibit file access, network access and native execution during
recalculation and verify that the saved sheet is not mutated.

- `check004`: 105 existing cases passed; all ten new cases failed before the fix.
- `check005`: all 115 cases passed in 3.61 seconds after the fix.

Both runs used the existing bounded local execution path with 20 GiB RAM,
4 GiB scratch and no wall-time limit. Exact source identities and test output
are retained in the original intent/receipt/log files. The worker's saved-sheet
dispatch and the result projection's model-association/scalar consumers were
inspected. The change does not alter either interface.

This correction establishes deterministic component recalculation. Full shared
Workflow verification remains separate under workload277. Binary/HMMER2 model
body decoding and index-internal decoding remain explicitly unimplemented.
