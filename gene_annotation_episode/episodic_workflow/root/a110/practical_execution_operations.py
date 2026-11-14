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


class _FluxBalanceInputFailure(ValueError):
    pass


class LocalPracticalOperations:
    """Local preparation commands and detached requested computation are distinct."""

    def __init__(self, configuration, *, flux_balance_input_reader=None):
        if (not {'kind', 'workspace', 'policy'} <= set(configuration)
                or set(configuration) - {'kind', 'workspace', 'policy', 'native_flux_balance'}
                or configuration['kind'] != 'local'):
            raise ValueError('explicit_local_practical_configuration_required')
        if flux_balance_input_reader is not None and not callable(flux_balance_input_reader):
            raise ValueError('native_flux_balance_input_reader_invalid')
        self.flux_balance_input_reader = flux_balance_input_reader
        self.configuration = json.loads(json.dumps(configuration, allow_nan=False))
        self.policy = LocalJobPolicy(**configuration['policy'])
        if 'native_flux_balance' in configuration:
            from .native_flux_balance_bindings import validate_flux_balance_bindings
            validate_flux_balance_bindings(configuration['native_flux_balance'])
    def initial_outcome(self, assignment, *, flux_balance_output_paths=()):
        self.validate_assignment(assignment)
        if flux_balance_output_paths and 'native_flux_balance' not in assignment['requested_job']:
            raise ValueError('practical_flux_balance_output_roles_require_fba')
        return {'facts': {'paths': path_facts(assignment, additional_paths=[
            *flux_balance_output_paths])}}

    def validate_assignment(self, assignment):
        if 'native_flux_balance' in assignment['requested_job']:
            from .native_flux_balance_contracts import POLICY, validate_flux_balance_requested_job
            from .native_flux_balance_bindings import flux_balance_binding_accepts_job
            job = validate_flux_balance_requested_job(assignment['requested_job'])['native_flux_balance']
            if not any(flux_balance_binding_accepts_job(row, job)
                    for row in self.configuration.get('native_flux_balance', [])):
                raise ValueError('native_flux_balance_operation_mode_software_format_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_flux_balance_local_resource_required')
            if not isinstance(assignment.get('resource_id'), str) or not assignment['resource_id']:
                raise ValueError('native_flux_balance_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_flux_balance_local_policy_conflict')
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

    def _read_flux_balance_input_control(self, state):
        if self.flux_balance_input_reader is None:
            raise _FluxBalanceInputFailure('native_flux_balance_input_reader_required')
        try:
            control = self.flux_balance_input_reader(state)
        except (ValueError, TypeError, OSError) as error:
            raise _FluxBalanceInputFailure('native_flux_balance_input_control_unavailable') from error
        if type(control) is not dict or set(control) != {'receipt', 'file'}:
            raise _FluxBalanceInputFailure('native_flux_balance_input_control_invalid')
        try:
            return json.loads(json.dumps(control, allow_nan=False))
        except (ValueError, TypeError, OverflowError) as error:
            raise _FluxBalanceInputFailure('native_flux_balance_input_control_invalid') from error

    def _handle(self, state, operation_key, command, *, cwd, env,
                native_flux_balance=False, flux_balance_input_control=None):
        root = self._action_directory(state, operation_key)
        handle = native.NativeJobHandle(root/'native.json')
        if native_flux_balance:
            from .native_flux_balance_local import prepare_local_flux_balance
            control = (self._read_flux_balance_input_control(state)
                if flux_balance_input_control is None else flux_balance_input_control)
            if type(control) is not dict or set(control) != {'receipt', 'file'}:
                raise _FluxBalanceInputFailure('native_flux_balance_input_control_invalid')
            try:
                handle = prepare_local_flux_balance(state, operation_key, root=root, policy=self.policy,
                    input_binding_receipt=control['receipt'], input_binding_file=control['file'])
            except ValueError as error:
                if str(error).startswith('fba_input_control_'):
                    raise _FluxBalanceInputFailure('native_flux_balance_input_control_invalid') from error
                raise
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

    def _flux_balance_plan(self, assignment, execution_id, *, run_id=None,
                           origin_episode_id=None, original_operation_key=None, attempt_id=None,
                           resource_id=None, requested_job_sha256=None):
        from .native_flux_balance_local import local_flux_balance_plan
        self.validate_assignment(assignment)
        plan = local_flux_balance_plan(assignment, execution_id)
        expected = {'run_id': run_id, 'episode_id': origin_episode_id,
            'operation_key': original_operation_key, 'attempt_id': attempt_id,
            'resource_id': resource_id, 'requested_job_sha256': requested_job_sha256}
        if (plan['policy'] != self.policy.to_dict() or any(value is not None and
                plan['identity'][key] != value for key, value in expected.items())):
            raise ValueError('native_flux_balance_original_attempt_mismatch')
        return plan

    @staticmethod
    def _flux_balance_identity(plan):
        from .native_flux_balance_storage import confined_file, read_json
        invocation = read_json(confined_file(Path(plan['identity']['execution_id']).parent, 'invoke.json'))
        return {'attempt_id': plan['identity']['attempt_id'],
            'attempt_operation_key': plan['identity']['operation_key'],
            'native_flux_balance_input_binding_file': invocation['native_flux_balance_input_binding_file']}

    def _flux_balance_state_plan(self, state, execution_id):
        plan = self._flux_balance_plan(state.assignment, execution_id,
            run_id=state.run_id, origin_episode_id=state.episode_id)
        identity = self._flux_balance_identity(plan)
        for receipt in state.receipts():
            outcome = receipt.get('outcome', {})
            if outcome.get('facts', {}).get('requested_job', {}).get('execution_id') == execution_id:
                prior = outcome.get('native_outcome') or {}
                if any(prior.get(key) != value for key, value in identity.items()):
                    raise ValueError('native_flux_balance_original_input_control_conflict')
        return plan

    def _flux_balance_observation_plan(self, assignment, execution_id, attempt_id, identity):
        plan = self._flux_balance_plan(assignment, execution_id, attempt_id=attempt_id,
            **{key: identity.get(key) for key in ('run_id', 'origin_episode_id',
                'original_operation_key', 'resource_id', 'requested_job_sha256')})
        expected = identity.get('native_flux_balance_input_binding_file')
        if expected is not None and self._flux_balance_identity(plan)['native_flux_balance_input_binding_file'] != expected:
            raise ValueError('native_flux_balance_original_input_control_conflict')
        return plan

    def _job_fact(self, state, handle, view):
        request = state.assignment['requested_job']
        flux_balance_plan = None
        if 'native_flux_balance' in request:
            flux_balance_plan = self._flux_balance_state_plan(state, str(handle.path))
        rc = view['metadata'].get('native_returncode')
        status = ('completed' if rc == 0 else 'failed') if view['terminal'] else (
            'running' if view['state'] == 'running' else 'submitted' if view['state'] == 'starting'
            else 'unknown')
        outputs = [p for r in state.assignment['progress_requirements']
            if r['predicate']['kind'] == 'requested_job_outputs'
            for p in r['predicate'].get('output_paths', ())]
        if flux_balance_plan is not None:
            attempt = Path(flux_balance_plan['attempt_directory'])
            outputs = [str(attempt / row['relative_path']) for row in flux_balance_plan['outputs']]
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
        allowed_logs = {'stdout', 'stderr', 'native_log'} if 'native_flux_balance' in assignment['requested_job'] else {'stdout', 'stderr'}
        if any(role not in allowed_logs for role in log_roles):
            raise ValueError('unsupported_native_log_role')
        if 'native_flux_balance' in assignment['requested_job']:
            from .native_flux_balance_observations import flux_balance_observed_files
            plan = self._flux_balance_observation_plan(assignment, execution_id, attempt_id, identity)
            view = native.status(native.NativeJobHandle(Path(execution_id)))
            metadata, measurements = view['metadata'], []
            rc = metadata.get('native_returncode')
            state = (('completed' if rc == 0 else 'failed') if view['terminal'] else
                'running' if view['state'] == 'running' else
                'submitted' if view['state'] in {'prepared', 'starting'} else 'unknown')
            failure = None if state != 'failed' else (
                'native_returncode_unavailable' if rc is None else 'native_nonzero_returncode')
            if view['terminal'] and metadata.get('elapsed_seconds') is not None:
                measurements.append({'measure': metadata['duration_measure'], 'seconds': metadata['elapsed_seconds']})
            outputs, logs, available = flux_balance_observed_files(plan, view,
                log_window_bytes=log_window_bytes, log_roles=log_roles)
            return {'observed_at': datetime.now(timezone.utc).isoformat(), 'state': state,
                'returncode': rc, 'failure_code': failure, 'result_available': available,
                'measurements': measurements, 'outputs': outputs, 'logs': logs,
                'provenance_refs': [], 'native': {'execution_id': execution_id, **view,
                    **self._flux_balance_identity(plan)}}
        handle = native.NativeJobHandle(confined(execution_id, assignment['workspace']))
        # The source pins this handle; never replace it with a later receipt.
        body = handle.read()
        request = json.loads((handle.path.parent/'invoke.json').read_text())
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
        for name in paths:
            path = confined(name, assignment['workspace'])
            available = path.is_file()
            result_available |= available
            outputs.append({'role': 'requested_output:'+name, 'available': available,
                'bytes': path.stat().st_size if available else None,
                'writer_closed': available and view['terminal']})
        if not paths:
            result_available = state == 'completed'
        return {'observed_at': datetime.now(timezone.utc).isoformat(), 'state': state,
            'returncode': rc, 'failure_code': failure, 'result_available': result_available,
            'measurements': measurements, 'outputs': outputs, 'logs': logs,
            'provenance_refs': [], 'native': {'execution_id': str(handle.path), **view}}

    def read_output(self, assignment, execution_id, *, path, offset, limit,
                    attempt_id=None, **identity):
        """Read the selected bounded output bytes; never start or collect work."""
        if 'native_flux_balance' in assignment['requested_job']:
            from .native_flux_balance_observations import read_flux_balance_output
            plan = self._flux_balance_observation_plan(assignment, execution_id, attempt_id, identity)
            return read_flux_balance_output(plan, path=str(path), offset=offset, limit=limit)
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
            options = {}
            if tool_name == 'practical.job.start' and 'native_flux_balance' in state.assignment['requested_job']:
                self.validate_assignment(state.assignment)
                self.validate_action(state.assignment, tool_name, arguments)
                try:
                    original = self._job_handle(state)
                except ValueError:
                    preparing = 'retry_failed_execution_id' not in arguments
                else:
                    preparing = ('retry_failed_execution_id' in arguments
                        and arguments['retry_failed_execution_id'] == str(original.path))
                if preparing:
                    # The authenticated Store reader stays on its owning event
                    # loop thread. Only detached original control data crosses.
                    options['flux_balance_input_control'] = self._read_flux_balance_input_control(state)
            return await asyncio.to_thread(self._execute, state, tool_name, arguments, operation_key, **options)
        except _FluxBalanceInputFailure as error:
            return {'facts': {}, 'native_outcome': {'failure': {'code': str(error)}}}, None
        except OSError as error:
            if tool_name not in {'practical.directory.create', 'practical.file.write',
                                 'practical.file.read', 'practical.context.set', 'practical.inventory.refresh'}:
                raise
            return {'facts': {'paths': await asyncio.to_thread(path_facts, state.assignment)},
                'native_outcome': {'failure': {'code': 'practical_filesystem_operation_failed',
                    'exception_type': type(error).__name__, 'errno': error.errno}}}, None

    def _execute(self, state, tool_name, arguments, operation_key, *, flux_balance_input_control=None):
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
                        native_flux_balance='native_flux_balance' in command,
                        **({} if flux_balance_input_control is None else {
                            'flux_balance_input_control': flux_balance_input_control}))
                if 'retry_failed_execution_id' in arguments:
                    attempt_identity = None
                    flux_balance_retry_plan = None
                    if 'native_flux_balance' in command:
                        flux_balance_retry_plan = self._flux_balance_state_plan(state, str(handle.path))
                        attempt_identity = flux_balance_retry_plan['identity']
                    old = native.status(handle)
                    if (arguments['retry_failed_execution_id'] != str(handle.path)
                            or not old['terminal'] or old['metadata'].get('native_returncode') == 0
                            or 'native_flux_balance' in command and (
                                old['state'] != 'returned' or type(old['metadata'].get('native_returncode')) is not int
                                or (old['metadata'].get('service_exit') or {}).get('EXIT_CODE') == 'killed')
                            or 'native_flux_balance' in command and old.get('quiescent') is not True):
                        return {'facts': {'requested_job': self._job_fact(state, handle, old),
                            'paths': path_facts(state.assignment)}, 'native_outcome': {
                            'failure': {'code': 'practical_retry_requires_original_failed_execution'},
                            'observation': old,
                            **({} if flux_balance_retry_plan is None else self._flux_balance_identity(flux_balance_retry_plan)),
                            **({} if attempt_identity is None else {
                                'attempt_id': attempt_identity['attempt_id'],
                                'attempt_operation_key': attempt_identity['operation_key']})}}, None
                    handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env,
                        native_flux_balance='native_flux_balance' in command,
                        **({} if flux_balance_input_control is None else {
                            'flux_balance_input_control': flux_balance_input_control}))
            else:
                handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env)
            if requested:
                if 'native_flux_balance' in command:
                    self._flux_balance_state_plan(state, str(handle.path))
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
            if 'native_flux_balance' in state.assignment['requested_job']:
                self._flux_balance_state_plan(state, str(handle.path))
            view = native.status(handle)
            outcome['facts']['requested_job'] = self._job_fact(state, handle, view)
            body = handle.read()
            if 'native_flux_balance' in state.assignment['requested_job']:
                outcome['native_outcome'] = view
            else:
                logs = {name: log_tail(body[name]) for name in ('stdout', 'stderr')}
                outcome['native_outcome'] = {**view, 'observed_logs': logs}
        else:
            raise ValueError('practical_operation_not_bound')
        if ('native_flux_balance' in state.assignment['requested_job']
                and 'requested_job' in outcome['facts']):
            from .native_flux_balance_observations import flux_balance_observed_files
            plan = self._flux_balance_state_plan(state,
                outcome['facts']['requested_job']['execution_id'])
            outputs, logs, _ = flux_balance_observed_files(plan, outcome['native_outcome'],
                log_window_bytes=8192, log_roles=('stdout', 'stderr'))
            outcome['native_outcome'] = {**outcome['native_outcome'],
                **self._flux_balance_identity(plan), 'observed_outputs': outputs, 'observed_logs': logs}
        role_paths = []
        if ('native_flux_balance' in state.assignment['requested_job']
                and 'requested_job' in outcome['facts']):
            from .practical_execution_records import flux_balance_role_paths
            for requirement in state.assignment['progress_requirements']:
                predicate = requirement['predicate']
                if predicate['kind'] == 'requested_job_outputs' and 'output_roles' in predicate:
                    role_paths.extend(flux_balance_role_paths(state.assignment,
                        outcome['facts']['requested_job'], predicate['output_roles']))
        outcome['facts']['paths'] = path_facts(state.assignment, additional_paths=role_paths)
        return outcome, updated


__all__ = ['LocalPracticalOperations', 'path_facts', 'digest', 'confined']
