# A110 — current numerical sheet for biochemical and pathway consistency

This is one consolidated scoring-sheet proposal. It carries measured chemistry,
resource budgets and conservation calculations through to a signed contribution
for a particular candidate chemical account. The equations below retain the
numerical meanings of `a110_chemical_sheet_016`; the previously separate full
isotope measurement operator is now included. No old record is superseded by
editing it. The companion [worked examples](WORKED_EXAMPLES_026.md),
[exact reader crosswalk](READER_CROSSWALK_026.md), and
[source/criterion assessment](SOURCE_AND_ASSESSMENT_026.md) belong to this sheet.

The deliverable goal is sevenfold: actual numerical cells; every operation to
the candidate contribution; contrasting published cells and complete example
chains; dependence/contradiction/nondetection handling; truthful source coverage;
targeted population fields; and printable formulas and unresolved choices.
Publication counts, installed readers and biological calibration are different
questions. The parent owns completion accounting and presentation to the user.

A110 asks whether the specified chemistry, atom sources, and resources fit the
proposed role. Direct molecular activity belongs to A105, perturbation to A106,
partner identification/coexpression to A107. A109 stays removed. A110 remains separate. No production
scorer, reader, prompt, library, annotation, scientific job or completion state
is changed here.

## The numerical sheet to populate

Each row belongs to an explicit physical question in a specified reaction or
pathway account. A possible function can emerge from supplied sequence, selected
file contents or snippets; no initial annotation or public name is required.
The following cell names are the outputs populated by the separate readers.

| Cell | Inputs and operation | Unit/range | What the number evaluates |
|---|---|---|---|
| `measurement.q_read` | Reported calibrated amount/rate, or the declared instrument calibration in Eq. 1 | Actual amount/rate/response unit | Native measured quantity before the chosen nuisance correction |
| `correction.b_comp` | Sum of measured response slopes times condition differences, Eq. 2 | Same unit as the corrected quantity | Bias due to differences other than the intended test variable |
| `correction.b_iso`, `recovery`, `intended_fraction`, `other_response` | Actual blanks, recovery standards and mixture measurements | Quantity unit; recovery >0; fraction in (0,1] | Isolation of the intended chemical contribution from the measured readout |
| `measurement.q_corrected`, `measurement.y` | Eq. 2, followed by ratio/net change/fraction normalization in Eq. 3 | Stated molar ratio or fraction | Corrected chemical quantity and its actual denominator |
| `prediction.mu` | Stoichiometric readout mapping or isotope convolution, Eqs. 3–4, for candidate and every named alternative | Identical unit and measurement window as y | What each account predicts for this experiment |
| `constraint.residuals`, `e_claim`, `e_alternative` | Per-experiment squared errors, Eq. 5 | Squared y units; fraction-vector errors in [0,2] | Absolute disagreement, retained even when the relative score is favorable |
| `constraint.s_pair`, `s_question` | Signed contrast and minimum over declared alternatives, Eq. 6 | [−1,1] | Relative consistency of the candidate versus the declared alternatives |
| `budget.z`, `f`, `s_supply` | Measured usable supplies/capacities and requested demand, Eqs. 7–8 | Output amount/rate; [0,1]; [−1,1] | Maximum feasible output and fraction of that demand supportable |
| `balance.R`, `P`, `residual`, `d`, `D` | Cancel identical species, count atoms/charge/electrons, Eq. 9 | Equivalents/turnover; normalized deficits [0,1] | Conservation defect of the written chemical account |
| `compilation.S`, `C`, `bounds` | Fixed physical-question weights and conservation deficit, Eq. 10 | [−1,1] | Explicit A110 contribution for the candidate account, with its missing-domain bounds |

These cells are numbers with defined operands. Source names, condition text,
observation identity and subject correspondence support the cells; they are not
additional quality scores. Every output preserves its inputs, original units,
experimental unit, uncertainty kind, source origin and conditional assumptions.
The numerical conventions are proposals, not probabilities or adopted policy.

## 1. Measurement and separate comparability/isolation operations

**Eq. 1 — calibration, only if the input has not already been calibrated.** A
reported amount/rate can enter directly with the reported method and uncertainty.
For a documented linear calibration `t = alpha*q + gamma`, with alpha>0:

    q_read = dilution_factor * (t − gamma) / alpha / normalizer.

