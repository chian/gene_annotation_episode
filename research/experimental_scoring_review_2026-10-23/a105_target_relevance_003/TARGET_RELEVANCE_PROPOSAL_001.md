# A105 numerical sheet proposal: connect the actual assayed molecule to the target

2026-10-23. New, unadopted sheet proposal. This is the source-to-target part of A105, not a new evidence axis, overall applicability grade, investigation prompt or populating reader. It consumes the measured molecular-activity result and its experimental uncertainty from the source assay. It does not redesign A101/A102/A104 or implement W05. The two source packets in this directory must be read individually with their required authority resets; the source synthesis here introduces no additional paper evidence.

## What the output means

The output is a numerical prediction of a DECLARED molecular quantity on the annotation target, conditional on the actual source finding and the measured correspondence. It includes separate corrections for known changes and numerical uncertainty for what the correspondence fails to determine. The corrections multiply the activity estimate; their logarithms add. Distinct uncertainties and covariances combine explicitly. A native sequence score, a structural distance, a phylogenetic distance and a measured response ratio retain different meanings.

For example, “the target/source reaction-rate ratio at these two metal recipes is 0.14” is a quantitative system relationship. “Sequence identity is 0.981” is an alignment measurement. The latter is not already a reaction-rate ratio or a probability that a function transfers. Both can enter this sheet, but through the calculations actually supported for them.

The common output port is:

```
target_parameter = h(source_parameter, measured_or_fitted_bridge_operands)
target_covariance = J * joint_input_covariance * J_transpose
                    + residual_correspondence_covariance
```

`J` is the Jacobian of h with respect to ALL source and bridge operands. A joint likelihood replaces first-order propagation where that approximation is poor. The sheet exposes every contribution to the mean and variance. Its final numerical evidence comparison is made on the target parameter ONCE, after this combination; a second overall relevance multiplier would count the correspondence again.

This proposes an explicit quantitative answer for how components come together. It does not claim that the available papers supply every target-specific operand. Known source activity with unknown target correspondence remains a numerical source result and an unknown target result, not a zero score or a default “same molecule.”

## Define the subject and endpoint before entering numbers

The sheet's non-score definitions identify the supplied target material/span, completeness, source assayed molecule/construct, mixture composition, molecular state, source/reference conditions, intended target conditions, molecular endpoint and its numerator/denominator. A label or public accession is optional; sequence or selected file contents can define the target. A short snippet cannot establish complete molecule identity or full-length coverage. Full sequence equality alone does not establish equal modification, truncation, oligomeric state or accessible partners.

For a comparison, specify which changes are deliberate and which are nuisances. Protein identity can be the intended change; purity, substrate exposure and metal state can differ in addition. Experimental isolation has already quantified source activity attributable to the source molecule, where measured. Do not put the same contamination estimate into a second relevance penalty.

Scope determines the endpoint. A biochemical-capability statement under a stated assay condition does not require a measurement of native cellular metal availability. A statement about native flux does. Binding affinity does not quantify downstream activation. Perturbation/growth/rescue results are not imported as A105 activity measurements. An empirical functional correspondence can be referenced if relevant, while its original endpoint and axis remain explicit.

## Numerical cells and exact operands

Every numeric entry has value or bound, unit, uncertainty type, covariance links, and status `observed`, `derived`, `fitted`, `proposed_conversion`, or `synthetic`. `unknown`, `not_applicable` and a measured zero are distinct. These status fields are provenance, not scores. The list below supplies cells, not a compulsory list of modalities.

