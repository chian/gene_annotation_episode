"""Local resource definition controls; counts never admit work.

Real SQLite and the actual tool factory execute. Only unlaunched service discovery
and unused PublicClients construction are controlled; no native/provider runs.
"""
from copy import deepcopy
from importlib import import_module
import json
import pytest
PACKAGE=__package__.rsplit('.tests',1)[0]
def module(name):return import_module(PACKAGE+'.'+name)
def rows(local):
    with local._transaction() as db:
        return (db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0],
                [tuple(row) for row in db.execute('SELECT * FROM reservations ORDER BY unit')])

@pytest.mark.parametrize('field',['max_running_jobs','cpu_threads','job_slots'])
def test_new_custom_count_initialization_is_still_rejected(tmp_path,field):
    lr=import_module('gene_annotation_episode.local_resources');config={field:1};original=dict(config)
    with pytest.raises(ValueError,match='invalid_local_resource_settings'):
        lr.LocalResources(tmp_path/'new',config)
    assert config==original

