"""One durable, resource-enforced native execution path, blocking or detached.

This module executes an already selected command. It has no episode, credit,
yield or scientific policy. A disk handle and the systemd completion receipt
resolve execution independently of the submitting Python process.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid

from ._local_job_worker import allocated_bytes, atomic_json
from .acquisition import AcquisitionError
from .local_jobs import LocalJobPolicy, LocalJobResult
from .local_resources import LocalResources


VERSION = 'durable_systemd_native_job_v2'


def _control(arguments):
    return subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          text=True, check=False)


def _properties(unit):
    selected = ('LoadState', 'ActiveState', 'SubState', 'MemoryMax', 'MemorySwapMax',
                'KillMode', 'OOMPolicy', 'ControlGroup','Slice','BindsTo')
    result = _control(['systemctl', '--user', 'show', unit,
                       *['--property='+name for name in selected]])
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def _word(value):
    return '"' + value.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"') + '"'


def _boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def _load(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return None


@dataclass(frozen=True)
class NativeJobHandle:
    path: Path

    def read(self):
        body = json.loads(self.path.read_text())
        if body.get('version') != VERSION:
            raise ValueError('unsupported_native_job_handle')
        return body


def _metadata(policy):
    return {'native_lifecycle_version': VERSION, 'policy': policy.to_dict(), 'enforcement': {
        'memory': 'systemd_cgroup_v2_memory_max', 'swap': 'systemd_memory_swap_max_zero',
        'scratch': 'monitored_visible_allocated_bytes_with_possible_overshoot',
        'per_file_bytes': 'hard_rlimit_fsize_equal_to_scratch_bytes',
        'process_tree': 'systemd_control_group', 'filesystem_sandbox': False}}


def prepare_job(command, *, cwd, policy, handle_path, stdout_path=None, stderr_path=None,
                stdin_path=None, env=None, statistics=None, native_events=None, cpu_threads=1):
    """Persist a complete reservation without submitting a service.

    Publication of the handle is last. A crash before that publication cannot
    have dispatched anything through this protocol. Execution timing starts at
    dispatch, not during preparation or an offline reservation interval.
    """
    if not isinstance(policy, LocalJobPolicy):
        raise TypeError('local_job_policy_required')
    if type(cpu_threads) is not int or cpu_threads < 1:
        raise ValueError('invalid_local_job_cpu_threads')
    if statistics is not None:
        from .execution_recording import NativeStatistics
        if type(statistics) is not NativeStatistics:
            raise TypeError('typed_native_execution_statistics_required')
        statistics.validate_policy(policy)
    if native_events is not None:
        from .native_events import NativeEventBinding
        if type(native_events) is not NativeEventBinding:
            raise TypeError('typed_native_event_binding_required')
    if not command or any(type(item) is not str or not item or '\0' in item for item in command):
        raise ValueError('invalid_local_job_command')
    cwd = Path(cwd).resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError('local_job_directory_required')
    from .workflow_budget import native_budget
    try:
        workflow=native_budget(policy,cpu_threads,cwd)
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        raise AcquisitionError('whole_workflow_budget_unavailable',phase='local_preflight',
            operational={'reason':str(error),'retryable':False,'prepared_handle_preserved':False}) from error
    stdout = Path(stdout_path or cwd/'stdout.log').resolve()
    stderr = Path(stderr_path or cwd/'stderr.log').resolve()
    handle_path = Path(handle_path).resolve()
    for path in (stdout, stderr, handle_path):
        if not path.is_relative_to(cwd) or '\n' in str(path):
            raise ValueError('local_job_output_must_be_in_job_directory')
        path.parent.mkdir(parents=True, exist_ok=True)
    if len({stdout, stderr, handle_path}) != 3:
        raise ValueError('local_job_output_paths_must_differ')
    if handle_path.exists():
        raise ValueError('native_job_handle_already_exists')
    if env is not None and any(type(k) is not str or type(v) is not str for k, v in env.items()):
        raise ValueError('invalid_local_job_environment')
    metadata = _metadata(policy)
    metadata['local_resources'] = LocalResources.configured().as_record()
    metadata['cpu_threads'] = cpu_threads
    metadata['whole_workflow_budget'] = workflow
    metadata['enforcement']['cpu'] = 'systemd_cgroup_v2_cpu_max'
    if not shutil.which('systemd-run') or not shutil.which('systemctl'):
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
                               operational={**metadata, 'reason': 'user_systemd_required'})
    initial = allocated_bytes(cwd)
    if initial > policy.scratch_bytes:
        raise AcquisitionError('local_job_resource_limit', phase='local_preflight', operational={
            **metadata, 'resource': 'scratch_bytes', 'limit': policy.scratch_bytes,
            'evidence': {'observed_allocated_bytes': initial, 'stage': 'staged_inputs'}})
    token = '.local-job-' + uuid.uuid4().hex
    paths = {name: str(cwd/(token+'.'+name)) for name in
             ('request', 'ready', 'release', 'status', 'result', 'launcher')}
    if statistics is not None:
        paths['statistics'] = str(cwd/(token+'.statistics'))
    if native_events is not None:
        paths['native_events'] = str(cwd/(token+'.native_events'))
    if {stdout, stderr, handle_path} & {Path(p) for p in paths.values()}:
        raise ValueError('native_job_control_path_collision')
    body = {'version': VERSION, 'unit': 'gene-local-job-'+uuid.uuid4().hex+'.service',
        'command': list(command), 'cwd': str(cwd), 'stdout': str(stdout), 'stderr': str(stderr),
        'paths': paths, 'metadata': metadata, 'stage': 'prepared',
        'started_at': None, 'started_monotonic_ns': None, 'boot_id': None}
    if statistics is not None:
        from .execution_memory import ExecutionMemory
        body['statistics'] = statistics.as_record()
        body['execution_memory_path'] = str(ExecutionMemory.configured().path)
    if native_events is not None:
        body['native_events'] = native_events.as_record()
    stdout.write_bytes(b''); stderr.write_bytes(b'')
    from .workflow_budget import ENV as WORKFLOW_ENV,WINDOW_ENV
    environment={**dict(env or {}),WORKFLOW_ENV:str(Path(workflow['run_directory'])/'workflow-budget.json'),
        WINDOW_ENV:workflow['window_id']}
    atomic_json(paths['request'], {'command': list(command), 'cwd': str(cwd),
        'file_bytes': policy.scratch_bytes, 'ready_path': paths['ready'], 'release_path': paths['release'],
        'result_path': paths['result'], 'stdin_path': str(Path(stdin_path).resolve()) if stdin_path else None,
        'env': environment})
    body['request_sha256'] = hashlib.sha256(Path(paths['request']).read_bytes()).hexdigest()
    # A visible prepared handle therefore has its full request on disk. No
    # backend call is permitted before this fsynced publication.
    atomic_json(handle_path, body)
    return NativeJobHandle(handle_path)


def start_prepared(handle, *, cancel_event=None):
    """Dispatch one reserved unit, or resume its existing handshake.

    A submitting/released reservation never triggers another systemd-run.
    Unconfirmed dispatch stays explicit if its original unit is not observed.
    """
    body = handle.read()
    from .workflow_budget import native_budget
    workflow=native_budget(LocalJobPolicy(**body['metadata']['policy']),body['metadata'].get('cpu_threads',1),body['cwd'])
    if body['metadata'].get('whole_workflow_budget')!=workflow:
        raise AcquisitionError('whole_workflow_budget_identity_conflict',phase='local_preflight')
    if body['stage'] != 'prepared':
        return resume_start(handle, cancel_event=cancel_event)
    policy = LocalJobPolicy(**body['metadata']['policy'])
    paths, metadata = body['paths'], body['metadata']
    if hashlib.sha256(Path(paths['request']).read_bytes()).hexdigest() != body['request_sha256']:
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
            operational={**metadata, 'reason': 'native_request_identity_mismatch'})
    # A legacy never-dispatched handle also enters the shared host gate. Its
    # original command/request bytes remain unchanged.
    if 'local_resources' not in metadata:
        metadata['local_resources'] = LocalResources.configured().as_record()
        metadata['cpu_threads'] = 1
        metadata['enforcement']['cpu'] = 'systemd_cgroup_v2_cpu_max'
    _ensure_event_registration(handle, body)
    if 'local_resources' in metadata:
        resources = LocalResources.reopen(metadata['local_resources'])
        body['capacity_reservation'] = resources.reserve(handle,
            cpu_threads=metadata['cpu_threads'], policy=policy)
    try:
        return _dispatch_prepared(handle, body, cancel_event=cancel_event)
    except BaseException:
        # No service can have been submitted while the original durable handle
        # still says prepared. Later uncertainty retains its reservation.
        if handle.read()['stage'] == 'prepared':
            _release_capacity(body)
        raise


def _dispatch_prepared(handle, body, *, cancel_event=None):
    policy = LocalJobPolicy(**body['metadata']['policy'])
    paths = body['paths']
    stdout, stderr, handle_path = Path(body['stdout']), Path(body['stderr']), handle.path
    if 'statistics' in body:
        from .execution_recording import NativeStatistics
        context = NativeStatistics.from_record(body['statistics'])
        if context.condition_capture == 'not_started':
            body['statistics'] = NativeStatistics.capture(context.history_path, context.execution_class,
                recovery_directory=context.recovery_directory).as_record()
    body.update(started_at=datetime.now(timezone.utc).isoformat(),
                started_monotonic_ns=time.monotonic_ns(), boot_id=_boot(), stage='submitting')
    worker = Path(__file__).with_name('_local_job_worker.py')
    properties = [f'MemoryMax={policy.memory_bytes}', 'MemorySwapMax=0', 'KillMode=control-group',
        'OOMPolicy=kill', 'TimeoutStopSec=15', 'SendSIGKILL=yes',
        'StandardOutput=file:'+str(stdout).replace('%', '%%'),
        'StandardError=file:'+str(stderr).replace('%', '%%'),
        'ExecStopPost='+' '.join(_word(str(v)) for v in (sys.executable, worker, 'report', paths['status'],
            *([handle_path] if 'statistics' in body or 'native_events' in body else [])))]
    if 'local_resources' in body['metadata']:
        properties.append(f"CPUQuota={body['metadata']['cpu_threads']*100}%")
    from .workflow_budget import SLICE as WORKFLOW_SLICE,UNIT as WORKFLOW_UNIT
    properties.extend(['BindsTo='+WORKFLOW_UNIT,'After='+WORKFLOW_UNIT])
    argv = ['systemd-run', '--user', '--quiet', '--no-block', '--service-type=exec', '--unit='+body['unit'],
            '--slice='+WORKFLOW_SLICE, '--setenv=PYTHONDONTWRITEBYTECODE=1']
    for prop in properties:
        argv.extend(['--property', prop])
    argv.extend([sys.executable, str(worker), 'run', paths['request'], body['request_sha256']])
    atomic_json(handle_path, body)
    with open(paths['launcher'], 'wb') as log:
        launch = subprocess.run(argv, stdout=log, stderr=log, check=False)
    if launch.returncode != 0:
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
            operational={**body['metadata'], 'reason': 'service_submission_failed', 'launcher_returncode': launch.returncode})
    return resume_start(handle, cancel_event=cancel_event)


def start_job(command, *, cwd, policy, handle_path, stdout_path=None, stderr_path=None,
              stdin_path=None, env=None, cancel_event=None, statistics=None, native_events=None,
              cpu_threads=1):
    """Blocking adapters and detached tools share preparation and dispatch."""
    handle = prepare_job(command, cwd=cwd, policy=policy, handle_path=handle_path,
        stdout_path=stdout_path, stderr_path=stderr_path, stdin_path=stdin_path, env=env,
        statistics=statistics, native_events=native_events, cpu_threads=cpu_threads)
    try:
        return start_prepared(handle, cancel_event=cancel_event)
    except BaseException:
        # No native command runs before release. If startup was released before
        # an exception, stop/reap its existing unit rather than submitting again.
        if native_events is None or handle.read()['stage'] != 'prepared':
            cancel(handle)
        raise


def resume_start(handle, *, cancel_event=None):
    """Finish a reservation or its existing handshake; never repeat an attempt."""
    body = handle.read()
    if body['stage'] == 'prepared':
        return start_prepared(handle, cancel_event=cancel_event)
    _ensure_event_registration(handle, body)
    if Path(body['paths']['release']).exists():
        return handle
    policy = LocalJobPolicy(**body['metadata']['policy'])
    if 'capacity_reservation' in body:
        LocalResources.reopen(body['capacity_reservation']['resource']).validate_reservation(
            body['capacity_reservation'])
    while not Path(body['paths']['ready']).exists():
        if cancel_event is not None and cancel_event.is_set():
            raise AcquisitionError('local_job_cancelled', phase='local_preflight', operational=body['metadata'])
        props = _properties(body['unit'])
        if props.get('ActiveState') in {'failed', 'inactive'} or props.get('LoadState') == 'not-found':
            raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
                operational={**body['metadata'], 'reason': 'service_did_not_initialize'})
        time.sleep(.01)
    actual = _properties(body['unit'])
    ready = _load(body['paths']['ready'])
    if ready.get('request_sha256') != body['request_sha256']:
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
            operational={**body['metadata'], 'reason': 'native_ready_identity_mismatch'})
    group = actual.get('ControlGroup', '')
    try:
        group_path = Path('/sys/fs/cgroup')/group.lstrip('/')
        memory = int((group_path/'memory.max').read_text())
        swap = int((group_path/'memory.swap.max').read_text())
        cpu = (group_path/'cpu.max').read_text().strip() if 'local_resources' in body['metadata'] else None
    except (OSError, ValueError):
        memory = swap = cpu = None
    cpu_verified = True
    if 'local_resources' in body['metadata']:
        values = cpu.split() if cpu else []
        cpu_verified = (len(values) == 2 and values[0].isdigit() and values[1].isdigit()
            and int(values[0]) == body['metadata']['cpu_threads']*int(values[1]))
    from .workflow_budget import SLICE as WORKFLOW_SLICE,UNIT as WORKFLOW_UNIT
    if (actual.get('Slice')!=WORKFLOW_SLICE or WORKFLOW_UNIT not in actual.get('BindsTo','').split()
            or not group or memory != policy.memory_bytes or swap != 0 or not cpu_verified or
            actual.get('MemoryMax') != str(policy.memory_bytes) or actual.get('MemorySwapMax') != '0' or
            actual.get('KillMode') != 'control-group' or actual.get('OOMPolicy') != 'kill'):
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
            operational={**body['metadata'], 'reason': 'cgroup_limits_not_verified', 'properties': actual})
    body['metadata']['verified_cgroup'] = {'memory_max': memory, 'memory_swap_max': swap,
        'kill_mode': actual['KillMode'], 'oom_policy': actual['OOMPolicy'],
        'workflow_slice':actual['Slice'],'workflow_owner':WORKFLOW_UNIT}
    if cpu is not None:
        body['metadata']['verified_cgroup'].update(cpu_max=cpu,
            cpu_threads=body['metadata']['cpu_threads'])
    body['stage'] = 'released'
    atomic_json(handle.path, body)
    Path(body['paths']['release']).touch()
    return handle


def _ensure_event_registration(handle, body):
    if 'native_events' not in body:
        return
    from method_loop.durable import DurableExecutionError
    from .native_events import ensure_native_event_target
    try:
        ensure_native_event_target(handle.path)
    except (DurableExecutionError, OSError, ValueError, KeyError, TypeError) as error:
        code = ('native_event_identity_conflict' if isinstance(error, DurableExecutionError)
            and error.failure['code'] == 'identity_conflict' or str(error) == 'native_event_identity_conflict'
            else 'native_event_storage_unavailable')
        raise AcquisitionError(code, phase='local_preflight', operational={
            **body['metadata'], 'reason': 'native_event_registration_failed',
            'exception_type': type(error).__name__}) from error


def status(handle):
    """A read: no controller observation, resubmission or state invention."""
    body = handle.read()
    prepared = body.get('stage') == 'prepared'
    props = {} if prepared else _properties(body['unit'])
    end = _load(body['paths']['status'])
    receipt = _load(body['paths']['result'])
    live = props.get('ActiveState') in {'active', 'activating', 'deactivating', 'reloading'}
    quiescent = (prepared or props.get('ActiveState') in {'inactive', 'failed'}
        or props.get('LoadState') == 'not-found')
    terminal = end is not None and quiescent
    if terminal:
        _release_capacity(body)
    state = ('prepared' if prepared else 'returned' if terminal else 'running' if live and Path(body['paths']['release']).exists()
             else 'starting' if live else 'execution_unknown')
    end_time = end['ended'] if end else None
    elapsed = None
    if end_time is not None and end_time['boot_id'] == body['boot_id']:
        elapsed = (end_time['monotonic_ns']-body['started_monotonic_ns'])/1e9
    elif end_time is None and live and body['boot_id'] == _boot():
        elapsed = (time.monotonic_ns()-body['started_monotonic_ns'])/1e9
    metadata = {**body['metadata'], 'duration_measure': 'systemd_service_wall_seconds',
        'service_exit': end, 'elapsed_seconds': elapsed,
        'native_returncode': receipt['native_returncode'] if receipt else None,
        'observed_scratch_bytes': receipt['observed_scratch_bytes'] if receipt else None}
    if 'statistics' in body['paths']:
        metadata['statistics_export'] = _load(body['paths']['statistics'])
    if 'native_events' in body['paths']:
        metadata['native_events_export'] = _load(body['paths']['native_events'])
    files = {}
    for name in ('stdout', 'stderr'):
        path = Path(body[name])
        try:
            files[name] = {'available': True, 'bytes': path.stat().st_size}
        except FileNotFoundError:
            files[name] = {'available': False, 'bytes': None}
    return {'version': VERSION, 'state': state, 'terminal': terminal, 'quiescent': quiescent,
            'metadata': metadata, 'native_receipt': receipt, 'files': files}


def collect(handle):
    """Return original native outcome; resource/execution failures stay typed."""
    view = status(handle)
    meta, receipt = view['metadata'], view['native_receipt']
    if not view['terminal']:
        raise AcquisitionError('local_job_not_collectable', phase='local_execution',
                               operational={'state': view['state'], **meta})
    exit_info = meta['service_exit']
    reason = exit_info.get('SERVICE_RESULT')
    # A completed historical receipt may contain retired settings. Reading its
    # memory/scratch evidence cannot restore an elapsed-time control.
    policy = LocalJobPolicy(meta['policy']['memory_bytes'], meta['policy']['scratch_bytes'])
    failure = None
    if reason == 'oom-kill':
        failure = {'resource': 'memory_bytes', 'limit': policy.memory_bytes,
                   'evidence': {'systemd_service_result': reason}}
    elif receipt is not None:
        failure = receipt['resource_failure']
        if failure is None and receipt['native_returncode'] == -int(signal.SIGXFSZ):
            failure = {'resource': 'file_bytes', 'limit': policy.scratch_bytes,
                       'evidence': {'native_returncode': receipt['native_returncode']}}
    if failure is not None:
        raise AcquisitionError('local_job_resource_limit', phase='local_execution', operational={**meta, **failure})
    if receipt is None or receipt['execution_failure'] is not None:
        raise AcquisitionError('local_job_execution_error', phase='local_execution', operational={**meta,
            'reason': 'native_receipt_missing' if receipt is None else 'native_command_did_not_start',
            'execution_failure': receipt['execution_failure'] if receipt else None})
    body = handle.read()
    return LocalJobResult(receipt['native_returncode'], Path(body['stdout']), Path(body['stderr']), meta)


def cancel(handle):
    """Stop the original control group; completion is not scientific success."""
    body = handle.read()
    _control(['systemctl', '--user', 'kill', '--kill-whom=all', '--signal=KILL', body['unit']])
    _control(['systemctl', '--user', 'stop', body['unit']])
    properties = _properties(body['unit'])
    if not (properties.get('ActiveState') in {'inactive', 'failed'}
            or properties.get('LoadState') == 'not-found'):
        raise AcquisitionError('local_job_stop_unconfirmed', phase='local_execution')
    _release_capacity(body)


def _release_capacity(body):
    reservation = body.get('capacity_reservation')
    if reservation is not None:
        LocalResources.reopen(reservation['resource']).release_reservation(reservation)


def release(handle):
    """Delete transient control files only after the unit is no longer live.

    Detached callers retain handles/receipts. Blocking callers keep the complete
    returned metadata and native stdout/stderr while releasing control files.
    """
    body = handle.read()
    if not status(handle)['quiescent']:
        raise AcquisitionError('local_job_cleanup_requires_quiescent_unit', phase='local_execution')
    _release_capacity(body)
    _control(['systemctl', '--user', 'reset-failed', body['unit']])
    for path in body['paths'].values():
        Path(path).unlink(missing_ok=True)
        Path(path+'.writing').unlink(missing_ok=True)
    if 'statistics' in body['paths']:
        Path(body['paths']['statistics']+'.lock').unlink(missing_ok=True)
    if 'native_events' in body['paths']:
        Path(body['paths']['native_events']+'.lock').unlink(missing_ok=True)
        Path(body['paths']['status']+'.lock').unlink(missing_ok=True)
    handle.path.unlink()


def run_blocking(command, *, cwd, policy, stdout_path=None, stderr_path=None,
                 stdin_path=None, env=None, cancel_event=None, statistics=None, cpu_threads=1):
    path = Path(cwd).resolve()/('.local-job-'+uuid.uuid4().hex+'.handle.json')
    handle = NativeJobHandle(path)
    try:
        start_job(command, cwd=cwd, policy=policy, handle_path=path, stdout_path=stdout_path,
                  stderr_path=stderr_path, stdin_path=stdin_path, env=env, cancel_event=cancel_event,
                  statistics=statistics, cpu_threads=cpu_threads)
        return wait_job(handle, cancel_event=cancel_event)
    except (OSError, subprocess.SubprocessError) as error:
        raise AcquisitionError('local_job_boundary_unavailable', phase='local_preflight',
            operational={**_metadata(policy), 'reason': type(error).__name__}) from error
    finally:
        if path.exists():
            if not status(handle)['quiescent']:
                cancel(handle)
            release(handle)


def wait_job(handle, *, cancel_event=None):
    """Wait on existing work through the shared lifecycle; never resubmit it."""
    try:
        while True:
            view = status(handle)
            if view['terminal']:
                return collect(handle)
            if cancel_event is not None and cancel_event.is_set():
                raise AcquisitionError('local_job_cancelled', phase='local_execution', operational=view['metadata'])
            if view['state'] == 'execution_unknown':
                raise AcquisitionError('local_job_execution_unknown', phase='local_execution', operational=view['metadata'])
            time.sleep(.05)
    except BaseException:
        if status(handle)['quiescent']:
            # A missing outcome stays an error. Confirmed service quiescence
            # nevertheless proves that its compute reservation can be freed.
            _release_capacity(handle.read())
        else:
            cancel(handle)
        raise
