# Numerical-cell qualifications and explicit input origin

Concrete implementation questions from the three owners are resolved here.
Earlier contracts stay unchanged as records. This does not change the goal.

## Reader input

ChannelBinding gains one required field, `measurement_origin`, whose allowed
values are observed|supplied_predicted. This is explicit caller information;
the reader never infers origin from a filename or numeric content. Finite parsed
values copy that field into Value.state. The saved Channel shape is unchanged:
each Value already retains its origin. This supersedes001's ChannelBinding key
set only; the public parser function signatures and EventParseResult are unchanged.

An explicitly unavailable/failed requested domain yields no accepted events and
measurement_domain_unavailable, preserving its original domain state. Retaining
source bytes does not establish an available numeric domain.

A UTF-8 failure after complete CSV records preserves only that complete prefix,
with partial extent and input_encoding_invalid. Do not feed a truncated physical
line to the CSV parser as a completed record. Failure in the first/header record
leaves unavailable data. A malformed snapshot row that is not a list retains its
ordinal as unavailable cells; an invalid individual value is an invalid cell.
JSON NaN/Infinity constants reject the document as stated previously.

For requested positional channels A/B, actual header A and data row `1,2`, retain
value2 at declared ordinal1 with channel_missing/header and invalid_event_row/width
qualifications. Do not invent B's native header name or shift another column.
The caller's explicit positional binding is the only association for that cell.

## Request identity and fixed units

Reject duplicate control_key requests even if include_legacy_clipping differs;
there is no implicit merging of conflicting request flags. Explicit and implicit
FractionRequests each yield selected_fraction and selected_percent through the
same helper. Control operand fractions are visited target then control in control
request order, appended once before control cells, and deduplicated against all
explicit fraction requests. No duplicate CellRequest identities are generated.

Units are exactly events, dimensionless, percent and percentage_points for their
corresponding counts, fractions, percentages and percentage-point differences.
Intensity count/missing_count use events; sum/mean/median use the saved channel
unit, including null when unknown. Population and intensity-count cell values
must be nonnegative integers. Fraction and percent cells have ranges [0,1] and
[0,100]. Shape/range validation does not recalculate any numeric answer.

## Count qualification

With an available primary population:

| Cell | Qualified rather than present when |
|---|---|
| retained_event_count | Declared root population incomplete |
| parent_event_count | Root incomplete or parent membership has unknown ordinals |
| parent_unknown_count | Root incomplete; this diagnostic count is exact for a complete retained universe |
| evaluable_event_count | Root incomplete or parent membership has unknown ordinals |
| selected_event_count | Root incomplete or final gate membership has unknown ordinals |
| rejected_event_count | Root incomplete, parent membership unknown, or parent_nonevaluable nonempty |
| unknown_gate_event_count | Root incomplete or parent membership unknown |

An explicit finite subset can have complete extent despite a partial original
source. An unavailable primary source/domain still makes all seven count cells
unavailable, never zero. False current predicates can exclude uncertain ancestors;
therefore selected_event_count qualification follows final unknown membership,
not the existence of any ancestor uncertainty that has already been excluded.

## Requested projection status

Views deep-copy only selected saved cells. Their issues are the stable deduplicated
union of those cells' issues, across all selected requests before pagination.
They do not copy unrelated whole-component issues or unrequested samples' failures.
Status is computed from selected saved Cell.state values, without numerical work:

- unavailable if a nonempty selected request set has no present/qualified cells;
- partial if any selected cell is qualified/unavailable or its issues remain;
- calculated otherwise, including an empty requested selection.

Pagination does not change the selected-result status. Original component status
and issues remain unchanged in their retained artifact. This is requested-field
projection, not new scoring or a new biological-success criterion.
