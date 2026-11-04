"""Real workbook jobs through scripted episode decisions; no scientific/model claim."""
from dataclasses import asdict, replace
import json
import sqlite3

import pytest

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_timing_information import read_measurement
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory
from test_native_timing_information_runtime import (UNIT, commission, measurement_form, run, setup, tool)
from test_runtime import ScriptedProvider
from test_spreadsheet_tools import workbook


def source(store, path):
    with store.transaction():
        artifact = store.artifact(path.read_bytes(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        return store.put('source', {'provider': 'synthetic_workbook_fixture', 'accession': None,
            'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
            'version': 'fixture', 'retrieved_at': None}, origin='external')['id']


def selected(reference):
    return {'source_ref': reference, 'sheet_key': 'selected', 'offset': 0, 'limit': 1,
            'where': {'column': 'A', 'match': 'equals', 'value': 'ybhp', 'case_sensitive': False},
            'header_row': 1}


def test_workbook_duration_credit_forms_forecasts_and_scientific_state_agree(tmp_path):
    path, _ = workbook(tmp_path)
    store, tools, target, history = setup(tmp_path)
    try:
        input_source = source(store, path)
        args = selected(input_source)
        durations = {}
        def choose_rows(context):
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == UNIT
            output = context['last_local_outcome']['result']
            assert output['sheets'][0]['sheet_key'] == args['sheet_key']
            durations['xlsx_sheets'] = output['provenance']['local_jobs']['work']['elapsed_seconds']
            return tool('source.xlsx.rows', args)
        def inspect_information(context):
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == 2*UNIT
            output = context['last_local_outcome']['result']
            assert output['rows'][0]['row_number'] == 2 and output['rows'][0]['cells'][0]['value'] == 'YBHP'
            assert output['rows'][0]['cells'][1]['value_is_formula_cache'] is True
            durations['xlsx_rows'] = output['provenance']['local_jobs']['work']['elapsed_seconds']
            assert {item['phase'] for item in context['resource_tool_estimates']} == {'spreadsheet_selection'}
            return tool('episode.monitoring_information', {'limit': 10, 'offset': 0})
        def parent(context):
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == 2*UNIT
            returned, = context['child_reports']
            assert returned['science'] == 0 and returned['monitoring'] == 2*UNIT
            assert {row['operation'] for row in returned['durations']} == set(durations)
            for row in returned['durations']:
                assert row['phase'] == 'spreadsheet_selection'
                assert row['elapsed_seconds'] == durations[row['operation']]
                assert row['query_residues'] is row['reference_residues'] is row['cpu_threads'] is None
                native = store.get(row['receipt_ref'])
                assert native['operands'] == [{'role': 'input_source', 'subject_ref': input_source}]
                actual = read_measurement(store, row['receipt_ref'])
                with sqlite3.connect(history) as db:
                    statistic = json.loads(db.execute('SELECT data FROM run_statistics WHERE attempt_sha256=?',
                        (actual.statistic.attempt_sha256,)).fetchone()[0])
                assert statistic['elapsed_seconds'] == row['elapsed_seconds']
            assert len(returned['forecasts']) == 2
            assert all(row['successful_duration_samples'] == 1 for row in returned['forecasts'])
            return tool('execution.estimate', {'tool': 'source.xlsx.rows', 'arguments': args})
        provider = ScriptedProvider([commission(target, measurement_form(with_forecasts=True)),
            tool('source.xlsx.sheets', {'source_ref': input_source}), choose_rows, inspect_information, parent])
        result = run(store, tools, provider, tmp_path/'run', counts=(2, 3), estimates=True)
        assert result['credit'] == 0 and result['monitoring_information_credit'] == 2*UNIT
        assert result['completed_actions'] == 2 and result['episode_count'] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 5
        assert store.count('native_execution') == 2 and store.count('observation') == 0
        with sqlite3.connect(history) as db:
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 2
            shared = json.dumps(db.execute('SELECT data FROM execution_classes').fetchall())
            shared += json.dumps(db.execute('SELECT data FROM run_statistics').fetchall())
            assert 'YBHP' not in shared and 'ybhp' not in shared and input_source not in shared and target not in shared
        final = json.loads(store.db.execute("SELECT result FROM runtime_actions "
            "WHERE json_extract(action,'$.tool')='execution.estimate' ORDER BY rowid DESC LIMIT 1").fetchone()[0])
        assert final['resource_tool_estimates'][0]['successful_duration_samples'] == 1
        assert final['resource_tool_estimates'][0]['expected_total_seconds'] == durations['xlsx_rows']
    finally:
        store.close()


@pytest.mark.parametrize('bad_string,truncated', [(True, False), (False, True)])
def test_partial_workbook_preserves_rows_and_completed_native_timing(tmp_path, bad_string, truncated):
    path, _ = workbook(tmp_path, bad_string=bad_string, truncated=truncated)
    store, tools, target, history = setup(tmp_path)
    try:
        input_source = source(store, path)
        args = {**selected(input_source), 'limit': 10, 'where': None}
        def after_partial(context):
            assert context['last_local_outcome']['status'] == 'partial'
            assert context['last_local_outcome']['result']['rows'][1]['cells'][0]['value'] == 'YBHP'
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == UNIT
            assert context['controller']['scores'] == [0]
            return tool('episode.monitoring_information', {'limit': 10, 'offset': 0})
        result = run(store, tools, ScriptedProvider([tool('source.xlsx.rows', args), after_partial]),
            tmp_path/'run', counts=(2, 2), estimates=True)
        assert result['credit'] == 0 and result['monitoring_information_credit'] == UNIT
        assert result['completed_actions'] == 2 and store.count('native_execution') == 1
        assert store.count('observation') == 0
    finally:
        store.close()


def test_bad_sheet_keeps_failed_execution_timing_without_completed_failed_action(tmp_path):
    path, _ = workbook(tmp_path)
    store, tools, target, history = setup(tmp_path)
    try:
        input_source = source(store, path)
        args = {**selected(input_source), 'sheet_key': 'missing'}
        def after_failure(context):
            assert context['last_local_outcome']['status'] == 'failed'
            assert context['feedback']['code'] == 'xlsx_source_or_selection_invalid'
            assert context['feedback']['category'] == 'execution'
            assert context['feedback']['detail'] == 'xlsx_available_sheet_key_required'
            assert context['controller']['scores'] == []
            assert context['current_credit'] == 0 and context['monitoring_information_credit'] == UNIT
            return tool('episode.monitoring_information', {'limit': 10, 'offset': 0})
        result = run(store, tools, ScriptedProvider([tool('source.xlsx.rows', args), after_failure]),
            tmp_path/'run', counts=(1, 1), estimates=True)
        assert result['credit'] == 0 and result['completed_actions'] == 1
        assert result['monitoring_information_credit'] == UNIT and store.count('native_execution') == 1
        with sqlite3.connect(history) as db:
            statistic = json.loads(db.execute('SELECT data FROM run_statistics').fetchone()[0])
            assert statistic['outcome'] == 'failed' and statistic['elapsed_seconds'] > 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
    finally:
        store.close()


def test_spreadsheet_compatibility_uses_technical_features_not_biological_labels(tmp_path):
    path, _ = workbook(tmp_path)
    binding = OrdinaryExecutionStatistics(tmp_path/'absent.sqlite', 'fixture-host', tmp_path/'receipts')
    policy = LocalJobPolicy.from_config()
    args = {key:value for key,value in selected('unused').items() if key != 'source_ref'}
    first = binding.spreadsheet_class(path, 'rows', args, policy)
    assert first.query_residues is first.reference_residues is first.reference_records is first.cpu_threads is None
    changed_literal = {**args, 'where': {**args['where'], 'value': 'abcd'}}
    assert binding.spreadsheet_class(path, 'rows', changed_literal, policy) == first
    for changed in ({'offset': 1}, {'limit': 2}, {'header_row': None}, {'where': None},
                    {'where': {**args['where'], 'value': 'longer'}}):
        assert binding.spreadsheet_class(path, 'rows', {**args, **changed}, policy).ref != first.ref
    assert binding.spreadsheet_class(path, 'sheets', {}, policy).ref != first.ref
    assert replace(binding, resource_id='other-host').spreadsheet_class(path, 'rows', args, policy).ref != first.ref
    renamed = tmp_path/'renamed.xlsx'; renamed.write_bytes(path.read_bytes())
    assert binding.spreadsheet_class(renamed, 'rows', args, policy) == first
    renamed.write_bytes(renamed.read_bytes()+b'\n')
    assert binding.spreadsheet_class(renamed, 'rows', args, policy).ref != first.ref
    assert not binding.history_path.exists() and not binding.recovery_directory.exists()
    with pytest.raises(ValueError, match='unsupported_execution_class'):
        ExecutionClass(**{**asdict(first), 'phase': 'missing', 'backend': None})


def test_returning_history_is_recovered_before_next_forecast_without_another_native_run(tmp_path):
    path, _ = workbook(tmp_path)
    store, tools, target, history = setup(tmp_path)
    history.unlink()
    try:
        input_source = source(store, path)
        args = selected(input_source)
        elapsed = []
        first_result = []
        def restore_history(context):
            assert context['monitoring_information_credit'] == UNIT
            actual = context['last_local_outcome']
            first_result.append(json.dumps(actual, sort_keys=True))
            elapsed.append(actual['result']['provenance']['local_jobs']['work']['elapsed_seconds'])
            assert actual['result']['provenance']['local_jobs']['work']['statistics_export']['state'] == 'unavailable'
            h = RunHistory(history); h.close()
            return tool('execution.estimate', {'tool': 'source.xlsx.rows', 'arguments': args})
        def verify_recovery(context):
            prediction, = context['resource_tool_estimates']
            assert prediction['status'] == 'available' and prediction['successful_duration_samples'] == 1
            assert prediction['expected_total_seconds'] == elapsed[0]
            recovery = context['last_local_outcome']['native_execution_expectations']['statistics_recovery']
            assert recovery['pending'] == recovery['recorded'] == 1
            assert context['monitoring_information_credit'] == UNIT
            return tool('episode.monitoring_information', {'limit': 10, 'offset': 0})
        result = run(store, tools, ScriptedProvider([tool('source.xlsx.rows', args), restore_history, verify_recovery]),
                     tmp_path/'run', estimates=True)
        assert result['credit'] == 0 and result['monitoring_information_credit'] == UNIT
        assert result['completed_actions'] == 3 and store.count('native_execution') == 1
        saved = json.loads(store.db.execute('SELECT result FROM runtime_actions ORDER BY decision_index LIMIT 1').fetchone()[0])
        assert json.dumps(saved, sort_keys=True) == first_result[0]
        with sqlite3.connect(history) as db:
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 1
        assert tools.native_statistics.recover_pending_statistics()['pending'] == 0
    finally:
        store.close()
