# Exact cells and targeted population interfaces

This is the IO specification for `A111_NUMERICAL_SHEET_001.md`, not an implementation. Every function in this file remains **unimplemented in production**. The research arithmetic checker consumes retained cross-case results and synthetic operands only. None of these structures is an investigation prompt or a generic judgment-to-score interpreter.

## Common typed cells

`NumberCell` fields are fixed as follows. Every computed fraction has domain [0,1]; signed results have domain [−1,1]. Here “signed results” means individual structural contributions: a candidate difference ΔZ has its own `signed_contrast` unit and domain [−2,2]. Native correlations retain [−1,1]. Units and uncertainty meaning are checked before arithmetic.

| Field | Type and exact meaning |
| --- | --- |
| `point` | Finite number or null. A proposed formula can have an algebraically determined point despite unused unknown operands, which remain listed. |
| `lower`, `upper` | Both finite or both null; lower≤upper. These describe the explicitly named bound scope. |
| `unit` | One of `fraction`, `signed_index`, `signed_contrast`, `display_100x`, `RSCC`, `Q_score`, `RSR`, `angstrom`, `degree`, `angstrom_squared`, `subunits`, `count`, `kelvin`, `pH_unit`, `percentage_point`, `molar`, `millisecond`, `megahertz`, `z_score`, `signal_unit`. `signal_unit` additionally requires its calibration/unit definition reference. |
| `bound_kind` | `reported_CI`, `reported_SD`, `reported_SE`, `reported_range`, `digitization_bound`, `model_scenario_range`, `logical_bound`, `outer_sensitivity_bound`, `exact_definition`, `conditional_arithmetic`, `unreported`. Reported SD/SE remain native descriptors; they are not silently treated as bounded intervals. |
| `confidence_level` | Number in (0,1) only for a reported CI; otherwise null. |
| `reported_sd`, `reported_se` | Nonnegative finite native spread values in the cell's units, or null. These preserve reported SD/SE without placing them into `lower`/`upper` as if they were interval bounds. |
| `sample_n`, `sample_unit_ref` | Positive integer and actual sampling-unit reference, or both null. Distinct from restraint count, model count and copy count. |
| `point_scope` | `measured`, `deposited_parameter`, `derived_from_measurement`, `conditional_model`, `synthetic`, `unavailable`. |
| `unconditional_uncertainty` | `reported`, `unreported`, `not_applicable_definition`. Conditional arithmetic does not erase unreported measurement uncertainty. |
| `missing_reason` | Null or `not_reported`, `not_inspected`, `not_measured`, `censored_without_limit`, `unresolved_mapping`, `unresolved_identity`, `unresolved_assignment`, `unknown_averaging`, `unknown_bound_correction`, `ambiguous_source`, `unsupported_method`, `extraction_failed`, `invalid_denominator`. |
| `source_refs`, `operand_refs`, `dependency_refs` | Lists of exact source/typed-cell/dependency references. Source custody and calculation lineage are retained outside model-facing prompts. |
| `formula_ref`, `conditional_assumption_refs` | Exact formula/version or null, plus the assumptions defining any conditional calculation. |

`SourceRef={document_ref,representation_ref,locator,reported_or_derived,reviewer_ref}`. `locator` is an actual source table/row/column, text span, coordinate selector, XML field or retained result JSON pointer. This worker's pointers to earlier researchers' results do **not** claim a new inspection of their primary sources. `ComparisonMetric={name,native_value,native_unit,method,version,source_ref}` preserves native diagnostics outside the bounded unit enum. No comparison metric silently enters a fraction.

`TargetMaterial={material_ref,kind,selection,observed_sequence,coordinate_system,completeness,known_context_refs}`. `kind` is `sequence|selected_record|selected_region|snippets`; `coordinate_system` is `amino_acid|nucleotide|file_native`; `completeness` is `complete|partial|unknown`. The exact record and 1-based closed ranges define `selection`; no extension of snippets, arbitrary record selection, public name or initial candidate is allowed.

