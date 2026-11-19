"""What the probe-episode tests share: a real Store, journal, model provider and two real services."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from .fact_collection.fact_extraction.episode import FactExtraction
from .probe.episode import Probe

SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}
CONTINUATION = {'probe': SETTINGS, 'fact_collection/fact_extraction': SETTINGS}
EXTRACTION = 'fact_collection__fact_extraction'


class Counter:
    """A real service: counts its uses."""

    def __init__(self):
        self.count = 0

    def bump(self):
        self.count += 1
        return self.count


class Switch:
    """A real service: whether the next tool failure is wanted."""

    def __init__(self, fail=False):
        self.fail = fail


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    subject = store.artifact(json.dumps({'name': 'GeneX', 'function': 'kinase'}), 'application/json')
    unrelated = store.artifact(json.dumps({'name': 'GeneY', 'function': 'unknown'}), 'application/json')
    built = []
    counter, switch = Counter(), Switch()

    def make(name, value):
        def factory():
            built.append(name)
            return value
        return factory
    services = {'counter': make('counter', counter), 'switch': make('switch', switch),
                'secret': make('secret', object())}
    yield {'store': store, 'subject': subject, 'unrelated': unrelated, 'counter': counter, 'switch': switch,
           'built': built, 'services': services, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path), 'tmp': tmp_path,
           'calls': tmp_path / 'model_calls'}
    store.close()


def collaborators(world, continuation=CONTINUATION, services=None):
    return {'store': world['store'], 'model_provider': world['provider'], 'continuation': continuation,
            'services': world['services'] if services is None else services}


def registry():
    return BindingRegistry([Probe(), FactExtraction()])


def entry(world, plan, assignment=None, **message):
    return {'assignment': {'subject_refs': [world['subject']], **(assignment or {})},
            'message': {'plan': plan, **message}, 'selection': []}


def run(world, run_id, plan, assignment=None, continuation=CONTINUATION, selection=(), **message):
    linked = link(registry(), 'probe', {**entry(world, plan, assignment, **message), 'selection': list(selection)},
                  run_id=run_id, journal=world['journal'], collaborators=collaborators(world, continuation))
    return asyncio.run(linked.run())


def again(world, run_id, continuation=CONTINUATION):
    return asyncio.run(resume(registry(), run_id=run_id, journal=world['journal'],
                              collaborators=collaborators(world, continuation)).run())


def probe_path(run_id):
    return (('probe', run_id),)


def outcomes(world, run_id, path=None):
    return [unit[2] for unit in world['journal'].units(run_id, path or probe_path(run_id))]


def tool(name, **arguments):
    return {'tool': name, 'arguments': arguments}


def child(slot, **arguments):
    return {'child': slot, 'arguments': arguments}
