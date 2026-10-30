#078 additive final ownership and native cross-field clarification007

The closed native row/array schemas are supplemented by these REQUIRED exact
cross-field validations in the native fact populating/projection functions:

| Row kind | Exact identity / fields |
| --- | --- |
|native_raw|component is the selected role's `<role>_response`; reading is nonnull and matches primary/companion key; pair_key/reading_assignment null. native_reading is EXACT actual original arm's native numeric projection, or null only for a genuinely absent/missing arm with the matching unavailable cell. reported_uncertainty is only that actual selected row's retained canonical uncertainty|
|local_difference|component=local_difference; exact selected pair_key; reading/reading_assignment/native_reading/reported_uncertainty null; cell formula=condition_control_difference; context/dependencies only the actual selected two readings and pair science|
|local_variance|component=local_variance; same exact pair; formula=local_joint_covariance; complete full source-C validation and actual pair owner/index/unit/scope dependencies; no raw magnitude/spread expansion|
|local_standard_uncertainty|component=local_standard_uncertainty; same exact pair; formula=local_square_root_variance; identical scientific/source-C validity support; independent finite display check|
|final|component one original twelve; key=final:<component>; reading/pair_key/reading_assignment/native_reading/reported_uncertainty null; source projection_status ready and exact final_projection_basis; original full cell and complete semantic/dependency projection match saved final sheet|
|conditional|component one original twelve; exact original supported joint index/map and scope; key=joint:<index>:<component>; reading/pair_key/native_reading/reported_uncertainty null; no final/unaffected promotion while active reconciliation unresolved|

For every row, canonical sheet_ref resolves to the ORIGINAL selected immutable
population source in the ACTUAL run; component_key round-trips against its exact
saved selector/assignment/roster and allowed requested name/view/key filters.
Schema-valid arbitrary keys do not authorize values. Unavailable cell reasons,
unit/approximation/graph bounds, original origins/methods and scientific statuses
must be copied from the exact selected result, not recomposed by a model.

Scientific context identity/status relationships validate against actual saved
meanings. Known requires its actual canonical IDs; unknown/conflicting cannot
retain invented known IDs. Numeric availability alone supplies none of these
relationships. Model/variance status reflects THAT component and actual source
scope. Source-kind/origin/method arrays include its actual relevant readings,
never unrelated A merely because the full population contains A.

Unrequested numeric locations include each unexpanded source response, graph
ordinate/calibration location where relevant, and source-C numbers. Derived-only
rows reveal their actual result and necessary semantic conditions, not the hidden
raw source values. Existing per-source unresolved-location masking is used when
exact coordinates are unavailable. Conditional assignment/selector metadata is
lineage, not permission to fetch private source content or all child cells.

The source/raw/native symbolic mixed-origin case in006 is NOT actual mixed-origin
scientific execution. Actual073 outputs retain synthetic source origin alongside
actual graph method. No synthetic source row is relabeled to stage a mixed-origin
proof. Future origin-path tests and actual primary scientific validation remain
required after design review.
