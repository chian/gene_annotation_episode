"""Explicit setup/role ports over real Store bindings, without scientific work.

The current published scientific catalog has A0/P19. These tests exercise its
setup and root edges only; they invent no first-slot option. Callables and units
in the fixtures are engineering operands, never production defaults.
"""
import asyncio
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from method_loop.durable import DurableExecutionError
from gene_annotation_episode.case_execution import (
    _load_policy, prepare_case_run, prepared_case_bindings)
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices, service_binding
from gene_annotation_episode.episode_monitoring import MonitorEpisodes, read_progress
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.independent_execution import _check_bindings
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.resource_episodes import HomologyResourceAdapter, LAUNCH_VERSION
from gene_annotation_episode.resource_service_setup import bind_resource_services
from gene_annotation_episode.runtime import Workflow, WorkflowError, run_workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_case_execution import PARAMETERS, POLICY, prepared
from test_homology_episode_runtime import Provider
from test_resource_service_setup import resources
from test_runtime import obj


MODE = 'actual_tool_catalog_v1'
ROLES = ('scientific_process', 'literature', 'launch', 'monitor', 'results')
PUBLICATION = Path(__file__).resolve().parents[1]/'research/slotted_process_library/publications/2026-10-21-001'


def forbidden(*args, **kwargs):
    raise AssertionError('No selected work, numerical observation or transport is allowed')


def zero(*args, **kwargs):
    return 0.


def test_service_input_protocol_keeps_legacy_record_and_requires_explicit_mode():
    expected = {'version': 'episode_application_services_v1',
        'factory': __name__+'.forbidden', 'definition': {'fixture': True}}
    assert service_binding(forbidden, {'fixture': True}) == expected
    assert service_binding(None, None) is None
    assert service_binding(forbidden, {'fixture': True}, inputs=MODE) == {
        **expected, 'version': 'episode_application_services_v2', 'inputs': MODE}
    for value in ('unknown', False, [], {}):
        with pytest.raises(ValueError, match='unsupported_episode_service_inputs'):
            service_binding(forbidden, {'fixture': True}, inputs=value)
    with pytest.raises(ValueError, match='requires_factory'):
        service_binding(None, None, inputs=MODE)


@pytest.mark.parametrize('mode', [None, MODE])
def test_factory_receives_the_same_actual_map_only_in_explicit_mode(tmp_path, mode):
    calls = []
    with Store(tmp_path/'workspace') as store:
        tools = ToolRegistry(store)
        original = tools.catalog()

        def setup(actual_store, **kwargs):
            assert actual_store is store
            calls.append(kwargs)
            assert set(kwargs) == {'run_id', 'directory', 'job_episodes', 'resource_estimator'} | (
                {'tool_catalog'} if mode else set())
            if mode:
                assert kwargs['tool_catalog'] == original
                assert kwargs['tool_catalog'] is not original
                kwargs['tool_catalog']['state.query']['description'] = 'changed borrowed JSON copy'
            return EpisodeApplicationServices([], {})

        Workflow(store, tools, object(), tmp_path/'run', 'port-fixture', forbidden, forbidden,
            episode_service_factory=setup, episode_service_binding={'fixture': True},
            episode_service_inputs=mode)
        assert len(calls) == 1 and tools.catalog() == original
        for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


@pytest.mark.parametrize('invalid', ['nonstring_key', 'record_object', 'nonfinite_value'])
def test_actual_catalog_rejects_unsupported_json_before_setup_publication(tmp_path, monkeypatch, invalid):
    class RecordObject:
        def as_record(self):
            return {'coerced': True}

    catalog = {'fixture.operation': {'input_schema': obj({}), 'description': 'Actual fixture contract'}}
    if invalid == 'nonstring_key':
        catalog = {7: catalog['fixture.operation']}
    else:
        catalog['fixture.operation']['configuration'] = (
            RecordObject() if invalid == 'record_object' else float('nan'))
    entered, published = [], tmp_path/'factory-publication.json'

    def setup(*args, **kwargs):
        entered.append(kwargs)
        published.write_text('This setup body must never run')
        return EpisodeApplicationServices([], {})

    with Store(tmp_path/'workspace') as store:
        tools = ToolRegistry(store)
        monkeypatch.setattr(tools, 'catalog', lambda: catalog)
        with pytest.raises((ValueError, TypeError)):
            Workflow(store, tools, object(), tmp_path/'run', 'invalid-catalog-fixture',
                forbidden, forbidden, episode_service_factory=setup,
                episode_service_binding={'fixture': True}, episode_service_inputs=MODE)
        assert entered == [] and not published.exists()
        for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


