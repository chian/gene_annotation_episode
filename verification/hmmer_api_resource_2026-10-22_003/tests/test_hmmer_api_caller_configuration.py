"""Actual opt-in caller factory and saved-policy consumers, without execution.

All configuration, sequence material and clients are engineering fixtures. These
checks start no episode, worker, native program, public HTTP or model transport.
Application factory/setup/Store/registry definitions are the real implementations.
"""
import asyncio
from copy import deepcopy
from dataclasses import fields
import hashlib
import json
from pathlib import Path

import pytest

from method_loop.durable import DurableExecutionError
from gene_annotation_episode import assembled_case_policy, assembled_service_setup
from gene_annotation_episode.assembled_case_policy import create_policy
from gene_annotation_episode.case_execution import PolicyBindings, _load_policy
from gene_annotation_episode.episode_application_services import service_binding
from gene_annotation_episode.homology_progress import HomologyProgressProvider
from gene_annotation_episode.investigation_policy import create_policy as investigation_policy
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.resource_operational_credit import ResourceOperationalCredit
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.tools import ToolRegistry
from test_assembled_case_policy import REPLACED_FIELDS, SPECIALIST_ROLES, parameters
from test_hmmer_api_operations import FixtureClient, registry
from test_resource_service_setup import resources
from test_runtime import ScriptedProvider


INPUTS = {1: 'actual_tool_catalog_v1', 2: 'actual_tool_registry_v1'}


def caller_parameters(client, version=2):
    supplied = parameters()
    supplied['services']['version'] = f'assembled_case_services_v{version}'
    if version == 2:
        supplied['services']['public_search_registry'] = registry(client)
    return supplied


def workflow_options(r, policy):
    return dict(controller_factory=policy.controller_factory,
        project_credit=policy.project_task_credit,
        project_child_credit=policy.project_scientific_child_credit,
        project_annotation_score=policy.project_annotation_score,
        initial_known_record_refs=policy.initial_known_record_refs,
        native_timing_information=policy.native_timing_information,
        job_episodes=r.homology, resource_estimator=r.estimator,
        episode_service_factory=policy.episode_service_factory,
        episode_service_binding=policy.episode_service_binding,
        episode_service_inputs=policy.episode_service_inputs,
        annotation_child_roles=policy.annotation_child_roles,
        episode_record_receipts=policy.episode_record_receipts)


def configured_workflow(r, policy, tools):
    provider = ScriptedProvider([])
    return Workflow(r.store, tools, provider, r.directory, r.run_id,
        **workflow_options(r, policy))


def assert_no_execution(r, client):
    assert client.calls == []
    for table in ('runtime_episodes', 'runtime_actions', 'runtime_model_calls',
                  'runtime_observations', 'runtime_commission_intents'):
        assert r.store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    for table in ('orders', 'handoffs', 'samples'):
        assert r.jobs.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


def assert_policy_objects_unchanged(actual, base, supplied):
    # This compares the actual PolicyBindings returned by the original factory,
    # including every numerical/scientific object, rather than rebuilding scores.
    for field in fields(PolicyBindings):
        if field.name not in REPLACED_FIELDS:
            assert getattr(actual, field.name) is getattr(base, field.name)
    assert actual.project_task_credit is actual.project_scientific_child_credit
    for role in ('annotation', 'job_launch', *SPECIALIST_ROLES):
        path = ((role, 'configuration-only'),)
        controller = actual.controller_factory(path, 11)
        original = base.controller_factory(path, 11)
        assert controller.cost == original.cost == supplied['policy']['controller'][
            'cost_by_role'].get(role, supplied['policy']['controller']['cost'])
        assert controller.initial_credit == original.initial_credit == 11
        assert controller.settings.as_record() == original.settings.as_record()


