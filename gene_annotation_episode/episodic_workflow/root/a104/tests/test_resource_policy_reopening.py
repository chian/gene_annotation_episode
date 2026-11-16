"""Local resource definitions carry byte limits only."""
from importlib import import_module
import pytest

from .test_no_count_resource_admission import resources

PACKAGE = __package__.rsplit('.tests', 1)[0]


def module(name):
    return import_module(PACKAGE+'.'+name)



def test_new_definition_and_settings_have_no_active_count_fields(resources):
    local, _ = resources
    assert local.as_record()['version'] == 'shared_local_resources_v2'
    assert set(local.as_record()['limits']) == {'memory_bytes', 'scratch_bytes'}
    with pytest.raises(ValueError, match='invalid_local_resource_settings'):
        module('local_resources').LocalResources(local.directory/'new', {'cpu_threads': 1})


