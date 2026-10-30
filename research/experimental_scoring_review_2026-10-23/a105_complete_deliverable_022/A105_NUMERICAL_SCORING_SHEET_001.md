# A105 — current numerical scoring sheet and populated deliverable

2026-10-23. This is the single entry point for the consolidated A105 proposal.
It produces **one A105 contribution for one persistent candidate annotation**
whose actual molecular assertions are declared. Its complete synthetic example
produces **0.616595042762**. All inputs, corrections, numerical components,
source combinations and candidate combinations are specified below.

This is a numerical-sheet research deliverable. The recommendation is explicit;
the user's answer to the source-pooling choice is still absent. No policy is
claimed as approved, no production reader or scorer is implemented, and neither
A105 nor the ten-axis goal is marked complete. Earlier records remain intact.

The seven-criterion assessment is at the end. Exact arithmetic and coverage are
in [ARITHMETIC_RESULTS_001.json](ARITHMETIC_RESULTS_001.json) and
[AUTHORITY_AND_COVERAGE_001.md](AUTHORITY_AND_COVERAGE_001.md).

## The user's three separate parts

1. **Investigation prompt:** the existing discovery task starts from supplied
   sequence, selected file contents or snippets. It investigates conversion,
   transport and binding, including evidence on corresponding molecules.
   Functions may emerge; an initial annotation or searchable name is not needed.
   No prompt is created or changed here. The detailed TASK and terse STEERING
   remain separate, as specified in the authority documents.
2. **Numerical scoring sheet:** the populated tables and equations below define
   measurable inputs, their numerical combinations and the candidate contribution.
3. **Targeted readers/graders:** the final field crosswalk identifies the precise
   cells each future reader populates. Those functions are **UNIMPLEMENTED**.
   They populate this sheet; they do not create an overall relevance grade or
   insert the sheet wholesale into a prompt.

A105 measures molecular activity/binding and the correspondence of that evidence
to the supplied target. Perturbation/restoration belongs to A106. A binding result
is not a conversion result; growth is not a measured transport rate.

## Numerical scope and origin labels

The sheet has source-assay rows, source-to-target relationship rows, one current
row per molecular statement, and one candidate result. A statement specifies
the endpoint, direction, comparison/boundary, target material span, molecular
state and conditions. A candidate's revisions retain its identity; alternative
candidate functions retain separate identities and scores.

| Label used here | Meaning |
|---|---|
| Reported | A published measurement or limit, as retained in the earlier inspected conversion |
| Graph-derived | A numerical extraction from a figure, not original instrument data |
| Derived | Arithmetic on identified numerical operands |
| Proposed | A scoring transformation, weight or combination convention |
| Synthetic | Invented measurement/model inputs solely for a numerical example |

The completed synthetic chain uses two compatible asserted statements about
invented target T at reference condition C: **T performs reaction A**, and
**T's activity on A exceeds its activity on B**. Neither statement requires a
separate binding experiment. Both are explicitly part of this example's candidate;
the conjunction is not an assay checklist imposed on every annotation.

The activity branch uses the existing source-assay correction and an uncalibrated
numerical correspondence. The specificity branch uses the existing calibrated
common-target mapping. No complete joint observation model spans both branches;
their final combination therefore has conventional score semantics.

## 1. Populated activity sheet: experimental measurement and reliability

Every input in this section is **synthetic**. Rates are micromolar/minute;
protein concentration is micromolar. The rate denominator therefore becomes
amount of assayed molecule, giving activity in min⁻¹. The actual scored endpoint
is attributed formation of the stated product at the source reference condition.

Let q be sample minus blank, g the measured contaminating contribution, k
calibration recovery, E assayed molecule concentration, and u/v the measured
same-endpoint response in test/reference conditions outside the intended contrast:

\[
q=s-b,\qquad h=u/v,\qquad
a=\frac{q-g}{kEh}=\frac{(q-g)v}{kEu}.
\]

| Exact numerical cell | Input or calculation | Populated value | What the number evaluates |
|---|---|---:|---|
| `sample_rate` | Synthetic measured sample | 1.20 µM/min | Preparation signal |
| `blank_rate` | Synthetic matched blank | 0.20 µM/min | Blank contribution |
| `net_rate` q | 1.20−0.20 | 1.00 µM/min | Preparation signal after blank |
| `contaminant_rate` g | Separately quantified synthetic contributor | 0.15 µM/min | Effect isolation: signal due to another contributor |
| `attributed_rate` | q−g | 0.85 µM/min | Signal assigned to the assayed molecule |
| `recovery` k | Measured/reference calibration response | 1.00 | Quantitative calibration |
| `protein_amount` E | Synthetic concentration | 1.00 µM | Rate normalization denominator |
| `condition_test_rate` u | Same-endpoint condition-control measurement | 2.00 µM/min | Condition response numerator |
| `condition_reference_rate` v | Its reference-condition counterpart | 1.60 µM/min | Condition response denominator |
| `condition_response` h | 2.00/1.60 | 1.25 | Experimental comparability outside the deliberately tested variable |
| `corrected_activity` a | 0.85/(1×1×1.25) | **0.680000000000 min⁻¹** | Attributed, normalized, condition-corrected source activity |

Comparability and isolation are separate inputs and separate calculations.
The intended difference under investigation is not a comparability penalty.
The displayed attributed fraction 0.85 and inverse response 0.80 are not applied
again as score multipliers after correcting a and its uncertainty.

The measurement boundary supplies q and its uncertainty directly. The separate
sample/blank variances are not supplied or invented. An alternative reader can
derive `variance_q = variance_sample + variance_blank − 2 covariance_sample_blank`
from actual traces, then populate this same summary boundary.

The full primitive order is (q,g,k,E,u,v). Its covariance is explicitly diagonal
in this synthetic example, with diagonal (.04,.0225,.0025,.01,.01,.01) in the
corresponding products of units. The derivative is

\[
J=\left(\frac{v}{kEu},-\frac{v}{kEu},-\frac a k,-\frac a E,
        -\frac a u,\frac a v\right)
=(.8,-.8,-.68,-.68,-.34,.425).
\]

