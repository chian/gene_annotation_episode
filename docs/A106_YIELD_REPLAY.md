# A106 continuation replay

The selected fixed continuation cost is **0.01**, with **uncertainty alpha 0.05**,
using the original `completed_signed_score_preferential_yield_v1` estimator.
The reusable configuration is
[yield-controller.json](../tests/fixtures/a106_evaluation/yield-controller.json).
The original availability parameters, window 8 and subsample 4, remain unchanged.
They describe when that original estimator has enough observations; they impose
no maximum number of actions or elapsed-time limit.

The user explicitly chose earlier partial or empty returns: a search that is
not making fast progress should yield so another search can be organized. Keeping
the first eventual discovery is therefore not a requirement of this tuning.
The cutoff remains in the iterator's existing credit units. No credit projector,
biological score, optimizer, elapsed-time cutoff or action budget was changed.

## What the trace showed

The stopped investigation retained 714 completed controller observations through
decision 741, with 87 progress units across 85 positive observations. Its last
expected next credit was 0.100468, with upper bound 0.313642. Against the original
cost of 0.001, the controller continued. Small distinct findings kept supplying
credit; that credit was not a delivered A106 numerical subscore. The parent had
received no report at the captured checkpoint.

The selected cutoff yields at **decision 32**, after **25 completed observations**.
The recorded action finished **1,067.85 seconds (17.8 minutes)** after the first
child decision began. This is a replay result, not an installed timer. There was
no intervention assessment at that point. The first credited finding in the
recorded path occurred at decision 44; foregoing that finding on this particular
search is an accepted consequence of returning control earlier.

| Fixed cost, alpha 0.05 | First yield decision on the recorded path | Recorded elapsed minutes |
| --- | --- | --- |
| 0.001 | No yield in the retained trace | — |
| 0.005 | No yield in the retained trace | — |
| 0.0075 | 37 | 20.9 |
| **0.01** | **32** | **17.8** |
| 0.02 | 22 | 11.9 |
| 0.05 | 12 | 6.1 |

Cost 0.01 is ten times the old opportunity cost while retaining the same
uncertainty setting. It gives an unproductive branch less room than 0.001 without
choosing the more aggressive 0.02–0.05 settings. In the earlier retained run,
0.01 also preserves a completed finalization in three of the four child traces
that eventually recorded one. Those historical finals were unavailable scores;
their preservation is not a numerical-positive result or a requirement to keep
every later finding.

For completeness, the replay quantified the discovery tradeoff rather than
selecting a convenient late crossing. At alpha 0.05, a fixed cost must be strictly
below 0.006181 to reach the first positive finding on the long trace. A later
crossing requires at least 0.064259. Thus no fixed cost can preserve that discovery
and also yield later in this recorded history. The user accepted earlier yielding;
no staged cutoff or change in credit meaning was introduced to avoid it.

## Verification

[replay_a106_yield.py](../tools/replay_a106_yield.py) reads the original SQLite
journals without modifying them and loads the frozen numerical implementation.
It checks that the numerical and vendor source hashes match the saved pins and
match across the selected runs. It validates observation order, cumulative credit
deltas, every reconstructed uncertainty band, and every original stop decision.
Alternative alphas reconstruct bands from the original fit's recorded point and
variance; they do not refit credit or feed later observations into earlier choices.

The completed replay covered **36 cost/alpha settings across nine episode traces
from three runs**, comprising **1,110 observations**. Full fits at prefixes 8, 32
and 714 were independently recomputed and matched the saved values. The selected
profile yields in eight of the nine retained traces; the remaining trace ends
after 16 zero-credit observations without reaching the cutoff. It is not forced
to stop at the end of the available data.

**Eight regression checks passed.** They cover the earliest crossing, immunity
of an earlier decision to later data, unavailable estimates, exact cutoff equality,
alpha changes, signed gain/loss subtraction, the discovery tradeoff, credit/decision
integrity, and exclusion of rejected grading/finalization attempts from completed
result counts.

Retained outputs:

- `runs/a106_yield_replay_20261105_03/replay.json`: final profile, grid results,
  source/driver/profile hashes, tradeoffs and recomputed-fit checks.
- The same directory contains the three compact extracted traces.
- `runs/a106_yield_replay_tests_20261105_02/`: eight passing regression checks.
- The original investigation retains `yield-replay-input.json`, captured while
  frozen before its processes were terminated for this serial replay work.

The original investigation and all replay/test workloads have exited. Its saved
scientific records and source snapshot remain intact.

## Reproduction and scope

From this repository, with the window's prior workload fully exited:

```bash
bash tools/one_workflow.sh runs/a106_yield_replay_repeat -- \
  runs/a106_integration_2026-11-03/env/bin/python -B tools/replay_a106_yield.py \
  --run runs/a106_sequence_case01_20261105_02 \
  --run runs/a106_sequence_case01_20261104_01 \
  --run runs/a106_sequence_case01_20261105_01 \
  --output-dir runs/a106_yield_replay_repeat \
  --verify-fit-prefixes 8 32 714
```

This is a continuation-decision replay on recorded actions, not a new autonomous
investigation or a demonstration of what the parent will search next. It covers
repeated investigations of one sequence, not a cross-sequence calibration study.
The underlying uncertainty bands remain approximate and model-dependent.

The selected profile is explicitly for the original estimator. Pass its
`controller` object as `controller_settings` when using that original implementation.
The current shared worktree contains a separately developed real-time estimator;
these old traces lack its required `progress_time` receipts. This work does not
substitute invented times, modify that estimator, change shared defaults, or claim
to have validated the new estimator with this replay. The CLI verifies estimator
identity before accepting the profile.

The requested trace review and fixed-cutoff selection are complete. The broader
A106 scientific demonstrations remain separately unfinished.
