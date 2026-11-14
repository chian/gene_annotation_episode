"""Controlled publication-kind inputs; genuine context and receipt consumers.

Only matching_enrichr_publications and committed_enrichr_reference_kind are
controlled for named real artifact references. These tests do not authenticate
an Enrichr producer, selected publication, API transport or scientific result.
The Store, typed requests, Journal, context authentication and receipt/inheritance
readers are real. A None verdict means defer, never permission to read a File.
"""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode import enrichr_reference_privacy as privacy
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext as GlobalContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import BindingContext as ForeignContext
from gene_annotation_episode.episodic_workflow.root.communication import plain, ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.method_loop.episode import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext as RootContext
from gene_annotation_episode.episodic_workflow.root.task_values import Record


RUN = 'controlled-enrichr-receipt-consumer'


class GlobalSubclass(GlobalContext):
    pass


class RootSubclass(RootContext):
    pass


def capture_context(store, scope, *, path=(('annotation', 'root'),), parent=None, save=True):
    """Use the actual typed request and public Journal/receipt write APIs."""
    journal = Journal(store, RUN)
    receipts = EpisodeReceipts(store, RUN)
    episode_id = EpisodeRef(RUN, path).episode_id
    manifest = receipts.bind(episode_id, None if parent is None else parent.episode_id)
    arguments = dict(objective='Check received references without executing science',
                     result_contract={'role': path[-1][0]})
    goal = (EpisodeGoal.root(**arguments) if parent is None else
            EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']), **arguments))
    request = EpisodeRequest(goal, Record({'scope': plain(scope), 'initial_report': {},
        'episode_assignment': {}, 'knowledge_inheritance': manifest})).as_record()
    context = RootContext(RUN, episode_id, path[-1][0], path, scope, {}, request)
    if save:
        with store.transaction():
            journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
                'request': canonical(request), 'initial_credit': 0, 'state': 'active',
                'completion': None, 'archive': None})
        assert reader(store).authenticate(context) is context
    return context, receipts


def reader(store):
    return EpisodeReturnRecords(store, RUN, failure_prefix='enrichr_reference_')


def controlled_kind(monkeypatch, store, mapping):
    """Two explicit classifier seams, never an authority or receipt replacement."""
    rows = {reference: object() for reference in mapping}
    assert all(store.get(reference)['record_type'] == 'artifact' for reference in mapping)

    def matching(actual_store, reference, *, current_run_id=None):
        assert actual_store is store and current_run_id is None
        return [rows[reference]] if reference in rows else []

    def classify(actual_store, row, reference):
        assert actual_store is store and row is rows[reference]
        return mapping[reference]

    monkeypatch.setattr(privacy, 'matching_enrichr_publications', matching)
    monkeypatch.setattr(privacy, 'committed_enrichr_reference_kind', classify)


def restrict_without_writes(store, context, reference, namespace='artifact', **options):
    before = store.db.total_changes
    verdict = privacy.enrichr_reference_restriction(store, context, reference, namespace, **options)
    assert store.db.total_changes == before
    return verdict


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / 'store') as store:
        problem = store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        scope = store.validate_scope({'subject_refs': problem['subject_refs']})
        context, receipts = capture_context(store, scope)
        raw = store.artifact(b'controlled raw bytes; no provider observation', 'text/plain')
        yield store, context, receipts, raw


@pytest.mark.parametrize('kind,eligible', [
    ('global', True), ('global_subclass', True), ('root', True),
    ('root_subclass', False), ('foreign_axis', False), ('attributes', False), ('none', False),
])
def test_controlled_raw_kind_preserves_global_isinstance_and_exact_root_eligibility(saved, monkeypatch, kind, eligible):
    store, root, _, raw = saved
    values = root.as_record()
    classes = {'global': GlobalContext, 'global_subclass': GlobalSubclass,
        'root': RootContext, 'root_subclass': RootSubclass, 'foreign_axis': ForeignContext,
        'attributes': SimpleNamespace}
    context = None if kind == 'none' else classes[kind](**values)
    assert RootContext is not GlobalContext and ForeignContext not in (RootContext, GlobalContext)
    # All non-None fixtures have authentic original values. Eligibility remains
    # a separate exact class boundary; duck-typed values must not broaden it.
    if context is not None:
        assert reader(store).authenticate(context) is context
    controlled_kind(monkeypatch, store, {raw: 'raw'})
    verdict = restrict_without_writes(store, context, raw, initial_record_refs=[raw])
    assert verdict is (None if eligible else False)


def test_controlled_raw_kind_requires_explicit_file_receipt_not_source_marker(saved, monkeypatch):
    store, context, receipts, raw = saved
    source = store.put('source', {'provider': 'enrichr', 'accession': None, 'uri': None,
        'artifact_ref': raw, 'text_ref': None, 'request_ref': None,
        'version': None, 'retrieved_at': None}, origin='external')
    controlled_kind(monkeypatch, store, {raw: 'raw'})
    assert restrict_without_writes(store, context, raw) is False
    receipts.receive(context.episode_id, [source['id']], kind='initial')
    assert set(receipts.known(context.episode_id)) == {source['id']}
    assert restrict_without_writes(store, context, raw) is False
    assert restrict_without_writes(store, context, raw, initial_record_refs=[source['id']]) is False
    # A context's advisory field is not a substitute for real receipt storage.
    assert restrict_without_writes(store, replace(context, received_record_refs=(raw,)), raw) is False
    receipts.receive(context.episode_id, [raw], kind='initial')
    assert set(receipts.known(context.episode_id)) == {source['id'], raw}
    assert restrict_without_writes(store, context, raw) is None
    changes = store.db.total_changes
    receipts.receive(context.episode_id, [raw], kind='initial')
    assert store.db.total_changes == changes
    assert restrict_without_writes(store, context, raw, namespace='source') is False
    assert restrict_without_writes(store, context, raw, namespace=None) is None


