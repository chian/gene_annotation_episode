"""Finite original/current HOMER implementation identity; never native execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from . import homer_tf_boundary_checks as checks
from .homer_original_argv import homer_adapter_argv as original_argv
from ..library import native_homer_execution as e
from ..library import native_homer_worker as worker


def test_original_software_plan_and_replay_preserve_original_argv(tmp_path, monkeypatch):
    call, calls = checks.make_selected_call(tmp_path, monkeypatch)
    supplied = deepcopy(call['selected']['binding']['software'])
    first = e.prepare_ordinary_homer_attempt(**call)
    assert first['plan']['software'] == supplied
    assert first['plan']['requested_job']['argv'] == original_argv(first['plan'])
    assert first['plan']['request']['arguments'] == call['arguments']
    assert first['plan']['request']['frozen_inputs'] == call['frozen_inputs']
    before = Path(first['handle_path']).read_bytes()
    assert e.prepare_ordinary_homer_attempt(**call) == first
    assert Path(first['handle_path']).read_bytes() == before and len(calls) == 1


def test_current_software_plan_and_replay_select_actual_private_worker(tmp_path, monkeypatch):
    call, calls = checks.make_selected_call(tmp_path, monkeypatch, current=True)
    supplied = deepcopy(call['selected']['binding']['software'])
    first = e.prepare_ordinary_homer_attempt(**call)
    expected = original_argv(first['plan'])
    expected[4] = worker.__name__
    assert first['plan']['software'] == supplied
    assert first['plan']['requested_job']['argv'] == expected == calls[0]['command']
    assert first['plan']['request']['arguments'] == call['arguments']
    assert first['plan']['request']['frozen_inputs'] == call['frozen_inputs']
    before = Path(first['handle_path']).read_bytes()
    assert e.prepare_ordinary_homer_attempt(**call) == first
    assert Path(first['handle_path']).read_bytes() == before and len(calls) == 1


@pytest.mark.parametrize('current', [False, True], ids=['original', 'current'])
def test_mixed_recorded_command_is_rejected(tmp_path, monkeypatch, current):
    call, calls = checks.make_selected_call(tmp_path, monkeypatch, current=current)
    prepared = e.prepare_ordinary_homer_attempt(**call)
    plan = deepcopy(prepared['plan'])
    plan['requested_job']['argv'][4] = (original_argv(plan)[4] if current else worker.__name__)
    plan['identity']['requested_job_sha256'] = e.digest(plan['requested_job'])
    with pytest.raises(ValueError, match='ordinary_homer_plan_job_conflict'):
        e.validate_homer_plan(plan)
    assert len(calls) == 1


@pytest.mark.parametrize('current', [False, True], ids=['original', 'current'])
def test_supplied_wrong_source_generation_rejects_at_original_preflight(tmp_path, monkeypatch, current):
    call, calls = checks.make_selected_call(tmp_path, monkeypatch, current=current,
        inventory_kind='original' if current else 'current')
    with pytest.raises(e.HomerPreflightRejected, match='ordinary_homer_preflight_rejected') as failure:
        e.prepare_ordinary_homer_attempt(**call)
    assert type(failure.value.__cause__) is ValueError
    assert str(failure.value.__cause__) == 'ordinary_homer_software_inventory_entry_closure_missing'
    assert calls == []


@pytest.mark.parametrize('missing', ['native_homer_worker.py', 'retained_file_pin.py', 'communication.py'])
def test_current_missing_actual_provider_rejects_before_reservation(tmp_path, monkeypatch, missing):
    call, calls = checks.make_selected_call(tmp_path, monkeypatch, current=True)
    software = call['selected']['binding']['software']
    path = Path(software['software_files_file']['path'])
    record = json.loads(path.read_bytes())
    matched = [row for row in record['files'] if Path(row['path']).name == missing]
    assert len(matched) == 1
    record['files'] = [row for row in record['files'] if row is not matched[0]]
    checks._write(path, record)
    software['software_files_file'] = checks._pin(path)
    with pytest.raises(e.HomerPreflightRejected) as failure:
        e.prepare_ordinary_homer_attempt(**call)
    assert str(failure.value.__cause__) == 'ordinary_homer_software_inventory_entry_closure_missing'
    assert calls == []


def test_unknown_software_version_rejects_before_original_inventory_io(tmp_path, monkeypatch):
    call, calls = checks.make_selected_call(tmp_path, monkeypatch, current=True)
    call['selected']['binding']['software']['version'] = 'unrecognized_implementation'
    def forbidden(*args, **kwargs):
        pytest.fail('software schema rejection must precede inventory I/O')
    monkeypatch.setattr(e, 'file_pin', forbidden)
    monkeypatch.setattr(e, 'read_bytes', forbidden)
    with pytest.raises(ValueError, match='ordinary_homer_software_invalid'):
        e.prepare_ordinary_homer_attempt(**call)
    assert calls == []


def test_current_worker_rejects_original_plan_before_native_execution(tmp_path, monkeypatch):
    call, calls = checks.make_selected_call(tmp_path, monkeypatch)
    prepared = e.prepare_ordinary_homer_attempt(**call)
    plan = prepared['plan']
    monkeypatch.chdir(plan['operation_directory'])
    def forbidden(*args, **kwargs):
        pytest.fail('mismatched worker may not dispatch native execution')
    monkeypatch.setattr(worker.subprocess, 'Popen', forbidden)
    with pytest.raises(ValueError, match='homer_worker_selected_worker_identity_conflict'):
        worker.run_native_homer(Path(prepared['plan_file']['path']), plan['selected_payload_sha256'])
    assert not Path(plan['attempt_directory']).exists() and len(calls) == 1
