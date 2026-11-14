"""Original scientific decision boundary presentation and saved-context custody.

Actual task.next and Store snapshots run; the provider boundary is intercepted
before any selection. These are controlled presentation cases, not new science.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.method_loop.episode import EpisodeView
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.task import ScientificTask
from gene_annotation_episode.episodic_workflow.root.a105.state import Store


class CapturedPresentation(Exception):
    pass


def harness(store, mode, kind, native, *, saved=None):
    source = ScientificTask.__new__(ScientificTask)
    source.path = (('scientific_process', 'head'),) if mode.startswith('standalone') else (('scientific_process', 'parent'), ('scientific_process', 'head'))
    source.episode_id = 'presentation-head'
    source.calls = 0
    source._execution_context = None
    source.scope = store.validate_scope()
    source.report_values, source.report_basis = {}, []
    source.interpret_schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    source.last_outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'feedback': {'qualification': 'missing_measurement_remains_unresolved'}}
    source.last_outcome_index = 0
    source.feedback = source.last_outcome['feedback']
    source.request = SimpleNamespace(goal=SimpleNamespace(as_record=lambda: {'objective': 'Present the original qualified outcome'}), report_contract=None)
    original_credit = {'credit': {'mode': 'annotation_axis_credit'} if mode == 'standalone_vector' else 0,
        'source_contributions': [{'qualification': 'target_correspondence_unresolved'}],
        'retained_finding_count': 0, 'inactive_dependencies': [], 'detail_pages': {},
        'proposed_annotations': [], 'comparisons': []}
    if native:
        original_credit.update(monitoring_information_credit=3, monitoring_information_binding={'scientific_credit': False, 'meaning': 'separate_observation_information'})
    calls = []
    def row(table, episode, index=None):
        if table == 'runtime_model_calls' and saved is not None:
            return {'request': json.dumps({'context': saved, 'schema': {'original_saved_schema': True}}), 'response': '{}'}
        if table == 'runtime_actions' and index == 0:
            return {'action': json.dumps({'kind': kind})}
        return None
    def working_state(actual):
        calls.append('working_state')
        return {'scientific_qualification': 'unresolved_original_subject'}
    def annotation_context(*args, **kwargs):
        calls.append('annotation_context')
        return {'annotation_support': 'separate_support_not_finding_credit'}
    workflow = SimpleNamespace(run_id='presentation-run', inprocess_replay=None, execution_binding=None,
        store=store, journal=SimpleNamespace(row=row, db=store.db, elapsed_view=lambda _: {}),
        working_state=working_state, local_outcome_preview=lambda value, **_: deepcopy(value),
        source_credit_view=lambda _: deepcopy(original_credit), receipt_projection=lambda _: True,
        source_credit_binding=lambda _: {'kind': 'original_scientific_credit'}, pending_work=lambda _: [],
        delivery_status=lambda _: [], controller_binding={'version': 'controlled-original-binding'},
        catalog=lambda *args, **kwargs: [], knowledge=SimpleNamespace(context=lambda: {}),
        job_episode_options=lambda _: None,
        extra_report_sources=lambda _: {}, is_scientific_source=lambda _: True,
        annotation_context=annotation_context, specialist=lambda _: None,
        tools=SimpleNamespace(), action_schema=lambda _: {'original_action_schema': True})
    source.workflow = workflow
    captured = {}
    async def capture(context, schema):
        captured.update(context=deepcopy(context), schema=deepcopy(schema))
        raise CapturedPresentation
    source.call = capture
    controller = {'arms': [], 'annotation_credits': {}, 'root_score': 0.5, 'decision': 'original_decision', 'scalar_extra': 'preserve_for_scientific_scalar'}
    view = EpisodeView(None, 'head', source.path, 0, (), controller, None, source.request)
    return source, view, captured, calls, original_credit


@pytest.mark.parametrize('mode', ['commissioned', 'standalone_scalar', 'standalone_vector'])
@pytest.mark.parametrize('kind', ['tool', 'episode_child'])
@pytest.mark.parametrize('native', [False, True])
def test_actual_next_keeps_scientific_and_optional_presentation_meanings(tmp_path, mode, kind, native):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        store.db.execute('CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT)')
        source, view, captured, calls, credit = harness(store, mode, kind, native)
        before = store.db.total_changes
        with pytest.raises(CapturedPresentation):
            asyncio.run(source.next(view))
        context = captured['context']
        assert calls.count('working_state') == 1
        assert context['_completed_work_axis_results'] == {'source_contributions': credit['source_contributions']}
        assert context['investigation_progress']['retained_finding_count'] == 0
        if mode == 'standalone_vector':
            assert context['working_state'] == {}
            assert context['current_credit'] == {'mode': 'annotation_axis_credit', 'root_score': 0.5}
            assert set(context['controller']) == {'arms', 'annotation_credits', 'root_score', 'decision'}
            assert 'annotation_context' not in calls
            assert context['proposed_annotations'] == [] and context['annotation_comparisons'] == []
        else:
            assert context['working_state']['scientific_qualification'] == 'unresolved_original_subject'
            assert context['current_credit'] == 0
            assert context['controller']['scalar_extra'] == 'preserve_for_scientific_scalar'
            assert context['annotation_support'] == 'separate_support_not_finding_credit'
        if mode == 'standalone_vector' and kind == 'episode_child':
            assert context['last_local_outcome'] == {'status': 'failed', 'record_ref_count': 0, 'changed_record_ref_count': 0}
            assert context['feedback'] is None
        else:
            assert context['last_local_outcome']['status'] == 'failed'
            assert context['feedback']['qualification'] == 'missing_measurement_remains_unresolved'
        if native:
            assert context['monitoring_information_credit'] == 3
            assert context['monitoring_information_binding']['scientific_credit'] is False
        else:
            assert 'monitoring_information_credit' not in context
        assert store.db.total_changes == before


@pytest.mark.parametrize('original_credit', [0.25, {'mode': 'annotation_axis_credit', 'root_score': 1.5}])
def test_saved_model_context_is_not_rebuilt_or_narrowed(tmp_path, original_credit):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        saved = {'current_credit': original_credit, 'original_saved_external_fields': {'a102_sheet': 'historical_presentation_only'}, 'qualification': 'retained_original_meaning'}
        source, view, captured, calls, _ = harness(store, 'commissioned', 'tool', False, saved=saved)
        before = store.db.total_changes
        with pytest.raises(CapturedPresentation):
            asyncio.run(source.next(view))
        assert captured == {'context': saved, 'schema': {'original_saved_schema': True}}
        assert calls == []
        assert store.db.total_changes == before
