"""Actual original336 typed schemas/rows, independently of native production.

These tests validate original recorded shapes only. They do not establish a
receiving grant, relocate a worker, assess new science or read raw structures.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
from importlib import import_module
import json
from pathlib import Path
import sqlite3
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]
FIXTURE=Path(__file__).resolve().parents[2]/'a108/tests/fixtures/retained_protein_reader_336'
DATABASE_SHA='efb35ce65a40b064ba9179b08c604779b9274a9da8cbe5311f2ae7fcd10609b7'

@lru_cache(maxsize=1)
def original_records():
    database=FIXTURE/'state/state.sqlite3'
    assert hashlib.sha256(database.read_bytes()).hexdigest()==DATABASE_SHA
    db=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        rows=db.execute('SELECT contract,form FROM runtime_report_attempts WHERE failure IS NULL AND form IS NOT NULL').fetchall()
        kept=[]
        for contract,form in rows:
            schema=json.loads(contract).get('measurements',{}).get('schema',{})
            payload=json.loads(form)
            selected={name:node for name,node in schema.get('properties',{}).items()
                      if str(node.get('x-source','')).startswith('execution_protein_structure_')}
            if selected:kept.append((schema,payload,selected))
        assert kept,'actual original336 protein forms required'
        assert any(payload.get(name) for _,payload,fields in kept for name in fields)
        return kept
    finally:db.close()


@pytest.mark.parametrize('altered',[False,True])
def test_actual_original_protein_schema_is_exactly_registered(altered):
    communication=import_module(PACKAGE+'.communication')
    for original,_,fields in original_records():
        schema=deepcopy(original)
        if altered:
            name=next(iter(fields))
            schema['properties'][name]['description']='changed original registered source schema'
            with pytest.raises(communication.ReportBoundaryError):
                communication.validate_closed_schema(schema)
        else:
            assert communication.validate_closed_schema(schema)==schema


@pytest.mark.parametrize('altered',[False,True])
def test_actual_nonempty_protein_rows_keep_original_typed_validation(altered):
    communication=import_module(PACKAGE+'.communication')
    examined=0
    for _,payload,fields in original_records():
        for name,node in fields.items():
            values=deepcopy(payload.get(name))
            if not values:continue
            assert type(values) is list and type(values[0]) is dict
            examined+=1
            if altered:
                values[0]['version']='changed-original-descriptor'
                with pytest.raises(communication.ReportBoundaryError):
                    communication._validate_protein_structure_fact_rows(values,node['x-source'],name)
            else:
                assert communication._validate_protein_structure_fact_rows(values,node['x-source'],name) is None
    assert examined
