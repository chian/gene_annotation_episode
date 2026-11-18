"""Actual custom service admission and private/default instruction dispatch."""
from importlib import import_module
from types import SimpleNamespace

import pytest

from .test_private_literature_bindings import AXIS, HOMES

ALL_HOMES = [*HOMES, 'experimental_activity_evidence']


def task_type(home):
    module = import_module(AXIS + '.' + home + '.episode')
    binding = module.ExperimentalActivityEvidenceEpisode if home == 'experimental_activity_evidence' else module.LiteratureEpisode
    return binding.decision_source_type


@pytest.fixture(scope='module')
def custom_workflow(tmp_path_factory):
    directory = tmp_path_factory.mktemp('instruction-service')
    Services = import_module(AXIS + '.episode_services').WorkflowServices
    Registry = import_module(AXIS + '.tools').ToolRegistry
    Store = import_module(AXIS + '.state').Store
    Workflow = import_module(AXIS + '.runtime').Workflow
    events = []
    class CallbackError(Exception):
        pass
    class CustomServices(Services):
        def instructions(self, source, context):
            events.append(('custom', source, context))
            if context['raise_callback']:
                raise context['exception']
            return context['custom_instructions']
    class CustomRegistry(Registry):
        def workflow_services(self, workflow):
            events.append(('factory', workflow))
            return CustomServices(workflow)
    def unused(*args, **kwargs):
        pytest.fail('Instruction selection must not execute provider, projector or controller')
    with Store(directory / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        tools = CustomRegistry(store, clients=SimpleNamespace())
        workflow = Workflow(store, tools, SimpleNamespace(complete=unused), directory / 'run',
            'custom-instructions', unused, unused, episode_binding_factories=[])
        assert type(workflow.services) is CustomServices
        assert events == [('factory', workflow)]
        yield workflow, events, CallbackError


@pytest.mark.parametrize('home', ALL_HOMES)
@pytest.mark.parametrize('raises', [False, True])
def test_original_custom_service_is_called_before_private_work(home, raises, custom_workflow, monkeypatch):
    workflow, events, Error = custom_workflow
    source = object.__new__(task_type(home)); source.workflow = workflow
    def forbidden(*args, **kwargs):
        pytest.fail('Custom instruction callback must precede specialist lookup and private composition')
    monkeypatch.setattr(workflow, 'specialist', forbidden)
    error = Error('original callback error')
    context = {'raise_callback': raises, 'exception': error,
        'custom_instructions': 'Use this caller instruction; target correspondence remains unresolved.'}
    before = list(events)
    if raises:
        with pytest.raises(Error) as caught:
            source.instructions(context)
        assert caught.value is error
    else:
        assert source.instructions(context) is context['custom_instructions']
    assert events == [*before, ('custom', source, context)]
    assert workflow.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
    assert workflow.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('home', ALL_HOMES)
def test_default_service_selects_full_private_composer_once(home, monkeypatch):
    task = task_type(home); source = object.__new__(task)
    composer = import_module(AXIS + '.' + home + '.task_instructions').instructions
    events = []
    specialist = SimpleNamespace(instructions=lambda context: 'Source claim retained; target correspondence unresolved.', replaces_default_instructions=False)
    def select(actual):
        assert actual is source
        events.append('specialist')
        return specialist
    source.workflow = SimpleNamespace(specialist=select, binding_context=lambda value: 'original-context',
        is_job_source=lambda value: False,
        permits_common_action=lambda value, action: action == 'reason' or action == 'wait' and home == 'experimental_activity_evidence',
        knowledge=SimpleNamespace(instructions='Original supplied knowledge.'),
        launch_instructions=SimpleNamespace(instructions='Original launch instructions.'),
        native_event_information=object(), decision_protocol='decision_exchange_v1')
    services = import_module(AXIS + '.episode_services').WorkflowServices(source.workflow)
    source.workflow.services = services
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    expected = composer(source, context)
    before = list(events)
    def forbidden(*args, **kwargs):
        pytest.fail('A declared private composer must not fall back to the generic prompt')
    monkeypatch.setattr(import_module(AXIS + '.runtime_prompt'), 'instructions', forbidden)
    assert services.instructions(source, context) == expected
    assert events == [*before, 'specialist']
    assert getattr(type(source), 'instruction_composer') is composer
    assert 'Source claim retained; target correspondence unresolved.' in expected


@pytest.mark.parametrize('declaration', [None, 'not a callable'])
def test_unclaimed_default_service_preserves_original_fallback(declaration, monkeypatch):
    class Unclaimed:
        instruction_composer = declaration
    source = Unclaimed()
    # Instance data must not override the class's actual instruction declaration.
    source.instruction_composer = lambda *_: pytest.fail('Instance replacement is not a task declaration')
    context = {'original': 'unclaimed context'}
    events = []
    result = object()
    def fallback(actual_source, actual_context):
        assert actual_source is source and actual_context is context
        events.append('fallback')
        return result
    monkeypatch.setattr(import_module(AXIS + '.runtime_prompt'), 'instructions', fallback)
    workflow = SimpleNamespace(specialist=lambda *_: pytest.fail('No eager specialist lookup'))
    services = import_module(AXIS + '.episode_services').WorkflowServices(workflow)
    assert services.instructions(source, context) is result
    assert events == ['fallback']
