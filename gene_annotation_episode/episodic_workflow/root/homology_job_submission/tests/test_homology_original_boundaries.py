"""Root Homology original role, failure, credit and commissioning identity controls.

Typed resource construction is bypassed only to avoid native registry I/O; real
resource classes and every actual private binding constructor remain in use.
"""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace
import pytest
ROOT='gene_annotation_episode.episodic_workflow.root'
ROLES=('job_launch','job_monitor','job_results')
BASE=(('homology_job_submission','HomologySubmissionEpisodes','job_launch'),
      ('homology_job_monitoring','HomologyMonitoringEpisodes','job_monitor'),
      ('homology_result_acquisition','HomologyAcquisitionEpisodes','job_results'))
CASES=tuple((prefix+home,('Legacy' if prefix else '')+name,role)
    for prefix in ('','legacy_annotation/') for home,name,role in BASE)
ORIGINAL_SHA='0970c0fa12d811a059ec339c8250fe1e2280645959acb1c6fc921f9d2ab246ae'


def original_class():
    path=Path(__file__).with_name('fixtures')/'original_boundary/homology_episodes.py.source'
    raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA
    cls=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='HomologyEpisodes')
    namespace=dict(globals(),__package__=ROOT,__name__=ROOT+'.tests._original_homology_boundary',
        HomologyJobs=importlib.import_module(ROOT+'.homology_jobs').HomologyJobs,
        LocalJobPolicy=importlib.import_module('gene_annotation_episode.local_jobs').LocalJobPolicy,
        ContractError=importlib.import_module('gene_annotation_episode.domain').ContractError,
        AcquisitionError=importlib.import_module('gene_annotation_episode.acquisition').AcquisitionError,
        ReportBoundaryError=importlib.import_module(ROOT+'.communication').ReportBoundaryError)
    nodes=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),cls]
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(path),'exec'),namespace)
    return namespace['HomologyEpisodes']


def resource():
    # Exact class identity is required by the original constructor. No native
    # registry is opened and no launch/sample/extract operation is performed.
    return object.__new__(importlib.import_module(ROOT+'.homology_jobs').HomologyJobs)


def configured(cls,*,value=2.5,events=None,jobs=None,**overrides):
    events=[] if events is None else events
    def operational(store,**kw): events.append(('operational',deepcopy(kw))); return {'credit':value}
    def monitoring(store,**kw): events.append(('monitoring',deepcopy(kw))); return value
    kw=dict(parser_policy=importlib.import_module('gene_annotation_episode.local_jobs').LocalJobPolicy(1024,2048),
        credit_projector=operational,credit_binding={'version':'controlled_operational','units':['a']},
        monitoring_projector=monitoring,monitoring_binding={'version':'controlled_monitoring','units':['b']})
    kw.update(overrides)
    return cls(resource() if jobs is None else jobs,**kw)


def capture(callback):
    try:return ('returned',callback())
    except Exception as error:return ('raised',type(error),str(error),getattr(error,'code',getattr(error,'diagnostic',{}).get('code')))


@pytest.fixture(scope='module')
def baseline():return original_class()


