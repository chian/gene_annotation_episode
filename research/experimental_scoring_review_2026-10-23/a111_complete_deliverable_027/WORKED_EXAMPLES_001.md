# A111 worked numerical examples

All transforms and aggregation below are proposals in `A111_NUMERICAL_SHEET_001.md`. Native values are reused from the original A111 researchers' **cross-case** numerical receipts and source-coverage reports. This worker did not reopen their primary papers, deposit files or paper-specific conversion packets. Complete target-level examples below are synthetic and are not findings about ybhP or another real target.

## Contrasting source-derived cells

| Original inspected case and precisely scoped observation | Native values retained by original researcher | Rechecked proposed calculation | Missingness / experimental distinction |
| --- | --- | --- | --- |
| Zarembinski1998 / MJ0577 / 1MJH, modeled ATP copies A2001 and B3001 | RSCC .963 and .958; RSR .065/.071; deposited occupancies 1 | D values .927369 and .917764; fixed equivalent-copy mean **.9225665** | ATP-shaped model fit, not population occupancy, native substrate identity or ATPase activity. T unknown. Conditional q=C=I=1 for this exact model feature gives target support null [0,.9225665], conditional on reported fit values. |
| Same dataset, Mn oxygen neighborhoods | Six oxygen distances/site; A 2.255419–2.382306 Å, B 2.276454–2.380708 Å; 15 donor-pair angles/site | All six distances in proposed [2.0,2.6] Å and all 15 angles within 15° of 90° or180°: G_distance=G_angle=1 | These are geometric cells. The necessary full local water/metal endpoint-fit panel was not populated; **the ATP-only D is not a completed coordination D**. Mn was supplied in crystallization; physiological metal and activity remain unknown. |
| Same dataset, crystal interface | Reported 1,056 Å² buried per monomer and 15% | Native fraction .15; example predicate area≥1,000 Å² gives G+=1 | Model/crystal architecture, not measured solution oligomerization. Threshold is the stated question, not a biological-assembly classifier. |
| Fuhrmann2013 / YwlE, 4KK3 phosphate vs4KK4 C7S-derived phosphoserine model | PO4 RSCC .967, RSR .079; SEP7 .934, .097; deposited occupancy1 | Ligand D **.935089** versus **.872356** | The mutant's modeled phosphoserine does not directly observe a wild-type phosphocysteine intermediate or intact phosphoarginine substrate. |
| Same YwlE states, crystal-neighbor Arg149–Asp118 contact | NH2–OD2 2.458450935 and2.916030864 Å; Arg RSCC .773/.907; Asp .944/.934 | At ≤3.2 Å, G+=1 in both; D=min(endpoint RSCC)²=**.597529**, **.822649** | The contact involves a neighboring protein's Arg149; it is not added free arginine. The selected endpoint fit, not the stronger phosphate fit, enters this feature's D. |
| Same YwlE between-state comparison | ΔpH1.5; ΔPEG5 percentage points; construct matching146/151 after intentional change excluded; equal temperature | Proposed τ_pH1, τ_PEG10, construct fraction and temperature: `C=[exp(−1.125) exp(−.125) (146/151)·1]^(1/4)=.725482517751` | Multiple nuisance differences accompany intended C7S. There is no measured nuisance-effect bound B for causal isolation; **I remains null**. C cannot fill it. |
| Cao2013 TRPV1, RTX+DkTx state3J5Q; two opposing G643 oxygen pairs | Q pairs(.385,.395),(.374,.430); widths7.731054585 and7.768594918 Å | D pairs .148225,.139876; copy mean **.1440505**. Both meet the illustrative ≥6 Å width predicate. | Residue-level Q is retained as residue-level. q=1 is named-model conditioning; population occupancy and target mapping are unknown. |
| Cao2013 capsaicin state3J5R, corresponding selected pairs | Q pairs(.337,.338),(.315,.372); widths4.157251376 and4.713740447 Å | D .113569,.099225; copy mean **.106397**. Both meet <6 Å. | The agonist and toxin conditions differ. These are distinct scoped states, not independent conflicting repeats of an unchanged condition or an isolated toxin perturbation. |
| Bae2016 DkTx lobe K1 /2N9Z model9 | NOE intervals[0,4.43],[0,5.50] Å; distances4.078006376,3.116843596 Å | v=(0,0), D=**1**; cross-loop≤4 Å gives G+=1 | Exact named single-proton restraints; native intervals are not measured central distances/CI. T unknown. |
| Bae2016 lobe K2 /2NAJ model3 | NOE intervals[0,4.18],[0,4.73] Å; distances4.516511596,3.531800957 Å | v=(.336511596354,0), D=`[exp(−.336511596354²/.5)+1]/2`=**.898667600990**; G+=1 | Different lobe sequence/length. Same-model restraint fit is not held-out validity. Native validation violation .34 Å agrees at its reported rounding. |

