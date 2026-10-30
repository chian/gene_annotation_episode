"""Actual tiny alignments under scripted method_loop decisions; no model run."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import sqlite3
from types import MappingProxyType

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.native_timing_information import (MEASUREMENT_SCHEMA, NativeTimingInformation,
    measurement_fields, read_measurement, validate_native_measurements)
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.resource_estimation import ESTIMATE_SCHEMA, ResourceToolEstimator
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider, obj


UNIT = 7  # Explicit engineering fixture, not a new production weight.


def tool(name, arguments):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments}, 'report_update': {}}


def commission(target, form):
    return {'selection': {'kind': 'child',
        'goal': 'Iteratively examine an alignment and its execution measurements; revise what is known from outcomes.',
        'purpose': 'Return the requested recorded duration information for later investigation choices.',
        'scope': {'subject_refs': [target]}, 'schema_json': json.dumps(form), 'initial_report_json': '{}'},
        'report_update': {}}


def zero_science(store, scope):
    return 0


def setup(tmp_path):
    history = tmp_path/'history.sqlite'
    created = RunHistory(history); created.close()
    store = Store(tmp_path/'workspace')
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    tools = ToolRegistry(store, native_statistics=OrdinaryExecutionStatistics(history, 'fixture-host', tmp_path/'receipts'))
    return store, tools, target, history


def run(store, tools, provider, path, *, counts=(3, 3), resume=False, binding=None, omit_binding=False, estimates=False):
    return asyncio.run(run_workflow(store, tools, provider=provider, run_dir=path, resume=resume,
        project_credit=zero_science, controller_factory=lambda path, initial:
            FixtureController(str(path), initial, counts[0] if len(path) == 1 else counts[1]),
        native_timing_information=None if omit_binding else binding or NativeTimingInformation(UNIT),
        resource_estimator=ResourceToolEstimator() if estimates else None,
        initial_known_record_refs=[]))


def measurement_form(*, with_forecasts=False):
    fields = {'science': {'type': 'number', 'x-source': 'credit'},
        'monitoring': {'type': 'number', 'x-source': 'monitoring_information_credit'},
        'durations': {'type': 'array', 'items': deepcopy(MEASUREMENT_SCHEMA),
                      'x-source': 'native_execution_measurements'}}
    if with_forecasts:
        fields['forecasts'] = {'type': 'array', 'items': deepcopy(ESTIMATE_SCHEMA),
                              'x-source': 'resource_tool_estimates'}
    return obj(fields)


def test_actual_duration_passes_requested_form_and_frozen_inheritance_without_scientific_gain(tmp_path):
    store, tools, target, history = setup(tmp_path)
    try:
        form = measurement_form(with_forecasts=True)
        validate_closed_schema(form)
        ref, duration = [], []
        def child_after_native(context):
            assert context['current_credit'] == 0
            assert context['monitoring_information_credit'] == UNIT
            assert context['controller']['scores'] == [0]
            output = context['last_local_outcome']
            ref.extend(output['native_execution_refs'])
            duration.append(output['result']['local_job']['elapsed_seconds'])
            assert output['result']['local_job']['native_execution_ref'] == ref[0]
            return tool('episode.monitoring_information', {'limit': 5, 'offset': 0})
        def repeated_read(context):
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == UNIT
            return tool('state.query', {'refs': ref})
        def parent_receives(context):
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == UNIT
            assert context['controller']['scores'] == [0]
            returned = context['child_reports'][0]
            assert returned['science'] == 0 and returned['monitoring'] == UNIT
            actual, = returned['durations']
            assert actual['receipt_ref'] == ref[0] and actual['elapsed_seconds'] == duration[0]
            assert actual['cpu_threads'] is None
            forecast, = returned['forecasts']
            assert forecast['phase'] == 'pairwise_sequence_alignment'
            assert forecast['successful_duration_samples'] == 1
            assert forecast['expected_total_seconds'] == duration[0]
            return commission(target, form)
        def inherited_read(context):
            assert context['current_credit'] == context['monitoring_information_credit'] == 0
            return tool('state.query', {'refs': ref})
        def inherited_monitoring(context):
            assert context['monitoring_information_credit'] == 0
            assert context['last_local_outcome']['result']['records'][0]['measurement']['statistic']['elapsed_seconds'] == duration[0]
            return tool('episode.monitoring_information', {'limit': 5, 'offset': 0})
        def inherited_again(context):
            assert context['last_local_outcome']['result']['native_execution_measurements'] == []
            return tool('state.query', {'refs': ref})
        def parent_after_second(context):
            assert context['monitoring_information_credit'] == UNIT
            assert context['child_reports'][-1]['monitoring'] == 0
            assert context['child_reports'][-1]['durations'] == []
            return tool('episode.monitoring_information', {'limit': 5, 'offset': 0})
        provider = ScriptedProvider([commission(target, form),
            tool('sequence.align', {'query_ref': target, 'reference_ref': target, 'molecule': 'protein', 'mode': 'global'}),
            child_after_native, repeated_read, parent_receives, inherited_read,
            inherited_monitoring, inherited_again, parent_after_second])
        result = run(store, tools, provider, tmp_path/'run', estimates=True)
        assert result['credit'] == 0 and result['completed_actions'] == 3 and result['episode_count'] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 9
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 9
        assert store.count('native_execution') == 1 and store.count('observation') == 1
        with sqlite3.connect(history) as db:
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
        assert len(set(provider.released)) == 3
        before = store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
        assert run(store, tools, ScriptedProvider([]), tmp_path/'run', resume=True, estimates=True) == result
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == before
        assert store.count('native_execution') == 1
    finally:
        store.close()


def test_receipt_not_requested_by_parent_does_not_cross_with_child_credit(tmp_path):
    store, tools, target, history = setup(tmp_path)
    try:
        form = obj({'monitoring': {'type': 'number', 'x-source': 'monitoring_information_credit'}})
        def parent(context):
            assert context['child_reports'][0]['monitoring'] == UNIT
            assert context['monitoring_information_credit'] == 0  # No duration receipt was returned.
            return tool('episode.monitoring_information', {'limit': 5, 'offset': 0})
        provider = ScriptedProvider([commission(target, form),
            tool('sequence.align', {'query_ref': target, 'reference_ref': target, 'molecule': 'protein', 'mode': 'local'}),
            tool('episode.monitoring_information', {'limit': 5, 'offset': 0}), parent])
        result = run(store, tools, provider, tmp_path/'run', counts=(2, 2))
        assert result['credit'] == 0
        root = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1").fetchone()[0]
        assert store.db.execute('''SELECT count(*) FROM runtime_record_receipts r JOIN records s ON s.id=r.record_ref
            WHERE r.episode_id=? AND s.record_type='native_execution' ''', (root,)).fetchone()[0] == 0
        with sqlite3.connect(history) as db:
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
    finally:
        store.close()


def test_failed_scientific_publication_preserves_actual_timing_without_completing_failed_action(tmp_path, monkeypatch):
    store, tools, target, history = setup(tmp_path)
    try:
        def publication_failure(*args):
            raise ContractError('injected_scientific_publisher_failure')
        monkeypatch.setattr(tools, '_align_one', publication_failure)
        def after_failure(context):
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == UNIT
            assert context['controller']['scores'] == []
            assert context['last_local_outcome']['status'] == 'invalid'
            assert context['feedback']['code'] == 'injected_scientific_publisher_failure'
            assert store.count('observation') == 0
            return tool('episode.monitoring_information', {'limit': 5, 'offset': 0})
        provider = ScriptedProvider([
            tool('sequence.align', {'query_ref': target, 'reference_ref': target, 'molecule': 'protein', 'mode': 'global'}),
            after_failure])
        result = run(store, tools, provider, tmp_path/'run', counts=(1, 1))
        assert result['credit'] == 0 and result['completed_actions'] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        assert store.count('native_execution') == 1 and store.count('observation') == 0
        with sqlite3.connect(history) as db:
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
    finally:
        store.close()


def test_timing_reference_fields_are_exact_and_not_biological_entities(tmp_path):
    store, tools, target, history = setup(tmp_path)
    try:
        outcome = tools.execute('sequence.align', {'query_ref': target, 'reference_ref': target,
            'molecule': 'protein', 'mode': 'global'})
        ref, = outcome['native_execution_refs']
        record = store.get(ref)
        values = measurement_fields(ref, read_measurement(store, ref), operation=record['operation'])
        validate_native_measurements(store, MappingProxyType(values), schema=MEASUREMENT_SCHEMA)
        wrong = {**values, 'elapsed_seconds': values['elapsed_seconds']+1}
        with pytest.raises(ReportBoundaryError, match='differ from their receipt'):
            validate_native_measurements(store, MappingProxyType(wrong), schema=MEASUREMENT_SCHEMA)
        with pytest.raises(ContractError, match='semantic_value_requires_entity_reference'):
            store.put('hypothesis', {'subject_refs': [target], 'predicate': 'biological_role',
                'value': {'type': 'reference', 'ref': ref}, 'context_refs': []}, origin='reasoning')
        payload = {k:v for k,v in record.items() if k not in {'id', 'record_type', 'origin'}}
        with pytest.raises(ContractError, match='native_execution_requires_native_tool_origin'):
            store.put('native_execution', payload, origin='external')
        measured = read_measurement(store, ref)
        mislabeled = replace(measured, execution_class=replace(measured.execution_class, phase='protein_homology_search'))
        artifact = store.artifact(json.dumps(mislabeled.as_record()), 'application/json')
        with pytest.raises(ContractError, match='native_execution_operation_phase_mismatch'):
            store.put('native_execution', {**payload, 'measurement_artifact_ref': artifact}, origin='tool')
        assert tools.execute('state.query', {'kind': 'native_execution', 'offset': 0, 'limit': 5})[
            'result']['records'][0]['measurement']['statistic']['elapsed_seconds'] == values['elapsed_seconds']
    finally:
        store.close()


def test_interruption_restores_original_native_binding_receipts_and_observation_prefix(tmp_path):
    store, tools, target, history = setup(tmp_path)
    try:
        path = tmp_path/'run'
        selected = tool('sequence.align', {'query_ref': target, 'reference_ref': target,
            'molecule': 'protein', 'mode': 'global'})
        with pytest.raises(asyncio.CancelledError):
            run(store, tools, ScriptedProvider([selected, asyncio.CancelledError()]), path, counts=(2, 2))
        original_action = store.db.execute('SELECT result,credit FROM runtime_actions').fetchone()
        original_observation = store.db.execute('SELECT observation FROM runtime_observations').fetchone()[0]
        assert store.db.execute('SELECT state FROM runtime_runs').fetchone()[0] == 'interrupted'
        ref, = json.loads(original_action[0])['native_execution_refs']
        with sqlite3.connect(history) as db:
            original_statistics = db.execute('SELECT * FROM run_statistics').fetchall()
        def resumed(context):
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == UNIT
            assert context['controller']['scores'] == [0]
            return tool('state.query', {'refs': [ref]})
        # Omitted binding is recovered from its original manifest, not dropped
        # or silently replaced by a new numeric setting.
        result = run(store, tools, ScriptedProvider([resumed]), path, counts=(2, 2),
                     resume=True, omit_binding=True)
        assert result['credit'] == 0 and result['completed_actions'] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2
        assert tuple(store.db.execute('SELECT result,credit FROM runtime_actions ORDER BY decision_index LIMIT 1').fetchone()) == tuple(original_action)
        assert store.db.execute('SELECT observation FROM runtime_observations ORDER BY unit_index LIMIT 1').fetchone()[0] == original_observation
        assert store.count('native_execution') == 1
        with sqlite3.connect(history) as db:
            assert db.execute('SELECT * FROM run_statistics').fetchall() == original_statistics
        from gene_annotation_episode.runtime import WorkflowError
        with pytest.raises(WorkflowError, match='replace_native_timing_information'):
            run(store, tools, ScriptedProvider([]), path, counts=(2, 2), resume=True,
                binding=NativeTimingInformation(UNIT+1))
    finally:
        store.close()


def test_prior_run_statistics_inform_decision_before_native_work_and_preserve_original_forecast(tmp_path):
    training = tmp_path/'training'
    training.mkdir()
    train_store, train_tools, train_target, history = setup(training)
    try:
        trained = train_tools.execute('sequence.align', {'query_ref': train_target,
            'reference_ref': train_target, 'molecule': 'protein', 'mode': 'global'})
        prior_seconds = trained['result']['local_job']['elapsed_seconds']
    finally:
        train_store.close()
    with Store(tmp_path/'new-workspace') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        tools = ToolRegistry(store, native_statistics=OrdinaryExecutionStatistics(
            history, 'fixture-host', tmp_path/'new-receipts'))
        arguments = {'query_ref': target, 'reference_ref': target, 'molecule': 'protein', 'mode': 'global'}
        def before_work(context):
            estimate, = context['resource_tool_estimates']
            assert estimate['status'] == 'available' and estimate['successful_duration_samples'] == 1
            assert estimate['expected_total_seconds'] == prior_seconds
            assert estimate['cpu_threads'] is None
            assert context['current_credit'] == context['monitoring_information_credit'] == 0
            assert store.count('native_execution') == 0 and store.count('observation') == 0
            assert not list(store.path.glob('.native-sequence-*'))
            with sqlite3.connect(history) as db:
                assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
            return tool('sequence.align', arguments)
        def after_work(context):
            assert context['monitoring_information_credit'] == UNIT and context['current_credit'] == 0
            estimate, = context['resource_tool_estimates']
            actual = context['last_local_outcome']['result']['local_job']['elapsed_seconds']
            assert estimate['successful_duration_samples'] == 2
            assert estimate['expected_total_seconds'] == pytest.approx((prior_seconds+actual)/2)
            original, = context['last_local_outcome']['resource_tool_estimates']
            assert original['successful_duration_samples'] == 1 and original['expected_total_seconds'] == prior_seconds
            assert original['expectation_ref'] != estimate['expectation_ref']
            return tool('episode.monitoring_information', {'limit': 5, 'offset': 0})
        provider = ScriptedProvider([tool('execution.estimate', {'tool': 'sequence.align', 'arguments': arguments}),
                                    before_work, after_work])
        result = run(store, tools, provider, tmp_path/'run', estimates=True)
        assert result['credit'] == 0 and result['completed_actions'] == 3
        assert store.count('native_execution') == store.count('observation') == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        rows = store.db.execute('SELECT result FROM runtime_actions ORDER BY decision_index').fetchall()
        assert json.loads(rows[0][0])['resource_tool_estimates'][0]['successful_duration_samples'] == 1
        assert json.loads(rows[1][0])['resource_tool_estimates'][0]['successful_duration_samples'] == 1
        contexts = [json.loads(row[0]) for row in store.db.execute(
            'SELECT data FROM runtime_estimation_contexts ORDER BY decision_index')]
        assert len(contexts) == 3
        assert contexts[0]['native_expectations'] is None
        assert contexts[1]['native_expectations']['snapshots'][0]['data']['statistics'][0]['complete_duration_count'] == 1
        assert contexts[1]['resource_tool_estimates_at_selection'][0]['expected_total_seconds'] == prior_seconds
        assert contexts[1]['resource_tool_estimates_after_action'][0]['expected_total_seconds'] == prior_seconds
        assert contexts[2]['resource_tool_estimates_at_selection'][0]['successful_duration_samples'] == 2


def test_unknown_prospective_forecast_crosses_form_and_does_not_block_native_work(tmp_path):
    store, tools, target, history = setup(tmp_path)
    history.unlink()  # Deliberately unavailable shared history; no native job exists yet.
    try:
        form = obj({'forecasts': {'type': 'array', 'items': deepcopy(ESTIMATE_SCHEMA),
                                 'x-source': 'resource_tool_estimates'}})
        args = {'query_ref': target, 'reference_ref': target, 'molecule': 'protein', 'mode': 'global'}
        def child_after_estimate(context):
            estimate, = context['resource_tool_estimates']
            assert estimate['status'] == 'history_unavailable'
            assert estimate['expected_total_seconds'] is None and estimate['successful_duration_samples'] == 0
            assert estimate['outcome_support'] is None
            assert not history.exists() and store.count('native_execution') == 0
            return tool('state.query', {'refs': [target]})
        def parent_after_form(context):
            forecast, = context['child_reports'][0]['forecasts']
            assert forecast['status'] == 'history_unavailable' and forecast['expected_total_seconds'] is None
            assert forecast['execution_class_ref'] is not None and forecast['proposal_ref'] is not None
            assert context['monitoring_information_credit'] == 0
            return tool('sequence.align', args)
        provider = ScriptedProvider([commission(target, form),
            tool('execution.estimate', {'tool': 'sequence.align', 'arguments': args}),
            child_after_estimate, parent_after_form])
        result = run(store, tools, provider, tmp_path/'run', counts=(2, 2), estimates=True)
        assert result['credit'] == 0 and result['monitoring_information_credit'] == UNIT
        assert result['completed_actions'] == 2 and store.count('native_execution') == 1
        assert store.count('observation') == 1 and not history.exists()
        receipt, = tools.native_statistics.recovery_directory.glob('*.measurement.json')
        assert json.loads(receipt.read_text())['measurement']['statistic']['outcome'] == 'succeeded'
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
    finally:
        store.close()
