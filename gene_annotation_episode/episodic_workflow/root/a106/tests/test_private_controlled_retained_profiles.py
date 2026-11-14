"""Actual captured A106 extraction profiles; full Store replay stays separate."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from .scientific_source_custody import science
from ..literature_contract_error import ExperimentalContractError

ASSET=Path(__file__).parent/'fixtures'/'retained_controlled_response_20261112.json'
EXPECTED_SHA256='6df168b88f36cd530f6d10b9c6a056e5db372a8152408c831438778f7a131ea9'

def captured(index):
    raw=ASSET.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED_SHA256
    row=json.loads(raw)[index]
    result=row['result'] if row['kind']=='extraction' else row['saved']['extraction']
    arguments=row['arguments'] if row['kind']=='extraction' else row['saved']['selection']
    version=2 if result['version']=='controlled_response_source_extraction_v2' else 3
    facade=science('literature_controlled_response_v'+str(version)+'_inputs')
    return arguments,result,facade,getattr(facade,'validate_controlled_response_v'+str(version)+'_extraction'),version

@pytest.mark.parametrize('index',range(6))
def test_actual_captured_extraction_and_store_projection_are_unchanged(index):
    arguments,result,_,validate,_=captured(index)
    original=deepcopy(result)
    assert validate(arguments,result)==original==result
    assert hashlib.sha256(ASSET.read_bytes()).hexdigest()==EXPECTED_SHA256

@pytest.mark.parametrize('index',range(6))
@pytest.mark.parametrize('mutation',('unknown_hash','mixed_saved_live'))
def test_unknown_or_mixed_dependency_maps_are_rejected(index,mutation):
    arguments,result,facade,validate,_=captured(index)
    value=deepcopy(result);fingerprints=value['implementation_dependencies']['expected_module_fingerprints']
    key='literature_assay_inputs.py'
    if mutation=='unknown_hash':fingerprints[key]='0'*64
    else:
        current=facade._dependencies();assert current[key]!=fingerprints[key]
        fingerprints[key]=current[key]
        assert fingerprints!=current and fingerprints!=result['implementation_dependencies']['expected_module_fingerprints']
    with pytest.raises(ExperimentalContractError) as error:validate(arguments,value)
    assert error.value.code=='saved_dependency_contract_mismatch'
    assert error.value.field=='implementation_dependencies'

@pytest.mark.parametrize('index',range(6))
def test_authentic_profile_does_not_accept_changed_scientific_projection(index):
    arguments,result,_,validate,version=captured(index)
    value=deepcopy(result)
    assert value['calculation_inputs']['arms']['protein_condition0']['value']==8.0
    value['calculation_inputs']['arms']['protein_condition0']['value']=9.0
    with pytest.raises(ExperimentalContractError) as error:validate(arguments,value)
    assert error.value.code==('saved_calculation_projection_mismatch' if version==2 else 'saved_source_projection_mismatch')

@pytest.mark.parametrize('version',(2,3))
def test_fresh_original_producer_stamps_actual_current_dependencies(version):
    if version==2:
        from .controlled_v2_fixtures import Fixture
    else:
        from .controlled_v3_fixtures import Fixture
    fixture=Fixture(0);facade=science('literature_controlled_response_v'+str(version)+'_inputs')
    result=getattr(facade,'read_controlled_response_v'+str(version)+'_inputs')(fixture.args,read_source=fixture.source)
    current=facade._dependencies()
    assert result['implementation_dependencies']=={'reader_contract_version':'controlled_response_source_extraction_v'+str(version),
        'calculator_contract_version':'controlled_response_owner_inputs_v2','expected_module_fingerprints':current}
    assert result['implementation_dependencies']!=captured(0 if version==2 else 1)[1]['implementation_dependencies']
    assert getattr(facade,'validate_controlled_response_v'+str(version)+'_extraction')(fixture.args,result)==result
