"""Reuse authenticated facts only during one synchronous report form check.

This frame owns no durable state and changes no record, observation or credit.
Providers retain their original authentication and semantic value validators.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
import json
from typing import Callable

from .episode_bindings import BindingContext


@dataclass
class _Frame:
    active: bool = True
    values: dict = field(default_factory=dict)


_current: ContextVar[_Frame | None] = ContextVar("form_reference_validation", default=None)


@contextmanager
def form_reference_validation():
    frame = _Frame()
    token = _current.set(frame)
    try:
        yield
    finally:
        # A copied Context can retain this object after reset in its creator.
        # Invalidate the object itself so that such a copy cannot reuse facts.
        frame.active = False
        frame.values.clear()
        _current.reset(token)


def form_validation_value(key: tuple, produce: Callable[[], dict]) -> dict:
    frame = _current.get()
    if frame is None or not frame.active:
        return produce()
    if key not in frame.values:
        # An exception leaves no remembered value. Keep a private copy rather
        # than a borrowed provider dictionary; callers also receive copies.
        value = deepcopy(produce())
        detached = deepcopy(value)
        frame.values[key] = value
        return detached
    return deepcopy(frame.values[key])


def _binding_key(context):
    """Include every immutable boundary operand, including received references.

    Unsupported duck-typed callers keep their prior factory/error behavior:
    a fresh object disables sharing instead of introducing a new type gate.
    """
    if type(context) is not BindingContext:
        return object()
    return json.dumps([context.as_record(), context.received_record_refs],
        sort_keys=True, separators=(",", ":"), allow_nan=False)
