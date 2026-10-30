# Exact sheet inputs and future reader outputs

These are **UNIMPLEMENTED** interfaces targeted to the numerical sheet in
`A104_POSITIVE_CLADE_PROPOSAL_001.md`. They are neither investigation prompts
nor a general grader format. Literature extraction and dataset parsing can
populate the same cells. The research checker implements only toy arithmetic,
not these readers or their biological/source validation.

## Common cell and scope objects

Every numeric cell is:

```text
NumericCell {
  value: real|null,
  lower: real|null, upper: real|null,
  unit: 'dimensionless'|'substitutions_per_site'|'count'|'bp'|declared_unit,
  value_origin: 'observed'|'derived'|'explicit_judgment'|'scenario_assumption'|
                'synthetic'|'missing'|'invalid',
  point_status: 'identified'|'unidentified'|'invalid',
  identification_bound_kind: 'exact'|'conservative'|'none',
  statistical_uncertainty: {kind, coverage_or_null, method, sample_ref}|null,
  operand_keys: [string], source_locators: [string], shared_measurement_keys: [string]
}
```

Identification bounds do not become a confidence interval. A measured point
without statistical uncertainty does not imply a zero-width confidence
interval. Mathematical zeros remain numerical values; missing values remain
null with their applicable bounds. A factor unused because another is known
zero may remain missing even when its product is exactly zero.

Host provenance keeps the persistent candidate identity, current revision,
input material boundaries, source identities and record custody. It is not
model-facing prompt material. A target can start as sequence, selected record
or snippets with a private label; none of these fields demands a publicly
searchable gene name or an initial functional candidate.

## 1. Source-backed clade and reference inventory

`read_clade_reference_scope` consumes:

```text
region_scope: {target_material_ref, coordinates, coordinate_unit, completeness}
functional_scope: {scope_key, endpoint_meaning, claim_resolution, source_locators}
intended_backbone: [{tip_key, molecular_identity, region_mapping,
                    organism_key, copy_key, identity_status, source_locators}]
query_tip_key
source_clade: {clade_key, source_boundary_locator, intended_member_tip_keys,
               external_boundary_tip_keys, root_definition_ref,
               membership_mapping_constraints, definition_excludes_query: true}
characterizations: [{subject_identity, endpoint_ref, experimental_subject_ref,
                     original_experiment_key, endpoint_scope,
                     relation_to_f: 'supports'|'incompatible'|'nonexclusive_other'|
                                    'unresolved',
                     relation_constraint_refs, functional_scope_key,
                     detection_or_exclusion_limits}]
included_comparisons: [{comparison_key, alternate_endpoint_scope,
                       incompatible_with_f_constraint_refs,
                       reference_tip_keys_or_null,
                       inclusion_status: 'records_received'|'included_records_missing'}]
aliases: [{alias_identity, canonical_identity, identity_evidence_ref}]
```

It returns:

```text
V, C_f, R_f, G:[{comparison_key, R_g_or_unresolved_manifest}]
characterization_inventory: {positive_tip_keys, incompatible_tip_keys,
                           nonexclusive_other_tip_keys, uncharacterized_tip_keys,
                           unmapped_tip_keys}
characterization_counts: {positive, incompatible, nonexclusive_other,
                         uncharacterized, unmapped}
reference_role_scenarios: [{scenario_key, role_assignments, constraint_refs}]
canonical_reference_aliases
clade_scope_status: 'defined'|'missing_boundary'|'missing_identity'|
                   'singleton_no_crown'|'whole_backbone_no_external_boundary'|
                   'unresolved_scope'
opposition_scope: 'received_included_comparisons'
unexamined_alternatives: 'not_assessed'
missing_operands
```

Declared characterization is an evidential relationship, not a numerical grade.
Different function names do not produce `incompatible`. Multifunctionality,
endpoint resolution and actual exclusion/detection limits must constrain that
relation. An assay nondetection does not automatically prove functional
incompatibility. Missing characterization does not assign a tip to R_f or G.
No prevalence/purity number is inferred from uncharacterized members.

Alias collapse is deterministic when supplied identities establish it. An
ambiguous biological identity remains a scenario/unknown, rather than an
arbitrary merge. Multiple actual tree leaves representing the same molecule
cannot be silently deleted while retaining invented branch geometry; that
sample's mapping must supply a valid canonical tree or stay unresolved.

## 2. Native tree and edge-placement input

`read_native_placement_bundle` consumes:

```text
analysis_key, source_data_block_key, homologous_region_scope_key
source_format, method_definition_ref, root_definition_ref, branch_unit
ensemble_kind: 'point_tree'|'bootstrap'|'posterior'|'weighted_placement'|
               'documented_joint_model'
normalization_scope: 'complete_declared_hypothesis_set'|'received_subset_only'|
                     'unknown'
native_total_mass_or_denominator: real|null
samples: [{sample_key, native_weight_or_count, tree_bytes_or_locator,
           original_sample_identity, intended_tip_map,
           placement_rows: [{placement_key, edge_key, distal_length,
                             pendant_length, native_weight,
                             conditional_on_tree_key,
                             source_locator}]|null}]
missing_mass: {value_or_null, lower, upper, normalization_source_ref}
native_split_support: [{exact_split_tip_keys, value, scale, method,
                       denominator_or_null, source_locator}]
documented_joint_sampling: {joint_model_ref, conditional_weight_meanings,
                           joined_sample_keys}|null
```

