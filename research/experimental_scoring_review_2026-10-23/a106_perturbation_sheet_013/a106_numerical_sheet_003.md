# A106 numerical sheet: perturbation and restoration — research revision 003

This additive revision preserves both earlier numerical-sheet drafts. It retains revision 002’s separate perturbation/restoration isolation and aggregation of signed points before joint uncertainty reduction. It also bounds the necessity-deficit transformation explicitly, applies the same joint uncertainty treatment to that mode, and defines zero-amount comparability. These corrections supersede the corresponding earlier formulas. No primary source was reopened to make these mathematical corrections.

**Goal:** provide a usable numerical sheet whose measured components combine into a bounded A106 contribution. This is independent preparation under the ten-sheet goal while A105 remains first and unfinished. This document delivers the numerical research proposal and exact population specification; no production reader, prompt, library entry, credit consumer, experimental job or scientific episode is implemented. It does not declare A106 complete or any formula adopted.

The evidence is a perturbation/restoration experiment on the supplied target **or a relevant homolog**, connected by measured correspondence. The starting material may be a sequence, selected record, region or snippets. A functional interpretation can emerge later. The sheet scores the bearing of observed perturbation effects on that interpretation in its stated system; it does not require an initially named candidate or public identifier. Direct reaction/transport/binding belongs to A105. A phenotype does not establish catalysis. A109 remains deleted and A110 remains separate.

## 1. Numerical sheet and complete combination

One populated row is one defined functional inference, endpoint, perturbation comparison and condition scope. Source provenance, genotype and sampling fields support the numeric cells but do not themselves earn points. `null` means unknown, with a reason; it is different from an observed zero or a component that is scientifically inapplicable.

For the basic restoration design, let `W`, `K`, and `R` be reference, perturbed, and restored population means of the **same nonnegative ratio-scale endpoint**. Its zero must have an experimental meaning. Examples are acquisition events per eligible cell, viable-count ratio at a fixed time, or lag minutes at a declared OD threshold. Use CFU or survival ratios rather than an arbitrary offset on a log-CFU plot. Convert back from logged reported values only with the exact transformation and averaging meaning preserved. Signed residuals or Z scores cannot be inserted into this formula as if they were counts.

| Cell | Exact inputs/type/unit/denominator | Calculation and range | What the number evaluates |
|---|---|---|---|
| `W,K,R` | Three nonnegative real means in identical endpoint units; each retains population, eligibility denominator, measurement model, independent-unit IDs and uncertainty | Mean over the nominated biological units after the specified measurement correction; not over technical duplicates | The actual phenotype in each arm |
| `D` | `W,K` | `W−K`, endpoint units | Magnitude and direction of the perturbation contrast |
| `theta` | `W,K`; `W+K>0` | `(W−K)/(W+K)`, [−1,1] | Symmetric proportional effect: invariant to endpoint unit scaling; halving produces 1/3; a near-zero difference produces near zero |
| `restoration_fraction_raw` | `W,K,R`; `D≠0` | `(R−K)/D`, unrestricted real | Fraction of the observed perturbation difference reversed, retaining overshoot |
| `r` | Same endpoint means | `clip(1−abs(R−W)/abs(D),0,1)` | Agreement with restoration to the reference phenotype, 0 to 1. Complete return gives 1; no return gives 0; overshoot is not silently counted as better rescue |
| `C_j` | Two nonnegative measured amounts/doses with `max(x_j0,x_j1)>0` for **one nominated unintended mismatch**, same unit and meaningful zero | `min(x_j0,x_j1)/max(x_j0,x_j1)`, [0,1] | Fractional agreement of that experimental quantity, without assuming a linear phenotype response |
| `C` | Distinct applicable `C_j`; dependencies and primitive-input reuse declared | `product_j C_j`, [0,1] | Overall measured experimental comparability outside the intended change |
| `B` | Endpoint-scale nuisance bounds `B_pert` for `W−K` and `B_rest` for `R−K`, each from applicable controls | `max(B_pert, B_rest*abs(W−K)/abs(R−K))` when both contrasts are nonzero | Rescales the two measured bounds to the perturbation scale; protects both forward and restoration attribution |
| `I` | `B,D`; `D≠0` | `clip(1−B/abs(D),0,1)` | Fraction of the observed difference remaining after the supplied bound on nuisance explanations; conditional on the controls/model's coverage |
| `M` | Measured molecule/feature correspondence, chosen relation defined below | A specified product/measurement below, [0,1] | Correspondence between the assayed molecule and supplied target |
| `O` | Measured joint source/target condition distributions under the **same claimed scope**, or verified identity of the two scoped systems | `sum_c min(p_source(c),p_target(c))`, [0,1] | Overlap of the assayed and target-system exposure contexts; not an organism-name grade |
| `H` | `M,O` | `M×O`, [0,1] | Measured evidence-chain correspondence, including molecular and system terms |
| `q_point` | All above numeric operands; orientation `s∈{−1,+1}` defined by the inference | `s × theta × r × C × I × H`, [−1,1] | Proposed signed, bounded A106 contribution before uncertainty reduction |
| `[q_L,q_U]` | The joint admissible measurement/model set, including shared operands and nuisance bounds | A conservative enclosure of the same `q_point` function over that set | Propagated measurement/model uncertainty, not an assumed probability |
| `U` | Point and interval containing that point | If `q_L>0`, `U=q_L/abs(q_point)`; if `q_U<0`, `U=abs(q_U)/abs(q_point)`; if interval crosses zero, `U=0`; undefined when point is zero/unknown | Fraction of the signed point contribution retained by the uncertainty bound |
| `q` | Point, `U` | `q=q_point×U`: nearest-to-zero bound when sign is resolved; 0 when a known interval crosses zero | Proposed uncertainty-resolved contribution; report its point and interval alongside it |

