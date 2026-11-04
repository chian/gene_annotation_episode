"""Calendar backend for an episode's persisted monitor controller.

One timer resumes the original action in this Codex window's bounded launcher.
The resume never submits a PBS job itself and never retries an authentication
failure. Timer registration is retained with the exact original forecast.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from .hpc_queue import digest


def resume_spec(directory, root, payload_argv, schedule, *, window):
    from .workflow_budget import window_units
    window_units(window)
    directory, root = Path(directory).resolve(), Path(root).resolve()
    if not directory.is_relative_to(root/'runs'):
        raise ValueError('monitor_schedule_requires_run_directory')
    if schedule.get('version') == 'hpc_monitor_schedule_v1':
        identity, due = schedule['schedule_ref'], schedule['reconsider_at']
        if schedule['wake_action']['tool'] != 'hpc.monitor' or not schedule['valuation']['schedule']:
            raise ValueError('explicit_pending_monitor_wake_required')
    else:
        identity, due = schedule['wait_id'], schedule['condition']['reconsider_at']
        if schedule['condition']['events'] or due is None:
            raise ValueError('legacy_checkpoint_requires_timer_only_wait')
    when = datetime.fromisoformat(due.replace('Z', '+00:00'))
    if when.tzinfo is None:
        raise ValueError('monitor_wake_requires_timezone')
    signature = digest({'window': window, 'directory': str(directory),
                        'payload_argv': payload_argv, 'schedule': schedule})
    invocation = root/'runs'/('hpc_resume_'+signature[:24])
    unit = 'gene-hpc-wake-'+window.replace('-', '')+'-'+signature[:16]
    command = ['/bin/bash', str(root/'tools'/'one_workflow.sh'), str(invocation), '--', *payload_argv]
    return {'version': 'hpc_calendar_resume_v1', 'event': 'episode_checkpointed',
            'identity': identity, 'resume_at': when.isoformat(), 'timer': unit+'.timer',
            'controller_run_directory': str(invocation), 'command': command,
            'backend': 'systemd_calendar_v1', 'window': window, 'schedule': schedule,
            'registration_argv': ['systemd-run', '--user', '--quiet', '--collect', '--unit='+unit,
                '--on-calendar='+when.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                '--timer-property=AccuracySec=1s', '--timer-property=RemainAfterElapse=no',
                '--property=WorkingDirectory='+str(root), '--setenv=CODEX_THREAD_ID='+window, *command]}


def register_resume(directory, root, payload_argv, schedule):
    spec = resume_spec(directory, root, payload_argv, schedule, window=os.environ['CODEX_THREAD_ID'])
    retained = Path(directory)/'monitor-scheduler'
    retained.mkdir(exist_ok=True)
    record = retained/(digest(spec)+'.json')
    serialized = json.dumps(spec, indent=2)+'\n'
    if record.exists() and record.read_text() != serialized:
        raise ValueError('monitor_timer_registration_identity_conflict')
    record.write_text(serialized)
    active = subprocess.run(['systemctl', '--user', 'is-active', spec['timer']],
                            capture_output=True, text=True, check=False)
    if active.stdout.strip() != 'active':
        if Path(spec['controller_run_directory']).exists():
            raise ValueError('monitor_wake_already_dispatched_no_automatic_retry')
        subprocess.run(spec['registration_argv'], check=True)
    (Path(directory)/'scheduled-resume.json').write_text(serialized)
    return spec
