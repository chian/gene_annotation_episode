"""Parent-chosen UniProt fields expand into the existing saved form contract."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import uniprot_return_contracts as contracts
from gene_annotation_episode.episode_contract_information import (
    ContractInformationError, expand_fact_form, validate_saved_fact_form,
)


SOURCE = 'uniprot_selected_returns'
PARAMETER = 'x-uniprot-selection'


def selection():
    return {'version': 'uniprot_return_selection_v1', 'pages': [{
        'publication': {'mode': 'assigned_page'}, 'page_fields': [],
        'records': [{'record': {'mode': 'primary_accession', 'accession': 'P0AAW1'},
            'grant_sequence_artifact': False,
            'fields': [{'kind': 'integer', 'field': 'observed_sequence_length'},
                       {'kind': 'sequence_window', 'start': 9, 'end': 19}]}],
        'grant_source': False}]}


def form(field):
    return {'type': 'object', 'properties': {'chosen_information': field},
            'required': ['chosen_information'], 'additionalProperties': False}


def expand(submitted, *, facts=None, role='results', permitted=('results',)):
    return expand_fact_form(json.dumps(submitted), child_role=role,
        facts_by_role={role: contracts.uniprot_fact_sources() if facts is None else facts},
        permitted_child_roles=permitted)


def test_selected_form_expands_exactly_and_replays_without_current_advertisement(monkeypatch):
    chosen = selection()
    submitted = form({'$ref': 'episode-fact:' + SOURCE, PARAMETER: chosen})
    original = deepcopy(submitted)
    result = expand(submitted)
    assert result['expanded_schema']['properties']['chosen_information'] == (
        contracts.uniprot_selected_return_schema(chosen))
    assert submitted == original
    assert result['declaration']['submitted_schema_json'] == json.dumps(submitted)

    def no_current_advertisement():
        raise AssertionError('saved forms must not consult current advertisements')

    monkeypatch.setattr(contracts, 'uniprot_fact_sources', no_current_advertisement)
    assert validate_saved_fact_form(child_role='results',
        submitted_schema_json=json.dumps(submitted),
        expanded_schema=result['expanded_schema'], declaration=result['declaration']) == (
            result['expanded_schema'])


def test_changed_selection_cannot_reuse_a_saved_expanded_form():
    submitted = form({'$ref': 'episode-fact:' + SOURCE, PARAMETER: selection()})
    result = expand(submitted)
    changed = deepcopy(submitted)
    changed['properties']['chosen_information'][PARAMETER]['pages'][0]['records'][0]['fields'][1]['start'] = 10
    declaration = {**result['declaration'], 'submitted_schema_json': json.dumps(changed)}
    with pytest.raises(ContractInformationError, match='saved_fact_selection_mismatch'):
        validate_saved_fact_form(child_role='results', submitted_schema_json=json.dumps(changed),
            expanded_schema=result['expanded_schema'], declaration=declaration)


def test_selected_form_requires_available_role_source_and_original_base():
    submitted = form({'$ref': 'episode-fact:' + SOURCE, PARAMETER: selection()})
    with pytest.raises(ContractInformationError, match='return_contract_not_available'):
        expand(submitted, facts={})
    with pytest.raises(ContractInformationError, match='return_child_role_not_available'):
        expand(submitted, permitted=())
    changed = contracts.uniprot_fact_sources()
    changed[SOURCE]['report_schema']['description'] = 'altered frozen advertisement'
    with pytest.raises(ContractInformationError, match='selected_fact_base_schema_mismatch'):
        expand(submitted, facts=changed)


@pytest.mark.parametrize('field', [
    {'$ref': 'episode-fact:execution_result_refs', PARAMETER: selection()},
    {'$ref': 'episode-fact:' + SOURCE, PARAMETER: selection(), 'extra': True},
    {'$dynamicRef': 'episode-fact:' + SOURCE, PARAMETER: selection()},
    {'$ref': 'https://example.invalid/source', PARAMETER: selection()},
    {'type': 'array', 'items': {'$ref': 'episode-fact:' + SOURCE, PARAMETER: selection()}},
])
def test_selected_shorthand_does_not_relax_other_reference_grammar(field):
    with pytest.raises(ContractInformationError, match='unsupported_form_reference'):
        expand(form(field))


def test_malformed_selection_is_a_typed_contract_error():
    with pytest.raises(ContractInformationError, match='invalid_fact_selection'):
        expand(form({'$ref': 'episode-fact:' + SOURCE, PARAMETER: None}))


def test_unparameterized_and_literal_forms_keep_their_meanings():
    empty = contracts.uniprot_fact_sources()[SOURCE]['report_schema']
    assert expand(form({'$ref': 'episode-fact:' + SOURCE}))['expanded_schema'] == form(empty)
    literal = form(contracts.uniprot_selected_return_schema(selection()))
    result = expand(literal)
    assert result['expanded_schema'] == literal
    assert result['declaration']['fact_references'] == []
