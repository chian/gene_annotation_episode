"""Retain installed default composers while restoring actual injected services."""
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
HOMES = tuple('/'.join(filter(None, (parent, 'execution_progress_assessment'))) for parent in PARENTS) + tuple(
    '/'.join(filter(None, (parent, ending))) for parent in ('', 'scientific_process')
    for ending in ('hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution', 'hpc_work_planning/hpc_resource_prediction'))

def selected_source(home):
    module = importlib.import_module(PACKAGE + '.' + home.replace('/', '.') + '.episode')
    binding = getattr(module, 'MonitorEpisode' if home.endswith('execution_progress_assessment') else 'HPCEpisode')
    cls = binding.decision_source_type
    assert cls.__module__ == module.__name__.rsplit('.', 1)[0] + '.task'
    source = object.__new__(cls)
    source.path = ((home, 'original-key'),)
    return source

def workflow_for(source, *, supplied=True):
    events, context = [], {'tool_knowledge': {}, 'launch_instruction_library': {}} if supplied else {}
    binding_context = object()
    def specialist(actual):
        assert actual is source
        events.append('specialist')
        return SimpleNamespace(instructions=goal)
    def bound(actual):
        assert actual is source
        events.append('binding_context')
        return binding_context
    def goal(actual):
        assert actual is binding_context
        events.append('goal')
        return 'Original installed owner goal.'
    def permits(actual, action):
        assert actual is source
        events.append('permits:' + action)
        return supplied
    workflow = SimpleNamespace(specialist=specialist, binding_context=bound, permits_common_action=permits,
        knowledge=SimpleNamespace(instructions='\nOriginal tool library.'),
        launch_instructions=SimpleNamespace(instructions='\nOriginal Launch library.'),
        native_event_information=object() if supplied else None,
        decision_protocol='decision_exchange_v1' if supplied else None,
        is_job_source=lambda actual: False, services=object.__new__(WorkflowServices))
    source.workflow = workflow
    return workflow, context, events

def record(tmp_path, home, kind, data):
    root = Path(os.environ.get('A104_INSTALLED_TASK_SERVICE_RECORDS', str(tmp_path)))
    root.mkdir(parents=True, exist_ok=True)
    target = root / (home.replace('/', '__') + '__' + kind + '.json')
    assert not target.exists()
    target.write_text(json.dumps({'home': home, 'kind': kind, **data}, indent=2) + '\n')

def custom(source, reference, failed):
    workflow, context, events = workflow_for(source)
    sentinel, original_error = object(), LookupError('original injected service error')
    def instructions(actual_source, actual_context):
        assert actual_source is source and actual_context is context
        events.append('custom_service')
        if failed: raise original_error
        return sentinel
    workflow.services = SimpleNamespace(instructions=instructions)
    try:
        value = runtime.DecisionSource.instructions(source, context) if reference else source.instructions(context)
        result = {'kind': 'return', 'same_object': value is sentinel,
            'unexpected_text': value if isinstance(value, str) else None}
    except Exception as error:
        result = {'kind': 'raise', 'same_object': error is original_error,
            'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)}
    return {'events': events, 'outcome': result}

@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_actual_injected_service_precedence_and_identity(home, tmp_path):
    source = selected_source(home)
    expected = [custom(source, True, failed) for failed in (False, True)]
    actual = [custom(source, False, failed) for failed in (False, True)]
    assert all(value['events'] == ['custom_service'] and value['outcome']['same_object'] for value in expected)
    record(tmp_path, home, 'custom', {'expected': expected, 'actual': actual})
    assert actual == expected

@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_installed_private_default_composer_text_and_call_order_stays_exact(home, tmp_path, monkeypatch):
    source = selected_source(home)
    module = importlib.import_module(PACKAGE + '.' + home.replace('/', '.') + '.task_instructions')
    private_calls = []
    if os.environ['A104_INSTALLED_TASK_SERVICE_PHASE'] == 'connected':
        assert isinstance(type(source).__dict__['instruction_composer'], staticmethod)
        original = type(source).instruction_composer
        assert original is module.instructions
        def called(actual_source, context):
            private_calls.append(actual_source)
            return original(actual_source, context)
        monkeypatch.setattr(type(source), 'instruction_composer', staticmethod(called))
    rows = []
    for supplied in (False, True):
        _, context, events = workflow_for(source, supplied=supplied)
        expected = {'text': module.instructions(source, context), 'events': list(events)}
        _, context, events = workflow_for(source, supplied=supplied)
        actual = {'text': source.instructions(context), 'events': list(events)}
        assert actual == expected
        assert actual['events'].count('specialist') == actual['events'].count('goal') == 1
        rows.append({'supplied': supplied, **actual})
    if os.environ['A104_INSTALLED_TASK_SERVICE_PHASE'] == 'connected':
        assert len(private_calls) == 2 and all(value is source for value in private_calls)
    record(tmp_path, home, 'default', {'records': rows})

def test_ordinary_default_service_fallback_remains_original():
    source = object.__new__(runtime.DecisionSource)
    source.path = (('ordinary-role', 'original-key'),)
    workflow, context, _ = workflow_for(source)
    workflow.specialist = lambda actual: None
    expected = runtime_prompt.instructions(source, context)
    assert source.instructions(context) == expected
