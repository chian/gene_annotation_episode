"""Saved descriptor composition with real storage and caller-owned fixtures.

No model, transport, scientific investigation or native job executes here.
Capability observations and credit definitions are explicit test fixtures.
Detached specialist execution is the common host integration's responsibility.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from method_loop import Episode
from method_loop.durable import DurableExecutionError, DurableExecutionStore, canonical

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import (
    EpisodeComposition, compose_episode_bindings, scientific_binding_compatible,
)
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_monitoring import MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, digest
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.resource_episodes import HomologyResourceAdapter, ResourceEpisodes, ROLES
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.state import Store


def forbidden(*args, **kwargs):
    raise AssertionError('composition must not execute work')


def test_one_literature_owner_selects_native_axis_capabilities_and_reconstructs(resources, monkeypatch):
    owner = LiteratureEpisodes(resources.services, axis_scoped_profiles=True)
    saved = owner.as_record()
    reopened = compose(resources, [saved]).bindings[0]
    assert type(reopened) is LiteratureEpisodes
    assert reopened.as_record() == saved
    a105, a108 = object(), object()
    monkeypatch.setattr(reopened, '_assay_grading_repository', lambda: a105)
    monkeypatch.setattr(reopened, '_a108_grading_repository', lambda: a108)
    for axis, enabled in [('A105', 'assay_grading_population'),
                          ('A106', 'a106_intervention'), ('A108', 'a108_context_evidence')]:
        context = SimpleNamespace(role='scientific_process',
            assignment={'selection': {'evidence_axis': {'option_id': axis}}})
        for option in ('assay_grading_population', 'a106_intervention', 'a108_context_evidence'):
            assert reopened._enabled(option, context) is (option == enabled)
        grading = reopened._required_grading_repository(context)
        assert grading is {'A105': a105, 'A106': None, 'A108': a108}[axis]
        from method_loop.identities import EpisodeRef
        import json
        path = (('annotation', 'root'), ('scientific_process', axis))
        resources.journal.save('runtime_episodes', {
            'episode_id': EpisodeRef(resources.journal.run_id, path).episode_id,
            'path': json.dumps(path), 'request': json.dumps({'message': {'episode_assignment':
                context.assignment}}), 'initial_credit': 0., 'state': 'active'})
        descendant = SimpleNamespace(role='literature', run_id=resources.journal.run_id,
            path=(*path, ('literature', 'read')), assignment={})
        assert reopened._required_grading_repository(descendant) is grading
        assert ('wait' in reopened.permitted_common_actions(descendant)) is (axis == 'A106')
        schema = reopened.child_assignment_schema(context, 'literature')
        from gene_annotation_episode.literature_a105_aggregation_storage import REQUESTED as A105_REQUESTED
        from gene_annotation_episode.literature_a106_subscore import REQUESTED as A106_REQUESTED
        assert (A105_REQUESTED in schema['properties']) is (axis == 'A105')
        assert (A106_REQUESTED in schema['properties']) is (axis == 'A106')


@pytest.fixture
def resources(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        journal = Journal(store, 'composition-fixture')
        backend = DurableExecutionStore(tmp_path / 'executions')
        executable = tmp_path / 'unexecuted-program'
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o700)
        database = tmp_path / 'unsearched.faa'
        database.write_text('>fixture\nMKWAA\n')
        policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3)
        jobs = HomologyJobs.create(tmp_path / 'jobs',
            executable=FileAsset(executable, digest(executable)),
            reference_database=FileAsset(database, digest(database)), policy=policy, max_cpu=2)
        try:
            homology = HomologyEpisodes(jobs, parser_policy=policy,
                credit_projector=forbidden, credit_binding={'kind': 'test_operational_only'},
                monitoring_projector=forbidden, monitoring_binding={'kind': 'test_monitoring_only'})
            host = SimpleNamespace(store=store, run_id=journal.run_id,
                role_credit_projectors={}, resource_capabilities=(), progress_provider=None)
            yield SimpleNamespace(store=store, journal=journal, backend=backend,
                jobs=jobs, homology=homology, services=WorkflowServices(host), host=host,
                estimator=ResourceToolEstimator(), tmp_path=tmp_path)
        finally:
            jobs.close()


def descriptors(resources):
    adapter = HomologyResourceAdapter(resources.homology, resources.store,
                                      resources.journal, resources.estimator)
    return [LiteratureEpisodes(resources.services, outcome_page_size=3).as_record(),
        MonitorEpisodes(resources.services, outcome_page_size=5).as_record(),
        ResourceEpisodes(resources.services, resource_adapters=[adapter]).as_record()]


def role_bindings(*roles):
    return {role: {'definition': {'version': 'fixture_credit_v1', 'role': role,
        'unit': {'meaning': ['caller-selected test unit'], 'amount': 7}},
        'project': forbidden} for role in roles}


def compose(resources, saved, **kwargs):
    options = dict(store=resources.store, journal=resources.journal,
        execution_backend=resources.backend, descriptors=saved,
        job_episodes=resources.homology, resource_estimator=resources.estimator,
        role_credit_bindings=role_bindings('monitor', *ROLES))
    options.update(kwargs)
    return compose_episode_bindings(resources.services, **options)


def capability(adapter, *, availability='unknown'):
    return {'resource_id': adapter.resource_id, 'kind': 'local',
        'availability': availability, 'observed_at': '2026-10-21T00:00:00+00:00',
        'provenance_refs': [adapter.homology.jobs.config['registry_ref']],
        'knowledge_entry_ids': [], 'tool_names': ['homology.environment']}


def assert_failure(error, code, reference):
    assert error.value.failure == {'code': code, 'affected_refs': [reference],
                                   'diagnostic_ref': None, 'partial_record_refs': []}


def test_saved_specialists_reopen_exactly_against_actual_resources(resources, monkeypatch):
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', capability)
    saved = descriptors(resources)
    definitions = role_bindings('monitor', *ROLES, 'caller_extra_role')
    result = compose(resources, saved, role_credit_bindings=definitions)
    assert isinstance(result, EpisodeComposition)
    assert [binding.as_record() for binding in result.bindings] == saved
    assert result.bindings[0].outcome_page_size == 3
    assert result.bindings[1].outcome_page_size == 5
    adapter = next(iter(result.bindings[2].adapters.values()))
    assert adapter.homology is resources.homology
    assert adapter.store is resources.store and adapter.journal is resources.journal
    assert adapter.resource_estimator is resources.estimator
    assert result.progress_provider.store is resources.store
    assert result.progress_provider.durable_store is resources.backend
    assert result.progress_provider.run_id == resources.journal.run_id
    assert plain(result.role_credit_definitions) == {
        role: pair['definition'] for role, pair in definitions.items()}
    assert all(result.role_credit_projectors[role] is pair['project']
               for role, pair in definitions.items())
    with pytest.raises(FrozenInstanceError):
        result.bindings = ()
    with pytest.raises(TypeError):
        result.role_credit_projectors['monitor'] = forbidden
    with pytest.raises(TypeError):
        result.role_credit_definitions['monitor']['unit']['amount'] = 999
    definitions['monitor']['definition']['unit']['amount'] = 999
    saved[0]['configuration']['outcome_page_size'] = 999
    assert result.role_credit_definitions['monitor']['unit']['amount'] == 7
    assert result.bindings[0].as_record()['configuration']['outcome_page_size'] == 3


@pytest.mark.parametrize('field,value', [
    ('implementation_sha256', '0' * 64), ('version', 'different_version'),
    ('unexpected_field', True)])
def test_changed_known_descriptor_is_rejected_before_progress_or_capability_reads(
        resources, monkeypatch, field, value):
    saved = descriptors(resources)
    saved[-1][field] = value
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', forbidden)
    monkeypatch.setattr(ProgressProvider, '__init__', forbidden)
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, saved)
    assert_failure(error, 'identity_conflict', 'resource_episodes')


@pytest.mark.parametrize('field', ['resource_id', 'homology', 'resource_estimator'])
def test_changed_adapter_or_caller_resource_binding_is_rejected(resources, monkeypatch, field):
    saved = descriptors(resources)
    adapter = saved[-1]['configuration']['resource_adapters'][0]
    reference = adapter['resource_id']
    if field == 'resource_id':
        adapter[field] = reference = 'different-local-resource'
    elif field == 'homology':
        adapter[field]['credit_binding'] = {'kind': 'changed_caller_binding'}
    else:
        adapter[field] = None
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', forbidden)
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, saved)
    assert_failure(error, 'identity_conflict', reference)


@pytest.mark.parametrize('absent_role', ['monitor', *ROLES])
def test_non_scientific_roles_require_each_explicit_caller_projector(
        resources, monkeypatch, absent_role):
    saved = descriptors(resources)
    bindings = role_bindings('monitor', *ROLES)
    del bindings[absent_role]
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', forbidden)
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, saved, role_credit_bindings=bindings)
    assert_failure(error, 'unavailable_binding', absent_role)


@pytest.mark.parametrize('changed', ['project', 'definition', 'nonfinite', 'extra'])
def test_invalid_explicit_credit_bindings_are_structured_failures(resources, changed):
    bindings = role_bindings('monitor')
    if changed == 'project':
        bindings['monitor']['project'] = 'cannot-reconstruct-a-callable'
    elif changed == 'definition':
        bindings['monitor']['definition'] = []
    elif changed == 'nonfinite':
        bindings['monitor']['definition']['unit']['amount'] = float('nan')
    else:
        bindings['monitor']['invented_weight'] = 1
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, [], role_credit_bindings=bindings)
    assert_failure(error, 'unavailable_binding', 'monitor')


def test_unknown_factories_and_absent_actual_bindings_are_not_inferred(resources):
    unknown = {'version': 'caller_binding_v1', 'binding_id': 'custom',
               'configuration': {}, 'implementation_sha256': '0' * 64}
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, [unknown])
    assert_failure(error, 'unavailable_binding', 'custom')
    saved = descriptors(resources)
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, [saved[1]], execution_backend=None)
    assert_failure(error, 'unavailable_binding', 'execution_backend')
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, [saved[2]], job_episodes=None)
    assert_failure(error, 'unavailable_binding',
                   saved[2]['configuration']['resource_adapters'][0]['resource_id'])
    saved[2]['configuration']['resource_adapters'][0]['version'] = 'custom_api_adapter_v1'
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, [saved[2]])
    assert_failure(error, 'unavailable_binding', 'resource_episodes')


def test_composition_starts_no_model_transport_job_or_science(resources, monkeypatch):
    saved = descriptors(resources)
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', capability)
    for owner, names in [(Episode, ('run_async',)),
            (ModelConnection, ('__init__', '__aenter__')),
            (DurableExecutionStore, ('commission', 'start', 'record_progress')),
            (HomologyJobs, ('order', 'configure', 'stage', 'submit', 'sample', 'check_handoff')),
            (HomologyEpisodes, ('assign', 'recover_statistics', 'execute')),
            (Store, ('commit_reasoning',))]:
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    records = list(resources.store.db.execute('SELECT * FROM records ORDER BY id'))
    result = compose(resources, saved)
    assert len(result.bindings) == 3
    assert list(resources.store.db.execute('SELECT * FROM records ORDER BY id')) == records
    for table in ('runtime_episodes', 'runtime_model_calls', 'runtime_actions',
                  'runtime_observations', 'runtime_forms', 'runtime_progress_receipts'):
        assert resources.store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    for table in ('orders', 'samples', 'handoffs'):
        assert resources.jobs.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    assert not (resources.tmp_path / 'providers').exists()


def test_projectors_and_actual_capabilities_reach_existing_service_ports(resources, monkeypatch):
    resources.store.create_problem(raw_sequence='MKWAA', molecule='protein')
    seen = []
    selected = {'known_progress_refs': ['actually-received-fixture'],
                'initial_progress_refs': ['original-baseline-fixture']}
    bindings = role_bindings('monitor', *ROLES)
    for role in bindings:
        def project(context, receiver_selection, *, role=role):
            seen.append((role, context, receiver_selection))
            return {'credit': 7, 'definition': bindings[role]['definition']}
        bindings[role]['project'] = project
    monkeypatch.setattr(HomologyResourceAdapter, 'capability',
                        lambda adapter: capability(adapter, availability='authentication_required'))
    result = compose(resources, descriptors(resources), role_credit_bindings=bindings)
    resources.host.role_credit_projectors = result.role_credit_projectors
    resources.host.resource_capabilities = result.resource_capabilities
    resources.host.progress_provider = result.progress_provider
    scope = resources.store.validate_scope({'subject_refs': resources.store.problem()['subject_refs']})
    for role in bindings:
        context = BindingContext(resources.journal.run_id, 'episode-' + role, role,
                                  ((role, 'fixture'),), scope, {}, {})
        binding = next(item for item in result.bindings if role in item.roles)
        view = binding.credit_view(context, selected)
        assert view['credit'] == 7
        assert seen[-1] == (role, context, selected)
        assert seen[-1][1] is context and seen[-1][2] is selected
    resource_binding = result.bindings[-1]
    assert canonical(resource_binding.capabilities()) == canonical(result.resource_capabilities)
    assert len(result.resource_capabilities) == 1
    assert result.resource_capabilities[0]['availability'] == 'authentication_required'
    assert {item['kind'] for item in result.resource_capabilities} == {'local'}


def test_progress_provider_is_available_without_monitor_and_job_provider_is_explicit(resources):
    jobs = SimpleNamespace(scope=forbidden, observe=forbidden, direct_dependencies=forbidden)
    saved = LiteratureEpisodes(resources.services).as_record()
    result = compose(resources, [saved], role_credit_bindings={}, job_progress_provider=jobs)
    assert result.progress_provider.job_provider is jobs
    assert result.progress_provider.durable_store is resources.backend
    assert result.role_credit_projectors == result.role_credit_definitions == {}
    assert result.resource_capabilities == ()
    assert len(result.bindings) == 1
    empty = compose(resources, [], execution_backend=None, role_credit_bindings={})
    assert empty.bindings == () and empty.progress_provider is None
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, [], execution_backend=None, job_progress_provider=jobs)
    assert_failure(error, 'unavailable_binding', 'execution_backend')


def test_duplicate_descriptors_do_not_create_another_binding(resources, monkeypatch):
    saved = descriptors(resources)[0]
    monkeypatch.setattr(ProgressProvider, '__init__', forbidden)
    with pytest.raises(DurableExecutionError) as error:
        compose(resources, [saved, deepcopy(saved)])
    assert_failure(error, 'identity_conflict', 'episode_bindings')


def _restriction_replay_descriptors():
    # Actual570 descriptor metadata, used only as pure compatibility inputs.
    # These dictionaries establish no library, producer, execution or custody.
    recorded = {
        'version': 'scientific_process_episodes_v8', 'binding_id': 'scientific_process',
        'implementation_sha256': 'cf9e98737150f9dff6a5a3371e2b3424850e4ac1ae957d916caca0271b5b5a24',
        'configuration': {
            'library': {'version': 'scientific_process_library_snapshot_v2',
                'library_id': '14979461e17dbf9ac3fadeb060144150f485a013dcf1f5fd2be5cb20dd0a841a',
                'manifest_sha256': '24e89e053b2c04814885c948c796cb2993fd62dc77867bd462c7badf68c4f9d0'},
            'tool_library': {'version': 'scientific_tool_library_v2',
                'catalog_sha256': '763a54379b621cc30f7903eb2e1fc38603fd1472987dbdd5f121e5dfdd07700d'},
            'child_roles': ['scientific_process']},
    }
    actual = deepcopy(recorded)
    actual['implementation_sha256'] = '3f4a6e314d2f6376e210de699545cc9fc2e14ada0ef8550954af21aa68cf33e3'
    return actual, recorded


def test_closed_restriction_repair_accepts_only_the_reviewed_current_to_recorded_pair():
    actual, recorded = _restriction_replay_descriptors()
    before = deepcopy((actual, recorded))
    assert scientific_binding_compatible(actual, recorded) is True
    assert scientific_binding_compatible(actual, actual) is True
    assert scientific_binding_compatible(recorded, recorded) is True
    assert {key: value for key, value in actual.items() if key != 'implementation_sha256'} == {
        key: value for key, value in recorded.items() if key != 'implementation_sha256'}
    assert (actual, recorded) == before


@pytest.mark.parametrize('changed', ['reverse', 'unknown_actual', 'unknown_recorded'])
def test_closed_restriction_repair_rejects_reverse_and_unknown_implementations(changed):
    actual, recorded = _restriction_replay_descriptors()
    if changed == 'reverse':
        actual, recorded = recorded, actual
    elif changed == 'unknown_actual':
        actual['implementation_sha256'] = '0' * 64
    else:
        recorded['implementation_sha256'] = 'f' * 64
    before = deepcopy((actual, recorded))
    assert scientific_binding_compatible(actual, recorded) is False
    assert (actual, recorded) == before


@pytest.mark.parametrize('changed', ['library', 'manifest', 'tool_catalog', 'child_roles',
    'binding_role', 'current_version', 'recorded_version', 'both_legacy_versions',
    'extra_configuration', 'extra_descriptor'])
def test_closed_restriction_repair_preserves_all_other_descriptor_operands(changed):
    actual, recorded = _restriction_replay_descriptors()
    if changed == 'library':
        actual['configuration']['library']['library_id'] = '0' * 64
    elif changed == 'manifest':
        actual['configuration']['library']['manifest_sha256'] = '0' * 64
    elif changed == 'tool_catalog':
        actual['configuration']['tool_library']['catalog_sha256'] = '0' * 64
    elif changed == 'child_roles':
        actual['configuration']['child_roles'].append('results')
    elif changed == 'binding_role':
        actual['binding_id'] = 'different_scientific_role'
    elif changed == 'current_version':
        actual['version'] = 'scientific_process_episodes_v7'
    elif changed == 'recorded_version':
        recorded['version'] = 'scientific_process_episodes_v7'
    elif changed == 'both_legacy_versions':
        actual['version'] = recorded['version'] = 'scientific_process_episodes_v7'
    elif changed == 'extra_configuration':
        actual['configuration']['unrecorded_option'] = True
    else:
        actual['unrecorded_field'] = True
    before = deepcopy((actual, recorded))
    assert scientific_binding_compatible(actual, recorded) is False
    assert (actual, recorded) == before
