# Compact cells at the typed return boundary

Accepted 362 CONTRACT_ADDENDUM_006 is applied after the actual check001 finding:
77 tests passed, while the 257-member payload-size check failed because four
selected aggregate cells copied 287,930 bytes of mostly repeated input_paths.
The original failed test/receipt/source pins are preserved unchanged.

`RETURNED_NUMERIC_CELL_SCHEMA` contains every existing NumericCell field except
input_paths. `RETURNED_SITE_CHANGE_SCHEMA` is the exact existing SiteChange
schema with its change_indicator replaced by this compact cell schema.
All other numerical return positions use the same compact cell. Complete
ComparisonComponents and their source paths are untouched. No numerical value,
formula, unit, denominator, state, reason, uncertainty or population is altered.

The existing result/calculation identities and selected family, comparison,
member, selection and metric still bind each returned cell. Exact C validation
compares the selected compact cell to its originating supplied component.
D's deterministic recalculation remains the required numerical proof.
Neither a new reference array nor a prose provenance summary is introduced.

The original INTERFACES_001 remains the earlier boundary record. This addendum
changes its full-cell copying description only; it does not claim tool or host
integration completion.
