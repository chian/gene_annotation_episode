"""Finite retained-file parsing/projection, with no Store or native dispatch."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from .atac_differential_inputs import (
    parse_macs2_peaks_xls, parse_macs2_narrowpeak, parse_macs2_summits_bed,
)
from .atac_differential_contracts import issue
from .atac_differential_result_contracts import canonical, validate_atac_result_record
from .macs2_peak_components import build_macs2_peak_components
from .macs2_peak_result_contracts import project_macs2_peak_values
from .native_atac_differential_driver import _regular, decode_json
from .native_file_capture import _identity
from .native_macs2_peak_execution import (
    validate_macs2_peak_run_plan, validate_macs2_peak_seal, macs2_peak_callpeak_binding,
)
from .native_atac_differential_contracts import failure, unique_failures


REQUEST_VERSION = 'macs2_peak_worker_request_v1'
RESULT_VERSION = 'macs2_peak_worker_result_v1'
COMPONENT_FORMAT = 'macs2_peak_components_v1'
_PARSERS = {
    'peaks_xls': ('peaks_xls', 'macs2_peaks_xls_narrow', parse_macs2_peaks_xls),
    'narrowpeak': ('narrowpeaks', 'macs2_narrowpeak10', parse_macs2_narrowpeak),
    'summits': ('summits', 'macs2_summits_bed5', parse_macs2_summits_bed),
}


def _require(condition, code):
    if not condition:
        raise ValueError('macs2_peak_worker_' + code)


def _file_path(file, path):
    file = _identity(file)
    selected = Path(path)
    _require(selected.is_absolute() and str(selected) == path and
        selected.parts[-3:] == ('artifacts', file['sha256'][:2], file['sha256']), 'file_custody_conflict')
    _require(file['artifact_ref'] == 'artifact_' + file['sha256'], 'file_identity_conflict')
    return file, selected


def _parse(native):
    _require(type(native) is dict and set(native) == {'plan', 'seal', 'roles'}, 'native_fields_invalid')
    plan = validate_macs2_peak_run_plan(native['plan'])
    seal = validate_macs2_peak_seal(native['seal'], plan=plan)
    binding = macs2_peak_callpeak_binding(plan, seal)
    request = plan['requested_job']['native_macs2_peak']['request']
    declared = {row['specification']['role']: row for row in seal['outputs']}
    _require(type(native['roles']) is list, 'roles_invalid')
    roles = {}
    for row in native['roles']:
        _require(type(row) is dict and set(row) == {
            'specification', 'source_ref', 'file', 'path', 'availability', 'qualification'}, 'role_fields_invalid')
        role = row['specification']['role']
        _require(role not in roles and row['specification'] in plan['outputs'], 'role_association_conflict')
        roles[role] = row
    sample = next(row for row in request['samples'] if row['sample_id'] == binding['sample_ids'][0])
    parsed, failures = {}, deepcopy(seal['failures'])
    for selected in roles.values():
        qualification = selected['qualification']
        code = None if qualification is None else qualification['code']
        if code in ('native_output_identity_conflict', 'selected_output_unavailable'):
            failures.append(failure('artifact_digest_mismatch' if code == 'native_output_identity_conflict'
                else 'native_output_unavailable', 'capture', file_key=selected['specification']['file_key'],
                artifact_ref=None if selected['file'] is None else selected['file']['artifact_ref'],
                requirement='matching_file_identity'))
    for role, (field, fmt, parser) in _PARSERS.items():
        specification, declaration = declared[role]['specification'], declared[role]['declaration']
        selected = roles.get(role)
        conflict = selected is not None and selected['qualification'] == {'code': 'native_output_identity_conflict'}
        available = selected is not None and selected['file'] is not None and selected['availability'] == 'retained' and not conflict
        if available:
            file, path = _file_path(selected['file'], selected['path'])
            conflict = (declaration['state'] != 'present' or selected['specification'] != specification
                or file['format'] != fmt or any(file[key] != declaration[key] for key in ('sha256', 'size_bytes')))
            if conflict:
                available, path = False, None
                failures.append(failure('artifact_digest_mismatch', 'capture', file_key=specification['file_key'],
                    artifact_ref=file['artifact_ref'], requirement='matching_file_identity'))
        else:
            path = None
        descriptor = dict(artifact_ref=binding['artifact_roles'][role], format=fmt,
            expected_sha256=declaration['sha256'], expected_size_bytes=declaration['size_bytes'],
            supplied_extent='complete' if seal['outcome'] == 'succeeded' else
                'partial' if declaration['state'] == 'present' else 'unknown',
            producer_run_ref=seal['producer_ref'], producer_outcome=seal['outcome'],
            writer_closed=True, producer_name='MACS2', producer_version='2.2.9.1',
            producer_source_ref=None if selected is None else selected['source_ref'], origin=sample['origin'])
        if path is None:
            report = parser(None, artifact=descriptor, callpeak=binding, parse_profile='matched_control_native_model')
        else:
            try:
                with _regular(path) as stream:
                    report = parser(stream, artifact=descriptor, callpeak=binding,
                        parse_profile='matched_control_native_model')
            except OSError:
                report = parser(None, artifact=descriptor, callpeak=binding,
                    parse_profile='matched_control_native_model')
        parsed[field] = [report]
        if conflict:
            report['issues'].append(issue('metadata_conflict', selected['file']['artifact_ref'], binding['run_key'],
                field='native_output_identity_conflict', requirement='matching_artifact'))
    components = build_macs2_peak_components(reference=request['reference'], callpeak_bindings=[binding],
        **parsed, parse_profile='matched_control_native_model')
    return components, seal['outcome'], unique_failures(failures)


def _saved(value):
    _require(type(value) is dict and set(value) == {'file', 'path', 'native_outcome', 'failures'},
        'saved_fields_invalid')
    file, path = _file_path(value['file'], value['path'])
    _require(file['format'] == COMPONENT_FORMAT, 'component_format_invalid')
    with _regular(path) as stream:
        raw = stream.read()
    _require(len(raw) == file['size_bytes'] and hashlib.sha256(raw).hexdigest() == file['sha256'],
        'saved_identity_conflict')
    components = validate_atac_result_record('NativePeakComponents', decode_json(raw))
    return components, value['native_outcome'], deepcopy(value['failures'])


def run_macs2_peak_result_job(*, request, output_directory):
    _require(type(request) is dict and set(request) == {'version', 'mode', 'row_window', 'native', 'saved'}
        and request['version'] == REQUEST_VERSION, 'request_invalid')
    directory = Path(output_directory)
    _require(directory.is_absolute() and directory.is_dir(), 'output_directory_invalid')
    if request['mode'] == 'parse':
        _require(request['saved'] is None, 'mode_conflict')
        components, native_outcome, failures = _parse(request['native'])
        raw = canonical(components)
        raw = raw.encode('utf-8') if isinstance(raw, str) else raw
        with (directory / 'components.json').open('xb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        declaration = dict(relative_path='components.json', format=COMPONENT_FORMAT,
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    else:
        _require(request['mode'] == 'project_saved' and request['native'] is None, 'mode_invalid')
        components, native_outcome, failures = _saved(request['saved'])
        declaration = None
    value = project_macs2_peak_values(components, native_outcome=native_outcome,
        row_window=request['row_window'], failures=failures)
    return dict(version=RESULT_VERSION, value=value, components=declaration)


__all__ = ['REQUEST_VERSION', 'RESULT_VERSION', 'COMPONENT_FORMAT', 'run_macs2_peak_result_job']
