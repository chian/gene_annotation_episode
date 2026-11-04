"""Actual optional registry dispatch and original-result replay, entirely offline."""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.api_execution_planning import ApiExecutionPlanner
from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
from gene_annotation_episode.api_timing_records import ApiTimingBinding, ApiTimingLedger
from gene_annotation_episode.domain import ContractError, canonical, validate_schema
from gene_annotation_episode.hmmer_resource_information import api_selection
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.public_search_operations import ProviderJobOperations, PublicSearchPorts
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import ExecutionClass, ReportedResultStatistic, RunHistory
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_hmmer_api_operations import FixtureClient, registry


def configured(path, *, history=True, native=False):
    store = Store(path/'workspace')
    problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    client = FixtureClient()
    ordinary = OrdinaryExecutionStatistics(path/'native.sqlite', 'fixture-native', path/'native-receipts') if native else None
    tools = ToolRegistry(store, clients=client, native_statistics=ordinary)
    reg = registry(client)
    binding = ApiTimingBinding(ledger_path=path/'timing.sqlite', history_path=path/'history.sqlite',
        resource_id=reg['resource_id'], monitoring_information_unit=.25)
    if history:
        RunHistory(binding.history_path).close()
    statistics = ApiReportedStatistics(binding, registry=reg)
    timing = ApiTimingLedger(store=store, run_id='planning-run', registry=reg,
        binding=binding, statistics=statistics)
    operations = ProviderJobOperations(store, tools.remote_searches, registry=reg, timing=timing)
    ports = PublicSearchPorts(reg, operations, PublicSearchResultPublisher(store, tools, operations=operations))
    estimator = ResourceToolEstimator.with_reported_results()
    planner = ApiExecutionPlanner(store, run_id='planning-run', ports=ports,
        timing=timing, resource_estimator=estimator)
    selected = {'tool': 'public.hmmer.search', 'arguments': {'subject_ref': problem['subject_refs'][0],
        'algorithm': 'phmmer', 'database': 'swissprot'}, 'resource_selection': api_selection(reg),
        'constraints': {}, 'immutable_input_versions': []}
    return store, client, tools, planner, selected


@pytest.mark.parametrize('native', [False, True])
def test_actual_catalog_preserves_native_branches_and_exact_bound_target_schema(tmp_path, native):
    store, client, tools, planner, selected = configured(tmp_path, native=native)
    with store:
        original = tools.catalog()
        base_resources = deepcopy(tools.resource_binding())
        assert tools.api_execution_planner is None
        assert tools.bind_api_execution_planner(planner) is planner
        catalog = tools.catalog()
        branches = catalog['execution.estimate']['input_schema']['anyOf']
        if native:
            assert branches[:-1] == original['execution.estimate']['input_schema']['anyOf']
            assert [branch['properties']['tool']['const'] for branch in branches[:-1]] == [
                'sequence.align', 'source.xlsx.sheets', 'source.xlsx.rows']
        else:
            assert 'execution.estimate' not in original
            assert len(branches) == 1
        branch = branches[-1]
        assert branch['properties']['arguments'] == catalog['public.hmmer.search']['input_schema']
        assert branch['properties']['resource_selection'] == {'const': selected['resource_selection']}
        assert branch['required'] == ['tool', 'arguments', 'resource_selection', 'constraints', 'immutable_input_versions']
        assert branch['additionalProperties'] is False
        assert catalog['execution.estimate']['configuration'] == planner.as_record()
        assert tools.resource_binding() == base_resources
        validate_schema(selected, catalog['execution.estimate']['input_schema'])
        branch['properties']['arguments']['properties']['subject_ref']['description'] = 'changed returned map'
        assert tools.catalog()['public.hmmer.search'] == original['public.hmmer.search']
        assert client.calls == []


def test_binding_requires_actual_owner_and_replaces_equal_descriptor_handle(tmp_path):
    store, client, tools, planner, selected = configured(tmp_path)
    with store:
        with pytest.raises(TypeError, match='typed_api_execution_planner_required'):
            tools.bind_api_execution_planner(object())
        tools.bind_api_execution_planner(planner)
        equivalent = ApiExecutionPlanner(store, run_id='planning-run', ports=planner.ports,
            timing=planner.timing, resource_estimator=planner.resource_estimator)
        assert tools.bind_api_execution_planner(equivalent) is equivalent
        assert tools.api_execution_planner is equivalent
        foreign_tools = ToolRegistry(store, clients=client)
        with pytest.raises(ValueError):
            foreign_tools.bind_api_execution_planner(equivalent)
        assert foreign_tools.api_execution_planner is None
        assert client.calls == []


