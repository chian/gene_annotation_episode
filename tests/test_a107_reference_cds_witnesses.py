"""Retain already computed CDS evidence without rerunning a native search.

The native text and expected legacy detector result come from real Aurora
9052184. These reader/custody checks are not a new HPC or autonomous run.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio.SeqRecord import SeqRecord
import pytest

from gene_annotation_episode.a103_detection import detect
from gene_annotation_episode.a103_scoring import _translation
from gene_annotation_episode.a107_genomic_detection_native import (
    PROFILE, REFERENCE_CDS_VERSION, matched_reference_translations,
    reference_translation_evidence, validate_reference_translations)
from gene_annotation_episode.a107_qualification import _detection
from gene_annotation_episode.component_axis_native_hpc import (
    RESULT_PROVIDER, VERSION, publish, read)
from gene_annotation_episode.state import Store


FIXTURES = Path(__file__).parent / 'fixtures'
SAVED = FIXTURES / 'a107_evaluation' / 'encoded-reference-cds'


def original_request():
    expected = json.loads((SAVED / 'original-detection.json').read_text())
    genome = FIXTURES / 'a103' / 'real' / 'rcapsulatus-bioy.gb'
    database = FIXTURES / 'a107_evaluation' / 'annotated-cds' / 'rcapsulatus-bioy.annotated.faa'
    query = str(next(SeqIO.parse(FIXTURES / 'a107_evaluation' / 'anonymous-case-02.faa', 'fasta')).seq)
    scope, = expected['record_scopes']
    assert hashlib.sha256(genome.read_bytes()).hexdigest() == scope['source_file_sha256']
    assert hashlib.sha256(database.read_bytes()).hexdigest() == expected['native_database_sha256']
    request = {'native_path': str(SAVED / 'positive-phmmer.txt'), 'database_path': str(database),
        'search_metadata': {'database_sha256': expected['native_database_sha256'],
            'native_parameters': expected['native_parameters']},
        'query_sequence': query, 'component_ref': expected['component_ref'],
        'snapshot_ref': None, 'native_source_ref': None,
        'database_source_ref': expected['database_source_ref'], 'neighborhood': None,
        'bindings': [{**scope, 'source_ref': 'source_fixture_genomic',
            'selected_accession': scope['accession'], 'genbank_projection': genome.read_text()}]}
    return request, expected


@pytest.fixture(scope='module')
def retained():
    request, expected = original_request()
    verified = []
    detection = detect(request, verified_cds=verified)
    assert detection == expected
    payload = {'version': PROFILE, 'query_sequence_sha256': hashlib.sha256(
        request['query_sequence'].encode()).hexdigest(), 'detection': detection,
        'reference_cds_verifications': matched_reference_translations(detection, verified)}
    scope, = expected['record_scopes']
    admission = {'reference_cds_verifications_version': REFERENCE_CDS_VERSION,
        'genomic_records': [{'source_ref': 'source_fixture_genomic', 'accession': scope['accession'],
            'source_request': scope['source_request']}],
        'assets': {'source_fixture_genomic': {'file': {'sha256': scope['source_file_sha256']}}}}
    return payload, admission, verified, request['query_sequence']


def test_legacy_default_result_is_the_original_real_detector_result():
    request, expected = original_request()
    assert detect(request) == expected


def test_original_verified_translation_is_retained_for_the_actual_matched_locus(retained):
    payload, admission, verified, query = retained
    assert len(verified) == 382
    witness, = payload['reference_cds_verifications']['matches']
    assert witness['source_feature_index'] == 290
    assert witness['accession'] == 'NC_014034.1'
    assert witness['segments'] == [[147967, 148540]]
    assert witness['strand'] == -1
    assert witness['coordinate_system'] == 'zero_based_half_open_record_local'
    assert witness['location_parts'] == [dict(start=147967, end=148540, strand=-1, ref=None, ref_db=None)]
    assert witness['translation']['status'] == 'verified'
    assert witness['translation']['sequence'] == witness['translation']['calculated_sequence'] == query
    assert witness['translation']['genetic_code'] == 11
    assert witness['translation']['codon_start'] == 1
    assert len(witness['translation']['nucleotide_sequence']) == 573
    assert witness['translation']['nucleotide_sequence'][-3:] in ('TAA', 'TAG', 'TGA')
    assert witness['native_target_ids'] == ['NC_014034.1:CDS:290']
    assert witness['translation_calculation']['translation_call'] == {
        'table': 11, 'cds': True, 'postprocessing': 'none'}
    validate_reference_translations(payload, admission)


def test_retained_fallback_provenance_does_not_claim_strict_cds_validation():
    record = SeqRecord(Seq('AAAGCT'), id='synthetic_fallback')
    feature = SeqFeature(FeatureLocation(0, 6, strand=1), type='CDS',
        qualifiers={'translation': ['KA'], 'transl_table': ['11']})
    original = _translation(record, feature)
    provenance = {}
    assert _translation(record, feature, calculation_provenance=provenance) == original
    assert original['status'] == 'verified' and original['sequence'] == 'KA'
    assert provenance['translation_call'] == {'table': 11, 'cds': False,
        'postprocessing': 'rstrip_terminal_stop_symbols'}


def test_sequence_equal_locus_candidates_are_not_selected_by_the_fasta_label(retained):
    payload, _, verified, _ = retained
    first = deepcopy(payload['reference_cds_verifications']['matches'][0])
    second = deepcopy(first)
    second.update(source_feature_index=999, segments=[[200000, 200573]])
    selection = {'native_hits': [{'native_target_id': 'an_untrusted_database_label',
        'sequence_sha256': first['sequence_sha256']}]}
    result = matched_reference_translations(selection, [first, second, *[
        row for row in verified if row['sequence_sha256'] != first['sequence_sha256']]])
    assert [row['source_feature_index'] for row in result['matches']] == [290, 999]
    assert all(row['native_target_ids'] == ['an_untrusted_database_label'] for row in result['matches'])


@pytest.mark.parametrize('change,error', [
    ('source', 'source_conflict'), ('sequence', 'sequence_conflict'),
    ('frame', 'frame_conflict'), ('hit', 'hit_conflict'),
])
def test_a_witness_cannot_change_its_admitted_source_sequence_frame_or_hit(retained, change, error):
    payload, admission, _, _ = retained
    altered = deepcopy(payload)
    witness = altered['reference_cds_verifications']['matches'][0]
    if change == 'source':
        witness['source_file_sha256'] = '0' * 64
    elif change == 'sequence':
        witness['translation']['calculated_sequence'] = 'M'
    elif change == 'frame':
        witness['segments'][0][1] = witness['record_length'] + 1
    else:
        witness['native_target_ids'] = ['invented-native-hit']
    with pytest.raises(ValueError, match=error):
        validate_reference_translations(altered, admission)


def test_new_requests_require_the_witness_but_historical_results_remain_readable(retained):
    payload, admission, _, _ = retained
    historical = {key: deepcopy(value) for key, value in payload.items() if key != 'reference_cds_verifications'}
    validate_reference_translations(historical, {})
    with pytest.raises(ValueError, match='requested_reference_translation_witnesses_missing'):
        validate_reference_translations(historical, admission)
    assert reference_translation_evidence(historical, payload['query_sequence_sha256'], []) is None


def test_unversioned_selected_accession_keeps_its_actual_record_identity(retained):
    payload, admission, _, _ = retained
    native, request = deepcopy(payload), deepcopy(admission)
    request['genomic_records'][0]['accession'] = 'NC_014034'
    native['reference_cds_verifications']['matches'][0]['selected_accession'] = 'NC_014034'
    validate_reference_translations(native, request)


def test_other_selected_records_in_the_same_file_do_not_shadow_a_matched_record(retained):
    payload, admission, _, _ = retained
    request = deepcopy(admission)
    request['genomic_records'].append({**request['genomic_records'][0], 'accession': 'another_record'})
    validate_reference_translations(payload, request)


def test_negative_or_unresolved_sequences_do_not_acquire_an_exact_locus(retained):
    payload, _, _, _ = retained
    negative = deepcopy(payload)
    negative['reference_cds_verifications'] = matched_reference_translations({'native_hits': []}, [])
    result = reference_translation_evidence(negative, payload['query_sequence_sha256'], [])
    assert result['matches'] == [] and result['literal_sequence_identity_supported'] is False
    unresolved = reference_translation_evidence(payload, payload['query_sequence_sha256'],
        [{'position': 0, 'symbol': 'X'}])
    assert unresolved['literal_sequence_identity_supported'] is True
    assert unresolved['biological_residue_identity_complete'] is False


@pytest.mark.parametrize('with_witness', [False, True])
def test_per_use_projection_preserves_native_values_and_unresolved_sample_origin(retained, tmp_path, with_witness):
    payload, _, _, query = retained
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence=query, molecule='protein')['subject_refs']
        native = deepcopy(payload)
        native['detection'].update(component_ref=target, binding_refs=[], target_ref=target,
            target_regions=[[0, len(query)]])
        if not with_witness:
            del native['reference_cds_verifications']
        body = {'version': VERSION, 'axis': 'A107', 'operation': 'partner.request_detection_hpc',
            'scientific_profile': PROFILE, 'scope': store.validate_scope(), 'target_ref': target,
            'target_regions': [[0, len(query)]], 'run_id': 'retained-native-reader-control',
            'hpc_result_ref': None, 'pbs_job_id': 'retained-9052184', 'native_components': native}
        reference = publish(store, RESULT_PROVIDER, body)
        result, _ = _detection(store, {'target_ref': target, 'component_ref': target,
            'detection_ref': reference}, {target, reference})
        assert result['exact_component_sequence_present'] is True
        assert result['functional_partner_presence'] is None
        assert result['target_genomic_context']['state'] == 'unresolved_target_genomic_context'
        assert result['native_hits'] == native['detection']['native_hits']
        assert read(store, reference, RESULT_PROVIDER) == body
        if with_witness:
            encoded = result['reference_encoded_correspondence']
            assert encoded['biological_residue_identity_complete'] is True
            assert encoded['matches'][0]['translation']['calculated_sequence'] == query
            assert 'submitted_target_genomic_or_sample_origin_not_established_by_reference_correspondence' in result['missing']
            assert 'independent_confirmation' in encoded['evidence_dependence']
        else:
            assert 'reference_encoded_correspondence' not in result
            assert 'target_genomic_collection_provenance_or_exact_target_placement' in result['missing']
