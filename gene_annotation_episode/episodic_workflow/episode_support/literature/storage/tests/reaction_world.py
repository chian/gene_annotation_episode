"""A held world for the A110 literature reaction grading: a Store with the problem, a short reaction paper, the
retained ``a110_source_reaction_measurements_v1`` dataset of its numbers, a source of literal witnesses and an
interpretation source (the fixtures of the old ``root/a110/tests/test_literature_reaction_storage.py`` at
``97308b94c``), the entry assignment that passes all of them in custody and the population arguments the model
would select (literal witnesses as source locations). Real records; nothing is faked."""
import json

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_population_contracts import (
    BINDINGS)

TEXT = 'Molecule|Construct|Experiment|Product numerator|Product denominator|Endpoint|Condition|Resource context'
PAPER = ('Methods: two independent enzyme preparations (prep1, prep2) of the synthetic oxidase were assayed. '
         'Results: the measured product-pair ratio was 0.7 and 0.9 mol/mol. The proposed reaction predicts 1.0 '
         'mol/mol; the named alternative (half) predicts 0.5 mol/mol. Usable resources: resource1 12 umol and '
         'resource2 6 umol, each consumed once per product; the demand is 10 umol. The numbers are retained in the '
         'attached measurement dataset.')


def source(store, text, parents=(), alias=False):
    artifact = store.artifact(text)
    return store.put('source', {'provider': 'synthetic_reaction_fixture', 'accession': None, 'uri': None,
                                'artifact_ref': artifact, 'text_ref': artifact if alias else None,
                                'request_ref': None, 'version': None, 'retrieved_at': None,
                                'parent_source_refs': list(parents)}, origin='caller')


def dataset():
    """The old fixture's v1 dataset: two independent ratio units, one named alternative, a complete budget."""
    ratio = {'mode': 'independent_units', 'ratio_kind': 'product_pair', 'unit': 'mol_per_mol', 'origin': 'synthetic',
             'observations': [{'measurement_key': 'prep1', 'value': .7}, {'measurement_key': 'prep2', 'value': .9}],
             'mean': None, 'sample_sd': None, 'independent_n': None, 'claim': 1,
             'alternatives': [{'key': 'half', 'prediction': .5}]}
    return {'version': 'a110_source_reaction_measurements_v1', 'ratio': ratio,
            'budget': {'basis': 'usable_batch', 'unit': 'umol', 'origin': 'synthetic', 'resources_complete': True,
                       'resources': [{'resource_key': 'resource1', 'value': 12, 'lower': 12, 'upper': 12,
                                      'coefficient': 1},
                                     {'resource_key': 'resource2', 'value': 6, 'lower': 6, 'upper': 6,
                                      'coefficient': 1}],
                       'demand': 10}}


def held_world(directory, requested=None, selection='window'):
    """The Store with the problem, the sources and their artifacts; the entry input passing all of them; the
    population arguments the model would select (literal witnesses as source locations). ``selection`` is the
    shape of the reading the leaf declares: one ``window`` or ``spans``."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    provenance = source(store, 'Synthetic retained source provenance.')
    paper = source(store, PAPER, parents=[provenance['id']])
    data = source(store, json.dumps(dataset()), parents=[paper['id']])
    literal = source(store, TEXT, parents=[paper['id']], alias=True)
    interpretation = source(store, 'Synthetic physical meaning of the numerical panel.', parents=[paper['id']])
    literals, offset = {}, 0
    for field, quote in zip((name for name, _ in BINDINGS.values()), TEXT.split('|')):
        literals[field] = {'source_ref': literal['id'], 'representation': 'original', 'start': offset,
                           'end': offset + len(quote)}
        offset += len(quote) + 1
    length = len('Synthetic physical meaning of the numerical panel.')
    arguments = {'source_ref': paper['id'], 'data_source_ref': data['id'], 'source_kind': 'synthetic_fixture',
                 'literals': literals, 'interpretation_witnesses': [{'source_ref': interpretation['id'],
                                                                     'representation': 'original', 'start': 0,
                                                                     'end': length}]}
    sources = (provenance, paper, data, literal, interpretation)
    held = [*scope['subject_refs'], *(row['id'] for row in sources), *(row['artifact_ref'] for row in sources)]
    page = {'version': 'page_assignment_v1', 'source_ref': paper['id'], 'representation': 'original',
            'artifact_ref': paper['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': []}
    window = {'source_ref': paper['id'], 'representation': 'original', 'offset': 0, 'limit': len(PAPER.encode())}
    assignment = {'version': 'reading_assignment_v1', 'page': page,
                  'selection': window if selection == 'window' else {'spans': [window]},
                  'scope': scope, 'finding_unit': 1.0, 'received_record_refs': list(dict.fromkeys(held))}
    if requested is not None:
        assignment['requested_reaction_components'] = requested
    entry = {'assignment': assignment, 'message': {'objective': 'read'}, 'selection': []}
    return store, entry, arguments, paper


