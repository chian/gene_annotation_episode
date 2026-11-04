"""Actual API planner/factory owners with local data and no selected work."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import sqlite3
from types import SimpleNamespace

import pytest
from method_loop.durable import DurableExecutionError

from gene_annotation_episode.api_execution_planning import (
    API_CAPTURE_SCHEMA, API_ESTIMATE_RESULT_SCHEMA, ApiExecutionPlanner, RESULT_VERSION)
from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
from gene_annotation_episode.api_timing_records import ApiTimingBinding, ApiTimingLedger
from gene_annotation_episode.assembled_service_setup import (
    bind_assembled_services_with_public_search_timing_planning)
from gene_annotation_episode.domain import ContractError, canonical, validate_schema
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.resource_service_setup import bind_public_search_ports
from gene_annotation_episode.run_statistics import ReportedResultStatistic, RunHistory
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_assembled_service_setup import operands
from test_hmmer_api_operations import FixtureClient, registry
from test_resource_service_setup import forbidden, resources


@pytest.fixture
def planner(tmp_path):
    with Store(tmp_path/'workspace') as store:
        problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        client = FixtureClient()
        tools = ToolRegistry(store, clients=client)
        owner = registry(client)
        history = tmp_path/'reported-history.sqlite'
        RunHistory(history).close()
        binding = ApiTimingBinding(ledger_path=tmp_path/'timing.sqlite', history_path=history,
            resource_id=owner['resource_id'], monitoring_information_unit=.375)
        statistics = ApiReportedStatistics(binding, registry=owner)
        timing = ApiTimingLedger(store=store, run_id='planning-fixture', registry=owner,
            binding=binding, statistics=statistics)
        ports = bind_public_search_ports(store, tools, registry=owner, timing=timing)
        estimator = ResourceToolEstimator.with_reported_results()
        planner = ApiExecutionPlanner(store, run_id='planning-fixture', ports=ports,
            timing=timing, resource_estimator=estimator)
        selected = {'tool': 'public.hmmer.search', 'arguments': {
            'subject_ref': problem['subject_refs'][0], 'algorithm': 'phmmer', 'database': 'fixture'},
            'resource_selection': planner._selection(), 'constraints': {}, 'immutable_input_versions': []}
        scope = store.validate_scope({'subject_refs': problem['subject_refs']})
        yield SimpleNamespace(planner=planner, store=store, tools=tools, client=client, ports=ports,
            timing=timing, statistics=statistics, binding=binding, estimator=estimator,
            selected=selected, scope=scope, history=history,
            baseline_record_count=store.db.execute('SELECT count(*) FROM records').fetchone()[0])


def no_work(h):
    assert h.client.calls == []
    for table in ('provider_jobs', 'public_search_orders', 'public_search_operations',
                  'public_search_publications'):
        assert h.store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    assert h.store.db.execute('SELECT count(*) FROM records').fetchone()[0] == h.baseline_record_count
    assert h.store.count('observation') == h.store.count('assessment') == 0
    with sqlite3.connect(h.binding.ledger_path) as db:
        for table in ('api_timing_orders', 'api_timing_submission_intents',
                      'api_timing_measurements', 'api_timing_export_dispositions'):
            assert db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


def test_real_capture_once_and_exact_request_original_defaults(planner, monkeypatch):
    h = planner
    captures = []
    capture = h.statistics.capture
    def count(request):
        captures.append(deepcopy(request))
        return capture(request)
    monkeypatch.setattr(h.statistics, 'capture', count)
    result = h.planner.estimate(h.selected, scope=h.scope)
    validate_schema(result, API_ESTIMATE_RESULT_SCHEMA)
    assert len(captures) == 1 and result['version'] == RESULT_VERSION
    assert result['arguments'] == h.selected['arguments']
    assert 'parameters' not in result['arguments'] and 'page_size' not in result['arguments']
    assert result['normalized_arguments'] == {**h.selected['arguments'], 'parameters': {}, 'page_size': 50}
    assert result['request'] == captures[0]
    assert result['request_sha256'] == hashlib.sha256(canonical(captures[0]).encode()).hexdigest()
    row, = result['api_reported_execution_forecasts']
    assert row['reported_result_support'] == {'reported_result_count': 0}
    assert row['expected_total_seconds'] is row['outcome_support'] is row['job_ref'] is row['sample_ref'] is None
    assert result['api_timing_planning_disposition']['state'] == 'available'
    assert result['api_execution_options'][0]['proposal_ref'] == row['proposal_ref']
    no_work(h)


def test_original_validation_is_pure_after_history_and_condition_change(planner, monkeypatch):
    h = planner
    original = h.planner.estimate(h.selected, scope=h.scope)
    execution_class = h.statistics.execution_class(original['request'])
    history = RunHistory(h.history)
    try:
        history.record_reported_result(execution_class, ReportedResultStatistic('a'*64, 'b'*64,
            '2026-10-22T00:00:00+00:00', 7.5, None))
    finally:
        history.close()
    learned = h.planner.estimate(h.selected, scope=h.scope)
    assert learned['api_reported_execution_forecasts'][0]['expected_total_seconds'] == 7.5
    assert original['api_reported_execution_forecasts'][0]['expected_total_seconds'] is None
    history = RunHistory(h.history)
    try:
        history.set_condition(operation_sha256='c'*64, resource_id=execution_class.resource_id,
            state='degraded', reason='operator_report', reported_at='2026-10-22T00:01:00+00:00')
    finally:
        history.close()
    changed = h.planner.estimate(h.selected, scope=h.scope)
    assert changed['api_reported_execution_forecasts'][0]['current_condition_state'] == 'degraded'
    assert changed['api_reported_execution_forecasts'][0]['reported_result_support'] == {'reported_result_count': 0}
    # Every current scientific/history/custody read is forbidden during replay.
    for owner, name in ((h.store, 'get'), (h.store, 'validate_scope'), (h.store, 'reference_subset'),
            (h.statistics, 'capture'), (type(h.ports), 'sequence_symbols'), (h.timing, 'retry_exports')):
        monkeypatch.setattr(owner, name, forbidden)
    validated = h.planner.validate_result(original, selected_arguments=h.selected, scope=h.scope)
    assert validated == original and validated is not original
    validated['arguments']['database'] = 'changed'
    assert original['arguments']['database'] == 'fixture'
    no_work(h)


def test_schema_copies_actual_target_contract_and_binds_actual_candidate(planner):
    h = planner
    actual = h.tools.catalog()['public.hmmer.search']['input_schema']
    declared = h.planner.input_schema(actual)
    assert declared['properties']['arguments'] == actual
    assert declared['properties']['arguments'] is not actual
    assert declared['properties']['resource_selection'] == {'const': h.selected['resource_selection']}
    declared['properties']['arguments']['properties']['subject_ref']['description'] = 'changed'
    declared['properties']['resource_selection']['const']['resource_id'] = 'foreign'
    assert h.planner.input_schema(actual)['properties']['arguments'] == actual
    assert h.planner.input_schema(actual)['properties']['resource_selection']['const'] == h.selected['resource_selection']
    no_work(h)


@pytest.mark.parametrize('state', ['missing', 'schema', 'locked', 'unsupported', 'invalid'])
def test_unavailable_and_explicit_invalid_captures_remain_information(planner, monkeypatch, state):
    h = planner
    connection = None
    if state == 'missing':
        h.history.unlink()
    elif state == 'schema':
        h.history.unlink()
        sqlite3.connect(h.history).close()
    elif state == 'locked':
        connection = sqlite3.connect(h.history)
        connection.execute('BEGIN EXCLUSIVE')
    elif state == 'unsupported':
        h.selected['arguments']['parameters'] = {'include_taxonomy': [562]}
    else:
        real = h.statistics.capture
        def invalid(request):
            value = real(request)
            return {**value, 'status': 'invalid_statistics', 'code': 'invalid_statistics', 'snapshots': []}
        monkeypatch.setattr(h.statistics, 'capture', invalid)
    try:
        result = h.planner.estimate(h.selected, scope=h.scope)
    finally:
        if connection is not None:
            connection.close()
    capture, = result['api_reported_execution_expectations']
    assert capture['status'] == ('invalid_statistics' if state == 'invalid' else 'unavailable')
    assert result['api_timing_planning_disposition']['state'] == 'unavailable'
    if state == 'unsupported':
        assert result['api_reported_execution_forecasts'] == result['api_execution_options'] == []
    else:
        row, = result['api_reported_execution_forecasts']
        assert row['reported_result_support'] is row['outcome_support'] is row['expected_total_seconds'] is None
        assert row['status'] == ('invalid_statistics' if state == 'invalid' else 'history_unavailable')
    if state == 'missing':
        assert not h.history.exists()
    no_work(h)


@pytest.mark.parametrize('field', ['request_sha256', 'scope_sha256', 'normalized_arguments',
    'arguments', 'api_execution_options', 'api_reported_execution_forecasts', 'api_timing_planning_disposition'])
def test_original_proposal_relationship_tampering_rejects(planner, field):
    h = planner
    result = h.planner.estimate(h.selected, scope=h.scope)
    if field.endswith('sha256'):
        result[field] = '0'*64
    elif field in {'arguments', 'normalized_arguments'}:
        result[field]['database'] = 'foreign'
    elif field == 'api_timing_planning_disposition':
        result[field]['state'] = 'unavailable'
    elif field == 'api_execution_options':
        result[field][0]['proposal_ref'] = 'execution_proposal_'+'c'*64
    else:
        result[field][0]['expected_total_seconds'] = 99
    with pytest.raises(ContractError, match='api_execution_proposal_conflict'):
        h.planner.validate_result(result, selected_arguments=h.selected, scope=h.scope)
    no_work(h)


@pytest.mark.parametrize('corruption', ['extra', 'class', 'ref', 'support', 'status'])
def test_malformed_original_capture_specific_failure(planner, corruption):
    h = planner
    result = h.planner.estimate(h.selected, scope=h.scope)
    capture = result['api_reported_execution_expectations'][0]
    if corruption == 'extra':
        capture['untyped'] = 'extra'
    elif corruption == 'class':
        capture['execution_classes'][0]['query_residues'] += 1
    elif corruption == 'ref':
        capture['snapshots'][0]['ref'] = 'execution_expectation_'+'0'*64
    elif corruption == 'support':
        capture['snapshots'][0]['data']['history_through_sequence'] = 7
        capture['snapshots'][0]['ref'] = 'execution_expectation_'+hashlib.sha256(
            canonical(capture['snapshots'][0]['data']).encode()).hexdigest()
    else:
        capture['code'] = 'history_unavailable'
    with pytest.raises(ContractError, match='invalid_api_execution_statistics'):
        h.planner.validate_result(result, selected_arguments=h.selected, scope=h.scope)
    no_work(h)


def test_typed_owner_identity_and_equivalent_attachment_replacement(planner):
    h = planner
    base = h.tools.resource_binding()
    h.tools.bind_api_execution_planner(h.planner)
    ports = bind_public_search_ports(h.store, h.tools, registry=h.ports.registry, timing=h.timing)
    equivalent = ApiExecutionPlanner(h.store, run_id=h.planner.run_id, ports=ports,
        timing=h.timing, resource_estimator=h.estimator)
    assert h.tools.bind_api_execution_planner(equivalent) is equivalent
    assert h.tools.api_execution_planner is equivalent and equivalent.ports is ports
    assert h.tools.resource_binding() == base
    with pytest.raises(ContractError, match='identity_conflict'):
        ApiExecutionPlanner(h.store, run_id='foreign-run', ports=ports, timing=h.timing,
            resource_estimator=h.estimator)
    with pytest.raises(ValueError, match='estimator_not_enabled'):
        ApiExecutionPlanner(h.store, run_id=h.planner.run_id, ports=ports, timing=h.timing,
            resource_estimator=ResourceToolEstimator())
    foreign = ToolRegistry(h.store, clients=FixtureClient())
    with pytest.raises(ContractError, match='identity_conflict'):
        equivalent.validate_registry(foreign)
    with pytest.raises(ValueError, match='binding_mismatch'):
        from gene_annotation_episode.hmmer_resource_adapter import HmmerServiceResourceAdapter
        from gene_annotation_episode.episode_journal import Journal
        HmmerServiceResourceAdapter(None, h.store, Journal(h.store, h.planner.run_id), ports=h.ports,
            timing=h.timing, resource_estimator=h.estimator, api_execution_planning=equivalent)
    no_work(h)


def test_factory_freezes_actual_full_map_and_composition_shares_final_owners(resources, tmp_path, monkeypatch):
    r = resources
    from gene_annotation_episode.resource_episodes import HomologyResourceAdapter
    from gene_annotation_episode.episode_journal import Journal
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', lambda adapter: {
        'resource_id': adapter.resource_id, 'kind': 'local', 'availability': 'unknown',
        'observed_at': '2026-10-22T00:00:00+00:00', 'provenance_refs': [],
        'knowledge_entry_ids': [], 'tool_names': []})
    monkeypatch.setattr('subprocess.run', forbidden)
    client = FixtureClient()
    tools = ToolRegistry(r.store, clients=client)
    base = tools.resource_binding()
    binding = ApiTimingBinding(ledger_path=tmp_path/'timing.sqlite', history_path=tmp_path/'history.sqlite',
        resource_id=registry(client)['resource_id'], monitoring_information_unit=.375)
    r.estimator = ResourceToolEstimator.with_reported_results()
    options = {**operands(r), 'tool_catalog': tools.catalog(), 'public_search_registry': registry(client),
        'tool_registry': tools, 'api_timing': binding}
    stale = deepcopy(options['tool_catalog']); stale.pop('state.query')
    with pytest.raises(DurableExecutionError, match='identity_conflict'):
        bind_assembled_services_with_public_search_timing_planning(r.store, **{**options, 'tool_catalog': stale})
    assert tools.api_execution_planner is None and not r.directory.exists()
    application = bind_assembled_services_with_public_search_timing_planning(r.store, **options)
    original = tools.api_execution_planner
    frozen = ScientificToolLibrary(r.directory/'scientific-tool-library')
    assert frozen.resolve(['execution.estimate'], available_catalog=tools.catalog())
    assert tools.resource_binding() == base and client.calls == []
    workflow = SimpleNamespace(store=r.store, tools=tools, run_id=r.run_id)
    composition = compose_episode_bindings(WorkflowServices(workflow), store=r.store,
        journal=Journal(r.store, r.run_id), execution_backend=None,
        descriptors=[item for item in application.episode_binding_descriptors if item['binding_id'] != 'monitor'],
        job_episodes=r.homology, resource_estimator=r.estimator,
        role_credit_bindings=application.role_credit_bindings, directory=r.directory)
    api = next(a for b in composition.bindings if b.as_record()['binding_id'] == 'resource_episodes'
        for a in b.adapters.values() if a.resource_id == registry(client)['resource_id'])
    final = tools.api_execution_planner
    assert final is not original and final.as_record() == original.as_record()
    assert api.api_execution_planning is final and api.ports is final.ports
    assert api.timing is final.timing is composition.api_timing_reader.ledger
    assert composition.api_timing_reader.ports is final.ports
    assert final.resource_estimator is r.estimator and tools.resource_binding() == base
    assert api.as_record()['version'] == 'hmmer_service_resource_adapter_v3'
    assert frozen.resolve(['execution.estimate'], available_catalog=tools.catalog())
    assert client.calls == [] and not binding.history_path.exists()
    assert r.store.db.execute('SELECT count(*) FROM public_search_orders').fetchone()[0] == 0
    assert r.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
    # Direct saved descriptors also install the real callable without invoking
    # the factory. A saved pin mismatch rejects before registry attachment.
    fresh_tools = ToolRegistry(r.store, clients=client)
    saved = [deepcopy(item) for item in application.episode_binding_descriptors if item['binding_id'] != 'monitor']
    altered = deepcopy(saved)
    saved_api = next(item for item in altered if item['binding_id'] == 'resource_episodes')['configuration']['resource_adapters'][1]
    saved_api['api_execution_planning']['preparation_sha256'] = '0'*64
    direct = SimpleNamespace(store=r.store, tools=fresh_tools, run_id=r.run_id)
    args = dict(store=r.store, journal=Journal(r.store, r.run_id), execution_backend=None,
        job_episodes=r.homology, resource_estimator=r.estimator,
        role_credit_bindings=application.role_credit_bindings, directory=r.directory)
    with pytest.raises(DurableExecutionError, match='identity_conflict'):
        compose_episode_bindings(WorkflowServices(direct), descriptors=altered, **args)
    assert fresh_tools.api_execution_planner is None
    direct_composition = compose_episode_bindings(WorkflowServices(direct), descriptors=saved, **args)
    assert fresh_tools.api_execution_planner.timing is direct_composition.api_timing_reader.ledger
    assert fresh_tools.api_execution_planner.ports is direct_composition.api_timing_reader.ports
    assert frozen.resolve(['execution.estimate'], available_catalog=fresh_tools.catalog())
    assert fresh_tools.resource_binding() == base and client.calls == []
