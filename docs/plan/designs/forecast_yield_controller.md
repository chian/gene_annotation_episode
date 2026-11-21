# The forecast yield controller (the fourth controller)

## The owner's words (verbatim; they govern)

- "Refusing a test that can't differentiate is kind of like saying you can estimate how much potential credit can be earned ... humans act based on an expected outcome and just like our job launcher has an expected outcome in terms of how long it will take, maybe these should have to have an expected outcome worked out to launch ... if the model knew it wouldn't gain much, i.e., it had a better yield estimator, then it would not do these things or the yield estimator woudl cut it off"
- "So our current accumulation estimator is a shape that assumes we don't know what credit we will get. but in the case of repeat tests we do kind of have a strong prior. And like the time estimator, we can keep a ledger to learn to have an even stronger prior ... If only there was a generalized yield estimator that could plug in that prior"
- "this way, you can't have the model estimate anything really. it's still a mathematical formula, yes?" (the lead answered yes: the forecast is a formula, not the model's)
- "so this then is a 4th type of yield estimator yes? and I would like to make it generalizable to other episode structures, which means it needs some kind of generalized parameter set that can be plugged in and work with any other credit formulas"
- On a deliberate UNBOUNDED: "UNBOUNDED filled in everywhere is bad; UNBOUNDED where truly unbounded is right"

## What was built

`yield_control.ForecastYieldController`, a peer of the accumulation, bounded-quality and completion controllers. The credit
formula enters only through `credit.ceiling` (the most the credit can rise if an action is the next unit, a number or
`UNBOUNDED`). Nothing else of the credit is known to it, and the model estimates nothing.

### Formula (for an offered action of kind `k` = `<binding path>:<action type>`, e.g. `sequence_homology_evidence:bvbrc_msa`)

- Bounded, ceiling `c`: forecast = `m x c`, `m` the learned share of its ceiling that units of `k` earned
  (`obtained / ceiling`). The owner (2026-11-21): "count this current history always more. the ledger should count for
  equal weight with current history": the ledger's history of `k` as a whole (rows weighted by age if old rows are
  forgotten) and this episode's own units of `k` as a whole each weigh one half: `m` = the mean of the ledger's mean share
  and this episode's mean share; with only one of them, that one; with neither, 1/2. Ceiling 0 forecasts 0. A unit that
  lost credit raises (`forecast_cannot_learn_a_negative_rise`): a share of a ceiling cannot be negative.
- `UNBOUNDED`: forecast = typical gain of `k` by the same rule: the mean of the ledger's mean gain and this episode's mean
  gain, or the one that exists. With no unit of `k` anywhere it is **unknown**, and an unknown forecast never lets the
  episode stop (unknown stays unknown, as in the other controllers).
- Cost = expected seconds. Action type in `job_kinds` whose ledger kind has measured finished jobs: median job
  duration (ledger, `duration_seconds` of the service's own task record) + median seconds the model took to decide (this
  episode's decisions, else the kind's ledger rows). Otherwise the median measured seconds of units of `k` (ledger + this
  episode). With none, the median unit seconds of this episode so far. With none: unknown (counted as 0 in the stop rule).
  A unit's seconds are measured from the previous unit's progress receipt to its own, so the decision time is in it.
- Stop: the episode stops when no offered action's forecast exceeds `expected seconds x exchange_rate`. Stopping is
  the controller's alone; no budget of time, tokens or turns exists, the cost is a forecast input.

### Parameter set (declared in the episode's `yield_bindings` entry, `kind: "forecast"`, no `cutoff`)

| parameter | value (A101 head) | reason |
|---|---|---|
| `exchange_rate` | 0.01 credit per second | a unit forecast to earn less than a hundredth of a credit unit per second of its cost is not worth it: a 30 s unit must forecast 0.3, about a third of one admitted candidate (an entry earns up to 1) |
| `forget_old_rows` | true | weight ledger rows by the estimate table's `ForgettingPolicy` (dropped after `history_seconds` = 90 days, half every `history_half_life_seconds` = 14 days), so a changed service or code is learned |
| `job_kinds` | none (`{}`) | a job action's cost is its measured unit seconds (launch, monitoring and extraction included); the service's job duration alone undercounted it (about 27 s against 190 s for an MSA unit in C2) |

