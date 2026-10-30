"""Selected factual NMF file/log observations; no scientific array loading."""
import base64
import os
from pathlib import Path

from .expression_nmf_common import require
from .native_expression_nmf_contracts import validate_expression_nmf_run_plan
from .native_expression_nmf_storage import confined_file, regular


def _detail(path, *, limit=None):
    try:
        with regular(path) as stream:
            size = os.fstat(stream.fileno()).st_size
            result = {'available': True, 'bytes': size}
            if limit is not None:
                offset = max(0, size-limit)
                stream.seek(offset)
                result.update(offset=offset, bytes_base64=base64.b64encode(stream.read(limit)).decode('ascii'))
            return result
    except FileNotFoundError:
        return {'available': False, 'bytes': None}


def expression_nmf_observed_files(plan, view, *, log_window_bytes, log_roles):
    plan = validate_expression_nmf_run_plan(plan)
    require(type(log_window_bytes) is int and log_window_bytes > 0, 'positive_log_window_required')
    require(type(log_roles) in (tuple, list) and all(r in ('stdout', 'stderr') for r in log_roles)
        and len(set(log_roles)) == len(log_roles), 'unsupported_native_log_role')
    require(type(view) is dict and type(view.get('terminal')) is bool, 'native_terminal_observation_required')
    attempt, root = Path(plan['attempt_directory']), Path(plan['identity']['execution_id']).parent
    outputs, logs, available = [], [], False
    for row in plan['outputs']:
        path = confined_file(attempt, row['relative_path'])
        detail = _detail(path)
        outputs.append({'role': 'requested_output:' + str(path), **detail,
            'writer_closed': detail['available'] and view['terminal']})
        available |= row['role'] == 'manifest' and detail['available']
    for role in ('stdout', 'stderr'):
        path = confined_file(root, role + '.log')
        detail = _detail(path, limit=log_window_bytes if role in log_roles else None)
        outputs.append({'role': role, 'available': detail['available'], 'bytes': detail['bytes'],
            'writer_closed': detail['available'] and view['terminal']})
        if role in log_roles and detail['available']:
            logs.append({'role': role, 'path': str(path), 'offset': detail['offset'],
                'observed_size': detail['bytes'], 'bytes_base64': detail['bytes_base64']})
    return outputs, logs, available


def read_expression_nmf_output(plan, *, path, offset, limit):
    plan = validate_expression_nmf_run_plan(plan)
    require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 1024*1024,
        'bounded_native_output_window_required')
    attempt, root = Path(plan['attempt_directory']), Path(plan['identity']['execution_id']).parent
    allowed = {str(attempt / row['relative_path']): (attempt, row['relative_path']) for row in plan['outputs']}
    allowed.update({str(root / (role + '.log')): (root, role + '.log') for role in ('stdout', 'stderr')})
    require(path in allowed, 'nmf_original_output_path_required')
    base, relative = allowed[path]
    with regular(confined_file(base, relative)) as stream:
        size = os.fstat(stream.fileno()).st_size
        stream.seek(offset)
        raw = stream.read(min(limit, max(0, size-offset)))
    return {'path': path, 'offset': offset, 'returned_bytes': len(raw), 'size_bytes': size,
        'bytes_base64': base64.b64encode(raw).decode('ascii'), 'text_utf8': raw.decode('utf-8', errors='replace')}
