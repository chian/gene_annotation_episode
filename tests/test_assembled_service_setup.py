"""Existing service assembly with explicit engineering operands and zero work."""
from copy import deepcopy
import inspect
from pathlib import Path

import pytest

from gene_annotation_episode import assembled_service_setup, episode_monitoring
from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices
from gene_annotation_episode.episode_monitoring import MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.homology_progress import HomologyProgressProvider
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.resource_episodes import HomologyResourceAdapter
from gene_annotation_episode.resource_operational_credit import ResourceOperationalCredit
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.scientific_tool_retrieval import ScientificToolRetriever
from test_resource_service_setup import assert_no_work, forbidden, resources


PUBLICATION = (Path(__file__).resolve().parents[1] /
    'research/slotted_process_library/publications/2026-10-21-001')
ROOT_ROLES = ('scientific_process', 'literature', 'launch', 'monitor', 'results')
OPERATIONAL_ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
RETRIEVAL = {'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
    'model': {'model': 'gpt-6-luna', 'reasoning_effort': 'none'}}
CATALOG = {'fixture.read': {'description': 'Engineering fixture reader contract.', 'resources': 'local',
    'input_schema': {'type': 'object', 'properties': {'offset': {'type': 'integer', 'minimum': 0}},
        'required': ['offset'], 'additionalProperties': False},
    'configuration': {'reader': 'explicit-engineering-reader-v1', 'page': 7}}}


def operands(r):
    return {'run_id': r.run_id, 'directory': r.directory,
        'job_episodes': r.homology, 'resource_estimator': r.estimator,
        'source_directory': PUBLICATION, 'tool_catalog': deepcopy(CATALOG),
        'tool_retrieval': deepcopy(RETRIEVAL), 'scientific_child_roles': ROOT_ROLES,
        'handoff_unit': 2.75, 'acquired_record_unit': 0.125,
        'monitoring_information_unit': 0.375, 'literature_outcome_page_size': 7,
        'monitor_outcome_page_size': 13, 'log_window_bytes': 123,
        'log_roles': ('native_stderr', 'native_text')}


def setup(r, **changes):
    return bind_assembled_services(r.store, **{**operands(r), **changes})