@pytest.mark.parametrize('version', [1, 2])
def test_actual_factory_forwards_catalog_and_registry_to_real_setup_without_changing_policy(
        resources, monkeypatch, version):
    r, client = resources, FixtureClient()
    tools = ToolRegistry(r.store, clients=client)
    supplied = caller_parameters(client, version)
    expected = deepcopy(supplied)
    bases, setups, catalogs = [], [], []
    real_catalog = tools.catalog

    def observed_catalog(*args, **kwargs):
        value = real_catalog(*args, **kwargs)
        catalogs.append(value)
        return value

    def original_policy(value, *, episode_roles):
        assert value is supplied['policy'] and episode_roles == SPECIALIST_ROLES
        base = investigation_policy(value, episode_roles=episode_roles)
        bases.append(base)
        return base

    name = ('bind_assembled_services_with_public_search' if version == 2
            else 'bind_assembled_services')
    real_setup = getattr(assembled_case_policy, name)

    def observed_setup(store, **kwargs):
        application = real_setup(store, **kwargs)
        setups.append((store, kwargs, application))
        return application

    monkeypatch.setattr(assembled_case_policy, 'investigation_policy', original_policy)
    monkeypatch.setattr(assembled_case_policy, name, observed_setup)
    monkeypatch.setattr(tools, 'catalog', observed_catalog)
    if version == 1:
        def forbidden_api(*args, **kwargs):
            raise AssertionError('Native-only factory must not resolve API ports')
        monkeypatch.setattr(assembled_service_setup, 'bind_public_search_ports', forbidden_api)
        monkeypatch.setattr('gene_annotation_episode.episode_services.WorkflowServices.public_search_ports',
            forbidden_api)

    policy = create_policy(supplied)
    assert_policy_objects_unchanged(policy, bases[0], supplied)
    # The caller's later mutation must leave the factory's captured configuration
    # and its independently retained reporting definition unchanged.
    supplied['services']['handoff_unit'] = 99
    supplied['services']['tool_retrieval']['model']['model'] = 'altered-caller-input'
    workflow = configured_workflow(r, policy, tools)
    store, operands, application = setups[0]
    assert len(setups) == 1 and store is r.store
    assert operands['job_episodes'] is r.homology
    assert operands['resource_estimator'] is r.estimator
    assert operands['tool_catalog'] == catalogs[0] == tools.catalog()
    assert operands['tool_catalog'] is not catalogs[0]
    assert operands['handoff_unit'] == expected['services']['handoff_unit']
    assert operands['acquired_record_unit'] == expected['services']['acquired_record_unit']
    assert operands['tool_retrieval'] == expected['services']['tool_retrieval']
    library = ScientificToolLibrary(r.directory/'scientific-tool-library')
    assert library.catalog() == [dict(name=name, **entry)
        for name, entry in sorted(tools.catalog().items())]
    assert workflow.episode_bindings.as_record() == list(application.episode_binding_descriptors)
    assert workflow.project_credit is policy.project_task_credit
    assert workflow.project_child_credit is policy.project_scientific_child_credit
    assert workflow.project_annotation_score is policy.project_annotation_score
    assert workflow.controller_factory is policy.controller_factory
    assert workflow.native_timing_information is policy.native_timing_information
    assert policy.episode_service_inputs == INPUTS[version]
    assert workflow.episode_application_services_binding['version'] == (
        'episode_application_services_v3' if version == 2 else 'episode_application_services_v2')
    assert workflow.episode_application_services_binding['definition'] == expected['services']
    adapters = tuple(workflow.episode_bindings.for_role('launch').adapters.values())
    if version == 2:
        assert operands['tool_registry'] is tools
        assert operands['public_search_registry'] == expected['services']['public_search_registry']
        router = application.job_progress_provider
        ports = router.api.ports
        assert router.ports is ports
        assert ports.operations.store is r.store
        assert ports.operations.remote_searches is tools.remote_searches
        assert ports.operations.remote_searches.clients is client is tools.clients
        assert ports.result_publisher.tools is tools
        assert ports.result_publisher.operations is ports.operations
        api = next(adapter for adapter in adapters
            if adapter.as_record()['version'] == 'hmmer_service_resource_adapter_v1')
        assert api.ports.operations.remote_searches is tools.remote_searches
        assert api.ports.result_publisher.tools is tools
        assert api.ports.registry == ports.registry == expected['services']['public_search_registry']
        assert r.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
    else:
        assert 'tool_registry' not in operands and 'public_search_registry' not in operands
        assert type(application.job_progress_provider) is HomologyProgressProvider
        assert application.job_progress_provider.jobs is r.jobs
        assert len(adapters) == 1 and adapters[0].as_record()['version'] == 'homology_resource_adapter_v1'
        assert type(application.role_credit_bindings['launch']['project']) is ResourceOperationalCredit
        assert application.role_credit_bindings['launch']['definition'] == (
            application.role_credit_bindings['launch']['project'].as_record())
        assert r.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='public_search_registries'").fetchone() is None
    assert_no_execution(r, client)
    assert workflow.provider.contexts == []


