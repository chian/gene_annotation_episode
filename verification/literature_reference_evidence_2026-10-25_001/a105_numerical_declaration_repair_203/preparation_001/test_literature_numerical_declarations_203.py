"""Controlled declaration/custody checks; no paper or actual model execution."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import interpretation_schema, validate_closed_schema
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_contract_information import ContractInformationError, validate_saved_fact_form
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode import literature_numerical_contracts as contracts
from gene_annotation_episode.schema_information_text import schema_fingerprint


QUALIFICATION = {'type': 'string', 'enum': ['unknown', 'qualified']}


def all_facts():
    binding = LiteratureEpisodes(None, rate_population=True,
        channel_population=True, compiled_assay_population=True,
        ion_discrimination_population=True, completion_time_population=True,
        product_partition_population=True, active_site_population=True,
        ratio_source_population=True, controlled_response_population=True, gel_population=True)
    return binding.fact_sources('literature')


def frozen(facts=None):
    facts = all_facts() if facts is None else facts
    # A second literal source tests that aliases do not change ordinary recorded
    # value-type declarations or accidentally grant a nonnumerical alias.
    facts = {**facts, 'credit': {'type': 'number', 'meaning': 'Original scalar credit.'},
        'caller_status': {'type': 'boolean', 'meaning': 'Original caller status.'}}
    action_schema = obj({'fixture': {'type': 'boolean'}})
    record = contracts.freeze_contracts(facts_by_role={'literature': facts},
        permitted_child_roles=['literature'], action_schema=action_schema)
    return {contracts.SAVED_MEMBER: record, 'schema': action_schema}


@pytest.mark.parametrize('source', contracts.registered_sources())
def test_catalog_matches_actual_bound_complete_host_type_and_preserves_interpretations(source):
    facts = all_facts()
    original = deepcopy(facts[source])
    assert contracts.registered_schema(source) == original['report_schema']
    assert contracts.is_registered_schema(original['report_schema'], source=source)
    submitted = obj({'selected': {'$ref': 'episode-fact:' + source}, 'qualification': QUALIFICATION})
    text = json.dumps(submitted, indent=1)
    saved = frozen({source: original})
    result = contracts.expand_numerical_form(text, child_role='literature', saved=saved)
    expected = obj({'selected': original['report_schema'], 'qualification': QUALIFICATION})
    assert result['expanded_schema'] == expected
    assert validate_closed_schema(expected) == expected
    assert interpretation_schema(expected) == obj({'qualification': QUALIFICATION})
    assert validate_saved_fact_form(child_role='literature', submitted_schema_json=text,
        expanded_schema=expected, declaration=result['declaration']) == expected
    assert result['declaration']['submitted_schema_json'] == text
    assert facts[source] == original


def test_snapshot_preserves_original_source_types_without_other_axis_sheets_or_aliases():
    saved = frozen()
    record = contracts.validate_frozen_contracts(saved)
    assert record['source_types_by_role']['literature']['credit'] == {'type': 'number'}
    assert record['source_types_by_role']['literature']['caller_status'] == {'type': 'boolean'}
    assert set(record['fact_sources_by_role']['literature']) == set(contracts.registered_sources())
    assert 'literature_perturbation_cells' in record['source_types_by_role']['literature']
    assert 'literature_perturbation_cells' not in record['fact_sources_by_role']['literature']
    for source in ('credit', 'caller_status', 'literature_perturbation_cells', 'absent_source'):
        with pytest.raises(ContractInformationError, match='return_contract_not_available'):
            contracts.expand_numerical_form(json.dumps(obj({'chosen': {'$ref': 'episode-fact:' + source}})),
                child_role='literature', saved=saved)


@pytest.mark.parametrize('schema', [
    obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells', 'description': 'override'}}),
    obj({'numbers': {'type': 'array', 'items': {'$ref': 'episode-fact:literature_kinetic_cells'}}}),
    obj({'numbers': {'$ref': 'https://invalid.example/schema'}}),
    obj({'numbers': {'$dynamicRef': 'episode-fact:literature_kinetic_cells'}}),
])
def test_reference_overrides_nested_external_and_dynamic_references_are_rejected(schema):
    with pytest.raises(ContractInformationError, match='unsupported_form_reference'):
        contracts.expand_numerical_form(json.dumps(schema), child_role='literature', saved=frozen())


def test_wrong_role_cannot_use_available_source_and_modified_type_gets_no_alias():
    with pytest.raises(ContractInformationError, match='return_child_role_not_available'):
        contracts.expand_numerical_form(json.dumps(obj({'numbers': {
            '$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature_strategy', saved=frozen())
    facts = all_facts()
    facts['literature_kinetic_cells']['report_schema']['items']['properties']['value']['minimum'] = 0
    assert not contracts.is_registered_schema(facts['literature_kinetic_cells']['report_schema'])
    saved = frozen(facts)
    assert 'literature_kinetic_cells' not in saved[contracts.SAVED_MEMBER]['fact_sources_by_role']['literature']
    with pytest.raises(ContractInformationError, match='return_contract_not_available'):
        contracts.expand_numerical_form(json.dumps(obj({'numbers': {
            '$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature', saved=saved)


def test_saved_expansion_uses_original_snapshot_with_fact_factories_blocked(monkeypatch):
    saved = frozen()
    before = deepcopy(saved)
    def forbidden(*_args, **_kwargs):
        raise AssertionError('Original frozen declarations must not reload current factories')
    monkeypatch.setattr(contracts, 'registered_schema', forbidden)
    result = contracts.expand_numerical_form(json.dumps(obj({'numbers': {
        '$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature', saved=saved)
    assert result['expanded_schema']['properties']['numbers'] == saved[contracts.SAVED_MEMBER][
        'fact_sources_by_role']['literature']['literature_kinetic_cells']['report_schema']
    assert saved == before


@pytest.mark.parametrize('location', ['schema', 'fact_source', 'source_type', 'roles'])
def test_original_snapshot_associations_reject_tamper(location):
    saved = frozen()
    if location == 'schema':
        saved['schema']['properties']['fixture']['type'] = 'integer'
    elif location == 'fact_source':
        saved[contracts.SAVED_MEMBER]['fact_sources_by_role']['literature'][
            'literature_kinetic_cells']['report_schema']['x-source'] = 'literature_binding_cells'
    elif location == 'source_type':
        saved[contracts.SAVED_MEMBER]['source_types_by_role']['literature']['credit']['type'] = 'array'
    else:
        saved[contracts.SAVED_MEMBER]['permitted_child_roles'].append('invented_role')
    with pytest.raises(ContractInformationError, match='original_literature_numerical'):
        contracts.validate_frozen_contracts(saved)


def test_even_rehashed_wrong_source_relationship_is_rejected_without_fact_factory():
    saved = frozen()
    record = saved[contracts.SAVED_MEMBER]
    record['fact_sources_by_role']['literature']['literature_kinetic_cells']['report_schema'][
        'x-source'] = 'literature_binding_cells'
    record['fact_sources_sha256'] = schema_fingerprint(record['fact_sources_by_role'])
    with pytest.raises(ContractInformationError, match='original_literature_numerical_fact_mismatch'):
        contracts.validate_frozen_contracts(saved)
