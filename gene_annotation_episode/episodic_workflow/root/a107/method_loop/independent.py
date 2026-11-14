"""Independent execution of an existing parent-owned child invocation.

This is the in-process execution primitive, not a scheduler or durable process
backend. Child work uses Episode.run_async, its own controller and an isolated
Context stack. Delivery uses the ordinary closed-result/report boundary.
"""
from __future__ import annotations

import asyncio
import inspect
from contextlib import nullcontext
from datetime import datetime, timezone
from dataclasses import dataclass, replace

from .episode import (ClosedRecord, Contribution, _AcquiredUnit,
    _require_closed_record, _receive_closed_child_async)


@dataclass(frozen=True)
class _ArchivedResult(ClosedRecord):
    reference: object
    identifiers: tuple[str, ...]

    def as_record(self):
        return self.reference.load()

    def audit_identifiers(self):
        return self.identifiers


async def _run_child(child, context, *, accounting_only=False):
    record = (await child.resume_owned_accounting_async(context) if accounting_only
        else await child.run_async(context))
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
        self._delivery_contract = unit.delivery_contract
        self._receive_failure = unit.receive_failure
        self._child_context = child_context
        self._child = unit.child
        self._accounting_recovery_started = False
        self._child_path = (*parent_context.path, (unit.child.grain.name, unit.child.key))
        self.decision_index = getattr(unit, 'decision_index', None)
        self._suspension = child_context._suspension
        self.role = unit.child.grain.name
        self.selected_at = datetime.now(timezone.utc).isoformat()
        self._collection_measure = getattr(unit, 'collection_measure', None)
        self._collection_returned = getattr(unit, 'collection_returned', None)
        self._released_for_wait = False
        self._delivered = False
        self._receiving = False
        self._acquired = None
        self._task = asyncio.create_task(_run_child(unit.child, child_context))
        parent_context._independent_invocations.setdefault(self._owner_path, []).append(self)

    def _release_receiver(self):
        # Release only after the original parent has received this invocation.
        self._receive_result = self._synthesize_report = None
        self._delivery_contract = None
        self._collection_measure = None
        self._collection_returned = None
        self._receive_failure = None
        self._child = None

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

    async def wait_until_return_or_suspension(self):
        suspended = asyncio.create_task(self._suspension.suspended.wait())
        try:
            await asyncio.wait([self._task, suspended], return_when=asyncio.FIRST_COMPLETED)
            self._released_for_wait = not self._task.done()
            return self._task.done()
        finally:
            suspended.cancel()
            await asyncio.gather(suspended, return_exceptions=True)

    def _validate_receiver(self, context):
        parent = context._active_episodes.get(context.path)
        if (context.path != self._owner_path or context.require_run_id() != self._run_id
                or parent is None or parent.goal.goal_id != self._owner_goal):
            raise ValueError('independent result requires its assigning active parent')

    async def _await_owned_return(self, context):
        try:
            while not self._task.done():
                changed = self._suspension.changed()
                try:
                    context._suspension.update({'kind': 'owned_child_return', 'handles': [self.handle]}
                        if self._suspension.condition is not None else None)
                    await asyncio.wait([self._task, changed], return_when=asyncio.FIRST_COMPLETED)
                finally:
                    changed.cancel()
            return await asyncio.shield(self._task)
        finally:
            context._suspension.update(None)

    async def acquire_async(self, context):
        self._validate_receiver(context)
        if self._delivered or self._receiving:
            raise ValueError('independent child result already received or receiving')
        if self._acquired is not None:
            return self._acquired
        self._receiving = True
        try:
            try:
                record, result = await self._await_owned_return(context)
            except Exception as error:
                owns_unfinished = self._child_context._has_owned_work(self._child_path)
                if owns_unfinished:
                    if self._accounting_recovery_started:
                        raise
                    # Keep the same live receiver and its existing controller,
                    # records and selected children. This task only accounts
                    # owned returns; it cannot request new scientific actions.
                    self._accounting_recovery_started = True
                    self._task = asyncio.create_task(_run_child(self._child,
                        self._child_context, accounting_only=True))
                    record, result = await self._await_owned_return(context)
                else:
                    if self._receive_failure is None:
                        raise
                    value = self._receive_failure(error)
                    if inspect.isawaitable(value):
                        value = await value
                    value = _require_closed_record(value, 'child failure projection')
                    self._acquired = _AcquiredUnit(Contribution(value), confirm_observed=self.confirm_observed)
                    return self._acquired
            self._validate_receiver(context)
            with (self._collection_measure() if self._released_for_wait
                    and self._collection_measure is not None else nullcontext()):
                acquired = await _receive_closed_child_async(record, result, self._request,
                    self._receive_result, self._synthesize_report,
                    delivery_contract=self._delivery_contract)
            context._receive_child_update(acquired.contribution.episode_update)
            self._acquired = replace(acquired, confirm_observed=self.confirm_observed)
            if self._released_for_wait and self._collection_returned is not None:
                self._collection_returned()
            return self._acquired
        finally:
            self._receiving = False

    def confirm_observed(self):
        if self._acquired is None:
            raise ValueError('original child acquisition must precede its observation')
        self._delivered = True
        self._acquired = None
        self._release_receiver()

    def acquire(self, context):
        raise TypeError('independent child delivery requires the async method loop')
