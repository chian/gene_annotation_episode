"""Real launcher ownership, no native process or scientific outcome.

Requested thread values are API metadata only. These tests allocate no such
threads or memory; the original authenticated workflow cgroup remains CPU100,
5 GiB RAM and no swap. Negative owner records are explicitly controlled fixtures.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import workflow_budget as owner


def actual_owner():
    value = owner.active_budget()
    assert value['window_id'] == owner.WINDOW_ID
    assert value['unit'] == owner.UNIT and value['slice'] == owner.SLICE
    assert value['environment_bounds'] == {'cpu_percent': 100, 'memory_bytes': 5*1024**3, 'swap_bytes': 0}
    assert owner.ENVIRONMENT_BOUNDS == value['environment_bounds']
    return value


@pytest.mark.parametrize('requested_threads', [1, 4, 64], ids=['one', 'four', 'sixty-four'])
def test_requested_threads_are_metadata_under_actual_one_cpu_owner(tmp_path, requested_threads):
    actual = actual_owner()
    policy = SimpleNamespace(memory_bytes=1024)
    before = dict(vars(policy))
    assert owner.native_budget(policy, requested_threads, tmp_path) == actual
    assert vars(policy) == before
    assert owner.active_budget() == actual


def test_exact_actual_memory_bound_is_accepted_without_allocating_it(tmp_path):
    actual = actual_owner()
    policy = SimpleNamespace(memory_bytes=actual['environment_bounds']['memory_bytes'])
    assert owner.native_budget(policy, 1, tmp_path) == actual


def test_memory_above_actual_bound_remains_rejected(tmp_path):
    actual = actual_owner()
    policy = SimpleNamespace(memory_bytes=actual['environment_bounds']['memory_bytes'] + 1)
    with pytest.raises(ValueError, match='^native_request_exceeds_environment_bounds$'):
        owner.native_budget(policy, 1, tmp_path)
    assert owner.active_budget() == actual


def test_output_outside_actual_run_remains_rejected():
    actual = actual_owner()
    outside = Path(__file__).resolve().parents[4]
    # This is a read-only operand. No directory outside the actual run is created.
    assert not outside.is_relative_to(Path(actual['run_directory']))
    with pytest.raises(ValueError, match='^native_output_outside_workflow_run$'):
        owner.native_budget(SimpleNamespace(memory_bytes=1024), 1, outside)
    assert owner.active_budget() == actual


def test_original_owner_start_identity_rejection_precedes_admission(tmp_path, monkeypatch):
    actual = actual_owner()
    directory = tmp_path / 'explicit-invalid-owner'; directory.mkdir()
    invalid = {**deepcopy(actual), 'run_directory': str(directory),
               'supervisor_start_ticks': 'explicit-invalid-start-fixture'}
    selected = directory / 'workflow-budget.json'
    selected.write_text(json.dumps(invalid))
    before = selected.read_bytes()
    monkeypatch.setenv(owner.ENV, str(selected))
    with pytest.raises(ValueError, match='^workflow_budget_owner_not_active$'):
        owner.native_budget(SimpleNamespace(memory_bytes=1024), 1, directory)
    assert selected.read_bytes() == before
