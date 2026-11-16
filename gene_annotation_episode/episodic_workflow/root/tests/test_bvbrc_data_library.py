"""BV-BRC Data v2 information and factual descriptors at actual owner ports.

Transport responses are synthetic. These checks use real catalogs, frozen
information, resource contracts and selected API handoffs, without network,
model decisions, AppService, or a complete parent-result admission claim.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a102.api_bvbrc import BVBRCDataClient, DATA_QUERY_OPERATION, DATA_RESULT_OPERATION, EMPTY_ARGUMENTS, QUERY_OPERATION
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_data_fields import COLLECTIONS, FIELD_REGISTRY
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.episodic_workflow.root.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.episodic_workflow.root.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_information import make_tool_info, workflow_execution_catalogs
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


LIBRARY = Path(__file__).resolve().parents[4]/'gene_annotation_episode/launch_instruction_library'
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
        tools = ToolRegistry(store, run_directory=store.path / 'tool-run')
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


def test_v2_information_resolves_actual_catalog_and_bound_commission_routes(owner):
    actual = workflow_execution_catalogs()
    contracts = bound_resource_tool_contracts(owner.family)
    library = ScientificToolLibrary.freeze(owner.directory/'tool-information', catalog=owner.tools.catalog(),
        resource_catalogs={'api': contracts})
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


def test_frozen_v2_information_reopens_without_replacing_original_instructions(owner, monkeypatch):
    contracts = bound_resource_tool_contracts(owner.family)
    directory = owner.directory/'frozen-information'
    library = ScientificToolLibrary.freeze(directory, catalog=owner.tools.catalog(),
        resource_catalogs={'api': contracts})
    selected = [{'name': DATA_RESULT_OPERATION, 'resources': 'api'}]
    original = library.resolve_tool_info(selected, contracts)
    frozen_bytes = (directory/'index.json').read_bytes()
    monkeypatch.setattr('gene_annotation_episode.tool_information._documents',
        lambda *_: 'A later manual is not retroactive information.')
    restored = ScientificToolLibrary.freeze(directory, catalog=owner.tools.catalog(),
        resource_catalogs={'api': contracts})
    assert restored.resolve_tool_info(selected, contracts) == original
    assert (directory/'index.json').read_bytes() == frozen_bytes
