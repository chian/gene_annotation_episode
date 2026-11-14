"""Service-first private instruction composition; controlled ports, no actions."""
import ast
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE = __package__.rsplit('.tests', 1)[0]
ROOT = Path(__file__).resolve().parents[1]
HOMES = sorted(str(path.parent.relative_to(ROOT)) for path in ROOT.rglob('task.py')
               if (path.parent / 'episode.py').is_file() and 'tests' not in path.parts)
assert len(HOMES) == {'a101': 40, 'a106': 29}[ROOT.name]


def private_task(home):
    import_module(PACKAGE + '.runtime')
    path = ROOT / home / 'task.py'
    classes = [node.name for node in ast.parse(path.read_bytes()).body if isinstance(node, ast.ClassDef)]
    assert len(classes) == 1
    return getattr(import_module(PACKAGE + '.' + home.replace('/', '.') + '.task'), classes[0])


def forbidden(*args, **kwargs):
    pytest.fail('Private composition or specialist lookup ran before the custom service callback')


@pytest.mark.parametrize('home', HOMES)
def test_custom_service_callback_precedes_private_composition(home):
    Task = private_task(home)
    source = object.__new__(Task)
    context = {'original_context_object': []}; result = object(); calls = []
    def custom(actual_source, actual_context):
        calls.append((actual_source, actual_context)); return result
    source.workflow = SimpleNamespace(services=SimpleNamespace(instructions=custom), specialist=forbidden)
    assert source.instructions(context) is result
    assert len(calls) == 1 and calls[0][0] is source and calls[0][1] is context


@pytest.mark.parametrize('home', HOMES)
def test_default_service_selects_exact_private_composer_and_keeps_its_text(home, monkeypatch):
    Task = private_task(home)
    composer = import_module(PACKAGE + '.' + home.replace('/', '.') + '.task_instructions').instructions
    assert isinstance(Task.__dict__['instruction_composer'], staticmethod)
    assert Task.instruction_composer is composer
    source = object.__new__(Task)
    binding = SimpleNamespace(instructions=lambda context: 'Exact private specialist goal', replaces_default_instructions=False)
    source.workflow = SimpleNamespace(specialist=lambda source: binding, binding_context=lambda source: object(),
        permits_common_action=lambda source, action: True,
        knowledge=SimpleNamespace(instructions='\nActual selected knowledge'),
        launch_instructions=SimpleNamespace(instructions='\nActual selected launch context'),
        native_event_information=object(), decision_protocol='decision_exchange_v1')
    service = import_module(PACKAGE + '.episode_services').WorkflowServices(source.workflow)
    source.workflow.services = service
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    expected = composer(source, context)
    monkeypatch.setattr(import_module(PACKAGE + '.runtime_prompt'), 'instructions', forbidden)
    assert service.instructions(source, context) == expected
    assert source.instructions(context) == expected
    assert 'Exact private specialist goal' in expected


@pytest.mark.parametrize('declaration', ['absent', None, 'not-callable'])
def test_unclaimed_source_retains_original_default_fallback(declaration, monkeypatch):
    class Unclaimed:
        pass
    if declaration != 'absent':
        Unclaimed.instruction_composer = declaration
    source = Unclaimed(); context = {}; result = object(); calls = []
    def original(actual_source, actual_context):
        calls.append((actual_source, actual_context)); return result
    monkeypatch.setattr(import_module(PACKAGE + '.runtime_prompt'), 'instructions', original)
    service = import_module(PACKAGE + '.episode_services').WorkflowServices(object())
    assert service.instructions(source, context) is result
    assert calls == [(source, context)]


def test_actual_workflow_preserves_tools_selected_custom_instruction_service(tmp_path, monkeypatch):
    module = lambda name: import_module(PACKAGE + '.' + name)
    library = module('scientific_process_library').ScientificProcessLibrary.freeze(tmp_path / 'library',
        source=ROOT.parents[3] / 'research/slotted_process_library/publications/2026-10-24-001')
    tool_library = module('scientific_tool_library').ScientificToolLibrary.freeze(tmp_path / 'tools', catalog=[], tool_info=True)
    events = []; result = object()
    class CustomServices(module('episode_services').WorkflowServices):
        def instructions(self, source, context):
            events.append(('instructions', source, context)); return result
    class CustomTools(module('tools').ToolRegistry):
        def workflow_services(self, workflow):
            events.append(('factory', workflow)); return CustomServices(workflow)
    class EngineeringProjector:
        def as_record(self):
            return {'version': 'instruction_callback_engineering_fixture_v1'}
        def __call__(self, store, scope, **arguments):
            return {'credit': 0, 'proposed_annotations': [], 'comparisons': []}
    with module('state').Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        Binding = module('scientific_process.episode').ScientificProcessEpisode
        workflow = module('runtime').Workflow(store, CustomTools(store, clients=SimpleNamespace()),
            SimpleNamespace(complete=forbidden), tmp_path / 'workflow', 'custom-service-fixture',
            forbidden, EngineeringProjector(), root_role='scientific_process', initial_known_record_refs=[],
            episode_binding_factories=(lambda services: Binding(services, library=library,
                tool_library=tool_library, child_roles=('scientific_process',)),))
        assert type(workflow.services) is CustomServices
        assert events == [('factory', workflow)]
        monkeypatch.setattr(workflow, 'specialist', forbidden)
        source = object.__new__(private_task('scientific_process')); source.workflow = workflow
        context = {'original_context': []}
        assert source.instructions(context) is result
        assert events[-1][0] == 'instructions' and events[-1][1] is source and events[-1][2] is context
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls', 'tool_operations'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
