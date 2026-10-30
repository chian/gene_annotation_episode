# Closing yield through a parent-defined form

A parent can request the `episode_yield` recorded fact in its existing closed
child form. This is available to scientific and job children. No field is
automatically appended to a returned form. The runtime still enforces the
parent's schema; there is no extra reporting model call.

The fact copies the numerical state **after the child's final completed action**.
The estimate shown to the child before that action can differ. Asking the child
to put that earlier estimate in its last `report_update` would not reliably
communicate the closing estimate.

For example, the parent can define this fact-only form programmatically:

```python
from gene_annotation_episode.episode_reports import report_sources

schema = {
    "type": "object",
    "additionalProperties": False,
    "required": ["monitoring_yield"],
    "properties": {
        "monitoring_yield": report_sources()["episode_yield"]["report_schema"],
    },
}
initial_report = {}
```

Here `monitoring_yield` is the parent's chosen field name. The complete declared
object has these fields, all required when it is not null:

| Field | Type and meaning |
| --- | --- |
| `completed_actions` | Nonnegative integer: the child's completed own actions, including a child invocation as one action at that level. It is sample context, not earned credit. |
| `expected_next_gain.value` | Finite number copied from the closing estimator band. |
| `expected_next_gain.lower` | Finite lower coordinate of that same band. |
| `expected_next_gain.upper` | Finite upper coordinate of that same band. |
| `expected_next_gain.status_code` | Integer enum: `0` normal, `-1` insufficient observations, `-2` unidentifiable. |
| `expected_next_gain.uncertainty_code` | Integer enum: `-1` unavailable, `0` exact, `1` Chebyshev, `2` Laplace approximation. A declared method does not establish calibrated coverage. |
| `expected_next_gain.alpha` | The actual band parameter: `-1` unavailable, `0` exact, otherwise its configured tail parameter. |
| `continuation_cost` | Nonnegative finite number from the child's continuation decision. |
| `stop_requested` | Boolean: whether that child's numerical controller requested stopping. It does not cancel the job, instruct the parent or establish scientific completion. |

Both objects are closed. There is no diagnostics field, raw yield history,
freeform explanation, private action, model conversation or internal episode
identifier in this projection. Scientific findings still use the parent's other
declared scientific fields. Global execution history still contains only run
statistics, not this child estimate.

A synthetic example of the actual returned shape is:

```json
{
  "monitoring_yield": {
    "completed_actions": 2,
    "expected_next_gain": {
      "value": 0.0,
      "lower": 0.0,
      "upper": 0.0,
      "status_code": 0,
      "uncertainty_code": 0,
      "alpha": 0.0
    },
    "continuation_cost": 0.0,
    "stop_requested": true
  }
}
```

Those numbers are a fixture example, not a proposed score, cost or forecasting
policy. They retain the child's configured controller units; this projection
introduces no gain-per-second conversion and does not predict when the external
job will finish. Negative coordinates with normal status can represent a signed
net forecast. Coded unavailable bands retain their original status sentinels;
they must not be interpreted as negative gain or replaced by zero.

The supported numerical `YieldState` supplies these fields. A custom controller
that does not expose that typed state returns null. Reporting does not construct
an estimate for it or substitute the application's default estimator.

The parent can use a requested monitoring yield with its returned job samples
and execution expectations to choose a subsequent investigation or timer. Low
yield from more monitoring now does not imply low value from the running job or
from monitoring later. The runtime supplies no timer cadence, delay formula,
extra stop condition or automatic recommissioning action.

The compact projection is frozen with the child's other closure facts. Report
repair/redelivery reuses it without refitting an estimator, polling the job,
loading child audit archives or changing completed-action history. A completed
run inspected later also retains its original projection.

`tests/test_episode_yield_reports.py` covers these boundaries with actual runtime
and form admission plus synthetic decisions and explicit fixture estimators.
The native role test additionally requests the closing band and bases a selected
monitoring delay on that returned field. Its execution coordination and numerical
policy are fixtures, not configured-model scientific reasoning or an approved
time/credit design.
