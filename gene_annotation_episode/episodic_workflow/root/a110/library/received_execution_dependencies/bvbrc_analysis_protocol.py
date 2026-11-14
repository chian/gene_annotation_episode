from copy import deepcopy
import json
import math
import re
RPC_METHODS = ('AppService.enumerate_apps', 'AppService.start_app2', 'AppService.query_tasks', 'Workspace.ls', 'Workspace.get', 'Workspace.get_download_url', 'Workspace.create', 'Minhash.compute_genome_distance_for_genome2', 'Minhash.compute_genome_distance_for_fasta2')
_UUID = re.compile('[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\\Z')
_START_STRINGS = frozenset({'parent_id', 'workspace', 'base_url', 'container_id', 'user_metadata', 'reservation', 'data_container_id', 'user_override', 'constraint'})
_META_FIELDS = ('name', 'type', 'parent_path', 'creation_time', 'object_id', 'object_owner', 'size', 'user_metadata', 'automatic_metadata', 'user_permission', 'global_permission', 'shock_url', 'error')

class RPCValidationError(ValueError):
    """Invalid preparation, with stable codes/paths and no serialized operands."""

    def __init__(self, diagnostics):
        self.diagnostics = deepcopy(diagnostics)
        self.code = diagnostics[0]['code']
        super().__init__(self.code)

def _issue(code, path):
    return {'code': code, 'path': path}

def _member(path, key):
    return path + '[' + json.dumps(str(key), ensure_ascii=False) + ']'

def _json_issues(value, path):
    """Require plain finite JSON without coercing keys, tuples or numbers."""
    issues = []

    def visit(item, location):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float:
            if not math.isfinite(item):
                issues.append(_issue('nonfinite_number', location))
        elif type(item) is list:
            for i, child in enumerate(item):
                visit(child, f'{location}[{i}]')
        elif type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    issues.append(_issue('nonstring_json_key', location))
                visit(child, _member(location, key))
        else:
            issues.append(_issue('not_plain_json', location))
    try:
        visit(value, path)
    except RecursionError:
        issues.append(_issue('recursive_or_too_deep_json', path))
    return issues

def _integer(value):
    return type(value) is int

def _flag(value):
    return _integer(value) and value in (0, 1)

def _task_id(value):
    return _integer(value) and value >= 0 or (type(value) is str and re.fullmatch('[0-9]+', value) is not None)

def _rpc_id(value):
    return value is None or type(value) in (str, int) or (type(value) is float and math.isfinite(value))

def _workspace_reference(value, *, listing=False, file=False):
    if type(value) is not str or any((c in value for c in '\x00\r\n')):
        return False
    if _UUID.fullmatch(value):
        return True
    if listing and value in ('', '/'):
        return True
    if not value.startswith('/'):
        return False
    parts = [p for p in value.split('/') if p]
    return len(parts) >= (3 if file else 1 if listing else 2)

def validate_start_parameters(value):
    """Validate explicit native StartParams; no defaults or permission claims.

    ``user_override`` and ``constraint`` are implemented SchedulerDB fields
    beyond the retained spec.  preflight_data is a native JSON object, whose
    actual numeric/nested values are preserved.  Staff authorization for a
    preflight override is the service's responsibility, not a preparer bypass.
    """
    path = '$.start_parameters'
    if type(value) is not dict:
        return [_issue('expected_object', path)]
    issues = _json_issues(value, path)
    for key, operand in value.items():
        location = path + '.' + str(key)
        if key in _START_STRINGS:
            if type(operand) is not str:
                issues.append(_issue('expected_string', location))
        elif key == 'disable_preflight':
            if not _integer(operand):
                issues.append(_issue('expected_integer', location))
        elif key == 'preflight_data':
            if type(operand) is not dict:
                issues.append(_issue('expected_object', location))
        else:
            issues.append(_issue('unknown_start_parameter', location))
    return issues

def _check_references(value, path, issues, *, listing=False):
    if type(value) is not list:
        issues.append(_issue('expected_array', path))
        return
    for i, item in enumerate(value):
        if not _workspace_reference(item, listing=listing):
            issues.append(_issue('invalid_workspace_reference', f'{path}[{i}]'))

