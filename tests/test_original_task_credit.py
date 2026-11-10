"""Original task selection, annotation custody and cutoff-unit isolation.

All units and cutoffs below are synthetic interface fixtures, not calibration.
"""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, ValidationError

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.numerical import (YieldController, AnnotationAxisYieldController,
    STATUS_UNIDENTIFIABLE)
from gene_annotation_episode import runtime
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from test_investigation_progress import put_finding
from test_scientific_findings import quoted_observation, target_question


def task_context(axis='A105', *, unit=3, annotation='hypothesis_fixture', scope=None):
    assignment = {'proposed_annotation_ref': annotation, 'context': {'evidence_task': {
        'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings',
        'evidence_axis': axis, 'credit_unit': unit}}}
    scope = scope or {'subject_refs': ['input_fixture']}
    request = {'message': {'scope': scope, 'episode_assignment': assignment}}
    return BindingContext('run_fixture', 'episode_fixture', 'scientific_process',
        (('annotation', 'root'), ('scientific_process', 'child')), scope, assignment, request)


def axis_owner(axis):
    # The option snapshot/custody mechanism is exercised by its existing tests;
    # this fixture fixes the authenticated original selection at that boundary.
    owner = ScientificProcessEpisodes.__new__(ScientificProcessEpisodes)
    owner._original_selection = lambda context: {'version': 'scientific_process_selection_v3',
        'evidence_axis': {'option_id': axis}}
    owner.library = SimpleNamespace(resolve=lambda selection: {'entry_version': 'evidence_axis_instruction_v1'})
    return owner


def test_fresh_child_schema_exposes_and_requires_the_selected_axis_task():
    owner = axis_owner('A105')
    owner.services = SimpleNamespace(annotation_task_required=lambda: True)
    schema = owner.child_assignment_schema(SimpleNamespace(), 'scientific_process')
    reference = {'version': 'scientific_process_option_ref_v1',
        'library_id': 'a'*64, 'entry_sha256': 'b'*64}
    assignment = task_context(annotation='hypothesis_' + 'c'*24).as_record()['assignment']
    assignment.update(selection={'version': 'scientific_process_selection_v3',
        'evidence_axis': {**reference, 'slot': 'evidence_axis', 'option_id': 'A105'},
        'thought_pattern': {**reference, 'slot': 'thought_pattern', 'option_id': 'P01'},
        'child_tool_info': []}, evidence_refs=[], constraints={})
    Draft202012Validator(schema).validate(assignment)
    missing = deepcopy(assignment)
    missing['context'].clear()
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(missing)
    wrong = deepcopy(assignment)
    wrong['context']['evidence_task']['evidence_axis'] = 'A106'
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(wrong)


def test_annotation_root_requires_frozen_evidence_refs_with_child_credit():
    owner = ScientificProcessEpisodes.__new__(ScientificProcessEpisodes)
    owner.services = SimpleNamespace(annotation_task_required=lambda: True)
    owner._invocation = lambda *_: {'report_schema': {'properties': {
        'results': {'x-source': 'scientific_process_results'}}}}
    parent = SimpleNamespace(path=(('annotation', 'root'),))
    with pytest.raises(ContractError, match='scientific_child_return_requires_committed_record_refs'):
        owner.prepare_invocation(parent, 'scientific_process', {}, {}, 'fixture', invocation={})
    assert 'committed_record_refs' in runtime.FACT_SOURCES


def test_annotation_root_tells_model_both_required_child_return_sources():
    from gene_annotation_episode.composition_information import child_options
    owner = ScientificProcessEpisodes.__new__(ScientificProcessEpisodes)
    owner.services = SimpleNamespace(annotation_task_required=lambda: True)
    owner.assignment_schema = lambda _role: {'type': 'object', 'required': ['selection']}
    owner.library = SimpleNamespace(headers=lambda: [
        {'option_ref': {'slot': 'evidence_axis'}}])
    workflow = SimpleNamespace(
        available_child_roles=lambda _source: ['scientific_process'],
        episode_bindings=SimpleNamespace(roles={'scientific_process'}, for_role=lambda _role: owner),
        scientific_process_binding=owner,
        report_sources=lambda _role: {},
        return_contract_sources=lambda _role: {
            'scientific_process_results': {}, 'committed_record_refs': {}})
    root = SimpleNamespace(path=(('annotation', 'root'),))
    text = child_options(workflow, root)['text']
    assert text.startswith('Required child return facts')
    assert 'scientific_process: scientific_process_results, committed_record_refs' in text
    assert '{"$ref":"episode-fact:<source>"}' in text


def test_scientific_child_return_sources_accept_decision_source_parent():
    parent = SimpleNamespace(path=(('annotation', 'root'), ('scientific_process', 'a101')))
    services = SimpleNamespace(annotation_task_required=lambda: True)
    execution = ExecutionEpisodes.__new__(ExecutionEpisodes)
    execution.services = services
    monitor = MonitorEpisodes.__new__(MonitorEpisodes)
    monitor.services = services
    assert execution.required_return_sources(parent, 'launch') == ('execution_handoff_refs',)
    assert execution.required_return_sources(parent, 'results') == ('execution_result_refs',)
    assert monitor.required_return_sources(parent, 'monitor') == ('monitoring_progress_refs',)