def test_wired_setup_has_one_launch_family_and_actual_tool_registry(resources):
    from gene_annotation_episode.execution_progress import ExecutionProgressProvider
    from gene_annotation_episode.tools import ToolRegistry
    r = resources
    tools = ToolRegistry(r.store)
    configuration = {'here': {'kind': 'local', 'workspace': str(r.directory/'project'), 'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}},
        'ebi': {'kind': 'hmmer_api'}}
    application = setup(r, execution_resources=configuration, initial_execution_information={},
        tool_registry=tools, log_roles=('stdout', 'stderr'))
    scientific, literature, execution, monitor = application.episode_binding_descriptors
    assert [entry['binding_id'] for entry in application.episode_binding_descriptors] == [
        'scientific_process', 'literature', 'execution_episodes', 'monitor']
    assert execution['configuration']['resources'] == configuration
    assert application.job_progress_provider.__class__ is ExecutionProgressProvider
    assert application.job_progress_provider.targets.api_execution.tools is tools
    assert scientific['configuration']['child_roles'] == list(ROOT_ROLES)
    assert set(application.role_credit_bindings) == {*OPERATIONAL_ROLES, 'monitor'}
    original = deepcopy(application.role_credit_bindings['results']['definition'])
    application.role_credit_bindings['launch']['definition']['handoff_unit'] = 999
    assert application.role_credit_bindings['results']['definition'] == original
    tables = {row[0] for row in r.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ('runtime_runs', 'runtime_episodes', 'runtime_actions', 'runtime_observations',
                  'api_execution_episodes', 'api_execution_actions', 'provider_jobs'):
        if table in tables:
            assert r.store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
    assert not (r.directory/'project').exists()


def test_wired_setup_connects_scientific_parent_to_hpc_and_shared_memory(resources):
    from hpc_helpers import commission, resources as hpc_resources
    from gene_annotation_episode.execution_memory import ExecutionMemory
    from gene_annotation_episode.tools import ToolRegistry
    r = resources
    tools = ToolRegistry(r.store)
    memory = ExecutionMemory(r.directory/'shared-memory.sqlite3')
    application = setup(r, execution_resources=hpc_resources(), initial_execution_information={},
        tool_registry=tools, log_roles=('stdout', 'stderr'), hpc_commissions={'a101': commission()},
        shared_execution_memory=memory.as_record())
    scientific = application.episode_binding_descriptors[0]
    hpc = next(row for row in application.episode_binding_descriptors if row['binding_id'] == 'hpc')
    assert 'hpc' in scientific['configuration']['child_roles']
    assert {'hpc', 'hpc_prediction'} <= application.role_credit_bindings.keys()
    assert tools.execution_memory.as_record() == memory.as_record()
    assert hpc['configuration']['shared_execution_memory'] == memory.as_record()
    assert not memory.path.exists()  # Binding does not probe or execute work.


def test_setup_returns_exact_existing_descriptors_six_bindings_and_actual_readers(resources, monkeypatch):
    r = resources
    supplied, captured = operands(r), []
    original_prepare = assembled_service_setup.prepare_scientific_binding

    def prepare(**kwargs):
        captured.append(kwargs)
        return original_prepare(**kwargs)

    monkeypatch.setattr(assembled_service_setup, 'prepare_scientific_binding', prepare)
    for owner, names in (
            (HomologyJobs, ('order', 'submit', 'status', 'check_handoff')),
            (HomologyResourceAdapter, ('capability', 'execute', 'check_handoff', 'credit_view')),
            (HomologyEpisodes, ('execute',)),
            (HomologyProgressProvider, ('observe', 'scope', 'direct_dependencies')),
            (ProgressProvider, ('__init__',)),
            (ResourceOperationalCredit, ('__call__',)),
            (ProgressInformationCredit, ('__call__',)),
            (ScientificToolRetriever, ('retrieve',)),
            (YieldController, ('__init__',))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr('subprocess.run', forbidden)
    application = bind_assembled_services(r.store, **supplied)
    assert type(application) is EpisodeApplicationServices
    call, = captured
    assert call == {'run_directory': r.directory, 'source_directory': PUBLICATION,
        'tool_catalog': supplied['tool_catalog'], 'child_roles': ROOT_ROLES,
        'tool_retrieval': RETRIEVAL}
    assert call['tool_catalog'] is supplied['tool_catalog']
    scientific, literature, resource, monitor = application.episode_binding_descriptors
    library = ScientificProcessLibrary(r.directory/'scientific-process-library')
    tools = ScientificToolLibrary(r.directory/'scientific-tool-library')
    assert scientific == ScientificProcessEpisodes(None, library=library, tool_library=tools,
        child_roles=ROOT_ROLES, tool_retrieval=RETRIEVAL).as_record()
    assert scientific['version'] == 'scientific_process_episodes_v10'
    assert scientific['configuration'] == {'library': library.as_record(),
        'tool_library': tools.as_record(), 'child_roles': list(ROOT_ROLES), 'tool_retrieval': RETRIEVAL}
    assert literature == LiteratureEpisodes(None, outcome_page_size=7).as_record()
    assert monitor == MonitorEpisodes(None, outcome_page_size=13).as_record()
    adapter, = resource['configuration']['resource_adapters']
    assert resource['binding_id'] == 'resource_episodes'
    assert adapter['homology'] == r.homology.as_record()
    assert adapter['resource_estimator'] == r.estimator.as_record()
    assert adapter['resource_identity_kind'] == 'logical_registry'
    assert adapter['resource_id'] == 'registry-local:' + r.jobs.config['registry_ref']
    assert tools.catalog() == [{'name': name, **entry} for name, entry in CATALOG.items()]
    assert tuple(application.role_credit_bindings) == (*OPERATIONAL_ROLES, 'monitor')
    projectors = [application.role_credit_bindings[role]['project'] for role in OPERATIONAL_ROLES]
    assert all(value is projectors[0] for value in projectors)
    operational = projectors[0]
    assert type(operational) is ResourceOperationalCredit
    assert operational.reader.store is r.store and operational.reader.jobs is r.jobs
    assert operational.reader.run_id == r.run_id
    for role in OPERATIONAL_ROLES:
        assert application.role_credit_bindings[role]['definition'] == operational.as_record()
    original = deepcopy(application.role_credit_bindings['results']['definition'])
    application.role_credit_bindings['launch']['definition']['reader']['run_id'] = 'changed'
    assert application.role_credit_bindings['results']['definition'] == operational.as_record() == original
    information = application.role_credit_bindings['monitor']['project']
    assert type(information) is ProgressInformationCredit and information.information_unit == .375
    assert application.role_credit_bindings['monitor']['definition'] == information.as_record()
    assert information.progress_provider.store is r.store
    assert information.progress_provider.run_id == r.run_id
    native = application.job_progress_provider
    assert type(native) is HomologyProgressProvider
    assert native.store is r.store and native.jobs is r.jobs and native.run_id == r.run_id
    assert native.as_record()['configuration'] == {'log_window_bytes': 123,
        'log_roles': ['native_stderr', 'native_text']}
    tables = {row[0] for row in r.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'runtime_homology_progress_custody' in tables
    assert 'runtime_progress_observations' not in tables
    assert_no_work(r)


def test_saved_monitor_credit_reader_delegates_exact_operands_without_observing(resources, monkeypatch):
    r = resources
    application = setup(r)
    reader = application.role_credit_bindings['monitor']['project'].progress_provider
    calls, result, scope = [], {'saved_only': True}, {'subject_refs': ['engineering-target']}

    def saved(*args):
        calls.append(args)
        return result

    monkeypatch.setattr(episode_monitoring, 'read_progress', saved)
    assert reader.read_progress('original-progress-ref', scope) is result
    assert calls == [(r.store, r.run_id, 'original-progress-ref', scope)]
    assert_no_work(r)


def test_current_publication_remains_a0_p19_and_cannot_construct_absent_first_slot(resources):
    r = resources
    application = setup(r)
    library = ScientificProcessLibrary(r.directory/'scientific-process-library')
    headers = library.headers()
    assert sum(row['option_ref']['slot'] == 'annotation_distinction' for row in headers) == 0
    assert sum(row['option_ref']['slot'] == 'thought_pattern' for row in headers) == 19
    tools = ScientificToolLibrary(r.directory/'scientific-tool-library')
    binding = ScientificProcessEpisodes(None, library=library, tool_library=tools,
        child_roles=ROOT_ROLES, tool_retrieval=RETRIEVAL)
    thought = headers[0]['option_ref']
    absent = {**thought, 'slot': 'annotation_distinction', 'option_id': 'A1'}
    with pytest.raises(ValueError, match='scientific_process_option_unknown'):
        binding.prepare_assignment(object(), 'scientific_process',
            {'selection': {'version': 'scientific_process_selection_v2',
                'annotation_ref': absent, 'thought_ref': thought, 'tools': []},
             'evidence_refs': [], 'constraints': {}, 'context': {}}, {}, 'engineering-only')
    assert application.episode_binding_descriptors[0] == binding.as_record()
    assert_no_work(r)


@pytest.mark.parametrize('change', ['missing', 'added', 'schema', 'configuration'])
def test_reopen_rejects_drift_of_the_supplied_actual_tool_map(resources, change):
    r = resources
    setup(r)
    changed = deepcopy(CATALOG)
    if change == 'missing':
        changed.clear()
    elif change == 'added':
        changed['fixture.extra'] = deepcopy(changed['fixture.read'])
    elif change == 'schema':
        changed['fixture.read']['input_schema']['properties']['offset']['minimum'] = 1
    else:
        changed['fixture.read']['configuration']['page'] = 8
    with pytest.raises(ValueError, match='scientific_tool_catalog_changed'):
        setup(r, tool_catalog=changed)
    assert_no_work(r)


@pytest.mark.parametrize(('name', 'invalid', 'message'), [
    ('handoff_unit', 0, 'explicit_positive_operational_credit_units_required'),
    ('handoff_unit', True, 'explicit_positive_operational_credit_units_required'),
    ('acquired_record_unit', float('nan'), 'explicit_positive_operational_credit_units_required'),
    ('monitoring_information_unit', float('inf'), 'explicit_positive_monitoring_information_unit_required'),
    ('monitoring_information_unit', False, 'explicit_positive_monitoring_information_unit_required'),
    ('literature_outcome_page_size', 0, 'positive_literature_outcome_page_size_required'),
    ('literature_outcome_page_size', True, 'positive_literature_outcome_page_size_required'),
    ('monitor_outcome_page_size', 1.5, 'positive_monitor_outcome_page_size_required'),
    ('log_window_bytes', 0, 'homology_progress_log_window_bytes_required'),
    ('log_window_bytes', True, 'homology_progress_log_window_bytes_required'),
    ('log_roles', ['native_text'], 'homology_progress_log_roles_required'),
    ('log_roles', ('native_text', 'native_text'), 'homology_progress_log_roles_required'),
    ('log_roles', ('invented',), 'homology_progress_log_roles_required'),
    ('tool_retrieval', None, 'explicit_scientific_tool_retrieval_configuration_required'),
])
def test_original_component_validation_rejects_invalid_explicit_inputs(resources, name, invalid, message):
    with pytest.raises((TypeError, ValueError), match=message):
        setup(resources, **{name: invalid})
    # Early validation may precede Journal initialization; no records/actions exist.
    assert resources.store.db.execute('SELECT count(*) FROM records').fetchone()[0] == 0
    assert resources.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0


@pytest.mark.parametrize('missing', [
    name for name, parameter in inspect.signature(bind_assembled_services).parameters.items()
    if name != 'store' and parameter.default is inspect.Parameter.empty
])
def test_all_setup_operands_are_required(resources, missing):
    supplied = operands(resources)
    del supplied[missing]
    with pytest.raises(TypeError, match=missing):
        bind_assembled_services(resources.store, **supplied)
