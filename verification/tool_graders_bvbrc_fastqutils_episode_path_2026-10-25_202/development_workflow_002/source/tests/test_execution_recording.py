"""Actual small native services export only typed execution statistics.

The short programs are labeled engineering fixtures, not biological evidence.
No scientific Store, model, credit projector or yield history participates.
"""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from gene_annotation_episode.execution_recording import (NativeMeasurement, NativeStatistics,
    publish_native_statistics, recover_native_measurement)
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.native_lifecycle import NativeJobHandle, collect, prepare_job, start_job, start_prepared, status
from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory
from test_native_lifecycle import cleanup, wait_for


POLICY = LocalJobPolicy(64*1024**2, 4*1024**2)
WORK = "import pathlib,time\nwhile not pathlib.Path('finish').exists(): time.sleep(.01)\nprint('private-fixture-output')"
COMMAND = [sys.executable, '-c', WORK]


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def scope():
    return ExecutionClass(phase='protein_homology_search', backend='local', resource_id='fixture-host',
        implementation_sha256=sha('explicit-engineering-program-fixture'), parameters_sha256=sha(WORK),
        memory_bytes=POLICY.memory_bytes, scratch_bytes=POLICY.scratch_bytes, cpu_threads=1,
        query_residues=253, reference_residues=253, reference_records=1, reference_state='available',
        duration_measure='systemd_service_wall_seconds')


def start(directory, context, *, detached_owner=False):
    directory.mkdir()
    handle = NativeJobHandle(directory/'handle.json')
    if detached_owner:
        code = ('from pathlib import Path\n'
            'from gene_annotation_episode.execution_recording import NativeStatistics\n'
            'from gene_annotation_episode.local_jobs import LocalJobPolicy\n'
            'from gene_annotation_episode.native_lifecycle import start_job\n'
            f'start_job({COMMAND!r},cwd=Path({str(directory)!r}),policy=LocalJobPolicy(**{POLICY.to_dict()!r}),'
            f'handle_path=Path({str(handle.path)!r}),statistics=NativeStatistics.from_record({context.as_record()!r}))')
        owner = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=15)
        assert owner.returncode == 0, owner.stderr
    else:
        start_job(COMMAND, cwd=directory, policy=POLICY, handle_path=handle.path, statistics=context)
    return handle


def finish(handle):
    (handle.path.parent/'finish').touch()
    wait_for(lambda: status(handle)['terminal'])
    returned = collect(handle)
    assert returned.returncode == 0 and returned.stdout_path.read_text() == 'private-fixture-output\n'
    return returned


def counts(path):
    with sqlite3.connect(path) as db:
        return db.execute('SELECT count(*) FROM run_statistics').fetchone()[0]


def test_completion_hook_survives_owner_exit_and_shares_exact_class_across_runs(tmp_path):
    path = tmp_path/'global.sqlite'
    history = RunHistory(path)
    first_snapshot = history.capture(scope())
    condition = history.set_condition(operation_sha256=sha('normal'), resource_id='fixture-host',
        state='normal', reason='operator_report', reported_at='2026-10-20T10:00:00Z')
    history.close()
    context = NativeStatistics.capture(path, scope())
    assert context.condition_ref == condition
    first = start(tmp_path/'one', context, detached_owner=True)
    second = None
    try:
        history = RunHistory(path, create=False)
        outage = history.set_condition(operation_sha256=sha('outage'), resource_id='fixture-host',
            state='unavailable', reason='outage', reported_at='2026-10-20T11:00:00Z')
        history.close()
        assert status(first)['state'] == 'running'
        assert counts(path) == 0  # Live observations are not completed run samples.
        returned = finish(first)
        assert returned.metadata['statistics_export']['state'] == 'recorded'
        # No parent process or explicit export call was needed for this record.
        assert counts(path) == 1
        original = returned.metadata['statistics_export']
        for _ in range(2):
            assert publish_native_statistics(first.path) == original
        assert counts(path) == 1
        second = start(tmp_path/'two', NativeStatistics.capture(path, scope()))
        finish(second)
        assert counts(path) == 2
        with sqlite3.connect(path) as db:
            rows = [json.loads(row[0]) for row in db.execute('SELECT data FROM run_statistics ORDER BY sequence')]
            assert rows[0]['condition_ref'] == condition and rows[1]['condition_ref'] == outage
            assert rows[0]['elapsed_seconds'] == returned.metadata['elapsed_seconds']
            assert rows[0]['attempt_sha256'] != rows[1]['attempt_sha256']
            payload = json.dumps([row for row in db.execute('SELECT * FROM execution_classes')]+[
                row for row in db.execute('SELECT * FROM run_statistics')])
            assert 'private-fixture-output' not in payload and str(tmp_path) not in payload
        history = RunHistory(path, create=False)
        reader = history.reader(first_snapshot)
        assert reader.get(first_snapshot)['statistics'] == []
        reader.close(); history.close()
    finally:
        cleanup(first)
        if second is not None:
            cleanup(second)


