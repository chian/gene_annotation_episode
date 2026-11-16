"""Configured resource owners and real frozen library; no service/model call."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.root.bvbrc_proteome_returns import FACT_SOURCES
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.episodic_workflow.root.scientific_tool_library import ScientificToolLibrary
from test_api_bvbrc_appservice import CONFIG
from gene_annotation_episode.episodic_workflow.root.a101.tests.test_bvbrc_homology_tool_info import factory
from test_bvbrc_proteome_tool_info import launch, results


def configuration(provider='bvbrc_proteome'):
    value = deepcopy(CONFIG)
    value['scientific_adapters'] = ([] if provider is None else [{
        'adapter_id': provider, 'adapter_version': '1'}])
    return value


def entry(family):
    return next(row for row in bound_resource_tool_contracts(family)
                if row['name'] == 'bvbrc.proteome_comparison')


@pytest.mark.parametrize('provider', [None, 'unknown_provider'])
def test_unbound_and_unknown_provider_expose_no_scientific_route(factory, provider):
    create, registry = factory
    family = create({'selected-api': configuration(provider)})
    assert not any(row['name'] == 'bvbrc.proteome_comparison' for row in family.resource_tool_contracts())
    assert ('bvbrc_proteome', '1') not in family.api_execution.services['selected-api'].scientific_adapters
    assert 'bvbrc.proteome_comparison' not in registry.catalog()


def test_actual_assignment_result_contract_and_eight_sources(factory):
    create, registry = factory
    family = create({'selected-api': configuration()})
    row = entry(family)
    validator = Draft202012Validator(row['input_schema'])
    for payload in (launch(), results()):
        assert validator.is_valid(payload), list(validator.iter_errors(payload))
    assert family.api_execution.validate_assignment(launch()) == launch()
    assert family.api_execution.services['selected-api'].result_catalog(launch()['request'], results()['selector'])
    assert set(FACT_SOURCES) <= set(family.fact_sources('results'))
    assert set(FACT_SOURCES) <= set(family.received_report_sources('scientific_process'))
    assert set(FACT_SOURCES) <= set(family.received_report_sources('annotation'))
    assert family.received_report_sources('launch') == {}
    assert row['name'] not in registry.catalog()


def test_multiple_explicit_resources_survive_real_library_and_service_catalog(factory, tmp_path):
    create, tools = factory
    family = create({'first-api': configuration(), 'second-api': configuration()})
    row = entry(family)
    assert {route['resource_id'] for route in row['invocation_route']['routes']} == {'first-api', 'second-api'}
    assert len(row['invocation_route']['routes']) == 4
    for resource in ('first-api', 'second-api'):
        payload = launch()
        payload['resource_id'] = resource
        assert Draft202012Validator(row['input_schema']).is_valid(payload)
    bindings = EpisodeBindingRegistry([family])
    workflow = SimpleNamespace(tools=tools, episode_bindings=bindings,
        scientific_process_binding=SimpleNamespace(child_roles=lambda _: ('launch', 'results')))
    catalog = WorkflowServices(workflow).tool_information_catalog({})
    actual = next(item for item in catalog if item['name'] == row['name'])
    assert actual == row
    resource_catalogs = {}
    for item in catalog:
        resource_catalogs.setdefault(item['resources'], []).append(item)
    library = ScientificToolLibrary.freeze(tmp_path / 'frozen', catalog=[],
        resource_catalogs=resource_catalogs)
    selection = [{'name': row['name'], 'resources': 'api'}]
    assert library.parent_tool_info([row]) == [{key: row[key] for key in ('name', 'description', 'resources')}]
    assert library.resolve_tool_info(selection, [row]) == [{key: row[key] for key in
        ('name', 'description', 'resources', 'instructions')}]
    assert library.resolve_invocations(selection, [row]) == [row]
    assert ScientificToolLibrary(tmp_path / 'frozen').resolve_invocations(selection, [row]) == [row]


def test_actual_factory_reconstruction_retains_configured_provider_contract(factory, tmp_path):
    _, registry = factory
    first = ExecutionServiceFactory(resources={'selected-api': configuration()}, initial_information={},
        handoff_unit=2, acquired_record_unit=3, monitoring_information_unit=1)
    restored = ExecutionServiceFactory.from_record(first.as_record())
    services = restored(registry.store, run_id='proteome-factory', directory=tmp_path / 'factory',
        tool_registry=registry)
    names = [row['name'] for row in services.resource_tool_catalogs['api']]
    assert names.count('bvbrc.proteome_comparison') == 1
    assert first.as_record() == restored.as_record()