Here `clip(z,0,1)=min(1,max(0,z))`. The constants 0 and 1 are bounds and proportional identity/no-effect anchors, not ordinal labels. Every exponent in the product is 1: each quantity has the interpretation written in the table. This is a scoring convention that penalizes incomplete effect/restoration, amount mismatch, residual alternative explanations, imperfect correspondence and uncertainty. It is **not** a calibrated causal probability or an assertion that the factors are independent. It has no tanh, A105 profile, universal relevance grade, or undefined “reliability” scalar.

`s=+1` means the emerging inference predicts larger endpoint values with the reference component than after perturbation; `s=−1` means it predicts smaller values. Its choice comes from the precise functional interpretation, not from which sign makes the observed result favorable. For a nondirectional “changes the endpoint” inference, retain two explicitly oriented alternatives rather than silently taking an absolute value for every claim.

If `D=0`, the positive-effect component is exactly zero, restoration is undefined, and the positive contribution is 0 only where the other evidence is known. This does not establish absence of function. If `W+K=0`, the ratio is undefined. Missing restoration, comparability, isolation or transfer inputs leave `q_point=null`; retain any computable component and a partial-domain bound. A missing factor is never silently replaced by 0, 0.5, or 1. “Not applicable” permits the multiplicative identity only with an explicit experimental reason, such as amount removal being the intended perturbation.

## 2. Experimental comparability and causal isolation are different calculations

`C` asks whether the compared experiments have similar measured nuisance conditions. `I` asks how much of the outcome can be assigned to the intended change, given specific alternative explanations. A high `C` cannot make `I=1`. Similar amounts do not prove normal folding or specific molecular action. A different amount can matter little in a saturated response regime. The 64% YeaG signal therefore populates one conditional comparability component, **not** a 36% activity loss or a phenotype correction.

Applicable `C_j` examples are measured protein amount during a residue-substitution comparison, measured rescue amount relative to the reference, or an unintended difference in supplied ligand dose. The intended deletion/depletion is excluded from `C`; its remaining amount/activity is a separate perturbation-extent measurement. Do not multiply both mRNA and protein amount as two versions of the same exposure, or both nominal inducer and protein amount when the inducer's only nominated effect is the expression already measured. Distinct direct inducer effects require their own evidence.

The ratio convention applies only to quantities with a meaningful zero and a justified proportional comparison. Kelvin-temperature ratios or arbitrary recoding of media names are not meaningful substitutes for biological comparability. Matched categorical settings remain facts. For nonproportional conditions, use an experimentally measured response or matched strata; unknown consequential differences remain explicitly unresolved. A source/target context overlap can be measured as `O` when empirical distributions exist, but invented state frequencies cannot fill it.

