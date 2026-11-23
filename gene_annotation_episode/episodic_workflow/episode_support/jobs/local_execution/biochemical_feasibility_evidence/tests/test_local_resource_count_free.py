"""Controlled capacity-row contracts; no worker, process or native dispatch.

Quantity values below are arithmetic data, never launcher allocations.
"""
from contextlib import closing
import importlib
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

AXIS = 'a110'
resources_module = importlib.import_module('gene_annotation_episode.local_resources')
native = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.native_lifecycle')
jobs = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.local_jobs')
guidance = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.instructions.execution_guidance')










@pytest.mark.parametrize('count', [1, 0, None])
def test_new_count_setting_is_not_a_current_policy(tmp_path, count):
    with pytest.raises(ValueError, match='invalid_local_resource_settings'):
        resources_module.LocalResources(tmp_path / 'new', {'max_running_jobs': count})


def test_ordinary_constructor_retains_empty_database_initialization(tmp_path):
    directory = tmp_path / 'empty-database'
    directory.mkdir()
    with closing(sqlite3.connect(directory / 'capacity.sqlite3')):
        pass
    owner = resources_module.LocalResources(directory)
    assert owner.as_record()['version'] == 'shared_local_resources'
    assert set(owner.as_record()['limits']) == {'memory_bytes', 'scratch_bytes'}


def test_route_recommendation_uses_dimensions_not_historical_count():
    route = {'binding_available': True, 'capacity_state': 'fresh',
        'available': {'job_slots': 0, 'cpu_threads': 1, 'memory_bytes': 10, 'scratch_bytes': 10}}
    view = guidance.compare_routes(route, None,
        requirements={'cpu_threads': 64, 'memory_bytes': 10, 'scratch_bytes': 10})
    assert view['preferred'] == 'local' and view['routes']['local']['eligible'] is True


