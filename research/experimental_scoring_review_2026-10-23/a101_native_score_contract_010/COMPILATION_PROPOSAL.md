# A101 native-score compilation: explicit proposal and filled synthetic example

## Goal and status

The goal is one fully specified route from native BLAST/HMMER quantities to a bounded **contribution within A101**, retaining function alternatives and shared-family dependence. This is the additive extension requested by the parent after the first contract draft: it supersedes the feature vector in Section 7 of `NATIVE_SCORE_CONTRACT.md` for the proposed worked compilation. The earlier proposal and arithmetic remain preserved.

No formula or coefficient is adopted. The numbers below define a **synthetic scoring convention for arithmetic demonstration**, not fitted coefficients, observations, quality categories, or probabilities of correct function. For real data, coefficients must be supplied as an expressly declared convention or established calibration artifact; this work supplies neither an accepted policy nor calibration evidence.

The contribution's scope is one supplied target, one subsequently proposed functional claim F, one declared functional alternative G, and one shared sequence/family evidence group. It is not the whole ten-axis score or a rule for adding every family found in a search. The group can contain overlapping BLAST and profile evidence about the same residues; it produces one contribution, never one per repeated representation.

## Exact operands and formula

For each function F or G, the comparison set must name the actual reference sequences or profiles and the independently grounded molecular endpoint being transferred. Matching an uncharacterized homolog or a broadly annotated family does not invent a function label. The function labels can arise during investigation. This is not an input-candidate requirement.

Within a fixed group and function set, this particular proposal selects the greatest already-recorded, scope-compatible BLAST HSP bit score and HMMER domain bit score. The native database/model versions, search options, target material, reference set and selected regions remain recorded. The calibration or chosen convention includes this selection procedure; it does not claim correction for arbitrary additional searches. A tie retains all tied references and uses the same numeric maximum. If equally scoring references disagree on function grounding, preserve that ambiguity; do not collapse them into one function-labeled row.

| Symbol | Exact operand | Unit / role |
| --- | --- | --- |
| b_F | Selected BLAST HSP bits for F | Bits; native local score, not full-protein function confidence |
| h_F | Selected HMMER domain bits for F | Bits; native domain-envelope score |
| b_G, h_G | The corresponding native quantities for the explicitly named alternative G | Bits; missing alternatives are not zero scores |
| Δb | b_F − b_G | Bits; descriptive BLAST competition under the recorded matching scope |
| Δh | h_F − h_G | Bits; descriptive profile competition, not automatically a likelihood ratio |
| c_q | Query span of the F BLAST HSP / supplied target length | Fraction |
| c_r | Reference span of the F BLAST HSP / actual reference length | Fraction |
| c_m | HMM span of the F HMMER domain / profile match-state count | Fraction; not whole-protein coverage |
| i | Identical alignment columns / all alignment columns for the F BLAST HSP | Fraction, including gap columns in the denominator |
| s | Compatible grounded reference sites / declared site count N | Fraction; a point only if all sites are assessed, otherwise the bounds in the native contract |

No min–max normalization, unreported clipping, rank conversion, raw self-score substitution, or implicit zero imputation is performed. Scale is one native bit for b and h, one bit squared for their product, and one unit fraction for coverage/identity/site components.

The proposed calculation is

    z_F = β0 + βb b_F + βh h_F + βbh b_F h_F
             + βΔb (b_F − b_G) + βΔh (h_F − h_G)
             + βq c_q + βr c_r + βm c_m + βi i + βs s

    C_A101_native(F | G, group) = 1 / (1 + exp(−z_F)).

The contribution is dimensionless and lies between 0 and 1. All β values are required. βb, βh, βΔb and βΔh have inverse-bit units; βbh has inverse-bits-squared units; the remaining coefficients are dimensionless. The logistic transform here is a declared bounded mapping of the index, not a posterior probability.

The two native algorithms are **joint inputs**, not independent evidence probabilities. The interaction coefficient is an explicit place for dependence in the proposed calculation; it does not guarantee that all dependence has been accounted for. Other functions, length effects, profile-family variability, site importance or shared training data may require a richer fitted relationship. No adequacy has been demonstrated here. With coefficients chosen by convention, those are explicit scoring preferences, not statistical facts. With fitted coefficients, the full training/validation requirements in Section 7 of the native contract apply to this expanded vector and both function-grounded comparison sets.

A different function G can change the contribution: the alternative is part of its scope. Scores for F and G are not assumed complementary and do not have to sum to one. A larger set of alternatives needs a declared extension and calibration of the selection procedure. Do not silently choose whichever alternative yields the most favorable result.

## Completely filled synthetic calculation

All source quantities here are synthetic. They are not records from BLAST, HMMER, Pfam, or a characterized protein. The two program-shaped fixtures in `SYNTHETIC_EXAMPLES.md` supply F's numerical inputs. A new synthetic G comparison supplies raw BLAST S_G=195 under λ=0.267 and K=0.041, hence b_G=79.7221495839 bits; its HMMER domain score is stipulated as h_G=64 bits. Their common target and relevant family/region scopes, and their separately characterized F/G endpoint labels, are **stipulated fixture inputs**, not inferred biological facts.

