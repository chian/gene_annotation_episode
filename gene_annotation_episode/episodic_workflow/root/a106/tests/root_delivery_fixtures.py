"""Unpromoted A106 controls: real owners, controlled RPC, no model process.

Requires an explicitly audited canonical source overlay or genuine placement.
This helper cannot silently load prepared code under a fabricated module identity.
"""
import ast
from copy import deepcopy
import hashlib
from importlib import import_module
import inspect
import json
from pathlib import Path
from types import MethodType, SimpleNamespace

from .. import providers as own, runtime
from ..episode_bindings import EpisodeBindingRegistry
from ..private_binding_factories import private_binding_type
from ... import providers as root_provider
from ... import model_session as root_session
from .literature_prompt_fixtures import snapshot, INSTRUCTION_TEXT, OUTPUT_SCHEMA, OBJECTIVE

AX='gene_annotation_episode.episodic_workflow.root.a106'
ROOT=Path(__file__).resolve().parents[1]
ASSETS=Path(__file__).with_name('fixtures')/'root_selector_delivery'
MANIFEST=json.loads((ASSETS/'source_manifest.json').read_bytes())
assert MANIFEST['version']=='a106_root_delivery_control_sources_v2'
assert MANIFEST['extension_manifest_sha256']=='62b6591aa02fab676d79c1500f0db7ea3b809d2735a1210cdfb3d3b70e6d21b5'
assert MANIFEST['extension_audit_sha256']=='b96918c0c0a8c516a73ee9a04c3600388612ad46e2616f9494095d45b6d52dc5'
HOMES=tuple(row['binding_path'] for row in MANIFEST['bindings'])
assert len(HOMES)==len(set(HOMES))==16


def single(values):
    value,=values
    return value