def configured_workflow(r, monkeypatch, *, roles=ROLES):
    r.store.create_problem(raw_sequence='MKK', molecule='protein', role='gene')
    tools = ToolRegistry(r.store)
    scope = {'subject_refs': r.store.problem()['subject_refs']}
    received = []

    def capability(adapter):
        return {'resource_id': adapter.resource_id, 'kind': 'local', 'availability': 'available',
            'observed_at': '2026-10-21T00:00:00+00:00',
            'provenance_refs': [r.jobs.config['registry_ref']], 'knowledge_entry_ids': [],
            'tool_names': [item['name'] for item in r.homology.catalog(
                SimpleNamespace(path=(('job_launch', 'fixture'),)))]}

    monkeypatch.setattr(HomologyResourceAdapter, 'capability', capability)

    def setup(store, *, run_id, directory, job_episodes, resource_estimator, tool_catalog):
        received.append(tool_catalog)
        scientific = prepare_scientific_binding(run_directory=directory,
            source_directory=PUBLICATION, tool_catalog=tool_catalog, child_roles=ROLES)
        resource = bind_resource_services(store, run_id=run_id, directory=directory,
            job_episodes=job_episodes, resource_estimator=resource_estimator,
            handoff_unit=2.75, acquired_record_unit=.125)
        information = ProgressInformationCredit(SimpleNamespace(
            read_progress=partial(read_progress, store, run_id)), information_unit=.25)
        return EpisodeApplicationServices((scientific, LiteratureEpisodes(None).as_record(),
            *resource.episode_binding_descriptors, MonitorEpisodes(None).as_record()),
            {**resource.role_credit_bindings,
                'monitor': {'definition': information.as_record(), 'project': information}})

    workflow = Workflow(r.store, tools, object(), r.directory, r.run_id, forbidden, zero,
        job_episodes=r.homology, resource_estimator=r.estimator,
        episode_service_factory=setup, episode_service_binding={'fixture': True},
        episode_service_inputs=MODE, annotation_child_roles=roles,
        episode_record_receipts=True, initial_known_record_refs=[])
    assert received == [tools.catalog()]
    library = ScientificProcessLibrary(r.directory/'scientific-process-library')
    assert len(library.search(slot='thought_pattern', query='', offset=0, limit=100)['entries']) == 19
    assert library.search(slot='annotation_distinction', query='', offset=0, limit=100)['entries'] == []
    root = workflow.build('annotation', 'root', 'Engineering root-role boundary', scope)
    return workflow, root, scope


def test_explicit_five_roles_match_tree_schema_and_job_context(resources, monkeypatch):
    workflow, root, _ = configured_workflow(resources, monkeypatch)
    assert tuple(grain.name for grain in workflow.tree.allowed_children('annotation')) == ROLES
    assert workflow.declared_child_roles('scientific_process') == ROLES
    assert workflow.declared_child_roles('launch') == ('launch_api', 'launch_local', 'launch_hpc')
    assert workflow.declared_child_roles('monitor') == ('monitor',)
    assert workflow.declared_child_roles('literature') == ('literature_strategy',)
    choices = workflow.action_schema(root.source)['properties']['selection']['anyOf']
    child_choices = [node['properties'] for node in choices
        if node['properties']['kind'].get('const') in {'child', 'job_child', 'episode_child'}]
    assert [node['role']['const'] for node in child_choices] == list(ROLES)
    assert all(node['kind']['const'] == 'episode_child' for node in child_choices)
    assert workflow.job_episode_options(root.source) is None
    assert resources.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0


@pytest.mark.parametrize('kind,role', [('job_child', 'job_launch'), ('job_child', 'job_monitor'),
    ('episode_child', 'launch_local'), ('child', 'improvement')])
def test_direct_selected_rejects_outside_root_roles_before_any_side_effect(resources, monkeypatch, kind, role):
    workflow, root, _ = configured_workflow(resources, monkeypatch)
    monkeypatch.setattr(resources.jobs, 'order', forbidden)
    monkeypatch.setattr(workflow, 'build', forbidden)
    monkeypatch.setattr(workflow, 'source_credit_view', forbidden)
    before = resources.store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0]
    with pytest.raises(ValueError, match='child_role_not_available_to_parent'):
        workflow.selected(root.source, {'kind': kind, 'role': role}, 0)
    assert resources.store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == before
    for table in ('runtime_actions', 'runtime_commission_intents', 'runtime_observations'):
        assert resources.store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