`B_pert` and `B_rest` must each cover the specified nuisance set for their own comparison. `I` is therefore the smaller of `clip(1−B_pert/abs(W−K),0,1)` and `clip(1−B_rest/abs(R−K),0,1)`. This prevents an unrelated bypass rescue from being treated as specific merely because the original perturbation was well isolated. The minimum is a deliberate weakest-comparison convention, not a probability or independence assertion. If `R=K`, restoration is zero and no positive restoration contribution is assigned; the undefined restoration isolation is retained. A measured joint bound that already covers both comparisons can populate `B` directly with its derivation.

Each underlying nuisance bound must cover the specified nuisance set. Examples are an amount-matched WT titration, an all-nuisance/no-target-change factorial contrast, or paired off-target correction with bounded residual interactions. If measured component bounds `b_j` and a joint interaction bound `b_interaction` actually justify a triangle bound, each of `B_pert` and `B_rest` can be populated as `sum_j b_j+b_interaction`; keep the exact values and units. Setting all unmeasured interactions to zero is an assumption, not data. A direct all-nuisance contrast can replace that sum and avoid inventing independence. “No off-target effect mentioned” does not make `B=0`.

Do not treat the downstream consequences that **define the intended functional contribution** as off-target nuisance. For example, a physiological regulatory response can be the contribution under investigation. Nuisance controls instead bound alternative changes introduced by the perturbation or rescue, such as dosage, unintended genetic changes or measurement interference. When a claim specifically concerns one catalytic activity, residual activity and competing molecular changes must be measured or remain unknown.

The product `C×I` deliberately evaluates both closeness of conditions and residual causal ambiguity. Where the same abundance measurement informs both, it is one shared primitive in the uncertainty set; the two outputs are not independent pieces of evidence. This convention is explicitly offered for review because it can be conservative. It does not assert linearity of the abundance–phenotype relationship.

## 3. Amount, residual activity, rescue dose and molecular transfer

Record these separately:

| Numeric cell | Exact calculation | Scientific use |
|---|---|---|
| `residual_amount_fraction` | Measured protein amount after perturbation / reference amount, same normalization | Quantifies amount remaining; does not establish residual catalytic capacity |
| `residual_activity_fraction` | Relevant activity of the perturbed system / reference activity under matched conditions, retaining protein normalization | Quantifies capacity remaining for that particular activity |
| `P_effective` | `clip(1−residual_capacity_fraction,0,1)` using the capacity actually required by the tested claim | Makes a negative/equivalence challenge interpretable; amount can substitute only for an amount-removal claim, not automatically for a catalytic knockout |
| `mutant_molecule_fraction` | `A_mutant/(A_mutant+A_WT)` in a verified mixture | Describes coexpression only; no phenotype or oligomer activity is calculated from it without a measured response model |
| `rescue_amount_ratio` | Restored protein's measured amount / reference amount | A possible `C_j` when reference-like dosage is relevant; also supports an empirical dose-response nuisance bound |

For positive effect/restoration, `P_effective` is reported but is not automatically multiplied into `q`: a selective partial perturbation can demonstrate contribution. For a negative result, incomplete perturbation limits what necessity claim was actually tested and enters the separate equation below. This distinction prevents a weak intervention with no phenotype from appearing as decisive evidence of dispensability.

Choose and document the actual molecular relationship that justifies transfer; do not average incompatible measurements or select whichever yields the largest score. These are finite proposed routes rather than a new overall relevance scale:

| Relationship used for this inference | Exact proposed `M` | Required measurements and limits |
|---|---|---|
| Assayed molecule is the supplied target | 1, within verified material/construct boundaries | Actual molecule identity and assayed region must be established. A shared label alone is insufficient; incomplete snippets cannot establish unobserved full-length identity |
| Sequence correspondence | `coverage × identity × determinant_agreement` | `coverage=target residues paired with an assayed nongap residue / full length of the declared target scope`; `identity=identical aligned residue pairs / aligned nongap pairs`; optional determinant term is `preserved mapped required determinants / all required determinants for this particular inference`. Preserve alignment raw score/E-value, coordinates and the actual tested construct. Do not quietly use the snippet length as a full-protein denominator |
| Structural correspondence | `min(TM_target_normalized,TM_assayed_normalized) × determinant_agreement` | Actual structure comparison scores and mapped experimentally implicated features; TM scores already contain a coverage/distance normalization, so do not multiply another copy of coverage. Neither a model name nor a shared fold supplies a number |
| Functional replacement in a matched recipient | `clip(1−abs(R_homolog−R_target)/abs(R_target−K),0,1)` | Independent, amount-controlled matched replacement measurements for this endpoint. This measured interchangeability relates the tested functions, not whole-molecule identity. If these are the same restoration data used in `q`, consume them once as the experiment itself rather than again as transfer |

