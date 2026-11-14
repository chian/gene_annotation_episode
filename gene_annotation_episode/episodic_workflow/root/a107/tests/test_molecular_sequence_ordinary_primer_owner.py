"""Real ordinary-primer argument boundaries; no acquisition or native execution."""
from copy import deepcopy
import hashlib
import pytest

from gene_annotation_episode.episodic_workflow.root.a107 import molecular_sequence_ordinary as ordinary
from gene_annotation_episode.episodic_workflow.root.a107.library import primer_placement_result_contracts as owner


def operands(*, scalar=False):
    def record(reference, sequence):
        raw = sequence.encode('ascii')
        digest = hashlib.sha256(raw).hexdigest()
        return {'version': 'ordinary_primer_placement_sequence_operand_v1',
            'subject': {'id': reference}, 'sequence': sequence, 'parent_mapping': None,
            'mapping_failure': {'code': 'subregion_mapping_unavailable'},
            'input_file': {'artifact_ref': 'artifact_' + digest, 'sha256': digest,
                'size_bytes': len(raw), 'format': 'ascii_sequence'},
            'associations': {}, 'footprint': []}
    primer = record('subject_primer', 'AC')
    arguments = {'target_ref': 'subject_target',
        'primer_refs': 'subject_primer' if scalar else ['subject_primer', 'subject_primer']}
    operand = {'version': 'ordinary_primer_placement_operands_v1',
        'target': record('subject_target', 'ACGT'),
        'primers': primer if scalar else [primer, deepcopy(primer)]}
    return arguments, operand


def invoke(boundary, arguments, operand):
    if boundary == 'operand':
        return ordinary._operand(operand, arguments, operation='align_sequences')
    if boundary == 'native_arguments':
        return ordinary._native_arguments('align_sequences', arguments, operand)
    if boundary == 'scientific_context':
        return ordinary._scientific_context('align_sequences', arguments, operand)
    raise AssertionError(boundary)


def expected(boundary, arguments, operand):
    if boundary == 'operand':
        return deepcopy(operand)
    if boundary == 'native_arguments':
        return {'long_seq': 'ACGT', 'short_seqs': 'AC' if type(operand['primers']) is dict else ['AC', 'AC']}
    return {'target_ref': 'subject_target', 'primer_refs': ['subject_primer'] if type(operand['primers']) is dict else ['subject_primer', 'subject_primer'],
        'target_mapping': None, 'primer_mappings': [None] if type(operand['primers']) is dict else [None, None]}


@pytest.mark.parametrize('boundary', ['operand', 'native_arguments', 'scientific_context'])
@pytest.mark.parametrize('scalar', [False, True])
def test_real_ordinary_primer_boundary_retains_shape_and_duplicate_occurrences(boundary, scalar):
    arguments, operand = operands(scalar=scalar)
    before = deepcopy((arguments, operand))
    actual = invoke(boundary, arguments, operand)
    assert actual == expected(boundary, arguments, operand)
    direct = {'operand': owner.validate_operands, 'native_arguments': owner.native_arguments,
        'scientific_context': owner.scientific_context}[boundary]
    assert actual == (direct(operand, arguments) if boundary == 'operand' else direct(arguments, operand))
    assert (arguments, operand) == before


@pytest.mark.parametrize('boundary', ['operand', 'native_arguments', 'scientific_context'])
@pytest.mark.parametrize('failure', ['operand_file_identity_conflict', 'primer_input_form_conflict', 'duplicate_operand_conflict'])
def test_real_ordinary_primer_boundary_preserves_invalid_outcomes(boundary, failure):
    arguments, operand = operands()
    if failure == 'operand_file_identity_conflict':
        operand['target']['sequence'] = 'TGCA'
    elif failure == 'primer_input_form_conflict':
        arguments['primer_refs'] = 'subject_primer'
    else:
        operand['primers'][1]['associations'] = {'observed': 'different'}
    with pytest.raises(ValueError, match='^ordinary_primer_placement_' + failure + '$'):
        invoke(boundary, arguments, operand)
