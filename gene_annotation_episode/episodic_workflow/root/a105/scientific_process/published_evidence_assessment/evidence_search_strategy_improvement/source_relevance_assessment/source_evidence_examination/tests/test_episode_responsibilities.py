"""Exercise this episode's connected task, messages, goal, grading and yield."""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import pytest

from ..episode import LiteratureEpisode
from ..goal import VERSION, commissioned_task
from ..task import SourceExaminationTask
from ..grading.literature_required_grading import action_schema

SOURCE = 'source_' + 'a' * 64
ARTIFACT = 'artifact_' + 'b' * 64
ANNOTATION = 'hypothesis_' + 'c' * 64
EXPERIMENT = 'reference_' + 'd' * 64
SETTINGS = {'kind': 'remaining_commissioned_credit', 'cutoff': .075,
            'uncertainty_alpha': .05}


def commissioned_context():
    task = {'version': VERSION, 'evidence_axis': 'A105', 'kind': 'a105_experiments',
            'credit_unit': 7, 'yield_settings': SETTINGS,
            'experiments': [{'experiment_ref': EXPERIMENT, 'assay_type': 'activity_rate'}]}
    assignment = {'version': 'page_assignment_v1', 'source_ref': SOURCE,
                  'artifact_ref': ARTIFACT, 'representation': 'original',
                  'question_context_refs': [ANNOTATION], 'prior_delivery_refs': [],
                  'proposed_annotation_ref': ANNOTATION, 'literature_task': task}
    schema = {'type': 'object', 'properties': {
        'assessment': {'type': 'array', 'items': {'type': 'object'},
                       'x-source': 'literature_assay_grading_cells'}}}
    return SimpleNamespace(role='literature_page', assignment=assignment,
        request={'goal': {'objective': 'Assess the identified activity experiment'},
                 'message': {'episode_assignment': assignment, 'initial_report': {}},
                 'report_contract': {'decision': 'Interpret the experiment',
                                     'measurements': {'schema': schema}}})


def test_goal_keeps_original_experiment_and_graded_return():
    context = commissioned_context()
    task, proposed = commissioned_task(context)
    assert task['experiments'][0]['experiment_ref'] == EXPERIMENT
    assert proposed == ANNOTATION
    context.request['report_contract']['measurements']['schema']['properties']['assessment']['x-source'] = 'unrelated_results'
    with pytest.raises(Exception, match='typed_return_mismatch'):
        commissioned_task(context)


def test_private_credit_definition_and_completed_yield_are_consistent():
    context = commissioned_context()
    binding = LiteratureEpisode(object(), private_yield_binding=True,
        yield_bindings={'A105:experiments': {'credit_unit': 7, **SETTINGS}})
    definition = binding.credit_projector(context).as_record()
    assert definition['unit'] == 'one_current_graded_assessment_per_original_experiment'
    assert definition['revision_credit'] is False
    assert definition['activity_credit'] is False
    module = import_module(binding.__module__.rsplit('.', 1)[0] + '.yield_estimator')
    estimate = module._RemainingCommissionedCredit(7, 7)([], module.YieldParameters(), [])
    assert estimate.expected_next_gain.value == 0
    assert estimate.expected_next_gain.upper == 0
    assert estimate.diagnostics['completion'] == 'all_requested_answers_earned'
    assert binding.yield_controller(context, 0, 'source').__class__.__module__ == module.__name__


def test_goal_plan_uses_the_commission_and_credit_definition():
    context = commissioned_context()
    binding = LiteratureEpisode(object())
    plan = binding.planning_context(context)
    assert plan['objective'] == context.request['goal']
    assert plan['commissioned_result'] == context.assignment['literature_task']
    assert plan['progress_definition'] == binding.credit_projector(context).as_record()


