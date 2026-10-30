"""Selected native sequence publication and authenticated saved-only reading.

The existing API publication transaction owns custody/replay. Native readers
preserve source claims; CDS work uses the existing739 producer and numerical
authority. This module adds no annotation score, episode or acquisition loop.
"""
from copy import deepcopy
import hashlib
import json
import math

from .api_services import publish_existing_acquisition
from .domain import ContractError, canonical, identity
from .sequence_support_contracts import (
    sequence_support_native_request, validate_sequence_support_request,
    validate_sequence_support_selector, validate_sequence_support_snapshot,
)


_TOP = {'version', 'request', 'selector', 'native_source_ref', 'native_artifact_ref',
        'representation', 'parsed', 'reference_bindings', 'extractions',
        'sequence_bindings', 'projection_errors'}
_REF_ROW = {'record_ordinal', 'reference_ref', 'sequence_ref'}
_SEQ_ROW = {'selection_ordinal', 'record_ordinal', 'feature_ordinal', 'reference_ref',
            'sequence_ref', 'symbol_count', 'status', 'issue_codes'}
_ERROR = {'code', 'record_ordinal', 'feature_ordinal'}
_STATUSES = {'available', 'completed', 'partial', 'failed', 'unavailable',
             'authentication_required', 'not_started', 'download_required', 'invalid'}


def _require(condition, code):
    if not condition:
        raise ValueError('sequence_support_publication_' + code)


def _finite(value):
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            _finite(child)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for child in value.values():
            _finite(child)
        return
    raise ValueError('sequence_support_publication_finite_json_required')


def _same(left, right):
    return canonical(left) == canonical(right)


def _artifact_id(content):
    if type(content) is str:
        content = content.encode('utf-8')
    return 'artifact_' + hashlib.sha256(content).hexdigest()


def _artifact(store, reference):
    try:
        raw = store.get_artifact(reference)
    except (ValueError, KeyError, OSError, TypeError) as error:
        raise ValueError('sequence_support_publication_artifact_unavailable') from error
    _require(type(raw) is bytes and reference == _artifact_id(raw), 'artifact_identity_conflict')
    return raw


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        _finite(value)
        _require(raw == canonical(value).encode('utf-8'), 'canonical_artifact_required')
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError) as error:
        raise ValueError('sequence_support_publication_saved_json_invalid') from error
    return value


def _ordinal(value):
    return type(value) is int and value >= 0


def _error(code, record=None, feature=None):
    return {'code': code, 'record_ordinal': record, 'feature_ordinal': feature}


def _unique_errors(rows):
    result, seen = [], set()
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _selected_records(request, selector):
    if request['operation'] == 'get_gene_coding_sequence':
        return list(dict.fromkeys(row['record_ordinal'] for row in selector['features']))
    return selector.get('record_ordinals', [])


def _reference_payload(record, source_ref, model, sequence_ref, native_record_ref):
    return {'reference_type': model, 'source_ref': source_ref,
        'accession': record['accession'], 'label': record.get('description') or record['accession'],
        'sequence_ref': sequence_ref, 'molecule': model, 'length': record['length'],
        'term_refs': [], 'context_refs': [], 'native_record_ref': native_record_ref}


def _identity_mapping(record, reference_ref):
    from .sequence_mapping import VERSION
    length = record['length']
    if type(record.get('sequence')) is not str or not record['sequence'] or not _ordinal(length) or length == 0:
        return None
    return {'version': VERSION, 'units_per_symbol': 1, 'symbol_length': length,
        'path': [{'subject_ref': reference_ref, 'start': 0, 'end': length, 'unit': 'nt', 'strand': '+'}]}


def _sequence_row(ordinal, record, feature, reference, sequence_ref, count, status, issues):
    return {'selection_ordinal': ordinal, 'record_ordinal': record, 'feature_ordinal': feature,
        'reference_ref': reference, 'sequence_ref': sequence_ref, 'symbol_count': count,
        'status': status, 'issue_codes': list(issues)}


def _extraction_errors(extractions):
    result = []
    for row in extractions['rows']:
        if row['extraction_status'] != 'completed':
            for code in row['issue_codes'] or ['extraction_' + row['extraction_status']]:
                result.append(_error(code, row['record_ordinal'], row['feature_ordinal']))
    return result


