"""Actual independent launchers compete for the same caller-owned local slot."""
import json
import subprocess
import sys
import time

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.local_resources import DIRECTORY_ENV, LocalResources
from gene_annotation_episode.native_lifecycle import (
    NativeJobHandle, cancel, collect, prepare_job, release, start_prepared, status,
)


MiB = 1024**2
POLICY = LocalJobPolicy(64*MiB, 4*MiB)
NATIVE = "from pathlib import Path\nimport time\nPath('native-started').touch()\nwhile not Path('finish').exists(): time.sleep(.01)"
LAUNCHER = """
import json,sys,time
from pathlib import Path
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.native_lifecycle import NativeJobHandle,start_prepared
handle=NativeJobHandle(Path(sys.argv[1]))
Path(sys.argv[2]).touch()
while not Path(sys.argv[3]).exists():time.sleep(.01)
try:
    start_prepared(handle)
    result={'status':'started','unit':handle.read()['unit']}
except AcquisitionError as error:
    result={'status':'blocked','code':error.code,'operational':error.operational}
print(json.dumps(result),flush=True)
"""


def wait_for(predicate, seconds=15):
    deadline=time.monotonic()+seconds
    while not predicate():
        assert time.monotonic()<deadline
        time.sleep(.02)


def cleanup(handle):
    if handle.path.exists():
        if not status(handle)['quiescent']:
            cancel(handle)
        release(handle)


@pytest.fixture
def capacity(tmp_path,monkeypatch):
    monkeypatch.setenv(DIRECTORY_ENV,str(tmp_path/'shared-host'))
    return LocalResources.configured()


def test_independent_launchers_share_one_slot_and_retry_original_prepared_job(tmp_path,capacity):
    handles=[]
    workers=[]
    barrier=tmp_path/'compete'
    try:
        for index in range(2):
            directory=tmp_path/f'run-{index}'
            directory.mkdir()
            handle=prepare_job([sys.executable,'-c',NATIVE],cwd=directory,policy=POLICY,
                handle_path=directory/'native.handle.json')
            handles.append(handle)
            workers.append(subprocess.Popen([sys.executable,'-c',LAUNCHER,str(handle.path),
                str(directory/'launcher-ready'),str(barrier)],stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,text=True))
        wait_for(lambda:all((h.path.parent/'launcher-ready').exists() for h in handles))
        barrier.touch()
        results=[]
        for worker in workers:
            stdout,stderr=worker.communicate(timeout=20)
            if worker.returncode and 'local_job_boundary_unavailable' in stderr:
                pytest.skip('user-systemd boundary unavailable')
            assert worker.returncode==0,stderr
            results.append(json.loads(stdout))
        assert sorted(row['status'] for row in results)==['blocked','started']
        winner=next(i for i,row in enumerate(results) if row['status']=='started')
        loser=1-winner
        first,second=handles[winner],handles[loser]
        wait_for(lambda:(first.path.parent/'native-started').exists())
        assert not (second.path.parent/'native-started').exists()
        blocked=results[loser]
        assert blocked['code']=='local_resource_busy'
        assert blocked['operational']['retryable']
        assert blocked['operational']['retry_same_prepared_job']
        assert second.read()['stage']=='prepared'
        original_unit=second.read()['unit']
        # Launching processes have exited; the live native service still owns
        # the slot, as observed by a new independent capacity reader.
        busy=LocalResources.configured().snapshot()
        assert busy['limits']['max_running_jobs']==1
        assert busy['available']['job_slots']==0
        assert busy['reserved']['job_slots']==1
        assert busy['jobs'][0]['state']=='running'
        assert first.read()['metadata']['verified_cgroup']['cpu_threads']==1
        # The actual parent runtime sees busy capacity before its first choice
        # and a fresh free-capacity snapshot before its next choice.
        from test_runtime import ScriptedProvider, reason, run, setup
        parent_directory=tmp_path/'parent'
        parent_directory.mkdir()
        store,tools=setup(parent_directory)
        tools.local_resources=LocalResources.configured()
        tools.local_job_policy=POLICY
        parent_views=[]
        def parent_decision(context):
            view=context['resource_context']['local']
            parent_views.append(view)
            if len(parent_views)==1:
                assert view['available']['job_slots']==0
                (first.path.parent/'finish').touch()
                # Capacity frees without a collector or surviving launcher.
                wait_for(lambda:capacity.snapshot()['available']['job_slots']==1)
            else:
                assert view['available']['job_slots']==1
            return reason(0)
        try:
            run(store,tools,ScriptedProvider([parent_decision,parent_decision]),
                parent_directory/'run',counts=(2,2))
            saved=json.loads(store.db.execute('SELECT request FROM runtime_model_calls '
                'ORDER BY rowid LIMIT 1').fetchone()[0])
            assert saved['context']['resource_context']['local']['available']['job_slots']==0
        finally:
            store.db.close()
        start_prepared(second)
        wait_for(lambda:(second.path.parent/'native-started').exists())
        assert second.read()['unit']==original_unit
        assert LocalResources.configured().snapshot()['available']['job_slots']==0
        assert collect(first).returncode==0
        # Reading the older completed job cannot release the newer reservation.
        assert LocalResources.configured().snapshot()['available']['job_slots']==0
        (second.path.parent/'finish').touch()
        wait_for(lambda:status(second)['terminal'])
        assert collect(second).returncode==0
        assert capacity.snapshot()['available']['job_slots']==1
        (tmp_path/'capacity-proof.json').write_text(json.dumps({
            'competing_launches':results,'busy_snapshot':busy,
            'parent_decision_snapshots':parent_views,
            'retry_used_original_unit':original_unit,
            'final_capacity':capacity.snapshot()},indent=2)+'\n')
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=10)
        for handle in handles:
            cleanup(handle)