@pytest.mark.parametrize('home,name,role',CASES)
@pytest.mark.parametrize('value',(0.0,2.5,-1.0,float('inf'),float('nan')))
def test_original_role_credit_and_copy_custody(home,name,role,value,baseline):
    observations=[]
    for cls in (baseline,getattr(importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode'),name)):
        events=[]; binding=configured(cls,value=value,events=events)
        assignment={'job_ref':'job_'+'1'*24,'cpu':2,'query_ref':'subject_'+'2'*24}
        result=capture(lambda:binding.initial_credit(None,role,assignment,'episode:original','run:original'))
        current=binding.binding_for(role); current['units'].append('changed')
        observations.append((result,events,binding.binding_for(role),binding.credit_kind(role),assignment))
    assert observations[0]==observations[1]
    expected='monitoring' if role=='job_monitor' else 'operational'
    assert observations[1][1][0][0]==expected
    assert observations[1][3]==expected
    assert 'changed' not in observations[1][2]['units']
    if math.isfinite(value):assert observations[1][0]==('returned',value)
    else:assert observations[1][0][0]=='raised'


@pytest.mark.parametrize('home,name,role',CASES)
@pytest.mark.parametrize('scenario',('wrong_resource','wrong_policy','no_credit','empty_credit','no_monitor','empty_monitor'))
def test_original_explicit_typed_resource_and_projector_rejection(home,name,role,scenario,baseline):
    def build(cls):
        changes={'wrong_resource':{'jobs':object()},'wrong_policy':{'parser_policy':object()},
            'no_credit':{'credit_projector':None},'empty_credit':{'credit_binding':{}},
            'no_monitor':{'monitoring_projector':None},'empty_monitor':{'monitoring_binding':{}}}[scenario]
        return capture(lambda:configured(cls,**changes))
    cls=getattr(importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode'),name)
    assert build(cls)==build(baseline)
    assert build(cls)[0]=='raised'


@pytest.mark.parametrize('home,name,role',CASES)
@pytest.mark.parametrize('failure',('value','storage','os','contract','unowned'))
def test_original_executed_failure_and_unacquired_tool_boundary(home,name,role,failure,baseline):
    observations=[]
    for cls in (baseline,getattr(importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode'),name)):
        events=[]; jobs=resource(); binding=configured(cls,jobs=jobs)
        errors={'value':ValueError('controlled_failed'),'storage':sqlite3.OperationalError('controlled_failed'),
                'os':OSError('controlled_failed'),
                'contract':importlib.import_module('gene_annotation_episode.domain').ContractError('controlled_failed')}
        def row(ref):events.append(('row',ref)); raise errors[failure]
        jobs._row=row
        operation={'job_launch':'homology.environment','job_monitor':'homology.sample','job_results':'homology.extract'}[role]
        binding.catalog=lambda source:[{'name':operation}]
        binding.assignment=lambda source:{'job_ref':'job_'+'1'*24,'cpu':2}
        source=SimpleNamespace(path=(('annotation','root'),(role,'child')),scope={},workflow=SimpleNamespace(store=None))
        name_used='homology.unowned' if failure=='unowned' else operation
        result=capture(lambda:asyncio.run(binding._execute(source,name_used,{},operation_key='original:operation')))
        observations.append((result,events))
    assert observations[0]==observations[1]
    if failure=='unowned':assert observations[1][0][0]=='raised' and observations[1][1]==[]
    else:
        assert observations[1][0][1]['status']=='failed'
        assert observations[1][0][1]['result'] is None
        assert observations[1][0][1]['feedback']['operation']==operation


@pytest.mark.parametrize('home,name,role',CASES)
def test_typed_return_source_conflict_keeps_original_exception_identity(home,name,role,baseline):
    observed=[]
    for cls in (baseline,getattr(importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode'),name)):
        binding=configured(cls); binding.fact_sources=lambda selected:{'job_ref':{}}
        observed.append(capture(lambda:binding._validate_role_return_sources(role,
            {'properties':{'unsupported':{'x-source':'job_foreign_fact'}}})))
    assert observed[0]==observed[1]
    assert observed[1][1] is importlib.import_module(ROOT+'.communication').ReportBoundaryError
    assert observed[1][3]=='homology_return_source_role_conflict'


@pytest.mark.parametrize('role',ROLES)
@pytest.mark.parametrize('parents',(('annotation',),('improvement',),('annotation','improvement'),
    ('improvement','improvement'),('annotation','improvement','improvement')))
def test_real_parent_lineage_selects_fixed_private_owner(role,parents):
    family=configured(importlib.import_module(ROOT+'.library.homology_episode_family').HomologyEpisodes)
    path=tuple((parent,'context_'+str(index)) for index,parent in enumerate(parents))
    selected=family.implementation_for_path(path,child_role=role)
    assert selected is family.implementation_for_path(path+((role,'child'),))
    expected=next(row for row in CASES if row[2]==role and row[0].startswith('legacy_annotation/')==('improvement' in parents))
    assert selected.binding_path==expected[0] and type(selected).__name__==expected[1]
    assert selected.jobs is family.jobs and selected._custody is family._custody
    assert selected.child_roles(role)==()


@pytest.mark.parametrize('path',((),(('scientific_process','x'),),(('hpc','x'),),
    (('monitor','x'),),(('annotation','x'),('scientific_process','y')),
    (('improvement','x'),('annotation','y')),(('annotation','x'),('job_launch','y'),('improvement','z'))))
def test_unowned_parent_lineages_do_not_acquire_homology_identity(path):
    family=configured(importlib.import_module(ROOT+'.library.homology_episode_family').HomologyEpisodes)
    assert capture(lambda:family.implementation_for_path(path,child_role='job_launch'))[0]=='raised'
