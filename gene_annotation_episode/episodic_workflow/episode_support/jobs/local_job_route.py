"""The route of ``job_access`` to detached local jobs: the durable systemd lifecycle of this machine.

``LocalJobRoute`` is one resource of the ``JobAccess`` service (``episode_runtime/job_access.py``, which states the
route protocol). A job is a command that runs as its own systemd user service inside the workflow's slice
(``gene_annotation_episode.native_lifecycle``: memory, swap and CPU limits of the caller's ``LocalJobPolicy``,
enforced by the service's control group), so it goes on after the Episode, and the process, that launched it.

The job's directory is ``<workspace>/<handle>``. The handle comes from the launching unit's operation key, so a
unit that runs again names the same directory: ``submit`` then finds the job's native handle file and takes that
job up (``adopted``) instead of preparing another. A reservation that was prepared and never dispatched is
dispatched; a dispatch that was cut during its handshake is resumed; nothing is submitted twice
(``native_lifecycle.start_prepared``).

The job runs ``detached_job.py``, which runs the command, writes its receipt (``result.json``) and publishes the
receipt to the native event ledger from the job's own process. ``submit`` registers the job as an event target of
that ledger before it starts the job, so a unit can wait for the job's end through the ``native_events`` service.

A job is ``{'command': [argv...], 'env': {name: value}}``. Staged input files are written into the job's directory
under the names the launching tool gives; they are not results. Every other regular file the job leaves in its
directory is a result (``stdout.log``, ``stderr.log``, ``result.json`` and what the command wrote).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from episode_runtime.job_access import RouteRequestError
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.local_job_policy import LocalJobPolicy

from .native_event_ledger import NativeEventLedger, native_target_handle

REPOSITORY = Path(__file__).resolve().parents[4]
JOB_PROCESS = Path(__file__).with_name('detached_job.py')
NATIVE_FILE, INPUTS_FILE, CANCELLED_FILE = 'native.json', 'inputs.json', 'cancelled'
MEDIA_TYPES = {'.json': 'application/json', '.log': 'text/plain', '.txt': 'text/plain'}
ENDED = ('finished', 'failed', 'cancelled')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _request_failure(error):
    return RouteRequestError(error.code, {'phase': error.phase, 'operational': json.loads(json.dumps(
        error.operational, default=str))})


class LocalJobRoute:
    """Detached local jobs below one workspace directory, limited by one policy."""

    kind = 'local'

    def __init__(self, workspace, policy, event_ledger_directory, *, resource_id, cpu_threads=1):
        if not isinstance(policy, LocalJobPolicy):
            raise TypeError('local_job_route_requires_a_LocalJobPolicy')
        if type(resource_id) is not str or not resource_id:
            raise ValueError('local_job_route_resource_id_must_be_text')
        if type(cpu_threads) is not int or cpu_threads < 1:
            raise ValueError('local_job_route_cpu_threads_must_be_a_positive_integer')
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.policy, self.resource_id, self.cpu_threads = policy, resource_id, cpu_threads
        self.event_ledger_directory = Path(event_ledger_directory).resolve()
        self._ledger = NativeEventLedger(self.event_ledger_directory)

    def describe(self):
        return {'resource_id': self.resource_id, 'kind': self.kind, 'workspace': str(self.workspace),
                'policy': self.policy.to_dict(), 'cpu_threads': self.cpu_threads}

    # -- the job's directory ---------------------------------------------------------------------------------
    def _directory(self, handle, native_identity=None):
        directory = self.workspace / handle
        if native_identity is not None and native_identity['directory'] != str(directory):
            raise RouteRequestError('local_job_directory_is_not_in_this_workspace',
                                    {'recorded': native_identity['directory'], 'workspace': str(self.workspace)})
        return directory

    @staticmethod
    def _confined(directory, name):
        path = (directory / name).resolve()
        if type(name) is not str or not name or not path.is_relative_to(directory) or path == directory:
            raise ValueError('local_job_file_name_must_stay_inside_the_job_directory:' + repr(name))
        return path

    def _native(self, handle, native_identity):
        path = self._directory(handle, native_identity) / NATIVE_FILE
        if not path.exists():
            raise RouteRequestError('local_job_not_found', {'job': handle})
        return native.NativeJobHandle(path)

    # -- submit ----------------------------------------------------------------------------------------------
    def submit(self, handle, job, files, owner):
        if not isinstance(job, dict) or set(job) != {'command', 'env'}:
            raise ValueError('local_job_requires_exactly_command_and_env')
        directory = self._directory(handle)
        job_handle = native.NativeJobHandle(directory / NATIVE_FILE)
        adopted = job_handle.path.exists()
        try:
            if not adopted:
                # Nothing was dispatched for this handle: a native handle file is published before any dispatch.
                directory.mkdir(parents=True, exist_ok=True)
                for name, data in files.items():
                    path = self._confined(directory, name)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                (directory / INPUTS_FILE).write_text(json.dumps(sorted(files)))
                command = [sys.executable, '-B', str(JOB_PROCESS), str(self.event_ledger_directory),
                           str(job_handle.path), str(directory / 'result.json'), '--', *job['command']]
                native.prepare_job(command, cwd=directory, policy=self.policy, handle_path=job_handle.path,
                                   env={**job['env'], 'PYTHONPATH': str(REPOSITORY),
                                        'PYTHONDONTWRITEBYTECODE': '1'}, cpu_threads=self.cpu_threads)
            body = job_handle.read()
            identity = {'kind': 'systemd_user_service', 'unit': body['unit'],
                        'request_sha256': body['request_sha256']}
            target = native_target_handle(identity)
            self._ledger.register_native_target({
                'version': 'native_event_registration_v1', 'handle': target, 'run_id': owner['run_id'],
                'owner_episode_id': owner['episode_id'], 'job_ref': handle, 'registry_ref': 'job_ledger:' + handle,
                'resource_id': self.resource_id, 'native_identity': identity})
            native.start_prepared(job_handle)
        except native.AcquisitionError as error:
            raise _request_failure(error) from error
        body = job_handle.read()
        return {'native': {'directory': str(directory), 'unit': body['unit'],
                           'request_sha256': body['request_sha256'], 'event_target': target},
                'submitted_at': body['started_at'], 'adopted': adopted,
                'reply': {'unit': body['unit'], 'stage': body['stage'], 'started_at': body['started_at'],
                          'policy': body['metadata']['policy'], 'cpu_threads': body['metadata']['cpu_threads'],
                          'verified_cgroup': body['metadata']['verified_cgroup']}}

    # -- status ----------------------------------------------------------------------------------------------
    def status(self, handle, native_identity):
        directory = self._directory(handle, native_identity)
        try:
            view = native.status(self._native(handle, native_identity))
        except native.AcquisitionError as error:
            raise _request_failure(error) from error
        receipt_path = directory / 'result.json'
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        if receipt is not None:
            # The command has ended and its receipt is committed: its output files are complete, whether or not
            # the service that carried it has left the system yet.
            state = 'finished' if receipt['returncode'] == 0 else 'failed'
        elif (directory / CANCELLED_FILE).exists() and view['quiescent']:
            state = 'cancelled'      # stopped before its command ended
        elif view['state'] in ('prepared', 'starting'):
            state = 'queued'
        elif view['state'] == 'running':
            state = 'running'
        elif view['state'] == 'returned':
            state = 'failed'         # the service ended without a receipt of its command (killed, out of memory)
        else:
            state = 'unknown'
        metadata = view['metadata']
        return {'state': state, 'result_available': receipt is not None or bool(view['terminal']),
                'observed_at': utc_now(),
                'reply': {'native_state': view['state'], 'terminal': view['terminal'],
                          'quiescent': view['quiescent'], 'files': view['files'],
                          'elapsed_seconds': metadata['elapsed_seconds'], 'service_exit': metadata['service_exit'],
                          'native_returncode': metadata['native_returncode'],
                          'observed_scratch_bytes': metadata['observed_scratch_bytes'], 'receipt': receipt}}

    async def wait(self, handle, native_identity):
        """Return when the job has ended. This waits on the job, not on a clock: there is no deadline."""
        while True:
            status = self.status(handle, native_identity)
            if status['state'] in ENDED:
                return
            if status['state'] == 'unknown':
                raise RouteRequestError('local_job_execution_unknown', status['reply'])
            await asyncio.sleep(0.05)

    # -- results ---------------------------------------------------------------------------------------------
    def results(self, handle, native_identity):
        directory = self._directory(handle, native_identity)
        status = self.status(handle, native_identity)
        if not status['result_available']:
            raise RouteRequestError('results_not_available', {'job': handle, 'state': status['state']})
        staged = set(json.loads((directory / INPUTS_FILE).read_text()))
        staged |= {NATIVE_FILE, INPUTS_FILE, CANCELLED_FILE}
        found = []
        for path in sorted(directory.rglob('*')):
            name = path.relative_to(directory).as_posix()
            if path.is_file() and not path.is_symlink() and name not in staged and not name.startswith('.local-job-'):
                found.append({'name': name, 'bytes': path.stat().st_size,
                              'media_type': MEDIA_TYPES.get(path.suffix, 'application/octet-stream')})
        return found

    def read(self, handle, native_identity, name, offset, limit):
        path = self._confined(self._directory(handle, native_identity), name)
        if not path.is_file():
            raise RouteRequestError('result_file_missing', {'job': handle, 'name': name})
        with path.open('rb') as stream:
            stream.seek(offset)
            return stream.read(limit)

    # -- cancel ----------------------------------------------------------------------------------------------
    def cancel(self, handle, native_identity):
        job_handle = self._native(handle, native_identity)
        (job_handle.path.parent / CANCELLED_FILE).touch()
        try:
            native.cancel(job_handle)
        except native.AcquisitionError as error:
            raise _request_failure(error) from error
        return {'reply': {'unit': job_handle.read()['unit'], 'cancelled_at': utc_now()}}


__all__ = ['LocalJobRoute']
