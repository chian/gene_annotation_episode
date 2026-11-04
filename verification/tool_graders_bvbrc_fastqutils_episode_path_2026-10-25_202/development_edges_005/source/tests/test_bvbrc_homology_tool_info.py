"""Actual configured resource/library contracts, without transport or grading."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG, original_request
from test_bvbrc_homology_bundle_adapter import c4_fixture
from test_bvbrc_appservice_custody import selector
from test_public_search import Client


def configuration(*, bound=True):
    config = deepcopy(CONFIG)
    config['scientific_adapters'] = ([{'adapter_id': adapter.ADAPTER_ID,
        'adapter_version': adapter.ADAPTER_VERSION,
        'implementation_sha256': adapter.implementation_sha256()}] if bound else [])
    return config


@pytest.fixture
def factory(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('tool information attempted transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')
        registry = ToolRegistry(store, clients=Client())

        def create(resources):
            return ExecutionEpisodes(None, store=store, directory=tmp_path / 'run',
                run_id='homology-library', resources=resources, initial_information={},
                tool_registry=registry, handoff_unit=2, acquired_record_unit=3,
                log_window_bytes=128, log_roles=('stdout', 'stderr'))
        yield create, registry


def scientific_rows(family):
    return {row['name'].split('.')[-1]: row for row in bound_resource_tool_contracts(family)
        if row['name'].startswith('bvbrc.homology.')}


def launch_payload(resource='selected-api'):
    return {'version': 'api_service_assignment_v1', 'resource_id': resource,
        'service': 'bvbrc_appservice', 'request': original_request(),
        'endpoint': 'usable_handoff', 'constraints': {}}


def result_payload(mode):
    _, _, _, parameters = c4_fixture()
    parameters['scientific_mode'] = mode
    if mode == 'pairwise_correspondence':
        parameters['database_model'] = None
    selected = selector()
    selected.update(endpoint='requested_projection', adapter={
        'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
        'parameters': parameters}, requested_schema=adapter.requested_form_schema({
            'hits': {'metric': 'reported_hit_count', 'report_index': 0}}))
    return {'version': 'execution_results_assignment_v1',
        'handoff_ref': 'actual-handoff-required-at-commission', 'selector': selected}


@pytest.mark.parametrize('mode', ['database_identification', 'pairwise_correspondence'])
def test_scientific_rows_describe_real_launch_and_results_contracts(factory, mode):
    create, registry = factory
    family = create({'selected-api': configuration()})
    rows = scientific_rows(family)
    assert set(rows) == {'database_identification', 'pairwise_correspondence'}
    entry = rows[mode]
    assert entry['resources'] == 'api'
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'selected-api', 'resource_role': 'launch_api'},
        {'entry_role': 'results', 'resource_id': 'selected-api', 'resource_role': 'results'}]}
    validator = Draft202012Validator(entry['input_schema'])
    Draft202012Validator.check_schema(entry['input_schema'])
    launch = launch_payload()
    assert validator.is_valid(launch)
    assert family.api_execution.validate_assignment(launch) == launch
    result = result_payload(mode)
    assert validator.is_valid(result), list(validator.iter_errors(result))
    service = family.api_execution.services['selected-api']
    assert service.result_catalog(launch['request'], result['selector'])
    assert entry['name'] not in registry.catalog()
    assert 'annotation probabilities' in entry['instructions'] or 'annotation correctness' in entry['instructions']


@pytest.mark.parametrize('change', ['application', 'resource', 'service', 'mode', 'adapter', 'pairwise_model'])
def test_wrong_existing_payload_or_scientific_mode_rejected(factory, change):
    create, _ = factory
    family = create({'selected-api': configuration()})
    validator = Draft202012Validator(scientific_rows(family)['pairwise_correspondence']['input_schema'])
    if change in {'application', 'resource', 'service'}:
        value = launch_payload()
        if change == 'application':
            value['request']['required_application_id'] = 'GeneTree'
        else:
            value['resource_id' if change == 'resource' else 'service'] = 'not-selected'
    else:
        value = result_payload('pairwise_correspondence')
        if change == 'mode':
            value['selector']['adapter']['parameters']['scientific_mode'] = 'database_identification'
        elif change == 'adapter':
            value['selector']['adapter']['adapter_id'] = 'not-selected'
        else:
            value['selector']['adapter']['parameters']['database_model'] = {
                'temperature_bits': 1, 'function_priors': None}
    assert not validator.is_valid(value)


def test_only_installed_bound_adapter_is_advertised(factory):
    create, _ = factory
    config = configuration(bound=False)
    assert scientific_rows(create({'selected-api': config})) == {}
    config['scientific_adapters'] = [{'adapter_id': 'unknown', 'adapter_version': '1',
        'implementation_sha256': '0' * 64}]
    assert scientific_rows(create({'selected-api': config})) == {}


def test_multiple_resources_remain_explicit_without_resource_selection(factory):
    create, _ = factory
    family = create({'first-api': configuration(), 'second-api': configuration()})
    for entry in scientific_rows(family).values():
        validator = Draft202012Validator(entry['input_schema'])
        assert validator.is_valid(launch_payload('first-api'))
        assert validator.is_valid(launch_payload('second-api'))
        assert not validator.is_valid(launch_payload('unconfigured-api'))
        assert {route['resource_id'] for route in entry['invocation_route']['routes']} == {'first-api', 'second-api'}
        assert len(entry['invocation_route']['routes']) == 4


def test_library_retrieval_separates_parent_information_and_child_instructions(factory, tmp_path):
    create, _ = factory
    family = create({'selected-api': configuration()})
    available = family.resource_tool_contracts()
    library = ScientificToolLibrary.freeze(tmp_path / 'library', catalog=[], tool_info=True,
        resource_catalogs={'api': available})
    retrieved = library.retrieve_literal_test('BV-BRC Homology aligned residues functions', available)
    picked = [row for row in retrieved['child_tool_info'] if row['name'].startswith('bvbrc.homology.')]
    assert len(picked) == 2
    assert all(set(row) == {'name', 'description', 'resources'} for row in picked)
    selection = [{'name': row['name'], 'resources': row['resources']} for row in picked]
    instructions = library.resolve_tool_info(selection, available)
    assert all(set(row) == {'name', 'description', 'resources', 'instructions'} for row in instructions)
    contracts = library.resolve_invocations(selection, available)
    assert all(row['invocation_route']['kind'] == 'commission' for row in contracts)
    assert [row['instructions'] for row in instructions] == [row['instructions'] for row in contracts]
    expected = {row['name']: row for row in available}
    assert all(row['instructions'] == expected[row['name']]['instructions'] for row in contracts)
    assert all(row['input_schema'] == expected[row['name']]['input_schema'] for row in contracts)
    changed = deepcopy(available)
    next(row for row in changed if row['name'] == picked[0]['name'])['instructions'] = 'Changed instructions'
    with pytest.raises(ValueError, match='scientific_tool_contract_changed'):
        library.resolve_invocations(selection, changed)
