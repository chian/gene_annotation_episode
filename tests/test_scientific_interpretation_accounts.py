"""Synthetic ownership boundary for local interpretation accounts."""
from gene_annotation_episode.state import Store
from test_scientific_hypervolume_runtime import annotation


def test_member_local_account_reference_preserves_its_scope_through_context(tmp_path):
    # A small boundary fixture, not another development workload or target gene.
    from test_library_scope_ownership import fixture, hypothesis
    store, tools, target, member, other, scope = fixture(tmp_path)
    with store:
        h = store.put('hypothesis', hypothesis(member['id']), origin='reasoning', scope=scope)
        account = store.put('interpretation_account', annotation(member['id'], h['id'], [], 0),
                            origin='reasoning', scope=scope, account_owner=('run', 'child'))
        source = store.put('source', {'provider': 'synthetic_fixture', 'accession': 'context',
            'uri': None, 'artifact_ref': store.artifact('SYNTHETIC context'), 'text_ref': None,
            'request_ref': None, 'version': 'fixture', 'retrieved_at': None}, origin='external')
        context = store.put('context', {'context_type': 'sample', 'name': 'SYNTHETIC',
            'source_ref': source['id'], 'attributes': [], 'related_refs': [account['id']]},
            origin='external', scope=scope)
        # Exercise ownership propagation through context.related_refs.
        reached = store._ownership_reach([context['id']])
        assert reached['library_refs'] == []
        assert reached['context_segments'] == store.coverage(member['id'])
        assert {span['member_ref'] for span in reached['context_segments']} == {member['member_ref']}