def test_direct_commission_and_dispatch_reject_excluded_role_before_intent_or_transport(resources, monkeypatch):
    workflow, root, _ = configured_workflow(resources, monkeypatch)
    monkeypatch.setattr(workflow.commissions, 'select', forbidden)
    monkeypatch.setattr(workflow.commissions, 'dispatch', forbidden)
    fake_child = SimpleNamespace(source=SimpleNamespace(path=(('job_launch', 'excluded'),)))
    with pytest.raises(ValueError, match='child_role_not_available_to_parent'):
        workflow.commission_child(root.source, fake_child, {'kind': 'job_child', 'role': 'job_launch'}, 0)
    with pytest.raises(ValueError, match='child_role_not_available_to_parent'):
        workflow.dispatch_commission(root.source, 0, {'child': {'role': 'launch_local'}})
    assert resources.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    assert resources.store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0] == 0


def test_dispatch_compares_the_actual_saved_intent_before_transport(resources, monkeypatch):
    workflow, root, _ = configured_workflow(resources, monkeypatch)
    original = {'run_id': workflow.run_id, 'handle': 'fixture-dispatch-handle',
        'parent': {'episode_id': root.source.episode_id, 'path': [list(part) for part in root.source.path]},
        'child': {'role': 'job_launch'}}
    # A caller's substituted metadata must not bless a different saved intent.
    with resources.store.transaction():
        resources.store.db.execute('INSERT INTO runtime_commission_intents VALUES(?,?,?,?,?,?,?,?,?)',
            (workflow.run_id, root.source.episode_id, 0, original['handle'], 'fixture-op',
                'fixture-digest', json.dumps(original), '{}', '2026-10-21T00:00:00+00:00'))
    monkeypatch.setattr(workflow.commissions, 'dispatch', forbidden)
    changed = {**original, 'child': {'role': 'launch'}}
    with pytest.raises(ValueError, match='commission_intent_identity_mismatch'):
        workflow.dispatch_commission(root.source, 0, changed)


def child_selection(role, assignment, scope):
    return {'kind': 'episode_child', 'role': role, 'assignment': assignment,
        'goal': 'Engineering investigation; no native execution is selected', 'scope': scope,
        'purpose': 'Return the original bounded fixture state',
        'schema_json': json.dumps(obj({'fixture_state': {'type': 'string', 'enum': ['unresolved']}})),
        'initial_report_json': '{"fixture_state":"unresolved"}'}


