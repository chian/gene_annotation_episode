# Targeted A108 populating contracts — all UNIMPLEMENTED

These functions are specifications for populating the exact numerical sheet.
They are separate from investigation prompt text. No function is registered,
deployed or integrated into an episode, library or credit consumer. The arithmetic
check script is a fixed research fixture, not an implementation of these readers.

## Typed records shared by the contracts

`NumericObservation`:

- `value_kind`: `point | interval | left_censored | right_censored | missing`.
- `value`, `lower`, `upper`: finite real or null as appropriate; bounds may use
  explicit `unbounded=true`, never fabricated finite infinity.
- `lower_closed`, `upper_closed`: booleans preserving < versus ≤.
- `unit`: explicit unit including basis, e.g. `ppbv_H2_gas`, `mM_tetrathionate`,
  `percent_O2_v_v_gas`, `percent_O2_saturation_solution`; incompatible bases are
  not interchangeable.
- `uncertainty_kind`: `instrument_bound | confidence_interval | SD | SEM |
  display_reading_range | no_reported_uncertainty`; `confidence_level` real/null.
- `origin`: `source_reported | dataset_observed | source_graph_derived |
  calculated | synthetic`. Synthetic values cannot be silently promoted.
- `source_ref`, `locator`, `original_measurement_id`, `correction_ids`: references.

`ContextUnit`:

- `unit_id`, `independent_cluster_id`, `collection_id`, `sample_frame_id`.
- `organism_ref` nullable; `strain_genotype_ref` nullable; `compartment_code`;
  `life_or_infection_state_code`; `collection_time`; `time_window`.
- `weight`: positive real; `weight_unit`; `weight_basis` in
  `equal_probability | sampled_duration | sampled_volume | inclusion_probability`;
  actual weight operand/denominator and source.
- `observations`: requirement-keyed `NumericObservation` or observed discrete
  state with physical meaning; no unrestricted reader-authored finding as a score.
- `technical_replicate_ids`: list of references; `population_membership`:
  `in_scope | out_of_scope | unknown`; unknown is not silently excluded.

`OperatingRequirement`:

- `requirement_id`, `candidate_id`, `endpoint_ref`, `studied_subject_ref`.
- `target_relationship_ref`: existing measured/declared relationship; nullable
  if unresolved, no new scalar transfer weight.
- `coordinate_units`: list of physical variable/unit pairs.
- `supported_regions`, `contradicted_regions`: disjoint lists of explicit
  numerical boxes or enumerated measured state sets, conditional on
  `background_condition_refs`; may be empty when unmeasured.
- `joint_domain_support_ref`: reference identifying joint measurements or
  explicitly justified separability; missing means joint membership unresolved.
- `interpolation`: `none | explicit_model`; model coefficients, model domain and
  uncertainty required for the latter. A named model without operands is invalid.
- `domain_uncertainty`: explicit threshold/domain bounds; `dependency_ids`.
- `axis_owner`: original A105/A106/etc. or contextual measurement; required
  so the same experiment is not reclassified as independent A108 proof.

`CandidateScope`:

- `candidate_id`, `target_material_ref`, `function_meaning_ref` and `scope_ref`.
- `target_input_kind`: `sequence | selected_file_record | bounded_snippets`.
- `scope_condition_codes`, `relevant_requirement_ids`, `sample_frame_id`.
- `scope_revision_id` with reason for changes; revisions never create independent
  candidates or new observations. No initial candidate is required for extraction;
  aggregation begins when one has emerged and its meaning is stated.

`ContextScore`:

- `sum_weights`, `known_supported_weight`, `known_contradicted_weight`,
  `unresolved_weight`, `n_independent_units`, `n_technical_measurements`.
- `condition_cells`: each numerator, denominator and nullable ratio.
- `compatibility_lower`, `compatibility_upper`: [0,1]; `point`: real/null.
- `display_lower`, `display_upper`: 100×compatibility bounds.
- `sampling_interval`: bounds/null and the exact n, alpha, method and assumptions.
- `status`: `fully_observed | partial | no_data | incompatible_scope`.
- `missing_input_codes`, `conflict_refs`, `used_dependency_ids`, `formula_version`.

## Specific functions

