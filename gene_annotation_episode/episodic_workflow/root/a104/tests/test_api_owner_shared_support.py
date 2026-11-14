"""Actual43-binding report traversal over nonempty controlled saved receipts.

SavedRecords supplies original typed parent/model/action/receipt rows; it does
not claim Workflow.selected admitted the scientific parent's API commission.
Actual Workflow.validate_report and registry selection remain untouched.
"""
from copy import deepcopy
from importlib import import_module
import json
import os
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import commission, resources
from .proteome_partner.binding_owners import PLACEMENTS, binding_types
from .proteome_partner.proteome_host_fixture import ProteomeDriver

PREFIX='gene_annotation_episode.episodic_workflow.root.a104.'
SUPPORT='bvbrc_appservice_support_refs'
def own(name):return import_module(PREFIX+name.replace('/','.'))
def plain(value):return own('communication').plain(value)
def rows(store):return list(store.db.iterdump())

def registry43(driver,directory):
    services=SimpleNamespace(annotation_task_required=lambda:False)
    # This is the same explicit empty information-library boundary as the
    # retained full-registry constructor probe, not a scientific assignment.
    library=SimpleNamespace(as_record=lambda:{},headers=lambda:[])
    science=own('scientific_process/episode').ScientificProcessEpisode(services,
        library=library,tool_library=library,child_roles=('scientific_process','hpc'))
    bindings=[science]
    hpc=dict(store=driver.store,run_id=driver.saved.run_id,directory=directory,
        resources=resources(),commissions={'commission':commission()})
    for parent in ('hpc_work_planning','scientific_process/hpc_work_planning'):
        for suffix in ('','/hpc_allocation_execution','/hpc_resource_prediction'):
            bindings.append(own(parent+suffix+'/episode').HPCEpisode(services,**hpc))
    existing={binding.binding_path:binding for binding in (driver.family,driver.launch_family,driver.parent_family)}
    options=dict(store=driver.store,run_id=driver.saved.run_id,directory=directory,
        resources={'selected-api':deepcopy(driver.config)},initial_information={},
        tool_registry=SimpleNamespace(store=driver.store,clients={}),handoff_unit=2,
        acquired_record_unit=3,log_window_bytes=1024,log_roles=('stdout','stderr'))
    for placement in PLACEMENTS:
        for suffix in ('execution_job_submission','execution_job_submission/api_job_execution',
                'execution_job_submission/local_job_execution','execution_job_submission/hpc_job_execution',
                'execution_result_acquisition'):
            home=placement+suffix
            bindings.append(existing[home] if home in existing else own(home+'/episode').ExecutionEpisode(services,**options))
        bindings.append(own(placement+'execution_progress_assessment/episode').MonitorEpisode(services))
    assert len(bindings)==len({binding.binding_path for binding in bindings})==43
    registry=own('episode_bindings').EpisodeBindingRegistry(bindings)
    return registry,bindings

@pytest.mark.parametrize('role',('launch_api','results'))
def test_actual_registry_and_workflow_validate_nonempty_appservice_support(tmp_path,monkeypatch,role,record_property):
    def forbidden(*args,**kwargs):raise AssertionError('report validation attempted external producer or transport')
    monkeypatch.setattr('socket.create_connection',forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open',forbidden)
    with own('state').Store(tmp_path/'state') as store:
        driver=ProteomeDriver(store,tmp_path,owners=binding_types('scientific_process/'))
        driver.start(supplementary=False)
        if role=='launch_api':
            context=driver.custody.context(driver.handoff['value']['receipt']['origin']['episode_id'])
            selected=driver.launch_family
        else:
            context=driver.support;selected=driver.family
        assert context.role==role
        registry,bindings=registry43(driver,tmp_path)
        assert registry.for_path(context.path) is selected
        active=registry._context_bindings(context)
        assert selected in active
        if role=='launch_api':assert driver.parent_family in active
        schema={'type':'object','properties':{'support':deepcopy(selected._appservice_sources()[SUPPORT]['report_schema'])},
            'required':['support'],'additionalProperties':False}
        expected=selected.api_execution.appservice.facts(context)[SUPPORT]
        assert expected and len(expected)==len(set(expected))
        form={'support':list(expected)}
        # The real Workflow method consumes only these original dependencies
        # for this report. No constructor/admission or default callback is
        # replaced, and every actual selected binding validator still runs.
        workflow=SimpleNamespace(store=store,episode_bindings=registry,
            native_event_information=None,native_timing_information=None,resource_estimator=None)
        before=rows(store);http=deepcopy(driver.client.calls);seen=[]
        def profile(frame,event,arg):
            if event!='call':return
            receiver=frame.f_locals.get('self');name=frame.f_code.co_name
            if name in {'validate_received_report','validate_report','_saved_support_facts'} and receiver is not None:
                seen.append({'method':name,'type':type(receiver).__module__+'.'+type(receiver).__qualname__,
                    'binding_path':getattr(receiver,'binding_path',None),'context_role':getattr(frame.f_locals.get('context'),'role',None)})
        previous=sys.getprofile();sys.setprofile(profile)
        try:
            own('runtime').Workflow.validate_report(workflow,form,plain(context.scope),schema=schema,context=context)
        finally:sys.setprofile(previous)
        visited={item['binding_path'] for item in seen if item['method']=='validate_received_report' and item['binding_path'] is not None}
        required={binding.binding_path for binding in active if callable(getattr(binding,'validate_received_report',None))}
        assert required<=visited
        if os.environ.get('A104_API_OWNER_PHASE')=='connected' and role=='launch_api':
            assert any(item['method']=='_saved_support_facts' and item['type']==PREFIX+'library.appservice_record_access.AppServiceRecordAccess' for item in seen)
        assert rows(store)==before and driver.client.calls==http
        with pytest.raises(ValueError,match='^appservice_received_support_refs_conflict$'):
            own('runtime').Workflow.validate_report(workflow,{'support':[]},plain(context.scope),schema=schema,context=context)
        assert rows(store)==before and driver.client.calls==http
        own('runtime').Workflow.validate_report(workflow,form,plain(context.scope),schema=schema,context=context)
        assert rows(store)==before and driver.client.calls==http
        record_property('actual_registry_support',json.dumps({'role':role,'registered':[binding.binding_path for binding in bindings],
            'selected':[binding.binding_path for binding in active],'context':context.as_record(),'schema':schema,'form':form,
            'validation_calls':seen,'rows_unchanged':True,'external_calls_unchanged':True,
            'saved_fixture_not_new_scientific_commission':True},sort_keys=True))
