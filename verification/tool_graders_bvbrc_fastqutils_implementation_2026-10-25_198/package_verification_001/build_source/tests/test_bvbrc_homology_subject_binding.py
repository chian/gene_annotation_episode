"""Pure source/member/native-reference joins with real synthetic sequence hashes.

These values are fixtures for an already authenticated C4 boundary. They test
scientific association, not host custody or live BV-BRC behavior.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_homology_subject_binding import validate_pairwise_subject


QUERY = 'ATGAAAACTGGGTAA'
REFERENCE = 'MKTGG'
FASTA = '>reference-1\n' + REFERENCE + '\n'


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _content(raw, source):
    return {'source_ref': source, 'artifact_field': 'artifact_ref',
        'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(),
        'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


def _fixture(*, retained=False, escaped=False, ancestor=False, native_mapping=False, hits=True):
    key = 'reference/members~list' if escaped else 'reference_members'
    token = key.replace('~', '~0').replace('/', '~1')
    base = '/payload' if ancestor else ''
    member_pointer, member_list_pointer = base + '/' + token + '/0', base + '/' + token
    reference = {'member_id': 'reference-member-0', 'supplied_id': 'reference-1',
        'sequence': REFERENCE, 'length': len(REFERENCE), 'molecule': 'protein',
        'sequence_sha256': hashlib.sha256(REFERENCE.encode()).hexdigest()}
    if native_mapping:
        reference['native_hit'] = {'report_index': 0, 'hit_index': 0,
            'description_index': 0, 'id': 'gnl|BL_ORD_ID|0', 'length': len(REFERENCE)}
    original = {key: [reference], 'fasta': FASTA, 'query_members': [{'member_id': 'query-member-0',
        'supplied_id': 'query-1', 'sequence': QUERY, 'length': len(QUERY), 'molecule': 'dna',
        'sequence_sha256': hashlib.sha256(QUERY.encode()).hexdigest()}]}
    source = _content(_bytes({'payload': original} if ancestor else original), 'source_original_input')
    evidence = lambda pointer: {'content': deepcopy(source), 'pointer': pointer}
    query = original['query_members'][0]
    query_input = {'binding_id': 'query', 'parameter_pointer': '/input_fasta_data',
        'kind': 'inline_parameter', 'content': None, 'workspace_path': None,
        'inline_value': '>query-1\n' + QUERY + '\n', 'link_evidence': None,
        'members': [{'member_id': query['member_id'], 'member_pointer': base + '/query_members/0',
            **{name: query[name] for name in ('length', 'molecule', 'sequence_sha256')},
            'evidence': evidence(base + '/query_members/0')}]}
    reference_input = {'binding_id': 'reference',
        'parameter_pointer': '/db_fasta_file' if retained else '/db_fasta_data',
        'kind': 'retained_bytes' if retained else 'supplied_link',
        'content': _content(FASTA.encode(), 'source_reference_fasta') if retained else None,
        'workspace_path': '/synthetic/selected/reference.faa' if retained else None,
        'inline_value': None if retained else FASTA,
        'link_evidence': None if retained else evidence(base + '/fasta'),
        'members': [{'member_id': reference['member_id'], 'member_pointer': member_pointer,
            **{name: reference[name] for name in ('length', 'molecule', 'sequence_sha256')},
            'evidence': evidence(member_pointer)}]}
    values = [{'evidence': evidence(base), 'value': original}]
    if retained:
        retained_value = {'content': deepcopy(reference_input['content']), 'text': FASTA}
        values.append({'evidence': {'content': _content(_bytes(retained_value), 'source_retained_text'),
            'pointer': ''}, 'value': retained_value})
    selection = {'db_type': 'faa', 'db_source': 'fasta_file' if retained else 'fasta_data',
        'db_fasta_file' if retained else 'db_fasta_data': reference_input['workspace_path'] if retained else FASTA}
    subject = {'source_ref': reference_input['content']['source_ref'] if retained else source['source_ref'],
        'member_ref': reference['member_id'], 'subject_ref': reference['member_id'],
        'sequence_sha256': reference['sequence_sha256'], 'length': len(REFERENCE), 'molecule': 'aa',
        'database_membership': {'source_ref': source['source_ref'], 'pointer': member_list_pointer, 'member_count': 1},
        'native_hit_links': [{'report_index': 0, 'hit_index': 0, 'description_index': 0}] if hits else []}
    database = {'requested_selection': selection, 'effective_native_database': 'SYNTHETIC_NATIVE_DATABASE',
        'effective_parameters_source': None, 'reference_release': None, 'reference_release_source': None,
        'actual_taxon_filter': None, 'actual_database_members': [{'identifier': reference['member_id'],
            'length': len(REFERENCE), 'molecule': 'aa', 'sequence_sha256': reference['sequence_sha256']}],
        'input_or_database_sequence_inventory_ref': source['source_ref']}
    bundle = {'version': 'bvbrc_appservice_artifact_bundle_v1',
        'original_task': {'required_application_id': 'Homology', 'native_application_id': 'Homology',
            'submitted_parameters': {'blast_program': 'blastx', 'input_source': 'fasta_data',
                'input_fasta_data': query_input['inline_value'], **selection}},
        'input_bindings': [query_input, reference_input],
        'supplied_scientific_metadata': [value['evidence'] for value in values]}
    queries = [{'report_index': 0, 'normalized_result': {'search': {'program': 'blastx'},
        'query': {'length': len(QUERY)}, 'hits': [{'hit_index': 0, 'length': len(REFERENCE),
            'descriptions': [{'id': 'gnl|BL_ORD_ID|0' if native_mapping else 'reference-1',
                'source_locator': {'report_index': 0, 'hit_index': 0, 'description_index': 0}}],
            'hsps': []}] if hits else []}}]
    return {'bundle': bundle, 'subject': subject, 'database': database,
        'supplied_values': values, 'queries': queries}


def _validate(fixture):
    before = deepcopy(fixture)
    result = validate_pairwise_subject(fixture['bundle'], **{key: fixture[key]
        for key in ('subject', 'database', 'supplied_values', 'queries')})
    assert fixture == before
    assert isinstance(result, list)
    assert all(set(row) == {'code', 'path'} and isinstance(row['code'], str) and row['code']
        and isinstance(row['path'], str) for row in result)
    return result


def _reject(fixture):
    failures = _validate(fixture)
    assert failures, 'Conflicting/missing reference evidence must not validate'
    return failures


@pytest.mark.parametrize('retained', [False, True])
@pytest.mark.parametrize('ancestor,escaped', [(False, False), (True, False), (False, True), (True, True)])
def test_complete_reference_and_exact_escaped_or_ancestor_source_pointer(retained, ancestor, escaped):
    assert _validate(_fixture(retained=retained, ancestor=ancestor, escaped=escaped)) == []


def test_valid_native_identifier_mapping_and_valid_zero_hit_case():
    assert _validate(_fixture(native_mapping=True)) == []
    assert _validate(_fixture(hits=False)) == []


@pytest.mark.parametrize('field,value', [
    ('sequence_sha256', hashlib.sha256(b'AAAAA').hexdigest()), ('length', 4),
    ('molecule', 'nt'), ('source_ref', 'source_unrelated'), ('member_ref', 'query-member-0'),
    ('subject_ref', 'unrelated-target')])
def test_subject_must_match_original_submitted_reference_member(field, value):
    fixture = _fixture()
    fixture['subject'][field] = value
    _reject(fixture)


@pytest.mark.parametrize('field,value', [('length', 4), ('molecule', 'dna'),
    ('sequence_sha256', hashlib.sha256(b'AAAAA').hexdigest()), ('member_id', 'query-member-0')])
def test_original_reference_member_measurements_are_checked(field, value):
    fixture = _fixture()
    fixture['bundle']['input_bindings'][1]['members'][0][field] = value
    _reject(fixture)


@pytest.mark.parametrize('change', ['wrong_source', 'wrong_pointer', 'nonlist', 'two_members',
    'different_member_evidence', 'missing_member_evidence', 'ambiguous_value', 'absent_values'])
def test_membership_is_an_actual_unambiguous_source_list(change):
    fixture = _fixture()
    membership = fixture['subject']['database_membership']
    member = fixture['bundle']['input_bindings'][1]['members'][0]
    if change == 'wrong_source':
        membership['source_ref'] = 'source_unrelated'
    elif change == 'wrong_pointer':
        membership['pointer'] = '/missing_members'
    elif change == 'nonlist':
        membership['pointer'] = '/reference_members/0'
    elif change == 'two_members':
        original = fixture['supplied_values'][0]['value']
        original['reference_members'].append({**original['reference_members'][0], 'member_id': 'second-reference'})
    elif change == 'different_member_evidence':
        member['evidence']['pointer'] = '/query_members/0'
    elif change == 'missing_member_evidence':
        member['evidence'] = None
    elif change == 'ambiguous_value':
        conflicting = deepcopy(fixture['supplied_values'][0])
        conflicting['value']['reference_members'][0]['sequence'] = 'AAAAA'
        fixture['supplied_values'].append(conflicting)
    else:
        fixture['supplied_values'] = []
    _reject(fixture)


@pytest.mark.parametrize('field,value', [('sequence', 'AAAAA'), ('length', 4), ('molecule', 'dna'),
    ('sequence_sha256', hashlib.sha256(b'AAAAA').hexdigest()), ('member_id', 'query-member-0'),
    ('supplied_id', 'not-the-submitted-reference')])
def test_retained_member_row_cannot_disagree_with_submitted_fasta(field, value):
    fixture = _fixture()
    fixture['supplied_values'][0]['value']['reference_members'][0][field] = value
    _reject(fixture)


def test_one_returned_hit_does_not_prove_one_submitted_sequence():
    fixture = _fixture()
    multiple = FASTA + '>second-reference\nAAAAA\n'
    fixture['bundle']['original_task']['submitted_parameters']['db_fasta_data'] = multiple
    fixture['bundle']['input_bindings'][1]['inline_value'] = multiple
    fixture['supplied_values'][0]['value']['fasta'] = multiple
    fixture['database']['requested_selection']['db_fasta_data'] = multiple
    assert len(fixture['queries'][0]['normalized_result']['hits']) == 1
    _reject(fixture)


@pytest.mark.parametrize('change', ['native_id', 'native_length', 'link_report', 'link_hit', 'link_description',
    'mapping_report', 'mapping_hit', 'mapping_description', 'mapping_id', 'mapping_length', 'multiple_native_hits'])
def test_native_original_ordinals_and_identifiers_keep_their_own_member(change):
    fixture = _fixture(native_mapping=change.startswith('mapping_'))
    native = fixture['queries'][0]['normalized_result']['hits'][0]
    if change == 'native_id':
        native['descriptions'][0]['id'] = 'unrelated-reference'
    elif change == 'native_length':
        native['length'] = 7
    elif change.startswith('link_'):
        field = {'link_report': 'report_index', 'link_hit': 'hit_index', 'link_description': 'description_index'}[change]
        fixture['subject']['native_hit_links'][0][field] = 1
    elif change.startswith('mapping_'):
        field = {'mapping_report': 'report_index', 'mapping_hit': 'hit_index', 'mapping_description': 'description_index',
            'mapping_id': 'id', 'mapping_length': 'length'}[change]
        fixture['supplied_values'][0]['value']['reference_members'][0]['native_hit'][field] = 'unrelated' if field == 'id' else 1
    else:
        fixture['queries'][0]['normalized_result']['hits'].append({**deepcopy(native), 'hit_index': 1})
    _reject(fixture)


@pytest.mark.parametrize('field,value', [('identifier', 'unrelated'), ('length', 4), ('molecule', 'nt'),
    ('sequence_sha256', hashlib.sha256(b'AAAAA').hexdigest()), ('sequence', 'AAAAA'),
    ('supplied_id', 'unrelated')])
def test_explicit_database_inventory_cannot_disagree_with_reference(field, value):
    fixture = _fixture()
    fixture['database']['actual_database_members'][0][field] = value
    _reject(fixture)


@pytest.mark.parametrize('change', ['wrong_text', 'missing_text', 'wrong_content', 'wrong_size', 'workspace_only'])
def test_retained_reference_requires_exact_full_acquired_text(change):
    fixture = _fixture(retained=True)
    reference = fixture['bundle']['input_bindings'][1]
    if change == 'wrong_text':
        fixture['supplied_values'][1]['value']['text'] = '>reference-1\nAAAAA\n'
    elif change == 'missing_text':
        fixture['supplied_values'].pop()
    elif change == 'wrong_content':
        fixture['supplied_values'][1]['value']['content']['source_ref'] = 'source_unrelated'
    elif change == 'wrong_size':
        reference['content']['byte_count'] += 1
        fixture['supplied_values'][1]['value']['content']['byte_count'] += 1
    else:
        reference.update(kind='workspace_object', content=None)
        fixture['supplied_values'].pop()
    _reject(fixture)


@pytest.mark.parametrize('change', ['link_value', 'operand', 'reference_pointer', 'two_reference_bindings', 'missing_reference'])
def test_original_database_selection_does_not_switch_to_query_or_another_source(change):
    fixture = _fixture()
    if change == 'link_value':
        fixture['bundle']['input_bindings'][1]['link_evidence']['pointer'] = '/query_members/0/sequence'
    elif change == 'operand':
        fixture['bundle']['original_task']['submitted_parameters']['db_fasta_data'] = '>other\nAAAAA\n'
    elif change == 'reference_pointer':
        fixture['bundle']['input_bindings'][1]['parameter_pointer'] = '/input_fasta_data'
    elif change == 'two_reference_bindings':
        fixture['bundle']['input_bindings'].append(deepcopy(fixture['bundle']['input_bindings'][1]))
    else:
        fixture['bundle']['input_bindings'].pop()
    _reject(fixture)


def test_validation_is_pure_and_unavailable_input_returns_specific_rows(monkeypatch):
    fixture = _fixture()

    def forbidden(*args, **kwargs):
        raise AssertionError('Pure pairwise subject association attempted I/O')

    for target in ('builtins.open', 'socket.create_connection', 'socket.socket.connect',
            'urllib.request.OpenerDirector.open', 'subprocess.run', 'subprocess.Popen'):
        monkeypatch.setattr(target, forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    assert _validate(fixture) == []
    for field in ('subject', 'database', 'supplied_values', 'queries'):
        damaged = deepcopy(fixture)
        damaged[field] = None
        _reject(damaged)


def test_explicit_member_subject_relationship_can_name_retained_reference():
    fixture = _fixture()
    fixture['subject']['subject_ref'] = 'reference_explicitly_linked'
    fixture['supplied_values'][0]['value']['reference_members'][0]['subject_ref'] = 'reference_explicitly_linked'
    assert _validate(fixture) == []


@pytest.mark.parametrize('change', ['requested_database', 'inventory_source', 'inventory_row_source',
    'inventory_row_pointer', 'mapping_wrong_ordinal_despite_direct_id',
    'mapping_wrong_id_despite_direct_id', 'mapping_duplicate', 'mapping_ambiguous_list'])
def test_additional_explicit_relationships_cannot_be_ignored(change):
    fixture = _fixture()
    row = fixture['supplied_values'][0]['value']['reference_members'][0]
    if change == 'requested_database':
        fixture['database']['requested_selection'] = {**fixture['database']['requested_selection'], 'db_type': 'fna'}
    elif change == 'inventory_source':
        fixture['database']['input_or_database_sequence_inventory_ref'] = 'source_unrelated'
    elif change == 'inventory_row_source':
        fixture['database']['actual_database_members'][0].update(source_ref='source_unrelated', pointer='/reference_members/0')
    elif change == 'inventory_row_pointer':
        fixture['database']['actual_database_members'][0].update(source_ref='source_original_input', pointer='/query_members/0')
    else:
        mapping = {'report_index': 0, 'hit_index': 0, 'description_index': 0, 'id': 'reference-1'}
        row['native_hit'] = mapping
        if change == 'mapping_wrong_ordinal_despite_direct_id':
            mapping['description_index'] = 1
        elif change == 'mapping_wrong_id_despite_direct_id':
            mapping['id'] = 'not-the-reported-reference'
        elif change == 'mapping_duplicate':
            row['native_hits'] = [deepcopy(mapping)]
        else:
            row['native_hits'] = [{**mapping, 'id': 'not-the-reported-reference'}]
    _reject(fixture)