def test_root_yield_stays_unresolved_while_original_axis_job_can_return():
    arm = {'proposed_annotation_ref': 'hypothesis_fixture', 'subject_ref': 'input_fixture',
        'scope': {'subject_refs': ['input_fixture']}, 'axis': 'A101', 'credit': 0.,
        'status': 'unscored', 'transfer': {}}
    credit = {'mode': 'annotation_axis_credit', 'arms': [arm]}
    owner = AnnotationAxisYieldController('root-fixture', credit, {'A101': 0.03})
    identity = {name: arm[name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}
    step = owner.observe('axis-return', {'credit': credit, 'estimation_context': {
        'completed_annotation_axis': identity,
        'unresolved_annotation_axis_credit': [{**identity,
            'handoff_ref': 'source_original_blast', 'native_state': 'WAITING'}]}})
    waiting, = step.state.arms
    assert waiting['unresolved_execution_handoffs'] == ['source_original_blast']
    assert waiting['expected_additional_credit']['status_code'] == STATUS_UNIDENTIFIABLE
    assert not waiting['stop_requested'] and not step.state.stop
    resolved = owner.observe('result-received', {'credit': credit, 'estimation_context': {
        'unresolved_annotation_axis_credit': []}})
    assert resolved.state.arms[0]['unresolved_execution_handoffs'] == []


@pytest.mark.parametrize('axis', ['A105', 'A106', 'A108'])
def test_whole_axis_finding_credit_keeps_opposition_and_excludes_other_annotations(tmp_path, axis):
    with Store(tmp_path/'state') as store:
        target, annotation = target_question(store)
        other = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'biological_role',
            'value': {'type': 'enum', 'value': 'negative'}, 'context_refs': []}, origin='reasoning')['id']
        subject, observed = quoted_observation(store, accession='opposing', start=0, end=17)
        opposition = put_finding(store, annotation, observed, subject, value='negative')
        unrelated = put_finding(store, other, observed, subject)
        context = task_context(axis, annotation=annotation, scope={'subject_refs': [target]})
        owner = axis_owner(axis)
        projector = owner.credit_projector(context)
        scope = context.as_record()['scope']
        result = projector(store, scope,
            assignment={'scope': scope, 'proposed_annotation_ref': annotation},
            known_assessment_refs=[opposition['id'], unrelated['id']])
        assert result['credit'] == 3
        assert result['retained_finding_count'] == 1
        assert owner.continuation_task(context) == axis + ':whole_axis_findings'
        assert result['policy']['annotation_support'] == 'separately_bound_not_this_score'


@pytest.mark.parametrize('axis', ['A102', 'A105', 'A106', 'A107', 'A108', 'A110'])
def test_axis_owner_counts_one_received_finding_once_across_deliveries(tmp_path, axis):
    from gene_annotation_episode.root_axis_receipts import axis_progress_from_received
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.domain import canonical
    with Store(tmp_path/'state') as store:
        target, annotation = target_question(store)
        subject, observed = quoted_observation(store, accession='resolved', start=0, end=17)
        assessment = put_finding(store, annotation, observed, subject)
        scope = {'subject_refs': [target]}
        known = [target, annotation, subject, observed['id'],
            observed['source_ref'], assessment['id']]
        receiver = SimpleNamespace(run_id='finding-axis-union', received_record_refs=tuple(known))
        projector = ScientificFindingProgress(FindingProgressPolicy(3))
        item = {'proposed_annotation_ref': annotation, 'scope': scope, 'axis': axis,
            'credit_projector': projector, 'credit_binding_ref': 'original-binding',
            'record_refs': [assessment['id']]}
        progress = axis_progress_from_received(store, receiver, [item, deepcopy(item)])
        assert progress[annotation, canonical(scope), axis]['credit'] == 1


@pytest.mark.parametrize('change', ['missing_task', 'other_axis', 'score_task', 'missing_annotation', 'missing_unit'])
def test_axis_does_not_infer_or_borrow_an_undeclared_task(change):
    context = task_context()
    assignment = deepcopy(context.as_record()['assignment'])
    task = assignment['context']['evidence_task']
    if change == 'missing_task':
        assignment['context'].clear()
    elif change == 'other_axis':
        task['evidence_axis'] = 'A106'
    elif change == 'score_task':
        task['kind'] = 'finalize_score'
    elif change == 'missing_annotation':
        assignment.pop('proposed_annotation_ref')
    else:
        task.pop('credit_unit')
    altered = BindingContext(context.run_id, context.episode_id, context.role,
        context.path, context.scope, assignment, context.request)
    with pytest.raises(ContractError):
        axis_owner('A105').credit_projector(altered)


def test_runtime_uses_the_commissioned_owner_binding_without_global_controller(monkeypatch):
    context = task_context()
    captured = []
    def owner_controller(bound, initial_credit, epoch):
        captured.append((bound.assignment['proposed_annotation_ref'], initial_credit, epoch))
        return YieldController(epoch, initial_credit, .075)
    owner = SimpleNamespace(private_yield_binding=True, yield_controller=owner_controller)
    def forbidden(*_args, **_kwargs):
        raise AssertionError('global controller must not select this episode')
    monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs:
        SimpleNamespace(episode_id=context.episode_id))
    workflow = SimpleNamespace(context=object(), grains={'scientific_process': object()},
        run_id=context.run_id, receipts=None, completed_action_inputs_version=None,
        journal=SimpleNamespace(row=lambda *args: {'initial_credit': 6,
            'request': json.dumps(context.as_record()['request'])}),
        episode_bindings=SimpleNamespace(roles=('scientific_process',), for_role=lambda role: owner),
        controller_factory=forbidden, has_native_estimation=lambda: False)
    selected = runtime.Workflow.controller(workflow, context.path)
    assert selected.controller.cost == .075
    assert captured[0][:2] == ('hypothesis_fixture', 6)
    assert captured[0][2] == selected.controller.epoch