def test_actual_tool_uses_normalized_scope_and_replays_original_after_history_growth(tmp_path):
    store, client, tools, planner, selected = configured(tmp_path)
    with store:
        before = {kind: store.count(kind) for kind in ('observation', 'source', 'native_execution')}
        tools.bind_api_execution_planner(planner)
        original = deepcopy(selected)
        first = tools.execute('execution.estimate', selected, operation_key='first')
        assert first['status'] == 'completed', first
        assert first['record_refs'] == []
        result = first['result']
        assert result['arguments'] == selected['arguments']
        assert result['normalized_arguments'] == {**selected['arguments'], 'parameters': {}, 'page_size': 50}
        assert result['scope_sha256'] == hashlib.sha256(canonical(store.validate_scope(None)).encode()).hexdigest()
        row = store.db.execute('SELECT arguments,scope,result FROM tool_operations WHERE operation_key=?', ('first',)).fetchone()
        assert json.loads(row['arguments']) == original and row['scope'] == 'null'
        assert json.loads(row['result']) == first
        forecast, = result['api_reported_execution_forecasts']
        assert forecast['status'] == 'no_matching_history' and forecast['expected_total_seconds'] is None
        assert forecast['reported_result_support'] == {'reported_result_count': 0}
        execution_class = ExecutionClass(**result['api_reported_execution_expectations'][0]['execution_classes'][0])
        history = RunHistory(planner.timing.binding.history_path, create=False)
        try:
            history.record_reported_result(execution_class, ReportedResultStatistic(
                observation_sha256=hashlib.sha256(b'synthetic-logical-result').hexdigest(),
                source_sha256=hashlib.sha256(b'synthetic-original-witness').hexdigest(),
                observed_at='2026-10-22T12:00:00Z', elapsed_seconds=6, condition_ref=None))
        finally:
            history.close()
        assert tools.execute('execution.estimate', selected, operation_key='first') == first
        second = tools.execute('execution.estimate', selected, operation_key='second')
        assert second['status'] == 'completed', second
        assert second['result']['api_reported_execution_forecasts'][0]['expected_total_seconds'] == 6
        assert json.loads(store.db.execute('SELECT result FROM tool_operations WHERE operation_key=?',
            ('first',)).fetchone()[0]) == first and selected == original
        changed = deepcopy(selected); changed['arguments']['database'] = 'pfam'
        with pytest.raises(ContractError, match='operation_key_reused_for_different_work'):
            tools.execute('execution.estimate', changed, operation_key='first')
        assert client.calls == []
        assert {kind: store.count(kind) for kind in before} == before
        for table in ('provider_jobs', 'public_search_orders', 'public_search_operations'):
            assert store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0


@pytest.mark.parametrize('mode', ['missing_history', 'unsupported_filter'])
def test_unavailable_statistics_complete_information_without_work_gate(tmp_path, mode):
    store, client, tools, planner, selected = configured(tmp_path, history=mode != 'missing_history')
    with store:
        tools.bind_api_execution_planner(planner)
        if mode == 'unsupported_filter':
            selected['arguments']['parameters'] = {'include_taxonomy': [562]}
        result = tools.execute('execution.estimate', selected, operation_key='unavailable')
        assert result['status'] == 'completed', result
        capture, = result['result']['api_reported_execution_expectations']
        assert capture['status'] == 'unavailable'
        assert capture['code'] == ('history_unavailable' if mode == 'missing_history' else 'unsupported_statistics_configuration')
        assert result['result']['api_timing_planning_disposition']['code'] == capture['code']
        assert result['record_refs'] == [] and client.calls == []
        assert store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0


def test_pin_errors_and_malformed_capture_keep_specific_structured_feedback(tmp_path, monkeypatch):
    store, client, tools, planner, selected = configured(tmp_path)
    with store:
        tools.bind_api_execution_planner(planner)
        selected['immutable_input_versions'] = [{'reference': selected['arguments']['subject_ref'],
            'version': 'invented', 'content_sha256': None}]
        failure = tools.execute('execution.estimate', selected, operation_key='bad-pin')
        assert failure['status'] == 'invalid' and failure['feedback']['code'] == 'resource_input_version_conflict'
        selected['immutable_input_versions'] = []
        monkeypatch.setattr(planner.timing.statistics, 'capture', lambda request: {})
        malformed = tools.execute('execution.estimate', selected, operation_key='malformed-capture')
        assert malformed['status'] == 'invalid'
        assert malformed['feedback']['code'] == 'invalid_api_execution_statistics'
        assert malformed['record_refs'] == [] and client.calls == []