Here t is the integrated instrument response, or `area/area_internal_standard`
when that is the response the calibration was fitted to. `normalizer=1` gives an
amount; wet mass in mg gives amount/mg. The calibration's amount and response
units, standard amounts, internal-standard amount, integration windows, dilution
and normalizer must be supplied. A fit is not inferred from a cited calibration
range. An already normalized reported quantity is not divided a second time.
Other established calibrations carry their explicit forward/inverse equations;
without one, raw area remains raw area, not a fabricated mole quantity.

**Eq. 2 — established linear mixture, not a universal assay assumption.** Define
q_ref as the intended quantity in the reference condition, q_other as the
corresponding amount/response from the other contributor, and q_read in the
calibrated readout unit:

    b_comp = sum_l beta_l * (x_test,l − x_reference,l)
    q_read = r * [lambda * (q_ref + b_comp)
                  + (1−lambda) * q_other] + b_iso
    q_ref = [(q_read−b_iso)/r − (1−lambda)*q_other]/lambda − b_comp.

`beta_l` is measured response per unit of condition x_l; r>0 is measured recovery;
0<lambda<=1 is the measured signal-contributing fraction on the stated mixture
basis; b_iso is additive interference/background in q_read units. Preserve each
correction separately and propagate its measured domain. lambda is not a
homology/transfer confidence. If the physical mixture has no dilution-average
interpretation, its own established measurement equation must be provided;
Eq. 2 is not silently imposed.

Comparability subtracts effects of condition differences. Isolation separates
contributors to the readout. They enter numerically at different places in Eq. 2,
not as two categorical grades or two extra observations. Unknown slopes,
background, mixture fractions or recovery remain unknown. Exact invariant
stoichiometry can explicitly omit a condition variable that cannot change the
predicted ratio; that does not prove readout recovery is invariant.

## 2. Corrected quantities and predictions

**Eq. 3 — ratios and net readouts.** Correct numerator N and denominator H in
their own units before calculating `y=N_corrected/H_corrected`, with H_corrected>0.
Keep `formed_per_consumed`, `formed_per_supplied`, and `net_signal_per_supplied`
distinct. A rate uses its actual time denominator. A concentration is not a flux.
For a net spectroscopic quantity use the documented linear combination, e.g.
`N = n_NADPH_formed − n_NADH_consumed`, before division. Predictions must pass
through the same measurement operator. In particular, a supplied-substrate
denominator predicts the ideal consumed-substrate ratio only conditional on the
declared extent of consumption. Missing consumption is not repaired by a precise
reported supplied amount.

Stoichiometric prediction coefficients are on one declared turnover basis.
Keep reaction direction, all required reporting/coupling reactions, and
alternative identities explicit. Do not compare rates with amounts or NADPH
formation with net NAD(P)H signal. If the alternative has no numerical prediction
on the measured scale, that required comparison has the unknown range [−1,1].

**Eq. 4 — full isotope measurement operator.** For independent experiment i and
the declared same windows j=0,...,J, let B_ij and L_ij be corrected nonnegative
baseline and labeled amounts. All totals below must be positive. j=0 is the
unlabeled monoisotopic window; each subsequent window is a +2 mass-unit shift in
the retained UbiUV operator. Other window/adduct mappings require their own
declared operator.

    b_ij = B_ij / sum_j B_ij
    y_ij = L_ij / sum_j L_ij
    f_mk = choose(m,k) * p_pool^k * (1−p_pool)^(m−k), k=0,...,m
    u_mij = sum_{k=0}^{min(m,j)} f_mk * b_i,j−k
    mu_mij = u_mij / sum_{j=0}^J u_mij.

This is the baseline-convolution model for m independent donor oxygen draws.
It explicitly assumes that baseline mass shifts combine additively with donor
label shifts, with the modeled responses/exchange already corrected. Use the
same finite window for observed and predicted normalization; do not insert zeros
for unmeasured bins. `f_mk` is a label-count prediction, not a measured product
fraction, and generally is not `mu_mij` because the latter includes the baseline.

