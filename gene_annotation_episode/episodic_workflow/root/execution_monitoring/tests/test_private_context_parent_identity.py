"""Real private task constructors retain exact Episode identity and binding type.

The controlled registry deliberately resolves one explicit parent owner. Main's
full context-parent registry composition is a separate integration obligation.
"""
from __future__ import annotations
import importlib
from types import SimpleNamespace
import pytest
ROOT='gene_annotation_episode.episodic_workflow.root'
MONITORS=tuple(prefix+home for prefix in ('','scientific_process/')
    for home in ('execution_monitoring','hpc_coordination/execution_monitoring',
                 'hpc_coordination/hpc_allocation_execution/execution_monitoring'))
HOMOLOGY=(('homology_job_submission','HomologySubmission','job_launch'),
          ('homology_job_monitoring','HomologyMonitoring','job_monitor'),
          ('homology_result_acquisition','HomologyAcquisition','job_results'))


def request():
    return SimpleNamespace(message=SimpleNamespace(as_record=lambda:{'initial_report':{'qualified':False}}),report_contract=None)


def workflow(role,path,binding):
    core=importlib.import_module(ROOT+'.method_loop.episode')
    grain=core.Grain(role,'Controlled original work.','Controlled original result.',lambda request:None)
    return SimpleNamespace(context=SimpleNamespace(require_run_id=lambda:'run:original'),grains={role:grain},
        root_role=path[0][0],episode_bindings=SimpleNamespace(roles=()),specialist=lambda source:binding)


def expected_identity(wf,path):
    return importlib.import_module(ROOT+'.method_loop.episode').Episode.identity(
        wf.context,wf.grains[path[-1][0]],path[-1][1],parent_path=path[:-1]).episode_id


def monitor_path(home,recursive):
    names=home.split('/')
    roles={'scientific_process':'scientific_process',
           'hpc_coordination':'hpc','hpc_allocation_execution':'hpc_execution',
           'execution_monitoring':'monitor'}
    parts=[('annotation','root')]
    parts.extend((roles[name],'owner_'+str(index)) for index,name in enumerate(names))
    if recursive:parts.append(('monitor','recursive'))
    return tuple(parts)


@pytest.mark.parametrize('home',MONITORS)
@pytest.mark.parametrize('recursive',(False,True))
def test_monitor_private_task_uses_exact_context_parent_and_recursive_identity(home,recursive):
    module=ROOT+'.'+home.replace('/','.')
    binding=importlib.import_module(module+'.episode').MonitorEpisodes(SimpleNamespace())
    task=importlib.import_module(module+'.task').MonitorTask
    path=monitor_path(home,recursive);wf=workflow('monitor',path,binding)
    source=task(wf,path,request(),{'subject_refs':[]})
    assert source.path==path and source.episode_id==expected_identity(wf,path)
    assert source.report_values=={'qualified':False} and source.report_basis==[]
    assert source.workflow.specialist(source) is binding
    other=next(value for value in MONITORS if value!=home)
    foreign=importlib.import_module(ROOT+'.'+other.replace('/','.')+'.episode').MonitorEpisodes(SimpleNamespace())
    wf.specialist=lambda source:foreign
    with pytest.raises(ValueError,match='fixed_execution_task_binding_required'):
        task(wf,path,request(),{'subject_refs':[]})


def family():
    cls=importlib.import_module(ROOT+'.library.homology_episode_family').HomologyEpisodes
    jobs=object.__new__(importlib.import_module(ROOT+'.homology_jobs').HomologyJobs)
    policy=importlib.import_module('gene_annotation_episode.local_jobs').LocalJobPolicy(1024,2048)
    return cls(jobs,parser_policy=policy,credit_projector=lambda *a,**kw:0,
        credit_binding={'version':'controlled'},monitoring_projector=lambda *a,**kw:0,
        monitoring_binding={'version':'controlled'})


@pytest.mark.parametrize('home,stem,role',HOMOLOGY)
@pytest.mark.parametrize('parents',(('annotation',),))
def test_homology_private_task_preserves_annotation_lineage_identity(home,stem,role,parents):
    module=ROOT+'.'+home.replace('/','.')
    cls=getattr(importlib.import_module(module+'.task'),stem+'Task')
    path=tuple((name,'parent_'+str(index)) for index,name in enumerate(parents))+((role,'original_child'),)
    wf=workflow(role,path,None);wf.job_episodes=family()
    source=cls(wf,path,request(),{'subject_refs':[]})
    assert source.path==path and source.episode_id==expected_identity(wf,path)
    assert source.report_values=={'qualified':False}
    assert wf.job_episodes.implementation_for_path(source.path).decision_source_type is cls
