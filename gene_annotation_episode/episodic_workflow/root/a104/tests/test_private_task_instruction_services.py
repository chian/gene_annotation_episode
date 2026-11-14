"""Actual custom/default instruction-service boundaries for 27 private tasks.

These focused tests do not replace each family's Store/Journal action and replay
tests. They invoke the real task method, real default WorkflowServices method and
the complete real original/private composers with controlled callback operands.
"""
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104 import runtime, runtime_prompt
from gene_annotation_episode.episodic_workflow.root.a104.episode_services import WorkflowServices

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
PARENTS = ('', 'scientific_process', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = tuple('/'.join(filter(None, (parent, 'execution_job_submission', child)))
    for parent in PARENTS for child in ('local_job_execution', 'hpc_job_execution')) + tuple(
    '/'.join(filter(None, (parent, ending))) for parent in PARENTS
    for ending in ('execution_job_submission', 'execution_result_acquisition')) + (
        'homology_job_submission', 'homology_job_monitoring', 'homology_result_acquisition')
assert len(HOMES) == len(set(HOMES)) == 27

def source_for(home):
    phase = os.environ['A104_TASK_SERVICE_PHASE']
    assert phase in {'baseline', 'connected'}
    cls = runtime.DecisionSource
    if phase == 'connected':
        module = importlib.import_module(PACKAGE + '.' + home.replace('/', '.') + '.task')
        classes = [value for value in vars(module).values() if isinstance(value, type)
            and value.__module__ == module.__name__ and value.__name__.endswith('Task')]
        cls, = classes
        assert 'next' in cls.__dict__ and callable(cls.__dict__['next'])
        assert isinstance(cls.__dict__['instruction_composer'], staticmethod)
        assert cls.instruction_composer.__module__ == module.__name__.rsplit('.', 1)[0] + (
            '.task_instructions' if home.endswith('execution_job_submission') and home not in {
                'execution_job_submission', 'scientific_process/execution_job_submission'} else '.instructions')
    binding_module = importlib.import_module(PACKAGE + '.' + home.replace('/', '.') + '.episode')
    binding = getattr(binding_module, 'HomologyEpisode' if home.startswith('homology_') else 'ExecutionEpisode')
    assert (getattr(binding, 'decision_source_type', None) is cls) == (phase == 'connected')
    source = object.__new__(cls)
    source.path = ((home, 'original-key'),)
    return source

def save(tmp_path, home, boundary, source, records):
    output = Path(os.environ.get('A104_TASK_SERVICE_RECORDS', str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    path = output / (home.replace('/', '__') + '__' + boundary + '.json')
    assert not path.exists()
    path.write_text(json.dumps({'home': home, 'boundary': boundary,
        'source_type': type(source).__module__ + '.' + type(source).__qualname__,
        'records': records}, indent=2) + '\n')

@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_custom_instruction_service_keeps_exact_call_identity_result_and_error(home, tmp_path):
    source = source_for(home)
    context, sentinel, calls = {'original-context': object()}, object(), []
    def instructions(actual_source, actual_context):
        calls.append((actual_source, actual_context))
        return sentinel
    source.workflow = SimpleNamespace(services=SimpleNamespace(instructions=instructions))
    assert source.instructions(context) is sentinel
    assert len(calls) == 1 and calls[0][0] is source and calls[0][1] is context
    error = LookupError('original injected instruction failure')
    def failed(actual_source, actual_context):
        calls.append((actual_source, actual_context))
        raise error
    source.workflow.services.instructions = failed
    with pytest.raises(LookupError) as caught:
        source.instructions(context)
    assert caught.value is error
    assert len(calls) == 2 and calls[1][0] is source and calls[1][1] is context
    save(tmp_path, home, 'custom', source, [{'calls': len(calls), 'same_source': True,
        'same_context': True, 'same_return_object': True, 'same_exception_object': True,
        'exception_type': type(error).__module__ + '.' + type(error).__qualname__, 'exception': str(error)}])

def run_default(source, case, use_original):
    events = []
    def observed(name, value):
        def call(*args):
            events.append(name)
            if name == 'job_goal': assert args == (source.path[-1][0],)
            elif name in {'is_job', 'specialist', 'binding_context'}: assert args == (source,)
            if isinstance(value, Exception): raise value
            return value
        return call
    bound_context = object()
    def specialist_goal(actual):
        assert actual is bound_context
        events.append('specialist_goal')
        return 'Original specialized goal.'
    specialist = None if case['specialist'] == 'absent' else SimpleNamespace(
        replaces_default_instructions=case['specialist'] == 'replace', instructions=specialist_goal)
    def permits(actual_source, action):
        assert actual_source is source
        events.append('permits:' + action)
        return case[action]
    workflow = SimpleNamespace(
        is_job_source=observed('is_job', case['job']),
        job_episodes=SimpleNamespace(instructions=observed('job_goal', 'Original job goal.')),
        specialist=observed('specialist', specialist),
        binding_context=observed('binding_context', bound_context), permits_common_action=permits,
        knowledge=SimpleNamespace(instructions='\nOriginal supplied tool knowledge.'),
        launch_instructions=SimpleNamespace(instructions='\nOriginal supplied Launch guidance.'),
        native_event_information=object() if case['native'] else None,
        decision_protocol=runtime_prompt.DECISION_EXCHANGE_PROTOCOL if case['exchange'] else None)
    if case.get('failure'):
        setattr(workflow, case['failure'], observed('is_job' if case['failure'] == 'is_job_source' else 'specialist',
            LookupError('original ' + case['failure'] + ' failure')))
    source.workflow = workflow
    workflow.services = object.__new__(WorkflowServices)
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}} if case['libraries'] else {}
    try:
        result = runtime_prompt.instructions(source, context) if use_original else source.instructions(context)
        outcome = {'kind': 'return', 'value': result}
    except Exception as error:
        outcome = {'kind': 'raise', 'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)}
    return {'events': events, 'outcome': outcome}

@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_default_service_uses_complete_original_composer_once_in_original_order(home, tmp_path, monkeypatch):
    source = source_for(home)
    private_calls = []
    if os.environ['A104_TASK_SERVICE_PHASE'] == 'connected':
        original_private = type(source).instruction_composer
        def private_composer(actual_source, actual_context):
            assert actual_source is source
            private_calls.append(actual_context)
            return original_private(actual_source, actual_context)
        monkeypatch.setattr(type(source), 'instruction_composer', staticmethod(private_composer))
    cases = []
    for job in (False, True):
        for specialist in ('absent', 'append', 'replace'):
            for supplied in (False, True):
                cases.append({'job': job, 'specialist': specialist, 'reason': supplied, 'wait': supplied,
                    'native': supplied, 'exchange': supplied, 'libraries': supplied})
    cases.extend({'job': True, 'specialist': 'append', 'reason': True, 'wait': True,
        'native': True, 'exchange': True, 'libraries': True, 'failure': name}
        for name in ('is_job_source', 'specialist'))
    records = []
    for case in cases:
        expected = run_default(source, case, True)
        actual = run_default(source, case, False)
        assert actual == expected, (home, case, actual, expected)
        if os.environ['A104_TASK_SERVICE_PHASE'] == 'connected':
            assert len(private_calls) == len(records) + 1
        if not case.get('failure'):
            assert actual['events'].count('is_job') == 1
            assert actual['events'].count('specialist') == 1
            assert actual['events'].count('job_goal') == int(case['job'])
            assert actual['events'].count('specialist_goal') == int(case['specialist'] != 'absent')
            assert actual['outcome']['kind'] == 'return'
        records.append({'case': case, **actual})
    save(tmp_path, home, 'default', source, records)

def test_default_service_nonparticipant_fallback_preserves_original_composer():
    source = object.__new__(runtime.DecisionSource)
    source.path = (('ordinary-original-role', 'original-key'),)
    case = {'job': False, 'specialist': 'absent', 'reason': True, 'wait': True,
        'native': True, 'exchange': True, 'libraries': True}
    assert not hasattr(type(source), 'instruction_composer')
    assert run_default(source, case, False) == run_default(source, case, True)
