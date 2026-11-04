"""Actual opt-in caller/factory/reopen owners; no selected or remote work."""
from copy import deepcopy
from dataclasses import fields
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from method_loop.durable import DurableExecutionError

from gene_annotation_episode import api_planning_case_policy as caller, assembled_case_policy
from gene_annotation_episode.api_execution_planning import ApiExecutionPlanner
from gene_annotation_episode.api_timing_information import ApiReportedTimingFactReader
from gene_annotation_episode.api_timing_records import ApiTimingBinding
from gene_annotation_episode.assembled_service_setup import (
    bind_assembled_services_with_public_search_timing_planning_direct)
from gene_annotation_episode.case_execution import _load_policy
from gene_annotation_episode.direct_hmmer_timing import DIRECT_MODE, DirectHmmerTiming
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.hmmer_resource_adapter import HmmerServiceResourceAdapter
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.resource_service_setup import bind_public_search_ports, bind_resource_services
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.tools import ToolRegistry
from test_api_planning_case_policy import parameters
from test_hmmer_api_operations import FixtureClient
from test_resource_service_setup import forbidden, resources


def direct_parameters(tmp_path, *, client=None):
    value = parameters(tmp_path, client=client)
    value['services']['version'] = 'assembled_case_api_prechoice_direct_timing_v1'
    value['services']['ordinary_hmmer_timing'] = deepcopy(DIRECT_MODE)
    return value


@pytest.fixture
def bound(resources, tmp_path, monkeypatch):
    r = resources
    # No native availability probe may execute this configuration-only file.
    Path(r.jobs.config['executable']['path']).chmod(0o600)
    monkeypatch.setattr('subprocess.run', forbidden)
    problem = r.store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    client = FixtureClient()
    value = direct_parameters(tmp_path, client=client)
    value['policy']['operational']['registry_ref'] = r.jobs.config['registry_ref']
    value['policy']['scientific_progress']['initial_known_record_refs'] = problem['subject_refs']
    RunHistory(value['services']['api_timing']['history_path']).close()
    policy = caller.create_policy(value)
    tools = ToolRegistry(r.store, clients=client)
    return SimpleNamespace(r=r, value=value, policy=policy, tools=tools, client=client,
        baseline_records=r.store.db.execute('SELECT count(*) FROM records').fetchone()[0])


def setup(h, **changes):
    r = h.r
    return h.policy.episode_service_factory(r.store, **{
        'run_id': r.run_id, 'directory': r.directory, 'job_episodes': r.homology,
        'resource_estimator': h.policy.resource_estimator,
        'tool_catalog': h.tools.catalog(), 'tool_registry': h.tools, **changes})


def no_work(h):
    assert h.client.calls == []
    assert h.r.store.db.execute('SELECT count(*) FROM records').fetchone()[0] == h.baseline_records
    for table in ('orders', 'handoffs', 'samples'):
        assert h.r.jobs.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
    for table in ('provider_jobs', 'public_search_orders', 'public_search_operations',
            'public_search_publications', 'runtime_actions', 'runtime_model_calls', 'runtime_observations'):
        assert h.r.store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
    assert h.r.store.count('observation') == h.r.store.count('assessment') == 0
    with sqlite3.connect(h.value['services']['api_timing']['ledger_path']) as db:
        for table in ('api_timing_orders', 'api_timing_submission_intents',
                'api_timing_measurements', 'api_timing_export_dispositions'):
            assert db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0


def descriptors(application):
    return [deepcopy(item) for item in application.episode_binding_descriptors
        if item['binding_id'] != 'monitor']


def api_descriptor(saved):
    return next(item for item in saved if item['binding_id'] == 'resource_episodes')[
        'configuration']['resource_adapters'][1]


def compose(h, application, *, tools=None, saved=None, services=None):
    tools = h.tools if tools is None else tools
    services = WorkflowServices(SimpleNamespace(store=h.r.store, tools=tools, run_id=h.r.run_id)) if services is None else services
    return compose_episode_bindings(services, store=h.r.store,
        journal=Journal(h.r.store, h.r.run_id), execution_backend=None,
        descriptors=descriptors(application) if saved is None else saved,
        job_episodes=h.r.homology, resource_estimator=h.policy.resource_estimator,
        role_credit_bindings=application.role_credit_bindings, directory=h.r.directory)


