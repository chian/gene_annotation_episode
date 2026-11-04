"""Physical receipt/export/owner checks; no model or scientific-score claim."""
from concurrent.futures import ThreadPoolExecutor
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from method_loop.durable import DurableExecutionError, DurableExecutionStore
from gene_annotation_episode import _local_job_worker as worker
from gene_annotation_episode import native_events as events
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode._local_job_worker import atomic_json
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, OUTPUTS, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy


EXIT = {'SERVICE_RESULT': 'success', 'EXIT_CODE': 'exited', 'EXIT_STATUS': '0'}
ENDED = {'at': '2026-10-21T14:00:00+00:00', 'monotonic_ns': 123456789, 'boot_id': 'fixture-boot'}


def binding(tmp_path, *, run='fixture-run', owner='selected-episode', job='fixture-job', registry='fixture-registry', resource='fixture-local'):
    return events.NativeEventBinding(tmp_path/'executions', run_id=run, owner_episode_id=owner,
        job_ref=job, registry_ref=registry, resource_id=resource)


def prepared(tmp_path, bound=None):
    directory = tmp_path/'native'
    directory.mkdir()
    return native.prepare_job([sys.executable, '-c', 'print("tiny")'], cwd=directory,
        policy=LocalJobPolicy(64*1024**2, 4*1024**2), handle_path=directory/'handle.json', native_events=bound)


def receipt(handle):
    events.commit_service_exit_receipt(handle.path, handle.read()['paths']['status'],
        service_exit=EXIT, event_time=lambda: dict(ENDED))
    return Path(handle.read()['paths']['status'])


def test_binding_roundtrip_preserves_original_owner_and_host_local_view(tmp_path):
    original = binding(tmp_path)
    assert events.NativeEventBinding.from_record(original.as_record()) == original
    provider = events.NativeEventProvider(original.execution_directory, run_id=original.run_id, resource_id=original.resource_id)
    assert provider.for_job(owner_episode_id='repair-episode', job_ref=original.job_ref,
        registry_ref=original.registry_ref, original_binding=original) is original
    for changed in ({'run_id': 'foreign'}, {'resource_id': 'foreign'}, {'execution_directory': tmp_path/'foreign'}):
        arguments = dict(execution_directory=provider.execution_directory, run_id=provider.run_id, resource_id=provider.resource_id)
        arguments.update(changed)
        with pytest.raises(ValueError, match='identity_conflict'):
            events.NativeEventProvider(**arguments).for_job(owner_episode_id='repair', job_ref=original.job_ref,
                registry_ref=original.registry_ref, original_binding=original)
    with pytest.raises(ValueError):
        events.NativeEventBinding.from_record({**original.as_record(), 'unexpected': True})
    with pytest.raises(ValueError):
        events.NativeEventProvider(Path('relative'), run_id='run', resource_id='local')


def test_first_exit_receipt_is_immutable_concurrent_and_original_bytes_are_custodied(tmp_path):
    bound = binding(tmp_path)
    handle = prepared(tmp_path, bound)
    target = events.ensure_native_event_target(handle.path)
    assert target == events.ensure_native_event_target(handle.path)
    path = receipt(handle)
    raw = path.read_bytes()
    def must_not_restamp():
        raise AssertionError('replay called event_time')
    def replay(_):
        events.commit_service_exit_receipt(handle.path, path,
            service_exit={**EXIT, 'EXIT_STATUS': '9'}, event_time=must_not_restamp)
        return events.publish_native_events(handle.path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(replay, range(8)))
    assert all(outcome == outcomes[0] for outcome in outcomes)
    assert outcomes[0]['state'] == 'recorded'
    assert path.read_bytes() == raw
    store = DurableExecutionStore(bound.execution_directory)
    saved = store.native_publication(target['handle'], outcomes[0]['record_ref'])
    assert saved['receipt_bytes'] == raw
    assert saved['publication']['occurred_at'] == ENDED['at']
    assert saved['publication']['receipt_sha256'] == hashlib.sha256(raw).hexdigest()
    path.unlink()
    assert store.native_publication(target['handle'], outcomes[0]['record_ref'])['receipt_bytes'] == raw


