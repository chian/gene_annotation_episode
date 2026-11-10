"""Parent work rows use their original typed receipts and original credit.

Synthetic custody fixtures exercise presentation only. They do not execute a
scientific child, manufacture experimental findings or change an iterator.
"""
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.literature_work_report import (
    _display_cell_results, _display_scoring_results, completed_work, render_completed_work,
)


def _database():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE runtime_actions(run_id,episode_id,decision_index,action,result);
        CREATE TABLE runtime_observations(run_id,episode_id,unit_index,observation);
        CREATE TABLE runtime_report_attempts(
            run_id,parent_episode_id,decision_index,contract,form,failure);
    ''')
    return db


def _returned(db, decision, *, question, credit, form, failure=None, receiver='parent'):
    action = dict(kind='episode_child', role='literature', goal=question,
        purpose='Return source-bound A105 results and unresolved claims.',
        assignment=dict(source_refs=['source_input'], question_context_refs=['hypothesis_input']))
    completion = dict(result_status='returned' if failure is None else 'failed',
        report_delivery='admitted' if failure is None else 'failed',
        ended_by='yield_stop' if failure is None else 'source_failed', failure=failure)
    result = dict(status='completed', child_completion=completion,
        changed_record_refs=form.get('changed_assessment_refs', []),
        record_refs=['retained-only-provenance'])
    properties = {
        'visibility': {'type': 'array', 'items': {'type': 'string'}, 'x-source': 'interpretation_basis_refs'},
        'changed_assessment_refs': {'type': 'array', 'items': {'type': 'string'}, 'x-source': 'changed_assessment_refs'},
        'assay': {'type': 'array', 'x-source': 'literature_assay_grading_cells',
            'items': {'type': 'object', 'properties': {'sheet_ref': {'type': 'string'},
                'component': {'type': 'string'}, 'value': {'type': ['number', 'null']}}}},
        'unresolved_hypothesis_refs': {'type': 'array', 'items': {'type': 'string'}},
        'scientific_state': {'type': 'string', 'enum': ['unresolved', 'partial']},
    }
    contract = {'measurements': {'schema': {'type': 'object', 'properties': properties}}}
    db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)',
        ('run', receiver, decision, json.dumps(action), json.dumps(result)))
    db.execute('INSERT INTO runtime_observations VALUES(?,?,?,?)',
        ('run', receiver, decision, json.dumps({'decision_index': decision,
            'step': {'marginal_credit': credit}})))
    db.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?)',
        ('run', receiver, decision, json.dumps(contract), json.dumps(form),
         None if failure is None else json.dumps(failure)))
    return deepcopy(action), deepcopy(result), deepcopy(form)


def test_child_work_keeps_original_question_result_and_credit_without_historical_bodies():
    with _database() as db:
        form = dict(visibility=['retained-only-provenance'], changed_assessment_refs=['assessment_changed'],
            assay=[dict(sheet_ref='source_sheet', component='measured_effect', value=6.18,
                        unit='per_s', status='point', interpretation={'control': 'source_context_only'},
                        measurement_keys=['retained-native-identity']),
                   dict(sheet_ref='source_sheet', component='effect_precision', value=None,
                        unit='unknown', status='unavailable', reasons=['variance_not_reported'])],
            unresolved_hypothesis_refs=['hypothesis_input'], scientific_state='partial')
        _returned(db, 1, question='Check the native turnover assay.', credit=2.0, form=form)
        _returned(db, 7, question='Resolve construct correspondence.', credit=0.0,
            form={**form, 'changed_assessment_refs': [], 'scientific_state': 'unresolved'})
        _returned(db, 3, question='A different parent private question.', credit=11.0,
            form=form, receiver='other-parent')
        before = list(db.iterdump())
        rows = completed_work(SimpleNamespace(db=db), SimpleNamespace(run_id='run', episode_id='parent'))
        assert list(db.iterdump()) == before
        assert len(rows) == 2
        assert [row['decisions'] for row in rows] == ['1', '7']
        assert [row['original_credit_marks'] for row in rows] == [[2.0], [0.0]]
        assert [row['inputs']['question'] for row in rows] == [
            'Check the native turnover assay.', 'Resolve construct correspondence.']
        assert rows[0]['inputs']['source_refs'] == ['source_input']
        returned = rows[0]['returned_result']
        assert returned['admitted_scoring_sheets'] == [dict(source='literature_assay_grading_cells',
            sheet_ref='source_sheet', results=[dict(component='measured_effect', value=6.18,
                unit='per_s', status='point'), dict(component='effect_precision', value=None,
                unit='unknown', status='unavailable', reasons=['variance_not_reported'])])]
        assert returned['requested_return_values'] == {
            'changed_assessment_refs': ['assessment_changed'],
            'unresolved_hypothesis_refs': ['hypothesis_input'], 'scientific_state': 'partial'}
        assert 'retained-only-provenance' not in json.dumps(rows)
        assert '6.18' in json.dumps(rows)
        assert 'retained-native-identity' not in json.dumps(rows)
        assert 'source_context_only' not in json.dumps(rows)
        assert rows[1]['returned_result']['requested_return_values']['scientific_state'] == 'unresolved'
        assert all('private question' not in json.dumps(row) for row in rows)


def test_failed_child_keeps_complete_failure_and_zero_credit_without_admitting_its_form():
    with _database() as db:
        failure = {'code': 'source_failure', 'message': 'First error line\nSecond error line',
                   'original_response': {'http_status': 503, 'body': '<provider>full error</provider>'}}
        _returned(db, 4, question='Read primary methods.', credit=0, failure=failure,
            form={'scientific_state': 'partial', 'assay': [dict(
                sheet_ref='unadmitted_sheet', component='measured_effect', value=6.18)]})
        rows = completed_work(SimpleNamespace(db=db), SimpleNamespace(run_id='run', episode_id='parent'))
        row, = rows
        assert row['original_credit_marks'] == [0]
        assert row['returned_result']['child_completion']['result_status'] == 'failed'
        assert 'admitted_scoring_sheets' not in row['returned_result']
        assert row['returned_diagnostics']['child_completion_failure'] == failure
        assert row['returned_diagnostics']['report_delivery_failure'] == failure
        assert 'unadmitted_sheet' not in json.dumps(rows)


def test_render_places_child_outcome_beside_its_original_credit():
    with _database() as db:
        _returned(db, 2, question='Check a new source.', credit=-1,
            form={'scientific_state': 'unresolved', 'changed_assessment_refs': ['assessment_revised'],
                  'assay': [dict(sheet_ref='source_original', component='measured_effect',
                                 value=.006, unit='uM', status='point')]})
        rows = completed_work(SimpleNamespace(db=db), SimpleNamespace(run_id='run', episode_id='parent'))
        class Display:
            def inline(self, value):
                return json.dumps(value, sort_keys=True)
        shown = render_completed_work(rows, table=lambda headers, values: (headers, values), display=Display())
        headers, values = shown
        assert headers[-2:] == ('Recorded earned credit', 'Original decisions')
        assert values[0][-2:] == ('-1', '2')
        assert 'Check a new source.' in values[0][1]
        assert 'assessment_revised' in values[0][2]
        assert '0.006' in values[0][2] and 'uM' in values[0][2]


def test_own_saved_grading_results_keep_actual_values_without_repeated_sheet_context():
    with _database() as db:
        cell = dict(component='measured_effect', value=6.18, unit='per_s', status='point',
            source_refs=['source_native'], interpretation={'actual_preparation': 'retained-in-sheet'},
            measurement_keys=['native-measurement-key'])
        own = {
            1: (dict(kind='tool', tool='literature.assay_grading.populate', arguments={}),
                dict(status='completed', result=dict(sheet_ref='source_direct', cells=[cell]))),
            3: (dict(kind='reason', commit={}, evidence_processing=dict(gradings=[
                    {'arguments': json.dumps({'assay_type': 'activity_rate'})}])),
                dict(status='completed', evidence_processing=dict(gradings=[dict(
                    status='completed', result=dict(sheet_ref='source_coupled', cells=[cell]))]))),
            5: (dict(kind='tool', tool='literature.rate.source.populate', arguments={}),
                dict(status='completed', result=dict(sheet_ref='source_native_parser', cells=[cell]))),
        }
        for decision, (action, result) in own.items():
            db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)',
                ('run', 'parent', decision, json.dumps(action), json.dumps(result)))
            db.execute('INSERT INTO runtime_observations VALUES(?,?,?,?)',
                ('run', 'parent', decision, json.dumps({'decision_index': decision,
                    'step': {'marginal_credit': 1 if decision == 3 else 0}})))
        before = list(db.iterdump())
        rows = completed_work(SimpleNamespace(db=db), SimpleNamespace(run_id='run', episode_id='parent'))
        assert list(db.iterdump()) == before
        by_decision = {row['decisions']: row for row in rows}
        literal = dict(component='measured_effect', value=6.18, unit='per_s', status='point')
        assert by_decision['1']['returned_result']['saved_components'] == [literal]
        assert by_decision['3']['returned_result']['saved_gradings'][0]['result']['saved_components'] == [literal]
        assert by_decision['3']['original_credit_marks'] == [1]
        assert by_decision['5']['returned_result']['saved_components'] == [cell]
        assert 'retained-in-sheet' not in json.dumps(by_decision['1']['returned_result'])
        assert 'retained-in-sheet' not in json.dumps(by_decision['3']['returned_result'])


def test_display_factors_only_identical_literal_results_inside_each_sheet():
    shared = dict(value=None, unit='unknown', status='unavailable',
        missing_inputs=[dict(experiment_ref='reference_assay', reason='metric_component_not_selected')])
    cells = [dict(component='reliability', **shared), dict(component='validity', **shared),
             dict(component='precision', **{**shared, 'unit': 'per_min_squared'}),
             dict(component='attribution', **{**shared, 'status': 'partial'}),
             dict(component='relevance', **{**shared, 'missing_inputs': [dict(
                 experiment_ref='reference_other', reason='metric_component_not_selected')]})]
    original = deepcopy(cells)
    shown = _display_cell_results(cells)
    assert cells == original
    assert shown == [dict(components=['reliability', 'validity'], **shared),
                     *cells[2:]]
    assert 'reference_other' in json.dumps(shown)
    assert 'per_min_squared' in json.dumps(shown)
    assert all(name in json.dumps(shown) for name in
               ('reliability', 'validity', 'precision', 'attribution', 'relevance'))


def test_display_factoring_keeps_each_original_sheet_action_question_and_credit():
    with _database() as db:
        form = dict(assay=[dict(sheet_ref='source_sheet', component='assertion_prediction_error',
                               value=None, unit='uM', status='unavailable', reasons=['missing_prediction']),
                          dict(sheet_ref='source_sheet', component='alternative_prediction_error',
                               value=None, unit='uM', status='unavailable', reasons=['missing_prediction']),
                          dict(sheet_ref='source_other_sheet', component='measured_effect',
                               value=.006, unit='uM', status='point')])
        _returned(db, 1, question='Check original report.', credit=1, form=form)
        _returned(db, 3, question='Check revised report.', credit=0, form=form)
        rows = completed_work(SimpleNamespace(db=db), SimpleNamespace(run_id='run', episode_id='parent'))
        original = deepcopy(rows)
        class Display:
            def inline(self, value):
                return json.dumps(value, sort_keys=True)
        _, values = render_completed_work(rows, table=lambda headers, values: (headers, values), display=Display())
        assert rows == original
        assert len(values) == 2
        assert [row[-2:] for row in values] == [('1', '1'), ('0', '3')]
        assert 'Check original report.' in values[0][1]
        assert 'Check revised report.' in values[1][1]
        for row in values:
            shown = row[2]
            assert shown.count('missing_prediction') == 1
            assert 'assertion_prediction_error' in shown and 'alternative_prediction_error' in shown
            assert 'source_sheet' in shown and 'source_other_sheet' in shown
            assert '0.006' in shown and 'uM' in shown


def test_saved_component_display_preserves_structured_values_and_custom_return_fields():
    shared = dict(value=.8, unit='fraction', status='point')
    cells = [dict(component='attributed_fraction', **shared),
             dict(component='condition_response', **shared)]
    result = dict(returned_result={'sheet_ref': 'source_main', 'saved_components': cells},
        saved_gradings=[{'status': 'completed', 'result': {
            'sheet_ref': 'source_assay', 'saved_components': cells}}],
        requested_return_values={'custom': {'saved_components': cells}},
        returned_provider_error={'complete_error': {'saved_components': cells}})
    original = deepcopy(result)
    shown = _display_scoring_results(result)
    assert result == original
    expected = [dict(components=['attributed_fraction', 'condition_response'], **shared)]
    assert shown['returned_result']['saved_components'] == expected
    assert shown['saved_gradings'][0]['result']['saved_components'] == expected
    assert shown['requested_return_values'] == result['requested_return_values']
    assert shown['returned_provider_error'] == result['returned_provider_error']