def test_runtime_selects_this_episode_task_and_keeps_default_for_other_bindings(monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a105 import runtime
    binding = LiteratureEpisode(object())
    identity = SimpleNamespace(episode_id='source')
    monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs: identity)
    monkeypatch.setattr(runtime, 'FeedbackEpisode',
                        lambda grain, key, source, *args, **kwargs: source)
    journal = SimpleNamespace(row=lambda *args: None, save=lambda *args: None)
    workflow = SimpleNamespace(
        context=object(), grains={'literature_page': object()},
        inprocess_completion_order=None, receipts=None, scientific_process_binding=None,
        episode_bindings=SimpleNamespace(roles=('literature_page',), for_path=lambda path: binding),
        contract_information_profile=lambda source: None,
        specialist=lambda source: binding, journal=journal, run_id='pilot',
        store=SimpleNamespace(transaction=nullcontext, db=SimpleNamespace(execute=lambda *args: None)),
        source_credit_view=lambda source: {'credit': 0},
        expose_assigned_job=lambda source: None, archive=SimpleNamespace(store=lambda value: value))
    source = runtime.Workflow.build(workflow, 'literature_page', 'source', 'Examine source', {})
    assert type(source) is SourceExaminationTask
    assert source.path == (('literature_page', 'source'),)
    assert source.report_values == {}
    # Existing bindings retain the original execution source unless they declare their own.
    workflow.episode_bindings.for_path = lambda path: object()
    default = runtime.Workflow.build(workflow, 'literature_page', 'source', 'Examine source', {})
    assert type(default) is runtime.DecisionSource


@pytest.mark.parametrize('role,method', [
    ('literature_table', 'receive_table_evidence_extraction'),
    ('literature_targeted', 'receive_passage_evidence_extraction'),
    ('literature_ordered', 'receive_source_coverage_improvement')])