def test_missing_history_does_not_fail_job_or_gain_a_later_outage_label(tmp_path):
    path = tmp_path/'not-created.sqlite'
    context = NativeStatistics.capture(path, scope())
    assert context.condition_capture == 'unavailable_before_submission'
    assert not path.exists()
    handle = start(tmp_path/'job', context)
    try:
        returned = finish(handle)
        assert returned.metadata['statistics_export']['state'] == 'unavailable'
        assert not path.exists()
        before = Path(handle.read()['paths']['result']).read_bytes()
        history = RunHistory(path)
        history.set_condition(operation_sha256=sha('later-outage'), resource_id='fixture-host',
            state='unavailable', reason='outage', reported_at='2026-10-20T12:00:00Z')
        history.close()
        repaired = publish_native_statistics(handle.path)
        assert repaired['state'] == 'recorded'
        assert repaired['condition_capture'] == 'unavailable_before_submission'
        assert Path(handle.read()['paths']['result']).read_bytes() == before
        with sqlite3.connect(path) as db:
            row = json.loads(db.execute('SELECT data FROM run_statistics').fetchone()[0])
            assert row['condition_ref'] is None and row['outcome'] == 'succeeded'
        assert publish_native_statistics(handle.path) == repaired and counts(path) == 1
    finally:
        cleanup(handle)


def test_busy_history_and_conflicting_receipt_preserve_native_work_and_prior_measurement(tmp_path):
    path = tmp_path/'global.sqlite'
    history = RunHistory(path); history.close()
    context = NativeStatistics.capture(path, scope())
    blocker = sqlite3.connect(path)
    blocker.execute('BEGIN EXCLUSIVE')
    handle = start(tmp_path/'job', context)
    try:
        returned = finish(handle)
        assert returned.metadata['statistics_export']['state'] == 'unavailable'
        assert returned.metadata['service_exit']['SERVICE_RESULT'] == 'success'
        blocker.rollback()
        assert counts(path) == 0
        recorded = publish_native_statistics(handle.path)
        assert recorded['state'] == 'recorded' and counts(path) == 1
        with sqlite3.connect(path) as db:
            original = db.execute('SELECT data FROM run_statistics').fetchone()[0]
        end = Path(handle.read()['paths']['status'])
        actual_bytes = end.read_bytes()
        altered = json.loads(actual_bytes)
        altered['synthetic_corruption_fixture'] = True
        end.write_text(json.dumps(altered))
        try:
            assert publish_native_statistics(handle.path)['code'] == 'statistics_identity_conflict'
            with sqlite3.connect(path) as db:
                assert db.execute('SELECT data FROM run_statistics').fetchone()[0] == original
        finally:
            end.write_bytes(actual_bytes)
        assert publish_native_statistics(handle.path) == recorded
    finally:
        blocker.rollback(); blocker.close(); cleanup(handle)


def test_native_statistics_reject_wrong_representation_or_policy_before_execution(tmp_path):
    path = tmp_path/'global.sqlite'
    history = RunHistory(path); history.close()
    handle = tmp_path/'handle.json'
    with pytest.raises(TypeError, match='typed_native_execution_statistics'):
        start_job(COMMAND, cwd=tmp_path, policy=POLICY, handle_path=handle, statistics={'findings': 'free text'})
    with pytest.raises(ValueError, match='does_not_describe_native_policy'):
        start_job(COMMAND, cwd=tmp_path, policy=POLICY, handle_path=handle,
                  statistics=NativeStatistics.capture(path, replace(scope(), memory_bytes=POLICY.memory_bytes*2)))
    assert not handle.exists() and counts(path) == 0