`AtomRef={dataset_ref,model_number,label_asym_id,auth_asym_id,label_seq_id,auth_seq_id,insertion_code,comp_id,atom_id,alt_id,symmetry_operation_ref}` retains exact source values; ligand sequence fields may be null. A symmetry operation includes its coordinate frame, matrix/translation and cell parameters. Biological assembly and crystal symmetry operations have distinct types.

## The numerical sheet's exact input records

| Record | Required fields and relationships |
| --- | --- |
| `Question` | `family_ref, question_ref, alpha, beta, material_ref, state_scope_ref, expected_predicate_refs, opposing_predicate_refs, geometry_panel_ref, target_role_panel_ref, local_panel_ref, condition_panel_ref, expectation_ref`. α and β are nonnegative NumberCells with the stated sum-to-one constraints. Predicates have explicit sets/interval boundaries and units; matching positive/negative sets cannot overlap. Empty expected-opposition sets are allowed only if that limitation is declared, not inferred from unreported measurements. |
| `GeometryPanel` | `panel_ref, fixed_J, members[]`. Each member: `member_ref, kind, measured_cell_refs, positive_set, incompatible_set, endpoint_refs, native_definition_ref`. Kinds: `distance`, `angle`, `subunit_count`, `reported_area`, `chemical_role`, `topology`, `eligible_object_fraction`. Counts/fractions retain numerator and denominator cells; geometric algorithms retain their coordinate system and assignments. |
| `TargetRolePanel` | `panel_ref, fixed_K, roles[]`. Each role: `role_ref, source_role_ref, required_atom_set, allowed_chemistries, route, mapping_alternatives, measured_role_comparison_ref, role_predicate, native_comparison_refs`. `route` is `identity|sequence|structure|measured_interchangeability`. A role can have multiple supporting route refs but counts once. Unknown role interpretations do not become p=.5. |
| `RoleComparison` | For interchangeability: `source_response, replacement_response, ratio_definition, denominator_scope, equivalence_lower, equivalence_upper, intended_role_ref, controlled_replacement_ref, residual_contributor_bound_ref, uncertainty_ref`. Response cells share units; denominator>0. The specified ratio is replacement/source, or a different explicitly written native definition. Equivalence interval must have lower≤upper and stated provenance. An unisolated endpoint leaves the role relation unknown. |
| `ConditionPanel` | `panel_ref, fixed_n, scope, intended_changed_variables[], nuisance_variables[]`. `scope=between_condition_comparison|single_state_conditioned`. Each nuisance entry: `name, units, value_A, value_B, transform, tau, scale_basis_ref`, or `matching_positions, union_positions, excluded_intended_positions`. `transform` is exactly `gaussian_difference|construct_fraction`. For n=0, require `scope=single_state_conditioned`; unknown nuisance panels are not empty panels. |
| `Occupancy` | `native_atom_parameters[], eligible_object_count, feature_object_count, measured_occupancy, occupancy_kind, sampling_design_ref, refined_parameter_status_ref, conditional_state_ref`. `occupancy_kind` is `measured|counted|refined|fixed_model|refinement_status_unknown|conditioned_present_state`. Only the relevant branch's operands are populated. A fixed-model parameter cannot populate unconditional q. |
| `Isolation` | `Y,B,unit_definition_ref,intended_component_ref,alternative_contributor_refs,control_source_refs,conditional_assignment_ref`. B is a measured upper bound or an explicit narrow atom-model condition, not a score adjective. |
| `Nondetection` | `q_upper,q_required_minimum,detection_calibration_ref,interrogated_state_ref,interrogated_region_ref,required_marker_refs,examined_marker_refs`. q_required_minimum>0; actual detected marker endpoints supply D; G_examined has the fixed required denominator. |
| `ExperimentIdentity` | `observation_ref,physical_sample_ref,preparation_ref,raw_dataset_refs,construct_ref,state_ref,model_ref,template_refs,representation_refs,dependence_group_ref,identity_basis_refs,fit_revision_ref,status,supersedes_refs`. `status=current|historical|unresolved_alternative`. Current selection/reconciliation must be explicit; timestamp/score does not silently choose it. |
| `DependencyEdge` | `from_ref,to_ref,relation,basis_refs`. `relation=same_observation_representation|equivalent_copy|shared_raw_data|shared_sample|shared_template|alternative_fit|alternative_assignment|same_experiment_state|technical_repeat|independence_established|independence_unresolved`. Alternative edges affect the joint scenario set. Unresolved independence does not create independent n. |
| `ObservationComposition` | `observation_ref,copy_member_refs[],copy_weights,copy_denominator,scenario_refs[],physical_state_weights,physical_weight_source_ref,paired_contrast_refs`. Copy weights are equal over the declared fixed members unless actual sampling weights exist. State weights are null unless measured, nonnegative and normalized. Alternatives and actual equivalent copies are distinct relationships. |
| `Scenario` | `scenario_ref,admissible_fit_refs,assignment_refs,mapping_refs,state_refs,shared_parameter_refs,excluded_alternative_refs,conditional_assumption_refs`. A single scenario cannot contain mutually exclusive assignments/versions. |

