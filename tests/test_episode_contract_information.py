"""Frozen contract lookup and saved-only form relationships, without custody claims."""
from copy import deepcopy
import json
from types import MappingProxyType

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_contract_information import (
    ContractInformationError, expand_fact_form, operation_contract_information,
    return_contract_information, validate_saved_fact_form)
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.schema_information_text import parse_schema_information, schema_fingerprint


OPERATIONS = _population_catalog()
FACTS = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def fixture(*, already_bound=False):
    schema = {'type': 'array', 'items': {'type': 'number'}, 'minItems': 0, 'uniqueItems': True}
    if already_bound:
        schema['x-source'] = 'measured_values'
    facts = {'literature': {'measured_values': {'type': 'array', 'meaning': 'Saved selected numerical values.', 'report_schema': schema}}}
    form = obj({'my_numbers': {'$ref': 'episode-fact:measured_values'},
                'qualification': {'type': 'string', 'enum': ['unknown', 'supported']}})
    return facts, encode(form)


def expanded_fixture(*, already_bound=False):
    facts, submitted = fixture(already_bound=already_bound)
    result = expand_fact_form(submitted, child_role='literature', facts_by_role=facts, permitted_child_roles=['literature'])
    return facts, submitted, result


def validate(submitted, result):
    return validate_saved_fact_form(child_role='literature', submitted_schema_json=submitted,
        expanded_schema=result['expanded_schema'], declaration=result['declaration'])


@pytest.mark.parametrize('row', OPERATIONS, ids=[row['name'] for row in OPERATIONS])
def test_actual_operations_return_exact_supplied_contracts_as_information_only(row):
    outcome = operation_contract_information(catalog=OPERATIONS, operation=row['name'])
    assert set(outcome) == {'status', 'record_refs', 'changed_record_refs', 'result', 'feedback'}
    assert outcome['status'] == 'completed' and outcome['feedback'] is None
    assert outcome['record_refs'] == outcome['changed_record_refs'] == []
    result = outcome['result']
    assert set(result) == {'information_kind', 'operation', 'meaning', 'input_schema', 'schema_sha256', 'text'}
    assert result['meaning'] == row['description']
    assert result['input_schema'] == row['input_schema']
    assert parse_schema_information(result['text']) == row['input_schema']
    assert result['schema_sha256'] == schema_fingerprint(row['input_schema'])
    assert result['schema_sha256'] not in result['text']


@pytest.mark.parametrize('source', FACTS, ids=list(FACTS))
def test_actual_fact_contracts_are_exact_and_role_scoped(source):
    outcome = return_contract_information(facts_by_role={'literature': FACTS}, permitted_child_roles=['literature'],
        role='literature', source=source)
    assert outcome['status'] == 'completed'
    result = outcome['result']
    assert set(result) == {'information_kind', 'role', 'source', 'meaning', 'report_schema', 'schema_sha256', 'text'}
    assert result['report_schema'] == FACTS[source]['report_schema']
    assert result['meaning'] == FACTS[source]['meaning']
    assert parse_schema_information(result['text']) == FACTS[source]['report_schema']


def test_unknown_operations_and_unpermitted_roles_do_not_return_other_contracts():
    unavailable = operation_contract_information(catalog=OPERATIONS, operation='unknown.operation')
    assert unavailable == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
        'feedback': {'category': 'decision_exchange', 'code': 'operation_contract_not_available'}}
    blocked = return_contract_information(facts_by_role={'literature': FACTS}, permitted_child_roles=[],
        role='literature', source=next(iter(FACTS)))
    assert blocked['result'] is None and blocked['feedback']['code'] == 'return_child_role_not_available'
    absent = return_contract_information(facts_by_role={'literature': FACTS}, permitted_child_roles=['literature'],
        role='literature', source='unknown_source')
    assert absent['result'] is None and absent['feedback']['code'] == 'return_contract_not_available'


def test_duplicate_catalog_names_are_an_error_instead_of_first_match_fallback():
    with pytest.raises(ContractInformationError, match='duplicate_catalog_operation'):
        operation_contract_information(catalog=[OPERATIONS[0], OPERATIONS[0]], operation=OPERATIONS[0]['name'])


@pytest.mark.parametrize('catalog', [None, {}, [{'name': 'op', 'description': None, 'input_schema': {}}],
    [{'name': 'op', 'description': 'Explicit', 'input_schema': []}]])
def test_invalid_catalog_shapes_are_rejected(catalog):
    with pytest.raises(ContractInformationError):
        operation_contract_information(catalog=catalog, operation='op')


