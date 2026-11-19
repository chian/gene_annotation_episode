"""A real held world for the A107 partner grading of this episode: a Store with the problem, a paper source, a source
of literal witnesses, an interpretation source and a retained partner selection dataset derived from the paper (the
fixtures of the library's ``test_literature_partner_storage.py``), and the reading assignment that passes all of them
in custody. Shared by the offline tests and the model-run test of this folder."""
import json

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import (
    BINDINGS)

LITERAL_TEXT = ('Subject|Partner|Experiment|Endpoint|Normalization|Reference condition|Omission condition|'
                'Addback condition|Function')
INTERPRETATION = 'Synthetic condition and measurement interpretations.'


def source(store, content, *, parents=(), text=False):
    artifact = store.artifact(content)
    return store.put('source', {'provider': 'synthetic_partner_fixture', 'accession': None, 'uri': None,
                                'artifact_ref': artifact, 'text_ref': artifact if text else None,
                                'request_ref': None, 'version': None, 'retrieved_at': None,
                                'parent_source_refs': list(parents)}, origin='caller')


def arm(role, value):
    return {'subject_ref': 'synthetic_subject', 'partner_ref': 'synthetic_partner',
            'partner_state': 'absent' if role == 'omitted' else 'present',
            'endpoint_ref': 'synthetic_product', 'normalization_ref': 'per_mg_subject',
            'unit': 'pmol/min/mg', 'conditions': {'coverage': 'complete', 'factors': [
                {'factor': 'nitrogen_source', 'level': 'glutamine', 'unit': 'identity'},
                {'factor': 'temperature', 'level': 37, 'unit': 'degC'}]},
            'measurement': {'measurement_id': 'synthetic_measurement_' + role, 'status': 'observed',
                            'value': value, 'origin': 'synthetic',
                            'spread': {'kind': 'SD', 'magnitude': 4} if role == 'reference'
                            else {'kind': 'unreported', 'magnitude': None}}}


def paper_text():
    """The paper the model reads: the partner experiment, in words and numbers."""
    return ('Partner dependence of SubjX activity. Assays of purified SubjX (per mg SubjX) measured product '
            'formation with glutamine as nitrogen source at 37 degC. With PartnerY present the rate was 100 '
            'pmol/min/mg (SD 4). Omitting PartnerY lowered it to 20 pmol/min/mg; adding PartnerY back restored '
            '90 pmol/min/mg. The selected measurements are retained in the partner selection dataset.')


def held_world(directory, *, components=True):
    """The Store and the entry input of the leaf: every source and artifact passed in custody."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    rows = {'ancestor': source(store, 'Synthetic provenance.')}
    rows['paper'] = source(store, paper_text(), parents=[rows['ancestor']['id']], text=True)
    root = rows['paper']['id']
    rows['literal'] = source(store, LITERAL_TEXT, parents=[root], text=True)
    rows['interpretation'] = source(store, INTERPRETATION, parents=[root])
    document = {'version': 'literature_partner_selection_v1', 'inputs': {
        'version': 'literature_partner_inputs_v1', 'arms': {
            role: arm(role, value) for role, value in (('reference', 100), ('omitted', 20), ('addback', 90))}}}
    rows['recipe'] = source(store, json.dumps(document), parents=[root])
    literals, offset = {}, 0
    for (literal, _), quote in zip(BINDINGS.values(), LITERAL_TEXT.split('|')):
        literals[literal] = {'source_ref': rows['literal']['id'], 'representation': 'text', 'start': offset,
                             'end': offset + len(quote)}
        offset += len(quote) + 1
    selection = {'source_ref': root, 'data_source_ref': rows['recipe']['id'], 'source_kind': 'synthetic_fixture',
                 'literals': literals,
                 'interpretation_witnesses': [{'source_ref': rows['interpretation']['id'],
                                               'representation': 'original', 'start': 0,
                                               'end': len(INTERPRETATION)}]}
    held = [*scope['subject_refs'], *(row['id'] for row in rows.values()),
            *(row['artifact_ref'] for row in rows.values())]
    page = {'version': 'page_assignment_v1', 'source_ref': root, 'representation': 'text',
            'artifact_ref': rows['paper']['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': []}
    assignment = {'version': 'reading_assignment_v1', 'page': page,
                  'selection': {'source_ref': root, 'representation': 'text', 'offset': 0, 'limit': 4000},
                  'scope': scope, 'received_record_refs': list(dict.fromkeys(held))}
    if components:
        assignment['literature_partner_components'] = ['partner_loss_fraction', 'addback_fraction']
    entry = {'assignment': assignment, 'message': {'objective': 'grade the partner experiment'}, 'selection': []}
    return store, entry, selection, rows


def collaborators(store, directory, continuation):
    return {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
            'continuation': continuation, 'services': {}}


def linked(episodes, path, entry, directory, store, run_id, continuation):
    """The linked run, its journal and its collaborators (``continuation``: the settings of every binding path)."""
    journal = RunJournal(directory / 'journal.sqlite3')
    shared = collaborators(store, directory, continuation)
    return link(BindingRegistry(episodes), path, entry, run_id=run_id, journal=journal, collaborators=shared), journal, shared