It returns sample or placement states with `w_z` NumericCells, complete native
normalization denominators, retained missing mass, root/branch units and
source-defined uncertainty interpretation. Exact split support remains separate.
It returns `conditional_subset_result_only` when the source weights cover only
the supplied subset without identified omitted mass. No hidden renormalization
is allowed. Native weight and event-history weight are not multiplied without
a documented conditional/joint model.

Bootstrap samples with identical topology remain distinct if they are distinct
original draws. Export aliases of one draw retain one original weight. An
unknown draw identity does not justify either independent counting or automatic
deduplication of all equal topologies.

## 3. Pruning and crown membership

`calculate_crown_membership` consumes each sample's exact tree or backbone/graft
record, V, C_f, q identity and root/identity/topology constraints. It returns:

```text
query_pruned_backbone
prune_map: [{original_edge_keys, canonical_edge_key, summed_length,
             preserved_root_relation}]
query_attachment: {kind:'edge'|'node'|'virtual_root'|'unresolved',
                   backbone_edge_or_node_key, distal_length_or_bounds,
                   pendant_length_or_bounds}
clade_display: 'displayed'|'resolved_nonmonophyly'|'unresolved'|'missing_scope'
crown_node_key_or_null
J_f: NumericCell  # range [0,1]
placement_class: 'interior'|'stem'|'outside'|'crown_boundary'|'unresolved'
compatible_completion_constraint_refs
```

J=1 or 0 is the result of the declared geometric predicate, not a low/high
category grade. A node exactly at the crown has J in [0,1] until resolved.
When a polytomy lies wholly below a fixed crown boundary, J can still be 1.
Missing intended tips do not shrink V/C_f or convert an unknown to resolved
nonmonophyly. Multiple possible source-boundary maps yield separate compatible
scope scenarios; the function never chooses the most favorable boundary.

## 4. Existing distance, contrast and history readers

The complete interfaces in the original numerical sheet and proposal002 remain
the inputs for `calculate_tree_distances`, `calculate_placement`,
`compare_organism_history` and `calculate_event_explanation_v2`. This addition
requires their sample/placement keys to match the pruned/grafted samples above.

Required numerical outputs per sample are:

```text
positive_distances: {R_f, pairwise_reference_distances,
                    query_reference_distances, s_f, d_qf, O_f}
contrasts: [{comparison_key, fixed_reference_pair_manifest,
             N_fg, n_f, n_g, n_outside, n_unresolved, P_fg,
             alternative_distances:{R_g,s_g,d_qg,O_g}}]
history: {independent_organism_tree_ref, species_copy_map,
          fixed_query_history_triplet_manifest, N_hist,
          n_vertical, n_discordant, n_unresolved,
          triplet_event_assignments, event_operand_keys, H}
events: [{event_key, route_inventory, other_routes_status,
          factual_scenario_key, joint_sample_keys,
          B_by_route, M_by_route, T_by_route, E_by_route, E_event}]
```

P/O/H outputs are NumericCells. All count identities and fixed denominators
retain the meanings in the preceding proposals. All environmental profile,
route-transition, cargo, chronology and unknown-other-routes fields in
proposal002 are retained unchanged; this file does not replace those readers.

## 5. Exact numerical compilation output

`compile_A104_clade_region_v1` consumes the scoped clade/characterization
inventory, all matched sample outputs, native weights/missing mass,
`profile_id='clade_received_contrasts_v1'`, and a shared-dependency constraint
map. It emits:

```text
sample_terms:[{sample_key,w_z,J_f,O_f,H,
               comparison_terms:[{comparison_key,P_fg,O_g,
                                   positive_contrast,opposing_contrast}],
               support_minimum, s_z, o_z}]
crown_association_L
native_placement_mass:{interior,stem,outside,unresolved,missing}
A104_positive, A104_opposing, A104_signed
contrast_only_v2_diagnostic_or_unidentified  # never an additional contribution
opposition_scope, included_comparison_keys, unavailable_included_comparison_keys
unexamined_alternatives:'not_assessed'
identification_bound_status, statistical_distribution_or_null
original_point_tree_result_or_null
sample_weight_interpretation, missing_operands, shared_dependency_keys
```

The mutually exclusive placement-mass classes are derived per placement.
For a fixed unresolved placement, keep its mass in `unresolved`; the separate
L bounds express compatible interior allocations without double counting that
mass in both classes. Report point-tree/ensemble status as actually supplied.
For an unweighted ensemble the inherited quantile rule is the sorted element
at `max(1,ceil(pR))`, one-based. For supplied unequal native weights, use the
left-continuous inverse empirical CDF: smallest score x with cumulative native
weight at or below x >= p. Unknown mass/score intervals yield quantile bounds,
not a fabricated completed distribution.

`compile_A104_candidate_v1` uses proposal002's existing requirement fields and
equations, with these region outputs. The requested compilation profile is
fixed throughout this candidate calculation. A second profile from the same
analysis is not another scenario to pool or another source to add. A required
region available only under another profile remains an identified data/scope
gap for this profile. No silent favorable-profile selection is defined.

The candidate output includes `candidate_S`, `candidate_O`,
`candidate_signed`, `candidate_A104_coordinate`, interval/statistical status,
per-region/per-inference terms, the exact requirement map and profile, source
dependencies and missing operands. It does not select an episode action,
request another experiment, stop an investigation or change a global formula.

Numerical validation identifies inconsistent count sums, units, weight
normalization, graft coordinates, aliases, source scopes and shared-sample
relationships. It preserves valid partial cells and specific invalid/missing
operands. It is not an approval mechanism or a scientific execution gate.
