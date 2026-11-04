"""Native-value and closed-judgment contracts; all case data are synthetic."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.evidence_axis_contracts import (
    entry_schema, judgment_schema, native_metric_facts,
    validate_axis_judgment, validate_evidence_axis_entry)
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.state import Store
from test_scientific_process_library import independent_source, write


def axis_entry():
    return {'entry_version': 'evidence_axis_entry_v1', 'id': 'A01', 'slot': 'evidence_axis',
        'name': 'Synthetic sequence evidence', 'description': 'Contract fixture, not scientific adoption.',
        'native_measurements': [
            {'metric_id': 'bit_score', 'name': 'Native bit score', 'native_field': 'bit_score',
             'observation_kinds': ['comparison'], 'units': ['bits'], 'direction': 'higher',
             'method_requirements': ['Retain actual program and database context.'],
             'comparison_limits': ['No function probability or cross-method normalization.'],
             'binding': {'kind': 'recorded_measurement', 'measurement_name': 'bitscore', 'json_pointer': None}},
            {'metric_id': 'structural_distance', 'name': 'Actual structural distance', 'native_field': None,
             'observation_kinds': ['structure_match'], 'units': ['angstrom'], 'direction': 'lower',
             'method_requirements': ['Require a real recorded structural comparison.'],
             'comparison_limits': ['No structure result exists in this fixture.'],
             'binding': {'kind': 'unbound', 'measurement_name': None, 'json_pointer': None}}],
        'judgment_criteria': [{'criterion_id': 'actual_subject',
            'question': 'Does the recorded comparison name the assigned actual query?',
            'required_metric_ids': ['bit_score'], 'required_evidence': ['query_identity'],
            'outcomes': {'met': 'The actual comparison query is the assigned subject.',
                'not_met': 'The actual comparison query is a different subject.',
                'unknown': 'The query identity is missing.'}, 'deterministic_test': None}],
        'qualitative_grading': [],
        'transfer_chain': {'source_subject': 'Retain the assayed source subject.',
            'source_property': 'Retain the actual measured source property.',
            'correspondence': 'Keep correspondence separate from characterization.',
            'target_hypothesis': 'Name the target proposition being considered.',
            'limitations': 'Retain missing data and transfer limits.'},
        'evidence': [{'case_group': 'fixture_case', 'case_id': 'fixture_record',
            'source_url': 'https://example.org/fixture', 'source_locator': 'Figure 2',
            'observation': 'The fixture records a contrast.',
            'limit': 'Engineering fixture only; no biological observation.'}]}


def judgment(witness):
    return {'criteria': [{'criterion_id': 'actual_subject', 'outcome': 'met',
        'witnesses': [witness], 'missing_inputs': []}], 'qualitative_grades': [],
        'evidence_chain': {key: [] for key in
            ('source_subject', 'source_property', 'correspondence', 'target_hypothesis', 'limitations')}}


def test_axis_contract_loads_new_slot_without_rewriting_legacy_bodies(tmp_path):
    old_source, source = tmp_path/'old', tmp_path/'current'
    independent_source(old_source)
    independent_source(source)
    old = ScientificProcessLibrary.freeze(tmp_path/'old-snapshot', source=old_source)
    original = old.reference('A01')
    index = json.loads((source/'index.json').read_text())
    for slot in index['slots']:
        if slot['slot'] == 'annotation_distinction': slot['slot'] = 'evidence_axis'
    body = axis_entry()
    for row in index['entries']:
        if row['id'] == 'A01': row.update({key: body[key] for key in ('slot', 'name', 'description')})
    write(source/'entries/A01.json', body)
    write(source/'index.json', index)
    current = ScientificProcessLibrary.freeze(tmp_path/'current-snapshot', source=source)
    assert current.reference('A01')['slot'] == 'evidence_axis'
    assert current.resolve(current.reference('A01')) == body
    assert current.search(slot='evidence_axis', query='', offset=0, limit=10)['entries']
    assert old.reference('A01') == original
    assert original['slot'] == 'annotation_distinction'
    assert old.search(slot='evidence_axis', query='', offset=0, limit=10)['entries']


def test_judge_contract_cannot_retype_scores_and_requires_actual_witnesses():
    entry, witness = axis_entry(), 'observation_' + 'a'*24
    assert validate_evidence_axis_entry(entry) == entry
    result = judgment(witness)
    assert validate_axis_judgment(entry, result, resolve_witness=lambda value: value == witness) == result
    invented = {**result, 'confidence': .9}
    assert not Draft202012Validator(judgment_schema(entry)).is_valid(invented)
    with pytest.raises(ValueError, match='witness_unavailable'):
        validate_axis_judgment(entry, result, resolve_witness=lambda _: False)
    empty = judgment(witness); empty['criteria'][0]['witnesses'] = []
    with pytest.raises(ValueError, match='requires_witnesses'):
        validate_axis_judgment(entry, empty)
    unknown = judgment(witness); unknown['criteria'][0].update(outcome='unknown', witnesses=[],
        missing_inputs=['query_identity'])
    assert validate_axis_judgment(entry, unknown) == unknown
    unknown['criteria'][0]['missing_inputs'] = []
    with pytest.raises(ValueError, match='requires_missing_inputs'):
        validate_axis_judgment(entry, unknown)


def test_host_copies_native_number_bounds_and_method_without_awarding_credit(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MK', molecule='protein')['subject_refs']
        artifact = store.artifact('{"bit_score":17.25}', 'application/json')
        source = store.put('source', {'provider': 'fixture.native', 'accession': None,
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': 'fixture_program_v1', 'retrieved_at': None}, origin='tool')
        atom = {'type': 'number', 'value': 17.25, 'unit_ref': None,
            'bound': 'greater_than', 'qualifier': 'approximate'}
        observation = store.put('observation', {'kind': 'comparison', 'subject_refs': [target],
            'source_subject_refs': [], 'source_ref': source['id'],
            'measurements': [{'name': 'bitscore', 'value': atom}], 'dependencies': [target],
            'anchor': None}, origin='tool')
        changes = store.db.total_changes
        facts = native_metric_facts(axis_entry(), store, observation_refs=[observation['id']],
            received_record_refs=[observation['id']])
        assert facts['native_facts'][0]['native_value'] == atom
        assert facts['native_facts'][0]['declared_native_unit'] == 'bits'
        assert facts['native_facts'][0]['method']['recorded_source_version'] == 'fixture_program_v1'
        assert facts['unavailable'] == [{'metric_id': 'structural_distance', 'reason': 'native_extractor_unbound'}]
        assert store.db.total_changes == changes
        with pytest.raises(ValueError, match='observation_not_received'):
            native_metric_facts(axis_entry(), store, observation_refs=[observation['id']], received_record_refs=[])


def test_unbound_is_not_a_fabricated_output_and_unknown_metric_links_are_rejected():
    entry = axis_entry()
    entry['native_measurements'][1]['binding']['json_pointer'] = '/imagined/rmsd'
    assert Draft202012Validator(entry_schema()).is_valid(entry)
    with pytest.raises(ValueError, match='unbound_metric_has_no_extractor'):
        validate_evidence_axis_entry(entry)
    entry = axis_entry(); entry['judgment_criteria'][0]['required_metric_ids'] = ['made_up_metric']
    with pytest.raises(ValueError, match='criterion_metric_unknown'):
        validate_evidence_axis_entry(entry)
