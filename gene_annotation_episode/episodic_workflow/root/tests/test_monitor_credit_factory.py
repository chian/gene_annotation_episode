"""Real service setup with controlled operational bindings; no job or scientific work."""
import importlib
from types import SimpleNamespace
import pytest
from .axis_roles import HEAD

@pytest.mark.parametrize('axis_name',['a102','a103','a104','a106','a107','a110'])
def test_execution_factory_uses_the_private_monitor_credit_selection(axis_name,monkeypatch,tmp_path):
    axis='gene_annotation_episode.episodic_workflow.root.'+axis_name
    module=importlib.import_module(axis+'.execution_service_setup')
    monitor_module=importlib.import_module(axis+'.'+HEAD[axis_name]+'.execution_progress_assessment.episode')
    calls=[]
    class Monitor(monitor_module.MonitorEpisode):
        def information_credit(self,reader,*,information_unit):
            calls.append((reader,information_unit))
            return super().information_credit(reader,information_unit=information_unit)
    monkeypatch.setattr(monitor_module,'MonitorEpisode',Monitor)
    if hasattr(module,'MonitorEpisode'):monkeypatch.setattr(module,'MonitorEpisode',Monitor)
    operational=SimpleNamespace(roles=('launch',),resource_tool_contracts=lambda:[],as_record=lambda:{'binding_id':'controlled'},
        project_credit=lambda *args: {'credit':0},job_progress_provider=object())
    def bindings(*args,**kwargs):return (operational,)
    monkeypatch.setattr(module,'create_execution_bindings',bindings)
    factory=module.ExecutionServiceFactory({'fixture':{'kind':'local'}},{},2.,.125,.375)
    extra={'execution_factory':bindings,'monitor_type':Monitor} if axis_name in {'a103','a107'} else {}
    configured=[]
    registry=SimpleNamespace(
        configure_protein_structure_resources=lambda *args,**kwargs:configured.append(('structure',args,kwargs)),
        configure_flux_balance_resources=lambda *args,**kwargs:configured.append(('flux',args,kwargs)))
    application=factory(object(),run_id='run',directory=tmp_path,tool_registry=registry,**extra)
    assert len(calls)==1 and calls[0][1]==.375
    actual=application.role_credit_bindings['monitor']['project']
    assert actual.information_unit==.375 and actual.progress_provider is calls[0][0]
    assert application.role_credit_bindings['monitor']['definition']==actual.as_record()
    assert application.role_credit_bindings['launch']['project'] is operational.project_credit


@pytest.mark.parametrize('axis_name',['a102','a103'])
def test_other_service_setup_paths_select_monitor_credit(axis_name,monkeypatch,tmp_path):
    axis='gene_annotation_episode.episodic_workflow.root.'+axis_name
    monitor_module=importlib.import_module(axis+'.'+HEAD[axis_name]+'.execution_progress_assessment.episode')
    calls=[]
    class Monitor(monitor_module.MonitorEpisode):
        def information_credit(self,reader,*,information_unit):
            calls.append((reader,information_unit))
            return super().information_credit(reader,information_unit=information_unit)
    monkeypatch.setattr(monitor_module,'MonitorEpisode',Monitor)
    scientific=importlib.import_module(axis+'.'+HEAD[axis_name]+'_setup')
    literature=importlib.import_module(axis+'.'+HEAD[axis_name]+'.published_evidence_assessment.episode')
    monkeypatch.setattr(scientific,'prepare_scientific_binding',lambda **kwargs:{'binding_id':'controlled_science'})
    monkeypatch.setattr(literature,'create_binding_tree',lambda *args,**kwargs:())
    if axis_name=='a103':
        module=importlib.import_module(axis+'.assembled_service_setup')
        monkeypatch.setattr(module,'MonitorEpisode',Monitor)
        monkeypatch.setattr(module,'create_binding_tree',lambda *args,**kwargs:())
        monkeypatch.setattr(module,'prepare_scientific_binding',lambda **kwargs:{'binding_id':'controlled_science'})
        monkeypatch.setattr(module,'bind_resource_services',lambda *args,**kwargs:SimpleNamespace(episode_binding_descriptors=(),role_credit_bindings={}))
        monkeypatch.setattr(module,'HomologyProgressProvider',lambda *args,**kwargs:object())
        application=module.bind_assembled_services(object(),run_id='run',directory=tmp_path,
            job_episodes=SimpleNamespace(jobs=object()),resource_estimator=object(),source_directory=tmp_path,
            tool_catalog={},tool_retrieval={},scientific_child_roles=('monitor',),handoff_unit=2,
            acquired_record_unit=.125,monitoring_information_unit=.375,literature_outcome_page_size=7,
            monitor_outcome_page_size=9,log_window_bytes=123,log_roles=('stdout',))
        unit=.375
    else:
        module=importlib.import_module(axis+'.a102_investigation')
        resources=importlib.import_module(axis+'.a102_resources')
        monkeypatch.setattr(resources,'A102ResourceAdapter',lambda *args:SimpleNamespace(catalog=lambda *args:()))
        monkeypatch.setattr(resources,'A102ResourceCredit',lambda *args:SimpleNamespace(as_record=lambda:{}))
        monkeypatch.setattr(resources,'A102ProgressProvider',lambda *args:object())
        operational=SimpleNamespace(roles=('launch',),as_record=lambda:{'binding_id':'controlled_resource'})
        monkeypatch.setattr(module,'create_resource_bindings',lambda *args,**kwargs:(operational,))
        application=module.A102ServiceFactory(str(tmp_path),{})(object(),run_id='run',directory=tmp_path,
            tool_catalog={},tool_registry=object())
        unit=1
    assert len(calls)==1 and calls[0][1]==unit
    project=application.role_credit_bindings['monitor']['project']
    assert project.information_unit==unit and project.progress_provider is calls[0][0]
    assert application.role_credit_bindings['monitor']['definition']==project.as_record()