def api_adapter(composition, resource):
    return next(adapter for binding in composition.bindings
        if binding.as_record()['binding_id'] == 'resource_episodes'
        for adapter in binding.adapters.values() if adapter.resource_id == resource)


def test_new_caller_preserves_all_original_operands_and_exact_base_projection(tmp_path, monkeypatch):
    value = direct_parameters(tmp_path)
    original = deepcopy(value)
    base_inputs, bases = [], []
    actual = assembled_case_policy.create_policy
    def capture(parameters):
        base_inputs.append(deepcopy(parameters))
        policy = actual(parameters)
        bases.append(policy)
        return policy
    monkeypatch.setattr(assembled_case_policy, 'create_policy', capture)
    policy = caller.create_policy(value)
    base, = bases
    for field in fields(type(policy)):
        if field.name not in {'resource_estimator', 'episode_service_factory',
                'episode_service_binding', 'episode_service_inputs'}:
            assert getattr(policy, field.name) is getattr(base, field.name)
    projected, = base_inputs
    assert projected['policy'] == original['policy']
    assert projected['services'] == {**{key: item for key, item in original['services'].items()
        if key not in {'ordinary_hmmer_timing', 'api_timing', 'api_execution_planning'}},
        'version': assembled_case_policy.API_VERSION}
    assert policy.episode_service_binding == original['services']
    assert policy.episode_service_inputs == 'actual_tool_registry_v1'
    assert policy.resource_estimator.as_record() == ResourceToolEstimator.with_reported_results().as_record()
    value['services']['ordinary_hmmer_timing']['tools'].clear()
    value['policy']['controller']['cost'] = 99
    assert policy.episode_service_binding == original['services']
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('change', ['missing', 'extra', 'tool_order', 'collect', 'page', 'key_version', 'old_version_extra', 'version_list'])
def test_direct_marker_is_closed_and_does_not_enable_old_callers(tmp_path, monkeypatch, change):
    value = direct_parameters(tmp_path)
    marker = value['services']['ordinary_hmmer_timing']
    if change == 'missing': del value['services']['ordinary_hmmer_timing']
    elif change == 'extra': marker['extra'] = True
    elif change == 'tool_order': marker['tools'].reverse()
    elif change in {'collect', 'page', 'key_version'}: marker[change] = 'unsupported'
    elif change == 'old_version_extra': value['services']['version'] = caller.VERSION
    else: value['services']['version'] = []
    monkeypatch.setattr(assembled_case_policy, 'create_policy', forbidden)
    with pytest.raises(ValueError, match='explicit_api_prechoice_services_configuration_required|unsupported_ordinary_hmmer_timing_binding'):
        caller.create_policy(value)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('name', ['handoff_unit', 'acquired_record_unit', 'monitoring_information_unit'])
@pytest.mark.parametrize('invalid', [True, 0, float('inf')], ids=['bool', 'zero', 'nonfinite'])
def test_new_caller_rejects_invalid_units_before_base_or_setup(tmp_path, monkeypatch, name, invalid):
    value = direct_parameters(tmp_path)
    value['services'][name] = invalid
    monkeypatch.setattr(assembled_case_policy, 'create_policy', forbidden)
    with pytest.raises(ValueError, match='explicit_positive_api_prechoice_service_units_required|finite_json_api_prechoice_parameters_required'):
        caller.create_policy(value)
    assert not list(tmp_path.iterdir())