| Uncertainty cell | Standard uncertainty of native operand | Propagation | Contribution to activity variance, min⁻² |
|---|---:|---|---:|
| `variance_measurement` | q: .20 µM/min | (.8×.20)² | .02560000 |
| `variance_isolation` | g: .15 µM/min | (−.8×.15)² | .01440000 |
| `variance_recovery` | k: .05 | (−.68×.05)² | .00115600 |
| `variance_amount` | E: .10 µM | (−.68×.10)² | .00462400 |
| `variance_comparability` | u,v: .10 µM/min each | (−.34×.10)²+(.425×.10)² | .00296225 |
| `distinct_residual_variance` | Supplied corrected-scale residual | .09−.0275 | .06250000 |
| `effect_variance` V | JΣJᵀ + distinct residual | Sum above | **.111242250000** |
| `effect_standard_uncertainty` | √V | √.11124225 | **.333529983660 min⁻¹** |
| `effect_precision` | 1/V | 4,000,000/444,969 | **8.989390272131 min²** |

The residual subtraction is the existing constructed fixture: .0275 is stipulated
already represented within a .09 residual estimate. It is not a universal
variance estimator or a license to subtract the complete propagated measurement
variance from every between-preparation spread. No preparation count is invented.
For actual observations use the supported variance-component model and add only
the distinct component once. Unknown covariance is not independence.

For this explicitly known-normal, nonnegative-presence example,

\[
S=\frac{\max(0,a)^2}{2V}=\frac{924800}{444969}=2.078347030917,
\qquad B=\tanh(S/2)=\mathbf{.777561486079}.
\]

S is a difference of best fitted log likelihoods; B is its proposed bounded
normalization. They are not the probability of function or physiological activity.
The signed measured a remains visible even if negative; a negative measurement
does not create positive presence support by being squared.

## 2. Populated activity sheet: separate numerical target correspondence

The following native operands are **synthetic** and their transformations are
**proposed conventions**. Each family has weight 1. Target correspondence is
not restricted to sequence similarity; the applicable families are specified
for the particular relationship. These five families are not five new axes or
five independent experiments.

| Exact numerical cell | Native operands and denominator | Calculation | Value |
|---|---|---|---:|
| `r_sequence` | Pair raw score 240; source/target self scores 300,320 | 2×240/(300+320) | .774193548387 |
| `r_structure` | Source/target-normalized TM scores .90,.85 | min(.90,.85) | .850000000000 |
| `r_site` | 8 exact matches; 10 predefined sites, all observed | 8/10 | .800000000000 |
| `r_evolution` | 85 supporting placements in 100 eligible tree replicates | 85/100 | .850000000000 |
| `system_distance_squared` | Δ=(7 °C,.5 pH); scale Σc=diag(100 °C²,1 pH²) | 49/100+.25/1 | .740000000000 |
| `r_system` | Same measured descriptor differences and proposed scale | exp(−.74/2) | .690734330637 |
| `relationship_index` R | Five declared numerical family weights, each 1 | Σ(wj rj)/Σwj | **.792985575805** |
| `observed_weight_fraction` | All declared family weight observed | 5/5 | 1; diagnostic only |
| `target_signed_index` D | Source B, multiplied once by R | .777561486079×.792985575805 | **.616595042762** |

The raw sequence normalization requires the retained compatible local scoring
conditions: nonnegative pair score, nonpositive gap penalties, positive self
scores, and substitution score s(a,b)≤[s(a,a)+s(b,b)]/2. Each residue is used at
most once. Arbitrary HMM bits/E-values do not fill these cells. The identity
alternative, when that is the actual sequence measurement, is
`identical_aligned_residues / max(known_source_span,known_target_span)`; it is a
different declared basis for that same family, not another factor. Snippet
correspondence never establishes whole-protein coverage.

Site counts need a predefined functional set; a changed residue is not thereby
proven nonfunctional. Phylogenetic support needs a fixed placement statement and
eligible replicate denominator; it is not function probability. The descriptor
scale is a proposed similarity scale, not measurement-error covariance or enzyme
response calibration. Here source-assay condition calibration and source-to-target
descriptor correspondence concern different relationships, as stipulated in the
retained fixture. If they use the same correction, do not score it again in R.

Multiple methods within one family share that family's fixed weight. Correlated
sequence, structure, site and tree outputs do not yield independent-proof bonuses
or a √5 uncertainty reduction. Where an actual response mapping exists, transform
the effect and uncertainty through it; do not apply its observations again as R.

For observed families O and missing relevant families M, with declared total
weight W, the exact full-family identification bounds are

\[
R_L=\frac{\sum_O w_jr_j}{W},\qquad
R_U=\frac{\sum_O w_jr_j+\sum_M w_j}{W}.
\]

The observed-family conditional point is ΣO(wr)/ΣO w and carries its actual basis.
It does not fill the missing full-family result. With evolution missing here,
the conditional R=.778731969756 and D=.605511987661, while full-family
R∈[.622985575805,.822985575805], D∈[.484409590129,.639921887345]. The full point is
null. These are identification bounds, not confidence intervals; a negative B
reverses the multiplication endpoints before ordering them.

For m matches among k observed of n declared functional sites, the full-site
fraction lies in [m/n,(m+n−k)/n]. No observed family means R is unknown in [0,1],
not a fabricated default. With no external target correspondence, source S/B
still survive. Exact molecular identity and matching scope can establish the
identity relationship without requiring five unrelated measurements.

## 3. Populated specificity sheet: calibrated effects and shared uncertainty

Every input below is **synthetic**, retained from the complete calibrated record.
The target comparison is θT=ln(aA,T/aB,T) at 30 °C, pH 7, substrates separately
assayed at 1 mM, molecular state M0. Source molecules G1/G2/G3 are not co-mingled.
Their assay conditions are respectively (25 °C,7), (30 °C,6.8), (35 °C,7.4).
Each rate is normalized per amount of the assayed source molecule, in min⁻¹.

Let y=ln(net rate A/net rate B), c be the measured log condition-response ratio,
and d=−ln(fA/fB), where fA/fB are separately measured attribution fractions of
their respective net rates. Thus y−d is the attributable log ratio. The
calibrated target-minus-source mapping is Xβ at the same reference state:

\[
z=y-c-d+X\beta,\quad
X=\begin{pmatrix}1&-1\\1&0\\1&1\end{pmatrix},\quad
\beta=(.15,.05)^T.
\]

| Cell | G1 | G2 | G3 | Meaning/origin |
|---|---:|---:|---:|---|
| `net_rate_A` | 2.459603111157 | 1.822118800391 | 2.585709659316 | Synthetic positive rate |
| `net_rate_B` | 1 | 1 | 1 | Rate denominator |
| `log_ratio_y` | .90 | .60 | .95 | ln(A/B), derived |
| `variance_y` | .04 | .09 | .16 | Supplied known log-summary variance |
| `condition_ratio_source` | 1.105170918076 | 1.051271096376 | 1.221402758160 | Attributed A/B control in source conditions |
| `condition_ratio_reference` | 1 | 1 | 1 | Same control at reference; not the main B-rate denominator |
| `log_condition_ratio_c` | .10 | .05 | .20 | Log of preceding source/reference ratio |
| `variance_c` | .01 | .01 | .04 | Condition-control uncertainty |
| `fraction_A` | .723869934429 | .814353676232 | .713422068376 | Intended-molecule contribution/net A rate |
| `fraction_B` | .80 | .90 | .75 | Intended-molecule contribution/net B rate |
| `negative_log_fraction_ratio_d` | .10 | .10 | .05 | −ln(fA/fB) |
| `variance_d` | .01 | .04 | .01 | Attribution-control uncertainty |
| `target_minus_source_x` | −1 | 0 | 1 | Exact synthetic descriptor 2−[3,2,1] |
| `source_corrected_contrast` | .70 | .45 | .70 | y−c−d |
| `response_mean` | .10 | .15 | .20 | Xβ |
| `mapped_target_contrast_z` | **.80** | **.60** | **.90** | Same target contrast, with different errors |

The 17 primitive entries, in order, are y[3], c[3], d[3], β[2], source
residuals[3], target residual[1], family residuals[2]. Residual means are zero.
The fixture supplies the following full covariance: block diagonal with the
listed blocks and **zero cross-block covariance as an explicit synthetic
assumption**, not a rule for real data. Each block's units are squared log ratio.

| Primitive block | Covariance | Loading into z |
|---|---|---|
| Assay y | diag(.04,.09,.16) | I |
| Comparability c | diag(.01,.01,.04) | −I |
| Isolation d | diag(.01,.04,.01) | −I |
| Response β | [[.020,.005],[.005,.020]] | X |
| Source mapping residual | .04 I3 | I; same source keeps its residual across preparations |
| Target mapping residual | [.06] | [1,1,1]ᵀ; common to every source mapping to T |
| Family mapping residual | .04 I2 | LF=[[1,0],[1,0],[0,1]]; supplied ownership, not a variance inferred from family names |

With J=[I,−I,−I,X,I,1,LF], **C=JΣJᵀ**. The coefficient contribution is
[[.030,.015,0],[.015,.020,.025],[0,.025,.050]]. The family contribution is
[[.04,.04,0],[.04,.04,0],[0,0,.04]], and the target contribution is .06 in every
entry. Hence

\[
C=\begin{pmatrix}.230&.115&.060\\.115&.300&.085\\.060&.085&.400\end{pmatrix}.
\]

No block or error source is added twice. Actual overlapping controls, fits,
denominators or uncertain predictors need their real cross-covariances. The
synthetic external calibration reuses none of the assay/control observations.
Its supplied coefficients are not a claimed empirical fit: original training
data, empirical replicate counts and estimated-covariance degrees of freedom
are not invented. Those absences do not leave this conditional fixture's
mathematics unspecified.

| Exact derived cell | Calculation | Populated value |
|---|---|---:|
| `precision_P` | 1ᵀC⁻¹1 | 6.431627794853 |
| `weights` | C⁻¹1/P | [.477136431784,.261244377811,.261619190405] |
| `target_effect` θ̂ | wᵀz | .773913043478 |
| `target_variance` | 1/P | .155481634183 |
| `target_standard_uncertainty` | √(1/P) | .394311595294 |
| `disagreement_Q` | (z−θ̂1)ᵀC⁻¹(z−θ̂1) | .217391304348 |
| `Q_degrees_of_freedom` | n−1 conditional on known C | 2; diagnostic only |
| `theta_plus`, `theta_minus` | max(0,θ̂), min(0,θ̂) | .773913043478, 0 |
| `Q_plus`, `Q_minus` | Same joint quadratic at those fits | .217391304348, 4.069559452781 |
| `target_profile_log_ratio` | (Qminus−Qplus)/2=θ̂ abs(θ̂)/(2V) | **1.926084074217** |
| `specificity_signed_index` | tanh(S/2) | **.745630704507** |

Q describes inconsistency; it is not another penalty or acceptance threshold.
The mapping already accounts for target correspondence, so the activity branch's
R is not multiplied into this specificity result. Binding parameters and transport
rates require their own effect equations; this rate-ratio model does not relabel
IC50 as Kd or occupancy as transport.

## 4. Same statement, several sources: current recommended proposal

First reconcile actual observation identities and fit each source's current
joint observations, including controls, repeats and contradictions. This produces
one current signed D per coherent source-to-target relationship. Several papers
about the same observation do not produce several D values.

For a **nonempty received roster** of uncalibrated relationships addressing the
same target statement and condition scope, the current recommendation is

\[
P=\max(0,\max_i D_i),\quad N=\max(0,\max_i[-D_i]),\quad
D_{\rm statement}=P-N.
\]

This explicitly measures strongest received support minus strongest received
opposition. Coefficients are 1; there is no roster denominator, historical maximum
or hidden allocation table. It is a conventional evidence balance, not a
dependence-adjusted likelihood. Weaker corroborating homologs remain in the sheet
without increasing this index. It neither estimates search-selection bias nor
claims the unseen literature contains no opposition.

The alternative whose effect must remain visible is fixed-allocation accumulation:

\[
K=\tanh\!\left[\sum_i a_i\operatorname{atanh}(D_i)\right],\quad a_i\ge0.
\]

