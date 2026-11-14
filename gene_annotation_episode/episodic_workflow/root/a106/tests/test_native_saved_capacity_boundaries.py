"""Controlled saved resource identities at real native entry points, no dispatch.

Fixtures are newly constructed original-shaped rows, not historical executions.
The canonical workflow checker still authenticates the actual enclosing launcher.
"""
from importlib import import_module
import json
from pathlib import Path
import sqlite3
import pytest
from .test_native_cpu_quota_policy import prepared, PACKAGE


def rows(path):
    with sqlite3.connect(path) as db:
        return (db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0],
                db.execute('SELECT * FROM reservations ORDER BY unit').fetchall())


def saved_binding(native,handle,version):
    body=handle.read();definition=body['metadata']['local_resources']
    definition['version']=version;definition['limits'].update(max_running_jobs=1,cpu_threads=1)
    path=Path(definition['directory'])/'capacity.sqlite3';raw=json.dumps(definition,sort_keys=True)
    with sqlite3.connect(path) as db:db.execute('UPDATE configuration SET value=? WHERE id=1',(raw,))
    body['metadata']['local_resources']=definition;native.atomic_json(handle.path,body)
    return path,definition,raw


@pytest.mark.parametrize('version',['shared_local_resources_v1','shared_local_resources_v2'])
@pytest.mark.parametrize('stage',['prepared','released'])
def test_native_entries_preserve_valid_saved_count_metadata_without_count_gate(prepared,monkeypatch,version,stage):
    native,handle,command=prepared;path,definition,raw=saved_binding(native,handle,version)
    body=handle.read()
    if stage=='released':
        owner=import_module(PACKAGE+'.local_resources').LocalResources.reopen(definition)
        policy=import_module(PACKAGE+'.local_jobs').LocalJobPolicy(**body['metadata']['policy'])
        body['capacity_reservation']=owner.reserve(handle,cpu_threads=4,policy=policy)
    body['stage']=stage;native.atomic_json(handle.path,body)
    request=Path(body['paths']['request']).read_bytes();before=handle.path.read_bytes();before_rows=rows(path)
    events=[];monkeypatch.setattr(native,'_ensure_event_registration',lambda *a:events.append(a))
    dispatched=[]
    def observed_dispatch(selected,ready,**kwargs):
        assert ready['metadata']['local_resources']==definition and ready['metadata']['cpu_threads']==4
        assert ready['capacity_reservation']['allocation']['cpu_threads']==4
        dispatched.append(ready);return selected
    monkeypatch.setattr(native,'_dispatch_prepared',observed_dispatch)
    if stage=='released':
        Path(body['paths']['release']).touch()
        assert native.resume_start(handle) is handle
        assert not dispatched and rows(path)==before_rows and handle.path.read_bytes()==before
    else:
        assert native.start_prepared(handle) is handle
        assert len(dispatched)==1
        owner=import_module(PACKAGE+'.local_resources').LocalResources.reopen(definition)
        owner.validate_reservation(dispatched[0]['capacity_reservation'])
        owner.release_reservation(dispatched[0]['capacity_reservation'])
        assert rows(path)==before_rows
    assert events and rows(path)[0]==raw
    assert handle.read()['command']==command and Path(body['paths']['request']).read_bytes()==request


@pytest.mark.parametrize('stage',['prepared','released'])
def test_mismatched_saved_resource_identity_rejects_before_registration_or_early_return(prepared,monkeypatch,stage):
    native,handle,_=prepared;path,definition,_=saved_binding(native,handle,'shared_local_resources_v1')
    body=handle.read();body['stage']=stage;body['metadata']['local_resources']={**definition,'resource_id':'wrong-resource-owner'}
    native.atomic_json(handle.path,body)
    if stage=='released':Path(body['paths']['release']).touch()
    before=handle.path.read_bytes();before_rows=rows(path);request=Path(body['paths']['request']).read_bytes();called=[]
    monkeypatch.setattr(native,'_ensure_event_registration',lambda *a:called.append('event'))
    monkeypatch.setattr(native,'_dispatch_prepared',lambda *a,**k:called.append('dispatch'))
    entry=native.start_prepared if stage=='prepared' else native.resume_start
    with pytest.raises(ValueError,match='^local_resource_binding_conflict$'):entry(handle)
    assert not called and handle.path.read_bytes()==before and rows(path)==before_rows
    assert Path(body['paths']['request']).read_bytes()==request


@pytest.mark.parametrize('legacy',[False,True])
@pytest.mark.parametrize('cpu_max',['0 0','100000 0'])
def test_resume_refuses_nonpositive_cpu_period_without_release(prepared,tmp_path,monkeypatch,legacy,cpu_max):
    native,handle,_=prepared
    from gene_annotation_episode import workflow_budget
    actual=workflow_budget.active_budget();assert actual['environment_bounds']['cpu_percent']==100
    body=handle.read();body['stage']='submitting'
    if legacy:body['metadata'].pop('cpu_quota_percent',None)
    native.atomic_json(handle.path,body);before=handle.path.read_bytes()
    Path(body['paths']['ready']).write_text(json.dumps({'request_sha256':body['request_sha256']}))
    root=tmp_path/'controlled-cgroups';group=root/'child';group.mkdir(parents=True)
    memory=body['metadata']['policy']['memory_bytes']
    (group/'cpu.max').write_text(cpu_max+'\n');(group/'memory.max').write_text(str(memory));(group/'memory.swap.max').write_text('0')
    props={'ControlGroup':'/child','Slice':workflow_budget.SLICE,'BindsTo':workflow_budget.UNIT,
        'MemoryMax':str(memory),'MemorySwapMax':'0','KillMode':'control-group','OOMPolicy':'kill'}
    monkeypatch.setattr(native,'_properties',lambda unit:props)
    monkeypatch.setattr(native,'Path',lambda *parts:root if parts==('/sys/fs/cgroup',) else Path(*parts))
    with pytest.raises(native.AcquisitionError) as caught:native.resume_start(handle)
    assert caught.value.operational['reason']=='cgroup_limits_not_verified'
    assert handle.path.read_bytes()==before and not Path(body['paths']['release']).exists()
