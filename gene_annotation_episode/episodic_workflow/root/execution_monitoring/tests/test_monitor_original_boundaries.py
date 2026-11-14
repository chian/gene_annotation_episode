"""Original MonitorEpisodes boundaries across actual Root private consumers.

The baseline executes pinned original callable AST with the preserved current
Root contracts/numerical providers. Controlled service ports do no native work.
This does not validate full parent commissioning, restoration or autonomous work.
"""
from __future__ import annotations
import ast
import asyncio
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
import math
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = 'gene_annotation_episode.episodic_workflow.root'
HOMES = tuple(prefix+home for prefix in ('','legacy_annotation/','scientific_process/')
    for home in ('execution_monitoring','hpc_coordination/execution_monitoring',
                 'hpc_coordination/hpc_allocation_execution/execution_monitoring'))
ORIGINAL_SHA = '118809b224ce84ac5b66d9c481c64b8e7c94ffcd3631e02b3eafad0fcd9b9872'
PROGRESS = 'progress_'+'1'*24
SOURCE = 'source_'+'2'*24
ARTIFACT = 'artifact_'+'3'*24


def original_class():
    path = Path(__file__).with_name('fixtures')/'original_boundary/episode_monitoring.py.source'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_SHA
    domain = importlib.import_module('gene_annotation_episode.domain')
    communication = importlib.import_module(ROOT+'.communication')
    bindings = importlib.import_module(ROOT+'.episode_bindings')
    plain = communication.plain
    namespace = dict(globals(), __package__=ROOT, __file__=str(path),
        __name__=ROOT+'.tests._pinned_original_monitor_boundary', plain=plain,
        validate_form=communication.validate_form,
        native_observation_options=bindings.native_observation_options,
        reference_in_context=bindings.reference_in_context)
    namespace.update({name:getattr(domain,name) for name in
        ('ContractError','REF','RECORD_SCHEMAS','identity','obj','validate_schema')})
    assignments = {'VERSION','FIELDS','_STATES','_REFS','_FIELDS','_TEXT','_ASSIGNMENT'}
    functions = {'_timestamp','_unique','_monitor_information_yield','_blast_monitor_yield'}
    nodes = [ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]
    for node in ast.parse(raw).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in node.targets):
            nodes.append(node)
        elif isinstance(node,ast.FunctionDef) and node.name in functions:
            nodes.append(node)
        elif isinstance(node,ast.ClassDef) and node.name == 'MonitorEpisodes':
            nodes.append(node)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(path),'exec'),namespace)
    return namespace['MonitorEpisodes']


class Ports:
    def __init__(self, *, blast=False, fail_observe=False, log_failure=False):
        self.calls=[]; self.blast=blast; self.fail_observe=fail_observe; self.log_failure=log_failure
        self.snapshots={PROGRESS:{
            'progress_ref':PROGRESS,'target_handle':'execution:target',
            'observed_at':'2026-11-13T00:00:00+00:00','execution_status':{'lifecycle_state':'returned'},
            'result_available':False,'committed_record_refs':[], 'dependencies':[],
            'log_windows':[{'source_ref':SOURCE,'artifact_ref':ARTIFACT,'start_byte':0,'end_byte':4}]}}
    def reference_in_scope(self,reference,scope,namespace):
        self.calls.append(('reference',reference,namespace)); return reference != 'execution:foreign'
    def read_progress(self,reference,scope):
        self.calls.append(('read_progress',reference)); return deepcopy(self.snapshots[reference])
    def dependencies(self,target,scope):
        self.calls.append(('dependencies',target)); return [{'handle':'execution:child'}]
    def describe_progress_target(self,target,scope):
        return {'resource_kind':'api','service_or_program':'ncbi_blast'} if self.blast else {}
    def annotation_task_required(self): return True
    def macs2_peak_monitor_task(self,parent,*,assignment):
        self.calls.append(('task_admission',parent.role,dict(assignment)))
    def bound_role_credit(self,context,selection):
        self.calls.append(('credit',context.episode_id,selection)); return {'credit':2.5,'kind':'monitoring'}
    def observe_progress(self,target,fields,scope,**options):
        self.calls.append(('observe',target,list(fields),options['operation_key']))
        if self.fail_observe:
            raise importlib.import_module('gene_annotation_episode.domain').ContractError('controlled_observation_unavailable')
        return deepcopy(self.snapshots[PROGRESS])
    def received_progress_refs(self,episode_id): return [PROGRESS]
    def own_outcomes(self,*args,**kwargs): return {'records':[],'next_offset':None}
    def read_record(self,reference): return {'record_type':'source','artifact_ref':ARTIFACT}
    def execute_tool(self,name,arguments,**kwargs):
        self.calls.append(('tool',name,arguments,kwargs['operation_key']))
        return {'status':'failed','record_refs':[],'changed_record_refs':[],
                'feedback':{'category':'acquisition','code':'controlled_read_failed'}}


class AwaitablePorts(Ports):
    async def observe_progress(self,*args,**kwargs):
        return super().observe_progress(*args,**kwargs)
    async def execute_tool(self,*args,**kwargs):
        return super().execute_tool(*args,**kwargs)


def assignment(target='execution:target', *, permitted=()):
    return {'version':'monitor_assignment_v1','target_handle':target,
            'requested_fields':['execution_status','log_windows'],'known_progress_refs':[],
            'permitted_committed_record_types':list(permitted)}


