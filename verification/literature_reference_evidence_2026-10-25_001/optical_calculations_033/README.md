# Synthetic NADH optical calculator verification

This workload adds only the finite `calculate_nadh_optical_rate(operands)`
calculator, its synthetic tests, and this verification directory. It adds no
source reader, prompt, model call, stored binding, typed communication encoding,
C7 integration, normalization, reliability factor, observation or credit.
No paper or retained paper-specific packet was read for this coding workload.
The full active objective, interface033, root architecture/W04 instructions,
existing activity/rate calculators and error contract were inspected.

The calculator consumes the four canonical primitives and explicit scientific
relationship meanings. It subtracts the matched no-reaction background once,
returns signed NADH depletion in uM/min and conditionally propagates supplied
covariance. It does not infer epsilon, path length, background, linearity,
independence, stoichiometry or a normal observation model. Estimated covariance
remains estimated in the snapshot and conditional facts. Unknown covariance
status leaves variance unavailable even when the supplied matrix is retained.

Reason precedence is: missing sample slope, blank slope, epsilon, path length;
then optical relation, blank role, endpoint, matched window, rate interval;
then rate numerical range. Variance inherits any rate failure; otherwise it
checks absent covariance, unknown covariance status, negative propagated
variance and representable numerical range, in that order. All input contract
validation precedes calculation. A negative propagated result admitted only by
the eigensolver tolerance is `invalid_propagated_variance`, never clipped.

Known reused identities must have compatible dimensions, equal present values
and equal supplied covariance rows/columns. Missing values are not imputed from
identity. Unknown identities do not establish independence; equal values do not
establish identity. Finite rational evaluation preserves signed cross terms
and avoids avoidable intermediate overflow. Only finite float/null results are
returned. A nonzero exact result rounding to zero is `numerical_model_range`.
Snapshot dictionaries/lists follow existing detached JSON-like conventions;
durable immutability is future storage work.

`receipt.json` retains the exact final test command, terminal exit status/output
and SHA256 hashes. `pytest.txt` is that final terminal output. The command runs
only the new optical tests and existing activity-calculator regression. The
initial attempted `python -m pytest ...` could not start because `python` is not
on PATH (exit127); all executable checks used `.venv/bin/python`.

`synthetic_examples.json` records the synthetic q=2 and variance=.0024 example,
an unresolved background, unknown covariance status, estimated covariance and
a negative signed rate. These are numerical fixtures, not source measurements.

Passing these checks establishes this local calculator boundary only. Source
reading, storage and selected LiteratureEpisodes integration, actual primary
source populated values, actual model execution, A105 completion and the full
literature objective remain outside this workload.
