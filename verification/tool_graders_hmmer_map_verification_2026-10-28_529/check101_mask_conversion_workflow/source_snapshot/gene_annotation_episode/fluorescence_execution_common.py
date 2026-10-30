"""Small, pure control records for supplied-fluorescence execution.

Control digests use UTF-8 text. Numerical artifacts retain the independent
ASCII-escaped canonical representation in fluorescence_event_contracts.
"""
from copy import deepcopy
import hashlib
import json
import re
import unicodedata


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def same(left, right):
    return canonical(left) == canonical(right)


def require(condition, code):
    if not condition:
        raise ValueError(code)


def closed(value, keys):
    require(type(value) is dict and set(value) == set(keys.split() if type(keys) is str else keys),
        'invalid_fluorescence_contract')


def unique(rows):
    require(type(rows) is list, 'invalid_fluorescence_contract')
    seen, result = set(), []
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


def identity(raw, *, format):
    require(type(raw) is bytes and type(format) is str and bool(format)
        and not any(unicodedata.category(c) == 'Cc' for c in format), 'invalid_fluorescence_file')
    sha = hashlib.sha256(raw).hexdigest()
    return {'artifact_ref': 'artifact_' + sha, 'sha256': sha, 'size_bytes': len(raw), 'format': format}


FAILURE_CODES = tuple('''input_file_unavailable input_identity_mismatch
capture_file_unavailable capture_file_digest_mismatch manifest_missing_or_malformed
native_manifest_conflict parsed_batch_unavailable parsed_batch_invalid
original_execution_mismatch native_software_mismatch worker_nonzero_exit
worker_resource_failure worker_output_unavailable worker_output_malformed
worker_execution_mismatch saved_sheet_incompatible projection_contract_invalid
preparation_unavailable preparation_incompatible preparation_failed
report_batch_unavailable report_batch_invalid'''.split())
FAILURE_STAGES = ('input', 'capture', 'authority', 'worker', 'projection')
_ROLES = {'manifest', 'sheet', 'calculations', 'projection', 'context', 'diagnostics',
    'worker_result', 'worker_execution'}


def validate_failure(value):
    closed(value, 'code stage input_index role')
    require(type(value['code']) is str and value['code'] in FAILURE_CODES
        and type(value['stage']) is str and value['stage'] in FAILURE_STAGES,
        'invalid_fluorescence_failure')
    index, role = value['input_index'], value['role']
    require(index is None or type(index) is int and index >= 0, 'invalid_fluorescence_failure')
    match = re.fullmatch(r'(?:event_input|support_input|event_batch|report_input|preparation_parameters|prepared_data|prepared_batch|report_batch):(0|[1-9][0-9]*)', role) if type(role) is str else None
    require(role is None or type(role) is str and (role in _ROLES or match is not None),
        'invalid_fluorescence_failure')
    if match is not None:
        require(type(index) is int and str(index) == match.group(1), 'invalid_fluorescence_failure')
    canonical(value)
    return deepcopy(value)
