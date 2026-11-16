"""Local resource definition controls; counts never admit work.

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

def test_current_definition_has_byte_limits_and_reopens_exactly(resources):
    local,handle=resources;definition=local.as_record()
    assert definition['version']=='shared_local_resources_v2'
    assert set(definition['limits'])=={'memory_bytes','scratch_bytes'}
    reservation=local.reserve(handle(),cpu_threads=4,policy=SimpleNamespace(memory_bytes=64,scratch_bytes=64))
    before=rows(local);restored=module('local_resources').LocalResources.reopen(definition)
    assert restored.as_record()==definition and rows(restored)==before
    restored.validate_reservation(reservation)
    assert reservation['allocation']['cpu_threads']==4

@pytest.mark.parametrize('field',['max_running_jobs','cpu_threads','job_slots'])
def test_new_custom_count_initialization_is_still_rejected(tmp_path,field):
    lr=module('local_resources');config={field:1};original=dict(config)
    with pytest.raises(ValueError,match='invalid_local_resource_settings'):
        lr.LocalResources(tmp_path/'new',config)
    assert config==original