| Function, all UNIMPLEMENTED | Exact inputs | Populated outputs and deterministic limits |
|---|---|---|
| `a108_read_context_literature` | Primary artifact; selected passage/table/figure locator; named environmental variable; sample identity; actual study subject and conditions | ContextUnits and NumericObservations. Copies values/units/censoring/n exactly; marks graph readings separately; leaves calibration/LOD/local mapping unknown when absent. Does not infer zero from nondetection or exact n from n≥3. |
| `a108_read_context_dataset` | Selected table/rows; field-to-variable map; unit/basis map; actual specimen, technical replicate and collection identifiers; sampling frame/design | Same ContextUnits and NumericObservations. Checks row identity and distinct independent units. Repeated assays remain one unit. Sampling weights require actual design operands. |
| `a108_read_calibration` | Matched blank values, known spike concentrations, measured increments, dilution/unit conversions, source correction declaration | Blank and recovery records with linked uncertainty; r=increment/spike. It must not apply a correction already listed in `correction_ids`. |
| `a108_normalize_local_exposure` | Apparent measurement, calibration output, explicit bulk-to-local model and its operands, or stated identity mapping from an actual local measurement | Corrected local bounds using section 2 formulas; exact units and correction provenance. Unknown local mapping returns missing local exposure and preserves bulk data. |
| `a108_import_operating_requirement` | Existing characterized endpoint record and native experimental conditions; candidate meaning; existing target relationship; explicit domain/model specification | OperatingRequirement. Preserves original axis ownership/dependencies. A sufficient test concentration does not automatically become a minimum, and a reported nonsignificant difference does not become a numerical equivalence interval. |
| `a108_compare_context_scope` | CandidateScope, ContextUnit, OperatingRequirement and measured condition transformations | Mapping status `matched | model_mapped | unresolved | irrelevant`, enumerated mismatches and transformed numerical operands. No universal relevance weight. `unresolved` retains [0,1] on the affected requirement; `irrelevant` must be justified against candidate meaning, not used to drop adverse evidence. |
| `a108_resolve_membership` | Corrected local value sets, joint operating domain/uncertainty, scope mapping | ell_ij/u_ij and joint L_i/U_i with exact supporting operands. For conflict, missing detection limit, unmatched background or unsupported joint interpolation, returns unresolved membership rather than a grade. |
| `a108_compile_context_sheet` | Deduplicated paired memberships, fixed population denominator, weights, independent cluster design, optional alpha=.05 reporting request | ContextScore through the exact sums/products in the sheet; conditional component ratios; supported/unresolved/contradicted masses. Applies no source popularity or replication multiplier. The Hoeffding display is supplied only for the stated independent equal-weight sample/cluster design; otherwise sampling interval stays unknown. |

Graph extraction additionally requires the image, calibrated axis ticks, scaling
(linear/log), selected mark coordinates and a declared display-reading interval.
It returns `origin=source_graph_derived`. Error bars cannot become confidence
intervals unless their definition and independent denominator are known. The
current tetrathionate 3.3 mM value was manually visually read, not extracted by
an implemented graph reader.

Every literature and dataset value reaches the same fields. No separate formula
is used because a value came from a paper, sensor table or metabolomics file.
Literature selection/interpretation can be intelligent; arithmetic, units,
deduplication and sample denominators should be deterministic.

## Validation and structured missing outcomes

Nonpositive denominators, incompatible unit bases, a duplicated ID with different
values, overlapping supported/contradicted domains, unknown local mapping,
unverified transfer, unsupported joint-domain construction, missing censor limit
and missing population definition have distinct codes. Preserve usable cells
alongside those codes. Do not turn the codes into runtime gates, requests for
approval or scientific stopping rules. `point=null` is not a numerical zero.

The final record must satisfy:

1. 0≤lower≤upper≤1 and all masses nonnegative.
2. supported + unresolved + contradicted = total denominator.
3. No original sampling unit contributes weight twice.
4. Conditional ratio denominators equal their preceding joint numerator.
5. Every calculated value has operands and a formula version; every source value
   has a locator and origin flag; every synthetic value remains labeled.
6. Domain/subject/context dependencies appear once, with no second application
   of source corrections or A105 reliability factors.

These are proposed reader-output constraints, not implemented checks or evidence
of production readiness. There is no investigation prompt insert in this folder.