Source organism, genotype, construct, coexisting molecules, intended changes, extra changes, exact endpoints and background contributors are supporting experimental-definition fields referenced from the corresponding typed records. Unreported context is explicitly unknown; no unrestricted source interpretation becomes a numeric operand.

## Three bounded native local-support inputs

`LocalPanel={panel_ref,question_ref,method,fixed_count,granularity,member_refs,construction_basis_refs}`. `method` is exactly `xray_local_rscc_squared_027`, `cryoem_local_q_squared_027`, or `nmr_assigned_distance_kernel_027`. `granularity=atom|residue|experimental_restraint`. Required members missing from input retain their denominator position. Zero members return an unknown D and invalid_denominator.

| Native input record | Exact fields |
| --- | --- |
| `XrayLocalInput` | `experiment_identity,coordinate_ref,validation_ref,map_ref,local_panel,endpoint_rscc_cells[],endpoint_rsr_cells[],atom_occupancy_parameters[],native_geometry_diagnostics[],resolution,Rwork,Rfree,representation_selection_ref`. Each endpoint cell carries its exact atom/residue selector and validation locator. Source values outside [−1,1] are invalid. Unavailable maps are not claimed inspected. |
| `CryoEMLocalInput` | `experiment_identity,map_ref,model_ref,validation_ref,local_panel,q_endpoint_cells[],q_software_name,q_software_version,q_reference_sigma_A,map_kind,mask_ref,sharpening_parameter_ref,half_map_refs[],global_diagnostics[],representation_selection_ref`. Each Q endpoint carries its reported granularity. Software/settings can be null when unreported; reported Q remains a qualified reported operand. `map_kind=primary|half_map|unsharpened|sharpened|unreported`. |
| `NMRRestraint` | `restraint_ref,source_record_ref,experimental_peak_refs[],basis,fit_use,endpoint_a_atoms[],endpoint_b_atoms[],native_atom_names[],atom_name_mapping_ref,native_bound_encoding,target_A,lower_deviation_A,upper_deviation_A,L_A,U_A,averaging,pair_set_refs[],pair_count,n_mono,bound_correction_ref,assignment_scenario_ref,model_scenario_ref,tau_A,reported_validation_violation_A`. `basis=reported_experimental_NOE|verified_experimental_NOE|other_measured_observable|homology_imposed|model_inferred|force_field|unreported`; only the first two fill this D branch. `fit_use=used_for_fitting|held_out|unreported`. `native_bound_encoding=xplor_target_deviations|explicit_interval`; `averaging=single|R-6|SUM|CENTER|unreported`; τ=.50 Å. Native single-proton bounds require no invented pseudoatom correction. |
| `NMRLocalInput` | `experiment_identity,coordinate_ref,restraint_file_ref,validation_ref,local_panel,restraints[],medoid_model_number,model_numbers[],sample_condition_cells[],raw_spectrum_refs[],representation_selection_ref`. Models map to Scenario records; their count never populates q or independent_n. Missing peak intensities do not erase a reported restraint, but its experimental-assignment limitation is retained. |

