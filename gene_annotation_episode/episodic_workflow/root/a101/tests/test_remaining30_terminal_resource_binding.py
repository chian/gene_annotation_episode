"""Actual custody/resource validator; no native operation or synthetic scientific result."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.native_database_terminal_custody import validate_native_database_resource

PROFILES=('native_blast_database','native_blast_standard_database')

def configuration(key):
    return {'workspace':'/controlled/workspace',key:{'version':key+'_resource_v1',
        'producer':{'module_root':'/controlled/package','manifest':{
            'path':'/controlled/manifest.json','sha256':'a'*64,'size_bytes':7,'artifact_ref':None}},
        'environment':{'CONTROLLED_METADATA':'retained'},'bindings':[]}}

@pytest.mark.parametrize('key',PROFILES)
def test_actual_resource_validator_retains_detached_configuration(key):
    value=configuration(key);before=deepcopy(value)
    returned=validate_native_database_resource(value,key)
    assert returned==before[key] and value==before
    returned['environment']['CONTROLLED_METADATA']='changed_return_only'
    assert value==before

@pytest.mark.parametrize('key',PROFILES)
def test_actual_resource_validator_preserves_original_schema_error(key):
    value=configuration(key);value[key]['producer']['manifest']['sha256']='not-a-digest';before=deepcopy(value)
    from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError
    with pytest.raises(ContractError,match='^representation_error$'):validate_native_database_resource(value,key)
    assert value==before

def test_unknown_public_resource_key_keeps_original_root_import_failure():
    key='unregistered_controlled_native_profile';value=configuration(key)
    with pytest.raises(ModuleNotFoundError) as caught:validate_native_database_resource(value,key)
    assert caught.value.name=='gene_annotation_episode.episodic_workflow.root.a101.'+key+'_contracts'
