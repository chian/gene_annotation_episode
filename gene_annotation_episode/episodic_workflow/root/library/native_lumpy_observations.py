"""LUMPY host observations and bounded original output custody.

Original output declarations and read ports remain on the host, outside the
current worker's deployed source closure.
"""
from __future__ import annotations
import base64
import os
from pathlib import Path
from .native_lumpy_execution import validate_lumpy_run_plan, require


def lumpy_observed_files(plan, view, *, log_window_bytes, log_roles):
    from .native_atac_differential_observations import _detail
    plan = validate_lumpy_run_plan(plan)
    require(type(log_window_bytes) is int and log_window_bytes > 0, 'positive_log_window_required')
    require(type(log_roles) in (tuple, list) and all(type(role) is str for role in log_roles)
        and len(set(log_roles)) == len(log_roles) and set(log_roles) <= {'stdout', 'stderr'}, 'unsupported_native_log_role')
    require(type(view) is dict and type(view.get('terminal')) is bool, 'native_terminal_observation_required')
    directory, root = Path(plan['attempt_directory']), Path(plan['identity']['execution_id']).parent
    outputs, logs, result_available = [], [], False
    for spec in plan['outputs']:
        role = spec['role'];is_log = role == 'stderr'
        limit = log_window_bytes if is_log and role in log_roles else None
        detail = _detail(directory, spec['relative_path'], tail_limit=limit)
        if is_log and not detail['available']:
            detail = _detail(root, role + '.log', tail_limit=limit)
        semantic_role = 'bam_header:' + spec['file_key'].removeprefix('header:') if role == 'bam_header' else role
        outputs.append(dict(role=semantic_role, available=detail['available'],
            bytes=detail.get('bytes'), writer_closed=detail['available'] and view['terminal'] and view.get('quiescent') is True))
        result_available |= role == 'seal' and detail['available']
        if is_log and role in log_roles and detail['available']:
            logs.append(dict(role=role, path=detail['path'], offset=detail['tail_byte_offset'],
                observed_size=detail['bytes'], bytes_base64=detail['bytes_base64']))
    if 'stdout' in log_roles:
        detail = _detail(root, 'stdout.log', tail_limit=log_window_bytes)
        outputs.append(dict(role='stdout', available=detail['available'], bytes=detail.get('bytes'),
            writer_closed=detail['available'] and view['terminal'] and view.get('quiescent') is True))
        if detail['available']:
            logs.append(dict(role='stdout', path=detail['path'], offset=detail['tail_byte_offset'],
                observed_size=detail['bytes'], bytes_base64=detail['bytes_base64']))
    return outputs, logs, result_available


def read_lumpy_output(plan, *, path, offset, limit):
    from gene_annotation_episode.native_file_capture import _path, _producer_file
    plan = validate_lumpy_run_plan(plan)
    require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 1024 * 1024, 'bounded_native_output_window_required')
    target = _path(path, absolute=True);directory = _path(plan['attempt_directory'], absolute=True)
    root = _path(str(Path(plan['identity']['execution_id']).parent), absolute=True)
    allowed = {str(directory / row['relative_path']): (directory, row['relative_path']) for row in plan['outputs']}
    allowed.update({str(root / (role + '.log')): (root, role + '.log') for role in ('stdout', 'stderr')})
    require(str(target) in allowed, 'native_lumpy_original_output_path_required')
    owner, relative = allowed[str(target)]
    with _producer_file(owner, _path(relative, absolute=False)) as pinned:
        with pinned.open('rb') as stream:
            size = os.fstat(stream.fileno()).st_size
            stream.seek(offset);raw = stream.read(min(limit, max(0, size - offset)))
    return dict(path=str(target), offset=offset, returned_bytes=len(raw), size_bytes=size,
        bytes_base64=base64.b64encode(raw).decode('ascii'), text_utf8=raw.decode('utf-8', errors='replace'))