def _workspace_options(method, options, issues):
    path = '$.params[0]'
    if type(options) is not dict:
        issues.append(_issue('expected_object', path))
        return
    operation = method.split('.')[1]
    primary = 'paths' if operation == 'ls' else 'objects'
    flags = {'ls': {'excludeDirectories', 'excludeObjects', 'recursive', 'fullHierachicalOutput', 'adminmode'}, 'get': {'metadata_only', 'adminmode'}, 'get_download_url': set(), 'create': {'createUploadNodes', 'downloadLinks', 'downloadFromLinks', 'overwrite', 'adminmode'}}[operation]
    extra = {'query'} if operation == 'ls' else {'permission', 'setowner'} if operation == 'create' else set()
    for key in options:
        if key not in flags | extra | {primary}:
            issues.append(_issue('unknown_workspace_option', path + '.' + str(key)))
    for key in sorted(flags & options.keys()):
        if not _flag(options[key]):
            issues.append(_issue('expected_integer_boolean', path + '.' + key))
    if 'query' in options and type(options['query']) is not dict:
        issues.append(_issue('expected_object', path + '.query'))
    if 'permission' in options and options['permission'] not in ('a', 'w', 'r', 'o', 'n', 'p'):
        issues.append(_issue('invalid_workspace_permission', path + '.permission'))
    if 'setowner' in options and options['setowner'] is not None and (type(options['setowner']) is not str):
        issues.append(_issue('expected_string', path + '.setowner'))
    if options.get('downloadLinks') == 1:
        issues.append(_issue('declared_but_unused_native_option', path + '.downloadLinks'))
    if primary not in options:
        issues.append(_issue('missing_required_operand', path + '.' + primary))
        return
    values = options[primary]
    if operation != 'create':
        _check_references(values, path + '.' + primary, issues, listing=operation == 'ls')
        return
    if type(values) is not list:
        issues.append(_issue('expected_array', path + '.objects'))
        return
    for i, obj in enumerate(values):
        loc = f'{path}.objects[{i}]'
        if type(obj) is not list or not 2 <= len(obj) <= 5:
            issues.append(_issue('invalid_creation_tuple', loc))
            continue
        if not _workspace_reference(obj[0]):
            issues.append(_issue('invalid_workspace_reference', loc + '[0]'))
        if type(obj[1]) is not str or not obj[1]:
            issues.append(_issue('expected_nonempty_string', loc + '[1]'))
        if len(obj) > 2 and obj[2] is not None and (type(obj[2]) is not dict):
            issues.append(_issue('expected_object', loc + '[2]'))
        if len(obj) > 3 and obj[3] is not None and (type(obj[3]) not in (str, list, dict)):
            issues.append(_issue('invalid_object_data', loc + '[3]'))
        if len(obj) > 4 and obj[4] is not None and (type(obj[4]) not in (str, int)):
            issues.append(_issue('invalid_creation_time', loc + '[4]'))

def prepare_rpc_request(method, params, *, request_id):
    """Return a detached exact JSON-RPC 1.1 request, or RPCValidationError.

    Only native operand validation occurs here.  Application-specific inputs
    belong to application preparation.  Workspace type availability, object
    existence and authorization cannot be established by this pure function.
    Native integer booleans are not converted from Python booleans or strings.
    """
    issues = []
    if type(method) is not str or method not in RPC_METHODS:
        issues.append(_issue('unsupported_rpc_method', '$.method'))
    if not _rpc_id(request_id):
        issues.append(_issue('invalid_request_id', '$.id'))
    issues.extend(_json_issues(params, '$.params'))
    arity = {'AppService.enumerate_apps': 0, 'AppService.start_app2': 3, 'AppService.query_tasks': 1}.get(method if type(method) is str else '', 8 if type(method) is str and method.startswith('Minhash.') else 1)
    if type(params) is not list:
        issues.append(_issue('expected_array', '$.params'))
    elif len(params) != arity:
        issues.append(_issue('wrong_parameter_arity', '$.params'))
    elif method == 'AppService.start_app2':
        if type(params[0]) is not str or not params[0]:
            issues.append(_issue('expected_nonempty_string', '$.params[0]'))
        if type(params[1]) is not dict:
            issues.append(_issue('expected_object', '$.params[1]'))
        issues.extend(validate_start_parameters(params[2]))
    elif method == 'AppService.query_tasks':
        if type(params[0]) is not list:
            issues.append(_issue('expected_array', '$.params[0]'))
        else:
            for i, task in enumerate(params[0]):
                if not _task_id(task):
                    issues.append(_issue('invalid_task_id', f'$.params[0][{i}]'))
    elif type(method) is str and method.startswith('Workspace.') and (method in RPC_METHODS):
        _workspace_options(method, params[0], issues)
    elif type(method) is str and method.startswith('Minhash.') and (method in RPC_METHODS):
        if method.endswith('fasta2'):
            valid_input = _workspace_reference(params[0], file=True)
        else:
            valid_input = type(params[0]) is str and re.fullmatch('[0-9]+\\.[0-9]+', params[0]) is not None
        if not valid_input:
            issues.append(_issue('invalid_minhash_input', '$.params[0]'))
        for i in (1, 2):
            if type(params[i]) not in (int, float) or not 0 <= params[i] <= 1:
                issues.append(_issue('invalid_minhash_threshold', f'$.params[{i}]'))
        if not _integer(params[3]) or params[3] < 0:
            issues.append(_issue('invalid_max_hits', '$.params[3]'))
        for i in range(4, 8):
            if not _integer(params[i]):
                issues.append(_issue('expected_integer', f'$.params[{i}]'))
    if issues:
        raise RPCValidationError(issues)
    return {'version': '1.1', 'method': method, 'params': deepcopy(params), 'id': request_id}