def context(role='monitor', *, target='execution:target', path=None):
    cls=importlib.import_module(ROOT+'.episode_bindings').BindingContext
    return cls('run:controlled','episode:controlled',role,
        path or (('annotation','root'),(role,'selected')), {'subject_refs':[]},
        assignment(target), {}, received_record_refs=())


def capture(call):
    try: return ('returned',call())
    except Exception as error:
        return ('raised',type(error),str(error),getattr(error,'code',None),getattr(error,'detail',None))


@pytest.fixture(scope='module')
def baseline(): return original_class()


@pytest.mark.parametrize('home',HOMES)
def test_fixed_private_identity_and_contract_schema(home,baseline):
    cls=importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode').MonitorEpisodes
    actual,original=cls(Ports()),baseline(Ports())
    assert actual.binding_path==home and actual.roles==('monitor',)
    assert actual.assignment_schema('monitor')==original.assignment_schema('monitor')
    assert actual.child_roles('monitor')==original.child_roles('monitor')==('monitor',)
    assert actual.credit_kind('monitor')==original.credit_kind('monitor')=='monitoring'
    assert actual.entry_roles == (('monitor',) if home=='execution_monitoring' else ())
    for role in ('job_monitor','launch','scientific_process',None):
        assert capture(lambda:actual.assignment_schema(role))==capture(lambda:original.assignment_schema(role))


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('scenario',('valid','empty_operation','foreign_target','wrong_dependency','expanded_types'))
def test_original_admission_order_and_negative_identity(home,scenario,baseline):
    observations=[]
    for cls in (baseline,importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode').MonitorEpisodes):
        ports=Ports(); binding=cls(ports)
        parent=context(target='execution:parent')
        selected=assignment('execution:child')
        if scenario=='foreign_target': selected['target_handle']='execution:foreign'
        if scenario=='wrong_dependency': selected['target_handle']='execution:unexposed'
        if scenario=='expanded_types': selected['permitted_committed_record_types']=['source']
        key='' if scenario=='empty_operation' else 'operation:assigned'
        result=capture(lambda:binding.prepare_assignment(parent,'monitor',selected,parent.scope,key))
        observations.append((result,deepcopy(ports.calls),selected))
    assert observations[0]==observations[1]
    if scenario=='valid': assert observations[1][0][0]=='returned'
    else: assert observations[1][0][0]=='raised'
    if scenario=='empty_operation': assert observations[1][1]==[]


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('ports_class',(Ports,AwaitablePorts))
@pytest.mark.parametrize('scenario',('success','provider_invalid','unavailable_tool','expanded_fields','failed_log'))
def test_executed_returned_invalid_and_failed_outcomes_preserved(home,scenario,ports_class,baseline):
    observed=[]
    for cls in (baseline,importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode').MonitorEpisodes):
        ports=ports_class(fail_observe=scenario=='provider_invalid'); binding=cls(ports); ctx=context()
        # Delivered observations are controlled input, not fabricated credit.
        binding._received=lambda unused:[PROGRESS]
        tool='progress.log' if scenario=='failed_log' else 'progress.missing' if scenario=='unavailable_tool' else 'progress.observe'
        args=({'progress_ref':PROGRESS,'log_index':0} if scenario=='failed_log' else
              {'requested_fields':['measurements'] if scenario=='expanded_fields' else ['execution_status']})
        result=asyncio.run(binding.execute(ctx,tool,args,'operation:observed'))
        observed.append((result,deepcopy(ports.calls)))
    assert observed[0]==observed[1]
    expected='completed' if scenario=='success' else 'failed' if scenario=='failed_log' else 'invalid'
    assert observed[1][0]['status']==expected
    if scenario in ('expanded_fields','unavailable_tool'):
        assert not any(call[0]=='observe' for call in observed[1][1])
    if scenario=='failed_log':
        assert observed[1][0]['progress_refs']==[PROGRESS]
        assert any(call[0]=='tool' and call[1]=='source.read' for call in observed[1][1])


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('blast',(False,True))
def test_original_credit_wait_and_yield_settings(home,blast,baseline):
    observed=[]
    for cls in (baseline,importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode').MonitorEpisodes):
        ports=Ports(blast=blast)
        binding=cls(ports,information_unit=3.0,
            yield_settings={'kind':'information_accumulation','cutoff':0.25,'uncertainty_alpha':0.2})
        ctx=context(); credit=binding.credit_view(ctx,{'action':'observed'})
        controller=binding.yield_controller(ctx,2.5,'epoch:controlled')
        estimate=controller.estimator.estimate_with_context((),controller.settings,())
        observed.append((credit,binding.permitted_common_actions(ctx),controller.cost,
                         controller.settings.as_record(),estimate.as_record()))
    assert observed[0]==observed[1]
    assert observed[1][0]['credit']==2.5
    assert ('wait' in observed[1][1]) is (not blast)


@pytest.mark.parametrize('home',HOMES)
def test_required_typed_progress_sources_keep_parent_condition(home,baseline):
    actual=importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode').MonitorEpisodes(Ports())
    original=baseline(Ports())
    for parent in (None,context('annotation'),context('scientific_process'),context('hpc')):
        assert actual.required_return_sources(parent,'monitor')==original.required_return_sources(parent,'monitor')
