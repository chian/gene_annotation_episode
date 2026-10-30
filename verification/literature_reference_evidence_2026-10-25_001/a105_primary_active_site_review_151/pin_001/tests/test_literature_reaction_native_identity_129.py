"""Primitive source identity is independent of recipes, excerpts and row order."""
from copy import deepcopy
import hashlib

from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_reaction_native_inputs import read_native_reaction_selection, VERSION
from gene_annotation_episode.literature_reaction_native_storage import publish_native_observations
from test_literature_reaction_native_inputs_129 import recipe, number, witness, declared, meanings


def rows_for(selection, raw, data_ref='source_recipe_1'):
    sources = _Sources(lambda ref, representation: {'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(), 'content': raw})
    output, trace = read_native_reaction_selection(selection, sources=sources)
    extraction = {'arguments': {'source_ref': 'source_report', 'data_source_ref': data_ref},
        'native_evidence': trace, 'observations': output, 'calculation_inputs': deepcopy(output)}
    extraction['calculation_inputs'] = {key: output[key] for key in ('ratio', 'budget')}
    records = {}
    def publish(kind, record):
        key = identity(kind, {'origin': 'tool', 'record': record})
        records[key] = record
        return key
    semantic = {'resources': [] if output['budget'] is None else [
        {'resource_ref': 'reference_' + item['resource_key']} for item in output['budget']['resources']]}
    rows = publish_native_observations(extraction, {}, semantic, publish)
    return rows, records


def test_point_identity_ignores_recipe_excerpt_and_row_position():
    raw = b'Preparation A ratio = 0.8; preparation B ratio = 0.9.'
    selection = recipe(raw)
    first, records = rows_for(selection, raw)
    small = deepcopy(selection)
    small['ratio']['summary']['value']['number'] = number(raw, '0.8', '0.8')
    second, _ = rows_for(small, raw, 'source_recipe_2')
    assert first[0]['measurement_ref'] == second[0]['measurement_ref']
    narrow = records[first[0]['measurement_ref']]['anchor']
    assert narrow['quote'] == '0.8' and narrow['end'] - narrow['start'] == 3
    reordered = deepcopy(small)
    reordered['ratio'].update(mode='independent_units', summary=None, observations=[
        {'measurement_key': 'second_private_key', 'value': {'kind': 'point', 'number': number(raw, '0.9', '0.9')}, 'basis_witnesses': []},
        {'measurement_key': 'different_first_key', 'value': small['ratio']['summary']['value'], 'basis_witnesses': []}])
    third, _ = rows_for(reordered, raw, 'source_recipe_3')
    assert third[1]['measurement_ref'] == first[0]['measurement_ref']
    assert third[0]['measurement_ref'] != third[1]['measurement_ref']


def test_author_pair_identity_is_the_exact_expression_not_surrounding_quote():
    raw = b'Products A:B reported ratio = 3:2 in this experiment.'
    selected = recipe()
    selected['ratio']['summary']['value'] = {'kind': 'reported_pair',
        'numerator': number(raw, raw.decode(), '3'), 'denominator': number(raw, raw.decode(), '2')}
    first, records = rows_for(selected, raw)
    selected['ratio']['summary']['value'] = {'kind': 'reported_pair',
        'numerator': number(raw, '3:2', '3'), 'denominator': number(raw, '3:2', '2')}
    second, _ = rows_for(selected, raw, 'source_recipe_changed')
    assert first[0]['measurement_ref'] == second[0]['measurement_ref']
    assert first[0]['source_number_refs'] == second[0]['source_number_refs']
    assert records[first[0]['measurement_ref']]['anchor']['quote'] == '3:2'


def test_resource_identity_survives_reordering_and_unit_interpretation_changes():
    raw = b'Table headings uM and umol. Supply A: 2; supply B: 3.'
    selected = {'version': VERSION, 'ratio': None, 'meanings': meanings(False), 'budget': {
        'basis': 'supplied_reagent_batch', 'unit': 'uM', 'resources_complete': False, 'demand': declared(10),
        'resources': [{'resource_key': key, 'value': {'number': number(raw, raw.decode(), token),
            'unit': witness(raw, 'uM')}, 'lower': None, 'upper': None, 'coefficient': declared(1)}
            for key, token in [('A', '2'), ('B', '3')]]}}
    first, records = rows_for(selected, raw)
    changed = deepcopy(selected)
    changed['budget']['resources'].reverse()
    changed['budget']['unit'] = 'umol'
    for item in changed['budget']['resources']:
        item['value']['unit'] = witness(raw, 'umol')
        token = '2' if item['resource_key'] == 'A' else '3'
        item['value']['number'] = number(raw, token, token)
    second, _ = rows_for(changed, raw, 'source_recipe_changed')
    assert first[0]['measurement_ref'] == second[1]['measurement_ref']
    assert first[1]['measurement_ref'] == second[0]['measurement_ref']
    assert first[0]['unit'] != second[1]['unit']
    assert records[first[0]['measurement_ref']]['anchor']['quote'] == '2'


def test_unextracted_ratio_does_not_claim_the_paper_omitted_it():
    selected = recipe()
    selected['ratio']['summary']['value'] = None
    rows, records = rows_for(selected, b'Reported ratio = 0.8.')
    assert rows[0]['ratio_form'] == 'not_extracted'
    assert rows[0]['transformation'] == 'not_extracted'
    assert records[rows[0]['measurement_ref']]['label'].startswith('Not extracted ')