The determinant term is applicable when the inference depends on a declared set of experimentally relevant determinants. It is not required merely because a protein has residues. An applicable but unmeasured determinant is unknown. A preserved determinant means its mapped chemical property or demonstrated functional replacement matches the specified requirement; do not invent “conservative substitution” weights. A feature count is a property measurement, not an overall ordinal relevance judgment. These conventions include structural and experimental relationships; transfer is not restricted to sequence homology.

`O` compares actual joint context distributions, using the same states and denominator in source and target. The state partitions must be fixed by the functional question (for example the same substrate/condition/partner contexts), not drawn afterward to improve overlap. If the claim is explicitly conditional on starvation, compare within that condition; the organism's total fraction of time starving is not an extra penalty. Verified same scoped system gives `O=1`. If no numerical system comparison exists, retain unknown; any later explicitly scoped qualitative judgment must identify its own operands and rationale and cannot replace the measured terms above.

## 4. Measurement validity and uncertainty

Validity is evaluated in the **observation model before effect calculation**, not through an assay-name grade. Record raw signal, blank, calibration slope/intercept and valid range where relevant. For a validated linear instrument relation `x=a*y+b`, use `y=(x−b)/a` with the measured uncertainty in `a,b,x`; do not multiply a second recovery penalty after the same bias was already corrected. If the measurement is an observed binary-event fraction with measured sensitivity `t` and false-positive rate `f`, the explicit correction is `p_true=(p_observed−f)/(t−f)`, requiring `t>f` and a compatible validation population. If this correction conflicts with physical limits, retain a model-fit failure/interval rather than clipping an impossible point and claiming calibration. These are alternative measurement models, not mandatory factors for every experiment.

For CFU, retain counts, plated volume, dilution, counting bounds and biological sampling. For recovery lag, retain time/OD values, blank correction, threshold and interpolation/fitting method. For PCR acquisition, equal OD template is not a calibration of expanded-locus fraction; needed amplification and detection information remains unknown. An arbitrary fluorescence intensity cannot simply become an event count.

Uncertainty uses the actual independent units and dependence structure. Technical wells, repeated time points, clones from one expansion, shared WT controls, and reused calibration samples retain common identities. With raw data, a later reader can calculate a joint interval using a declared model and resample entire independent blocks. With covariance, preserve off-diagonal terms; never set them to zero merely because they are unreported. SD is not SEM; SEM is not a confidence interval; rounded ±0.0 is not known exactness.

When only defensible component bounds are available, interval arithmetic is conservative without assuming independence. All comparisons using the same `W,K,R` refer to the same unknown quantities. Evaluating each factor's extrema and multiplying nonnegative bounds can yield a loose **outer enclosure**, which is acceptable if labeled as such; it does not claim that all extrema occur together. For a statistical confidence enclosure, its declared joint coverage must come from the actual model or simultaneous interval construction. No 95% confidence is invented from a pair of displayed error bars.

For the common branch `W>K`, `K<R<W`, with these orderings preserved throughout the bounds:

```
theta_L = (W_L−K_U)/(W_L+K_U)
theta_U = (W_U−K_L)/(W_U+K_L)
r_L = (R_L−K_U)/(W_U−K_U)
r_U = (R_U−K_L)/(W_L−K_L)
I_L = clip(1−B_U/(W_L−K_U),0,1)
I_U = clip(1−B_L/(W_U−K_L),0,1)
q_L = theta_L*r_L*C_L*I_L*H_L
q_U = theta_U*r_U*C_U*I_U*H_U
```

This supplies a directly computable enclosure for the worked example. Other orderings use the original absolute-value/clipping formulas and interval branches; possible `D=0` requires retaining `r,I∈[0,1]` with the singular point reported. An arbitrary corner enumeration is insufficient when an extremum can occur at `R=W` or a clipping boundary. A point outside its purported interval is an input/model error. Unknown components keep `q_point=null`, even if a coarse domain bound can be calculated.