Its numerical allocations are explicit policy inputs. The comparison below
uses **ai=1**; the allocation is not inferred from source names, ancestry or
covariance. Fixed coefficients retain zero-append neutrality. For the same
two contrary source indexes, allocations (.5,.5) instead give .340233352999.
If no allocation is supplied, accumulation has an undefined *policy input*,
not permission to choose a favorable coefficient. The recommended P−N route
needs no such input. The question of choosing between them is still unanswered.

All values below are **synthetic**. D+=.8 tanh(4/2)=.771222064061;
Dweak=.4 tanh(2/2)=.304637662382. The negative source uses −Dweak for the same
ordered contrast, not an unrelated condition or a zero-filled nondetection.

| Current received source indexes | Recommended P−N | Unit-allocation K |
|---|---:|---:|
| D+ alone | .771222064061 | .771222064061 |
| D+, Dweak | .771222064061 | .871181484985 |
| D+, −Dweak | **.466584401678** | **.609869037957** |
| Ten distinct D+ rows, −Dweak | .466584401678 | .999999995150 |
| D+, −D+ | 0 | 0 |
| D+, an exactly zero-correspondence append | .771222064061 | .771222064061 |

A new independent assay **within** a source changes its fit. For observations
2,2 with known independent variances 1,1, S=4. A third actual independent 2
gives S=6; at R=.8 its D rises from .771222064061 to .796043802949. Reprinting
the first two assays does not cause that increase. A correction that reduces a
source D to .20 replaces its earlier .771222 result: together with −.304637662382,
the current P−N is −.104637662382. Earlier snapshots remain historical.

An included unresolved source is not dropped. For Di∈[li,ui], P−N is
coordinatewise nondecreasing, so evaluating at every lower endpoint and then
every upper endpoint gives its tight image bounds for a rectangular set.
With D+ and one unresolved Di∈[−1,1], these are [−.228777935939,1]. Coupled
constraints remain coupled; box results are labeled outer bounds. An empty
entire roster has null point and [−1,1] bounds. An empty *opposition subset*
within a nonempty roster gives N=0, meaning no received opposition.

The calibrated route fits one common target effect using its actual mapping and
joint covariance, as in section 3. Its likelihood is not multiplied by conventional
R×B indexes as if they were independent likelihoods. A proposed cross-route
merger would have to state its own conventional meaning; none is needed by this
worked candidate, whose different routes concern different required statements.
A genuinely unresolved mixed-route same-statement result retains the received
rows and allowed bounds rather than silently discarding contrary evidence.

## 5. Candidate-level contribution and its exact populated instance

The candidate's actual molecular meaning supplies positive required/sufficient
relations. Let G contain the canonical statement sets, each of which is a
genuinely sufficient way for this same molecular assertion to hold. The
recommended conventional reduction is

\[
D_{A105}=\max_{g\in G}\min_{j\in g}D_j,\qquad
c_{A105}=\max(0,D_{A105}).
\]

Required claims use minimum; genuinely sufficient alternatives within the same
assertion use maximum. Competing candidate annotations are not OR branches simply
because investigation is undecided. Repeated assays of one statement belong in
its source/statement calculation, not in this formula as alternative claims.
Resolve proven synonyms, duplicate clauses and absorption, e.g. A OR (A AND B)=A.
Do not infer biological equivalence from similar names or equal numbers.

| Populated candidate cell | Exact value or calculation |
|---|---|
| `candidate_identity` | One invented candidate T; retained through evidence revisions |
| `asserted_statement_activity` | T performs reaction A at C; conventional source-to-target route |
| `asserted_statement_specificity` | T's A rate exceeds its B rate at C; calibrated log-ratio route |
| `candidate_formula` | Activity AND specificity; one sufficient clause containing both |
| `activity_current_sources` | One complete source D=.616595042762; P=.616595042762, N=0 |
| `activity_statement_index` | **.616595042762** |
| `specificity_statement_index` | **.745630704507** |
| `candidate_signed_index` | min(.616595042762,.745630704507)=**.616595042762** |
| `A105_coordinate` | max(0,.616595042762)=**.616595042762** |
| `candidate_profile_log_ratio` | Null: this min/max combination is not a joint likelihood |
| `essential_statement_coverage` | 2/2 complete numerical statement inputs; descriptive, not a multiplier |
| `identification_bounds` | [.616595042762,.616595042762] given the specified inputs; not a confidence interval |
| `sampling_uncertainty` | The source/model uncertainties above remain; no calibrated interval for this conventional candidate score is invented |
| `origin/status` | Complete conditional synthetic arithmetic under the stated proposed conventions; not a biological target score |

The native activity, source S/B, relevance components, calibrated specificity
and their qualifications remain alongside this scalar. One candidate produces
one coordinate; revisions are not additional candidates. This does not compute
the other nine coordinates, a full hypervolume, investigation progress, timing
credit or an episode stopping decision. W05 owns production credit consumption.

For intervals, use the same monotone formula at the lower and upper endpoints,
then the positive part. Missing required input in [−1,1] with another required
index .84 gives a null coordinate with [0,.84] bounds. A required −.2 plus an
unknown requirement identifies c=0 while signed bounds remain [−1,−.2]. If
evolution is missing in this example, full candidate bounds are
**[.484409590129,.639921887345]**, point null; the specificity result does not
turn missing activity correspondence into a completed measurement.

Where an actual joint observation model spans the candidate's assertion, define
the assertion and complement as parameter regions and calculate
`SF = sup_F log L − sup_notF log L`, then tanh(SF/2), before positive projection.
For known multivariate normal y,C this is half the difference of constrained
quadratic minima. It is not the sum of independently optimized marginal scores.
For y=(2,3), C=I, both directions required give S=2 and B=.761594155956;
either direction sufficient gives S=6.5 and B=.996997635487. The conventional
maximum of marginal B values is .978026114739, a different calculation.

## 6. Exact numerical routes for other assay designs

The measurement design and statement select the route. The largest available
score never selects it. Each unknown input stays null with its reason and allowed
range; unaffected native cells remain usable.

