# Exact proposed A111 reader inputs and outputs

All interfaces here are **unimplemented production functions**. The research calculator is not their implementation. They populate the fixed numerical cells in `PROPOSED_A111_SHEET_001.md`; they do not create a generic grading language, decide episode actions, require an initial candidate annotation, or compose prompts. Deterministic calculations consume measurements/typed selections. A literature extraction function can identify quoted quantities and allowed interpretations; it cannot fabricate missing measurements or assign overall confidence grades.

## Shared typed records

`NumberCell` has exactly these fields:

| Field | Type / permitted values |
| --- | --- |
| `value` | finite number or null |
| `lower`, `upper` | finite numbers or null; bounds must both exist or both be null; lower≤upper |
| `unit` | `fraction`, `angstrom`, `degree`, `subunits`, `kelvin`, `pH_unit`, `percentage_point`, `count`, `RSCC`, `RSR`, `z_score`, `angstrom_squared`, `signal_unit` |
| `uncertainty_kind` | `reported_CI`, `reported_SE_or_SD`, `reported_range`, `digitization_bound`, `model_ensemble_range`, `logical_bound`, `unreported`, `exact_count_or_definition` |
| `confidence_level` | number strictly between 0 and 1 only for a reported CI; otherwise null |
| `sample_n` | positive integer or null, with an explicit sample-unit reference |
| `point_scope` | `measured`, `deposited_model`, `conditional_model_calculation`, `derived_measurement`, `synthetic`, `unavailable` |
| `missing_reason` | null or `not_reported`, `not_inspected`, `not_measured`, `censored_without_limit`, `unresolved_mapping`, `unresolved_identity`, `ambiguous_source`, `unsupported_method`, `extraction_failed` |
| `source_refs` | list of host references resolving to exact table/cell/text span/coordinate/validation records |
| `calculation_ref` | null or the exact proposed formula/version and ordered operand references |

Native comparison scores whose units are not in this bounded enum are preserved in `ComparisonMetric {name, native_value, native_unit, method, version, source_ref}`. They do not enter a fraction cell without an explicit defined calculation. `NumberCell` bounds are not silently inferred from displayed decimal digits. Native RSCC is within [−1,1]; q, D, G, T, C, I and N are within [0,1]. Values outside their domains produce a typed field error while valid fields survive.

`TargetMaterial` is `{material_ref, kind, selection, observed_sequence, coordinate_system, completeness, known_context_refs}`, where `kind∈{sequence,selected_record,selected_region,snippets}`, `selection` identifies the exact record and/or 1-based closed ranges, `completeness∈{complete,partial,unknown}`, and `coordinate_system∈{amino_acid,nucleotide,file_native}`. A partial snippet is not silently extended to an entire gene. A public name is neither required nor sufficient to identify material.

`AtomRef` is `{dataset_ref, model_number, label_asym_id, auth_asym_id, label_seq_id, auth_seq_id, insertion_code, comp_id, atom_id, alt_id, symmetry_operation_ref}`. All are exact source values; null sequence fields are permitted for nonpolymer ligands. Alternate locations are selected explicitly; the reader cannot select the best fitting conformer without recording alternatives. `SymmetryOperation` includes its exact fractional-coordinate matrix/translation, cell parameters and units. A biological assembly transformation and a crystallographic symmetry transformation remain distinct types.

`FeatureDefinition` is `{feature_family_ref, elementary_question_ref, weight, required_constraints, required_target_roles, observed_state_ref, expectation_ref}`. It contains no numeric confidence adjective. A constraint is one of:

- `{kind:distance_interval, atom_a, atom_b, lower_A, upper_A}`;
- `{kind:angle_interval, atom_a, vertex_b, atom_c, lower_deg, upper_deg}`;
- `{kind:stoichiometry_interval, component_ref, lower_subunits, upper_subunits}`;
- `{kind:atom_role_count, eligible_roles, compatible_roles}`;
- `{kind:interface_area_interval, surface_definition_ref, lower_A2, upper_A2}`;
- `{kind:entity_identity, observed_entity_ref, required_entity_ref}`.

