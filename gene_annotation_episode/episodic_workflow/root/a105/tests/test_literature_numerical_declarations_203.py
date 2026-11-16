"""Controlled declaration/custody checks; no paper or actual model execution."""
from copy import deepcopy
import json
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import interpretation_schema, validate_closed_schema
from gene_annotation_episode.episodic_workflow.root.a105.domain import obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_contract_information import ContractInformationError, validate_saved_fact_form
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_numerical_contracts as contracts
QUALIFICATION = {'type': 'string', 'enum': ['unknown', 'qualified']}

def all_facts():
    binding = LiteratureEpisode(None, rate_population=True, channel_population=True, compiled_assay_population=True, ion_discrimination_population=True, completion_time_population=True, product_partition_population=True, active_site_population=True, assay_grading_population=True, parent_depletion_population=True, stoichiometric_balance_population=True, ratio_source_population=True, controlled_response_population=True, gel_population=True)
    return binding.fact_sources('literature')

def frozen(facts=None):
    facts = all_facts() if facts is None else facts
    facts = {**facts, 'credit': {'type': 'number', 'meaning': 'Original scalar credit.'}, 'caller_status': {'type': 'boolean', 'meaning': 'Original caller status.'}}
    action_schema = obj({'fixture': {'type': 'boolean'}})
    record = contracts.freeze_contracts(facts_by_role={'literature': facts}, permitted_child_roles=['literature'], action_schema=action_schema)
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
    assert validate_saved_fact_form(child_role='literature', submitted_schema_json=text, expanded_schema=expected, declaration=result['declaration']) == expected
    assert result['declaration']['submitted_schema_json'] == text
    assert facts[source] == original


def test_explicit_fact_reference_detection_keeps_literal_native_documents_on_original_route():
    assert set(contracts.RETURN_MEANINGS) == set(contracts.registered_sources())
    for source in ('literature_gel_component_cells', 'literature_controlled_response_component_cells'):
        literal = obj({'native': contracts.registered_schema(source)})
        assert not contracts.uses_fact_references(literal)
        literal['properties']['chosen'] = {'$ref': 'episode-fact:literature_kinetic_cells'}
        assert contracts.uses_fact_references(literal)

