"""Saved identity/default reconstruction controls; inert counts never admit work.

Real SQLite and the actual tool factory execute. Only unlaunched service discovery
and unused PublicClients construction are controlled; no native/provider runs.
"""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
import pytest
from .test_no_count_resource_admission import resources
PACKAGE=__package__.rsplit('.tests',1)[0]
def module(name):return import_module(PACKAGE+'.'+name)
def rows(local):
    with local._transaction() as db:
        return (db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0],
                [tuple(row) for row in db.execute('SELECT * FROM reservations ORDER BY unit')])
def saved(resources,version):
    local,handle=resources;definition=local.as_record();definition['version']=version
    definition['limits'].update(max_running_jobs=1,cpu_threads=1)
    raw=json.dumps(definition,sort_keys=True)
    with local._transaction() as db:db.execute('UPDATE configuration SET value=? WHERE id=1',(raw,))
    return definition,raw,handle

def test_current_definition_has_byte_limits_and_reopens_exactly(resources):
    local,handle=resources;definition=local.as_record()
    assert definition['version']=='shared_local_resources_v2'
    assert set(definition['limits'])=={'memory_bytes','scratch_bytes'}
    reservation=local.reserve(handle(),cpu_threads=4,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    before=rows(local);restored=module('local_resources').LocalResources.reopen(definition)
    assert restored.as_record()==definition and rows(restored)==before
    restored.validate_reservation(reservation)
    assert reservation['allocation']['cpu_threads']==4

@pytest.mark.parametrize('version',['shared_local_resources_v1','shared_local_resources_v2'])
def test_saved_identity_and_reservations_reopen_with_inert_counts(resources,version):
    definition,raw,handle=saved(resources,version);cls=module('local_resources').LocalResources
    local=cls.reopen(definition);assert rows(local)[0]==raw
    first=local.reserve(handle(),cpu_threads=4,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    second=local.reserve(handle(),cpu_threads=8,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    before=rows(local);restored=cls(local.directory,dict(definition['limits']))
    assert restored.as_record()==definition and rows(restored)==before
    restored.validate_reservation(first);restored.validate_reservation(second)
    assert first['allocation']['cpu_threads']==4 and second['allocation']['cpu_threads']==8
    assert set(restored.snapshot()['limits'])==set(restored.snapshot()['available'])=={'memory_bytes','scratch_bytes'}
    restored.release_reservation(first);restored.validate_reservation(second)
    assert rows(restored)[0]==raw

@pytest.mark.parametrize('version',['shared_local_resources_v1','shared_local_resources_v2'])
def test_actual_factory_preserves_saved_settings_and_database(resources,tmp_path,monkeypatch,version):
    definition,raw,_=saved(resources,version);local,_=resources;before=rows(local)
    config={'local_resources':dict(definition['limits']),'public':{'ncbi_email':None,'provider_access_dir':str(tmp_path/'access')}};original=deepcopy(config)
    monkeypatch.setenv(module('local_resources').DIRECTORY_ENV,str(local.directory))
    tools=module('tool_configuration');monkeypatch.setattr(tools,'PublicClients',lambda **kwargs:SimpleNamespace())
    with module('state').Store(tmp_path/'state') as store:
        registry=tools.build_tools(store,config)
        assert registry.resource_binding()['local_resources']==definition
    assert config==original and rows(local)==before and rows(local)[0]==raw

@pytest.mark.parametrize('version',['shared_local_resources_v1','shared_local_resources_v2'])
def test_missing_database_recreates_only_the_exact_default_identity(tmp_path,version):
    lr=module('local_resources');directory=tmp_path/'missing'
    definition={'version':version,'resource_id':lr._resource_id(),'directory':str(directory.resolve()),'limits':lr._limits({})}
    if version=='shared_local_resources_v1':definition['limits'].update(max_running_jobs=1,cpu_threads=1)
    original=deepcopy(definition);assert not directory.exists()
    restored=lr.LocalResources.reopen(definition)
    assert restored.as_record()==definition==original
    assert json.loads(rows(restored)[0])==definition and rows(restored)[1]==[]
    assert lr.LocalResources.reopen(definition).as_record()==definition

@pytest.mark.parametrize('version,field',[
    ('shared_local_resources_v1','memory_bytes'),('shared_local_resources_v2','memory_bytes'),
    ('shared_local_resources_v1','max_running_jobs'),('shared_local_resources_v1','cpu_threads')])
def test_missing_custom_descriptor_is_not_used_to_seed_a_database(tmp_path,version,field):
    lr=module('local_resources');directory=tmp_path/'missing-custom'
    defaults={'version':'shared_local_resources_v2','resource_id':lr._resource_id(),'directory':str(directory.resolve()),'limits':lr._limits({})}
    definition=deepcopy(defaults);definition['version']=version
    if version=='shared_local_resources_v1':definition['limits'].update(max_running_jobs=1,cpu_threads=1)
    definition['limits'][field]+=1;original=deepcopy(definition)
    with pytest.raises(ValueError,match='local_resource_binding_conflict'):lr.LocalResources.reopen(definition)
    assert definition==original
    # This is the original constructor-before-equality behavior, not migration.
    actual=lr.LocalResources(directory)
    expected={**defaults,'version':'shared_local_resources_v1','limits':{**defaults['limits'],'max_running_jobs':1,'cpu_threads':1}}
    assert actual.as_record()==expected and json.loads(rows(actual)[0])==expected and rows(actual)[1]==[]

@pytest.mark.parametrize('field',['max_running_jobs','cpu_threads','job_slots'])
def test_new_custom_count_initialization_is_still_rejected(tmp_path,field):
    lr=module('local_resources');config={field:1};original=dict(config)
    with pytest.raises(ValueError,match='invalid_local_resource_settings'):
        lr.LocalResources(tmp_path/'new',config)
    assert config==original

@pytest.mark.parametrize('field',['max_running_jobs','cpu_threads','memory_bytes'])
def test_changed_saved_settings_are_rejected_without_rewriting_rows(resources,field):
    definition,_,_=saved(resources,'shared_local_resources_v1');local,_=resources;before=rows(local)
    requested=dict(definition['limits']);requested[field]+=1
    with pytest.raises(ValueError,match='local_resource_limits_conflict'):
        module('local_resources').LocalResources(local.directory,requested)
    assert rows(local)==before

@pytest.mark.parametrize('field,value',[('max_running_jobs',True),('max_running_jobs',0),('cpu_threads',True),('cpu_threads',0)])
def test_malformed_saved_metadata_is_not_admitted_or_rewritten(resources,field,value):
    definition,_,_=saved(resources,'shared_local_resources_v1');local,_=resources;definition['limits'][field]=value
    with local._transaction() as db:db.execute('UPDATE configuration SET value=? WHERE id=1',(json.dumps(definition,sort_keys=True),))
    before=rows(local)
    with pytest.raises(ValueError,match='invalid_local_resource_limits'):
        module('local_resources').LocalResources.reopen(definition)
    assert rows(local)==before

@pytest.mark.parametrize('case',[
    'wrong_version','missing_version','missing_limits','missing_max_running_jobs',
    'missing_cpu_threads','extra_field','extra_limit','null_limits','list_limits',
    'boolean_count','negative_memory','wrong_resource_id'])
def test_rejected_missing_descriptor_preserves_original_initialization(tmp_path,case):
    lr=module('local_resources');directory=tmp_path/'rejected-original-default'
    original_default={'version':'shared_local_resources_v1','resource_id':lr._resource_id(),
        'directory':str(directory.resolve()),'limits':{'max_running_jobs':1,'cpu_threads':1,
            'memory_bytes':21474836480,'scratch_bytes':4294967296}}
    definition=deepcopy(original_default)
    if case=='wrong_version':definition['version']='unknown_saved_version'
    elif case=='missing_version':definition.pop('version')
    elif case=='missing_limits':definition.pop('limits')
    elif case=='missing_max_running_jobs':definition['limits'].pop('max_running_jobs')
    elif case=='missing_cpu_threads':definition['limits'].pop('cpu_threads')
    elif case=='extra_field':definition['unexpected']='retained-only-fixture'
    elif case=='extra_limit':definition['limits']['unexpected']=1
    elif case=='null_limits':definition['limits']=None
    elif case=='list_limits':definition['limits']=[]
    elif case=='boolean_count':definition['limits']['cpu_threads']=False
    elif case=='negative_memory':definition['limits']['memory_bytes']=-1
    elif case=='wrong_resource_id':definition['resource_id']='different-original-machine'
    else:raise AssertionError(case)
    supplied=deepcopy(definition);assert not directory.exists()
    with pytest.raises(ValueError,match='local_resource_binding_conflict'):
        lr.LocalResources.reopen(definition)
    assert definition==supplied
    restored=lr.LocalResources(directory)
    raw,reservations=rows(restored)
    assert restored.as_record()==original_default
    assert raw==json.dumps(original_default,sort_keys=True) and reservations==[]
    before=rows(restored)
    with pytest.raises(ValueError,match='local_resource_binding_conflict'):
        lr.LocalResources.reopen(definition)
    assert rows(restored)==before and definition==supplied