def _publish(tools, request, selector, snapshot):
    # Native source custody comes first, including a failed native projection.
    source = tools._source(snapshot.service, None, snapshot=snapshot)
    native = validate_sequence_support_snapshot(snapshot, request=request)
    body = {'version': 'sequence_support_publication_v1', 'request': request, 'selector': selector,
        'native_source_ref': source['id'], 'native_artifact_ref': source['artifact_ref'],
        'representation': native['representation'], 'parsed': None, 'reference_bindings': [],
        'extractions': None, 'sequence_bindings': [], 'projection_errors': []}
    refs = [source['id']]
    if native['representation'] == 'ncbi_gene_xml':
        from .ncbi_gene_native import read_ncbi_gene_xml
        body['parsed'] = read_ncbi_gene_xml(snapshot.content, source_ref=source['id'],
            requested_gene_ids=request['gene_ids'], response_complete=True)
        body['projection_errors'] = [_error(row['code'], row['record_ordinal']) for row in body['parsed']['issues']]
    elif native['representation'] == 'addgene_html':
        from .addgene_sequence_native import read_addgene_sequences
        body['parsed'] = read_addgene_sequences(snapshot.content, source_ref=source['id'],
            requested_id=request['plasmid_id'], response_complete=True)
        body['projection_errors'] = [_error(row['code'], row['record_ordinal']) for row in body['parsed']['issues']]
        records = {row['record_ordinal']: row for row in body['parsed']['records']}
        for ordinal, index in enumerate(selector['record_ordinals']):
            row = records.get(index)
            if row is None:
                issues, status, sequence = ['selected_record_unavailable'], 'unavailable', None
            else:
                issues, status, sequence = row['issue_codes'], row['sequence_status'], row['sequence']
            sequence_ref = tools.store.artifact(sequence, 'text/plain') if sequence is not None else None
            body['sequence_bindings'].append(_sequence_row(ordinal, index, None, None,
                sequence_ref, None, status, issues))
            if row is None:
                body['projection_errors'].append(_error(issues[0], index))
    else:
        from .acquisition import parse_genbank
        body['parsed'] = parse_genbank(snapshot.content)
        records = {row['source_record_index']: row for row in body['parsed']}
        if not records:
            body['projection_errors'].append(_error('genbank_records_unavailable'))
        references = {}
        for index in _selected_records(request, selector):
            record = records.get(index)
            if record is None:
                continue
            try:
                sequence_ref = tools.store.artifact(record['sequence'], 'text/plain') if record['sequence'] is not None else None
                native_record_ref = tools.store.artifact(canonical(record), 'application/json')
                reference = tools._put('reference', _reference_payload(record, source['id'],
                    request['molecule_model'], sequence_ref, native_record_ref), origin='external')
            except (ValueError, ContractError, TypeError) as error:
                body['projection_errors'].append(_error('native_reference_unpublishable', index))
                continue
            references[index] = reference
            body['reference_bindings'].append({'record_ordinal': index,
                'reference_ref': reference['id'], 'sequence_ref': sequence_ref})
            refs.append(reference['id'])
        if request['operation'] == 'get_gene_coding_sequence':
            from .coding_sequence_support import plan_coding_sequence_extractions, read_coding_sequence_results
            from .coding_sequence_native import run_coding_sequence_plan
            choices = []
            for chosen in selector['features']:
                record, reference = records.get(chosen['record_ordinal']), references.get(chosen['record_ordinal'])
                subject = reference['id'] if reference else source['id']
                choices.append({**chosen, 'subject_ref': subject,
                    'parent_mapping': _identity_mapping(record, subject) if reference else None})
            plan = plan_coding_sequence_extractions(body['parsed'], selection=choices,
                source_ref=source['id'], molecule_model=request['molecule_model'])
            body['extractions'] = read_coding_sequence_results(plan, extracted=run_coding_sequence_plan(plan))
            for row in body['extractions']['rows']:
                reference = references.get(row['record_ordinal'])
                sequence_ref = tools.store.artifact(row['sequence'], 'text/plain') if row['sequence'] is not None else None
                scores = (row.get('grading') or {}).get('scores') or {}
                body['sequence_bindings'].append(_sequence_row(row['selection_ordinal'],
                    row['record_ordinal'], row['feature_ordinal'], reference['id'] if reference else None,
                    sequence_ref, scores.get('summary', {}).get('output_symbol_count'),
                    row['extraction_status'], row['issue_codes']))
            body['projection_errors'].extend(_extraction_errors(body['extractions']))
        else:
            for ordinal, index in enumerate(selector['record_ordinals']):
                record, reference = records.get(index), references.get(index)
                if record is None:
                    issues, status = ['selected_record_unavailable'], 'unavailable'
                elif reference is None:
                    issues, status = ['native_reference_unpublishable'], 'unavailable'
                elif record['sequence'] is None:
                    issues, status = ['source_sequence_unavailable'], 'unavailable'
                else:
                    issues, status = [], 'available'
                body['sequence_bindings'].append(_sequence_row(ordinal, index, None,
                    reference['id'] if reference else None, reference['sequence_ref'] if reference else None,
                    record['length'] if record else None, status, issues))
                body['projection_errors'].extend(_error(code, index) for code in issues)
    body['projection_errors'] = _unique_errors(body['projection_errors'])
    _finite(body)
    artifact = tools.store.artifact(canonical(body), 'application/json')
    return {'source_ref': source['id'], 'sequence_support_ref': artifact,
            'reference_refs': list(dict.fromkeys(refs[1:])),
            'projection_errors': deepcopy(body['projection_errors'])}, list(dict.fromkeys(refs))