@pytest.mark.parametrize('resource',['cpu_threads','memory_bytes','scratch_bytes'])
def test_job_exceeding_shared_budget_never_dispatches(tmp_path,capacity,resource):
    limits=capacity.as_record()['limits']
    allocation={'cpu_threads':1,'memory_bytes':POLICY.memory_bytes,'scratch_bytes':POLICY.scratch_bytes}
    allocation[resource]=limits[resource]+1
    policy=LocalJobPolicy(allocation['memory_bytes'],allocation['scratch_bytes'])
    handle=prepare_job([sys.executable,'-c',NATIVE],cwd=tmp_path,policy=policy,
        handle_path=tmp_path/'native.handle.json',cpu_threads=allocation['cpu_threads'])
    try:
        with pytest.raises(AcquisitionError) as caught:
            start_prepared(handle)
        assert caught.value.code=='local_job_resource_limit'
        assert caught.value.operational['resource']==resource
        assert caught.value.operational['retryable'] is False
        assert handle.read()['stage']=='prepared'
        assert not (tmp_path/'native-started').exists()
        assert capacity.snapshot()['available']['job_slots']==1
    finally:
        cleanup(handle)


def test_unknown_dispatch_retains_capacity_until_explicit_quiescent_cancellation(
        tmp_path,capacity,monkeypatch):
    from gene_annotation_episode import native_lifecycle
    handle=prepare_job([sys.executable,'-c',NATIVE],cwd=tmp_path,policy=POLICY,
        handle_path=tmp_path/'native.handle.json')
    reservation=capacity.reserve(handle,cpu_threads=1,policy=POLICY)
    body=handle.read()
    body.update(stage='submitting',capacity_reservation=reservation)
    handle.path.write_text(json.dumps(body))
    monkeypatch.setattr(native_lifecycle,'_properties',lambda unit:{'LoadState':'not-found'})
    try:
        view=capacity.snapshot()
        assert view['available']['job_slots']==0
        assert view['jobs'][0]['state']=='execution_unknown'
        cancel(handle)
        assert capacity.snapshot()['available']['job_slots']==1
    finally:
        cleanup(handle)


def test_dead_owner_of_never_dispatched_reservation_does_not_leak_slot(tmp_path,capacity):
    handle=prepare_job([sys.executable,'-c',NATIVE],cwd=tmp_path,policy=POLICY,
        handle_path=tmp_path/'native.handle.json')
    script="""
import sys
from pathlib import Path
from gene_annotation_episode.local_resources import LocalResources
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle
LocalResources.configured().reserve(NativeJobHandle(Path(sys.argv[1])),
    cpu_threads=1,policy=LocalJobPolicy(64*1024**2,4*1024**2))
"""
    try:
        result=subprocess.run([sys.executable,'-c',script,str(handle.path)],
            capture_output=True,text=True,timeout=15)
        assert result.returncode==0,result.stderr
        assert capacity.snapshot()['available']['job_slots']==1
        assert handle.read()['stage']=='prepared'
    finally:
        cleanup(handle)


def test_shared_policy_cannot_be_replaced_by_another_run(tmp_path,capacity):
    with pytest.raises(ValueError,match='local_resource_limits_conflict'):
        LocalResources(capacity.directory,{'max_running_jobs':2})
    assert LocalResources(capacity.directory).as_record()==capacity.as_record()


def test_existing_untracked_service_occupies_capacity(tmp_path,capacity,monkeypatch):
    from types import SimpleNamespace
    from gene_annotation_episode import native_lifecycle
    monkeypatch.setattr(native_lifecycle,'_control',lambda *a,**k:SimpleNamespace(returncode=0,
        stdout='gene-local-job-existing.service loaded active running Existing native job\n'))
    snapshot=capacity.snapshot()
    assert snapshot['state']=='busy'
    assert snapshot['available']['job_slots']==0
    assert snapshot['jobs'][0]['state']=='untracked_running'


def test_unavailable_capacity_probe_never_advertises_free_slots(tmp_path,capacity,monkeypatch):
    from types import SimpleNamespace
    from gene_annotation_episode import native_lifecycle
    monkeypatch.setattr(native_lifecycle,'_control',lambda *a,**k:SimpleNamespace(returncode=1,stdout=''))
    snapshot=capacity.snapshot()
    assert snapshot['state']=='unknown'
    assert snapshot['available']['job_slots']==0
    assert snapshot['jobs'][0]['state']=='capacity_unavailable'


def test_cancel_actual_job_frees_slot_after_service_is_quiescent(tmp_path,capacity):
    handle=prepare_job([sys.executable,'-c',NATIVE],cwd=tmp_path,policy=POLICY,
        handle_path=tmp_path/'native.handle.json')
    try:
        start_prepared(handle)
        wait_for(lambda:(tmp_path/'native-started').exists())
        assert capacity.snapshot()['available']['job_slots']==0
        cancel(NativeJobHandle(handle.path))
        assert status(handle)['quiescent']
        assert capacity.snapshot()['available']['job_slots']==1
    finally:
        cleanup(handle)