For this complete fixture, all five grounded synthetic sites have an assessable correspondence, three compatible and two incompatible. Thus s=3/5=0.6. This is an explicitly different fixture from the earlier incomplete-site row (four assessed, one unknown); no observation was inferred to fill its missing site.

| Term | Synthetic coefficient | Synthetic operand | Product included in z_F |
| --- | ---: | ---: | ---: |
| Intercept | −3 | 1 | −3 |
| BLAST native score | 0.025 / bit | 81.6481474635 bits | 2.0412036866 |
| HMMER native domain score | 0.020 / bit | 60 bits | 1.2000000000 |
| Joint score product | −0.0002 / bit² | 81.6481474635 × 60 = 4898.8888478109 bit² | −0.9797777696 |
| BLAST function contrast | 0.040 / bit | 81.6481474635 − 79.7221495839 = 1.9259978796 bits | 0.0770399152 |
| HMMER function contrast | 0.050 / bit | 60 − 64 = −4 bits | −0.2000000000 |
| Query span fraction | 0.5 | 236/300 = 0.7866666667 | 0.3933333333 |
| Reference span fraction | 0.5 | 236/260 = 0.9076923077 | 0.4538461538 |
| Profile span fraction | 0.5 | 108/120 = 0.9 | 0.4500000000 |
| All-column identity fraction | 0.5 | 180/240 = 0.75 | 0.3750000000 |
| Site-compatible fraction | 0.5 | 3/5 = 0.6 | 0.3000000000 |

    z_F = sum of the displayed terms = 1.1106453193886485
    C_A101_native = 1 / (1 + exp(−1.1106453193886485))
                  = 0.7522493993457139.

The numerical result is a proposed bounded A101 group contribution **under these invented coefficients only**. It is not a 75.2% probability of F, not an adopted annotation score, and not evidence that functional inference has succeeded. The competing HMMER profile remains visible as a negative contrast even though both native scores are large. No favorable/poor category was mapped to a fixed number.

The negative interaction is an arithmetic choice, not an estimated correction. It also means that the toy polynomial can have unintuitive behavior outside this example. No monotonicity, calibration, biological validity, or extrapolation claim is made for these coefficients; they must not be installed as defaults.

## Missing inputs, uncertainty, and duplicate behavior

| Condition | Defined numerical behavior |
| --- | --- |
| One of the five sites is unknown, with three compatible among four assessed | s lies in [3/5,4/5]=[0.6,0.8]. With the fixed synthetic βs=0.5, z lies in [1.1106453194,1.2106453194] and C lies in [0.7522493993,0.7704131110]. Point value stays null for this incomplete row. |
| β missing and no coefficient bounds supplied | `value=null`, `status=not_identifiable`, reason `policy_or_calibration_absent`; only the vacuous mathematical bound [0,1] is available. |
| A β has a declared finite interval | Propagate its interval through the exact feature expression. Preserve common operands and coefficient dependencies; a rectangular interval can give conservative bounds but is not a statistical confidence interval. |
| A required score, alternative reference, function grounding, or comparison-group relationship is missing | No zero imputation. Retain available component cells; combined value null. Without a finite supported operand bound, [0,1] is all the mapping establishes. |
| Only BLAST or only HMMER is available | This two-tool formula is unavailable. A separately specified/calibrated subset formula can be supplied. The task does not require running the absent tool. |
| Printed-score rounding or certified censoring bounds | Propagate the documented intervals; do not turn rounding error into biological uncertainty or a missing hit into an exact score. |
| Coefficients estimated from a dataset | Use complete coefficient vectors from declared group-level resampling or another justified joint uncertainty representation; do not assume independent coefficients or independent algorithms. Unknown parameter uncertainty stays unknown. |
| Same row delivered again, or the same sequence result represented by a paper and a table | Reuse the same group component. Do not add a second C or form `1−(1−C)^2`. |
| New overlapping HSP or same-clan profile | Retain the result and recompute the declared representative selection if appropriate. It does not create an independent group automatically. |
| Several genuinely different groups | This proposal does not specify their total. Additional aggregation must identify shared residues, families and underlying characterization experiments before claiming additive support. |

The fixed synthetic calculation is executable arithmetic, not a production scorer. `synthetic_joint_alternative_check.py` checks both the complete point fixture and the preserved missing-site bound. Its output is `synthetic_joint_alternative_results.json`. Actual real-case contribution remains null with `policy_or_calibration_absent`.

The remaining work is finite and specific: compare this route against the case-derived A101 components; choose or replace its explicitly listed feature/combination convention; supply actual required coefficients or a suitable calibration dataset; inspect contrasting published function-transfer cases; and implement readers only after the sheet's cells and calculations are settled. Those are not completed by this arithmetic example.