The structural reviewer inspected Zarembinski/Fuhrmann; the native-modality reviewer inspected Cao/Bae to the finite coverage listed in `SOURCE_TO_COMPONENT_001.md`. The table retains their reported experimental arrangements. It does not reconstruct uninspected organism/genotype fields; taxon/construct details not carried in the cross-case artifacts remain unknown here. All source-target mappings remain null. A measured source feature never becomes a complete real-target annotation merely because its local D can be calculated.

The full NMR ensembles are **20 alternative model scenarios per dataset**, not 20 experiments or measured populations. Recomputing all retained numerical scenarios gives support-only DG ranges K1[0,1], K2[0,.920544685515]. If the question explicitly pairs ≤4 Å support with >4 Å opposition, complete signed-model ranges are K1[−1,1], K2[−.905144702365,.920544685515]. Those are conditional model ranges, not CIs; averaging the models or maximizing their positive and negative pieces into one point is not allowed.

## Full synthetic X-ray calculation and denominator repair

Supplied synthetic target material contains selected positions101–104=`DSAG`,201–202=`RF`,301–302=`DF`,401–402=`WR`. Source mappings to those exact target positions are stipulated here, rather than a public name or an overall homology grade. These records are invented specifically to fill the numerical sheet.

For the ligand-site feature, the source requires four roles: carboxylate oxygen at101, hydroxyl oxygen at102, histidine-ring nitrogen at103, backbone N at104. The target preserves three and fails the histidine role: T_A=T_C=3/4. Source B's fourth requirement is Lys terminal NZ rather than backbone N, so it preserves only the first two: T_B=2/4. The interface requires an aromatic CZ at202 and Lys NZ at201; target F preserves the first and R fails the exact stipulated second role, giving T_D=1/2. These are narrow role-preservation fractions, not assertions that Arg cannot have related chemistry.

The ligand geometry has six oxygen-distance predicates, support[2.0,2.6] Å and incompatible≥3.0 Å. XA distances are(2.2,2.3,2.35,2.45,2.55,2.8): G+=5/6,G−=0; the last lies in a declared gap, not an unread value. XB has all six distances2.3 Å, giving G+=1,G−=0. Required endpoint RSCCs for these synthetic panels all equal the listed minimum; no measured endpoint is missing. XC is a calibrated occupancy nondetection in the corresponding site, with observed surrounding marker RSCC .90 and full interrogated-site coverage G_examined=1. It supplies no ligand RSCC. XD is a separately declared crystal-interface feature with native measured area1,056 Å², support≥1,000 Å² and incompatible<900 Å².

| Canonical independent dataset | q or N | D | G+ / G− (or examined) | T | C | I | Directed products |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| XA | 80/100=.80 | .95²=.9025 | 5/6 /0 | .75 | .90 | .90 | p=.3655125,o=0 |
| XB | 75/100=.75 | .90²=.81 | 1/0 | .50 | .95 | 1 | p=.2885625,o=0 |
| XC calibrated nondetection | `N=1−.10/.50=.80` | .90²=.81 | examined1 | .75 | 1 | 1 | p=0,o=.486 |
| XD interface | 60/100=.60 | .80²=.64 | 1/0 | .50 | 1 | 1 | p=.192,o=0 |

All q counts are stipulated complete sampling counts. C_XA=.90 comes from one declared pH difference `sqrt(−2 ln .90)=.459043605` with proposed τ=1 pH unit; C_XB=.95 similarly uses .320291412. The other required conditions are stipulated fixed, rather than additional matching entries. I_XA=.90 comes from a distinct calibrated signal Y=10 units, other-component upper bound B=1 in the same units. XB/XC/XD have synthetic controlled B=0 under their specified assignments. C_XC=C_XD=1 records identical conditions for the exact comparison. XC calibration supplies q_U=.10 and its candidate feature entails q_req=.50 under those conditions.

The proposed ligand question gives P=max(.3655125,.2885625,0)=.3655125, O=.486, **Z=−.1204875**. With equal fixed weights for the ligand and interface families:

