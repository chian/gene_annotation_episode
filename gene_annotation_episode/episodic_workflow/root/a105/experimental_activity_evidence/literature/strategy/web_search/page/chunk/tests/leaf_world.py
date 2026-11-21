"""A real world for the extraction leaf: a Store with a source whose artifact holds a text, a proposed annotation
(a hypothesis), the entry input that passes the source and its artifact in custody and names the chunk (a window of
bytes of that text), and the run's collaborators (real runner, journal, Store, model provider)."""
import importlib

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}


def held_world(directory, text, offset, length, name='world', experiment_type='spr'):
    """``text`` is the source's text; the chunk is ``length`` bytes of it from byte ``offset``."""
    directory = directory / name
    directory.mkdir()
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    target = store.problem()['subject_refs'][0]
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_a105_text', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'binding', 'label': 'Binding',
                                  'term_type': 'reaction', 'source_ref': source, 'anchor': None},
                         origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'binds',
                                        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []},
                         origin='reasoning')['id']
    assignment = {'source_ref': source, 'passed_refs': [source, artifact], 'offset': offset, 'limit': length,
                  'experiment_type': experiment_type, 'proposed_annotation_ref': proposed}
    return {'directory': directory, 'store': store, 'source': source, 'artifact': artifact, 'proposed': proposed,
            'input': {'assignment': assignment, 'message': {}, 'selection': ['record_refs']}}


def collaborators(world, model_calls='model_calls'):
    return {'store': world['store'],
            'model_provider': ModelProvider(load_config(), world['directory'] / model_calls, world['directory']),
            'continuation': {PATH: SETTINGS}, 'services': {}}


def linked(world, run_id, journal=None):
    return link(BindingRegistry([EPISODE()]), PATH, world['input'], run_id=run_id,
                journal=journal or RunJournal(world['directory'] / 'journal.sqlite3'),
                collaborators=collaborators(world))


def resumed(world, run_id, journal):
    return resume(BindingRegistry([EPISODE()]), run_id=run_id, journal=journal,
                  collaborators=collaborators(world, 'model_calls_resumed'))