def _finish(native, records, issues):
    for row in records:
        row['status'] = 'invalid' if row['diagnostics'] else 'ok'
        issues.extend(row['diagnostics'])
    status = 'ok' if not issues else 'partial' if any((r['status'] == 'ok' for r in records)) else 'invalid'
    return {'status': status, 'records': records, 'native': deepcopy(native), 'diagnostics': issues}

def _normalized_path(path):
    return re.sub('/+', '/', path).rstrip('/') or '/'

def _metadata(raw, path, diagnostics):
    row = {name: None for name in _META_FIELDS}
    row.update(native_metadata=deepcopy(raw), object_path=None)
    if type(raw) is not list:
        diagnostics.append(_issue('invalid_metadata_tuple', path))
        return row
    if len(raw) not in (12, 13):
        diagnostics.append(_issue('invalid_metadata_arity', path))
    for i, name in enumerate(_META_FIELDS):
        if i >= len(raw):
            break
        item = raw[i]
        valid = item is None or (type(item) is dict if i in (7, 8) else _integer(item) and item >= 0 if i == 6 else type(item) is str)
        if valid:
            row[name] = deepcopy(item)
        else:
            diagnostics.append(_issue('invalid_metadata_field', f'{path}[{i}]'))
    for i in (0, 1, 2, 4):
        if not row[_META_FIELDS[i]]:
            diagnostics.append(_issue('missing_object_identity', f'{path}[{i}]'))
    if row['object_id'] and (not _UUID.fullmatch(row['object_id'])):
        diagnostics.append(_issue('invalid_workspace_uuid', path + '[4]'))
    if row['name'] and row['parent_path']:
        if '/' in row['name'] or not row['parent_path'].startswith('/'):
            diagnostics.append(_issue('invalid_object_path', path))
        else:
            row['object_path'] = row['parent_path'].rstrip('/') + '/' + row['name']
    if row['error'] not in (None, ''):
        diagnostics.append(_issue('native_object_error', path + '[12]'))
    return row

def _matches_reference(reference, row):
    if _UUID.fullmatch(reference):
        return reference.lower() == (row['object_id'] or '').lower()
    if reference.startswith('/_uuid/'):
        return None
    return row['object_path'] is not None and _normalized_path(reference) == _normalized_path(row['object_path'])

