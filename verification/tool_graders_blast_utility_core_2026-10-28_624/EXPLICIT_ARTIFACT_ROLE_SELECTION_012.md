# Explicit native artifact role selection for prepared-database reuse

Implementation clarification under the unchanged goal.629's exact-ordinal
artifact selection cannot request a native file category before the native
program chooses the family size and metadata position. Reusing a prepared
manifest also requires an explicit grant for its original preparation receipt
and selected metadata artifacts; source existence must not grant them.

Root extends only artifact selector ordinal to int>=0 or null. Null explicitly
requests every original occurrence with the selected direction and role. It is
not a default or source-wide artifact grant. Returned occurrences keep concrete
original integer ordinals and byte identity. Overlapping explicit requests are
fulfilled with each occurrence once, preserving request order then original
occurrence order. No matches yields the same typed missing artifact request,
with null ordinal retained. Saved selector validation and returned-reference
validation use the same shared matching helper, without parsing/calculation.

The original bundle is an actual retained output preparation_receipt occurrence
ordinal0 in631, permitting explicit selection. No other original capture row
or source payload changes. Root's new Workflow requests that receipt and all
output database_metadata occurrences explicitly, plus the prepared manifest;
it does not receive binary database files or unrelated artifacts by implication.
Numeric fields, credit, episode types and model prompts remain unchanged.
Existing exact-ordinal selectors retain their meanings. Verify grouped role
selection, overlap deduplication, zero matches, exact-original returned ordinals,
forged extra artifact rejection and source-only exclusion. Historical089 tests
remain evidence for their original source; a new allocated check verifies this
specific additional contract and its regression consumers.
