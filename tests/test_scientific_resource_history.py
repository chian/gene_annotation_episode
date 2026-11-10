"""Caller resource history must reach the actual scientific parent's prompt."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.scientific_process_prompt import render_episode_steering


FIXTURE = Path(__file__).parent / 'fixtures/work_reports/a107-genomic06-resource-context.json.gz'


def test_actual_root_receives_resource_history_beyond_the_host_context():
    with gzip.open(FIXTURE, 'rt') as handle:
        original = json.load(handle)
    frame = original['context']
    before = deepcopy(frame)
    state = frame['fields']
    history = state['execution_initial_information']['aurora']['retained_operational_history']
    assert history['biological_results_included'] is False
    assert len(history['observations']) == 2
    assert all(row['job_id'] not in original['actual_input'] for row in history['observations'])
    provider = object.__new__(_SessionConnection)
    provider.scientific_prompt_states = {}
    rendered, _ = provider._presentation(original['episode_id'], 'REASONING', original['instructions'], frame)
    documents = [json.loads(line) for line in rendered.splitlines() if line.startswith('{')]
    for name in ('execution_resource_capabilities', 'execution_initial_information'):
        assert next(value[name] for value in documents if name in value) == state[name]
    assert all(row['job_id'] in rendered for row in history['observations'])
    assert all(row['submitted_script']['sha256'] in rendered for row in history['observations'])
    assert '"failure_cause":"unresolved"' in rendered
    assert '"biological_results_included":false' in rendered
    assert provider.scientific_prompt_states[(original['episode_id'], 'REASONING')] == state
    assert frame == before


def test_supplied_resource_observations_preserve_unknowns_and_actual_operands():
    with gzip.open(FIXTURE, 'rt') as handle:
        original = json.load(handle)
    state = deepcopy(original['context']['fields'])
    observed = {'resource_id': 'aurora', 'current_availability': None,
        'returncode': 1, 'capacity_bytes': 5368709120, 'swap_bytes': 0,
        'original_job_id': 'actual-resource-observation'}
    state['execution_resource_information'] = observed
    before = deepcopy(state)
    rendered = render_episode_steering(state)
    documents = [json.loads(line) for line in rendered.splitlines() if line.startswith('{')]
    assert next(value['execution_resource_information'] for value in documents
        if 'execution_resource_information' in value) == observed
    assert state == before