def test_export_recovery_does_not_report_poll_execute_or_restamp(tmp_path, monkeypatch):
    bound = binding(tmp_path)
    handle = prepared(tmp_path, bound)
    events.ensure_native_event_target(handle.path)
    path = receipt(handle)
    raw = path.read_bytes()
    actual = events.DurableExecutionStore.publish_native_event
    monkeypatch.setattr(events.DurableExecutionStore, 'publish_native_event', lambda *a, **k:
        (_ for _ in ()).throw(DurableExecutionError('storage_failure')))
    unavailable = events.publish_native_events(handle.path)
    assert unavailable['state'] == 'unavailable' and unavailable['code'] == 'native_event_storage_unavailable'
    monkeypatch.setattr(events.DurableExecutionStore, 'publish_native_event', actual)
    for name in ('status', '_properties', 'start_prepared', 'resume_start'):
        monkeypatch.setattr(native, name, lambda *a, **k: (_ for _ in ()).throw(AssertionError('native operation during export')))
    monkeypatch.setattr(worker, 'event_time', lambda: (_ for _ in ()).throw(AssertionError('restamped')))
    monkeypatch.setattr(worker, 'report', lambda *a, **k: (_ for _ in ()).throw(AssertionError('reentered report')))
    exported = events.publish_native_events(handle.path)
    assert exported['state'] == 'recorded'
    assert events.publish_native_events(handle.path) == exported
    assert path.read_bytes() == raw


@pytest.mark.parametrize('failing_exporter', ['statistics', 'events'])
def test_hook_exports_independently_and_keeps_actual_exit(tmp_path, monkeypatch, failing_exporter):
    from gene_annotation_episode import execution_recording
    handle = prepared(tmp_path, binding(tmp_path))
    body = handle.read()
    body['statistics'] = {'fixture': True}
    atomic_json(handle.path, body)
    calls = []
    def exporter(kind):
        def run(_):
            calls.append(kind)
            if kind == failing_exporter:
                raise OSError('fixture exporter unavailable')
        return run
    monkeypatch.setattr(execution_recording, 'publish_native_statistics', exporter('statistics'))
    monkeypatch.setattr(events, 'publish_native_events', exporter('events'))
    monkeypatch.setattr(worker, 'event_time', lambda: dict(ENDED))
    for key, value in EXIT.items():
        monkeypatch.setenv(key, value)
    worker.report(body['paths']['status'], handle.path)
    original = Path(body['paths']['status']).read_bytes()
    monkeypatch.setattr(worker, 'event_time', lambda: (_ for _ in ()).throw(AssertionError('restamped')))
    worker.report(body['paths']['status'], handle.path)
    assert calls == ['statistics', 'events', 'statistics', 'events']
    assert Path(body['paths']['status']).read_bytes() == original
    assert json.loads(original)['EXIT_STATUS'] == '0'


def test_registration_failure_preserves_prepared_reservation_and_blocks_dispatch(tmp_path, monkeypatch):
    handle = prepared(tmp_path, binding(tmp_path))
    initial = handle.path.read_bytes()
    monkeypatch.setattr(events, 'ensure_native_event_target', lambda *_:
        (_ for _ in ()).throw(DurableExecutionError('storage_failure')))
    monkeypatch.setattr(native.subprocess, 'run', lambda *a, **k:
        (_ for _ in ()).throw(AssertionError('dispatch before registration')))
    with pytest.raises(AcquisitionError) as failure:
        native.start_prepared(handle)
    assert failure.value.code == 'native_event_storage_unavailable'
    assert handle.path.read_bytes() == initial
    assert handle.read()['stage'] == 'prepared'
    assert not Path(handle.read()['paths']['release']).exists()


def test_hook_argument_is_present_for_events_only_and_unbound_shape_is_unchanged(tmp_path, monkeypatch):
    handle = prepared(tmp_path, binding(tmp_path))
    dispatched = []
    def dispatch(argv, **kwargs):
        dispatched.append(argv)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(native.subprocess, 'run', dispatch)
    monkeypatch.setattr(native, 'resume_start', lambda *a, **k: handle)
    native.start_prepared(handle)
    hook = next(value for value in dispatched[0] if value.startswith('ExecStopPost='))
    assert str(handle.path) in hook
    assert events.ensure_native_event_target(handle.path)['handle'].startswith('native_event_target_')
    other = tmp_path/'unbound'
    other.mkdir()
    unbound = native.prepare_job([sys.executable, '-c', 'pass'], cwd=other,
        policy=LocalJobPolicy(64*1024**2, 4*1024**2), handle_path=other/'handle.json')
    assert 'native_events' not in unbound.read() and 'native_events' not in unbound.read()['paths']
    assert events.ensure_native_event_target(unbound.path) is None
    assert events.publish_native_events(unbound.path) == events.disposition('not_configured')
    monkeypatch.setattr(worker, 'event_time', lambda: dict(ENDED))
    worker.report(unbound.read()['paths']['status'])
    assert set(json.loads(Path(unbound.read()['paths']['status']).read_bytes())) == {*EXIT, 'ended'}


