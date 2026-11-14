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

def test_native_types_keep_original_members_and_genuine_external_type_identity():
    recording=importlib.import_module(ROOT+'.execution_recording');events=importlib.import_module(ROOT+'.native_events')
    for module,fixture,names in ((events,'native_events',('NativeEventDisposition','NativeEventBinding','NativeEventProvider')),
                                (recording,'execution_recording',('NativeStatistics','NativeMeasurement'))):
        actual=ast.parse(Path(module.__file__).read_bytes());old=original(fixture)
        for name in names:
            before=next(n for n in old.body if isinstance(n,ast.ClassDef) and n.name==name)
            after=next(n for n in actual.body if isinstance(n,ast.ClassDef) and n.name==name)
            assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
    actual=ast.parse(Path(recording.__file__).read_bytes())
    cls=deepcopy(next(n for n in actual.body if isinstance(n,ast.ClassDef) and n.name=='HomologyStatistics'))
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='execution_class_for_query')
    imports=[n for n in ast.walk(method) if isinstance(n,ast.ImportFrom)]
    assert [(n.module,n.level) for n in imports]==[(ROOT+'.library.homology_job_inputs',0),('gene_annotation_episode.native_lifecycle',0)]
    imports[0].module='homology_jobs';imports[0].level=1
    imports[1].module='native_lifecycle';imports[1].level=1
    guard=next(n for n in method.body if isinstance(n,ast.If) and ast.unparse(n.test)=='type(cpu) is not int or cpu < 1')
    guard.test=ast.parse("type(cpu) is not int or not 1 <= cpu <= configuration['max_cpu']",mode='eval').body
    before=next(n for n in original('execution_recording').body if isinstance(n,ast.ClassDef) and n.name=='HomologyStatistics')
    assert ast.dump(before,include_attributes=False)==ast.dump(cls,include_attributes=False)
    statistics=importlib.import_module('gene_annotation_episode.run_statistics')
    durable=importlib.import_module(ROOT+'.method_loop.durable')
    assert recording.ExecutionClass is statistics.ExecutionClass and recording.RunStatistic is statistics.RunStatistic
    assert events.DurableExecutionStore is durable.DurableExecutionStore and events.DurableExecutionError is durable.DurableExecutionError

@pytest.mark.parametrize('home,name',CASES)
@pytest.mark.parametrize('kind',('real','wrong_object','foreign_subclass'))
def test_genuine_statistics_type_and_original_constructor_rejection(home,name,kind,tmp_path):
    recording=importlib.import_module(ROOT+'.execution_recording')
    class ForeignStatistics(recording.HomologyStatistics):pass
    statistics=(recording.HomologyStatistics if kind=='real' else ForeignStatistics)(tmp_path/'history.sqlite3','cpu_original',10,100) if kind!='wrong_object' else object()
    jobs,keywords=resources(tmp_path);keywords['statistics']=statistics
    original_self=SimpleNamespace()
    expected=capture(lambda:original_initializer()(original_self,jobs,**keywords))
    observed=capture(lambda:actual_class(home,name)(jobs,**keywords))
    if kind!='real':
        assert observed==expected==('raised',TypeError,'typed_homology_statistics_binding_required')
        return
    assert expected==('returned',None)
    binding=observed[1]
    assert binding.statistics is original_self.statistics is statistics
    assert binding.jobs is jobs and binding.parser_policy is keywords['parser_policy']
    configuration=deepcopy(jobs.config)
    record=binding.as_record()
    assert record['statistics']==statistics.as_record()
    assert record['registry_configuration']==configuration==jobs.config
    if home=='library':
        assert all(row['statistics']==statistics.as_record() for group in ('private_implementations','standalone_improvement_implementations') for row in record[group].values())
    else:
        assert len(record['implementation_sha256'])==64

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

@pytest.mark.parametrize('cpu',(1,2,0,True,'2'))
def test_configured_cpu_is_metadata_and_existing_positive_integer_rule_is_preserved(cpu,tmp_path):
    recording=importlib.import_module(ROOT+'.execution_recording')
    statistics=recording.HomologyStatistics(tmp_path/'history.sqlite3','cpu_original',10,100)
    jobs,_=resources(tmp_path)
    node=member(original('execution_recording'),'HomologyStatistics','execution_class_for_query')
    imports=[n for n in ast.walk(node) if isinstance(n,ast.ImportFrom)]
    assert [(n.module,n.level) for n in imports]==[('homology_jobs',1),('native_lifecycle',1)]
    imports[0].module=ROOT+'.library.homology_job_inputs';imports[0].level=0
    imports[1].module='gene_annotation_episode.native_lifecycle';imports[1].level=0
    baseline=compiled(node,dict(vars(recording)))
    before=capture(lambda:baseline(statistics,jobs,query_fasta='>query\nACDEFG\n',cpu=cpu))
    after=capture(lambda:statistics.execution_class_for_query(jobs,query_fasta='>query\nACDEFG\n',cpu=cpu))
    if cpu==2 and type(cpu) is int:
        assert before==('raised',ValueError,'cpu_outside_caller_allocation')
        assert after[0]=='returned' and after[1].cpu_threads==2
        assert jobs.config['max_cpu']==1
    elif type(cpu) is int and cpu==1:
        assert before==after and after[1].cpu_threads==1
    else:
        assert before==after==('raised',ValueError,'cpu_outside_caller_allocation')
    # A proposed ExecutionClass is metadata only: no registry, subprocess,
    # service, cgroup or verified execution receipt is created by this call.

@pytest.mark.parametrize('scenario',('succeeded','failed_exit','missing_receipt','oom','resource_failure','unmeasured','negative'))
def test_original_native_receipt_outcome_and_unavailable_duration_are_preserved(scenario):
    recording=importlib.import_module(ROOT+'.execution_recording')
    original_node=next(n for n in original('execution_recording').body if isinstance(n,ast.FunctionDef) and n.name=='_measurement')
    baseline=compiled(original_node,{})
    body={'boot_id':'original_boot','started_monotonic_ns':100}
    end={'SERVICE_RESULT':'success','ended':{'boot_id':'original_boot','monotonic_ns':500}}
    receipt={'execution_failure':None,'native_returncode':0,'resource_failure':None}
    if scenario=='failed_exit':receipt['native_returncode']=3
    elif scenario=='missing_receipt':receipt=None
    elif scenario=='oom':end['SERVICE_RESULT']='oom-kill'
    elif scenario=='resource_failure':receipt['resource_failure']='controlled_memory_failure'
    elif scenario=='unmeasured':end['ended']['boot_id']='other_boot'
    elif scenario=='negative':end['ended']['monotonic_ns']=50
    before=capture(lambda:baseline(deepcopy(body),deepcopy(end),deepcopy(receipt)))
    after=capture(lambda:recording._measurement(deepcopy(body),deepcopy(end),deepcopy(receipt)))
    assert before==after
    if scenario in {'failed_exit','missing_receipt'}:assert after[1][0]=='failed'
    if scenario in {'oom','resource_failure'}:assert after[1][0]=='resource_limit'
    if scenario=='unmeasured':assert after[1][1:]==('unmeasured',None)
    if scenario=='negative':assert after==('raised',ValueError,'negative_native_receipt_duration')

