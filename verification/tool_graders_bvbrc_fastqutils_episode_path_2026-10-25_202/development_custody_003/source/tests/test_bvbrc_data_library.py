"""BV-BRC Data v2 information and factual descriptors at actual owner ports.

Transport responses are synthetic. These checks use real catalogs, frozen
information, resource contracts and selected API handoffs, without network,
model decisions, AppService, or a complete parent-result admission claim.
"""
import asyncio
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_bvbrc import (
    BVBRCDataClient, DATA_QUERY_OPERATION, DATA_RESULT_OPERATION,
    EMPTY_ARGUMENTS, QUERY_OPERATION, RESULT_OPERATION,
)
from gene_annotation_episode.bvbrc_data_fields import COLLECTIONS, FIELD_REGISTRY
from gene_annotation_episode.bvbrc_data_views import FACT_SOURCES
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_progress import describe_execution_target
from gene_annotation_episode.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_information import make_tool_info, workflow_execution_catalogs
from gene_annotation_episode.tools import ToolRegistry


LIBRARY = Path(__file__).resolve().parents[1]/'gene_annotation_episode/launch_instruction_library'
PUBLISHER_FIELDS = ['source_ref', 'raw_artifact_ref', 'grading_artifact_ref', 'collection',
    'mode', 'parse_status', 'qualification', 'requested_projection_complete', 'projection_failures']


def query(collection='genome', mode='page', **operands):
    return {'version': 'bvbrc_data_request_v2', 'collection': collection, 'mode': mode,
        'filters': [], **operands}


def selection(projection=None, page=None):
    return {'version': 'bvbrc_data_result_selector_v2', 'page': page,
        'projection': projection or {'family': 'query_metadata'}, 'inputs': [], 'supplied_metadata': []}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def prohibited(*args, **kwargs):
        pytest.fail('library/descriptor verification attempted external access')
    monkeypatch.setattr('urllib.request.OpenerDirector.open', prohibited)
    monkeypatch.setattr('socket.create_connection', prohibited)


@pytest.fixture
def owner(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        tools = ToolRegistry(store)
        journal = Journal(store, 'bvbrc-library-fixture')
        resources = {'selected-bvbrc': {'kind': 'api', 'service': 'bvbrc_data'}}
        family = ExecutionEpisodes(None, store=store, directory=tmp_path/'run', run_id=journal.run_id,
            resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
            acquired_record_unit=2, log_window_bytes=1024, log_roles=[])
        calls = []

        def native_response(client, prepared):
            calls.append(deepcopy(prepared))
            effective, native = prepared['effective_request'], prepared['native_request']
            key = FIELD_REGISTRY[effective['collection']]['unique_key']
            docs = [] if effective['mode'] != 'page' else [{key: 'fixture-id'}]
            payload = {'responseHeader': {'status': 0}, 'response': {
                'docs': docs, 'start': effective['offset'], 'numFound': 2, 'numFoundExact': True}}
            if effective['mode'] == 'facet':
                payload['facet_counts'] = {'facet_fields': {effective['facet']['field']: ['fixture-id', 1]}}
            return SourceSnapshot('bvbrc_data', native['url'], deepcopy(effective),
                '2026-10-24T20:00:00+00:00', json.dumps(payload).encode(),
                'application/solr+json; charset=utf-8', {'status': 200, 'body_complete': True,
                    'request': {name: deepcopy(native[name]) for name in ('method', 'url', 'headers', 'body')},
                    'effective_url': native['url'], 'automatic_redirects': False})

        def legacy_response(client, request):
            calls.append(deepcopy(request))
            return SourceSnapshot('bvbrc_data', 'https://www.bv-brc.org/api/genome/', request,
                '2026-10-24T20:00:00+00:00', b'[{"genome_id":"fixture-id"}]',
                'application/json', {'status': 200, 'body_complete': True,
                    'headers': {'content-range': 'items 0-1/2'}})

        monkeypatch.setattr(BVBRCDataClient, 'query_prepared', native_response)
        monkeypatch.setattr(BVBRCDataClient, 'query', legacy_response)
        yield SimpleNamespace(store=store, tools=tools, journal=journal, family=family,
            scope={'subject_refs': [target]}, calls=calls, directory=tmp_path)


def context(owner, role, assignment, episode_id, path=None):
    path = path or ((role, episode_id),)
    request = {'message': {'scope': owner.scope, 'episode_assignment': deepcopy(assignment)}}
    value = BindingContext(owner.journal.run_id, episode_id, role, path, owner.scope, assignment, request)
    with owner.store.transaction():
        owner.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
    return value


def selected_call(owner, ctx, name):
    key = f'{ctx.run_id}:{ctx.episode_id}:0'
    with owner.store.transaction():
        owner.journal.save('runtime_actions', {'episode_id': ctx.episode_id, 'decision_index': 0,
            'action': canonical({'kind': 'tool', 'tool': name, 'arguments': {}}),
            'result': None, 'credit': None})
    result = asyncio.run(owner.family.execute(ctx, name, {}, key))
    with owner.store.transaction():
        owner.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? '
            'AND decision_index=0', (canonical(result), ctx.run_id, ctx.episode_id))
    assert result['status'] == 'completed', result
    return result


