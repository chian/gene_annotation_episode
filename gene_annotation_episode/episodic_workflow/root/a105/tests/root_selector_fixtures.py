"""DRAFT required helper: real defining modules, controlled RPC; no model process.

Not promoted. Requires separately reviewed root placement and A105 composition.
The controlled session lifecycle is deliberately not evidence of process cleanup.
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
from .. import runtime
from ..episode_bindings import EpisodeBindingRegistry
from ... import providers as root_provider
from ... import model_session as root_session
from .literature_prompt_fixtures import snapshot, INSTRUCTION_TEXT, OUTPUT_SCHEMA

AX = 'gene_annotation_episode.episodic_workflow.root.a105'
ROOT = Path(__file__).resolve().parents[1]
OLD = Path(__file__).with_name('fixtures')/'provider_selector_v3'
OLD_MANIFEST_BYTES = (OLD/'manifest.json').read_bytes()
assert hashlib.sha256(OLD_MANIFEST_BYTES).hexdigest() == '71e13d70568b0ad9b1c973d965b38b7a8f9cc530116ba416fe583539477b10e7'
OLD_MANIFEST = json.loads(OLD_MANIFEST_BYTES)
HOMES = tuple(OLD_MANIFEST['homes'])


def retained(name):
    raw=(OLD/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==OLD_MANIFEST['files'][name]
    return raw


def single(values):
    value,=values
    return value


def expression(home, method, *, original=False):
    """Extract only the actual original/current call expression, no rewritten args."""
    if original:
        owner=single(n for n in ast.parse(retained('runtime.py.txt')).body
            if isinstance(n,ast.ClassDef) and n.name=='DecisionSource')
        target='self.workflow.provider.complete'
        namespace=dict(vars(runtime))
    else:
        module=import_module(AX+'.'+home.replace('/','.')+'.task_decision')
        raw=Path(module.__file__).read_bytes()
        owner=single(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef)
            and n.name==OLD_MANIFEST['classes'][home])
        target='self.decision_completion()'
        namespace=dict(vars(module))
    function=single(n for n in owner.body if isinstance(n,ast.AsyncFunctionDef) and n.name==method)
    call=single(n for n in ast.walk(function) if isinstance(n,ast.Call) and ast.unparse(n.func)==target)
    assert len(call.args)==5 and not call.keywords
    # Copied namespace retains real function globals; no manufactured renderer/global.
    code=compile(ast.fix_missing_locations(ast.Expression(ast.Await(value=deepcopy(call)))),
        '<retained-original-call>' if original else str(module.__file__), 'eval',
        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    return code,namespace


def selected_task(home, provider):
    """Real family registry, actual path resolver and actual Workflow.specialist.

    One seven-binding family is supplied, with an actual supported standalone
    entry path. This does not assert full root+scientific parent composition.
    """
    family=[h for h in HOMES if h.startswith('scientific_process/')==home.startswith('scientific_process/')]
    services=SimpleNamespace(workflow=SimpleNamespace(store=object()))
    bindings=[import_module(AX+'.'+h.replace('/','.')+'.episode').LiteratureEpisode(
        services,rate_population=True,assay_grading_population=True) for h in family]
    registry=EpisodeBindingRegistry(bindings)
    selected=bindings[family.index(home)]
    task=object.__new__(selected.decision_source_type)
    task.episode_id='controlled-'+home
    task.path=((selected.roles[0],'controlled-path-key'),)
    workflow=SimpleNamespace(provider=provider,episode_bindings=registry)
    workflow.specialist=MethodType(runtime.Workflow.specialist,workflow)
    task.workflow=workflow
    assert workflow.specialist(task) is selected
    assert selected.binding_path==home
    renderer_module=(AX+'.'+home.replace('/','.')+'.prompts.literature_experimental_prompt'
        if home=='scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
        else AX+'.library.literature_experimental_prompt')
    renderer=import_module(renderer_module).render_literature_experimental_prompt
    assert selected.decision_prompt_renderer is renderer
    assert getattr(renderer,'presentation_protocol',None) is None
    return task,selected


def controlled_root(monkeypatch,tmp_path):
    """Do not replace any seven root identity captures or complete/serial methods."""
    assert hashlib.sha256(Path(root_provider.__file__).read_bytes()).hexdigest() == '5196484b900d37500734f1725e58ad7ffa87bc16797a3408315ec590adf99aa9'
    assert hashlib.sha256(Path(root_session.__file__).read_bytes()).hexdigest() == '6d118158a5e6f8be4b3afa1afbbd09d1f7d328763e5100ec81a267daee59fc34'
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


def source_qualified_state():
    """Reuse the original presentation fixture's synthetic outcome verbatim."""
    from .literature_prompt_fixtures import SOURCE_TEXT,QUALIFICATION
    state=snapshot()
    state['last_local_outcome']={
        'status':'completed','operation_ref':'PRIVATE_OPERATION',
        'record_refs':[],'changed_record_refs':[],'result':{
            'source_ref':'source_selected','artifact_ref':'artifact_selected',
            'representation':'original','start':0,'end':len(SOURCE_TEXT.encode()),
            'text':SOURCE_TEXT,'qualification':QUALIFICATION}}
    return state


def genuine_presenter_session():
    """Only explicit state for a pure function boundary, not a live session."""
    from .. import decision_context,scientific_process_prompt
    assert hashlib.sha256(Path(root_provider.__file__).read_bytes()).hexdigest() == '5196484b900d37500734f1725e58ad7ffa87bc16797a3408315ec590adf99aa9'
    assert hashlib.sha256(Path(root_session.__file__).read_bytes()).hexdigest() == '6d118158a5e6f8be4b3afa1afbbd09d1f7d328763e5100ec81a267daee59fc34'
    presenter=own._ORIGINAL_DECLARED_PRESENTATION
    assert presenter is own._SessionConnection._declared_presentation
    assert presenter.__globals__ is vars(own)
    assert presenter.__globals__['DECISION_CONTEXT_VERSION']==decision_context.VERSION
    assert presenter.__globals__['apply_state_frame'] is decision_context.apply_state_frame
    assert presenter.__globals__['text_instructions'] is scientific_process_prompt.text_instructions
    actual_module=ast.parse(Path(own.__file__).read_bytes())
    retained_module=ast.parse(retained('providers.py.txt'))
    def function(tree):
        session=single(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='_SessionConnection')
        return single(n for n in session.body if isinstance(n,ast.FunctionDef) and n.name=='_declared_presentation')
    assert ast.dump(function(actual_module),include_attributes=False)==ast.dump(function(retained_module),include_attributes=False)
    session=object.__new__(root_session._SessionConnection)
    session.scientific_prompt_states={}
    return presenter,session