def test_factory_and_v4_composition_use_one_actual_final_reader_and_all_owners(bound, monkeypatch):
    h = bound
    before_map, before_resources = deepcopy(h.tools.catalog()), deepcopy(h.tools.resource_binding())
    readers = []
    actual = ApiReportedTimingFactReader.__init__
    def count(self, *args, **kwargs):
        actual(self, *args, **kwargs)
        readers.append(self)
    monkeypatch.setattr(ApiReportedTimingFactReader, '__init__', count)
    application = setup(h)
    first = h.tools.api_direct_hmmer_timing
    assert type(first) is DirectHmmerTiming and len(readers) == 1
    assert first.planner is h.tools.api_execution_planner
    assert first.reader is readers[0]
    assert application.job_progress_provider.ports is first.planner.ports
    frozen = ScientificToolLibrary(h.r.directory/'scientific-tool-library')
    catalog = h.tools.catalog()
    for name in ('public.hmmer.search', 'public.hmmer.collect'):
        assert catalog[name]['configuration'] == {'ordinary_hmmer_timing': first.as_record()}
        assert catalog[name]['input_schema'] == before_map[name]['input_schema']
    assert catalog['public.hmmer.page'] == before_map['public.hmmer.page']
    assert h.tools.resource_binding() == before_resources
    assert api_descriptor(descriptors(application))['version'] == 'hmmer_service_resource_adapter_v4'
    composition = compose(h, application)
    final = h.tools.api_direct_hmmer_timing
    api = api_adapter(composition, first.planner.ports.registry['resource_id'])
    assert final is not first and final.as_record() == first.as_record()
    assert len(readers) == 2
    assert api.api_direct_timing is final
    assert api.api_execution_planning is final.planner is h.tools.api_execution_planner
    assert api.timing_reader is final.reader is composition.api_timing_reader is readers[-1]
    assert final.reader.ports is api.ports is final.planner.ports
    assert final.reader.ledger is api.timing is final.planner.timing
    assert final.planner.resource_estimator is h.policy.resource_estimator
    assert frozen.resolve(['execution.estimate', 'public.hmmer.search', 'public.hmmer.collect'], available_catalog=h.tools.catalog())
    no_work(h)


@pytest.mark.parametrize('field', ['configuration', 'poll_interval_seconds', 'implementation_sha256', 'reader', 'planner', 'extra'])
def test_saved_v4_descriptor_tampering_rejects_before_any_handle_attachment(bound, field):
    h = bound
    application = setup(h)
    fresh = ToolRegistry(h.r.store, clients=h.client)
    saved = descriptors(application)
    direct = api_descriptor(saved)['ordinary_hmmer_timing']
    if field == 'configuration': direct[field]['page'] = 'cached'
    elif field == 'poll_interval_seconds': direct[field] += 1
    elif field == 'implementation_sha256': direct[field] = '0'*64
    elif field == 'reader': direct[field]['ledger']['run_id'] = 'foreign'
    elif field == 'planner': direct[field]['preparation_sha256'] = '0'*64
    else: direct[field] = True
    with pytest.raises(DurableExecutionError, match='identity_conflict'):
        compose(h, application, tools=fresh, saved=saved)
    assert fresh.api_execution_planner is fresh.api_direct_hmmer_timing is None
    no_work(h)


def test_reopen_from_saved_v4_without_factory_reattaches_exact_supplied_handles(bound):
    h = bound
    application = setup(h)
    fresh = ToolRegistry(h.r.store, clients=h.client)
    composition = compose(h, application, tools=fresh)
    api = api_adapter(composition, h.value['services']['public_search_registry']['resource_id'])
    assert fresh.api_direct_hmmer_timing is api.api_direct_timing
    assert fresh.api_execution_planner is api.api_execution_planning
    assert fresh.api_direct_hmmer_timing.reader is composition.api_timing_reader
    assert fresh.api_direct_hmmer_timing.reader.ports is fresh.api_execution_planner.ports
    assert ScientificToolLibrary(h.r.directory/'scientific-tool-library').resolve(
        ['public.hmmer.search', 'public.hmmer.collect'], available_catalog=fresh.catalog())
    no_work(h)


@pytest.mark.parametrize('change', ['stale_map', 'client_pin', 'estimator', 'foreign_store', 'marker'])
def test_actual_new_factory_rejects_mismatched_inputs_before_freezing_or_acquisition(bound, tmp_path, change):
    h = bound
    changes = {}
    if change == 'stale_map':
        changes['tool_catalog'] = deepcopy(h.tools.catalog())
        del changes['tool_catalog']['state.query']
    elif change == 'client_pin':
        supplied = deepcopy(h.value)
        supplied['services']['public_search_registry']['client_binding_sha256'] = '0'*64
        h.policy = caller.create_policy(supplied)
    elif change == 'estimator': changes['resource_estimator'] = ResourceToolEstimator()
    elif change == 'marker':
        from test_assembled_service_setup import operands
        opts = {**operands(h.r), 'resource_estimator': h.policy.resource_estimator,
            'tool_registry': h.tools, 'tool_catalog': h.tools.catalog(),
            'public_search_registry': h.value['services']['public_search_registry'],
            'api_timing': h.value['services']['api_timing'],
            'ordinary_hmmer_timing': {**DIRECT_MODE, 'extra': True}}
        with pytest.raises(ValueError, match='unsupported_ordinary_hmmer_timing_binding'):
            bind_assembled_services_with_public_search_timing_planning_direct(h.r.store, **opts)
        assert not h.r.directory.exists() and h.client.calls == []
        return
    else:
        from gene_annotation_episode.state import Store
        with Store(tmp_path/'foreign-workspace') as foreign:
            changes['tool_registry'] = ToolRegistry(foreign, clients=h.client)
            changes['tool_catalog'] = changes['tool_registry'].catalog()
            with pytest.raises((DurableExecutionError, ValueError)):
                setup(h, **changes)
        assert h.tools.api_execution_planner is h.tools.api_direct_hmmer_timing is None
        assert not h.r.directory.exists() and h.client.calls == []
        return
    with pytest.raises((DurableExecutionError, ValueError)):
        setup(h, **changes)
    assert h.tools.api_execution_planner is h.tools.api_direct_hmmer_timing is None
    assert not h.r.directory.exists() and h.client.calls == []