## 5. Completely filled synthetic end-to-end sheet

**Every number in this section is invented for arithmetic demonstration. None is YeaG, Cas2, ybhP or an executed experiment.** This example investigates a protein's contribution to a cellular event in a defined condition. The endpoint is independently validated events per 100,000 eligible cells, with no remaining classification correction in this fixture. The intended change is reduction of functional protein capacity; the added construct restores it. The compared genotype carries no coexisting WT copy in the perturbed arm.

| Synthetic input | Values and exact meaning |
|---|---|
| Three matched biological blocks | Reference: 98, 100, 102; perturbed: 18, 20, 22; restored: 88, 90, 92 events per 100,000 cells. Each row/block contains all three arms. Technical repeat count 1 |
| Means | `W=100`, `K=20`, `R=90` |
| Bounded error assumptions supplied with this synthetic dataset | True tested-population means are within `W∈[98,102]`, `K∈[18,22]`, `R∈[88,92]`. These are stipulated validation bounds, **not confidence intervals inferred from the observed ranges** |
| Nuisance-only controls | Perturbation nuisance bound `B_pert=8`, admissible `[6,10]`; restoration nuisance bound `B_rest=7` exactly in this fixture, both in events per 100,000 cells and covering their residual interactions. Thus `B=max(8,7*80/70)=8`. The conservative outer interval `[6,10]` remains valid: the largest scaled restoration bound is `7*84/66=8.90909<10` |
| Perturbation extent | Reference relevant capacity 100 units, perturbed 5 units; residual fraction 0.05 and `P_effective=0.95`. Reported, not multiplied into this positive-effect row |
| Rescue amount comparison | 90 versus 100 molecules per cell, exact fixture values: `C=90/100=0.9`. No other distinct applicable nuisance comparability term is nominated |
| Molecular correspondence | Declared target scope length 100 residues; 90 target residues aligned; 72 identical aligned pairs; 3 of 4 required determinants retained: `M=(90/100)*(72/90)*(3/4)=0.54` |
| System correspondence | In the declared two-state scope, source frequencies `(1,0)` and target frequencies `(0.8,0.2)`: `O=min(1,.8)+min(0,.2)=.8`. Exact fixture fractions; `H=.54*.8=.432` |
| Claim orientation | `s=+1`: component promotes the measured event under this scope |
| Grouping | One experimental contribution group, with three matched biological blocks. No duplicated record; all three arms share block identities |

| Filled score component | Checked calculation | Result |
|---|---|---:|
| Signal | `(100−20)/(100+20)` | 0.6666666667 |
| Raw restoration fraction | `(90−20)/(100−20)` | 0.875 |
| Restoration agreement | `1−abs(90−100)/80` | 0.875 |
| Experimental comparability | `90/100` | 0.9 |
| Isolation | `1−8/80` | 0.9 |
| Molecular correspondence | `.9*.8*.75` | 0.54 |
| System overlap | `.8+0` | 0.8 |
| Combined correspondence | `.54*.8` | 0.432 |
| Point contribution | `(2/3)*.875*.9*.9*.432` | **0.20412** |
| Signal bound | `[76/120,84/120]` | [0.6333333333, 0.7] |
| Restoration bound | `[66/80,74/80]` | [0.825, 0.925] |
| Isolation bound | `[1−10/76,1−6/84]` | [0.8684210526, 0.9285714286] |
| Conservative contribution enclosure | Products of lower and upper components above | **[0.176418, 0.233766]** |
| Uncertainty retention | `.176418/.20412 = 121/140` | 0.8642857143 |
| Final uncertainty-resolved row contribution | `.20412*(121/140)` | **0.176418** |

The one-group A106 contribution is therefore 0.176418 bounded units; a presentation-only 100-point scale would display **17.6418**. This is not a probability and does not install a new global annotation formula. The actual source papers do not supply all these fixture quantities.

The example also shows why a raw 0.9 rescue amount is not the score: signal, recovery of the phenotype, distinct nuisance isolation, molecular/system correspondence, and uncertainty all have separate measured roles and explicitly combine.

## 6. Shared evidence, replication, consistency and bounded aggregation

