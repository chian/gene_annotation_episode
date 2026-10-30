"""Check the exact retained finite worker at a failed full-path boundary.

This reuses the original completed native/worker bytes. It dispatches no job
and creates no episode action. Run with478 --existing-case explicitly selected.
"""
from importlib import import_module
import json
import os
from pathlib import Path

from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_atac_episode_path_2026-10-27_478.fixture_helpers')


def test_original_actual_worker_controls_match_shared_binding(monkeypatch):
    directory = Path(os.environ['ATAC478_EXISTING_CASE'])
    configuration = json.loads((directory / 'fixture-configuration.json').read_text())

    def deny(*args, **kwargs):
        raise AssertionError('worker control validation attempted new work')

    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    root, = [path.parent for path in (directory / 'run').rglob('worker-execution.json')]
    receipt = {key: json.loads((root / name).read_text()) for name, key in (
        ('intent.json', 'intent'), ('capture.json', 'capture'), ('native-snapshot.json', 'native'),
        ('worker-plan.json', 'worker_plan'), ('worker-capture.json', 'worker_capture'),
        ('worker-execution.json', 'worker_execution'))}
    with Store(directory / 'state') as store:
        before = {table: F.rows(store, table) for table in F.TABLES}
        owner = F.execution_owner(store, directory, configuration)
        owner.atac_results.receipts.validate_worker(receipt, verify_control_bytes=True)
        assert {table: F.rows(store, table) for table in F.TABLES} == before
