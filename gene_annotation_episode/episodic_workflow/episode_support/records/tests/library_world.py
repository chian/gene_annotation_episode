"""What the records library tests share: a real Store, journal and provider (the runtime's own ``open_world``), the
library probe episode, and a run of one plan on the records passed in custody."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, link
from episode_runtime.tests.probe_world import open_world

from .library_probe.episode import LibraryProbe

SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}
CONTINUATION = {'library_probe': SETTINGS}
PROTEIN = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ'


@pytest.fixture
def bare_world(tmp_path):
    """A real Store without a problem."""
    opened = open_world(tmp_path)
    yield opened
    opened['store'].close()

@pytest.fixture
def world(bare_world):
    """The Store with one protein subject, the problem."""
    target, = bare_world['store'].create_problem(raw_sequence=PROTEIN, molecule='protein')['subject_refs']
    return {**bare_world, 'target': target}


def tool(name, **arguments):
    return {'tool': name, 'arguments': arguments}


def run(world, run_id, plan, subjects=None, held=()):
    """Run the plan with the subjects and held records passed in custody; the units' records, in order."""
    collaborators = {'store': world['store'], 'model_provider': world['provider'], 'continuation': CONTINUATION,
                     'services': world['services']}
    entry = {'assignment': {'subject_refs': list(subjects or [world['target']]), 'held_refs': list(held)},
             'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([LibraryProbe()]), 'library_probe', entry, run_id=run_id,
                  journal=world['journal'], collaborators=collaborators)
    result = asyncio.run(linked.run())
    path = (('library_probe', run_id),)
    return result, [unit[2] for unit in world['journal'].units(run_id, path)]
