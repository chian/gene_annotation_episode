"""Original native summary boundaries with real specialist role selection.

All persistence/model/context ports are declared controls. No restoration,
scientific worker, model call, or annotation evidence is produced.
"""
from __future__ import annotations
from contextlib import nullcontext
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a107'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = [('/'.join(filter(None, (prefix, 'execution_job_submission', suffix))), role)
    for prefix in PREFIXES for suffix, role in (('api_job_execution', 'launch_api'), ('local_job_execution', 'launch_local'), ('hpc_job_execution', 'launch_hpc'))]


def observations(home, role, credit_shape):
    from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import EpisodeBindingRegistry
    from gene_annotation_episode.episodic_workflow.root.a107.runtime import Workflow
    episode = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode')
    task = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.task')
    snapshot = task.NativeTask.next.__globals__['_native_decision_snapshot']
    owner = object.__new__(episode.ExecutionEpisode)
    owner.as_record = lambda: {'controlled_descriptor': home}
    owner.decision_context = lambda context, view: {'original_private_context': {'role': context.role, 'failed_information_preserved': True}}
    registry = EpisodeBindingRegistry(); registry.register(owner)
    workflow = object.__new__(Workflow)
    workflow.episode_bindings, workflow.receipts = registry, None
    workflow.run_id, workflow.controller_binding = 'controlled-summary', {'original_controller': True}
    # Registry.for_path explicitly supports standalone invocation of one actual
    # bound private owner. Keep that real path selector instead of mocking it.
    path = ((role, 'controlled-standalone'),)
    workflow.store = SimpleNamespace(read_snapshot=nullcontext, get=lambda reference: (_ for _ in ()).throw(AssertionError('unexpected_record_read')))
    original_feedback = {'status': 'invalid', 'detail': 'original_failed_information'}
    outcome = {'status': 'invalid', 'record_refs': [], 'feedback': original_feedback}
    workflow.working_state = lambda source: {'last_original_state': 'failed'}
    workflow.local_outcome_preview = lambda value, decision_index: deepcopy(value)
    row = SimpleNamespace(fetchone=lambda: None)
    workflow.journal = SimpleNamespace(db=SimpleNamespace(execute=lambda *args: row),
        elapsed_view=lambda episode_id: {'original_elapsed_information': 2.5}, row=lambda *args: None)
    scalar = {'credit': -0.25, 'operational_credit': -0.25}
    shaped = {'credit': {'mode': 'annotation_axis_credit'}, 'axis_components': {'retained_shape': True}}
    workflow.source_credit_view = lambda source: deepcopy(scalar if credit_shape == 'scalar' else shaped)
    workflow.source_credit_binding = lambda source: {'original_credit_binding': credit_shape}
    workflow.pending_work = lambda source: []
    workflow.delivery_status = lambda episode_id: {'status': 'unavailable'}
    workflow.catalog = lambda scope, source: []
    workflow.knowledge = SimpleNamespace(context=lambda: {'original_knowledge': []})
    workflow.job_episode_options = lambda source: []
    workflow.extra_report_sources = lambda source: {'original_extra': {'type': 'reference_array'}}
    workflow.tools = SimpleNamespace()
    workflow.annotation_context = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('operational_owner_reached_scientific_context'))
    schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    message = SimpleNamespace(as_record=lambda: {'episode_assignment': {}})
    request = SimpleNamespace(goal=SimpleNamespace(as_record=lambda: {'goal_id': 'original-goal', 'objective': 'preserve boundary'}),
        report_contract=None, message=message, as_record=lambda: {'message': message.as_record()})
    source = SimpleNamespace(workflow=workflow, path=path, episode_id='controlled-native', scope={'subject_refs': []},
        request=request, last_outcome=outcome, last_outcome_index=0, feedback=original_feedback,
        report_values={}, interpret_schema=schema, report_basis=[])
    assert workflow.specialist(source) is owner
    assert workflow.is_scientific_source(source) is False and workflow.receipt_projection(source) is False
    view = SimpleNamespace(child_reports=[], controller_state={'arms': [], 'annotation_credits': [], 'root_score': 0.0, 'decision': 'continue', 'retained_other_field': 'keep-when-scalar'},
        model_inputs=lambda value, reports: {**value, 'controlled_child_report_count': len(reports)})
    context = snapshot(source, view)
    assert context['last_local_outcome']['status'] == 'invalid'
    assert context['feedback'] == original_feedback
    assert context['original_private_context']['role'] == role
    assert 'investigation_progress' not in context and 'proposed_annotations' not in context
    if credit_shape == 'scalar':
        assert context['working_state'] == {'last_original_state': 'failed'} and context['current_credit'] == -0.25
    else:
        assert context['working_state'] == {} and context['current_credit'] == {'mode': 'annotation_axis_credit', 'root_score': 0.0}
    return context


@pytest.mark.parametrize('home,role', HOMES, ids=[home for home, _ in HOMES])
@pytest.mark.parametrize('credit_shape', ('scalar', 'job_selected_annotation_shape'))
def test_native_summary_preserves_original_data_and_failure_context(home, role, credit_shape):
    expected = json.loads((Path(__file__).parent / 'fixtures/organization_preservation/a107_native_summary_baseline.json').read_bytes())
    assert observations(home, role, credit_shape) == expected['observations'][home][credit_shape]
