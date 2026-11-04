"""Caller-owned local capacity, shared by independent registries and runs.

Reservations precede native dispatch and survive the launching process. Only
observed service quiescence, cancellation, or a never-dispatched dead owner can
free capacity. Unknown execution retains its reservation.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tomllib
import uuid

from .acquisition import AcquisitionError


VERSION = 'shared_local_resources_v1'
DIRECTORY_ENV = 'GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY'
_LIVE = {'active', 'activating', 'deactivating', 'reloading'}


def _boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def _process_start(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


@lru_cache(maxsize=1)
def _runs_directory():
    # The common Git directory also unifies worktrees and run source snapshots.
    for root in Path(__file__).resolve().parents:
        git = root/'.git'
        if git.is_file():
            pointer = git.read_text().strip().removeprefix('gitdir: ')
            git = (root/pointer).resolve()
        if git.is_dir():
            common = git/'commondir'
            shared = (git/common.read_text().strip()).resolve() if common.is_file() else git.resolve()
            return shared.parent/'runs'
    return Path.cwd().resolve()/'runs'


def _resource_id():
    machine = Path('/etc/machine-id')
    identity = machine.read_text().strip() if machine.exists() else _boot()
    return 'local-host:' + hashlib.sha256(f'{identity}:{os.getuid()}'.encode()).hexdigest()[:24]


def _limits(settings):
    defaults = tomllib.loads(Path(__file__).with_name('defaults.toml').read_text())['local_resources']
    if not isinstance(settings, dict) or set(settings)-set(defaults):
        raise ValueError('invalid_local_resource_settings')
    result = {**defaults, **settings}
    if any(type(value) is not int or value <= 0 for value in result.values()):
        raise ValueError('invalid_local_resource_limits')
    return result


class LocalResources:
    def __init__(self, directory, settings=None, *, workflow_slice=None):
        if settings is not None and not isinstance(settings, dict):
            raise ValueError('invalid_local_resource_settings')
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory/'capacity.sqlite3'
        with self._transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS configuration (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS reservations ('
                'unit TEXT PRIMARY KEY, token TEXT UNIQUE NOT NULL, handle TEXT NOT NULL,'
                'cpu_threads INTEGER NOT NULL, memory_bytes INTEGER NOT NULL, scratch_bytes INTEGER NOT NULL,'
                'owner_pid INTEGER NOT NULL, owner_start TEXT NOT NULL, boot_id TEXT NOT NULL,'
                'created_at TEXT NOT NULL)')
            saved = db.execute('SELECT value FROM configuration WHERE id=1').fetchone()
            if saved is None:
                definition = {'version': VERSION, 'resource_id': _resource_id(),
                    'directory': str(self.directory), 'limits': _limits(settings or {})}
                if workflow_slice is not None:
                    definition['workflow_slice'] = workflow_slice
                db.execute('INSERT INTO configuration VALUES(1,?)', (json.dumps(definition, sort_keys=True),))
            else:
                definition = json.loads(saved[0])
                if (definition.get('version') != VERSION or definition.get('resource_id') != _resource_id()
                        or definition.get('directory') != str(self.directory)
                        or definition.get('workflow_slice') != workflow_slice):
                    raise ValueError('local_resource_binding_conflict')
                _limits(definition['limits'])
                if settings is not None:
                    requested = {**definition['limits'], **settings}
                    if _limits(requested) != definition['limits']:
                        raise ValueError('local_resource_limits_conflict')
            self.definition = definition

    @classmethod
    def configured(cls, settings=None):
        selected = os.environ.get(DIRECTORY_ENV)
        from .workflow_budget import ENV, active_budget
        if selected is None and os.environ.get(ENV):
            budget = active_budget()
            return cls(Path(budget['run_directory'])/'local-resources', settings,
                workflow_slice=budget['slice'])
        directory = Path(selected) if selected else _runs_directory()/'local-resources'/_resource_id().split(':')[1]
        return cls(directory, settings)

    @classmethod
    def reopen(cls, definition):
        value = cls(definition['directory'], workflow_slice=definition.get('workflow_slice'))
        if value.as_record() != definition:
            raise ValueError('local_resource_binding_conflict')
        return value

    def as_record(self):
        return json.loads(json.dumps(self.definition))

    @contextmanager
    def _transaction(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _refresh(self, db):
        from .native_lifecycle import _control, _properties
        jobs = []
        boot = _boot()
        registered = set()
        for row in db.execute('SELECT * FROM reservations ORDER BY created_at').fetchall():
            registered.add(row['unit'])
            if row['boot_id'] != boot:
                db.execute('DELETE FROM reservations WHERE token=?', (row['token'],))
                continue
            try:
                body = json.loads(Path(row['handle']).read_text())
            except (OSError, ValueError):
                body = {}
            if body and body.get('unit') != row['unit']:
                raise ValueError('local_resource_reservation_identity_conflict')
            try:
                properties = _properties(row['unit'])
            except (OSError, subprocess.SubprocessError):
                properties = {}
            active = properties.get('ActiveState')
            live = active in _LIVE
            quiescent = active in {'failed', 'inactive'} or properties.get('LoadState') == 'not-found'
            owner_live = _process_start(row['owner_pid']) == row['owner_start']
            never_dispatched = body.get('stage') == 'prepared' and not owner_live
            ended = body.get('paths', {}).get('status')
            terminal = ended is not None and Path(ended).is_file()
            if quiescent and (terminal or never_dispatched):
                db.execute('DELETE FROM reservations WHERE token=?', (row['token'],))
                continue
            state = ('running' if live and Path(body.get('paths', {}).get('release', '/nonexistent')).is_file()
                else 'starting' if live else 'reserved' if body.get('stage') == 'prepared' and owner_live
                else 'execution_unknown')
            jobs.append({'reservation_ref': row['token'], 'execution_handle': row['unit'], 'state': state,
                'allocation': {key: row[key] for key in ('cpu_threads', 'memory_bytes', 'scratch_bytes')}})
        # Older or independently configured registries can already have native
        # services on this host. Unknown allocations conservatively occupy the
        # entire budget rather than advertising those resources as free.
        try:
            inventory = _control(['systemctl', '--user', 'list-units', '--all', '--type=service',
                '--plain', '--no-legend', '--no-pager', 'gene-local-job-*.service'])
        except (OSError, subprocess.SubprocessError):
            inventory = None
        if inventory is None or inventory.returncode != 0:
            jobs.append({'reservation_ref': None, 'execution_handle': None,
                'state': 'capacity_unavailable',
                'allocation': {key: self.definition['limits'][key]
                    for key in ('cpu_threads', 'memory_bytes', 'scratch_bytes')}})
        else:
            for line in inventory.stdout.splitlines():
                fields = line.split()
                if len(fields) >= 4 and fields[0] not in registered and fields[2] in _LIVE:
                    if self.definition.get('workflow_slice'):
                        observed_slice = _properties(fields[0]).get('Slice')
                        if observed_slice and observed_slice != self.definition['workflow_slice']:
                            continue
                    jobs.append({'reservation_ref': None, 'execution_handle': fields[0],
                        'state': 'untracked_running',
                        'allocation': {key: self.definition['limits'][key]
                            for key in ('cpu_threads', 'memory_bytes', 'scratch_bytes')}})
        return jobs

    def _view(self, jobs):
        limits = self.definition['limits']
        used = {key: sum(job['allocation'][key] for job in jobs)
            for key in ('cpu_threads', 'memory_bytes', 'scratch_bytes')}
        remaining = {key: max(0, limits[key]-used[key]) for key in used}
        remaining['job_slots'] = max(0, limits['max_running_jobs']-len(jobs))
        return {'version': VERSION, 'resource_id': self.definition['resource_id'],
            'observed_at': datetime.now(timezone.utc).isoformat(), 'limits': dict(limits),
            'reserved': {**used, 'job_slots': len(jobs)}, 'available': remaining,
            'state': ('unknown' if any(job['state']=='capacity_unavailable' for job in jobs)
                else 'busy' if not all(remaining.values()) else 'available'), 'jobs': jobs,
            'admission': 'atomic_shared_host_reservation_before_native_dispatch',
            'unknown_execution': 'retains_capacity_until_quiescence_is_established'}

    def snapshot(self):
        with self._transaction() as db:
            return self._view(self._refresh(db))

    def reserve(self, handle, *, cpu_threads, policy):
        requested = {'cpu_threads': cpu_threads, 'memory_bytes': policy.memory_bytes,
            'scratch_bytes': policy.scratch_bytes}
        if any(type(value) is not int or value <= 0 for value in requested.values()):
            raise ValueError('invalid_local_resource_allocation')
        body = handle.read()
        with self._transaction() as db:
            jobs = self._refresh(db)
            view = self._view(jobs)
            if view['state'] == 'unknown':
                raise AcquisitionError('local_job_boundary_unavailable', phase='local_admission',
                    operational={'reason': 'local_capacity_unavailable', 'retryable': True,
                        'local_resources': view})
            for key, value in requested.items():
                if value > view['limits'][key]:
                    raise AcquisitionError('local_job_resource_limit', phase='local_admission',
                        operational={'resource': key, 'limit': view['limits'][key], 'requested': value,
                            'retryable': False, 'local_resources': view})
            if (view['available']['job_slots'] == 0 or any(value > view['available'][key]
                    for key, value in requested.items())):
                raise AcquisitionError('local_resource_busy', phase='local_admission', operational={
                    'retryable': True, 'retry_same_prepared_job': True, 'local_resources': view})
            token = 'local_reservation_' + uuid.uuid4().hex
            db.execute('INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?,?)',
                (body['unit'], token, str(handle.path.resolve()), requested['cpu_threads'],
                 requested['memory_bytes'], requested['scratch_bytes'], os.getpid(),
                 _process_start(os.getpid()), _boot(), datetime.now(timezone.utc).isoformat()))
            return {'resource': self.as_record(), 'reservation_ref': token,
                'execution_handle': body['unit'], 'allocation': requested}

    def release_reservation(self, reservation):
        if reservation['resource'] != self.as_record():
            raise ValueError('local_resource_binding_conflict')
        with self._transaction() as db:
            db.execute('DELETE FROM reservations WHERE token=? AND unit=?',
                (reservation['reservation_ref'], reservation['execution_handle']))

    def validate_reservation(self, reservation):
        if reservation['resource'] != self.as_record():
            raise ValueError('local_resource_binding_conflict')
        with self._transaction() as db:
            row = db.execute('SELECT * FROM reservations WHERE token=? AND unit=?',
                (reservation['reservation_ref'], reservation['execution_handle'])).fetchone()
            if row is None or any(row[key] != value for key, value in reservation['allocation'].items()):
                raise ValueError('local_resource_reservation_unavailable')


__all__ = ['LocalResources', 'VERSION', 'DIRECTORY_ENV']
