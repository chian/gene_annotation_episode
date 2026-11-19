"""A closed JSON record value for the method loop (requests' messages, controller inputs, results).

``closed_record(value, audit_identifiers=())`` returns a ``method_loop.ClosedRecord`` whose ``as_record()`` is a
plain JSON copy of ``value`` (finite numbers only). ``audit_identifiers`` are the bookkeeping identities (for
example a child episode id or an operation key) a parent report must not contain.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json

from method_loop import ClosedRecord


@dataclass(frozen=True)
class _JsonRecord(ClosedRecord):
    text: str
    identifiers: tuple

    def as_record(self):
        return json.loads(self.text)

    def audit_identifiers(self):
        return self.identifiers


def closed_record(value, audit_identifiers=()):
    """A ``ClosedRecord`` of the JSON object ``value``; raises ``ValueError`` for anything not closed JSON."""
    if not isinstance(value, Mapping):
        raise TypeError('closed_record_requires_a_mapping')
    try:
        text = json.dumps(value, sort_keys=True, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise ValueError('closed_record_must_be_closed_json') from error
    if not isinstance(audit_identifiers, (tuple, list)) or any(
            type(item) is not str or not item for item in audit_identifiers):
        raise TypeError('closed_record_audit_identifiers_must_be_nonempty_text')
    return _JsonRecord(text, tuple(audit_identifiers))


__all__ = ['closed_record']
