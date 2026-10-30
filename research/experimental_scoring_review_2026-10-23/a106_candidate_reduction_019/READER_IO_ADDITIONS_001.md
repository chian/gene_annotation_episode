# Exact additions to unimplemented A106 population readers

This is an additive **UNIMPLEMENTED** contract for the cells in
A106_CANDIDATE_REDUCTION_001.md and WORKED_CANDIDATE_001.md. It extends, without
editing, ../a106_perturbation_sheet_013/reader_io_003.md and its final missing-
provenance clarification. These are proposed field types and deterministic
calculations, not implemented schemas, prompts, graders or a runtime gate.

Every numerical result uses the existing NumberCell/CountCell provenance,
status, units, bounds and value-kind distinction. Domain bounds without a
measurement remain labeled as mathematical domains, not empirical intervals.
Source descriptions remain limited source-linked content. No output asks a
model for an overall relevance, confidence or intuitive score.

## 1. Additional exact input records

### CandidateA106Definition

| Field | Exact type and meaning |
| --- | --- |
| candidate_ref | Persistent local candidate identity, distinct from a revision |
| target_material_ref | Existing Material identity; shared across revisions |
| revision_ref, previous_revision_ref | Current immutable evidence/meaning snapshot and nullable predecessor |
| definition_origin | Enum emerged_from_investigation, supplied_candidate; no discovery prerequisite |
| a106_statement_refs | Nonempty unique list of canonical InferenceScope references, or empty with explicit no_axis_question |
| expression | CandidateExpression defined below; null only if meaning unavailable/no_axis_question |
| canonical_statement_aliases | List of {alias_ref,canonical_ref,basis_ref}; basis identifies actual declared synonym/entailment evidence |
| content_change | Enum initial, evidence_only, source_correction, scope_qualification, asserted_meaning_change |
| prior_scope_ref, current_scope_ref | Typed references; same for evidence_only |
| competing_candidate_refs | Distinct candidates; never automatically inserted into expression |
| formula_ref | This explicit candidate-reduction version |

CandidateExpression is a tagged union:

    {kind: leaf, statement_ref}
    {kind: all_of, children: nonempty list[CandidateExpression]}
    {kind: any_of, children: nonempty list[CandidateExpression]}

The interpretation of each operator is supplied by candidate meaning. A reader
does not choose all_of/any_of from the resulting scores. No free generated
instruction field belongs in this record.

### BiologicalObservationIdentity additions

| Field | Type and meaning |
| --- | --- |
| original_observation_ref | Canonical identity of a physical observation |
| representation_refs | Source locations reporting that observation |
| biological_unit_ref, technical_measurement_ref | Original unit identities, not display-row indexes |
| sampling_design_ref | Defines units eligible to be pooled into the group |
| independence_basis_ref | Existing experimental design record or unknown; equal values neither prove nor disprove independence |
| paired_endpoint_vector | Ordered {endpoint_ref,arm_ref,value_cell_ref} entries for one biological unit |
| covariance_model_ref | Actual covariance or declared model, nullable |
| correction_of_ref | Nullable prior current observation; corrections do not add a unit |

For the worked fixture, each paired_endpoint_vector has six entries and one
common block-error primitive. The known model has covariance 4*J_6, and the
sample-mean covariance is 4*J_6/n. Technical counts remain one per entry.

### A106ContributionGroup additions

| Field | Type and meaning |
| --- | --- |
| group_ref, statement_ref | Existing experiment contribution identity and exact statement |
| sampling_design_ref, primary_endpoint_ref | Declared design and selected endpoint; primary selection is fixed before comparing scores |
| unique_biological_unit_refs | Canonical units used by the actual sampling calculation |
| row_refs | Existing A106NumericRow identities consumed once |
| within_group_estimand | Enum primary_endpoint, declared_endpoint_mean, declared_population_mean |
| endpoint_weights | Empty for primary; otherwise finite {endpoint_ref,weight,denominator_ref} list, all weights>=0 and sum=1 |
| correspondence_relation_refs | Actual M/O relation identities, shared where reused |
| source_effect | NumberCell a before H, by the exact row mode formula |
| H, q_point | Existing corresponding cells; q=H*a or the declared composite sum |
| joint_dependency_refs | Union of actual row/control/transfer dependencies |
| original_group_ref | Group lineage retained across independent replication/corrections |

For a composite, readers output both sums sum(w_j q_j) and sum(w_j H_j). The
factored a is their ratio only when the latter is positive; H=q=0 can be
identified with a unknown. Needed composites cannot invent endpoint weights.