| Route and exact cells | Calculation and denominator | Uncertainty and missing-data rule |
|---|---|---|
| Signed difference: `rate_A`, `rate_B`, `difference_boundary`, joint 2×2 covariance | e=A−B−boundary, same rate unit | Ve=VA+VB−2CovAB; explicit zero boundary only for an equality comparison |
| Positive rate preference: `rate_A`, `rate_B`, `required_ratio` | e=ln(A/B)−ln(required_ratio) | Derivative [1/A,−1/B]; use full covariance; no logs of nondetections/nonpositive noisy readings |
| Affinity preference: `Kd_A`, `Kd_B`, `required_affinity_ratio`, joint fit covariance | e=ln(KdB/KdA)−ln(required ratio); lower KdA means positive preference | Preserve same concentration units, fit model and qualifier; IC50 cannot fill Kd without an actual binding model |
| Occupancy difference: `free_ligand_A/B`, `Kd_A/B`, boundary, full covariance | LA/(KdA+LA)−LB/(KdB+LB)−boundary | One-site equilibrium model only; total ligand is not automatically free ligand |
| Michaelis-Menten response: `substrate_source`, `substrate_reference`, `Km`, joint covariance | h=[Ss/(Km+Ss)]/[Sr/(Km+Sr)] | Same applicable molecule/preparation/model; shared Km propagated once; not a quality score |
| Known-normal signed contrast: `contrast_estimate`, `known_variance`>0 | S=e abs(e)/(2V); B=tanh(S/2) | Signed contrast versus the other direction, boundary already subtracted |
| Known-normal nonnegative presence: `observed_corrected_activity`, `known_variance`>0 | S=max(0,a)²/(2V) | Physical activity constrained nonnegative; negative measurement retained |
| Paired normal, unknown variance: `independent_pair_count` n>1, `mean_paired_difference` d, `sample_sd_paired_difference` s>0 | t=d/(s/√n); S=sign(d)(n/2)ln[1+t²/(n−1)] | Actual independent pairs; not an arbitrary t, Welch statistic, p-value or unidentified error bar |
| Known-normal common effect: `contrast_estimates` z, full known positive-definite `contrast_covariance` C | P=1ᵀC⁻¹1, e=(1ᵀC⁻¹z)/P, V=1/P, signed-normal S | Keep Q=(z−e1)ᵀC⁻¹(z−e1); no automatic extra penalty |
| Detected and censored normal observations: detected `value,known_variance`; censored `lower_limit,upper_limit,known_sd`; parameter domain | Joint log densities plus ln[Φ((upper−a)/sd)−Φ((lower−a)/sd)]; maximize in declared hypothesis regions | This factorization requires actual independence; correlated censoring requires its joint model. Missing threshold/noise does not yield a likelihood |
| Joint normal compound statement: `observed_contrasts`, full C, numerical inequality coefficients/boundaries and physical parameter domain | Q=(y−θ)ᵀC⁻¹(y−θ); S=[min_notF Q−min_F Q]/2 | Preserve shared original observations/nuisances; an unmeasured required endpoint is unknown, not a fictitious observed equal fit |

For two independent normal groups with unknown separate variances, the exact
fields are `group_A.count/mean/sample_sd` and the same for B. Set
vg=(ng−1)sg²/ng. Then

\[
\ell_{free}=-\tfrac12\sum_g n_g\ln v_g,\quad
\ell_{equal}(\mu)=-\tfrac12\sum_g n_g\ln[v_g+(\bar y_g-\mu)^2],\quad
S=\operatorname{sign}(\bar y_A-\bar y_B)
 [\ell_{free}-\max_\mu\ell_{equal}(\mu)].
\]

Find the global maximum by evaluating endpoints and all real stationary roots
between the observed means, using the cubic
`nA(μ−meanA)[vB+(μ−meanB)²]+nB(μ−meanB)[vA+(μ−meanA)²]=0`.
The midpoint is not generally the maximizer. Unknown error-bar meaning does not
populate sample SD; unknown dependence does not establish independent groups.

Nonlinear derivative propagation is an approximation unless the model is linear.
Use its actual joint distribution/fit where needed. Estimated-covariance,
clustered or bootstrap data retain their supported uncertainty model; no
infinite empirical degrees of freedom are assumed. Singular/invalid covariance,
zero sample spread and unidentified nuisance parameters return a specific
unavailable result rather than jitter, invented errors or an infinite score.
This sheet does not promise one universal observation model for every experiment.

## 7. Shared evidence, complementary experiments and missing operands

| Situation | Numerical treatment |
|---|---|
| Same physical measurement in a paper, figure and dataset | One canonical observation before fitting; aliases retain source custody |
| Equal values from distinct measurements | Values alone establish neither identity nor independence |
| Technical repetitions/time points | Model their actual repeated-measure structure; do not count them as independent preparations |
| Independent preparations of one source | Joint source fit; shared calibration/source mapping error remains shared |
| Shared control, denominator or calibration | One primitive observation and actual covariance; separate labels do not remove dependence |
| Contradictory observations of the same statement | Refit the current joint source/target model, then recompute D; preserve Q and signed opposition |
| Contradictory uncalibrated source relationships | Current P−N proposal; opposition enters before final positive projection |
| Complementary assays | Repair a named limitation in the measurement/model or supply a distinct asserted endpoint; not automatic independent replication |
| Nondetection | Measured censoring limit plus observation model; never substitute zero or a pseudocount |
| Different state, endpoint or conditions | Separate scope unless a supported mapping connects them; no automatic contradiction |
| Unknown native operand | Keep null and its allowed numerical set; propagate the image to dependent outputs |
| Complete arithmetic but unadopted convention | Return explicitly conditional proposed result; no missing experimental value is invented |

For the earlier known-normal signed contrast with variance .11124225, two
independent observations .68 and −.68 fit mean 0 and B=0 while disagreement
remains. A duplicate representation of the single .68 observation leaves
its variance and B unchanged. In the existing detected-plus-censored fixture,
.68 with that variance plus an independent nondetection below .10 with sd .20
and a≥0 fits a=.147958504, S=.271726302, B=.135033321; the nondetection is not
an observed zero. These are retained synthetic consequences, not new biology.