Declaration to put in the continuation settings of the head (the other agent edits `runs/` settings; this is the exact entry):
`yield_bindings["A101:a101_native_sequence_correspondence"] = {"kind": "forecast", "parameters": {
"exchange_rate": 0.01, "forget_old_rows": true, "job_kinds": {}}, "credit_definition": A101DifferentialCredit().as_record()}`
(credit definition v2, unchanged).

## Wiring (why here)

- The ceilings are computed by the unit source (`method_loop/episode_type.py`, `_SystemSource`), so the source is the one
  place that has both the offered ceilings and the summary. A stop is decided after each unit but the next decision's
  offered actions are not yet asked, so the source computes the ceilings the next decision will offer from the summary after the
  unit (the same functions) and puts them in the unit's controller input (`estimation_context['forecast']`), together with
  the action type, its ceiling, the measured unit seconds and the decision seconds. The controller input is journaled, so
  resume and replay rebuild the controller exactly. Nothing changes for the three older controllers (the source acts only when
  `view.controller_state` is a `ForecastYieldState`).
- The runner (`episode_runtime/runner.py`) builds a `ForecastLedger` per Episode (`episode_runtime/forecast_ledger.py`),
  hands it to a `ForecastYieldController` once (read: `history`) and gives the source the writing side. The ledger service is
  offered to every run by `run_command._collaborators` but an episode sees it only if it declares it; the head does not.
- Model sees (runner, generic, no `task.py` change): the decision's `ModelRequest.context` gets the key `action_forecasts`, one
  row per offered action: `action_type`, `ceiling` (number or `"unbounded"`), `forecast_gain`, `expected_seconds` (numbers or
  `"unknown"`). Facts only.
- History is recorded in the run journal the first time an action kind is asked about (like a clock point), so a resumed run and every
  replay of a decision sees the history it first saw. This episode's own ledger rows are excluded from it (they enter as observations).

## Ledger rows (estimate table `actions`, existing `expect`/`resolve`)

Kind `<binding path>:<action type>`, key `forecast:<episode id>:<position>`. Before the unit, `expect`: gain band
`{value: forecast, lower: 0, upper: ceiling}` (unbounded: upper = value; an unknown forecast is written as value 0 with
`forecast: null`), `cost` = expected seconds, plus `ceiling`, `forecast`, `expected_seconds`, `seconds_basis`. After the unit, `resolve`:
`gain` = rise, `cost` = `duration_seconds` = the unit's seconds, `decision_seconds`, outcome `finished`. A unit that fails stays open
and is never part of a history. Only the runner writes; no tool or model is handed the table.

## Choices made where the brief left room

- Prior with history: the capped ledger counts alone (not added to Beta(1,1)), so a kind that always earned nothing
  forecasts 0 until it earns; uninformative only with no history.
- Binding path is the runner's (`sequence_homology_evidence`), not an `a101/` prefix.
- The credit's `yield_method` of the head is now `forecast`; its definition record stays v2.
- Resolve-after-crash: a unit re-run after its resolve was written but before its journal row would find different seconds and raise `identity_conflict` (loud, not repaired).

## Findings from the direct check (labelled; see the report)

With no ledger history of the new kinds the prior is uninformative and the loose ceilings dominate: `hmmer_profile_scan`
has ceiling 53275 (the profile database size), so its forecast stays in the thousands and the head never stops by the
rule while it is offered; a tighter ceiling or the ledger's own history of its fractions is what stops it. This is the
formula working as specified, and it is the ceiling's looseness, not the controller, that has to change.

## Not exercised

No real run, no model call; the live write of ledger rows through a run (`expect`/`resolve`) was exercised only on a scratch table;
a resumed run on another boot (receipts unavailable) raises; `next_decision` (stepped, no model) does not add `action_forecasts`.