### StatementPoolingInput

| Field | Type and meaning |
| --- | --- |
| statement_ref | One canonical InferenceScope with endpoint, condition, direction and target |
| observed_group_refs | Unique groups actually received; unperformed experiments are not invented rows |
| unavailable_group_refs | Groups already in the roster with actual unavailable operands; remain present |
| H_equality_classes | Exact shared correspondence-variable identities; not similarity clusters |
| shared_primitive_refs | Full linked variable graph including cross-statement sharing |
| source_effect_domain | [-1,1] for restoration or [-1,0] for necessity, unless tighter measured/model bounds exist |
| pooling_rule | Literal correspondence_sum_floor_one_v1, this proposed rule only |
| normalization_floor | Exact NumberCell 1 with kind proposed_score_transform |

### CandidateJointUncertainty

| Field | Type and meaning |
| --- | --- |
| primitive_variables | Unique variable refs, nominal cells, bounds and their scientific meanings |
| joint_model_ref | Actual model/validation record or null with explicit missing reason |
| shared_variable_occurrences | Every expression occurrence mapped to the same primitive identity |
| covariance | Actual named-variable matrix or null; missing covariance never becomes zero |
| continuous_bounds | Declared simultaneous/deterministic interval set with its coverage basis |
| finite_joint_scenarios | Complete finite allowed assignments if that mode is used; otherwise empty |
| method | Enum box_linear_fractional_vertices, joint_finite_enumeration, joint_analytic_monotonicity |
| analytic_derivation_ref | Required for joint_analytic_monotonicity; exact equation and monotonic domain |
| relaxed_constraints | Existing joint constraints relaxed to obtain outer bounds; no silent independence |
| interval_meaning | Enum deterministic_domain, conservative_outer, joint_confidence_region_image |
| coverage_probability | Actual coverage if supported, otherwise null |
| missing_input_refs | Exact missing operands, not a missingness grade |

## 2. Targeted functions and exact outputs

All functions in this table have reader_status=unimplemented.

| Function | Exact inputs | Cells populated and deterministic responsibility |
| --- | --- | --- |
| identify_a106_observations | Original experiment records, dataset row custody, representation/correction links | Canonical observation and biological-unit identities, representation aliases, current supersession mapping; count neither report copies nor superseded values as new units |
| update_a106_group_statistics | Existing sampling design, corrected paired observations, actual weights/model/covariance | Means, n_biological, n_technical, covariance_of_mean, effect/control bounds and union of primitive refs; use current unique observations, not largest historical score |
| factor_a106_row_contribution | Existing row mode, theta,r,C,I or deficit,P_effective,C,I_cancel, plus H | source_effect a, a bounds, q=H*a; exact multiplication and alias to one existing row contribution |
| assemble_a106_group | Row refs, endpoint estimand/weights, original group/control identities | Group H and q sums, factored a when defined, exact endpoint numerator/denominator, preserved shared dependencies |
| populate_a106_statement_pool | StatementPoolingInput and current group cells | T=sum H, d=max(1,T), positive_numerator, negative_numerator, N, Q_point=N/d; no_data for empty roster, no silent dropping of missing groups |
| bound_a106_statement_pool | Group a/H intervals, exact H equality classes, CandidateJointUncertainty | Q_lower,Q_upper by the specified finite box-vertex/hyperplane-edge enumeration; linked shared constraints and outer-bound status |
| populate_candidate_a106_expression | CandidateA106Definition and statement outputs | Leaf mappings, exact min/max evaluation, candidate_point or null, algebraic absorption and identified constants; no combination across competing candidates |
| bound_candidate_a106_expression | Same expression, joint uncertainties, leaf bounds | Candidate lower/upper by explicit monotone min/max box propagation or complete declared joint method; coverage/status inherited, never manufactured |
| reduce_candidate_a106_uncertainty | Candidate point/bounds, missing-input dependencies | Nearest-to-zero signed contribution once; coordinate=max(0,signed), coordinate bounds, null versus identified-zero distinction |
| retain_candidate_a106_revision | Persistent candidate/material refs, immutable old snapshot, current complete inputs/results | Current revision snapshot and links; prior snapshots preserved; no sum or maximum over historical scores |

The last function's responsibility describes proposed research IO, not a request
to implement candidate storage. Existing reader functions continue to populate
all underlying native cells before these mathematical operations.

## 3. Exact statement output

