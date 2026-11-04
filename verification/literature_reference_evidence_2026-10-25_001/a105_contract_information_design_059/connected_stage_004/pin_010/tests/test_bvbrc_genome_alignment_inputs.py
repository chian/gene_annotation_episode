"""Offline input extraction with explicitly SYNTHETIC task/custody bindings.

Source-shaped native stdout and actual FASTA byte strings test parsing and
relationships. They establish no live BV-BRC job, host possession or same-run
input provenance. The real public C value validator checks every result.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_genome_alignment_inputs import (
    extract_genome_alignment_inputs, validate_genome_alignment_supplied_value_shapes,
)
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import validate_genome_alignment_inputs
from gene_annotation_episode.execution_contracts import canonical, digest
from test_bvbrc_genome_alignment_retained_records import (
    PREFIX, acquisition_record, content, fixture, inline, log_bytes, log_record, rewrap,
)


def metadata(value, data, *, name='metadata', pointer='/value'):
    raw = canonical({'value': value}).encode()
    binding = content(raw, name)
    data[binding['artifact_ref']] = raw
    return {'evidence': {'content': binding, 'pointer': pointer}, 'value': deepcopy(value)}


def candidate(task, data, *, raw=b'>one exact header\nACGT\n>two\nry\n', name='candidate', file_id=None, binding=None):
    binding = content(raw, name) if binding is None else binding
    data[binding['artifact_ref']] = raw
    value = {'kind': 'genome_alignment_staged_file', 'original_task_id': task['task_id'],
        'file_id': name if file_id is None else file_id, 'native_path_token': '/task/work/123.1.fasta',
        'content': binding, 'genome_occurrence_indices': [0], 'retrieval': {'query': 'asserted query',
            'requested_record_limit': 25000, 'reported_total_records': 2, 'returned_records': 2,
            'state': 'complete', 'evidence': [{'content': content(b'{}', 'asserted-census'), 'pointer': ''}]}}
    return metadata(value, data, name=name + ':metadata')


def extract(task, records, data, values=()):
    result = extract_genome_alignment_inputs(task, supplied_values=values,
        supplied_bytes=data, retained_records=records)
    if result['value'] is not None:
        validate_genome_alignment_inputs(result['value'])
        assert result['requirements'] == result['value']['requirements']
        assert result['diagnostics'] == result['value']['diagnostics']
    return result


def codes(result):
    return {d['code'].removeprefix(PREFIX) for d in result['diagnostics']}


def test_filled_candidate_lengths_stay_separate_from_run_denominators():
    task, request, handoff, data = fixture()
    log = log_record(task, request, data)
    supplied = candidate(task, data)
    before = deepcopy((task, request, handoff, log, data, supplied))
    result = extract(task, (handoff, log), data, (supplied,))
    value = result['value']
    assert result['status'] == 'partial'
    assert [r['genome_id'] for r in value['genome_occurrences']] == ['123.1', '456.2']
    assert value['invocation']['observed_argv'] == ['progressiveMauve', '--output=/task/work/alignment.xmfa',
                                                 '/task/work/123.1.fasta', '/task/work/456.2.fasta']
    assert value['invocation']['observed_program_version'] is None
    assert [f['artifact'] for f in value['files'][:2]] == [None, None]
    file = value['files'][2]
    assert file['native_path_token'] == value['files'][0]['native_path_token']
    assert file['file_id'] != value['files'][0]['file_id']
    assert [len(r['sequence']) for r in file['records']] == [4, 2]
    assert [r['header'] for r in file['records']] == ['one exact header', 'two']
    assert file['retrieval'] == {'query': None, 'requested_record_limit': None, 'reported_total_records': None,
        'returned_records': 2, 'state': 'unknown', 'evidence': []}
    assert file['same_run_state'] == file['path_state'] == 'unverified'
    assert file['genome_occurrence_indices'] == []
    assert [m['source_length'] for m in value['member_bindings']] == [None]*4
    assert value['xmfa_source_inputs'] is None and value['original_maps'] == []
    assert value['genome_census_state'] == 'unknown'
    assert (task, request, handoff, log, data, supplied) == before
    value['files'][2]['records'][0]['sequence'] = 'changed detached result'
    assert (task, request, handoff, log, data, supplied) == before


@pytest.mark.parametrize('binding_kind', ['scalar', 'group', 'supplied_link', 'ambiguous', 'none'])
def test_original_scalar_group_and_duplicate_occurrence_pointers(binding_kind):
    genomes = ['123.1', '123.1']
    scalar = inline('scalar-0', '/genome_ids/0', genomes[0])
    group = inline('original-ordered-group', '/genome_ids', genomes)
    bindings = {'scalar': [scalar], 'group': [group], 'none': [],
        'supplied_link': [inline('original-link', '/genome_ids/0', genomes[0], kind='supplied_link')],
        'ambiguous': [scalar, group]}[binding_kind]
    task, request, handoff, data = fixture(genomes, bindings=bindings)
    log = log_record(task, request, data, raw=log_bytes(genomes))
    result = extract(task, (handoff, log), data)
    value = result['value']
    expected = {'scalar': ['scalar-0', None], 'group': ['original-ordered-group']*2,
        'supplied_link': ['original-link', None], 'ambiguous': [None, 'original-ordered-group'], 'none': [None, None]}
    assert [o['input_binding_id'] for o in value['genome_occurrences']] == expected[binding_kind]
    assert [o['parameter_pointer'] for o in value['genome_occurrences']] == ['/genome_ids/0', '/genome_ids/1']
    assert [o['occurrence_index'] for o in value['genome_occurrences']] == [0, 1]
    assert 'duplicate_genome_occurrence' in codes(result)
    assert ('genome_occurrence_conflict' in codes(result)) == (binding_kind == 'ambiguous')
    assert len(value['files']) == 1
    assert value['files'][0]['genome_occurrence_indices'] == [0, 1]
    assert value['invocation']['ordered_file_ids'][0] == value['invocation']['ordered_file_ids'][1]


def test_unrelated_member_pointers_never_invent_original_scalar_bindings():
    binding = inline('group', '/genome_ids', ['123.1', '456.2'])
    # The group relation is exact on its own, even with no MemberFact rows.
    task, _, handoff, data = fixture(bindings=[binding])
    result = extract(task, (handoff,), data)
    assert [o['input_binding_id'] for o in result['value']['genome_occurrences']] == ['group', 'group']


def test_all_required_missing_inputs_are_retained_without_zero_denominators():
    task, _, _, _ = fixture()
    result = extract(task, (), {})
    assert result['status'] == 'partial' and len(result['value']['genome_occurrences']) == 2
    assert all(not o['evidence'] for o in result['value']['genome_occurrences'])
    assert {'metadata_record_unverified', 'invocation_missing', 'staged_file_missing',
            'genome_census_unknown', 'feature_map_missing', 'native_execution_unverified'} <= codes(result)
    assert result['value']['invocation']['effective_recipe'] is None


@pytest.mark.parametrize('mutate', ['application', 'missing', 'empty', 'integer', 'wrong_recipe'])
def test_uninterpretable_original_inputs_and_semantic_recipe_conflict(mutate):
    task, _, _, _ = fixture()
    if mutate == 'application': task.update(required_application_id='Homology', native_application_id='Homology')
    elif mutate == 'missing': del task['submitted_parameters']['genome_ids']
    elif mutate == 'empty': task['submitted_parameters']['genome_ids'] = []
    elif mutate == 'integer': task['submitted_parameters']['genome_ids'] = ['123.1', 4]
    else: task['submitted_parameters']['recipe'] = 'unsupported'
    result = extract(task, (), {})
    if mutate == 'wrong_recipe':
        assert result['status'] == 'partial' and result['value'] is not None
        assert result['value']['invocation']['recipe_basis'] == 'conflicting'
    else:
        assert result['status'] == 'invalid' and result['value'] is None


@pytest.mark.parametrize('recipe,count,mode', [('progressiveMauve', 1, 'single_file_entries'),
    ('progressiveMauve', 2, 'multiple_files_concatenated'),
    ('mauveAligner', 1, 'unknown'), ('mauveAligner', 2, 'multiple_files_concatenated')])
def test_actual_recipe_modes_and_legacy_sml_pairs(recipe, count, mode):
    genomes = ['123.1', '456.2'][:count]
    task, request, handoff, data = fixture(genomes, recipe=recipe)
    paths = ['/task/work/input with spaces.fasta', '/task/work/other.fasta'][:count]
    raw = log_bytes(genomes, recipe=recipe, paths=paths, options=('--weight=3',))
    log = log_record(task, request, data, raw=raw)
    result = extract(task, (handoff, log), data)
    invocation = result['value']['invocation']
    assert invocation['effective_recipe'] == recipe
    assert invocation['mode'] == mode
    assert invocation['observed_argv'][2] == paths[0]
    assert invocation['observed_argv'][-1] == '--weight=3'
    if recipe == 'mauveAligner':
        assert invocation['observed_argv'][3] == paths[0] + '.sml'
    if mode == 'unknown':
        assert 'invocation_missing' in codes(result)


@pytest.mark.parametrize('mutate,expected', [
    ('empty', 'invocation_missing'), ('partial_transport', 'invocation_missing'),
    ('window', 'invocation_missing'), ('invalid_utf8', 'invocation_missing'),
    ('truncated_operands', 'invocation_missing'), ('unterminated_group', 'invocation_missing'),
    ('missing_retrieval', 'invocation_conflict'), ('swapped_retrieval', 'invocation_conflict'),
    ('extra_operand', 'invocation_conflict'), ('unsupported_option', 'invocation_conflict'),
    ('option_order', 'invocation_conflict'), ('duplicate_option', 'invocation_conflict'),
    ('nul', 'invocation_conflict'), ('cr', 'invocation_conflict'), ('duplicate_commands', 'invocation_conflict')])
def test_bad_native_log_is_local_and_candidate_records_survive(mutate, expected):
    task, request, handoff, data = fixture()
    raw, complete, window = log_bytes(), True, None
    if mutate == 'empty': raw = b''
    elif mutate == 'partial_transport': complete = False
    elif mutate == 'window': window = {'start': 0, 'end_exclusive': 10}
    elif mutate == 'invalid_utf8': raw = b'\xff' + raw
    elif mutate == 'truncated_operands': raw = raw[:raw.index(b'/task/work/456.2.fasta\n')]
    elif mutate == 'unterminated_group': raw = raw[:raw.index(b'Sequence loaded successfully.')]
    elif mutate == 'missing_retrieval': raw = raw.replace(b'Writing /task/work/456.2.fasta...\n', b'')
    elif mutate == 'swapped_retrieval': raw = raw.replace(b'Fetching genome: 456.2', b'Fetching genome: 999.9')
    elif mutate == 'extra_operand': raw = raw.replace(b'Sequence loaded successfully.', b'/unexpected/file\nSequence loaded successfully.')
    elif mutate == 'unsupported_option': raw = raw.replace(b'Sequence loaded successfully.', b'--guess=1\nSequence loaded successfully.')
    elif mutate == 'option_order': raw = raw.replace(b'Sequence loaded successfully.', b'--weight=3\n--seed-weight=4\nSequence loaded successfully.')
    elif mutate == 'duplicate_option': raw = raw.replace(b'Sequence loaded successfully.', b'--weight=3\n--weight=3\nSequence loaded successfully.')
    elif mutate == 'nul': raw = raw.replace(b'--output=', b'--output=\x00')
    elif mutate == 'cr': raw = raw.replace(b'--output=', b'--output=\r')
    else: raw += log_bytes()
    log = log_record(task, request, data, raw=raw, complete=complete, window=window)
    supplied = candidate(task, data)
    result = extract(task, (handoff, log), data, (supplied,))
    assert expected in codes(result)
    assert result['value']['invocation']['observed_argv'] is None
    assert [len(r['sequence']) for r in result['value']['files'][0]['records']] == [4, 2]


def test_legacy_sml_correspondence_is_exact_not_basename_based():
    task, request, handoff, data = fixture(recipe='mauveAligner')
    raw = log_bytes(recipe='mauveAligner').replace(b'/task/work/123.1.fasta.sml', b'/elsewhere/123.1.fasta.sml')
    log = log_record(task, request, data, raw=raw)
    result = extract(task, (handoff, log), data)
    assert 'invocation_conflict' in codes(result)


@pytest.mark.parametrize('exit_code', [None, '1', '-9', 'null'])
def test_reported_argv_survives_unverified_native_execution(exit_code):
    task, request, handoff, data = fixture()
    log = log_record(task, request, data, raw=log_bytes(exit_code=exit_code))
    result = extract(task, (handoff, log), data)
    assert result['value']['invocation']['effective_recipe'] == 'progressiveMauve'
    assert 'native_execution_unverified' in codes(result)


def test_bad_receipt_neighbor_cannot_erase_valid_original_log_and_fasta():
    task, request, handoff, data = fixture(bindings=[inline('genomes', '/genome_ids', ['123.1', '456.2'])])
    good = log_record(task, request, data)
    bad = log_record(task, request, data, name='wrong-task')
    bad['record']['value']['task_id'] = '900002'
    bad = rewrap(bad, data)
    supplied = candidate(task, data)
    result = extract(task, (bad, handoff, good), data, (supplied,))
    assert 'metadata_task_conflict' in codes(result)
    assert [o['input_binding_id'] for o in result['value']['genome_occurrences']] == ['genomes', 'genomes']
    assert result['value']['invocation']['recipe_basis'] == 'observed_argv'
    assert len(result['value']['files'][-1]['records']) == 2
    failures = [d for d in result['diagnostics'] if d['code'] == PREFIX + 'metadata_task_conflict']
    assert failures[0]['path'] == '/retained_records/0'
    assert failures[0]['evidence_refs'] == [bad['record']['source_ref']]


def test_two_bad_sources_keep_two_distinct_requirements():
    task, request, handoff, data = fixture()
    logs = [log_record(task, request, data, name='bad-' + str(i)) for i in range(2)]
    for row in logs:
        del data[row['receipt_content']['artifact_ref']]
    result = extract(task, (handoff, *logs), data)
    rows = [r for r in result['requirements'] if r['reason_code'] == PREFIX + 'content_missing']
    assert len(rows) == 2 and len({r['requirement_id'] for r in rows}) == 2


def test_conflicting_receipt_reference_group_is_entirely_unusable():
    task, request, handoff, data = fixture()
    first = log_record(task, request, data, name='same-ref')
    second = log_record(task, request, data, raw=log_bytes(paths=['/a.fasta', '/b.fasta']), name='same-ref')
    good = log_record(task, request, data, name='independent-valid')
    result = extract(task, (handoff, first, second, good), data)
    assert result['value']['invocation']['observed_argv'][-2:] == ['/task/work/123.1.fasta', '/task/work/456.2.fasta']
    assert 'metadata_record_unverified' in codes(result)
    assert 'invocation_conflict' not in codes(result)


def test_exact_duplicate_receipts_do_not_create_independent_files_or_invocations():
    task, request, handoff, data = fixture()
    log = log_record(task, request, data)
    a, b = extract(task, (handoff, log), data), extract(task, (handoff, log, deepcopy(log)), data)
    assert a == b


def test_conflicting_complete_native_invocations_preserve_occurrences_and_candidate_bytes():
    task, request, handoff, data = fixture()
    first = log_record(task, request, data, name='first')
    second = log_record(task, request, data, raw=log_bytes(paths=['/a.fasta', '/b.fasta']), name='second')
    supplied = candidate(task, data)
    result = extract(task, (handoff, first, second), data, (supplied,))
    assert result['value']['invocation']['recipe_basis'] == 'conflicting'
    assert len(result['value']['genome_occurrences']) == 2
    assert len(result['value']['files'][0]['records']) == 2


def test_differently_bound_request_cannot_reuse_original_handoff():
    task, request, handoff, data = fixture(bindings=[inline('real-group', '/genome_ids', ['123.1', '456.2'])])
    changed = deepcopy(request)
    changed['input_bindings'] = []
    log = log_record(task, changed, data)
    result = extract(task, (handoff, log), data)
    assert 'metadata_task_conflict' in codes(result)
    assert result['value']['invocation']['observed_argv'] is None
    assert [o['input_binding_id'] for o in result['value']['genome_occurrences']] == ['real-group']*2


@pytest.mark.parametrize('reverse', [False, True])
def test_two_different_handoff_references_cannot_both_claim_the_original_submission(reverse):
    task, request, handoff, data = fixture(bindings=[inline('original-group', '/genome_ids', ['123.1', '456.2'])])
    foreign = deepcopy(handoff)
    foreign['record']['value']['receipt']['receipt_ref'] = 'synthetic:another-submission'
    foreign['record']['value']['original_task']['submission_receipt_ref'] = 'synthetic:another-submission'
    foreign = rewrap(foreign, data)
    records = (foreign, handoff) if reverse else (handoff, foreign)
    result = extract(task, records, data)
    assert 'metadata_task_conflict' in codes(result)
    assert [o['input_binding_id'] for o in result['value']['genome_occurrences']] == ['original-group']*2


@pytest.mark.parametrize('reverse', [False, True])
def test_conflicting_handoff_representations_never_choose_a_request_by_order(reverse):
    task, request, handoff, data = fixture(bindings=[inline('first-group', '/genome_ids', ['123.1', '456.2'])])
    other_request = deepcopy(request)
    other_request['input_bindings'][0]['binding_id'] = 'incompatible-group'
    other = deepcopy(handoff)
    selected = other['record']['value']['receipt']['snapshot']['selected_operands']
    selected['native_operands']['request'] = other_request
    selected['request_sha256'] = digest(other_request)
    other = rewrap(other, data)
    log = log_record(task, request, data)
    records = (other, handoff, log) if reverse else (handoff, other, log)
    result = extract(task, records, data)
    assert 'metadata_record_unverified' in codes(result)
    assert [o['input_binding_id'] for o in result['value']['genome_occurrences']] == [None, None]
    assert result['value']['invocation']['recipe_basis'] == 'observed_argv'


@pytest.mark.parametrize('raw,entries,sequences', [
    (b'>a full\r\nAC\r\nGT\r\n>b\r\nNn', [1, 2], ['ACGT', 'Nn']),
    (b'>good\nAC\n>bad\nAC-G\n>next\nTT\n', [1, 3], ['AC', 'TT']),
    (b'>good\nAC\n>bad\nACUX\n>next\nTT\n', [1, 3], ['AC', 'TT']),
    (b'>good\nAC\n>trailing empty\n', [1], ['AC']),
    (b'not fasta\n>good\nAC\n', [1], ['AC']),
    (b'', [], []), (b'CLUSTAL W\nsequence AC\n', [], []),
    (b'>bad\nAC\x0bGT\n>good\nTT\n', [2], ['TT']),
])
def test_full_fasta_records_exact_locations_and_malformed_neighbors(raw, entries, sequences):
    task, _, handoff, data = fixture()
    supplied = candidate(task, data, raw=raw)
    result = extract(task, (handoff,), data, (supplied,))
    file = result['value']['files'][0]
    assert [r['entry_1based'] for r in file['records']] == entries
    assert [r['sequence'] for r in file['records']] == sequences
    for record in file['records']:
        loc = record['source_location']
        fragment = raw[loc['byte_start_0based']:loc['byte_end_0based_exclusive']]
        assert fragment.startswith(b'>')
        assert fragment.split(b'\n')[0].rstrip(b'\r')[1:].decode() == record['header']
        assert loc['line_start_1based'] == 1 + raw[:loc['byte_start_0based']].count(b'\n')
    if raw.startswith(b'>a full'):
        assert file['record_completeness'] == 'complete'
    else:
        assert file['record_completeness'] == 'partial' and 'source_records_partial' in codes(result)
    if b'AC-G' in raw or b'ACUX' in raw or b'\x0b' in raw:
        assert 'source_sequence_mismatch' in codes(result)


def test_transport_truncation_does_not_certify_a_valid_looking_final_fasta_record():
    task, request, handoff, data = fixture()
    raw = b'>first\nACGT\n>last\nAC\n'
    acquired = acquisition_record(task, request, data, raw=raw, complete=False)
    binding = acquired['record']['value']['snapshot']['content']
    supplied = candidate(task, data, raw=raw, binding=binding)
    result = extract(task, (handoff, acquired), data, (supplied,))
    file = result['value']['files'][0]
    assert file['record_completeness'] == 'partial'
    assert [r['sequence'] for r in file['records']] == ['ACGT']
    assert file['retrieval']['state'] == 'unknown'
    assert file['same_run_state'] == 'unverified'


@pytest.mark.parametrize('mutation', ['missing_bytes', 'wrong_bytes', 'wrong_pointer', 'wrong_task'])
def test_bad_candidate_cannot_delete_its_valid_neighbor(mutation):
    task, _, handoff, data = fixture()
    good = candidate(task, data, name='good')
    bad = candidate(task, data, raw=b'>different\nAATTCC\n', name='bad')
    if mutation == 'missing_bytes': del data[bad['value']['content']['artifact_ref']]
    elif mutation == 'wrong_bytes': data[bad['value']['content']['artifact_ref']] += b'X'
    elif mutation == 'wrong_pointer': bad['evidence']['pointer'] = '/no-such-value'
    else:
        bad['value']['original_task_id'] = '900002'
        bad = metadata(bad['value'], data, name='bad:metadata')
    result = extract(task, (handoff,), data, (bad, good))
    good_file = next(f for f in result['value']['files'] if f['file_id'] == 'good')
    assert [len(r['sequence']) for r in good_file['records']] == [4, 2]
    if mutation == 'wrong_task':
        assert next(f for f in result['value']['files'] if f['file_id'] == 'bad')['same_run_state'] == 'conflicting'


def test_conflicting_candidate_ids_preserve_both_byte_sets_with_local_identities():
    task, _, handoff, data = fixture()
    first = candidate(task, data, name='first', file_id='asserted-shared')
    second = candidate(task, data, name='second', file_id='asserted-shared', raw=b'>other\nAAAAAAA\n')
    result = extract(task, (handoff,), data, (first, second))
    files = result['value']['files']
    assert len({f['file_id'] for f in files}) == 2
    assert [[len(r['sequence']) for r in f['records']] for f in files] == [[4, 2], [7]]
    assert 'native_path_conflict' in codes(result)


def test_metadata_invocation_assertion_cannot_override_observed_native_argv():
    task, request, handoff, data = fixture()
    log = log_record(task, request, data)
    supplied = metadata({'kind': 'genome_alignment_invocation', 'original_task_id': task['task_id'],
        'argv': ['mauveAligner', '--version'], 'program_version': 'fictional deployment',
        'ordered_file_ids': ['fabricated'], 'mode': 'single_file_entries'}, data)
    result = extract(task, (handoff, log), data, (supplied,))
    assert result['value']['invocation']['effective_recipe'] == 'progressiveMauve'
    assert result['value']['invocation']['observed_program_version'] is None
    assert {'invocation_conflict', 'metadata_record_unverified'} <= codes(result)


@pytest.mark.parametrize('bad', [False, True])
def test_contig_feature_interval_assertions_do_not_create_native_relationships(bad):
    task, _, handoff, data = fixture()
    supplied = candidate(task, data)
    a = {'source_ref': supplied['value']['content']['source_ref'],
         'raw_artifact_ref': supplied['value']['content']['artifact_ref'],
         'sha256': supplied['value']['content']['sha256']}
    contig = {'kind': 'genome_alignment_contig_identity', 'original_task_id': task['task_id'],
        'file_id': 'candidate', 'record_id': 'missing-record' if bad else 'candidate:record:1',
        'sequence_id': 'asserted-sequence', 'accession': 'NC_asserted', 'accession_version': 'NC_asserted.1',
        'genome_occurrence_indices': [0]}
    feature = {'kind': 'genome_alignment_feature_mapping', 'original_task_id': task['task_id'],
        'feature': {'input_binding_id': 'asserted-input', 'member_id': 'asserted-feature', 'occurrence_index': 0},
        'original_length': 4, 'genome_occurrence_index': 0, 'segments': [{
            'segment_id': 'asserted-segment', 'file_id': 'candidate', 'record_id': 'candidate:record:1',
            'feature_interval_0based_half_open': [0, 7 if bad else 4],
            'record_interval_0based_half_open': [0, 4], 'strand': '+',
            'transformation_id': 'asserted-transform', 'evidence': []}]}
    interval = {'kind': 'genome_alignment_interval_mapping', 'original_task_id': task['task_id'],
        'bbcols_artifact': a, 'xmfa_artifact': a, 'mappings': [
            {'native_interval_index_0based': 7, 'xmfa_block_index': 0},
            {'native_interval_index_0based': 8, 'xmfa_block_index': 0 if bad else 1}],
        'omitted_native_interval_indices': []}
    wrappers = tuple(metadata(v, data, name=v['kind']) for v in (contig, feature, interval))
    result = extract(task, (handoff,), data, (supplied, *wrappers))
    value = result['value']
    assert value['feature_bindings'] == value['original_maps'] == []
    assert all(r['sequence_id'] is None and r['accession_version'] is None for r in value['contig_bindings'])
    assert {'metadata_record_unverified', 'feature_map_missing', 'interval_join_missing'} <= codes(result)
    if bad:
        assert {'contig_identity_conflict', 'feature_map_conflict', 'interval_join_conflict'} <= codes(result)
    # Shape is independently closed for each variant, including unused fields.
    for wrapper in wrappers:
        broken = deepcopy(wrapper)
        broken['value']['assume_verified'] = True
        with pytest.raises(ValueError, match='^' + PREFIX + 'argument_invalid$'):
            validate_genome_alignment_supplied_value_shapes((broken,))


def test_unknown_candidate_transfer_completeness_stays_unknown():
    task, request, handoff, data = fixture()
    raw = b'>candidate\nACGT\n'
    acquired = acquisition_record(task, request, data, raw=raw)
    acquired['record']['value']['artifact']['transfer'].update(object_complete='unknown', total_size=None)
    acquired = rewrap(acquired, data)
    supplied = candidate(task, data, raw=raw, binding=acquired['record']['value']['snapshot']['content'])
    result = extract(task, (handoff, acquired), data, (supplied,))
    assert result['value']['files'][0]['record_completeness'] == 'unknown'
    assert result['value']['files'][0]['retrieval']['state'] == 'unknown'


def test_retained_native_v4_counts_survive_missing_source_identity_in_actual_consumer():
    # Authentic upstream file bytes; its relationship to this synthetic task is
    # deliberately unclaimed. This exercises only C -> existing A arithmetic.
    from test_mauve_v4_formats import OFFICIAL, parse
    from test_mauve_v4_calculators import selection
    from gene_annotation_episode.mauve_v4_calculators import calculate_mauve_v4_segments
    task, request, handoff, data = fixture(recipe='mauveAligner')
    log = log_record(task, request, data, raw=log_bytes(recipe='mauveAligner'))
    supplied = candidate(task, data)
    inputs = extract(task, (handoff, log), data, (supplied,))['value']
    document = parse(OFFICIAL.read_bytes())['value']
    native = calculate_mauve_v4_segments(document,
        selection=selection(document, denominator='native_declared_length'), inputs=inputs)
    staged = calculate_mauve_v4_segments(document,
        selection=selection(document, denominator='validated_staged_length'), inputs=inputs)
    assert [c['known_union_bases']['value'] for c in native['coverage']] == [690, 2000]
    assert native['coverage'][0]['coverage_fraction']['value'] == 690 / 693
    assert [c['known_union_bases']['value'] for c in staged['coverage']] == [690, 2000]
    assert all(c['denominator_bases']['value'] is None and c['coverage_fraction']['value'] is None
               for c in staged['coverage'])
    assert native['pair_segments'][2]['counts']['identical_canonical']['value'] == 4
    assert all(req in native['requirements'] and req in staged['requirements'] for req in inputs['requirements'])


def test_retained_source_default_is_labelled_expectation_not_deployment():
    task, _, handoff, data = fixture(recipe=...)
    source = Path('verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/p3_mauve/scripts/p3-mauve.js').read_bytes()
    binding = content(source, 'actual-retained-source')
    data[binding['artifact_ref']] = source
    supplied = metadata({'kind': 'genome_alignment_producer', 'original_task_id': task['task_id'],
        'application_id': 'GenomeAlignment', 'recipe': 'progressiveMauve', 'producer_source': binding,
        'native_version': 'asserted-version', 'output_artifacts': []}, data)
    result = extract(task, (handoff,), data, (supplied,))
    inv = result['value']['invocation']
    assert inv['effective_recipe'] == 'progressiveMauve' and inv['recipe_basis'] == 'retained_source_default'
    assert inv['observed_argv'] is None and inv['observed_program_version'] is None
    assert all(f['native_path_token'] is None and f['same_run_state'] == 'missing' for f in result['value']['files'])


def test_explicit_zero_and_legacy_source_option_qualifications_preserve_argv():
    task, request, handoff, data = fixture(recipe='mauveAligner', parameters={
        'weight': 0, 'seedWeight': 5, 'maxGappedAlignerLength': 100, 'hmmPGoHomologous': 0.001})
    raw = log_bytes(recipe='mauveAligner', options=('--seed-weight=5', '--max-gapped-aligner-length=100', '--hmm-p-go-homologous=0.001'))
    log = log_record(task, request, data, raw=raw)
    result = extract(task, (handoff, log), data)
    assert 'explicit_zero_not_forwarded' in codes(result)
    issues = [d['path'] for d in result['diagnostics'] if d['code'] == PREFIX + 'source_option_unsupported']
    assert '/original_task/submitted_parameters/seedWeight' in issues
    assert '/original_task/submitted_parameters/hmmPGoHomologous' in issues
    assert '/original_task/submitted_parameters/maxGappedAlignerLength' not in issues
    assert '--weight=0' not in result['value']['invocation']['observed_argv']


def test_supplied_receipt_value_is_not_provider_metadata_or_a_trust_flag():
    task, request, handoff, data = fixture()
    log = log_record(task, request, data)
    # Stored /value has the receipt self reference removed, as it really does.
    raw = data[log['receipt_content']['artifact_ref']]
    supplied = {'evidence': {'content': log['receipt_content'], 'pointer': '/value'},
                'value': json.loads(raw)['value']}
    result = extract(task, (handoff, log), data, (supplied,))
    assert 'metadata_type_unsupported' in codes(result)
    assert result['value']['invocation']['recipe_basis'] == 'observed_argv'


@pytest.mark.parametrize('mutation', ['extra', 'missing', 'wrong_type', 'nonfinite', 'wrapper_extra'])
def test_recognized_metadata_shape_errors_raise_before_local_data_recovery(mutation):
    task, _, handoff, data = fixture()
    supplied = candidate(task, data)
    if mutation == 'extra': supplied['value']['trusted'] = True
    elif mutation == 'missing': del supplied['value']['content']
    elif mutation == 'wrong_type': supplied['value']['retrieval']['returned_records'] = True
    elif mutation == 'nonfinite': supplied['value']['retrieval']['returned_records'] = float('nan')
    else: supplied['unexpected'] = None
    with pytest.raises(ValueError, match='^' + PREFIX + 'argument_invalid$'):
        extract(task, (handoff,), data, (supplied,))


def test_pure_saved_input_replay_forbids_file_network_process_and_model_boundaries(monkeypatch):
    from gene_annotation_episode.providers import ModelConnection
    from gene_annotation_episode.acquisition import PublicClients
    from gene_annotation_episode.bvbrc_appservice_records import AppServiceRecords
    task, request, handoff, data = fixture()
    log = log_record(task, request, data)
    supplied = candidate(task, data)
    expected = extract(task, (handoff, log), data, (supplied,))
    # Round-trip saved JSON arguments and exact byte strings without fetching.
    task2, rows2, values2 = json.loads(json.dumps([task, [handoff, log], [supplied]]))
    def forbidden(*args, **kwargs):
        pytest.fail('pure saved-input extraction attempted I/O or execution')
    for target in ('builtins.open', 'pathlib.Path.open', 'pathlib.Path.read_text', 'pathlib.Path.read_bytes',
                   'socket.socket', 'socket.create_connection', 'subprocess.run', 'subprocess.Popen',
                   'os.system', 'urllib.request.urlopen'):
        monkeypatch.setattr(target, forbidden)
    monkeypatch.setattr(ModelConnection, 'complete', forbidden)
    monkeypatch.setattr(PublicClients, '_http', forbidden)
    monkeypatch.setattr(AppServiceRecords, 'read', forbidden)
    result = extract(task2, tuple(rows2), deepcopy(data), tuple(values2))
    assert result == expected
    assert validate_genome_alignment_supplied_value_shapes(tuple(values2)) is None


def test_unexpected_programming_errors_are_not_converted_into_missing_science(monkeypatch):
    task, _, handoff, data = fixture()
    def unexpected(*args, **kwargs):
        raise RuntimeError('deliberate programming error')
    monkeypatch.setattr('gene_annotation_episode.bvbrc_genome_alignment_inputs.validate_genome_alignment_retained_records', unexpected)
    with pytest.raises(RuntimeError, match='deliberate programming error'):
        extract(task, (handoff,), data)
