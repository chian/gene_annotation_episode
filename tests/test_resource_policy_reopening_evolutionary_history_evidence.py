"""Local resource definitions carry byte limits only."""
from importlib import import_module
import pytest

PACKAGE = __package__.rsplit('.tests', 1)[0]


def module(name):
    return import_module(PACKAGE+'.'+name)


def test_new_definition_and_settings_have_no_active_count_fields(tmp_path):
    local = import_module('gene_annotation_episode.local_resources').LocalResources(tmp_path/'capacity', {'memory_bytes': 512, 'scratch_bytes': 512})
    assert local.as_record()['version'] == 'shared_local_resources_v3'
    assert set(local.as_record()['limits']) == {'memory_bytes', 'scratch_bytes'}
    with pytest.raises(ValueError, match='invalid_local_resource_settings'):
        import_module('gene_annotation_episode.local_resources').LocalResources(local.directory/'new', {'cpu_threads': 1})
