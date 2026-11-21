# The local wrapper: `execute_on_local_resource` (19 November 2026)

One function per resource kind is the single execution and inspection point of the library. This is the one for
the kind `local`. Every episode that works on a local resource calls it from its defined action:
`local_job_execution` and `local_resource_work_execution`, in every axis. The episodes keep their purposes; their
actions call the wrapper. The hpc and api wrappers are separate modules with their own owners.

## Where

`gene_annotation_episode/episodic_workflow/episode_support/jobs/resource_local.py`, one public function:

```python
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource

async def execute_on_local_resource(ctx, resource_id, command, environment, *, wait,
                                    inputs=None, estimates=None, name='job')
```

It is `async`, so the tool that calls it is `async def tool(arguments, ctx)` and awaits it. The episode declares
`SERVICES = ('job_access',)` (plus whatever else it uses); the run's caller supplies the factory from
`episode_support/jobs/job_services.py` (`job_services(configuration)`).

## Behaviour (owner's specification)

It is a **pure pass-through**. It runs the command **verbatim** and passes back standard output, standard error
and the exit code **verbatim**. There is no rewriting, trimming, summarizing, validation or guard of any kind. Its
only purpose is to be the one place where controls are inserted later; the owner adds them later, not now. The
body has one marked line (`# INSPECTION POINT`) where the inspection of the command before launch will go, and
nothing else. Do not add checks to it and do not wrap it with checks in an episode.

It is not a tool and is never offered to a model. The model picks a defined action with controlled arguments; the
episode's action or tool calls this function with a command that code took from the assignment. There is no
`exec_command` and no model-written shell.

## Arguments

| Argument | Meaning |
|---|---|
| `ctx` | the tool's `UnitContext` (`ctx.store`, `ctx.services`, `ctx.operation_key`) |
| `resource_id` | the local resource, as the run's `job_services` configuration binds it (`configuration['local'][resource_id]`) |
| `command` | the argv: a list of text. It is run as given, not through a shell |
| `environment` | `{name: text}`, added to the job's environment as given |
| `wait` | required keyword. `False`: launch and return at handoff. `True`: launch, wait for the end, fetch the files, return the output |
| `inputs` | optional `{file name: reference}`: each artifact the Episode holds is staged in the job's directory under that name before the command starts |
| `estimates` | optional closed JSON kept in the handoff row (`wait=False` only): what was expected of the job before it ran |
| `name` | text that tells apart several executions of one unit (default `'job'`) |

The command runs as a detached systemd user service inside the workflow's slice (`LocalJobRoute`), with the working
directory `<resource workspace>/<job handle>`. The job handle is derived from `ctx.operation_key`, `resource_id` and
`name`: a unit that runs again (resume) takes up the job it already started and starts nothing twice.

## What it returns

`wait=False` (a launch that ends at handoff; what `JobAccess.launch` returns):

```python
{'status': 'completed', 'job': <handle>, 'resource_id', 'kind': 'local', 'submitted_at': <UTC>,
 'adopted': bool, 'replayed': bool, 'handoff_ref': <JOB_LEDGER handoff row>, 'reply_ref': <artifact>}
```

The Episode holds the handoff row as produced by the unit. It returns `handoff_ref` to its parent in a
`record_refs` field; the parent passes it to its monitor (`job_access.check(ctx, handoff_ref)`) and fetch
(`job_access.fetch(ctx, handoff_ref)`) children. The job goes on after the Episode.

`wait=True` (a command whose result the unit needs; `JobAccess.run`, plus the output):

```python
{'status': 'completed',
 'launch': {... as above ...},
 'fetch': {'status': 'completed', 'job', 'resource_id', 'outcome': 'results_acquired', 'state': 'finished' | 'failed',
           'closed_at', 'results': [{'name', 'ref', 'bytes', 'sha256'}, ...], 'result_refs': [...],
           'replayed', 'closure_ref': <JOB_LEDGER closure row>, 'reply_ref'},
 'stdout': <the whole standard output, text>,
 'stderr': <the whole standard error, text>,
 'returncode': <the command's exit code>}
```

- `stdout` and `stderr` are the bytes of the job's `stdout.log` and `stderr.log` decoded as UTF-8, whole. The same
  bytes are artifacts the Episode holds: their references are in `fetch['results']` (names `stdout.log`,
  `stderr.log`, `result.json`, and every other file the command left in its directory).
- A command that exits nonzero is a completed execution: `status` is `'completed'`, `returncode` is the code and
  `fetch['state']` is `'failed'`. What that is worth is the calling episode's `credit.py`.
- A command that could not be started at all has `returncode` 127 (`result.json` then names the `start_failure`).

A request the resource refuses (`RouteRequestError` in the route) is returned, not raised, exactly as `JobAccess`
returns it, and no job row is written for a refused launch:

```python
{'status': 'failed', 'job', 'resource_id', 'failure': {'code', 'detail'}}                     # wait=False
{'status': 'failed', 'launch': {... 'status': 'failed' or 'completed' ...}, 'fetch': None | {...failed...}}   # wait=True
```

Any other error (an unbound `resource_id`: `LookupError('job_resource_not_bound:...')`; an input the Episode does
not hold: `CustodyError`) propagates and ends the run.

## How an episode calls it

```python
SERVICES = ('job_access',)

async def launch_job(arguments, ctx):            # a launch that ends at handoff (local_job_execution)
    return await execute_on_local_resource(ctx, arguments['resource_id'], arguments['command'],
                                           arguments['environment'], wait=False)

async def run_work(arguments, ctx):              # resource work whose output the unit needs
    return await execute_on_local_resource(ctx, arguments['resource_id'], arguments['command'],
                                           arguments['environment'], wait=True, inputs=arguments['inputs'])
```

`arguments` are built by the episode's `action` from the assignment (`read_from_parent` output in the summary),
never from text the model wrote: the model's answer names the defined action and its controlled fields only.

## Records and credit

- The handoff row and (when waiting) the closure row and the result artifacts are in the Episode's custody as
  produced by the unit. `credit(summary, records)` reads them through `records`
  (`episode_support/jobs/job_records.py`: `job_rows(records)`, `handoff`, `closure`, `outstanding_jobs`).
- The wrapper earns nothing by itself. What a handoff, an exit code or an output is worth is the calling episode's
  own `credit.py`.

## Tests

`episode_support/jobs/tests/test_resource_local.py` runs it through the real runner on real detached local jobs
(the test episode `episode_support/jobs/tests/resource_local_probe/`): both modes, a nonzero exit, a refused
launch, staged inputs, and a rerun that starts nothing twice. It needs the workflow launcher
(`tools/one_workflow.sh`), because a local job runs inside the launcher's slice.