For **one exact inference and scope**, form `G` distinct contribution groups from the original experiment identities. Duplicate articles, tables, figure panels, retained summaries or later reports of the same experiment remain one group. Several variants sharing WT controls and several readouts of the same cultures are one dependence-connected group unless the design identifies distinct populations and questions. Use one nominated primary endpoint per group by default. Complementary measurements populate its measurement model, `B`, correspondence or uncertainty; they are not extra positive scores.

If the scientific inference genuinely defines a composite of endpoints, declare all `J` endpoints before looking at their scores and use `q_g_point=sum_j q_gj_point/J` within that group, then calculate its joint enclosure. This is an equal-endpoint convention, not an independence assumption. Preserve joint uncertainty and do not let many easy endpoints dilute a required mechanistic failure. If an inference requires **all** endpoint conditions, instead define the conjunction's endpoint before scoring and keep it separate from this averaging convention. These are different scientific estimands, not optional ways to maximize credit.

Independent replication contributes its raw blocks to the declared sampling model or supplies an independently replicated experimental group. There is no bonus equal to publication count, laboratory reputation or technical-repeat count. Without raw values/uncertainty, “replicated ≥3” is a bounded replication count, not a precision score.

The default finite combination across distinct comparable groups is:

```
w_g = 1/G
Q_point = sum_g w_g*q_point_g
[Q_L,Q_U] = a joint conservative enclosure of the same signed weighted sum
Q = Q_L if Q_L>0; Q_U if Q_U<0; otherwise 0
positive_mass = sum_g w_g*max(q_point_g,0)
negative_mass = sum_g w_g*max(−q_point_g,0)
Q_point = positive_mass − negative_mass
consistency = abs(Q_point)/(positive_mass+negative_mass), when denominator > 0
A106_support = max(0,Q)
A106_counter = max(0,−Q)
```

Thus `Q_point,Q∈[−1,1]`, and support/counter each lie in [0,1]. Per-row `q` remains a useful displayed conservative contribution; aggregate the signed points and joint intervals, not already-reduced per-row `q` values. This applies uncertainty once and prevents opposing interval ranges from producing a falsely resolved aggregate sign. Equal group weights mean each independently identified experiment design has one share. They are an explicit scoring convention, not inverse-variance probabilities. Do not multiply consistency into `Q` again: cancellation is already represented. Retain positive and negative masses so a zero caused by disagreement is distinguished from no measured effect.

A complete annotation may contain several distinct functional inferences. This sheet returns the per-inference A106 contribution and scope; W05 owns how those enter the global annotation function. It does not add scores for different functions or assay conditions simply because they share a gene. It can export a declared fixed-scope equal average of per-scope contributions if that is the annotation's actual scope, retaining every scope's numerator and denominator. No maximum-over-favorable-experiments selection is built in.

Unknown groups stay in the declared denominator and carry interval domains; silently dropping them and renormalizing known favorable groups would overstate completeness. A partial known-subset score may be printed with its explicit denominator alongside the whole-scope interval. Repeated representations do not change `G` or the arithmetic. Shared covariance remains in the aggregate interval.

**Complete synthetic contradictory comparison:** a second independent group has `W=20`, `K=100`, `R=30`, the same `C=.9`, `B=8`, `H=.432`, and mirrored bounds `[18,22]`, `[98,102]`, `[28,32]`. Under the same promoting-function orientation, `theta=−2/3`, `r=.875`, `I=.9`, `q_point=−.20412`, enclosure `[−.233766,−.176418]`, and `q=−.176418`. Combining the two groups gives `Q_point=Q=0`, positive mass = negative mass = `.10206`, consistency = 0, and combined enclosure `[−.028674,.028674]`. The former draft used `.088209` masses after per-row reduction; these are replaced by point-contribution masses in this revision. This is unresolved contradiction in the specified scope, not disappearance of both experiments. Different endpoint/timing scopes should instead be separated, as the YeaG lag/survival distinction demonstrates.

## 7. Nondetection and numerical counterevidence

Failure to detect a perturbed endpoint is censored data. If `K<LOD` and its calibrated range is `[0,LOD]`, propagate that range. For known positive `W`, `theta∈[(W−LOD)/(W+LOD),1]`. A missing detection limit gives no numeric upper bound on `K`. If both arms are below detection, no functional absence follows. A visible but uncalibrated PCR band supplies neither a fraction of cells nor a numerical equivalence interval.