def jobs(tmp_path):
    database = tmp_path/'references.faa'
    database.write_text('>reference\nMAAA\n')
    program = Path(sys.executable).resolve()
    return HomologyJobs.create(tmp_path/'jobs', executable=FileAsset(program, digest(program)),
        reference_database=FileAsset(database, digest(database)), policy=LocalJobPolicy(64*1024**2, 4*1024**2), max_cpu=1)


def reserve(service, job, bound):
    service.stage(job)
    directory = service._directory(job)
    return native.prepare_job(service._command(service._row(job)), cwd=directory,
        policy=LocalJobPolicy(**service.config['job_limits']), handle_path=directory/'native.handle.json',
        stdout_path=directory/OUTPUTS['native_text'], stderr_path=directory/OUTPUTS['native_stderr'], native_events=bound)


def test_registry_reads_are_side_effect_free_and_recovery_filters_actual_run_directory_resource(tmp_path):
    service = jobs(tmp_path)
    provider = events.NativeEventProvider(tmp_path/'executions', run_id='ours', resource_id='our-local')
    try:
        handles = []
        for index, delta in enumerate(({}, {'run_id': 'foreign'}, {'resource_id': 'foreign'},
                                       {'execution_directory': tmp_path/'foreign-executions'})):
            job = service.order(query_ref='query', query_fasta='>q\nMAAA\n', cpu=1, operation_key=str(index))
            arguments = dict(execution_directory=provider.execution_directory, run_id=provider.run_id,
                resource_id=provider.resource_id, owner_episode_id='original-owner', job_ref=job,
                registry_ref=service.config['registry_ref'])
            arguments.update(delta)
            bound = events.NativeEventBinding(**arguments)
            handle = reserve(service, job, bound)
            receipt(handle)
            handles.append(handle)
            assert service.native_event_targets(job) == []
        assert not provider.execution_directory.exists()
        assert len(list(service.recover_native_events(native_event_provider=provider))) == 1
        assert service.native_event_targets(handles[0].read()['native_events']['job_ref'])
        for handle in handles[1:]:
            assert not Path(handle.read()['paths']['native_events']).exists()
        assert not (tmp_path/'foreign-executions').exists()
        original = service.native_event_binding(handles[0].read()['native_events']['job_ref'])
        assert provider.for_job(owner_episode_id='repair', job_ref=original.job_ref,
            registry_ref=original.registry_ref, original_binding=original).owner_episode_id == 'original-owner'
    finally:
        service.close()


def test_selected_failure_keeps_registered_target_and_clone_does_not_mutate_caller(tmp_path, monkeypatch):
    service = jobs(tmp_path)
    original = HomologyEpisodes(service, parser_policy=LocalJobPolicy(64*1024**2, 4*1024**2),
        credit_projector=lambda *a, **k: 0, credit_binding={'fixture': 1},
        monitoring_projector=lambda *a, **k: 0, monitoring_binding={'fixture': 1})
    before = original.as_record()
    provider = events.NativeEventProvider(tmp_path/'executions', run_id='ours', resource_id='local')
    view = original.with_native_events(provider)
    assert view is not original and original.native_event_provider is None
    assert original.as_record() == view.as_record() == before
    try:
        job = service.order(query_ref='query', query_fasta='>q\nMAAA\n', cpu=1, operation_key='selected')
        service.stage(job)
        source = SimpleNamespace(episode_id='actual-selecting-episode', path=(('job_launch', 'fixture'),),
            workflow=SimpleNamespace(run_id='ours'), request=SimpleNamespace(message=SimpleNamespace(
                as_record=lambda: {'job_assignment': {'job_ref': job, 'query_ref': 'query', 'cpu': 1}})))
        def interrupted(handle):
            events.ensure_native_event_target(handle.path)
            raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight')
        monkeypatch.setattr('gene_annotation_episode.homology_jobs.start_prepared', interrupted)
        outcome = asyncio.run(view.execute(source, 'homology.submit', {}, operation_key='irrelevant:any:owner'))
        assert outcome['status'] == 'failed' and len(outcome['native_event_targets']) == 1
        assert service.native_event_binding(job).owner_episode_id == source.episode_id
        original_binding = service.native_event_binding(job)
        source.episode_id = 'repair-episode'
        outcome = asyncio.run(view.execute(source, 'homology.resume_start', {}, operation_key='repair'))
        assert outcome['status'] == 'failed' and len(outcome['native_event_targets']) == 1
        assert service.native_event_binding(job) == original_binding
        altered = provider.for_job(owner_episode_id='different-owner', job_ref=job, registry_ref=service.config['registry_ref'])
        with pytest.raises(ValueError, match='immutable'):
            service.submit(job, native_events=altered)
    finally:
        service.close()


