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
LEGACY_DEFAULT_LIMITS={'max_running_jobs':1,'cpu_threads':1,'memory_bytes':21474836480,'scratch_bytes':4294967296}
def module(name):return import_module(PACKAGE+'.'+name)
def rows(local):
    with local._transaction() as db:
        return (db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0],
                [tuple(row) for row in db.execute('SELECT * FROM reservations ORDER BY unit')])
def saved(local,version):
    definition=local.as_record();definition['version']=version
    definition['limits'].update(max_running_jobs=1,cpu_threads=1)
    raw=json.dumps(definition,sort_keys=True)
    with local._transaction() as db:db.execute('UPDATE configuration SET value=? WHERE id=1',(raw,))
    return definition,raw


def test_new_definition_has_byte_only_active_settings(resources):
    local,_=resources
    assert local.as_record()['version']=='shared_local_resources_v2'
    assert set(local.as_record()['limits'])=={'memory_bytes','scratch_bytes'}


@pytest.mark.parametrize('version',['shared_local_resources_v1','shared_local_resources_v2'])
def test_valid_saved_rows_and_reservations_keep_exact_identity(resources,version):
    local,handle=resources;definition,raw=saved(local,version);owner=module('local_resources').LocalResources
    reopened=owner.reopen(definition)
    assert rows(reopened)[0]==raw and reopened.as_record()==definition
    first=reopened.reserve(handle(),cpu_threads=4,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    second=reopened.reserve(handle(),cpu_threads=8,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    before=rows(reopened);again=owner.reopen(definition)
    again.validate_reservation(first);again.validate_reservation(second)
    assert rows(again)==before and rows(again)[0]==raw and again.as_record()==definition
    assert set(again.snapshot()['available'])=={'memory_bytes','scratch_bytes'}
    again.release_reservation(first);again.validate_reservation(second)
    assert rows(again)[0]==raw


def test_saved_factory_configuration_is_exact_and_not_a_new_custom_setting(resources,tmp_path,monkeypatch):
    local,_=resources;definition,raw=saved(local,'shared_local_resources_v1');before=rows(local)
    tools=module('tool_configuration');monkeypatch.setattr(tools,'PublicClients',lambda **kwargs:SimpleNamespace())
    monkeypatch.setenv(module('local_resources').DIRECTORY_ENV,str(local.directory))
    configuration={'local_resources':deepcopy(definition['limits']),'public':{'ncbi_email':None,'provider_access_dir':str(tmp_path/'access')}};original=deepcopy(configuration)
    with module('state').Store(tmp_path/'state') as store:
        restored=tools.build_tools(store,configuration)
        assert restored.local_resources.as_record()==definition
        assert restored.reconstruction_configuration==original
    assert configuration==original and rows(local)==before and rows(local)[0]==raw


@pytest.mark.parametrize('legacy',[False,True],ids=['current-default','original-v1-default'])
def test_missing_database_default_reconstruction_preserves_exact_descriptor(resources,tmp_path,legacy):
    owner=module('local_resources').LocalResources
    original=owner(tmp_path/('default-'+str(legacy)));definition=original.as_record()
    if legacy:
        definition['version']='shared_local_resources_v1';definition['limits']=deepcopy(LEGACY_DEFAULT_LIMITS)
    original.path.unlink()
    reopened=owner.reopen(definition)
    assert reopened.as_record()==definition
    raw,records=rows(reopened);assert json.loads(raw)==definition and records==[]
    assert owner.reopen(definition).as_record()==definition and rows(reopened)==(raw,records)


@pytest.mark.parametrize('legacy',[False,True],ids=['current-custom','original-v1-custom'])
def test_missing_database_custom_descriptor_retains_original_rejection(resources,tmp_path,legacy):
    owner=module('local_resources').LocalResources;original=owner(tmp_path/('custom-'+str(legacy)));definition=original.as_record()
    if legacy:definition['version']='shared_local_resources_v1';definition['limits']=deepcopy(LEGACY_DEFAULT_LIMITS)
    definition['limits']['scratch_bytes']+=1;original.path.unlink()
    with pytest.raises(ValueError,match='^local_resource_binding_conflict$'):owner.reopen(definition)
    # Original reopen initializes defaults, then refuses mismatched descriptors.
    assert original.path.is_file()
    actual=owner(original.directory);assert actual.as_record()!=definition
    expected={**original.as_record(),'version':'shared_local_resources_v1','limits':deepcopy(LEGACY_DEFAULT_LIMITS)}
    assert actual.as_record()==expected
    raw,records=rows(actual);assert raw==json.dumps(expected,sort_keys=True) and records==[]


@pytest.mark.parametrize('fault',[
    'unknown_version','missing_version','missing_limits','missing_jobs','missing_threads',
    'extra_field','extra_limit','null_limits','list_limits','boolean_count',
    'negative_memory','wrong_resource_id'])
def test_rejected_missing_descriptor_initializes_original_default_before_comparison(resources,tmp_path,fault):
    owner=module('local_resources').LocalResources
    original=owner(tmp_path/('rejected-'+fault))
    expected={**original.as_record(),'version':'shared_local_resources_v1','limits':deepcopy(LEGACY_DEFAULT_LIMITS)}
    definition=deepcopy(expected)
    if fault=='unknown_version':definition['version']='unknown_saved_version'
    elif fault=='missing_version':definition.pop('version')
    elif fault=='missing_limits':definition.pop('limits')
    elif fault=='missing_jobs':definition['limits'].pop('max_running_jobs')
    elif fault=='missing_threads':definition['limits'].pop('cpu_threads')
    elif fault=='extra_field':definition['extra']='controlled-unrecognized-field'
    elif fault=='extra_limit':definition['limits']['extra']=1
    elif fault=='null_limits':definition['limits']=None
    elif fault=='list_limits':definition['limits']=[]
    elif fault=='boolean_count':definition['limits']['cpu_threads']=False
    elif fault=='negative_memory':definition['limits']['memory_bytes']=-1
    elif fault=='wrong_resource_id':definition['resource_id']='different-resource'
    else:raise AssertionError(fault)
    supplied=deepcopy(definition);original.path.unlink()
    with pytest.raises(ValueError,match='^local_resource_binding_conflict$'):owner.reopen(definition)
    assert definition==supplied and original.path.is_file()
    actual=owner(original.directory);raw,reservations=rows(actual)
    assert actual.as_record()==expected and raw==json.dumps(expected,sort_keys=True) and reservations==[]
    before=rows(actual)
    with pytest.raises(ValueError,match='^local_resource_binding_conflict$'):owner.reopen(definition)
    assert definition==supplied and rows(actual)==before


@pytest.mark.parametrize('field',['max_running_jobs','cpu_threads','job_slots'])
def test_new_custom_count_settings_remain_invalid(resources,field):
    local,_=resources;owner=module('local_resources').LocalResources
    with pytest.raises(ValueError,match='^invalid_local_resource_settings$'):
        owner(local.directory/('new-'+field),{field:1})


@pytest.mark.parametrize('field',['max_running_jobs','cpu_threads','memory_bytes','scratch_bytes'])
def test_changed_saved_caller_configuration_still_rejects_without_rewriting(resources,field):
    local,_=resources;definition,raw=saved(local,'shared_local_resources_v1');before=rows(local)
    settings=deepcopy(definition['limits']);settings[field]+=1
    with pytest.raises(ValueError,match='^local_resource_limits_conflict$'):
        module('local_resources').LocalResources(local.directory,settings)
    assert rows(local)==before and rows(local)[0]==raw


def test_saved_byte_metadata_and_view_remain_exact_under_separate_physical_bound(resources):
    local,_=resources;definition,raw=saved(local,'shared_local_resources_v1');definition['limits']['memory_bytes']=20*1024**3;raw=json.dumps(definition,sort_keys=True)
    with local._transaction() as db:db.execute('UPDATE configuration SET value=? WHERE id=1',(raw,))
    restored=module('local_resources').LocalResources.reopen(definition)
    assert restored.as_record()==definition and restored.snapshot()['limits']['memory_bytes']==20*1024**3
    assert rows(restored)[0]==raw


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
