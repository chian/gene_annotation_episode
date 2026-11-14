"""Real defining owners and registry; controlled RPC, no provider process.

Required retained assets are installed beside these tests, never read from runs.
Only the actual call expression executes; this is not a full task/workflow test.
"""
import ast
from copy import deepcopy
import hashlib
from importlib import import_module
import inspect
import json
from pathlib import Path
from types import MethodType, SimpleNamespace
from .. import providers as own
from .. import runtime, decision_context
from ..episode_bindings import EpisodeBindingRegistry
from ... import providers as root_provider
from ... import model_session as root_session
from .root_delivery_state import snapshot, INSTRUCTION_TEXT, OUTPUT_SCHEMA

AX = __package__.rsplit('.tests',1)[0]
AXIS = AX.rsplit('.',1)[1]
ASSETS = Path(__file__).with_name('fixtures')/'root_delivery_source'
MANIFEST_BYTES = (ASSETS/'manifest.json').read_bytes()
assert hashlib.sha256(MANIFEST_BYTES).hexdigest() == '21d1a190e6c1ffeb31599f7f66ef97dc23d229f4340968d5e45579704530e1ad'
MANIFEST = json.loads(MANIFEST_BYTES)
assert MANIFEST['axis']==AXIS
HOMES = tuple(MANIFEST['homes'])

