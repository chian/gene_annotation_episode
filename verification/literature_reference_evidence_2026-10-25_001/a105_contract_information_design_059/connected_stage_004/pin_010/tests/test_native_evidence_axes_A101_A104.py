"""Native axis binding/provenance checks; synthetic numbers, no jobs or models."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.evidence_axis_contracts import (
    judgment_schema, native_metric_facts, validate_axis_judgment,
    validate_evidence_axis_entry)
from gene_annotation_episode.state import Store


REPO = Path(__file__).resolve().parents[1]
PUBLICATION = REPO/'research/slotted_process_library/publications/2026-10-23-002'


def axis(name):
    return json.loads((PUBLICATION/'entries'/f'{name}.json').read_text())


@pytest.fixture
def received_alignment(tmp_path):
    with Store(tmp_path/'workspace') as store:
        subject = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs'][0]
        payload = {'meaning': 'Synthetic native-binding fixture, not a biological measurement',
                   'bitscore': 53.5, 'evalue_upper_bound': 1e-12, 'alignment_score': 27.5}
        artifact = store.artifact(json.dumps(payload), 'application/json')
        source = store.put('source', {'provider': 'synthetic.native_axis_fixture',
            'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact,
            'request_ref': None, 'version': 'engineering_fixture_only', 'retrieved_at': None}, origin='tool')
        values = [
            {'name': 'bitscore', 'value': {'type': 'number', 'value': 53.5, 'unit_ref': None}},
            {'name': 'evalue', 'value': {'type': 'number', 'value': 1e-12, 'unit_ref': None,
                                        'bound': 'less_than'}},
            {'name': 'alignment_score', 'value': {'type': 'number', 'value': 27.5, 'unit_ref': None}},
        ]
        observation = store.put('observation', {'subject_refs': [subject],
            'source_subject_refs': [subject], 'kind': 'alignment', 'source_ref': source['id'],
            'measurements': values, 'dependencies': [], 'anchor': None}, origin='tool')
        yield store, observation, source


def test_sequence_axis_copies_actual_received_numbers_and_preserves_the_native_bound(received_alignment):
    store, observation, source = received_alignment
    result = native_metric_facts(axis('A101'), store, observation_refs=[observation['id']],
        received_record_refs=[observation['id'], source['id']])
    facts = {fact['metric_id']: fact for fact in result['native_facts']}
    assert facts['bitscore']['native_value'] == observation['measurements'][0]['value']
    assert facts['evalue']['native_value'] == observation['measurements'][1]['value']
    assert facts['evalue']['native_value']['bound'] == 'less_than'
    assert facts['alignment_score']['native_value'] == observation['measurements'][2]['value']
    assert all(fact['source'] == source['id'] and fact['observation'] == observation['id']
               for fact in facts.values())
    assert all('confidence' not in fact and 'weight' not in fact for fact in facts.values())
    assert {'identity_fraction', 'query_coverage', 'comparator_coverage', 'profile_model_score'} <= {
        row['metric_id'] for row in result['unavailable']}


def test_unreceived_native_values_are_not_inherited_or_read_from_the_workspace(received_alignment):
    store, observation, _ = received_alignment
    with pytest.raises(ValueError, match='observation_not_received'):
        native_metric_facts(axis('A101'), store, observation_refs=[observation['id']], received_record_refs=[])


@pytest.mark.parametrize('axis_id', ['A102', 'A104'])
def test_unbound_native_metrics_stay_unknown_instead_of_relabeling_sequence_scores(received_alignment, axis_id):
    store, observation, _ = received_alignment
    entry = axis(axis_id)
    result = native_metric_facts(entry, store, observation_refs=[observation['id']],
        received_record_refs=[observation['id']])
    assert result['native_facts'] == []
    assert {row['metric_id'] for row in result['unavailable']} == {
        metric['metric_id'] for metric in entry['native_measurements']}
    assert all(row['reason'] == 'native_extractor_unbound' for row in result['unavailable'])


def test_neighbor_identification_scores_are_not_relabelled_as_a_genomic_context_statistic(received_alignment):
    store, observation, _ = received_alignment
    result = native_metric_facts(axis('A103'), store, observation_refs=[observation['id']],
        received_record_refs=[observation['id']])
    assert {fact['metric_id'] for fact in result['native_facts']} == {
        'neighbor_identification_bitscore', 'neighbor_identification_evalue'}
    assert {row['metric_id'] for row in result['unavailable']} == {
        metric['metric_id'] for metric in axis('A103')['native_measurements']
        if metric['binding']['kind'] == 'unbound'}


@pytest.mark.parametrize('axis_id', ['A101', 'A102', 'A103', 'A104'])
def test_axis_outputs_are_closed_judgments_and_witnesses_not_model_generated_numbers(axis_id):
    entry = validate_evidence_axis_entry(axis(axis_id))
    output = {'criteria': [{'criterion_id': row['criterion_id'], 'outcome': 'unknown',
        'witnesses': [], 'missing_inputs': [row['required_evidence'][0]]}
        for row in entry['judgment_criteria']],
        'qualitative_grades': [{'criterion_id': row['criterion_id'], 'grade': 'unknown', 'witnesses': []}
        for row in entry['qualitative_grading']],
        'evidence_chain': {key: [] for key in entry['transfer_chain']}}
    assert validate_axis_judgment(entry, output) == output
    assert 'native_facts' not in judgment_schema(entry)['properties']
    forged = deepcopy(output)
    forged['criteria'][0]['native_score'] = 100
    with pytest.raises(ValueError, match='judgment_invalid'):
        validate_axis_judgment(entry, forged)
    unsupported = deepcopy(output)
    unsupported['criteria'][0].update(outcome='met', missing_inputs=[])
    with pytest.raises(ValueError, match='requires_witnesses'):
        validate_axis_judgment(entry, unsupported)


def test_only_the_user_permitted_hgt_explanation_gets_qualitative_grading():
    for name in ('A101', 'A102', 'A103'):
        assert axis(name)['qualitative_grading'] == []
    grade, = axis('A104')['qualitative_grading']
    assert grade['kind'] == 'hgt_environment_explanation'
    assert all(set(level) == {'code', 'meaning'} for level in grade['ordered_levels'])


def test_corrected_axis_sources_retain_original_observations_limits_and_file_hashes():
    crosswalk = json.loads((PUBLICATION/'SOURCE_CROSSWALK_A101_A104.json').read_text())
    for link in crosswalk['rows']:
        path = REPO/link['original_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == link['original_file_sha256']
        index = int(link['original_pointer'].rsplit('/', 1)[1])
        original = json.loads(path.read_text())['evidence'][index]
        assert axis(link['axis_id'])['evidence'][link['evidence_index']] == original
