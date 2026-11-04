"""Caller reconstruction publication; no model, episode or scientific work."""
from dataclasses import FrozenInstanceError
import json

import pytest

from method_loop.durable import DurableExecutionError, canonical, content_digest
from gene_annotation_episode import application_execution_binding as application
from gene_annotation_episode.default_scientific_binding import VERSION as DEFAULT_VERSION
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from gene_annotation_episode.tools import ToolRegistry


MARKER = {'version': 'durable_episode_application_v1',
          'binding_file': 'episode-execution-binding.json'}


@pytest.fixture
def run(tmp_path):
    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        directory = tmp_path/'run'
        directory.mkdir()
        settings = {'directory': str(directory), 'problem': store.problem(),
            'binding_definitions': {'credit': {'default_entrypoint': DEFAULT_VERSION}},
            'episode_bindings': [], 'episode_role_credit_bindings': {},
            'models': {'fixture': 'unused'}, 'controller': {'fixture': 'unused'}}
        journal = Journal(store, 'run_fixture')
        journal.save('runtime_runs', {'settings': canonical(settings), 'state': 'created',
            'summary': None, 'started_at': 'original-start', 'updated_at': 'original-update'})
        (directory/'run.json').write_text(canonical({'run_id': 'run_fixture', **settings}))
        yield store, directory, settings


def saved_settings(store):
    return json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])


def custom_binding(**changes):
    return {'factory_module': 'fixture_owned_factory', 'factory_name': 'open_commission',
        'arguments': {'owned_configuration': {'value': 7}},
        'implementation_sha256': 'a'*64, 'settings_sha256': 'b'*64, **changes}


@pytest.fixture
def known_factory(monkeypatch):
    calls = []
    monkeypatch.setattr(application.reconstruction, 'implementation_sha256', lambda: 'c'*64)

    def make(store, directory, *, kind, tool_configuration):
        # The real factory opens a separate Store connection. Establish that
        # settings are committed and the manifest already matches that state.
        with Store(store.path) as reopened:
            settings = saved_settings(reopened)
        assert settings['episode_execution'] == MARKER
        assert settings['tool_configuration'] == tool_configuration
        assert json.loads((directory/'run.json').read_text()) == {'run_id': 'run_fixture', **settings}
        pins = ({name: content_digest(json.loads((directory/name).read_text()))
                 for name in ('case-launch.json', 'policy-binding.json')}
                if kind == 'fixed_case' else {})
        calls.append((kind, tool_configuration))
        return {'factory_module': application.reconstruction.FACTORY_MODULE,
            'factory_name': application.reconstruction.FACTORY_NAME,
            'arguments': {'kind': kind, 'tool_configuration': tool_configuration,
                          'caller_binding_pins': pins},
            'implementation_sha256': 'c'*64, 'settings_sha256': content_digest(settings)}

    monkeypatch.setattr(application.reconstruction, 'make_runtime_binding', make)
    return calls


def test_legacy_without_reconstruction_selection_stays_unchanged(run):
    store, directory, settings = run
    before = (directory/'run.json').read_bytes()
    result = application.bind_episode_execution(store, directory, settings=settings, resume=True)
    assert result.settings == settings and result.runtime_binding is None
    assert saved_settings(store) == settings
    assert (directory/'run.json').read_bytes() == before
    assert not (directory/application.BINDING_FILE).exists()
    assert store.db.execute("SELECT name FROM sqlite_master WHERE name='runtime_execution_bindings'").fetchone() is None
    with pytest.raises(FrozenInstanceError):
        result.settings = {}


@pytest.mark.parametrize('options', [{'requested_binding': custom_binding()}, {'use_saved_runtime': True}])
def test_legacy_resume_cannot_convert_execution_semantics(run, options):
    store, directory, settings = run
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=settings, resume=True,
            tool_configuration={}, **options)
    assert error.value.failure['code'] == 'identity_conflict'
    assert saved_settings(store) == settings
    assert not (directory/application.BINDING_FILE).exists()


