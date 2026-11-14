"""Saved V1 resource identities remain exact while active count gates disappear."""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
import pytest

from .test_no_count_resource_admission import resources

PACKAGE = __package__.rsplit('.tests', 1)[0]


def module(name):
    return import_module(PACKAGE+'.'+name)


def legacy_definition(resources):
    local, handle = resources
    definition = deepcopy(local.as_record())
    definition['version'] = 'shared_local_resources_v1'
    definition['limits'].update(max_running_jobs=1, cpu_threads=1)
    raw = json.dumps(definition, sort_keys=True)
    with local._transaction() as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
    return definition, raw, handle


def test_new_definition_and_settings_have_no_active_count_fields(resources):
    local, _ = resources
    assert local.as_record()['version'] == 'shared_local_resources_v2'
    assert set(local.as_record()['limits']) == {'memory_bytes', 'scratch_bytes'}
    with pytest.raises(ValueError, match='invalid_local_resource_settings'):
        module('local_resources').LocalResources(local.directory/'new', {'cpu_threads': 1})


def test_saved_v1_definition_and_reservations_reopen_exactly_with_inert_counts(resources):
    definition, raw, handle = legacy_definition(resources)
    LocalResources = module('local_resources').LocalResources
    local = LocalResources.reopen(definition)
    first = local.reserve(handle(), cpu_threads=4, policy=SimpleNamespace(memory_bytes=64, scratch_bytes=64))
    second = local.reserve(handle(), cpu_threads=8, policy=SimpleNamespace(memory_bytes=64, scratch_bytes=64))
    reopened = LocalResources.reopen(definition)
    reopened.validate_reservation(first)
    reopened.validate_reservation(second)
    assert reopened.as_record() == definition
    with reopened._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0] == raw
    assert set(reopened.snapshot()['available']) == {'memory_bytes', 'scratch_bytes'}
    reopened.release_reservation(first)
    reopened.validate_reservation(second)


def test_saved_tool_factory_uses_exact_resource_definition(resources, tmp_path, monkeypatch):
    definition, raw, _ = legacy_definition(resources)
    tools = module('tool_configuration')
    monkeypatch.setattr(tools, 'PublicClients', lambda **kwargs: SimpleNamespace())
    monkeypatch.setenv(module('local_resources').DIRECTORY_ENV, str(resources[0].directory))
    configuration = {'public': {'ncbi_email': None, 'provider_access_dir': str(tmp_path/'provider-access')},
                     'local_resources': dict(definition['limits'])}
    original = deepcopy(configuration)
    with module('state').Store(tmp_path/'state') as store:
        restored = tools.build_tools(store, configuration)
        assert restored.resource_binding()['local_resources'] == definition
        assert restored.reconstruction_configuration == original
        with restored.local_resources._transaction() as db:
            assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0] == raw


def test_legacy_memory_definition_is_preserved_but_effective_view_obeys_whole_window(resources):
    definition, _, _ = legacy_definition(resources)
    definition['limits']['memory_bytes'] = 20*1024**3
    raw = json.dumps(definition, sort_keys=True)
    with resources[0]._transaction() as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
    local = module('local_resources').LocalResources.reopen(definition)
    assert local.as_record()['limits']['memory_bytes'] == 20*1024**3
    assert local.snapshot()['limits']['memory_bytes'] == 5*1024**3
    with local._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0] == raw
