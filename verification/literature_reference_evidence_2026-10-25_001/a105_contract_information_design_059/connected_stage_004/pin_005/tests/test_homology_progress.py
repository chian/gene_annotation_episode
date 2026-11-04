"""Native progress custody/replay tests; one explicitly tiny real phmmer run.

Other log/state cases use controlled files/status observations in a real Store
and registry. No model, episode science, credit unit or investigation run is used.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
import time

import pytest

from method_loop.durable import content_digest
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.homology_jobs import FileAsset, HomologyJobs, OUTPUTS, digest
from gene_annotation_episode.homology_progress import HomologyProgressProvider
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.progress_records import validate_job_status
from gene_annotation_episode.state import Store
from test_durable_episode import commission_spec


PROJECT = Path(__file__).resolve().parents[1]
PROGRAM = PROJECT / 'resources/software/infernal-1.1.5/hmmer/src/phmmer'
PROTEIN = 'MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE'
RUN = 'durable-fixture-run'
FIELDS = ['execution_status', 'measurements', 'log_windows', 'committed_record_refs',
          'dependencies', 'result_available']


def make_provider(store, jobs, *, window=8, roles=('native_text', 'native_stderr')):
    return HomologyProgressProvider(store, jobs, run_id=RUN,
        log_window_bytes=window, log_roles=roles)


@pytest.fixture
def fixture(tmp_path):
    database = tmp_path / 'reference.faa'
    database.write_text('>tiny_fixture_reference\n' + PROTEIN + '\n')
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence=PROTEIN, molecule='protein')
        query = store.targets()[0]['id']
        jobs = HomologyJobs.create(tmp_path / 'jobs', executable=FileAsset(PROGRAM, digest(PROGRAM)),
            reference_database=FileAsset(database, digest(database)),
            policy=LocalJobPolicy(128 * 1024**2, 4 * 1024**2), max_cpu=2,
            search_modes=['native_defaults', 'maximum_sensitivity'])
        try:
            job = jobs.order(query_ref=query, query_fasta='>query\n' + PROTEIN + '\n',
                cpu=1, search_mode='native_defaults', operation_key='selected-native-order')
            provider = make_provider(store, jobs)
            yield store, jobs, query, job, provider
        finally:
            jobs.close()


def forbid(*_args, **_kwargs):
    raise AssertionError('unexpected execution or new observation')


def fixture_status(jobs, job, *, state='running', elapsed=1.25, outcome='pending', failure=None):
    """Controlled native observation, including actual fixture file sizes."""
    return {'job_ref': job, 'registry_ref': jobs.config['registry_ref'],
        'state': state, 'outcome': outcome, 'elapsed_seconds': elapsed,
        'duration_measure': 'systemd_service_wall_seconds', 'native_returncode':
            1 if failure else 0 if outcome == 'succeeded' else None,
        'failure_code': failure, 'resource': None,
        'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction',
        'outputs': [{'role': role, 'available': (jobs.directory / job / name).is_file(),
            'bytes': (jobs.directory / job / name).stat().st_size
                if (jobs.directory / job / name).is_file() else None,
            'writer_closed': state == 'returned' and (jobs.directory / job / name).is_file()}
            for role, name in OUTPUTS.items()]}


def log_file(jobs, job, content=b'0123456789abcdef', role='native_text'):
    directory = jobs.directory / job
    directory.mkdir(exist_ok=True)
    path = directory / OUTPUTS[role]
    path.write_bytes(content)
    return path


def source_body(store, source):
    return json.loads(store.get_artifact(store.get(source)['request_ref']))


def progress_sources(store):
    return [source for source in store.list('source')
            if source['provider'].startswith('homology.progress.')]


def assigned_spec(tmp_path, provider, job, query, *, resource=False, key='selected-owner'):
    spec = commission_spec(tmp_path, key=key)
    spec['child']['scope'] = provider.scope(job)
    assignment = {'job_ref': job, 'query_ref': query, 'cpu': 1, 'search_mode': 'native_defaults'}
    spec['child']['request']['message'] = ({'episode_assignment': {'adapter_assignment': assignment}}
        if resource else {'job_assignment': assignment})
    return spec


def test_definition_and_scope_are_bound_to_registered_query(fixture, monkeypatch):
    store, jobs, query, job, provider = fixture
    record = provider.as_record()
    assert set(record) == {'version', 'implementation_sha256', 'registry_ref',
                          'registry_configuration_sha256', 'configuration'}
    assert record['version'] == 'homology_progress_provider_v1'
    assert record['registry_configuration_sha256'] == content_digest(jobs.config)
    assert record['implementation_sha256'] == hashlib.sha256(
        (PROJECT / 'gene_annotation_episode/homology_progress.py').read_bytes()).hexdigest()
    assert record['configuration'] == {'log_window_bytes': 8,
                                       'log_roles': ['native_text', 'native_stderr']}
    scope = provider.scope(job)
    assert scope == store.validate_scope({'subject_refs': [query], 'segments': store.coverage(query)})
    monkeypatch.setattr(jobs, 'status', forbid)
    assert provider.direct_dependencies(job, scope) == []
    with pytest.raises(ContractError, match='target_unavailable'):
        provider.scope('homology_job_' + 'f' * 24)
    with pytest.raises(ContractError, match='outside_scope'):
        provider.direct_dependencies(job, {'subject_refs': [query], 'segments': [{
            'target_ref': query, 'start': 0, 'end': 1, 'unit': 'aa'}]})
    with pytest.raises(ContractError, match='query_identity_conflict'):
        jobs.db.execute('UPDATE orders SET query_fasta=? WHERE job_ref=?', ('>query\nAAAA\n', job))
        provider.scope(job)


@pytest.mark.parametrize('window,roles', [(0, ()), (True, ()), (1, ['native_text']),
    (1, ('hit_table',)), (1, ('native_text', 'native_text')), (1, ([],))])
def test_caller_must_supply_valid_log_representation_bounds(fixture, window, roles):
    store, jobs, *_ = fixture
    with pytest.raises(ValueError):
        make_provider(store, jobs, window=window, roles=roles)


def test_observation_only_reads_status_and_publishes_resolvable_provenance(fixture, monkeypatch):
    store, jobs, query, job, provider = fixture
    for method in ('configure', 'stage', 'submit', 'resume_start', 'result_file', 'sample',
                   'receive', 'check_handoff', 'recover_statistics'):
        monkeypatch.setattr(jobs, method, forbid)
    monkeypatch.setattr(provider, '_read_log', forbid)
    scope = provider.scope(job)
    observed = provider.observe(job, ['measurements'], scope)
    assert validate_job_status(observed['execution_status']) == observed['execution_status']
    assert observed['execution_status']['lifecycle_state'] == 'pending'
    assert observed['result_available'] is False
    assert observed['log_windows'] == observed['dependencies'] == observed['committed_record_refs'] == []
    assert all(row['value'] is None for row in observed['measurements'])
    assert {row['name'] for row in observed['measurements']} == {
        'elapsed_seconds', *(role + '_bytes' for role in OUTPUTS)}
    assert set(store.reference_subset(observed['provenance_refs'], scope)) == set(observed['provenance_refs'])
    saved = source_body(store, observed['progress_ref'])
    assert saved == {key: value for key, value in observed.items() if key != 'progress_ref'}
    status_source = store.get(observed['measurements'][0]['provenance_ref'])
    assert status_source['operand_refs'] == [query]
    assert source_body(store, status_source['id'])['native_status'] == observed['execution_status']['native']
    assert jobs.db.execute('SELECT staged,submission_requested FROM orders').fetchone()[:] == (0, 0)
    assert not store.list('observation') and not store.list('native_execution')


def test_log_tail_is_exact_retained_bytes_with_original_offsets(fixture, monkeypatch):
    store, jobs, query, job, provider = fixture
    path = log_file(jobs, job)
    native = fixture_status(jobs, job)
    monkeypatch.setattr(jobs, 'status', lambda _handle: deepcopy(native))
    observed = provider.observe(job, FIELDS, provider.scope(job))
    window, = observed['log_windows']
    assert (window['start_byte'], window['end_byte']) == (0, 8)
    assert store.get_artifact(window['artifact_ref']) == path.read_bytes()[-8:]
    metadata = source_body(store, window['source_ref'])
    assert metadata['original_start_byte'] == 8 and metadata['original_end_byte'] == 16
    assert metadata['observed_file_size'] == metadata['status_output_bytes'] == 16
    assert metadata['whole_file_atomic_snapshot'] is False
    source = store.get(window['source_ref'])
    assert source['operand_refs'] == [query]
    assert source['parent_source_refs'] == [metadata['status_source_ref']]
    assert all(store.reference_subset([ref], provider.scope(job)) for ref in
        [source['id'], source['artifact_ref'], source['request_ref'], metadata['status_source_ref']])
    assert observed['result_available'] is True
    assert all(not row['writer_closed'] for row in native['outputs'])
    assert provider.observe(job, FIELDS, provider.scope(job)) == observed
    assert len(progress_sources(store)) == 3


def test_partial_log_read_keeps_only_actual_bytes_and_growth_is_not_atomic(fixture, monkeypatch):
    store, jobs, _, job, provider = fixture
    path = log_file(jobs, job)
    native = fixture_status(jobs, job)
    monkeypatch.setattr(jobs, 'status', lambda _handle: native)
    original_open = Path.open

    class PartialRead:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def seek(self, offset):
            return self.stream.seek(offset)
        def read(self, count):
            assert count == 8
            # Controlled growth after fstat, followed by a short actual read.
            with original_open(path, 'ab') as writer:
                writer.write(b'newly_appended')
            return self.stream.read(3)

    def partial_open(selected, mode='r', *args, **kwargs):
        stream = original_open(selected, mode, *args, **kwargs)
        return PartialRead(stream) if selected == path and mode == 'rb' else stream

    monkeypatch.setattr(Path, 'open', partial_open)
    observed = provider.observe(job, ['log_windows'], provider.scope(job))
    window, = observed['log_windows']
    assert store.get_artifact(window['artifact_ref']) == b'89a'
    metadata = source_body(store, window['source_ref'])
    assert metadata['observed_file_size'] == 16
    assert metadata['original_start_byte'] == 8 and metadata['original_end_byte'] == 11
    assert metadata['retained_bytes'] == window['end_byte'] == 3
    assert metadata['whole_file_atomic_snapshot'] is False


def test_same_bytes_at_different_offsets_retain_distinct_custody(fixture, monkeypatch):
    store, jobs, _, job, provider = fixture
    path = log_file(jobs, job, b'abcdefghabcdefgh')
    monkeypatch.setattr(jobs, 'status', lambda _handle: fixture_status(jobs, job))
    first = provider.observe(job, ['log_windows'], provider.scope(job))['log_windows'][0]
    path.write_bytes(path.read_bytes() + b'abcdefgh')
    second = provider.observe(job, ['log_windows'], provider.scope(job))['log_windows'][0]
    assert first['artifact_ref'] == second['artifact_ref']
    assert first['source_ref'] != second['source_ref']
    assert source_body(store, first['source_ref'])['original_start_byte'] == 8
    assert source_body(store, second['source_ref'])['original_start_byte'] == 16


def test_selected_replay_precedes_status_and_log_reads_and_conflicts_on_selection(fixture, monkeypatch):
    store, jobs, _, job, provider = fixture
    path = log_file(jobs, job)
    monkeypatch.setattr(jobs, 'status', lambda _handle: fixture_status(jobs, job))
    scope = provider.scope(job)
    original = provider.observe(job, FIELDS, scope, operation_key='selected-observation')
    path.unlink()
    monkeypatch.setattr(jobs, 'status', forbid)
    monkeypatch.setattr(provider, '_read_log', forbid)
    assert provider.observe(job, FIELDS, scope, operation_key='selected-observation') == original
    for changed in ({'handle': 'homology_job_' + 'f' * 24}, {'requested_fields': []},
                    {'scope': {'subject_refs': scope['subject_refs']}}):
        arguments = {'handle': job, 'requested_fields': FIELDS, 'scope': scope, **changed}
        with pytest.raises(ContractError, match='operation_identity_conflict'):
            provider.observe(**arguments, operation_key='selected-observation')
    with Store(store.path) as reopened:
        recovered = make_provider(reopened, jobs)
        assert recovered.observe(job, FIELDS, scope, operation_key='selected-observation') == original


@pytest.mark.parametrize('state', ['submission_unconfirmed', 'execution_unknown'])
def test_unknown_native_states_and_measurements_remain_unknown(fixture, monkeypatch, state):
    _, jobs, _, job, provider = fixture
    native = fixture_status(jobs, job, state=state, outcome='unknown', elapsed=None)
    monkeypatch.setattr(jobs, 'status', lambda _handle: native)
    observed = provider.observe(job, FIELDS, provider.scope(job))
    assert observed['execution_status']['lifecycle_state'] is None
    assert observed['execution_status']['native'] == native
    assert observed['result_available'] is False
    assert all(row['value'] is None for row in observed['measurements'])


def test_failures_and_live_partial_outputs_are_preserved_without_scientific_completion(fixture, monkeypatch):
    _, jobs, _, job, provider = fixture
    log_file(jobs, job, b'partial native error\n', role='native_stderr')
    native = fixture_status(jobs, job, state='returned', outcome='failed',
                            failure='native_nonzero_exit', elapsed=2.5)
    monkeypatch.setattr(jobs, 'status', lambda _handle: native)
    observed = provider.observe(job, FIELDS, provider.scope(job))
    assert observed['execution_status']['native'] == native
    assert observed['execution_status']['lifecycle_state'] == 'returned'
    assert observed['execution_status']['native']['outcome'] == 'failed'
    assert observed['result_available'] is True and not observed['committed_record_refs']
    assert observed['measurements'][0]['value'] == 2.5


def test_invalid_native_status_and_disappearing_logs_roll_back_capture(fixture, monkeypatch):
    store, jobs, _, job, provider = fixture
    path = log_file(jobs, job)
    native = fixture_status(jobs, job)
    native['outputs'][0]['writer_closed'] = True
    monkeypatch.setattr(jobs, 'status', lambda _handle: native)
    with pytest.raises(ContractError, match='output_relationship_mismatch'):
        provider.observe(job, FIELDS, provider.scope(job), operation_key='failed')
    assert len(progress_sources(store)) == 0
    native['outputs'][0]['writer_closed'] = False
    path.unlink()
    with pytest.raises(ContractError, match='log_read_failed'):
        provider.observe(job, FIELDS, provider.scope(job), operation_key='failed')
    assert len(progress_sources(store)) == 0
    assert store.db.execute('SELECT count(*) FROM runtime_homology_progress_operations').fetchone()[0] == 0
    with pytest.raises(RuntimeError, match='caller rollback'):
        with store.transaction():
            provider.observe(job, [], provider.scope(job), operation_key='rolled-back')
            raise RuntimeError('caller rollback')
    assert len(progress_sources(store)) == 0


@pytest.mark.parametrize('resource', [False, True])
def test_dependency_is_exact_selected_order_relationship_without_live_poll(fixture, tmp_path, monkeypatch, resource):
    store, jobs, query, job, provider = fixture
    spec = assigned_spec(tmp_path, provider, job, query, resource=resource)
    monkeypatch.setattr(jobs, 'status', forbid)
    relation = provider.dependency(spec, operation_key='assigned-job')
    assert relation['handle'] == job and relation['state'] == 'pending' and relation['kind'] == 'job'
    assert store.reference_subset([relation['relation_ref']], spec['child']['scope']) == [relation['relation_ref']]
    assert source_body(store, relation['relation_ref']) == {
        'version': 'native_job_dependency_v1', 'run_id': RUN, 'owner_handle': spec['handle'],
        'owner_episode_id': spec['child']['episode_id'], 'commission_sha256': content_digest(spec),
        'job_ref': job, 'registry_ref': jobs.config['registry_ref'], 'query_ref': query,
        'cpu': 1, 'search_mode': 'native_defaults', 'job_operation_key': 'selected-native-order'}
    assert provider.dependency(spec, operation_key='assigned-job') == relation
    assert provider.dependency(spec, operation_key='same-relationship') == relation
    changed = deepcopy(spec)
    changed['constraints']['changed-selection'] = True
    with pytest.raises(ContractError, match='operation_identity_conflict'):
        provider.dependency(changed, operation_key='assigned-job')


@pytest.mark.parametrize('field,value', [('cpu', 2), ('cpu', True), ('query_ref', 'foreign'),
    ('search_mode', 'maximum_sensitivity'), ('registry_ref', 'foreign'),
    ('handoff', {'job_ref': 'foreign', 'registry_ref': 'foreign'})])
def test_dependency_rejects_mismatched_registered_assignment(fixture, tmp_path, field, value):
    _, _, query, job, provider = fixture
    spec = assigned_spec(tmp_path, provider, job, query)
    spec['child']['request']['message']['job_assignment'][field] = value
    with pytest.raises(ContractError, match='assignment_.*conflict'):
        provider.dependency(spec, operation_key='bad-assignment')


def test_dependency_absence_is_durable_and_foreign_scope_is_rejected(fixture, tmp_path):
    _, _, query, job, provider = fixture
    spec = assigned_spec(tmp_path, provider, job, query)
    spec['child']['request']['message'] = {}
    assert provider.dependency(spec, operation_key='none') is None
    assert provider.dependency(spec, operation_key='none') is None
    spec['child']['request']['message'] = {'job_assignment': {'job_ref': 'unregistered'}}
    assert provider.dependency(spec, operation_key='unregistered') is None
    spec['child']['request']['message'] = {'job_assignment': {'job_ref': job, 'query_ref': query,
        'cpu': 1, 'search_mode': 'native_defaults'}}
    spec['child']['scope']['segments'][0]['end'] = 1
    with pytest.raises(ContractError, match='outside_scope'):
        provider.dependency(spec, operation_key='bad-scope')


def test_concurrent_writers_reuse_first_snapshot_and_selected_operation(fixture, monkeypatch):
    store, jobs, _, job, provider = fixture
    scope = provider.scope(job)
    barrier = threading.Barrier(2)
    count = 0
    lock = threading.Lock()
    original_status = HomologyJobs.status

    def counting_status(service, handle):
        nonlocal count
        with lock:
            count += 1
        return original_status(service, handle)

    monkeypatch.setattr(HomologyJobs, 'status', counting_status)

    def capture(_index):
        with Store(store.path) as connection:
            registry = HomologyJobs(jobs.directory)
            try:
                local = make_provider(connection, registry)
                barrier.wait(timeout=10)
                return local.observe(job, FIELDS, scope, operation_key='same-selected-read')
            finally:
                registry.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(capture, range(2)))
    assert first == second and count == 1
    assert len(progress_sources(store)) == 2
    # An unkeyed unchanged observation also retains the first capture/time.
    assert provider.observe(job, FIELDS, scope) == first
    assert count == 2 and len(progress_sources(store)) == 2


def test_actual_tiny_local_native_run_and_retained_log_bytes(fixture):
    """Actual phmmer/systemd work, separate from the controlled status fixtures."""
    store, jobs, _, job, provider = fixture
    # These explicit test setup actions are the only native execution here.
    jobs.configure(job, 1)
    jobs.stage(job)
    jobs.submit(job)
    try:
        deadline = time.monotonic() + 15  # Test deadline, never adapter policy.
        while jobs.status(job)['state'] in {'starting', 'running'}:
            assert time.monotonic() < deadline
            time.sleep(.02)
        observed = provider.observe(job, FIELDS, provider.scope(job), operation_key='actual-native-progress')
        native = observed['execution_status']['native']
        assert native['state'] == 'returned' and native['outcome'] == 'succeeded', native
        assert native['native_returncode'] == 0
        assert native['elapsed_seconds'] is not None and native['elapsed_seconds'] > 0
        assert all(row['available'] and row['writer_closed'] for row in native['outputs'])
        assert observed['result_available'] is True
        assert observed['measurements'][0]['value'] == native['elapsed_seconds']
        assert observed['log_windows']
        for window in observed['log_windows']:
            metadata = source_body(store, window['source_ref'])
            path = Path(metadata['path'])
            assert store.get_artifact(window['artifact_ref']) == path.read_bytes()[
                metadata['original_start_byte']:metadata['original_end_byte']]
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('native_execution')
    finally:
        from gene_annotation_episode.native_lifecycle import cancel
        if jobs.status(job)['state'] in {'starting', 'running'}:
            cancel(jobs._handle(job))