def test_saved_v2_policy_reopens_original_source_factory_configuration_and_unsubmitted_order(
        resources, tmp_path):
    r, client = resources, FixtureClient()
    subject = r.store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs'][0]
    tools = ToolRegistry(r.store, clients=client)
    supplied = caller_parameters(client)
    expected = deepcopy(supplied)
    policy_source = tmp_path/'caller.py'
    policy_source.write_bytes(Path(assembled_case_policy.__file__).read_bytes())
    r.directory.mkdir()
    policy, saved = _load_policy(r.directory, policy_source, supplied, resume=False)
    marker = (r.directory/'policy-binding.json').read_bytes()
    snapshot = r.directory/saved['snapshot_file']
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == saved['source_sha256']
    descriptor = saved['episode_application_services']
    assert descriptor == {
        'version': 'episode_application_services_v3', 'inputs': 'actual_tool_registry_v1',
        'factory': f"fixed_gene_policy_{saved['source_sha256']}.create_policy.<locals>.setup",
        'definition': expected['services']}
    first = configured_workflow(r, policy, tools)
    ports = first.services.public_search_ports(expected['services']['public_search_registry'])
    scope = r.store.validate_scope({'subject_refs': [subject]})
    order = ports.operations.order(operation_key='caller-configuration-order', provider='hmmer',
        subject_ref=subject, query_fasta=f'>{subject}\nMKWAA\n', algorithm='phmmer',
        database='fixture', parameters={}, page_size=2, scope=scope)
    original = ports.operations.inspect(order['job_ref'])
    original_scope = ports.operations.open_scope(order['job_ref'])
    assert original['state'] == 'not_submitted' and original['remote_id'] is None
    assert original['submission_claim_refs'] == original['latest_operation_refs'] == []
    policy_source.write_text('raise AssertionError("Use the saved original source")\n')
    supplied['services']['public_search_registry']['client_binding_sha256'] = '0'*64
    supplied['policy']['controller']['cost'] = 91
    policy.episode_service_binding['public_search_registry']['resource_id'] = 'altered-reporting-copy'
    restored, replay = _load_policy(r.directory, None, None, resume=True)
    assert replay == saved and (r.directory/'policy-binding.json').read_bytes() == marker
    assert service_binding(restored.episode_service_factory, restored.episode_service_binding,
        inputs=restored.episode_service_inputs) == descriptor
    assert restored.episode_service_factory.__module__ == policy.episode_service_factory.__module__
    for field in ('task_credit_definition', 'scientific_child_credit_definition',
                  'annotation_score_definition', 'job_credit_definition',
                  'monitoring_credit_definition', 'controller_definition'):
        assert getattr(restored, field) == getattr(policy, field)
    assert restored.native_timing_information.as_record() == policy.native_timing_information.as_record()
    reopened = configured_workflow(r, restored, tools)
    assert reopened.episode_bindings.as_record() == first.episode_bindings.as_record()
    assert reopened.episode_job_progress_provider_binding == first.episode_job_progress_provider_binding
    recovered = reopened.services.public_search_ports(expected['services']['public_search_registry'])
    assert recovered.operations.inspect(order['job_ref']) == original
    assert recovered.operations.open_scope(order['job_ref']) == original_scope
    assert recovered.operations.remote_searches is tools.remote_searches
    assert recovered.result_publisher.tools is tools
    assert r.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 1
    assert_no_execution(r, client)


