# Recorded F-calc numerical examples

This records results from `example_run_004`, not a replacement formula contract.
Each linked JSON contains the complete actual-populator-produced sheet, explicit
model and complete components. All inputs are synthetic retained-format fixtures;
live database execution and episode return verification are explicitly false.
The manifest records hashes, sizes and compact projections without truncating
the saved examples. `run_012` supplies the independent asserted numerical checks.

`P` is conditional_function_weight and `C` is
representation_adjusted_function_weight. Fractions below are mathematical test
oracles; the full JSON retains the actual binary64 values and log2 values. Null
linear values retain their distinct reason/status and are never presented as 0.

| Complete example | Verified numerical meaning |
|---|---|
| [whole_t1](example_run_004/examples/whole_t1.json) | Scores 20/18, T=1: masses1 and1/4; P=(4/5,1/5). Three source entities, four eligible original HSPs and two target units. Full census has six member instances, five target units and function counts(4,1); rates=(1/8,1/8), C=(1/2,1/2). |
| [whole_t2](example_run_004/examples/whole_t2.json) | The identical saved sheet at T=2: masses1 and1/2, P=(2/3,1/3), C=(1/3,2/3). |
| [translated_features](example_run_004/examples/translated_features.json) | Opposite source strands with identical oriented feature nt/coding identity form one target unit while retaining both original maps; the other target stays distinct. P=(2/3,1/3). No census correction is selected. |
| [translated_siblings](example_run_004/examples/translated_siblings.json) | Valid own-function HSPs retain their score maxima. Excluded wrong-frame40-bit and broad50-bit siblings cannot lend scores. P remains(2/3,1/3), explicitly partial. |
| [assignment_conflict_missing_feature](example_run_004/examples/assignment_conflict_missing_feature.json) | A conflicting copy of an assignment key points to a missing feature. Its 30-bit original observation is retained incompatible; independent 29-bit A and 28-bit B observations yield P=(2/3,1/3) at T=1, partial. |
| [assignment_conflict_other_bound_feature](example_run_004/examples/assignment_conflict_other_bound_feature.json) | The conflicting copy points to another bound feature. Both conflicting observations stay excluded; independent A/B rows still yield P=(2/3,1/3). An unannotated duplicate adds no unknown target mass. |
| [source_cap_baseline](example_run_004/examples/source_cap_baseline.json) | Three distinct equal-score targets give P=(2/3,1/3); shared sample relations are retained but unused. |
| [source_cap_selected](example_run_004/examples/source_cap_selected.json) | Same targets, explicit source cap: A/B share one block and another A target remains separate; P=(3/4,1/4). Literal source/target counts are unchanged. |
| [full_census_bridge](example_run_004/examples/full_census_bridge.json) | Returned-only P=(1/3,1/3,1/3). The complete census links A/B through an unreturned entity: recomputed observed masses=(1/2,1/2,1), N=3 blocks, N_f=(2,1,1), rates=(1/12,1/6,1/3), C=(1/7,2/7,4/7). The bridge receives no HSP. |
| [own_function_score_split](example_run_004/examples/own_function_score_split.json) | The same group has own-function maxima20 and18: Z=1+1/4, split contributions=(4/5,1/5). The weaker function never receives the stronger function's HSP score. |
| [unknown_target_mass](example_run_004/examples/unknown_target_mass.json) | Two assigned equal-score targets and a distinct unassigned target: P=(1/2,1/2), unknown_reference_kernel_fraction=1/3. Missing annotation qualifies the result as partial. |
| [explicit_zero_prior](example_run_004/examples/explicit_zero_prior.json) | B's explicit prior0 yields P_B=C_B=0 while positive native B mass remains. Mathematical zero has null log2 and zero status. |
| [positive_prior_underflow](example_run_004/examples/positive_prior_underflow.json) | Positive finite raw priors with extreme scale retain a finite normalized log prior and null underflowed linear prior/weight; they do not become zero-prior evidence. |
| [log2_minus_2000](example_run_004/examples/log2_minus_2000.json) | Native score0 remains eligible against score2000 at T=1. B mass and weight retain log2=-2000 with null linear value and underflow status. |
| [finite_arithmetic_failure_valid_other_scope](example_run_004/examples/finite_arithmetic_failure_valid_other_scope.json) | A whole-member stratum's finite scores and tiny positive T produce an unrepresentable derived log. Its statistical fields are unavailable with the exact arithmetic code; native scores and census counts (4,1), N=5 survive. A separate feature stratum still has weight1. |
| [incompatible_census](example_run_004/examples/incompatible_census.json) | Wrong census snapshot leaves P=(4/5,1/5); all C fields are incompatible/null. Supplied census counts remain descriptive. |
| [census_unknown_dependency_separate](example_run_004/examples/census_unknown_dependency_separate.json) | Fully enumerated census with incomplete sample relations, source-cap model and qualify_separate: P=(4/5,1/5), conditional C=(2/3,1/3), partial with dependency_unknown/unknown_dependency_separate. |
| [census_unknown_dependency_withheld](example_run_004/examples/census_unknown_dependency_withheld.json) | Same sheet with withhold_weights: P=(4/5,1/5) survives, C is unavailable with dependency_unknown. |
| [qualified_zero_hits_nonzero_census](example_run_004/examples/qualified_zero_hits_nonzero_census.json) | Strict successful no-hit source: no candidates/groups, every observed stratum count0, no normalized weights. Independently supplied complete census facts survive. |
| [empty_table6_unavailable](example_run_004/examples/empty_table6_unavailable.json) | Empty non-authoritative table6 does not prove no hits: overall unavailable. |

Additional final tests, beyond these twenty saved examples, verify equal-score
multilabel splits, overlapping census fractions whose sum exceeds1, duplicate and
lower-HSP invariance, all winning ties, an unannotated duplicate without extra
unknown mass, scope-separated parent edges, explicit dependencies, namespace
separation, missing observed census functions, wrong units/filter/scope/snapshot,
partial/null pagination, count conflict, real zero census, missing parent proof,
unknown origins and proven-but-unscored targets. They also verify PSSM-master
meaning, named native reporting limits, no-candidate and sample-only cases,
zero/negative/nonfinite/boolean model rejection, candidate-prior consistency,
closed output shapes, original sheet/model immutability, and saved recalculation
through the actual validator with parsing/population/I/O disabled.

The full files remain the evidence for exact source/HSP/group associations and
binary64 output. The final source pins and actual bounded-job receipts are in
the manifest, HANDOFF_001 and ARTIFACT_HASHES_001. Earlier example_run_001 is
retained as a superseded development artifact, as explained in HANDOFF_001.
