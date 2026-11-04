"""One local workflow per Codex window, with an aggregate cgroup budget.

This module intentionally uses only the standard library. The shell launcher
starts it inside a capped service before importing application or test code.
All nested native services must join its capped slice and bind to its lifetime.
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
PROFILE_ENV='GENE_EPISODE_WORKFLOW_PROFILE'
PROFILES={
    'default': {'cpu_percent':100,'memory_bytes':512*1024**2,'swap_bytes':0,
        'tasks':64,'wall_seconds':600,'scratch_bytes':256*1024**2,'per_file_bytes':64*1024**2},
    # Selection requires the user's approval for the concrete run budget.
    # Defining a profile does not activate it or change the default boundary.
    'a108-validation': {'cpu_percent':100,'memory_bytes':3*1024**3,'swap_bytes':0,
        'tasks':128,'wall_seconds':None,'scratch_bytes':24*1024**3,'per_file_bytes':16*1024**3},
}


def profile_limits(profile):
    if not isinstance(profile,str) or profile not in PROFILES:
        raise ValueError('unknown_workflow_budget_profile')
    return dict(PROFILES[profile])


PROFILE=os.environ.get(PROFILE_ENV,'default')
LIMITS=profile_limits(PROFILE)


def _control(*args):
    return subprocess.run(['systemctl','--user',*args],capture_output=True,text=True,timeout=10,check=True)


def _properties(unit):
    value=_control('show',unit,'--property=ControlGroup','--property=ActiveState','--property=Slice','--property=BindsTo','--property=LoadState')
    return dict(line.split('=',1) for line in value.stdout.splitlines() if '=' in line)


def _cgroup():
    return next(line.split(':',2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))


def _pid_start(pid):
    try:return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:return None


def _slice_path():
    window_units(WINDOW_ID)
    group=_properties(SLICE).get('ControlGroup')
    if not group or not group.startswith('/'):
        raise ValueError('workflow_budget_cgroup_unavailable')
    return group,Path('/sys/fs/cgroup')/group.lstrip('/')


def _verify(expected):
    group,path=_slice_path()
    cpu=(path/'cpu.max').read_text().split()
    values={'memory_bytes':int((path/'memory.max').read_text()),
        'swap_bytes':int((path/'memory.swap.max').read_text()),
        'tasks':int((path/'pids.max').read_text())}
    if values!={k:expected[k] for k in values} or len(cpu)!=2 or cpu[0]=='max' or int(cpu[0])*100!=expected['cpu_percent']*int(cpu[1]):
        raise ValueError('workflow_budget_limits_not_enforced')
    if not _cgroup().startswith(group+'/'):
        raise ValueError('workflow_process_outside_budget')
    return group,path


def active_budget():
    """Authenticate actual cgroup placement; an environment flag is insufficient."""
    selected=os.environ.get(ENV)
    if not selected:raise ValueError('whole_workflow_budget_required; use tools/one_workflow.sh')
    file=Path(selected).resolve()
    value=json.loads(file.read_text())
    if (value.get('version')!=VERSION or value.get('window_id')!=WINDOW_ID
            or value.get('unit')!=UNIT or value.get('slice')!=SLICE
            or value.get('limits')!=profile_limits(value.get('profile','default'))
            or value.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            or file!=Path(value['run_directory'])/'workflow-budget.json'):
        raise ValueError('workflow_budget_identity_conflict')
    group,_=_verify(value['limits'])
    service=_properties(UNIT)
    if service.get('ActiveState')!='active' or service.get('ControlGroup')!=value['driver_cgroup'] or value['slice_cgroup']!=group:
        raise ValueError('workflow_budget_owner_not_active')
    if _pid_start(value['supervisor_pid'])!=value.get('supervisor_start_ticks'):
        raise ValueError('workflow_budget_owner_not_active')
    owner_args=Path('/proc',str(value['supervisor_pid']),'cmdline').read_bytes().decode().split('\0')
    try:owner_index=owner_args.index('gene_annotation_episode.workflow_budget')
    except ValueError:raise ValueError('workflow_budget_owner_identity_conflict') from None
    if owner_args[owner_index+1:owner_index+3]!=[value['run_directory'],'--']:
        raise ValueError('workflow_budget_owner_identity_conflict')
    return value


def native_budget(policy,cpu_threads,cwd):
    value=active_budget()
    limits=value['limits']
    if (cpu_threads*100>limits['cpu_percent'] or policy.memory_bytes>limits['memory_bytes']
            or policy.scratch_bytes>limits['scratch_bytes']):
        raise ValueError('native_request_exceeds_whole_workflow_budget')
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


def cleanup():
    """Stop sibling workers, without declaring their scientific work successful."""
    units=_owned_units()
    if units:
        _control('--no-block','stop',*units)
        end=time.monotonic()+15
        while time.monotonic()<end:
            if all(_properties(u).get('ActiveState') not in {'active','activating','deactivating','reloading'} for u in units):break
            time.sleep(.1)
        else:raise ValueError('workflow_native_cleanup_unconfirmed')
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
    if _properties(UNIT).get('ControlGroup')!=_cgroup():raise ValueError('workflow_supervisor_requires_capped_service')
    _control('set-property','--runtime',SLICE,'CPUQuota=100%','MemoryMax='+str(LIMITS['memory_bytes']),
        'MemorySwapMax=0','TasksMax='+str(LIMITS['tasks']),
        'IOReadBandwidthMax=','IOWriteBandwidthMax=')
    group,path=_verify(LIMITS)
    if _members(path)!={os.getpid()}:raise ValueError('another_workflow_process_still_present')
    peak_reset=False;peak_file=None
    try:
        # The kernel resets memory.peak for subsequent reads on this same FD.
        peak_file=(path/'memory.peak').open('r+')
        peak_file.write('0');peak_file.flush();peak_reset=True
    except OSError:
        if peak_file is not None:peak_file.close();peak_file=None
    events_before=dict(line.split() for line in (path/'memory.events').read_text().splitlines())
    value={'version':VERSION,'window_id':WINDOW_ID,'unit':UNIT,'slice':SLICE,'profile':PROFILE,'limits':LIMITS,
        'run_directory':str(directory),'driver_cgroup':_cgroup(),'slice_cgroup':group,
        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'supervisor_pid':os.getpid(),'supervisor_start_ticks':_pid_start(os.getpid()),
        'command':command,'disk_bandwidth_enforced':False,
        'memory_peak_scope':'this_workflow' if peak_reset else 'slice_lifetime_upper_bound'}
    file=directory/'workflow-budget.json';file.write_text(json.dumps(value,indent=2)+'\n')
    env=dict(os.environ)
    env[ENV]=str(file)
    env[PROFILE_ENV]=PROFILE
    env.update(PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(directory/'tmp'),TMP=str(directory/'tmp'),TEMP=str(directory/'tmp'),
        XDG_CACHE_HOME=str(directory/'cache'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1',RAYON_NUM_THREADS='1')
    for name in ('tmp','cache'):(directory/name).mkdir(exist_ok=True)
    process=None
    def interrupted(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    failure=None;started=time.monotonic();peak_scratch=0;next_scan=0
    try:
        process=subprocess.Popen(command,env=env)
        while process.poll() is None:
            if time.monotonic()>=next_scan:
                peak_scratch=max(peak_scratch,_allocated(directory));next_scan=time.monotonic()+2
            if peak_scratch>LIMITS['scratch_bytes']:raise ValueError('whole_workflow_scratch_limit')
            if LIMITS['wall_seconds'] is not None and time.monotonic()-started>LIMITS['wall_seconds']:
                raise ValueError('whole_workflow_wall_limit')
            time.sleep(.2)
        code=process.returncode
    except BaseException as error:
        failure=type(error).__name__+': '+str(error);code=1
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        try:cleanup()
        except Exception as error:
            failure='cleanup_unconfirmed: '+str(error);code=1
        peak_scratch=max(peak_scratch,_allocated(directory))
        if peak_scratch>LIMITS['scratch_bytes']:
            failure='whole_workflow_scratch_limit';code=1
        if peak_file is not None:
            peak_file.seek(0);memory_peak=int(peak_file.read());peak_file.close()
        else:memory_peak=int((path/'memory.peak').read_text())
        events_after=dict(line.split() for line in (path/'memory.events').read_text().splitlines())
        event_deltas={key:int(count)-int(events_before.get(key,0)) for key,count in events_after.items()}
        receipt={**value,'returncode':code,'failure':failure,'elapsed_seconds':time.monotonic()-started,
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
