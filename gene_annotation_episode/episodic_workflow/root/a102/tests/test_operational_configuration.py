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


@pytest.mark.parametrize('mutation', ['malformed_descriptor','malformed_reservation','conflicting','unknown_version',
    'empty_allocation','allocation_mismatch','active_memory_bound','metadata_malformed','cpu_boolean'],
    ids=['malformed_descriptor','malformed_reservation',
         'conflicting','unknown_version','empty_allocation','allocation_mismatch','active_memory_bound',
         'metadata_malformed','cpu_boolean'])
def test_direct_resume_rejects_unreleased_authority(mutation, directory, tmp_path, monkeypatch):
    native, resource, handle, body = resume_fixture(directory, tmp_path, monkeypatch)
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
    expected=ValueError if mutation=='active_memory_bound' else AcquisitionError
    with pytest.raises(expected) as caught:
        native.resume_start(handle)
    assert type(caught.value) is expected
    if mutation=='active_memory_bound':
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


def test_actual_requested_threads_under_authenticated_ancestor(directory,tmp_path,monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a102 import native_lifecycle as native
    from gene_annotation_episode.workflow_budget import active_budget
    actual=active_budget()
    assert actual['environment_bounds']=={'cpu_percent':100,'memory_bytes':5368709120,'swap_bytes':0}
    resource=lr.LocalResources(directory,workflow_slice=actual['slice'])
    with resource._transaction() as db:
        configuration=db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]
    monkeypatch.setattr(lr.LocalResources,'configured',classmethod(lambda cls,settings=None:resource))
    work=tmp_path/'thread-metadata-native';work.mkdir()
    policy=local_jobs.LocalJobPolicy(512*1024**2,1024**2)
    handle=native.prepare_job(['/bin/true'],cwd=work,policy=policy,handle_path=work/'handle.json',cpu_threads=3)
    body=handle.read()
    assert body['metadata']['cpu_threads']==3
    try:
        native.start_prepared(handle)
        result=native.wait_job(handle)
        assert result.returncode==0 and handle.read()['metadata']['cpu_threads']==3
        verified=result.metadata['verified_cgroup']
        assert verified['memory_max']==512*1024**2 and verified['memory_swap_max']==0
        assert verified['workflow_slice']==actual['slice'] and verified['workflow_owner']==actual['unit']
        assert active_budget()==actual
        assert verified['cpu_threads']==3
        quota,period=map(int,verified['cpu_max'].split())
        assert quota==period
        reservation=handle.read()['capacity_reservation']
        assert reservation['allocation']=={'cpu_threads':3,**policy.to_dict()}
        assert reservation['execution_handle']==handle.read()['unit']
        (tmp_path/'raw-thread-native.json').write_text(json.dumps({
            'requested_cpu_threads':3,'actual_owner':actual,'handle':handle.read(),
            'metadata':result.metadata,'returncode':result.returncode,
            'configuration_bytes':configuration},indent=2))
    finally:
        if not native.status(handle)['quiescent']:native.cancel(handle)
        native.release(handle)
    with resource._transaction() as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]==configuration
        assert db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==0


def test_requested_thread_metadata_does_not_consume_admission_slots(directory,tmp_path,monkeypatch):
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
    (tmp_path/'raw-thread-admission.json').write_text(json.dumps({
        'definition':resource.as_record(),'before':before,'after':after,'reservations':[first,second],
        'recommendation':recommendation,'configuration_bytes':configuration,
        'service_observation_controlled':True},indent=2))
    resource.release_reservation(first);resource.release_reservation(second)


@pytest.mark.parametrize('kind',['new','empty_database','saved_current'],
                         ids=['new','empty_database','saved_current'])
@pytest.mark.parametrize('setting_request',['unknown','memory','boolean'],ids=['unknown','memory','boolean'])
def test_rejected_custom_initialization_preserves_all_existing_bytes(kind,setting_request,directory,tmp_path,monkeypatch):
    if kind=='empty_database':
        directory.mkdir();db=sqlite3.connect(directory/'capacity.sqlite3');db.close()
    elif kind=='saved_current':lr.LocalResources(directory)
    settings={'unknown':{'invented_field':1},'memory':{'memory_bytes':21474836481},
              'boolean':{'cpu_threads':True}}[setting_request]
    def snapshot():
        return {'exists':directory.exists(),
            'directories':sorted(str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_dir()),
            'files':{str(p.relative_to(directory)):p.read_bytes().hex() for p in directory.rglob('*') if p.is_file()}}
    before=snapshot()
    with pytest.raises(ValueError) as caught:lr.LocalResources(directory,settings)
    assert type(caught.value) is ValueError and snapshot()==before
    expected=({'unknown':'invalid_local_resource_settings','memory':'local_resource_limits_exceed_environment_bounds',
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