@pytest.mark.parametrize('schema', [obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells', 'description': 'override'}}), obj({'numbers': {'type': 'array', 'items': {'$ref': 'episode-fact:literature_kinetic_cells'}}}), obj({'numbers': {'$ref': 'https://invalid.example/schema'}}), obj({'numbers': {'$dynamicRef': 'episode-fact:literature_kinetic_cells'}})])
def test_reference_overrides_nested_external_and_dynamic_references_are_rejected(schema):
    with pytest.raises(ContractInformationError, match='unsupported_form_reference'):
        contracts.expand_numerical_form(json.dumps(schema), child_role='literature', saved=frozen())

def test_wrong_role_cannot_use_available_source_and_modified_type_gets_no_alias():
    with pytest.raises(ContractInformationError, match='return_child_role_not_available'):
        contracts.expand_numerical_form(json.dumps(obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature_strategy', saved=frozen())
    facts = all_facts()
    facts['literature_kinetic_cells']['report_schema']['items']['properties']['value']['minimum'] = 0
    assert not contracts.is_registered_schema(facts['literature_kinetic_cells']['report_schema'])
    saved = frozen(facts)
    assert 'literature_kinetic_cells' not in saved[contracts.SAVED_MEMBER]['fact_sources_by_role']['literature']
    with pytest.raises(ContractInformationError, match='return_contract_not_available'):
        contracts.expand_numerical_form(json.dumps(obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature', saved=saved)

def test_saved_expansion_uses_original_snapshot_with_fact_factories_blocked(monkeypatch):
    saved = frozen()
    before = deepcopy(saved)

    def forbidden(*_args, **_kwargs):
        raise AssertionError('Original frozen declarations must not reload current factories')
    monkeypatch.setattr(contracts, 'registered_schema', forbidden)
    result = contracts.expand_numerical_form(json.dumps(obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature', saved=saved)
    assert result['expanded_schema']['properties']['numbers'] == saved[contracts.SAVED_MEMBER]['fact_sources_by_role']['literature']['literature_kinetic_cells']['report_schema']
    assert saved == before

@pytest.mark.parametrize('location', ['schema', 'fact_source', 'source_type', 'roles'])
def test_original_snapshot_associations_reject_tamper(location):
    saved = frozen()
    if location == 'schema':
        saved['schema']['properties']['fixture']['type'] = 'integer'
    elif location == 'fact_source':
        saved[contracts.SAVED_MEMBER]['fact_sources_by_role']['literature']['literature_kinetic_cells']['report_schema']['x-source'] = 'literature_binding_cells'
    elif location == 'source_type':
        saved[contracts.SAVED_MEMBER]['source_types_by_role']['literature']['credit']['type'] = 'array'
    else:
        saved[contracts.SAVED_MEMBER]['permitted_child_roles'].append('invented_role')
    with pytest.raises(ContractInformationError, match='original_literature_numerical'):
        contracts.validate_frozen_contracts(saved)







@pytest.mark.parametrize('native', ['literature_gel_component_cells', 'literature_controlled_response_component_cells'])
def test_mixed_native_literal_and_alias_expand_and_saved_validate_without_changing_either(native):
    facts = all_facts()
    submitted = obj({'native': facts[native]['report_schema'], 'kinetic': {'$ref': 'episode-fact:literature_kinetic_cells'}, 'qualification': QUALIFICATION})
    text = json.dumps(submitted)
    result = contracts.expand_numerical_form(text, child_role='literature', saved=frozen({name: facts[name] for name in (native, 'literature_kinetic_cells')}))
    expected = obj({'native': facts[native]['report_schema'], 'kinetic': facts['literature_kinetic_cells']['report_schema'], 'qualification': QUALIFICATION})
    assert result['expanded_schema'] == expected
    assert validate_saved_fact_form(child_role='literature', submitted_schema_json=text, expanded_schema=expected, declaration=result['declaration']) == expected
    assert result['declaration']['fact_references'][0]['field'] == 'kinetic'
    assert len(result['declaration']['fact_references']) == 1

@pytest.mark.parametrize('native', ['literature_gel_component_cells', 'literature_controlled_response_component_cells'])
@pytest.mark.parametrize('mutation', ['nested_alias', 'modified_type', 'invented_native_label', 'wrong_native_family', 'dynamic_ref'])
def test_native_literal_opacity_rejects_altered_schema_labels_and_nested_aliases(native, mutation):
    facts = all_facts()
    literal = deepcopy(facts[native]['report_schema'])
    if mutation == 'nested_alias':
        literal['$defs']['IllicitAlias'] = {'$ref': 'episode-fact:literature_kinetic_cells'}
    elif mutation == 'modified_type':
        literal['minItems'] = 0
    elif mutation == 'invented_native_label':
        literal['x-source'] = 'invented_native_document'
    elif mutation == 'wrong_native_family':
        literal['x-source'] = 'literature_controlled_response_component_cells' if native == 'literature_gel_component_cells' else 'literature_gel_component_cells'
    else:
        literal['$defs']['IllicitDynamic'] = {'$dynamicRef': '#/$defs/Cell'}
    submitted = obj({'native': literal, 'kinetic': {'$ref': 'episode-fact:literature_kinetic_cells'}})
    with pytest.raises(ContractInformationError):
        contracts.expand_numerical_form(json.dumps(submitted), child_role='literature', saved=frozen({name: facts[name] for name in (native, 'literature_kinetic_cells')}))


@pytest.mark.parametrize('source', contracts.registered_sources())
@pytest.mark.parametrize('surface', ['legacy_request', 'profile_request', 'profile_lookup', 'legacy_parent'])
def test_actual_public_return_surfaces_keep_scientific_task_interpretations_and_usable_declaration(source, surface):
    from gene_annotation_episode.episodic_workflow.root.a105.composition_information import CONTRACT_INFORMATION_PROFILE
    from gene_annotation_episode.episodic_workflow.root.a105.episode_contract_information import return_contract_information
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_prompt import EXPERIMENTAL_TASK, render_literature_experimental_prompt
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_reference_parent_prompt import REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt
    schema = contracts.registered_schema(source)
    form = obj({'numbers': schema, 'qualification': QUALIFICATION})
    fact = {'type': 'array', 'meaning': contracts.RETURN_MEANINGS[source], 'report_schema': schema}
    state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}, 'goal': {'objective': 'Examine the supplied synthetic experiment and retain its actual measurement meanings.', 'result_contract': form}, 'requested_form': form, 'available_report_facts': {source: fact}}
    lookups = []
    if surface.startswith('profile'):
        state['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    if surface == 'profile_lookup':
        lookups = [return_contract_information(facts_by_role={'literature': {source: fact}}, permitted_child_roles=['literature'], role='literature', source=source)]
        state.pop('requested_form')
        state['goal'].pop('result_contract')
    if surface == 'legacy_parent':
        state['literature_experimental_work']['aspect'] = 'reference_evidence_parent'
        state['reference_evidence_parent'] = {'version': 'reference_evidence_parent_v1', 'source_refs': ['synthetic_source_assignment']}
    original_state, original_lookups = (deepcopy(state), deepcopy(lookups))
    renderer = render_reference_evidence_parent_prompt if surface == 'legacy_parent' else render_literature_experimental_prompt
    prompt = renderer(state, 'Examine the assigned synthetic experiment.', lookup_results=lookups)
    task, steering = prompt.split('\n\nSTEERING\n', 1)
    assert (REFERENCE_PARENT_TASK if surface == 'legacy_parent' else EXPERIMENTAL_TASK) in task
    assert 'uncertainty' in task
    assert 'episode-fact:' + source in task
    assert 'formula_code' not in task
    assert 'count_reported_value' not in task
    assert '"$defs"' not in task
    if surface != 'profile_lookup':
        assert 'qualification' in task and 'qualified' in task and ('unknown' in task)
    else:
        assert 'Requested recorded return declaration' in task
        assert 'Complete requested contract' not in task
        assert 'formula_code' not in steering
    assert state == original_state
    assert lookups == original_lookups
    assert schema == contracts.registered_schema(source)

def test_operation_input_nomination_contract_is_not_redacted_as_a_return_sheet():
    from gene_annotation_episode.episodic_workflow.root.a105.composition_information import CONTRACT_INFORMATION_PROFILE
    from gene_annotation_episode.episodic_workflow.root.a105.episode_contract_information import operation_contract_information
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.source_contracts import _population_catalog
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_prompt import render_literature_experimental_prompt
    from gene_annotation_episode.episodic_workflow.root.a105.schema_information_text import render_schema_information
    operation = next((row for row in _population_catalog() if row['name'] == 'literature.kinetic.populate'))
    original = deepcopy(operation)
    reply = operation_contract_information(catalog=[operation], operation=operation['name'])
    state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}, 'contract_information_profile': CONTRACT_INFORMATION_PROFILE}
    prompt = render_literature_experimental_prompt(state, 'Identify the original source operands.', lookup_results=[reply])
    task = prompt.split('\n\nSTEERING\n', 1)[0]
    assert render_schema_information(operation['input_schema'], title='Arguments for ' + operation['name']) in task
    assert 'number_start' in task and 'number_end' in task
    assert operation == original
    assert reply['result']['input_schema'] == operation['input_schema']


