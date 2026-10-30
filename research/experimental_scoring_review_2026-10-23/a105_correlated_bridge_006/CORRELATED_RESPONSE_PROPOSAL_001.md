# A105: combine calibrated source measurements on one target contrast

2026-10-23. Source-free mathematical proposal. **Every numerical input below is
SYNTHETIC.** No paper, source packet, new empirical calibration, reader, prompt,
production scorer or scientific run was used. This finishes a conditional
multi-source arithmetic example, not A105 or any of the ten scoring sheets.

When actual response mappings and covariance are supported, map the source
measurements onto the **same target molecular contrast**, combine their joint
measurement model, and then calculate the directional profile contrast once.
This defines a usable measured/calibrated route. It does not supply missing
empirical mappings, require a new experiment on the target, or exclude the
separate uncalibrated-correspondence route for novel targets.

The pending choice between an average source index and a cumulative score
convention remains unanswered. This example chooses neither convention. A fitted
common target effect is a different estimand from an average of source scores.
Its directional confidence need not increase after every positive observation.

## 1. Numerical cells, denominators and model

The target can be defined by supplied sequence, selected file contents or
snippets; neither a public name nor an initial candidate function is required.
Once molecular findings establish a meaningful comparison, define here

```
theta_T = log(a_A,T / a_B,T)
```

where both a values are attributed molecular rates per molecule amount at one
declared reference state and condition. Positive theta means greater A activity.
The numerator and denominator are two specified molecular reactions, not growth,
expression or a supposed physiological role. The same calculation could use a
properly defined affinity contrast, but that would be a different endpoint.
Here all rates are positive and the reported log contrasts have a specified
normal error model; nondetections are not replaced by zero or pseudocounts.

| Numerical cell | Defined measurement or calculation | Evaluation and use |
|---|---|---|
| `y_i` | `log(net_rate_A,i / net_rate_B,i)` on assayed source i, after measured instrument/matched-blank treatment; dimensionless | The actual source measurement and its assay uncertainty |
| `c_i` | `log((A/B)_source_condition / (A/B)_reference_condition)` from matched condition-response controls | Comparability correction for differences **other than** A versus B, the intended changed variable |
| `d_i` | `-log(f_A,i / f_B,i)`, where f is measured fraction of each net rate attributable to the intended assayed molecule | Separate isolation correction; a mixed preparation is not made attributable by a sequence match |
| `X_i beta` | Fitted or measured target-minus-source response on that same log contrast | Molecular/system response mapping, with its supported domain and coefficient covariance |
| `z_i = h_i(...)` | `y_i - c_i - d_i + X_i beta` | Source i's estimate of the one declared target contrast |
| `C` | Joint covariance of all z, with measured/fitted input covariance and residual correspondence effects | Determines precision and dependence; no overall relevance grade |
| `theta_hat`, `V_hat` | GLS estimate and variance defined below | Common target effect and its conditional uncertainty |
| `S`, `B` | Signed directional profile separation and proposed bounded transformation | Evidence about the sign of this contrast, not function probability or a wired annotation coordinate |
| `Q` | Covariance-weighted residual sum of squares | Diagnostic disagreement with the common-effect model; not another multiplier |

The fields also retain uncertainty type, degrees of freedom when applicable,
measurement/preparation identity, reference conditions, source-to-target endpoint
definition, calibration domain and status. These support the numbers; they do
not substitute for the numerical cells. Reader functions for those exact inputs
remain separate work. No extra grade is applied after C has already accounted
for a measured weakness.

For general mappings, let u contain **all** source observations, corrections,
predictors and response coefficients. With Jacobian J and external residual
loadings L:

```
C = J Sigma_u J^T + L_T Omega_T L_T^T + L_F Omega_F L_F^T + D_source
```

Cross-covariances inside Sigma_u include assay/response fits reusing data,
correlated coefficients, shared standards, controls and denominators. Residuals
are added only if they are not already in Sigma_u. The fixture's residuals are
included in the full primitive matrix instead, so `C = J Sigma_full J^T` is
exactly the same calculation. Nonlinear h uses justified propagation or its
full likelihood; a large-uncertainty nonlinear transformation need not be normal.

The explicit synthetic observation model is

```
z_i = theta_T + e_y,i - e_c,i - e_d,i
      + X_i delta_beta + u_source,i + u_T + u_family,g(i)
```