def publish_sequence_support(tools, *, request, selector, snapshot, scope, operation_key):
    """Publish only the selected response; the original API helper owns replay."""
    request = validate_sequence_support_request(request)
    selector = validate_sequence_support_selector(request, selector)
    return publish_existing_acquisition(tools, 'sequence_support.' + request['operation'],
        {'request': request, 'selector': selector}, snapshot, scope, operation_key,
        publisher=lambda: _publish(tools, request, selector, snapshot))


def _record(store, reference, kind):
    try:
        record = store.get(reference)
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError('sequence_support_publication_record_unavailable') from error
    payload = {key: value for key, value in record.items() if key not in {'id', 'record_type', 'origin'}}
    _require(record['record_type'] == kind and reference == identity(kind,
        {'origin': record['origin'], 'record': payload}), 'record_identity_conflict')
    return record


def _receipt(store, artifact_ref, body):
    expected_name = 'internal.api_service.sequence_support.' + body['request']['operation']
    for saved in store.db.execute('SELECT arguments,result FROM tool_operations WHERE name=?', (expected_name,)):
        outcome, operands = json.loads(saved['result']), json.loads(saved['arguments'])
        result = outcome.get('result') or {}
        if result.get('sequence_support_ref') != artifact_ref:
            continue
        _require(outcome.get('status') in {'completed', 'partial'} and
            _same(operands.get('arguments'), {'request': body['request'], 'selector': body['selector']}), 'original_operation_conflict')
        expected_refs = list(dict.fromkeys([body['native_source_ref'],
            *[row['reference_ref'] for row in body['reference_bindings']]]))
        _require(outcome['record_refs'] == expected_refs and result == {
            'source_ref': body['native_source_ref'], 'sequence_support_ref': artifact_ref,
            'reference_refs': expected_refs[1:], 'projection_errors': body['projection_errors']}, 'original_outcome_conflict')
        return operands
    raise ValueError('sequence_support_publication_original_operation_required')


def _shape(body):
    _require(type(body) is dict and set(body) == _TOP and body['version'] == 'sequence_support_publication_v1', 'schema_required')
    validate_sequence_support_request(body['request'])
    validate_sequence_support_selector(body['request'], body['selector'])
    native = sequence_support_native_request(body['request'])
    _require(body['representation'] == native['representation'], 'representation_conflict')
    for key in ('reference_bindings', 'sequence_bindings', 'projection_errors'):
        _require(type(body[key]) is list, 'row_list_required')
    for row in body['reference_bindings']:
        _require(type(row) is dict and set(row) == _REF_ROW and _ordinal(row['record_ordinal']), 'reference_row_invalid')
    for ordinal, row in enumerate(body['sequence_bindings']):
        _require(type(row) is dict and set(row) == _SEQ_ROW and type(row['selection_ordinal']) is int
            and row['selection_ordinal'] == ordinal and _ordinal(row['record_ordinal'])
            and (row['feature_ordinal'] is None or _ordinal(row['feature_ordinal']))
            and (row['symbol_count'] is None or _ordinal(row['symbol_count']))
            and row['status'] in _STATUSES and type(row['issue_codes']) is list
            and all(type(code) is str and bool(code) for code in row['issue_codes']), 'sequence_row_invalid')
    for row in body['projection_errors']:
        _require(type(row) is dict and set(row) == _ERROR and type(row['code']) is str and bool(row['code'])
            and all(row[key] is None or _ordinal(row[key]) for key in ('record_ordinal', 'feature_ordinal')), 'error_row_invalid')
    return native