def test_detached_information_preserves_frozen_input_and_unknown_schema_keywords():
    schema = {'type': 'object', 'vendor_unknown': {'const': {'name': 'Definition1'}}}
    catalog = (MappingProxyType({'name': 'op', 'description': 'Exact meaning.', 'input_schema': schema,
                                'private_host_annotation': 'not a returned field'}),)
    result = operation_contract_information(catalog=catalog, operation='op')['result']
    result['input_schema']['vendor_unknown']['const']['name'] = 'changed'
    assert schema['vendor_unknown']['const']['name'] == 'Definition1'
    assert 'private_host_annotation' not in result
    assert 'private_host_annotation' not in result['text']


@pytest.mark.parametrize('source', FACTS, ids=list(FACTS))
def test_every_actual_fact_reference_expands_to_the_same_closed_original_type(source):
    submitted = encode(obj({'chosen_field': {'$ref': 'episode-fact:' + source}}))
    result = expand_fact_form(submitted, child_role='literature', facts_by_role={'literature': FACTS},
        permitted_child_roles=['literature'])
    expected = deepcopy(FACTS[source]['report_schema'])
    expected['x-source'] = source
    assert result['expanded_schema']['properties']['chosen_field'] == expected
    assert validate_closed_schema(result['expanded_schema']) == result['expanded_schema']
    assert validate(submitted, result) == result['expanded_schema']


@pytest.mark.parametrize('already_bound', [False, True])
def test_mixed_form_expansion_preserves_literal_fields_and_records_original_selector_state(already_bound):
    facts, submitted, result = expanded_fixture(already_bound=already_bound)
    assert result['expanded_schema']['properties']['qualification'] == {'type': 'string', 'enum': ['unknown', 'supported']}
    assert result['declaration']['submitted_schema_json'] == submitted
    assert result['declaration']['fact_references'] == [{'field': 'my_numbers', 'source': 'measured_values',
        'schema_sha256': schema_fingerprint(facts['literature']['measured_values']['report_schema']),
        'source_had_x_source': already_bound}]
    assert validate(submitted, result) == result['expanded_schema']
    result['expanded_schema']['properties']['my_numbers']['items']['type'] = 'integer'
    assert facts['literature']['measured_values']['report_schema']['items']['type'] == 'number'


def test_parent_can_name_return_fields_without_outer_schema_bookkeeping():
    facts, _ = fixture()
    submitted = encode({'properties': {
        'my_numbers': {'$ref': 'episode-fact:measured_values'},
        'qualification': {'type': 'string', 'enum': ['unknown', 'supported']}}})
    result = expand_fact_form(submitted, child_role='literature', facts_by_role=facts,
        permitted_child_roles=['literature'])
    schema = result['expanded_schema']
    assert schema['type'] == 'object'
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])
    assert validate(submitted, result) == schema
    for conflicting in ({'type': 'array'}, {'additionalProperties': True},
                        {'required': ['qualification']}):
        with pytest.raises(ContractInformationError):
            expand_fact_form(encode({'properties': {'my_numbers': {
                '$ref': 'episode-fact:measured_values'}, 'qualification': {
                'type': 'string', 'enum': ['unknown', 'supported']}}, **conflicting}),
                child_role='literature', facts_by_role=facts,
                permitted_child_roles=['literature'])


def test_two_parent_named_fields_for_one_source_are_distinct_detached_copies():
    facts, _ = fixture()
    submitted = encode(obj({'first': {'$ref': 'episode-fact:measured_values'}, 'second': {'$ref': 'episode-fact:measured_values'}}))
    result = expand_fact_form(submitted, child_role='literature', facts_by_role=facts, permitted_child_roles=['literature'])
    assert len(result['declaration']['fact_references']) == 2
    assert validate(submitted, result) == result['expanded_schema']
    result['expanded_schema']['properties']['first']['items']['type'] = 'integer'
    assert result['expanded_schema']['properties']['second']['items']['type'] == 'number'


def test_fully_literal_forms_keep_all_constraints_and_need_no_fact_definitions():
    form = obj({'answer': {'type': 'string', 'enum': ['unknown', 'same'], 'description': 'Literal $ref text.'},
                'amount': {'type': ['number', 'null'], 'minimum': 0, 'maximum': 10}})
    submitted = '\n ' + encode(form) + '\n'
    result = expand_fact_form(submitted, child_role='literature', facts_by_role={}, permitted_child_roles=['literature'])
    assert result['expanded_schema'] == form
    assert result['declaration']['fact_references'] == []
    assert validate(submitted, result) == form


