"""Requested artifact delivery using real Store/receipts and synthetic jobs.

The connected cases use the existing controlled PBS/native-byte emitter. They
execute production collection and return validation, not a live database job.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_blast_database_results import REFERENCE_SOURCE
from gene_annotation_episode.native_blast_database_result_views import SAVED_INPUT_SOURCE
from gene_annotation_episode.state import Store
from test_native_blast_database_episode_binding import SyntheticHost, schema_for, selector
from test_native_blast_vdb_function_integration import connected_fixture, results_child


VERSION = 'native_blast_database_bundle_v1'


def source_record(store, *, version=VERSION, provider='episode.execution_result'):
    bundle = store.artifact(b'Synthetic retained bundle, not a native output.')
    selected = store.artifact(b'Synthetic selected artifact.')
    hidden = store.artifact(b'Synthetic unrequested artifact.')
    source = store.put('source', dict(provider=provider, accession='synthetic-352',
        uri=None, artifact_ref=bundle, text_ref=None, request_ref=None,
        version=version, retrieved_at=None, auxiliary_artifact_refs=[selected, hidden]),
        origin='tool')['id']
    return source, bundle, selected, hidden


def ledger(store):
    return [tuple(r) for r in store.db.execute(
        'SELECT * FROM runtime_record_receipts ORDER BY receipt_index')]


@pytest.mark.parametrize('kind', ['initial', 'decision_input', 'own_action',
    'child_form', 'report_redelivery'])
def test_source_custody_does_not_expand_receipts_and_explicit_refs_survive(tmp_path, kind):
    with Store(tmp_path / 'store') as store:
        source, bundle, selected, hidden = source_record(store)
        original = deepcopy(store.get(source))
        receipts = EpisodeReceipts(store, 'synthetic-352')
        receipts.bind('parent')
        receipts.receive('parent', [source], kind=kind, source_index=0)
        assert set(receipts.known('parent')) == {source}
        receipts.bind('child', 'parent')
        receipts.receive('parent', [selected, source], kind=kind, source_index=1)
        assert set(receipts.known('parent')) == {source, selected}
        assert set(receipts.known('child')) == {source}
        before = ledger(store)
        receipts.receive('parent', [source, selected], kind=kind, source_index=2)
        assert ledger(store) == before
        assert store.get(source) == original
        assert store.get(bundle)['record_type'] == store.get(hidden)['record_type'] == 'artifact'


@pytest.mark.parametrize(('provider', 'version'), [
    ('caller', VERSION), ('episode.execution_result', 'ordinary_source_v1')])
def test_other_source_types_keep_their_existing_dependencies(tmp_path, provider, version):
    with Store(tmp_path / 'store') as store:
        refs = source_record(store, provider=provider, version=version)
        receipts = EpisodeReceipts(store, 'synthetic-352')
        receipts.bind('parent')
        receipts.receive('parent', [refs[0]], kind='child_form')
        assert set(receipts.known('parent')) == set(refs)


def services_for(h):
    # Exercise the actual WorkflowServices resolver as well as reconstruction
    # with ExecutionEpisodes.services=None; no model/workflow loop is invoked.
    return WorkflowServices(SimpleNamespace(run_id=h.run_id, store=h.store,
        episode_bindings=h.family, progress_provider=None, native_event_information=None))


def assert_artifact_access(h, reference, expected, *, context=None):
    context = context or h.root
    assert h.family.resolve(context, reference, 'artifact') is expected
    assert services_for(h).reference_in_context(context, reference, 'artifact') is expected


@pytest.mark.parametrize('version', ['legacy', 'function'])
def test_actual_source_only_return_and_historical_rows_do_not_authorize_native_artifacts(
        tmp_path, monkeypatch, version):
    if version == 'function':
        h, selected = connected_fixture(tmp_path, monkeypatch)
    else:
        h = SyntheticHost(tmp_path, monkeypatch, 'psiblast')
        selected = selector('hsp')
    try:
        child = results_child(h, selected, schema=schema_for(REFERENCE_SOURCE), descriptors=False)
        outcome = h.select(child, 0, 'execution.results.collect')
        assert outcome['status'] == 'completed', outcome
        body = outcome['result']
        assert body['complete'], body['failures']
        source = h.store.get(body['publication']['source_ref'])
        custody = deepcopy(source)
        native = {source['artifact_ref'], *source['auxiliary_artifact_refs']}
        unknown = native - set(h.receipts.known(h.root.episode_id))
        assert unknown
        form, schema = h.returned(child)
        admitted = h.family.native_blast_database_returns._references({REFERENCE_SOURCE: [source['id']]})
        assert admitted == [source['id']]
        after = set(h.receipts.known(h.root.episode_id))
        assert not unknown & after
        for ref in unknown:
            assert_artifact_access(h, ref, False)
        # A later child inherits only the already delivered source, not files.
        nested = h.child(h.root, 'scientific_process', {}, schema_for(REFERENCE_SOURCE), index=2)
        assert not unknown & set(h.receipts.known(nested.episode_id))
        for ref in unknown:
            assert_artifact_access(h, ref, False, context=nested)
        # Reproduce old ledger expansion as a fixture; the repair never removes
        # or rewrites these historical rows, and they are not access authority.
        for ref in unknown:
            h.store.db.execute('INSERT INTO runtime_record_receipts '
                '(run_id,episode_id,record_ref,receipt_kind,source_index) VALUES(?,?,?,?,?)',
                (h.run_id, h.root.episode_id, ref, 'child_form', 1))
        before = ledger(h.store)
        for ref in unknown:
            assert_artifact_access(h, ref, False)
        h.returned(child)
        assert ledger(h.store) == before
        assert h.store.get(source['id']) == custody
        assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        # Explicitly supplied same-content bytes remain usable by the assigned
        # child. Presence in an unrelated source is not an exclusive owner.
        one = sorted(unknown)[0]
        supplied = h.child(h.root, 'scientific_process', {'supplied_artifact_ref': one},
            schema_for(REFERENCE_SOURCE), index=3)
        assert_artifact_access(h, one, True, context=supplied)
        for ref in unknown - {one}:
            assert_artifact_access(h, ref, False, context=supplied)
        # A failed or nested-only result is insufficient. A completed action's
        # explicit record_refs is actual independent delivery, even where old
        # ledger rows are already present. No action is executed by this fixture.
        for index, status, refs, nested_refs, expected in (
                (90, 'failed', [one], [], False),
                (91, 'completed', [], [one], False),
                (92, 'partial', [one], [], True)):
            h.journal.save('runtime_actions', dict(episode_id=h.root.episode_id,
                decision_index=index, action=canonical(dict(kind='tool',
                    tool='synthetic.independent_delivery', arguments={})),
                result=canonical(dict(status=status, record_refs=refs,
                    result={'fixture_only_refs': nested_refs})), credit=None))
            assert_artifact_access(h, one, expected)
        for ref in unknown - {one}:
            assert_artifact_access(h, ref, False)
        assert ledger(h.store) == before
        (tmp_path / 'source-only-admission.json').write_text(canonical(dict(
            form=form, schema=schema, admitted=admitted, withheld=sorted(unknown),
            historical_rows_preserved=True, source_custody_preserved=True)))
    finally:
        h.store.close()


def test_actual_selected_saved_descriptor_admits_its_artifacts_only(tmp_path, monkeypatch):
    h, selected = connected_fixture(tmp_path, monkeypatch)
    try:
        child = results_child(h, selected, schema=schema_for(SAVED_INPUT_SOURCE))
        outcome = h.select(child, 0, 'execution.results.collect')
        assert outcome['status'] == 'completed', outcome
        assert outcome['result']['complete'], outcome['result']['failures']
        h.returned(child)
        returns = h.family.native_blast_database_returns
        descriptor, = returns.received_facts(h.root, schema_for(SAVED_INPUT_SOURCE))[SAVED_INPUT_SOURCE]
        explicit = set(returns._references({SAVED_INPUT_SOURCE: [descriptor]}))
        assert explicit <= set(h.receipts.known(h.root.episode_id))
        artifact_refs = [ref for ref in explicit if h.store.get(ref)['record_type'] == 'artifact']
        assert artifact_refs
        for ref in artifact_refs:
            assert_artifact_access(h, ref, True)
        source = h.store.get(outcome['result']['publication']['source_ref'])
        hidden = set(source['auxiliary_artifact_refs']) - explicit - set(h.receipts.known(h.root.episode_id))
        assert hidden
        for ref in hidden:
            assert_artifact_access(h, ref, False)
        assert returns.resolve_saved_function_input(h.root, descriptor)['operation_key'] == outcome['result']['operation_key']
    finally:
        h.store.close()
