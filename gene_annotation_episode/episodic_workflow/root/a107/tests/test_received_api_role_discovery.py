"""Configuration declarations use real factories; no API/native work is invoked.

Run baseline selectors before application, connected selectors afterward.
These tests do not grant receipt access or claim a scientific result.
"""
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace

import pytest

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a107.'


def module(name):
    return importlib.import_module(PREFIX + name.replace('/', '.'))


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('configuration-only test attempted transport or native execution')
    monkeypatch.setattr('socket.create_connection', denied)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', denied)
    monkeypatch.setattr('subprocess.Popen', denied)
    native = module('native_lifecycle')
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'collect', 'wait_job'):
        monkeypatch.setattr(native, name, denied)


@pytest.fixture
def configured(tmp_path):
    resources = {'data': {'kind': 'api', 'service': 'bvbrc_data'},
        'minhash': {'kind': 'api', 'service': 'bvbrc_minhash',
            'endpoint': 'https://minhash.example.invalid/native/rpc'}}
    with module('state').Store(tmp_path / 'store') as store:
        tools = module('tools').ToolRegistry(store)
        services = SimpleNamespace(annotation_task_required=lambda: False)
        factory = module('execution_service_setup').ExecutionServiceFactory(
            resources, {}, 3., 2., 1., log_window_bytes=1024, log_roles=('stdout',))
        record = module('communication').plain(factory.as_record())
        options = {key: deepcopy(record[key]) for key in ('resources', 'initial_information',
            'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')}
        owners = [module(home + '/episode').ExecutionEpisode(services, store=store,
            run_id='api-role-discovery', directory=tmp_path / 'workflow', tool_registry=tools,
            **options) for home in ('hpc_work_planning/execution_result_acquisition',
                'execution_result_acquisition')]
        yield SimpleNamespace(store=store, tools=tools, services=services, factory=factory,
            owner=owners[0], other=owners[1], directory=tmp_path / 'workflow', output=tmp_path)


def registry_for(case, *, duplicate=False):
    return module('episode_bindings').EpisodeBindingRegistry(
        [case.owner, case.other] if duplicate else [case.owner])


@pytest.mark.parametrize('role', ['annotation', 'scientific_process', 'results'])
def test_baseline_original_unambiguous_role_only_schema_lookup(configured, role):
    case = configured
    registry = registry_for(case)
    assert registry._context_bindings(role) == [case.owner]
    before = tuple(case.store.db.iterdump())
    expected = case.owner.received_report_sources(role)
    actual = registry.received_report_sources(role)
    assert actual == expected
    assert tuple(case.store.db.iterdump()) == before
    (case.output / ('original-role-schema-' + role + '.json')).write_text(json.dumps({
        'role': role, 'binding_path': case.owner.binding_path, 'original_sources': actual,
        'schema_only': True, 'native_or_api_operations': 0}, indent=2) + '\n')


def test_baseline_original_duplicate_roles_require_saved_context(configured):
    registry = registry_for(configured, duplicate=True)
    with pytest.raises(LookupError, match='^episode_binding_context_required$'):
        registry.received_report_sources('annotation')


def connect(case, registry, *, explicit_mapping=False):
    authority = module('library/received_api_information/received_api_authority')
    if explicit_mapping:
        second = type(case.factory).from_record(case.factory.as_record())
        assert second is not case.factory and second.as_record() == case.factory.as_record()
        configuration = authority.ReceivedAPIConfiguration([('a', case.factory), ('b', second)],
            [{'recipient': '@annotation', 'authority_id': 'a'},
             {'recipient': case.owner.binding_path, 'authority_id': 'a'}])
    else:
        configuration = authority.ReceivedAPIConfiguration.original_global_factory(case.factory)
    catalog = configuration.construct(store=case.store, run_id=case.owner.run_id,
        directory=case.directory, tool_registry=case.tools, services=case.services)
    registry.configure_received_api_information(catalog,
        module('annotation_received_api_information').received_api_reports)
    if not explicit_mapping:
        general_configuration = module('library/received_execution_information/received_configuration').ReceivedExecutionConfiguration.original_global_factory(case.factory)
        general = general_configuration.construct(store=case.store, run_id=case.owner.run_id,
            directory=case.directory, tool_registry=case.tools, services=case.services)
        registry.configure_received_execution_information(general,
            module('annotation_received_execution_information').received_execution_information)
    else:
        general = None
    return catalog, general


