"""Replay actual controlled emissions across exact private source stages."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from .scientific_source_custody import science
from ..literature_contract_error import ExperimentalContractError

DIRECTORY=Path(__file__).parent/'fixtures/controlled_private_emissions_20261112'
MANIFEST_SHA256='bc93aa9f1cf7041e3a65a2645701c8a410e00cf9c3d8a06a474a8656664ba5b5'
STAGES=('pre_repair_private','post_repair_private')

def manifest():
    raw=(DIRECTORY/'manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==MANIFEST_SHA256
    return json.loads(raw)

def saved(stage,version):
    m=manifest();entry=m['captures'][stage]
    content=(DIRECTORY/entry['records']).read_bytes()
    assert hashlib.sha256(content).hexdigest()==entry['records_sha256']
    row=next(r for r in json.loads(content) if r['version']==version)
    assert row['stage']==stage and row['case_index']==6
    facade=science('literature_controlled_response_v'+str(version)+'_inputs')
    return row,facade,getattr(facade,'validate_controlled_response_v'+str(version)+'_extraction')

def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from walk(v)
    elif isinstance(x,list):
        for v in x:yield from walk(v)

@pytest.fixture(autouse=True)
def forbid_new_source_acquisition(monkeypatch):
    def forbidden(*args,**kwargs):
        pytest.fail('Saved private emission replay must not reacquire source material')
    monkeypatch.setattr(science('literature_controlled_response_inputs'),'open_controlled_response_sources',forbidden)

@pytest.mark.parametrize('stage',STAGES)
@pytest.mark.parametrize('version',(2,3))
def test_actual_private_emission_replays_unchanged(stage,version):
    row,_,validate=saved(stage,version);original=deepcopy(row['result'])
    assert validate(row['arguments'],row['result'])==original==row['result']
    assert any(x.get('status')=='measured' for x in walk(original) if 'counter_module_sha256' in x)
    assert manifest()['historical_store_claim'] is False

@pytest.mark.parametrize('stage',STAGES)
@pytest.mark.parametrize('version',(2,3))
@pytest.mark.parametrize('mutation',('unknown_private_map','mixed_private_map','mismatched_counter'))
def test_correlated_private_profile_rejects_mixed_or_changed_identity(stage,version,mutation):
    row,facade,validate=saved(stage,version);value=deepcopy(row['result'])
    fingerprints=value['implementation_dependencies']['expected_module_fingerprints']
    if mutation=='unknown_private_map':
        fingerprints['literature_assay_inputs.py']='0'*64
    elif mutation=='mixed_private_map':
        other=STAGES[1-STAGES.index(stage)]
        other_row,_,_=saved(other,version);other_map=other_row['result']['implementation_dependencies']['expected_module_fingerprints']
        key='literature_controlled_response_inputs.py'
        assert fingerprints[key]!=other_map[key]
        fingerprints[key]=other_map[key]
        assert fingerprints!=other_map and fingerprints!=facade._dependencies()
    else:
        pixels=[x for x in walk(value) if 'counter_module_sha256' in x];assert pixels
        for pixel in pixels:
            assert pixel['counter_module_sha256']!='0'*64
            pixel['counter_module_sha256']='0'*64
    with pytest.raises(ExperimentalContractError) as error:validate(row['arguments'],value)
    assert error.value.code==('saved_graph_image_identity_mismatch' if mutation=='mismatched_counter' else 'saved_dependency_contract_mismatch')
    assert error.value.field==('pixels' if mutation=='mismatched_counter' else 'implementation_dependencies')

@pytest.mark.parametrize('stage',STAGES)
def test_actual_fixture_inputs_and_implementation_provenance_are_preserved(stage):
    m=manifest();entry=m['captures'][stage];capture=json.loads((DIRECTORY/entry['capture']).read_bytes())
    assert capture['actual_original_producer_calls']==2 and capture['historical_store_claim'] is False
    assert capture['metadata_transformation'] is False and capture['application_unchanged']
    for relative,digest in capture['files'].items():
        assert hashlib.sha256((DIRECTORY/stage/relative).read_bytes()).hexdigest()==digest
    for version in (2,3):
        row,_,_=saved(stage,version);profile=row['result']['implementation_dependencies']
        assert profile==capture['profiles']['controlled_response_source_extraction_v'+str(version)]
        assert row['arguments']==row['result']['selection']
        for source in row['implementation']:
            assert hashlib.sha256((DIRECTORY/stage/source['file']).read_bytes()).hexdigest()==profile['expected_module_fingerprints'][source['name']]
        assert row['actual_read_calls'] and row['source_inputs']
