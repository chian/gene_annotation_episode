# Coverage depends on the information needed by its selected basis

Accepted additive clarification for workload143, 2026-10-25. This supplements
015 without changing the frozen output records or repairing native alignments.

Individually valid native rows keep their coordinates when another row makes a
block ragged. Alignment aggregates that require trustworthy shared columns stay
incompatible. Coverage follows its actual per-basis dependencies:

- `represented` uses the selected actual nongap cells of the member itself.
  Its full selected fraction is available when those cells/spans, the matching
  complete source and the explicit complete selection are known. A different
  width in another row alone does not make these known positions unknown.
- `multi_member_block` additionally requires unambiguous membership with at
  least two distinct valid positive selected members. Differing widths alone
  do not change their recorded presence. Missing/ambiguous required membership
  keeps the dependent result partial.
- `cooccupied_column` depends on trustworthy shared alignment columns. Ragged
  alignment cannot establish its full selected fraction merely because some
  array indices happen to exist in both rows.

For example, two individually valid/source-matching positive rows of lengths4
and3 in one terminated ragged block can each have known represented native
positions and a fraction relative to its own known source. They do not establish
a valid four-column pair comparison or a complete cooccupied-column fraction.
Selected coordinates absent from an actual row remain absent; this clarification
adds no padding, inferred repair or silent removal of selected observations.