def test_runtime_delivers_redelivery_to_the_original_child_counterpart(role, method, monkeypatch, tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a105 import runtime
    from gene_annotation_episode.episodic_workflow.root.a105.state import Store
    from gene_annotation_episode.episodic_workflow.root.a105.episode_journal import Journal
    binding = LiteratureEpisode(object())
    context = commissioned_context()
    seen = []
    setattr(binding, method, lambda *args: seen.append(args) or ['saved-finding'])
    receipts = []
    with Store(tmp_path / 'original-counterpart') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        source = SimpleNamespace(episode_id='source', scope=store.validate_scope(),
            path=(('literature_page', 'source'),))
        journal = Journal(store, 'pilot')
        journal.save('runtime_episodes', {'episode_id':'original-child',
            'path':json.dumps((*source.path, (role, 'original-child'))),
            'request':'{}','initial_credit':0,'state':'yielded','completion':None,'archive':None})
        journal.save('runtime_actions', {'episode_id':'source','decision_index':3,
            'action':json.dumps({'kind':'redeliver_report','delivery_ref':'original-delivery'}),
            'result':None,'credit':None})
        journal.save('runtime_report_attempts', {'parent_episode_id':'source','decision_index':3,
            'delivery_ref':'original-delivery','child_episode_id':'original-child',
            'contract':'{}','form':'{}','failure':None})
        workflow = SimpleNamespace(
            receipts=SimpleNamespace(receive=lambda *args, **kwargs: receipts.append((args, kwargs))),
            is_job_source=lambda source: False, progress_provider=None, store=store,
            specialist=lambda source: binding, binding_context=lambda source: context,
            journal=journal, run_id='pilot', native_timing_information=None)
        monkeypatch.setattr(runtime, '_references_in', lambda *args, **kwargs: [])
        result = runtime.Workflow._receive_form(workflow, source, {}, {}, 3, redelivery=True)
        assert result == ['saved-finding']
        assert seen == [(context, {}, {}, 'pilot:source:3:typed_form')]
        assert receipts[0][1] == {'kind':'report_redelivery', 'source_index':3}




def test_private_tool_contract_error_returns_an_invalid_action():
    from ..tools.literature_contract_error import ExperimentalContractError
    binding = LiteratureEpisode(object())
    binding._tool_arguments = lambda context, name, arguments: arguments
    binding._materialize_text_arguments = lambda context, arguments, repo: arguments
    def invalid(*args):
        raise ExperimentalContractError('missing_measurement', 'effect')
    binding._assay_grading_repository = lambda: SimpleNamespace(populate=invalid)
    result = asyncio.run(binding.execute(commissioned_context(),
        'literature.assay_grading.populate', {}, 'pilot:source:tool'))
    assert result['status'] == 'invalid'
    assert result['feedback']['field'] == 'effect'
    assert result['record_refs'] == []


@pytest.mark.parametrize('role', ['literature_table','literature_ordered','literature_targeted'])
def test_outgoing_requests_preserve_source_and_leave_child_selection_intact(role):
    binding = LiteratureEpisode(object())
    parent = commissioned_context()
    request = {'page': {k: parent.assignment[k] for k in
                       ('source_ref','artifact_ref','representation')},
               'selection': {'question': 'Resolve units and controls'}}
    saved = deepcopy(request)
    sent = binding.prepare_child_request(parent, role, request)
    assert sent == saved and sent is not request
    assert request == saved
    sent['page']['artifact_ref'] = 'artifact_' + 'e' * 64
    with pytest.raises(Exception, match='artifact_ref_mismatch'):
        binding.prepare_child_request(parent, role, sent)


def test_child_returns_use_the_original_counterpart():
    binding = LiteratureEpisode(object())
    seen = []
    binding.receive_table_evidence_extraction = lambda *args: seen.append('table') or ['table-result']
    binding.receive_passage_evidence_extraction = lambda *args: seen.append('passage') or ['passage-result']
    binding.receive_source_coverage_improvement = lambda *args: seen.append('coverage') or ['coverage-result']
    assert binding.receive_child_result(None,'literature_table',{}, {},'op') == ['table-result']
    assert binding.receive_child_result(None,'literature_targeted',{}, {},'op') == ['passage-result']
    assert seen == ['table','passage']


def test_required_grading_keeps_typed_finding_in_same_action():
    commit = {'type': 'object', 'properties': {'assessments': {'type': 'array',
        'items': {'type': 'object', 'properties': {'investigation_finding': {'type': 'object'}},
                  'required': []}}}}
    schema = action_schema(commit, {'type': 'object'})
    fields = schema['properties']['commit']['properties']['assessments']['items']['required']
    assert 'investigation_finding' in fields
    assert 'evidence_processing' in schema['properties']


def test_task_observes_scoring_before_credit_and_does_not_repeat_completed_work():
    events = []
    rows = {}
    class Journal:
        def row(self, table, episode, index):
            return rows.get(index)
        def save(self, table, value):
            rows[value['decision_index']] = dict(value)
        def measure(self, *args):
            return nullcontext()
    binding = LiteratureEpisode(object())
    def interpret(*args):
        events.extend(['interpret', 'grade_and_save_sheet'])
        return {'status': 'completed', 'record_refs': ['finding'], 'changed_record_refs': []}
    binding.execute_reasoning = interpret
    async def score(source,index,result):
        events.append('automatic_sheet_updates')
        return result
    def credit(source):
        events.append('credit')
        return {'credit': 7}
    workflow = SimpleNamespace(journal=Journal(),run_id='pilot',
        execution_binding=None,wait_inputs_version=None,completed_action_inputs_version=None,
        specialist=lambda source: binding,binding_context=lambda source: commissioned_context(),
        receive_native_outcome=lambda *args: None,receive_outcome=lambda *args: events.append('receive'),
        automatic_score_updates=score,source_credit_view=credit,
        controller_value=lambda source,index,value: value)
    source = object.__new__(SourceExaminationTask)
    source.workflow,source.episode_id,source.path,source.scope = workflow,'source',(('literature_page','source'),),{}
    source.checkpoint = lambda: None
    selection = {'kind':'reason','commit':{}}
    assert asyncio.run(source.execute(selection,0)) == 7
    assert events.index('grade_and_save_sheet') < events.index('automatic_sheet_updates') < events.index('credit')
    first = list(events)
    assert asyncio.run(source.execute(selection,0)) == 7
    assert events == first
    assert json.loads(rows[0]['result'])['record_refs'] == ['finding']
    assert binding.decision_source_type is SourceExaminationTask