All error means are zero in this fixture. Their declared variances are below.
After marginalizing these specified Gaussian errors, `z | theta_T ~ N(1 theta_T,C)`.
One target effect is inferred; each homolog does **not** get its own optimized
target effect. The common target residual u_T is the same random error for every
mapping to this target, so more source assays cannot average it away. A family
effect is shared only where the supplied calibrated model establishes that
relationship. Membership labels give loadings; they do not estimate variances.
In particular, a tree cluster supplies no numerical correlation coefficient.

This random-effect interpretation requires an independently supported centered
residual distribution. If u_T is instead an unbounded fixed unknown bias, the
data identify `theta_T + u_T`, not theta_T separately. A finite target score
then needs additional information or declared sensitivity bounds; the variance
cannot be invented. The same applies to a common unknown calibration bias.

## 2. Explicit three-source inputs and complete covariance construction

These are invented quantities on three distinct source molecules, each with its
own preparation. Source-specific assay, comparability and isolation measurements
are independent in this fixture; the response-coefficient fit is external and
does not reuse these assays. These zero cross-covariances are stated model
inputs, not deductions from different paper or preparation labels.

All rate denominators B can be represented by 1 per minute and numerators A by
`exp(y_i)` per minute. The independent condition-response ratio is `exp(c_i)`;
the independent attribution-fraction ratio `f_A/f_B` is `exp(-d_i)`.
Those three numerical ratios retain distinct experimental meanings.

| Source | y | c | d | x | Corrected source `y-c-d` | Response mean `.15+.05x` | Mapped z | Var(y) | Var(c) | Var(d) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 | .90 | .10 | .10 | -1 | .70 | .10 | .80 | .04 | .01 | .01 |
| G2 | .60 | .05 | .10 | 0 | .45 | .15 | .60 | .09 | .01 | .04 |
| G3 | .95 | .20 | .05 | 1 | .70 | .20 | .90 | .16 | .04 | .01 |

x is a declared dimensionless directional descriptor in this synthetic fitted
response model, treated as exact here. It is not sequence identity or a proxy
functional probability. A real mapping needs the actual descriptor definition,
measurement uncertainty and empirically supported coefficients. This fixture
conditions on such inputs; it does not claim to have fitted them from real data.

```
X = [[1,-1], [1,0], [1,1]]        beta = [.15,.05]
Omega_beta = [[.020,.005], [.005,.020]]
X Omega_beta X^T = [[.030,.015,.000],
                  [.015,.020,.025],
                  [.000,.025,.050]]

D_y   = diag(.04,.09,.16)
D_c   = diag(.01,.01,.04)
D_d   = diag(.01,.04,.01)
D_src = diag(.04,.04,.04)
C_T   = [[.06,.06,.06], [.06,.06,.06], [.06,.06,.06]]
L_F   = [[1,0], [1,0], [0,1]]     Omega_F = [[.04,0], [0,.04]]
C_F   = [[.04,.04,0], [.04,.04,0], [0,0,.04]]

C = D_y + D_c + D_d + X Omega_beta X^T + D_src + C_T + C_F
  = [[.230,.115,.060],
     [.115,.300,.085],
     [.060,.085,.400]]
```

For example, `C_12 = .015 + .060 + .040 = .115`; `C_13 = 0 + .060 + 0 = .060`.
The shared family variance .04 and target variance .06 are explicit SYNTHETIC
calibration operands. Their magnitude is not inferred from which family a
source belongs to. All omitted entries of the listed diagonal/block matrices
are exactly zero under this fixture's independence assumptions.

The complete 17-dimensional input ordering is `(y[3],c[3],d[3],beta[2],
source_residual[3],target_residual[1],family_residual[2])`. Its covariance is
`blockdiag(D_y,D_c,D_d,Omega_beta,D_src,[.06],Omega_F)`; its Jacobian is
`[I,-I,-I,X,I,1,L_F]`. The research JSON contains all 289 numerical covariance
entries and all 51 Jacobian entries, plus every component above. Means of all
residual terms are zero and every numerical input is populated.

For positive-definite C, ordinary generalized least squares gives

```
P = 1^T C^-1 1
w = C^-1 1 / P
theta_hat = w^T z                       V_hat = 1/P
Q = (z - theta_hat 1)^T C^-1 (z - theta_hat 1)
ell(theta) = -.5 (z-theta 1)^T C^-1 (z-theta 1) + constant
S = max_(theta>=0) ell(theta) - max_(theta<=0) ell(theta)
  = sign(theta_hat) theta_hat^2/(2 V_hat)
B = tanh(S/2)
```

