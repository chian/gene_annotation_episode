# Exact additions to the UNIMPLEMENTED A111 reader IO

These are targeted future interfaces for the numerical cells already defined in `PROPOSED_NATIVE_MODALITY_ADDENDUM_001.md`. Every production function below remains **UNIMPLEMENTED**. The bounded research arithmetic script is not a general reader and is not connected to evidence state, prompts or credit. Existing target-material, geometry, mapping, comparability, isolation, nondetection and reducer contracts remain in `a111_structural_evidence_sheet_017/READER_IO_001.md`.

## Additive typed cells

Keep `NumberCell` unchanged except that its native-unit enum gains `Q_score`, `millisecond`, `megahertz`, and `molar`. Q_score has domain [−1,1]; D remains `fraction` [0,1]. NOE bounds, distance, violation and τ use existing `angstrom`. Native restraint bounds are physical permitted intervals, not reported confidence limits. The original `uncertainty_kind`, `point_scope`, source references and finite missing-reason vocabulary remain mandatory.

`LocalObservationMethod` gains exactly `cryoem_local_q_squared_001` and `nmr_local_noe_restraint_kernel_001` alongside `xray_local_rscc_squared_001`. This is declared specification coverage, not deployed coverage. No general `cryoem`, `nmr` or `crosslinking` catch-all selector is accepted.

`RequiredLocalPanel` is `{panel_ref, feature_definition_ref, required_endpoint_refs[], required_restraint_refs[], fixed_count, granularity, construction_basis_refs[]}`. `granularity∈{atom,residue,experimental_restraint}`. `fixed_count` must equal the number of distinct declared members; a repeated representation of a member does not increase it. A zero count returns `invalid_denominator` and an unknown D; it does not validate the feature. Required members missing from input retain their place in the panel.

`CryoEMLocalRow` contains exactly:

| Field | Type and meaning |
| --- | --- |
| `experiment_identity` | Existing ExperimentIdentity, including raw map and refinement-template dependencies |
| `map_ref`, `model_ref`, `validation_ref` | Exact retained source references, not display names alone |
| `local_panel` | RequiredLocalPanel with atom or residue granularity |
| `q_endpoint_cells[]` | `{endpoint_ref, atom_refs[], residue_ref, native_Q:NumberCell, source_granularity, source_attribute_ref}`; exactly one selected native value per panel member |
| `q_software_name`, `q_software_version` | Exact source-reported identifiers or null; do not infer them from acquisition date |
| `q_reference_sigma_A` | NumberCell or null, only when reported for the retained computation; a README default is not proof it was used |
| `map_processing` | `{map_kind, mask_ref, sharpening_parameter_ref, half_map_refs[]}`, with `map_kind∈{primary,half_map,unsharpened,sharpened,unreported}` and null unresolved references |
| `global_diagnostics[]` | Existing ComparisonMetric records for resolution/FSC/global Q/percentiles; not substituted into D |
| `representation_selection_ref` | Explicit reconciliation choosing this coordinate/validation pair; unresolved disagreement preserves alternatives |

Known native Q plus unreported processing settings produces a reported-Q index with the qualification retained; it does not fabricate settings or automatically erase the source measurement. A map/model identity conflict prevents the invalid join and returns the valid independent native cells with a typed failure.

`NMRDistanceRestraint` contains exactly:

| Field | Type and meaning |
| --- | --- |
| `restraint_ref`, `source_record_ref`, `experimental_peak_refs[]` | Resolvable native identities; peak refs may be empty when not deposited, without inventing intensities |
| `basis` | `reported_experimental_NOE`, `verified_experimental_NOE`, `other_measured_observable`, `homology_imposed`, `model_inferred`, `force_field`, or `unreported`; these are provenance categories, not score grades |
| `fit_use` | `used_in_structure_calculation`, `held_out`, `unreported` |
| `endpoint_a_atoms[]`, `endpoint_b_atoms[]` | Existing exact AtomRefs; grouped selections are complete, not only their best-fitting members |
| `native_atom_names[]`, `atom_name_mapping_ref` | Retained source names and explicit alias/stereoassignment mapping, nullable if unresolved |
| `native_bound_encoding` | `xplor_target_deviations` or `explicit_interval` |
| `target_distance_A`, `lower_deviation_A`, `upper_deviation_A` | NumberCells only for Xplor encoding; null otherwise |
| `lower_bound_A`, `upper_bound_A` | Derived/native NumberCells for `[t−l,t+u]` or the explicit interval, obeying 0≤L≤U |
| `averaging` | `single`, `R-6`, `SUM`, `CENTER`, or `unreported` |
| `pair_set_refs[]`, `pair_count`, `n_mono` | Exact pair set; positive pair count; n_mono strictly positive only for SUM, otherwise null |
| `bound_correction_ref` | Source's applied pseudoatom correction record or explicit no-correction record; null when unresolved |
| `assignment_scenario_ref`, `model_scenario_ref` | Coupled scenario references; retain unresolved alternatives |
| `tau_A` | Exact-definition NumberCell .50 Å for this proposed selector |
| `validation_violation_A` | Native reported NumberCell or null, plus source field; omission from a thresholded list is not zero |

