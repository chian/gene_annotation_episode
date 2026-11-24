"""The real records of an A106 leaf run of this episode: a Store with the problem, one paper source whose text is the
library's constructed perturbation summary (``test_literature_perturbation_source.TEXT``: engineering data, not biology),
followed by a second chunk that reports nothing, the proposed annotation (a hypothesis), all passed in custody by the entry
assignment. The answer a model would give is the library's constructed arguments with every witness reduced to its quotation.
Nothing is faked: the records are written to a real Store and read through the real runner's custody."""
from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence.tests.test_literature_perturbation_source import (
    TEXT, arguments)

SECOND = b' The second chunk reports no perturbation experiment.'
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'literature_populations': [],
            'literature_evidence_origins': {}}


def quotations(value):
    """``value`` with every witness (an object with a quote and its place) reduced to the quotation."""
    if isinstance(value, list):
        return [quotations(item) for item in value]
    if isinstance(value, dict):
        if 'quote' in value and 'start' in value:
            return {'quote': value['quote']}
        return {key: quotations(child) for key, child in value.items()}
    return value


def answer():
    """What a model answers for the first chunk: the form of the library's constructed arguments, quotations only."""
    form = quotations(arguments())
    for name in ('source_ref', 'source_kind', 'data_source_ref'):
        del form[name]
    return form


def silent_answer():
    """An answer for the second chunk, which reports no experiment: nothing stated, only the unit it can quote."""
    form = answer()
    form['literals'] = dict.fromkeys(form['literals'])
    form.update(design='unknown', measurement_status='unknown', same_endpoint_scope='unknown', amount_role='unknown',
                orientation=None, interpretation_witnesses=[])
    form['source_measurements'] = {'endpoint_unit': {'quote': 'chunk'}, 'exposure_unit': None,
                                   'measurements': dict.fromkeys(form['source_measurements']['measurements'])}
    return form


def held_world(directory, task_kind='verified_source_leads', chunks=2):
    """The Store and the entry input of a leaf commissioned with ``chunks`` chunks of the source (1 or 2)."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    artifact = store.artifact(TEXT + SECOND, 'text/plain')
    source = store.put('source', {'provider': 'constructed_perturbation_summary', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']
    subject = store.put('reference', {'reference_type': 'assay', 'source_ref': source, 'accession': 'constructed_a106',
                                      'label': 'Constructed assay', 'sequence_ref': None, 'molecule': None,
                                      'length': None, 'term_refs': [], 'context_refs': []}, origin='caller')['id']
    term = store.put('term', {'namespace': 'synthetic', 'accession': 'reaction_a106', 'label': 'Synthetic reaction',
                              'term_type': 'reaction', 'source_ref': source, 'anchor': None}, origin='caller')['id']
    assertion = store.put('hypothesis', {'subject_refs': [subject], 'predicate': 'catalyzes',
                                         'value': {'type': 'term_ref', 'ref': term}, 'context_refs': []},
                          origin='reasoning')['id']
    held = [*scope['subject_refs'], source, artifact, subject, term, assertion]
    page = {'version': 'page_assignment', 'source_ref': source, 'representation': 'original',
            'artifact_ref': artifact, 'question_context_refs': [subject, assertion], 'prior_delivery_refs': []}
    task = {'version': 'literature_local_task', 'evidence_axis': 'A106', 'kind': task_kind, 'credit_unit': 1.0}
    spans = [{'source_ref': source, 'representation': 'original', 'offset': 0, 'limit': len(TEXT)},
             {'source_ref': source, 'representation': 'original', 'offset': len(TEXT) + 1,
              'limit': len(SECOND) - 1}][:chunks]
    assignment = {'version': 'reading_assignment', 'page': page, 'selection': {'spans': spans},
                  'literature_task': task, 'proposed_annotation_ref': assertion, 'scope': scope,
                  'received_record_refs': held}
    entry = {'assignment': assignment, 'message': {'objective': 'extract the perturbation experiment'},
             'selection': []}
    names = {'source': source, 'artifact': artifact, 'assertion': assertion, 'scope': scope, 'spans': spans}
    return store, entry, names


def linked_run(directory, episodes, path, entry, store, run_id, settings):
    """The real runner over the real Store, journal and model provider."""
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls',
                                                                    directory),
                     'continuation': settings, 'services': {}}
    journal = RunJournal(directory / 'journal.sqlite3')
    return link(BindingRegistry(episodes), path, entry, run_id=run_id, journal=journal,
                collaborators=collaborators), journal, collaborators
