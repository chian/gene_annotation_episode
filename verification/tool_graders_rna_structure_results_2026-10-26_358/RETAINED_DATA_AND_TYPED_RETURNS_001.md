# Exact retained structure versus current requested returns

This records the existing single-structure implementation for root's later
question-specific comparison and presentation work. It implements no new
scientific family, comparison, perturbation, display or model prompt. Read the
later user direction in 349/USER_DIRECTION_009.md alongside this boundary.

The complete retained RNASheet contains original_input.sequence and, for
supplied structures, original_input.dot_bracket. It retains the selected
structure.dot_bracket, optional energy_dot_bracket and the explicit
energy_conversion.index_map. analysis_sequence preserves original_sequence,
analysis_sequence, case_operation and original_to_analysis_indices.
topology.positions retains every original index/input_index, bracket,
partner_index, pair_key, stem_key and unpaired_region_key. Full pairs, stems,
regions, interval associations and sequence_pairs remain in the sheet. An
explicit subject binding also retains its original subject, complete sequence
artifact, interval and strand; publication checks the actual Store mapping.

The current typed numerical families are summary, pair, stem and region:

| Requested family | Structural association carried in its current typed row |
| --- | --- |
| summary | Original record/structure association and selected scalar cells |
| pair | Selected zero-based indices [i,j], pair key, symbols and ordered pair; selected pair-span cell |
| stem | Ordered member pair keys and pair indices; selected stem-length/stack cells |
| region | Region kind, closing pair key, immediate branch keys and exposed half-open intervals; selected region cells |

All numerical rows carry the explicit selected calculation parameters and the
complete component generation's calculation_key. A qualified subject_ref does
not expand into a full interval/strand mapping in those rows. Their selector
uses family row keys or ordinal windows; it has no arbitrary selected-base
request. These typed rows do not contain the complete sequence/dot-bracket or
per-base positions table. Source possession and summary-only return do not
authorize expanding them into that retained data.

An explicitly requested SavedRNAInput descriptor grants its declared source,
handoff, original bundle and sheet operands, allowing the exact full sheet to
be used in the separately selected saved-sheet calculation route. The
descriptor must itself have been received through an authenticated eligible
typed form. Merely knowing the same artifact handles grants no such route.
This is custody and calculation authority, not a dedicated structure display.

The synthetic nine-base example retains GGGAAACCC / (((...))). Its positions
0, 1, 2 pair with 8, 7, 6 respectively; 3, 4, 5 are unpaired in the hairpin closed by
(2,6), whose interval is [3,6). Three GC pairs form one three-pair stem with two
stacks. Full arrays are retained even when the parent requests four summary
cells. The actual complete JSON snapshots are in each successful check's
examples/features_delivery.json and examples/prediction_delivery.json.

No current row computes cross-structure correspondence, changed-pair counts,
selected-position changes, conservation, perturbation ranking or biological
importance. Those require the parent's explicit question, the agreed comparison
population and correspondence/parameter contracts, and separately selected
measurements. The user has rejected returning every structure for a scan and
has not accepted the aggregate-only illustrative display as a universal return.
Root owns that additional contract and any subsequent implementation.
