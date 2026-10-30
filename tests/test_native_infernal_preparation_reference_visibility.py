"""Metadata-only preparation custody/delivery boundary checks (workload 258).

All sources, bytes and saved actions/forms here are explicitly synthetic. The
Store, receipt journal, Workflow resolver, execution owner and child-return
authenticator are real. Positive child forms use a declared completed-results
port; they do not establish production capture/grading or nested execution.
The separate workload 257 nested tests cover that larger production path.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_infernal_preparation_returns import NativeInfernalPreparationReturns
from gene_annotation_episode.runtime import Record, TypedReportContract, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


RUN_ID = 'synthetic-preparation-reference-visibility-258'
VERSION = 'native_infernal_preparation_bundle_v1'
REFERENCE_SOURCE = 'execution_infernal_preparation_result_refs'
RECEIPT_KINDS = ('initial', 'decision_input', 'own_action', 'child_form', 'report_redelivery')


def forbidden(*args, **kwargs):
    raise AssertionError('Metadata-only visibility verification attempted forbidden work')


@pytest.fixture(autouse=True)
def no_external_or_numerical_work(monkeypatch):
    """A passing check cannot launch a native/grade subprocess or use a network."""
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode import native_infernal_preparation_results as result_module
    from gene_annotation_episode import native_infernal_preparation_result_publication as publication
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(native_lifecycle, 'start_job', forbidden)
    for module in (result_module, publication):
        monkeypatch.setattr(module, 'prepare_native_infernal_preparation_grading', forbidden)
        monkeypatch.setattr(module, 'publish_selected_preparation_result', forbidden)


@contextmanager
def metadata_only(store, monkeypatch):
    """Reject both the Store byte API and direct file reads of retained bytes."""
    original_open = io.open
    artifact_directory = store.path / 'artifacts'

    def guarded_open(file, mode='r', *args, **kwargs):
        if isinstance(file, (str, bytes, Path)):
            path = Path(file)
            if path.is_relative_to(artifact_directory) and ('r' in mode or '+' in mode):
                forbidden()
        return original_open(file, mode, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(store, 'get_artifact', forbidden)
        guard.setattr(io, 'open', guarded_open)
        yield


def retained_metadata(store):
    """Snapshot persisted records and byte-file metadata without opening data."""
    return {
        'records': [tuple(row) for row in store.db.execute('SELECT * FROM records ORDER BY id')],
        'artifacts': [tuple(row) for row in store.db.execute('SELECT * FROM artifacts ORDER BY id')],
        'files': [(str(path.relative_to(store.path)), path.stat().st_size, path.stat().st_mtime_ns)
            for path in sorted((store.path / 'artifacts').glob('*/*')) if path.is_file()],
    }


def receipt_rows(store):
    return [tuple(row) for row in store.db.execute(
        'SELECT * FROM runtime_record_receipts ORDER BY receipt_index')]


class MetadataBoundary:
    """Real Workflow/Store with no model, episode loop or native work invoked."""
    def __init__(self, tmp_path, *, assignment_ref=False, subject_bytes=False):
        self.store = Store(tmp_path / 'state')
        self.store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        self.scope = self.store.validate_scope()
        self.bundle = self.store.artifact(b'Synthetic bundle bytes; not a native bundle.')
        self.selected_bytes = b'Synthetic explicitly selected artifact.\n'
        self.selected = self.store.artifact(self.selected_bytes)
        self.unrequested = self.store.artifact(b'Synthetic unrequested auxiliary output.\n')
        self.subject_artifact = self.store.get(self.scope['subject_refs'][0])['sequence_ref']
        self.shared = self.subject_artifact if subject_bytes else self.selected
        self.source = self.new_source('preparation', auxiliary=[self.selected, self.unrequested, self.shared])
        self.tools = ToolRegistry(self.store)
        self.directory = tmp_path / 'run'
        self.resources = {'synthetic-local': {'kind': 'local', 'workspace': str(tmp_path),
            'policy': {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3, 'wall_seconds': None},
            # Configuration only: this nonexistent software is never invoked.
            'native_infernal_preparation': [{'program': 'cmemit', 'mode': 'consensus', 'software': {
                'executable': str(tmp_path / 'never-invoked-cmemit'), 'sha256': '0' * 64,
                'engine_version': 'synthetic-unexecuted-binding'}}]}}
        self.workflow = Workflow(self.store, self.tools, SimpleNamespace(complete=forbidden),
            self.directory, RUN_ID, forbidden, lambda *args, **kwargs: 0,
            episode_record_receipts=True, initial_known_record_refs=[],
            episode_binding_factories=(self.owner,))
        self.bound = self.workflow.episode_bindings.for_role('results')
        assignment = {'supplied_artifact_ref': self.shared} if assignment_ref else {}
        self.root = self.workflow.build('annotation', 'root',
            'Verify explicitly synthetic reference delivery.', self.scope, episode_assignment=assignment)
        self.context = self.workflow.binding_context(self.root.source)
        self.receipts, self.journal = self.workflow.receipts, self.workflow.journal
        self.reconstructed = self.owner(None)

    def owner(self, services):
        return ExecutionEpisodes(services, store=self.store, directory=self.directory, run_id=RUN_ID,
            resources=self.resources, initial_information={}, tool_registry=self.tools,
            handoff_unit=1, acquired_record_unit=1, log_window_bytes=64, log_roles=('stdout', 'stderr'))

    def new_source(self, label, *, provider='episode.execution_result', version=VERSION,
            auxiliary=None, artifact=None):
        return self.store.put('source', {'provider': provider, 'accession': 'synthetic-' + label,
            'uri': None, 'artifact_ref': artifact or self.bundle, 'text_ref': artifact or self.bundle,
            'request_ref': None, 'version': version, 'retrieved_at': None,
            'auxiliary_artifact_refs': list(dict.fromkeys(auxiliary or []))}, origin='tool')['id']

    def action(self, references, *, index=0, status='completed', episode_id=None, run_id=RUN_ID,
            nested_only=False):
        result = {'status': status, 'record_refs': [] if nested_only else list(references),
            'result': {'synthetic_fixture': True, 'references': list(references)}}
        self.journal.save('runtime_actions', {'run_id': run_id,
            'episode_id': episode_id or self.context.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': 'synthetic.explicit-delivery', 'arguments': {}}),
            'result': canonical(result), 'credit': None})
        return result

    def access(self, reference, namespace='artifact'):
        return self.bound.native_infernal_preparation_results.retained_reference_access(
            self.context, reference, namespace)

    def resolve(self, reference, namespace='artifact'):
        return self.workflow.resolver(self.scope, context=self.context)(reference, namespace)

    def assert_resolution(self, reference, expected, namespace='artifact'):
        assert self.resolve(reference, namespace) is expected
        assert self.reconstructed.resolve(self.context, reference, namespace) is expected

    def pollute_receipts(self, *references):
        # Deliberately reproduce historical source-expansion ledger rows. This
        # is fixture creation, never production admission or a repair migration.
        for reference in references:
            self.store.db.execute('INSERT INTO runtime_record_receipts '
                '(run_id,episode_id,record_ref,receipt_kind,source_index) VALUES(?,?,?,?,?)',
                (RUN_ID, self.context.episode_id, reference, 'child_form', 17))


@pytest.fixture
def boundary(tmp_path):
    value = MetadataBoundary(tmp_path)
    try:
        yield value
    finally:
        value.store.close()


@pytest.mark.parametrize('kind', RECEIPT_KINDS)
def test_preparation_source_custody_admits_only_explicit_selected_references(boundary, monkeypatch, kind):
    b = boundary
    before = retained_metadata(b.store)
    own_episode = 'synthetic-receiver-' + kind
    b.receipts.bind(own_episode)
    with metadata_only(b.store, monkeypatch):
        b.receipts.receive(own_episode, [b.source], kind=kind, source_index=0)
        assert set(b.receipts.known(own_episode)) == {b.source}
        b.receipts.receive(own_episode, [b.source, b.selected], kind=kind, source_index=1)
        assert set(b.receipts.known(own_episode)) == {b.source, b.selected}
        rows = receipt_rows(b.store)
        b.receipts.receive(own_episode, [b.selected, b.source], kind=kind, source_index=2)
        assert receipt_rows(b.store) == rows
        assert retained_metadata(b.store) == before
        assert b.store.get(b.selected)['sha256'] == hashlib.sha256(b.selected_bytes).hexdigest()


@pytest.mark.parametrize(('provider', 'version'), [
    ('episode.execution_result', 'native_infernal_bundle_v1'),
    ('synthetic.other_provider', VERSION),
    ('synthetic.other_provider', 'other_version'),
])
def test_other_source_provider_or_version_keeps_existing_recursive_receipts(boundary, monkeypatch,
        provider, version):
    b = boundary
    artifact = b.store.artifact(b'Synthetic ordinary-provider bytes.')
    auxiliary = b.store.artifact(b'Synthetic ordinary-provider auxiliary.')
    source = b.new_source('ordinary', provider=provider, version=version,
        artifact=artifact, auxiliary=[auxiliary])
    b.receipts.bind('ordinary-receiver')
    with metadata_only(b.store, monkeypatch):
        b.receipts.receive('ordinary-receiver', [source], kind='child_form', source_index=0)
        assert set(b.receipts.known('ordinary-receiver')) == {source, artifact, auxiliary}
        assert b.access(source, 'source') is None
        assert b.access(artifact) is None
        assert b.access(auxiliary) is None
        b.assert_resolution(auxiliary, True)


@pytest.mark.parametrize('historical_pollution', [False, True])
def test_store_scope_or_old_receipts_cannot_authorize_unrequested_preparation_bytes(boundary,
        monkeypatch, historical_pollution):
    b = boundary
    b.receipts.receive(b.context.episode_id, [b.source], kind='child_form', source_index=0)
    if historical_pollution:
        b.pollute_receipts(b.bundle, b.selected, b.unrequested)
    before, retained = receipt_rows(b.store), retained_metadata(b.store)
    with metadata_only(b.store, monkeypatch):
        for reference in (b.bundle, b.selected, b.unrequested):
            assert b.store.reference_subset([reference], b.scope) == [reference]
            assert b.access(reference) is False
            b.assert_resolution(reference, False)
        assert b.access(b.source, 'source') is False
        b.assert_resolution(b.source, False, 'source')
        assert receipt_rows(b.store) == before
        assert retained_metadata(b.store) == retained
        assert not b.store.db.execute('SELECT 1 FROM runtime_observations').fetchone()


@pytest.mark.parametrize('status', ['completed', 'partial'])
def test_independently_returned_same_content_bytes_keep_access(boundary, monkeypatch, status):
    b = boundary
    b.pollute_receipts(b.selected, b.unrequested)
    # Identical bytes have the same content identity, independently of source.
    independently_delivered = b.store.artifact(b.selected_bytes)
    assert independently_delivered == b.selected
    outcome = b.action([independently_delivered], status=status)
    before = receipt_rows(b.store)
    with metadata_only(b.store, monkeypatch):
        b.workflow.receive_outcome(b.root.source, {'kind': 'tool', 'tool': 'synthetic.explicit-delivery'},
            outcome, 0)
        assert b.access(independently_delivered) is None
        b.assert_resolution(independently_delivered, True)
        assert b.access(b.unrequested) is False
        b.assert_resolution(b.unrequested, False)
        # INSERT OR IGNORE retains the actual historical row; authority comes
        # from the explicit action result, not a rewritten receipt kind.
        assert receipt_rows(b.store) == before
        for namespace in ('source', 'subject', 'native_infernal_preparation_name', 'execution_handoff'):
            b.assert_resolution(independently_delivered, False, namespace)


@pytest.mark.parametrize('case', ['invalid', 'failed', 'pending', 'other_episode', 'other_run', 'nested_only'])
def test_attempts_and_nonreceiving_actions_do_not_authorize_retained_bytes(boundary, monkeypatch, case):
    b = boundary
    b.pollute_receipts(b.selected)
    b.action([b.selected], status=case if case in {'invalid', 'failed', 'pending'} else 'completed',
        episode_id='synthetic-other-episode' if case == 'other_episode' else None,
        run_id='synthetic-other-run' if case == 'other_run' else RUN_ID,
        nested_only=case == 'nested_only')
    with metadata_only(b.store, monkeypatch):
        assert b.access(b.selected) is False
        b.assert_resolution(b.selected, False)


@pytest.mark.parametrize('route', ['original_assignment', 'supplied_subject'])
def test_explicit_supplied_inputs_allow_shared_preparation_artifact(tmp_path, monkeypatch, route):
    b = MetadataBoundary(tmp_path, assignment_ref=route == 'original_assignment',
        subject_bytes=route == 'supplied_subject')
    try:
        with metadata_only(b.store, monkeypatch):
            assert b.access(b.shared) is None
            b.assert_resolution(b.shared, True)
            assert b.access(b.unrequested) is False
            b.assert_resolution(b.unrequested, False)
    finally:
        b.store.close()


def test_unknown_records_and_identifier_namespaces_stay_outside_provider_guard(boundary, monkeypatch):
    b = boundary
    with metadata_only(b.store, monkeypatch):
        for reference, namespace in ((b.scope['subject_refs'][0], 'subject'),
                ('source_missing', 'source'), ('artifact_missing', 'artifact'),
                (b.selected, 'native_infernal_preparation_name')):
            assert b.access(reference, namespace) is None
        b.assert_resolution(b.scope['subject_refs'][0], True, 'subject')
        b.assert_resolution('artifact_missing', False)
        b.assert_resolution(b.selected, False, 'native_infernal_preparation_name')


class SuppliedCompletedResults:
    """Explicit fixture seam; original selected-result facts are synthetic.

    Real child-return authentication still checks the original context,
    commission, requested form, frozen facts and result reference types.
    """
    def __init__(self, store):
        self.store = store

    def applies(self, context):
        return context.role == 'results' and context.assignment.get('synthetic_completed_results') is True

    def facts(self, context):
        assert self.applies(context)
        row = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=0', (context.run_id, context.episode_id)).fetchone()
        assert row is not None
        outcome = json.loads(row['result'])
        assert outcome['status'] == 'completed'
        return deepcopy(outcome['synthetic_fixture_facts'])


def install_synthetic_child_return(b):
    """Populate real journal rows without running or claiming an episode loop."""
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['selected'], 'properties': {
        'selected': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': REFERENCE_SOURCE}}}
    contract = TypedReportContract('Return the explicitly selected fixture references.', schema, lambda *_: True)
    assignment = {'synthetic_completed_results': True}
    path = (*b.context.path, ('results', 'child_0'))
    episode_id = EpisodeRef(RUN_ID, path).episode_id
    goal = EpisodeGoal.child(EpisodeGoal.from_record(plain(b.context.request)['goal']),
        objective='Return synthetic metadata only.', result_contract=schema)
    request = EpisodeRequest(goal, Record({'scope': b.scope, 'episode_assignment': assignment,
        'initial_report': {}}), contract).as_record()
    b.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
        'request': canonical(request), 'initial_credit': 0, 'state': 'yielded', 'completion': None, 'archive': None})
    selected = [b.source, b.selected]
    facts, form = {REFERENCE_SOURCE: selected}, {'selected': selected}
    b.journal.save('runtime_actions', {'episode_id': episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}),
        'result': canonical({'status': 'completed', 'record_refs': selected,
            'synthetic_fixture_facts': facts}), 'credit': None})
    b.journal.save('runtime_forms', {'episode_id': episode_id, 'facts': canonical(facts), 'form': canonical(form)})
    b.journal.save('runtime_actions', {'episode_id': b.context.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'episode_child', 'role': 'results', 'scope': b.scope,
            'assignment': assignment, 'schema_json': canonical(schema), 'purpose': contract.decision}),
        'result': None, 'credit': None})
    b.journal.save('runtime_report_attempts', {'parent_episode_id': b.context.episode_id, 'decision_index': 0,
        'delivery_ref': 'synthetic-delivery-258', 'child_episode_id': episode_id,
        'contract': canonical(contract.as_record()), 'form': canonical(form), 'failure': None})
    for owner in (b.bound, b.reconstructed):
        owner.native_infernal_preparation_returns = NativeInfernalPreparationReturns(SimpleNamespace(
            store=b.store, run_id=RUN_ID, native_infernal_preparation_results=SuppliedCompletedResults(b.store)))
    return schema, form


def test_authenticated_explicit_child_form_preserves_only_selected_references(boundary, monkeypatch):
    b = boundary
    schema, form = install_synthetic_child_return(b)
    retained = retained_metadata(b.store)
    with metadata_only(b.store, monkeypatch):
        admitted = b.workflow.receive_form(b.root.source, form, schema, 0)
        assert set(admitted) == {b.source, b.selected}
        assert set(b.receipts.known(b.context.episode_id)) & {
            b.source, b.bundle, b.selected, b.unrequested} == {b.source, b.selected}
        assert b.access(b.source, 'source') is True
        assert b.access(b.selected) is True
        b.assert_resolution(b.source, True, 'source')
        b.assert_resolution(b.selected, True)
        for reference in (b.bundle, b.unrequested):
            assert b.access(reference) is False
            b.assert_resolution(reference, False)
        before = receipt_rows(b.store)
        assert b.workflow.receive_form(b.root.source, form, schema, 0) == admitted
        assert receipt_rows(b.store) == before
        assert retained_metadata(b.store) == retained
        assert not b.store.db.execute('SELECT 1 FROM runtime_observations').fetchone()


def test_unrequested_results_reference_does_not_reopen_original_bundle(boundary, monkeypatch):
    """Deny unselected bytes before entering unrelated saved-result validation.

    The target and capture replay ports are explicit metadata fixtures. This
    preserves the real helper -> own-body -> validation path to its first byte
    read; it does not claim a valid native bundle or production capture. No
    artifact contents are necessary to deny an absent explicit reference.
    """
    from gene_annotation_episode import native_infernal_preparation_results as result_module

    b = boundary
    owner, results = b.bound, b.bound.native_infernal_preparation_results
    selector = {'version': 'native_infernal_preparation_result_selector_v1',
        'acquisition': 'complete_bound_bundle', 'projection': None,
        'artifacts': [{'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}]}
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': b.source, 'selector': selector}
    target = {'resource_kind': 'local', 'resource_id': 'synthetic-local',
        'assignment': {'requested_job': {'native_infernal_preparation': {
            'program': 'cmemit', 'mode': 'consensus'}}}}
    path = (*b.context.path, ('results', 'child_1'))
    episode_id = EpisodeRef(RUN_ID, path).episode_id
    request = {'message': {'scope': b.scope, 'episode_assignment': assignment}, 'report_contract': None}
    context = BindingContext(RUN_ID, episode_id, 'results', path, b.scope, assignment, request)
    b.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
        'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    operation_key = f'{RUN_ID}:{episode_id}:0'
    capture = {'bundle_validated': True, 'bundle_artifact_ref': b.bundle}
    body = {'version': result_module.VERSION, 'run_id': RUN_ID, 'episode_id': episode_id,
        'scope': b.scope, 'assignment': assignment, 'operation_key': operation_key,
        'tool_name': 'execution.results.collect', 'arguments': {}, 'target': target,
        'observation': {'state': 'completed', 'returncode': 0}, 'capture': capture,
        'prepared': None, 'source_ref': b.source, 'record_refs': [b.source, b.selected],
        'rows': [], 'artifacts': [], 'population': None, 'failures': [], 'complete': False}
    b.journal.save('runtime_actions', {'episode_id': episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': body['tool_name'], 'arguments': {}}),
        'result': canonical({'status': 'completed', 'record_refs': body['record_refs'], 'result': body}),
        'credit': None})
    directory = results._saved_directory(episode_id, operation_key)
    (directory / 'capture').mkdir(parents=True)
    for name, value in {'receipt.json': body, 'observation.json': body['observation'],
            'intent.json': {key: body[key] for key in (
                'target', 'assignment', 'operation_key', 'tool_name', 'arguments', 'scope')},
            'capture/capture.json': capture}.items():
        (directory / name).write_text(canonical(value) + '\n')

    def supplied_target(reference, scope):
        assert reference == b.source and plain(scope) == b.scope
        return deepcopy(target)

    monkeypatch.setattr(owner.job_progress_provider.targets, 'read_target', supplied_target)
    monkeypatch.setattr(result_module, 'capture_local_bundle', lambda *args, **kwargs: deepcopy(capture))
    before = receipt_rows(b.store)
    with metadata_only(b.store, monkeypatch):
        assert results.retained_reference_access(context, b.unrequested, 'artifact') is False
        assert results.retained_reference_access(context, b.selected, 'artifact') is True
        assert results.retained_reference_access(context, b.source, 'source') is True
        assert results.retained_reference_access(context, b.selected, 'source') is False
        assert receipt_rows(b.store) == before