## Cell-to-function crosswalk

All names ending `_027` below denote future, unimplemented targeted functions. They accept typed numerical selections and return sheet cells plus their exact lineage. Literature extraction may need human/model reading for explicit fields; it must not generate unavailable measurements or a generic relevance grade. Arithmetic is deterministic.

| Function | Exact inputs | Exact outputs / calculation |
| --- | --- | --- |
| `resolve_material_027` | Supplied bytes/reference, selected record/ranges, coordinate/alphabet hint | TargetMaterial, selection errors. No search/name/candidate prerequisite. |
| `extract_structure_fields_027` | Source bytes, actual inspected coverage, exact anchors, requested fields named in this file | Native/experimental-definition fields with source spans, `reported_measurement|reported_parameter|reported_interpretation|not_reported` status. No model call to restate mechanically parsed facts. |
| `read_xray_fields_027` | Coordinate/validation bytes, exact selectors, LocalPanel | XrayLocalInput. Demonstrated selected `ModelledSubgroup/@rscc`, `@rsr`, `@avgoccu` keyed by model/author chain/residue/insertion/alt. avgoccu does not establish free refinement. |
| `read_em_fields_027` | Same map/model/validation identities, selectors, LocalPanel | CryoEMLocalInput. Demonstrated `ModelledSubgroup/@Q_score`; no global-to-local replacement. Map/model mismatch preserves native cells and fails the invalid join. |
| `read_nmr_fields_027` | Native restraint/coordinate/validation records, exact restraint selectors, endpoint/averaging declarations, LocalPanel | NMRLocalInput; [t−l,t+u] conversion; assignments/bounds/fit use retained. Omission from a thresholded validation violation list does not imply zero violation. |
| `calculate_local_fit_027` | One declared LocalPanel and its selected native input/scenario | D, per-member native values/violations/scores, fixed panel count, unresolved member refs. Exact RSCC/Q minimum-square or NOE mean-kernel formula and stated bounds. |
| `calculate_noe_distance_027` | One NMRRestraint, selected coordinates, complete endpoint/pair sets | d in Å by the exact single/R-6/SUM/CENTER convention, source/operand refs and unresolved assignment fields. |
| `calculate_geometry_027` | GeometryPanel, same-model coordinates or actual measured native quantities | J_G, per-member paired predicates, G+/G− and bounds. Also distances/angles/counts/areas and original units. Reported-area consumption is supported; unspecified area recomputation is not. |
| `calculate_correspondence_027` | TargetMaterial, TargetRolePanel, actual alignments/superpositions/replacement comparisons and joint alternatives | c,d,u,K, role p_k values, T point/bounds, native comparison metrics, explicit mapping scenarios. Duplicate routes for one role do not increase K. |
| `calculate_occupancy_027` | Occupancy plus requested scope | q and native deposited parameters separately; counted branch uses actual numerator/denominator. Fixed model q remains unavailable for an unconditional population. |
| `calculate_comparability_027` | ConditionPanel with paired native cells and explicit scales | Each c_k, n, C, bounds. Intended change excluded; irrelevant matching metadata cannot be added to improve the geometric mean. |
| `calculate_isolation_027` | Isolation | I point/bounds under the exact Y/B formula and same-unit check. C is not an input. |
| `calculate_nondetection_027` | Nondetection plus actual marker fit/coverage | N, G_examined, bounds, calibration and inspected-region references. No upper limit gives null N. |
| `populate_directed_row_027` | Question, q or N, D, G+/G− or G_examined, T,C,I, current scenario | DirectedRow: p/o products and bounds, unknown operand refs, conditional assumptions. No user-confidence sign; predicates determine direction. |
| `canonicalize_current_observations_027` | ExperimentIdentity, DependencyEdge, reconciliation/current-version records | Unique representations, current fit identities, copy/scenario/group membership, unresolved relations. Historical versions are excluded from current maxima without deleting history. |
| `compose_observation_027` | Canonical directed rows, ObservationComposition, one admissible Scenario | Fixed-copy or actually weighted p/o **product** means; paired-contrast composition; one canonical observation result. Unknown state weights yield no population point. |
| `reduce_question_027` | Current simultaneous composed observations for one fixed question/scenario and dependency groups | Per-group max p/o, per-question max p/o, Z, bounds, argmax witness identities, empty/unknown coverage. Empty evidence inventory returns zero documented contribution; empty required analysis panels remain unknown. |
| `reduce_a111_027` | Fixed α/β, all question results, joint scenarios, optional candidate expectations | A111Result below by weighted P/O sums, Z=P−O, A=max(0,Z), optional display100×. No global credit, run-state or continuation mutation. |
| `compare_candidates_027` | Same material/scope/weights, candidate results per **shared** scenario and source refs | Paired ΔZ per scenario, envelope and unresolved predicate refs. Shared-input cancellation is retained. |

