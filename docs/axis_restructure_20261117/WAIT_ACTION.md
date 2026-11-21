# The `wait` action: its format and its runner (19 November 2026)

Owner decision: `wait` is a simple defined action with a fixed format and checked arguments. It has two named
parts, kept apart so that what it waits on can change (a set time now, a job event later) without changing the
action's shape or any episode's copy of it:

1. **the action format**: the schema the model answers against, in the episode's own `task.py`;
2. **the runner**: one library function that does the waiting and returns the job's current state, read through
   `job_access.check`.

Worked examples (A102, real model and offline): `root/a102/structural_homology_evidence/resource_work_submission/local_resource_work_execution`
and `root/a102/structural_homology_evidence/resource_result_acquisition`.

## Where it is offered

Only where the Episode holds the handoff row of a job (a `JOB_LEDGER` row with `event == 'handoff'`): in a launching
child once it has launched (`local_resource_work_execution`: the branch is added when `summary['jobs']` is not
empty), and in an episode that is handed the job (`resource_result_acquisition`: always, its assignment passes the
row). It is not offered by `resource_work_submission`.

## Part 1: the action format (in the episode's `task.py`)

The model's answer:

```json
{"selection": {"action": "wait", "seconds": 5}}
```

One argument, `seconds`: a number in the range the episode's settings give. No other argument: the job is the one
whose handoff row the Episode holds, and code names it.

The branch of the answer schema (`answer_schema` in `task.py`; `wait_seconds` is `ctx.settings['wait_seconds']`):

```python
_branch({'action': {'type': 'string', 'enum': ['wait']},
         'seconds': {'type': 'number', 'minimum': wait_seconds['minimum'], 'maximum': wait_seconds['maximum']}})
# _branch(properties) = {'type': 'object', 'additionalProperties': False,
#                        'required': list(properties), 'properties': properties}
```

The settings key (the episode's entry of the `continuation` collaborator, journaled at link):

```python
'wait_seconds': {'minimum': 1, 'maximum': 60}
```

Code validates the answer: `action` validates the model's answer against the same schema it was asked with
(`Draft202012Validator(answer_schema(...)).validate(response)`); an answer outside the range, with another
argument, or given where no handoff row is held, raises `Rejected` and creates no unit. The model endpoint accepted
the schema with `minimum` and `maximum` in the recorded runs (`runs/fixres_14`, `fixres_19`, `fixres_20`).

What `action` returns for an accepted answer (the handoff row comes from the summary, never from the answer):

```python
ToolCall('wait', {'handoff_ref': <the held handoff row>, 'seconds': selection['seconds']})
```

The line of the instructions:

```
- wait: wait the given number of seconds, then read the state of the job.
```

## Part 2: the runner (library)

`gene_annotation_episode/episodic_workflow/episode_support/jobs/job_wait.py`:

```python
async def wait_for_job(ctx, handoff_ref, *, seconds)
```

- `ctx`: the tool's `UnitContext`; the episode declares `'job_access'` in its `SERVICES`.
- `handoff_ref`: the held handoff row of the job.
- `seconds`: how long to wait.
- Returns what `JobAccess.check` returns, with `'waited_seconds': seconds` added: `{'status': 'completed', 'job',
  'resource_id', 'state', 'result_available', 'observed_at', 'assessment', 'replayed', 'check_ref', 'reply_ref',
  'waited_seconds'}`, or `{'status': 'failed', 'job', 'resource_id', 'failure': {'code', 'detail'}, 'waited_seconds'}`
  when the resource refuses the status request.

Today it waits a set time (`await asyncio.sleep(seconds)`) and then makes the one status request. The check row is
written through `ctx.store` by the service, so the Episode holds it as produced by the unit.

The handler in the episode's `task.py` calls the runner and nothing else:

```python
async def wait(arguments, ctx):
    return await wait_for_job(ctx, arguments['handoff_ref'], seconds=arguments['seconds'])

TOOLS = {..., 'wait': wait}
```

**Journaled, and replayed without waiting again.** The wait is a tool unit, so the system journals its attempt and
its outcome like any unit. A resumed run replays the finished unit from the journal: the tool is not run, nothing
waits, no status request is made (`resource_result_acquisition/tests/test_acquisition_steps.py`: an 8-second wait,
then the resumed run returns in under 8 seconds with the same units). A unit that was cut while it waited runs
again and waits again.

**Swapping the runner.** A later runner that waits on a job event (the `native_events` service; the event target
of a local job is in its handoff row, `detail['native']['event_target']`) replaces the body of `wait_for_job` and
keeps its signature and its return. The action format, the handler and every episode's copy stay as they are; an
episode would then add `'native_events'` to its `SERVICES`. It is not built.

## Credit and stopping

A wait earns nothing. In `resource_result_acquisition` credit counts held result files, so nothing is needed. In a
launching child the check row a wait writes must not count as the receiving check: `internal_summary` counts as
receiving checks only the rows its `check_handoff` units wrote, while the job's shown state is its latest row
of either kind.

The yield estimator alone decides when repeated waiting stops. What was seen with the completion controller, whose
forecast falls with the measured progress time in units of the Episode's first span:

| Run | Units (credit) | The controller |
|---|---|---|
| offline, cost 0.5 (`runs/fixres_9`) | inspect (0), launch (4.0), wait 1 s (0) | stopped after the wait (forecast upper bound 0.44) |
| offline, cost 0.05 (`runs/fixres_11`) | inspect (0), launch (4.0), wait 1 s (0), check (7.0) | went on after the wait, stopped at the target |
| offline, cost 0.05 (`runs/fixres_10`) | failed fetch (0), wait 8 s (0) | stopped after the wait |
| offline, cost 0.05 (`runs/fixres_11`) | wait 8 s (0), fetch (1.0) | went on after the wait, stopped at the target |
| real model, cost 0.05, a job of 20 s (`runs/fixres_14`) | check (0), failed fetch (0), wait 1 s (0), wait 5 s (0), wait 10 s (0), fetch (1.0) | went on through five units that earned nothing, stopped at the target |
| real model, cost 0.05, a job of 20 s (`runs/fixres_20`) | check (0), failed fetch (0), wait 5 s (0), wait 5 s (0), fetch (1.0) | went on through four units that earned nothing, stopped at the target |

In a real run the first span includes the model's answer time, so a wait is not long beside it; offline the first
span is a few milliseconds and one wait ends the Episode at cost 0.5. An episode whose model is expected to wait
needs a cost that lets it (a setting; no code).

## Copying it into another episode

1. `task.py`: add the branch to the answer schema where a handoff row is held; add the `ToolCall` to `action`; add
   the handler and its `TOOLS` entry; add the line to the instructions; name `wait_seconds` in the module
   docstring's settings.
2. `SERVICES`: `'job_access'` must be declared.
3. `messages/internal_summary.py`: show the wait in the list of the Episode's own actions; where a check row
   earns credit, do not count the wait's row.
4. Settings of the run: `wait_seconds`.
5. Tests: a rejected answer outside the range; a stepped wait whose outcome has `waited_seconds` and a held
   `check_ref`; credit unchanged by it; a resume that does not wait again.