def launched(owner, request):
    assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-bvbrc',
        'service': 'bvbrc_data', 'request': deepcopy(request), 'endpoint': 'usable_handoff', 'constraints': {}}
    parent_assignment = {'version': 'execution_launch_assignment_v1', 'requests': {'selected-bvbrc': assignment},
        'immutable_input_versions': [], 'constraints': {}}
    parent = context(owner, 'launch', parent_assignment, 'launch-parent')
    original = owner.family.prepare_assignment(parent, 'launch_api', assignment, owner.scope, 'prepare-only')
    child = context(owner, 'launch_api', original, 'api-child',
        (('launch', 'launch-parent'), ('launch_api', 'api-child')))
    name = DATA_QUERY_OPERATION if 'version' in request else QUERY_OPERATION
    assert [row['name'] for row in owner.family.catalog(child)] == [name]
    outcome = selected_call(owner, child, name)
    assert 'handoff_ref' in outcome['result'], outcome
    return outcome['result']['handoff_ref']


def function(path):
    module, name = path.rsplit('.', 1)
    return getattr(importlib.import_module(module), name)


def test_v2_information_resolves_actual_catalog_and_bound_commission_routes(owner):
    actual = workflow_execution_catalogs()
    contracts = bound_resource_tool_contracts(owner.family)
    library = ScientificToolLibrary.freeze(owner.directory/'tool-information', catalog=owner.tools.catalog(),
        tool_info=True, resource_catalogs={'api': contracts})
    for name, entry_role, resource_role in ((DATA_QUERY_OPERATION, 'launch', 'launch_api'),
                                          (DATA_RESULT_OPERATION, 'results', 'results')):
        declared = next(row for row in actual['api'] if row['name'] == name)
        info = make_tool_info(declared, 'api')
        assert set(info) == {'name', 'description', 'resources', 'instructions'}
        assert info['name'] == name and info['resources'] == 'api'
        assert info['description'] == declared['description']
        assert declared['input_schema'] == EMPTY_ARGUMENTS
        assert (LIBRARY/'api-bvbrc-data-v2.md').read_text().strip() in info['instructions']
        assert (LIBRARY/'api-bvbrc.md').read_text().strip() not in info['instructions']
        selected = [{'name': name, 'resources': 'api'}]
        frozen, = library.resolve_tool_info(selected, contracts)
        invoked, = library.resolve_invocations(selected, contracts)
        assert frozen == info and invoked['instructions'] == info['instructions']
        assert invoked['input_schema'] == EMPTY_ARGUMENTS
        assert invoked['invocation_route'] == {'kind': 'commission', 'routes': [{
            'entry_role': entry_role, 'resource_id': 'selected-bvbrc', 'resource_role': resource_role}]}
        assert name not in owner.tools.catalog()
        with pytest.raises(ValueError, match='contract_changed'):
            library.resolve_invocations(selected, owner.tools.catalog())
        assert all(row['name'] != name for kind in ('local', 'hpc') for row in actual[kind])
    assert all(row['availability'] == 'unknown' for row in owner.family.capabilities())
    assert owner.calls == []
    assert owner.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0


