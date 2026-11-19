"""The acquisition library on the scoped store: files of a producer's directory captured as artifacts and read back
through custody, run as tool units of a real episode through the real runner on a real Store."""
import pytest

from .probe_world import outcomes, run, tool, world  # noqa: F401 - ``world`` is the fixture

AXES = {'hmmer_capture': ['evolutionary_history_evidence', 'gene_context_evidence', 'partner_presence_evidence',
                          'sequence_homology_evidence'],
        'blast_capture': ['evolutionary_history_evidence', 'gene_context_evidence', 'partner_presence_evidence',
                          'sequence_homology_evidence', 'structural_homology_evidence']}


def done(world, run_id, name, **arguments):
    run(world, run_id, [tool(name, **arguments)])
    return outcomes(world, run_id)[0]['outcome']


@pytest.mark.parametrize('axis', AXES['hmmer_capture'])
def test_a_profile_file_is_captured_and_read_back_through_custody(world, axis):
    out = done(world, 'hmmer_' + axis, 'hmmer_capture', axis=axis, unheld=world['source'])
    assert out['bytes_equal'] and out['size'] == 34 * 40 and out['media_type'] == 'text/plain'
    assert out['unheld']['raised'].startswith('CustodyError: record_not_held')


@pytest.mark.parametrize('axis', AXES['blast_capture'])
def test_bundle_files_are_captured_with_their_digests_through_custody(world, axis):
    out = done(world, 'blast_' + axis, 'blast_capture', axis=axis)
    assert out['bytes_equal'] and out['size'] == 34 * 40 and out['retained'] is None
    result = out['result']
    assert [row['relative_path'] for row in result['artifacts']] == ['tabular.tsv']
    assert [row['relative_path'] for row in result['invalid_artifacts']] == ['tabular.tsv']
    assert [row['stage'] for row in result['failures']] == ['capture', 'capture']
    assert result['failures'][0]['code'].startswith('native_blast_sealed_artifact_digest_mismatch')
    assert result['failures'][1]['code'] == 'native_blast_bundle_file_unavailable_or_escaped:missing.tsv'


def test_a_protein_structure_file_is_captured_and_verified_by_its_identity(world):
    out = done(world, 'structure', 'protein_structure_capture')
    assert out['bytes_equal'] and out['verified'] is None
    assert out['identity']['byte_length'] == 34 * 40 and out['identity']['format'] == 'text'
    assert out['wrong_length']['raised'] == 'ValueError: input_digest_mismatch'


def test_the_protein_query_follows_references_only_through_custody(world):
    out = done(world, 'query', 'protein_query', target=world['target'], unheld=world['source'])
    assert out['target']['ok'] == world['target']
    assert 'bad' in out['unknown']['raised'] or out['unknown']['raised'].startswith('CustodyError')