If S is known but R is missing in [0,1], D has bounds
[min(0,B),max(0,B)]. If a required signed source/statement calculation is
unavailable with no tighter information, its allowed index is [−1,1]; a
nonnegative-presence B has [0,1]. Do not discard known constraints. No-data,
measured zero, opposition, conditional result and invalid input remain distinct.
Bounds here describe possible completions, not an implicit uniform prior.

## 8. Filled published-case cells and source-to-component trace

These numerical rows reuse the earlier source conversions documented in the
read cross-case sheets. This worker inspected **no new primary paper or
paper-specific packet**. The table gives the retained inspection references;
it does not convert inherited coverage into a fresh primary-source claim.
Rounded graph numbers retain their precision. Real native measurement gaps
remain explicit; the fully populated chain above remains synthetic.

| Published case and inspected source location | Filled cells, origin and checked arithmetic | Component and exact limit | Retained conversion/inspection reference |
|---|---|---|---|
| CsiD; DOI 10.1038/s41467-018-07563-6; Supplementary Fig. 5 and electrode Methods | Graph-derived oxygen rates ≈.16062,.10484 µmol/min; `rate_difference`≈.05578 µmol/min from the rounded inputs | Preparation oxygen-rate contrast; not isolated product formation. This table does not supply raw trace covariance or the missing attribution/target relationship. Source S and target D are not manufactured from the difference alone | [CSID_NUMERICAL_CELLS_003.md](../a105_sheet_construction_001/CSID_NUMERICAL_CELLS_003.md) |
| BtsT; DOI 10.1128/JB.00599-17; whole-cell kinetic figure and Methods | Reported `Km`=16.5 µM. For the explicitly declared 10/40 µM scenario, saturations 10/26.5=.377358490566 and 40/56.5=.707964601770; `condition_response`=.533018867925 | A measured kinetic parameter supplies a nonlinear same-system condition correction. Scenario concentrations are not relabeled reported observations. Vmax cancels only under this same applicable curve. No transfer to a different vesicle preparation; covariance/uncertainty absent here remains unknown | [BTST_NUMERICAL_CELLS_001.md](../a105_sheet_construction_001/BTST_NUMERICAL_CELLS_001.md) |
| IscR 2013; DOI 10.1038/nsmb.2568; competition tables and Methods | Reported IC50 32 nM and >510 nM. For less-favored/favored IC50: `native_ratio`>510/32=15.9375; `log_native_ratio`>2.768674822919 | Point/limit selectivity bound, not Kd or a confidence bound. The 32 nM point's missing sampling uncertainty cannot be silently fixed to zero. No numerical likelihood follows without its censor/error model | [ISCR_NUMERICAL_CELLS_001.md](../a105_sheet_construction_001/ISCR_NUMERICAL_CELLS_001.md) |
| IscR 2025; DOI 10.1111/mmi.70021; binding/state Methods and Fig. 4 | Reported apparent Kd 22 nM versus >1000 nM; ratio >45.454545454545. Reported 26 nM after air then anaerobic treatment compared with 22 nM gives 26/22=1.181818181818 | Actual state at measurement qualifies binding interpretation; preparation names alone do not establish state. This row supplies a point/limit ratio and a separate state contrast, not independent likelihoods or evidence of activation | [ISCR_STATE_QUALIFICATION_002.md](../a105_sheet_construction_001/ISCR_STATE_QUALIFICATION_002.md) |
| FolE2; DOI 10.1128/JB.00287-09; retained metal/kinetic comparisons | Reported/normalized metal-condition relative activity .14; separate derived substrate response .279114219 retained as a different comparison | Protocol/condition comparability. The denominators and models belong to different protocols; **do not multiply .14×.279114219** as though a common response was measured. No new combined score is asserted | [FOLE2_NUMERICAL_CELLS_004.md](../a105_sheet_construction_001/FOLE2_NUMERICAL_CELLS_004.md) |
| TriA/AtzA; DOI 10.1128/JB.183.8.2405-2410.2001; retained sequence and substrate-activity comparison | Reported 466/475 identical residues → `r_identity`=.981052631579 for the stated spans. TriA aminoatrazine activity 17 versus atrazine limit .01 nmol/min/mg → point/limit preference >1700 | Global correspondence and reaction-specific selectivity are distinct numbers. High identity does not override the measured selectivity. Missing native uncertainty/calibration means no fabricated target S/D; the activity limit is not a measured zero | [TRIA_NUMERICAL_CELLS_005.md](../a105_sheet_construction_001/TRIA_NUMERICAL_CELLS_005.md) |

The CsiD retained conversion also has a conditional two-group profile result,
but the rounded two rates above alone do not reproduce its sample-size/spread
inputs. That conditional S is therefore not pasted into an apparently complete
native row. The source's full calculation remains in its cited conversion.
Likewise, the FolE2 separate response is carried as an already derived value,
not claimed as newly recomputed or supplied with an invented denominator.

This gives contrasting reaction, transport and binding examples using the same
sheet meanings, with explicit numeric cells and dependent unknowns. It does not
claim a fully observed published source-to-novel-target candidate chain.

## 9. Targeted UNIMPLEMENTED readers: exact field crosswalk

The fields below are the mathematical contract for future population; they
are not existing runtime IO. Literal numbers, counts, units and defined
calculations fill the sheet. Source text/identities constrain meaning but are
not numeric grades. Literature extraction and dataset analysis must populate
the same cells and preserve `reported/graph_derived/derived/proposed/synthetic`
origin, source location and original observation identity for every value.

