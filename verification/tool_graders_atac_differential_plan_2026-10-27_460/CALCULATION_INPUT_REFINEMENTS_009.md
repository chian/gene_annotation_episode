# ATAC calculation input refinements

This additive implementation record preserves contracts004–008 and the user's
original goal. It clarifies two concrete consumer issues found during review;
neither is a new episode decision, credit rule or scientific acceptance gate.

## Parameter validation with an empty comparison

The per-interval numerical leaf rejects an unknown depth unit or a nonpositive,
nonfinite pseudocount. The interval-component iterator must apply those same
parameter checks even when its input contains no intervals. An empty comparison
does not make an invalid mathematical declaration valid.

Root owns a shared pure function in `atac_differential_scores.py`:

```
validate_atac_likelihood_parameters(*, depth_unit: str,
                                    pseudocount: int | float) -> float
```

It returns the already accepted finite positive binary64 pseudocount or raises
the existing parameter-specific ValueError. Both the leaf and
`iter_atac_interval_components` call it. The iterator validates before consuming
its first segment. Missing, zero or invalid depth measurements remain numerical
input outcomes handled by the leaf; this does not turn missing evidence into a
parameter error. Numerical formulas and original native precision stay unchanged.

Verification includes invalid declarations on empty input, invalid declarations
before an input iterator is consumed, and the existing native numerical cases.

## Native reference bounds versus selected comparison bounds

The parser's exact retained row port and `ordered_row_index` remain unchanged.
Rows with known geometry extending past the actual declared reference sequence
must not be removed from that index: removing one could conceal an overlap and
make another row appear unambiguous. Raw values, lexical tokens, coordinates,
source ordinals and source-located issues remain retained in the native sheet.

The separate calculation-input consumer validates each row against its actual
reference dictionary. A row crossing that reference boundary retains its ordinal
and geometry in the sweep input, but supplies a null calculation operand.
Therefore an otherwise unique affected span is invalid, and a span overlapping
another row remains ambiguous. This is not a repaired or validated native value.
The original numerical value remains accessible by its source row in the sheet.

Clipping a valid row to a narrower explicitly selected comparison interval is
different and remains valid: that interval is the requested population, not the
reference sequence's physical length. Unknown or conflicting reference mappings
cannot authorize a numerical join. Retained-table geometry is checked while its
rows are consumed, with late failures preserved as partial outcomes. No native
row or BED coordinate is rewritten. Root owns this consumer; parser workload464
does not implement a competing projection or silently filter the raw row port.

This record does not establish production integration or increase the tally.
