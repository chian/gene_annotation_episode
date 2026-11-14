"""Original custom service callback and explicit private default guidance ports.

Controlled instruction calls use the actual private task types. One additional
case constructs the real Workflow through ToolRegistry.workflow_services. No
provider, native action, scientific assessment or iteration is executed.
"""
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]
AXIS=__package__.rsplit('.tests',1)[0]
HOMES=sorted(p.parent.relative_to(ROOT).as_posix() for p in ROOT.rglob('binding_record.py') if 'tests' not in p.relative_to(ROOT).parts)

def module(name):return import_module(AXIS+'.'+name)

def task(home):
    owner=module(home.replace('/','.')+'.task')
    return object.__new__(getattr(owner,'ScientificTask' if home=='scientific_process' else 'LiteratureTask'))

@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('raises',[False,True])
def test_custom_service_is_first_and_preserves_exact_return_or_exception(home,raises):
    source=task(home);context={'own_context':'unchanged'};calls=[];value='exact custom service guidance';error=RuntimeError('custom service failure')
    def callback(actual,inputs):
        calls.append((actual,inputs))
        if raises:raise error
        return value
    def forbidden(*args,**kwargs):pytest.fail('no specialist/composer lookup before the original custom service')
    source.workflow=SimpleNamespace(services=SimpleNamespace(instructions=callback),specialist=forbidden,binding_context=forbidden)
    if raises:
        with pytest.raises(RuntimeError) as caught:source.instructions(context)
        assert caught.value is error
    else:assert source.instructions(context) is value
    assert calls==[(source,context)] and calls[0][1] is context

@pytest.mark.parametrize('home',HOMES)
def test_default_service_uses_actual_private_static_composer(home):
    source=task(home);calls=[];context={'tool_knowledge':{},'launch_instruction_library':{}}
    def specialist(actual):calls.append(('specialist',actual));return None
    def permits(actual,action):calls.append(('permits',actual,action));return action=='reason' or home=='scientific_process' and action=='wait'
    def unclaimed(*args):pytest.fail('private default composition must not dispatch the unclaimed runtime composer')
    workflow=SimpleNamespace(specialist=specialist,permits_common_action=permits,is_job_source=unclaimed,
        native_event_information=None,decision_protocol=None,knowledge=SimpleNamespace(instructions='\nSelected knowledge'),
        launch_instructions=SimpleNamespace(instructions='\nSelected launch guidance'))
    source.workflow=workflow;services=module('episode_services').WorkflowServices(workflow);workflow.services=services
    composer=module(home.replace('/','.')+'.task_instructions').instructions
    declared=vars(type(source)).get('instruction_composer')
    assert isinstance(declared,staticmethod) and declared.__func__ is composer
    expected=composer(source,context);expected_calls=list(calls);calls.clear()
    actual=source.instructions(context)
    assert actual==expected and calls==expected_calls

@pytest.mark.parametrize('declared_none',[False,True])
def test_unclaimed_source_keeps_exact_original_default_fallback(declared_none):
    source=type('Unclaimed',(),{'instruction_composer':None} if declared_none else {})()
    # An undeclared instance attribute must not become a private type binding.
    source.instruction_composer=lambda *_:pytest.fail('default composer binding is declared on the task type')
    source.path=(('annotation','unclaimed'),)
    source.workflow=SimpleNamespace(is_job_source=lambda *_:False,specialist=lambda *_:None,
        permits_common_action=lambda _,action:action=='reason',native_event_information=None,decision_protocol=None,
        knowledge=SimpleNamespace(instructions='\nOriginal knowledge'),launch_instructions=SimpleNamespace(instructions='\nOriginal launch guidance'))
    context={'tool_knowledge':{},'launch_instruction_library':{}}
    services=module('episode_services').WorkflowServices(source.workflow)
    assert services.instructions(source,context)==module('runtime_prompt').instructions(source,context)

def test_actual_workflow_obeys_tools_custom_service_factory(tmp_path,monkeypatch):
    captured=[];calls=[];answer='Actual tools-owned workflow guidance'
    class CustomServices(module('episode_services').WorkflowServices):
        def instructions(self,source,context):calls.append((source,context));return answer
    def factory(workflow):
        services=CustomServices(workflow);captured.append(services);return services
    def forbidden(*args,**kwargs):pytest.fail('instruction dispatch must not execute work or inspect a specialist first')
    library=module('scientific_process_library').ScientificProcessLibrary(ROOT/'tests/fixtures/retained_protein_reader_336/run/scientific-process-library')
    tools_library=module('scientific_tool_library').ScientificToolLibrary.freeze(tmp_path/'tools',catalog=[],tool_info=True)
    with module('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        tools=module('tools').ToolRegistry(store,clients=SimpleNamespace());monkeypatch.setattr(tools,'workflow_services',factory)
        projector=lambda *_args,**_kwargs:{'credit':0}
        projector.as_record=lambda:{'kind':'controlled_engineering_projector','unit':1}
        Binding=module('scientific_process.episode').ScientificProcessEpisode
        workflow=module('runtime').Workflow(store,tools,SimpleNamespace(complete=forbidden),tmp_path/'run',
            'custom-instruction-port',forbidden,projector,root_role='scientific_process',
            episode_binding_factories=[lambda services:Binding(services,library=library,tool_library=tools_library,child_roles=('scientific_process',))])
        assert len(captured)==1 and workflow.services is captured[0]
        source=task('scientific_process');source.workflow=workflow;context={'original_context':True}
        monkeypatch.setattr(workflow,'specialist',forbidden)
        assert source.instructions(context) is answer and calls==[(source,context)]
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