`p_supplied = A_label/(A_label+A_unlabeled)` is the measured supplied-precursor
fraction only under the stated area/response correction. `p_pool` is the actual
donor-pool fraction. These are separate cells. If an independently established
two-pool mixing model applies, `p_pool=t*p_supplied+(1−t)*p_background` uses a
measured mixing fraction t; absent t or exchange information gives a missing
pool parameter, not equality of the two p values. At endpoints p=0 or 1 use the
binomial limit, avoiding ambiguous 0^0 in software.

For the restricted first-two-bin diagnostic only, this operator yields
`mu_ratio(m)=B_1/B_0 + m*p_pool/(1−p_pool)` for p_pool<1. Its observed quantity is
`L_1/L_0`. It is an additional representation of the same isotope experiment,
with no extra weight. It cannot substitute for the declared full-pattern row.
At p_pool=1 the ratio is undefined when the denominator vanishes; no epsilon is
inserted. The full vector can still be evaluable.

## 3. Measurement error, replication and signed components

**Eq. 5 — one error per independent experimental unit.**

    Scalar: e_h = (1/n) sum_i (y_i − mu_hi)^2.
    Vector: e_h = (1/n) sum_i sum_j (y_ij − mu_hij)^2.

h identifies the candidate or one alternative. For scalar summary data with a
common constant prediction, a known mean ybar, sample SD s_y and known independent
n give exactly `e_h=(ybar−mu_h)^2+(n−1)*s_y^2/n`. A known single measured unit may
use its direct residual; a source mean with unknown n/SD cannot be treated as
that single unit with no variation. Its central calculation is conditional.

Fractions are a single vector per experiment. Bins, injections, time points and
figures are not independent experiments. Technical repeats may yield the
declared per-experiment response mean, with covariance/uncertainty, but do not
increase n. Never average raw errors of different units or different question
dimensions. Their separate signed components enter Eq. 10.

**Eq. 6 — retained signed comparison.**

    s_c,a = (e_a−e_c)/(e_a+e_c); s_c,a=0 if both errors are zero.
    s_question = min_{a in declared alternatives} s_c,a.

The alternative minimum is over the fixed named set; all pairwise errors and
contrasts stay in the sheet. Repeated alternatives do not change the minimum.
No declared alternative means an unpopulated comparison, not automatic positive
support. Equal wrong predictions have equal errors and score zero. A positive
contrast can favor a poor fit over a worse fit; absolute residuals are compulsory
companions. There is no probability, significance or absolute reliability claim.

## 4. Material, capacity and energy budgets

**Eq. 7 — same-period resource coverage.** For a simple fixed reaction, measured
usable resource U_i and positive consumption a_i per product give:

    z = min_{i:a_i>0} U_i/a_i
    f = min(1,z/v_star), v_star>0
    s_supply = 2*f − 1.

Use amount/amount for a batch and rate/rate for a steady-state budget. U includes
the declared compartment access, competing consumption and time basis. A supplied
reagent budget can be evaluated as such, without calling it consumed substrate
or native intracellular capacity. Regenerated cofactors are represented by
regeneration reactions/capacities, not charged once per catalytic turnover as
irreversible consumption. A genomic hit cannot populate a flux bound.

**Eq. 8 — explicit network generalization.** For finite reactions j, exchanges,
shared resources and chosen output coordinate t:

    z = maximize v_t
    subject to S_internal * v = accumulation,
               l_j <= v_j <= u_j,
               G*v <= h,
               v_t >= 0.

Every matrix entry, unit, bound, exchange, alternative route and regeneration
reaction is part of the input. S is molar stoichiometry; v, l, u and accumulation
have compatible rate units. `G*v<=h` carries actual shared constraints so a
resource cannot be spent on two routes at once. The example file gives a small
network with an analytic optimum and a matching feasible solution.

A feasible model with known zero attainable production has z=0. An infeasible
model instead returns conflicting constraints and an unknown biological capacity;
it is not converted into zero. An unbounded model with missing capacity limits
does not establish measured sufficiency: report unbounded model z and missing
empirical coverage [0,1]. Zero/negative v_star is invalid for a positive-demand
question; absent demand is unknown. Retain these statuses separately.

