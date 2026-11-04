"""Actual local operations selected by a practical episode; no decision loop.

Native commands use the existing durable systemd lifecycle. An interrupted
action reopens its original handle; it never creates a replacement command.
"""
from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .local_jobs import LocalJobPolicy


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def confined(path, workspace):
    path = Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(Path(workspace).resolve()):
        raise ValueError('practical_write_outside_workspace')
    return path.resolve()


def path_facts(assignment):
    paths, hash_paths = set(), set()
    for requirement in assignment['progress_requirements']:
        predicate = requirement['predicate']
        if predicate['kind'] in {'path_exists', 'file_sha256'}:
            paths.add(predicate['path'])
            if predicate['kind'] == 'file_sha256':
                hash_paths.add(predicate['path'])
        elif predicate['kind'] == 'requested_job_outputs':
            paths.update(predicate['output_paths'])
    values = []
    for name in sorted(paths):
        path = Path(name)
        exists = path.exists()
        kind = ('file' if path.is_file() else 'directory' if path.is_dir()
                else 'other' if exists else 'missing')
        sha = None
        if kind == 'file' and name in hash_paths:
            with path.open('rb') as stream:
                hasher = hashlib.sha256()
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    hasher.update(block)
                sha = hasher.hexdigest()
        values.append({'path': name, 'exists': exists, 'object_type': kind, 'sha256': sha})
    return values


def log_tail(path, limit=8192):
    path = Path(path)
    if not path.is_file():
        return {'path': str(path), 'available': False}
    size = path.stat().st_size
    offset = max(0, size-limit)
    with path.open('rb') as stream:
        stream.seek(offset)
        raw = stream.read(min(limit, max(0, size-offset)))
    return {'path': str(path), 'available': True, 'bytes': size,
            'tail_byte_offset': offset, 'bytes_base64': base64.b64encode(raw).decode('ascii'),
            'tail_utf8': raw.decode('utf-8', errors='replace')}


