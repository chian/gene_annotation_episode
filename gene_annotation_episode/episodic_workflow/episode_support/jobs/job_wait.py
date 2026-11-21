"""The wait runner: the one library function behind every episode's ``wait`` action.

An episode that holds the handoff row of a job may offer its model the action ``wait``. The action has two parts,
kept apart so that one can change without the other:

1. **The action format** is the episode's own: the schema the model answers against, in the episode's ``task.py``
   (``{"action": "wait", "seconds": <a number in the range of the episode's settings>}``; see
   ``docs/axis_restructure_20261117/WAIT_ACTION.md``).
2. **The runner** is this function. The episode's ``wait`` tool calls it and nothing else. It does the waiting and
   returns the current state of the job, read through ``job_access.check``.

Today the runner waits a set time. The tool unit that calls it is journaled by the system like any unit, so a run
that is resumed replays the finished unit and does not wait again; a unit that was cut while it waited runs again.
A later runner may wait on a job event (the ``native_events`` service) instead: it replaces the body of this
function, with the same return, and no episode changes.

The episode declares ``'job_access'`` in its ``SERVICES``. The check row of the status request is written through
``ctx.store`` by the service, so the Episode holds it as produced by the unit. A wait earns what the calling
episode's ``credit.py`` gives it, which is nothing where the owner's rule is followed.
"""
from __future__ import annotations

import asyncio


async def wait_for_job(ctx, handoff_ref, *, seconds):
    """Wait ``seconds``, then make one status request for the job of the held handoff row ``handoff_ref``.

    Returns what ``JobAccess.check`` returns (``{'status': 'completed', 'job', 'resource_id', 'state',
    'result_available', 'observed_at', 'assessment', 'replayed', 'check_ref', 'reply_ref'}``, or ``{'status':
    'failed', 'job', 'resource_id', 'failure': {'code', 'detail'}}`` when the resource refuses the request) with
    ``'waited_seconds': seconds`` added."""
    await asyncio.sleep(seconds)
    return {**ctx.services['job_access'].check(ctx, handoff_ref), 'waited_seconds': seconds}


__all__ = ['wait_for_job']
