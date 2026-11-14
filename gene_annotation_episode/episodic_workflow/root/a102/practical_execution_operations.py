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


def path_facts(assignment, *, additional_paths=()):
    paths, hash_paths = set(additional_paths), set()
    for requirement in assignment['progress_requirements']:
        predicate = requirement['predicate']
        if predicate['kind'] in {'path_exists', 'file_sha256'}:
            paths.add(predicate['path'])
            if predicate['kind'] == 'file_sha256':
                hash_paths.add(predicate['path'])
        elif predicate['kind'] == 'requested_job_outputs':
            paths.update(predicate.get('output_paths', ()))
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


def _output_details(path, *, text_log, limit=8192):
    """Binary artifacts expose availability and size without a log read."""
    if text_log:
        return log_tail(path, limit)
    path = Path(path)
    available = path.is_file()
    return {'path': str(path), 'available': available,
            **({'bytes': path.stat().st_size} if available else {})}


class LocalPracticalOperations:
    """A102 local structure execution and explicit preparation commands."""

    def __init__(self, configuration):
        if (not {'kind', 'workspace', 'policy'} <= set(configuration)
                or set(configuration) - {'kind', 'workspace', 'policy', 'native_protein_structure'}
                or configuration['kind'] != 'local'):
            raise ValueError('explicit_local_practical_configuration_required')
        self.configuration = json.loads(json.dumps(configuration, allow_nan=False))
        self.policy = LocalJobPolicy(**configuration['policy'])
        if 'native_protein_structure' in configuration:
            from .native_protein_structure_contracts import validate_protein_structure_bindings
            validate_protein_structure_bindings(configuration['native_protein_structure'])

    def initial_outcome(self, assignment):
        self.validate_assignment(assignment)
        return {'facts': {'paths': path_facts(assignment)}}

    def validate_assignment(self, assignment):
        if 'native_protein_structure' in assignment['requested_job']:
            from .native_protein_structure_contracts import POLICY, validate_protein_structure_requested_job
            job = validate_protein_structure_requested_job(assignment['requested_job'])['native_protein_structure']
            request = job['request']
            selection = {'operation': request['operation'],
                'scientific_mode': request['parameters']['mode'] if request['operation'] == 'compare' else None,
                'software': job['software']}
            if selection not in self.configuration.get('native_protein_structure', []):
                raise ValueError('native_protein_structure_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_protein_structure_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_protein_structure_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_protein_structure_local_policy_conflict')
        constraints = assignment['constraints']
        allowed = {'allocation', 'memory_bytes', 'scratch_bytes'}
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

    def _handle(self, state, operation_key, command, *, cwd, env, native_protein_structure=False):
        root = self._action_directory(state, operation_key)
        handle = native.NativeJobHandle(root/'native.json')
        if native_protein_structure:
            from .native_protein_structure_local import prepare_local_protein_structure
            handle = prepare_local_protein_structure(state, operation_key, root=root, policy=self.policy)
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

    def _protein_plan(self, assignment, execution_id, *, run_id=None, origin_episode_id=None,
                      original_operation_key=None, attempt_id=None, resource_id=None):
        """Authenticate the original protein reservation without executing it."""
        from .native_protein_structure_local import local_protein_structure_plan
        self.validate_assignment(assignment)
        plan = local_protein_structure_plan(assignment, execution_id)
        expected = {'run_id': run_id, 'episode_id': origin_episode_id,
            'operation_key': original_operation_key, 'attempt_id': attempt_id, 'resource_id': resource_id}
        if (plan['policy'] != self.policy.to_dict() or any(value is not None and
                plan['identity'][key] != value for key, value in expected.items())):
            raise ValueError('original_commission_mismatch')
        return plan

    def _job_fact(self, state, handle, view):
        request = state.assignment['requested_job']
        protein_plan = (self._protein_plan(state.assignment, str(handle.path), run_id=state.run_id,
            origin_episode_id=state.episode_id) if 'native_protein_structure' in request else None)
        rc = view['metadata'].get('native_returncode')
        status = ('completed' if rc == 0 else 'failed') if view['terminal'] else (
            'running' if view['state'] == 'running' else 'submitted' if view['state'] == 'starting'
            else 'unknown')
        outputs = [p for r in state.assignment['progress_requirements']
            if r['predicate']['kind'] == 'requested_job_outputs'
            for p in r['predicate'].get('output_paths', ())]
        if protein_plan is not None:
            from .native_protein_structure_contracts import BUNDLE_FILENAME
            attempt = Path(protein_plan['attempt_directory'])
            outputs = [str(attempt / row['relative_path']) for row in request['native_protein_structure']['outputs']]
            outputs.append(str(attempt / BUNDLE_FILENAME))
        return {'requested_job_sha256': digest(request), 'argv': request['argv'],
            'environment': request['environment'], 'resource_kind': 'local',
            'execution_id': str(handle.path), 'status': status, 'returncode': rc,
            'output_paths': sorted(set(outputs)), 'handoff': {
                'execution_id': str(handle.path), 'monitor_operation': 'practical.job.status',
                'results_operation': 'practical.job.collect'}}

    def observe_execution(self, assignment, execution_id, *, log_window_bytes=8192,
                          log_roles=('stdout', 'stderr'), attempt_id=None, **identity):
        self.validate_assignment(assignment)
        if type(log_window_bytes) is not int or log_window_bytes <= 0:
            raise ValueError('positive_log_window_required')
        if any(role not in {'stdout', 'stderr'} for role in log_roles):
            raise ValueError('unsupported_native_log_role')
        handle = native.NativeJobHandle(confined(execution_id, assignment['workspace']))
        # The source pins this handle; never replace it with a later receipt.
        body = handle.read()
        request = json.loads((handle.path.parent/'invoke.json').read_text())
        native_plan, native_family = None, None
        if 'native_protein_structure' in assignment['requested_job']:
            native_plan = self._protein_plan(assignment, execution_id, attempt_id=attempt_id,
                **{key: identity.get(key) for key in ('run_id', 'origin_episode_id', 'original_operation_key', 'resource_id')})
            native_family = 'native_protein_structure'
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
            text_log = True
            if native_plan is not None:
                native_job = assignment['requested_job'][native_family]
                selected_role = role
                selected_output = next(item for item in native_job['outputs'] if item['role'] == selected_role)
                path = confined(Path(native_plan['attempt_directory'])/selected_output['relative_path'], assignment['workspace'])
                if native_family == 'native_protein_structure':
                    from .native_protein_structure_driver import confined_file
                    path = confined_file(Path(native_plan['attempt_directory']), selected_output['relative_path'])
            else:
                path = confined(body[role], assignment['workspace'])
            tail = _output_details(path, text_log=text_log and role in log_roles, limit=log_window_bytes)
            outputs.append({'role': role, 'available': tail['available'],
                'bytes': tail.get('bytes'), 'writer_closed': tail['available'] and view['terminal']})
            if text_log and role in log_roles and tail['available']:
                logs.append({'role': role, 'path': str(path), 'offset': tail['tail_byte_offset'],
                    'observed_size': tail['bytes'], 'bytes_base64': tail['bytes_base64']})
        result_available = False
        paths = sorted(set(path for row in assignment['progress_requirements']
            if row['predicate']['kind'] == 'requested_job_outputs'
            for path in row['predicate']['output_paths']))
        if native_family == 'native_protein_structure':
            paths = sorted({str(Path(native_plan['attempt_directory']) / row['relative_path'])
                for row in assignment['requested_job'][native_family]['outputs']
                if row['role'] not in {'stdout', 'stderr'}})
        for name in paths:
            path = confined(name, assignment['workspace'])
            if native_family == 'native_protein_structure':
                from .native_protein_structure_driver import confined_file
                path = confined_file(Path(native_plan['attempt_directory']),
                    str(Path(name).relative_to(native_plan['attempt_directory'])))
            available = path.is_file()
            result_available |= available
            outputs.append({'role': 'requested_output:'+name, 'available': available,
                'bytes': path.stat().st_size if available else None,
                'writer_closed': available and view['terminal']})
        if not paths:
            result_available = state == 'completed'
        if native_plan is not None:
            manifest = confined(Path(native_plan['attempt_directory'])/'bundle.json', assignment['workspace'])
            if native_family == 'native_protein_structure':
                from .native_protein_structure_contracts import BUNDLE_FILENAME
                from .native_protein_structure_driver import confined_file
                manifest = confined_file(Path(native_plan['attempt_directory']), BUNDLE_FILENAME)
            result_available = manifest.is_file()
            outputs.append({'role': native_family+'_bundle', 'available': result_available,
                'bytes': manifest.stat().st_size if result_available else None,
                'writer_closed': result_available and view['terminal']})
        return {'observed_at': datetime.now(timezone.utc).isoformat(), 'state': state,
            'returncode': rc, 'failure_code': failure, 'result_available': result_available,
            'measurements': measurements, 'outputs': outputs, 'logs': logs,
            'provenance_refs': [], 'native': {'execution_id': str(handle.path), **view}}

    def read_output(self, assignment, execution_id, *, path, offset, limit,
                    attempt_id=None, **identity):
        self.validate_assignment(assignment)
        if 'native_protein_structure' in assignment['requested_job']:
            from .native_protein_structure_contracts import BUNDLE_FILENAME
            from .native_protein_structure_driver import confined_file
            plan = self._protein_plan(assignment, execution_id, attempt_id=attempt_id,
                **{key: identity.get(key) for key in ('run_id', 'origin_episode_id', 'original_operation_key', 'resource_id')})
            paths = {str(Path(plan['attempt_directory']) / row['relative_path'])
                for row in assignment['requested_job']['native_protein_structure']['outputs']}
            paths.add(str(Path(plan['attempt_directory']) / BUNDLE_FILENAME))
            if str(path) not in paths:
                raise ValueError('native_protein_structure_original_output_path_required')
            confined_file(Path(plan['attempt_directory']), str(Path(path).relative_to(plan['attempt_directory'])))
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
                        native_protein_structure='native_protein_structure' in command)
                if 'retry_failed_execution_id' in arguments:
                    original = (self._protein_plan(state.assignment, str(handle.path), run_id=state.run_id,
                        origin_episode_id=state.episode_id)['identity'] if 'native_protein_structure' in command else None)
                    old = native.status(handle)
                    if (arguments['retry_failed_execution_id'] != str(handle.path)
                            or not old['terminal'] or old['metadata'].get('native_returncode') == 0
                            or original is not None and (old['state'] != 'returned'
                                or type(old['metadata'].get('native_returncode')) is not int
                                or (old['metadata'].get('service_exit') or {}).get('EXIT_CODE') == 'killed')):
                        return {'facts': {'requested_job': self._job_fact(state, handle, old),
                            'paths': path_facts(state.assignment)}, 'native_outcome': {
                            'failure': {'code': 'practical_retry_requires_original_failed_execution'},
                            'observation': old, **({} if original is None else {
                                'attempt_id': original['attempt_id'],
                                'attempt_operation_key': original['operation_key']})}}, None
                    handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env,
                        native_protein_structure='native_protein_structure' in command)
            else:
                handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env)
            if requested:
                if 'native_protein_structure' in command:
                    self._protein_plan(state.assignment, str(handle.path), run_id=state.run_id,
                        origin_episode_id=state.episode_id)
                view = native.status(handle)
                outcome['facts']['requested_job'] = self._job_fact(state, handle, view)
                outcome['native_outcome'] = view
                if 'native_protein_structure' in command:
                    original = self._protein_plan(state.assignment, str(handle.path), run_id=state.run_id,
                        origin_episode_id=state.episode_id)['identity']
                    outcome['native_outcome'] = {**view, 'attempt_id': original['attempt_id'],
                        'attempt_operation_key': original['operation_key']}
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
            if 'native_protein_structure' in state.assignment['requested_job']:
                self._protein_plan(state.assignment, str(handle.path), run_id=state.run_id,
                    origin_episode_id=state.episode_id)
            view = native.status(handle)
            outcome['facts']['requested_job'] = self._job_fact(state, handle, view)
            outcome['native_outcome'] = view
            if 'native_protein_structure' in state.assignment['requested_job']:
                from .native_protein_structure_contracts import BUNDLE_FILENAME
                from .native_protein_structure_driver import confined_file
                plan = self._protein_plan(state.assignment, str(handle.path), run_id=state.run_id,
                    origin_episode_id=state.episode_id)
                logs, outputs = {}, []
                for selected in [*state.assignment['requested_job']['native_protein_structure']['outputs'],
                        {'role': 'native_protein_structure_bundle', 'format': 'json', 'relative_path': BUNDLE_FILENAME}]:
                    path = confined_file(Path(plan['attempt_directory']), selected['relative_path'])
                    text_log = selected['role'] in {'stdout', 'stderr'}
                    detail = _output_details(path, text_log=text_log)
                    outputs.append({'role': selected['role'], 'available': detail['available'],
                        'bytes': detail.get('bytes'), 'writer_closed': detail['available'] and view['terminal']})
                    if text_log:
                        logs[selected['role']] = detail
                outcome['native_outcome'] = {**view, 'observed_logs': logs, 'observed_outputs': outputs,
                    'attempt_id': plan['identity']['attempt_id'],
                    'attempt_operation_key': plan['identity']['operation_key']}
            else:
                body = handle.read()
                logs = {role: log_tail(body[role]) for role in ('stdout', 'stderr')}
                outcome['native_outcome'] = {**view, 'observed_logs': logs}
        outcome['facts']['paths'] = path_facts(state.assignment)
        return outcome, updated


__all__ = ['LocalPracticalOperations', 'path_facts', 'digest', 'confined']
