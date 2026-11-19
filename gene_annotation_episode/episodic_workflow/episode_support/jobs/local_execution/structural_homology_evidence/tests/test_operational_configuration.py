"""Real A102 constructors and SQLite admission; external host observations controlled explicitly."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode import local_resources as lr
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence import local_jobs
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_alignment.structural_homology_evidence import read_mapping
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.structural_homology_evidence.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.evidence_operations import A102ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.tools import ToolRegistry
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




def test_route_recommendation_uses_resources_not_count():
    from gene_annotation_episode.episodic_workflow.episode_support.instructions.execution_guidance import compare_routes
    route = {'binding_available': True, 'capacity_state': 'fresh',
             'available': {'cpu_threads': 1, 'memory_bytes': 1024, 'scratch_bytes': 1024, 'job_slots': 0}}
    result = compare_routes(route, None, requirements={'cpu_threads': 1, 'memory_bytes': 512})
    assert result['preferred'] == 'local' and result['admission_reserved'] is False


















@pytest.mark.parametrize('kind',['new','empty_database','saved_current'],
                         ids=['new','empty_database','saved_current'])
@pytest.mark.parametrize('setting_request',['unknown','memory','boolean'],ids=['unknown','memory','boolean'])
def test_rejected_custom_initialization_preserves_all_existing_bytes(kind,setting_request,directory,tmp_path,monkeypatch):
    if kind=='empty_database':
        directory.mkdir();db=sqlite3.connect(directory/'capacity.sqlite3');db.close()
    elif kind=='saved_current':lr.LocalResources(directory)
    settings={'unknown':{'invented_field':1},'memory':{'memory_bytes':21474836481},
              'boolean':{'memory_bytes':True}}[setting_request]
    def snapshot():
        return {'exists':directory.exists(),
            'directories':sorted(str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_dir()),
            'files':{str(p.relative_to(directory)):p.read_bytes().hex() for p in directory.rglob('*') if p.is_file()}}
    before=snapshot()
    with pytest.raises(ValueError) as caught:lr.LocalResources(directory,settings)
    assert type(caught.value) is ValueError and snapshot()==before
    expected=({'unknown':'invalid_local_resource_settings','memory':'local_resource_limits_exceed_environment_bounds',
         'boolean':'invalid_local_resource_limits'}[setting_request])
    assert str(caught.value)==expected
    (tmp_path/'raw-custom-initialization.json').write_text(json.dumps({'kind':kind,'request':setting_request,
        'settings':settings,'before':before,'after':snapshot(),'exception_type':'builtins.ValueError',
        'message':str(caught.value)},indent=2))


@pytest.mark.parametrize('count',[0,-1,True,'3',None],ids=['zero','negative','boolean','string','null'])
def test_requested_threads_remain_positive_typed_metadata(count,directory,tmp_path,monkeypatch):
    resource=lr.LocalResources.configured()
    handle=Handle(tmp_path/'typed.json');before=handle.path.read_bytes()
    with resource._transaction() as db:rows=[dict(row) for row in db.execute('SELECT * FROM reservations')]
    with pytest.raises(ValueError,match='^invalid_local_resource_allocation$'):
        resource.reserve(handle,cpu_threads=count,policy=local_jobs.LocalJobPolicy(1024,1024))
    assert handle.path.read_bytes()==before
    with resource._transaction() as db:assert [dict(row) for row in db.execute('SELECT * FROM reservations')]==rows