These define a narrow physical inference, not a decision tree or prompt. Their fixed denominators/weights are retained by the parent-defined scientific question. A required role is `{source_role_ref, required_atom_set, allowed_residue_chemistries, target_positions, geometric_predicates}`. Allowed chemical classes must be explicit source-grounded atom sets, not the word “similar.” Different correspondence routes can populate them.

`ExperimentIdentity` is `{physical_sample_ref, preparation_ref, raw_dataset_refs, construct_ref, state_ref, model_ref, refinement_template_refs, representation_refs, dependence_cluster_ref, identity_basis_refs}`. No identity follows merely from equal numerical values. Shared raw data gives a definite dependence edge; unresolved independence returns an explicit unresolved edge and a conservative grouped scenario. Unknown independence does not authorize a fictitious n.

## Targeted function contracts

| Proposed function | Exact inputs | Exact outputs and invariants |
| --- | --- | --- |
| `resolve_target_material_v1` | Raw supplied material bytes/reference; explicit selected record/ranges; alphabet/coordinate-system hint | `TargetMaterial`, typed selection/translation errors. Never requires a candidate, gene name or public accession. |
| `read_crystal_native_cells_v1` | Retained mmCIF bytes; wwPDB validation XML bytes; `AtomRef[]`; declared required endpoints; crystallization/construct fields to read | `NativeStructureRow` containing `q_atom[]`, occupancy provenance, `rscc_endpoint[]`, `rsr_endpoint[]`, selected native geometry validation, resolution, Rwork/Rfree, cell/symmetry, sequence/construct, and `ExperimentIdentity`; every NumberCell has its original source field. Refined-vs-fixed occupancy is unknown unless established. |
| `extract_literature_structure_cells_v1` | Source bytes and exact inspected coverage; selected table/figure/text anchors; requested fields from this sheet | Same native numerical/condition/identity fields as above, with source spans and reported uncertainty. Returns `observed_entity_relation∈{same_construct,modified_construct,crystal_neighbor,separate_ligand,unresolved}` and `observation_status∈{reported_measurement,reported_model,reported_interpretation,not_reported}`. No reported interpretation becomes a measured field. This function's extraction can need human/model reading, but arithmetic is deterministic. |
| `calculate_geometry_predicates_v1` | Retained atom coordinates, selected alt/model, exact symmetry operator/cell, typed constraint list | Native distances/angles/areas/stoichiometries or named unsupported-field errors; per-constraint bounded satisfaction; `J`, satisfied/failed/unknown counts; `G` with bounds. A surface-area calculation additionally requires algorithm, atomic radii, probe radius and buried-area convention; paper-reported area can be extracted without rerunning it. |
| `calculate_local_fit_v1` | The required endpoint RSCC NumberCells, method selector exactly `xray_local_rscc_squared_001` | `D=min_j max(0,RSCC_j)²`, endpoint minimum provenance, interval propagation. Missing required endpoint returns null point and bounds; missing unrelated residues do not become requirements. Other method selectors return `unsupported_method` with preserved native cells. |
| `map_required_feature_roles_v1` | `TargetMaterial`; actual retained alignment/superposition/entity mapping alternatives; native comparison metrics; explicit required role predicates | For each alternative: K, compatible c, incompatible d, unresolved u, exact mapped positions/atoms, role results, `T=[c/K,(c+u)/K]`; point only when completely resolved. Alternative envelope and comparison native scores retained. No search or annotation run is implied by consuming a mapping. |
| `calculate_comparability_v1` | List of declared nuisance variables excluding intended change; paired measured values/bounds; each explicit τ and its provenance, or construct-position matching counts | Per-variable `c_k`, fixed n, `C` geometric mean and interval. For no cross-condition comparison, returns exact-definition C=1 and a `single_state_conditioned` scope; does not claim environmental similarity. Unknown declared inputs are retained as logical intervals. |
| `calculate_effect_isolation_v1` | Y NumberCell, B NumberCell, same-unit certificate, component/contrast references | `I=max(0,1−B/Y)` with Y=0→0; interval extrema over admitted Y/B bounds, handling Y lower=0 by evaluating limit/endpoints. B absent→unknown I. Atom-assignment-conditioned B=0 must carry `conditional_model_calculation`; a label alone cannot generate B=0. |
| `calculate_nondetection_v1` | Detection-calibration reference; q_U NumberCell; q_req>0 NumberCell; the actual interrogated site/state; required geometric scope | `N=max(0,1−q_U/q_req)`, bounds, censoring code. Absent/omitted density without a limit returns null N; q_U≥q_req returns zero opposing magnitude. Bounds use q_U lower/q_req upper for N upper and q_U upper/q_req lower for N lower. |
| `canonicalize_structure_evidence_v1` | Native rows, ExperimentIdentity records, explicit same-source/model/template dependencies and any reconciliation selection | Canonical observations, representation-to-observation map, copy group, dependence cluster, independent-cluster count, unresolved dependency fields. Conflicting repeated values are not averaged unless the selected physical relationship warrants it. |
| `populate_a111_row_v1` | FeatureDefinition plus q or N, D,G,T,C,I NumberCells, relation sign from the declared predicate | Complete row product w, signed interval, conditional/unconditional status, unresolved operand list. Point is null if any required point is null; zero is not substituted. |
| `reduce_a111_sheet_v1` | Canonical rows; copy/cluster membership; fixed elementary/family weights; optional alternative-hypothesis expectation definitions using the same observations | `A111Result` below. Equal means/sums and the specified positive-part transform only. No global-credit mutation, smoothing, best-account selection or continuation decision. |