def parse_workspace_records(value, *, operation, requested_paths=None):
    """Retain positional and path associations for each native Workspace shape.

    create is unordered and may include ancestors: request_indices is computed
    from actual paths/UUIDs, never from row order.  ls keeps each map key and its
    local row_index.  get keeps native positions and checks the metadata against
    the corresponding requested object.  get_download_url carries a URL or null
    per input position; neither proves that any bytes were downloaded.
    """
    records, issues = ([], [])
    if operation not in ('ls', 'get', 'get_download_url', 'create'):
        return _finish(value, [], [_issue('unsupported_workspace_operation', '$.operation')])
    if requested_paths is not None and (type(requested_paths) is not list or any((type(p) is not str for p in requested_paths))):
        return _finish(value, [], [_issue('invalid_requested_paths', '$.requested_paths')])
    if type(value) is not (dict if operation == 'ls' else list):
        return _finish(value, [], [_issue('invalid_workspace_result', '$')])
    entries = []
    if operation == 'ls':
        for key, group in value.items():
            path = _member('$', key)
            if type(key) is not str or type(group) is not list:
                issues.append(_issue('invalid_listing_group', path))
                continue
            entries.extend(((key, i, raw, f'{path}[{i}]') for i, raw in enumerate(group)))
    else:
        entries = [(None, i, raw, f'$[{i}]') for i, raw in enumerate(value)]
    positional = operation in ('get', 'get_download_url')
    if positional and requested_paths is not None and (len(value) != len(requested_paths)):
        issues.append(_issue('response_count_mismatch', '$'))
        for i in range(len(value), len(requested_paths)):
            issues.append(_issue('requested_object_not_returned', f'$.requested_paths[{i}]'))
    for index, (key, row_index, raw, path) in enumerate(entries):
        diagnostics = []
        row = {'record_index': index, 'row_index': row_index, 'listing_path': key, 'request_index': None, 'request_indices': [], 'requested_path': None, 'native_record': deepcopy(raw), 'diagnostics': diagnostics}
        if positional and requested_paths is not None:
            if row_index < len(requested_paths):
                row.update(request_index=row_index, request_indices=[row_index], requested_path=requested_paths[row_index])
            else:
                diagnostics.append(_issue('unrequested_response_position', path))
        if operation == 'get_download_url':
            row['download_url'] = raw if type(raw) is str or raw is None else None
            if raw is not None and (type(raw) is not str or not re.match('https?://[^/\\s]+/', raw)):
                diagnostics.append(_issue('invalid_download_url', path))
        else:
            meta, meta_path = (raw, path)
            if operation == 'get':
                meta = raw[0] if type(raw) is list and raw else None
                meta_path = path + '[0]'
                if type(raw) is not list or len(raw) not in (1, 2):
                    diagnostics.append(_issue('invalid_get_tuple', path))
            row.update(_metadata(meta, meta_path, diagnostics))
            if operation == 'get':
                has_content = type(raw) is list and len(raw) >= 2
                content = raw[1] if has_content else None
                row.update(content=deepcopy(content), content_kind='not_returned')
                if has_content:
                    if content is None:
                        row['content_kind'] = 'native_null'
                    elif type(content) is not str:
                        row['content_kind'] = 'invalid'
                        diagnostics.append(_issue('invalid_object_data', path + '[1]'))
                    elif row['shock_url']:
                        row['content_kind'] = 'shock_url'
                        if content != row['shock_url']:
                            diagnostics.append(_issue('shock_content_url_mismatch', path + '[1]'))
                    elif row['type'] == 'folder':
                        row['content_kind'] = 'directory_placeholder'
                    else:
                        row['content_kind'] = 'inline_text'
                if row['requested_path'] is not None:
                    match = _matches_reference(row['requested_path'], row)
                    if match is False:
                        diagnostics.append(_issue('requested_object_path_mismatch', meta_path))
                    elif match is None:
                        diagnostics.append(_issue('workspace_uuid_mapping_unavailable', meta_path))
            elif requested_paths is not None:
                matches = []
                for i, requested in enumerate(requested_paths):
                    match = _matches_reference(requested, row)
                    if operation == 'ls' and key is not None and (not _UUID.fullmatch(requested)):
                        parent = _normalized_path(requested)
                        match = _normalized_path(key) == parent or bool(row['object_path'] and row['object_path'].startswith(parent.rstrip('/') + '/'))
                    if match:
                        matches.append(i)
                row['request_indices'] = matches
                if len(matches) == 1:
                    row.update(request_index=matches[0], requested_path=requested_paths[matches[0]])
        records.append(row)
    if operation == 'create' and requested_paths is not None:
        for i in range(len(requested_paths)):
            matches = [r for r in records if i in r['request_indices']]
            if not matches:
                issues.append(_issue('requested_object_not_returned', f'$.requested_paths[{i}]'))
            elif len(matches) > 1:
                for row in matches:
                    row['diagnostics'].append(_issue('ambiguous_created_object', f"$[{row['record_index']}]"))
    return _finish(value, records, issues)
