# Workload033: finite optical conversion into existing A105 rate inputs

Read the full active objective attachment before work. Exactly ten axes remain;
A105 first. A101 and target-transfer/final credit/W05/tool graders are excluded.
Root has reviewed a source case and completed its full32-chunk25-document reset.
This brief supplies a numerical contract, not a paper-specific evidence packet.
Do not read primary papers or retained case reports for this synthetic-only
coding workload. No new scientific interpretation or model transport is needed.

The numerical gap is conversion of a supported NADH absorbance slope into the
existing net endpoint-rate input. It is not a new scoring sheet, reliability
factor, activity normalization or independent contribution. Optical extinction
and path length do not populate dimensionless calibration recovery k. A matched
background is subtracted once; a dependency/control arm is not automatically a
background. Source meaning remains episode-owned. TASK feedback is pending;
this workload does not create, edit, import or wire any prompt.

Own ONLY NEW gene_annotation_episode/literature_optical_calculations.py,
NEW tests/test_literature_optical_calculations.py and NEW
verification/literature_reference_evidence_2026-10-25_001/optical_calculations_033/.
Do not mutate shared production, existing tests, pins, state, sources or libraries.
Inspect applicable complete root architecture/W04 instructions and the existing
activity calculation conventions first. Send an exact short implementation plan
and interface questions before editing; this written contract authorizes the
bounded calculator implementation when no disagreement remains. Fresh ownership
is required by W04. Do not delegate further.

Export calculate_nadh_optical_rate(operands). Exact closed input fields:
version='a105_nadh_optical_rate_operands_v1', sample_slope, blank_slope, epsilon,
path_length, covariance, covariance_status, relation, blank_role, same_endpoint,
matched_window, rate_window, primitive_observation_refs.
The four nullable finite numerical primitives are in fixed canonical units:
absorbance/min, absorbance/min, mM^-1cm^-1, cm. Reject booleans/nonfinite values;
epsilon and path are strictly positive when present. Do not infer a default
path, extinction coefficient, sign, stoichiometric conversion or blank.
primitive_observation_refs is an ordered list of four nullable nonempty strings,
matching those primitives. Unknown identities establish no independence. Known
reused identities must have compatible dimensions and consistent covariance
rows/columns; no label/value equality establishes identity.

Interpretation enums are exactly:
relation=applicable_extinction_relation|not_applicable|unknown|conflicting;
blank_role=matched_no_reaction_background|condition_reference|component_omission|
unknown|conflicting;
same_endpoint and matched_window each=same|different|unknown;
rate_window=source_supported_rate_interval|interval_mean_only|static_only|unknown.
Knownness is supplied interpretation, not proof from matching units or a method
name. Preserve it in the immutable detached input snapshot and conditional facts.

For the applicable matched same-endpoint/window rate interpretation and complete
primitives, q=-1000*(sample_slope-blank_slope)/epsilon/path_length in uM/min.
Retain signed noisy q including negative and zero estimates. Static/interval-mean
values do not become an initial rate through this function. It performs no
kinetic fit, linearity inference, new model call or arbitrary threshold test.

Covariance is null or a finite symmetric positive-semidefinite4x4 matrix in the
exact primitive order and product units. Reject inconsistent shape/symmetry/PSD,
negative diagonal and known reused-identity contradictions. A tiny eigensolver
roundoff tolerance may follow existing conventions without changing/jittering
the matrix. Covariance may accompany unknown primitives as retained information,
but dependent variance requires all rate inputs. covariance_status is exactly
known|estimated|unknown. If matrix absent: variance unavailable with
covariance_unreported. If status unknown: preserve supplied matrix but leave
statistical variance unavailable with covariance_status_unknown. Otherwise
Vq=J*Sigma*J^T with J=(-1000/(epsilon*l),+1000/(epsilon*l),-q/epsilon,-q/l).
Retain signed cross terms and first-order-propagation qualification. Estimated
covariance is not promoted to known variance; neither status creates likelihood,
S/B, probability, annotation credit or an extra observation.

Exact output fields:
version='a105_nadh_optical_rate_cells_v1', endpoint='NADH_depletion',
net_depletion_rate, net_depletion_variance, primitive_observation_refs,input_snapshot.
Each cell exactly value,unit,status,formula,origin,unavailable_reason,conditional_on.
status=populated|unavailable, value null iff unavailable, origin=derived.
Rate unit uM/min; variance unit (uM/min)^2. Reader/typed-unit encoding is later
work; do not weaken existing CODE or communication contracts here.

Explicit missing/relationship reasons include missing_sample_slope,
missing_blank_slope,missing_epsilon,missing_path_length,optical_relation_unknown,
optical_relation_conflicting,optical_relation_not_applicable,blank_role_unresolved,
blank_role_not_background,endpoint_mismatch_or_unknown,window_mismatch_or_unknown,
rate_interval_unestablished,covariance_unreported,covariance_status_unknown,
numerical_model_range. Define deterministic reason precedence and report it.
Invalid input fields raise existing ExperimentalContractError(code,field).
Do not clip impossible propagated variance; return a specific numerical result
failure/reason. Preserve the input snapshot and useful partial facts.

Verify meaningful synthetic contrasts, not tests mirroring code:
- sample=-.012,blank=-.002,epsilon=5,path=1 gives q=2uM/min.
- diagonal covariance=(1e-8,1e-8,.01,.0001), slope cross-covariance5e-9 gives
Vq=.0024 by independently checked arithmetic (all values synthetic).
- missing each operand, static/interval-only/unmatched/unresolved relationships,
condition reference or omission as blank, unknown covariance and estimated status;
- exact zero/negative noisy effects; known reused slope identity and contradictory
covariance; symmetric indefinite matrix even when a requested direction is positive;
- nonfinite/bool/nonpositive denominators, overflow/underflow and detached snapshots.
No broad tests needed beyond this new module and existing activity calculator
regression if relevant. Preserve final hashes, exact command and terminal result.
No source-reader/storage/C7 integration, primary-source populated optical value,
actual model run or completed A105/full-goal claim.

## Interface clarification before coding

The exact active objective path is
/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt.
Read that full file; older GOAL_VERBATIM copies are not substitutes. Snapshot
output follows existing ordinary detached JSON-like dictionary/list conventions,
using deepcopy without input/output aliasing. No MappingProxy/tuple type is
introduced. Durable immutability belongs to future storage; this pure function
returns an independently detached numerical input snapshot.