When uncertainty affects budgets, compute f bounds over the declared joint
parameter domain. For independent nonnegative box bounds in the simple model,
`z_L=min_i U_i,L/a_i,U` and `z_U=min_i U_i,U/a_i,L`, requiring positive a lower
bounds; `f_L=min(1,z_L/v_star,U)` and `f_U=min(1,z_U/v_star,L)` require positive
demand lower bound. Otherwise retain the full physical [0,1] bound or solve the
specified joint domain. For measured network uncertainty, each feasible scenario
has its own optimum; do not combine incompatible favorable capacities.

An energy constraint enters only with its actual energy source, direction,
concentrations and turnover basis. For available E>0 and cost g>0 per ATP with
requested n_ATP>0, `f_energy=min(1,E/(n_ATP*g))`; transform by the same 2f−1.
An author scenario is not a measured energy budget. If energy already constrains
Eq. 8, it is not scored a second time as another weighted resource question.

The scale 2f−1 is a proposed continuous convention. Coverage one-half maps to
zero by that convention, not by a biological threshold. No surplus bonus exists.

## 5. Conservation of the written account

**Eq. 9.** Use negative signed rational coefficients nu_i for reactants and
positive for products. Species identity includes formula, protonation, charge
and compartment. Cancel identical species on both sides before normalization.
If unchanged symbolic molecular skeletons cancel algebraically, show that
cancellation; do not infer missing chemical identities from a desired balance.

    R_l = sum_{nu_i<0} abs(nu_i)*n_il
    P_l = sum_{nu_i>0} nu_i*n_il
    residual_l = P_l−R_l
    d_l = abs(residual_l)/max(R_l,P_l), or 0 when both are 0
    residual_Q = sum_i nu_i*q_i
    d_Q = abs(residual_Q)/sum_i abs(nu_i*q_i), or 0 for zero denominator
    d_e = abs(E_donated−E_accepted)/max(E_donated,E_accepted), or 0 if both 0
    D = max(all declared d_l, d_Q, d_e).

Atom residuals are mol atoms/turnover; charge and electron residuals are mol
elementary-charge equivalents/turnover. d and D are unitless. Exact equation
balance is exact algebra, not a measured flux residual or a tolerance test.
Unknown formula/charge/electron terms leave D unknown in [0,1], unless known
defects supply a justified lower bound. An open half-reaction may balance with
explicit electrons while the full catalytic net remains unidentified; it does
not fill the complete-net D. A non-redox account explicitly has E_d=E_a=0.
All declared atom types must be evaluated, including elements outside C/H/O.

Balanced chemistry D=0 gives no extra positive observation. For an identical
specified reaction the conservation law is transferable; identity of enzymes,
cofactor preferences and physiological deployment is not implied by that law.

## 6. Candidate contribution and every missing-data branch

**Eq. 10 — current proposal, unchanged in meaning.** Freeze the finite physical
question set and its weights w_g>=0, sum_g w_g=1 for the specific chemical scope.
The displayed default uses equal weights for distinct prespecified questions;
a question block may have a declared internal split. Diagnostic duplicates have
zero additional weight. Native measurements do not choose these weights.

    S = sum_g w_g*s_g
    C_A110 = (1−D)*S − D.

s_g is Eq. 6 for a chemical comparison or Eq. 7/8 for a resource question.
Nested weights multiply: a reaction block of weight 1/3 with two half-weight
directions gives 1/6 to each direction. Positive and negative contributions can
cancel; retain the separate cells. Scope and weights cannot be changed merely
to hide an unmeasured or contradictory question.

For each quantity preserve reported SD/SE/CI/range, plot-extraction interval,
calibration domain, model domain, or unknown uncertainty separately. A confidence
level is recorded only when actually reported/defined. This sheet's interval
operations enclose allowed values; they do not turn SD into a confidence interval.
For a declared joint domain, evaluate the formulas over that domain. With only
bounded scalars Y=[yL,yU] and prediction M=[mL,mU], conservative error bounds are:

    e_L = max(0,yL−mU,mL−yU)^2
    e_U = max(abs(yL−mU),abs(yU−mL))^2.

