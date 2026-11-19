"""What the literature storage tests share: a real Store, journal and model provider, and the literature probe
episode run by the real runner."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, link
from episode_runtime.tests.probe_world import SETTINGS, collaborators, open_world

from .literature_probe.episode import LiteratureProbe

CONTINUATION = {'literature_probe': SETTINGS}


@pytest.fixture
def world(tmp_path):
    opened = open_world(tmp_path)
    yield opened
    opened['store'].close()


def step(name, **arguments):
    return {'tool': name, 'arguments': arguments}


def run(world, run_id, plan, held):
    """Run ``plan`` in the probe, which is passed ``held`` in custody; its result and the unit outcomes."""
    entry = {'assignment': {'held_refs': held}, 'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([LiteratureProbe()]), 'literature_probe', entry, run_id=run_id,
                  journal=world['journal'], collaborators=collaborators(world, CONTINUATION))
    result = asyncio.run(linked.run())
    return result, [unit[2] for unit in world['journal'].units(run_id, (('literature_probe', run_id),))]
