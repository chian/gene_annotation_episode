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
- Same definition only, per action (2026-11-21): the ledger's shares of `k` are only the rows recorded under `k`'s own
  definition of credit and ceiling: the credit's definition and the ceiling version of `k`'s action type alone (parameter
  `definition`, below). A share learned under another credit or another ceiling of that action is on another scale and is not
  used; rows that record no definition (all rows written before this rule) are not used. With no comparable row the ledger
  has no half, so the share is this episode's own (or 1/2 with no own unit either), exactly as for a kind with no history.
  Changing one action's ceiling changes only that action's version, so it discards only that action's shares. Seconds are
  not credit: the ledger's measured seconds of `k` (unit seconds and decision seconds, which set expected seconds) are every
  resolved row of `k` whatever its definition (dropped past the forgetting window like every row when `forget_old_rows`),
  and so are the job durations (`job_seconds`, the service jobs' own ledger rows). Found in real runs:
  `runs/a101_goal3_ws_cspa/model_calls_resume` call-00001 refused the first alignment (forecast 0.889 = share 0.038 x
  ceiling 23.3 < threshold 1.035) because the share came from three `bvbrc_msa` rows of an earlier run whose ceilings (30,
  29.3, 55.4) were of an earlier derivation; and `runs/a101_goal6_ws_cspa/model_calls_cspa` call-00023 refused
  `bvbrc_metacats` (ceiling 1.667, forecast 0.833 = 1/2 x ceiling, expected seconds 246.07 = this run's median unit,
  threshold 1.6) because one version for all actions (bumped to v2 for `all_vs_all` only) had discarded its two ledger rows
  (share 0.9 each) and with them its measured seconds (151.2 and 165.8 s). Recomputed under the per-action rule (direct
  check, not a real run): share 0.9, forecast 1.5, expected seconds 158.5, threshold 1.03, worth it.
- Recency within this episode's own units (owner, 2026-11-21: "the yield estimator must learn just like the accumulation
  estimator from past experience after the first round. So after nothing new is added a second time, the yield estimator
  should be very low for that"; "why you can't just threshold better or have the yield estimator update faster"): this
  episode's own share (bounded) or own mean gain (UNBOUNDED) of `k` is a recency-weighted mean: the latest own unit of
  `k` has weight 1 and each earlier one half the weight of the one after it (half-life: one unit). The ledger's half
  and the equal weighting of ledger and own history are unchanged.
- A pending unit is not an observation (owner, 2026-11-21). A unit whose outcome is pending (its action started work that a
  later unit of the same action finishes: a child that returned parked, its job launched and not extracted) has a rise that
  measures nothing of `k` yet (by design 0: nothing is extracted) and seconds that cover only the launch. It gives `k` no
  share, no gain and no unit seconds, neither in this episode's own history (`pending` of the unit's facts;
  `forecast_actions` skips it) nor in the ledger (its row is resolved with outcome `pending`, which `history` skips for the
  shares and the seconds). The later unit that continues the work (the same action, `until` extracted) is the observation,
  as usual. Its decision seconds and the episode's median unit (the last fallback of expected seconds) still count it. The
  episode says which units are pending through the optional member `credit.py` `outcome_pending(summary, records,
  position)`; there is no default: an episode with a forecast controller and child slots that does not supply it raises
  `forecast_episode_with_children_must_supply_outcome_pending` (one without children has no unit that can be pending). The
  A101 head: a child unit whose child returned `parked` (`bvbrc_blast`, `bvbrc_msa`, `bvbrc_metacats`). Found in a real run:
  `runs/a101_goal7_ws_reca` (journal `journal_reca.sqlite3`): the head commissioned `bvbrc_blast` `until launched`, the child
  launched and returned parked (rise 0), and the controller learned that 0 as `bvbrc_blast`'s own share (recency weighted:
  own share 0 against the ledger's 0.0115), so at `model_calls_reca/call-00004` the row was forecast 1.79 over 348.2 s
  (threshold 2.09), not worth it; the head ran `hmmer_profile_scan` and stopped by its estimator with the search outstanding
  (`outstanding_handoff_count` 1), never extracted, and the ledger row of the launch unit recorded gain 0 for `bvbrc_blast`.
  Recomputed under the rule (direct check, not a real run, `runs/pending_outcome_check_3`): share 0.0115 (the ledger's
  four rows), forecast 3.589, expected seconds 355.4 (the ledger's nine unit seconds, the 47.4 s launch unit left out),
  threshold 2.132, worth it, and the stop decision after the scan does not stop (`bvbrc_blast` still worth it); the
  launch unit's ledger row is resolved `pending`.
- `UNBOUNDED`: forecast = typical gain of `k` by the same rule: the mean of the ledger's mean gain and this episode's mean
  gain, or the one that exists. With no unit of `k` anywhere it is **unknown**, and an unknown forecast never lets the
  episode stop (unknown stays unknown, as in the other controllers).
- Cost = expected seconds. Action type in `job_kinds` whose ledger kind has measured finished jobs: median job
  duration (ledger, `duration_seconds` of the service's own task record) + median seconds the model took to decide (this
  episode's decisions, else the kind's ledger rows). Otherwise the median measured seconds of the units of `k` that are not
  pending (ledger + this episode). With none, the median unit seconds of this episode so far. With none: unknown (counted as 0 in the stop rule).
  A unit's seconds are measured from the previous unit's progress receipt to its own, so the decision time is in it.
- Per-action gate (owner, 2026-11-21: "since the numbers for credit are very similar, you should be able to find one
  threshold to cap wasteful actions reasonably well"; "if you did this right 4-7 is on your thresholding"): after the
  episode's `action` has made a call and its ceiling is asked with its arguments, the unit source compares that action's
  forecast row (the same row the model is shown) with its threshold (expected seconds x exchange rate). If it is not
  worth it the response is raised as `Rejected` (no unit, the model decides again) with feedback `{'status': 'invalid',
  'category': 'forecast', 'code': 'action_forecast_not_worth_its_cost', 'detail': {action_type, ceiling, forecast_gain,
  expected_seconds, threshold, choose_from}}` (`choose_from`: the best commission's arguments, when the episode supplies the optional
  `best_arguments`; the row the model is shown carries them as `best_arguments`, and its ceiling and forecast are those of exactly that commission). An unknown forecast (no history anywhere for an UNBOUNDED action) is not refused;
  only episodes with a forecast controller are gated. The `action_forecasts` rows the model sees gain `worth`.
  It is a forecast comparison, never a limit on the episode.
- Stop: the episode stops when no offered action's forecast exceeds `expected seconds x exchange_rate` and it holds no
  started work it must finish. Stopping is the controller's alone; no budget of time, tokens or turns exists, the cost is a
  forecast input.
- Started work is finished (owner, 2026-11-21: "the head must finish parked jobs"). Each unit's facts carry the required
  boolean `must_continue`, from the episode's optional member `task.py` `resume_action(summary, records, ctx)` (`None`, or
  `{action_type, arguments, due}`: the unit that resumes work the episode started, e.g. a parked BV-BRC job's commission again
  with `until` extracted, `due` once its expected remaining seconds have passed); while it is true the controller does not
  stop, whatever the forecasts. The unit source (`method_loop/episode_type.py`): while a resume is owed its action type must
  be offered (`episode_resume_not_offered`); once it is due it is the only action offered; it is taken as the unit without
  the model when it is due or when no offered action is worth its cost (where the episode would have stopped); and the gate
  never refuses that resume (only that exact action type and arguments: completing launched work is not optional), while
  its forecast is still recorded in the ledger. Before it is due and while other work is worth its cost, the model chooses
  as usual and the resume is an ordinary gated choice. An episode with a forecast controller and child slots must supply
  `resume_action` (`forecast_episode_with_children_must_supply_resume_action`); one with another controller may not
  (`resume_action_requires_a_forecast_controller`). Found in the real run `runs/a101_goal7_ws_reca`: the head launched a
  `bvbrc_blast` search `until launched`, ran `hmmer_profile_scan` and stopped by its estimator with the search outstanding;
  the job row stayed open. Under the rule (direct check, not a real run, `runs/parked_rule_check_2`): with the controller as
  that run learned (unit 0 not pending), the stop after the scan does not fire (`must_continue` true; it would have without
  the rule), the next decision takes the resume (`bvbrc_blast`, `until extracted`) without the model, and the gate, which
  refuses it as a model choice (forecast 1.794 < threshold 2.089), lets it pass as the owed resume.

### Parameter set (declared in the episode's `yield_bindings` entry, `kind: "forecast"`, no `cutoff`)

| parameter | value (A101 head) | reason |
|---|---|---|
| `exchange_rate` | 0.002 credit per second for the top-two credit (definition v7); kept after four real runs (2026-11-21) | derived from the replay of the stored real runs under the top-two rule (`runs/a101_top_two_check/`; a direct check, not real runs): the first units that earned were an alignment (rise 0.75, ceiling 5.83), a clustering (0.62, ceiling 0.80) and a MetaCATS (0.75, ceiling 0.83). With no ledger history of the new definition the learned share is one half, so the lowest-forecast productive first unit is the clustering: 0.40 over about 150 s = 0.0027 per second. 0.002 is the largest round rate at which it is still worth running; a second alignment after one that earned 0.75 forecasts 0.75 over about 190 s = 0.0039 and runs once more, and after it earns 0 the recency-weighted share gives 0.25 over 190 s = 0.0013, which is refused. The earlier 0.006 was derived under the sum over every pair (definition v6) and would refuse that first clustering. Re-derived from the decision rows of the four real runs under the top-two rule (`runs/top2_a101_ws_cspa`, `top2_a101_ws_reca`, `top2_a102_ws_cspa`, `top2_a102_ws_reca`; forecast gain over expected seconds at each decision). A101: the first-time actions that then earned were taken at 0.0035 (clustering, MetaCATS) to 0.0155 per second; the two refused were a second clustering at 0.0007 and a third alignment at 0.0013; any rate between 0.0013 and 0.0035 gives the same decisions. A102: the lowest forecast taken was a site test at 0.0025 (it earned 0.06); refused were a second site test at 0.0018 and the partner test at 0.0007; any rate between 0.0018 and 0.0025 gives the same decisions. 0.002 lies in both windows; the A102 window is narrow and rests on two runs. The partner test is refused at this rate once the ledger holds one row of it (see `a102_head.md`, "What the runs show") |
| `forget_old_rows` | true | weight ledger rows by the estimate table's `ForgettingPolicy` (dropped after `history_seconds` = 90 days, half every `history_half_life_seconds` = 14 days), so a changed service or code is learned |
| `job_kinds` | none (`{}`) | a job action's cost is its measured unit seconds (launch, monitoring and extraction included); the service's job duration alone undercounted it (about 27 s against 190 s for an MSA unit in C2) |
| `definition` | derived, never declared, per action: `forecast_definitions(A101DifferentialCredit().as_record(), CEILING_VERSIONS)` = `{action type: 'credit_sha256:<sha256 of the canonical credit definition record>\|ceiling:<that action's version>'}`; `HEAD/credit.py` `CEILING_VERSIONS` (2026-11-21, the top-two rule): `all_vs_all` `a101_ceiling_v5`, `bvbrc_blast`, `bvbrc_msa`, `bvbrc_metacats` and `hmmer_profile_scan` `a101_ceiling_v2`, `pairwise_blast`, `reason` and `execute_selected_tool` `a101_ceiling_v1`; the shares learned under the sum over every pair (the earlier versions) are not mixed with the new | names the scale each action's shares are on. The credit's meaning is its definition record (already checked against the declaration's `credit_definition`); an action's ceiling's meaning is code, so it is a version string per action type, declared beside `ceiling` in `HEAD/credit.py`, that must change whenever that action's ceiling derivation changes, and only that action's. The string format is the one rows were written in, so an action's rows match while its ceiling is unchanged (`bvbrc_metacats` rows written as `...\|ceiling:a101_ceiling_v1` still match; `all_vs_all` rows written under v1 do not). Rows of other actions written as `...\|ceiling:a101_ceiling_v2` while v2 was one version for all actions (the run `runs/a101_goal6_ws_cspa` and the following one) do not match their action's v1 and give no share; their seconds are used. Required: `ForecastParameters` has no default (`definition` is a mapping action type -> name, or one name for every action of an episode whose ceilings share one version, e.g. the A105 leaves with one action); an offered action the mapping does not name raises `forecast_definition_missing_for_action:<action type>`; `open_yield_controller` raises `forecast_yield_requires_its_definition` without it and `forecast_definition_is_derived_not_declared` if the declared parameters carry one; the ledger raises `forecast_ledger_has_no_definition` if asked or written before the controller defined it |

Declaration to put in the continuation settings of the head (the other agent edits `runs/` settings; this is the exact entry):
`yield_bindings["A101:a101_native_sequence_correspondence"] = {"kind": "forecast", "parameters": {
"exchange_rate": 0.002, "forget_old_rows": true, "job_kinds": {}}, "credit_definition": A101DifferentialCredit().as_record()}`
(the definition record is `HEAD/credit.py` `A101DifferentialCredit`).

## Wiring (why here)

- The ceilings are computed by the unit source (`method_loop/episode_type.py`, `_SystemSource`), so the source is the one
  place that has both the offered ceilings and the summary. A stop is decided after each unit but the next decision's
  offered actions are not yet asked, so the source computes the ceilings the next decision will offer from the summary after the
  unit (the same functions) and puts them in the unit's controller input (`estimation_context['forecast']`), together with
  the action type, its ceiling, the measured unit seconds, the decision seconds, `pending` (the episode's
  `outcome_pending`) and `must_continue` (the episode's `resume_action` is not `None`). The controller input is journaled, so
  resume and replay rebuild the controller exactly; a journal written before `pending` or `must_continue` existed raises
  `forecast_context_requires_exactly` on resume (loud, not repaired). Nothing changes for the three older controllers (the source acts only when
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
`gain` = rise, `cost` = `duration_seconds` = the unit's seconds, `decision_seconds`, outcome `finished`, or `pending` when the
unit's outcome is pending (the same facts; `history` skips the row; any other outcome raises `forecast_row_outcome_unknown`).
A unit that fails stays open and is never part of a history. Only the runner writes; no tool or model is handed the table.
Every `expect` also writes `definition`, the definition of the unit's action (`ForecastParameters.definition_of(action type)`,
handed to the `ForecastLedger` by `ForecastYieldController.attach` through `ForecastLedger.define`). `history` returns
`rows` (the shares: `ceiling`, `gain`, `weight`) only of resolved `finished` rows whose `definition` equals the action's, and
`seconds` (`seconds`, `decision_seconds`) of every resolved `finished` row of the kind, whatever its definition. The history stays recorded in the
journal under `forecast_history.<action type>`, so a resumed run sees the history it first saw. A history journaled before
the per-action rule has no `seconds` and raises `forecast_history_journaled_before_per_action_definitions:<action type>` on
resume (loud, not repaired); a unit that was expected and not journaled before a crash is expected again and, if its
definition differs from the row already written, raises `identity_conflict:expectation:...` (loud, not repaired).

## Choices made where the brief left room

- A kind whose history (ledger and this run) always earned nothing forecasts 0 until it earns; with no history anywhere its share is one half.
- Binding path is the runner's (`sequence_homology_evidence`), not an `a101/` prefix.
- The credit's `yield_method` of the head is `forecast`.
- Resolve-after-crash: a unit re-run after its resolve was written but before its journal row would find different seconds and raise `identity_conflict` (loud, not repaired).

## Findings from the direct check (labelled; see the report)

With no history of a kind its share is one half, so a loose ceiling dominates: `hmmer_profile_scan`
has ceiling 53275 (the profile database size), so its forecast stays in the thousands and the head never stops by the
rule while it is offered; a tighter ceiling or the ledger's own history of its fractions is what stops it. This is the
formula working as specified, and it is the ceiling's looseness, not the controller, that has to change.

Per-action definitions (2026-11-21, on a copy of the ledger as it was after `runs/a101_goal6_ws_cspa`, not a real run; the figures 2.5 of 23.3 and the window of the exchange rate were computed under the sum over every pair, replaced the same day by the top-two rule, so they no longer hold and the rate is to be re-derived from runs under it): at a
fresh run's first offer of `bvbrc_msa` the ledger's v1 rows (two first alignments that earned 2.5 of 23.3, two repeats that
earned 0) give share 0.054, forecast 1.25 at ceiling 23.3, against threshold 193.6 s x 0.0065 = 1.258: the first alignment
is refused by 0.008. The ledger's share mixes first alignments and repeats of one kind; the window of the exchange rate is
that narrow.

## Not exercised

No real run, no model call; the live write of ledger rows through a run (`expect`/`resolve`) was exercised only on a scratch table;
a resumed run on another boot (receipts unavailable) raises; `next_decision` (stepped, no model) does not add `action_forecasts`.
The pending rule and the rule that started work is finished (`resume_action`) ran in no real run (direct checks only). The real ledger's row of the reca launch unit
(`forecast:episode_18d798d0ca56fbbc7daccbf4f42951a3ef438677abddff11daccdafc8bf87165:0`, `bvbrc_blast`) was written before the
rule as `finished` with gain 0 and 47.4 s and is unchanged (the ledger is not rewritten here): until it is resolved
`pending`, later runs read it as a 0 share and a 47.4 s unit of `bvbrc_blast` (on a copy: the ledger's share falls from
0.0115 to about 0.0092 and its median seconds from 355.4 to 348.2 s).

## To be tuned later: how much the prior weighs (owner, 2026-11-21)

The owner's terms: the prior is the ledger; an episode either knows nothing (an empty ledger for the action: half the ceiling) or has a prior.
"Wonder if we need to change the learning formula but that's it. It is a tuning of how much to weigh the prior"; "The prior is the ledger. So that
one test is what i mean by the prior. You can assume you know nothing or have a prior"; "Leave it to be tuned later".

What the formula does today: a ledger with any rows of the action's definition is taken at full weight whatever its size; with a result of this
run too, the ledger's mean and the run's recency-weighted mean each weigh one half. What was seen (real runs, `a102_head.md`, "What the runs
show"): after one `partner_contacts` row (0.22 of a ceiling of 49, a share of 0.0045) the next run's forecast for that action was 0.327 against
a threshold of 0.934 and it was not run, where with an empty ledger it had been 24.5. The tuning would weigh the ledger by how much it holds, so
that a ledger of one test moves the forecast only part of the way from half the ceiling. Not changed; the formula is in `yield_control/`.
