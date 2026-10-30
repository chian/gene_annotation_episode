# XMFA calculation boundary clarifications

Accepted additive clarification for coding worker143, 2026-10-25. The complete
frozen XMFA records and the accepted workload014 stay unchanged.

For `symbol_counts[].count`, the exact method ID is `xmfa_symbol_count_v1`.
Other cells use their named scientific field and the accepted prefix/basis.

An explicit CellRef identifies a particular retained native row. Valid native
coordinates for that row survive a neighboring ragged row or block-width
conflict. Aggregate cells depending on unusable/conflicting selected members
remain null/incompatible. An unrelated unselected row does not erase measurements
for an explicitly narrower valid selection. Keep actual scope/completeness
qualifications; never silently filter a selected bad row from its denominator.

Original coverage completeness is evaluated per original occurrence, against
selected placements in the source-record components explicitly associated with
that occurrence. Unrelated contigs mapped to other occurrences need not also map
to it. Within a participating component, selected bases lacking any usable
original map make mapping incomplete and its fraction null, while known union
remains available. A selected base explicitly mapped only to another occurrence
is accounted for; it is not an unexplained gap in mapping. Unselected positions
need not be mapped for this selected-coverage calculation.

Conflicting maps suppress ambiguous bases for the affected occurrence;
independently consistent occurrences survive. Conflicting original_length values
for one occurrence invalidate that occurrence's denominator. The function never
infers that an unmapped component belongs to an occurrence from a shared name,
sequence, taxon or source container. All actual maps and qualifications remain
inspectable in the retained binding and full output.
