"""Recording/recovery producer and Root Store share the actual receipt type.

Completion files contain explicitly engineered outcomes and durations. These
checks execute receipt processing, SQLite persistence and redelivery, with no
native job, model request or scientific conclusion.
"""
from dataclasses import asdict
import json
import sqlite3

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory
from gene_annotation_episode.episodic_workflow.root import execution_recording as recording
from gene_annotation_episode.episodic_workflow.root import native_measurement
from gene_annotation_episode.episodic_workflow.root import native_timing_information as timing
from gene_annotation_episode.episodic_workflow.root.tests.test_root_native_receipt_admission import (
    _measurement_record, store_and_operands,
)


@pytest.mark.parametrize('returncode,end_boot,outcome,kind,seconds', [
    (0, 'engineered-boot', 'succeeded', 'complete', 2.5),
    (1, 'engineered-boot', 'failed', 'complete', 2.5),
    (0, 'different-engineered-boot', 'succeeded', 'unmeasured', None),
])
def test_recorded_recovery_receipt_crosses_actual_root_store(
        tmp_path, store_and_operands, returncode, end_boot, outcome, kind, seconds):
    store, operands = store_and_operands
    execution_class = ExecutionClass(**_measurement_record()['execution_class'])
    history_path = tmp_path / 'history.sqlite3'
    history = RunHistory(history_path)
    history.close()
    context = recording.NativeStatistics.capture(history_path, execution_class,
        recovery_directory=tmp_path / 'recovery')
    paths = {name: tmp_path / (name + '.json')
             for name in ('handle', 'status', 'result', 'statistics')}
    body = {'statistics': context.as_record(),
        'paths': {name: str(paths[name]) for name in ('status', 'result', 'statistics')},
        'unit': 'engineered-receipt-unit', 'boot_id': 'engineered-boot',
        'started_monotonic_ns': 1_000_000_000,
        'execution_memory_path': str(tmp_path / 'memory.sqlite3')}
    completion = {'SERVICE_RESULT': 'success' if returncode == 0 else 'exit-code',
        'ended': {'boot_id': end_boot, 'monotonic_ns': 3_500_000_000,
                  'at': '2026-11-13T00:00:00+00:00'}}
    native = {'native_returncode': returncode, 'execution_failure': None,
              'resource_failure': None}
    for name, value in (('handle', body), ('status', completion), ('result', native)):
        paths[name].write_text(canonical(value))
    original = {name: paths[name].read_bytes() for name in ('handle', 'status', 'result')}

    exported = recording.publish_native_statistics(paths['handle'])
    assert exported['state'] == 'recorded'
    assert exported['recovery_state'] == 'retained'
    assert json.loads(paths['statistics'].read_text()) == exported
    measured = recording.NativeMeasurement.from_record(exported['measurement'])
    assert asdict(measured.execution_class) == asdict(execution_class)
    assert (measured.statistic.outcome, measured.statistic.duration_kind,
            measured.statistic.elapsed_seconds) == (outcome, kind, seconds)
    assert measured.execution_class.cpu_threads is None
    assert measured.condition_capture == context.condition_capture
    assert measured.statistic.condition_ref == context.condition_ref

    receipt = timing.record_native_measurement(store, measured,
        operation='align_pair', operands=operands)
    assert type(measured) is native_measurement.NativeMeasurement
    restored = timing.read_measurement(store, receipt)
    assert type(restored) is type(measured)
    assert restored.as_record() == exported['measurement']
    fields = timing.measurement_fields(receipt, restored, operation='align_pair')
    timing.validate_native_measurements(store, fields, schema=timing.MEASUREMENT_SCHEMA)

    recovery = tmp_path / 'recovery' / (measured.statistic.attempt_sha256 + '.measurement.json')
    saved_recovery = recovery.read_bytes()
    assert json.loads(saved_recovery)['measurement'] == measured.as_record()
    assert recording.publish_native_statistics(paths['handle']) == exported
    assert recording.recover_native_measurement(recovery) == exported
    assert recording.recover_native_measurement(recovery) == exported
    recovered = recording.NativeMeasurement.from_record(json.loads(recovery.read_text())['measurement'])
    assert recovered.as_record() == measured.as_record()
    assert recovered.statistic.attempt_sha256 == measured.statistic.attempt_sha256
    assert recovered.statistic.elapsed_seconds == seconds
    assert timing.record_native_measurement(store, restored,
        operation='align_pair', operands=operands) == receipt
    assert len(store.list('native_execution')) == 1
    assert recovery.read_bytes() == saved_recovery
    assert {name: paths[name].read_bytes() for name in original} == original
    with sqlite3.connect(history_path) as db:
        rows = db.execute('SELECT data FROM run_statistics').fetchall()
    assert len(rows) == 1
    assert json.loads(rows[0][0]) == asdict(measured.statistic)
