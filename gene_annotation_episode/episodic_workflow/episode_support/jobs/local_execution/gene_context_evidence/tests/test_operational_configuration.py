"""Real A103 constructors and SQLite admission; external host observations controlled explicitly."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode import local_resources as lr
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence import local_jobs
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations import A103ToolRegistry
from gene_annotation_episode.state import Store
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path/'store') as value:
        yield value


@pytest.fixture
def directory(tmp_path, monkeypatch):
    selected = tmp_path/'capacity'
    monkeypatch.setenv(lr.DIRECTORY_ENV, str(selected))
    return selected


@pytest.mark.parametrize('settings,reason', [
    ({'max_running_jobs': 1}, 'invalid_local_resource_settings'),
    ({'job_slots': 1}, 'invalid_local_resource_settings'),
    ({'memory_bytes': 20*1024**3}, 'local_resource_limits_exceed_environment_bounds'),
    ({'memory_bytes': True}, 'invalid_local_resource_limits'),
    ({'memory_bytes': 0}, 'invalid_local_resource_limits'),
], ids=['retired_count', 'retired_slots', 'memory_bound', 'boolean', 'zero'])
def test_current_settings_reject_invalid(settings, reason, directory):
    with pytest.raises(ValueError) as caught:
        lr.LocalResources.configured(settings)
    assert type(caught.value) is ValueError and str(caught.value) == reason


class Handle:
    def __init__(self, path, unit='gene-local-job-operational-fixture.service'):
        self.path = path
        self.value = {'unit': unit, 'stage': 'prepared'}
        path.write_text(json.dumps(self.value))

    def read(self):
        return deepcopy(self.value)


def test_actual_native_receipt_and_machine_bounds(tmp_path, monkeypatch):
    # Required connected check under the normal single-workflow launcher.
    # No fake status, control group, native outcome, timeout, or count ceiling.
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.native_lifecycle import run_blocking
    # Use the actual launcher's own run/slice instead of an unscoped shared
    # host directory; this preserves other windows' independent ownership.
    monkeypatch.delenv(lr.DIRECTORY_ENV, raising=False)
    work = tmp_path/'native'
    work.mkdir()
    result = run_blocking(['/bin/true'], cwd=work,
        policy=local_jobs.LocalJobPolicy(512*1024**2, 1024**2), cpu_threads=1)
    assert result.returncode == 0
    verified = result.metadata['verified_cgroup']
    assert verified['memory_max'] == 512*1024**2 and verified['memory_swap_max'] == 0
    assert verified['cpu_threads'] == 1
    quota, period = map(int, verified['cpu_max'].split())
    assert quota == period
    (tmp_path/'raw-native-result.json').write_text(json.dumps({
        'returncode': result.returncode, 'metadata': result.metadata,
        'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path)}, indent=2))


@pytest.mark.parametrize('count',[0,-1,True,'3',None],ids=['zero','negative','boolean','string','null'])
def test_requested_threads_remain_positive_typed_metadata(count,directory,tmp_path,monkeypatch):
    resource=lr.LocalResources.configured()
    handle=Handle(tmp_path/'typed.json');before=handle.path.read_bytes()
    with resource._transaction() as db:rows=[dict(row) for row in db.execute('SELECT * FROM reservations')]
    with pytest.raises(ValueError,match='^invalid_local_resource_allocation$'):
        resource.reserve(handle,cpu_threads=count,policy=local_jobs.LocalJobPolicy(1024,1024))
    assert handle.path.read_bytes()==before
    with resource._transaction() as db:assert [dict(row) for row in db.execute('SELECT * FROM reservations')]==rows


