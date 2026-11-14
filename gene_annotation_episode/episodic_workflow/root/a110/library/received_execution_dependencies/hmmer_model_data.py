from __future__ import annotations
import re
OCCURRENCE_FIELDS = frozenset({'occurrence_id', 'direction', 'role', 'ordinal', 'artifact_ref', 'sha256', 'size_bytes', 'completeness'})

def _occurrence_valid(occurrence):
    if not isinstance(occurrence, dict) or occurrence.keys() != OCCURRENCE_FIELDS:
        return False
    if any((type(occurrence[key]) is not str or not occurrence[key] for key in ('occurrence_id', 'role', 'artifact_ref'))):
        return False
    return isinstance(occurrence['direction'], str) and occurrence['direction'] in {'input', 'output'} and isinstance(occurrence['completeness'], str) and (occurrence['completeness'] in {'complete', 'partial', 'unknown'}) and (type(occurrence['ordinal']) is int) and (occurrence['ordinal'] >= 0) and (type(occurrence['size_bytes']) is int) and (occurrence['size_bytes'] >= 0) and isinstance(occurrence['sha256'], str) and (re.fullmatch('[0-9a-fA-F]{64}', occurrence['sha256']) is not None)
