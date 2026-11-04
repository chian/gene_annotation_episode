"""Explicit service setup over actual Store/registry, without executing work."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode import resource_service_setup
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
from gene_annotation_episode.execution_recording import HomologyStatistics
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, digest
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.resource_episodes import HomologyResourceAdapter, ResourceEpisodes
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.resource_operational_credit import ResourceOperationalCredit
from gene_annotation_episode.resource_service_setup import bind_resource_services
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
UNITS = {'handoff_unit': 2.75, 'acquired_record_unit': 0.125}


def forbidden(*args, **kwargs):
    raise AssertionError('Setup must not execute work or project credit')


@pytest.fixture
def resources(tmp_path):
    # These are configuration assets. Neither is run or interpreted as evidence.
    executable = tmp_path/'fixture_program'
    executable.write_text('#!/bin/sh\nexit 99\n')
    executable.chmod(0o700)
    database = tmp_path/'fixture_database.faa'
    database.write_text('>fixture\nMKK\n')
    limits = LocalJobPolicy(memory_bytes=20*1024**3, scratch_bytes=4*1024**3)
    jobs = HomologyJobs.create(tmp_path/'registry',
        executable=FileAsset(executable, digest(executable)),
        reference_database=FileAsset(database, digest(database)), policy=limits, max_cpu=2)
    with Store(tmp_path/'workspace') as store:
        homology = HomologyEpisodes(jobs, parser_policy=limits,
            credit_projector=forbidden, credit_binding={'kind': 'explicit_fixture_legacy_credit'},
            monitoring_projector=forbidden,
            monitoring_binding={'kind': 'explicit_fixture_monitoring_credit'})
        try:
            yield SimpleNamespace(store=store, homology=homology, jobs=jobs,
                estimator=ResourceToolEstimator(), directory=tmp_path/'run', run_id='setup-fixture')
        finally:
            jobs.close()


def setup(resources, **overrides):
    options = {'run_id': resources.run_id, 'directory': resources.directory,
        'job_episodes': resources.homology, 'resource_estimator': resources.estimator, **UNITS}
    options.update(overrides)
    return bind_resource_services(resources.store, **options)


def assert_no_work(resources):
    for table in ('orders', 'handoffs', 'samples'):
        assert resources.jobs.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    for table in ('runtime_runs', 'runtime_episodes', 'runtime_actions',
                  'runtime_model_calls', 'runtime_observations'):
        assert resources.store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    assert resources.store.db.execute('SELECT count(*) FROM records').fetchone()[0] == 0


@pytest.mark.parametrize('physical_identity', [False, True])
def test_setup_binds_exact_reader_registry_run_and_all_five_roles(
        resources, monkeypatch, physical_identity):
    r = resources
    if physical_identity:
        r.homology.statistics = HomologyStatistics(r.directory/'history.sqlite',
            'explicit-fixture-resource', 1, 3)
    adapters = []

    def capture_adapter(*args, **kwargs):
        value = HomologyResourceAdapter(*args, **kwargs)
        adapters.append(value)
        return value

    monkeypatch.setattr(resource_service_setup, 'HomologyResourceAdapter', capture_adapter)
    for name in ('capability', 'execute', 'check_handoff', 'credit_view'):
        monkeypatch.setattr(HomologyResourceAdapter, name, forbidden)
    monkeypatch.setattr(HomologyEpisodes, 'execute', forbidden)
    monkeypatch.setattr(ResourceOperationalCredit, '__call__', forbidden)
    monkeypatch.setattr(ResourceToolEstimator, 'estimate', forbidden)
    monkeypatch.setattr(ResourceToolEstimator, 'estimate_context', forbidden)
    monkeypatch.setattr('subprocess.run', forbidden)

    application = setup(r)
    assert type(application) is EpisodeApplicationServices
    assert application.job_progress_provider is None
    assert tuple(application.role_credit_bindings) == ROLES
    adapter, = adapters
    assert adapter.homology is r.homology
    assert adapter.resource_estimator is r.estimator
    assert adapter.store is adapter.journal.store is r.store
    assert adapter.journal.db is r.store.db
    assert adapter.journal.run_id == r.run_id
    assert adapter.information.store is r.store
    assert adapter.information.jobs is r.jobs
    assert adapter.information.run_id == r.run_id
    assert adapter.record_selection is None
    assert application.episode_binding_descriptors == (
        ResourceEpisodes(None, resource_adapters=(adapter,)).as_record(),)
    descriptor, = application.episode_binding_descriptors
    saved_adapter, = descriptor['configuration']['resource_adapters']
    assert saved_adapter == adapter.as_record()
    assert saved_adapter['homology'] == r.homology.as_record()
    assert saved_adapter['resource_estimator'] == r.estimator.as_record()
    assert saved_adapter['resource_identity_kind'] == (
        'physical_binding' if physical_identity else 'logical_registry')
    projectors = []
    for binding in application.role_credit_bindings.values():
        assert set(binding) == {'definition', 'project'}
        projector = binding['project']
        projectors.append(projector)
        assert type(projector) is ResourceOperationalCredit
        assert projector.reader is adapter.information
        assert binding['definition'] == projector.as_record()
        assert binding['definition']['reader'] == {
            'version': 'resource_information_reader_v1', 'run_id': r.run_id,
            'registry_ref': r.jobs.config['registry_ref']}
        assert {name: binding['definition'][name] for name in UNITS} == UNITS
    assert all(value is projectors[0] for value in projectors)
    # Each retained JSON definition is detached even though the callable is shared.
    original = deepcopy(application.role_credit_bindings['results']['definition'])
    application.role_credit_bindings['launch']['definition']['reader']['run_id'] = 'altered'
    assert application.role_credit_bindings['results']['definition'] == original
    assert projectors[0].as_record() == original
    assert not r.directory.exists()
    assert_no_work(r)


@pytest.mark.parametrize('name', tuple(UNITS))
@pytest.mark.parametrize('invalid', [None, 0, -1, True, float('nan'), float('inf'), '1'])
def test_setup_rejects_nonpositive_nonfinite_or_implicit_units(resources, name, invalid):
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        setup(resources, **{name: invalid})
    assert_no_work(resources)


@pytest.mark.parametrize('missing', tuple(UNITS))
def test_setup_requires_both_unit_operands(resources, missing):
    options = {'run_id': resources.run_id, 'directory': resources.directory,
        'job_episodes': resources.homology, 'resource_estimator': resources.estimator, **UNITS}
    del options[missing]
    with pytest.raises(TypeError, match=missing):
        bind_resource_services(resources.store, **options)


def test_caller_merges_services_and_explicitly_enables_receipts(resources, monkeypatch):
    r = resources
    applications, observed = [], []

    def factory(store, *, run_id, directory, job_episodes, resource_estimator):
        assert store is r.store and run_id == r.run_id and directory == r.directory
        assert job_episodes is r.homology and resource_estimator is r.estimator
        resource = bind_resource_services(store, run_id=run_id, directory=directory,
            job_episodes=job_episodes, resource_estimator=resource_estimator, **UNITS)
        application = EpisodeApplicationServices(
            (*resource.episode_binding_descriptors, LiteratureEpisodes(None).as_record()),
            resource.role_credit_bindings)
        applications.append(application)
        return application

    def capability(adapter):
        observed.append(adapter)
        return {'resource_id': adapter.resource_id, 'kind': 'local', 'availability': 'unknown',
            'observed_at': '2026-10-21T00:00:00+00:00',
            'provenance_refs': [r.jobs.config['registry_ref']], 'knowledge_entry_ids': [],
            'tool_names': []}

    monkeypatch.setattr(HomologyResourceAdapter, 'capability', capability)
    monkeypatch.setattr(ResourceOperationalCredit, '__call__', forbidden)
    monkeypatch.setattr('subprocess.run', forbidden)
    workflow = Workflow(r.store, ToolRegistry(r.store), object(), r.directory, r.run_id,
        forbidden, forbidden, job_episodes=r.homology, resource_estimator=r.estimator,
        episode_service_factory=factory,
        episode_service_binding={'kind': 'explicit_fixture_resource_setup', **UNITS},
        episode_record_receipts=True, initial_known_record_refs=[])
    application, = applications
    assert workflow.receipts is not None
    assert workflow.initial_known_record_refs == []
    assert workflow.episode_bindings.as_record() == list(application.episode_binding_descriptors)
    assert set(workflow.role_credit_projectors) == set(ROLES)
    for role in ROLES:
        assert workflow.role_credit_projectors[role] is application.role_credit_bindings[role]['project']
        reader = workflow.role_credit_projectors[role].reader
        assert reader.store is r.store and reader.jobs is r.jobs and reader.run_id == r.run_id
    # One actual capability read belongs to composition, after pure setup returned.
    assert len(observed) == 1
    assert_no_work(r)
