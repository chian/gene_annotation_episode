"""Case- and occurrence-preserving readers for supplied masking artifacts.

All I/O is outside these functions. Hash checks bind the supplied bytes to their
descriptor; authentication of the producer is the host's responsibility.
"""
from __future__ import annotations

def _failure(stage, code, occurrence_id=None, record_key=None, line_number=None):
    return {'stage': stage, 'code': code, 'occurrence_id': occurrence_id, 'record_key': record_key, 'line_number': line_number}

def _check(name, status, record_key=None, reason=None):
    return {'name': name, 'status': status, 'record_key': record_key, 'reason': reason}