def test_selected_resource_branch_preserves_parent_work_and_orders_only_under_launch(resources, monkeypatch):
    workflow, root, scope = configured_workflow(resources, monkeypatch)
    query = scope['subject_refs'][0]
    assignment = {'version': LAUNCH_VERSION, 'job_request': {'query_ref': query, 'cpu': 1},
        'immutable_input_versions': [], 'constraints': {'cpu': 1}, 'resource_selection': None,
        'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    launch = workflow.selected(root.source, child_selection('launch', assignment, scope), 0).child
    assert resources.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    assert workflow.available_child_roles(launch.source) == ('launch_local',)
    adapter, = workflow.specialist(launch.source).adapters.values()
    local_selection = child_selection('launch_local',
        {**assignment, 'resource_selection': adapter._selection(1)}, scope)
    local = workflow.selected(launch.source, local_selection, 0).child
    actual = local.request.message.as_record()['episode_assignment']
    assert actual['job_request'] == assignment['job_request']
    assert actual['constraints'] == assignment['constraints']
    assert actual['adapter_assignment']['query_ref'] == query
    assert actual['adapter_assignment']['cpu'] == 1
    assert resources.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    assert resources.jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    assert resources.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    # A selected commission's type edge survives later capability changes.
    binding = workflow.specialist(launch.source)
    monkeypatch.setattr(binding, 'allowed_children', forbidden)
    workflow.validate_child_choice(launch.source, 'launch_local', original=True)


def test_absent_role_marker_preserves_legacy_flat_alternatives(resources, monkeypatch):
    workflow, root, _ = configured_workflow(resources, monkeypatch, roles=None)
    expected = (*resources.homology.roles, *workflow.episode_bindings.entry_roles)
    assert tuple(grain.name for grain in workflow.tree.allowed_children('annotation')) == expected
    choices = workflow.action_schema(root.source)['properties']['selection']['anyOf']
    flat = [node['properties']['role']['const'] for node in choices
        if node['properties']['kind'].get('const') == 'job_child']
    assert flat == ['job_launch', 'job_launch', 'job_monitor', 'job_results']
    assert workflow.job_episode_options(root.source) == resources.homology.describe()


@pytest.mark.parametrize('roles', [('launch_local',), ('unknown',), ('literature_strategy',)])
def test_nested_only_or_unknown_root_entry_is_rejected_during_assembly(resources, monkeypatch, roles):
    with pytest.raises(ValueError, match='annotation_child_role_not_an_entry_role'):
        configured_workflow(resources, monkeypatch, roles=roles)
    assert resources.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    assert resources.store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 0


PORT_POLICY = '''
from dataclasses import replace
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
_original_create_policy = create_policy
def setup(store, *, run_id, directory, job_episodes, resource_estimator, tool_catalog):
    raise AssertionError('Policy loading must not call setup')
def create_policy(parameters):
    return replace(_original_create_policy(parameters),
        episode_service_factory=setup, episode_service_binding={'fixture': 'explicit_ports'},
        episode_service_inputs='actual_tool_catalog_v1', annotation_child_roles=())
'''


def test_case_policy_pins_new_mode_and_empty_roles_without_executing_setup(tmp_path):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    policy_file.write_text(POLICY+PORT_POLICY)
    directory = tmp_path/'run'
    prepare_case_run(case, directory, configuration)
    policy, recorded = _load_policy(directory, policy_file, PARAMETERS, resume=False)
    assert recorded['annotation_child_roles'] == []
    assert recorded['episode_application_services']['version'] == 'episode_application_services_v2'
    assert recorded['episode_application_services']['inputs'] == MODE
    with Store(case/'workspace') as store, prepared_case_bindings(store, directory) as (_, options):
        assert options['episode_service_inputs'] == MODE
        assert options['annotation_child_roles'] == ()
        assert options['episode_service_binding'] == policy.episode_service_binding
        assert options['job_episodes'].jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='runtime_runs'").fetchone() is None


class BeforeRoot(Exception):
    pass


def test_run_persists_explicit_roles_and_rejects_changed_ports_before_provider_construction(tmp_path, monkeypatch):
    calls = []

    def setup(store, **kwargs):
        calls.append(kwargs)
        return EpisodeApplicationServices([], {})

    with Store(tmp_path/'workspace') as store:
        store.create_problem(raw_sequence='MKK', molecule='protein')
        tools = ToolRegistry(store)
        options = dict(episode_service_factory=setup, episode_service_binding={'fixture': True},
            episode_service_inputs=MODE, annotation_child_roles=(), run_dir=tmp_path/'run')
        with monkeypatch.context() as patched:
            patched.setattr(Workflow, 'build', lambda *a, **k: (_ for _ in ()).throw(BeforeRoot()))
            with pytest.raises(BeforeRoot):
                asyncio.run(run_workflow(store, tools, provider=Provider([]), **options))
        saved = json.loads((tmp_path/'run'/'run.json').read_text())
        assert saved['annotation_child_roles'] == []
        assert saved['episode_application_services']['inputs'] == MODE
        assert calls[0]['tool_catalog'] == tools.catalog()
        monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection', forbidden)
        for changed, message in [({'annotation_child_roles': None}, 'original_annotation_child_roles'),
                ({'annotation_child_roles': ('literature',)}, 'original_annotation_child_roles'),
                ({'episode_service_inputs': None}, 'original_episode_application_services')]:
            with pytest.raises(WorkflowError, match=message):
                asyncio.run(run_workflow(store, tools, resume=True, **{**options, **changed}))
        assert len(calls) == 1
        assert json.loads((tmp_path/'run'/'run.json').read_text()) == saved


def test_worker_rejects_changed_ports_before_any_executable_binding_lookup():
    setup = lambda **kwargs: None
    definition = {'fixture': True}
    options = {'episode_service_factory': setup, 'episode_service_binding': definition,
        'episode_service_inputs': MODE, 'annotation_child_roles': ROLES}
    settings = {'episode_application_services': service_binding(setup, definition, inputs=MODE),
        'annotation_child_roles': list(ROLES)}
    for changed, affected in [({'episode_service_inputs': None}, 'episode_application_services'),
            ({'annotation_child_roles': ('literature',)}, 'annotation_child_roles'),
            ({'annotation_child_roles': None}, 'annotation_child_roles')]:
        with pytest.raises(DurableExecutionError) as error:
            _check_bindings({**options, **changed}, settings)
        assert error.value.failure['code'] == 'identity_conflict'
        assert error.value.failure['affected_refs'] == [affected]
