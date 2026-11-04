"""Association contracts use actual parser records, not fabricated row schemas."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_alignment_associations import (
    extract_alignment_associations, extract_inline_fasta_members, input_member_occurrence_subject_id,
)
from gene_annotation_episode import bvbrc_alignment_provider_contracts as c
from gene_annotation_episode.bvbrc_metacats_input_formats import parse_metacats_input_fasta
from gene_annotation_episode.phylogeny_formats import parse_newick


def artifact(data, name):
    return {'raw_artifact_ref': name, 'source_ref': 'source:' + name, 'sha256': hashlib.sha256(data).hexdigest()}


def evidence(name='facts', pointer=''):
    return {'content': {'source_ref': 'source:' + name, 'artifact_field': 'artifact_ref', 'artifact_ref': name,
        'sha256': hashlib.sha256(name.encode()).hexdigest(), 'byte_count': len(name)}, 'pointer': pointer}


def binding(data, name='original', inline=False):
    content = {**{'source_ref': 'source:' + name, 'artifact_field': 'artifact_ref', 'artifact_ref': name},
        'sha256': hashlib.sha256(data.encode()).hexdigest(), 'byte_count': len(data.encode())}
    return {'binding_id': name, 'parameter_pointer': '/input/' + name, 'kind': 'inline_parameter' if inline else 'retained_bytes',
        'content': None if inline else content, 'workspace_path': None if inline else '/workspace/' + name,
        'inline_value': data if inline else None, 'link_evidence': None, 'members': []}


def alignment(data='>a\nAC\n>b\nAT\n', name='aligned'):
    raw = data.encode()
    result = parse_metacats_input_fasta(raw, artifact=artifact(raw, name), encoding='utf-8')
    assert result['value'] is not None, result
    return {'kind': 'alignment', 'value': result['value']}


def common_fixture(data='>a\nAC\n>b\nAT\n', output=None, molecule='dna', inline=False):
    inp = binding(data, inline=inline)
    original = alignment(data, 'original')
    aligned = alignment(output if output is not None else data)
    documents = [aligned] if inline else [original, aligned]
    selection = {'kind': 'inline_fasta', 'input_binding_id': 'original', 'id_rule': 'first_whitespace_token',
        'encoding': 'utf-8', 'molecule': molecule, 'evidence': []} if inline else {
        'kind': 'parsed_document', 'input_binding_id': 'original', 'document': original['value']['alignment_id'],
        'member_id_rule': 'first_whitespace_token', 'molecule': molecule, 'host_member_joins': [], 'evidence': []}
    declarations = {'common': {'version': 'bvbrc_alignment_associations_v1', 'analysis_id': 'analysis',
        'input_sequences': [selection], 'row_joins': [], 'automatic_row_joins': [{'alignment': aligned['value']['alignment_id'],
        'input_binding_ids': ['original'], 'method': 'exact_unique_header', 'case_policy': 'literal', 'gap_policy': 'literal',
        'transformation_ids': [], 'evidence': []}], 'transformations': [], 'correspondences': [],
        'feature_genomes': [], 'source_records': [], 'member_entities': []}, 'functions': None, 'taxonomy': None}
    return {'inputs': (inp,), 'documents': tuple(documents), 'declarations': declarations}


def value_of(operands):
    result = extract_alignment_associations(**operands)
    assert result['value'] is not None, result
    return result['value']


def forbid_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('I/O, network or subprocess called during pure replay')
    for name in ('open',):
        monkeypatch.setattr('builtins.' + name, forbidden)
    for name in ('read_text', 'read_bytes', 'write_text', 'write_bytes', 'open'):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)


def test_occurrence_identity_percent_unicode_roundtrip():
    assert input_member_occurrence_subject_id('a/b%', 'é ?/', 12) == 'input_member_occurrence:a%2Fb%25/%C3%A9%20%3F%2F/12'
    with pytest.raises(ValueError, match='bvbrc_alignment_provider_'):
        input_member_occurrence_subject_id('a', 'b', True)


@pytest.mark.parametrize('molecule,data', [('dna', '>a\nAC\n>b\nAT\n'), ('protein', '>a\nMK\n>b\nML\n')])
def test_unique_alignment_retains_original_occurrences_and_detaches(molecule, data):
    operands = common_fixture(data, molecule=molecule); before = deepcopy(operands)
    value = value_of(operands)
    assert [r['state'] for r in value['row_members']] == ['resolved', 'resolved']
    assert [m['original_length'] for m in value['original_members']] == [2, 2]
    assert operands == before
    value['original_members'][0]['evidence'].append(evidence())
    assert operands == before


def test_duplicate_labels_and_duplicate_sequences_are_not_arbitrary_joins():
    duplicate = common_fixture('>same\nAC\n>same\nAT\n')
    value = value_of(duplicate)
    assert [m['key']['occurrence_index'] for m in value['original_members']] == [0, 1]
    assert all(r['state'] == 'conflicting' and len(r['member_keys']) == 2 for r in value['row_members'])
    assert value['dependence_groups'][0]['kind'] == 'duplicate_original_label'
    equal = common_fixture('>one\nAC\n>two\nAC\n', '>x\nAC\n>y\nAC\n')
    equal['declarations']['common']['automatic_row_joins'][0]['method'] = 'exact_unique_sequence'
    value = value_of(equal)
    assert all(r['state'] == 'conflicting' for r in value['row_members'])
    assert any(g['kind'] == 'identical_sequence' for g in value['dependence_groups'])


def test_inline_occurrences_ranges_unicode_malformed_and_no_acquisition():
    original = 'orphan\n>same details\r\nac g\r\ntt\n>same details\nAé\n>\nA!\n>empty\n'
    inp = binding(original, inline=True)
    inp['members'] = [{'member_id': 'same', 'member_pointer': '/input/original', 'length': None,
        'molecule': 'dna', 'sequence_sha256': None, 'evidence': None}]
    result = extract_inline_fasta_members(inp, id_rule='first_whitespace_token', encoding='ascii', molecule='dna')
    assert result['status'] == 'partial'; value = result['value']
    assert [r['sequence'] for r in value['rows']] == ['acgtt', 'Aé', 'A!', '']
    assert [m['key']['occurrence_index'] for m in value['members']] == [0, 1, 0]
    assert value['members'][1]['sequence_sha256'] is None
    assert all(m['host_member_id'] is None and m['source_document_id'] is None for m in value['members'])
    assert value['requirements'] == []
    assert original[value['rows'][0]['character_start_0based']:value['rows'][0]['character_end_0based_exclusive']] == '>same details\r\nac g\r\ntt\n'
    assert all('artifact' not in r and 'source_location' not in r for r in value['rows'])
    operands = common_fixture(original, output='>x\nA\n', inline=True)
    operands['inputs'] = (inp,); operands['declarations']['common']['input_sequences'][0]['encoding'] = 'ascii'
    common = value_of(operands)
    assert common['inline_inputs'][0] == value
    assert common['requirements'] and all(r['kind'] != 'input_bytes' for r in common['requirements'])


def test_explicit_entities_multiple_features_share_occurrence_and_no_container_join():
    operands = common_fixture('>same\nAC\n>same\nAC\n')
    decl = operands['declarations']['common']; ev = evidence('response')
    decl['input_sequences'][0]['evidence'] = [ev]
    decl['source_records'] = [{'source_record_id': name, 'kind': kind, 'evidence': ev}
        for name, kind in [('f1-record', 'feature'), ('f2-record', 'feature'), ('g-record', 'genome')]]
    value = value_of(operands)
    assert all(m['feature_ids'] == [] and m['genome_ids'] == [] for m in value['original_members'])
    key = value['original_members'][1]['key']
    decl['member_entities'] = [{'member_key': key, 'subject': {'kind': 'feature', 'id': name, 'source_record_id': name + '-record'}, 'evidence': [ev]} for name in ('f1', 'f2')]
    decl['feature_genomes'] = [{'feature_id': 'f1', 'genome_id': 'genome-1', 'source_record_id': 'g-record', 'evidence': [ev]}]
    value = value_of(operands)
    assert value['original_members'][0]['feature_ids'] == []
    assert value['original_members'][1]['feature_ids'] == ['f1', 'f2']
    assert value['original_members'][1]['genome_ids'] == ['genome-1']
    forged = deepcopy(value); forged['original_members'][0]['feature_ids'] = ['f1']
    with pytest.raises(ValueError, match='member_entity_array_conflict'):
        c.validate_association_set(forged, inputs=operands['inputs'], documents=operands['documents'])
    for mutate in ('unknown_occurrence', 'wrong_kind', 'empty_evidence', 'duplicate'):
        bad = deepcopy(operands)
        if mutate == 'unknown_occurrence':
            bad['declarations']['common']['member_entities'][0]['member_key']['occurrence_index'] = 99
        elif mutate == 'wrong_kind':
            bad['declarations']['common']['source_records'][0]['kind'] = 'genome'
        elif mutate == 'empty_evidence':
            bad['declarations']['common']['member_entities'][0]['evidence'] = []
        else:
            bad['declarations']['common']['member_entities'].append(deepcopy(bad['declarations']['common']['member_entities'][0]))
        assert extract_alignment_associations(**bad)['status'] == 'invalid'


def transformed_fixture():
    operands = common_fixture('>dna\nCCCCAT\n>other\nAAA\n', '>product\nMGK\n')
    decl = operands['declarations']['common']; decl['automatic_row_joins'] = []
    key = {'input_binding_id': 'original', 'member_id': 'dna', 'occurrence_index': 0}
    other = {'input_binding_id': 'original', 'member_id': 'other', 'occurrence_index': 0}
    ref = {'alignment_id': 'aligned#alignment', 'row_index': 0}
    base = {'input_members': [key, other], 'input_rows': [], 'output_rows': [ref], 'evidence': [evidence()]}
    decl['transformations'] = [dict(base, transformation_id='concat', kind='concatenate', segment_order=['a', 'b'],
        output_intervals=[{'segment_id': 'a', 'interval_0based_half_open': [0, 2]}, {'segment_id': 'b', 'interval_0based_half_open': [2, 3]}]),
        dict(base, input_members=[key], transformation_id='translate', kind='translate', translation_table=11, frame=0, strand='-', input_intervals=[[0, 6]]),
        dict(base, input_members=[other], transformation_id='translate-other', kind='translate', translation_table=11, frame=0, strand='+', input_intervals=[[0, 3]])]
    decl['row_joins'] = [{'association_id': 'explicit', **ref, 'member_keys': [key, other], 'transformation_ids': ['concat', 'translate', 'translate-other'],
        'state': 'resolved', 'basis': 'transformation_record', 'evidence': [evidence()]}]
    decl['correspondences'] = [{**ref, 'column_0based': 0, 'staged_ungapped_position_0based': 0,
        'original_member': {'input_binding_id': 'original', 'member_id': 'dna'}, 'original_interval_0based_half_open': [3, 6],
        'strand': '-', 'translation_table': 11, 'transformation_id': 'translate', 'evidence': [evidence()]}]
    decl['correspondences'].extend([{**decl['correspondences'][0], 'column_0based': 1, 'staged_ungapped_position_0based': 1,
        'original_interval_0based_half_open': [0, 3]}, {**decl['correspondences'][0], 'column_0based': 2,
        'staged_ungapped_position_0based': 2, 'original_member': {'input_binding_id': 'original', 'member_id': 'other'},
        'original_interval_0based_half_open': [0, 3], 'strand': '+', 'transformation_id': 'translate-other'}])
    return operands


def test_explicit_reverse_translation_and_concatenation_maps():
    operands = transformed_fixture()
    value = value_of(operands)
    assert value['correspondences'][0]['original_interval_0based_half_open'] == [3, 6]
    forged = deepcopy(value); forged['correspondences'][0]['original_interval_0based_half_open'] = [3, 7]
    with pytest.raises(ValueError, match='original_interval_outside_member'):
        c.validate_association_set(forged, inputs=operands['inputs'], documents=operands['documents'])


def test_newick_document_and_read_outcome_use_real_tree_validator():
    raw = b'(a:1,b:2);'; a = artifact(raw, 'tree')
    parsed = parse_newick(raw, artifact=a, dialect='newick', allow_multiple=False)
    doc = {'kind': 'tree', 'value': parsed['value']}
    assert c.validate_parsed_document(doc) == doc
    reader = {'reader': 'newick', 'dialect': 'newick', 'allow_multiple': False}
    receipt = {'read_id': 'read', 'slot_id': 'tree', 'artifact': a, 'reader': reader,
        'status': parsed['status'], 'document_ids': [doc['value']['document_id']], 'diagnostics': parsed['diagnostics']}
    assert c.validate_reader_outcome(receipt, documents=(doc,)) == receipt
    forged = deepcopy(doc); forged['value']['trees'][0]['source_location']['artifact']['source_ref'] = 'forged'
    with pytest.raises(ValueError, match='bvbrc_alignment_provider_'):
        c.validate_parsed_document(forged)


def test_serialized_replay_without_io_network_or_subprocess(monkeypatch):
    operands = common_fixture(inline=True); value = value_of(operands)
    saved = json.loads(json.dumps({'operands': operands, 'value': value}))
    forbid_io(monkeypatch)
    assert c.validate_association_set(saved['value'], inputs=tuple(saved['operands']['inputs']), documents=tuple(saved['operands']['documents'])) == value
    assert extract_alignment_associations(**saved['operands'])['value'] == value


@pytest.mark.parametrize('bad', [None, [], {'reader': 'xmfa'}, {'reader': 'newick', 'dialect': 'newick', 'allow_multiple': 1}])
def test_bad_reader_shape_finite_error(bad):
    with pytest.raises(ValueError, match='bvbrc_alignment_provider_'):
        c.validate_reader_spec(bad, provider='msa')


def test_run_record_exact_types_and_populations_references():
    run = {'original_task_id': 'task', 'settings': [{'name': 'threads', 'value': 2, 'origin': 'requested', 'evidence': [], 'location': None}],
        'commands': [], 'versions': [], 'conflicts': [], 'completeness': 'unknown'}
    assert c.validate_run_record(run) == run
    run['settings'][0]['value'] = True
    with pytest.raises(ValueError, match='integer_invalid'):
        c.validate_run_record(run)
    operands = common_fixture(); associations = value_of(operands)
    population = {'population_id': 'p', 'alignment_id': 'aligned#alignment', 'row_indices': [0, 1], 'columns_0based': [0, 1], 'completeness': 'complete', 'evidence': []}
    pops = {'alignments': [population], 'composition': [], 'taxonomy': [], 'leaves': []}
    assert c.validate_populations(pops, documents=operands['documents'], associations=associations) == pops
    population['row_indices'] = [9]
    with pytest.raises(ValueError, match='bvbrc_alignment_provider_'):
        c.validate_populations(pops, documents=operands['documents'], associations=associations)


def test_accepted_xmfa_reader_is_msa_only_and_keeps_its_native_document():
    from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
    raw = b'#FormatVersion Mauve1\n> 1:1-2 + sequence\nAC\n=\n'
    a = artifact(raw, 'native.xmfa')
    parsed = parse_mauve_xmfa(raw, artifact=a, dialect='mauve1', alphabet='dna', encoding='ascii')
    assert parsed['value'] is not None, parsed
    document = {'kind': 'xmfa', 'value': parsed['value']}
    reader = {'reader': 'mauve_xmfa_v1', 'dialect': 'mauve1', 'alphabet': 'dna', 'encoding': 'ascii'}
    assert c.validate_reader_spec(reader, provider='msa') == reader
    with pytest.raises(ValueError, match='reader_provider_conflict'):
        c.validate_reader_spec(reader, provider='metacats')
    assert c.validate_parsed_document(document) == document
    outcome = {'read_id': 'xmfa-read', 'slot_id': 'full_xmfa', 'artifact': a, 'reader': reader,
        'status': parsed['status'], 'document_ids': [parsed['value']['document_id']], 'diagnostics': parsed['diagnostics']}
    assert c.validate_reader_outcome(outcome, documents=(document,)) == outcome
    forged = deepcopy(document); forged['value']['blocks'][0]['records'][0]['sequence'] = 'AA'
    with pytest.raises(ValueError, match='bvbrc_alignment_provider_'):
        c.validate_parsed_document(forged)