| Cell(s) | Numerical meaning and input | Calculation and use |
|---|---|---|
| `source.value`, `source.covariance` | Source activity, log specificity/affinity contrast, or fitted molecular parameter; physical units and a declared reference | Passed from source experimental reliability. No rereading/regrading of source quality here. |
| `sequence.native_score`, `sequence.score_unit` | Actual tool score, e.g. bit score; exact tool/model/scoring configuration | Entered directly as a calibrated predictor. Scores from different programs/configurations are not assumed exchangeable. |
| `sequence.identity_numerator`, `sequence.identity_denominator` | Identical and compared aligned residue counts | Their ratio is native sequence identity. It is not a functional probability. |
| `sequence.source_coverage`, `sequence.target_coverage` | Aligned residues divided by the corresponding known full sequence length | Conditions a fitted relationship on alignment extent. Unknown full length gives unknown full-length coverage; fragment coverage is separately labeled. |
| `structure.native_score`, `structure.aligned_count` | Original TM-score, DALI score, RMSD or other declared comparison and its matched atoms/residues | Retain normalization direction and compared region. Do not average incompatible native scores. |
| `structure.site_rmsd_A`, `structure.site_atom_count` | RMSD in Å across declared, mapped catalytic/binding-site atoms after the declared superposition | `sqrt(sum_i ||position_target_i-position_source_i||^2 / n)`. Site selection and missing atoms matter; global fold RMSD is not silently substituted. |
| `site.signed_feature_differences[]` | Target minus source values of measured molecular features with units: e.g. a resolved kinetic determinant's measured energetic contribution | Enter a fitted MEAN difference if quantitatively linked to the endpoint. A residue-name change alone supplies no invented energetic number. |
| `evolution.patristic_distance` | Sum of tree branch lengths between source and target, in substitutions/site, for the actual inferred tree | A possible predictor of residual functional difference. Tree uncertainty supplies repeated inferred distances/covariance, not “bootstrap support = functional probability.” |
| `system.reference_response`, `system.target_response` | Measured response of the appropriate molecule at source/reference and target conditions, on the SAME molecular denominator | `r_system=response_target/response_reference`; `d_system=log(r_system)` for positive responses. A calibrated joint response surface replaces separate factors where variables interact. |
| `empirical.source_endpoint`, `empirical.target_endpoint` | Paired molecular measurements on explicitly identified source and target under common or corrected conditions | Direct `r_molecule=a_target/a_source`, or corresponding difference/contrast. Shared data stay linked. No sequence or structure modality is required in addition. |
| `bridge.mean_component[j]` | A measured log response difference, or fitted term `beta_j*x_j` | Adds to a declared target-minus-source parameter difference. Its source, units and uncertainty are explicit. |
| `bridge.variance_component[j]` | Squared uncertainty of each independent bridge operand propagated onto the target scale | Adds to target variance, with covariance cross-terms retained separately. For fitted functional correspondence, residual prediction variance is distinct from fitted-mean uncertainty. |
| `bridge.joint_covariance` | Covariance among source result, response parameters, predictor estimates and calibration effects | Prevents repeated experiments, shared substrates/denominators and correlated modalities from behaving as independent evidence. |
| `target.value`, `target.covariance` | h output on the declared target endpoint | Actual numerical input to the contribution comparison. Raw measurements remain available beside it. |

Deterministic arithmetic can populate counts, fractions, response-curve evaluations, Jacobians, covariance propagation and fitted predictions once their operands exist. A targeted literature reader supplies those operands and their experimental definitions; a dataset calculation can supply the same fields. No generic grader invents the missing coefficients. Reader implementation is outside this proposal.

## Explicit sums and products for common molecular quantities

### Positive activity and same-endpoint response changes

For positive activity measured per declared molecule amount, let `a_s` be the source estimate at the reference state, and `r_j` be individually measured/predicted target/reference response ratios. If the joint model supports their factorization:

```
a_t = a_s * product_j(r_j)
z_s = log(a_s / a_unit)
d_j = log(r_j)
z_t = z_s + sum_j(d_j)
V_t = V_s + sum_j Var(d_j) + 2*sum_{i<j} Cov(input_i,input_j)
      + V_unexplained_bridge
```

`a_unit` is the fixed physical unit used to make the logarithm dimensionless; it is not a biological threshold. The covariance sum includes the source z_s and all d_j. Both the mean shift and its uncertainty matter. A known small response ratio need not weaken evidence for the narrow claim “some activity exists”; it changes the magnitude. It can substantially change a claim about specificity or rate at a given target condition.

The log expression is appropriate to positive multiplicative quantities. For noisy net rates compatible with zero, use the original-scale model. In the simple independent product `a_t=a_s*r`, exact variance for random inputs with finite second moments is:

```
Var(a_t) = mean(r)^2*Var(a_s) + mean(a_s)^2*Var(r)
           + Var(a_s)*Var(r)
```

The last product is absent from first-order delta propagation and matters with broad uncertainty. General dependence needs the actual joint moments or full likelihood. Unknown measurement uncertainty is never zero.

When h is fitted on a logarithmic scale, exponentiating the predicted log mean gives a geometric center/median under a lognormal model, not its arithmetic mean. Under an actual lognormal predictive distribution, the mean is `a_unit*exp(z_t+V_t/2)`. A sampling uncertainty interval for an estimated parameter and biological predictive variability are different objects; the sheet retains which one V_t represents.

### Specificity and affinities

For a declared A-versus-B comparison:

```
theta_s = log(aA_s/aB_s)
theta_t = theta_s + sum_j(dA_j - dB_j)
```

Identical common multiplicative corrections cancel exactly. `Var(dA-dB)=Var(dA)+Var(dB)-2Cov(dA,dB)`. Independent errors cannot be assumed from separate table columns. For affinity, choose and state direction, for example `theta=log(Kd_B/Kd_A)` so positive values mean stronger A binding. Neither EC50 nor an occupancy-only measurement is silently treated as Kd.

For activity above background, transfer the sample and background on their actual endpoints and THEN form the contrast. Multiplying a source net effect by one r is valid only if h establishes how each background contributor behaves. A mixed preparation is not fixed by a sequence match.

### Identity is a factual cancellation

If the source molecule and the target molecule AND relevant state are demonstrably the same, the molecular-transfer term is exactly zero on a difference scale: `d_molecule=0`. No molecular transfer variance is needed for that absent step. Actual remaining system/assay uncertainties still apply. This is not a default 1.0 grade, and unfamiliar names, incomplete sequences or merely matching an accession do not establish the relationship.

## A fully specified proposal for using native comparison measurements

This section supplies an actual quantitative mapping to fit; it does not assert that it has been empirically validated for A105. A paper's native comparison scores alone cannot identify the mapping's coefficients. The required calibration dataset is defined here, so missing fitted effects are identifiable work rather than the phrase “some calibration is needed.”

Collect source–target PAIRS with the same defined molecular endpoint measured on both subjects, calibrated or corrected to the same reference conditions. Let `y_k = theta_target,k - theta_source,k`. The pair includes actual assay error covariance, construct/state definitions, original comparison metrics, source/target ordering, biological family and shared-preparation/source identifiers. It must include discordant and nondetected cases; restricting to pairs already called the same function would bias the relationship. An unknown source-to-target mapping cannot be repaired by counts of papers.

For the positive, approximately normal contrast regime, propose:

```
y = X*beta + e_measurement + e_correspondence
V(beta,gamma) = V_measurement + diag(tau_k_squared)
tau_k_squared = exp(q_k^T * gamma)
```

`X` contains measured DIRECTIONAL descriptor differences and an intercept only when its source→target sampling meaning is justified. A symmetric distance by itself cannot determine which protein has the larger activity. The `q` predictors can include native bit score/coverage, mapped site RMSD, phylogenetic distance and relevant measured system descriptors. They quantify how much molecular divergence remains unpredicted by the mean model. Biological family dependence or repeated source molecules require off-diagonal covariance rather than this independent-pair diagonal illustration.

Fit beta and gamma by minimizing the explicit normal negative log likelihood, excluding the irrelevant constant:

```
objective(beta,gamma) = 0.5*log(det(V))
                       + 0.5*(y-X*beta)^T * inverse(V) * (y-X*beta)
beta_given_gamma = inverse(X^T*inverse(V)*X) * X^T*inverse(V)*y
```

The log-variance link makes variance nonnegative without clamping negative “excess variance.” A boundary with no resolved residual variance requires its uncertainty/profile, not a factual claim of exact zero. Full numerical rank is necessary for identified coefficient effects. Scores from collinear comparisons do not become separately identified biological contributions by writing more columns.

For a new source/target pair with measured `x*`, `q*`:

```
mean_difference = x*^T * beta
residual_variance = exp(q*^T * gamma)
variance_of_fitted_mean = x*^T * Cov(beta) * x*
```