def retained(name):
    raw=(ASSETS/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==MANIFEST['assets'][name]
    return raw


def actual_module(name):
    module=import_module(name)
    path=Path(module.__file__).resolve()
    assert module.__name__==name and module.__spec__.name==name
    assert Path(module.__spec__.origin).resolve()==path
    assert hashlib.sha256(path.read_bytes()).hexdigest()==MANIFEST['expected_installed_modules'][name]
    return module


def expression(home,method,*,original=False):
    if original:
        raw=retained('runtime.py.txt');namespace=dict(vars(runtime));target='self.workflow.provider.complete'
        owner_name='DecisionSource';filename=str(ASSETS/'runtime.py.txt')
    else:
        module=actual_module(AX+'.'+home.replace('/','.')+'.task_decision')
        raw=Path(module.__file__).read_bytes();namespace=dict(vars(module));target='self.decision_completion()'
        owner_name=single(row['decision_class'] for row in MANIFEST['bindings'] if row['binding_path']==home)
        filename=str(module.__file__)
    owner=single(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name==owner_name)
    fn=single(n for n in owner.body if isinstance(n,ast.AsyncFunctionDef) and n.name==method)
    call=single(n for n in ast.walk(fn) if isinstance(n,ast.Call) and ast.unparse(n.func)==target)
    assert len(call.args)==5 and not call.keywords
    code=compile(ast.fix_missing_locations(ast.Expression(ast.Await(value=deepcopy(call)))),filename,'eval',flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    return code,namespace


def selected_task(home,provider):
    """One real binding through the original supported standalone registry path.

    No artificial parent or full two-family root graph is constructed.
    """
    row=single(r for r in MANIFEST['bindings'] if r['binding_path']==home)
    module=actual_module(AX+'.'+home.replace('/','.')+'.episode')
    binding_type,family=private_binding_type(home)
    assert binding_type is getattr(module,row['binding_class'])
    assert family==('monitor' if row['decision_class']=='MonitorTaskDecision' else 'literature')
    binding=binding_type(SimpleNamespace(workflow=SimpleNamespace(store=object())))
    registry=EpisodeBindingRegistry([binding])
    task=object.__new__(binding.decision_source_type)
    task.episode_id='controlled-'+home
    task.path=((binding.roles[0],'controlled-key'),)
    workflow=SimpleNamespace(provider=provider,episode_bindings=registry)
    workflow.specialist=MethodType(runtime.Workflow.specialist,workflow)
    task.workflow=workflow
    assert workflow.specialist(task) is binding and binding.binding_path==home
    actual_module(AX+'.'+home.replace('/','.')+'.task')
    renderer_module=actual_module(row['callback_module'])
    renderer=getattr(renderer_module,'render_monitor_prompt' if family=='monitor' else 'render_literature_experimental_prompt')
    assert binding.decision_prompt_renderer is renderer
    assert renderer.__globals__ is vars(renderer_module)
    assert getattr(renderer,'presentation_protocol',None) is None
    return task,binding


def state_for(home):
    if 'execution_progress_assessment' not in home.split('/'):
        return snapshot()
    # Engineering monitor state, based on actual monitor_assignment_v1 fields;
    # these are descriptive status facts, not a scientific outcome or credit.
    return {'monitor_assignment':{'version':'monitor_assignment_v1','target_handle':'original-target',
        'requested_fields':['execution_status'],'known_progress_refs':[],
        'permitted_committed_record_types':[]},
        'requested_form':{'type':'object','properties':{'status':{'type':'string','enum':['running'],
            'x-source':'monitoring_status'}},'required':['status'],'additionalProperties':False},
        'available_report_facts':{'monitoring_status':{'meaning':'Original monitored execution status.'},
            'unrequested_science':{'meaning':'UNREQUESTED_SCIENCE_DEFINITION'}},
        'feedback':None}


def assert_visible(home,text):
    if 'execution_progress_assessment' in home.split('/'):
        assert 'Actual monitor state' in text and 'original-target' in text
        assert 'monitoring_status' in text and 'Original monitored execution status.' in text
        assert 'UNREQUESTED_SCIENCE_DEFINITION' not in text
    else:
        assert_task(text);assert_no_bookkeeping(text)
def assert_task(text):
    assert text.startswith("TASK\n\n")
    assert text.count("\n\nSTEERING\n") == 1
    task = text.split("\n\nSTEERING\n", 1)[0]
    for item in (OBJECTIVE, "source_selected", "source.read", "representation", "offset", "limit",
                 "rate_difference", "difference_se", "source_signed_index",
                 "Return the requested source-rate cells and necessary qualifications.",
                 "Recorded source-preparation measurements; unavailable inputs remain null."):
        assert item in task
    # Experimental meanings matter more than an exact sentence or heading.
    for item in ("subject", "condition", "endpoint", "control", "uncertainty"):
        assert item in task.lower()
    assert "no-enzyme" in task.lower()
    assert "product" in task.lower()
    assert "independen" in task.lower()
    assert "transfer" in task.lower()
    return task


def assert_no_bookkeeping(text):
    for item in ("PRIVATE_GOAL", "PRIVATE_PARENT_GOAL", "PRIVATE_PROBLEM", "PRIVATE_EPOCH",
                 "PRIVATE_FIT", "PRIVATE_OWN_HISTORY", "PRIVATE_CHILD_HISTORY", "PRIVATE_RESTORE_HISTORY",
                 "UNREQUESTED_SOURCE_INVENTORY", "UNREQUESTED_OBSERVATION", "UNREQUESTED_FACT_DEFINITION",
                 "PRIVATE_OPERATION", "PRIVATE_PIN", "base_revision", "removed_fields",
                 "decision_bootstrap supplies", "restored_pending_decision_index",
                 "DO_NOT_RENDER_RESPONSE_TRANSCRIPT"):
        assert item not in text


def controlled_root(monkeypatch,tmp_path):
    """Do not replace any seven root identity captures or complete/serial methods."""
    assert hashlib.sha256(Path(root_provider.__file__).read_bytes()).hexdigest() == '5196484b900d37500734f1725e58ad7ffa87bc16797a3408315ec590adf99aa9'
    assert hashlib.sha256(Path(root_session.__file__).read_bytes()).hexdigest() == '6d118158a5e6f8be4b3afa1afbbd09d1f7d328763e5100ec81a267daee59fc34'
    assert actual_module(AX+'.providers') is own
    assert actual_module(AX+'.runtime') is runtime
    sent=[];workers=[]
    async def enter(self):
        self.process=SimpleNamespace(pid='controlled-no-process',returncode=0)
        workers.append(self)
        return self
    async def leave(self,*args):
        return None
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
    assert type(provider) is root_provider.ModelConnection
    assert provider.complete.__func__ is root_provider._ORIGINAL_MODEL_COMPLETE
    assert inspect.getattr_static(type(provider),'_complete_serial') is root_provider._ORIGINAL_MODEL_COMPLETE_SERIAL
    assert root_provider._ORIGINAL_MODEL_SESSION_TYPE is root_session._SessionConnection
    assert root_session._SessionConnection.complete is root_provider._ORIGINAL_SESSION_COMPLETE
    assert root_session._SessionConnection._presentation is root_provider._ORIGINAL_SESSION_PRESENTATION
    assert own._ORIGINAL_DECLARED_PRESENTATION is own._SessionConnection._declared_presentation
    return provider,sent,workers


async def invoke(task,home,method,context,*,original=False):
    code,namespace=expression(home,method,original=original)
    request={'instructions':INSTRUCTION_TEXT,'context':context,'output_schema':OUTPUT_SCHEMA}
    return await eval(code,namespace,dict(self=task,instructions=INSTRUCTION_TEXT,
        context=context,schema=OUTPUT_SCHEMA,request=request))


def unusual_root_receiver(base,kind,tmp_path,events):
    """Keep captured root methods; vary only the explicit eligibility operand."""
    assert type(base) is root_provider.ModelConnection
    if kind=='metaclass':
        class GuardMeta(type):
            def __getattribute__(cls,name):
                if name=='__dict__':
                    events.append('metaclass_dict_lookup')
                    raise AssertionError('metaclass dictionary must not be consulted')
                return type.__getattribute__(cls,name)
        class RootSubclass(root_provider.ModelConnection,metaclass=GuardMeta):
            pass
        receiver=RootSubclass(base.config,tmp_path/'metaclass-connection',base.cwd)
        assert type(type(receiver)) is GuardMeta
    elif kind=='borrowed_bound_complete':
        # This is intentionally NOT a ModelConnection. Supply its original
        # callable protocol explicitly; do not falsely manufacture ancestry.
        receiver=SimpleNamespace(**dict(root_provider._ORIGINAL_MODEL_INSTANCE_DICT.__get__(base)))
        receiver.complete=MethodType(root_provider._ORIGINAL_MODEL_COMPLETE,receiver)
        receiver._complete_serial=MethodType(root_provider._ORIGINAL_MODEL_COMPLETE_SERIAL,receiver)
        receiver.release=MethodType(root_provider.ModelConnection.release,receiver)
        receiver.session_type=root_provider._ORIGINAL_MODEL_SESSION_TYPE
        assert not isinstance(receiver,root_provider.ModelConnection)
    elif kind=='nonstring_dictionary_key':
        receiver=base
        class CollidingKey:
            def __hash__(self): return hash('complete_with_presentation')
            def __eq__(self,other):
                events.append('nonstring_key_equality')
                raise AssertionError('dictionary guard must not compare this key')
        values=root_provider._ORIGINAL_MODEL_INSTANCE_DICT.__get__(receiver)
        assert 'complete_with_presentation' not in values
        values[CollidingKey()]=object()
        assert any(type(key) is not str for key,value in dict.items(values))
    else:
        raise AssertionError(kind)
    assert receiver.complete.__func__ is root_provider._ORIGINAL_MODEL_COMPLETE
    return receiver


async def invoke_argument_mutation(task,home,method,context,*,original,change,events,failure=None):
    """Observe the actual original five-operand AST with one explicit arg effect.

    The schema wrapper calls the genuine helper once; the request subclass only
    observes the original subscript. No provider/selector method is rewritten.
    """
    code,namespace=expression(home,method,original=original)
    def perform_change():
        events.append('argument_mutation')
        if change=='provider':
            async def unexpected(*args):
                events.append('replacement_called')
                raise AssertionError('argument mutation replaced the captured callee')
            task.workflow.provider=SimpleNamespace(complete=unexpected)
        elif change=='episode':
            task.episode_id='changed-during-argument-evaluation'
        else:
            raise AssertionError(change)
        if failure is not None: raise failure
    if method=='call':
        actual_schema=namespace['_action_generation_schema']
        def traced_schema(value):
            perform_change()
            result=actual_schema(value)
            events.append(('evaluated_schema',deepcopy(result)))
            return result
        namespace['_action_generation_schema']=traced_schema
        request={'instructions':INSTRUCTION_TEXT,'context':context,'output_schema':OUTPUT_SCHEMA}
    else:
        assert method=='exchange_decision'
        class Request(dict):
            def __getitem__(self,key):
                if key=='output_schema': perform_change()
                return super().__getitem__(key)
        request=Request(instructions=INSTRUCTION_TEXT,context=context,output_schema=OUTPUT_SCHEMA)
    return await eval(code,namespace,dict(self=task,instructions=INSTRUCTION_TEXT,
        context=context,schema=OUTPUT_SCHEMA,request=request))


def genuine_presenter_session():
    """Only explicit state for a pure function boundary, not a live session."""
    from .. import decision_context,scientific_process_prompt
    assert hashlib.sha256(Path(root_provider.__file__).read_bytes()).hexdigest() == '5196484b900d37500734f1725e58ad7ffa87bc16797a3408315ec590adf99aa9'
    assert hashlib.sha256(Path(root_session.__file__).read_bytes()).hexdigest() == '6d118158a5e6f8be4b3afa1afbbd09d1f7d328763e5100ec81a267daee59fc34'
    assert actual_module(AX+'.providers') is own
    actual_module(AX+'.decision_context');actual_module(AX+'.scientific_process_prompt')
    presenter=own._ORIGINAL_DECLARED_PRESENTATION
    assert presenter is own._SessionConnection._declared_presentation
    assert presenter.__globals__ is vars(own)
    assert presenter.__globals__['DECISION_CONTEXT_VERSION']==decision_context.VERSION
    assert presenter.__globals__['apply_state_frame'] is decision_context.apply_state_frame
    assert presenter.__globals__['text_instructions'] is scientific_process_prompt.text_instructions
    actual_tree=ast.parse(Path(own.__file__).read_bytes())
    retained_module=ast.parse(retained('providers.py.txt'))
    def function(tree):
        session=single(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='_SessionConnection')
        return single(n for n in session.body if isinstance(n,ast.FunctionDef) and n.name=='_declared_presentation')
    assert ast.dump(function(actual_tree),include_attributes=False)==ast.dump(function(retained_module),include_attributes=False)
    session=object.__new__(root_session._SessionConnection)
    session.scientific_prompt_states={}
    return presenter,session
