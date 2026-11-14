"""Nonterminal external waits inside an owned episode invocation.

Waiting changes scheduling state only. It supplies neither a result nor an
iterator observation, and never closes the waiting episode or its receiver.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar


_receiver = ContextVar('episode_wait_receiver', default=None)


class SuspensionState:
    def __init__(self):
        self.condition = None
        self.suspended = asyncio.Event()
        self.listener = None
        self._changes = set()

    def update(self, condition):
        self.condition = condition
        if condition is None:
            self.suspended.clear()
        else:
            self.suspended.set()
        if self.listener is not None:
            self.listener(condition)
        for future in tuple(self._changes):
            if not future.done():
                future.set_result(None)
        self._changes.clear()

    def changed(self):
        future = asyncio.get_running_loop().create_future()
        self._changes.add(future)
        future.add_done_callback(self._changes.discard)
        return future

    @contextmanager
    def bind(self, listener=None):
        prior = self.listener
        self.listener = listener
        token = _receiver.set(self)
        try:
            yield
        finally:
            _receiver.reset(token)
            self.listener = prior


async def external_wait(awaitable, condition):
    """Release a live branch only for its actual selected external dependency."""
    state = _receiver.get()
    if state is not None:
        state.update(condition)
    try:
        return await awaitable
    finally:
        if state is not None:
            state.update(None)