def test_controlled_raw_kind_preserves_saved_authentication_and_original_request(saved, monkeypatch):
    store, context, receipts, raw = saved
    receipts.receive(context.episode_id, [raw], kind='initial')
    controlled_kind(monkeypatch, store, {raw: 'raw'})
    restored = reader(store).context(context.episode_id)
    assert type(restored) is RootContext and restored.as_record() == context.as_record()
    assert restrict_without_writes(store, restored, raw) is None
    for invalid in (replace(context, episode_id='foreign-episode'),
                    replace(context, run_id='foreign-run'),
                    replace(context, path=(('annotation', 'foreign-valid-path'),)),
                    replace(context, assignment={'unrecorded': True}),
                    replace(context, scope={'subject_refs': []})):
        with pytest.raises(ValueError, match='enrichr_reference_context_conflict'):
            reader(store).authenticate(invalid)
        assert restrict_without_writes(store, invalid, raw, initial_record_refs=[raw]) is False
    request = plain(context.request)
    request['message']['episode_assignment'] = {'unrecorded': True}
    changed = replace(context, assignment=request['message']['episode_assignment'], request=request)
    with pytest.raises(ValueError, match='enrichr_reference_original_context_conflict'):
        reader(store).authenticate(changed)
    assert restrict_without_writes(store, changed, raw, initial_record_refs=[raw]) is False


def test_controlled_raw_kind_preserves_original_allow_unsaved_initial_input(saved, monkeypatch):
    store, _, _, raw = saved
    scope = store.validate_scope({'subject_refs': store.problem()['subject_refs']})
    unsaved, _ = capture_context(store, scope, path=(('annotation', 'unsaved'),), save=False)
    with pytest.raises(ValueError, match='enrichr_reference_saved_context_required'):
        reader(store).authenticate(unsaved)
    assert reader(store).authenticate(unsaved, allow_unsaved=True) is unsaved
    controlled_kind(monkeypatch, store, {raw: 'raw'})
    assert restrict_without_writes(store, unsaved, raw) is False
    assert restrict_without_writes(store, unsaved, raw, initial_record_refs=[raw]) is None
    assert restrict_without_writes(store, replace(unsaved, assignment={'changed': True}), raw,
                                   initial_record_refs=[raw]) is False


def test_controlled_raw_kind_freezes_real_parent_receipt_prefix_and_reopens(saved, monkeypatch):
    store, parent, receipts, first = saved
    later = store.artifact(b'later delivered raw bytes', 'text/plain')
    receipts.receive(parent.episode_id, [first], kind='initial')
    child, _ = capture_context(store, parent.scope,
        path=parent.path + (('evidence', 'child'),), parent=parent)
    frozen = receipts.manifest(child.episode_id)
    receipts.receive(parent.episode_id, [later], kind='decision_input', source_index=0)
    assert receipts.bind(child.episode_id, parent.episode_id) == frozen
    assert set(receipts.known(parent.episode_id)) == {first, later}
    assert set(receipts.known(child.episode_id)) == {first}
    controlled_kind(monkeypatch, store, {first: 'raw', later: 'raw'})
    assert restrict_without_writes(store, child, first) is None
    assert restrict_without_writes(store, child, later, initial_record_refs=[later]) is False
    with Store(store.path) as reopened:
        actual = reader(reopened).context(child.episode_id)
        assert type(actual) is RootContext
        inherited = EpisodeReceipts(reopened, RUN)
        assert inherited.manifest(child.episode_id) == frozen
        assert set(inherited.known(child.episode_id)) == {first}
        controlled_kind(monkeypatch, reopened, {first: 'raw', later: 'raw'})
        assert restrict_without_writes(reopened, actual, first) is None
        assert restrict_without_writes(reopened, actual, later, initial_record_refs=[later]) is False


def test_controlled_private_and_contextless_deferrals_keep_original_order(saved, monkeypatch):
    store, context, receipts, raw = saved
    receipts.receive(context.episode_id, [raw], kind='initial')
    controlled_kind(monkeypatch, store, {raw: 'private'})
    assert restrict_without_writes(store, context, raw, initial_record_refs=[raw]) is False
    assert restrict_without_writes(store, None, raw, private_only=True) is False
    controlled_kind(monkeypatch, store, {raw: 'raw'})
    assert restrict_without_writes(store, None, raw) is False
    assert restrict_without_writes(store, None, raw, private_only=True) is None
    controlled_kind(monkeypatch, store, {raw: 'source'})
    assert restrict_without_writes(store, None, raw) is None
    controlled_kind(monkeypatch, store, {})
    assert restrict_without_writes(store, None, raw) is None


@pytest.mark.parametrize('options', [{'private_only': 1}, {'initial_record_refs': {1}},
                                     {'initial_record_refs': [1]}])
def test_controlled_kind_keeps_original_boundary_error_owner(saved, monkeypatch, options):
    store, context, _, raw = saved
    controlled_kind(monkeypatch, store, {raw: 'raw'})
    changes = store.db.total_changes
    with pytest.raises(ReportBoundaryError) as caught:
        privacy.enrichr_reference_restriction(store, context, raw, 'artifact', **options)
    assert type(caught.value) is ReportBoundaryError
    assert caught.value.diagnostic['code'] == 'enrichr_original_context_conflict'
    assert store.db.total_changes == changes
