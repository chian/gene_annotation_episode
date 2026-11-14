"""Desired resource admission preserves byte bounds, without job/thread ceilings.

The native checker uses the actual existing launcher owner. Service discovery is
controlled for the SQLite reservation tests; no service, worker or provider is
launched. Thread counts are request metadata, never a CPU-quota substitute.
"""
from importlib import import_module
import json
from types import SimpleNamespace
import pytest
from .test_canonical_workflow_resources import PACKAGE,selected_checker


def test_native_request_with_multiple_threads_retains_one_cpu_whole_window(tmp_path):
    checker=selected_checker();actual=checker.active_budget()
    admitted=checker.native_budget(SimpleNamespace(memory_bytes=1024),4,tmp_path)
    assert admitted==actual
    assert admitted['environment_bounds']=={'cpu_percent':100,'memory_bytes':5*1024**3,'swap_bytes':0}


@pytest.fixture
def resources(tmp_path,monkeypatch):
    native=import_module(PACKAGE+'.native_lifecycle')
    monkeypatch.setattr(native,'_control',lambda *args:SimpleNamespace(returncode=0,stdout=''))
    monkeypatch.setattr(native,'_properties',lambda unit:{'LoadState':'not-found'})
    local=import_module(PACKAGE+'.local_resources').LocalResources(tmp_path/'capacity',
        {'memory_bytes':512,'scratch_bytes':512})
    counter=[]
    def handle():
        index=len(counter);path=tmp_path/('prepared-'+str(index)+'.json')
        body={'unit':'original-prepared-'+str(index),'stage':'prepared'}
        path.write_text(json.dumps(body));counter.append(path)
        return SimpleNamespace(path=path,read=lambda:json.loads(path.read_text()))
    return local,handle


def test_multiple_requested_threads_are_retained_without_count_admission_cap(resources):
    local,handle=resources
    reserved=local.reserve(handle(),cpu_threads=4,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    assert reserved['allocation']=={'cpu_threads':4,'memory_bytes':64,'scratch_bytes':64}
    local.validate_reservation(reserved)


def test_multiple_owned_jobs_fit_when_byte_resources_remain(resources):
    local,handle=resources
    first=local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    second=local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    assert first['reservation_ref']!=second['reservation_ref']
    local.validate_reservation(first);local.validate_reservation(second)
    assert len(local.snapshot()['jobs'])==2


def test_current_capacity_does_not_advertise_available_thread_or_job_counts(resources):
    local,_=resources;snapshot=local.snapshot()
    assert 'cpu_threads' not in snapshot['available']
    assert 'job_slots' not in snapshot['available']
    assert snapshot['available']['memory_bytes']==snapshot['available']['scratch_bytes']==512


def test_memory_capacity_and_owned_reservation_identity_still_apply(resources):
    local,handle=resources;error=import_module(PACKAGE+'.acquisition').AcquisitionError
    first=local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=512,scratch_bytes=64))
    with pytest.raises(error) as failure:
        local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=1,scratch_bytes=64))
    assert failure.value.code=='local_resource_busy'
    changed={**first,'resource':{**first['resource'],'directory':'changed-owner'}}
    with pytest.raises(ValueError,match='local_resource_binding_conflict'):local.validate_reservation(changed)
    local.validate_reservation(first)


def test_per_request_memory_bound_still_rejects_oversize(resources):
    local,handle=resources;error=import_module(PACKAGE+'.acquisition').AcquisitionError
    with pytest.raises(error) as failure:
        local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=513,scratch_bytes=64))
    assert failure.value.code=='local_job_resource_limit'
    assert failure.value.operational['resource']=='memory_bytes'
