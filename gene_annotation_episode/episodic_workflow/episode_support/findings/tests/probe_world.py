"""What the findings tests share: a real Store, journal and provider (``episode_runtime.tests.probe_world``) and
the findings probe episode, run through the real runner."""
import asyncio
import io

import pytest
from PIL import Image

from episode_runtime import BindingRegistry, link
from episode_runtime.tests.probe_world import SETTINGS, open_world

from .probe.episode import FindingsProbe

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
    picture = io.BytesIO()
    Image.new('RGB', (6, 4), (200, 30, 30)).save(picture, format='PNG')
    png = store.artifact(picture.getvalue(), 'image/png')
    original = store.put('source', {'provider': 'test', 'accession': 'IMG1', 'uri': None, 'artifact_ref': png,
                                    'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None},
                         origin='external')['id']
    yield {**opened, 'target': target, 'source': source, 'png': png, 'image_source': original}
    store.close()


def run(world, run_id, plan, held=()):
    entry = {'assignment': {'subject_refs': [world['target']], 'input_refs': [world['target']],
                            'held_refs': list(held)},
             'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([FindingsProbe()]), 'probe', entry, run_id=run_id,
                  journal=world['journal'],
                  collaborators={'store': world['store'], 'model_provider': world['provider'],
                                 'continuation': CONTINUATION, 'services': world['services']})
    return asyncio.run(linked.run())


def outcomes(world, run_id):
    return [unit[2] for unit in world['journal'].units(run_id, (('probe', run_id),))]


def tool(name, **arguments):
    return {'tool': name, 'arguments': arguments}