def test_all_reviewed_collection_modes_reach_the_same_real_v2_contracts(owner):
    service = owner.family.api_execution.services['selected-bvbrc']
    assert len(COLLECTIONS) == 22
    for collection in COLLECTIONS:
        for mode in ('page', 'count', 'facet'):
            operands = {}
            if mode == 'facet':
                field = next(name for name, definition in FIELD_REGISTRY[collection]['fields'].items()
                    if definition['facet_supported'])
                operands['facet'] = {'field': field, 'offset': 0, 'limit': 1, 'min_count': 0,
                    'sort': 'index', 'include_missing': True}
            request = query(collection, mode, **operands)
            assert service.launch_catalog(request)[0]['name'] == DATA_QUERY_OPERATION
            assert service.result_catalog(request, selection())[0]['name'] == DATA_RESULT_OPERATION
    assert owner.calls == []


PROJECTIONS = [
    (query(), selection(), [], []),
    (query(mode='count'), selection(), [], []),
    (query(mode='facet', facet={'field': 'genome_id', 'offset': 0, 'limit': 2,
        'min_count': 0, 'sort': 'index', 'include_missing': True}), selection(),
        ['execution_bvbrc_facets'], ['calculate_facet_fractions']),
    (query(fields=['genome_id', 'plasmids']), selection({'family': 'collection_rows',
        'row_indices': [0], 'numeric_fields': ['plasmids'], 'metadata_fields': ['genome_id']},
        page={'offset': 1, 'limit': 1}), ['execution_bvbrc_numeric_rows'], []),
    (query('genome_feature'), selection({'family': 'feature_sequence', 'feature_ids': ['fixture-id'],
        'sequence_kind': 'AA', 'include_sequence_values': True, 'feature_metadata_fields': ['product']}),
        ['execution_bvbrc_feature_sequence_rows'], ['calculate_feature_sequence_counts']),
    (query('bioset_result'), selection({'family': 'molecular_experiment', 'result_ids': ['fixture-id'],
        'measurement_fields': ['counts', 'log2_fc'],
        'metadata_fields': [{'source_level': 'bioset', 'field': 'treatment_name'}]}),
        ['execution_bvbrc_expression_rows'], []),
]


