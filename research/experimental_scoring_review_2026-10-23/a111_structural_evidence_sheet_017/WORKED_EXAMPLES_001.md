# Print-ready A111 numerical examples

PROPOSED arithmetic, not an accepted axis or a target annotation. Source rows are measured/deposited facts plus explicitly identified calculations. The end-to-end illustration is entirely synthetic. `PROPOSED_A111_SHEET_001.md` defines all fields and the reducer; this file is suitable for printing its concrete results for user judgment.

## Contrasting inspected source rows

| Physical question and source | Native numerical inputs | Proposed calculated cells | What the number does not establish |
| --- | --- | --- | --- |
| ATP-shaped modeled occupancy in MJ0577; DOI 10.1073/pnas.95.26.15189, 1MJH | ATP A2001 RSCC .963, RSR .065, qmodel 1; B3001 RSCC .958, RSR .071, qmodel 1 | D_A=.927369, D_B=.917764; equivalent-copy mean D=.9225665 | Two sites in one diffraction dataset are not two experiments. Fixed/model occupancy is not population occupancy, affinity, ATPase activity or physiological ligand identity. |
| Mn coordination in the same 1MJH model | Six oxygen distances 2.255419–2.382306 Å in A; 2.276454–2.380708 Å in B; mean distances 2.326082 and 2.345861 Å | Under the explicit 2.0–2.6 Å oxygen-distance question, Gdistance=6/6=1 in each. Under the example nearest-90°/180° ±15° angular question, Gangle=15/15=1 in each. | These are geometric predicates in a Mn-containing crystal. Mn was supplied during crystallization. They do not establish a native intracellular metal, catalytic rate or quantitative metal affinity. |
| Crystal interface in 1MJH | Reported buried area 1,056 Å² per monomer; reported fraction 15% | Native buried fraction .15; for the explicitly limited question “at least 1,000 Å² buried per monomer in this crystal,” G=1 | Area is a native architectural quantity, not biological-assembly confidence. Independent solution stoichiometry was not populated. The 1,000 Å² boundary defines this illustration, not a universal biological-assembly threshold. |
| Phosphate-bearing groups in YwlE states; DOI 10.1016/j.celrep.2013.05.023 | 4KK3 PO4 RSCC .967, RSR .079; 4KK4 SEP7 RSCC .934, RSR .097; both qmodel 1 | D_PO4=.935089; D_SEP=.872356 | The C7S mutant has modeled phosphoserine. This does not directly observe a phosphocysteine intermediate in wild type or an intact phosphoarginine substrate. |
| Crystal-neighbor Arg149–Asp118 contact in those states | Distance NH2–OD2 2.458451 / 2.916031 Å; Arg149 RSCC .773 / .907; Asp118 RSCC .944 / .934 | At an explicitly defined ≤3.2 Å contact criterion, G=1/1; Dcontact=.597529 / .822649 | Contact source is a neighboring protein's Arg149, not a freely added arginine substrate. The poorer fitted contact endpoint matters despite the strong phosphate fit. |
| Between-state comparison in YwlE | ΔpH=1.5; ΔPEG=5 percentage points; four MSE/MET differences plus terminal insertion outside intentional C7S; matching temperatures | Illustrative two-condition C=.535261429; four-component C=.725482518. Native effect-isolation bound B absent, so I=null | A quantitative comparability index cannot isolate the effect of C7S. Unknown I cannot be silently replaced by C or a qualitative reliability category. |

All proposed predicate thresholds above are explicit illustrative definitions, not empirically calibrated universal criteria. Native Rfree, ligand geometry Z scores and the 4KK4 current-coordinate NH2–P–OG angle are retained in the source packet as qualifications. The deposited P–OG distance is 1.681567 Å, matching the validation report's rounded 1.68 Å. No current target correspondence was computed. T remains null for both papers. A source-local index such as .9225665 therefore does **not** become a target score. Conditional on the model and narrowly defined feature, the target envelope is [0,.9225665]; measured occupancy and mapping uncertainty can widen the unconditional interpretation.

The source has ATP-shaped occupancy under both an ATP-binding interpretation and an ATP-hydrolyzing interpretation. That shared observed feature has the same value under each interpretation, so its contrast ΔZ is 0. A molecular activity assay may distinguish them in A105; it is not manufactured from the structural row. The same distinction applies to a soaked analogue, a mutant covalent adduct and a crystal packing contact.

## Entirely synthetic complete joined sheet

**No numbers in this section are measurements of 1MJH, YwlE or the project's target.** This synthetic material exercises every required operand of the proposed reducer. It assumes a supplied anonymous sequence, later mapped to two structural feature families H1 and H2. H1 describes a ligand site with six required geometric constraints and four target roles. H2 describes a separately declared crystal-interface feature with one geometry constraint and two target roles. Each family receives weight 1/2. It is not a claim of solution oligomerization.

Three independent diffraction/experimental clusters address H1. Cluster A has three representations (paper, coordinates and validation), which yield one observation. Cluster B is an independent preparation and dataset. Cluster C is a calibrated nondetection under the H1 hypothesis's required conditions. Cluster D addresses H2. Their data/model dependencies are stipulated independent in this synthetic example; a real reader must establish that fact.

