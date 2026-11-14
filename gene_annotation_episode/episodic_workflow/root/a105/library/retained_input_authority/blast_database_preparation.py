"""Pure makeblastdb artifact population and existing prepared-manifest projection.

This supporting operation produces no scientific score. All file facts are
supplied occurrences from the original attempt: this module never opens a path,
enumerates a directory, launches a command, or invents a native measurement.
"""
from __future__ import annotations
from pathlib import PurePosixPath

def _failure(code, *, stage='validation', occurrence_id=None, native_returncode=None):
    return {'stage': stage, 'code': code, 'occurrence_id': occurrence_id, 'record_key': None, 'line_number': None, 'native_returncode': native_returncode}

def _check(name, status, *, subject_refs, method, reason=None, occurrences=()):
    return {'name': name, 'status': status, 'subject_refs': list(subject_refs), 'method': method, 'reason': reason, 'evidence_occurrence_ids': list(occurrences)}

def _native_file_path(value, occurrence):
    """Resolve a native filename only against its own supplied source location."""
    if not value or any((c in value for c in ('\x00', '\n', '\r'))) or '..' in value.split('/') or (str(PurePosixPath(value)) != value):
        return None
    if value.startswith('/'):
        return value if not value.startswith('//') else None
    source = None if occurrence is None else occurrence['native_path']
    if source is None:
        return None
    return str(PurePosixPath(source).parent / value)
