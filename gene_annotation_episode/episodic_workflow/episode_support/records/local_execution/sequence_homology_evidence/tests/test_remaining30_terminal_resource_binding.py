"""Actual custody/resource validator; no native operation or synthetic scientific result."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.local_execution.sequence_homology_evidence.native_database_terminal_custody import validate_native_database_resource

PROFILES=('native_blast_database','native_blast_standard_database')

def configuration(key):
    return {'workspace':'/controlled/workspace',key:{'version':key+'_resource_v1',
        'producer':{'module_root':'/controlled/package'},
        'environment':{'CONTROLLED_METADATA':'retained'},'bindings':[]}}

@pytest.mark.parametrize('key',PROFILES)
def test_actual_resource_validator_retains_detached_configuration(key):
    value=configuration(key);before=deepcopy(value)
    returned=validate_native_database_resource(value,key)
    assert returned==before[key] and value==before
    returned['environment']['CONTROLLED_METADATA']='changed_return_only'
    assert value==before

def test_unknown_public_resource_key_keeps_original_root_import_failure():
    key='unregistered_controlled_native_profile';value=configuration(key)
    with pytest.raises(ModuleNotFoundError) as caught:validate_native_database_resource(value,key)
    assert caught.value.name=='gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.'+key+'_tool_info'
