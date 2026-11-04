"""Serial work portfolio inside one real PBS allocation.

This is an execution tool, not an episode. The owning episode chooses the
portfolio and may reorder its remaining approved units at unit boundaries.
There is no holding loop, scheduler polling, automatic resubmission or local
fallback. Interrupted unit intents are never repeated on restart.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def publish(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.writing')
    with temporary.open('w') as stream:
        stream.write(canonical(value)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def confined(root, path):
    selected = Path(path).resolve()
    if not selected.is_relative_to(root):
        raise ValueError('allocation_path_outside_workspace')
    return selected


def run(manifest_path, expected_sha):
    if not os.environ.get('PBS_JOBID') or not os.environ.get('PBS_NODEFILE'):
        raise RuntimeError('real_PBS_allocation_required; no_local_fallback')
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    if digest(manifest) != expected_sha:
        raise ValueError('allocation_manifest_changed')
    root = Path(manifest['workspace']).resolve()
    if not root.is_relative_to('/lus/flare/projects/BioReason-Aurora-Test/chian/runs'):
        raise ValueError('BioReason_project_run_workspace_required')
    confined(root, manifest_path)
    status_path = root/'allocation-status.json'
    lock = (root/'allocation.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if status_path.exists():
        raise RuntimeError('allocation_already_started; inspect_original_intents')
    started, clock = time.time(), time.monotonic()
    state = {'version': 'hpc_allocation_status_v1', 'manifest_sha256': expected_sha,
        'plan_id': manifest['plan_id'], 'job_id': os.environ['PBS_JOBID'],
        'started_at': started, 'updated_at': started, 'state': 'running', 'units': [],
        'wall_seconds': manifest['wall_seconds'], 'current_unit_id': None}
    publish(status_path, state)
    units = {unit['unit_id']: unit for unit in manifest['units']}
    order = list(units)
    while order:
        control = root/'allocation-control.json'
        if control.exists():
            selection = json.loads(control.read_text())
            begun = {row['unit_id'] for row in state['units']}
            if (selection['manifest_sha256'] != expected_sha or not set(selection['unit_ids']) <= set(units)
                    or not set(units)-begun <= set(selection['unit_ids'])):
                raise ValueError('allocation_control_not_in_original_manifest')
            order = selection['unit_ids']
        done = {row['unit_id'] for row in state['units']}
        pending = [identity for identity in order if identity not in done]
        if not pending:
            break
        unit = units[pending[0]]
        remaining = manifest['wall_seconds']-(time.monotonic()-clock)-manifest['shutdown_margin_seconds']
        if remaining < unit['minimum_seconds']:
            state['stop_reason'] = 'remaining_allocation_below_next_unit_minimum'
            break
        unit_directory = confined(root, root/'units'/unit['unit_id'])
        unit_directory.mkdir(parents=True, exist_ok=False)
        environment = dict(os.environ)
        environment.update(unit['environment'])
        for name in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'PIP_CACHE_DIR',
                     'NUMBA_CACHE_DIR', 'PYTHONUSERBASE', 'CONDA_PKGS_DIRS'):
            directory = unit_directory/name.lower()
            directory.mkdir()
            environment[name] = str(directory)
        environment.update(PYTHONDONTWRITEBYTECODE='1', HPC_UNIT_DIRECTORY=str(unit_directory),
                           HPC_UNIT_ID=unit['unit_id'], HPC_PLAN_ID=manifest['plan_id'])
        intent = {'unit_id': unit['unit_id'], 'obligation_id': unit['obligation_id'],
                  'started_at': time.time(), 'state': 'running'}
        # The intent reaches disk before a command can begin.
        publish(unit_directory/'intent.json', {**intent, 'argv': unit['argv'], 'plan_id': manifest['plan_id']})
        state['units'].append(intent)
        state.update(current_unit_id=unit['unit_id'], updated_at=time.time())
        publish(status_path, state)
        timeout = min(remaining, unit['maximum_seconds'])
        code, reason = 127, None
        with (unit_directory/'stdout').open('wb') as stdout, (unit_directory/'stderr').open('wb') as stderr:
            try:
                child = subprocess.Popen(unit['argv'], cwd=unit_directory, env=environment,
                                         stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    code = child.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=min(10, manifest['shutdown_margin_seconds']))
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                    code, reason = 124, 'unit_time_budget_exhausted'
            except OSError as error:
                reason = type(error).__name__
        intent.update(state='complete' if code == 0 else 'failed', returncode=code,
                      failure=reason, finished_at=time.time())
        result_path = confined(root, unit_directory/'result.json')
        if code == 0 and result_path.is_file() and result_path.stat().st_size <= manifest['result_limit_bytes']:
            payload = result_path.read_bytes()
            intent.update(result_path=str(result_path), result_sha256=hashlib.sha256(payload).hexdigest(),
                          result_bytes=len(payload))
        else:
            intent['result_path'] = None
        publish(unit_directory/'receipt.json', intent)
        state.update(current_unit_id=None, updated_at=time.time())
        publish(status_path, state)
    state.update(state='complete', finished_at=time.time(), updated_at=time.time())
    publish(status_path, state)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest')
    parser.add_argument('sha256')
    args = parser.parse_args()
    return run(args.manifest, args.sha256)


if __name__ == '__main__':
    raise SystemExit(main())