def _validate_extractions(body, references):
    from .coding_sequence_support import _validated_plan
    value = body['extractions']
    _require(type(value) is dict and set(value) == {'version','source_ref','plan','rows','population_scope','status'}
        and value['version'] == 'coding_sequence_results_v1' and value['source_ref'] == body['native_source_ref']
        and value['population_scope'] == 'explicit_selected_source_features_only', 'extractions_invalid')
    plan = _validated_plan(value['plan'])
    _require(_same(plan['records'], body['parsed']) and plan['source_ref'] == body['native_source_ref']
        and plan['molecule_model'] == body['request']['molecule_model'], 'extraction_source_conflict')
    expected_choices = []
    records = {row['source_record_index']: row for row in body['parsed']}
    for chosen in body['selector']['features']:
        reference = references.get(chosen['record_ordinal'])
        subject = reference['id'] if reference else body['native_source_ref']
        expected_choices.append({**chosen, 'subject_ref': subject,
            'parent_mapping': _identity_mapping(records[chosen['record_ordinal']], subject) if reference else None})
    _require(_same(plan['selection'], expected_choices) and type(value['rows']) is list
        and len(value['rows']) == len(plan['rows']), 'extraction_selection_conflict')
    for selected, row in zip(plan['rows'], value['rows'], strict=True):
        _require(type(row) is dict and set(row) == set(selected) | {'extraction_status','sequence','native_result','grading'}
            and all(_same(row[key], child) for key, child in selected.items() if key != 'issue_codes'), 'extraction_row_conflict')
        _require(type(row['extraction_status']) is str
            and row['extraction_status'] in {'completed','partial','failed','unavailable','not_started'}
            and (row['sequence'] is None or type(row['sequence']) is str), 'extraction_row_invalid')
        issues, planned = row['issue_codes'], selected['issue_codes']
        _require(type(issues) is list and all(type(code) is str and bool(code) for code in issues)
            and _same(issues[:len(planned)], planned), 'extraction_issue_codes_conflict')
        runtime = issues[len(planned):]
        if row['extraction_status'] == 'failed':
            # The producer appends one original failure_code or ValueError text.
            # Its authenticated saved value is not rederived from today's code.
            native = row['native_result']
            _require(selected['status'] == 'ready' and len(runtime) == 1
                and row['grading'] is None and (native is None or type(native) is dict),
                'extraction_failure_conflict')
            sequence = native.get('sequence') if native is not None else None
            _require(_same(row['sequence'], sequence if type(sequence) is str else None),
                'extraction_failure_sequence_conflict')
        else:
            _require(not runtime, 'extraction_issue_codes_conflict')
        grading = row['grading']
        if grading is not None:
            _require(type(grading) is dict and set(grading) == {'sheet','scores'}
                and grading['sheet'].get('schema') == 'sequence_extraction_sheet_v1'
                and grading['scores'].get('schema') == 'sequence_extraction_scores_v1', 'shared_grading_required')
            sheet = grading['sheet']
            _require(_same(sheet['native_result'], row['native_result']) and all(_same(sheet[key], row[key])
                for key in ('input_sequence','subject_ref','parent_mapping'))
                and _same(sheet['request'], row['effective_request']), 'grading_operand_conflict')
    _require(value['status'] == ('complete' if all(row['extraction_status']=='completed' for row in value['rows']) else 'partial'), 'extraction_status_conflict')
    return value


