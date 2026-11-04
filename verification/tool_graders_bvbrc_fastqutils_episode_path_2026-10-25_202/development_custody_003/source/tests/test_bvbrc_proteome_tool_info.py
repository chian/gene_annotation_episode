"""Actual library/API assignment contracts; no dispatch or service-run claim."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.bvbrc_application_definitions import prepare_application
from gene_annotation_episode.bvbrc_proteome_tool_info import proteome_tool_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_custody import request, selector
from test_bvbrc_homology_tool_info import factory
from test_bvbrc_proteome_bundle_resolution import fixture as provider_fixture


def entry(family, resource='selected-api'):
    return proteome_tool_contracts(resource_id=resource,
        assignment_schema=family.api_execution.assignment_schema(resource))[0]


def launch(kind='genome_ids'):
    query = request()
    query['required_application_id'] = 'GenomeComparison'
    query['parameters'] = {'genome_ids': [], 'user_genomes': [], 'user_feature_groups': [],
        'reference_genome_index': 1, 'output_path': '/synthetic/work/output', 'output_file': 'compare',
        'min_ident': .25, 'min_seq_cov': .3, 'min_positives': .2, 'max_e_val': 1e-5}
    query['parameters'][kind] = (['83333.1', '83333.1'] if kind == 'genome_ids'
        else ['/synthetic/input/first', '/synthetic/input/first'])
    return {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
        'service': 'bvbrc_appservice', 'request': query, 'endpoint': 'usable_handoff', 'constraints': {}}


def results():
    case = provider_fixture()
    selected = selector()
    selected.update(endpoint='requested_projection', requested_schema=case['requested_form'],
        adapter={'adapter_id': 'bvbrc_proteome', 'adapter_version': '1', 'parameters': case['parameters']})
    return {'version': 'execution_results_assignment_v1', 'handoff_ref': 'source_actual_handoff_required',
        'selector': selected}


@pytest.mark.parametrize('kind', ['genome_ids', 'user_genomes', 'user_feature_groups'])
def test_actual_application_inputs_preserve_occurrences_and_parameters(factory, kind):
    create, registry = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    row, value = entry(family), launch(kind)
    original = deepcopy(value)
    validator = Draft202012Validator(row['input_schema'])
    Draft202012Validator.check_schema(row['input_schema'])
    assert validator.is_valid(value), list(validator.iter_errors(value))
    assert family.api_execution.validate_assignment(value) == value
    prepared = prepare_application('GenomeComparison', value['request']['parameters'], {})
    assert prepared['status'] == 'ok', prepared
    assert value == original
    assert row['name'] not in registry.catalog()
    assert row['invocation_route']['routes'] == [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]


def test_explicit_omitted_native_options_stay_omitted(factory):
    create, _ = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    value = launch()
    for name in ('reference_genome_index', 'min_ident', 'min_seq_cov', 'min_positives', 'max_e_val'):
        value['request']['parameters'].pop(name)
    original = deepcopy(value)
    assert Draft202012Validator(entry(family)['input_schema']).is_valid(value)
    assert prepare_application('GenomeComparison', value['request']['parameters'], {})['status'] == 'ok'
    assert value == original


def test_nested_provider_parameter_references_resolve_inside_real_result_schema(factory):
    create, _ = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    row, value = entry(family), results()
    validator = Draft202012Validator(row['input_schema'])
    assert validator.is_valid(value), list(validator.iter_errors(value))
    # Traverse the nested parameter schema far enough to reject a real field,
    # rather than accepting it as an unconstrained opaque dictionary.
    value['selector']['adapter']['parameters']['native_documents'][0]['role'] = 'made_up'
    assert not validator.is_valid(value)


@pytest.mark.parametrize('wrong', ['resource', 'service', 'application', 'reference_index',
    'input_type', 'output_path', 'adapter', 'version', 'endpoint', 'calculation_parameters'])
def test_wrong_commission_contract_rejected(factory, wrong):
    create, _ = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    value = results() if wrong in {'adapter', 'version', 'endpoint', 'calculation_parameters'} else launch()
    if wrong == 'resource': value['resource_id'] = 'different-api'
    elif wrong == 'service': value['service'] = 'different-service'
    elif wrong == 'application': value['request']['required_application_id'] = 'MSA'
    elif wrong == 'reference_index': value['request']['parameters']['reference_genome_index'] = 0
    elif wrong == 'input_type': value['request']['parameters']['genome_ids'] = '83333.1'
    elif wrong == 'output_path': value['request']['parameters'].pop('output_path')
    elif wrong == 'adapter': value['selector']['adapter']['adapter_id'] = 'bvbrc_msa'
    elif wrong == 'version': value['selector']['adapter']['adapter_version'] = '2'
    elif wrong == 'endpoint': value['selector']['endpoint'] = 'requested_artifacts'
    else: value['selector']['adapter']['parameters']['calculation_parameters']['minimum_identity_fraction'] = 'strong'
    assert not Draft202012Validator(entry(family)['input_schema']).is_valid(value)


def test_library_passes_exact_instructions_only_to_selected_child(factory, tmp_path):
    create, _ = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    row = entry(family)
    library = ScientificToolLibrary.freeze(tmp_path / 'library', catalog=[], tool_info=True,
        resource_catalogs={'api': [row]})
    selected = [{'name': row['name'], 'resources': 'api'}]
    parent = library.parent_tool_info([row])
    assert parent == [{key: row[key] for key in ('name', 'description', 'resources')}]
    child = library.resolve_tool_info(selected, [row])
    assert child == [{key: row[key] for key in ('name', 'description', 'resources', 'instructions')}]
    assert library.resolve_invocations(selected, [row]) == [row]
    assert library.retrieve_literal_test('proteome matches', [row])['child_tool_info'] == parent
    changed = deepcopy(row)
    changed['instructions'] = 'silently changed information'
    with pytest.raises(ValueError, match='scientific_tool_contract_changed'):
        library.resolve_tool_info(selected, [changed])


def test_detached_schemas_preserve_the_actual_assignment_and_next_entry(factory):
    create, _ = factory
    family = create({'selected-api': deepcopy(CONFIG)})
    schema = family.api_execution.assignment_schema('selected-api')
    original = deepcopy(schema)
    rows = proteome_tool_contracts(resource_id='selected-api', assignment_schema=schema)
    rows[0]['input_schema']['oneOf'][0]['allOf'].clear()
    assert schema == original
    fresh = entry(family)
    value = launch()
    value['request']['required_application_id'] = 'Homology'
    assert not Draft202012Validator(fresh['input_schema']).is_valid(value)


@pytest.mark.parametrize('resource', ['', ' ', 'a\0b', None, 7])
def test_resource_identity_required(resource):
    with pytest.raises(ValueError, match='proteome_explicit_api_resource_required'):
        proteome_tool_contracts(resource_id=resource, assignment_schema={})
