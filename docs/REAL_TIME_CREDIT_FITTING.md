# Real-time credit fitting

Source implementation, 2026-11-05. Static review only: no Python, tests, or
workflow was executed for this change. The existing frozen A108 run is unchanged.

An iterator still supplies its own cumulative credit. Its controller subtracts
the previous value to obtain one raw signed marginal credit for each actual
completed observation. Neither credit nor the configured continuation cost is
divided by time. A completed monitor earns the progress its own projector
actually sees; elapsed time and a clock read earn no credit.

The default estimator now fits those marks against real progress-receipt time,
not action or category-occurrence rank. An executed failed/unavailable tool or
reasoning action contributes its actual progress, including zero when no progress
was retained. Invalid requests rejected before execution contribute no observation.

## Clock and immutable observations

`ExecutionContextController` captures `progress_time` in the existing original
action's `runtime_estimation_contexts` row immediately before its credit
observation. The record includes the run, episode, original decision identity,
boot identity, origin and observation monotonic timestamps, and measured seconds.
The origin is the start of that episode's first recorded decision interval.

The coordinate is elapsed real time on that clock. Overlapping child work is
counted once by timestamp subtraction; dispatch durations are not summed. Idle
and suspended time on the same boot are included. This is not compute usage.
When a result returns late, its parent's actual receipt time is used: credit
represents the evidence that the parent has just received, not the child's
earlier dispatch or its private progress.

The original record is reused on replay. Missing historical timestamps,
incompatible boots, a zero reference duration, mismatched identities or reversed
clock order remain explicit unavailable operands. There is no fallback to ranks,
invented duration, missing-time zero, or reconstruction from the current clock.
An execution with old records is not silently migrated to new statistical meaning;
the estimator version changed and existing workflow version checks remain intact.

The ordinary `Workflow` supplies the original action identity on every new
controller observation, including when no optional native, waiting or completion
evidence binding is configured. Its own actions and child-return credit callbacks
use this same boundary. The local job example's existing own-action path also
uses the shared `ExecutionContextController`; constructing a scalar controller
alone is not a timing adapter. Configuration-validation constructors observe no
work and therefore need no timing. Explicit custom estimators retain their own
contracts; an old validation harness using a turn budget is not made a valid
autonomous workflow by this change.

## Quantity, time scale and prior

Let `y_i` be this iterator's unchanged marginal credit, `t_i` its measured receipt
time since the episode origin, and `t_first` the first received progress time.
That first actual episode-start-to-receipt span fixes `s = t_first > 0`. The
dimensionless real-time coordinate is

```
x_i = (t_i - t_first) / s
```

The scale is recorded and remains fixed. It is an empirical temporal prior
binding, not a forecast of the next action's duration or an action-count proxy.
Unequally spaced receipts have unequally spaced fit coordinates. Multiplying
all measured times, including the recorded reference span, by the same factor
leaves the credit prediction unchanged; the output is not a credit rate.

The existing latent-lognormal fractional-Poisson working kernel is retained:

```
log expected credit mark = beta - exp(log_delta) * x + latent
beta prior: mean 0, variance 36
log_delta prior: mean log(0.05), variance 4
```

Thus the decay prior is explicitly per recorded reference span. It is not
silently relabeled as 0.05 per second. The preserved vendored optimizer and
quadrature are used without modifying the vendor source or its hash. Each fit
starts at the prior mode with the prior inverse curvature, not an identity
matrix mistaken for observed information.

Every history length is considered immediately. With no observations the result
is explicitly prior-only; at an unobserved time origin its intercept prior needs
no duration. With observations but missing timing the result is unavailable.
There is no mandatory fit window or subsample count. Old `window_size` and
`subsample_size` fields remain accepted only as ignored saved-definition
compatibility values and are absent from the defaults.

Signed revisions retain their raw history. Positive and negative marks are
fitted at exactly the same recorded times, then combined using the existing
component-band subtraction. The inherited no-loss assumption before any observed
loss remains explicit. Bands remain approximate working-model curvature bands,
not calibrated confidence intervals. Declining expected mark size is a modeling
assumption; late discoveries can violate it.

## Forecast and decisions

The forecast is expected acquisition credit conditional on the recorded current
time. The controller evaluates it at the actual progress receipt when its
continuation decision is updated. It makes no claim about an unknown future
completion timestamp and invents no forecast horizon. Its unchanged stopping
comparison is available forecast upper bound against the iterator's configured
cost in the same credit units. Unavailable operands do not become zero or create
a stopping rule.

Category tables use the same episode clock/reference span, but capture a fresh
clock point for the actual decision/query. That point is retained in the existing
original model-request snapshot; replay reuses the snapshot. It is not appended
to progress history. A category's last receipt can be old after a long wait,
while its conditional forecast is evaluated at the actual new decision time.
Category fits remain presentation-only and do not replace the controller.

The built-in HPC active-work fit receives the selected original observations'
aligned time contexts and evaluates at the current receipt. Pending total-credit
valuation, monitoring costs and explicit elapsed-cost operands retain their
existing quantities. Practical active-work fitting uses the same real-time
binding; verified practical endpoints retain their existing exact-zero future
forecast. Explicitly injected custom estimators keep their caller-defined
contracts. This change does not redefine any iterator's credit projector,
monitoring policy, ownership, suspension or return path.