def test_invalid_receipt_and_changed_native_request_remain_specific_failures(tmp_path):
    handle = prepared(tmp_path, binding(tmp_path))
    target = events.ensure_native_event_target(handle.path)
    path = receipt(handle)
    original = path.read_bytes()
    body = json.loads(original)
    body['native_identity']['unit'] = 'foreign.service'
    path.write_text(json.dumps(body))
    failed = events.publish_native_events(handle.path)
    assert failed == events.disposition('unavailable', code='native_event_receipt_invalid', target_handle=target['handle'])
    path.write_bytes(original)
    recorded = events.publish_native_events(handle.path)
    assert recorded['state'] == 'recorded'
    body = json.loads(original)
    body['EXIT_STATUS'] = '3'
    path.write_text(json.dumps(body))
    failed = events.publish_native_events(handle.path)
    assert failed['state'] == 'unavailable' and failed['code'] == 'native_event_identity_conflict'
    request = Path(handle.read()['paths']['request'])
    request.write_bytes(request.read_bytes()+b' ')
    failed = events.publish_native_events(handle.path)
    assert failed['state'] == 'unavailable' and failed['code'] == 'native_event_identity_conflict'


@pytest.mark.parametrize('failure,code', [
    (DurableExecutionError('storage_failure'), 'native_event_storage_unavailable'),
    (ValueError('native_event_binding_identity_conflict'), 'native_event_identity_conflict')])
def test_metadata_lookup_failure_is_structured_without_changing_native_outcome(tmp_path, monkeypatch, failure, code):
    service = jobs(tmp_path)
    original = HomologyEpisodes(service, parser_policy=LocalJobPolicy(64*1024**2, 4*1024**2),
        credit_projector=lambda *a, **k: 0, credit_binding={'fixture': 1},
        monitoring_projector=lambda *a, **k: 0, monitoring_binding={'fixture': 1})
    view = original.with_native_events(events.NativeEventProvider(tmp_path/'executions', run_id='ours', resource_id='local'))
    try:
        job = service.order(query_ref='query', query_fasta='>q\nMAAA\n', cpu=1, operation_key='selected')
        source = SimpleNamespace(episode_id='actual-selecting-episode', path=(('job_launch', 'fixture'),),
            workflow=SimpleNamespace(run_id='ours'), request=SimpleNamespace(message=SimpleNamespace(
                as_record=lambda: {'job_assignment': {'job_ref': job, 'query_ref': 'query', 'cpu': 1}})))
        async def outcome(*args, **kwargs):
            return {'status': 'failed', 'result': None, 'feedback': {'code': 'native_outcome_preserved'}}
        monkeypatch.setattr(view, '_execute', outcome)
        monkeypatch.setattr(service, 'native_event_targets', lambda *_: (_ for _ in ()).throw(failure))
        result = asyncio.run(view.execute(source, 'homology.submit', {}, operation_key='selected'))
        assert result['status'] == 'failed' and result['feedback']['code'] == 'native_outcome_preserved'
        assert result['native_event_target_failure'] == {'code': code, 'affected_refs': [job]}
        assert result['native_event_targets'] == []
    finally:
        service.close()


def test_real_tiny_events_only_service_hook_exports_its_first_receipt(tmp_path):
    import time
    bound = binding(tmp_path)
    directory = tmp_path/'real-native'
    directory.mkdir()
    handle = native.NativeJobHandle(directory/'handle.json')
    try:
        native.start_job([sys.executable, '-c', 'print("native event fixture", flush=True)'],
            cwd=directory, policy=LocalJobPolicy(64*1024**2, 4*1024**2),
            handle_path=handle.path, native_events=bound)
        deadline = time.monotonic()+15
        while not native.status(handle)['terminal']:
            assert time.monotonic() < deadline
            time.sleep(.02)
        assert native.collect(handle).returncode == 0
        body = handle.read()
        raw = Path(body['paths']['status']).read_bytes()
        service_exit = json.loads(raw)
        assert service_exit['version'] == 'native_service_exit_receipt_v1'
        assert service_exit['native_identity']['unit'] == body['unit']
        assert Path(body['stdout']).read_text() == 'native event fixture\n'
        exported = json.loads(Path(body['paths']['native_events']).read_text())
        assert exported['state'] == 'recorded'
        store = DurableExecutionStore(bound.execution_directory)
        saved = store.native_publication(exported['target_handle'], exported['record_ref'])
        assert saved['receipt_bytes'] == raw
        assert events.publish_native_events(handle.path) == exported
        assert Path(body['paths']['status']).read_bytes() == raw
        native.release(handle)
        assert store.native_publication(exported['target_handle'], exported['record_ref'])['receipt_bytes'] == raw
    finally:
        if handle.path.exists():
            if not native.status(handle)['quiescent']:
                native.cancel(handle)
            native.release(handle)
