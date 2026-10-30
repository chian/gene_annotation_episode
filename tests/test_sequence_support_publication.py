"""Saved CDS failure facts, using engineered records and receipt fixtures.

These pure checks exercise the real producer and frozen publication reader.
The in-memory receipt is an explicit engineering fixture, not an API or episode
custody proof. No native extraction, original acquisition or network is run.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import sqlite3

import pytest

from gene_annotation_episode import acquisition, coding_sequence_support, sequence_extraction_grader
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.sequence_support_contracts import sequence_support_native_request
from gene_annotation_episode import sequence_support_publication as publication


class SavedStore:
    """Exact immutable record/artifact addresses and one engineered receipt."""

    def __init__(self):
        self.records, self.artifacts = {}, {}
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE tool_operations (name TEXT, arguments TEXT, result TEXT)')

    def artifact(self, raw):
        if type(raw) is str:
            raw = raw.encode('utf-8')
        ref = 'artifact_' + hashlib.sha256(raw).hexdigest()
        self.artifacts[ref] = raw
        return ref

    def record(self, kind, payload):
        ref = identity(kind, {'origin': 'external', 'record': payload})
        self.records[ref] = {'id': ref, 'record_type': kind, 'origin': 'external', **payload}
        return self.records[ref]

    def get(self, reference):
        return deepcopy(self.records[reference])

    def get_artifact(self, reference):
        return self.artifacts[reference]


def native_view(start, end, sequence):
    return {'operation_version': 'explicit_sequence_view_v1', 'sequence': sequence,
        'molecule_model': 'dna', 'molecule_assignment': 'not_performed', 'orientation': 'as_is',
        'input_segments': [{'start': start, 'end': end}], 'input_length': 8,
        'output_length': len(sequence), 'coordinate_system': 'zero_based_half_open'}


@pytest.fixture
def saved_case():
    store = SavedStore()
    request = {'operation': 'get_gene_coding_sequence', 'accession': 'ENGINEERED.1',
        'molecule_model': 'dna', 'max_bytes': 4096}
    native = sequence_support_native_request(request)
    # Retained bytes identify this engineering source; no native parser is
    # invoked while checking its already-produced saved projections.
    raw = b'engineering source record ENGINEERED.1: AACCGGTT\n'
    raw_ref = store.artifact(raw)
    transport = {'status': 200, 'body_complete': True, 'response_byte_limit': 4096}
    custody = {'request': native['params'], 'transport': transport}
    source = store.record('source', {'provider': native['service'], 'accession': None,
        'uri': native['url'], 'artifact_ref': raw_ref, 'text_ref': None,
        'request_ref': store.artifact(canonical(custody)), 'version': None,
        'retrieved_at': '2026-10-30T00:00:00+00:00'})
    exact = {'start': 0, 'end': 4, 'strand': '+', 'start_kind': 'ExactPosition',
        'end_kind': 'ExactPosition', 'ref': None, 'ref_db': None}
    qualified = {**exact, 'start': 4, 'end': 8, 'strand': 'unknown', 'start_kind': 'BeforePosition'}
    record = {'source_record_index': 0, 'accession': 'ENGINEERED.1',
        'description': 'engineered saved-row contract', 'sequence': 'AACCGGTT', 'length': 8,
        'features': [{'source_feature_index': i, 'kind': 'CDS', 'segments': [part],
            'operator': None, 'qualifiers': {}} for i, part in enumerate((exact, qualified))],
        'unlocated_features': []}
    sequence_ref = store.artifact(record['sequence'])
    native_record_ref = store.artifact(canonical(record))
    reference = store.record('reference', publication._reference_payload(
        record, source['id'], 'dna', sequence_ref, native_record_ref))
    selector = {'view': 'cds', 'features': [{'record_ordinal': 0, 'feature_ordinal': i}
        for i in (0, 1, 0, 0, 99, 1)]}
    choices = [{**chosen, 'subject_ref': reference['id'],
        'parent_mapping': publication._identity_mapping(record, reference['id'])}
        for chosen in selector['features']]
    plan = coding_sequence_support.plan_coding_sequence_extractions([record], selection=choices,
        source_ref=source['id'], molecule_model='dna')
    invalid_native = {**native_view(0, 4, 'AACC'), 'operation_version': 'engineered_invalid_version'}
    extracted = [{'selection_ordinal': 0, 'native_result': native_view(0, 4, 'AACC'), 'failure_code': None},
        {'selection_ordinal': 1, 'native_result': None, 'failure_code': 'original recorded runtime failure'},
        {'selection_ordinal': 2, 'native_result': invalid_native, 'failure_code': None},
        {'selection_ordinal': 5, 'native_result': native_view(4, 8, 'GGTT'), 'failure_code': None}]
    results = coding_sequence_support.read_coding_sequence_results(plan, extracted=extracted)
    bindings = []
    for row in results['rows']:
        scores = (row['grading'] or {}).get('scores') or {}
        bindings.append({'selection_ordinal': row['selection_ordinal'], 'record_ordinal': 0,
            'feature_ordinal': row['feature_ordinal'], 'reference_ref': reference['id'],
            'sequence_ref': None if row['sequence'] is None else store.artifact(row['sequence']),
            'symbol_count': scores.get('summary', {}).get('output_symbol_count'),
            'status': row['extraction_status'], 'issue_codes': deepcopy(row['issue_codes'])})
    body = {'version': 'sequence_support_publication_v1', 'request': request, 'selector': selector,
        'native_source_ref': source['id'], 'native_artifact_ref': raw_ref, 'representation': 'genbank',
        'parsed': [record], 'reference_bindings': [{'record_ordinal': 0,
            'reference_ref': reference['id'], 'sequence_ref': sequence_ref}],
        'extractions': results, 'sequence_bindings': bindings,
        'projection_errors': publication._extraction_errors(results)}
    artifact_ref = store.artifact(canonical(body))
    operands = {'arguments': {'request': request, 'selector': selector},
        'snapshot_sha256': hashlib.sha256(raw).hexdigest(), **custody}
    outcome = {'status': 'partial', 'record_refs': [source['id'], reference['id']],
        'result': {'source_ref': source['id'], 'sequence_support_ref': artifact_ref,
            'reference_refs': [reference['id']], 'projection_errors': body['projection_errors']}}
    store.db.execute('INSERT INTO tool_operations VALUES(?,?,?)', (
        'internal.api_service.sequence_support.get_gene_coding_sequence',
        canonical(operands), canonical(outcome)))
    try:
        yield store, artifact_ref, body, {0: reference}
    finally:
        store.db.close()


def test_saved_reader_retains_original_runtime_failures_and_independent_scores(saved_case, monkeypatch):
    store, artifact_ref, body, _ = saved_case
    original = deepcopy(body)
    raw = store.get_artifact(artifact_ref)
    records = deepcopy(store.records)
    artifacts = deepcopy(store.artifacts)

    def forbidden(*args, **kwargs):
        raise AssertionError('saved failure reader attempted production or recalculation')

    monkeypatch.setattr(coding_sequence_support, 'read_coding_sequence_results', forbidden)
    monkeypatch.setattr(coding_sequence_support, 'grade_extraction', forbidden)
    monkeypatch.setattr(sequence_extraction_grader, 'grade_extraction', forbidden)
    monkeypatch.setattr(sequence_extraction_grader, 'calculate_extraction_scores', forbidden)
    monkeypatch.setattr(acquisition, 'parse_genbank', forbidden)
    monkeypatch.setattr('urllib.request.urlopen', forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)
    original_import = builtins.__import__

    def saved_import(name, *args, **kwargs):
        if name == 'Bio' or name.startswith('Bio.') or name.endswith('coding_sequence_native'):
            raise AssertionError('saved failure reader imported native extraction')
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', saved_import)
    result = publication.read_sequence_support_publication(store, artifact_ref)
    assert result == original and store.get_artifact(artifact_ref) == raw
    assert store.records == records and store.artifacts == artifacts
    rows = result['extractions']['rows']
    assert [row['extraction_status'] for row in rows] == [
        'completed', 'failed', 'failed', 'not_started', 'unavailable', 'partial']
    assert rows[1]['issue_codes'] == [*rows[5]['issue_codes'], 'original recorded runtime failure']
    assert rows[2]['issue_codes'] == ['sequence_extraction_native_schema_required']
    assert rows[2]['sequence'] == 'AACC' and rows[2]['native_result']['operation_version'] == 'engineered_invalid_version'
    assert rows[1]['grading'] is rows[2]['grading'] is None
    assert rows[0]['grading']['scores']['summary']['matching_symbol_count'] == 4
    assert rows[5]['grading']['scores']['summary']['matching_symbol_count'] == 4
    assert body == original


@pytest.mark.parametrize('change', ['missing_prefix', 'changed_prefix', 'reordered_prefix',
    'extra_code', 'empty_code', 'numeric_code', 'bool_code', 'tuple_codes', 'completed_extension',
    'partial_extension', 'not_started_extension', 'unavailable_extension', 'failed_without_code',
    'failed_with_grading', 'failed_with_sequence', 'failed_with_native_list',
    'native_sequence_conflict', 'unavailable_plan_failed', 'status_list', 'status_bool',
    'selected_operand_changed'])
def test_saved_failure_extensions_cannot_replace_plan_facts_or_forge_runtime_shapes(saved_case, change):
    _, _, original, references = saved_case
    body = deepcopy(original)
    row = body['extractions']['rows'][1]
    if change == 'missing_prefix': row['issue_codes'].pop(0)
    elif change == 'changed_prefix': row['issue_codes'][0] = 'invented_source_fact'
    elif change == 'reordered_prefix': row['issue_codes'][:2] = reversed(row['issue_codes'][:2])
    elif change == 'extra_code': row['issue_codes'].append('invented_second_runtime_failure')
    elif change == 'empty_code': row['issue_codes'][-1] = ''
    elif change == 'numeric_code': row['issue_codes'][-1] = 7
    elif change == 'bool_code': row['issue_codes'][-1] = True
    elif change == 'tuple_codes': row['issue_codes'] = tuple(row['issue_codes'])
    elif change in {'completed_extension', 'partial_extension', 'not_started_extension', 'unavailable_extension'}:
        row['extraction_status'] = change.removesuffix('_extension')
    elif change == 'failed_without_code': row['issue_codes'].pop()
    elif change == 'failed_with_grading': row['grading'] = deepcopy(body['extractions']['rows'][0]['grading'])
    elif change == 'failed_with_sequence': row['sequence'] = 'invented'
    elif change == 'failed_with_native_list': row['native_result'] = []
    elif change == 'native_sequence_conflict':
        body['extractions']['rows'][2]['sequence'] = 'invented'
    elif change == 'unavailable_plan_failed':
        row = body['extractions']['rows'][4]
        row['extraction_status'] = 'failed'
        row['issue_codes'].append('invented native failure')
    elif change == 'status_list': row['extraction_status'] = ['failed']
    elif change == 'status_bool': row['extraction_status'] = True
    else: row['input_sequence'] = 'invented source'
    with pytest.raises(ValueError, match='sequence_support_publication_extraction_'):
        publication._validate_extractions(body, references)
    assert original['extractions']['rows'][1]['issue_codes'][-1] == 'original recorded runtime failure'


def test_failure_extensions_still_require_original_artifact_identity_and_receipt(saved_case):
    store, artifact_ref, body, _ = saved_case
    tampered = deepcopy(body)
    tampered['extractions']['rows'][1]['issue_codes'][-1] = 'different recorded failure'
    store.artifacts[artifact_ref] = canonical(tampered).encode('utf-8')
    with pytest.raises(ValueError, match='artifact_identity_conflict'):
        publication.read_sequence_support_publication(store, artifact_ref)
    replacement = store.artifact(canonical(tampered))
    with pytest.raises(ValueError, match='original_operation_required'):
        publication.read_sequence_support_publication(store, replacement)