@pytest.mark.parametrize('api_request,selector,additional_facts,additional_calculators', PROJECTIONS)
def test_descriptor_uses_actual_request_selector_and_only_bound_functions(
        owner, monkeypatch, api_request, selector, additional_facts, additional_calculators):
    handoff = launched(owner, api_request)
    target_reader = owner.family.job_progress_provider.targets
    target = target_reader.read_target(handoff, owner.scope)
    assert describe_execution_target(target)['mode'] == api_request['mode']
    before = [tuple(row) for row in owner.store.db.execute('SELECT * FROM runtime_actions')]

    def prohibited(*args, **kwargs):
        pytest.fail('describing a retained target performed work')
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc.encode_native_query', prohibited)
    monkeypatch.setattr('gene_annotation_episode.api_bvbrc.BVBRCDataService.invoke', prohibited)
    descriptor = target_reader.describe_target(handoff, owner.scope, selector=selector)
    assert descriptor['called_operation'] == DATA_QUERY_OPERATION
    assert descriptor['operation'] == api_request['mode']
    assert descriptor['collection'] == api_request['collection'] and descriptor['request'] == api_request
    assert descriptor['request_profile'] == 'solr_query_solr_json_v1'
    assert descriptor['request_media_type'] == 'application/solrquery+x-www-form-urlencoded'
    assert descriptor['expected_response_media_type'] == 'application/solr+json'
    assert descriptor['observed_response_media_type'] == 'application/solr+json; charset=utf-8'
    assert descriptor['output_format'] == 'solr_json_envelope_v1'
    assert descriptor['projection'] == selector['projection'] and descriptor['page_selector'] == selector['page']
    assert descriptor['observation_basis'] == 'original_retained_response'
    assert descriptor['status_operations'] == []
    assert descriptor['acquisition_operations'] == [DATA_RESULT_OPERATION]
    extractor, = descriptor['extractors']
    assert extractor['return_fields'] == PUBLISHER_FIELDS
    assert extractor['return_fact_sources'] == ['execution_result_refs',
        'execution_bvbrc_pages', 'execution_bvbrc_counts', *additional_facts]
    assert set(extractor['return_fact_sources'][1:]) <= set(FACT_SOURCES)
    assert extractor['parser'] == 'gene_annotation_episode.bvbrc_data_readers.parse_data_snapshot'
    assert extractor['implementation'] == 'gene_annotation_episode.bvbrc_data_publication.publish_bvbrc_data'
    assert extractor['service_implementation'] == 'gene_annotation_episode.api_bvbrc.BVBRCDataService.publish'
    assert extractor['projection_implementation'] == 'gene_annotation_episode.bvbrc_data_views.project_bvbrc_data_facts'
    assert [name.rsplit('.', 1)[1] for name in extractor['calculators']] == [
        'calculate_page_counts', *additional_calculators]
    if selector['projection']['family'] == 'feature_sequence':
        assert extractor['metadata_extractors'] == [
            'gene_annotation_episode.bvbrc_data_feature_sequences.extract_feature_sequence_join']
    elif selector['projection']['family'] == 'molecular_experiment':
        assert extractor['metadata_extractors'] == [
            'gene_annotation_episode.bvbrc_data_molecular.extract_molecular_experiment_rows']
    else:
        assert extractor['metadata_extractors'] == []
    assert 'extract_collection_rows' not in json.dumps(descriptor)
    for name in [extractor['parser'], extractor['implementation'], extractor['projection_implementation'],
                 *extractor['metadata_extractors'], *extractor['calculators']]:
        assert callable(function(name))
    if api_request['mode'] == 'facet':
        assert extractor['calculator_parameters'] == {
            'gene_annotation_episode.bvbrc_data_calculators.calculate_facet_fractions': {
                'denominator_policy': 'same_response_exact_document_count'}}
    else:
        assert extractor['calculator_parameters'] == {}
    assert len(owner.calls) == 1
    assert [tuple(row) for row in owner.store.db.execute('SELECT * FROM runtime_actions')] == before
    descriptor['projection']['family'] = 'changed'
    assert target_reader.describe_target(handoff, owner.scope, selector=selector)['projection'] == selector['projection']


def test_no_selector_does_not_invent_a_v2_result_projection(owner):
    handoff = launched(owner, query(mode='count'))
    descriptor = owner.family.job_progress_provider.targets.describe_target(handoff, owner.scope)
    assert descriptor['mode'] == 'count' and descriptor['projection'] is None
    assert descriptor['acquisition_operations'] == descriptor['extractors'] == []
    assert len(owner.calls) == 1


