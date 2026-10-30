# Shared saved-sheet validation workload

This defines the remaining shared dependency named in B4_FREEZE_003. Root may
assign its implementation to a fresh worker with exclusive ownership of new
`bvbrc_proteome_sheet_contracts.py`, `bvbrc_proteome_sheet_schemas.json`, its own
tests and verification directory. Existing B0/native files and the B4 calculator
are separate owners. This is validation of saved data, not a sheet builder.

Public functions are `proteome_sheet_schema(name: str) -> dict` and
`validate_proteome_sheet_data(name: str, value: dict) -> dict`, returning detached
copies. Fixed errors use existing ProteomeDataError(code,path). Required entry
points are NativeSheet, NativeSheetResult, NativeCalculationParameters,
NativeComponents and NativeComponentsResult. Other named subshapes can be
exposed for composition only with their applicable structural checks.

Use exact DATA_SHAPES_PROPOSAL_002 definitions, preserving all33installed B1
definitions and A's definitions unchanged. A separate package asset avoids
changing B0's frozen asset while its tests finish. The normative meanings are
proposal001 plus correction002 and B1_PARAMETER_SOURCES_002; do not reinterpret
the original records. The full goal and sixteen principles remain authoritative.

Meaningful saved-sheet checks must cover:

- All nonnull native projections pass the existing data-only
  validate_native_projection. A primary source resolves uniquely to a retained
  valid projection. Native cells/keys copied into the sheet exactly match it.
- Each supplied inventory, metadata snapshot and input index passes existing
  B0 validation. Inventory/snapshot identities and row ordinals cannot be
  silently merged. References resolve to the appropriate retained occurrence.
- Reference and comparison track identities, ordinals, selected input mapping,
  copied source fields, record membership and metadata indices remain coherent.
  A malformed table row cannot claim a trustworthy positional interpretation.
- Null/unresolved joins cannot carry an admitted protein. Joined proteins must
  resolve to the saved source/index/link and satisfy the existing B2 structural
  requirements. Validation checks declared links; it does not select or create
  a link. A matching label is insufficient.
- Correction002 disallows promoting locator-only execution or occurrence
  claims. No exact-executed denominator or complete-executed membership can be
  admitted under the current witness interface. Preserve missing values and
  declared raw claims separately. Native descriptive measurements remain usable.
- Reference/association array populations, unique keys, copied-cell equality,
  declared count/null states and alternate-representation associations must
  remain consistent. Numerical formula correctness belongs to B4 and its
  independent tests; no parser/calculator rerun during saved-data validation.
- Full directional-report attachment is unfinished. Accept None, or an explicit
  unavailable attachment retaining zero reports and its missing requirements.
  Do not admit claimed complete scientific reports without the missing format
  and witness contract. This is a precise unfinished interface, not final scope
  reduction or a new scientific acceptance rule.
- Parameters have unique selected comparison tracks, finite fraction thresholds
  and unique allowed categories. The calculator additionally checks parameter
  track membership against its supplied sheet. NativeComponents preserves the
  explicit parameters/sheet digest, one result per selected track/association,
  usable-number versus unknown states, correct per-field populations and
  references. Do not calculate a mean or rerun scientific arithmetic to validate
  a saved component. Small array membership/count checks are data integrity.

The worker must inspect the actual accepted A/B0 modules, frozen filled examples
and complete B4 consumer. Tests include populated saved data and adversarial
mutations of source refs, copied numbers, native keys, input occurrences,
unknown denominators, unavailable witness claims, false completeness, duplicate
tracks, malformed cells and components. Validation must not read source bytes,
execute a parser/calculator, perform network/Store calls or assign credit.
Preserve valid partial native data instead of rejecting merely because a full
scientific dependency is missing. No registry or episode change belongs here.
