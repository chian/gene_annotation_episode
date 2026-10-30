# Three concrete provider interpretation boundaries

This additive clarification applies to the accepted provider workloads. It
does not modify the original frozen files, numerical formulas, episode behavior
or the immutable goal. Root inspected the existing original-coverage calculator,
native membership parser and exact provider types before resolving these gaps.

## Transformation digests

`before_sequence_sha256`, when non-null, identifies the single original input
member's exact sequence-symbol digest recorded in its actual MemberFact. It
must equal that digest and requires exactly one input member. If there are
multiple original members, or their single digest is unknown, this scalar is
null; their individual original facts remain in InputBindings.

`after_sequence_sha256`, when non-null, identifies exactly one complete output
AlignmentRow.sequence: SHA256 of its UTF-8 bytes, retaining case and every
literal gap/symbol. It requires exactly one output row. Do not accept either
gapped or ungapped strings interchangeably. Multiple output rows or an
unavailable/incomplete output use null. This field is not an original-residue
map. Nongap offsets, translation widths, strand and actual original intervals
still require their separately typed correspondence evidence. Concatenation
retains its distinct input-member digests; no combined input hash is invented.

These conventions define previously ambiguous nullable scalar fields. They do
not change native artifact digests or normalize any source bytes. Verify exact
gapped/case-sensitive matching, rejection of an ungapped alternative, single vs
multiple operands, and unknown digests without losing unrelated matrix facts.

## Native duplicate membership records

The native parser retains original duplicate feature occurrences and their
diagnostics. A saved Family.memberships record represents biological membership
as ordered unique IDs, with source_table_id/source_row_index resolving the
complete original raw record. Derive each of feature_ids/deleted_feature_ids/
missing_codon_feature_ids by stable unique projection of its corresponding
native list. Preserve all original occurrences in native_tables and ReadOutcome
diagnostics. Add a finite qualification for this explicit projection; it is not
a silently altered native list and does not create additional biological votes.

An included/deleted or included/missing contradiction has no unambiguous
membership projection. Retain the original table row and error, omit only that
contradictory typed membership record, and retain a precise unmet membership
requirement. Independently evidenced matrix, tree and other family records
remain usable. Explicit supplied contradictory matrix/joins remain structural
errors. Do not normalize duplicate features within a supplied family matrix;
that matrix must establish each exact feature/genome relationship once.

## Saved model validation

Extraction checks each ModelAssociation.read_id/log_model_index against the
actual supplied RAxMLRunObservations and copies its real parameters/locations
into PartitionModel. Save the exact assembly mapping and reader outcomes.
Saved validation checks the resulting read, artifact, partition and source
location relationships without reparsing native logs. It must not claim to
reconstruct the original input-only model array or recheck its full index range
from the flattened sheet. C4 separately authenticates the originally published
immutable sheet; pure recalculation validates and uses its actual saved numbers.
No new model confidence, inferred missing model, extra reader call or duplicated
raw-log model table is introduced to pretend that absent information exists.
