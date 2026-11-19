"""Immutable identity and assignment view of one episode for library calls."""
from __future__ import annotations

from dataclasses import dataclass
import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class BindingContext:
    """Immutable identity/assignment view of one episode."""

    run_id: str
    episode_id: str
    role: str
    path: tuple[tuple[str, str], ...]
    scope: Mapping[str, Any]
    assignment: Mapping[str, Any]
    request: Mapping[str, Any]
    received_record_refs: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ('run_id', 'episode_id', 'role'):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f'nonempty_{name}_required')
        path = tuple(tuple(part) for part in self.path)
        if (not path or any(len(part) != 2 or any(not isinstance(item, str) or not item
                for item in part) for part in path) or path[-1][0] != self.role):
            raise ValueError('binding_context_path_must_match_role')
        object.__setattr__(self, 'path', path)
        if (not isinstance(self.received_record_refs, (tuple, list))
                or any(not isinstance(ref, str) or not ref for ref in self.received_record_refs)):
            raise ValueError('received_record_refs_must_be_explicit_references')
        object.__setattr__(self, 'received_record_refs', tuple(self.received_record_refs))
        for name in ('scope', 'assignment', 'request'):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise TypeError(f'{name}_must_be_mapping')
            # Preserve JSON values while preventing bindings from changing the
            # original assignment through a borrowed mutable dictionary.
            normalized = json.loads(json.dumps(_plain(value), allow_nan=False))
            object.__setattr__(self, name, _freeze(normalized))

    def as_record(self):
        return {name: _plain(getattr(self, name)) for name in
                ('run_id', 'episode_id', 'role', 'path', 'scope', 'assignment', 'request')}


__all__ = ['BindingContext']
