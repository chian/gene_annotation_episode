"""Real A102 constructors and SQLite admission; external host observations controlled explicitly."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a102 import local_resources as lr
from gene_annotation_episode.episodic_workflow.root.a102 import local_jobs, read_mapping
from gene_annotation_episode.episodic_workflow.root.a102.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.episodic_workflow.root.a102.a102_tools import A102ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a102.a102_resources import A102ResourceAdapter
from gene_annotation_episode.episodic_workflow.root.a102.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a102.state import Store
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path/'store') as value:
        yield value


@pytest.fixture
def directory(tmp_path, monkeypatch):
    selected = tmp_path/'capacity'
    monkeypatch.setenv(lr.DIRECTORY_ENV, str(selected))
    return selected


@pytest.mark.parametrize('operation,missing', [
    ('policy', 'local_jobs'), ('capacity', 'local_resources'),
    ('mapper', 'local_tools'), ('tools', 'local_jobs'),
    ('a102_tools', 'local_jobs'), ('adapter', 'local_jobs'),
], ids=['policy', 'capacity', 'mapper', 'tools', 'a102_tools', 'adapter'])
def test_original_constructor_failure(operation, missing, directory, tmp_path, store):
    # Run only before application. These are real constructors, not repaired
    # original fixtures, a fake registry, or assertions of future success.
    with pytest.raises(KeyError) as caught:
        if operation == 'policy':
            local_jobs.LocalJobPolicy.from_config()
        elif operation == 'capacity':
            lr.LocalResources.configured()
        elif operation == 'mapper':
            read_mapping.local_configuration()
        elif operation == 'tools':
            ToolRegistry(store)
        else:
            tools = A102ToolRegistry(store, a102_work_directory=tmp_path/'native')
            if operation == 'adapter':
                A102ResourceAdapter(tools, store, 'operational-constructor')
    assert type(caught.value) is KeyError
    assert caught.value.args == (missing,)
    (tmp_path/'raw-constructor.json').write_text(json.dumps({'operation': operation,
        'exception_type': type(caught.value).__module__+'.'+type(caught.value).__qualname__,
        'message': str(caught.value), 'args': list(caught.value.args),
        'production_registry_replaced': False}, indent=2))


def test_real_constructor_and_resource_identity(directory, tmp_path, monkeypatch, store):
    # Host inventory and explicit null client contact are controlled. All
    # constructors and SQLite resources remain real; no native operation runs.
    monkeypatch.setattr(lr.LocalResources, '_refresh', lambda self, db: [])
    clients = PublicClients(ncbi_email=None)
    tools = A102ToolRegistry(store, clients=clients, a102_work_directory=tmp_path/'native')
    assert tools.clients is clients and type(clients) is PublicClients
    assert clients.ncbi_email is None
    assert tools.store is store
    assert tools.local_job_policy.memory_bytes == ENVIRONMENT_BOUNDS['memory_bytes']
    assert tools.local_job_policy.scratch_bytes == 4 * 1024**3
    assert tools.minimap2_configuration['cpu'] == 1
    assert tools.a102_policy.to_dict() == {'memory_bytes': 2*1024**3, 'scratch_bytes': 1024**3}
    adapter = A102ResourceAdapter(tools, store, 'operational-constructor')
    assert adapter.tools is tools and adapter.store is store
    assert adapter.run_id == 'operational-constructor'
    assert adapter.selection()['allocation'] == {'cpu': 1, **tools.a102_policy.to_dict()}
    descriptor = tools.local_resources.as_record()
    assert descriptor['version'] == 'shared_local_resources_v2'
    assert lr.LocalResources.reopen(descriptor).as_record() == descriptor
    assert tools.resource_binding()['local_resources'] == descriptor
    (tmp_path/'raw-current-constructor.json').write_text(json.dumps({
        'resource_binding': tools.resource_binding(),
        'a102_policy': tools.a102_policy.to_dict(),
        'client_configuration': {'ncbi_email': clients.ncbi_email},
        'client_type': type(clients).__module__+'.'+type(clients).__qualname__,
        'registry_retains_client_identity': tools.clients is clients,
        'production_registry_replaced': False}, indent=2))


@pytest.mark.parametrize('settings,reason', [
    ({'max_running_jobs': 1}, 'invalid_local_resource_settings'),
    ({'job_slots': 1}, 'invalid_local_resource_settings'),
    ({'memory_bytes': 20*1024**3}, 'local_resource_limits_exceed_environment_bounds'),
    ({'cpu_threads': True}, 'invalid_local_resource_limits'),
    ({'memory_bytes': 0}, 'invalid_local_resource_limits'),
], ids=['retired_count', 'retired_slots', 'memory_bound', 'boolean', 'zero'])
def test_current_settings_reject_invalid(settings, reason, directory):
    with pytest.raises(ValueError) as caught:
        lr.LocalResources.configured(settings)
    assert type(caught.value) is ValueError and str(caught.value) == reason


class Handle:
    def __init__(self, path, unit='gene-local-job-operational-fixture.service'):
        self.path = path
        self.value = {'unit': unit, 'stage': 'prepared'}
        path.write_text(json.dumps(self.value))

    def read(self):
        return deepcopy(self.value)


def test_original_historical_count_admission(directory, tmp_path, monkeypatch):
    # Explicit historical-policy fixture, separate from the six untouched real
    # constructor failures. These literals match the retained git-show source.
    historical = {'max_running_jobs': 1, 'cpu_threads': 1,
                  'memory_bytes': 20*1024**3, 'scratch_bytes': 4*1024**3}
    monkeypatch.setattr(lr, '_limits', lambda settings: deepcopy(historical))
    resource = lr.LocalResources.configured()
    assert resource.definition['version'] == 'shared_local_resources_v1'
    jobs = [{'state': 'reserved', 'allocation': {'cpu_threads': 0, 'memory_bytes': 0, 'scratch_bytes': 0}}]
    monkeypatch.setattr(resource, '_refresh', lambda db: jobs)
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(Handle(tmp_path/'old.json'), cpu_threads=1,
                         policy=local_jobs.LocalJobPolicy(1024, 1024))
    assert caught.value.code == 'local_resource_busy'
    assert resource.snapshot()['available']['job_slots'] == 0
    assert resource.snapshot()['available']['cpu_threads'] == 1
    (tmp_path/'raw-historical-admission.json').write_text(json.dumps({
        'explicit_historical_configuration_fixture': historical,
        'error': {'type': type(caught.value).__module__+'.'+type(caught.value).__qualname__,
                  'code': caught.value.code, 'phase': caught.value.phase,
                  'operational': caught.value.operational},
        'resource_definition': resource.as_record()}, indent=2))


def test_original_historical_count_recommendation():
    from gene_annotation_episode.episodic_workflow.root.a102.execution_guidance import compare_routes
    route = {'binding_available': True, 'capacity_state': 'fresh',
             'available': {'cpu_threads': 1, 'memory_bytes': 1024, 'scratch_bytes': 1024, 'job_slots': 0}}
    result = compare_routes(route, None, requirements={'cpu_threads': 1, 'memory_bytes': 512})
    assert result['preferred'] is None
    assert result['routes']['local']['reasons'] == ['no_job_slot']


@pytest.mark.parametrize('kind', ['empty', 'many_zero_allocations', 'memory_busy', 'cpu_busy', 'unknown'],
                         ids=['empty', 'many_zero_allocations', 'memory_busy', 'cpu_busy', 'unknown'])
def test_atomic_resource_admission(kind, directory, tmp_path, monkeypatch):
    resource = lr.LocalResources.configured()
    zero = {'cpu_threads': 0, 'memory_bytes': 0, 'scratch_bytes': 0}
    # Synthetic host observation controls isolate arithmetic from job count;
    # no synthetic row is inserted or represented as an actual launched job.
    jobs = [] if kind == 'empty' else [
        {'state': 'reserved', 'allocation': dict(zero)} for _ in range(8)]
    if kind in ('cpu_busy', 'memory_busy', 'unknown'):
        field = 'memory_bytes' if kind == 'memory_busy' else 'cpu_threads'
        jobs = [{'state': 'capacity_unavailable' if kind == 'unknown' else 'running',
                 'allocation': {**zero, field: resource.definition['limits'][field]}}]
    monkeypatch.setattr(resource, '_refresh', lambda db: jobs)
    handle = Handle(tmp_path/'handle.json')
    policy = local_jobs.LocalJobPolicy(1024, 1024)
    if kind in ('empty', 'many_zero_allocations', 'cpu_busy'):
        reservation = resource.reserve(handle, cpu_threads=1, policy=policy)
        assert reservation['allocation'] == {'cpu_threads': 1, 'memory_bytes': 1024, 'scratch_bytes': 1024}
        resource.validate_reservation(reservation)
        with resource._transaction() as db:
            assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0] == 1
        view = resource.snapshot()
        assert 'job_slots' not in view['reserved'] and 'job_slots' not in view['available']
        assert 'max_running_jobs' not in view['limits']
        resource.release_reservation(reservation)
        with pytest.raises(ValueError, match='local_resource_reservation_unavailable'):
            resource.validate_reservation(reservation)
    else:
        with pytest.raises(AcquisitionError) as caught:
            resource.reserve(handle, cpu_threads=1, policy=policy)
        assert caught.value.code == ('local_job_boundary_unavailable' if kind == 'unknown' else 'local_resource_busy')
        with resource._transaction() as db:
            assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0] == 0


def historical_resource(directory):
    resource = lr.LocalResources.configured()
    record = resource.as_record()
    record['version'] = 'shared_local_resources_v1'
    record['limits'] = {'max_running_jobs': 1, 'cpu_threads': 1,
                        'memory_bytes': 20*1024**3, 'scratch_bytes': 4*1024**3}
    with resource._transaction() as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (json.dumps(record, sort_keys=True),))
        db.execute('INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?,?)', (
            'historical.service', 'historical-token', str(directory/'old-handle.json'),
            1, 20*1024**3, 4*1024**3, 123, 'saved-start', 'saved-boot', 'saved-time'))
    return record


@pytest.mark.parametrize('operation', ['read', 'validate', 'release', 'reserve', 'snapshot', 'constructor'],
                         ids=['read', 'validate', 'release', 'reserve', 'snapshot', 'constructor'])
def test_historical_policy_preserves_resource_admission(operation, directory, tmp_path,monkeypatch):
    definition = historical_resource(directory)
    resource = lr.LocalResources.reopen(deepcopy(definition))
    assert resource.as_record() == definition
    reservation = {'resource': deepcopy(definition), 'reservation_ref': 'historical-token',
                   'execution_handle': 'historical.service',
                   'allocation': {'cpu_threads': 1, 'memory_bytes': 20*1024**3, 'scratch_bytes': 4*1024**3}}
    if operation == 'validate':
        resource.validate_reservation(reservation)
    elif operation == 'release':
        resource.release_reservation(reservation)
        with pytest.raises(ValueError, match='local_resource_reservation_unavailable'):
            resource.validate_reservation(reservation)
    elif operation in ('reserve', 'snapshot'):
        # Controlled host observations isolate count from actual allocations.
        jobs=[{'state':'reserved','allocation':{'cpu_threads':0,'memory_bytes':0,'scratch_bytes':0}}]*8
        monkeypatch.setattr(resource,'_refresh',lambda db:jobs)
        if operation=='reserve':
            added=resource.reserve(Handle(tmp_path/'new.json'),cpu_threads=1,
                policy=local_jobs.LocalJobPolicy(1024,1024))
            resource.validate_reservation(added);resource.release_reservation(added)
        view=resource.snapshot()
        assert view['version']=='shared_local_resources_v1'
        assert view['limits']=={'cpu_threads':1,'memory_bytes':5368709120,'scratch_bytes':4294967296}
        assert 'job_slots' not in view['available'] and 'job_slots' not in view['reserved']
    elif operation=='constructor':
        assert lr.LocalResources.configured().as_record()==definition
    with sqlite3.connect(directory/'capacity.sqlite3') as db:
        assert json.loads(db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]) == definition


@pytest.mark.parametrize('mutation', ['version', 'host', 'directory', 'limits', 'extra', 'reservation'],
                         ids=['version', 'host', 'directory', 'limits', 'extra', 'reservation'])
def test_historical_identity_rejects_conflict(mutation, directory):
    original = historical_resource(directory)
    record = deepcopy(original)
    if mutation == 'version': record['version'] = 'foreign-version'
    elif mutation == 'host': record['resource_id'] += '-foreign'
    elif mutation == 'directory': record['directory'] += '-absent'
    elif mutation == 'limits': record['limits']['max_running_jobs'] = 2
    elif mutation == 'extra': record['foreign'] = True
    if mutation == 'reservation':
        resource = lr.LocalResources.reopen(record)
        with pytest.raises(ValueError, match='local_resource_reservation_unavailable'):
            resource.validate_reservation({'resource': record, 'reservation_ref': 'foreign',
                'execution_handle': 'historical.service', 'allocation': {}})
    else:
        with pytest.raises(ValueError): lr.LocalResources.reopen(record)
    with sqlite3.connect(directory/'capacity.sqlite3') as db:
        assert json.loads(db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]) == original


def test_route_recommendation_uses_resources_not_count():
    from gene_annotation_episode.episodic_workflow.root.a102.execution_guidance import compare_routes
    route = {'binding_available': True, 'capacity_state': 'fresh',
             'available': {'cpu_threads': 1, 'memory_bytes': 1024, 'scratch_bytes': 1024, 'job_slots': 0}}
    result = compare_routes(route, None, requirements={'cpu_threads': 1, 'memory_bytes': 512})
    assert result['preferred'] == 'local' and result['admission_reserved'] is False


def test_retry_waits_for_actual_allocation_and_cancels(monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102.tests.a102_native_fixture import NativeCase
    views = iter([
        {'state': 'busy', 'available': {'cpu_threads': 1, 'memory_bytes': 0, 'scratch_bytes': 100}},
        {'state': 'available', 'available': {'cpu_threads': 1, 'memory_bytes': 100, 'scratch_bytes': 100}},
    ])
    fake = SimpleNamespace(capacity_retries={'episode': 0}, last_decisions={'episode': {'selection': 'original'}},
        tools=SimpleNamespace(a102_policy=local_jobs.LocalJobPolicy(100, 100),
                              local_resources=SimpleNamespace(snapshot=lambda: next(views))))
    sleeps = []
    async def sleep(delay): sleeps.append(delay)
    monkeypatch.setattr(asyncio, 'sleep', sleep)
    result = asyncio.run(NativeCase.retry_capacity(fake, 'episode', {'feedback': {'code': 'local_resource_busy'}}))
    assert result == fake.last_decisions['episode'] and result is not fake.last_decisions['episode']
    assert sleeps == [.5] and fake.capacity_retries['episode'] == 1
    fake.tools.local_resources.snapshot = lambda: {'state': 'unknown', 'available': {}}
    async def cancel(delay): raise asyncio.CancelledError
    monkeypatch.setattr(asyncio, 'sleep', cancel)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(NativeCase.retry_capacity(fake, 'episode', {'feedback': {'code': 'local_resource_busy'}}))


def test_actual_native_receipt_and_machine_bounds(tmp_path, monkeypatch):
    # Required connected check under the normal single-workflow launcher.
    # No fake status, control group, native outcome, timeout, or count ceiling.
    from gene_annotation_episode.episodic_workflow.root.a102.native_lifecycle import run_blocking
    # Use the actual launcher's own run/slice instead of an unscoped shared
    # host directory; this preserves other windows' independent ownership.
    monkeypatch.delenv(lr.DIRECTORY_ENV, raising=False)
    work = tmp_path/'native'
    work.mkdir()
    result = run_blocking(['/bin/true'], cwd=work,
        policy=local_jobs.LocalJobPolicy(512*1024**2, 1024**2), cpu_threads=1)
    assert result.returncode == 0
    verified = result.metadata['verified_cgroup']
    assert verified['memory_max'] == 512*1024**2 and verified['memory_swap_max'] == 0
    assert verified['cpu_threads'] == 1
    quota, period = map(int, verified['cpu_max'].split())
    assert quota == period
    (tmp_path/'raw-native-result.json').write_text(json.dumps({
        'returncode': result.returncode, 'metadata': result.metadata,
        'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path)}, indent=2))


def resume_fixture(directory, tmp_path, monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    from gene_annotation_episode.workflow_budget import active_budget
    resource = lr.LocalResources.configured()
    monkeypatch.setattr(resource, '_refresh', lambda db: [])
    raw = Handle(tmp_path/'resume-handle.json')
    policy = local_jobs.LocalJobPolicy(1024, 1024)
    reservation = resource.reserve(raw, cpu_threads=1, policy=policy)
    body = {'version': native.VERSION, 'unit': raw.value['unit'], 'stage': 'submitting',
        'cwd': str(tmp_path), 'paths': {'release': str(tmp_path/'released'), 'ready': str(tmp_path/'ready')},
        'metadata': {'local_resources': resource.as_record(), 'policy': policy.to_dict(),
                     'cpu_threads': 1, 'whole_workflow_budget': active_budget()},
        'capacity_reservation': reservation}
    raw.path.write_text(json.dumps(body))
    return native, resource, native.NativeJobHandle(raw.path), body


@pytest.mark.parametrize('mutation', ['historical_record_conflict','metadata_v1','reservation_v1',
    'malformed_descriptor','malformed_reservation','conflicting','unknown_version',
    'empty_allocation','allocation_mismatch','active_memory_bound','metadata_malformed','cpu_boolean'],
    ids=['historical_record_conflict','metadata_v1','reservation_v1','malformed_descriptor','malformed_reservation',
         'conflicting','unknown_version','empty_allocation','allocation_mismatch','active_memory_bound',
         'metadata_malformed','cpu_boolean'])
def test_direct_resume_rejects_unreleased_authority(mutation, directory, tmp_path, monkeypatch):
    native, resource, handle, body = resume_fixture(directory, tmp_path, monkeypatch)
    if mutation in {'historical_record_conflict','metadata_v1'}:
        body['metadata']['local_resources']['version'] = 'shared_local_resources_v1'
    if mutation in {'historical_record_conflict','reservation_v1'}:
        body['capacity_reservation']['resource']['version'] = 'shared_local_resources_v1'
    if mutation=='historical_record_conflict':
        # Structurally valid saved v1 record, but the actual DB still holds v2.
        body['metadata']['local_resources']['limits']['max_running_jobs']=1
        body['capacity_reservation']['resource']['limits']['max_running_jobs']=1
    if mutation == 'malformed_descriptor': body['metadata']['local_resources'] = None
    if mutation == 'malformed_reservation': body['capacity_reservation'] = None
    if mutation == 'conflicting': body['capacity_reservation']['resource']['resource_id'] += '-foreign'
    if mutation == 'unknown_version':
        body['metadata']['local_resources']['version'] = 'unknown'
        body['capacity_reservation']['resource']['version'] = 'unknown'
    if mutation == 'empty_allocation': body['capacity_reservation']['allocation'] = {}
    if mutation == 'allocation_mismatch': body['capacity_reservation']['allocation']['memory_bytes'] += 1
    if mutation == 'active_memory_bound': body['metadata']['policy']['memory_bytes'] = ENVIRONMENT_BOUNDS['memory_bytes']+1
    if mutation == 'metadata_malformed': body['metadata'] = None
    if mutation == 'cpu_boolean': body['capacity_reservation']['allocation']['cpu_threads'] = True
    handle.path.write_text(json.dumps(body));original = handle.path.read_bytes()
    events = []
    def forbidden(*args, **kwargs):
        events.append('unexpected-handshake');raise AssertionError('unreleased authority must reject before handshake')
    monkeypatch.setattr(native, '_ensure_event_registration', forbidden)
    monkeypatch.setattr(native, '_properties', forbidden)
    monkeypatch.setattr(native, 'atomic_json', forbidden)
    expected=ValueError if mutation in {'historical_record_conflict','active_memory_bound'} else AcquisitionError
    with pytest.raises(expected) as caught:
        native.resume_start(handle)
    assert type(caught.value) is expected
    if mutation=='historical_record_conflict':
        assert str(caught.value)=='local_resource_binding_conflict'
    elif mutation=='active_memory_bound':
        assert str(caught.value)=='native_request_exceeds_environment_bounds'
    else:
        assert caught.value.phase=='local_preflight'
        assert caught.value.code == 'local_job_boundary_unavailable'
    assert not events and not Path(body['paths']['release']).exists()
    assert handle.path.read_bytes() == original
    (tmp_path/'raw-resume-rejection.json').write_text(json.dumps({'case': mutation,
        'before': json.loads(original), 'after': json.loads(handle.path.read_bytes()),
        'error': {'type': type(caught.value).__module__+'.'+type(caught.value).__qualname__,
                  'code': getattr(caught.value,'code',None), 'phase': getattr(caught.value,'phase',None),
                  'operational': getattr(caught.value,'operational',None),'message':str(caught.value)},
        'handshake_events': events, 'released': False}, indent=2))


def test_current_resume_reaches_original_handshake(directory, tmp_path, monkeypatch):
    native, resource, handle, body = resume_fixture(directory, tmp_path, monkeypatch)
    marker = RuntimeError('stop at original event-registration boundary')
    events = []
    def stop(selected, saved):
        assert selected is handle and saved == body
        events.append('original-event-registration');raise marker
    monkeypatch.setattr(native, '_ensure_event_registration', stop)
    with pytest.raises(RuntimeError) as caught: native.resume_start(handle)
    assert caught.value is marker and events == ['original-event-registration']
    assert not Path(body['paths']['release']).exists()
    resource.validate_reservation(body['capacity_reservation'])


def test_prepared_resume_keeps_original_delegation(directory, tmp_path, monkeypatch):
    native, resource, handle, body = resume_fixture(directory, tmp_path, monkeypatch)
    body['stage'] = 'prepared';handle.path.write_text(json.dumps(body))
    marker, cancellation = object(), object()
    def original(selected, *, cancel_event):
        assert selected is handle and cancel_event is cancellation
        return marker
    monkeypatch.setattr(native, 'start_prepared', original)
    assert native.resume_start(handle, cancel_event=cancellation) is marker


def test_already_released_historical_resume_is_read_only(directory, tmp_path, monkeypatch):
    native, resource, handle, body = resume_fixture(directory, tmp_path, monkeypatch)
    body['metadata']['local_resources']['version'] = 'shared_local_resources_v1'
    body['capacity_reservation']['resource']['version'] = 'shared_local_resources_v1'
    handle.path.write_text(json.dumps(body));original=handle.path.read_bytes()
    Path(body['paths']['release']).touch()
    def forbidden(*args, **kwargs):raise AssertionError('released read must not reauthorize admission')
    monkeypatch.setattr(native, '_validate_unreleased_resume_capacity', forbidden)
    assert native.resume_start(handle) is handle and handle.path.read_bytes()==original


@pytest.mark.parametrize('operation',['status','collect','cancel','release'],ids=['status','collect','cancel','release'])
def test_historical_completed_receipt_cleanup(operation, directory, tmp_path, monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    definition = historical_resource(directory)
    handle = native.NativeJobHandle(tmp_path/'historical-handle.json')
    files = {name:str(tmp_path/('historical-'+name)) for name in ('release','ready','status','result')}
    ended = {'ended': {'boot_id':'recorded-old-boot','monotonic_ns':20},'SERVICE_RESULT':'success'}
    receipt = {'native_returncode':0,'observed_scratch_bytes':0,'resource_failure':None,'execution_failure':None}
    for name in ('release','ready'):Path(files[name]).touch()
    Path(files['status']).write_text(json.dumps(ended));Path(files['result']).write_text(json.dumps(receipt))
    stdout,stderr=tmp_path/'historical-stdout',tmp_path/'historical-stderr';stdout.write_text('original');stderr.write_text('')
    body={'version':native.VERSION,'unit':'historical.service','stage':'released','paths':files,
        'stdout':str(stdout),'stderr':str(stderr),'boot_id':'recorded-old-boot','started_monotonic_ns':10,
        'metadata':{'local_resources':definition,'policy':{'memory_bytes':20*1024**3,'scratch_bytes':4*1024**3}},
        'capacity_reservation':{'resource':definition,'reservation_ref':'historical-token','execution_handle':'historical.service',
            'allocation':{'cpu_threads':1,'memory_bytes':20*1024**3,'scratch_bytes':4*1024**3}}}
    handle.path.write_text(json.dumps(body));original=handle.path.read_bytes()
    saved={name:Path(path).read_bytes() for name,path in files.items()}
    calls=[]
    monkeypatch.setattr(native,'_properties',lambda unit:{'ActiveState':'inactive'})
    monkeypatch.setattr(native,'_control',lambda argv:calls.append(argv))
    if operation=='status':
        result=native.status(handle);assert result['terminal'] and result['native_receipt']==receipt
        assert result['metadata']['policy']==body['metadata']['policy']
    elif operation=='collect':
        result=native.collect(handle);assert result.returncode==0 and result.metadata['policy']==body['metadata']['policy']
    elif operation=='cancel':native.cancel(handle)
    else:native.release(handle)
    if operation!='release':
        assert handle.path.read_bytes()==original
        assert {name:Path(path).read_bytes() for name,path in files.items()}==saved
    else:assert not handle.path.exists() and all(not Path(path).exists() for path in files.values())
    with sqlite3.connect(directory/'capacity.sqlite3') as db:
        assert json.loads(db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0])==definition
        assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==0


@pytest.mark.parametrize('case', ['borrowed_unit','copied_handle','missing_execution_handle'],
    ids=['borrowed_unit','copied_handle','missing_execution_handle'])
def test_direct_resume_rejects_borrowed_current_reservation(case, directory, tmp_path, monkeypatch):
    native, resource, handle, body = resume_fixture(directory, tmp_path, monkeypatch)
    if case == 'borrowed_unit':
        # A genuine different unit's current reservation, with the same resource,
        # allocation and workflow. Original validation accepts it for THAT unit.
        resource.release_reservation(body['capacity_reservation'])
        other = Handle(tmp_path/'other-handle.json', unit='gene-local-job-other.service')
        body['capacity_reservation'] = resource.reserve(other, cpu_threads=1,
            policy=local_jobs.LocalJobPolicy(**body['metadata']['policy']))
        assert body['capacity_reservation']['execution_handle'] != body['unit']
    elif case == 'copied_handle':
        # Unit/token/allocation remain genuine; only the actual handle path is
        # different from the immutable path retained in the reservation row.
        handle = native.NativeJobHandle(tmp_path/'copied-handle.json')
    reservation = deepcopy(body['capacity_reservation'])
    resource.validate_reservation(reservation)
    if case == 'missing_execution_handle': body['capacity_reservation'].pop('execution_handle')
    handle.path.write_text(json.dumps(body));original=handle.path.read_bytes()
    with resource._transaction() as db:
        before=[dict(row) for row in db.execute('SELECT * FROM reservations ORDER BY unit')]
    events=[]
    def forbidden(*args, **kwargs):
        events.append('unexpected-handshake');raise AssertionError('borrowed reservation reached handshake')
    monkeypatch.setattr(native,'_ensure_event_registration',forbidden)
    monkeypatch.setattr(native,'_properties',forbidden)
    monkeypatch.setattr(native,'atomic_json',forbidden)
    with pytest.raises(AcquisitionError) as caught:native.resume_start(handle)
    assert type(caught.value) is AcquisitionError
    assert caught.value.code=='local_job_boundary_unavailable' and caught.value.phase=='local_preflight'
    reason=('native_reservation_handle_conflict' if case=='copied_handle'
            else 'authenticated_local_resource_reservation_required')
    assert caught.value.operational=={'reason':reason}
    assert not events and not Path(body['paths']['release']).exists()
    assert handle.path.read_bytes()==original
    resource.validate_reservation(reservation)
    with resource._transaction() as db:
        after=[dict(row) for row in db.execute('SELECT * FROM reservations ORDER BY unit')]
    assert before==after
    (tmp_path/'raw-resume-owner-rejection.json').write_text(json.dumps({'case':case,
        'actual_handle_path':str(handle.path.resolve()),'before':json.loads(original),
        'after':json.loads(handle.path.read_bytes()),'reservations_before':before,'reservations_after':after,
        'original_reservation_validation_passed':True,'handshake_events':events,'released':False,
        'error':{'type':type(caught.value).__module__+'.'+type(caught.value).__qualname__,
                 'code':caught.value.code,'phase':caught.value.phase,'operational':caught.value.operational}},indent=2))


def authenticated_legacy_capacity(directory,monkeypatch):
    """Real own SQLite/host/slice identity with explicit retained v1 fixture bytes."""
    from gene_annotation_episode.workflow_budget import active_budget
    historical={'max_running_jobs':1,'cpu_threads':1,
        'memory_bytes':21474836480,'scratch_bytes':4294967296}
    if lr.VERSION=='shared_local_resources_v1':
        # Separate retained-policy control: current original A102 defaults lack
        # this section (the six original constructor failures still run).
        # This isolates the actual old lifecycle against its original saved
        # policy; it does not claim the broken current default constructor works.
        def historical_limits(settings):
            assert isinstance(settings,dict) and not set(settings)-set(historical)
            result={**historical,**settings}
            assert all(type(value) is int and value>0 for value in result.values())
            return result
        monkeypatch.setattr(lr,'_limits',historical_limits)
    resource=lr.LocalResources(directory,workflow_slice=active_budget()['slice'])
    record=resource.as_record();record['version']='shared_local_resources_v1';record['limits']=historical
    with resource._transaction() as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1',(json.dumps(record,sort_keys=True),))
    original=json.dumps(record,sort_keys=True)
    resource=lr.LocalResources.reopen(record)
    monkeypatch.setattr(lr.LocalResources,'configured',classmethod(lambda cls,settings=None:resource))
    return resource,original


@pytest.mark.parametrize('operation',['reserve','snapshot','configured','resume'],ids=['reserve','snapshot','configured','resume'])
def test_authenticated_saved_v1_continuation(operation,directory,tmp_path,monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    from gene_annotation_episode.workflow_budget import active_budget
    resource,original=authenticated_legacy_capacity(directory,monkeypatch)
    monkeypatch.setattr(resource,'_refresh',lambda db:[])
    handle=Handle(tmp_path/'saved-active.json');policy=local_jobs.LocalJobPolicy(1024,1024)
    if operation in {'reserve','resume'}:
        reservation=resource.reserve(handle,cpu_threads=1,policy=policy)
        resource.validate_reservation(reservation)
    if operation=='resume':
        body={'version':native.VERSION,'unit':handle.value['unit'],'stage':'submitting','cwd':str(tmp_path),
            'paths':{'release':str(tmp_path/'release')},
            'metadata':{'local_resources':resource.as_record(),'policy':policy.to_dict(),'cpu_threads':1,
                        'whole_workflow_budget':active_budget()},'capacity_reservation':reservation}
        handle.path.write_text(json.dumps(body));selected=native.NativeJobHandle(handle.path)
        marker=RuntimeError('original event-registration boundary');events=[]
        def stop(actual,saved):
            assert actual is selected and saved==body
            events.append('original_event_registration');raise marker
        monkeypatch.setattr(native,'_ensure_event_registration',stop)
        with pytest.raises(RuntimeError) as caught:native.resume_start(selected)
        assert caught.value is marker and events==['original_event_registration']
        assert selected.read()==body and not Path(body['paths']['release']).exists()
    elif operation=='snapshot':
        view=resource.snapshot()
        if lr.VERSION=='shared_local_resources_v1':assert view['available']['job_slots']==1
        else:
            assert 'job_slots' not in view['available']
            assert view['limits']=={'cpu_threads':1,'memory_bytes':5368709120,'scratch_bytes':4294967296}
    elif operation=='configured':
        # Exercise the actual constructor against the existing record, not the
        # deliberately controlled configured port used by the native fixtures.
        reopened=lr.LocalResources(directory,workflow_slice=active_budget()['slice'])
        assert reopened.as_record()==resource.as_record()
    with resource._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]==original
    (tmp_path/'raw-saved-v1.json').write_text(json.dumps({'operation':operation,'definition':resource.as_record(),
        'configuration_bytes':original,'active_resource_version':lr.VERSION,'accepted':True},indent=2))


@pytest.mark.parametrize('resource_name',['memory','cpu'],ids=['memory','cpu'])
def test_saved_v1_actual_machine_bound(resource_name,directory,tmp_path,monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    from gene_annotation_episode.workflow_budget import active_budget
    resource,original=authenticated_legacy_capacity(directory,monkeypatch)
    policy=local_jobs.LocalJobPolicy(21474836480 if resource_name=='memory' else 1024,1024)
    body={'version':native.VERSION,'unit':'gene-local-job-over-bound.service','stage':'prepared','cwd':str(tmp_path),
        'metadata':{'local_resources':resource.as_record(),'policy':policy.to_dict(),
            'cpu_threads':2 if resource_name=='cpu' else 1,'whole_workflow_budget':active_budget()}}
    path=tmp_path/'over-bound.json';path.write_text(json.dumps(body));before=path.read_bytes()
    if resource_name=='cpu':
        # Canonical CPU metadata correction is an independently authenticated
        # prerequisite. Own original count-gated admission is tested separately;
        # a requested count is no longer a canonical machine-bound rejection.
        from gene_annotation_episode.workflow_budget import native_budget
        actual=active_budget()
        assert native_budget(policy,2,tmp_path)==actual
        assert actual['environment_bounds']=={'cpu_percent':100,'memory_bytes':5368709120,'swap_bytes':0}
        assert path.read_bytes()==before
        (tmp_path/'raw-thread-budget.json').write_text(json.dumps({
            'requested_cpu_threads':2,'actual_owner':actual,
            'policy':policy.to_dict(),'accepted':True,'handle_unchanged':True},indent=2))
        return
    def forbidden(*args,**kwargs):raise AssertionError('over-bound request reached event/dispatch')
    monkeypatch.setattr(native,'_ensure_event_registration',forbidden)
    monkeypatch.setattr(native,'_dispatch_prepared',forbidden)
    with pytest.raises(ValueError) as caught:native.start_prepared(native.NativeJobHandle(path))
    assert type(caught.value) is ValueError and str(caught.value)=='native_request_exceeds_environment_bounds'
    assert path.read_bytes()==before
    with resource._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]==original
        assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==0
    (tmp_path/'raw-saved-bound.json').write_text(json.dumps({'resource':resource_name,'error_type':'builtins.ValueError',
        'error':str(caught.value),'definition':resource.as_record(),'handle_before':json.loads(before),'handle_after':json.loads(path.read_bytes())},indent=2))


@pytest.mark.parametrize('kind',['descriptorless','descriptor_only','reservation_only'],ids=['descriptorless','descriptor_only','reservation_only'])
def test_original_optional_reservation_boundary(kind,directory,tmp_path,monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    from gene_annotation_episode.workflow_budget import active_budget
    resource,_=authenticated_legacy_capacity(directory,monkeypatch)
    monkeypatch.setattr(resource,'_refresh',lambda db:[])
    raw=Handle(tmp_path/'optional.json');policy=local_jobs.LocalJobPolicy(1024,1024)
    body={'version':native.VERSION,'unit':raw.value['unit'],'stage':'submitting','cwd':str(tmp_path),
        'paths':{'release':str(tmp_path/'released')},'metadata':{'policy':policy.to_dict(),'whole_workflow_budget':active_budget()}}
    if kind=='descriptor_only':body['metadata'].update(local_resources=resource.as_record(),cpu_threads=1)
    if kind=='reservation_only':body['capacity_reservation']=resource.reserve(raw,cpu_threads=1,policy=policy)
    raw.path.write_text(json.dumps(body));handle=native.NativeJobHandle(raw.path);before=raw.path.read_bytes()
    marker=RuntimeError('original event boundary');events=[]
    def original(selected,saved):
        assert selected is handle and saved==body
        events.append('original');raise marker
    monkeypatch.setattr(native,'_ensure_event_registration',original)
    with pytest.raises(RuntimeError) as caught:native.resume_start(handle)
    assert caught.value is marker and events==['original'] and raw.path.read_bytes()==before
    assert not Path(body['paths']['release']).exists()
    (tmp_path/'raw-optional-authority.json').write_text(json.dumps({'kind':kind,'body':body,
        'reached_original_event_boundary':True,'database_reservation_claimed':kind=='reservation_only'},indent=2))


@pytest.mark.parametrize('kind',['descriptorless','prepared_fallback','saved_v1','earlier_cwd'],ids=['descriptorless','prepared_fallback','saved_v1','earlier_cwd'])
def test_actual_legacy_native_continuation(kind,directory,tmp_path,monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    resource,original=authenticated_legacy_capacity(directory,monkeypatch)
    work=tmp_path/'legacy-native';work.mkdir()
    policy=local_jobs.LocalJobPolicy(512*1024**2,1024**2)
    handle=native.prepare_job(['/bin/true'],cwd=work,policy=policy,handle_path=work/'handle.json',cpu_threads=1)
    body=handle.read()
    if kind in {'descriptorless','prepared_fallback','earlier_cwd'}:
        body['metadata'].pop('local_resources');body['metadata'].pop('cpu_threads')
        handle.path.write_text(json.dumps(body))
    earlier=None
    if kind=='earlier_cwd':
        import hashlib,os
        from gene_annotation_episode.workflow_budget import active_budget
        prepared=Path(os.environ['GENE_OPERATIONAL_LEGACY_PREPARATION']).resolve()
        earlier=(prepared/'before').resolve()
        assert earlier.is_dir() and 'runs' in earlier.parts
        assert not earlier.is_relative_to(Path(active_budget()['run_directory']).resolve())
        budgets=[p/'workflow-budget.json' for p in prepared.parents if (p/'workflow-budget.json').is_file()]
        retained=json.loads(budgets[0].read_bytes())
        assert retained['run_directory']!=active_budget()['run_directory']
        request=json.loads(Path(body['paths']['request']).read_bytes())
        request['cwd']=body['cwd']=str(earlier)
        body['metadata']['whole_workflow_budget']=retained
        Path(body['paths']['request']).write_text(json.dumps(request))
        body['request_sha256']=hashlib.sha256(Path(body['paths']['request']).read_bytes()).hexdigest()
        handle.path.write_text(json.dumps(body))
        # Constructed legacy shape: original request format, real earlier cwd,
        # actual retained budget provenance and current actual worker/unit.
        # No past execution or cross-run restoration success is claimed.
    try:
        if kind in {'descriptorless','earlier_cwd'}:
            # Actual original no-reservation worker branch; the real ready hash,
            # Slice/BindsTo, memory/swap and worker receipt must all verify.
            native._dispatch_prepared(handle,body,cancel_event=None)
        else:native.start_prepared(handle)
        result=native.wait_job(handle)
        assert result.returncode==0
        verified=result.metadata['verified_cgroup']
        assert verified['memory_max']==512*1024**2 and verified['memory_swap_max']==0
        assert verified['workflow_slice']==resource.as_record()['workflow_slice']
        if kind in {'descriptorless','earlier_cwd'}:assert 'cpu_threads' not in verified and 'capacity_reservation' not in handle.read()
        else:assert verified['cpu_threads']==1 and handle.read()['capacity_reservation']['resource']==resource.as_record()
        request_raw=Path(body['paths']['request']).read_bytes()
        import hashlib
        assert hashlib.sha256(request_raw).hexdigest()==handle.read()['request_sha256']
        request=json.loads(request_raw)
        assert request['cwd']==handle.read()['cwd']
        ready_raw=Path(body['paths']['ready']).read_bytes()
        assert json.loads(ready_raw)['request_sha256']==handle.read()['request_sha256']
        if earlier is not None:assert request['cwd']==str(earlier) and result.metadata['whole_workflow_budget']==retained
        (tmp_path/'raw-legacy-native.json').write_text(json.dumps({'kind':kind,'returncode':result.returncode,
            'metadata':result.metadata,'handle':handle.read(),'configuration_bytes':original,
            'request':request,'request_raw':request_raw.decode(),'ready_raw':ready_raw.decode(),
            'request_sha256':hashlib.sha256(request_raw).hexdigest()},indent=2))
    finally:
        if not native.status(handle)['quiescent']:native.cancel(handle)
        native.release(handle)
    with resource._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]==original
        assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==0


@pytest.mark.parametrize('conflict',['token','unit','handle'],ids=['token','unit','handle'])
def test_saved_v1_reservation_identity_conflict(conflict,directory,tmp_path,monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    from gene_annotation_episode.workflow_budget import active_budget
    resource,_=authenticated_legacy_capacity(directory,monkeypatch)
    monkeypatch.setattr(resource,'_refresh',lambda db:[])
    raw=Handle(tmp_path/'identity.json');policy=local_jobs.LocalJobPolicy(1024,1024)
    reservation=resource.reserve(raw,cpu_threads=1,policy=policy)
    body={'version':native.VERSION,'unit':raw.value['unit'],'stage':'submitting','cwd':str(tmp_path),
        'paths':{'release':str(tmp_path/'release')},'metadata':{'local_resources':resource.as_record(),
        'policy':policy.to_dict(),'cpu_threads':1,'whole_workflow_budget':active_budget()},'capacity_reservation':reservation}
    if conflict=='token':reservation['reservation_ref']='not-the-saved-token'
    elif conflict=='unit':body['unit']='gene-local-job-different.service'
    else:raw.path=tmp_path/'copied-identity.json'
    raw.path.write_text(json.dumps(body));handle=native.NativeJobHandle(raw.path);before=raw.path.read_bytes()
    with resource._transaction() as db:rows=[dict(row) for row in db.execute('SELECT * FROM reservations')]
    marker=RuntimeError('original event boundary')
    def event(*args,**kwargs):raise marker
    monkeypatch.setattr(native,'_ensure_event_registration',event)
    if lr.VERSION=='shared_local_resources_v1':
        # Original ordering reaches event registration before reservation checks.
        with pytest.raises(RuntimeError) as caught:native.resume_start(handle)
        assert caught.value is marker
    else:
        expected=ValueError if conflict=='token' else AcquisitionError
        with pytest.raises(expected) as caught:native.resume_start(handle)
        assert type(caught.value) is expected
        if conflict=='token':assert str(caught.value)=='local_resource_reservation_unavailable'
        else:assert caught.value.code=='local_job_boundary_unavailable'
    assert raw.path.read_bytes()==before and not Path(body['paths']['release']).exists()
    with resource._transaction() as db:assert [dict(row) for row in db.execute('SELECT * FROM reservations')]==rows
    (tmp_path/'raw-saved-conflict.json').write_text(json.dumps({'conflict':conflict,'active_resource_version':lr.VERSION,
        'exception_type':type(caught.value).__module__+'.'+type(caught.value).__qualname__,'message':str(caught.value),
        'handle_unchanged':True,'rows_unchanged':True},indent=2))


@pytest.mark.parametrize('kind',['current','saved_v1','historical_child','prepared_fallback','descriptorless'],
                         ids=['current','saved_v1','historical_child','prepared_fallback','descriptorless'])
def test_actual_requested_threads_under_authenticated_ancestor(kind,directory,tmp_path,monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    from gene_annotation_episode.workflow_budget import active_budget
    actual=active_budget()
    assert actual['environment_bounds']=={'cpu_percent':100,'memory_bytes':5368709120,'swap_bytes':0}
    if kind in {'saved_v1','historical_child'}:
        resource,configuration=authenticated_legacy_capacity(directory,monkeypatch)
    else:
        resource=lr.LocalResources(directory,workflow_slice=actual['slice'])
        with resource._transaction() as db:
            configuration=db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]
        monkeypatch.setattr(lr.LocalResources,'configured',classmethod(lambda cls,settings=None:resource))
    work=tmp_path/'thread-metadata-native';work.mkdir()
    policy=local_jobs.LocalJobPolicy(512*1024**2,1024**2)
    handle=native.prepare_job(['/bin/true'],cwd=work,policy=policy,handle_path=work/'handle.json',cpu_threads=3)
    body=handle.read()
    assert body['metadata']['cpu_threads']==3
    if kind in {'prepared_fallback','descriptorless'}:
        body['metadata'].pop('local_resources')
        handle.path.write_text(json.dumps(body))
    dispatches=[]
    original_run=native.subprocess.run
    def historical_dispatch(argv,*args,**kwargs):
        if isinstance(argv,list) and argv and argv[0]=='systemd-run':
            assert kind=='historical_child' and argv.count('CPUQuota=100%')==1
            argv=list(argv);argv[argv.index('CPUQuota=100%')]='CPUQuota=300%'
            dispatches.append(argv)
        return original_run(argv,*args,**kwargs)
    if kind=='historical_child':
        # Constructed original child-rate fixture. Actual systemd launches the
        # ordinary worker with the saved requested-three quota, still inside the
        # real current100% ancestor. No owner/cgroup/ready observation is mocked.
        monkeypatch.setattr(native.subprocess,'run',historical_dispatch)
    try:
        if kind=='descriptorless':native._dispatch_prepared(handle,body,cancel_event=None)
        else:native.start_prepared(handle)
        result=native.wait_job(handle)
        assert result.returncode==0 and handle.read()['metadata']['cpu_threads']==3
        verified=result.metadata['verified_cgroup']
        assert verified['memory_max']==512*1024**2 and verified['memory_swap_max']==0
        assert verified['workflow_slice']==actual['slice'] and verified['workflow_owner']==actual['unit']
        assert active_budget()==actual
        if kind=='descriptorless':
            assert 'capacity_reservation' not in handle.read() and 'cpu_max' not in verified
        else:
            assert verified['cpu_threads']==3
            quota,period=map(int,verified['cpu_max'].split())
            assert quota==(3 if kind=='historical_child' else 1)*period
            reservation=handle.read()['capacity_reservation']
            assert reservation['allocation']=={'cpu_threads':3,**policy.to_dict()}
            assert reservation['execution_handle']==handle.read()['unit']
        assert len(dispatches)==(1 if kind=='historical_child' else 0)
        (tmp_path/'raw-thread-native.json').write_text(json.dumps({'kind':kind,
            'requested_cpu_threads':3,'actual_owner':actual,'handle':handle.read(),
            'metadata':result.metadata,'returncode':result.returncode,
            'configuration_bytes':configuration,'historical_dispatch_argv':dispatches,
            'constructed_historical_child':kind=='historical_child'},indent=2))
    finally:
        if not native.status(handle)['quiescent']:native.cancel(handle)
        native.release(handle)
    with resource._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]==configuration
        assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==0


@pytest.mark.parametrize('kind',['current','saved_v1'],ids=['current','saved_v1'])
def test_requested_thread_metadata_does_not_consume_admission_slots(kind,directory,tmp_path,monkeypatch):
    if kind=='saved_v1':resource,configuration=authenticated_legacy_capacity(directory,monkeypatch)
    else:
        resource=lr.LocalResources(directory,{'cpu_threads':3})
        with resource._transaction() as db:configuration=db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]
    # Explicit capacity-only control: actual SQLite rows, no claimed native jobs.
    # Only service observation is replaced, preserving each recorded allocation.
    def observed(db):
        return [{'state':'reserved','allocation':{key:row[key] for key in
            ('cpu_threads','memory_bytes','scratch_bytes')}} for row in db.execute('SELECT * FROM reservations')]
    monkeypatch.setattr(resource,'_refresh',observed)
    before=resource.snapshot();policy=local_jobs.LocalJobPolicy(1024,1024)
    first=resource.reserve(Handle(tmp_path/'first.json','thread-first.service'),cpu_threads=64,policy=policy)
    second=resource.reserve(Handle(tmp_path/'second.json','thread-second.service'),cpu_threads=3,policy=policy)
    after=resource.snapshot()
    assert after['reserved']['cpu_threads']==67 and after['available']['cpu_threads']==0
    assert after['state']=='available'
    assert first['allocation']['cpu_threads']==64 and second['allocation']['cpu_threads']==3
    with resource._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]==configuration
    from gene_annotation_episode.episodic_workflow.root.a102.execution_guidance import compare_routes
    route={'binding_available':True,'capacity_state':'fresh','available':after['available']}
    recommendation=compare_routes(route,None,requirements={'cpu_threads':128,'memory_bytes':1024,'scratch_bytes':1024})
    assert recommendation['preferred']=='local'
    (tmp_path/'raw-thread-admission.json').write_text(json.dumps({'kind':kind,
        'definition':resource.as_record(),'before':before,'after':after,'reservations':[first,second],
        'recommendation':recommendation,'configuration_bytes':configuration,
        'service_observation_controlled':True},indent=2))
    resource.release_reservation(first);resource.release_reservation(second)


@pytest.mark.parametrize('kind',['new','empty_database','saved_current','saved_v1'],
                         ids=['new','empty_database','saved_current','saved_v1'])
@pytest.mark.parametrize('setting_request',['unknown','memory','boolean'],ids=['unknown','memory','boolean'])
def test_rejected_custom_initialization_preserves_all_existing_bytes(kind,setting_request,directory,tmp_path,monkeypatch):
    workflow=None
    if kind=='empty_database':
        directory.mkdir();db=sqlite3.connect(directory/'capacity.sqlite3');db.close()
    elif kind=='saved_current':lr.LocalResources(directory)
    elif kind=='saved_v1':
        resource,_=authenticated_legacy_capacity(directory,monkeypatch)
        workflow=resource.as_record()['workflow_slice']
    settings={'unknown':{'invented_field':1},'memory':{'memory_bytes':21474836481},
              'boolean':{'cpu_threads':True}}[setting_request]
    def snapshot():
        return {'exists':directory.exists(),
            'directories':sorted(str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_dir()),
            'files':{str(p.relative_to(directory)):p.read_bytes().hex() for p in directory.rglob('*') if p.is_file()}}
    before=snapshot()
    with pytest.raises(ValueError) as caught:lr.LocalResources(directory,settings,workflow_slice=workflow)
    assert type(caught.value) is ValueError and snapshot()==before
    expected=('local_resource_limits_conflict' if kind=='saved_v1' and setting_request=='memory' else
        {'unknown':'invalid_local_resource_settings','memory':'local_resource_limits_exceed_environment_bounds',
         'boolean':'invalid_local_resource_limits'}[setting_request])
    assert str(caught.value)==expected
    (tmp_path/'raw-custom-initialization.json').write_text(json.dumps({'kind':kind,'request':setting_request,
        'settings':settings,'before':before,'after':snapshot(),'exception_type':'builtins.ValueError',
        'message':str(caught.value)},indent=2))


@pytest.mark.parametrize('count',[0,-1,True,'3',None],ids=['zero','negative','boolean','string','null'])
def test_requested_threads_remain_positive_typed_metadata(count,directory,tmp_path,monkeypatch):
    resource=lr.LocalResources.configured()
    handle=Handle(tmp_path/'typed.json');before=handle.path.read_bytes()
    with resource._transaction() as db:rows=[dict(row) for row in db.execute('SELECT * FROM reservations')]
    with pytest.raises(ValueError,match='^invalid_local_resource_allocation$'):
        resource.reserve(handle,cpu_threads=count,policy=local_jobs.LocalJobPolicy(1024,1024))
    assert handle.path.read_bytes()==before
    with resource._transaction() as db:assert [dict(row) for row in db.execute('SELECT * FROM reservations')]==rows