@pytest.mark.parametrize('node', [
    {'$ref': 'episode-fact:measured_values', 'description': 'Sibling not allowed'},
    {'$ref': 'https://example.invalid/remote'},
    {'$dynamicRef': 'episode-fact:measured_values'},
    {'type': 'array', 'items': {'$ref': 'episode-fact:measured_values'}},
    {'type': 'object', 'properties': {'nested': {'$ref': 'episode-fact:measured_values'}},
     'required': ['nested'], 'additionalProperties': False},
])
def test_sibling_nested_dynamic_and_external_refs_are_rejected(node):
    facts, _ = fixture()
    with pytest.raises(ContractInformationError, match='unsupported_form_reference'):
        expand_fact_form(encode(obj({'field': node})), child_role='literature', facts_by_role=facts, permitted_child_roles=['literature'])


def test_unknown_and_wrong_role_fact_refs_are_rejected_without_fallback():
    facts, submitted = fixture()
    with pytest.raises(ContractInformationError, match='return_child_role_not_available'):
        expand_fact_form(submitted, child_role='literature', facts_by_role=facts, permitted_child_roles=[])
    with pytest.raises(ContractInformationError, match='return_contract_not_available'):
        expand_fact_form(submitted, child_role='literature', facts_by_role={'another_role': facts['literature']}, permitted_child_roles=['literature'])


@pytest.mark.parametrize('text', ['{"type":"object","type":"array","properties":{}}',
    '{"type":"object","properties":{},"minimum":NaN}', '[]', 'not JSON'])
def test_submitted_form_uses_strict_original_json_object_parsing(text):
    with pytest.raises(ContractInformationError):
        expand_fact_form(text, child_role='literature', facts_by_role={}, permitted_child_roles=['literature'])


@pytest.mark.parametrize('change', [
    lambda row: row.update(type='number'),
    lambda row: row['report_schema'].update(**{'x-source': 'different_source'}),
    lambda row: row.update(meaning=None),
    lambda row: row.update(type=float('nan')),
])
def test_inconsistent_source_contract_metadata_is_rejected(change):
    facts, submitted = fixture()
    change(facts['literature']['measured_values'])
    with pytest.raises(ContractInformationError):
        expand_fact_form(submitted, child_role='literature', facts_by_role=facts, permitted_child_roles=['literature'])


def test_saved_validation_has_no_factory_and_survives_current_catalog_changes(monkeypatch):
    facts, submitted, result = expanded_fixture()
    facts['literature']['measured_values']['report_schema']['items']['type'] = 'integer'
    def forbidden(*args, **kwargs):
        raise AssertionError('No current factory or source lookup during saved validation')
    import gene_annotation_episode.episode_contract_information as module
    monkeypatch.setattr(module, '_fact', forbidden)
    monkeypatch.setattr(LiteratureEpisodes, '_rate_fact_sources', forbidden)
    assert validate(submitted, result) == result['expanded_schema']


def test_saved_exact_compact_selection_and_child_role_are_retained():
    _, submitted, result = expanded_fixture()
    with pytest.raises(ContractInformationError, match='saved_contract_declaration_mismatch'):
        validate(submitted + ' ', result)
    with pytest.raises(ContractInformationError, match='saved_contract_declaration_mismatch'):
        validate_saved_fact_form(child_role='another_role', submitted_schema_json=submitted,
            expanded_schema=result['expanded_schema'], declaration=result['declaration'])


@pytest.mark.parametrize('part', ['expanded_schema', 'source_schema', 'selector', 'roster', 'selector_flag', 'extra_declaration'])
def test_saved_relationship_tampering_is_rejected_even_with_recomputed_outer_digest(part):
    _, submitted, result = expanded_fixture()
    expanded, declaration = result['expanded_schema'], result['declaration']
    if part == 'expanded_schema':
        expanded['properties']['qualification']['enum'] = ['different']
    elif part == 'source_schema':
        expanded['properties']['my_numbers']['items']['type'] = 'integer'
    elif part == 'selector':
        expanded['properties']['my_numbers']['x-source'] = 'other_source'
    elif part == 'roster':
        declaration['fact_references'].append(deepcopy(declaration['fact_references'][0]))
    elif part == 'selector_flag':
        declaration['fact_references'][0]['source_had_x_source'] = True
    else:
        declaration['undeclared'] = 'bad'
    declaration['expanded_schema_sha256'] = schema_fingerprint(expanded)
    with pytest.raises(ContractInformationError):
        validate(submitted, result)


def test_saved_helper_checks_consistency_rather_than_claiming_original_custody():
    _, submitted, result = expanded_fixture()
    # A completely different coherent record is valid pure data. Original
    # request/admission authentication must reject its substitution later.
    result['expanded_schema']['properties']['my_numbers']['items']['type'] = 'integer'
    original = deepcopy(result['expanded_schema']['properties']['my_numbers'])
    del original['x-source']
    result['declaration']['fact_references'][0]['schema_sha256'] = schema_fingerprint(original)
    result['declaration']['expanded_schema_sha256'] = schema_fingerprint(result['expanded_schema'])
    assert validate(submitted, result) == result['expanded_schema']