def test_reserved_job_starts_timing_and_condition_capture_at_actual_dispatch(tmp_path):
    path = tmp_path/'global.sqlite'
    history = RunHistory(path)
    history.set_condition(operation_sha256=sha('before-reservation'), resource_id='fixture-host',
        state='normal', reason='operator_report', reported_at='2026-10-20T10:00:00Z')
    directory = tmp_path/'job'
    directory.mkdir()
    handle = prepare_job(COMMAND, cwd=directory, policy=POLICY, handle_path=directory/'handle.json',
        statistics=NativeStatistics.pending(path, scope()))
    try:
        reserved = handle.read()
        assert reserved['statistics']['condition_capture'] == 'not_started'
        assert reserved['started_monotonic_ns'] is reserved['boot_id'] is None
        assert status(handle)['state'] == 'prepared' and status(handle)['metadata']['elapsed_seconds'] is None
        assert publish_native_statistics(handle.path)['state'] == 'pending'
        assert counts(path) == 0
        changed = history.set_condition(operation_sha256=sha('after-reservation'), resource_id='fixture-host',
            state='degraded', reason='maintenance', reported_at='2026-10-20T11:00:00Z')
        history.close()
        before_dispatch = time.monotonic_ns()
        start_prepared(handle)
        result = finish(handle)
        assert handle.read()['unit'] == reserved['unit']
        assert handle.read()['started_monotonic_ns'] >= before_dispatch
        assert handle.read()['statistics']['condition_ref'] == changed
        with sqlite3.connect(path) as db:
            sample = json.loads(db.execute('SELECT data FROM run_statistics').fetchone()[0])
            assert sample['condition_ref'] == changed
            assert sample['elapsed_seconds'] == result.metadata['elapsed_seconds']
        assert counts(path) == 1
    finally:
        history.close()
        cleanup(handle)


def test_blocking_pairwise_job_uses_same_native_statistics_path_and_preserves_unknown_cpu(tmp_path):
    """A real tiny alignment, without an episode, model or production credit."""
    program = ('from Bio.Align import PairwiseAligner\n'
        'aligner=PairwiseAligner(mode="local", match_score=2, mismatch_score=-1, '
        'open_gap_score=-2, extend_gap_score=-.5)\n'
        'print(aligner.score("ACGT", "ACCT"))\n')
    policy = LocalJobPolicy(128*1024**2, 4*1024**2)
    execution_class = replace(scope(), phase='pairwise_sequence_alignment',
        implementation_sha256=sha(program), parameters_sha256=sha(program),
        query_residues=4, reference_residues=4, cpu_threads=None,
        memory_bytes=policy.memory_bytes, scratch_bytes=policy.scratch_bytes)
    path = tmp_path/'global.sqlite'
    history = RunHistory(path)
    condition = history.set_condition(operation_sha256=sha('ordinary-native-start'), resource_id='fixture-host',
        state='normal', reason='operator_report', reported_at='2026-10-21T06:00:00Z')
    history.close()
    directory = tmp_path/'ordinary-tool'; directory.mkdir()
    result = run_local_job([sys.executable, '-c', program], cwd=directory, policy=policy,
        statistics=NativeStatistics.pending(path, execution_class))
    assert result.returncode == 0 and result.stdout_path.read_text() == '5.0\n'
    assert result.metadata['statistics_export']['state'] == 'recorded'
    assert result.metadata['statistics_export']['class_ref'] == execution_class.ref
    with sqlite3.connect(path) as db:
        row, = db.execute('SELECT class_ref,data FROM run_statistics').fetchall()
        statistic = json.loads(row[1])
        assert row[0] == execution_class.ref
        assert statistic['outcome'] == 'succeeded' and statistic['duration_kind'] == 'complete'
        assert statistic['elapsed_seconds'] == result.metadata['elapsed_seconds'] > 0
        assert statistic['condition_ref'] == condition
        recorded_class = json.loads(db.execute('SELECT data FROM execution_classes').fetchone()[0])
        assert recorded_class['cpu_threads'] is None
        assert recorded_class['query_residues'] == recorded_class['reference_residues'] == 4
    # Successful blocking cleanup does not discard the committed statistic.
    assert not list(directory.glob('*.handle.json'))
    assert not list(directory.glob('.local-job-*.statistics'))