def test_result_descriptor_fields_match_actual_selected_publication(owner):
    handoff = launched(owner, query(mode='count'))
    selector = selection()
    descriptor = owner.family.job_progress_provider.targets.describe_target(
        handoff, owner.scope, selector=selector)
    assignment = {'version': 'execution_results_assignment_v1',
        'handoff_ref': handoff, 'selector': selector}
    receiver = context(owner, 'results', assignment, 'result-reader')
    assert [row['name'] for row in owner.family.catalog(receiver)] == [DATA_RESULT_OPERATION]
    outcome = selected_call(owner, receiver, DATA_RESULT_OPERATION)
    result = outcome['result']
    extractor, = descriptor['extractors']
    assert set(result) == set(extractor['return_fields']) | {'acquisition_receipt', 'handoff_ref'}
    assert result['mode'] == 'count' and result['parse_status'] == 'complete'
    assert result['requested_projection_complete'] is True and result['projection_failures'] == []
    from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
    grading, = source_tool_gradings(owner.store, result['source_ref'])
    assert grading['parse_result']['sheet']['count']['reported_value'] == 2
    assert grading['page_components']['native_row_count'] == 0
    assert len(owner.calls) == 1  # Results reused the original immediate response.


def test_legacy_descriptor_and_instruction_entry_remain_unchanged(owner):
    original = {'collection': 'genome', 'filters': []}
    handoff = launched(owner, original)
    descriptor = owner.family.job_progress_provider.targets.describe_target(handoff, owner.scope, selector={})
    assert descriptor == {'resource_kind': 'api', 'service_or_program': 'bvbrc_data',
        'operation': 'genome', 'output_format': 'bvbrc_json', 'called_operation': QUERY_OPERATION,
        'status_operations': [], 'acquisition_operations': [RESULT_OPERATION], 'extractors': [{
            'operation': RESULT_OPERATION, 'implementation': 'gene_annotation_episode.api_bvbrc.BVBRCDataService.publish',
            'return_fields': ['source_ref', 'records'], 'return_fact_sources': ['execution_result_refs']}]}
    manifest = json.loads((LIBRARY/'index.json').read_text())
    old = next(row for row in manifest['entries'] if row['entry_id'] == 'launch-api-bvbrc')
    assert hashlib.sha256((LIBRARY/'api-bvbrc.md').read_bytes()).hexdigest() == (
        'c4c0a79fb811713f99db5d985c2abc88a2aad96fa2e3209c3571efeb026576a9')
    assert hashlib.sha256(json.dumps(old, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == (
        '523f1b48b93fb467045a0314fd2e2766980e680e97cb7ac912e99559ee69187a')
    current = next(row for row in manifest['entries'] if row['entry_id'] == 'launch-api-bvbrc-data-v2')
    assert current['tool_names'] == [DATA_QUERY_OPERATION, DATA_RESULT_OPERATION]
    legacy = next(row for row in workflow_execution_catalogs()['api'] if row['name'] == QUERY_OPERATION)
    instructions = make_tool_info(legacy, 'api')['instructions']
    assert (LIBRARY/'api-bvbrc.md').read_text().strip() in instructions
    assert (LIBRARY/'api-bvbrc-data-v2.md').read_text().strip() not in instructions


def test_frozen_v2_information_reopens_without_replacing_original_instructions(owner, monkeypatch):
    contracts = bound_resource_tool_contracts(owner.family)
    directory = owner.directory/'frozen-information'
    library = ScientificToolLibrary.freeze(directory, catalog=owner.tools.catalog(),
        tool_info=True, resource_catalogs={'api': contracts})
    selected = [{'name': DATA_RESULT_OPERATION, 'resources': 'api'}]
    original = library.resolve_tool_info(selected, contracts)
    frozen_bytes = (directory/'index.json').read_bytes()
    monkeypatch.setattr('gene_annotation_episode.tool_information._documents',
        lambda *_: 'A later manual is not retroactive information.')
    restored = ScientificToolLibrary.freeze(directory, catalog=owner.tools.catalog(),
        tool_info=True, resource_catalogs={'api': contracts})
    assert restored.resolve_tool_info(selected, contracts) == original
    assert (directory/'index.json').read_bytes() == frozen_bytes