def original_api_declarations(role):
    if role not in {'annotation', 'scientific_process'}:
        return {}
    data = module('bvbrc_data_views').bvbrc_data_fact_sources()
    minhash = module('bvbrc_minhash_views').minhash_fact_sources()
    assert data and minhash and not set(data).intersection(minhash)
    return {**data, **minhash}


@pytest.mark.parametrize('role', ['annotation', 'scientific_process', 'results', 'unbound-custom-role'])
def test_connected_global_role_discovery_preserves_actual_api_declarations(configured, monkeypatch, role):
    case = configured
    registry = registry_for(case)
    catalog, general = connect(case, registry)
    expected_api = original_api_declarations(role)
    expected_general = general.configured('@original-global-role-only-schema').received_report_sources(role)
    assert not set(expected_api).intersection(expected_general)
    before = tuple(case.store.db.iterdump())
    def no_receipt_lookup(*args, **kwargs):
        pytest.fail('configuration discovery requested received context or evidence')
    monkeypatch.setattr(catalog, 'received', no_receipt_lookup)
    monkeypatch.setattr(general, 'received', no_receipt_lookup)
    reader = registry._recipient_received_api_reports(role, configuration_only=True)
    assert reader.received_report_sources(role) == expected_api
    assert registry.received_report_sources(role) == {**expected_api, **expected_general}
    assert tuple(case.store.db.iterdump()) == before


def test_connected_global_authority_preserves_original_role_ambiguity(configured, monkeypatch):
    registry = registry_for(configured, duplicate=True)
    catalog, _ = connect(configured, registry)
    monkeypatch.setattr(catalog, 'configured', lambda *_: pytest.fail('ambiguous role reached configured reader'))
    with pytest.raises(LookupError, match='^episode_binding_context_required$'):
        registry._recipient_received_api_reports('annotation', configuration_only=True)
    with pytest.raises(LookupError, match='^episode_binding_context_required$'):
        registry.received_report_sources('annotation')


def test_connected_equal_factories_and_explicit_mapping_do_not_authorize_role_only(configured):
    registry = registry_for(configured)
    catalog, _ = connect(configured, registry, explicit_mapping=True)
    assert catalog.configuration.original_global_authority is None
    with pytest.raises(LookupError, match='^episode_binding_context_required$'):
        registry._recipient_received_api_reports('annotation', configuration_only=True)


@pytest.mark.parametrize('operation', ['reader', 'facts', 'reference', 'validation', 'admission'])
def test_connected_role_only_never_grants_received_evidence(configured, operation):
    registry = registry_for(configured)
    connect(configured, registry)
    before = tuple(configured.store.db.iterdump())
    schema = {'type': 'object', 'properties': {}, 'additionalProperties': False}
    calls = {
        'reader': lambda: registry._recipient_received_api_reports('annotation'),
        'facts': lambda: registry.received_report_facts('annotation'),
        'reference': lambda: registry.resolve_received_reference('annotation', 'source_unreceived', 'source'),
        'validation': lambda: registry.validate_received_report('annotation', {}, schema),
        'admission': lambda: registry.received_form_references('annotation', {}, schema, 'no-context'),
    }
    with pytest.raises(LookupError, match='^episode_binding_context_required$'):
        calls[operation]()
    assert tuple(configured.store.db.iterdump()) == before


def test_connected_duplicate_source_field_remains_an_error(configured, monkeypatch):
    case = configured
    registry = registry_for(case)
    connect(case, registry)
    expected = original_api_declarations('annotation')
    name = next(iter(expected))
    # Explicit competing declaration exercises the unchanged strict aggregator.
    monkeypatch.setattr(case.owner, 'received_report_sources', lambda role: {name: expected[name]}, raising=False)
    with pytest.raises(ValueError, match='^received_report_field_conflict:received_report_sources$'):
        registry.received_report_sources('annotation')
