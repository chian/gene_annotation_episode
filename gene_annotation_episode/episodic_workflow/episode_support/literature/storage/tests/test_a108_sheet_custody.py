"""A108 contextual grading and main sheets through the real runner: the library functions run in a tool unit over
the custody-scoped store, on real records, and the sheets, their cells and the dependency tables they keep are rows
the Episode holds."""

from copy import deepcopy
import json

import pytest



from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_grading import COMPONENTS, CRITERIA_BY_TYPE
from .literature_world import run, step, world  # noqa: F401

def records(store):
    """The records of one synthetic contextual observation, written to the Store before the run."""
    target, = store.create_problem(raw_sequence='MARG', molecule='protein')['subject_refs']
    problem_source = store.targets()[0]['source_ref']
    term = store.put('term', {'namespace': 'synthetic_function', 'accession': 'thermal', 'label': 'thermal', 'term_type': 'family', 'source_ref': problem_source, 'anchor': None}, origin='external')['id']
    proposal = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'functional_family', 'value': {'type': 'term_ref', 'ref': term}, 'context_refs': []}, origin='reasoning')['id']
    text = 'Synthetic sample grows at 20 C; this is an engineering fixture, not biological evidence.'
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_context_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic sample', 'source_ref': source, 'attributes': [], 'related_refs': [target]}, origin='caller')['id']
    observed = store.put('reference', {'reference_type': 'literature_result', 'source_ref': source, 'accession': 'synthetic-observation', 'label': 'Synthetic thermal observation', 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [sample], 'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0, 'end': len(text), 'quote': text}}, origin='caller')['id']
    witness = {'source_ref': source, 'representation': 'original', 'start': 0, 'end': len(text), 'quote': text}
    population = {'assertion_ref': proposal, 'source_ref': source, 'target_context_ref': sample, 'target_identity': {'status': 'supported', 'support_refs': [sample]}, 'target_identity_evidence': [], 'grader_type': 'environment_temperature', 'observations': [{'original_observation_ref': observed, 'context_claim_ref': proposal, 'source_subject_ref': target, 'source_context_ref': sample, 'origin': 'recorded_sample_condition', 'target_relationship': 'direct', 'relation': 'support', 'criteria': {name: {'status': 'supported', 'support_refs': [observed]} for name in CRITERIA_BY_TYPE['environment_temperature']}, 'qualifications': ['Synthetic applicability is stipulated.'], 'evidence': [{'kind': 'literature_passage', 'witness': witness}], 'origin_link_evidence': []}]}
    held = [target, term, proposal, artifact, source, sample, observed, problem_source]
    return {'scope': {'subject_refs': [target]}, 'population': population, 'held': held, 'target': target}


@pytest.mark.parametrize('requested', [True, False])
def test_a_saved_context_grading_updates_the_main_sheet_even_without_requested_cells(world, requested):
    fixture = records(world['store'])
    scope, population = fixture['scope'], fixture['population']
    names = list(COMPONENTS) if requested else []
    changed = deepcopy(population)
    changed['observations'][0]['relation'] = 'conflict'
    common = dict(scope=scope, requested=names)
    result, units = run(world, 'publication', [
        step('grade', population=population, **common), step('look', **common),
        step('grade', population=changed, **common), step('look', **common)], fixture['held'])
    assert len(units) >= 4
    first, before, second, after = (unit['outcome'] for unit in units[:4])
    sheet = first['outcome']['result']['sheet_ref']
    assert first['outcome']['status'] in ('completed', 'partial')
    # The saved sheet is a record the unit produced; its operation and its cells are rows the unit wrote.
    assert sheet in units[0]['produced']
    rows = [ref for ref in units[0]['produced'] if ref.startswith('row_')]
    assert rows
    assert before['grading_sheets'] == [sheet] and before['owns'] == [True]
    assert before['grading_cells'] == names
    # The main sheet was made and updated by the saved grading, with no cell requested of the grading itself.
    current, = before['current']
    assert current['support_count'] == 1 and current['conflict_count'] == 0
    assert [family[2] for family in before['dependencies']] == ['current', 'current']
    assert before['main_saved'][current['sheet_ref']]['support_count'] == 1
    # The correction becomes the current version; the first stays readable as it was saved.
    new, = after['current']
    assert new['sheet_ref'] in second['outcome']['record_refs']
    assert new['support_count'] == 0 and new['conflict_count'] == 1
    assert after['main_saved'][current['sheet_ref']]['support_count'] == 1
    assert new['observation_sets']['conflict'] == current['observation_sets']['support']
    assert after['grading_sheets'] == [sheet, second['outcome']['result']['sheet_ref']]


@pytest.mark.parametrize('missing', ['target_identity', 'criterion'])
def test_a_missing_context_operand_saves_a_partial_original_observation(world, missing):
    fixture = records(world['store'])
    population = deepcopy(fixture['population'])
    observation = population['observations'][0]
    qualification = 'Actual source condition retained; transfer remains unresolved.'
    observation['qualifications'] = [qualification]
    if missing == 'target_identity':
        population['target_identity'] = {'status': 'unknown', 'support_refs': []}
    else:
        criterion = next(iter(observation['criteria']))
        observation['criteria'][criterion] = {'status': 'unknown', 'support_refs': []}
    common = dict(scope=fixture['scope'], requested=[])
    _, units = run(world, 'unresolved', [step('grade', population=population, **common), step('look', **common)],
                   fixture['held'])
    sheet = units[0]['outcome']['outcome']['result']['sheet_ref']
    cells = units[1]['outcome']['saved'][sheet]
    assert cells['support_count']['value'] == 0 and cells['evidence_amount']['value'] == 0
    assert cells['unresolved_count']['value'] == 1 and cells['unresolved_count']['status'] == 'partial'
    # The cells were not requested, and no cell row was written for the parent to be given.
    assert units[1]['outcome']['grading_cells'] == []


def test_another_episode_holds_the_cells_it_was_given_and_does_not_own_the_sheet(world):
    fixture = records(world['store'])
    common = dict(scope=fixture['scope'], requested=['evidence_amount'])
    _, units = run(world, 'owner', [step('grade', population=fixture['population'], **common), step('look', **common)],
                   fixture['held'])
    sheet = units[0]['outcome']['outcome']['result']['sheet_ref']
    cell_row = units[1]['outcome']['grading_cell_rows']
    assert len(cell_row) == 1 and cell_row[0] in units[0]['produced']
    _, received = run(world, 'receiver', [step('foreign', sheet_ref=sheet, components=['evidence_amount'], **common)],
                      [*fixture['held'], *cell_row])
    seen = received[0]['outcome']
    assert seen['owns'] is False
    assert [cell['component'] for cell in seen['facts']] == ['evidence_amount'] == [cell['component'] for cell in seen['received']]
    assert seen['facts'][0]['sheet_ref'] == sheet and seen['facts'][0]['value'] == 1
