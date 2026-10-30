# Current batch loss during a new native-result calculation

Additive clarification requested by workload432, 2026-10-27. Original
driver_state=sealed_batch remains that fact after retained batch bytes are lost.
Frozen capture records also remain real custody facts; neither is rewritten.

The closed worker plan does not supply another authenticated original batch
declaration body when its batch RetainedFile is unusable. In that case a lone
parsed-set file cannot independently establish its original parser provenance.
Treat it as retained diagnostic data unless its whole map exactly matches a
reparse of the retained original source. Do not fabricate a batch/SetOutput or
change the historical driver state to make it eligible. Record the current
failure and preserve independently qualified comparisons. This uses the same
fallback as the absent-batch case, without erasing original sealed history.

Previously authenticated saved-sheet recalculation remains a distinct route:
it needs its exact received sheet, not original producer paths or batch bytes.
This clarification adds no output fields, authority store, native invocation,
score change or episode action.