def retained(name):
    raw=(ASSETS/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==MANIFEST['files'][name]
    return raw

def single(values):
    value,=values;return value

def expression(home, method, *, original=False):
    if original:
        tree=ast.parse(retained('runtime.py.txt'))
        owner=single(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DecisionSource')
        target='self.workflow.provider.complete';namespace=dict(vars(runtime))
    else:
        module=import_module(AX+'.'+home.replace('/','.')+'.task_decision')
        owner=single(n for n in ast.parse(Path(module.__file__).read_bytes()).body
            if isinstance(n,ast.ClassDef) and n.name==MANIFEST['classes'][home])
        target=None;namespace=dict(vars(module))
    fn=single(n for n in owner.body if isinstance(n,ast.AsyncFunctionDef) and n.name==method)
    call=single(n for n in ast.walk(fn) if isinstance(n,ast.Call) and (ast.unparse(n.func)==target if original else ast.unparse(n.func) in ('self.complete_decision','self.decision_completion()')))
    assert not call.keywords
    if original:assert len(call.args)==5
    else:assert ast.dump(call,include_attributes=False) in MANIFEST['call_shapes'][home][method]
    code=compile(ast.fix_missing_locations(ast.Expression(ast.Await(value=deepcopy(call)))),
        '<retained-original-call>' if original else str(module.__file__), 'eval',
        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    return code,namespace

def selected_task(home, provider):
    # Both registries explicitly support standalone selection of one bound role.
    # A108 also constructs the actual seven-binding family. This is not a full
    # configured scientific-parent graph or admission/assignment test.
    family=([home] if AXIS=='a101' else [h for h in HOMES
        if h.startswith('scientific_process/')==home.startswith('scientific_process/')])
    services=SimpleNamespace()
    name='MonitorEpisode' if AXIS=='a101' else 'LiteratureEpisode'
    bindings=[getattr(import_module(AX+'.'+h.replace('/','.')+'.episode'),name)(services)
        for h in family]
    registry=EpisodeBindingRegistry(bindings);selected=bindings[family.index(home)]
    task=object.__new__(selected.decision_source_type)
    task.episode_id='controlled-'+home
    task.path=((selected.roles[0],'controlled-path-key'),)
    workflow=SimpleNamespace(provider=provider,episode_bindings=registry)
    workflow.specialist=MethodType(runtime.Workflow.specialist,workflow);task.workflow=workflow
    assert workflow.specialist(task) is selected and selected.binding_path==home
    owner=import_module(AX+'.library.'+('monitor_prompt' if AXIS=='a101' else 'literature_experimental_prompt'))
    renderer=getattr(owner,'render_monitor_prompt' if AXIS=='a101' else 'render_literature_experimental_prompt')
    assert selected.decision_prompt_renderer is renderer
    return task,selected

def controlled_root(monkeypatch,tmp_path):
    # These must be actual canonical owners, not loaded copies or module aliases.
    assert root_provider.__spec__.name=='gene_annotation_episode.episodic_workflow.root.providers'
    assert root_session.__spec__.name=='gene_annotation_episode.episodic_workflow.root.model_session'
    assert Path(root_provider.__file__).resolve()==Path(own.__file__).resolve().parents[1]/'providers.py'
    assert Path(root_session.__file__).resolve()==Path(own.__file__).resolve().parents[1]/'model_session.py'
    assert hashlib.sha256(Path(root_provider.__file__).read_bytes()).hexdigest()=='5196484b900d37500734f1725e58ad7ffa87bc16797a3408315ec590adf99aa9'
    assert hashlib.sha256(Path(root_session.__file__).read_bytes()).hexdigest()=='6d118158a5e6f8be4b3afa1afbbd09d1f7d328763e5100ec81a267daee59fc34'
    sent=[];workers=[]
    async def enter(self):
        self.process=SimpleNamespace(pid='controlled-no-process',returncode=0)
        workers.append(self);return self
    async def leave(self,*args):return None
    async def rpc(self,method,params):
        sent.append((method,deepcopy(params)))
        if method=='thread/start':
            return {'thread':{'id':'controlled-root-thread'},'model':params['model'],
                'reasoningEffort':params['config']['model_reasoning_effort']}
        assert method=='turn/start'
        self.pending.extend([
            {'method':'item/completed','params':{'threadId':'controlled-root-thread',
                'item':{'type':'agentMessage','text':'{"fixture":true}'}}},
            {'method':'turn/completed','params':{'threadId':'controlled-root-thread',
                'turn':{'id':'controlled-turn','status':'completed'}}}])
        return {'turn':{'id':'controlled-turn'}}
    monkeypatch.setattr(root_session._SessionConnection,'__aenter__',enter)
    monkeypatch.setattr(root_session._SessionConnection,'__aexit__',leave)
    monkeypatch.setattr(root_session._SessionConnection,'_rpc',rpc)
    provider=root_provider.ModelConnection(root_provider.load_config(),tmp_path/'connection',tmp_path)
    assert provider.complete.__func__ is root_provider._ORIGINAL_MODEL_COMPLETE
    assert inspect.getattr_static(type(provider),'complete_with_presentation') is root_provider._ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION
    assert inspect.getattr_static(type(provider),'_complete_serial') is root_provider._ORIGINAL_MODEL_COMPLETE_SERIAL
    assert inspect.getattr_static(type(provider),'__dict__') is root_provider._ORIGINAL_MODEL_INSTANCE_DICT
    assert root_provider._ORIGINAL_MODEL_SESSION_TYPE is root_session._SessionConnection
    assert root_session._SessionConnection.complete is root_provider._ORIGINAL_SESSION_COMPLETE
    assert root_session._SessionConnection._presentation is root_provider._ORIGINAL_SESSION_PRESENTATION
    return provider,sent,workers

async def invoke(task,home,method,context,*,original=False):
    code,namespace=expression(home,method,original=original)
    request={'instructions':INSTRUCTION_TEXT,'context':context,'output_schema':OUTPUT_SCHEMA}
    return await eval(code,namespace,dict(self=task,instructions=INSTRUCTION_TEXT,
        context=context,schema=OUTPUT_SCHEMA,request=request))

async def invoke_mutation(task,home,method,context,*,original,change,events,failure=None):
    code,namespace=expression(home,method,original=original)
    def mutate():
        events.append('argument_mutation')
        if change=='provider':
            async def replacement(*args):raise AssertionError('captured callee lost')
            task.workflow.provider=SimpleNamespace(complete=replacement)
        else:
            assert change=='episode';task.episode_id='changed-during-argument-evaluation'
        if failure is not None:raise failure
    if method=='call':
        original_schema=namespace['_action_generation_schema']
        def traced_schema(value):
            mutate();answer=original_schema(value);events.append(('schema',deepcopy(answer)));return answer
        namespace['_action_generation_schema']=traced_schema
        request={'instructions':INSTRUCTION_TEXT,'context':context,'output_schema':OUTPUT_SCHEMA}
    else:
        assert method=='exchange_decision'
        class Request(dict):
            def __getitem__(self,key):
                if key=='output_schema':mutate()
                return super().__getitem__(key)
        request=Request(instructions=INSTRUCTION_TEXT,context=context,output_schema=OUTPUT_SCHEMA)
    return await eval(code,namespace,dict(self=task,instructions=INSTRUCTION_TEXT,
        context=context,schema=OUTPUT_SCHEMA,request=request))

def presenter_session():
    presenter=own._ORIGINAL_DECLARED_PRESENTATION
    assert presenter is own._SessionConnection._declared_presentation
    assert presenter.__globals__ is vars(own)
    assert presenter.__globals__['DECISION_CONTEXT_VERSION']==decision_context.VERSION
    assert presenter.__globals__['apply_state_frame'] is decision_context.apply_state_frame
    prompt=import_module(AX+('.scientific_process_prompt' if AXIS=='a101' else '.library.scientific_process_prompt'))
    assert presenter.__globals__['text_instructions'] is prompt.text_instructions
    def method(raw):
        cls=single(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='_SessionConnection')
        return single(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_declared_presentation')
    assert ast.dump(method(Path(own.__file__).read_bytes()),include_attributes=False)==ast.dump(method(retained('providers.py.txt')),include_attributes=False)
    session=object.__new__(root_session._SessionConnection);session.scientific_prompt_states={}
    return presenter,session
