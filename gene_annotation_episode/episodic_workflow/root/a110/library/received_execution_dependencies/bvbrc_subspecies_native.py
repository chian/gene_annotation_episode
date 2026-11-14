from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_native import _canonical, _content, _finite_json
DOCUMENT_VERSION = 'bvbrc_subspecies_native_document_v1'
COMPONENTS_VERSION = 'bvbrc_subspecies_components_v1'
REPRESENTATIONS = ('classification_summary', 'cladinator_results', 'rota_result', 'rota_error')
_DOCUMENT_FIELDS = {'version', 'representation', 'content', 'capture_complete', 'expected_task_id', 'parsing_state', 'native_document', 'issues'}

def _require(condition, code='bvbrc_subspecies_document_invalid'):
    if not condition:
        raise ValueError(code)

def _issue(code, path, severity='qualification'):
    return dict(code=code, path=path, severity=severity)

def _table_issues(native, representation):
    issues = []
    header = native['header']
    if header is None:
        return [_issue('native_table_header_missing', '/native_document/header', 'error')]
    names = header['cells']
    if representation == 'classification_summary' and names != ['Query Identifier', 'Clade Classification']:
        issues.append(_issue('native_summary_header_incompatible', '/native_document/header', 'error'))
    if representation == 'cladinator_results':
        for name in ('Query', 'Assignment'):
            if names.count(name) != 1:
                issues.append(_issue('native_cladinator_column_missing_or_ambiguous', '/native_document/header', 'error'))
    if representation in {'rota_result', 'rota_error'}:
        issues.append(_issue('native_rota_column_schema_unverified', '/native_document/header'))
    if len(set(names)) != len(names):
        issues.append(_issue('native_table_duplicate_column_names', '/native_document/header'))
    for ordinal, row in enumerate(native['rows']):
        if len(row['cells']) != len(names):
            issues.append(_issue('native_table_row_width_conflict', '/native_document/rows/' + str(ordinal), 'error'))
        if row['raw_line'] == '':
            issues.append(_issue('native_table_blank_row', '/native_document/rows/' + str(ordinal)))
        if representation == 'classification_summary' and names == ['Query Identifier', 'Clade Classification']:
            required = (0, 1)
        elif representation == 'cladinator_results':
            required = tuple((index for index, name in enumerate(names) if name in {'Query', 'Assignment'}))
        else:
            required = (0, 2) if representation == 'rota_result' else (0,)
        if any((index < len(row['cells']) and row['cells'][index] == '' for index in required)):
            issues.append(_issue('native_query_or_classification_empty', '/native_document/rows/' + str(ordinal)))
    if representation == 'rota_error' and native['rows']:
        issues.append(_issue('native_rota_errors_reported', '/native_document/rows'))
    return issues

def validate_subspecies_document(value):
    """Validate saved observations without native I/O or numerical work."""
    _finite_json(value)
    _require(type(value) is dict and set(value) == _DOCUMENT_FIELDS and (value['version'] == DOCUMENT_VERSION) and (type(value['representation']) is str) and (value['representation'] in REPRESENTATIONS) and (type(value['capture_complete']) is bool) and (type(value['expected_task_id']) is str) and bool(value['expected_task_id']) and (value['parsing_state'] in {'available', 'unavailable'}) and (type(value['issues']) is list))
    content = _content(value['content'])
    native = value['native_document']
    _require((native is None) == (value['parsing_state'] == 'unavailable'))
    expected = []
    if native is None:
        expected.append(_issue('invalid_native_utf8', '/native_document', 'error'))
    else:
        _require(type(native) is dict and set(native) == {'delimiter', 'encoding', 'header', 'rows'} and (native['delimiter'] == '\t') and (native['encoding'] == 'utf-8') and (type(native['rows']) is list))
        _require(native['header'] is not None or native['rows'] == [])
        start = 0
        digest = hashlib.sha256()
        physical = ([] if native['header'] is None else [native['header']]) + native['rows']
        for ordinal, row in enumerate(physical):
            fields = {'raw_line', 'cells', 'line_ending', 'source_location'} | ({'row_ordinal'} if ordinal else set())
            _require(type(row) is dict and set(row) == fields and (type(row['raw_line']) is str) and ('\r' not in row['raw_line']) and ('\n' not in row['raw_line']) and (row['cells'] == row['raw_line'].split('\t')) and (row['line_ending'] in {'', '\n', '\r', '\r\n'}))
            if ordinal:
                _require(type(row['row_ordinal']) is int and row['row_ordinal'] == ordinal - 1)
            _require(ordinal == len(physical) - 1 or row['line_ending'] != '')
            raw = (row['raw_line'] + row['line_ending']).encode('utf-8')
            _require(row['source_location'] == dict(byte_start_0based=start, byte_end_0based_exclusive=start + len(raw), line_1based=ordinal + 1))
            digest.update(raw)
            start += len(raw)
        _require(start == content['byte_count'] and digest.hexdigest() == content['sha256'], 'bvbrc_subspecies_saved_bytes_conflict')
        expected.extend(_table_issues(native, value['representation']))
    if not value['capture_complete']:
        expected.append(_issue('native_capture_incomplete', '/capture_complete'))
    _require(_canonical(value['issues']) == _canonical(expected))
    return deepcopy(value)
