# Rfam table-native measurements in requested returns

Root owns this backward-compatible extension of v2 tblout selection. Existing
JSON metrics, saved JSON/table calculations and v1/v2 report behavior remain
unchanged. New table selections can request the following already retained native
Infernal components; no extra acquisition or calculation model is introduced.

| Field | Exact source/calculation | Unit/denominator | Missing behavior |
| --- | --- | --- | --- |
| native_bias_bits | native_calculation.hits.components.bias_bits | bits; no denominator | invalid/missing native cell stays null |
| native_model_from_1i | sheet.hits.model_from | model position, one-based inclusive | invalid model geometry stays null |
| native_model_to_1i | sheet.hits.model_to | model position, one-based inclusive | invalid model geometry stays null |
| native_model_span_positions | native_calculation.hits.components.model_span_length | emitted model positions; end-start+1 | invalid geometry stays null |
| native_model_span_fraction | native_calculation.hits.components.model_span_fraction | emitted model span / explicitly bound full consensus length | missing/conflicting denominator stays null |

These are table coordinate spans, not represented alignment positions or
residue correspondence. Preserve native reporting/inclusion classifications in
the full original sheet; do not convert them to numerical confidence.

Expose a separate RFAM_TABLE_HIT_METRICS/projection validator. The v2 tblout
selector uses it; JSON selectors continue to reject table-only metrics. Existing
rfam_result_rows keeps its fields and gains these explicit numeric enum options.
Return validation selects saved values only; old artifacts remain replayable
and cannot be expanded beyond their original selector. Wrong/unbound query
identity invalidates attributed values as before. Pure Infernal calculations
remain unchanged and fully retained.

Verify actual six-query native table: bias0, model intervals1..120 except
prefix70's1..71, and unavailable full-model fractions. Show that native model
span is available while represented alignment positions remain unavailable.
Verify new selections do not enter JSON and do not alter original saved views.
