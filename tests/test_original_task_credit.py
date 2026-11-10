"""Original task selection, annotation custody and cutoff-unit isolation.

All units and cutoffs below are synthetic interface fixtures, not calibration.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, ValidationError

from gene_annotation_episode import investigation_policy, runtime
from gene_annotation_episode.case_execution import _load_policy
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.investigation_policy import create_policy
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from test_investigation_policy import parameters
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


def configured_tasks():
    config = parameters('registry_fixture')
    contexts = [task_context(axis) for axis in ('A105', 'A106')]
    owners = [axis_owner(axis) for axis in ('A105', 'A106')]
    config['controller']['cost_by_task'] = {
        owner.continuation_task(context): {'cutoff': cutoff,
            'credit_definition': owner.credit_projector(context).as_record()}
        for owner, context, cutoff in zip(owners, contexts, (.23, .41))}
    return config, contexts, owners


def test_cutoffs_follow_task_and_exact_units_and_survive_recorded_reload(tmp_path):
    config, contexts, owners = configured_tasks()
    policy, recorded = _load_policy(tmp_path, Path(investigation_policy.__file__), config, resume=False)
    restored, replay = _load_policy(tmp_path, None, None, resume=True)
    assert replay == recorded
    assert 'scientific_child_credit' not in recorded['definitions']
    for context, owner, cutoff in zip(contexts, owners, (.23, .41)):
        key = owner.continuation_task(context)
        definition = owner.credit_projector(context).as_record()
        for selected in (policy, restored):
            actual = selected.controller_factory(context.path, 6, context=context,
                task_key=key, credit_definition=definition)
            assert actual.initial_credit == 6 and actual.cost == cutoff
        changed = axis_owner('A105').credit_projector(task_context(unit=9)).as_record()
        with pytest.raises(ValueError, match='cutoff_credit_definition_mismatch'):
            policy.controller_factory(context.path, 6, context=context,
                task_key=key, credit_definition=changed)
    key = owners[0].continuation_task(contexts[0])
    config['controller']['cost_by_task'][key]['cutoff'] = 99
    policy.controller_definition['cost_by_task'][key]['cutoff'] = 88
    assert policy.controller_factory(contexts[0].path, 0, context=contexts[0], task_key=key,
        credit_definition=owners[0].credit_projector(contexts[0]).as_record()).cost == .23


def test_missing_task_cutoff_does_not_use_a_role_or_root_cutoff():
    config, contexts, owners = configured_tasks()
    config['controller']['cost_by_role']['scientific_process'] = .01
    config['controller']['cost_by_task'].pop('A106:whole_axis_findings')
    policy = create_policy(config, episode_roles=('scientific_process',))
    context, owner = contexts[1], owners[1]
    with pytest.raises(ValueError, match='episode_task_cutoff_not_declared:A106'):
        policy.controller_factory(context.path, 0, context=context,
            task_key=owner.continuation_task(context), credit_definition=owner.credit_projector(context).as_record())


def test_runtime_passes_original_commission_before_constructing_controller(monkeypatch):
    config, contexts, owners = configured_tasks()
    policy = create_policy(config)
    context, owner = contexts[1], owners[1]
    owner.credit_kind = lambda role: 'scientific'
    monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs:
        SimpleNamespace(episode_id=context.episode_id))
    workflow = SimpleNamespace(context=object(), grains={'scientific_process': object()},
        run_id=context.run_id, receipts=None, completed_action_inputs_version=None,
        journal=SimpleNamespace(row=lambda *args: {'initial_credit': 6,
            'request': json.dumps(context.as_record()['request'])}),
        episode_bindings=SimpleNamespace(roles=('scientific_process',), for_role=lambda role: owner),
        controller_factory=policy.controller_factory, has_native_estimation=lambda: False)
    workflow.scientific_projector_for_context = MethodType(runtime.Workflow.scientific_projector_for_context, workflow)
    result = runtime.Workflow.controller(workflow, context.path)
    assert result.controller.cost == .41
    assert result.controller.initial_credit == 6

    # Original two-argument caller factories remain reconstructible, without
    # receiving today's additional task parameters during historical recovery.
    calls = []
    def historical(path, initial):
        calls.append((path, initial))
        return result.controller
    workflow.controller_factory = historical
    runtime.Workflow.controller(workflow, context.path)
    assert calls == [(context.path, 6)]
