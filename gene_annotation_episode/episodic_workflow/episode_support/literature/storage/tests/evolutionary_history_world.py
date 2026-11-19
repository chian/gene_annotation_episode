"""What the evolutionary-history storage tests share: a real Store, run journal and model provider, the storage probe
episode, and the records a population call reads (a problem, and sources the probe holds)."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

from .evolutionary_history_probe.episode import StorageProbe

SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}
CONTINUATION = {'evolutionary_history_probe': SETTINGS}
ROOT = 'gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.'


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    target, = store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ', molecule='protein')['subject_refs']
    yield {'store': store, 'target': target, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path), 'scope': {'subject_refs': [target]}}
    store.close()


def source(world, text, media_type='text/plain', provider='test'):
    """A source record of ``text`` in the Store, as an earlier acquisition left it: its reference and its artifact's."""
    store = world['store']
    artifact = store.artifact(text, media_type)
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None},
                     origin='external')['id'], artifact


def run(world, run_id, plan, held=()):
    """Run ``plan`` (a list of ``{'tool': name, 'arguments': {...}}``) in the probe, which is passed ``held`` in
    custody; the outcome of each unit, in order."""
    registry = BindingRegistry([StorageProbe()])
    collaborators = {'store': world['store'], 'model_provider': world['provider'], 'continuation': CONTINUATION,
                     'services': {}}
    entry = {'assignment': {'input_refs': [world['target']], 'held_refs': list(held)}, 'message': {'plan': plan},
             'selection': []}
    linked = link(registry, 'evolutionary_history_probe', entry, run_id=run_id, journal=world['journal'],
                  collaborators=collaborators)
    asyncio.run(linked.run())
    return [unit[2]['outcome'] for unit in world['journal'].units(run_id, (('evolutionary_history_probe', run_id),))]


def call(repository, method, *arguments, scope, assignment=None, **keywords):
    """The plan step that runs ``method`` of ``repository`` (a class of the evolutionary-history storage) with the
    population arguments."""
    return {'tool': 'call', 'arguments': {'repository': ROOT + repository, 'method': method, 'call': list(arguments), 'keywords': keywords,
                                          'scope': scope, 'assignment': assignment or {}}}


def read(repository, method, *arguments, **keywords):
    return {'tool': 'read', 'arguments': {'repository': ROOT + repository, 'method': method,
                                          'call': list(arguments), 'keywords': keywords}}


def function(module, name, *arguments, **keywords):
    """The plan step that runs ``name`` of ``module`` (below the evolutionary-history storage) on the store."""
    return {'tool': 'function', 'arguments': {'module': ROOT + module, 'name': name, 'call': list(arguments),
                                              'keywords': keywords}}