Checked result: `w=(.477136432,.261244378,.261619190)`, `P=6.431627795`,
`theta_hat=.773913043`, `V_hat=.155481634`, `SE=.394311595`, `Q=.217391304`
with 2 residual degrees of freedom **conditional on fixed C**. The constrained
quadratic fits give `Q_Hplus=.217391304`, `Q_Hminus=4.069559453`, hence
`S=(4.069559453-.217391304)/2=1.926084074` and `B=.745630705`.

B is the normalized difference of the two best directional likelihood fits.
It is not a posterior probability. Estimated C, uncertain variance components
or nonnormal residuals require their supported joint/profile/bootstrap model;
fixed-C arithmetic does not establish calibrated real-data uncertainty.

## 3. One versus two versus ten sources

This controlled comparison sets every mapped estimate to .8 and every marginal
variance to .25. Equal values are deliberate synthetic observations, not evidence
of duplicate identity. For every row: `y=.8`, `c=.1`, `d=.1`, `X=[1,1]`,
`beta=[.1,.1]`; thus `h=.8-.1-.1+.2=.8`.

The two columns below are **different complete hypothetical calibration models**.
They do not rename a real shared-target error as independent merely to get the
independence result.

| Covariance component | Entirely independent model | Shared-error model |
|---|---|---|
| Source assay | .04 I | .04 I |
| Comparability | .01 I | .01 I |
| Isolation | .01 I | .01 I |
| Response coefficients | .05 I, distinct external fit per source | .05 J, same external fit |
| Source-specific response residual | .14 I | .04 I |
| Target residual | exactly 0 in this hypothetical model | .06 J |
| Family residual | exactly 0 in this hypothetical model | .04 J |
| Total C | **.25 I** | **.10 I + .15 J** |

J is the all-ones matrix. The coefficient covariance for each fit is the same
`[[.02,.005],[.005,.02]]`; `[1,1] Omega_beta [1,1]^T=.05`.
The independent model needs support for the absence of shared residual terms;
independently prepared samples alone do not establish it. Its residual .14
differs from the other model's source-specific .04, preserving the equal .25
marginal variance for comparison.

The correlated two-source matrix is `[[.25,.15],[.15,.25]]`. Its fully populated
ten-source matrix is:

```
[[.25,.15,.15,.15,.15,.15,.15,.15,.15,.15],
 [.15,.25,.15,.15,.15,.15,.15,.15,.15,.15],
 [.15,.15,.25,.15,.15,.15,.15,.15,.15,.15],
 [.15,.15,.15,.25,.15,.15,.15,.15,.15,.15],
 [.15,.15,.15,.15,.25,.15,.15,.15,.15,.15],
 [.15,.15,.15,.15,.15,.25,.15,.15,.15,.15],
 [.15,.15,.15,.15,.15,.15,.25,.15,.15,.15],
 [.15,.15,.15,.15,.15,.15,.15,.25,.15,.15],
 [.15,.15,.15,.15,.15,.15,.15,.15,.25,.15],
 [.15,.15,.15,.15,.15,.15,.15,.15,.15,.25]]
```

| Sources | Model | Fitted target contrast | Fitted variance | S | B |
|---:|---|---:|---:|---:|---:|
| 1 | Either model | .800000000 | .250000000 | 1.280000000 | .564899553 |
| 2 | Entirely independent | .800000000 | .125000000 | 2.560000000 | .856484915 |
| 10 | Entirely independent | .800000000 | .025000000 | 12.800000000 | .999994478 |
| 2 | Shared error | .800000000 | .200000000 | 1.600000000 | .664036770 |
| 10 | Shared error | .800000000 | .160000000 | 2.000000000 | .761594156 |

Arithmetic: `V_independent=.25/n`; `V_shared=.10/n+.15`. In the shared model,
the limit is `.15`, not zero, and `S` approaches `.8^2/(2*.15)=2.133333333`.
Neither fixed discount factors nor paper counts appear in this calculation.

## 4. Duplicate identity and genuinely new preparations

An exact re-representation of one observation has the same assay, corrections,
response fit and residual realization. Its two-row covariance is `.25 J`, a
singular matrix. Canonicalize that observation once; it stays `V=.25, S=1.28,
B=.564899553`. No artificial diagonal noise or independent error is added.
Equality of numbers by itself establishes neither duplicate identity nor
independence. Conflicting representations of one recorded observation require
source reconciliation, not an extra observation.