@pytest.mark.parametrize('returncode', [0, 7])
def test_blocking_measurement_survives_temporary_directory_and_missing_history(tmp_path, monkeypatch, returncode):
    """Recover actual success/failure without repeating the native command."""
    import shutil
    from gene_annotation_episode.resource_estimation import ResourceToolEstimator
    path = tmp_path/'not-created.sqlite'
    recovery = tmp_path/'native-receipts'
    directory = tmp_path/'ordinary-tool'; directory.mkdir()
    context = NativeStatistics.pending(path, scope(), recovery_directory=recovery)
    assert NativeStatistics.from_record(context.as_record()) == context
    command = [sys.executable, '-c', f'print("private-output"); raise SystemExit({returncode})']
    returned = run_local_job(command, cwd=directory, policy=POLICY, statistics=context)
    assert returned.returncode == returncode
    exported = returned.metadata['statistics_export']
    assert exported['state'] == 'unavailable' and exported['code'] == 'statistics_history_unavailable'
    assert exported['condition_capture'] == 'unavailable_before_submission'
    measurement = NativeMeasurement.from_record(exported['measurement'])
    assert measurement.statistic.elapsed_seconds == returned.metadata['elapsed_seconds'] > 0
    assert measurement.statistic.outcome == ('succeeded' if returncode == 0 else 'failed')
    receipt, = recovery.glob('*.measurement.json')
    original = receipt.read_bytes()
    assert receipt.name == measurement.statistic.attempt_sha256+'.measurement.json'
    assert 'private-output' not in original.decode() and str(directory) not in original.decode()
    assert not path.exists() and not list(directory.glob('*.handle.json'))
    shutil.rmtree(directory)

    # The native files, original owner and service are no longer needed.
    def no_execution(*args, **kwargs):
        raise AssertionError('recovery must not execute or inspect a native service')
    monkeypatch.setattr(subprocess, 'run', no_execution)
    history = RunHistory(path)
    later = history.set_condition(operation_sha256=sha('later'), resource_id='fixture-host',
        state='degraded', reason='outage', reported_at='2026-10-21T09:00:00Z')
    history.close()
    assert recover_native_measurement(receipt)['state'] == 'recorded'
    assert recover_native_measurement(receipt)['state'] == 'recorded'
    assert counts(path) == 1 and receipt.read_bytes() == original
    with sqlite3.connect(path) as db:
        recorded, = db.execute('SELECT data FROM run_statistics').fetchall()
        assert json.loads(recorded[0]) == asdict(measurement.statistic)
        assert json.loads(recorded[0])['condition_ref'] is None
    # A later outage must not relabel the original unknown starting condition.
    history = RunHistory(path, create=False)
    snapshot = history.capture(scope())
    reader = history.reader(snapshot)
    original_data = reader.get(snapshot)
    assert original_data['current_condition']['ref'] == later
    assert original_data['statistics'][0]['condition_state'] == 'unspecified'
    forecast, = ResourceToolEstimator().estimate_context({'status': 'available',
        'execution_classes': [asdict(scope())], 'snapshots': [{'ref': snapshot, 'data': original_data}]})
    assert forecast['status'] == 'no_matching_history' and forecast['expected_total_seconds'] is None
    assert forecast['successful_duration_samples'] == 0
    reader.close(); history.close()


