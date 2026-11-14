"""Original incoming contracts and original model-field exclusions together."""
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture(scope='module')
def original():
    raw=(Path(__file__).parent/'fixtures/retained_domain_contract/original_domain.py.txt').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='ede8c98584889d77485017e66c59e4885104a3956d9251d856ef6359759112d0'
    name='retained_original_domain_contract_fixture'
    assert name not in sys.modules
    module=ModuleType(name)
    sys.modules[name]=module
    try:
        exec(compile(raw,'<authenticated original pure domain contracts>','exec'),module.__dict__)
        yield module
    finally:
        del sys.modules[name]




@pytest.mark.parametrize('axis',['a101','a105','a106','a108'])
def test_original_native_record_schema_accepts_and_rejects_actual_fields(axis,original):
    current=import_module('gene_annotation_episode.episodic_workflow.root.'+axis+'.domain')
    record={'subject_refs':[original.identity('reference', {'control': 'original schema fixture'})],'source_subject_refs':[], 'kind':'alignment',
        'source_ref':original.identity('source', {'control': 'original schema fixture'}),'measurements':[],'dependencies':[],'anchor':None,
        'native_blast':{'program':'blastp','report_ordinal':0,'hit_ordinal':0,'hsp_ordinal':0,
            'query_from':1,'query_to':4,'hit_from':1,'hit_to':4,
            'query_coordinate_unit':'aa','hit_coordinate_unit':'aa','alignment_unit':'aa'}}
    original.validate_schema(record,original.RECORD_SCHEMAS['observation'])
    current.validate_schema(record,current.RECORD_SCHEMAS['observation'])
    changed=deepcopy(record);changed['native_blast']['query_from']=0
    with pytest.raises(current.ContractError):current.validate_schema(changed,current.RECORD_SCHEMAS['observation'])
    forged=deepcopy(record);forged['native_blast']['invented_identity']='forged'
    with pytest.raises(current.ContractError):current.validate_schema(forged,current.RECORD_SCHEMAS['observation'])