Native metrics and their coefficients contribute explicit sums in the predictor and multiplicative factors in residual variance. These factors describe ONE joint empirical model; they are not independent pieces of experimental evidence. Input metric uncertainty is propagated through this fit (or resampled jointly). Uncertainty in gamma is also retained. A normal approximation for fitted gamma gives

```
E(residual_variance) ≈ exp(q*^T*gamma_hat + 0.5*q*^T*Cov(gamma_hat)*q*)
```

under that approximation. A joint likelihood/profile or parametric bootstrap is preferable when the approximation is poor. Resampling units are independent source/target assay blocks or biological groups, not table entries. Calibration results must show prediction errors on held-out source molecules/families as appropriate; the target's very assay cannot both train the relation and independently validate its transferred result.

Exact inputs still needed for a REAL fitted mapping: paired molecular measurements and limits; their calibration/background/normalization uncertainties; source/target material and state; pair direction; the measured native predictors and their configurations; shared-source/preparation covariance; supported biological/assay domain; and enough independent contrasts to identify fitted effects and assess their errors. Neither retained packet supplies this calibration dataset. The model can still be proposed and tested numerically without pretending otherwise.

For censoring, the observed likelihood is integrated over the actual nondetection region of the corresponding molecular measurement. Do not log zero or train only on detected positives. In a normal latent-contrast case with a VALID contrast bound L, a censored row contributes `Phi((L-X*beta)/sqrt(V_kk))`; correlated rows require the multivariate probability over their joint region. If L itself is derived from an uncertain source rate/denominator, its uncertainty belongs in the original joint assay model, not an exact manufactured contrast limit. Interval-censored observations use the difference of CDFs. If neither such a bound nor a complete assay observation model exists, the censored row remains uncomputed for that fit.

### Missing modalities do not create invented zeros

A direct measured functional response can supply h without sequence, structure or a tree. A calibrated structure-only model can supply h without a sequence score. One may fit a supported model using the actually available predictor subset, retaining the residual uncertainty for omitted predictors. Alternatively, an explicit joint model can integrate missing predictors conditional on observed predictors; it must also integrate their uncertainty. Replacing missing RMSD with 0 would claim an exact structural match and is invalid. Multiplying a measured response by zero because a phylogeny is unavailable is also invalid.

The model's modality set, domain and missing-data behavior are declared before evaluating a target. Selecting whichever fitted modality model yields the most favorable target score is not evidence combination. No universal minimum identity cutoff, mandatory structure determination, or mandatory timing/assay workflow is introduced.

## Worked synthetic fit: native scores predict correspondence error, not function probability

EVERY datum in this section is invented to check the proposed calculation. It is not TriA, FolE2, BtsT or ybhP evidence. The molecular endpoint is a source–target difference in `theta=log(rate_A/rate_B)` under matched conditions. The synthetic pairs use one fixed sequence-scoring setup and comparable lengths/coverage, and one fixed mapped functional-site atom set. Those held-constant conditions are required to interpret the two varied metrics.

Each row describes four independent synthetic pairs with observed differences `[-a,-a,+a,+a]`, and known per-pair assay measurement variance 0.01. Duplicate numeric values here are deliberately independent synthetic experiments; in real data, equality alone does not establish either identity or independence.

| Native bit score b | Site RMSD r, Å | a | ML variance of the four observed differences | Residual variance after the specified 0.01 assay variance |
|---:|---:|---:|---:|---:|
| 60 | 0 | 0.4123105626 | 0.17 | 0.16 |
| 120 | 0 | 0.2236067977 | 0.05 | 0.04 |
| 60 | 2 | 0.6082762530 | 0.37 | 0.36 |
| 120 | 2 | 0.3162277660 | 0.10 | 0.09 |

These are continuous predictor values at four experimental design points, not four grades. With `q_b=(b-90)/30` and `q_r=(r^2-2)/2`, fitting the stated likelihood gives:

```
mean_difference = beta0_hat = 0
Var(beta0_hat) = 1 / sum_k(1/V_kk) = 0.006479192419
log(tau_squared) = -2.1202635362 - 0.6931471806*q_b + 0.4054651081*q_r
tau_squared = 0.12 * exp(-0.6931471806*q_b) * exp(0.4054651081*q_r)
```