@pytest.mark.parametrize(('change', 'message'), [
    ('caller_source', 'resume_cannot_replace_policy_source'),
    ('caller_parameters', 'resume_cannot_replace_policy_parameters'),
    ('saved_source', 'recorded_policy_source_changed'),
    ('saved_services', 'restored_policy_definition_changed'),
])
def test_saved_v2_loader_rejects_replacement_or_corruption_without_invoking_setup(
        tmp_path, monkeypatch, change, message):
    client = FixtureClient()
    supplied = caller_parameters(client)
    caller = tmp_path/'caller.py'
    caller.write_bytes(Path(assembled_case_policy.__file__).read_bytes())
    directory = tmp_path/'saved'
    directory.mkdir()
    _, saved = _load_policy(directory, caller, supplied, resume=False)

    def forbidden_setup(*args, **kwargs):
        raise AssertionError('Policy reopening must not construct services or execute HTTP')

    monkeypatch.setattr(assembled_service_setup, 'bind_assembled_services_with_public_search',
        forbidden_setup)
    options = {}
    if change == 'caller_source':
        caller.write_text('raise AssertionError("Changed caller source")\n')
        options['policy_file'] = caller
    elif change == 'caller_parameters':
        options['parameters'] = deepcopy(supplied)
        options['parameters']['services']['handoff_unit'] += 1
    elif change == 'saved_source':
        with (directory/saved['snapshot_file']).open('a') as stream:
            stream.write('\n# altered saved source\n')
    else:
        changed = deepcopy(saved)
        changed['episode_application_services']['inputs'] = 'actual_tool_catalog_v1'
        (directory/'policy-binding.json').write_text(json.dumps(changed))
    before = (directory/'policy-binding.json').read_bytes()
    with pytest.raises(ValueError, match=message):
        _load_policy(directory, options.get('policy_file'), options.get('parameters'), resume=True)
    assert (directory/'policy-binding.json').read_bytes() == before
    assert client.calls == []


@pytest.mark.parametrize(('change', 'code'), [
    ('client_configuration', 'identity_conflict'),
    ('client_missing', 'unavailable_binding'),
    ('remote_store', 'identity_conflict'),
])
def test_reopened_v2_actual_binding_rejects_before_model_transport_or_http(
        resources, monkeypatch, change, code):
    r, client = resources, FixtureClient()
    r.store.create_problem(raw_sequence='MKWAA', molecule='protein')
    tools = ToolRegistry(r.store, clients=client)
    r.directory.mkdir()
    _load_policy(r.directory, Path(assembled_case_policy.__file__),
        caller_parameters(client), resume=False)
    restored, _ = _load_policy(r.directory, None, None, resume=True)
    if change == 'client_configuration':
        client.hmmer_fixture_binding = {**client.hmmer_fixture_binding,
            'transport_timeout_seconds': 21}
    elif change == 'client_missing':
        tools.remote_searches.clients = object()
    else:
        tools.remote_searches.store = object()
    transport_entries = []

    async def forbidden_transport(*args, **kwargs):
        transport_entries.append(True)
        raise AssertionError('Client binding rejection must precede transport')

    monkeypatch.setattr(ModelConnection, '__aenter__', forbidden_transport)
    monkeypatch.setattr(ModelConnection, 'complete', forbidden_transport)
    with pytest.raises(DurableExecutionError) as error:
        asyncio.run(run_workflow(r.store, tools, run_dir=r.directory/'attempt',
            **workflow_options(r, restored)))
    assert error.value.failure['code'] == code
    assert transport_entries == []
    assert_no_execution(r, client)
    assert r.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