def test_known_default_publishes_actual_configuration_before_factory_and_does_not_rehash_self(run, known_factory):
    store, directory, settings = run
    configuration = {'public': {'transport_timeout_seconds': 73}, 'local_tools': {'cmsearch_cpu': 2}}
    result = application.bind_episode_execution(store, directory, settings=settings,
        use_saved_runtime=True, tool_configuration=configuration)
    assert known_factory == [('standard_default', configuration)]
    assert result.settings == {**settings, 'episode_execution': MARKER, 'tool_configuration': configuration}
    assert result.runtime_binding['settings_sha256'] == content_digest(result.settings)
    assert json.loads((directory/application.BINDING_FILE).read_text()) == result.runtime_binding
    assert 'runtime_binding' not in result.settings
    assert saved_settings(store) == result.settings
    row = store.db.execute('SELECT * FROM runtime_runs').fetchone()
    assert (row['state'], row['started_at'], row['updated_at']) == ('created', 'original-start', 'original-update')
    configuration['local_tools']['cmsearch_cpu'] = 99
    assert result.settings['tool_configuration']['local_tools']['cmsearch_cpu'] == 2


def test_explicit_custom_descriptor_is_unchanged_and_does_not_import_factory(run, monkeypatch):
    store, directory, settings = run
    monkeypatch.setattr(application.reconstruction, 'make_runtime_binding',
        lambda *args, **kwargs: pytest.fail('a custom descriptor must not choose a known factory'))
    binding = custom_binding()
    result = application.bind_episode_execution(store, directory, settings=settings, requested_binding=binding)
    assert result.runtime_binding == binding
    assert result.settings == {**settings, 'episode_execution': MARKER}
    assert 'tool_configuration' not in result.settings
    assert json.loads((directory/application.BINDING_FILE).read_text()) == binding
    binding['arguments']['owned_configuration']['value'] = 99
    assert result.runtime_binding['arguments']['owned_configuration']['value'] == 7


@pytest.mark.parametrize('changes', [
    {'extra': 'forbidden'}, {'factory_name': 'factory()'}, {'arguments': []},
    {'implementation_sha256': 'not-a-digest'}, {'settings_sha256': 'F'*64},
    {'arguments': {'invalid': float('nan')}}])
def test_custom_descriptor_has_exact_finite_c1_shape(run, changes):
    store, directory, settings = run
    with pytest.raises(ValueError):
        application.bind_episode_execution(store, directory, settings=settings,
            requested_binding=custom_binding(**changes))
    assert saved_settings(store) == settings


def test_changed_descriptor_configuration_or_authoritative_settings_cannot_replace_saved_binding(run):
    store, directory, settings = run
    result = application.bind_episode_execution(store, directory, settings=settings,
        requested_binding=custom_binding(), tool_configuration={})
    before = (directory/application.BINDING_FILE).read_bytes()
    for options in ({'requested_binding': custom_binding(arguments={'changed': True})},
                    {'tool_configuration': {'changed': True}},
                    {'settings': {**result.settings, 'new': True}}):
        with pytest.raises(DurableExecutionError) as error:
            application.bind_episode_execution(store, directory,
                **{'settings': result.settings, 'resume': True, **options})
        assert error.value.failure['code'] == 'identity_conflict'
    assert (directory/application.BINDING_FILE).read_bytes() == before
    assert saved_settings(store) == result.settings


@pytest.mark.parametrize('manifest', ['missing', 'stale'])
def test_recovery_repairs_manifest_and_missing_descriptor_from_store_without_factory(run, monkeypatch, manifest):
    store, directory, settings = run
    original = application.bind_episode_execution(store, directory, settings=settings,
        requested_binding=custom_binding(), tool_configuration={})
    (directory/application.BINDING_FILE).unlink()
    if manifest == 'missing':
        (directory/'run.json').unlink()
    else:
        (directory/'run.json').write_text(canonical({'run_id': 'unrelated', 'directory': 'stale'}))
    monkeypatch.setattr(application.reconstruction, 'make_runtime_binding',
        lambda *args, **kwargs: pytest.fail('saved descriptor recovery must not select a factory'))
    recovered = application.bind_episode_execution(store, directory, settings=original.settings, resume=True)
    assert recovered == original
    assert json.loads((directory/'run.json').read_text()) == {'run_id': 'run_fixture', **original.settings}
    assert json.loads((directory/application.BINDING_FILE).read_text()) == original.runtime_binding