`DirectedRow={question_ref,observation_ref,scenario_ref,event_branch,q_or_N,D,G_plus,G_minus,G_examined,T,C,I,p,o,unknown_operand_refs,conditional_assumption_refs,source_refs}`; `event_branch=detected|calibrated_nondetection`. Irrelevant branch operands are null and marked inapplicable, not missing required inputs.

`A111Result` contains exactly:

```
version: proposed_a111_027
material_ref
method_selectors[]
scope_refs[], fixed_weight_cells[]
current_observation_refs[], historical_excluded_refs[]
dependency_groups[], unresolved_dependency_refs[]
scenario_results[]:
    scenario_ref, group_results[], question_results[], family_results[],
    positive_component, opposing_component, signed_contribution, nonnegative_support
positive_component, opposing_component, signed_contribution, nonnegative_support
optional_display_100x
point_scope, nominal_scenario_ref, unconditional_uncertainty
signed_envelope, support_envelope, envelope_kind
direction: positive|negative|zero|unresolved
coverage_by_question: unexamined|known_zero|populated|partial|invalid_analysis
raw_dataset_count, equivalent_copy_counts, model_scenario_counts
independent_n_by_compatible_repeat_set, sample_SD_by_set, descriptive_SE_by_set
max_witness_refs[], source_to_cell_refs[], reused_source_refs[]
unknown_operand_refs[], conditional_assumption_refs[]
candidate_contrasts[]
partial_failures[]
```

All named numerical outputs use NumberCell. `envelope_kind=joint_scenario_range|outer_sensitivity_bound|logical_bound|unreported`. A source-local conditional point never silently fills an unconditional target result. Metadata for repeated sources across evidence axes enables later credit handling; this sheet does not invent that global combination.

`CandidateContrast={candidate_a_ref,candidate_b_ref,shared_scope_ref,shared_scenario_refs,delta,delta_envelope,envelope_kind,shared_input_refs,unknown_predicate_refs,conditional_assumption_refs}`. `delta` and `delta_envelope` are NumberCells with `unit=signed_contrast`; their domain is [−2,2]. Their source/operand references point to the two jointly evaluated candidate results. For example, candidate indices +1 and −1 have ΔZ=2, not an invalid structural score. This explicit contrast record and the separate native SD/SE fields clarify the field meanings before handoff; they change no evidence or score.

`partial_failures={code,field_ref,source_ref,affected_cell_refs}` uses the NumberCell missing reasons plus `invalid_range`, `invalid_units`, `invalid_reference`, `invalid_weights`, `conflicting_current_representations`, `map_model_mismatch`, `nonexperimental_restraint`, `ambiguous_atom_names`, `unresolved_physical_weights`, `incompatible_scenario`. Preserve valid partial cells. These are numerical/data validation outcomes, not workflow stopping gates or approval steps.