class LocalPracticalOperations:
    """Local preparation commands and detached requested computation are distinct."""

    def __init__(self, configuration):
        if (not {'kind', 'workspace', 'policy'} <= set(configuration)
                or set(configuration) - {'kind', 'workspace', 'policy', 'native_hmmer'}
                or configuration['kind'] != 'local'):
            raise ValueError('explicit_local_practical_configuration_required')
        self.configuration = json.loads(json.dumps(configuration, allow_nan=False))
        self.policy = LocalJobPolicy(**configuration['policy'])
        if 'native_hmmer' in configuration:
            from .native_hmmer_tool_info import validate_native_hmmer_bindings
            validate_native_hmmer_bindings(configuration['native_hmmer'])

    def initial_outcome(self, assignment):
        self.validate_assignment(assignment)
        return {'facts': {'paths': path_facts(assignment)}}

    def validate_assignment(self, assignment):
        if 'native_hmmer' in assignment['requested_job']:
            from .native_hmmer_contracts import validate_native_hmmer_requested_job
            job = validate_native_hmmer_requested_job(assignment['requested_job'])['native_hmmer']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_hmmer', []):
                raise ValueError('native_hmmer_program_mode_software_not_bound')
            if not assignment.get('resource_id'):
                raise ValueError('native_hmmer_resource_identity_required')
        constraints = assignment['constraints']
        allowed = {'allocation', 'memory_bytes', 'scratch_bytes', 'wall_seconds'}
        if set(constraints)-allowed:
            raise ValueError('unsupported_explicit_local_constraint')
        policy = self.configuration['policy']
        for key in allowed-{'allocation'}:
            if key in constraints and constraints[key] != policy[key]:
                raise ValueError('practical_local_allocation_constraint_mismatch')
        if 'allocation' in constraints and constraints['allocation'] != policy:
            raise ValueError('practical_local_allocation_constraint_mismatch')

    def validate_action(self, assignment, tool_name, arguments):
        if 'argv' in arguments and any(not part or '\0' in part for part in arguments['argv']):
            raise ValueError('invalid_practical_command_argument')

    async def read_inventory(self, path):
        path = confined(path, self.configuration['workspace'])
        return await asyncio.to_thread(path.read_bytes)

    def _action_directory(self, state, operation_key):
        root = confined(Path(state.assignment['workspace'])/'.episode-operations'/
            digest({'run': state.run_id, 'episode': state.episode_id})/digest(operation_key),
            self.configuration['workspace'])
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _handle(self, state, operation_key, command, *, cwd, env, native_hmmer=False):
        root = self._action_directory(state, operation_key)
        handle = native.NativeJobHandle(root/'native.json')
        if native_hmmer:
            from .native_hmmer_local import prepare_local_hmmer
            handle = prepare_local_hmmer(state, operation_key, root=root, policy=self.policy)
        elif not handle.path.exists():
            # Native lifecycle requires all control/output files under cwd.
            # A tiny explicit runner preserves the selected working directory.
            runner = root/'invoke.py'
            runner.write_text('import json,os,sys\nr=json.load(open(sys.argv[1]))\n'
                'os.chdir(r["cwd"])\nos.execvpe(r["argv"][0],r["argv"],'
                '{**os.environ,**r["environment"]})\n')
            request = root/'invoke.json'
            request.write_text(json.dumps({'cwd': str(cwd), 'argv': command,
                'environment': env}, allow_nan=False))
            import sys
            native.prepare_job([sys.executable, str(runner), str(request)], cwd=root,
                policy=self.policy, handle_path=handle.path,
                env={'TMPDIR': str(root), 'XDG_CACHE_HOME': str(root/'cache'),
                     'PYTHONDONTWRITEBYTECODE': '1'})
        body = handle.read()
        if body['stage'] == 'prepared':
            native.start_prepared(handle)
        elif body['stage'] == 'submitting':
            native.resume_start(handle)
        return handle

    def _job_handle(self, state):
        for receipt in reversed(state.receipts()):
            job = receipt['outcome'].get('facts', {}).get('requested_job')
            if job is not None:
                return native.NativeJobHandle(Path(job['execution_id']))
        raise ValueError('requested_job_not_started')

    def _job_fact(self, state, handle, view):
        request = state.assignment['requested_job']
        if 'native_hmmer' in request:
            from .native_hmmer_local import local_hmmer_plan
            local_hmmer_plan(state.assignment, str(handle.path))
        rc = view['metadata'].get('native_returncode')
        status = ('completed' if rc == 0 else 'failed') if view['terminal'] else (
            'running' if view['state'] == 'running' else 'submitted' if view['state'] == 'starting'
            else 'unknown')
        outputs = [p for r in state.assignment['progress_requirements']
            if r['predicate']['kind'] == 'requested_job_outputs'
            for p in r['predicate']['output_paths']]
        return {'requested_job_sha256': digest(request), 'argv': request['argv'],
            'environment': request['environment'], 'resource_kind': 'local',
            'execution_id': str(handle.path), 'status': status, 'returncode': rc,
            'output_paths': sorted(set(outputs)), 'handoff': {
                'execution_id': str(handle.path), 'monitor_operation': 'practical.job.status',
                'results_operation': 'practical.job.collect'}}

    def observe_execution(self, assignment, execution_id, *, log_window_bytes=8192,
                          log_roles=('stdout', 'stderr'), attempt_id=None, **identity):
        """Read one selected exact native attempt, without opening episode state."""
        self.validate_assignment(assignment)
        if type(log_window_bytes) is not int or log_window_bytes <= 0:
            raise ValueError('positive_log_window_required')
        if any(role not in {'stdout', 'stderr'} for role in log_roles):
            raise ValueError('unsupported_native_log_role')
        handle = native.NativeJobHandle(confined(execution_id, assignment['workspace']))
        # The source pins this handle; never replace it with a later receipt.
        body = handle.read()
        request = json.loads((handle.path.parent/'invoke.json').read_text())
        hmmer_plan = None
        if 'native_hmmer' in assignment['requested_job']:
            from .native_hmmer_local import local_hmmer_plan
            hmmer_plan = local_hmmer_plan(assignment, execution_id)
        if (request['argv'] != assignment['requested_job']['argv']
                or request['environment'] != assignment['requested_job']['environment']):
            raise ValueError('practical_execution_request_identity_conflict')
        view = native.status(handle)
        metadata = view['metadata']
        rc = metadata.get('native_returncode')
        state = (('completed' if rc == 0 else 'failed') if view['terminal'] else
                 'running' if view['state'] == 'running' else
                 'submitted' if view['state'] in {'prepared', 'starting'} else 'unknown')
        failure = None
        if state == 'failed':
            failure = ('native_returncode_unavailable' if rc is None else 'native_nonzero_returncode')
        measurements = []
        elapsed = metadata.get('elapsed_seconds')
        if view['terminal'] and elapsed is not None:
            measurements.append({'measure': metadata['duration_measure'], 'seconds': elapsed})
        outputs, logs = [], []
        for role in ('stdout', 'stderr'):
            if hmmer_plan is not None:
                native_job = assignment['requested_job']['native_hmmer']
                selected_role = 'stockholm' if role == 'stdout' and native_job['program'] == 'hmmalign' else role
                selected_output = next(item for item in native_job['outputs'] if item['role'] == selected_role)
                path = confined(Path(hmmer_plan['attempt_directory'])/selected_output['relative_path'], assignment['workspace'])
            else:
                path = confined(body[role], assignment['workspace'])
            tail = log_tail(path, log_window_bytes)
            outputs.append({'role': role, 'available': tail['available'],
                'bytes': tail.get('bytes'), 'writer_closed': tail['available'] and view['terminal']})
            if role in log_roles and tail['available']:
                logs.append({'role': role, 'path': str(path), 'offset': tail['tail_byte_offset'],
                    'observed_size': tail['bytes'], 'bytes_base64': tail['bytes_base64']})
        result_available = False
        paths = sorted(set(path for row in assignment['progress_requirements']
            if row['predicate']['kind'] == 'requested_job_outputs'
            for path in row['predicate']['output_paths']))
        for name in paths:
            path = confined(name, assignment['workspace'])
            available = path.is_file()
            result_available |= available
            outputs.append({'role': 'requested_output:'+name, 'available': available,
                'bytes': path.stat().st_size if available else None,
                'writer_closed': available and view['terminal']})
        if not paths:
            result_available = state == 'completed'
        if hmmer_plan is not None:
            manifest = confined(Path(hmmer_plan['attempt_directory'])/'bundle.json', assignment['workspace'])
            result_available = manifest.is_file()
            outputs.append({'role': 'native_hmmer_bundle', 'available': result_available,
                'bytes': manifest.stat().st_size if result_available else None,
                'writer_closed': result_available and view['terminal']})
        return {'observed_at': datetime.now(timezone.utc).isoformat(), 'state': state,
            'returncode': rc, 'failure_code': failure, 'result_available': result_available,
            'measurements': measurements, 'outputs': outputs, 'logs': logs,
            'provenance_refs': [], 'native': {'execution_id': str(handle.path), **view}}

    def read_output(self, assignment, execution_id, *, path, offset, limit,
                    attempt_id=None, **identity):
        """Read the selected bounded output bytes; never start or collect work."""
        confined(execution_id, assignment['workspace'])
        path = confined(path, assignment['workspace'])
        if (type(offset) is not int or offset < 0 or type(limit) is not int
                or not 1 <= limit <= 1024*1024):
            raise ValueError('bounded_native_output_window_required')
        with path.open('rb') as stream:
            size = os.fstat(stream.fileno()).st_size
            stream.seek(offset)
            raw = stream.read(min(limit, max(0, size-offset)))
        return {'path': str(path), 'offset': offset, 'returned_bytes': len(raw),
            'size_bytes': size, 'bytes_base64': base64.b64encode(raw).decode('ascii'),
            'text_utf8': raw.decode('utf-8', errors='replace')}

    async def execute(self, state, tool_name, arguments, operation_key):
        try:
            return await asyncio.to_thread(self._execute, state, tool_name, arguments, operation_key)
        except OSError as error:
            if tool_name not in {'practical.directory.create', 'practical.file.write',
                                 'practical.file.read', 'practical.context.set', 'practical.inventory.refresh'}:
                raise
            return {'facts': {'paths': await asyncio.to_thread(path_facts, state.assignment)},
                'native_outcome': {'failure': {'code': 'practical_filesystem_operation_failed',
                    'exception_type': type(error).__name__, 'errno': error.errno}}}, None

    def _execute(self, state, tool_name, arguments, operation_key):
        self.validate_assignment(state.assignment)
        self.validate_action(state.assignment, tool_name, arguments)
        context = state.context()
        updated = None
        outcome = {'facts': {}, 'native_outcome': None}
        workspace = state.assignment['workspace']
        if tool_name == 'practical.context.set':
            cwd = confined(arguments['cwd'], workspace)
            if not cwd.is_dir():
                outcome['native_outcome'] = {'failure': {'code': 'practical_working_directory_missing',
                                                         'path': str(cwd)}}
            else:
                updated = {'revision': context['revision']+1, 'cwd': str(cwd),
                           'environment': arguments['environment']}
                if updated['cwd'] == context['cwd'] and updated['environment'] == context['environment']:
                    updated['revision'] = context['revision']
        elif tool_name == 'practical.directory.create':
            path = confined(arguments['path'], workspace)
            path.mkdir(parents=True, exist_ok=True)
            outcome['native_outcome'] = {'path': str(path), 'is_directory': path.is_dir()}
        elif tool_name == 'practical.file.write':
            path = confined(arguments['path'], workspace)
            data = arguments['text'].encode('utf-8')
            # Idempotent publication of these exact selected bytes. A separate
            # action may intentionally replace them; replay cannot change them.
            temporary = path.with_name('.'+path.name+'.'+digest(operation_key)+'.writing')
            with temporary.open('wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
            outcome['native_outcome'] = {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}
        elif tool_name == 'practical.file.read':
            path = confined(arguments['path'], self.configuration['workspace'])
            with path.open('rb') as stream:
                stream.seek(arguments['offset'])
                raw = stream.read(arguments['limit'])
            outcome['native_outcome'] = {'path': str(path), 'offset': arguments['offset'],
                'returned_bytes': len(raw), 'size_bytes': path.stat().st_size,
                'bytes_base64': base64.b64encode(raw).decode('ascii'),
                'text_utf8': raw.decode('utf-8', errors='replace')}
        elif tool_name == 'practical.inspect':
            pass
        elif tool_name == 'practical.inventory.refresh':
            from .execution_inventory import validate_catalog
            path = confined(arguments['path'], self.configuration['workspace'])
            raw = path.read_bytes()
            outcome['inventory_bytes_base64'] = base64.b64encode(raw).decode('ascii')
            try:
                outcome['inventory_catalog'] = validate_catalog(json.loads(raw))
            except (ValueError, UnicodeError, TypeError) as error:
                outcome['inventory_failure'] = {'code': 'practical_inventory_catalog_invalid',
                                                'exception_type': type(error).__name__}
        elif tool_name in {'practical.command.run', 'practical.job.start'}:
            requested = tool_name == 'practical.job.start'
            command = state.assignment['requested_job'] if requested else arguments
            # Request identity is immutable. Context only supplies cwd; the
            # requested job's explicit environment is not silently substituted.
            env = command['environment'] if requested else {**context['environment'], **command['environment']}
            cwd = confined(context['cwd'], workspace)
            if requested:
                try:
                    handle = self._job_handle(state)
                except ValueError:
                    if 'retry_failed_execution_id' in arguments:
                        return {'facts': {'paths': path_facts(state.assignment)},
                            'native_outcome': {'failure': {'code': 'requested_job_not_started'}}}, None
                    handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env,
                        native_hmmer='native_hmmer' in command)
                if 'retry_failed_execution_id' in arguments:
                    old = native.status(handle)
                    if (arguments['retry_failed_execution_id'] != str(handle.path)
                            or not old['terminal'] or old['metadata'].get('native_returncode') == 0):
                        return {'facts': {'requested_job': self._job_fact(state, handle, old),
                            'paths': path_facts(state.assignment)}, 'native_outcome': {
                            'failure': {'code': 'practical_retry_requires_original_failed_execution'},
                            'observation': old}}, None
                    handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env,
                        native_hmmer='native_hmmer' in command)
            else:
                handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env)
            if requested:
                view = native.status(handle)
                outcome['facts']['requested_job'] = self._job_fact(state, handle, view)
                outcome['native_outcome'] = view
            else:
                # Waiting for this one selected command is execution, not an
                # autonomous investigation. The native lifecycle is durable.
                try:
                    result = native.wait_job(handle)
                    rc, detail = result.returncode, result.metadata
                except AcquisitionError as error:
                    view = native.status(handle)
                    rc, detail = view['metadata'].get('native_returncode'), {
                        'failure_code': error.code, 'observation': view}
                outcome['facts']['command'] = {'argv': command['argv'], 'environment': env,
                    'returncode': rc, 'execution_id': str(handle.path)}
                body = handle.read()
                outcome['native_outcome'] = {'metadata': detail, 'stdout_path': body['stdout'],
                    'stderr_path': body['stderr'],
                    'stdout': log_tail(body['stdout']), 'stderr': log_tail(body['stderr'])}
        elif tool_name in {'practical.job.status', 'practical.job.collect'}:
            handle = self._job_handle(state)
            view = native.status(handle)
            outcome['facts']['requested_job'] = self._job_fact(state, handle, view)
            body = handle.read()
            logs = {name: log_tail(body[name]) for name in ('stdout', 'stderr')}
            outcome['native_outcome'] = {**view, 'observed_logs': logs}
        else:
            raise ValueError('practical_operation_not_bound')
        outcome['facts']['paths'] = path_facts(state.assignment)
        return outcome, updated


__all__ = ['LocalPracticalOperations', 'path_facts', 'digest', 'confined']