A106StatementReduction contains exactly:

    statement_ref
    formula_ref
    current_group_refs
    group_source_effect_cells
    group_H_cells
    group_q_cells
    unique_biological_counts
    T, d, positive_numerator, negative_numerator, N
    Q_point, Q_lower, Q_upper
    consistency
    bounds_method, joint_uncertainty_ref, primitive_dependency_refs
    missing_input_refs
    result_status
    reader_status

T and d are dimensionless nonnegative NumberCells, d>=1. Q is in [-1,1].
No field here calls d a biological sample size. consistency is null when both
numerators are zero and never enters Q again.

result_status is one of observed_point, measurement_interval_crosses_zero,
missing_inputs, algebraically_identified, no_data, invalid_inputs.
The distinction between a group with known zero q and an unknown point is
preserved even if a numerical interval's lower endpoint happens to be zero.

## 4. Exact candidate output

A106CandidateReduction contains exactly:

    candidate_ref, target_material_ref, revision_ref, previous_revision_ref
    current_scope_ref, content_change
    expression, canonical_statement_refs
    statement_reduction_refs
    candidate_point, candidate_lower, candidate_upper
    signed_A106
    A106_coordinate
    coordinate_lower, coordinate_upper
    coordinate_status
    unresolved_statement_refs, missing_input_refs
    shared_primitive_refs, joint_uncertainty_ref, bounds_method
    coverage_probability, interval_meaning
    formula_ref, reader_status

coordinate_status is one of observed_resolved_support, observed_unresolved_sign,
observed_opposition, identified_zero_with_missing_inputs, missing_inputs,
no_data, no_axis_question, invalid_candidate_meaning, invalid_inputs.

candidate_point and signed_A106 are distinct. The first is the nominal min/max
expression; the second is the nearest-to-zero propagated bound. Missing inputs
leave both null unless their values are identified algebraically. A fully
nonpositive candidate image can identify coordinate=0 with signed_A106 null;
the missing signed value is not guessed. For an observed sign-uncertain
calculation, signed_A106=coordinate=0 but candidate_point and interval remain.

The number consumed by a future accepted W05 contract is A106_coordinate,
conditional on that contract's interval/missing-data treatment. This research
does not choose a global formula or coerce null into a fabricated zero.

## 5. Meaningful relation checks and concrete fixture operands

These are obligations of the future populating functions, not runtime approval
steps:

- All groups in one statement pool refer to the same target, endpoint meaning,
  condition scope, intended contribution and predicted orientation.
- Repeated reports retain the original biological IDs. Actual independent
  repetitions add raw unique units and update covariance; citation count
  cannot alter n.
- q,H,a describe the same group and satisfy the declared multiplication/sums.
  If H enters both numerator and denominator, it is the same variable.
- A shared observation can inform two candidate statements but is not counted
  as two independent biological units. The candidate expression cannot sum
  those statement scores.
- A necessity-challenge result requires its actual quantitative minimum,
  capacity measurement and cancellation bound. A missing measurement stays
  missing.
- An old formula version and result remain immutable historical inputs. A
  correction updates the current snapshot; it does not fabricate an additional
  group.
- A scope qualification is visible as a meaning change. Neither synonym
  canonicalization nor any_of can collapse competing candidates without
  declared semantic grounds.

For the complete printed fixture, exact additional point operands are:

| Cell | Populated operand |
| --- | --- |
| C-plus expression | all_of(leaf A, leaf B) |
| A group roster | G1-X and G2-X |
| B group roster | G1-Y |
| G1 paired biological IDs | b1,b2,b3; later b1 through b6 |
| G1 shared covariance | 4*J_6/n |
| Shared H1 | M=0.54 times O=0.8; bounds [0.378,0.486] |
| G1-X a,q | 0.4725,0.20412 |
| G1-Y a,q | 0.23625,0.10206 |
| G2-X H,a,q | 0.8,-0.15,-0.12 |
| A T,d,N,Q | 1.232,1.232,0.08412,2103/30800 |
| B T,d,N,Q | 0.432,1,0.10206,0.10206 |
| Candidate point | 2103/30800 |
| Bounds method | joint_analytic_monotonicity |
| Three-block candidate interval | [0.04423852311606068,0.09225213507719301] |
| Three-block coordinate | 0.04423852311606068 |
| Six-block coordinate | 0.04581073927568406 |

The actual function implementations, calibrated fitters, persisted runtime
records and prompt rendering remain UNIMPLEMENTED by this assignment.