`P111=(.3655125+.192)/2=.27875625`, `O111=.486/2=.243`,

**`Z111=A111=.03575625`**, display3.575625.

The historical experiment-roster mean instead gave ligand Z=(.3655125+.2885625−.486)/3=.056025 and two-family Z=.1240125. The new arithmetic changes the declared estimand prospectively. It does not rewrite earlier results.

| Operation on the single XA record | Old properly deduplicated roster mean | Current proposal |
| --- | ---: | ---: |
| Original | .3655125 | .3655125 |
| Add known-zero T=0 experiment | .18275625 | .3655125 |
| Add7 duplicate representations | .3655125 | .3655125 |
| Revise sole current fit to .2, retain old version only in history | .2 | .2 |

For the first-three ligand rows, retain original synthetic product sensitivity bounds XA[.145807725,.764246025], XB[.2317392,.33856], XC opposition[.40656,.57132]. They derive from the fully stated factor intervals below and are outer sensitivity bounds, not experimental CIs:

| Row | q or q_U | RSCC | G+ | T | C | I |
| --- | --- | --- | --- | --- | --- | --- |
| XA | [.70,.90] | [.93,.97] | [4/6,1] | [.5,1] | [.85,.95] | [.85,.95] |
| XB | [.70,.80] | [.88,.92] | [1,1] | [.5,.5] | [.90,1] | [.95,1] |
| XC | q_U[.05,.15],q_req=.50 | [.88,.92] | examined1 | [.75,.75] | 1 | 1 |
| XD | [.50,.70] | [.78,.82] | 1 | [.5,.5] | 1 | 1 |

XA geometry uncertainty here concerns an additional gap/positive boundary and supplies no opposing event in the admitted scenarios. The declared bounds do not claim independent measurement errors. Row/source dependencies remain attached; endpoint propagation is an outer enclosure. The native conditions corresponding to C/I bounds are explicit: |ΔpH|=`sqrt(−2 ln C)` and B/Y=`1−I` for these synthetic definitions.

Therefore ligand P∈[max(.145807725,.2317392),max(.764246025,.33856)]=[.2317392,.764246025]; O∈[.40656,.57132]; Z∈[−.3395808,.357686025]. XD∈[.1521,.23534]. The two-family result has **Z∈[−.0937404,.2965130125]**, **A∈[0,.2965130125]**. Its positive point does not establish positive bounded direction.

## Full synthetic cryo-EM calculation, including mixed evidence

At target301–302=`DF`, source `DY` maps positionwise. Required roles are Asp OD1, Asp OD2, Tyr aromatic CZ and Tyr OH; the target preserves3/4. Four named contact distances share the fixed positive range[2.5,3.5] Å and incompatible range[4,∞) Å. G+/G− use the same denominator4. A distance in the intervening gap contributes neither. The local Q panel contains both endpoint residues, at residue granularity.

E1 has60 selected-feature objects among80 eligible objects, so q=.75. A distinct control bounds other-component contributions at B=12 of Y=60, giving I=.8. The fixed relevant nuisance list has pH7.5 vs7.0 (τ=1) and temperature298.15 K vs298.15 K (τ=10 K); hence C=`sqrt(exp(−.5²/2)·1)`=exp(−.0625)=.939413062813476. The intentional state difference is excluded.

| Observation / copy | Local Q | Four distances, Å | D | G+ | G− | p | o |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| E1 copy a | .80,.90 | 2.8,3.0,3.2,4.2 | .64 | .75 | .25 | .202913221568 | .067637740523 |
| E1 copy b | .70,.95 | 2.8,3.0,3.2,3.4 | .49 | 1 | 0 | .207140580350 | 0 |
| E2 independent dataset | .60,.90 | 4.5,4.6,4.7,4.8 | .36 | 0 | 1 | 0 | .135 |

E1 uses the shared q=.75,T=.75,C above,I=.8. E2 has40/80=.50, the same T=.75, documented identical nuisance conditions C=1 and synthetic control B=0,Y=40 giving I=1. All inputs have exact stipulated values for this calculation, with no claim of empirical error calibration.

Equivalent-copy **product means** give E1 p=.205026900959041, o=.033818870261285. E2 is a distinct actual preparation/dataset in the synthetic design. The current reducer gives:

**P=.205026900959041, O=max(.033818870261285,.135)=.135, Z=A=.070026900959041.**