@pytest.mark.parametrize('change', ['planner', 'reader_ports', 'no_planner', 'not_typed'])
def test_adapter_rejects_descriptor_equal_but_different_owner_objects(bound, change):
    h = bound
    setup(h)
    direct = h.tools.api_direct_hmmer_timing
    planner = direct.planner
    if change == 'planner':
        planner = ApiExecutionPlanner(h.r.store, run_id=h.r.run_id, ports=planner.ports,
            timing=planner.timing, resource_estimator=h.policy.resource_estimator)
    elif change == 'no_planner': planner = None
    elif change == 'not_typed': direct = SimpleNamespace(planner=planner, reader=direct.reader)
    else:
        other_ports = bind_public_search_ports(h.r.store, h.tools,
            registry=planner.ports.registry, timing=planner.timing)
        # Mutating only this fixture's owner object establishes an actual mismatch.
        direct.reader.ports = other_ports
    with pytest.raises(ValueError, match='api_direct_timing_adapter_binding_mismatch'):
        HmmerServiceResourceAdapter(None, h.r.store, Journal(h.r.store, h.r.run_id),
            ports=h.tools.api_execution_planner.ports, timing=h.tools.api_execution_planner.timing,
            resource_estimator=h.policy.resource_estimator, api_execution_planning=planner,
            api_direct_timing=direct)
    no_work(h)


def test_direct_binding_requires_ports_and_v1_caller_keeps_v3(bound):
    h = bound
    with pytest.raises(ValueError, match='api_direct_timing_requires_public_search_ports'):
        bind_resource_services(h.r.store, run_id=h.r.run_id, directory=h.r.directory,
            job_episodes=h.r.homology, resource_estimator=h.policy.resource_estimator,
            handoff_unit=1, acquired_record_unit=1, api_direct_timing=object())
    old = deepcopy(h.value)
    old['services']['version'] = caller.VERSION
    del old['services']['ordinary_hmmer_timing']
    h.policy = caller.create_policy(old)
    before = deepcopy(h.tools.catalog())
    application = setup(h)
    assert h.tools.api_direct_hmmer_timing is None
    saved = api_descriptor(descriptors(application))
    assert saved['version'] == 'hmmer_service_resource_adapter_v3'
    assert 'ordinary_hmmer_timing' not in saved
    for tool in ('public.hmmer.search', 'public.hmmer.collect', 'public.hmmer.page'):
        assert h.tools.catalog()[tool] == before[tool]
    no_work(h)


def test_actual_snapshot_loader_retains_new_caller_marker_and_full_definition(tmp_path):
    value = direct_parameters(tmp_path)
    directory = tmp_path/'snapshot'
    directory.mkdir()
    policy, original = _load_policy(directory, Path(caller.__file__), value, resume=False)
    assert original['parameters'] == value
    assert original['episode_application_services']['definition'] == value['services']
    assert original['episode_application_services']['inputs'] == 'actual_tool_registry_v1'
    restored, replay = _load_policy(directory, None, None, resume=True)
    assert replay == original
    assert restored.episode_service_binding == policy.episode_service_binding == value['services']
    assert restored.resource_estimator.as_record() == policy.resource_estimator.as_record()
    assert restored.controller_definition == policy.controller_definition
    assert not list(tmp_path.glob('*.sqlite'))
