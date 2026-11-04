"""Real library/resource selection; no transport or live service claim."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_application_definitions import prepare_application
from gene_annotation_episode.bvbrc_genome_alignment_returns import FACT_SOURCES
from gene_annotation_episode.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_custody import selector
from test_bvbrc_genome_alignment_retained_records import fixture
from test_bvbrc_genome_alignment_bundle_resolution import arguments
from test_bvbrc_homology_tool_info import factory


def configuration(bound=True):
    value = deepcopy(CONFIG)
    value['scientific_adapters'] = ([{'adapter_id': adapter.ADAPTER_ID,
        'adapter_version': adapter.ADAPTER_VERSION,
        'implementation_sha256': adapter.implementation_sha256()}] if bound else [])
    return value


def entry(family):
    return next(row for row in bound_resource_tool_contracts(family) if row['name'] == 'bvbrc.genome_alignment')


def launch(recipe='progressiveMauve', resource='selected-api'):
    _, query, _, _ = fixture(recipe=recipe)
    return {'version': 'api_service_assignment_v1', 'resource_id': resource,
        'service': 'bvbrc_appservice', 'request': query, 'endpoint': 'usable_handoff', 'constraints': {}}


def results(fmt):
    native = arguments(fmt)
    selection = selector()
    selection.update(endpoint='requested_projection', requested_schema=native['requested_form'],
        adapter={'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
            'parameters': native['parameters']})
    return {'version': 'execution_results_assignment_v1', 'handoff_ref': 'source_original_handoff',
        'selector': selection}


@pytest.mark.parametrize('recipe', ['progressiveMauve', 'mauveAligner', ...])
def test_actual_native_recipe_selection_and_no_inserted_defaults(factory, recipe):
    create, registry = factory
    family = create({'selected-api': configuration()})
    row, payload = entry(family), launch(recipe)
    before = deepcopy(payload)
    validator = Draft202012Validator(row['input_schema'])
    Draft202012Validator.check_schema(row['input_schema'])
    assert validator.is_valid(payload), list(validator.iter_errors(payload))
    assert family.api_execution.validate_assignment(payload) == payload
    prepared = prepare_application('GenomeAlignment', payload['request']['parameters'], {})
    assert prepared['status'] == 'ok', prepared
    assert payload == before
    assert row['name'] not in registry.catalog()
    assert all(route['resource_id'] == 'selected-api' for route in row['invocation_route']['routes'])


@pytest.mark.parametrize('fmt', ['mauve_v4', 'mauve1_xmfa', 'mauve_backbone', 'mauve_bbcols'])
def test_actual_provider_parameters_and_closed_parent_return_sources(factory, fmt):
    create, _ = factory
    family = create({'selected-api': configuration()})
    payload = results(fmt)
    validator = Draft202012Validator(entry(family)['input_schema'])
    assert validator.is_valid(payload), list(validator.iter_errors(payload))
    assert family.api_execution.services['selected-api'].result_catalog(launch()['request'], payload['selector'])
    assert set(FACT_SOURCES) <= set(family.fact_sources('results'))
    assert set(FACT_SOURCES) <= set(family.received_report_sources('scientific_process'))


@pytest.mark.parametrize('wrong', ['resource', 'application', 'recipe', 'empty_genomes', 'adapter', 'parameters'])
def test_wrong_actual_resource_or_provider_selection_rejected(factory, wrong):
    create, _ = factory
    validator = Draft202012Validator(entry(create({'selected-api': configuration()}))['input_schema'])
    payload = results('mauve_v4') if wrong in {'adapter', 'parameters'} else launch()
    if wrong == 'resource': payload['resource_id'] = 'unconfigured'
    elif wrong == 'application': payload['request']['required_application_id'] = 'MSA'
    elif wrong == 'recipe': payload['request']['parameters']['recipe'] = 'invented'
    elif wrong == 'empty_genomes': payload['request']['parameters']['genome_ids'] = []
    elif wrong == 'adapter': payload['selector']['adapter']['adapter_id'] = 'bvbrc_msa'
    else: payload['selector']['adapter']['parameters']['calculation_plan']['requests'][0]['kind'] = 'invented'
    assert not validator.is_valid(payload)


def test_only_bound_provider_is_listed_and_multiple_resources_remain_explicit(factory, tmp_path):
    create, _ = factory
    assert not any(row['name'] == 'bvbrc.genome_alignment' for row in
        create({'selected-api': configuration(False)}).resource_tool_contracts())
    family = create({'first-api': configuration(), 'second-api': configuration()})
    row = entry(family)
    assert {r['resource_id'] for r in row['invocation_route']['routes']} == {'first-api', 'second-api'}
    validator = Draft202012Validator(row['input_schema'])
    assert all(validator.is_valid(launch(resource=r)) for r in ('first-api', 'second-api'))
    available = family.resource_tool_contracts()
    library = ScientificToolLibrary.freeze(tmp_path / 'library', catalog=[], tool_info=True,
        resource_catalogs={'api': available})
    selected = [{'name': row['name'], 'resources': 'api'}]
    info = library.resolve_tool_info(selected, available)
    assert set(info[0]) == {'name', 'description', 'resources', 'instructions'}
    assert library.resolve_invocations(selected, available) == [row]
    assert set(library.parent_tool_info([row])[0]) == {'name', 'description', 'resources'}
    assert info[0]['instructions'] == row['instructions']
