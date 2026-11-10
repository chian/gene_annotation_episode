"""Lightweight real process/cgroup checks; no biological algorithms or models."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from gene_annotation_episode.workflow_budget import active_budget,ENV,SLICE,UNIT
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import prepare_job,start_prepared,wait_job,_properties
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.providers import ModelConnection,_SessionConnection,ModelCallError,load_config


ROOT=Path(__file__).resolve().parents[1]


async def providers(directory):
    config=load_config()
    config['connection']['command']=[sys.executable,str(ROOT/'tests/workflow_budget_fake_provider.py')]
    one=_SessionConnection(config,directory/'lease-one',ROOT)
    two=_SessionConnection(config,directory/'lease-two',ROOT)
    async with one:
        try:await two.__aenter__()
        except ModelCallError as error:assert str(error)=='single_provider_process_already_active'
        else:raise AssertionError('Second provider unexpectedly started')
        assert two.process is None
    original=_SessionConnection.complete
    async def fake(self,*_):return {'pid':self.process.pid}
    _SessionConnection.complete=fake
    try:
        async with ModelConnection(config,directory/'serial',ROOT) as connection:
            first=await connection.complete('episode-one','REASONING','',{},{} )
            second=await connection.complete('episode-two','REASONING','',{},{} )
            assert first['pid']!=second['pid']
            assert not Path('/proc',str(first['pid'])).exists()
            assert not connection.has_session('episode-one','REASONING')
            assert connection.maximum_active_workers==1
            await connection.complete('episode-one','REASONING','',{},{} )
            assert not Path('/proc',str(second['pid'])).exists()
            assert connection.maximum_active_workers==1
    finally:_SessionConnection.complete=original
    return {'second_provider_rejected_before_fork':True,'maximum_active_provider_workers':1,
        'previous_provider_exited_before_next':True}


def main():
    budget=active_budget();directory=Path(budget['run_directory'])
    if '--abandon-children' in sys.argv:
        ordinary=subprocess.Popen([sys.executable,'-c','import time;time.sleep(90)'],start_new_session=True)
        native=directory/'abandoned-native';native.mkdir()
        command=[sys.executable,'-c',
            "import os,time;from pathlib import Path;Path('native.pid').write_text(str(os.getpid()));time.sleep(90)"]
        handle=prepare_job(command,cwd=native,policy=LocalJobPolicy(64 * 1024 ** 2, 16 * 1024 ** 2),
            handle_path=native/'native.handle.json',cpu_threads=1)
        start_prepared(handle)
        deadline=time.monotonic()+5
        while not (native/'native.pid').exists():
            if time.monotonic()>deadline:raise AssertionError('Native probe did not start')
            time.sleep(.02)
        (directory/'abandoned.json').write_text(json.dumps({'ordinary_pid':ordinary.pid,
            'native_pid':int((native/'native.pid').read_text()),'native_unit':handle.read()['unit']}))
        print('Deliberately leaving two sleeping children for the guard to stop.')
        return
    # A new process session cannot escape the aggregate cgroup.
    child=subprocess.run([sys.executable,'-c',
        "from pathlib import Path;print(Path('/proc/self/cgroup').read_text())"],
        start_new_session=True,capture_output=True,text=True,check=True)
    assert budget['slice_cgroup']+'/' in child.stdout
    marker=directory/'second-workflow-ran'
    rejected=subprocess.run(['bash',str(ROOT/'tools/one_workflow.sh'),str(directory/'rejected-workflow'),'--',
        '/usr/bin/touch',str(marker)],capture_output=True,text=True)
    assert rejected.returncode==75 and not marker.exists(),rejected
    native=directory/'native';native.mkdir()
    command=[sys.executable,'-c',
        "from gene_annotation_episode.workflow_budget import active_budget;import json;print(json.dumps(active_budget()['limits']))"]
    handle=prepare_job(command,cwd=native,policy=LocalJobPolicy(64 * 1024 ** 2, 16 * 1024 ** 2),
        handle_path=native/'native.handle.json',cpu_threads=1,env={'PYTHONPATH':str(ROOT)})
    start_prepared(handle)
    result=wait_job(handle)
    assert result.returncode==0,result
    actual=result.metadata['verified_cgroup']
    assert actual['workflow_slice']==SLICE and actual['workflow_owner']==UNIT
    assert json.loads(result.stdout_path.read_text())==budget['limits']
    rejected_handle=native/'oversize.handle.json'
    try:prepare_job(command,cwd=native,policy=LocalJobPolicy(1024 ** 3, 16 * 1024 ** 2),
        handle_path=rejected_handle,cpu_threads=1)
    except AcquisitionError as error:
        assert error.code=='whole_workflow_budget_unavailable'
        assert error.operational['reason']=='native_request_exceeds_whole_workflow_budget'
    else:raise AssertionError('Oversized native request was admitted')
    assert not rejected_handle.exists()
    current=os.environ.pop(ENV)
    try:
        try:active_budget()
        except ValueError:pass
        else:raise AssertionError('Missing workflow proof was accepted')
    finally:os.environ[ENV]=current
    false_dir=directory/'forged-budget';false_dir.mkdir()
    false_value={**budget,'run_directory':str(false_dir)}
    false_file=false_dir/'workflow-budget.json';false_file.write_text(json.dumps(false_value))
    os.environ[ENV]=str(false_file)
    try:
        try:active_budget()
        except ValueError as error:assert str(error)=='workflow_budget_owner_identity_conflict'
        else:raise AssertionError('A copied budget file authorized another workflow directory')
    finally:os.environ[ENV]=current
    report={'new_process_session_stayed_inside_aggregate_cap':True,'second_workflow_rejected_before_payload':True,
        'native_worker_in_same_slice':True,'native_worker_bound_to_driver_lifetime':True,
        'oversize_request_rejected_before_handle_or_process':True,'missing_budget_rejected':True,
        'limits':budget['limits'],'disk_bandwidth_enforced':False,'copied_budget_cannot_authorize_another_run':True,
        'provider':asyncio.run(providers(directory))}
    (directory/'PROBE_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