def read_sequence_support_publication(store, artifact_ref):
    """Read authenticated saved projections, never original native parsers/work."""
    body = _json(_artifact(store, artifact_ref))
    native = _shape(body)
    operands = _receipt(store, artifact_ref, body)
    source = _record(store, body['native_source_ref'], 'source')
    _require(source['origin'] == 'external' and source['provider'] == native['service']
        and source['uri'] == native['url'] and source['artifact_ref'] == body['native_artifact_ref']
        and body['native_artifact_ref'] == 'artifact_' + operands['snapshot_sha256'], 'native_source_conflict')
    custody = _json(_artifact(store, source['request_ref']))
    _require(_same(custody, {'request': operands['request'], 'transport': operands['transport']})
        and _same(custody['request'], native['params']), 'native_request_conflict')
    # Hash/custody validation reads bytes only. It never parses native formats.
    _artifact(store, body['native_artifact_ref'])
    references = {}
    if body['representation'] == 'genbank':
        _require(type(body['parsed']) is list and all(type(row) is dict and _ordinal(row.get('source_record_index'))
            for row in body['parsed']), 'genbank_records_invalid')
        records = {row['source_record_index']: row for row in body['parsed']}
        _require(len(records) == len(body['parsed']), 'genbank_record_identity_conflict')
        chosen = _selected_records(body['request'], body['selector'])
        ordered = [row['record_ordinal'] for row in body['reference_bindings']]
        _require(ordered == [index for index in chosen if index in ordered]
            and len(set(ordered)) == len(ordered), 'reference_population_conflict')
        for row in body['reference_bindings']:
            index, reference = row['record_ordinal'], _record(store, row['reference_ref'], 'reference')
            _require(index in records and index in chosen, 'reference_record_conflict')
            record = records[index]
            sequence_ref = _artifact_id(record['sequence']) if record['sequence'] is not None else None
            native_record_ref = _artifact_id(canonical(record))
            expected = _reference_payload(record, source['id'], body['request']['molecule_model'], sequence_ref, native_record_ref)
            _require(reference['origin'] == 'external' and _same({key: value for key, value in reference.items()
                if key not in {'id','record_type','origin'}}, expected)
                and row['sequence_ref'] == sequence_ref, 'reference_binding_conflict')
            _require(_artifact(store, native_record_ref) == canonical(record).encode('utf-8'), 'native_record_conflict')
            if sequence_ref is not None:
                _require(_artifact(store, sequence_ref) == record['sequence'].encode('utf-8'), 'reference_sequence_conflict')
            references[index] = reference
        if body['request']['operation'] == 'get_gene_coding_sequence':
            extractions = _validate_extractions(body, references)
            expected = []
            for row in extractions['rows']:
                reference = references.get(row['record_ordinal'])
                scores = (row.get('grading') or {}).get('scores') or {}
                expected.append(_sequence_row(row['selection_ordinal'], row['record_ordinal'], row['feature_ordinal'],
                    reference['id'] if reference else None,
                    _artifact_id(row['sequence']) if row['sequence'] is not None else None,
                    scores.get('summary', {}).get('output_symbol_count'), row['extraction_status'], row['issue_codes']))
            _require(_same(body['sequence_bindings'], expected), 'extraction_binding_conflict')
        else:
            _require(body['extractions'] is None, 'unexpected_extractions')
            expected = []
            for ordinal, index in enumerate(body['selector']['record_ordinals']):
                record, reference = records.get(index), references.get(index)
                issues = (['selected_record_unavailable'] if record is None else ['native_reference_unpublishable']
                    if reference is None else ['source_sequence_unavailable'] if record['sequence'] is None else [])
                expected.append(_sequence_row(ordinal, index, None, reference['id'] if reference else None,
                    reference['sequence_ref'] if reference else None, record['length'] if record else None,
                    'unavailable' if issues else 'available', issues))
            _require(_same(body['sequence_bindings'], expected), 'sequence_population_conflict')
    else:
        _require(body['reference_bindings'] == [] and body['extractions'] is None, 'non_genbank_reference_conflict')
        if body['representation'] == 'ncbi_gene_xml':
            from .ncbi_gene_native import validate_ncbi_gene_native
            parsed = validate_ncbi_gene_native(body['parsed'])
            _require(parsed['source_ref'] == source['id'] and parsed['request']['gene_ids'] == body['request']['gene_ids']
                and body['sequence_bindings'] == [], 'gene_source_conflict')
        else:
            from .addgene_sequence_native import validate_addgene_sequence_page
            parsed = validate_addgene_sequence_page(body['parsed'])
            _require(parsed['source_ref'] == source['id'] and parsed['requested_id'] == body['request']['plasmid_id'], 'addgene_source_conflict')
            records = {row['record_ordinal']: row for row in parsed['records']}
            expected = []
            for ordinal, index in enumerate(body['selector']['record_ordinals']):
                row = records.get(index)
                sequence = row['sequence'] if row else None
                expected.append(_sequence_row(ordinal, index, None, None,
                    _artifact_id(sequence) if sequence is not None else None, None,
                    row['sequence_status'] if row else 'unavailable',
                    row['issue_codes'] if row else ['selected_record_unavailable']))
            _require(_same(body['sequence_bindings'], expected), 'addgene_population_conflict')
    for row in body['sequence_bindings']:
        if row['sequence_ref'] is not None:
            _artifact(store, row['sequence_ref'])
    return deepcopy(body)


__all__ = ['publish_sequence_support', 'read_sequence_support_publication']
