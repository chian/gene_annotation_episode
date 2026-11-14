"""Actual own-A102 outgoing/receiving boundaries against original runtime methods.

Observation stops run the real child constructor or saved request comparison,
then stop before initialization/credit. No completed scientific workflow claim.
"""
import ast
from contextlib import contextmanager,ExitStack
from copy import deepcopy
from dataclasses import replace
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import MethodType,SimpleNamespace
from unittest.mock import patch
from . import source_family_checks as source_helpers
from ..scientific_process.tests import head_checks
PREFIX='gene_annotation_episode.episodic_workflow.root.a102'
EDGES=(('', 'literature', 'published_evidence_assessment'), ('scientific_process', 'literature', 'scientific_process/published_evidence_assessment'), ('published_evidence_assessment', 'literature_strategy', 'published_evidence_assessment/evidence_search_strategy_improvement'), ('published_evidence_assessment/evidence_search_strategy_improvement', 'literature_search', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_page', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_table', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_ordered', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_targeted', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'), ('scientific_process/published_evidence_assessment', 'literature_strategy', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'literature_search', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_page', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_table', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_ordered', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_targeted', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'))
ORIGINAL_SHA='598a42abe6f3a96a692a4508348f4bf0a0ab9c5a8d0adade85b8dac97cd014fe'
def own(name):return import_module(PREFIX+'.'+name)
def plain(value):return own('communication').plain(value)
class ConstructionObserved(Exception):pass
class ReconstructionObserved(Exception):pass

def observe(callback):
    try:return {'status':'returned','value':plain(callback())}
    except AssertionError:raise
    except Exception as error:return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,
        'message':str(error),'code':getattr(error,'code',None),'detail':plain(getattr(error,'detail',None)),
        'field':getattr(error,'field',None)}

def original_methods():
    path=Path(__file__).parent/'fixtures/source_request_assembly/runtime_original.py.txt';raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA
    tree=ast.parse(raw);owner,=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Workflow']
    methods=[deepcopy(n) for n in owner.body if isinstance(n,ast.FunctionDef) and n.name in {'selected','build','_receive_form'}]
    assert {n.name for n in methods}=={'selected','build','_receive_form'}
    namespace=dict(vars(own('runtime')))
    exec(compile(ast.fix_missing_locations(ast.Module(methods,[])),'<authenticated-original-A102-message-boundaries>','exec'),namespace)
    return SimpleNamespace(**{n.name:namespace[n.name] for n in methods})

def configuration():
    declarations={key:{'credit_unit':2.5,'kind':'accumulation' if key.endswith('verified_source_leads') else 'remaining_commissioned_credit',
        'cutoff':.25,'uncertainty_alpha':.1} for key in own('literature_task_credit').YIELD_TASKS}
    return {'outcome_page_size':3,'structure_population':False,'private_yield_binding':True,'yield_bindings':declarations}

def assignment(role,source,artifact,proposed,length,task):
    page={'version':'page_assignment_v1','source_ref':source['id'],'representation':'original',
        'artifact_ref':artifact,'question_context_refs':[],'prior_delivery_refs':[]}
    window={'source_ref':source['id'],'representation':'original','offset':0,'limit':length}
    if role=='literature_page':value=page
    elif role in ('literature_table','literature_ordered','literature_targeted'):
        value={'version':'reading_assignment_v1','page':page,'selection':{'spans':[window]} if role=='literature_targeted' else window}
    else:
        version,field={'literature':('literature_assignment_v1','source_refs'),
            'literature_strategy':('strategy_assignment_v1','prior_search_refs'),
            'literature_search':('search_assignment_v1','search_result_refs')}[role]
        value={'version':version,'question_context_refs':[],field:[source['id']]}
    value.update(literature_task=deepcopy(task),proposed_annotation_ref=proposed);return value


def save_parent(workflow,task):
    workflow.journal.save('runtime_episodes',{'episode_id':task.episode_id,'path':own('runtime')._json(task.path),
        'request':own('runtime')._json(task.request.as_record()),'initial_credit':0.,'state':'active','completion':None,'archive':None})


