"""Scientific custody for native programs launched through ordinary commands.

This module does not choose a command, run a program, prepare an environment,
submit a job or calculate credit. Scientific contracts still validate their own
manifests and outputs. The general executor records actual bytes and actions.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath

from .execution_contracts import canonical, digest


_PROFILES = {
    'native_expression_nmf': ('native_expression_nmf_contracts',
        'validate_expression_nmf_run_plan', 'RUN_PLAN_FILENAME'),
    'native_fluorescence': ('native_fluorescence_contracts',
        'validate_fluorescence_run_plan', 'RUN_PLAN_FILENAME'),
    'native_genomic_overlap': ('native_genomic_overlap_contracts',
        'validate_genomic_overlap_run_plan', 'RUN_PLAN_FILENAME'),
    'native_chromatin_interactions': ('native_chromatin_interaction_contracts',
        'validate_chromatin_run_plan', 'RUN_PLAN_FILENAME'),
    'native_atac_differential': ('native_atac_differential_contracts',
        'validate_atac_run_plan', 'RUN_PLAN_FILENAME'),
    'native_protein_structure': ('native_protein_structure_contracts',
        'validate_protein_structure_run_plan', 'RUN_PLAN_FILENAME'),
    'native_flux_balance': ('native_flux_balance_contracts',
        'validate_flux_balance_run_plan', 'RUN_PLAN_FILENAME'),
}
_DRIVER_ARGUMENTS = {
    'native_expression_nmf': 'expression_nmf_driver_argv',
    'native_fluorescence': 'fluorescence_driver_argv',
    'native_genomic_overlap': 'genomic_overlap_driver_argv',
    'native_chromatin_interactions': 'chromatin_driver_argv',
    'native_atac_differential': 'atac_driver_argv',
    'native_protein_structure': 'driver_argv',
    'native_flux_balance': 'flux_balance_driver_argv',
}


def _require(value, code='terminal_scientific_custody_mismatch'):
    if not value:
        raise ValueError(code)


def _profile(requested):
    selected = [name for name in _PROFILES if name in requested]
    if len(selected) != 1:
        return None
    key = selected[0]
    module_name, validator_name, filename_name = _PROFILES[key]
    module = importlib.import_module('.' + module_name, __package__)
    return key, getattr(module, validator_name), getattr(module, filename_name)


def _plan_path(assignment, arguments):
    """Only a selected direct native-driver invocation establishes this proof."""
    requested = assignment.get('requested_job', {})
    profile = _profile(requested)
    argv = arguments.get('cmd')
    if (profile is None or assignment.get('resource_kind') != 'local'
            or arguments.get('target', 'resource') != 'resource'
            or not isinstance(argv, list) or not argv):
        return None
    path = Path(argv[-1])
    if not path.is_absolute():
        path = Path(arguments['workdir']) / path
    if path.name != profile[2]:
        return None
    _require(str(path) == str(PurePosixPath(path)) and '..' not in path.parts)
    return profile, path


def terminal_plan_identity(owner, *, attempt_directory):
    """Validate current command identity without pretending it is a job handle."""
    if not isinstance(owner, Mapping) or not isinstance(owner.get('execution_id'), str):
        return False
    execution = PurePosixPath(owner['execution_id'])
    root = execution.parent
    return (execution.is_absolute() and execution.name == 'intent.json'
        and '..' not in execution.parts and root.name == digest(owner.get('operation_key'))
        and root.parent.name == 'commands'
        and root.parent.parent.name == digest({
            'run_id': owner.get('run_id'), 'episode_id': owner.get('episode_id')})
        and root.parent.parent.parent.name == '.episode-execution'
        and PurePosixPath(attempt_directory).is_relative_to(root)
        and PurePosixPath(attempt_directory) != root)


def _plan(assignment, arguments):
    selected = _plan_path(assignment, arguments)
    if selected is None:
        return None
    profile, path = selected
    value = profile[1](json.loads(path.read_bytes()))
    _require(path.is_relative_to(assignment['workspace'])
        and Path(value['attempt_directory']).is_relative_to(assignment['workspace']))
    _require(value['requested_job'] == assignment['requested_job'])
    _require(value['identity']['assignment_sha256'] == digest(assignment))
    _require(path == Path(value['identity']['execution_id']).parent / profile[2])
    module = importlib.import_module('.' + _PROFILES[profile[0]][0], __package__)
    expected = getattr(module, _DRIVER_ARGUMENTS[profile[0]])(value)
    actual = list(arguments['cmd'])
    actual[-1] = str(path)
    _require(actual == expected)
    return profile, path, value


def _identified_files(value, *, module_roots=()):
    """Original purpose-specific validated file operands, including software."""
    for file in _identified_file_values(value, module_roots=module_roots):
        yield file['path']


def terminal_artifact_paths(assignment, arguments):
    """Select exact scientific operands for the executor's immutable capture.

    Preparation and shell commands remain ordinary actions. A command without
    this direct scientific invocation supplies no scientific job evidence.
    Missing or malformed plans remain in the command's own failure outcome;
    selecting snapshots never makes them accepted scientific evidence.
    """
    manifest = assignment.get('scientific_manifest')
    if assignment.get('resource_kind') == 'hpc' and isinstance(manifest, Mapping):
        return {'inputs': [manifest['path']], 'outputs': [manifest['path']]}
    try:
        selected = _plan(assignment, arguments)
    except Exception:
        return {'inputs': [], 'outputs': []}
    if selected is None:
        return {'inputs': [], 'outputs': []}
    profile, path, plan = selected
    module_roots = arguments['env'].get('PYTHONPATH', '').split(':')
    inputs = [str(path), *_identified_files(plan['requested_job'], module_roots=module_roots)]
    if terminal_plan_identity(plan['identity'], attempt_directory=plan['attempt_directory']):
        inputs.append(plan['identity']['execution_id'])
    outputs = [str(path)]
    module = importlib.import_module('.' + _PROFILES[profile[0]][0], __package__)
    for name in ('OWNER_FILENAME', 'STARTED_FILENAME', 'ENVIRONMENT_FILENAME', 'SOLVE_ENTERED_FILENAME'):
        filename = getattr(module, name, None)
        if isinstance(filename, str):
            outputs.append(str(Path(plan['attempt_directory']) / filename))
    specifications = plan.get('outputs', plan['requested_job'][profile[0]].get('outputs', []))
    if profile[0] == 'native_protein_structure':
        specifications = module.manifest_files(plan['requested_job'][profile[0]])
    for row in specifications:
        if isinstance(row, Mapping) and isinstance(row.get('relative_path'), str):
            outputs.append(str(Path(plan['attempt_directory']) / row['relative_path']))
    bundle_filename = getattr(module, 'BUNDLE_FILENAME', None)
    if isinstance(bundle_filename, str):
        outputs.append(str(Path(plan['attempt_directory']) / bundle_filename))
    return {'inputs': list(dict.fromkeys(inputs)), 'outputs': list(dict.fromkeys(outputs))}


def snapshot_bytes(snapshot):
    """Read exactly the immutable copy identified by the original executor."""
    _require(isinstance(snapshot, Mapping) and snapshot.get('available') is True
        and snapshot.get('source_stable_during_read') is True)
    raw = Path(snapshot['captured_path']).read_bytes()
    _require(len(raw) == snapshot['size_bytes']
        and hashlib.sha256(raw).hexdigest() == snapshot['sha256'])
    return raw


def verified_snapshot_path(snapshot):
    _require(isinstance(snapshot, Mapping) and snapshot.get('available') is True
        and snapshot.get('source_stable_during_read') is True)
    path = Path(snapshot['captured_path'])
    checksum, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
            size += len(block)
    _require(size == snapshot['size_bytes'] and checksum.hexdigest() == snapshot['sha256'])
    return path


def scientific_command_proof(assignment, arguments, outcome):
    """Bind actual direct execution to its original manifest and pinned inputs.

    This returns factual custody only. Each result adapter must still validate
    every scientific output with its unchanged purpose-specific reader.
    """
    selected = _plan_path(assignment, arguments)
    if selected is None:
        return None
    profile, path = selected
    detail = outcome.get('native_outcome', {})
    command = outcome.get('facts', {}).get('command', {})
    executed = detail.get('execution_command', {})
    _require(command.get('argv') == arguments['cmd']
        and command.get('environment') == arguments['env']
        and executed.get('cmd') == arguments['cmd']
        and executed.get('env') == arguments['env']
        and executed.get('target', 'resource') == 'resource'
        and executed.get('workdir') == arguments['workdir']
        and executed.get('command_sha256') == digest({name: arguments[name]
            for name in ('cmd', 'workdir', 'env')})
        and command.get('execution_id') == executed.get('intent_path')
        and type(command.get('returncode')) is int
        and command['returncode'] == executed.get('returncode'))
    before = {row['path']: row for row in detail.get('input_snapshots', [])}
    after = {row['path']: row for row in detail.get('output_snapshots', [])}
    _require(str(path) in before and str(path) in after)
    raw = snapshot_bytes(before[str(path)])
    _require(raw == snapshot_bytes(after[str(path)]))
    plan = profile[1](json.loads(raw))
    _require(path.is_relative_to(assignment['workspace'])
        and Path(plan['attempt_directory']).is_relative_to(assignment['workspace']))
    _require(plan['requested_job'] == assignment['requested_job']
        and plan['identity']['assignment_sha256'] == digest(assignment)
        and path == Path(plan['identity']['execution_id']).parent / profile[2])
    module = importlib.import_module('.' + _PROFILES[profile[0]][0], __package__)
    expected = getattr(module, _DRIVER_ARGUMENTS[profile[0]])(plan)
    actual = list(arguments['cmd'])
    actual[-1] = str(path)
    _require(actual == expected)
    relocated = {'TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'PIP_CACHE_DIR'}
    _require(all(name in relocated or arguments['env'].get(name) == value
        for name, value in assignment['requested_job']['environment'].items()))
    original = json.loads(Path(executed['intent_path']).read_bytes())
    owner = plan['identity']
    _require(original['assignment'] == assignment and original['arguments'] == arguments
        and owner['run_id'] == original['run_id']
        and owner['episode_id'] == original['episode_id']
        and owner['resource_id'] == assignment['resource_id']
        and owner['requested_job_sha256'] == digest(assignment['requested_job']))
    if terminal_plan_identity(owner, attempt_directory=plan['attempt_directory']):
        _require(owner['execution_id'] in before)
        preparation = json.loads(snapshot_bytes(before[owner['execution_id']]))
        _require(preparation['assignment'] == assignment
            and preparation['run_id'] == owner['run_id']
            and preparation['episode_id'] == owner['episode_id']
            and preparation['operation_key'] == owner['operation_key'])
    for original in _identified_file_values(plan['requested_job'],
            module_roots=arguments['env'].get('PYTHONPATH', '').split(':')):
        _require(original['path'] in before)
        actual = before[original['path']]
        verified_snapshot_path(actual)
        _require(actual['sha256'] == original['sha256']
            and ('size_bytes' not in original and 'size' not in original
                or actual['size_bytes'] == original.get('size_bytes', original.get('size'))))
    return {'version': 'terminal_scientific_command_proof_v1',
        'profile': profile[0], 'original_plan': deepcopy(plan),
        'plan_snapshot': deepcopy(before[str(path)]),
        'execution_command': deepcopy(executed), 'command': deepcopy(command),
        'input_snapshots': deepcopy(detail.get('input_snapshots', [])),
        'output_snapshots': deepcopy(detail.get('output_snapshots', []))}


def _identified_file_values(value, *, module_roots=()):
    if isinstance(value, Mapping):
        if (isinstance(value.get('path'), str) and value['path'].startswith('/')
                and isinstance(value.get('sha256'), str)):
            yield value
        if isinstance(value.get('path'), str) and value['path'].startswith('/'):
            descriptor = value.get('file')
            source = value.get('source')
            if isinstance(source, Mapping) and isinstance(source.get('file'), Mapping):
                descriptor = source['file']
            if isinstance(descriptor, Mapping) and isinstance(descriptor.get('sha256'), str):
                yield {**descriptor, 'path': value['path']}
        if isinstance(value.get('python_executable'), str) and isinstance(value.get('python_sha256'), str):
            yield {'path': value['python_executable'], 'sha256': value['python_sha256']}
        module_root = value.get('module_root')
        roots = [module_root] if isinstance(module_root, str) else module_roots
        for file in value.get('implementation_files', []):
            if (isinstance(file, Mapping) and isinstance(file.get('module'), str)
                    and isinstance(file.get('sha256'), str)):
                relative = file['module'].replace('.', '/')
                candidates = [Path(root) / suffix for root in roots if root and Path(root).is_absolute()
                    for suffix in (relative + '.py', relative + '/__init__.py')]
                selected = next((path for path in candidates if path.is_file()), None)
                _require(selected is not None, 'terminal_native_implementation_path_unavailable')
                yield {'path': str(selected), 'sha256': file['sha256']}
        for child in value.values():
            yield from _identified_file_values(child, module_roots=module_roots)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _identified_file_values(child, module_roots=module_roots)


def is_terminal_target(target):
    if not isinstance(target, Mapping) or target.get('resource_kind') != 'local':
        return False
    value = target.get('execution_id')
    if not isinstance(value, str):
        return False
    path = PurePosixPath(value)
    return path.name == 'intent.json' and '.episode-execution' in path.parts


def finalize_scientific_command(assignment, arguments, outcome):
    """Publish authenticated local native facts before the original iterator."""
    if assignment.get('resource_kind') != 'local':
        return outcome
    returned = deepcopy(outcome)
    try:
        if _plan_path(assignment, arguments) is None:
            return outcome
        proof = scientific_command_proof(assignment, arguments, outcome)
    except Exception as error:
        returned.setdefault('native_outcome', {})['scientific_custody_failure'] = {
            'code': 'terminal_scientific_custody_unavailable',
            'exception_type': type(error).__name__, 'message': str(error)}
        return returned
    if proof is None:
        return returned
    command = proof['command']
    execution_id = command['execution_id']
    returned.setdefault('native_outcome', {})['scientific_command_proof'] = proof
    returned.setdefault('facts', {})['requested_job'] = {
        'argv': command['argv'], 'environment': command['environment'],
        'returncode': command['returncode'], 'execution_id': execution_id,
        'requested_job_sha256': digest(assignment['requested_job']),
        'resource_kind': 'local',
        'status': 'completed' if command['returncode'] == 0 else 'failed',
        'output_paths': [row['path'] for row in proof['output_snapshots'] if row['available']],
        'handoff': {'execution_id': execution_id,
            'monitor_operation': 'exec_command', 'results_operation': 'exec_command'}}
    return returned


def terminal_local_job_matches(assignment, outcome):
    """Validate only already recorded host facts, without reopening files."""
    try:
        detail = outcome['native_outcome']
        proof = detail['scientific_command_proof']
        command = outcome['facts']['command']
        executed = detail['execution_command']
        job = outcome['facts']['requested_job']
        profile = _profile(assignment['requested_job'])
        _require(profile is not None and proof['profile'] == profile[0]
            and proof['version'] == 'terminal_scientific_command_proof_v1'
            and proof['command'] == command and proof['execution_command'] == executed)
        plan = profile[1](proof['original_plan'])
        _require(plan['requested_job'] == assignment['requested_job']
            and plan['identity']['assignment_sha256'] == digest(assignment))
        actual = {name: executed[name] for name in ('cmd', 'workdir', 'env')}
        selected = _plan_path(assignment, actual)
        _require(selected is not None and command['argv'] == actual['cmd']
            and command['environment'] == actual['env']
            and executed['command_sha256'] == digest(actual)
            and executed['intent_path'] == command['execution_id']
            and type(command['returncode']) is int
            and executed['returncode'] == command['returncode']
            and proof['input_snapshots'] == detail['input_snapshots']
            and proof['output_snapshots'] == detail['output_snapshots'])
        module = importlib.import_module('.' + _PROFILES[profile[0]][0], __package__)
        expected_argv = getattr(module, _DRIVER_ARGUMENTS[profile[0]])(plan)
        actual_argv = list(actual['cmd'])
        actual_argv[-1] = str(selected[1])
        _require(actual_argv == expected_argv)
        _require(job == {'argv': command['argv'], 'environment': command['environment'],
            'returncode': command['returncode'], 'execution_id': command['execution_id'],
            'requested_job_sha256': digest(assignment['requested_job']), 'resource_kind': 'local',
            'status': 'completed' if command['returncode'] == 0 else 'failed',
            'output_paths': [row['path'] for row in proof['output_snapshots'] if row['available']],
            'handoff': {'execution_id': command['execution_id'],
                'monitor_operation': 'exec_command', 'results_operation': 'exec_command'}})
        return True
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def read_terminal_handoff(store, run_id, target, scope):
    from .practical_receipt_information import PracticalReceiptInformation
    from .execution_contracts import validate_target
    from .episode_return_records import EpisodeReturnRecords
    from .communication import plain
    from method_loop.identities import EpisodeRef
    information = PracticalReceiptInformation(store, run_id)
    body = information.read(target['handle'], scope)
    source = store.get(target['handle'])
    snapshot = information._artifact_json(source['request_ref'])
    receipt = body['receipt']
    assignment = snapshot['assignment']
    returns = EpisodeReturnRecords(store, run_id, failure_prefix='terminal_scientific_')
    original = returns.context(body['episode_id'])
    returns.authenticate(original)
    _require(plain(original.scope) == body['scope'] and len(original.path) > 1)
    returns._commission(returns.context(EpisodeRef(run_id, original.path[:-1]).episode_id), original)
    selected = information._selected(receipt)
    _require(selected['result'] is not None)
    actual_return = json.loads(selected['result'])
    from .flux_balance_request_binding import is_compact_assignment
    if is_compact_assignment(plain(original.assignment)):
        from .flux_balance_request_binding import read_request_binding, match_practical_public_outcome
        control = read_request_binding(store, run_id, body['episode_id'])
        match_practical_public_outcome(actual_return, receipt, target['handle'],
            assignment=assignment, control_version=control['version'])
    else:
        _require(actual_return.get('status') in ('completed', 'partial')
            and actual_return.get('result') == receipt
            and target['handle'] in actual_return.get('record_refs', []))
    _require(receipt['tool_name'] == 'exec_command'
        and terminal_local_job_matches(assignment, receipt['outcome']))
    plan = receipt['outcome']['native_outcome']['scientific_command_proof']['original_plan']
    _require(plan['identity']['run_id'] == run_id
        and plan['identity']['episode_id'] == body['episode_id']
        and plan['identity']['resource_id'] == assignment['resource_id'])
    expected = {'version': 'execution_target_v1', 'handle': target['handle'],
        'run_id': run_id, 'resource_id': assignment['resource_id'], 'resource_kind': 'local',
        'execution_id': receipt['outcome']['facts']['requested_job']['execution_id'],
        'request_sha256': digest(assignment['requested_job']),
        'origin_episode_id': body['episode_id'], 'assignment': assignment, 'scope': body['scope']}
    _require(validate_target(expected) == target)
    return {'source_record': source, 'body': body, 'assignment_snapshot': snapshot,
        'start_receipt': receipt}


def validate_terminal_handoff(proof, intent, store, run_id):
    expected = read_terminal_handoff(store, run_id, intent['target'], intent['scope'])
    allowed = set(expected)
    if 'native_flux_balance' in intent['target']['assignment']['requested_job']:
        allowed.add('input_binding')
    _require(set(expected) <= set(proof) <= allowed)
    _require({name: proof[name] for name in expected} == expected)


def captured_terminal_file(store, snapshot, format):
    """Retain the original executed file bytes, never a later live-path version."""
    from .materials import artifact_file
    reference = artifact_file(store, verified_snapshot_path(snapshot))
    _require(reference == 'artifact_' + snapshot['sha256'])
    return terminal_file_identity(snapshot, format)


def terminal_file_identity(snapshot, format):
    _require(snapshot.get('available') is True and snapshot.get('source_stable_during_read') is True)
    return {'artifact_ref': 'artifact_' + snapshot['sha256'], 'sha256': snapshot['sha256'],
        'size_bytes': snapshot['size_bytes'], 'format': format}


def _marker_valid(plan, marker):
    if 'native_flux_balance' in plan['requested_job']:
        return (isinstance(marker, Mapping) and marker.get('plan_sha256') == digest(plan)
            and isinstance(marker.get('started_at'), str) and bool(marker['started_at']))
    return (isinstance(marker, Mapping) and set(marker) == {'plan', 'started_at'}
        and marker['plan'] == plan and isinstance(marker['started_at'], str) and bool(marker['started_at']))


def terminal_native_snapshot(receipts, action, observation):
    intent = action.intent
    store = getattr(receipts, 'store', getattr(receipts, '_store', None))
    handoff = read_terminal_handoff(store, receipts.owner.run_id, intent['target'], intent['scope'])
    proof = handoff['start_receipt']['outcome']['native_outcome']['scientific_command_proof']
    plan = proof['original_plan']
    profile = _profile(plan['requested_job'])
    module = importlib.import_module('.' + _PROFILES[profile[0]][0], __package__)
    marker_path = str(Path(plan['attempt_directory']) / module.STARTED_FILENAME)
    marker_snapshot = next((row for row in proof['output_snapshots'] if row['path'] == marker_path), None)
    marker, marker_file = None, None
    if marker_snapshot is not None and marker_snapshot['available']:
        marker = json.loads(snapshot_bytes(marker_snapshot))
        _require(_marker_valid(plan, marker))
        marker_file = captured_terminal_file(store, marker_snapshot, 'native_started_marker')
    value = {'version': 'terminal_native_snapshot_v1', 'original_plan': deepcopy(plan),
        'command_proof': deepcopy(proof),
        'plan_file': captured_terminal_file(store, proof['plan_snapshot'], plan['version']),
        'started_marker': marker, 'started_marker_file': marker_file,
        'driver_started': True if marker is not None else False if proof['command']['returncode'] != 0 else None}
    validate_terminal_native(value, intent, observation, store, receipts.owner.run_id)
    return value


def validate_terminal_native(value, intent, observation, store, run_id):
    _require(set(value) == {'version', 'original_plan', 'command_proof', 'plan_file',
        'started_marker', 'started_marker_file', 'driver_started'}
        and value['version'] == 'terminal_native_snapshot_v1')
    handoff = read_terminal_handoff(store, run_id, intent['target'], intent['scope'])
    proof = handoff['start_receipt']['outcome']['native_outcome']['scientific_command_proof']
    _require(value['command_proof'] == proof and value['original_plan'] == proof['original_plan']
        and value['plan_file'] == terminal_file_identity(proof['plan_snapshot'], value['original_plan']['version']))
    from .native_file_capture import _metadata
    for file in (value['plan_file'], value['started_marker_file']):
        if file is not None:
            metadata = _metadata(store, file['artifact_ref'])
            _require(metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'])
    _require(observation['native'].get('scientific_command_proof') == proof
        and observation['native'].get('terminal') is True
        and observation['native'].get('quiescent') is True
        and observation['returncode'] == proof['command']['returncode'])
    marker = value['started_marker']
    if marker is not None:
        _require(_marker_valid(value['original_plan'], marker) and value['driver_started'] is True)
        profile = _profile(value['original_plan']['requested_job'])
        module = importlib.import_module('.' + _PROFILES[profile[0]][0], __package__)
        marker_path = str(Path(value['original_plan']['attempt_directory']) / module.STARTED_FILENAME)
        actual = next((row for row in proof['output_snapshots'] if row['path'] == marker_path), None)
        _require(actual is not None and value['started_marker_file'] == terminal_file_identity(actual, 'native_started_marker'))
        raw = canonical(marker).encode('utf-8')
        _require(any(hashlib.sha256(candidate).hexdigest() == actual['sha256']
            and len(candidate) == actual['size_bytes'] for candidate in (raw, raw + b'\n')))
    else:
        _require(value['started_marker_file'] is None and value['driver_started'] is (
            False if proof['command']['returncode'] != 0 else None))


def terminal_observation(target, proof):
    """The completed original command is synchronous; no new job is invented."""
    command = proof['command']
    returned = command['returncode']
    return {'observed_at': proof['execution_command']['finished_at'],
        'state': 'completed' if returned == 0 else 'failed', 'returncode': returned,
        'failure_code': None if returned == 0 else 'native_command_failed',
        'result_available': any(row['available'] for row in proof['output_snapshots']),
        'measurements': [], 'outputs': [
            {'role': 'requested_output:' + row['path'], 'available': row['available'],
                'bytes': row['size_bytes'] if row['available'] else None,
                'writer_closed': row['available']} for row in proof['output_snapshots']],
        'logs': [], 'provenance_refs': [target['handle']],
        'native': {'terminal': True, 'quiescent': True,
            'scientific_command_proof': deepcopy(proof)}}


def validate_terminal_observation(value, intent, store, run_id):
    from .progress_records import validate_resource_observation
    validate_resource_observation(value)
    handoff = read_terminal_handoff(store, run_id, intent['target'], intent['scope'])
    proof = handoff['start_receipt']['outcome']['native_outcome']['scientific_command_proof']
    _require(value == terminal_observation(intent['target'], proof))
    return value
