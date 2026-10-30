# Additive exact-field correction

The final machine-readable example is `filled_cells_002.json`. It preserves every numerical value and bound in `filled_cells.json`; the first file and its generating checker remain available as research history.

The first generated record had several formatting defects: native-route `E` was labelled with fraction units instead of signed-index units despite being not applicable; the version string appended an explanatory phrase to `12.5`; the timestamp was an incomplete manifest reference; formula/input fields sometimes contained expressions rather than retained references; and the coverage field used a new descriptive literal outside the current field sheet's enum.

`check_fields_002.py` corrects those fields in a separate output. Version is exactly `12.5`, observed via the separate version endpoint in the same session. The timestamp is the actual response-file save time, with that meaning preserved in the request manifest. Formula and input references point to retained material. Coverage uses the existing `own_cross_case_read` value for this new comparative example; the source trace separately records its actual native retrieval and paper-reading boundaries.

These are format corrections, not new score transforms. The result remains `t=S=c=.844`, `O=0`, with native `C` and `E` not applicable. No production schema or reader was changed.