def test_existing_descriptor_file_is_immutable_even_when_store_has_original(run):
    store, directory, settings = run
    original = application.bind_episode_execution(store, directory, settings=settings,
        requested_binding=custom_binding())
    changed = custom_binding(arguments={'different': True})
    (directory/application.BINDING_FILE).write_text(canonical(changed))
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=original.settings, resume=True)
    assert error.value.failure['code'] == 'identity_conflict'
    assert json.loads((directory/application.BINDING_FILE).read_text()) == changed
    row = store.db.execute('SELECT runtime_binding FROM runtime_execution_bindings').fetchone()
    assert json.loads(row[0]) == original.runtime_binding


@pytest.mark.parametrize('replacement', [True, 1.0])
def test_descriptor_identity_preserves_json_value_types(run, replacement):
    store, directory, settings = run
    original = application.bind_episode_execution(store, directory, settings=settings,
        requested_binding=custom_binding(arguments={'value': 1}))
    changed = custom_binding(arguments={'value': replacement})
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=original.settings,
            requested_binding=changed, resume=True)
    assert error.value.failure['code'] == 'identity_conflict'
    (directory/application.BINDING_FILE).write_text(canonical(changed))
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=original.settings, resume=True)
    assert error.value.failure['code'] == 'identity_conflict'


def test_crash_after_marker_uses_original_known_factory_without_reselecting_from_new_files(run, known_factory, monkeypatch):
    store, directory, settings = run
    original = application.reconstruction.make_runtime_binding
    monkeypatch.setattr(application.reconstruction, 'make_runtime_binding',
        lambda *args, **kwargs: (_ for _ in ()).throw(DurableExecutionError('unavailable_binding')))
    with pytest.raises(DurableExecutionError):
        application.bind_episode_execution(store, directory, settings=settings,
            use_saved_runtime=True, tool_configuration={})
    marked = saved_settings(store)
    assert marked['episode_execution'] == MARKER
    assert not (directory/application.BINDING_FILE).exists()
    # A later file cannot change the original standard_default selection.
    (directory/'case-launch.json').write_text(canonical({'configuration': {}}))
    monkeypatch.setattr(application.reconstruction, 'make_runtime_binding', original)
    recovered = application.bind_episode_execution(store, directory, settings=marked, resume=True)
    assert recovered.runtime_binding['arguments']['kind'] == 'standard_default'
    assert known_factory == [('standard_default', {})]


def test_crash_after_marker_keeps_original_custom_descriptor_even_without_caller_repeat(run, monkeypatch):
    store, directory, settings = run
    publish = application._publish
    monkeypatch.setattr(application, '_publish',
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError('fixture publication interruption')))
    binding = custom_binding()
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=settings, requested_binding=binding)
    assert error.value.failure['code'] == 'storage_failure'
    marked = saved_settings(store)
    monkeypatch.setattr(application, '_publish', publish)
    recovered = application.bind_episode_execution(store, directory, settings=marked, resume=True)
    assert recovered.runtime_binding == binding


def test_fixed_case_keeps_original_launch_and_policy_pins(run, known_factory):
    store, directory, settings = run
    configuration = {'workspace': str(store.path), 'local_tools': {'cmsearch_cpu': 2}}
    for name, value in (('case-launch.json', {'configuration': configuration}),
                        ('policy-binding.json', {'source_sha256': 'd'*64, 'parameters': {'cost': .01}})):
        (directory/name).write_text(canonical(value))
    result = application.bind_episode_execution(store, directory, settings=settings,
        use_saved_runtime=True, tool_configuration=configuration)
    assert known_factory == [('fixed_case', configuration)]
    assert result.runtime_binding['arguments']['caller_binding_pins'] == {
        name: content_digest(json.loads((directory/name).read_text()))
        for name in ('case-launch.json', 'policy-binding.json')}