The coefficients follow the measured SYNTHETIC residual dispersions. The centering/scaling only reparameterizes raw b and r²; it does not assign a relevance tier. In native coordinates this same fit is `0.64*exp(-0.02310490602*b + 0.2027325541*r^2)`.

For a new synthetic comparison b = 90 bits and r = 1 Å:

| Compiled correspondence cell | Calculation | Value |
|---|---|---:|
| Sequence numerical factor in residual variance | exp(-0.6931471806 × 0) | 1.0000000000 |
| Site numerical factor in residual variance | exp(0.4054651081 × -0.5) | 0.8164965809 |
| Conditional residual variance | 0.12 × 1 × 0.8164965809 | 0.09797958971 |
| Variance of estimated log residual variance | q*ᵀ Cov(gamma) q* | 0.2051612236 |
| Residual variance averaged under stated normal coefficient approximation | 0.09797958971 × exp(0.2051612236/2) | 0.1085639935 |
| Fitted-mean uncertainty | Var(beta0_hat) | 0.006479192419 |
| Total predicted molecular-difference variance | 0.1085639935 + 0.006479192419 | 0.1150431859 |

The numerical factors multiply a VARIANCE. They are neither probabilities nor standalone function scores. The complete Hessian/covariance and synthetic data are in the arithmetic artifact. In this symmetric fixture the mean/variance coefficient covariance is zero; it cannot generally be dropped. Sixteen pairs are a calculation fixture, not a validated model or a proposed sample-size cutoff.

Now give the source assay a synthetic specificity ratio 4 with source log-contrast variance 0.04. Independently measured target-system responses are r_A = 0.6 and r_B = 1, and the standard uncertainty of their LOG RESPONSE DIFFERENCE is 0.05. Its variance is 0.0025. These are synthetic response data, not assumed physical effects of a named system.

```
target_specificity_ratio = 4 * exp(0) * 0.6/1 = 2.4
theta_target = log(4) + 0 + log(0.6) - log(1) = 0.8754687374
V_target = 0.04 + 0.1150431859 + 0.0025 = 0.1575431859
SE_target = 0.3969171020
theta_target / SE_target = 2.2056714939
```

The predicted target ratio is a geometric center, as noted above. The total error contains source experimental uncertainty, correspondence uncertainty learned from the quantitative metrics, and measured system-response uncertainty. Nothing was inferred from a missing modality, and sequence identity was never treated as functional probability.

## Numerical contribution interface agreed with the contribution-math worker

For an interpretable contrast theta with natural null 0, the source-to-target sheet delivers theta_target and its joint likelihood or covariance. The contribution sheet can then compare the two directional parameter spaces:

```
S = max_(theta>=0) log L - max_(theta<=0) log L
```

For the approximate normal target contrast with fixed propagated V:

```
S = sign(theta_target)*theta_target^2/(2*V_target)
```

An optional bounded mathematical transformation is `B=tanh(S/2)`, the normalized difference between those best-fit directional likelihoods. It is an evidence index, not annotation probability, and its adoption belongs to the parent/user review. This is a concrete connection to annotation contribution with no invented universal expected rate. It does not turn every biochemical claim into a direction-only claim; the comparison must match the actual functional inference.

For the fully declared synthetic example above:

```
S_target = 2.4324933695
B_target = tanh(2.4324933695/2) = 0.8385435245
```

For comparison the source's own S is 24.0226506959, evaluated on its own source contrast and variance. It is not added to S_target: the target calculation already consumes that source evidence. A diagnostic retained-precision fraction is `0.04/0.1575431859 = 0.2538986360`. This diagnostic is NOT another multiplier on S_target or B_target after the bridge variance has already been used.

The normal calculation is approximate here because fitted variance uncertainty was summarized into V_target. A mixture/profile likelihood should be used if that approximation is inadequate. The parent's earlier experimental-reliability likelihood comparison of specified physical predictions remains a separate available interface; neither formula is silently adopted or overwritten by this note.

## Shared evidence, contradictions, and non-detection