Only `reported_experimental_NOE` and `verified_experimental_NOE` are operands in this defined method. A required member with another basis remains unresolved for this method and produces a specific failure. It is not silently discarded from J. A reported NOE restraint can populate conditional fit even when the original intensity is unavailable; the reader must retain that assignment and measurement limitation.

`NMRLocalRow` is `{experiment_identity, model_ref, restraint_file_ref, validation_ref, local_panel, restraints[], medoid_model_number, model_numbers[], physical_model_weights, weight_source_ref, sample_condition_cells[], raw_spectrum_refs[], representation_selection_ref}`. `physical_model_weights` is null unless actually measured with a stated experimental normalization. The mere presence of twenty deposited models never fills it. Report sample concentration, pH, temperature, field and mixing time only as actually known; their comparison enters C only when the scientific question declares them relevant nuisance variables.

`LocalSupportResult` is `{method_selector, D:NumberCell, required_panel_ref, per_member_cells[], model_scenario_ref, unresolved_member_refs[], native_operand_refs[], formula_ref, qualification_codes[], partial_failures[]}`. Qualification codes are restricted to `residue_granularity`, `processing_unreported`, `assignment_conditional`, `used_for_fitting`, `ensemble_not_population`, `reported_bound_not_CI`, `shared_template`, `unresolved_identity`, `native_method_uncovered`. They communicate interpretation limits without assigning extra numerical penalties.

## Exact population functions

| UNIMPLEMENTED function | Inputs | Outputs / deterministic calculation |
| --- | --- | --- |
| `read_cryoem_local_cells_v1` | Retained coordinate and validation bytes; exact map/model refs; RequiredLocalPanel; field selections | CryoEMLocalRow. Read `ModelledSubgroup/@Q_score` keyed by model/author chain/author residue/insertion/alt for demonstrated residue rows; retain label/author correspondence. Atom-level input requires its actual reported atom field. Missing endpoint gives null, never global Q. |
| `read_nmr_distance_cells_v1` | Retained MR/restraint bytes, coordinates, validation bytes; exact selected native records; atom-name/averaging/basis declarations supported by sources; RequiredLocalPanel | NMRLocalRow with bounds converted exactly, medoid and all admitted models retained. Native XML `violated_distance_restraint` values remain reported rounded fields; full bounds/coordinates supply exact zeros where calculable. A missing listed violation alone never supplies zero. |
| `calculate_nmr_effective_distance_v1` | One NMRDistanceRestraint, its selected model coordinates, exact endpoint/pair sets, known bound correction and averaging | d NumberCell using the exact single/R-6/SUM/CENTER equations in the sheet, complete operand refs, typed unresolved assignments. No best-conformer or nearest-proton fallback. |
| `calculate_local_fit_v2` | RequiredLocalPanel, LocalObservationMethod, selected native Q cells **or** exact experimental restraint distances/bounds/τ, coupled model/assignment scenario | LocalSupportResult. Q branch min(max(0,Q)²); NOE branch v=max(0,L−d,d−U), s=exp(−v²/(2τ²)), D=Σs/J. Uses explicit interval formulas and fixed missing-member denominator. X-ray delegates the unchanged specified RSCC arithmetic. |
| `collect_nmr_scenarios_v1` | Complete admitted model/assignment alternatives; the existing per-scenario q,D,G,T,C,I results and h; any actually measured physical weights | One observation with complete-product scenarios, min/max envelope and null unweighted population point. A separately labeled named-model point can be returned. Preserve shared atoms/bounds jointly; never feed the scenario list as independent cluster rows. |
| `extract_literature_structure_cells_v2` | Source bytes and inspected coverage; selected anchors; requested new native fields above | Source-grounded CryoEMLocalRow/NMRLocalRow fields with reported-versus-derived provenance. No adjective-to-number inference and no extra call to restate parsed facts. Arithmetic delegates deterministic population functions. |

The old `calculate_geometry_predicates_v1` computes G for the same selected model/assignment; `map_required_feature_roles_v1` still consumes actual supplied target material/mapping. `calculate_comparability_v1` and `calculate_effect_isolation_v1` retain separate operands. `populate_a111_row_v1` receives the new D NumberCell with all its scope/uncertainty, and uses the unchanged product. Its point remains null if any required point is null. No new scientific acceptance test is introduced.

`canonicalize_structure_evidence_v1` receives two new explicit relation values: `alternative_model_same_dataset` and `technical_spectrum_same_preparation`, alongside existing same-source/copy/template relationships. The former is an uncertainty-scenario relation, not a copy-average group. Both prevent fictitious independent n. The scalar reducer itself is unchanged.

`A111Result.method_coverage` may list the two new selectors only when the corresponding defined operand path is actually used. Add `local_support_results[]` and `scenario_results[]` references to the host result; the existing `source_to_cell_refs[]`, `unknown_operand_refs[]`, `conditional_assumption_refs[]` and partial failures remain authoritative. Conditional points never silently fill an unconditional record. These result fields are host records, not a prompt-context dump.

Add error codes `ambiguous_atom_names`, `unknown_averaging`, `unknown_bound_correction`, `nonexperimental_restraint`, `map_model_mismatch`, and `unresolved_physical_weights`. They identify missing inputs/invalid joins and preserve all valid partial native cells. All original missing-reason codes remain. Unsupported NMR observables or uncalibrated cross-linking statistics retain native ComparisonMetric records but cannot return a falsely completed D scalar under these selectors.
