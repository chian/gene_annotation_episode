"""Engineering controls for private presentation and explicit standalone inputs.

These test original field custody and frame selection. They do not calculate
scientific progress or establish a provider-driven workflow.
"""
import json
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('standalone,root_shape', [(False, False), (True, False), (True, True), (False, True)])
def test_private_frame_preserves_original_inputs_and_explicit_standalone_shape(standalone, root_shape):
    from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.presentation_fields import frame_for, annotation_context, attach_native_timing
    controller = {'arms': [], 'annotation_credits': [], 'root_score': 0., 'decision': {'stop': False}, 'scalar_detail': 'retained'}
    report = SimpleNamespace(as_record=lambda: {'original': 'child'},
        contract=SimpleNamespace(measurements={'schema': {'type': 'object'}}))
    view = SimpleNamespace(child_reports=(report,), controller_state=controller)
    credit = {'mode': 'annotation_axis_credit', 'arms': []} if root_shape else 2.5
    credit_view = {'credit': credit, 'source_contributions': [{'finding': 'qualified'}],
        'a101_sheet': {'original_injected': True}, 'proposed_annotations': [], 'comparisons': [],
        'monitoring_information_credit': 3., 'monitoring_information_binding': {'original': 'native-observation'}}
    outcome = {'status': 'partial', 'record_refs': ['source_original'], 'changed_record_refs': [], 'result': {'detail': 'original'}}
    feedback = {'original': 'feedback'}
    state = {'original': 'working-state'}
    journal_calls = []
    def row(*args):
        journal_calls.append(args)
        return {'action': json.dumps({'kind': 'episode_child'})}
    source = SimpleNamespace(path=(('scientific_process', 'standalone'),) if standalone else
        (('annotation', 'root'), ('scientific_process', 'commissioned')),
        scope={'original': 'scope'}, report_values={'original': 'interpretation'},
        interpret_schema={'type': 'object'}, last_outcome_index=4, episode_id='scientific',
        workflow=SimpleNamespace(journal=SimpleNamespace(row=row),
            annotation_context=lambda scope, source: {'actual_annotation_context': scope}))
    frame = frame_for(source, view, credit_view, state, outcome, feedback)
    if root_shape:
        assert frame['state'] == {}
        assert frame['reports'] == () and len(frame['forms']) == 1
        assert frame['controller_state'] == {key: controller[key] for key in ('arms', 'annotation_credits', 'root_score', 'decision')}
        assert frame['outcome'] == {'status': 'partial', 'record_ref_count': 1, 'changed_record_ref_count': 0}
        assert frame['feedback'] is None
        assert frame['credit'] == {'mode': 'annotation_axis_credit', 'root_score': 0.}
        assert annotation_context(source, frame, credit_view) == {'proposed_annotations': [], 'annotation_comparisons': []}
        assert journal_calls == [('runtime_actions', 'scientific', 4)]
    else:
        assert frame['state'] is state and frame['outcome'] is outcome and frame['feedback'] is feedback
        assert frame['reports'] is view.child_reports and len(frame['forms']) == 2
        assert frame['credit'] == 2.5 and frame['controller_state'] == controller
        assert annotation_context(source, frame, credit_view) == {'actual_annotation_context': source.scope}
        assert journal_calls == []
    expected = {'source_contributions': credit_view['source_contributions']}
    if standalone or root_shape:
        expected['a101_sheet'] = credit_view['a101_sheet']
    assert frame['completed_work'] == expected
    context = {}
    attach_native_timing(context, credit_view)
    assert context == {key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')}
    assert outcome['result'] == {'detail': 'original'} and state == {'original': 'working-state'}


@pytest.mark.parametrize('root_shape', [False, True])
def test_recorded_context_preserves_original_yield_table_selection(monkeypatch, root_shape):
    from gene_annotation_episode.episodic_workflow.root.a108.scientific_process import standalone_presentation as owner
    calls = []
    journal = object()
    source = SimpleNamespace(workflow=SimpleNamespace(journal=journal), episode_id='original')
    parameters = {'original': 'yield-parameters'}
    context = {'current_credit': {'mode': 'annotation_axis_credit', 'arms': []} if root_shape else 2.5,
               'controller': {'arms': [{'original': 'saved-arm'}]}}
    monkeypatch.setattr(owner, 'yield_table', lambda *args, **kwargs: calls.append((args, kwargs)) or {'original': 'ordinary-table'})
    table = owner.decision_yield_table(source, context, 4, parameters)
    if root_shape:
        assert table == {'version': 'annotation_axis_yield_table_v1', 'rows': context['controller']['arms'],
            'forecast_unit': 'another_whole_axis_invocation', 'source': 'actual_root_controller'}
        assert calls == []
    else:
        assert table == {'original': 'ordinary-table'}
        assert calls == [((journal, 'original'), {'before': 4, 'parameters': parameters})]