For vectors sum these bounds over j, then average over i; simplex-vector e_U may
be capped at 2. Marginal boxes are conservative when inputs share parameters.
For nonnegative isotope convolution, ordinary interval sums/products and positive
denominator division give enclosures; if a normalizing denominator can vanish,
report the valid-domain qualification and use [0,1] for individual fractions.
For a binomial term k at bounded p, its extrema are at the domain endpoints and,
for its maximum, p=k/m if in the domain. For m=0 the sole probability is 1.
These supply deterministic finite bounds without a fitted statistical model.

For error intervals C=[cL,cU] and A=[aL,aU]:

    s_L=(aL−cU)/(aL+cU) if denominator>0, otherwise 0
    s_U=(aU−cL)/(aU+cL) if denominator>0, otherwise 0.

Thus exact zero errors for both accounts give [0,0]; one exactly zero error
against another possibly positive error gives [0,1] or [−1,0]. No epsilon is
introduced. Shared-parameter joint bounds can be tighter. All-unconstrained
comparison errors use [−1,1]. For alternatives with bounds [L_a,U_a], a valid
enclosure of their minimum is `[min_a L_a,min_a U_a]`.

Missing s_g retains its original weight and [−1,1] unless actual evidence narrows
that domain. A question with no observations does not receive zero. With
`S_L=sum w_g L_g`, `S_U=sum w_g U_g`, and D in [D_L,D_U]:

    C_L=(1−D_U)*S_L−D_U
    C_U=(1−D_L)*S_U−D_L.

This follows because C increases with S and decreases with D on the stated
domain. Conditional nominal C is stored separately from these bounds. A positive
reference-system point does not fill the supplied target's unknown chemistry or
resources. When reference-to-target correspondence cannot determine the target
observable/prediction, that target question remains unknown with its weight;
the populated reference sheet is retained separately. No blanket transfer grade
is introduced and correspondence is not restricted to sequence homology.

## 7. Dependence, contradiction, nondetection and complements

| Situation | Numerical action |
|---|---|
| Same experiment reappears as figure/table/database/citation | Keep one observation identity, one set of residuals and one weight; equality of numbers alone is not identity |
| Technical repeats | Populate one experiment's response and technical uncertainty under its declared averaging design; do not add biological n |
| Independent repeats of the same question | Include every corrected unit in Eq. 5; no publication-count multiplier |
| Contradictory matched units | Retain their errors/variance; the two-unit example y=[0,1], c=1,a=0 gives e_c=e_a=1/2 and s=0 |
| Conditions differ | Use separately declared questions or measured b_comp; an unknown correction cannot be replaced by pooling |
| Complementary endpoints/directions | Fixed separate physical-question weights; no claim they are independent probabilities |
| Nondetection with calibrated nonnegative amount bound LOD | Use [0,LOD] and propagate; carry background/censoring method. An unshown bar or “not detected” without a quantified limit remains unknown |
| Same observation contributes to A105/A106/A107 | Retain shared-observation references and A110's different chemical role; do not fabricate independent credit. W05 must consume that dependency |
| Supplied-resource diagnostic derived from a scored stoichiometric endpoint | Show its arithmetic, with zero additional weight; it is not a new native-resource experiment |
| Missing complement | Name the particular missing measurable operand. No mandatory experiment sequence or investigation stop follows |

For NfnAB, measured recovery, residual substrate and an independent chemical
quantification would constrain the readout model. For UbiUV, complete per-culture
isotopologue amounts and donor-pool enrichment would constrain the isotope model;
identification/measurement of an electron sink and its capacity would constrain
the complete redox/resource account. These are specific limitations and possible
measurements, not scores made from the words “weak” or “strong.”

The explicit choices for the user's judgment are Eq. 6's contrast and alternative
minimum, the physical-question weights, 2f−1, and Eq. 10's conservation penalty.
All are fully defined but unadopted. Missing published values, production
implementation and empirical calibration remain distinct from undefined algebra.

### Additive domain clarification from final review

Signed scalar net changes remain signed after background correction; they are
not clamped to zero before residual comparison. The isotope operator instead
requires physical nonnegative amount vectors. A negative corrected bin is
retained as an observed processing outcome with its uncertainty and a structured
invalid-domain/missing-conversion result; it is not silently set to zero. A
documented censoring or measurement model can supply an admissible physical
domain. The exact Eq. 4 baseline operator requires every intervening index
j=0,...,J. A noncontiguous reported panel does not populate the omitted bins.
