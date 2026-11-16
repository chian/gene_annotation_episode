"""Caller-owned selection of statistical inputs for particular episode types.

This is not an estimator, credit projector, job monitor or report composer.
Only the fixed run-statistics interface crosses from global history. Decisions
and completed-action contexts persist the returned snapshots locally for replay.
"""
from dataclasses import asdict
from pathlib import Path
import sqlite3
from types import MappingProxyType

from .run_statistics import ExecutionClass, RunHistory


VERSION = "episode_execution_expectation_binding_v3"


def capture_execution_scopes(path, scopes, *, assigned_execution_class_ref=None):
    """Freeze caller-bound exact scopes without creating a statistical store.

    This infrastructure helper captures only typed execution statistics. A
    missing history is information for the episode, never permission to stop
    its selected work. Existing snapshots are immutable and can be journaled
    with the decision that used them.
    """
    scopes = tuple(scopes)
    if any(type(scope) is not ExecutionClass for scope in scopes):
        raise TypeError('execution_expectations_require_typed_execution_classes')
    if len({scope.ref for scope in scopes}) != len(scopes):
        raise ValueError('duplicate_execution_expectation_class')
    if assigned_execution_class_ref is not None and assigned_execution_class_ref not in {scope.ref for scope in scopes}:
        raise ValueError('assigned_execution_class_not_in_supplied_scopes')
    metadata = {'version': VERSION, 'execution_classes': [asdict(scope) for scope in scopes]}
    if assigned_execution_class_ref is not None:
        metadata['assigned_execution_class_ref'] = assigned_execution_class_ref
    history = None
    try:
        history_path = Path(path).expanduser().resolve()
        if not history_path.is_file():
            return {**metadata, 'status': 'unavailable', 'code': 'history_unavailable', 'snapshots': []}
        history = RunHistory(history_path, create=False)
        snapshots = []
        for scope in scopes:
            ref = history.capture(scope)
            reader = history.reader(ref)
            try:
                snapshots.append({'ref': ref, 'data': reader.get(ref)})
            finally:
                reader.close()
        return {**metadata, 'status': 'available', 'code': None, 'snapshots': snapshots}
    except (OSError, sqlite3.Error):
        return {**metadata, 'status': 'unavailable', 'code': 'history_unavailable', 'snapshots': []}
    except (ValueError, KeyError, TypeError):
        return {**metadata, 'status': 'invalid_statistics', 'code': 'invalid_statistics', 'snapshots': []}
    finally:
        if history is not None:
            history.close()


class ExecutionExpectations:
    def __init__(self, path, *, by_grain=None):
        by_grain = {} if by_grain is None else by_grain
        if not isinstance(by_grain, dict) or not by_grain:
            raise ValueError("execution_expectations_require_caller_owned_episode_types")
        bindings = {}
        for name, scopes in by_grain.items():
            if type(name) is not str or not name.isidentifier():
                raise ValueError("invalid_execution_expectation_episode_type")
            if not isinstance(scopes, (tuple, list)) or not scopes or any(type(scope) is not ExecutionClass for scope in scopes):
                raise ValueError("execution_expectations_require_typed_execution_classes")
            if len({scope.ref for scope in scopes}) != len(scopes):
                raise ValueError("duplicate_execution_expectation_class")
            bindings[name] = tuple(scopes)
        self.path = Path(path).expanduser().resolve()
        self.by_grain = MappingProxyType(bindings)

    @property
    def episode_types(self):
        return frozenset(self.by_grain)

    def applies(self, grain):
        return grain in self.episode_types

    def as_record(self):
        return {"version": VERSION, "path": str(self.path),
                "by_grain": {name: [asdict(scope) for scope in scopes]
                             for name, scopes in sorted(self.by_grain.items())}, "homology": None}  # No adapter is assigned to this descriptor field.

    @classmethod
    def from_record(cls, record):
        if (not isinstance(record, dict) or set(record) != {"version", "path", "by_grain", "homology"}
                or record["version"] != VERSION or record["homology"] is not None):
            raise ValueError("unsupported_execution_expectation_binding")
        return cls(record["path"], by_grain={name: [ExecutionClass(**scope) for scope in scopes]
                                           for name, scopes in record["by_grain"].items()})

    def capture(self, grain):
        """No child writes to history; infrastructure freezes statistical views.

        An inaccessible shared database is explicit missing context, not a zero
        duration, permission gate, cancellation or fabricated controller turn.
        No history database is silently created at a missing configured path.
        """
        scopes = list(self.by_grain.get(grain, ()))
        return capture_execution_scopes(self.path, scopes)
