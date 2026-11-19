"""What the probe-episode tests share: a real Store, journal, model provider and three real services."""
import asyncio
import json
import threading

import pytest

from episode_runtime import BindingRegistry, RunJournal, WorkCache, link, resume
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
    """A real service: whether the next tool failure is wanted; and what a tool's worker thread tells the test
    (``started``: the thread is running; ``seen``: what it saw)."""

    def __init__(self, fail=False):
        self.fail = fail
        self.started = threading.Event()
        self.seen = {}


def open_world(directory, calls='model_calls'):
    """The Store, journal, model provider and services kept below ``directory``. A second process that opens the
    same directory works on the same Store, journal and work cache (``cut_run.py``); it names a folder of its
    own for its model provider's call files (the provider makes that folder and requires it to be new)."""
    built = []
    counter, switch = Counter(), Switch()

    def make(name, value):
        def factory():
            built.append(name)
            return value
        return factory
    services = {'counter': make('counter', counter), 'switch': make('switch', switch),
                'work_cache': make('work_cache', WorkCache(directory / 'work_cache')),
                'secret': make('secret', object())}
    return {'store': Store(directory / 'store'), 'counter': counter, 'switch': switch, 'built': built,
            'services': services, 'journal': RunJournal(directory / 'journal.sqlite3'),
            'provider': ModelProvider(load_config(), directory / calls, directory), 'tmp': directory,
            'calls': directory / calls}


@pytest.fixture
def world(tmp_path):
    opened = open_world(tmp_path)
    store = opened['store']
    subject = store.artifact(json.dumps({'name': 'GeneX', 'function': 'kinase'}), 'application/json')
    unrelated = store.artifact(json.dumps({'name': 'GeneY', 'function': 'unknown'}), 'application/json')
    yield {**opened, 'subject': subject, 'unrelated': unrelated}
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


def journal_rows(world):
    """Every row of every table of the journal, by table (to show that a replay recorded nothing)."""
    db = world['journal'].db
    names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: db.execute('SELECT * FROM ' + name + ' ORDER BY rowid').fetchall() for name in names}