def test_blocking_busy_history_recovers_original_known_condition_and_exact_forecast(tmp_path, monkeypatch):
    from gene_annotation_episode.resource_estimation import ResourceToolEstimator
    path = tmp_path/'global.sqlite'
    history = RunHistory(path)
    original = history.set_condition(operation_sha256=sha('original-normal'), resource_id='fixture-host',
        state='normal', reason='operator_report', reported_at='2026-10-21T06:00:00Z')
    history.close()
    context = NativeStatistics.capture(path, scope(), recovery_directory=tmp_path/'receipts')
    blocker = sqlite3.connect(path)
    blocker.execute('BEGIN EXCLUSIVE')
    directory = tmp_path/'ordinary-tool'; directory.mkdir()
    try:
        returned = run_local_job([sys.executable, '-c', 'print("fixture")'],
            cwd=directory, policy=POLICY, statistics=context)
        assert returned.metadata['statistics_export']['state'] == 'unavailable'
        receipt, = context.recovery_directory.glob('*.measurement.json')
        measurement = NativeMeasurement.from_record(json.loads(receipt.read_text())['measurement'])
        assert measurement.statistic.condition_ref == original
    finally:
        blocker.rollback(); blocker.close()
    assert counts(path) == 0
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: pytest.fail('recovery resubmitted work'))
    assert recover_native_measurement(receipt)['state'] == 'recorded'
    assert counts(path) == 1
    history = RunHistory(path, create=False)
    snapshot = history.capture(scope())
    reader = history.reader(snapshot)
    forecast, = ResourceToolEstimator().estimate_context({'status': 'available',
        'execution_classes': [asdict(scope())], 'snapshots': [{'ref': snapshot, 'data': reader.get(snapshot)}]})
    assert forecast['status'] == 'available' and forecast['successful_duration_samples'] == 1
    assert forecast['expected_total_seconds'] == returned.metadata['elapsed_seconds']
    assert forecast['observed_min_seconds'] == forecast['observed_max_seconds'] == returned.metadata['elapsed_seconds']
    reader.close(); history.close()


def test_measurement_rejects_extra_content_and_recovery_preserves_conflicting_identity(tmp_path):
    path = tmp_path/'not-created.sqlite'
    directory = tmp_path/'job'; directory.mkdir()
    recovery = tmp_path/'receipts'
    result = run_local_job([sys.executable, '-c', 'print("fixture")'], cwd=directory, policy=POLICY,
        statistics=NativeStatistics.pending(path, scope(), recovery_directory=recovery))
    receipt, = recovery.glob('*.measurement.json')
    body = json.loads(receipt.read_text())
    body['measurement']['findings'] = 'an unrestricted scientific paragraph'
    with pytest.raises(ValueError, match='unsupported_native_execution_measurement'):
        NativeMeasurement.from_record(body['measurement'])
    del body['measurement']['findings']
    history = RunHistory(path)
    measurement = NativeMeasurement.from_record(body['measurement'])
    # Simulate an existing conflicting global fact, without overwriting it.
    conflict = replace(measurement.statistic, elapsed_seconds=measurement.statistic.elapsed_seconds+1)
    history.record(measurement.execution_class, conflict)
    history.close()
    original_receipt = receipt.read_bytes()
    disposition = recover_native_measurement(receipt)
    assert disposition['code'] == 'statistics_identity_conflict'
    assert receipt.read_bytes() == original_receipt and counts(path) == 1
    with sqlite3.connect(path) as db:
        assert json.loads(db.execute('SELECT data FROM run_statistics').fetchone()[0]) == asdict(conflict)
    assert result.returncode == 0


def test_recovery_storage_failure_does_not_block_native_result_or_available_history(tmp_path):
    path = tmp_path/'global.sqlite'
    history = RunHistory(path); history.close()
    blocked_directory = tmp_path/'cannot-be-a-directory'
    blocked_directory.write_text('fixture file obstructs receipt directory')
    directory = tmp_path/'job'; directory.mkdir()
    result = run_local_job([sys.executable, '-c', 'print("fixture")'], cwd=directory, policy=POLICY,
        statistics=NativeStatistics.pending(path, scope(), recovery_directory=blocked_directory))
    assert result.returncode == 0
    exported = result.metadata['statistics_export']
    assert exported['state'] == 'recorded' and counts(path) == 1
    assert exported['recovery_state'] == 'unavailable'
    assert exported['recovery_code'] == 'statistics_receipt_storage_unavailable'
    measurement = NativeMeasurement.from_record(exported['measurement'])
    assert measurement.statistic.elapsed_seconds == result.metadata['elapsed_seconds']
    assert blocked_directory.read_text() == 'fixture file obstructs receipt directory'
