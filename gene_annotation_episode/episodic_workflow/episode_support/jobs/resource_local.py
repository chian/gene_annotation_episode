"""Execution on a local resource: the one function every episode that works on a local resource calls.

``execute_on_local_resource`` is **the inspection point before execution** for the resource kind ``local``. Every
defined action of every episode that starts work on a local resource (a job launch that ends at handoff, a piece of
resource work that is waited for) calls this function and nothing else to do it. No episode calls
``job_access.launch`` or ``job_access.run`` for a local resource itself, and no model writes or runs a command:
the model picks a defined action with controlled arguments, the episode's action calls this function, and this
function runs the command through the real route.

It is a pure pass-through today. The command runs verbatim, and its standard output, standard error and exit code
come back verbatim: nothing is rewritten, trimmed, summarized, validated or guarded. Its only purpose is to be the
single place where controls are inserted later; the marked line in the body is where they go.

The route is the run's ``job_access`` service on a ``LocalJobRoute`` (``local_job_route.py``): the command runs as a
detached systemd user service inside the workflow's slice, in a directory of its own below the resource's
workspace, and ``job_access`` writes the job's rows of ``JOB_LEDGER`` through ``ctx.store`` (custody is built in:
the calling Episode holds them as produced by the unit). The episode declares ``'job_access'`` in its ``SERVICES``.
"""
from __future__ import annotations

import json


async def execute_on_local_resource(ctx, resource_id, command, environment, *, wait, inputs=None, estimates=None,
                                    name='job'):
    """Run ``command`` (an argv list of text) with ``environment`` (``{name: text}``) on the local resource
    ``resource_id``, verbatim. This is the inspection point before execution: every local execution of every
    episode passes here, so a control of the command before it starts is added here and nowhere else.

    ``ctx`` is the tool's ``UnitContext``. ``inputs`` is ``{file name: reference}``: each held artifact is staged
    in the job's directory under that name. ``name`` tells apart several executions of one unit. The job's handle
    comes from ``ctx.operation_key`` and ``name``, so a unit that runs again takes up the job it already started
    and starts nothing twice.

    ``wait=False`` launches and returns at handoff (``JobAccess.launch``); the job goes on after the Episode.
    ``estimates`` (what was expected of the job before it ran) is kept in the handoff row. Returns ``{'status':
    'completed', 'job', 'resource_id', 'kind', 'submitted_at', 'adopted', 'replayed', 'handoff_ref',
    'reply_ref'}``: ``handoff_ref`` is the ``JOB_LEDGER`` handoff row, to return in a ``record_refs`` field.

    ``wait=True`` launches, waits until the command has ended and fetches its files (``JobAccess.run``). Returns
    ``{'status': 'completed', 'launch': <as above>, 'fetch': {'results': [{'name', 'ref', 'bytes', 'sha256'}],
    'result_refs', 'closure_ref', ...}, 'stdout', 'stderr', 'returncode'}``: ``stdout`` and ``stderr`` are the
    whole text the command wrote, ``returncode`` its exit code (a command that exits nonzero is a completed
    execution with that code). Every file the command left is an artifact the Episode holds (``fetch``).

    A request the resource refuses is returned, not raised, as ``JobAccess`` returns it: ``{'status': 'failed',
    'job', 'resource_id', 'failure': {'code', 'detail'}}`` without waiting, ``{'status': 'failed', 'launch',
    'fetch'}`` when waiting. No job row is written for a refused launch."""
    # INSPECTION POINT: controls of ``command`` and ``environment`` before they run go here. None today.
    job = {'command': list(command), 'env': dict(environment)}
    access = ctx.services['job_access']
    if not wait:
        return access.launch(ctx, resource_id, job, inputs=inputs, estimates=estimates, name=name)
    outcome = await access.run(ctx, resource_id, job, inputs=inputs, name=name)
    if outcome['status'] != 'completed':
        return outcome
    files = {item['name']: ctx.store.get_artifact(item['ref']) for item in outcome['fetch']['results']}
    return {**outcome, 'stdout': files['stdout.log'].decode(), 'stderr': files['stderr.log'].decode(),
            'returncode': json.loads(files['result.json'])['returncode']}


__all__ = ['execute_on_local_resource']
