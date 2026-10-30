# A105 calibrated combination — explicit conditional calculation

Additive source-free research, 2026-10-23. All numerical values below are
synthetic. This is a defined calculation when its numerical model inputs are
available, not an empirically calibrated rule for arbitrary homologs. It does
not select the unanswered average-versus-accumulation preference or adopt a
production annotation policy.

## What is being scored

One declared molecular statement: the target's specified activity A exceeds
activity B under the declared reference conditions. The endpoint is
`theta = log(activity_A_target / activity_B_target)`. Activities and conditions
must have compatible physical meanings. A binding constant cannot silently
become a catalytic rate; different conditions are not independent replications.
An investigation can begin with supplied sequence alone and establish this
scoped comparison later; no initial candidate annotation is required.

For source i:

`z_i = y_i - comparability_bias_i - isolation_bias_i + fitted_response_i`

where y is the observed log activity ratio, comparability bias corrects the
specified condition difference outside the intended contrast, isolation bias
corrects the measured mixture/background effect, and the fitted response maps
the source contrast to the target contrast. The corrections must be supported
by their actual measurements/model. The formula does not infer them from a
protein name, sequence identity, purification label or organism.

Build the full covariance C by propagating the joint primitive covariance
through this calculation, retaining shared calibration, preparation, source,
family and target terms only where those are separately justified. A label of
shared family does not provide a numerical covariance. Unknown covariance is
not independence; an unbounded fixed bias is not a centered random error.

For the conditional known-covariance normal example, with vector 1 of ones:

`precision = 1' C^-1 1`

`theta_hat = (1' C^-1 z) / precision`

`variance = 1 / precision`

`S = theta_hat * abs(theta_hat) / (2 * variance)`

`signed_index = tanh(S / 2)`

Here S compares the best fits under the two directional constraints. The
likelihood is combined before fitting that common parameter. Summing the
already optimized source scores gives a different and generally incorrect
common-effect calculation. Neither S nor the bounded index is a probability
that the annotation is true. Fitted/estimated covariance needs its appropriate
uncertainty model rather than being silently treated as known.

## Complete numerical example and checks

The separately populated 17-variable primitive covariance and Jacobian in
`../a105_correlated_bridge_006/arithmetic_001.json` yield

```
z = [0.8, 0.6, 0.9]
C = [[0.230, 0.115, 0.060],
     [0.115, 0.300, 0.085],
     [0.060, 0.085, 0.400]]
```

The weights are `[0.477136432, 0.261244378, 0.261619190]`. The fitted target
effect is **0.773913043**, its variance **0.155481634**, its standard error
**0.394311595**, S **1.926084074**, and bounded signed index **0.745630705**.
These operands include comparability and isolation separately. No additional
native-correspondence multiplier is applied after the fitted mapping already
uses that relationship.

To isolate dependence behavior, take all effects as 0.8, marginal variance 0.25:

| Declared synthetic error model | Observations | Pooled variance | S | Bounded signed index |
|---|---:|---:|---:|---:|
| One source | 1 | 0.250 | 1.280 | 0.564900 |
| Independent source estimates | 2 | 0.125 | 2.560 | 0.856485 |
| Independent source estimates | 10 | 0.025 | 12.800 | 0.999994 |
| Shared component: C=0.10 I + 0.15 J | 2 | 0.200 | 1.600 | 0.664037 |
| Same shared-component model | 10 | 0.160 | 2.000 | 0.761594 |
| Two preparations of one source: C=0.06 I + 0.19 J | 2 | 0.220 | 1.454545 | 0.621394 |
| Repeated representation of the original observation | 1 distinct | 0.250 | 1.280 | 0.564900 |

I is the identity matrix and J is the all-ones matrix. These error decompositions
are specified synthetic inputs, not empirical estimates for protein families.
Exact duplicates are retained once. Equal-valued distinct measurements are not
deduplicated merely because their numbers match. Singular or invalid covariance
is not repaired with invented jitter.

Additional positive measurements need not increase support: independent
observations 0.8 and 0.1 with variance 0.25 each give mean 0.45, variance 0.125,
S=0.81 and index **0.384219**, below the first observation's 0.564900. The added
measurement improves precision but changes the estimated effect. For 0.8 and
-0.8 the index is zero and the disagreement remains recorded separately.

## Unknown covariance with known components

The sensitivity addendum to the worker proposal is necessary. If C=0.10 I+R
and each residual diagonal is 0.15, the known 0.10 I component is retained in
every allowed matrix. For ten equal effects of 0.8:

- Nonnegative exchangeable residual correlation gives variance [0.025,0.16],
  S [2,12.8] and signed-index bounds [0.761594,0.999994].
- Allowing any positive-semidefinite residual with that diagonal gives variance
  [0.01,0.16], S [2,32] and signed-index bounds [0.761594,0.999999999999975].

These are synthetic identification bounds under the respective allowed sets,
not measured confidence intervals. No midpoint is installed as a score. A
marginal-only correlation range that discards the known 0.10 I component is a
different model and cannot replace these bounds.

## Numerical handoff and completion boundary

This calculation defines a contribution for **one molecular statement**, with
its source measurements, target scope, signed result and uncertainty. The
existing positive-support proposal would return `max(0, signed_index)` only
after the compatible evidence was combined. Negative results remain in the
signed sheet. A compound statement requires explicitly stated joint conditions
and a joint observation model. This is not an already-defined scalar for an
annotation containing arbitrary multiple or alternative molecular claims.

The route without a calibrated source-to-target response remains a separate
conventional scoring proposal; its aggregation cannot be justified by pointing
to this likelihood calculation. Actual unavailable inputs are distinct from
an undefined calculation. No raw measurement is thrown away because a later
derived score is unknown, and no missing component becomes a runtime gate.

The parent read both source-free worker proposals and their scripts, then ran
the 115 main checks and the known-component sensitivity checks into the new
`correlated_parent_check_006/` directory. The earlier worker artifacts were not
rewritten. These are research arithmetic/model checks, not production-reader
tests, a biological calibration or a configured scientific investigation.
