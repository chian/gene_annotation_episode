"""Real library/resource selection; no transport or live service claim."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_genome_alignment_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_application_definitions import prepare_application
from gene_annotation_episode.episodic_workflow.root.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.episodic_workflow.root.scientific_tool_library import ScientificToolLibrary
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_genome_alignment_retained_records import fixture
from gene_annotation_episode.episodic_workflow.root.a101.tests.test_bvbrc_homology_tool_info import factory


def configuration(bound=True):
    value = deepcopy(CONFIG)
    value['scientific_adapters'] = ([{'adapter_id': adapter.ADAPTER_ID,
        'adapter_version': adapter.ADAPTER_VERSION}] if bound else [])
    return value


def entry(family):
    return next(row for row in bound_resource_tool_contracts(family) if row['name'] == 'bvbrc.genome_alignment')


def launch(recipe='progressiveMauve', resource='selected-api'):
    _, query, _, _ = fixture(recipe=recipe)
    return {'version': 'api_service_assignment_v1', 'resource_id': resource,
        'service': 'bvbrc_appservice', 'request': query, 'endpoint': 'usable_handoff', 'constraints': {}}


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
    library = ScientificToolLibrary.freeze(tmp_path / 'library', catalog=[],
        resource_catalogs={'api': available})
    selected = [{'name': row['name'], 'resources': 'api'}]
    info = library.resolve_tool_info(selected, available)
    assert set(info[0]) == {'name', 'description', 'resources', 'instructions'}
    assert library.resolve_invocations(selected, available) == [row]
    assert set(library.parent_tool_info([row])[0]) == {'name', 'description', 'resources'}
    assert info[0]['instructions'] == row['instructions']