For isolation intervals at Y∈[YL,YU], B∈[BL,BU], with YU>0: `IU=max(0,1−BL/YU)`; `IL=0` if YL=0, otherwise `max(0,1−BU/YL)`. YU=0 gives both 0. This explicitly defines the zero-denominator limit instead of leaving a future implementation choice. With an unknown nonnegative B, use [0,1] for I and null point. Comparability kernel bounds use the smallest/largest possible |xA−xB| over the paired intervals; τ must be strictly positive. q_req lower must be >0 for a bounded nondetection calculation; otherwise the relevant lower bound is unknown and the reason is returned.

`A111Result` contains exactly:

```
version: "proposed_a111_result_001"
method_coverage: ["xray_local_rscc_squared_001"]
target_material_ref
feature_definition_refs[]
canonical_observation_refs[]
copy_counts_by_dataset{}
raw_dataset_count
dependence_cluster_count
unresolved_dependence_refs[]
family_results[]:
    family_ref, fixed_weight, positive_mean, opposing_mean, signed_mean,
    signed_bounds, nominal_status, independent_n, sample_SD, descriptive_SE,
    unknown_operand_refs[], conditional_assumption_refs[]
positive_component: NumberCell
opposing_component: NumberCell
signed_contribution: NumberCell
nonnegative_support: NumberCell
optional_display_100x: NumberCell
alternative_contrasts[]: {expectation_a_ref, expectation_b_ref, delta, bounds,
                         unknown_operand_refs[], shared_input_refs[]}
source_to_cell_refs[]
partial_failures[]: {code, field_ref, source_ref, affected_cell_refs[]}
```

`nominal_status∈{fully_measured,conditional_model,synthetic,incomplete}`. It is descriptive provenance, not a score or approval gate. `sample_SD` and `descriptive_SE` are null below two independent clusters. `positive_mean`, `opposing_mean` and `signed_mean` have the same cluster denominator. Conditional and unconditional records cannot be merged without retaining the corresponding assumptions; a conditional point cannot silently populate an unconditional annotation score.

Each source reference, observation identity, role mapping, sign and denominator is validated against its actual retained records. `partial_failures` use the same finite missing-reason vocabulary plus `invalid_range`, `invalid_units`, `conflicting_representations`, `invalid_reference`, and `invalid_denominator`. Valid partial measurements survive errors. A null result is useful information for an episode and does not stop it. No function asks for an extra reviewer or model-composed facts.

## What is implemented in this directory

Only `research_arithmetic_001.py` parses selected deposited atoms/validation attributes, checks the listed coordinate geometry and evaluates the printed synthetic arithmetic. It is a reproducibility aid scoped to the three retained deposits and research examples. It is not wired to episode tools, evidence state, a model prompt, production reader contracts, the existing annotation-credit function, or a current target. All production interfaces above remain unimplemented.