| Targeted population responsibility, all UNIMPLEMENTED | Exact cells supplied | Deterministic receiving calculation/output |
|---|---|---|
| Assay/trace reader | `sample_rate`, `blank_rate`, `net_rate`, their units, `variance_net_rate`; alternatively sample/blank variance and covariance | q=s−b; Vq=Vs+Vb−2Covsb; preserves preparation versus product endpoint |
| Attribution-control reader | `contaminant_rate`, its uncertainty; or rate-specific `fraction_A`, `fraction_B` and joint covariance | g subtraction in activity; d=−ln(fA/fB) in calibrated log-ratio route |
| Calibration/amount reader | `recovery`, `protein_amount`, units, joint covariance with reused measurements | k,E denominator and derivatives |
| Condition-control reader | `condition_test_rate`, `condition_reference_rate`, joint covariance; or `condition_ratio_source`, `condition_ratio_reference`, log-summary covariance | h=u/v or c=ln(source/reference); intended variable excluded |
| Error/replication assembler | Ordered `primitive_names`, `primitive_values`, `primitive_units`, complete `primitive_covariance`, `distinct_residual_variance`, actual independent-unit IDs and covariance estimation status | JΣJᵀ plus distinct residual; outputs each named variance contribution and cross terms, V, standard uncertainty and precision |
| Statistical route population | **The exact route-specific numerical cells in section 6**, with hypotheses/boundaries, independence/known-variance status and missing reason | Corrected effect; joint fitted effect/variance; S; B; model diagnostics. No generic unspecified `measurement_model_inputs` replaces these cells |
| Native sequence comparison reader | `pair_raw_score`, `source_self_raw_score`, `target_self_raw_score`, same scoring configuration; or `identical_aligned_residues`, known compared spans | Defined sequence normalization under its supported conditions |
| Structural comparison reader | `tm_source`, `tm_target`, normalization spans and actual comparison | rstructure=min(TMsource,TMtarget) |
| Functional-site mapping reader | `site_matches`, `sites_observed`, `sites_declared`, predefined set/mapping | Full-site fraction or its exact missing-site bounds |
| Placement reader | `placement_support_count`, `placement_replicate_count`, fixed supported event/alternative | Count fraction, preserving actual denominator |
| System-descriptor reader | `descriptor_differences`, their units, `reference_scale_covariance`, scale origin | Squared distance and exp(−distance/2); not an enzyme response |
| Numerical correspondence assembler | `applicable_families`, fixed `family_weights`, each component value/bounds, actual observed basis | Ravailable, observed-weight fraction, Rfull bounds, D=RB and its ordered bounds |
| Calibrated response reader/analysis | `prediction_design_X`, `coefficient_values_beta`, `coefficient_covariance`, calibration endpoint/state/domain/data-reuse meaning; residual owners, means, loadings and covariance | z=y−c−d+Xβ; complete 17-variable assembly in the worked example; C=JΣJᵀ; GLS/S/B from section 3. Exact existing proposed paths are in the [calibrated contract](../a105_calibrated_contract_007/CALIBRATED_FIELD_CONTRACT_001.md) |
| Current same-statement assembler | `statement_definition`, `current_source_indexes`/bounds, current fit references, original observation identities, `pooling_convention` | P,N,Dstatement under recommended P−N; alternative additionally requires explicit `allocation_coefficients` or allowed set |
| Candidate meaning/identity population | `candidate_identity`, `semantic_revision`, target material/scope, canonical statements, proven aliases, required/sufficient relations, separate alternative-candidate IDs | Exact positive AND/OR meaning; canonical sufficient sets with duplicate/absorbed clauses removed; no score-driven meaning selection |
| Candidate numerical reducer | Current `statement_signed_indexes`/bounds with route, missingness and shared-evidence references; declared formula | DA105=max min D; c=max(0,DA105); profile S null for conventional route; coordinate/bounds and explicit status |
| Availability/provenance retention | `value_origin`, `source_location`, original measurement/control/fit identity, `missing_cells`, `allowed_set`, `bound_kind`, `calculation_basis`, immutable input snapshot | Keeps reported facts, calculations, choices and synthetic values distinct; no extra numerical credit |

For a full candidate joint-normal route, additional exact cells are ordered
`observed_contrasts`, `known_covariance`, each statement's inequality coefficient
vector/boundary/unit, physical parameter-domain inequalities, native observation
identities, and any linear transform with its native covariance. These populate
the constrained quadratic calculation in section 5, not a generic unnamed model.

The point/bound status vocabulary distinguishes complete conventional point,
complete joint-profile point, conditional only, interval only, identified
projection with missing input, no data, semantic input missing and representation
conflict. Status names are not scores. Unknown native sampling uncertainty and
identification bounds are distinct cells.

## 10. Current choices and seven-criterion assessment

| Explicit current proposal | Consequence shown here | Remaining judgment |
|---|---|---|
| Source S and B=tanh(S/2) | Native magnitude/uncertainty retained; bounded best-fit contrast | Proposed normalization, not empirical function probability |
| Equal-weight native correspondence mean | R=.792985575805; D=.616595042762 | Numerical family/normalization choices. Earlier shifted harmonic alternative with .1 offset gives R=.788899482632, D=.613417854083 |
| Full point only when its operands identify it; conditional observed-basis point shown separately | Missing evolution gives full candidate bounds [.484409590129,.639921887345] | Whether a later consumer elects conditional points; no silent full-point imputation |
| Strongest received positive minus strongest received negative | .466584401678 versus .609869037957 under unit accumulation | **User's pooling answer remains unanswered**; no acceptance inferred |
| Weakest required statement/strongest sufficient branch | Candidate conjunction .616595042762 | Explicit conventional candidate meaning; joint model used where actually supplied |
| Positive part once at candidate output | c=.616595042762; opposition kept in signed cells | Negative severity is not represented below zero in the single support coordinate |

The current proposal corrects measured comparability/isolation and propagates
their uncertainty once. No undefined extra reliability penalty is needed to
calculate it. Adding a new penalty would require a distinct evaluated quantity
and new numerical definition; an unanswered earlier question does not add it.

