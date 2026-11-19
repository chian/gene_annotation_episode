"""What the acquisition tests share: a real Store, journal and provider (``episode_runtime.tests.probe_world``) and
the acquisition probe episode, run through the real runner."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, link
from episode_runtime.tests.probe_world import SETTINGS, open_world

from .probe.episode import AcquisitionProbe

CONTINUATION = {'probe': SETTINGS}


@pytest.fixture
def world(tmp_path):
    opened = open_world(tmp_path)
    store = opened['store']
    target, = store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ', molecule='protein')['subject_refs']
    note = store.artifact('The sequence is intact.', 'text/plain')
    source = store.put('source', {'provider': 'test', 'accession': 'X1', 'uri': None, 'artifact_ref': note,
                                  'text_ref': note, 'request_ref': None, 'version': None, 'retrieved_at': None},
                       origin='external')['id']
    yield {**opened, 'target': target, 'source': source}
    store.close()


def run(world, run_id, plan, held=()):
    entry = {'assignment': {'subject_refs': [world['target']], 'input_refs': [world['target']],
                            'held_refs': list(held)},
             'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([AcquisitionProbe()]), 'probe', entry, run_id=run_id,
                  journal=world['journal'],
                  collaborators={'store': world['store'], 'model_provider': world['provider'],
                                 'continuation': CONTINUATION, 'services': world['services']})
    return asyncio.run(linked.run())


def outcomes(world, run_id):
    return [unit[2] for unit in world['journal'].units(run_id, (('probe', run_id),))]


def tool(name, **arguments):
    return {'tool': name, 'arguments': arguments}
