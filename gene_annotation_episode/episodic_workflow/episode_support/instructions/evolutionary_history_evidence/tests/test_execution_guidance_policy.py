"""Actual A104 route recommendations retain byte and provenance safeguards."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.execution_guidance import compare_routes


def test_local_first_requires_real_capacity_and_sufficient_deadline():
    route = {'binding_available': True, 'capacity_state': 'fresh',
             'available': {'cpu_threads': 1, 'memory_bytes': 100, 'scratch_bytes': 100},
             'total_seconds_upper': 50, 'provenance': ['measured-prediction']}
    need = {'cpu_threads': 1, 'memory_bytes': 50}
    assert compare_routes(route, route, requirements=need)['preferred'] == 'local'
    busy = {**route, 'available': {**route['available'], 'memory_bytes': 10}}
    assert compare_routes(busy, route, requirements=need)['preferred'] == 'hpc'
    stale = {**route, 'capacity_state': 'stale'}
    assert compare_routes(stale, stale, requirements=need)['preferred'] is None
    assert compare_routes({**route, 'total_seconds_upper': 100000}, route,
                          requirements=need)['preferred'] == 'local'


@pytest.mark.parametrize('reported_threads', [0, 1, None])
def test_count_metadata_does_not_exclude_byte_sufficient_routes(reported_threads):
    route = {'binding_available': True, 'capacity_state': 'fresh',
             'available': {'cpu_threads': reported_threads, 'job_slots': 0,
                           'memory_bytes': 100, 'scratch_bytes': 100},
             'total_seconds_upper': None, 'provenance': ['actual-capacity']}
    original = deepcopy(route)
    requirements = {'cpu_threads': 128, 'memory_bytes': 50, 'scratch_bytes': 50}
    result = compare_routes(route, None, requirements=requirements)
    assert result['preferred'] == 'local'
    assert result['admission_reserved'] is False
    assert result['routes']['local'] == {'eligible': True, 'reasons': [],
        'total_seconds_upper': None, 'provenance': ['actual-capacity']}
    assert route == original


@pytest.mark.parametrize('fault,reason', [
    ('memory_bytes', 'insufficient_or_unknown_memory_bytes'),
    ('scratch_bytes', 'insufficient_or_unknown_scratch_bytes'),
    ('missing_memory', 'insufficient_or_unknown_memory_bytes'),
    ('missing_scratch', 'insufficient_or_unknown_scratch_bytes'),
    ('stale', 'refresh_capacity'),
    ('unbound', 'execution_binding_unavailable'),
])
def test_byte_capacity_freshness_and_binding_still_select_supported_hpc(fault, reason):
    remote = {'binding_available': True, 'capacity_state': 'fresh',
        'available': {'memory_bytes': 100, 'scratch_bytes': 100},
        'total_seconds_upper': 10**12, 'provenance': ['retained-forecast']}
    local = deepcopy(remote)
    if fault in ('memory_bytes', 'scratch_bytes'):
        local['available'][fault] = 49
    elif fault.startswith('missing_'):
        local['available'].pop(fault.removeprefix('missing_') + '_bytes')
    elif fault == 'stale':
        local['capacity_state'] = 'stale'
    else:
        local['binding_available'] = False
    before = deepcopy((local, remote))
    requirements = {'memory_bytes': 50, 'scratch_bytes': 50}
    result = compare_routes(local, remote, requirements=requirements)
    assert result['preferred'] == 'hpc'
    assert result['routes']['local']['reasons'] == [reason]
    assert result['routes']['hpc']['total_seconds_upper'] == 10**12
    assert result['routes']['hpc']['provenance'] == ['retained-forecast']
    assert result['admission_reserved'] is False
    assert compare_routes(local, None, requirements=requirements)['preferred'] is None
    assert (local, remote) == before
