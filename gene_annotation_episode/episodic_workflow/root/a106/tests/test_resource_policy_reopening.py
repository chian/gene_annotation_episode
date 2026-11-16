"""Controlled saved/default identities survive; counts never admit or stop work.

These are explicit controlled SQLite records, not claimed historical workflows.
New custom count settings remain invalid; exact saved settings are identities.
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


def test_new_definition_has_byte_only_active_settings(resources):
    local,_=resources
    assert local.as_record()['version']=='shared_local_resources_v2'
    assert set(local.as_record()['limits'])=={'memory_bytes','scratch_bytes'}







@pytest.mark.parametrize('field',['max_running_jobs','cpu_threads','job_slots'])
def test_new_custom_count_settings_remain_invalid(resources,field):
    local,_=resources;owner=module('local_resources').LocalResources
    with pytest.raises(ValueError,match='^invalid_local_resource_settings$'):
        owner(local.directory/('new-'+field),{field:1})




@pytest.mark.parametrize('failure',['nonzero_inventory','inventory_oserror'])
def test_unavailable_inventory_keeps_reservations_and_conservative_byte_capacity(resources,monkeypatch,failure):
    local,handle=resources;native=module('native_lifecycle')
    reservation=local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    before=rows(local)
    def unavailable(*args):
        if failure=='inventory_oserror':raise OSError('controlled inventory unavailable')
        return SimpleNamespace(returncode=1,stdout='')
    monkeypatch.setattr(native,'_control',unavailable)
    view=local.snapshot()
    registered,=[x for x in view['jobs'] if x['reservation_ref']==reservation['reservation_ref']]
    unknown,=[x for x in view['jobs'] if x['state']=='capacity_unavailable']
    assert registered['allocation']=={'memory_bytes':64,'scratch_bytes':64}
    assert unknown['allocation']=={'memory_bytes':512,'scratch_bytes':512}
    assert unknown['reservation_ref'] is None and unknown['execution_handle'] is None
    assert view['state']=='unknown' and view['available']=={'memory_bytes':0,'scratch_bytes':0}
    assert view['reserved']=={'memory_bytes':576,'scratch_bytes':576}
    assert rows(local)==before and reservation['allocation']['cpu_threads']==1
    with pytest.raises(module('acquisition').AcquisitionError) as caught:
        local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=1,scratch_bytes=1))
    assert caught.value.code=='local_job_boundary_unavailable' and rows(local)==before
    local.validate_reservation(reservation)


def test_untracked_live_service_keeps_owned_reservation_and_consumes_byte_capacity(resources,monkeypatch):
    local,handle=resources;native=module('native_lifecycle')
    reservation=local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    before=rows(local);unit='gene-local-job-controlled-untracked.service'
    monkeypatch.setattr(native,'_control',lambda *args:SimpleNamespace(returncode=0,stdout=unit+' loaded active running controlled\n'))
    view=local.snapshot()
    registered,=[x for x in view['jobs'] if x['reservation_ref']==reservation['reservation_ref']]
    unknown,=[x for x in view['jobs'] if x['state']=='untracked_running']
    assert registered['allocation']=={'memory_bytes':64,'scratch_bytes':64}
    assert unknown['allocation']=={'memory_bytes':512,'scratch_bytes':512}
    assert unknown['execution_handle']==unit and unknown['reservation_ref'] is None
    assert view['state']=='busy' and view['available']=={'memory_bytes':0,'scratch_bytes':0}
    assert view['reserved']=={'memory_bytes':576,'scratch_bytes':576}
    assert rows(local)==before and reservation['allocation']['cpu_threads']==1
    with pytest.raises(module('acquisition').AcquisitionError) as caught:
        local.reserve(handle(),cpu_threads=1,policy=SimpleNamespace(memory_bytes=1,scratch_bytes=1))
    assert caught.value.code=='local_resource_busy' and rows(local)==before
    local.validate_reservation(reservation)
