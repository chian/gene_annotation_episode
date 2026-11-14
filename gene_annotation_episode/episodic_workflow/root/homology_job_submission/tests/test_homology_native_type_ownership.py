"""Controlled native type/configuration boundaries; no physical work or publish.

ExecutionMemory, native lifecycle launch, worker hooks, saved restoration and
scientific validation are deliberately outside these tests' execution scope.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT='gene_annotation_episode.episodic_workflow.root'
HERE=Path(__file__).with_name('fixtures')/'native_type_ownership'
PINS=json.loads((HERE/'manifest.json').read_text())
BASE=(('homology_job_submission','HomologySubmissionEpisodes'),
      ('homology_job_monitoring','HomologyMonitoringEpisodes'),
      ('homology_result_acquisition','HomologyAcquisitionEpisodes'))
CASES=tuple((prefix+home,('Legacy' if prefix else '')+name)
            for prefix in ('','legacy_annotation/') for home,name in BASE)+(('library','HomologyEpisodes'),)

def original(name):
    raw=(HERE/(name+'.py.source')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==PINS[name]
    return ast.parse(raw)

def member(tree,cls,name):
    owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    return deepcopy(next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name==name))

def compiled(node,namespace):
    module=ast.Module(body=ast.parse('from __future__ import annotations').body+[deepcopy(node)],type_ignores=[])
    local=dict(namespace)
    exec(compile(ast.fix_missing_locations(module),'<authenticated-original-method>','exec'),local)
    return local[node.name]

def capture(callback):
    try:return ('returned',callback())
    except Exception as error:return ('raised',type(error),str(error))

def actual_class(home,name):
    module=ROOT+'.library.homology_episode_family' if home=='library' else ROOT+'.'+home.replace('/','.')+'.episode'
    return getattr(importlib.import_module(module),name)

def resources(tmp_path):
    jobs=object.__new__(importlib.import_module(ROOT+'.homology_jobs').HomologyJobs)
    jobs.directory=tmp_path/'unlaunched_registry'
    jobs.config={'registry_ref':'registry_original','max_cpu':1,
        'executable':{'sha256':'a'*64},'reference_database':{'sha256':'b'*64},
        'job_limits':{'memory_bytes':1024,'scratch_bytes':2048}}
    policy=importlib.import_module('gene_annotation_episode.local_jobs').LocalJobPolicy(1024,2048)
    def operational(*args,**kwargs):return {'credit':2.0}
    def monitoring(*args,**kwargs):return 3.0
    keywords={'parser_policy':policy,'credit_projector':operational,
        'credit_binding':{'version':'original_operational'},'monitoring_projector':monitoring,
        'monitoring_binding':{'version':'original_monitoring'}}
    return jobs,keywords

def original_initializer():
    node=member(original('homology_episodes'),'HomologyEpisodes','__init__')
    matches=[n for n in ast.walk(node) if isinstance(n,ast.ImportFrom) and n.level==1 and n.module=='execution_recording']
    assert len(matches)==1 and [a.name for a in matches[0].names]==['HomologyStatistics']
    old=deepcopy(matches[0]);matches[0].level=0;matches[0].module=ROOT+'.execution_recording'
    # Only the defining-owner import is normalized for this typed comparison.
    inverse=deepcopy(node);item=next(n for n in ast.walk(inverse) if isinstance(n,ast.ImportFrom) and n.module==ROOT+'.execution_recording')
    item.module=old.module;item.level=old.level
    assert ast.dump(inverse,include_attributes=False)==ast.dump(member(original('homology_episodes'),'HomologyEpisodes','__init__'),include_attributes=False)
    return compiled(node,{'json':json,'HomologyJobs':importlib.import_module(ROOT+'.homology_jobs').HomologyJobs,
                         'LocalJobPolicy':importlib.import_module('gene_annotation_episode.local_jobs').LocalJobPolicy})



@pytest.mark.parametrize('home,name',CASES)
@pytest.mark.parametrize('kind',('real','wrong_object','foreign_subclass','resource_conflict'))
def test_native_provider_identity_and_host_local_custody(home,name,kind,tmp_path):
    recording=importlib.import_module(ROOT+'.execution_recording');events=importlib.import_module(ROOT+'.native_events')
    class ForeignProvider(events.NativeEventProvider):pass
    factory=ForeignProvider if kind=='foreign_subclass' else events.NativeEventProvider
    provider=object() if kind=='wrong_object' else factory(tmp_path/'events',run_id='original_run',resource_id='other_cpu' if kind=='resource_conflict' else 'cpu_original')
    jobs,keywords=resources(tmp_path);keywords['statistics']=recording.HomologyStatistics(tmp_path/'history.sqlite3','cpu_original',None,None)
    binding=actual_class(home,name)(jobs,**keywords)
    result=capture(lambda:binding.with_native_events(provider))
    if kind in {'wrong_object','foreign_subclass'}:
        assert result==('raised',TypeError,'typed_native_event_provider_required');return
    if kind=='resource_conflict':
        assert result==('raised',ValueError,'native_event_resource_identity_conflict');return
    current=result[1]
    assert current is not binding and current._custody is not binding._custody
    assert binding.native_event_provider is None and current.native_event_provider is provider
    assert current.statistics is binding.statistics and current.jobs is binding.jobs
    if home=='library':
        assert all(child._custody is current._custody and child.native_event_provider is provider
                   for values in (current._implementations,current._standalone_implementations) for child in values.values())
    native=provider.for_job(owner_episode_id='episode_original',job_ref='job_original',registry_ref='registry_original')
    assert type(native) is events.NativeEventBinding
    assert type(events.NativeEventBinding.from_record(native.as_record())) is events.NativeEventBinding
    assert provider.for_job(owner_episode_id='other_episode',job_ref='job_original',registry_ref='registry_original',original_binding=native) is native

    # A proposed ExecutionClass is metadata only: no registry, subprocess,
    # service, cgroup or verified execution receipt is created by this call.