def test_fixed_case_crash_gap_rejects_changed_original_policy_pin(run, known_factory, monkeypatch):
    store, directory, settings = run
    (directory/'case-launch.json').write_text(canonical({'configuration': {}}))
    (directory/'policy-binding.json').write_text(canonical({'original': True}))
    original = application.reconstruction.make_runtime_binding
    monkeypatch.setattr(application.reconstruction, 'make_runtime_binding',
        lambda *args, **kwargs: (_ for _ in ()).throw(DurableExecutionError('unavailable_binding')))
    with pytest.raises(DurableExecutionError):
        application.bind_episode_execution(store, directory, settings=settings,
            use_saved_runtime=True, tool_configuration={})
    (directory/'policy-binding.json').write_text(canonical({'original': False}))
    monkeypatch.setattr(application.reconstruction, 'make_runtime_binding', original)
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=saved_settings(store), resume=True)
    assert error.value.failure['code'] == 'identity_conflict'
    assert known_factory == []


@pytest.mark.parametrize('changed', ['implementation', 'policy'])
def test_saved_known_binding_rejects_changed_original_pins_before_return(run, known_factory, monkeypatch, changed):
    store, directory, settings = run
    (directory/'case-launch.json').write_text(canonical({'configuration': {}}))
    (directory/'policy-binding.json').write_text(canonical({'original': True}))
    original = application.bind_episode_execution(store, directory, settings=settings,
        use_saved_runtime=True, tool_configuration={})
    before = (directory/application.BINDING_FILE).read_bytes()
    if changed == 'implementation':
        monkeypatch.setattr(application.reconstruction, 'implementation_sha256', lambda: 'e'*64)
    else:
        (directory/'policy-binding.json').write_text(canonical({'original': False}))
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=original.settings, resume=True)
    assert error.value.failure['code'] == 'identity_conflict'
    assert (directory/application.BINDING_FILE).read_bytes() == before
    assert len(known_factory) == 1


@pytest.mark.parametrize('kind', ['arbitrary_registry', 'custom_science'])
def test_missing_known_reconstruction_capability_is_structured_and_installs_nothing(run, known_factory, kind):
    store, directory, settings = run
    if kind == 'custom_science':
        settings['binding_definitions'] = {'credit': {'custom': True}}
        store.db.execute('UPDATE runtime_runs SET settings=?', (canonical(settings),))
    with pytest.raises(DurableExecutionError) as error:
        application.bind_episode_execution(store, directory, settings=settings,
            use_saved_runtime=True, tool_configuration={} if kind == 'custom_science' else None)
    assert error.value.failure['code'] == 'unavailable_binding'
    assert saved_settings(store) == settings
    assert known_factory == []
    assert not (directory/application.BINDING_FILE).exists()


def test_build_tools_copies_only_actual_configuration_operands_without_changing_resources(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'user-config'))
    monkeypatch.delenv('NCBI_EMAIL', raising=False)
    configuration = {'local_tools': {'cmsearch_cpu': 2},
        'public': {'transport_timeout_seconds': 73, 'ncbi_email': None}, 'caller_metadata': {'selection': ['actual']}}
    with Store(tmp_path/'workspace') as store:
        ordinary = ToolRegistry(store, cmsearch_cpu=2)
        configured = build_tools(store, configuration)
        assert configured.resource_binding() == ordinary.resource_binding()
        assert not hasattr(ordinary, 'reconstruction_configuration')
        assert configured.reconstruction_configuration == configuration
        configuration['caller_metadata']['selection'].append('later')
        assert configured.reconstruction_configuration['caller_metadata']['selection'] == ['actual']
        assert build_tools(store).reconstruction_configuration == {'public': {'ncbi_email': None}}
