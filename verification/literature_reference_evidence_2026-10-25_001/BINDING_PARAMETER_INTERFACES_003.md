# Source row indices and canonical observation aliases

source.row_index is the zero-based JSON array position. A primary_table locator's
row_index is its separately retained original table coordinate. They need not be
equal; no source coordinate is silently rewritten to match an extraction array.

Retain alias transcriptions in output reference_rows/test_rows for provenance.
For numerical operand selection, canonicalize identical visual observations by
original_source_ref,original_artifact_ref,image_region, irrespective of wrapper
source/ref or JSON row order. The same physical measurement with matching parsed
value, relation, spread and subject/state/experiment/ligand supplies one operand.
Reprinting that operand cannot make an otherwise available ratio ambiguous.
Different parsed values or meanings at that same physical location are conflicting.
Several distinct physical observations in one arm remain ambiguous in this finite
single-parameter contrast; no averaging, extra independent count or precision is
inferred. These clarify interface001 rather than changing any historical sheet.
