"""Genuine global intake and original privacy deferral boundaries.

No permission verdict, scope validator, Store record or application module is
replaced. No API transport, scientific execution or root workflow is invoked.
"""
from copy import deepcopy
import hashlib
import sys

import pytest

from gene_annotation_episode import materials
from gene_annotation_episode.domain import identity
from gene_annotation_episode.state import Store


def _intake_with_actual_privacy_observation(store, **arguments):
    """Observe actual Python returns; never replace either validator's code."""
    owners = {
        ('gene_annotation_episode.enrichr_reference_privacy', 'enrichr_reference_restriction'): 'enrichr',
        ('gene_annotation_episode.molecular_reference_privacy', 'molecular_reference_restriction'): 'molecular',
    }
    observations = []
    previous = sys.getprofile()

    def observe(frame, event, result):
        owner = owners.get((frame.f_globals.get('__name__'), frame.f_code.co_name))
        if owner is not None and event == 'return':
            observations.append({'owner': owner, 'reference': frame.f_locals['reference'],
                'context': frame.f_locals['context'], 'private_only': frame.f_locals['private_only'],
                'verdict': result})
        if callable(previous):
            previous(frame, event, result)

    sys.setprofile(observe)
    try:
        problem = store.create_problem(**arguments)
    finally:
        sys.setprofile(previous)
    assert sys.getprofile() is previous
    return problem, observations


@pytest.mark.parametrize('representation', ['raw', 'fasta'])
def test_real_fresh_intake_calls_both_original_privacy_validators_and_reopens(tmp_path, representation):
    if representation == 'raw':
        original_bytes = b'ATGAAATAG'
        arguments = {'raw_sequence': original_bytes.decode('ascii'), 'molecule': 'dna', 'role': 'assembly'}
        expected = [('input', b'ATGAAATAG')]
    else:
        original_bytes = b'>query\nACGT\n>reference\nAGGT\n'
        supplied = tmp_path / 'engineering.fasta'
        supplied.write_bytes(original_bytes)
        arguments = {'input_path': supplied, 'format': 'fasta', 'molecule': 'dna', 'role': 'assembly'}
        expected = [('query', b'ACGT'), ('reference', b'AGGT')]
    directory = tmp_path / 'store'
    with Store(directory) as store:
        problem, observations = _intake_with_actual_privacy_observation(store, **arguments)
        assert problem['intake_status'] == 'completed' and problem['intake_feedback'] == []
        assert problem['target_binding'] == 'sequence_targets'
        assert len(problem['subject_refs']) == len(expected)
        assert {row['owner'] for row in observations} == {'enrichr', 'molecular'}
        assert all(row['context'] is None and row['private_only'] is True and row['verdict'] is None
                   for row in observations)
        checked = {owner: {row['reference'] for row in observations if row['owner'] == owner}
                   for owner in ('enrichr', 'molecular')}
        scope = store.validate_scope({'subject_refs': problem['subject_refs']})
        assert scope == {'subject_refs': sorted(problem['subject_refs'])}
        for ordinal, (reference, (name, sequence)) in enumerate(zip(problem['subject_refs'], expected)):
            target = store.get_input(reference)
            assert target['name'] == name and target['origin'] == 'caller'
            assert target['record_type'] == 'input' and target['input_issues'] == []
            assert target['length'] == store.subject_length(reference) == len(sequence)
            assert target['unit'] == store.subject_unit(reference) == 'nt'
            assert target['source_record']['ordinal'] == ordinal
            payload = {key: value for key, value in target.items() if key not in {'id', 'record_type', 'origin'}}
            assert reference == identity('input', payload)
            source = store.get(target['source_ref'])
            assert source['provider'] == 'caller' and source['origin'] == 'caller'
            assert store.get_artifact(source['artifact_ref']) == original_bytes
            assert source['artifact_ref'] in checked['enrichr'] & checked['molecular']
            assert target['sequence_ref'] in checked['enrichr'] & checked['molecular']
            # Re-enter the actual access-authority boundary, including both
            # validators and the verified content hash, for each selected input.
            actual_path = materials.artifact_path(store, target['sequence_ref'])
            assert actual_path.read_bytes() == sequence
            assert target['sequence_ref'] == 'artifact_' + hashlib.sha256(sequence).hexdigest()
        saved = deepcopy(problem)
    with Store(directory) as reopened:
        assert reopened.problem() == saved
        assert reopened.validate_scope(scope) == scope
        assert [materials.artifact_path(reopened, reopened.get_input(ref)['sequence_ref']).read_bytes()
                for ref in saved['subject_refs']] == [sequence for _, sequence in expected]


def _tables(store):
    return [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


def test_real_fresh_store_deferrals_do_not_create_runtime_tables_or_permission_receipts(tmp_path):
    from gene_annotation_episode import enrichr_reference_privacy as enrichr
    from gene_annotation_episode import molecular_reference_privacy as molecular
    with Store(tmp_path / 'store') as store:
        reference = store.artifact(b'ordinary caller bytes', 'text/plain')
        before, changes = _tables(store), store.db.total_changes
        assert 'tool_operations' not in before and 'runtime_actions' not in before
        assert enrichr.matching_enrichr_publications(store, reference) == []
        assert enrichr.enrichr_reference_restriction(store, None, reference, 'artifact', private_only=True) is None
        assert molecular.molecular_reference_restriction(store, None, reference, 'artifact', private_only=True) is None
        assert materials.artifact_path(store, reference).read_bytes() == b'ordinary caller bytes'
        assert _tables(store) == before and store.db.total_changes == changes


def test_source_marker_alone_is_not_an_authenticated_enrichr_publication(tmp_path):
    from gene_annotation_episode import enrichr_reference_privacy as enrichr
    from gene_annotation_episode import molecular_reference_privacy as molecular
    with Store(tmp_path / 'store') as store:
        artifact = store.artifact(b'{"engineering_source_marker":true}', 'application/json')
        source = store.put('source', {'provider': 'enrichr', 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='external')
        before, changes = _tables(store), store.db.total_changes
        assert 'tool_operations' not in before and 'runtime_actions' not in before
        for reference, namespace in ((source['id'], 'source'), (artifact, 'artifact')):
            assert enrichr.matching_enrichr_publications(store, reference) == []
            assert enrichr.enrichr_reference_restriction(store, None, reference, namespace, private_only=True) is None
            assert molecular.molecular_reference_restriction(store, None, reference, namespace, private_only=True) is None
        assert _tables(store) == before and store.db.total_changes == changes


def test_direct_malformed_classifier_fails_closed_without_publication_authentication(tmp_path):
    """Exercise the original malformed-row rejection after pure owner recovery.

    No selected publication chain is supplied or authenticated. The historical
    missing-api_services failure remains prior-stage evidence; a genuine producer
    and its authenticated publication/receipt integration remain pending.
    """
    from gene_annotation_episode import enrichr_reference_privacy as enrichr
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
    with Store(tmp_path / 'store') as store:
        reference = store.artifact(b'not a selected publication', 'text/plain')
        before, changes = _tables(store), store.db.total_changes
        with pytest.raises(ReportBoundaryError) as caught:
            enrichr.committed_enrichr_reference_kind(store, None, reference)
        assert type(caught.value) is ReportBoundaryError
        assert caught.value.diagnostic['code'] == 'enrichr_foreign_publication_conflict'
        assert isinstance(caught.value.__cause__, TypeError)
        assert _tables(store) == before and store.db.total_changes == changes
