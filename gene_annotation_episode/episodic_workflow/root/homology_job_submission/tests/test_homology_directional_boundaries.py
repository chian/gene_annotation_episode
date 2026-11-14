"""Main-owned Homology parent recipes, exercised in an authenticated source view.

Uses actual private assignment functions and original family assignment with
controlled registry/store ports. Full Main hook/registry integration is separate.
"""
from __future__ import annotations
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace
import pytest
ROOT='gene_annotation_episode.episodic_workflow.root'
helpers=importlib.import_module(ROOT+'.execution_monitoring.tests.test_monitor_directional_boundaries')
homology=importlib.import_module(ROOT+'.homology_job_submission.tests.test_homology_original_boundaries')
BASE=(('homology_job_submission','job_launch'),('homology_job_monitoring','job_monitor'),
      ('homology_result_acquisition','job_results'))
PARENTS=(('annotation',),('improvement',),('annotation','improvement','improvement'))
JOB='homology_job_'+'1'*24
SUBJECT='subject_'+'2'*24


def endpoint(home,parents,direction):
    prefix='legacy_annotation.' if parents[-1]=='improvement' else ''
    module=ROOT+'.'+prefix+direction+'_child_'+home
    return getattr(importlib.import_module(module),'prepare_request' if direction=='to' else 'admit_return')


def outgoing(callback,home,role,parents,scenario,*,original):
    events=[];path=tuple((name,'parent_'+str(index)) for index,name in enumerate(parents))
    source=SimpleNamespace(path=path,episode_id='episode:original')
    jobs=homology.resource();jobs.config={}
    def row(reference):
        events.append(('job',reference))
        if scenario=='storage_failure':raise ValueError('controlled_job_not_registered')
        return {'job_ref':JOB,'query_ref':SUBJECT,'cpu':2,'search_mode':'native_defaults'}
    jobs._row=row
    jobs.check_handoff=lambda handoff:events.append(('handoff',deepcopy(handoff)))
    def query(store,scope,reference):
        events.append(('query',reference))
        if scenario=='foreign_query':
            raise importlib.import_module('gene_annotation_episode.domain').ContractError('controlled_query_not_visible')
        return {'id':reference}
    if original:
        binding=homology.configured(homology.original_class(),jobs=jobs);binding._query=query
    else:
        cls=importlib.import_module(ROOT+'.library.homology_episode_family').HomologyEpisodes
        binding=homology.configured(cls,jobs=jobs)
        for owned in (*binding._implementations.values(),*binding._standalone_implementations.values()):owned._query=query
        chosen=binding.implementation_for_path(path,child_role=role)
        assert chosen.binding_path==('legacy_annotation/' if parents[-1]=='improvement' else '')+home
    scope={'subject_refs':[SUBJECT]}
    selection={'kind':'job_child','role':role,'goal':'Preserve original Homology request.',
        'purpose':'Typed native execution information.',
        **({'existing_job_ref':JOB} if role=='job_launch' else {'handoff':{'job_ref':JOB}})}
    wf=SimpleNamespace(run_id='run:original',job_episodes=binding,store=SimpleNamespace())
    def form(*args,**kw):events.append(('form',args[2],args[3],kw));return deepcopy(helpers.SCHEMA),None
    wf.expanded_contract_form=form
    wf.child_initial_report_input=lambda *args:json.dumps({'qualified':'invalid' if scenario=='invalid_initial' else False})
    def resolver(scope,*,grain):events.append(('resolver',deepcopy(scope),grain));return lambda *args:True
    def validate(value,scope,*,grain,schema):events.append(('validate_report',deepcopy(value),deepcopy(scope),grain,deepcopy(schema)))
    wf.resolver=resolver;wf.validate_report=validate
    result=helpers.capture(lambda:callback(wf,source,selection,4,scope,role,None))
    return result,events


@pytest.mark.parametrize('home,role',BASE)
@pytest.mark.parametrize('parents',PARENTS)
@pytest.mark.parametrize('scenario',('valid','invalid_initial','foreign_query','storage_failure'))
def test_original_job_request_actual_parent_owner_and_assignment(home,role,parents,scenario):
    actual=outgoing(endpoint(home,parents,'to'),home,role,parents,scenario,original=False)
    expected=outgoing(helpers.original_callbacks()[0],home,role,parents,scenario,original=True)
    assert actual==expected
    if scenario=='valid':
        assert actual[0][0]=='returned' and len(actual[0][1])==6
        assert actual[0][1][3:5]==(None,None)
        assert actual[0][1][5]['job_ref']==JOB and actual[0][1][5]['cpu']==2
        assert actual[0][1][5]['query_ref']==SUBJECT
    else:assert actual[0][0]=='raised'
    if scenario=='invalid_initial':assert not any(row[0] in ('job','query','handoff') for row in actual[1])
    assert actual[1][0][-1]=={'owner':None}


@pytest.mark.parametrize('home,role',BASE)
@pytest.mark.parametrize('parents',(('annotation',),('improvement',)))
@pytest.mark.parametrize('scenario',('fresh','invalid','saved','saved_failure','redelivery'))
def test_original_job_return_typed_admission_saved_failure_and_redelivery(home,role,parents,scenario):
    actual=helpers.incoming(endpoint(home,parents,'from'),scenario)
    expected=helpers.incoming(helpers.original_callbacks()[1],scenario)
    assert actual==expected and actual[0]==actual[1]
    if scenario in ('invalid','saved_failure'):
        assert actual[0][1] is importlib.import_module(ROOT+'.method_loop.episode').ReportDeliveryError
        assert not any(row[0]=='receive' for row in actual[2])
    else:assert actual[0][0]=='returned' and actual[0][1][1]==['record_'+'4'*24]