| Active goal criterion | Evidence in this deliverable | Exact remaining issue |
|---|---|---|
| 1. Numerical cells, inputs, units, denominators, calculations, uncertainty, missingness | Sections 1–3 and 6–9 give exact operands, derivatives, covariance, point/limit/bound meanings and complete synthetic inputs | No essential undefined calculation in the declared supported routes. Actual missing native operands remain null with defined ranges, not an open-ended research quota |
| 2. Explicit component combination; separate comparability/isolation; no intuitive relevance grade | a=(q−g)v/(kEu), JΣJᵀ, source S/B, five measured R components, calibrated z/C, current P−N, candidate min/max and positive projection | Policy election is explicit and pending; the formulas themselves are defined |
| 3. Contrasting published filled examples with checked arithmetic and origin separation | Section 8 has reaction, transport and binding cells; sections 1–5 have the complete synthetic chain; arithmetic receipt recomputes the consolidated chain and supported source arithmetic | Published examples retain real unmeasured uncertainty/attribution/correspondence. No fully measured published-to-novel-target chain is claimed or required to invent a number |
| 4. Shared evidence, replication, contradiction, nondetection | Sections 3–7 give original-identity deduplication, actual covariance, current fit replacement, opposition before clipping and censored likelihood | No unknown covariance or source allocation is inferred from a label. A future different observation model needs its actual operands; this is explicit availability handling |
| 5. Components traced to inspected sources | Section 8 gives DOI/source location and exact retained conversion reference; coverage record distinguishes earlier source inspection from this mathematical integration | No fresh primary-paper coverage claimed by this worker |
| 6. Exact reader/grader fields; separate three responsibilities | Section 9 binds the numerical equations to exact cells and named targeted population responsibilities | Reader implementation remains UNIMPLEMENTED and outside this numerical-sheet goal; it is not an undefined arithmetic gap |
| 7. Formulas/examples/choices printed for judgment and feedback incorporated | This document and the print-ready handoff give the complete current chain and policy alternatives; known corrections on scope, relevance, missingness, current fits and candidate identity are incorporated | Parent must present/review the handoff and incorporate any actual new feedback. The pooling choice is still unanswered; no worker completion mark substitutes for user judgment |

**No essential undefined arithmetic was found in the stated current proposal's
complete source→statement→candidate chains.** A requested extension outside
those stated routes is not silently represented as an already computed result.
In particular, a mixed calibrated/uncalibrated calculation for the *same*
statement without a chosen merger has received rows and bounds, not a fabricated
joint likelihood; the example's actual different-statement combination is
fully defined. Missing native measurements and explicit unadopted scoring
choices are reported separately from undefined calculations.

The new bounded verification passed **28 arithmetic checks**: reconstructing
activity correction/variance, reconstructing the calibrated covariance from all
17 primitives, joining the two statement outputs, checking the current pooling
and missing-input propagation, and checking the listed source-derived arithmetic.
No historical sensitivity grid was rerun. No production tests, current-target
annotation, native program or HPC job ran. Goal/axis completion is left to the
parent's review of these actual deliverables.

## 11. Additive final consolidation: mixed input and criterion 7

This section corrects the first draft's finite omission in section 4, which
said a same-statement mixture of calibrated and uncalibrated evidence would
need a separately stated merger. **The complete current proposal supplies that
merger here.** It also clarifies the completion wording in section 10: criterion
7 expressly permits unresolved choices printed for judgment. A reply or
production-policy adoption is not an additional mathematical completion criterion.

When an applicable complete joint target model spans all received observations
for a statement, use its joint fit. Otherwise preserve each supported, complete
calibrated joint block as **one** current index B, and each remaining current
uncalibrated relationship as one D=RB. Apply the same **proposed conventional
P−N** rule to these completed index rows:

\[
\mathcal I=\{B_{\text{complete calibrated block}}\}
             \cup\{D_{\text{remaining uncalibrated relationship}}\},\quad
D_{\text{statement}}=\max(0,\max\mathcal I)
                       -\max(0,\max[-\mathcal I]).
\]

This is an explicit extension of the current recommendation's conventional
meaning. It does not multiply likelihoods, add independent-proof credit, or
back-convert a mixed result into a profile log likelihood. It does not change a
calibrated block's internal joint fit. The resulting statement index has
`index_kind=conventional_target_index` and `profile_log_ratio=null`.

Block membership follows the supported model and declared endpoint, not whichever
partition yields the largest score. An original observation already in a joint
block is not separately appended as another row. Canonical duplicate
representations collapse before fitting. Competing fits of the same observation
are alternative allowed calculations or a representation conflict, not extra
positive/negative evidence. Shared known errors within a joint block remain in
its covariance. If two distinct surviving rows share target or other information,
their dependence remains recorded; this conventional maximum-based balance
makes no independence or calibrated-uncertainty claim. A newly measured control
that changes a block's fit updates that block first.

If the supported block membership itself is unresolved, retain the allowed
assignments and take the image of the formula over that set; no favorable
assignment or midpoint is selected. Missing numeric row inputs use the same
monotone interval calculation already specified in section 4. The exact new
fields are `statement_index_rows[].index_kind`, `.current_model_block`,
`.original_observation_members`, `.signed_index`/`.allowed_set`,
`model_block_membership`/`allowed_memberships`, and `shared_information_refs`.
The statement assembler populates P,N,D and the bounds; it is UNIMPLEMENTED.

A separate fully numerical **synthetic** example stipulates that the calibrated
specificity block B=.745630704507 and a distinct uncalibrated source
D=−.4 tanh(1)=−.304637662382 concern the same target A/B statement and state.
They share no original assay observation in this example. Then

\[
P=.745630704507,\quad N=.304637662382,\quad
D_{\text{statement}}=\mathbf{.440993042125}.
\]

No new source measurement is asserted by that compatibility stipulation. Its
single new arithmetic check is in
[MIXED_STATEMENT_ARITHMETIC_002.json](MIXED_STATEMENT_ARITHMETIC_002.json).
The earlier 28 checks remain preserved, giving **29 bounded arithmetic checks
across the two receipts**. The complete primary candidate is unchanged at
**.616595042762**; this additional example closes the otherwise unspecified
same-statement connection without inventing a likelihood.

**Final seven-criterion assessment:** criteria 1–6 are supplied by this research
sheet, including this additive connection. Criterion 7 is satisfied when the
parent prints the provided formulas/examples/unresolved choices for judgment;
the print-ready handoff is supplied with this deliverable. Known user feedback
is incorporated. An unanswered choice remains unanswered, but is not by itself
a failure of criterion 7 or a reason to invent further research work. No
essential undefined numerical operation remains in the current recommended
proposal. Actual unmeasured native operands have explicit missing/bound results;
every recommended scoring convention remains labeled proposed. This is an
assessment of the numerical research deliverable, not a worker action marking
the axis/goal complete or adopting production policy.
