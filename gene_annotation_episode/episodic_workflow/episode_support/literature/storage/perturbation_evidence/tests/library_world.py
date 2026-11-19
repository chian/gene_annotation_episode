"""A real run of the library probe episode: a real Store with its problem, the journal and the model provider."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, link
from episode_runtime.tests.probe_world import open_world

from .library_probe.episode import LibraryProbe

SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}
CONTINUATION = {'library_probe': SETTINGS}


@pytest.fixture
def world(tmp_path):
    opened = open_world(tmp_path)
    store = opened['store']
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    yield {**opened, 'subjects': store.problem()['subject_refs']}
    store.close()


def run_scenarios(world, run_id, *plan):
    """Run each ``(name, keywords)`` of ``plan`` as one unit of the probe episode; the unit outcomes."""
    steps = [{'name': name, 'keywords': keywords} for name, keywords in plan]
    collaborators = {'store': world['store'], 'model_provider': world['provider'], 'continuation': CONTINUATION,
                     'services': world['services']}
    linked = link(BindingRegistry([LibraryProbe()]), 'library_probe',
                  {'assignment': {'subject_refs': world['subjects']}, 'message': {'plan': steps}, 'selection': []},
                  run_id=run_id, journal=world['journal'], collaborators=collaborators)
    asyncio.run(linked.run())
    return [unit[2]['outcome'] for unit in world['journal'].units(run_id, (('library_probe', run_id),))
            if 'idle' not in unit[2]['outcome']]