| Cluster | q, or N for nondetection | RSCC → D | G | T | C | I | Signed product |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A, H1 detected | .80 | .95²=.9025 | 5/6 | 3/4 | .90 | .90 | +.3655125 |
| B, H1 detected | .75 | .90²=.81 | 6/6 | 2/4 | .95 | 1 | +.2885625 |
| C, H1 calibrated nondetection | N=1−.10/.50=.80 | .90²=.81 | 1 | 3/4 | 1 | 1 | −.4860000 |
| D, H2 detected | .60 | .80²=.64 | 1/1 | 1/2 | 1 | 1 | +.1920000 |

Every operand has a specified origin in the synthetic construction:

- q values are synthetic fitted occupancy estimates with explicit bounds below. G numerators count the measured constraints satisfied; G denominators and T role counts stay fixed. T zeros correspond to known incompatible/missing target features, not unread snippets. Four H1 roles remain the denominator even when only two preserve the feature.
- C_A=.90 arises from one declared nuisance variable with τ=1 pH unit and a measured pH difference `sqrt(−2 ln .90)=.459043605` units. C_B=.95 analogously uses `.320291412` units. The pH scale is an explicit proposed numerical tolerance, not a natural constant. All other relevant variables are stipulated fixed; they are not inserted as matching terms to inflate C. C_C=C_D=1 follows documented identical conditions for their specific comparison.
- I_A=.90 uses an absolute measured structural-effect signal Y=10 arbitrary, consistently calibrated signal units and a measured nuisance contribution upper bound B=1 in the same units. This is an invented control measurement distinct from the pH comparison. For B/C/D the assigned within-state/count contrast has a synthetic B=0. No unmeasured B is set to zero.
- C's detection calibration supplies an occupancy upper limit q_U=.10 in the interrogated site. H1 entails q_req≥.50 under these same conditions. Hence N=.80. If the only source said “no ligand modeled,” N would be null and this negative product would not be justified.

H1 supporting and opposing means use the same three-cluster denominator:

\[
P_1=(.3655125+.2885625+0)/3=.218025,
\]
\[
O_1=(0+0+.486)/3=.162,
\qquad Z_1=.056025.
\]

For H2, `P2=.192`, `O2=0`, and `Z2=.192`. Therefore:

\[
P_{111}=(.218025+.192)/2=.2050125,\quad
O_{111}=.162/2=.081,
\]
\[
Z_{111}=.1240125,\qquad A_{111}=\max(0,.1240125)=.1240125.
\]

The optional display number is **12.40125 on a 0–100 structural-support scale**, conditional on the declared questions and proposed transforms. It is not 12.4% probability that an annotation is correct. Copying the paper/coordinate representation of A any number of times leaves this result unchanged. Removing the calibrated contradictory result would change the evidence and denominator; it is not a formatting operation.

## Complete uncertainty arithmetic for the synthetic example

These are stipulated bounded sensitivity intervals, not confidence intervals. Shared variables must be varied jointly; in this synthetic illustration the stated extrema are admissible together. C and I bounds are explicit bounded measurements/assumptions; their exact underlying bounds can be recovered as `|ΔpH|=sqrt(−2 ln C)` and `B/Y=1−I` for these definitions.

| Cluster | q or q_U bounds | RSCC bounds | G bounds | T bounds | C bounds | I bounds | Signed product bounds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | [.70,.90] | [.93,.97] | [4/6,6/6] | [2/4,4/4] | [.85,.95] | [.85,.95] | [.145807725,.764246025] |
| B | [.70,.80] | [.88,.92] | [1,1] | [.5,.5] | [.90,1] | [.95,1] | [.2317392,.33856] |
| C | q_U∈[.05,.15], q_req=.50 | [.88,.92] | [1,1] | [.75,.75] | [1,1] | [1,1] | [−.57132,−.40656] |
| D | [.50,.70] | [.78,.82] | [1,1] | [.5,.5] | [1,1] | [1,1] | [.1521,.23534] |

`Z1∈[−.064591025,.2320820083]`; `Z2∈[.1521,.23534]`. The equal-family reduction gives:

\[
Z_{111}, A_{111}\in[.0437544875,.2337110042].
\]

H1 alone has a nonnegative-support lower bound of 0 because its signed lower bound is negative. The separate H2 contribution keeps the joined lower bound positive in this constructed example. If a required target role is unread rather than known incompatible, the point T becomes null and its interval retains the fixed denominator. For example c=2, d=1, u=1 among K=4 gives T∈[.5,.75], not 2/3 and not a default .5 point score.

H1's signed independent cluster values have sample SD .470981583 and descriptive SE .271921343 at n=3. This spread makes the contradiction visible. Neither is multiplied into the contribution again, and neither is a calibrated probability of error. The symmetry-related/source-copy count cannot enlarge n.

## Remaining choices for user judgment

The full proposal deliberately exposes RSCC², multiplicative combination, fixed feature denominators, equal cluster/family averaging and the nuisance scales. Those choices can be rejected or changed after judgment; none is silently presented as a standard, validated annotation probability. The source examples lack actual target mapping and occupancy uncertainty, so they are **component-populated examples**, while the only complete target-level arithmetic is clearly synthetic. Method-specific non-diffraction observation support, empirical calibration, production readers, production credit integration and prompt review remain unimplemented.
