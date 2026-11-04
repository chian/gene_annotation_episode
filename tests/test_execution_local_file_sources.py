"""Real file/Store custody with controlled job-observation port values.

These tests do not claim a native job or full Workflow invocation. They use
saved production episode/action/receipt primitives and actual retained bytes.
The separate native addition case checks scientific model changes and solves.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
from types import MethodType, SimpleNamespace

import pytest

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import (
    ReportBoundaryError, plain, validate_closed_schema, validate_form,
)
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, native_result_operation_catalog
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_contract_information import (
    expand_fact_form, return_contract_information, validate_saved_fact_form,
)
from gene_annotation_episode.local_file_capture_results import (
    LocalFileSourceResults, SELECTOR_VERSION, SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA,
    full_window_key, whole_file_bridge,
)
from gene_annotation_episode.materials import source_for_artifact
from gene_annotation_episode.native_file_capture import NativeFileCaptureError, capture_native_file
from gene_annotation_episode.runtime import Record
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_custody import SavedRecords


class CaptureFixture:
    def __init__(self, store, directory, *, files=1, receive_handoff=True,
                 schema=None, scientific_parent=False, parent_schema=None, saved=None):
        self.saved = SavedRecords(store) if saved is None else saved
        assert self.saved.store is store
        self.store = store
        self.workspace = directory / 'workspace'
        self.workspace.mkdir()
        self.paths = [self.workspace / f'control-{i}.json' for i in range(files)]
        self.originals = [canonical({'control': i, 'value': i + 1}).encode() for i in range(files)]
        for path, data in zip(self.paths, self.originals):
            path.write_bytes(data)
        self.handoff = self.saved.source(b'{"qualification":"controlled historical job facts"}')['source_ref']
        if receive_handoff:
            self.saved.own(self.saved.root, self.handoff)
        self.assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': self.handoff,
            'selector': {'version': SELECTOR_VERSION, 'files': [
                {'path': str(path), 'format': 'json_control'} for path in self.paths]}}
        self.parent = (self.saved.child(self.saved.root, 'scientific_process', {}, 1,
            schema=parent_schema or schema) if scientific_parent else self.saved.root)
        self.context = self.saved.child(self.parent, 'results', self.assignment,
            0 if scientific_parent else 1, schema=schema)
        self.target = {'version': 'execution_target_v1', 'handle': self.handoff,
            'run_id': self.saved.run_id, 'resource_id': 'local', 'resource_kind': 'local',
            'execution_id': str(self.workspace / 'controlled-native-handle.json'),
            'request_sha256': '0' * 64, 'origin_episode_id': self.saved.root.episode_id,
            'assignment': {'workspace': str(self.workspace), 'requested_job': {
                'argv': ['controlled-job-observation-port'], 'environment': {}}},
            'scope': deepcopy(self.saved.scope)}
        self.observation = {'observed_at': '2026-10-29T00:00:00Z', 'state': 'completed', 'returncode': 0,
            'native': {'terminal': True, 'quiescent': True}}
        self.observations = 0

        def read_target(reference, scope):
            assert reference == self.handoff
            store.validate_scope(self.target['scope'], parent_scope=plain(scope))
            return deepcopy(self.target)

        def observe_target(target, *, operation_key):
            assert target == self.target
            self.observations += 1
            return deepcopy(self.observation)

        self.owner = SimpleNamespace(store=store, run_id=self.saved.run_id,
            directory=directory / 'run', resources={'local': {
                'kind': 'local', 'workspace': str(self.workspace)}},
            job_progress_provider=SimpleNamespace(targets=SimpleNamespace(
                read_target=read_target, observe_target=observe_target)))
        self.owner._selection = lambda context: {
            'known_record_refs': list(self.saved.receipts.known(context.episode_id)),
            'initial_known_record_refs': list(self.saved.receipts.known(context.episode_id, baseline=True))}
        self.owner._target = lambda context: read_target(plain(context.assignment)['handoff_ref'], context.scope)
        self.owner._result_directory = MethodType(ExecutionEpisodes._result_directory, self.owner)
        self.owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, self.owner)
        self.backend = LocalFileSourceResults(self.owner)
        self.owner.local_file_sources = self.backend
        self.outcomes = []

    def select(self, index, tool='execution.results.collect'):
        self.saved.journal.save('runtime_actions', {'episode_id': self.context.episode_id,
            'decision_index': index, 'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': {}}),
            'result': None, 'credit': None})
        return f'{self.saved.run_id}:{self.context.episode_id}:{index}'

    def execute(self, index, tool='execution.results.collect', *, selected=False):
        key = f'{self.saved.run_id}:{self.context.episode_id}:{index}' if selected else self.select(index, tool)
        outcome = asyncio.run(self.backend.execute(self.context, self.target, tool, {}, key))
        row = self.saved.journal.row('runtime_actions', self.context.episode_id, index)
        self.saved.journal.save('runtime_actions', {**row, 'result': canonical(outcome)})
        self.saved.receipts.receive(self.context.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
        self.outcomes.append(outcome)
        return outcome

    def results(self):
        return {outcome['record_refs'][0]: self.private(outcome) for outcome in self.outcomes}

    def private(self, outcome):
        return self.backend.read_wrapper(outcome['record_refs'][0], self.context.scope)

    def selection(self):
        return self.owner._selection(self.context)


@pytest.fixture
def captured(tmp_path):
    with Store(tmp_path / 'state') as store:
        yield CaptureFixture(store, tmp_path)


def test_complete_raw_source_preserves_bytes_and_typed_receiver(captured):
    outcome = captured.execute(0)
    wrapper, source_ref = outcome['record_refs']
    source = captured.store.get(source_ref)
    assert captured.store.get_artifact(source['artifact_ref']) == captured.originals[0]
    assert source['origin'] == 'tool' and source['provider'] == 'episode.execution_file'
    assert source['parent_source_refs'] == [captured.handoff]
    assert captured.backend.read_wrapper(wrapper, captured.context.scope)['windows'] == []
    row = captured.backend.read_source(source_ref, captured.context.scope, verify_artifact=True)
    assert row['origin']['writer_closure'] == 'not_established'
    assert row['origin']['attempt_output_version'] == 'unverified'
    assert captured.backend.complete(captured.context, [captured.private(outcome)])
    assert outcome['result']['files'] == [{'path': str(captured.paths[0]), 'format': 'json_control',
        'source_ref': source_ref, 'availability': 'retained', 'size_bytes': len(captured.originals[0]), 'failure': None}]
    assert set(outcome['result']) == {'version', 'operation', 'job', 'files', 'provenance', 'failure'}
    assert captured.paths[0].read_bytes() == captured.originals[0]
    captured.saved.admit(captured.saved.root, captured.context, source_ref)
    assert source_ref in captured.saved.receipts.known(captured.saved.root.episode_id)
    assert captured.saved.custody.possession(captured.saved.root, source_ref) == 'admitted_return'
    assert captured.store.count('observation') == captured.store.count('assessment') == captured.store.count('annotation') == 0


def test_replay_uses_retained_source_after_producer_disappears(captured):
    original = captured.execute(0)
    captured.paths[0].unlink()
    repeated = captured.execute(0, selected=True)
    assert repeated == original and captured.observations == 1
    assert captured.store.get_artifact(captured.store.get(repeated['record_refs'][1])['artifact_ref']) == captured.originals[0]
    assert captured.backend.acquisition_counts(captured.context, captured.selection(), captured.results()) == (0, 1)


def test_independent_file_commit_survives_sibling_storage_failure(tmp_path, monkeypatch):
    from gene_annotation_episode import local_file_capture_results as module
    with Store(tmp_path / 'state') as store:
        case = CaptureFixture(store, tmp_path, files=2)
        actual = module.capture_native_file
        def fail_second(*args, **kwargs):
            if kwargs['relative_path'] == case.paths[1].name:
                raise OSError('controlled retained-storage failure')
            return actual(*args, **kwargs)
        monkeypatch.setattr(module, 'capture_native_file', fail_second)
        key = case.select(0)
        with pytest.raises(OSError, match='retained-storage'):
            asyncio.run(case.backend.execute(case.context, case.target, 'execution.results.collect', {}, key))
        with sqlite3.connect(store.path / 'state.sqlite3') as independent:
            rows = independent.execute('SELECT source_ref FROM runtime_execution_file_captures').fetchall()
        assert len(rows) == 1 and rows[0][0] is not None
        first_source = rows[0][0]
        outside = tmp_path / 'outside-control'
        outside.write_bytes(b'replaced producer after committed sibling')
        case.paths[0].unlink()
        case.paths[0].symlink_to(outside)
        monkeypatch.setattr(module, 'capture_native_file', actual)
        outcome = case.execute(0, selected=True)
        assert outcome['record_refs'][1] == first_source and case.observations == 1
        assert store.get_artifact(store.get(first_source)['artifact_ref']) == case.originals[0]
        assert store.get_artifact(store.get(outcome['record_refs'][2])['artifact_ref']) == case.originals[1]
        assert case.backend.acquisition_counts(case.context, case.selection(), case.results()) == (0, 2)


def test_missing_file_retains_success_and_new_selected_retry(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = CaptureFixture(store, tmp_path, files=2)
        case.paths[1].unlink()
        partial = case.execute(0)
        assert len(partial['record_refs']) == 2
        assert case.private(partial)['captured_files'][1]['failure'] == {'code': 'capture_file_unavailable'}
        assert partial['result']['files'][1]['availability'] == 'unavailable'
        assert partial['result']['files'][1]['size_bytes'] is None
        assert not case.backend.complete(case.context, [case.private(partial)])
        case.paths[1].write_bytes(case.originals[1])
        assert case.execute(0, selected=True) == partial
        finished = case.execute(1)
        assert case.backend.complete(case.context, [case.private(partial), case.private(finished)])
        assert case.backend.acquisition_counts(case.context, case.selection(), case.results()) == (0, 2)


def test_repeated_source_ids_inherited_baseline_and_actual_changed_content(captured):
    first = captured.execute(0)
    second = captured.execute(1)
    assert first['record_refs'][1] != second['record_refs'][1]
    assert captured.backend.acquisition_counts(captured.context, captured.selection(), captured.results()) == (0, 1)
    baseline = captured.selection()
    baseline['initial_known_record_refs'] = list(baseline['known_record_refs'])
    assert captured.backend.acquisition_counts(captured.context, baseline, captured.results()) == (0, 0)
    captured.paths[0].write_bytes(b'{"control":0,"value":19}')
    captured.execute(2)
    current = captured.selection()
    current['initial_known_record_refs'] = baseline['known_record_refs']
    assert captured.backend.acquisition_counts(captured.context, current, captured.results()) == (0, 1)


@pytest.mark.parametrize('capture_first', [True, False])
def test_capture_and_legacy_complete_window_share_one_acquisition(captured, capture_first, monkeypatch):
    outcome = captured.execute(0)
    raw = captured.originals[0]
    window = {'path': str(captured.paths[0]), 'offset': 0, 'returned_bytes': len(raw),
        'size_bytes': len(raw), 'bytes_base64': base64.b64encode(raw).decode('ascii')}
    legacy_ref = captured.saved.source(canonical(window).encode())['source_ref']
    legacy = {'target': captured.target, 'windows': [window]}
    assert full_window_key(captured.target, window) == captured.backend.source_key(outcome['record_refs'][1], captured.context.scope)
    refs = [*outcome['record_refs'], legacy_ref] if capture_first else [legacy_ref, *outcome['record_refs']]
    selection = {'known_record_refs': [captured.handoff, *refs], 'initial_known_record_refs': [captured.handoff]}
    results = {**captured.results(), legacy_ref: legacy}
    # Credit reads use frozen bridge metadata, never original/model bytes.
    monkeypatch.setattr('gene_annotation_episode.local_file_capture_results.retained_native_file',
        lambda *_args, **_kwargs: pytest.fail('credit reopened a full retained file'))
    assert captured.backend.acquisition_counts(captured.context, selection, results) == (
        (0, 1) if capture_first else (1, 0))
    selection['initial_known_record_refs'] = [captured.handoff, refs[0]]
    if capture_first:
        selection['initial_known_record_refs'].append(outcome['record_refs'][1])
    assert captured.backend.acquisition_counts(captured.context, selection, results) == (0, 0)


@pytest.mark.parametrize('size', [0, 1, 2, 3, 786431, 786432, 786433])
def test_streaming_bridge_matches_exact_existing_window_digest(tmp_path, size):
    with Store(tmp_path / 'state') as store:
        raw = (bytes(range(251)) * ((size + 250) // 251))[:size]
        path = tmp_path / 'binary-control'
        path.write_bytes(raw)
        file = capture_native_file(store, directory=str(tmp_path), relative_path=path.name, format='binary_control')
        expected = hashlib.sha256(canonical(base64.b64encode(raw).decode('ascii')).encode()).hexdigest()
        assert whole_file_bridge(store, file) == {'offset': 0, 'returned_bytes': size,
            'size_bytes': size, 'bytes_base64_sha256': expected}


def test_active_or_nonquiescent_job_cannot_publish_complete_file(captured):
    captured.observation['native']['quiescent'] = False
    outcome = captured.execute(0)
    assert len(outcome['record_refs']) == 1 and captured.private(outcome)['captured_files'] == []
    assert outcome['result']['files'][0]['availability'] == 'not_acquired'
    assert not captured.backend.complete(captured.context, [captured.private(outcome)])
    assert captured.backend.acquisition_counts(captured.context, captured.selection(), captured.results()) is None


def test_failed_native_status_is_not_rewritten_by_successful_byte_delivery(captured):
    captured.observation.update(state='failed', returncode=9)
    outcome = captured.execute(0)
    assert outcome['result']['job']['returncode'] == 9
    assert captured.backend.complete(captured.context, [captured.private(outcome)])


def test_unreceived_handoff_and_outside_workspace_are_denied(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = CaptureFixture(store, tmp_path, receive_handoff=False)
        with pytest.raises(ValueError, match='handoff_not_received'):
            case.execute(0)
        outside = deepcopy(case.assignment)
        outside['selector']['files'][0]['path'] = str(tmp_path / 'outside')
        with pytest.raises(ValueError, match='outside_workspace'):
            case.backend.selector(outside, case.target)


def test_new_source_wrapper_cannot_forge_a_capture_receipt(captured):
    outcome = captured.execute(0)
    source = captured.store.get(outcome['record_refs'][1])
    forged = source_for_artifact(captured.store, source['artifact_ref'], provider='episode.execution_file',
        request={'version': 'execution_file_capture_v1'}, parent_source_refs=[captured.handoff])
    with pytest.raises(ValueError, match='source_receipt_missing'):
        captured.backend.read_source(forged['id'], captured.context.scope)


def test_rejected_intent_does_not_bypass_later_first_admission(captured):
    outside = captured.workspace.parent / 'outside-control'
    outside.write_bytes(b'outside access')
    captured.paths[0].unlink()
    captured.paths[0].symlink_to(outside)
    key = captured.select(0)
    with pytest.raises(ValueError, match='outside_workspace'):
        asyncio.run(captured.backend.execute(captured.context, captured.target,
            'execution.results.collect', {}, key))
    assert captured.store.db.execute('SELECT count(*) FROM runtime_execution_file_capture_admissions').fetchone()[0] == 0
    assert captured.observations == 0
    captured.paths[0].unlink()
    captured.paths[0].write_bytes(captured.originals[0])
    outcome = captured.execute(0, selected=True)
    assert captured.store.get_artifact(captured.store.get(outcome['record_refs'][1])['artifact_ref']) == captured.originals[0]
    assert captured.observations == 1


@pytest.mark.parametrize('change', ['null', 'scalar', 'list', 'body', 'numeric_type',
    'refs', 'changed_refs', 'extra', 'pending'])
def test_committed_public_capture_outcome_must_match_private_journal(captured, change):
    original = captured.execute(0)
    altered = deepcopy(original)
    if change == 'null':
        altered = None
    elif change == 'scalar':
        altered = 4
    elif change == 'list':
        altered = []
    elif change == 'body':
        altered['result']['failure'] = {'code': 'replaced'}
    elif change == 'numeric_type':
        altered['result']['job']['returncode'] = False
    elif change == 'refs':
        altered['record_refs'] = [original['record_refs'][0]]
    elif change == 'changed_refs':
        altered['changed_record_refs'] = []
    elif change == 'extra':
        altered['invented_grant'] = original['record_refs'][1]
    else:
        altered['pending_work_after_action'] = {'version': 'invalid', 'captured_at': 'invalid', 'items': []}
    row = captured.saved.journal.row('runtime_actions', captured.context.episode_id, 0)
    captured.saved.journal.save('runtime_actions', {**row, 'result': canonical(altered)})
    with pytest.raises(ValueError):
        captured.backend.read_source(original['record_refs'][1], captured.context.scope)
    with pytest.raises(ValueError):
        captured.backend.read_wrapper(original['record_refs'][0], captured.context.scope)


def test_runtime_pending_metadata_is_validated_without_relaxing_public_body(captured):
    from gene_annotation_episode.waiting import PENDING_VERSION
    original = captured.execute(0)
    public = deepcopy(original)
    public['pending_work_after_action'] = {'version': PENDING_VERSION,
        'captured_at': '2026-10-29T00:00:00Z', 'items': []}
    row = captured.saved.journal.row('runtime_actions', captured.context.episode_id, 0)
    captured.saved.journal.save('runtime_actions', {**row, 'result': canonical(public)})
    assert captured.backend.read_source(original['record_refs'][1], captured.context.scope)['source_ref'] == original['record_refs'][1]


@pytest.mark.parametrize('change', ['source', 'bridge', 'failure'])
def test_unavailable_file_has_no_source_or_bridge_grant(captured, change):
    captured.paths[0].unlink()
    original = captured.execute(0)
    value = deepcopy(captured.private(original)['captured_files'][0])
    # Exercise the closed per-file relationship in a legitimately staged
    # result-NULL state, before a final public outcome owns its exact body.
    row = captured.saved.journal.row('runtime_actions', captured.context.episode_id, 0)
    captured.saved.journal.save('runtime_actions', {**row, 'result': None})
    if change == 'source':
        value['source_ref'] = captured.handoff
    elif change == 'bridge':
        value['whole_file_bridge'] = {'bytes_base64_sha256': '0' * 64}
    else:
        value['failure'] = None
    captured.store.db.execute('UPDATE runtime_execution_file_captures SET receipt=?', (canonical(value),))
    with pytest.raises(ValueError, match='unavailable_file_relationship'):
        captured.backend._validate_file(value, captured.context.scope)


@pytest.mark.parametrize('change', ['format', 'digest_type', 'digest_shape', 'failure'])
def test_successful_file_format_bridge_and_failure_relationships(captured, change):
    original = captured.execute(0)
    value = deepcopy(captured.private(original)['captured_files'][0])
    row = captured.saved.journal.row('runtime_actions', captured.context.episode_id, 0)
    captured.saved.journal.save('runtime_actions', {**row, 'result': None})
    if change == 'format':
        value['file']['format'] = 'invented_format'
    elif change == 'digest_type':
        value['whole_file_bridge']['bytes_base64_sha256'] = 3
    elif change == 'digest_shape':
        value['whole_file_bridge']['bytes_base64_sha256'] = 'bad'
    else:
        value['failure'] = {'code': 'capture_file_unavailable'}
    captured.store.db.execute('UPDATE runtime_execution_file_captures SET receipt=?', (canonical(value),))
    with pytest.raises(ValueError, match='relationship|bridge_metadata'):
        captured.backend._validate_file(value, captured.context.scope)


def test_competing_resume_commits_between_optimistic_read_and_write_lock(captured, monkeypatch):
    # Force precisely the adversarial interleaving without timing assumptions:
    # a second authentic backend commits after the first sees no file row.
    competitor = LocalFileSourceResults(captured.owner)
    original_read = captured.backend._saved
    committed = []
    def stale_read(context, key, path):
        previous = original_read(context, key, path)
        if previous is None and not committed:
            admission = competitor._admission(context, captured.target, key)
            observation_path = competitor._paths(context, key)[1]
            observation = json.loads(observation_path.read_bytes())
            committed.append(competitor._capture(context, captured.target,
                plain(context.assignment)['selector']['files'][0], key, observation, admission))
            captured.paths[0].write_bytes(b'producer changed after competing committed capture')
        return previous
    monkeypatch.setattr(captured.backend, '_saved', stale_read)
    outcome = captured.execute(0)
    assert outcome['record_refs'][1] == committed[0]['source_ref']
    assert captured.store.db.execute('SELECT count(*) FROM runtime_execution_file_captures').fetchone()[0] == 1
    assert captured.store.get_artifact(captured.store.get(outcome['record_refs'][1])['artifact_ref']) == captured.originals[0]
    assert captured.backend.acquisition_counts(captured.context, captured.selection(), captured.results()) == (0, 1)


@pytest.mark.parametrize('code', ['retained_artifact_unavailable', 'retained_artifact_mismatch'])
def test_actual_storage_error_crosses_outer_dispatch_and_keeps_same_action_recoverable(tmp_path, monkeypatch, code):
    from gene_annotation_episode import local_file_capture_results as module
    with Store(tmp_path / 'state') as store:
        case = CaptureFixture(store, tmp_path, files=2)
        # Use the existing real generic operation schema. These controlled-port
        # tests do not claim the pending capture-specific public registration.
        case.owner.catalog = lambda _context: native_result_operation_catalog()
        actual = module.capture_native_file
        interrupted = []
        def storage_failure(*args, **kwargs):
            if kwargs['relative_path'] == case.paths[1].name:
                try:
                    raise OSError('controlled retained storage interruption')
                except OSError as cause:
                    error = NativeFileCaptureError(code)
                    interrupted.append(error)
                    raise error from cause
            return actual(*args, **kwargs)
        monkeypatch.setattr(module, 'capture_native_file', storage_failure)
        key = case.select(0)
        with pytest.raises(NativeFileCaptureError) as failure:
            asyncio.run(ExecutionEpisodes.execute(case.owner, case.context,
                'execution.results.collect', {}, key))
        assert failure.value is interrupted[0] and failure.value.code == code
        assert isinstance(failure.value.__cause__, OSError)
        assert case.saved.journal.row('runtime_actions', case.context.episode_id, 0)['result'] is None
        first = store.db.execute('SELECT receipt FROM runtime_execution_file_captures').fetchone()[0]
        admission = store.db.execute('SELECT admission FROM runtime_execution_file_capture_admissions').fetchone()[0]
        first_source = json.loads(first)['source_ref']
        outside = tmp_path / 'outside-after-commit'
        outside.write_bytes(b'changed producer after retained-storage failure')
        case.paths[0].unlink()
        case.paths[0].symlink_to(outside)
        monkeypatch.setattr(module, 'capture_native_file', actual)
        resumed = asyncio.run(ExecutionEpisodes.execute(case.owner, case.context,
            'execution.results.collect', {}, key))
        assert resumed['status'] == 'completed' and resumed['record_refs'][1] == first_source
        row = case.saved.journal.row('runtime_actions', case.context.episode_id, 0)
        case.saved.journal.save('runtime_actions', {**row, 'result': canonical(resumed)})
        case.saved.receipts.receive(case.context.episode_id, resumed['record_refs'], kind='own_action', source_index=0)
        case.outcomes.append(resumed)
        assert store.db.execute('SELECT admission FROM runtime_execution_file_capture_admissions').fetchone()[0] == admission
        assert store.db.execute('SELECT receipt FROM runtime_execution_file_captures WHERE source_ref=?', (first_source,)).fetchone()[0] == first
        assert store.get_artifact(store.get(first_source)['artifact_ref']) == case.originals[0]
        assert store.get_artifact(store.get(resumed['record_refs'][2])['artifact_ref']) == case.originals[1]
        assert case.observations == 1
        assert case.backend.acquisition_counts(case.context, case.selection(), case.results()) == (0, 2)
        repeated = asyncio.run(ExecutionEpisodes.execute(case.owner, case.context,
            'execution.results.collect', {}, key))
        assert repeated == resumed and case.observations == 1


def _custody_form(*, outcomes=False):
    fields = {'files': deepcopy(SOURCE_REFS_SCHEMA)}
    if outcomes:
        fields['outcomes'] = deepcopy(OUTCOMES_SCHEMA)
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def _registered_capture_owner(store, directory):
    workspace = directory / 'registry-workspace'
    workspace.mkdir()
    return ExecutionEpisodes(None, store=store, directory=directory / 'registered-run',
        run_id='controlled-capture-registry', resources={'local': {'kind': 'local',
            'workspace': str(workspace), 'policy': {'memory_bytes': 21474836480,
                'scratch_bytes': 4294967296, 'wall_seconds': None}}},
        initial_information={}, tool_registry=None, handoff_unit=1,
        acquired_record_unit=1, log_window_bytes=128, log_roles=('stdout', 'stderr'))


def _registered_custody_form(owner, role, *, outcomes=False):
    sources = (owner.fact_sources(role) if role == 'results'
        else owner.received_report_sources(role))
    fields = {'files': {'$ref': 'episode-fact:execution_file_source_refs'}}
    if outcomes:
        fields['outcomes'] = {'$ref': 'episode-fact:execution_file_capture_outcomes'}
    submitted = canonical({'type': 'object', 'properties': fields,
        'required': list(fields), 'additionalProperties': False})
    expanded = expand_fact_form(submitted, child_role=role,
        facts_by_role={role: sources}, permitted_child_roles=[role])
    return validate_saved_fact_form(child_role=role, submitted_schema_json=submitted,
        expanded_schema=expanded['expanded_schema'], declaration=expanded['declaration'])


def test_registered_capture_facts_are_exact_detached_and_role_scoped(tmp_path):
    with Store(tmp_path / 'state') as store:
        owner = _registered_capture_owner(store, tmp_path)
        registered = owner.fact_sources('results')
        schemas = {'execution_file_source_refs': SOURCE_REFS_SCHEMA,
            'execution_file_capture_outcomes': OUTCOMES_SCHEMA}
        for source, schema in schemas.items():
            assert registered[source]['type'] == 'array'
            information = return_contract_information(facts_by_role={'results': registered},
                permitted_child_roles=['results'], role='results', source=source)
            assert information['status'] == 'completed'
            assert information['record_refs'] == information['changed_record_refs'] == []
            assert information['result']['report_schema'] == schema
            for role in ('annotation', 'scientific_process'):
                assert owner.received_report_sources(role)[source] == registered[source]
            for role in ('launch', 'launch_local', 'launch_hpc', 'launch_api'):
                assert source not in owner.fact_sources(role)
                assert source not in owner.received_report_sources(role)
        registered['execution_file_source_refs']['report_schema']['items']['format'] = 'invalid'
        assert owner.fact_sources('results')['execution_file_source_refs']['report_schema'] == SOURCE_REFS_SCHEMA
        assert store.count('source') == store.count('observation') == 0


def _admit_recorded_custody(case, parent, child, form):
    schema = plain(child.request)['report_contract']['measurements']['schema']
    # Use the real closed-form value and semantic-reference consumer before
    # constructing this controlled historical typed-return attempt.
    form = validate_form(form, schema, lambda reference, namespace:
        namespace == 'source' and case.backend.read_source(reference, parent.scope) is not None)
    facts = {node['x-source']: deepcopy(form[name]) for name, node in schema['properties'].items()}
    case.saved.journal.save('runtime_forms', {'episode_id': child.episode_id,
        'facts': canonical(facts), 'form': canonical(form)})
    index = int(child.path[-1][1][6:])
    case.saved.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
        'decision_index': index, 'delivery_ref': 'controlled-custody-delivery',
        'child_episode_id': child.episode_id, 'contract': canonical(plain(child.request)['report_contract']),
        'form': canonical(form), 'failure': None})
    references = case.backend.admit_return(parent, form, schema,
        f'{parent.run_id}:{parent.episode_id}:{index}:typed_form')
    case.saved.receipts.receive(parent.episode_id, references, kind='child_form', source_index=index)
    return references


@pytest.mark.parametrize('change', ['constant', 'missing_field', 'unrestricted_fact',
    'unknown_source', 'nested_fact', 'generic_freeform'])
def test_capture_outcome_schema_admits_only_complete_top_level_recorded_contract(change):
    original = _custody_form(outcomes=True)
    assert validate_closed_schema(original) == original
    altered = deepcopy(original)
    node = altered['properties']['outcomes']
    if change == 'constant':
        node['items']['properties']['version']['const'] = 'different_outcome_version'
    elif change == 'missing_field':
        del node['items']['properties']['files']
        node['items']['required'].remove('files')
    elif change == 'unrestricted_fact':
        altered['properties']['outcomes'] = {'type': 'array', 'items': {'type': 'string'},
            'x-source': 'execution_file_capture_outcomes'}
    elif change == 'unknown_source':
        node['x-source'] = 'unknown_capture_outcomes'
    elif change == 'nested_fact':
        altered = {'type': 'object', 'properties': {'nested': original},
            'required': ['nested'], 'additionalProperties': False}
    else:
        altered = {'type': 'object', 'properties': {'text': {'type': 'string'}},
            'required': ['text'], 'additionalProperties': False}
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(altered)


@pytest.mark.parametrize('state', ['retained', 'unavailable', 'not_acquired', 'failed_job'])
def test_capture_outcome_values_keep_nullable_facts_and_actual_source_validation(captured, state):
    if state == 'unavailable':
        captured.paths[0].unlink()
    elif state == 'not_acquired':
        captured.observation['native']['quiescent'] = False
    elif state == 'failed_job':
        captured.observation.update(state='failed', returncode=9, failure_code='native_control_failure')
    outcome = captured.execute(0)
    refs = outcome['record_refs'][1:]
    form = {'files': refs, 'outcomes': [outcome['result']]}
    schema = _custody_form(outcomes=True)
    resolve = lambda reference, namespace: namespace == 'source' and captured.backend.read_source(
        reference, captured.context.scope) is not None
    assert validate_form(form, schema, resolve) == form
    malformed = deepcopy(form)
    malformed['outcomes'][0]['job']['returncode'] = False
    with pytest.raises(ReportBoundaryError):
        validate_form(malformed, schema, resolve)
    if refs:
        forged = deepcopy(form)
        forged['outcomes'][0]['files'][0]['source_ref'] = captured.handoff
        with pytest.raises(ReportBoundaryError) as failure:
            validate_form(forged, schema, resolve)
        assert failure.value.diagnostic['code'] == 'unknown_reference'


@pytest.mark.parametrize('forward_outcomes', [False, True])
def test_same_recorded_custody_fact_forwards_both_typed_boundaries(tmp_path, forward_outcomes):
    with Store(tmp_path / 'state') as store:
        owner = _registered_capture_owner(store, tmp_path)
        case = CaptureFixture(store, tmp_path, scientific_parent=True,
            schema=_registered_custody_form(owner, 'results', outcomes=True),
            parent_schema=_registered_custody_form(owner, 'scientific_process', outcomes=forward_outcomes))
        outcome = case.execute(0)
        source_ref = outcome['record_refs'][1]
        actual_outcomes = case.backend.outcomes_for_context(case.context)
        assert actual_outcomes == [outcome['result']]
        child_form = {'files': [source_ref], 'outcomes': actual_outcomes}
        assert _admit_recorded_custody(case, case.parent, case.context, child_form) == [source_ref]
        parent_form = {'files': case.backend.received_sources(case.parent)}
        if forward_outcomes:
            parent_form['outcomes'] = case.backend.received_outcomes(case.parent)
        assert _admit_recorded_custody(case, case.saved.root, case.parent, parent_form) == [source_ref]
        assert case.backend.received_sources(case.saved.root) == [source_ref]
        assert case.backend.received_outcomes(case.saved.root) == (actual_outcomes if forward_outcomes else [])
        assert store.count('observation') == store.count('assessment') == store.count('annotation') == 0


def test_unavailable_file_and_original_job_status_are_automatic_typed_facts(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = CaptureFixture(store, tmp_path, scientific_parent=True,
            schema=_custody_form(outcomes=True))
        case.paths[0].unlink()
        outcome = case.execute(0)
        child_form = {'files': [], 'outcomes': case.backend.outcomes_for_context(case.context)}
        assert child_form['outcomes'][0]['files'][0]['failure'] == {'code': 'capture_file_unavailable'}
        assert child_form['outcomes'][0]['job']['state'] == 'completed'
        assert child_form['outcomes'][0]['job']['returncode'] == 0
        assert _admit_recorded_custody(case, case.parent, case.context, child_form) == []
        parent_form = {'files': case.backend.received_sources(case.parent),
            'outcomes': case.backend.received_outcomes(case.parent)}
        assert _admit_recorded_custody(case, case.saved.root, case.parent, parent_form) == []
        assert case.backend.received_outcomes(case.saved.root) == [outcome['result']]
        assert case.backend.received_sources(case.saved.root) == []
        assert case.backend.acquisition_counts(case.context, case.selection(), case.results()) == (0, 0)


@pytest.mark.parametrize('invalid', ['format', 'path'])
def test_all_capture_declarations_are_validated_before_first_file_commit(tmp_path, invalid):
    with Store(tmp_path / 'state') as store:
        case = CaptureFixture(store, tmp_path, files=2)
        selection = deepcopy(case.assignment)
        if invalid == 'format':
            selection['selector']['files'][1]['format'] = '\n'
        else:
            selection['selector']['files'][1]['path'] = str(case.workspace / 'unsupported\nspelling')
        case.assignment = selection
        case.context = case.saved.child(case.saved.root, 'results', selection, 2)
        case.owner.catalog = lambda _context: native_result_operation_catalog()
        sources_before = store.count('source')
        key = case.select(0)
        outcome = asyncio.run(ExecutionEpisodes.execute(case.owner, case.context,
            'execution.results.collect', {}, key))
        assert outcome['status'] == 'invalid' and outcome['record_refs'] == []
        assert store.db.execute('SELECT count(*) FROM runtime_execution_file_captures').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_execution_file_capture_admissions').fetchone()[0] == 0
        assert case.observations == 0 and store.count('source') == sources_before
        assert case.paths[0].read_bytes() == case.originals[0]


def _registered_capture_dispatch_case(store, directory, *, saved=None, scientific_parent=False,
                                      schema=None, parent_schema=None):
    """Real registered owner/capture reader; only target observation is controlled."""
    case = CaptureFixture(store, directory, saved=saved, scientific_parent=scientific_parent,
        schema=schema, parent_schema=parent_schema)
    targets = case.owner.job_progress_provider
    owner = ExecutionEpisodes(None, store=store, directory=case.owner.directory,
        run_id=case.saved.run_id, resources={'local': {'kind': 'local',
            'workspace': str(case.workspace), 'policy': {'memory_bytes': 21474836480,
                'scratch_bytes': 4294967296, 'wall_seconds': None}}},
        initial_information={}, tool_registry=None, handoff_unit=1,
        acquired_record_unit=1, log_window_bytes=128, log_roles=('stdout', 'stderr'))
    owner.job_progress_provider = targets
    case.owner, case.backend = owner, owner.local_file_sources
    return case


@pytest.mark.parametrize('condition', ['allowed_none', 'allowed_source', 'wrong_namespace',
    'foreign_scope', 'forged_capture', 'missing_source'])
def test_local_file_source_probe_preserves_registered_capture_authority(tmp_path, condition):
    from method_loop.episode import EpisodeGoal
    with Store(tmp_path / 'state') as store:
        if condition == 'foreign_scope':
            manifest = tmp_path / 'scope-targets.json'
            manifest.write_text(canonical({'schema_version': 1, 'entries': [
                {'sequence': 'ACGT', 'molecule': 'dna', 'name': 'capture-A'},
                {'sequence': 'CGTA', 'molecule': 'dna', 'name': 'receiver-B'}]}))
            saved = SavedRecords(store, manifest_path=manifest)
            subject_a, subject_b = store.problem()['subject_refs']
            assert subject_a != subject_b
            assert store.get_artifact(store.get_input(subject_a)['sequence_ref']) == b'ACGT'
            assert store.get_artifact(store.get_input(subject_b)['sequence_ref']) == b'CGTA'
            saved.scope = {'subject_refs': [subject_a]}
            case = _registered_capture_dispatch_case(store, tmp_path, saved=saved)
            assert store.validate_scope(plain(case.saved.root.scope)) == store.validate_scope(
                {'subject_refs': [subject_a, subject_b]})
            assert plain(case.context.scope) == store.validate_scope({'subject_refs': [subject_a]})
        else:
            case = _registered_capture_dispatch_case(store, tmp_path)
        outcome = case.execute(0)
        source_ref = outcome['record_refs'][1]
        context, namespace = case.context, 'source'
        if condition == 'allowed_none':
            namespace = None
        elif condition == 'wrong_namespace':
            namespace = 'bvbrc_data_cell'
        elif condition == 'foreign_scope':
            original = case.saved.scope
            try:
                case.saved.scope = {'subject_refs': [subject_b]}
                context = case.saved.save_context('annotation', (('annotation', 'foreign'),), {},
                    EpisodeGoal.root(objective='Test an unrelated file receiver scope',
                        result_contract={'role': 'annotation'}), None)
            finally:
                case.saved.scope = original
            case.backend.records.authenticate(context)
            assert plain(context.scope) == store.validate_scope({'subject_refs': [subject_b]})
            assert context.episode_id != case.context.episode_id
            with pytest.raises(ValueError, match='scope_outside_parent'):
                case.backend.read_source(source_ref, context.scope)
        elif condition == 'forged_capture':
            source = store.get(source_ref)
            source_ref = source_for_artifact(store, source['artifact_ref'],
                provider='episode.execution_file', request={'version': 'execution_file_capture_v1'},
                parent_source_refs=[case.handoff])['id']
        elif condition == 'missing_source':
            source_ref = 'source_' + '0' * 24
        expected = condition in {'allowed_none', 'allowed_source'}
        assert case.owner.resolve_received_reference(context, source_ref, namespace) is expected
        assert case.observations == 1
        assert store.get_artifact(store.get(outcome['record_refs'][1])['artifact_ref']) == case.originals[0]


@pytest.mark.parametrize('failure', ['other_contract_error', 'invalid_stored_json'])
def test_local_file_source_probe_propagates_unexpected_store_integrity_errors(tmp_path, monkeypatch, failure):
    from gene_annotation_episode.domain import ContractError
    with Store(tmp_path / 'state') as store:
        case = _registered_capture_dispatch_case(store, tmp_path)
        outcome = case.execute(0)
        source_ref = outcome['record_refs'][1]
        error = (ContractError('controlled_record_integrity_conflict')
            if failure == 'other_contract_error' else json.JSONDecodeError('controlled invalid stored JSON', '', 0))
        actual = store.get
        def failed_read(reference):
            if reference == source_ref:
                raise error
            return actual(reference)
        monkeypatch.setattr(store, 'get', failed_read)
        with pytest.raises(type(error)) as caught:
            case.owner.resolve_received_reference(case.context, source_ref, 'source')
        assert caught.value is error
        assert case.observations == 1


def _capture_receiver_context(store, scope, *, run_id, path=(('annotation', 'receiver'),),
                              parent=None, save=True):
    """Engineered receiving request using real journal and inheritance owners."""
    journal = Journal(store, run_id)
    receipts = EpisodeReceipts(store, run_id)
    episode_id = EpisodeRef(run_id, path).episode_id
    manifest = receipts.bind(episode_id, None if parent is None else parent.episode_id)
    objective = 'Check explicitly delivered execution-file references'
    goal = (EpisodeGoal.root(objective=objective, result_contract={'role': path[-1][0]})
        if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']),
            objective=objective, result_contract={'role': path[-1][0]}))
    request = EpisodeRequest(goal, Record({'scope': plain(scope), 'initial_report': {},
        'episode_assignment': {}, 'knowledge_inheritance': manifest}), None).as_record()
    context = BindingContext(run_id, episode_id, path[-1][0], path, scope, {}, request)
    if save:
        journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'active',
            'completion': None, 'archive': None})
    return context, receipts


def test_captured_source_and_file_need_actual_same_scope_receiver_delivery(tmp_path, monkeypatch):
    """Controlled capture/typed boundaries; no native execution is claimed."""
    with Store(tmp_path / 'state') as store:
        case = _registered_capture_dispatch_case(store, tmp_path, scientific_parent=True,
            schema=_custody_form(), parent_schema=_custody_form())
        outcome = case.execute(0)
        source_ref = outcome['record_refs'][1]
        artifact_ref = store.get(source_ref)['artifact_ref']
        assert artifact_ref in case.saved.receipts.known(case.context.episode_id)
        assert source_ref in case.saved.receipts.known(case.context.episode_id)
        for receiver in (case.parent, case.saved.root):
            assert plain(receiver.scope) == plain(case.context.scope)
            assert {source_ref, artifact_ref}.isdisjoint(case.saved.receipts.known(receiver.episode_id))
            # Scientific ownership alone admits both through the generic Store
            # fallback, so the capture receiver boundary must decide first.
            assert set(store.reference_subset([source_ref, artifact_ref], plain(receiver.scope))) == {
                source_ref, artifact_ref}
            assert case.owner.resolve_received_reference(receiver, source_ref, 'source') is False
            assert case.owner.resolve_received_reference(receiver, artifact_ref, 'artifact') is False
        for namespace in (None, 'source'):
            assert case.owner.resolve_received_reference(case.context, source_ref, namespace) is True
        child_form = {'files': [source_ref]}
        assert validate_form(child_form, _custody_form(), lambda ref, namespace:
            case.owner.resolve_received_reference(case.context, ref, namespace)) == child_form
        assert _admit_recorded_custody(case, case.parent, case.context, child_form) == [source_ref]
        assert artifact_ref in case.saved.receipts.known(case.parent.episode_id)
        assert case.owner.resolve_received_reference(case.parent, source_ref, 'source') is True
        known = {context.episode_id: set(case.saved.receipts.known(context.episode_id))
            for context in (case.saved.root, case.parent, case.context)}
        changes = store.db.total_changes
        def forbidden(*_args, **_kwargs):
            pytest.fail('metadata reference admission read bytes, published or reacquired data')
        with monkeypatch.context() as guarded:
            guarded.setattr(store, 'get_artifact', forbidden)
            guarded.setattr(store, 'artifact', forbidden)
            guarded.setattr(store, 'put', forbidden)
            guarded.setattr(case.backend, 'read_source', forbidden)
            guarded.setattr('gene_annotation_episode.local_file_capture_results.read_control', forbidden)
            guarded.setattr('gene_annotation_episode.local_file_capture_results.capture_native_file', forbidden)
            for receiver in (case.context, case.parent):
                for namespace in (None, 'artifact'):
                    assert case.owner.resolve_received_reference(receiver, artifact_ref, namespace) is True
            # The unknown Source is rejected before its private custody reader.
            assert case.owner.resolve_received_reference(case.saved.root, source_ref, 'source') is False
            assert case.owner.resolve_received_reference(case.saved.root, artifact_ref, 'artifact') is False
        assert store.db.total_changes == changes
        assert known == {context.episode_id: set(case.saved.receipts.known(context.episode_id))
            for context in (case.saved.root, case.parent, case.context)}
        assert case.observations == 1


@pytest.mark.parametrize('delivery', ['initial', 'unsaved_initial', 'inherited', 'late_parent',
    'other_run_initial'])
def test_captured_file_metadata_preserves_explicit_initial_and_inherited_grants(tmp_path, monkeypatch, delivery):
    with Store(tmp_path / 'state') as store:
        case = _registered_capture_dispatch_case(store, tmp_path)
        outcome = case.execute(0)
        source_ref = outcome['record_refs'][1]
        artifact_ref = store.get(source_ref)['artifact_ref']
        repeated = case.execute(1)
        assert repeated['record_refs'][1] != source_ref
        assert store.get(repeated['record_refs'][1])['artifact_ref'] == artifact_ref
        run_id = ('independent-file-receiver' if delivery == 'other_run_initial' else case.saved.run_id)
        receiver, receipts = _capture_receiver_context(store, case.context.scope,
            run_id=run_id, save=delivery != 'unsaved_initial')
        if delivery != 'late_parent':
            receipts.receive(receiver.episode_id, [artifact_ref], kind='initial')
        if delivery in {'inherited', 'late_parent'}:
            parent = receiver
            receiver, _ = _capture_receiver_context(store, case.context.scope, run_id=run_id,
                path=(*parent.path, ('results', 'child_0')), parent=parent)
            if delivery == 'late_parent':
                receipts.receive(parent.episode_id, [artifact_ref], kind='own_action', source_index=0)
        expected = delivery != 'late_parent'
        assert (artifact_ref in set(receipts.known(receiver.episode_id))) is expected
        assert source_ref not in receipts.known(receiver.episode_id)
        changes = store.db.total_changes
        def forbidden(*_args, **_kwargs):
            pytest.fail('metadata receiver accessed file/control bytes or created a grant')
        with monkeypatch.context() as guarded:
            guarded.setattr(store, 'get_artifact', forbidden)
            guarded.setattr(store, 'put', forbidden)
            guarded.setattr(case.backend, 'read_source', forbidden)
            assert case.owner.resolve_received_reference(receiver, artifact_ref, 'artifact') is expected
            assert case.owner.resolve_received_reference(receiver, source_ref, 'source') is False
        assert store.db.total_changes == changes
        assert case.observations == 2


@pytest.mark.parametrize('delivery', ['initial', 'inherited'])
def test_captured_source_explicit_and_inherited_receipts_keep_original_custody(tmp_path, delivery):
    with Store(tmp_path / 'state') as store:
        case = _registered_capture_dispatch_case(store, tmp_path)
        outcome = case.execute(0)
        source_ref = outcome['record_refs'][1]
        artifact_ref = store.get(source_ref)['artifact_ref']
        receiver, receipts = _capture_receiver_context(store, case.context.scope,
            run_id='explicit-source-receiver')
        receipts.receive(receiver.episode_id, [source_ref], kind='initial')
        if delivery == 'inherited':
            receiver, _ = _capture_receiver_context(store, case.context.scope,
                run_id=receiver.run_id, path=(*receiver.path, ('results', 'child_0')), parent=receiver)
        assert {source_ref, artifact_ref} <= set(receipts.known(receiver.episode_id))
        changes = store.db.total_changes
        assert case.owner.resolve_received_reference(receiver, source_ref, 'source') is True
        assert case.owner.resolve_received_reference(receiver, artifact_ref, 'artifact') is True
        assert store.db.total_changes == changes
        assert case.observations == 1


@pytest.mark.parametrize('change', ['namespace', 'assignment', 'request', 'run'])
def test_captured_file_receiver_rejects_wrong_namespace_and_forged_context(tmp_path, monkeypatch, change):
    with Store(tmp_path / 'state') as store:
        case = _registered_capture_dispatch_case(store, tmp_path)
        outcome = case.execute(0)
        source_ref = outcome['record_refs'][1]
        artifact_ref = store.get(source_ref)['artifact_ref']
        receiver, namespace = case.context, 'artifact'
        if change == 'namespace':
            namespace = 'source'
        elif change == 'assignment':
            receiver = replace(receiver, assignment={'forged': True})
        elif change == 'request':
            request = plain(receiver.request)
            request['message']['initial_report'] = {'forged': True}
            receiver = replace(receiver, request=request)
        else:
            receiver = replace(receiver, run_id='forged-receiving-run')
        changes = store.db.total_changes
        def forbidden(*_args, **_kwargs):
            pytest.fail('denied receiver reached payload/control bytes')
        with monkeypatch.context() as guarded:
            guarded.setattr(store, 'get_artifact', forbidden)
            guarded.setattr(case.backend, 'read_source', forbidden)
            assert case.owner.resolve_received_reference(receiver, artifact_ref, namespace) is False
            assert case.owner.resolve_received_reference(receiver, source_ref,
                'artifact' if change == 'namespace' else 'source') is False
        assert store.db.total_changes == changes


def test_received_capture_source_still_requires_original_custody_and_unrelated_files_defer(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = _registered_capture_dispatch_case(store, tmp_path)
        outcome = case.execute(0)
        source = store.get(outcome['record_refs'][1])
        forged = source_for_artifact(store, source['artifact_ref'], provider='episode.execution_file',
            request={'version': 'execution_file_capture_v1'}, parent_source_refs=[case.handoff])
        case.saved.receipts.receive(case.context.episode_id, [forged['id']], kind='initial')
        assert case.owner.resolve_received_reference(case.context, forged['id'], 'source') is False
        unrelated = store.artifact(b'independent supplied File', 'application/octet-stream')
        case.saved.receipts.receive(case.saved.root.episode_id, [unrelated], kind='initial')
        assert case.backend.reference_access(case.saved.root, unrelated, 'artifact') is None
        assert unrelated in case.saved.receipts.known(case.saved.root.episode_id)