This deliberately repairs the earlier synthetic table's sign omission: its fourth distance4.2 Å met the declared contrary criterion but was counted only as lost positive geometry. The current table retains both. The earlier arithmetic remains preserved in its original files and is not a current scientific result. Multiplying separately averaged D and G instead of averaging complete products is also incorrect.

## Full synthetic NMR calculation

At target401–402=`WR`, source `WK` maps positionwise. Required roles are Trp indole group, second-residue backbone HA and the specifically stipulated Lys terminal NZ group. The target preserves2/3. Two local proton-distance predicates support d≤5 Å and oppose d>5 Å; fixed J_G=2. Two synthetic independent preparations each supply a named model and assigned single-proton NOE restraints; all native bounds/units are explicit below. q=C=I=1 have **named-model, assignment-conditional** meanings, not measured population probabilities.

| Dataset | Restraint intervals, Å | Modeled distances, Å | Violations, Å | D with τ=.50 Å | G+ /G− | p /o |
| --- | --- | --- | --- | ---: | --- | --- |
| N1 | [0,4],[0,5] | 4,5.5 | 0,.5 | (1+exp(−.5))/2=.803265329856 | .5 /.5 | .267755109952 /.267755109952 |
| N2 | [0,5],[0,6] | 5.25,6.75 | .25,.75 | (exp(−.125)+exp(−1.125))/2=.603574684971 | 0 /1 | 0 /.402383123314 |

The current reducer gives **P=.267755109952106,O=.402383123314315,Z=−.134628013362209,A=0**. This retains N1's actually opposing second contact instead of displaying it only as a reduction of positive geometry. If other admitted models were available, complete p/o products and candidate results would be evaluated jointly in each scenario; there would be no average population from model count.

## Two complete synthetic candidate sheets across all three modalities

H_A expects the ligand-site and crystal-interface features above plus the shorter EM and NMR contact panels. H_B expects the same ligand/interface features but the longer EM/NMR panels; the explicit positive/contrary sets for those last two panels swap. Both candidates use the same supplied material, mappings, source observations and **four fixed family weights¼** (one question per family, β=1). These are competing structural expectations, not proposed real functional annotations. The joined index remains conditional on the specified NMR models and the proposed transformations.

| Family | H_A P | H_A O | H_A Z | H_B Z |
| --- | ---: | ---: | ---: | ---: |
| X-ray ligand | .3655125 | .486 | −.1204875 | −.1204875 |
| X-ray interface | .192 | 0 | .192 | .192 |
| Cryo-EM contacts | .205026900959 | .135 | .070026900959 | −.070026900959 |
| NMR contacts | .267755109952 | .402383123314 | −.134628013362 | .134628013362 |

H_A: P=.257573627728,O=.255845780829, **Z=A=.001727846899** (display .172784689921).

H_B: P=.273723905829,O=.239695502728, **Z=A=.034028403101** (display3.402840310079).

Under the declared X-ray sensitivity bounds and fixed synthetic EM/NMR values:

* H_A Z∈[−.063020478101,.132106228149], A∈[0,.132106228149].
* H_B Z∈[−.030719921899,.164406784351], A∈[0,.164406784351].
* The shared uncertain ligand/interface terms cancel **within every common scenario**. ΔZ=Z_A−Z_B=**−.032300556202** has a point calculation envelope, conditional on the stipulated EM/NMR inputs. Subtracting the two separate wide candidate intervals would lose this known dependency.

Neither candidate has robust positive absolute direction under those sensitivity envelopes. The stated relative contrast favors H_B's specified geometry in this synthetic scenario; it does not select an annotation or provide a posterior probability.

## Boundary cases that do not manufacture evidence

An unexamined question has zero **documented contribution** and explicit unexamined coverage; it is not negative evidence. A real row missing a required Q or NOE remains an unknown contribution. A known T=0 annihilates its product even if a different factor is unreported, while that factor's missing cell is preserved. Adding the zero chain cannot dilute another chain.

Two possible conformers with complete signed products+.6 and−.4 give no population point and an envelope[−.4,.6]. By contrast, actually measured physical weights(.7,.3) applied to(+.4,−.2) give P=.28,O=.06,Z=.22. Fixed physical weights and changing evidence-roster counts are different denominators.

The full research checker passed112 assertions, including all40 retained NMR numerical scenarios, actual printed arithmetic, current-fit replacement, duplicate/zero invariance, real opposition, fixed missing-member denominators, joint candidate cancellation and bounds. It recomputed from cross-case receipts; it did not re-extract primary data or run a structure calculation.