**A measured source→target ratio can reuse the source assay.** If the very same measured a_s appears in `r=a_t/a_s`, then `a_s*r=a_t`. The source error cancels; this is not a source experiment plus an independent bridge experiment plus a target experiment. In logs:

```
Var(z_s)=0.04; Var(z_t)=0.09; Cov(z_s,z_t)=0      [SYNTHETIC]
Var(d=z_t-z_s)=0.13; Cov(z_s,d)=-0.04
Var(z_s+d)=0.04+0.13+2*(-0.04)=0.09
```

A system-response fit shared across A and B similarly cancels what is actually common; use the gradient rather than counting fit parameters twice. Sequence identity and mismatch are two functions of one alignment. Native score, identity, coverage and a tree built from that alignment are often correlated predictors; their joint calibration may use them, but they are not separate independent experimental likelihoods.

For multiple source proteins, retain the covariance induced by a shared calibration model, a common target-specific residual effect, common assay conditions or overlapping preparations. Independent source measurements cannot remove an unresolved target-specific uncertainty simply by their count. Compatible directional contradictions enter the common target likelihood with their actual signs/values. Incompatible endpoints or unresolved state differences remain separate until h supplies the relationship; averaging their scores does not solve it.

Nondetection stays a bound and an observation likelihood. A source with an unknown detection limit supplies no invented zero. A target nondetection with a known limit can strongly constrain a claimed transferred rate, and should be included in the fit/check rather than discarded. No high sequence or structure score overrules that direct molecular result. A full kinetic panel can supply a vector endpoint, so contradictory specificity is represented through the actual substrate-specific components and their covariance.

## Published-case trace and remaining inputs

| Source packet | Numerical components actually available | Concrete role in the proposal | What remains unmeasured for a completed target contribution |
|---|---|---|---|
| `01_tria_atza_target_correspondence_001.md`; Seffernick et al. 2001, DOI 10.1128/JB.183.8.2405-2410.2001 | Native alignment identity; within-protein positive and bounded alternative activity | Retain sequence score as a predictor; train/test against functional divergence and censoring; avoid cross-protein denominator substitution | Cross-protein normalized rates, actual target correspondence and bridge coefficients/uncertainty |
| `02_fole2_2009_system_correspondence_001.md`; Sankaran et al. 2009, DOI 10.1128/JB.00287-09 | Actual metal-response ratios, kinetic-response parameters, structural RMSDs/counts | Measured system ratios multiply predicted activity; substrate response uses fitted kinetics; structure data can inform a measured relation beyond sequence | Assay/fit covariance, cross-ortholog paired rates, joint response when metal and substrate both change; native system quantities only for a native-condition claim |
| `check_relevance_arithmetic_001.py` and `relevance_arithmetic_001.json` | Explicit synthetic calibration, coefficients, Hessian, prediction and shared-error cancellation | Establish arithmetic and define every fitted operand/combination; NOT empirical calibration | Real calibration data and validation; user review of proposed score interface |

The published packets supply contrasting FILLED numerical component calculations. Neither supplies a complete real target likelihood. In particular no ybhP correspondence, rate, coefficient or annotation score was fabricated. Essential undefined effects remain unknown; this is a completed concrete mathematical proposal for discussion, not a declaration that A105 or any of the ten sheets is complete.

The unresolved design choices are specific: whether the proposed conditional activity/contrast mapping and its residual-error treatment are the preferred relevance calculation; which actual molecular contrasts each annotation uses; what calibration domain can support native metric coefficients; and which contribution transformation the user accepts. The exact conditional fitting formula, score combination, missing-data behavior and examples above are supplied so those choices are reviewable.

## What was checked and changed

The worker read one retained TriA/AtzA packet and one primary FolE2 paper, with complete authority resets after each and repair of every observed truncation. SOURCE_CORRECTIONS and the parent's unadopted experimental-reliability proposal were read. Only new files under this assigned directory were created. The stdlib-only arithmetic script was run successfully; it checks all published-derived arithmetic, exactly reconstructs the synthetic fitted residual variances, and verifies shared-error cancellation. No production test suite, reader, scorer, model training on real proteins, scientific run or runtime behavior was changed or claimed.