For a **specific necessity claim** that predicts at least `theta_required∈(0,1]` after the stated molecular perturbation, define a second mode with the same point/bounds/aggregation machinery:

```
theta_oriented = s*theta
deficit_point = clip(theta_required − theta_oriented,0,1)
I_cancel = clip(1 − B_cancel/D_required,0,1)
q_counter_point = −deficit_point * P_effective * C * I_cancel * H
[q_counter_L,q_counter_U] = joint enclosure of that same formula
q_counter = q_counter_U if q_counter_U<0; otherwise 0
```

`D_required>0` is the endpoint-scale minimum effect entailed by the same claim; `B_cancel` bounds nuisance changes that could cancel that effect. The upper cap of 1 makes the deficit a bounded scoring transform even when the observed effect has the opposite sign; it prevents `theta_required−theta_oriented` from exceeding the unit contribution scale. It is a declared saturation convention, not a probability. `P_effective` must measure the molecular change named in the claim. A gene’s presence, a signature-residue substitution, and a demonstrated catalytic-null state are different perturbations.

All point operands and their joint bounds enter the same function. When `P_effective,C,I_cancel,H` are exact nonnegative values and the oriented effect has bounds `[theta_lower,theta_upper]`, the explicit enclosure is:

```
q_counter_L = −clip(theta_required−theta_lower,0,1)*P_effective*C*I_cancel*H
q_counter_U = −clip(theta_required−theta_upper,0,1)*P_effective*C*I_cancel*H
```

If those factors or the claim’s effect translation are uncertain, propagate their actual joint bounds too; using point factors with an effect bound is not automatically conservative. Unknown relevant residual capacity remains unknown. This mode therefore uses a deficit point and a full interval, not an uncertainty-bound deficit mislabeled as a point.

Set `scoring_mode=necessity_challenge`; the restoration row uses `scoring_mode=restoration_effect`. The modes answer distinct scientific inferences and cannot count twice as independent contributions from the same experiment. A necessity-challenge row assigns `q_point=q_counter_point`, `[q_L,q_U]=[q_counter_L,q_counter_U]` and `q=q_counter` for the shared output/aggregation interface. Thus aggregation still combines point contributions and joint bounds once. The resolved row does not receive a second uncertainty multiplier. Its positive maximum is 0 because this mode tests contradiction of a specified necessity minimum, not positive establishment of necessity.

The minimum effect is attached to the scientific claim before interpreting this test, not invented from an observed p-value. When a claim has no such minimum, retain the negative observation without fabricating a numerical necessity challenge.

**Fully specified synthetic negative example:** the claim requires ≥50% endpoint loss from reference `W=100`, so `D_required=50` and `theta_required=(100−50)/(100+50)=1/3`. Observed means `W=100,K=97` give point `theta=3/197`; a stipulated valid joint analysis gives `theta∈[−.02,.05]`. Relevant residual capacity is 5/100, hence `P_effective=.95`; a nuisance-cancellation bound 5 units gives `I_cancel=1−5/50=.9`; `C=H=1` for this exact synthetic target/system. All factors except the effect are exact fixture values. The point deficit is `1/3−3/197=188/591`, giving `q_counter_point=−.2719796954`. The deficit interval is `[17/60,53/150]`, hence the contribution interval is `[−.3021,−.24225]`; its uncertainty-resolved counterevidence is `q_counter=−.24225`. This result is synthetic and specifically challenges the quantitative necessity claim. It does not say the protein has no role. Cas2’s qualitative E9 observation cannot populate this example because the numerical acquisition interval and relevant residual activity are absent.

## 8. Published contrasts and source-to-component trace

The paper packets contain the experimental definitions and actual source qualifiers. This table shows how those observations inform the sheet rather than replacing it with the papers' language. Unknown operands remain unknown; the full synthetic score is not attributed to either paper.