Two genuinely independent preparations of **the same source molecule**, with
new independent assay/comparability/isolation measurements, have independent
variance `.04+.01+.01=.06` each. The source-specific mapping residual `.04`
is now shared because the molecular source is the same. Together with the
common response fit `.05`, target `.06` and family `.04`, shared variance is
`.19`. Thus

```
C = [[.25,.19], [.19,.25]]
V_hat = .06/2 + .19 = .22
theta_hat=.8; S=1.454545455; B=.621393997
```

This new preparation contributes information while preserving the source-to-target
uncertainty. Independent preparation is not equivalent to an independently
known source-to-target relationship. Technical readings that share preparation
effects require their own smaller independent measurement component.

## 5. Contradiction, positive magnitude conflict, and sum-before-profile

For independent measurements, add log likelihoods at the **same trial target
effect**, then optimize. For correlated measurements, use the joint covariance
likelihood (or a shared-nuisance likelihood), not a product of marginal fits.
Do not sum optimized S values; do not add B values; do not describe `R*B` as a
likelihood. No R multiplier occurs in this response-mapping calculation.

All rows below use marginal variance .25. The independent pairs have zero
cross-covariance; correlated pairs have cross-covariance .15.

| Observed mapped effects | Model | theta_hat | V_hat | S | B | Q |
|---|---|---:|---:|---:|---:|---:|
| +.8 alone | One | .80 | .250 | 1.280000000 | .564899553 | 0 |
| +.8, +.1 | Independent | .45 | .125 | .810000000 | .384219009 | .98 |
| +.8, +.1 | Correlated | .45 | .200 | .506250000 | .247853953 | 2.45 |
| +.8, -.8 | Independent | 0 | .125 | 0 | 0 | 5.12 |
| +.8, -1.2 | Independent | -.20 | .125 | -.160000000 | -.079829769 | 8.00 |
| +.8, -1.2 | Correlated | -.20 | .200 | -.100000000 | -.049958375 | 20.00 |

The additional **positive** .1 estimate improves precision but moves the fitted
common effect toward zero: `.45^2/(2*.125)=.81`, below the original `1.28`.
Its magnitude conflicts with the first estimate's larger effect. This is not
source-roster mean-score dilution; it follows the specified common-target
measurement likelihood. No unconditional monotonicity requirement is justified
by the word “positive.” For equal variances v and positive observations a,b,

```
S_first = a^2/(2v)
S_joint = (a+b)^2/(4v)
S_joint < S_first exactly when b/a < sqrt(2)-1
```

For independent `.8,.1`, separate fitted scores are `1.28` and `.02`, whose
sum `1.30` is **not** the common-effect result `.81`. For `.8,-1.2`, their sum
is `1.28-2.88=-1.60`, while the proper common-effect result is `-.16`.
The accidental equality for `.8,.8` does not make the sum rule generally valid.

Q preserves disagreement; it is not multiplied into S as another score. Under
these fixed-C Gaussian common-effect models the pairs have one residual degree
of freedom. Large Q calls the model's common-effect/covariance assumptions into
question; no automatic gate, arbitrary penalty or covariance inflation is
introduced. A measured null does not mean absent evidence, and a pooled zero
does not mean each source has no effect.

## 6. Known zero, missing covariance, and sensitivity bounds

A measured or model-supported **zero cross-covariance** permits the independent
calculation. An unreported covariance is unknown, not zero. Missing h leaves the
target contribution unknown while preserving the source result. All-zero
covariance, exact duplicates and other singular models require their appropriate
deterministic constraints or canonical observations; they are not repaired with
invented variance or reported as infinite confidence from a missing error bar.

For an explicit sensitivity family with ten equal mapped estimates .8, let

```
C(rho) = .25 ((1-rho) I + rho J)
V_hat(rho) = .25 (1+9rho)/10
S(rho) = .8^2 / (2 V_hat(rho))
```

| Assumed rho | Fitted variance | S | B |
|---:|---:|---:|---:|
| 0 | .025 | 12.800000000 | .999994478 |
| .2 | .070 | 4.571428571 | .979525426 |
| .6 | .160 | 2.000000000 | .761594156 |
| .8 | .205 | 1.560975610 | .652986604 |

