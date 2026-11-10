"""Workflow ownership, machine resource bounds and measurements.

This module intentionally uses only the standard library. The shell launcher
starts it inside an owned service before importing application or test code.
The historical module name is retained for existing callers.
CPU and RAM are environment constraints; the episode iterator owns scientific
continuation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time


VERSION='whole_workflow_budget_v2'
WINDOW_ENV='CODEX_THREAD_ID'
WINDOW_ID=os.environ.get(WINDOW_ENV)


def window_units(window_id):
    if not isinstance(window_id,str) or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',window_id):
        raise ValueError('stable_codex_window_identity_required')
    key=window_id.replace('-','')
    return 'gene-episode-workflow-'+key+'.service','geneepisodewindow'+key+'.slice'


UNIT,SLICE=window_units(WINDOW_ID) if WINDOW_ID else (None,None)
ENV='GENE_EPISODE_WORKFLOW_BUDGET_FILE'
ENVIRONMENT_BOUNDS={'cpu_percent':100,'memory_bytes':5*1024**3,
    'swap_bytes':0}


def _control(*args):
    return subprocess.run(['systemctl','--user',*args],capture_output=True,text=True,check=True)


def _properties(unit):
    value=_control('show',unit,'--property=ControlGroup','--property=ActiveState','--property=Slice','--property=BindsTo','--property=LoadState')
    return dict(line.split('=',1) for line in value.stdout.splitlines() if '=' in line)


def _cgroup(pid='self'):
    return next(line.split(':',2)[2] for line in Path('/proc',str(pid),'cgroup').read_text().splitlines() if line.startswith('0::'))


def _pid_start(pid):
    try:
        fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
        return None if fields[0] in {'Z','X','x'} else fields[19]
    except FileNotFoundError:return None


def _slice_path():
    window_units(WINDOW_ID)
    # Ownership checks must not need another process to authenticate placement.
    # The kernel's current placement, not a supplied path, identifies this
    # window's actual slice. A sibling window cannot supply this ancestor.
    parts=Path(_cgroup()).parts
    matches=[index for index,name in enumerate(parts) if name==SLICE]
    if len(matches)!=1:
        raise ValueError('workflow_process_outside_budget')
    group=str(Path(*parts[:matches[0]+1]))
    return group,Path('/sys/fs/cgroup')/group.lstrip('/')


def _verify():
    group,path=_slice_path()
    cpu=(path/'cpu.max').read_text().split()
    resources={'memory_bytes':int((path/'memory.max').read_text()),
        'swap_bytes':int((path/'memory.swap.max').read_text())}
    if (resources!={key:ENVIRONMENT_BOUNDS[key] for key in resources}
            or len(cpu)!=2 or cpu[0]=='max'
            or int(cpu[0])*100!=ENVIRONMENT_BOUNDS['cpu_percent']*int(cpu[1])):
        raise ValueError('workflow_environment_bounds_not_enforced')
    if not _cgroup().startswith(group+'/'):
        raise ValueError('workflow_process_outside_budget')
    return group,path


def active_budget():
    """Authenticate the live owner and enforced cgroup without forking a helper."""
    selected=os.environ.get(ENV)
    if not selected:raise ValueError('whole_workflow_budget_required; use tools/one_workflow.sh')
    file=Path(selected).resolve()
    value=json.loads(file.read_text())
    if (value.get('version')!=VERSION or value.get('window_id')!=WINDOW_ID
            or value.get('unit')!=UNIT or value.get('slice')!=SLICE
            or value.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            or file!=Path(value['run_directory'])/'workflow-budget.json'):
        raise ValueError('workflow_budget_identity_conflict')
    group,_=_verify()
    driver_group=group+'/'+UNIT
    if value['driver_cgroup']!=driver_group or value['slice_cgroup']!=group:
        raise ValueError('workflow_budget_owner_not_active')
    owner=value['supervisor_pid']
    if type(owner) is not int or owner<=0 or _pid_start(owner)!=value.get('supervisor_start_ticks'):
        raise ValueError('workflow_budget_owner_not_active')
    try:
        owner_group=_cgroup(owner)
        owner_args=Path('/proc',str(owner),'cmdline').read_bytes().decode().split('\0')
    except (FileNotFoundError,ProcessLookupError):
        raise ValueError('workflow_budget_owner_not_active') from None
    if owner_group!=driver_group or _pid_start(owner)!=value.get('supervisor_start_ticks'):
        raise ValueError('workflow_budget_owner_not_active')
    try:owner_index=owner_args.index('gene_annotation_episode.workflow_budget')
    except ValueError:raise ValueError('workflow_budget_owner_identity_conflict') from None
    if owner_args[owner_index+1:owner_index+3]!=[value['run_directory'],'--']:
        raise ValueError('workflow_budget_owner_identity_conflict')
    return value


def native_budget(policy,cpu_threads,cwd):
    value=active_budget()
    if cpu_threads*100>ENVIRONMENT_BOUNDS['cpu_percent'] or policy.memory_bytes>ENVIRONMENT_BOUNDS['memory_bytes']:
        raise ValueError('native_request_exceeds_environment_bounds')
    if not Path(cwd).resolve().is_relative_to(Path(value['run_directory'])):
        raise ValueError('native_output_outside_workflow_run')
    return value


def _members(path):
    result=set()
    for file in path.rglob('cgroup.procs'):
        try:result.update(int(p) for p in file.read_text().split())
        except FileNotFoundError:pass
    return result


def _owned_units():
    window_units(WINDOW_ID)
    rows=_control('list-units','--all','--type=service','--plain','--no-legend','--no-pager','gene-local-job-*.service')
    return [line.split()[0] for line in rows.stdout.splitlines()
        if line.split() and _properties(line.split()[0]).get('Slice')==SLICE]


def _descendants_active(path):
    """Keep ownership until detached workers and service transitions finish.

    The supervisor is intentionally still alive after its driver returns. A
    worker service can briefly have no process while activating or running its
    stop hooks, so an empty process list alone does not establish completion.
    The control commands below are synchronous and reaped before returning;
    they are not outstanding scientific workers.
    """
    if _members(path)-{os.getpid()}:
        return True
    return any(_properties(unit).get('ActiveState') in
        {'active','activating','deactivating','reloading'} for unit in _owned_units())


def cleanup():
    """Stop owned workers on failure/cancellation or final service cleanup.

    A successful driver's exit is not a request to cancel its descendants.
    Normal supervision keeps this service alive until they have actually exited.
    """
    units=_owned_units()
    if units:
        _control('--no-block','stop',*units)
        while True:
            if all(_properties(u).get('ActiveState') not in {'active','activating','deactivating','reloading'} for u in units):break
            time.sleep(.1)
        for unit in units:
            if _properties(unit).get('LoadState')=='not-found':continue
            try:_control('reset-failed',unit)
            except subprocess.CalledProcessError:
                if _properties(unit).get('LoadState')!='not-found':raise


def _allocated(directory):
    total=0
    for root,dirs,files in os.walk(directory,followlinks=False):
        for name in files:
            try:total+=(Path(root)/name).lstat().st_blocks*512
            except FileNotFoundError:pass
    return total


def supervise(directory,command):
    window_units(WINDOW_ID)
    directory=Path(directory).resolve()
    if not command or 'runs' not in directory.parts:raise ValueError('workflow_command_and_run_directory_required')
    if _properties(UNIT).get('ControlGroup')!=_cgroup():raise ValueError('workflow_supervisor_requires_owned_service')
    _control('set-property','--runtime',SLICE,'CPUQuota=100%',
        f"MemoryMax={ENVIRONMENT_BOUNDS['memory_bytes']}",
        'MemorySwapMax=0','TasksMax=infinity')
    group,path=_verify()
    if _members(path)!={os.getpid()}:raise ValueError('another_workflow_process_still_present')
    peak_reset=False;peak_file=None
    try:
        # The kernel resets memory.peak for subsequent reads on this same FD.
        peak_file=(path/'memory.peak').open('r+')
        peak_file.write('0');peak_file.flush();peak_reset=True
    except OSError:
        if peak_file is not None:peak_file.close();peak_file=None
    events_before=dict(line.split() for line in (path/'memory.events').read_text().splitlines())
    value={'version':VERSION,'window_id':WINDOW_ID,'unit':UNIT,'slice':SLICE,
        'environment_bounds':dict(ENVIRONMENT_BOUNDS),
        'run_directory':str(directory),'driver_cgroup':_cgroup(),'slice_cgroup':group,
        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'supervisor_pid':os.getpid(),'supervisor_start_ticks':_pid_start(os.getpid()),
        'command':command,'disk_bandwidth_enforced':False,
        'memory_peak_scope':'this_workflow' if peak_reset else 'slice_lifetime_upper_bound'}
    file=directory/'workflow-budget.json';file.write_text(json.dumps(value,indent=2)+'\n')
    env=dict(os.environ)
    env[ENV]=str(file)
    env.update(PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(directory/'tmp'),TMP=str(directory/'tmp'),TEMP=str(directory/'tmp'),
        XDG_CACHE_HOME=str(directory/'cache'))
    for name in ('tmp','cache'):(directory/name).mkdir(exist_ok=True)
    process=None
    def interrupted(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    failure=None;started=time.monotonic();peak_scratch=0;next_scan=0
    driver_finished=None;waited_for_descendants=False;descendant_drain_completed=False
    drain_started=None;drain_finished=None
    def observe_storage():
        nonlocal peak_scratch,next_scan
        if time.monotonic()>=next_scan:
            peak_scratch=max(peak_scratch,_allocated(directory));next_scan=time.monotonic()+2
    try:
        process=subprocess.Popen(command,env=env)
        while process.poll() is None:
            observe_storage()
            time.sleep(.2)
        code=process.returncode
        driver_finished=time.monotonic()
        if code==0:
            # A parent can yield while independently owned children continue.
            # Preserve the service, its machine bounds and the launcher's
            # ownership lock until those workers finish naturally. This is
            # process supervision, not another Episode action or stop rule.
            drain_started=time.monotonic()
            while _descendants_active(path):
                waited_for_descendants=True
                observe_storage()
                time.sleep(.2)
            drain_finished=time.monotonic()
            descendant_drain_completed=True
    except BaseException as error:
        failure=type(error).__name__+': '+str(error);code=1
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait()
        if failure is not None or code!=0:
            try:cleanup()
            except Exception as error:
                failure='cleanup_unconfirmed: '+str(error);code=1
        peak_scratch=max(peak_scratch,_allocated(directory))
        if peak_file is not None:
            peak_file.seek(0);memory_peak=int(peak_file.read());peak_file.close()
        else:memory_peak=int((path/'memory.peak').read_text())
        events_after=dict(line.split() for line in (path/'memory.events').read_text().splitlines())
        event_deltas={key:int(count)-int(events_before.get(key,0)) for key,count in events_after.items()}
        finished=time.monotonic()
        receipt={**value,'returncode':code,'failure':failure,'elapsed_seconds':finished-started,
            'driver_returncode':process.returncode if process is not None else None,
            'driver_elapsed_seconds':driver_finished-started if driver_finished is not None else None,
            'waited_for_descendants':waited_for_descendants,
            'descendant_drain_completed':descendant_drain_completed,
            'descendant_drain_seconds':drain_finished-drain_started if drain_finished is not None else None,
            'observed_scratch_bytes':peak_scratch,
            'memory_peak_bytes':memory_peak,'memory_events_scope':'this_workflow_delta',
            'memory_events':''.join(key+' '+str(count)+'\n' for key,count in event_deltas.items()),
            'memory_events_before':events_before,'memory_events_after':events_after}
        (directory/'workflow-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return code


def main():
    if sys.argv[1:]==['cleanup']:cleanup();return
    if len(sys.argv)<4 or sys.argv[2]!='--':raise ValueError('expected run_directory -- command arguments')
    raise SystemExit(supervise(sys.argv[1],sys.argv[3:]))


if __name__=='__main__':main()
