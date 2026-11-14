"""Byte-resource recommendations do not reintroduce job/thread count gates."""
from importlib import import_module
import pytest
PACKAGE=__package__.rsplit('.tests',1)[0]
@pytest.mark.parametrize('thread_request',[1,4,128])
def test_count_fields_do_not_change_local_route_recommendation(thread_request):
    route={'binding_available':True,'capacity_state':'fresh','available':{'memory_bytes':512,'scratch_bytes':512,'cpu_threads':0,'job_slots':0},'total_seconds_upper':12,'provenance':['synthetic-capacity-control']}
    result=import_module(PACKAGE+'.execution_guidance').compare_routes(route,None,requirements={'memory_bytes':64,'scratch_bytes':64,'cpu_threads':thread_request})
    assert result['preferred']=='local' and result['routes']['local']['eligible']
    assert not result['admission_reserved'] and result['routes']['local']['total_seconds_upper']==12
@pytest.mark.parametrize('field',['memory_bytes','scratch_bytes'])
def test_byte_requirement_and_unknown_capacity_still_prevent_recommendation(field):
    route={'binding_available':True,'capacity_state':'fresh','available':{'memory_bytes':512,'scratch_bytes':512}}
    result=import_module(PACKAGE+'.execution_guidance').compare_routes(route,None,requirements={field:513})
    assert result['preferred'] is None and result['routes']['local']['reasons']==['insufficient_or_unknown_'+field]
    route['capacity_state']='unknown'
    result=import_module(PACKAGE+'.execution_guidance').compare_routes(route,None,requirements={})
    assert result['preferred'] is None and result['routes']['local']['reasons']==['refresh_capacity']

from types import SimpleNamespace
from .test_no_count_resource_admission import resources

def test_scratch_admission_still_enforces_per_request_and_remaining_bytes(resources):
    local,handle=resources;error=import_module(PACKAGE+'.acquisition').AcquisitionError
    with pytest.raises(error) as failure:local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=513))
    assert failure.value.code=='local_job_resource_limit' and failure.value.operational['resource']=='scratch_bytes'
    first=local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=512))
    with pytest.raises(error) as failure:local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=1))
    assert failure.value.code=='local_resource_busy';local.validate_reservation(first)

def test_unobserved_service_inventory_still_refuses_admission(resources,monkeypatch):
    local,handle=resources;native=import_module(PACKAGE+'.native_lifecycle');error=import_module(PACKAGE+'.acquisition').AcquisitionError
    monkeypatch.setattr(native,'_control',lambda *args:None)
    with pytest.raises(error) as failure:local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    assert failure.value.code=='local_job_boundary_unavailable' and failure.value.operational['reason']=='local_capacity_unavailable'

@pytest.mark.parametrize('threads',[0,-1,True,1.5])
def test_thread_request_remains_a_positive_integer_metadata_field(resources,threads):
    local,handle=resources
    with pytest.raises(ValueError,match='invalid_local_resource_allocation'):
        local.reserve(handle(),cpu_threads=threads,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