If `rho in [0,.8]` is the **declared sensitivity assumption**, the exact lower
and upper values in this family are `S in [1.560975610,12.800000000]` and
`B in [.652986604,.999994478]`. The bound [.0,.8] is SYNTHETIC and is not an
empirically inferred range for real homologs. Its midpoint is not an estimated
score. For the fixed equal effects these bounds follow monotonicity in rho;
general unequal effects/covariances require actual optimization of their own
allowed covariance set, and need not have that monotonic behavior.

With no justified correlation bounds, no point score is available. Positive
semidefiniteness alone permits exchangeable `rho` approaching `-1/9` from above;
the variance of this mean approaches zero and S is unbounded above. As rho
approaches 1, the perfectly shared-error limit gives `V=.25, S=1.28`.
Thus even in this restricted family, knowing only the marginal variances does
not justify a finite upper S or an independence default. A nonnegative-rho
restriction is an additional model assumption, not a fact supplied by a family
label. Unknown covariance stays visibly unresolved.

Covariance can also **cancel** reused error. If a measured log ratio
`d=z_target-z_source` reuses the exact source assay, a synthetic covariance is
`Cov(z_source,d)=-.04`, `Var(z_source)=.04`, `Var(d)=.13`. Then
`Var(z_source+d)=.04+.13-2*.04=.09`, the target assay variance. These are not
three independent contributions. This algebra is an illustration of reused
data, not a requirement to measure the target.

## 7. Where pooling is and is not defined

Pool only when each supported h refers to the same target molecule/material
scope, state, molecular numerator/denominator and reference condition. Different
homologs can qualify through calibrated mappings; merely sharing an annotation,
fold, clade or units does not supply that mapping. Different source conditions
can qualify through measured condition-response functions and their uncertainty.

Binding affinity cannot be pooled with a transport rate as repeated measurements
of this theta. A substrate ratio, absolute rate, binding Kd, EC50, occupancy,
growth phenotype and activation consequence are not interchangeable endpoints.
If a scientifically supported joint model relates different endpoints, fit that
model and its specified hypothesis; otherwise retain separate numerical sheets.
A106 perturbation/restoration evidence stays outside this A105 contrast.
Complementary assays can resolve identity or attribution without being
independent repeated measurements of the same effect.

Known nondetection limits require their censored observation likelihood and
source-to-target mapping; the Gaussian GLS shortcut is not applied to a
fabricated zero. Unknown limits or unresolved state differences remain unknown.
Discovery-selected contrasts retain their tested panel/selection scope; this
example does not calibrate the selection process.

## 8. Exact scope, artifacts and unresolved work

The executable research calculation is `check_correlated_bridge_001.py`.
`python3 .../check_correlated_bridge_001.py` ran successfully with NumPy 2.5.2,
checking 115 arithmetic/model relationships. Checks compare covariance from
primitive inputs with component sums, GLS normal equations with explicit
directional quadratic fits, compound-symmetry closed forms, likelihood sums
before optimization, sign/unit invariance, duplicate identity, invalid/missing
covariance, shared-denominator cancellation and analytic sensitivity endpoints.
They verify this conditional mathematics, not any real measurement model.

`arithmetic_001.json` has all populated primitive inputs, covariance matrices,
Jacobian entries and results. `NUMERICAL_TABLE_001.md` is the concise generated
comparison table. `AUTHORITY_READ_001.md` records the complete instruction read.
Only new files in this assigned directory were created; no old record changed.

Still required for a real target calculation: supported h and its domain;
actual molecular contrasts and uncertainty; source/calibration/preparation
identity; coefficient covariance and any input cross-covariance; shared-target,
family and source residual estimates or justified sensitivity sets; and a model
for their estimation uncertainty. This synthetic example supplies none of those
empirical facts and does not declare a new target experiment mandatory.

S/B remain proposed signed sheet outputs. B ranges from -1 to 1 and is not
directly the retained nonnegative annotation-support coordinate. The user's
aggregation preference, the uncalibrated route's convention, and the separate
W05 signed-to-annotation interface remain unresolved. No clamp, neutral .5,
overall relevance grade, altered hypervolume or completed-sheet claim is made.

Additive clarification after this calculation:
[SENSITIVITY_CONSTRAINT_ADDENDUM_001.md](SENSITIVITY_CONSTRAINT_ADDENDUM_001.md)
distinguishes section 6's marginal-only sensitivity set from a set that preserves
known independent variance components. Use that distinction when quoting bounds;
do not select the allowed covariance giving the largest score as an estimate.
