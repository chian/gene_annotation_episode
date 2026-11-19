"""The records library on real records through the real runner: each function runs in a tool unit of the library
probe episode on the scoped store, its tables are declared work tables, and what it writes is held by the Episode as
produced by the unit."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.scoring import (
    NATIVE_SCHEMA)

from .library_world import bare_world, world, tool, run  # noqa: F401 - the fixtures

AXES = ('gene_context_evidence', 'partner_presence_evidence')


def recurrence(target):
    return {'schema': 'a103_recurrence_v1', 'group_balanced_fraction': 0.4, 'producer_operation': 'recurrence',
            'target_ref': target}


@pytest.mark.parametrize('axis', AXES)
def test_a103_measurement_is_published_with_its_grant_row_received_back_and_read_by_credit(world, axis):
    target = world['target']
    binding = {'schema': 'a103_locus_binding_v1', 'producer_operation': 'bind', 'target_ref': target}
    result, units = run(world, 'measurement_' + axis, [
        tool('publish_measurement', axis=axis, body=recurrence(target)),
        tool('publish_measurement', axis=axis, body=binding, binding={**binding, 'genbank_projection': {'x': 1}})])
    first, second = (unit['outcome'] for unit in units)
    assert first['kind'] == 'recurrence' and first['body'] == recurrence(target)
    assert second['kind'] == 'locus_binding' and second['binding']['genbank_projection'] == {'x': 1}
    for unit in units:
        row, = unit['outcome']['rows']
        assert row.startswith('row_') and row in unit['produced'] and unit['outcome']['ref'] in unit['produced']
    assert result['result'].as_record()['credit'] == 2.0


def test_a102_native_comparison_is_published_and_its_receipt_resolved(world):
    target = world['target']
    length = 100
    native = {'schema': NATIVE_SCHEMA, 'target_ref': target, 'reference_ref': 'reference_fixture',
        'supplied_length': length, 'target_scope': [0, length], 'reference_length': length,
        'target_positions': list(range(90)), 'reference_positions': list(range(90)), 'distances_A': [1.0] * 90,
        'comparison_group': 'comparison-0', 'variant_ref': 'variant-0', 'primary': True, 'atom_selection': 'CA',
        'target_model': {'origin': 'supplied_unknown'}, 'reference_model': {'origin': 'experimental'},
        'target_structure_sha256': 'a' * 64, 'reference_structure_sha256': 'b' * 64,
        'transform_sha256': 'c' * 64, 'native_metrics': {'reported_rmsd_A': 1.0}, 'producer': 'US-align'}
    _, units = run(world, 'comparison', [tool('publish_comparison', native=native),
                                         tool('publish_comparison', native=deepcopy(native))])
    first, second = (unit['outcome'] for unit in units)
    assert first['same'] is True and first['B'] == pytest.approx(0.72)
    assert second['source_ref'] == first['source_ref'] and second['rows'] == first['rows'] and len(first['rows']) == 1
    assert first['source_ref'] in units[0]['produced']


def test_a104_attachment_is_authenticated_against_its_row_and_retained_grading(world):
    target = world['target']
    body = {'target_ref': target, 'policy': 'test_policy', 'score': 0.5}
    _, units = run(world, 'a104', [tool('attach_a104', body=body)])
    done = units[0]['outcome']
    assert done['received'] == [{**body, 'source_ref': done['source'],
                                 'grading_artifact_ref': done['received'][0]['grading_artifact_ref']}]
    assert done['source'] in units[0]['produced']


def test_a103_attachment_row_is_written_with_its_source_and_received(world):
    target = world['target']
    body = {'target_ref': target, 'policy': 'test_policy', 'score': 0.5}
    _, units = run(world, 'a103_attachment', [tool('attach_a103', measurement=recurrence(target), body=body,
                                                   target_ref=target)])
    done = units[0]['outcome']
    received, = done['received']
    assert received['source_ref'] == done['source'] and received['policy'] == 'test_policy'
    assert received['measurement_ref'] == done['measurement'] and done['rows'] == [done['source']]


def test_a102_attachment_request_and_attachment_are_rows_and_the_attachment_is_received(world):
    target = world['target']
    body = {'target_ref': target, 'policy': 'direct_native_geometry_v1', 'score': 0.5}
    _, units = run(world, 'a102_attachment', [tool('attach_a102', request={'operation': 'structure.reference_align'},
                                                   body=body, target_ref=target)])
    done = units[0]['outcome']
    received, = done['received']
    assert received['source_ref'] == done['source'] and received['request_ref'] == done['request']
    assert done['request_rows'] == [done['request']] and done['attachment_rows'] == [done['source']]


@pytest.mark.parametrize('axis', AXES)
def test_a_completed_native_search_snapshot_is_authenticated_from_its_row(world, axis):
    _, units = run(world, 'search_' + axis, [tool('search_receipt', axis=axis, component_ref=world['target'])],
                    held=[world['store'].get(world['target'])['sequence_ref']])
    assert units[0]['outcome'] == {'same_body': True, 'sequence': True}


def test_public_sources_and_private_auxiliaries_are_judged_among_the_held_sources(world):
    _, units = run(world, 'restriction', [tool('source_restriction')])
    assert units[0]['outcome'] == {'source': True, 'artifact': True, 'request': False, 'private': False,
                                   'not_permitted': False, 'private_only': None, 'unrelated': None,
                                   'wrong_namespace': False}


@pytest.mark.parametrize('axis', ('partner_presence_evidence', 'structural_homology_evidence',
                                  'perturbation_evidence'))
def test_a_producer_file_is_retained_as_an_artifact_and_declared_files_are_captured(world, tmp_path, axis):
    produced = tmp_path / 'producer' / 'out'
    produced.mkdir(parents=True)
    (produced / 'result.txt').write_text('native result bytes')
    _, units = run(world, 'capture_' + axis, [tool('capture_file', axis=axis, directory=str(tmp_path / 'producer'))])
    done = units[0]['outcome']
    assert done['bytes'] == 'native result bytes' and done['size'] == len('native result bytes')
    assert done['identity']['sha256'] == hashlib.sha256(b'native result bytes').hexdigest()
    assert done['held_as_produced'] == 'produced' and done['identity']['artifact_ref'] in units[0]['produced']
    assert done['outcomes'] == ['verified', 'unavailable', 'declared_absent']


@pytest.mark.parametrize('axis', ('biochemical_feasibility_evidence', 'evolutionary_history_evidence',
                                  'experimental_activity_evidence', 'gene_context_evidence',
                                  'partner_presence_evidence', 'perturbation_evidence', 'sample_context_evidence',
                                  'sequence_homology_evidence', 'structural_homology_evidence'))
def test_the_read_library_target_is_identified_without_the_store(world, axis):
    _, units = run(world, 'library_' + axis, [tool('library_identity', axis=axis, input_ref=world['target'])])
    assert units[0]['outcome'] == {'is_library': False, 'read': 'read_subject_' + 'a' * 24 + 'b' * 24}


def test_the_metadata_source_of_a_search_is_checked_against_the_subjects_of_the_scope(world):
    _, units = run(world, 'rfam', [tool('rfam_scope', target_ref=world['target'])])
    assert units[0]['outcome'] == {'source': True}


@pytest.mark.parametrize('axis', ('evolutionary_history_evidence', 'gene_context_evidence',
                                  'partner_presence_evidence', 'sequence_homology_evidence',
                                  'structural_homology_evidence'))
@pytest.mark.parametrize('program', ('blast', 'hmmer'))
def test_captured_artifacts_of_a_native_bundle_are_copied_into_the_scratch_directory(world, axis, program):
    _, units = run(world, 'captured_%s_%s' % (axis, program), [
        tool('captured', axis=axis, program=program, text='>q\nMKTAYIAKQR\n')])
    assert units[0]['outcome'] == {'custody': True, 'failures': [], 'copies': ['>q\nMKTAYIAKQR\n'],
                                   'names': ['query.fa']}


@pytest.mark.parametrize('axis', ('evolutionary_history_evidence', 'gene_context_evidence',
                                  'partner_presence_evidence', 'sequence_homology_evidence',
                                  'structural_homology_evidence'))
def test_a_window_of_a_held_subject_sequence_is_read_through_the_held_artifact(world, axis):
    _, units = run(world, 'window_' + axis, [tool('subject_window', axis=axis, ref=world['target'], start=3,
                                                  end=12)],
                    held=[world['store'].get(world['target'])['sequence_ref']])
    assert units[0]['outcome'] == {'window': 'AYIAKQRQI'}


@pytest.mark.parametrize('module', ('native_blast_masking_result_publication',
                                    'similarity_search.native_blast_utility_result_publication'))
def test_an_artifact_is_given_to_a_native_worker_as_a_scratch_file(world, module):
    _, units = run(world, 'staged_' + module.split('.')[-1], [tool('staged_file', module=module,
                                                                  text='native input bytes')])
    done = units[0]['outcome']
    assert done['first'] is True and done['text'] == 'native input bytes' and done['same_identity'] is True
    assert done['identity'] == {'sha256': hashlib.sha256(b'native input bytes').hexdigest(),
                                'size_bytes': len('native input bytes')}