| Inspected source/locator | Actual numerical contrast or boundary | Sheet cells informed | Exact reason not to fill an entire published score |
|---|---|---|---|
| [YeaG paper](https://doi.org/10.1038/srep17524), Fig. 3C and Results | K116A His signal/WT plasmid His signal = .64; R232A=.48; Y382Stop=.96 | Conditional `C_amount=.64,.48,.96`; genotype, normalization and intended-variable fields | No dose–phenotype bound, full calibration/uncertainty or relevant target mapping; relative signal is not per-cell active protein |
| Same, Fig. 3C versus Results | K426A figure signal 1.12, Results abundance 100% | Alternative `C_amount=1/1.12=.8928571429` versus 1 | Explicit unresolved source discrepancy; values are neither averaged nor counted as two experiments |
| Same, Fig. 2 | 12/18/24 h starvation: lag reductions 8.5/10.7/13.4% | `theta=.0443864230/.0565240359/.0718113612` | Shared/cross-time covariance, full intervals and restoration data unavailable; different starvation durations are separate scopes |
| Same, Fig. 3 versus Fig. 6B | Recovery variants include K116A; survival panel lists K426A and Y382Stop at 20 min/72/120 h | Endpoint and contribution identity; dependence grouping | No K116A survival experiment may be fabricated; early regrowth and late survival are not opposing estimates of one endpoint |
| [Cas2 paper](https://doi.org/10.1038/nsmb.2820), Supplementary Table 1 | 30/32 listed spacers have length 33 bp; 2/32 length 34; 26/32 plasmid, 6/32 genomic | Conditional event-composition cells `.9375,.0625,.8125,.1875`; measurement denominator | Already-selected expanded clones, with unknown independent sampling; cannot become acquisition frequency or generic validity |
| Same, Methods/Figs. 3–4 | OD-normalized PCR, ≥3 acquisition repetitions, E9 variants retain detectable acquisition; interface deletion nondetected | Measurement model, independent-unit lower bound, censoring, residual activity, negative-evidence route | No calibrated per-cell frequencies/detection limit/variant activity; “similar” is not numeric equivalence |
| Same, Supplementary Figs. 1–3 and main comparisons | Tag controls, assembly comparisons, and donor/recipient distinctions | Nominated nuisance controls and transfer feature/scope definitions | Not every variant receives a quantitative folding, abundance or activity validation; no blanket `I=1` |

Native measurements, derived arithmetic and proposed transforms are labeled in each packet. `arithmetic_results.json`, `arithmetic_results_002.json`, and `arithmetic_results_003.json` verify the printed source fractions and synthetic calculations with exact rational arithmetic. It does not independently validate the experiments or estimate missing data.

## 9. Exact reader population interface and remaining review choices

`reader_io_003.md` specifies the exact typed input/output fields for future literature and dataset readers that populate this sheet. These readers remain unimplemented, as assigned. They populate native measurements and declared relationships; deterministic calculations then fill the formula cells. A model is not asked for one “overall relevance” number. Source uncertainties, missing operands, construct coexistence and dependence are validated as meaningful relationships, not buried in free text.

The bounded draft supplies every calculation required for the worked complete score, its counterevidence example, molecular/system combination and aggregate. It does not defer completion to perpetual calibration research. The finite proposed conventions still need the user's judgment: symmetric proportional effect size; restoration-to-reference penalty including overshoot; joint use of comparability and effect isolation; the explicit molecular correspondence products; conservative uncertainty retention; and equal-group aggregation. Those are reviewable choices with printed consequences, not hidden unknown weights.

The remaining **empirical** gaps are source-specific: missing YeaG amount-response/normalization/uncertainty and discrepant K426A/strain labels; uncalibrated Cas2 acquisition frequencies/limits, residual activity and independent clone identities; and absent correspondence to a supplied target. Those gaps prevent fully populated published totals, which is why the complete synthetic example is labeled separately. The present arithmetic check cannot establish biological calibration, reader implementation, W05 wiring, user acceptance or axis completion.

### Boundary conventions checked in revision 003

A measured zero compared with a positive amount yields `C_j=0` if that amount difference is an applicable unintended mismatch. Two zero amounts give an undefined ratio and cannot establish comparable positive exposure; retain `zero_denominator` or a justified inapplicability statement. Censored “zero” measurements retain their detection bounds. Intended depletion remains excluded from `C`.

The composite-endpoint sum explicitly uses point contributions before calculating a joint group enclosure. The bounded necessity transform saturates at 1 for a sufficiently opposing effect and at 0 for a measured effect meeting the stated minimum. These boundaries were checked with exact rational arithmetic. They do not change the printed synthetic positive or resolved negative example.
