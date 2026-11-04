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


def _output_details(path, *, text_log, limit=8192):
    """Binary artifacts expose availability and size without a log read."""
    if text_log:
        return log_tail(path, limit)
    path = Path(path)
    available = path.is_file()
    return {'path': str(path), 'available': available,
            **({'bytes': path.stat().st_size} if available else {})}


class LocalPracticalOperations:
    """Local preparation commands and detached requested computation are distinct."""

    def __init__(self, configuration):
        if (not {'kind', 'workspace', 'policy'} <= set(configuration)
                or set(configuration) - {'kind', 'workspace', 'policy', 'native_hmmer', 'native_infernal',
                                        'native_infernal_preparation', 'native_hmmer_preparation', 'native_blast'}
                or configuration['kind'] != 'local'):
            raise ValueError('explicit_local_practical_configuration_required')
        self.configuration = json.loads(json.dumps(configuration, allow_nan=False))
        self.policy = LocalJobPolicy(**configuration['policy'])
        if 'native_blast' in configuration:
            from .native_blast_tool_info import validate_native_blast_bindings
            validate_native_blast_bindings(configuration['native_blast'])
        if 'native_hmmer' in configuration:
            from .native_hmmer_tool_info import validate_native_hmmer_bindings
            validate_native_hmmer_bindings(configuration['native_hmmer'])
        if 'native_hmmer_preparation' in configuration:
            from .native_hmmer_preparation_tool_info import validate_native_hmmer_preparation_bindings
            validate_native_hmmer_preparation_bindings(configuration['native_hmmer_preparation'])
        if 'native_infernal' in configuration:
            from .native_infernal_tool_info import validate_native_infernal_bindings
            validate_native_infernal_bindings(configuration['native_infernal'])
        if 'native_infernal_preparation' in configuration:
            from .native_infernal_preparation_tool_info import validate_native_infernal_preparation_bindings
            validate_native_infernal_preparation_bindings(configuration['native_infernal_preparation'])

    def initial_outcome(self, assignment):
        self.validate_assignment(assignment)
        return {'facts': {'paths': path_facts(assignment)}}

    def validate_assignment(self, assignment):
        if 'native_blast' in assignment['requested_job']:
            from .native_blast_contracts import validate_native_blast_requested_job
            job = validate_native_blast_requested_job(assignment['requested_job'])['native_blast']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_blast', []):
                raise ValueError('native_blast_program_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_blast_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_blast_resource_identity_required')
        if 'native_hmmer_preparation' in assignment['requested_job']:
            from .native_hmmer_preparation_contracts import validate_native_hmmer_preparation_requested_job
            job = validate_native_hmmer_preparation_requested_job(
                assignment['requested_job'])['native_hmmer_preparation']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_hmmer_preparation', []):
                raise ValueError('native_hmmer_preparation_program_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_hmmer_preparation_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_hmmer_preparation_resource_identity_required')
        if 'native_hmmer' in assignment['requested_job']:
            from .native_hmmer_contracts import validate_native_hmmer_requested_job
            job = validate_native_hmmer_requested_job(assignment['requested_job'])['native_hmmer']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_hmmer', []):
                raise ValueError('native_hmmer_program_mode_software_not_bound')
            if not assignment.get('resource_id'):
                raise ValueError('native_hmmer_resource_identity_required')
        if 'native_infernal' in assignment['requested_job']:
            from .native_infernal_contracts import validate_native_infernal_requested_job
            job = validate_native_infernal_requested_job(assignment['requested_job'])['native_infernal']
            selection = {key: job[key] for key in ('program', 'software')}
            if selection not in self.configuration.get('native_infernal', []):
                raise ValueError('native_infernal_program_software_not_bound')
            if not assignment.get('resource_id'):
                raise ValueError('native_infernal_resource_identity_required')
        if 'native_infernal_preparation' in assignment['requested_job']:
            from .native_infernal_preparation_contracts import validate_native_infernal_preparation_requested_job
            job = validate_native_infernal_preparation_requested_job(
                assignment['requested_job'])['native_infernal_preparation']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_infernal_preparation', []):
                raise ValueError('native_infernal_preparation_program_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_infernal_preparation_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_infernal_preparation_resource_identity_required')
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

    def _handle(self, state, operation_key, command, *, cwd, env,
                native_hmmer=False, native_infernal=False, native_infernal_preparation=False,
                native_hmmer_preparation=False, native_blast=False):
        root = self._action_directory(state, operation_key)
        handle = native.NativeJobHandle(root/'native.json')
        if native_blast:
            from .native_blast_local import prepare_local_blast
            handle = prepare_local_blast(state, operation_key, root=root, policy=self.policy)
        elif native_hmmer:
            from .native_hmmer_local import prepare_local_hmmer
            handle = prepare_local_hmmer(state, operation_key, root=root, policy=self.policy)
        elif native_hmmer_preparation:
            from .native_hmmer_preparation_local import prepare_local_hmmer_preparation
            handle = prepare_local_hmmer_preparation(state, operation_key, root=root, policy=self.policy)
        elif native_infernal:
            from .native_infernal_local import prepare_local_infernal
            handle = prepare_local_infernal(state, operation_key, root=root, policy=self.policy)
        elif native_infernal_preparation:
            from .native_infernal_preparation_local import prepare_local_infernal_preparation
            handle = prepare_local_infernal_preparation(state, operation_key, root=root, policy=self.policy)
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
        preparation_plan = None
        blast_plan = None
        if 'native_blast' in request:
            from .native_blast_local import local_blast_plan
            blast_plan = local_blast_plan(state.assignment, str(handle.path))
            if (blast_plan['identity']['run_id'] != state.run_id
                    or blast_plan['identity']['episode_id'] != state.episode_id
                    or blast_plan['policy'] != self.policy.to_dict()):
                raise ValueError('native_blast_original_owner_conflict')
        if 'native_hmmer_preparation' in request:
            from .native_hmmer_preparation_local import local_hmmer_preparation_plan
            preparation_plan = local_hmmer_preparation_plan(state.assignment, str(handle.path))
            if (preparation_plan['identity']['run_id'] != state.run_id
                    or preparation_plan['identity']['episode_id'] != state.episode_id):
                raise ValueError('native_hmmer_preparation_original_owner_conflict')
        if 'native_hmmer' in request:
            from .native_hmmer_local import local_hmmer_plan
            local_hmmer_plan(state.assignment, str(handle.path))
        if 'native_infernal' in request:
            from .native_infernal_local import local_infernal_plan
            local_infernal_plan(state.assignment, str(handle.path))
        if 'native_infernal_preparation' in request:
            from .native_infernal_preparation_local import local_infernal_preparation_plan
            local_infernal_preparation_plan(state.assignment, str(handle.path))
        rc = view['metadata'].get('native_returncode')
        status = ('completed' if rc == 0 else 'failed') if view['terminal'] else (
            'running' if view['state'] == 'running' else 'submitted' if view['state'] == 'starting'
            else 'unknown')
        outputs = [p for r in state.assignment['progress_requirements']
            if r['predicate']['kind'] == 'requested_job_outputs'
            for p in r['predicate']['output_paths']]
        if preparation_plan is not None:
            from .native_hmmer_preparation_driver import BUNDLE_NAME
            attempt = Path(preparation_plan['attempt_directory'])
            outputs = [str(attempt / row['relative_path'])
                for row in request['native_hmmer_preparation']['outputs']]
            outputs.append(str(attempt / BUNDLE_NAME))
        if blast_plan is not None:
            attempt = Path(blast_plan['attempt_directory'])
            outputs = [str(attempt / row['relative_path']) for row in request['native_blast']['outputs']]
            outputs.append(str(attempt / 'bundle.json'))
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
        native_plan, native_family = None, None
        if 'native_blast' in assignment['requested_job']:
            from .native_blast_local import local_blast_plan
            native_plan = local_blast_plan(assignment, execution_id)
            native_family = 'native_blast'
            expected = {'run_id': identity.get('run_id'), 'episode_id': identity.get('origin_episode_id'),
                'operation_key': identity.get('original_operation_key'), 'attempt_id': attempt_id,
                'resource_id': identity.get('resource_id')}
            if (native_plan['policy'] != self.policy.to_dict()
                    or any(value is not None and native_plan['identity'][key] != value for key, value in expected.items())):
                raise ValueError('native_blast_original_owner_conflict')
        elif 'native_hmmer' in assignment['requested_job']:
            from .native_hmmer_local import local_hmmer_plan
            native_plan = local_hmmer_plan(assignment, execution_id)
            native_family = 'native_hmmer'
        elif 'native_hmmer_preparation' in assignment['requested_job']:
            from .native_hmmer_preparation_local import local_hmmer_preparation_plan
            native_plan = local_hmmer_preparation_plan(assignment, execution_id)
            native_family = 'native_hmmer_preparation'
            owner = native_plan['identity']
            expected = {'run_id': identity.get('run_id'),
                'episode_id': identity.get('origin_episode_id'),
                'operation_key': identity.get('original_operation_key'), 'attempt_id': attempt_id}
            if any(value is not None and owner[key] != value for key, value in expected.items()):
                raise ValueError('native_hmmer_preparation_original_owner_conflict')
        elif 'native_infernal' in assignment['requested_job']:
            from .native_infernal_local import local_infernal_plan
            native_plan = local_infernal_plan(assignment, execution_id)
            native_family = 'native_infernal'
        elif 'native_infernal_preparation' in assignment['requested_job']:
            from .native_infernal_preparation_local import local_infernal_preparation_plan
            native_plan = local_infernal_preparation_plan(assignment, execution_id)
            native_family = 'native_infernal_preparation'
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
                selected_role = 'stockholm' if role == 'stdout' and native_job['program'] == 'hmmalign' else role
                selected_output = next(item for item in native_job['outputs'] if item['role'] == selected_role)
                path = confined(Path(native_plan['attempt_directory'])/selected_output['relative_path'], assignment['workspace'])
                if native_family == 'native_blast':
                    from .native_blast_driver import _confined_file
                    path = _confined_file(Path(native_plan['attempt_directory']), selected_output['relative_path'])
                text_log = selected_output['format'] != 'hmmer_binary'
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
        if native_family in {'native_hmmer_preparation', 'native_blast'}:
            paths = sorted({str(Path(native_plan['attempt_directory']) / row['relative_path'])
                for row in assignment['requested_job'][native_family]['outputs']
                if row['role'] not in {'stdout', 'stderr'}})
        for name in paths:
            path = confined(name, assignment['workspace'])
            if native_family == 'native_blast':
                from .native_blast_driver import _confined_file
                path = _confined_file(Path(native_plan['attempt_directory']),
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
            if native_family == 'native_blast':
                from .native_blast_driver import _confined_file
                manifest = _confined_file(Path(native_plan['attempt_directory']), 'bundle.json')
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
        """Read the selected bounded output bytes; never start or collect work."""
        if 'native_blast' in assignment['requested_job']:
            from .native_blast_local import local_blast_plan
            from .native_blast_driver import _confined_file
            self.validate_assignment(assignment)
            plan = local_blast_plan(assignment, execution_id)
            expected = {'run_id': identity.get('run_id'), 'episode_id': identity.get('origin_episode_id'),
                'operation_key': identity.get('original_operation_key'), 'attempt_id': attempt_id}
            if (plan['policy'] != self.policy.to_dict()
                    or any(value is not None and plan['identity'][key] != value for key, value in expected.items())):
                raise ValueError('native_blast_original_owner_conflict')
            paths = {str(Path(plan['attempt_directory']) / row['relative_path'])
                for row in assignment['requested_job']['native_blast']['outputs']}
            paths.add(str(Path(plan['attempt_directory']) / 'bundle.json'))
            if str(path) not in paths:
                raise ValueError('native_blast_original_output_path_required')
            _confined_file(Path(plan['attempt_directory']),
                str(Path(path).relative_to(plan['attempt_directory'])))
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
                        native_hmmer='native_hmmer' in command, native_infernal='native_infernal' in command,
                        native_infernal_preparation='native_infernal_preparation' in command,
                        native_hmmer_preparation='native_hmmer_preparation' in command,
                        native_blast='native_blast' in command)
                if 'retry_failed_execution_id' in arguments:
                    old = native.status(handle)
                    if 'native_blast' in command:
                        self._job_fact(state, handle, old)
                    if (arguments['retry_failed_execution_id'] != str(handle.path)
                            or not old['terminal'] or old['metadata'].get('native_returncode') == 0
                            or 'native_blast' in command and old['metadata'].get('native_returncode') is None):
                        return {'facts': {'requested_job': self._job_fact(state, handle, old),
                            'paths': path_facts(state.assignment)}, 'native_outcome': {
                            'failure': {'code': 'practical_retry_requires_original_failed_execution'},
                            'observation': old}}, None
                    handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env,
                        native_hmmer='native_hmmer' in command, native_infernal='native_infernal' in command,
                        native_infernal_preparation='native_infernal_preparation' in command,
                        native_hmmer_preparation='native_hmmer_preparation' in command,
                        native_blast='native_blast' in command)
            else:
                handle = self._handle(state, operation_key, command['argv'], cwd=cwd, env=env)
            if requested:
                view = native.status(handle)
                outcome['facts']['requested_job'] = self._job_fact(state, handle, view)
                outcome['native_outcome'] = view
                if 'native_blast' in command:
                    from .native_blast_local import local_blast_plan
                    owner = local_blast_plan(state.assignment, str(handle.path))['identity']
                    outcome['native_outcome'] = {**view, 'attempt_id': owner['attempt_id'],
                        'attempt_operation_key': owner['operation_key']}
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
            if 'native_blast' in state.assignment['requested_job']:
                from .native_blast_local import local_blast_plan
                plan = local_blast_plan(state.assignment, str(handle.path))
                logs, outputs = {}, []
                selected_outputs = [*state.assignment['requested_job']['native_blast']['outputs'],
                    {'role': 'native_blast_bundle', 'format': 'json', 'relative_path': 'bundle.json'}]
                for selected in selected_outputs:
                    from .native_blast_driver import _confined_file
                    path = _confined_file(Path(plan['attempt_directory']), selected['relative_path'])
                    text_log = selected['role'] in {'stdout', 'stderr'}
                    detail = _output_details(path, text_log=text_log)
                    outputs.append({'role': selected['role'], 'available': detail['available'],
                        'bytes': detail.get('bytes'), 'writer_closed': detail['available'] and view['terminal']})
                    if text_log:
                        logs[selected['role']] = detail
                outcome['native_outcome'] = {**view, 'observed_logs': logs, 'observed_outputs': outputs,
                    'attempt_id': plan['identity']['attempt_id'],
                    'attempt_operation_key': plan['identity']['operation_key']}
            elif 'native_hmmer_preparation' in state.assignment['requested_job']:
                from .native_hmmer_preparation_local import local_hmmer_preparation_plan
                plan = local_hmmer_preparation_plan(state.assignment, str(handle.path))
                logs, outputs = {}, []
                for selected in state.assignment['requested_job']['native_hmmer_preparation']['outputs']:
                    path = confined(Path(plan['attempt_directory']) / selected['relative_path'], workspace)
                    text_log = selected['role'] in {'stdout', 'stderr'} and selected['format'] != 'hmmer_binary'
                    detail = _output_details(path, text_log=text_log)
                    outputs.append({'role': selected['role'], 'available': detail['available'],
                        'bytes': detail.get('bytes'), 'writer_closed': detail['available'] and view['terminal']})
                    if text_log:
                        logs[selected['role']] = detail
                outcome['native_outcome'] = {**view, 'observed_logs': logs, 'observed_outputs': outputs}
            else:
                logs = {name: log_tail(body[name]) for name in ('stdout', 'stderr')}
                outcome['native_outcome'] = {**view, 'observed_logs': logs}
        else:
            raise ValueError('practical_operation_not_bound')
        outcome['facts']['paths'] = path_facts(state.assignment)
        return outcome, updated


__all__ = ['LocalPracticalOperations', 'path_facts', 'digest', 'confined']
