# Clarification: a sensitivity set must preserve known covariance components

2026-10-23. Additive clarification of section 6 in
`CORRELATED_RESPONSE_PROPOSAL_001.md`; its arithmetic is preserved unchanged.

The section 6 interval `rho in [0,.8]` is a **standalone marginal-only sensitivity
exercise**, not a permissible change to the fully specified `.10 I + .15 J`
calibration model in section 3. It knows the .25 diagonal but does not retain the
section 3 decomposition. This distinction matters: if `.10 I` is already known
to be independent error and remaining residual diagonal is .15, total positive
pair correlation cannot exceed `.15/.25=.6`. The .8 row cannot describe that
partially known model.

A directly usable alternative preserves the known information:

```
C = .10 I + R
diag(R) = .15, R positive semidefinite
```

For ten equal mapped contrasts .8, every GLS mean is .8. If only these covariance
constraints are known, the **exact attainable** sensitivity bounds are

```
.010 <= Var(theta_hat) <= .160
2.0 <= S <= 32.0
.761594155955765 <= B <= .999999999999975
```

The lower variance bound follows from `C >= .10 I`, hence
`1^T C^-1 1 <= 10/.10`. The upper bound follows by evaluating the ordinary equal
weighted mean: positive semidefinite R and its .15 diagonal imply every
`R_ij <= .15`, so this mean's variance is at most `.10/10+.15=.16`.
The variance of GLS, the minimum-variance linear unbiased mean for known C, is
no larger. Both bounds are attained:

| Allowed residual matrix | Residual pair correlation | Total pair correlation | V | S | B |
|---|---:|---:|---:|---:|---:|
| `.15 J` | 1 | .6 | .160 | 2.0 | .761594156 |
| `.15 I` | 0 | 0 | .025 | 12.8 | .999994478 |
| `.15 ((10/9) I - (1/9) J)` | -1/9 | -1/15 | .010 | 32.0 | .999999999999975 |

The third residual matrix is singular but positive semidefinite; total C remains
positive definite because `.10 I` is retained. No fabricated diagonal jitter is
needed. Here the known independent component prevents the unbounded upper S
possible in the marginal-only exercise.

If the additional model assumption is exchangeable **nonnegative** residual
correlation `kappa in [0,1]`, then

```
R(kappa) = .15 ((1-kappa) I + kappa J)
V(kappa) = .025 + .135 kappa
S in [2,12.8]; B in [.761594156,.999994478]
```

The covariance constraints supply these bounds; no midpoint score or fitted
correlation is claimed. Real component bounds must come from actual calibration
and knowledge of shared errors. These illustrations do not infer a correlation
from a tree label, nor do they justify using the broadest bound when additional
known shared terms already restrict C. The same calculation for unequal observed
effects needs the actual allowed covariance set and must account for changes in
both the GLS mean and variance.

`check_sensitivity_constraints_001.py` checks all three explicit matrices,
positive semidefiniteness, total positive definiteness and closed-form/GLS
endpoint agreement. It writes `sensitivity_constraints_001.json`; every number
is SYNTHETIC. This addition leaves the pending aggregation convention and the
missing empirical calibration unresolved.