@contextmanager
def fixture(edge,output):
    parent,role,child=edge;output=Path(output)
    runtime=own('runtime')
    if parent=='scientific_process':
        scientific_type=own('scientific_process.episode').ScientificProcessEpisode
        constructor=scientific_type.__init__
        def configured(self,services,**kwargs):
            assert kwargs['child_roles']==('scientific_process',)
            kwargs['child_roles']=('scientific_process','literature')
            constructor(self,services,**kwargs)
        with patch.object(scientific_type,'__init__',configured):
            with head_checks.actual(output/'scientific-parent') as head:
                host=head.workflow;task=head.task;binding=head.binding
                raw=b'Original synthetic source claim; no biological finding is asserted.'
                artifact=host.store.artifact(raw)
                record=host.store.put('source',{'provider':'source_request_engineering_fixture','accession':None,'uri':None,
                    'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None,'parent_source_refs':[]},origin='caller')
                bindings={h:source_helpers.own(h.replace('/','.')+'.episode').LiteratureEpisode(host.services,**deepcopy(configuration()))
                    for h,_ in source_helpers.HOMES}
                host.episode_bindings=own('episode_bindings').EpisodeBindingRegistry((binding,*bindings.values()))
                for name in dict.fromkeys(r for _,r in source_helpers.HOMES):
                    host.grains[name]=runtime.Grain(name,'Original source question','Original qualified result',source_helpers.forbidden)
                graph={host.grains[name]:tuple(host.grains[r] for r in
                    (('scientific_process','literature') if name in ('annotation','scientific_process') else
                    tuple(r for r,_ in source_helpers.CHILDREN.get(name,())))) for name in host.grains}
                host.tree=runtime.EpisodeTree(host.grains['annotation'],graph,self_nesting=('scientific_process',))
                host.context=runtime.ReleasingContext(tree=host.tree,run_id=host.run_id)
                host.receipts.receive(task.episode_id,[record['id'],artifact],kind='initial')
                credit=own('literature_task_credit');task_value={'version':credit.VERSION,'evidence_axis':'A102',
                    'credit_unit':2.5,'kind':'verified_source_leads','yield_settings':{
                        'kind':'accumulation','cutoff':.25,'uncertainty_alpha':.1}}
                value=SimpleNamespace(workflow=host,task=task,binding=binding,bindings=bindings,source=record,artifact=artifact,
                    raw=raw,proposed=head.proposed,task_value=task_value,scope=plain(task.scope),output=output,
                    schema=own('domain').obj({'answers':credit.lead_return_schema()}))
                yield finish_fixture(value,edge)
    else:
        with source_helpers.fixture(parent or 'published_evidence_assessment',output/'source-parent') as base:
            host=base.workflow;binding=base.binding if parent else None
            path=base.context.path if parent else base.context.path[:1]
            assigned=deepcopy(base.assignment) if parent else {'proposed_annotation_ref':base.proposed}
            goal=runtime.EpisodeGoal.root(objective='Original parent source question',result_contract={'role':path[-1][0]})
            contract=runtime.TypedReportContract('Original qualified parent result',base.schema,lambda *_:True)
            request=runtime.EpisodeRequest(goal,runtime.Record({'scope':plain(base.context.scope),
                'initial_report':{},'episode_assignment':assigned}),contract)
            source_type=getattr(binding,'decision_source_type',runtime.DecisionSource)
            task=source_type(host,path,request,plain(base.context.scope));save_parent(host,task)
            host.receipts.bind(task.episode_id)
            host.receipts.receive(task.episode_id,list(base.context.received_record_refs),kind='initial')
            value=SimpleNamespace(workflow=host,task=task,binding=binding,bindings=base.bindings,source=base.source,
                artifact=base.artifact,raw=base.raw,proposed=base.proposed,task_value=base.assignment['literature_task'],
                scope=plain(base.context.scope),output=output,schema=base.schema)
            yield finish_fixture(value,edge)


def finish_fixture(value,edge):
    parent,role,child=edge;host=value.workflow
    host.inprocess_completion_order=None
    host.launch_instructions=own('launch_instructions').LaunchInstructions.freeze(value.output/'launch-instructions')
    value.edge=edge;value.child=value.bindings[child]
    assert host.specialist(value.task) is value.binding
    assert host.episode_bindings.for_child(value.task.path,role) is value.child
    value.selection={'kind':'episode_child','role':role,'scope':deepcopy(value.scope),
        'goal':'Examine the original source question','purpose':'Return original qualified source-lead dispositions',
        'assignment':assignment(role,value.source,value.artifact,value.proposed,len(value.raw),value.task_value),
        'schema_json':own('runtime')._json(value.schema),'initial_report_json':'{}'}
    return value


def snapshot(workflow):
    return {name:[dict(row) for row in workflow.store.db.execute('SELECT * FROM '+name+' WHERE run_id=? ORDER BY rowid',(workflow.run_id,))]
        for name in ('runtime_actions','runtime_episodes','runtime_receipt_inheritance','runtime_record_receipts')}


def selected_observation(value,case,methods,private=False):
    runtime=own('runtime');host=value.workflow;task=value.task;child=value.child
    selection=deepcopy(value.selection);index=7
    if case=='bad_assignment':selection['assignment']['unrecognized_original_operand']=True
    elif case=='bad_initial':selection['initial_report_json']='{'
    elif case=='bad_pin':selection['assignment']['launch_instructions']={'invalid':'original pin'}
    elif case=='missing_goal':selection.pop('goal')
    elif case not in ('valid','saved_same','saved_changed','action_same','action_changed'):raise AssertionError(case)
    original_admit=child.prepare_assignment;constructor_type=getattr(child,'decision_source_type',runtime.DecisionSource)
    original_constructor=constructor_type.__init__;original_pins=host.launch_instructions.materialize
    original_bind=host.receipts.bind;original_specialist=host.specialist
    trace=[];captured={};route=[];selected_object=selection['assignment']
    def admission(context,role,assignment,scope,operation_key):
        trace.append('child_admission');assert assignment is selected_object
        assert operation_key==host.run_id+':'+task.episode_id+':'+str(index)
        result=original_admit(context,role,assignment,scope,operation_key);captured['admitted']=plain(result);return result
    def pins(value):trace.append('launch_pins');return original_pins(value)
    original_allowed=None if value.binding is None else value.binding.allowed_children
    def allowed(*args,**kwargs):trace.append('allowed_children');return original_allowed(*args,**kwargs)
    def inheritance(episode_id,parent_id=None):
        trace.append('knowledge_inheritance');assert host.store.db.in_transaction
        result=original_bind(episode_id,parent_id);captured['inheritance']=plain(result);return result
    def constructed(self,*args,**kwargs):
        original_constructor(self,*args,**kwargs)
        if self.path[:-1]!=task.path:return
        trace.append('actual_child_constructor');assert host.store.db.in_transaction
        row=host.journal.row('runtime_actions',task.episode_id,index)
        assert json.loads(row['action'])==selection and row['result'] is None
        captured.update(request=plain(self.request.as_record()),episode_id=self.episode_id,path=plain(self.path),
            known=sorted(host.receipts.known(self.episode_id)),source_type=type(self).__module__+'.'+type(self).__qualname__)
        assert value.source['id'] in captured['known']
        if case not in ('saved_same','saved_changed'):raise ConstructionObserved('actual_child_constructed')
    def specialist(source):
        if source.path[:-1]==task.path:
            trace.append('saved_request_compared');raise ReconstructionObserved('original_saved_request_compared')
        return original_specialist(source)
    def instrument_selector(callback):
        def selected(*args):
            route.append({'event':'selector','role':value.edge[1]});assembler=callback(*args)
            if assembler is None:return None
            assert assembler.__module__==PREFIX+'.'+(value.edge[0].replace('/','.')+'.' if value.edge[0] else '')+'to_child_'+value.edge[2].rsplit('/',1)[-1]
            def invoke(*args,**kwargs):
                route.append({'event':'assembler','owner':assembler.__module__+'.'+assembler.__qualname__})
                return assembler(*args,**kwargs)
            return invoke
        return selected
    before=snapshot(host)
    with ExitStack() as stack:
        stack.enter_context(patch.object(host,'build',MethodType(methods.build,host)))
        stack.enter_context(patch.object(child,'prepare_assignment',admission))
        stack.enter_context(patch.object(host.launch_instructions,'materialize',pins))
        stack.enter_context(patch.object(host.receipts,'bind',inheritance))
        stack.enter_context(patch.object(constructor_type,'__init__',constructed))
        stack.enter_context(patch.object(host,'specialist',specialist))
        if original_allowed is not None:stack.enter_context(patch.object(value.binding,'allowed_children',allowed))
        selector=getattr(value.binding,'child_request_assembler',None)
        if selector is not None:stack.enter_context(patch.object(value.binding,'child_request_assembler',instrument_selector(selector)))
        elif value.binding is None:
            from importlib.util import find_spec
            if find_spec(PREFIX+'.annotation_child_commissioning') is not None:
                module=own('annotation_child_commissioning')
                stack.enter_context(patch.object(module,'literature_request_assembler',instrument_selector(module.literature_request_assembler)))
        result=observe(lambda:methods.selected(host,task,selection,index))
    assert result['status']=='raised',result
    assert snapshot(host)==before,'original commission/receipt transaction did not roll back'
    if case in ('valid','action_same'):
        assert result['type']==__name__+'.ConstructionObserved' and 'actual_child_constructor' in trace,result
    elif case=='saved_same':assert result['type']==__name__+'.ReconstructionObserved',result
    elif case=='saved_changed':
        assert result['type']==PREFIX+'.episode_journal.WorkflowError' and result['message']=='reconstructed immutable assignment differs',result
    elif case=='action_changed':
        assert result['type']==PREFIX+'.episode_journal.WorkflowError' and result['message']=='reconstructed selected work changed',result
    else:assert 'actual_child_constructor' not in trace,result
    if not private:assert route==[],route
    elif case in ('valid','saved_same','saved_changed','action_same'):
        assert [item['event'] for item in route]==['selector','assembler'],route
    elif case=='missing_goal':assert [item['event'] for item in route]==['selector'],route
    else:assert route==[],route
    return {'edge':list(value.edge),'case':case,'trace':trace,'captured':captured,'result':result,'route':route}


def interface_installed():return 'request_assembler' in own('runtime').Workflow.build.__code__.co_varnames

def selected_case(value,case):
    oracle=original_methods();runtime=own('runtime');host=value.workflow;index=7
    if case in ('saved_same','saved_changed'):
        original=selected_observation(value,'valid',oracle)
        captured=original['captured'];saved=deepcopy(captured['request'])
        if case=='saved_changed':saved['message']['initial_report']={'original_saved_difference':True}
        host.journal.save('runtime_episodes',{'episode_id':captured['episode_id'],'path':runtime._json(captured['path']),
            'request':runtime._json(saved),'initial_credit':0.,'state':'active','completion':None,'archive':None})
    elif case in ('action_same','action_changed'):
        saved=deepcopy(value.selection)
        if case=='action_changed':saved['goal']='Different original saved selection'
        host.journal.save('runtime_actions',{'episode_id':value.task.episode_id,'decision_index':index,
            'action':runtime._json(saved),'result':None,'credit':None})
    first=selected_observation(value,case,oracle)
    current=selected_observation(value,case,SimpleNamespace(selected=runtime.Workflow.selected,build=runtime.Workflow.build),
        private=interface_installed())
    original_route=first.pop('route');route=current.pop('route')
    assert original_route==[] and current==first,{'original':first,'current':current}
    if case=='valid':
        assert current['trace']==(['allowed_children'] if value.binding is not None else [])+[
            'launch_pins','child_admission','launch_pins','knowledge_inheritance','actual_child_constructor']
    return {'observation':current,'private_route':route,'interface_installed':interface_installed()}


def selected_assembler(value):
    if value.binding is not None:
        selector=getattr(value.binding,'child_request_assembler',None)
        return None if selector is None else selector(value.edge[1])
    if not interface_installed():return None
    return own('annotation_child_commissioning').literature_request_assembler(value.task,value.child)


def direct_build(value,variant):
    runtime=own('runtime');host=value.workflow;oracle=original_methods();role=value.edge[1]
    constructor_type=getattr(value.child,'decision_source_type',runtime.DecisionSource)
    original_constructor=constructor_type.__init__
    contract=runtime.TypedReportContract(value.selection['purpose'],value.schema,lambda *_:True)
    operands={'parent':value.task.request.goal,'parent_path':value.task.path,'contract':contract,
        'initial':{'answers':[]},'episode_assignment':deepcopy(value.selection['assignment']),
        'job_assignment':{'original_message_operand':['job',3]},
        'scientific_process':{'original_message_operand':['process',None]}}
    if variant in ('malformed_declaration','declaration_without_contract'):
        operands['report_contract_declaration']={'submitted_schema_json':'{}'}
    if variant=='declaration_without_contract':operands['contract']=None
    elif variant=='bad_pin':operands['episode_assignment']['launch_instructions']={'invalid':'original pin'}
    elif variant not in ('full_message','malformed_declaration'):raise AssertionError(variant)
    host.inprocess_completion_order=own('inprocess_replay').VERSION
    observations=[];private_calls=[]
    for route in ('original','current_fallback','private_if_declared'):
        captured={};before=snapshot(host)
        def constructed(self,*args,**kwargs):
            original_constructor(self,*args,**kwargs)
            assert type(self.request) is runtime.EpisodeRequest and type(self.request.goal) is runtime.EpisodeGoal
            assert type(self.request.message) is runtime.Record and host.store.db.in_transaction
            captured.update(request=plain(self.request.as_record()),episode_id=self.episode_id,path=plain(self.path),
                known=sorted(host.receipts.known(self.episode_id)),
                types=[type(obj).__module__+'.'+type(obj).__qualname__ for obj in (self.request,self.request.goal,self.request.message)])
            raise ConstructionObserved('actual_child_constructed')
        def invoke():
            with host.store.transaction():
                if route=='original':return oracle.build(host,role,'direct-child',value.selection['goal'],value.scope,**operands)
                assembler=selected_assembler(value) if route=='private_if_declared' else None
                options={}
                if assembler is not None:
                    def selected(*args,**kwargs):
                        private_calls.append(assembler.__module__+'.'+assembler.__qualname__);return assembler(*args,**kwargs)
                    options['request_assembler']=selected
                return runtime.Workflow.build(host,role,'direct-child',value.selection['goal'],value.scope,**operands,**options)
        with patch.object(constructor_type,'__init__',constructed):result=observe(invoke)
        assert snapshot(host)==before
        observations.append({'captured':captured,'result':result})
    assert observations[0]==observations[1]==observations[2],observations
    if variant=='full_message':
        captured=observations[0]['captured'];assert value.source['id'] in captured['known']
        assert captured['request']['message']['job_assignment']==operands['job_assignment']
        assert captured['request']['message']['scientific_process']==operands['scientific_process']
        assert captured['request']['message']['inprocess_completion_order']=={'version':host.inprocess_completion_order}
    else:
        assert not observations[0]['captured']
        if variant=='declaration_without_contract':
            assert observations[0]['result']['type']=='builtins.AttributeError'
            assert observations[0]['result']['message']=="'NoneType' object has no attribute 'schema'"
    assert len(private_calls)==(1 if interface_installed() else 0)
    return {'edge':list(value.edge),'variant':variant,'observation':observations[0],
        'private_calls':private_calls,'interface_installed':interface_installed()}


def nonparticipant(value,mode):
    runtime=own('runtime');host=value.workflow;source=value.task;binding=value.binding
    dispatches=[];calls=[];original_specialist=host.specialist
    class ParentWithoutAssembly:
        def __getattr__(self,name):
            if name=='child_request_assembler':raise AttributeError(name)
            return getattr(binding,name)
    class ParentDecliningAssembly(ParentWithoutAssembly):
        def child_request_assembler(self,role):dispatches.append(role);return None
    def legacy_signature(name,key,goal_text,scope,*,parent=None,parent_path=(),contract=None,initial=None,
            job_assignment=None,episode_assignment=None,scientific_process=None,report_contract_declaration=None):
        calls.append({'name':name,'key':key,'goal':goal_text,'scope':plain(scope),'assignment':plain(episode_assignment)})
        raise ConstructionObserved('original_build_signature_preserved')
    before=snapshot(host)
    with ExitStack() as stack:
        stack.enter_context(patch.object(host,'build',legacy_signature))
        if binding is not None:
            proxy=ParentWithoutAssembly() if mode=='absent' else ParentDecliningAssembly()
            stack.enter_context(patch.object(host,'specialist',lambda task:proxy if task is source else original_specialist(task)))
        else:
            assert mode=='returns_none'
            if interface_installed():
                module=own('annotation_child_commissioning')
                def decline(*args):dispatches.append(value.edge[1]);return None
                stack.enter_context(patch.object(module,'literature_request_assembler',decline))
        result=observe(lambda:runtime.Workflow.selected(host,source,deepcopy(value.selection),7))
    assert result['type']==__name__+'.ConstructionObserved' and result['message']=='original_build_signature_preserved',result
    assert snapshot(host)==before
    assert calls==[{'name':value.edge[1],'key':'child_7','goal':value.selection['goal'],'scope':value.scope,
        'assignment':value.selection['assignment']}]
    assert dispatches==([value.edge[1]] if mode=='returns_none' and interface_installed() else [])
    return {'edge':list(value.edge),'mode':mode,'result':result,'calls':calls,
        'dispatches':dispatches,'interface_installed':interface_installed()}


class ObservationRollback(Exception):pass

def database_state(store):
    # This small engineering Store is retained in full, including original facts,
    # receipt order and report attempts. Journal requests use Store's existing
    # logical row decoder; no fixture-specific result normalization hides writes.
    schema=[dict(row) for row in store.db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name')]
    tables={}
    for row in schema:
        if row['type']!='table':continue
        name=row['name'];assert name.replace('_','').isalnum()
        tables[name]=[dict(item) for item in store.db.execute('SELECT * FROM "'+name+'" ORDER BY rowid')]
    return {'schema':schema,'tables':tables}


def structural_return(value):
    import asyncio
    import pytest
    from .source_request_structure_inputs import source,cif,xml,selector
    host=value.workflow;config={**configuration(),'structure_population':True}
    bindings={home:source_helpers.own(home.replace('/','.')+'.episode').LiteratureEpisode(host.services,**deepcopy(config))
        for home,_ in source_helpers.HOMES}
    head=next(b for b in host.episode_bindings._bindings if b.binding_path=='scientific_process')
    host.episode_bindings=own('episode_bindings').EpisodeBindingRegistry((head,*bindings.values()))
    value.bindings=bindings;value.child=bindings[value.edge[2]]
    coordinates=source(host.store,cif(),parents=[value.source['id']])
    validation=source(host.store,xml(),parents=[value.source['id']])
    text='Molecule|Construct|System|Condition|Partner|Experiment'
    literal=source(host.store,text,parents=[value.source['id']],alias=True)
    literals={};offset=0
    for field,quote in zip(('molecule','construct','experimental_system','condition','partner','experiment'),text.split('|')):
        literals[field]={'source_ref':literal['id'],'representation':'original','start':offset,'end':offset+len(quote),'quote':quote}
        offset+=len(quote)+1
    arguments={'source_ref':value.source['id'],'coordinate_source_ref':coordinates['id'],
        'validation_source_ref':validation['id'],'source_kind':'synthetic_fixture','model_number':1,'literals':literals,
        'geometry_panel':[{'endpoint_a':{**selector(),'atom_names':['OE1','OE2']},
            'endpoint_b':{**selector('B','2','LIG'),'atom_names':['N1']},'positive_max_A':3.5,'incompatible_min_A':4.5}],
        'local_panel':[selector(),selector('B','2','LIG')],'evaluation_scope':'conditional_deposited_model_geometry'}
    assigned=deepcopy(value.selection['assignment'])
    assigned['source_refs']=[value.source['id'],coordinates['id'],validation['id'],literal['id']]
    host.receipts.receive(value.task.episode_id,assigned['source_refs'],kind='initial')
    schema=own('domain').obj({'cells':{**own('literature_structure_storage').structure_cells_schema(),
        'x-source':own('a102_literature_bindings').SOURCE_NAME}})
    value.selection['assignment']=assigned
    value.selection['schema_json']=own('runtime')._json(schema);value.selection['initial_report_json']='{}'
    # Produce under the actual selected child's immutable request and receipt
    # inheritance. Possessing another episode's sheet is not cell ownership.
    captured=selected_observation(value,'valid',original_methods())['captured']
    path=tuple(map(tuple,captured['path']));episode_id=captured['episode_id']
    inheritance=host.receipts.bind(episode_id,value.task.episode_id)
    assert plain(inheritance)==captured['request']['message']['knowledge_inheritance']
    context=replace(host.binding_context(value.task),role='literature',path=path,episode_id=episode_id,
        assignment=captured['request']['message']['episode_assignment'],request=captured['request'],
        received_record_refs=tuple(host.receipts.known(episode_id)))
    result=asyncio.run(value.child.execute(context,'literature.structure.populate',arguments,'original-outgoing-boundary-science'))
    assert result['status']=='completed',result
    rows=value.child.literature_structure_repository().project_cells([result['result']['sheet_ref']],
        permitted_record_refs=result['record_refs'],components=('source_geometry_signed','local_fit_index'))
    assert len(rows)==2 and rows[0]['value']==rows[1]['value']==pytest.approx(.64)
    assert all(row['origin']=='proposed' and row['unconditional_uncertainty']=='unreported' for row in rows)
    return {'cells':rows},schema,result


def receive_case(value,case,redelivery,progress):
    assert value.edge in EDGES[:2]
    host=value.workflow;runtime=own('runtime');task=value.task;index=7
    form={'answers':[]};schema=value.schema;science=None
    if case=='nonempty':form,schema,science=structural_return(value)
    captured=selected_observation(value,'valid',original_methods())['captured']
    child_id=captured['episode_id'];child_path=tuple(map(tuple,captured['path']));request=captured['request']
    host.journal.save('runtime_episodes',{'episode_id':child_id,'path':runtime._json(child_path),
        'request':runtime._json(request),'initial_credit':0.,'state':'active','completion':None,'archive':None})
    inheritance=host.receipts.bind(child_id,task.episode_id)
    assert plain(inheritance)==request['message']['knowledge_inheritance']
    if science is not None:host.receipts.receive(child_id,science['record_refs'],kind='initial')
    child_context=own('episode_return_records').EpisodeReturnRecords(host.store,host.run_id,failure_prefix='recorded_admission_').context(child_id)
    child_context=replace(child_context,received_record_refs=tuple(host.receipts.known(child_id)))
    child_report=observe(lambda:value.child.validate_report(child_context,form,schema))
    assert child_report['status']=='returned',child_report
    action={'episode_id':task.episode_id,'decision_index':index,'action':runtime._json(value.selection),'result':None,'credit':None}
    host.journal.save('runtime_actions',action)
    facts={node['x-source']:form[name] for name,node in schema['properties'].items() if 'x-source' in node}
    host.journal.save('runtime_forms',{'episode_id':child_id,'facts':runtime._json(facts),'form':runtime._json(form)})
    attempt={'parent_episode_id':task.episode_id,'decision_index':index,'delivery_ref':'original-source-report',
        'child_episode_id':child_id,'contract':runtime._json(request['report_contract']),
        'form':runtime._json(form),'failure':None,'timing_receipts':None,'report_contract_declaration':None}
    host.journal.save('runtime_report_attempts',attempt)
    registry=host.episode_bindings
    if case in ('cached','cached_ambiguous','cached_malformed_action'):
        action['result']=runtime._json({'status':'completed','record_refs':[]})
    elif case=='invalid_cached_result':action['result']='{'
    if case in ('malformed_action','cached_malformed_action'):action['action']='{'
    elif case=='action_list':action['action']='[]'
    elif case=='foreign_role':action['action']=runtime._json({'kind':'episode_child','role':'foreign_original_role'})
    elif case=='role_conflict':action['action']=runtime._json({'kind':'episode_child','role':'monitor'})
    host.journal.save('runtime_actions',action)
    if case=='no_action':
        for table,key in (('runtime_actions','episode_id'),('runtime_report_attempts','parent_episode_id')):
            host.store.db.execute('DELETE FROM '+table+' WHERE run_id=? AND '+key+'=? AND decision_index=?',(host.run_id,task.episode_id,index))
    elif case=='action_only':
        host.store.db.execute('DELETE FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
            (host.run_id,task.episode_id,index))
    elif case=='missing_child':
        host.store.db.execute('DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?',(host.run_id,child_id))
    elif case=='parent_conflict':
        wrong=list(child_path);wrong[0]=(wrong[0][0],'foreign-original-root')
        host.store.db.execute('UPDATE runtime_episodes SET path=? WHERE run_id=? AND episode_id=?',
            (runtime._json(wrong),host.run_id,child_id))
    elif case=='custom_registry':
        class ActualRegistrySubclass(type(registry)):pass
        host.episode_bindings=ActualRegistrySubclass(registry._bindings)
    elif case in ('foreign_binding','ambiguous_binding','cached_ambiguous'):
        class CallerSuppliedChild(type(value.child)):pass
        foreign=CallerSuppliedChild(host.services,**deepcopy(configuration()))
        if case!='foreign_binding':foreign.binding_path='explicit_caller_supplied_source'
        bindings=[foreign if binding is value.child and case=='foreign_binding' else binding for binding in registry._bindings]
        if case!='foreign_binding':bindings.append(foreign)
        host.episode_bindings=type(registry)(bindings)
    else:assert case in ('valid','nonempty','cached','cached_malformed_action','invalid_cached_result',
        'malformed_action','action_list','foreign_role','role_conflict')
    observations=[];private_routes=[]
    before=database_state(host.store)
    for method in (original_methods()._receive_form,runtime.Workflow._receive_form):
        callbacks=[];route=[]
        # This records the original provider callback boundary and return value;
        # it makes no new timing observation or scientific-progress claim.
        class OriginalProgressBoundary:
            def receive_form(self,*args):callbacks.append(plain(args));return None
        provider=OriginalProgressBoundary() if progress else None
        def instrument(callback):
            def choose(*args):
                receiver=callback(*args)
                if receiver is None:return None
                owner=PREFIX+'.'+('scientific_process.' if value.edge[0] else '')+'from_child_published_evidence_assessment.receive_report'
                assert receiver.__module__+'.'+receiver.__qualname__==owner
                def receive(*a,**kw):route.append(owner);return receiver(*a,**kw)
                return receive
            return choose
        with ExitStack() as stack:
            stack.enter_context(patch.object(host,'progress_provider',provider))
            if interface_installed():
                if value.binding is None:
                    module=own('annotation_child_commissioning')
                    stack.enter_context(patch.object(module,'literature_report_receiver',instrument(module.literature_report_receiver)))
                else:
                    callback=value.binding.published_evidence_report_receiver
                    stack.enter_context(patch.object(value.binding,'published_evidence_report_receiver',instrument(callback)))
            try:
                with host.store.transaction():
                    first=observe(lambda:method(host,task,form,schema,index,redelivery=redelivery))
                    second=observe(lambda:method(host,task,form,schema,index,redelivery=redelivery))
                    observations.append({'result':first,'repeat_result':second,'callbacks':callbacks,
                        'database_after':database_state(host.store),'known':sorted(host.receipts.known(task.episode_id))})
                    private_routes.append(route);raise ObservationRollback()
            except ObservationRollback:pass
        assert database_state(host.store)==before
    assert observations[0]==observations[1],{'before':observations[0],'after':observations[1]}
    assert private_routes[0]==[]
    selected=case in ('valid','action_only','cached','invalid_cached_result','nonempty')
    assert len(private_routes[1])==(2 if interface_installed() and selected else 0),private_routes
    if case=='cached_ambiguous' and not redelivery:
        assert observations[0]['result']=={'status':'returned','value':[]} and not observations[0]['callbacks']
    if case in ('valid','nonempty','action_only','cached'):
        assert observations[0]['result']['status']=='returned',observations[0]
        if case=='nonempty':assert observations[0]['result']['value']
    return {'edge':list(value.edge),'case':case,'redelivery':redelivery,'progress':progress,
        'child_report':child_report,'science':science,'form':form,'schema':schema,
        'observation':observations[0],'private_route':private_routes[1],'interface_installed':interface_installed()}
