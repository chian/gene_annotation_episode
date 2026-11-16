"""Bound operation declarations do not acquire data or grant direct execution."""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.api_execution import hmmer_operation_catalog
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_information import workflow_execution_catalogs
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def prohibited(*args, **kwargs):
    raise AssertionError('operation declaration performed work')


def binding(store, resources):
    tools = ToolRegistry(store, clients=SimpleNamespace())
    return ExecutionEpisodes(None, store=store, directory=store.path/'execution',
        run_id='declaration-check', resources=resources, initial_information={},
        tool_registry=tools, handoff_unit=1, acquired_record_unit=1,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))


def test_configured_catalog_has_exact_owners_without_query_or_execution(tmp_path, monkeypatch):
    resources = {'hmmer1': {'kind': 'hmmer_api', 'service': 'ebi_hmmer'},
        'hmmer2': {'kind': 'hmmer_api', 'service': 'ebi_hmmer'},
        'blast': {'kind': 'api', 'service': 'ncbi_blast'},
        'uniprot': {'kind': 'api', 'service': 'uniprot'},
        'bvbrc': {'kind': 'api', 'service': 'bvbrc_data'},
        'local': {'kind': 'local', 'workspace': str(tmp_path/'work'),
            'policy': {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4 * 1024 ** 3}}}
    with Store(tmp_path/'store') as store:
        owner = binding(store, resources)
        for service in owner.api_execution.services.values():
            for name in ('validate_request', 'launch_catalog', 'result_catalog', 'invoke', 'prepare'):
                monkeypatch.setattr(service, name, prohibited)
        monkeypatch.setattr(owner.api_execution.legacy, '_assignment', prohibited)
        monkeypatch.setattr(owner.api_execution.legacy, 'catalog', prohibited)
        rows = owner.resource_tool_contracts()
        contracts = {(row['name'], row['resources']): row for row in rows}
        assert len(rows) == len(contracts)
        assert all(row['invocation_route']['kind'] == 'commission' for row in rows)
        assert not any(row['resources'] == 'hpc' for row in rows)
        assert not any(row['name'].startswith('native.') for row in rows)
        assert contracts['api.hmmer.result', 'api']['invocation_route']['routes'] == [
            {'entry_role': 'results', 'resource_id': resource, 'resource_role': 'results'}
            for resource in ('hmmer1', 'hmmer2')]
        assert contracts['api.blast.status', 'api']['invocation_route']['routes'] == [
            {'entry_role': 'launch', 'resource_id': 'blast', 'resource_role': 'launch_api'},
            {'entry_role': 'results', 'resource_id': 'blast', 'resource_role': 'results'}]
        assert contracts['practical.job.start', 'local']['invocation_route']['routes'] == [
            {'entry_role': 'launch', 'resource_id': 'local', 'resource_role': 'launch_local'}]
        global_api = {row['name']: row for row in workflow_execution_catalogs()['api']}
        for row in rows:
            if row['resources'] == 'api':
                assert row['input_schema'] == global_api[row['name']]['input_schema']
        assert owner.tool_registry.remote_searches.jobs() == []


@pytest.mark.parametrize('service,job_request,selector', [
    ('ncbi_blast', {'subject_ref': 'synthetic-subject', 'program': 'blastp', 'database': 'nr'}, {}),
    ('uniprot', {'operation': 'record', 'accession': 'P0AAW1'}, {}),
])
def test_declarations_equal_validated_service_result_contract(tmp_path, service, job_request, selector):
    with Store(tmp_path) as store:
        owner = binding(store, {'selected': {'kind': 'api', 'service': service}})
        primitive = owner.api_execution.services['selected']
        assert owner.api_execution.operation_contracts('selected', 'results') == primitive.result_catalog(job_request, selector)
        with pytest.raises(ValueError, match='api_resource_not_bound'):
            owner.api_execution.operation_contracts('unbound', 'results')


@pytest.mark.parametrize('job_request,selector,operation', [
    ({'collection': 'genome', 'filters': [], 'fields': ['genome_id'],
        'offset': 0, 'limit': 1}, {}, 'api.bvbrc.result'),
    ({'version': 'bvbrc_data_request_v2', 'collection': 'genome', 'mode': 'page', 'filters': []},
        {'version': 'bvbrc_data_result_selector_v2', 'page': None,
            'projection': {'family': 'query_metadata'}, 'inputs': [], 'supplied_metadata': []},
        'api.bvbrc.data.result'),
])
def test_bvbrc_declares_both_versions_but_request_selects_exactly_one(
        tmp_path, monkeypatch, job_request, selector, operation):
    original_request, original_selector = deepcopy(job_request), deepcopy(selector)
    with Store(tmp_path) as store:
        owner = binding(store, {'selected': {'kind': 'api', 'service': 'bvbrc_data'}})
        primitive = owner.api_execution.services['selected']
        monkeypatch.setattr(primitive, 'invoke', prohibited)
        monkeypatch.setattr(primitive.client, 'query', prohibited)
        monkeypatch.setattr(primitive.client, 'query_prepared', prohibited)
        declared = owner.api_execution.operation_contracts('selected', 'results')
        assert [row['name'] for row in declared] == ['api.bvbrc.result', 'api.bvbrc.data.result']
        assert declared == primitive.result_capabilities()
        selected = primitive.result_catalog(job_request, selector)
        assert selected == [row for row in declared if row['name'] == operation]
        prepared = primitive.prepare(operation, job_request, {}, scope=None,
            previous_events=[], selector=selector)
        assert prepared['operation'] == operation
        assert prepared['mutates_remote'] is False
        assert prepared['cache_original'] is True
        wrong_operation, = [row['name'] for row in declared if row['name'] != operation]
        with pytest.raises(ContractError, match='bvbrc_operation_request_version_conflict'):
            primitive.prepare(wrong_operation, job_request, {}, scope=None,
                previous_events=[], selector=selector)
        assert job_request == original_request and selector == original_selector
        assert owner.tool_registry.remote_searches.jobs() == []


def test_hmmer_declaration_is_an_independent_copy():
    expected = hmmer_operation_catalog('results')
    mutated = deepcopy(expected)
    mutated[0]['input_schema']['required'].append('fabricated')
    assert hmmer_operation_catalog('results') == expected
    with pytest.raises(ValueError, match='api_execution_role_required'):
        hmmer_operation_catalog('annotation')


