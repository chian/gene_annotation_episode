"""Independent execution of an existing parent-owned child invocation.

This is the in-process execution primitive, not a scheduler or durable process
backend. Child work uses Episode.run_async, its own controller and an isolated
Context stack. Delivery uses the ordinary closed-result/report boundary.
"""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass

from .episode import ClosedRecord, _require_closed_record, _receive_closed_child_async


@dataclass(frozen=True)
class _ArchivedResult(ClosedRecord):
    reference: object
    identifiers: tuple[str, ...]

    def as_record(self):
        return self.reference.load()

    def audit_identifiers(self):
        return self.identifiers


async def _run_child(child, context):
    record = await child.run_async(context)
    result = child.build_result(record)
    if inspect.isawaitable(result):
        result = await result
    result = _require_closed_record(result, 'Episode.build_result()')
    if child.archive_record is not None:
        # Closed history leaves active memory even before a parent collects it.
        record = record.archived(child.archive_record)
        result = _ArchivedResult(child.archive_record(result), result.audit_identifiers())
    return record, result


class IndependentChild:
    """A pending invocation, acquired once by its assigning active parent.

    Status contains no child work, interpretation or private trace. Waiting for
    readiness does not deliver a report or observe a completed parent action.
    Cancelling a wait/receiver does not cancel the independent child. When the
    Python event loop itself exits, this backend cannot keep a task alive;
    durable independent processes are a separate binding requirement.
    """
    def __init__(self, unit, parent_context, child_context, *, handle):
        if not isinstance(handle, str) or not handle:
            raise ValueError('independent child requires a semantic execution handle')
        self.handle, self.label = handle, unit.label
        self._owner_path = parent_context.path
        self._owner_goal = parent_context._active_episodes[self._owner_path].goal.goal_id
        self._run_id = parent_context.require_run_id()
        self._request = unit.child.request
        self._receive_result, self._synthesize_report = unit.receive_result, unit.synthesize_report
        self._delivered = False
        self._receiving = False
        self._task = asyncio.create_task(_run_child(unit.child, child_context))
        parent_context._independent_invocations.setdefault(self._owner_path, []).append(self)

    def _release_receiver(self):
        # Projection closures may capture a parent's live source/history. A
        # yielded parent cannot receive again; keep the child's result/task,
        # contract and identity, but release those no-longer-usable closures.
        self._receive_result = self._synthesize_report = None

    def status(self):
        if not self._task.done():
            state = 'running'
        elif self._task.cancelled():
            state = 'interrupted'
        elif self._task.exception() is not None:
            state = 'failed'
        else:
            state = 'returned'
        return {'handle': self.handle, 'state': state, 'delivered': self._delivered}

    async def wait_ready(self):
        await asyncio.shield(self._task)
        return self.status()

    def _validate_receiver(self, context):
        parent = context._active_episodes.get(context.path)
        if (context.path != self._owner_path or context.require_run_id() != self._run_id
                or parent is None or parent.goal.goal_id != self._owner_goal):
            raise ValueError('independent result requires its assigning active parent')

    async def acquire_async(self, context):
        self._validate_receiver(context)
        if self._delivered or self._receiving:
            raise ValueError('independent child result already received or receiving')
        self._receiving = True
        try:
            record, result = await asyncio.shield(self._task)
            self._validate_receiver(context)
            acquired = await _receive_closed_child_async(record, result, self._request,
                self._receive_result, self._synthesize_report)
            context._receive_child_update(acquired.contribution.episode_update)
            self._delivered = True
            self._release_receiver()
            return acquired
        finally:
            self._receiving = False

    def acquire(self, context):
        raise TypeError('independent child delivery requires the async method loop')
