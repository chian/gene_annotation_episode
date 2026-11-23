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

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import canonical, digest


_PROFILES = {
}
_DRIVER_ARGUMENTS = {
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


def terminal_plan_identity(original_context, *, attempt_directory):
    """Validate current command identity without pretending it is a job handle."""
    if not isinstance(original_context, Mapping) or not isinstance(original_context.get('execution_id'), str):
        return False
    execution = PurePosixPath(original_context['execution_id'])
    root = execution.parent
    return (execution.is_absolute() and execution.name == 'intent.json'
        and '..' not in execution.parts and root.name == digest(original_context.get('operation_key'))
        and root.parent.name == 'commands'
        and root.parent.parent.name == digest({
            'run_id': original_context.get('run_id'), 'episode_id': original_context.get('episode_id')})
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


def _identified_files(value):
    """Original purpose-specific validated file operands."""
    for file in _identified_file_values(value):
        yield file['path']


def terminal_artifact_paths(assignment, arguments):
    """Select exact scientific operands for the executor's immutable capture.

    Preparation and shell commands remain ordinary actions. A command without
    this direct scientific invocation supplies no scientific job evidence.
    A selected plan that fails validation raises; selecting snapshots never
    makes a plan accepted scientific evidence.
    """
    manifest = assignment.get('scientific_manifest')
    if assignment.get('resource_kind') == 'hpc' and isinstance(manifest, Mapping):
        return {'inputs': [manifest['path']], 'outputs': [manifest['path']]}
    selected = _plan(assignment, arguments)
    if selected is None:
        return {'inputs': [], 'outputs': []}
    profile, path, plan = selected
    inputs = [str(path), *_identified_files(plan['requested_job'])]
    if terminal_plan_identity(plan['identity'], attempt_directory=plan['attempt_directory']):
        inputs.append(plan['identity']['execution_id'])
    outputs = [str(path)]
    module = importlib.import_module('.' + _PROFILES[profile[0]][0], __package__)
    for name in ('OWNER_FILENAME', 'STARTED_FILENAME', 'ENVIRONMENT_FILENAME', 'SOLVE_ENTERED_FILENAME'):
        filename = getattr(module, name, None)
        if isinstance(filename, str):
            outputs.append(str(Path(plan['attempt_directory']) / filename))
    specifications = plan.get('outputs', plan['requested_job'][profile[0]].get('outputs', []))
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
    original_context = plan['identity']
    _require(original['assignment'] == assignment and original['arguments'] == arguments
        and original_context['run_id'] == original['run_id']
        and original_context['episode_id'] == original['episode_id']
        and original_context['resource_id'] == assignment['resource_id']
        and original_context['requested_job_sha256'] == digest(assignment['requested_job']))
    if terminal_plan_identity(original_context, attempt_directory=plan['attempt_directory']):
        _require(original_context['execution_id'] in before)
        preparation = json.loads(snapshot_bytes(before[original_context['execution_id']]))
        _require(preparation['assignment'] == assignment
            and preparation['run_id'] == original_context['run_id']
            and preparation['episode_id'] == original_context['episode_id']
            and preparation['operation_key'] == original_context['operation_key'])
    for original in _identified_file_values(plan['requested_job']):
        _require(original['path'] in before)
        actual = before[original['path']]
        verified_snapshot_path(actual)
        _require(actual['sha256'] == original['sha256']
            and ('size_bytes' not in original and 'size' not in original
                or actual['size_bytes'] == original.get('size_bytes', original.get('size'))))
    return {'version': 'terminal_scientific_command_proof',
        'profile': profile[0], 'original_plan': deepcopy(plan),
        'plan_snapshot': deepcopy(before[str(path)]),
        'execution_command': deepcopy(executed), 'command': deepcopy(command),
        'input_snapshots': deepcopy(detail.get('input_snapshots', [])),
        'output_snapshots': deepcopy(detail.get('output_snapshots', []))}


def _identified_file_values(value):
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
        for child in value.values():
            yield from _identified_file_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _identified_file_values(child)


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
            and proof['version'] == 'terminal_scientific_command_proof'
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


def captured_terminal_file(store, snapshot, format):
    """Retain the original executed file bytes, never a later live-path version."""
    from gene_annotation_episode.materials import artifact_file
    reference = artifact_file(store, verified_snapshot_path(snapshot))
    _require(reference == 'artifact_' + snapshot['sha256'])
    return terminal_file_identity(snapshot, format)


def terminal_file_identity(snapshot, format):
    _require(snapshot.get('available') is True and snapshot.get('source_stable_during_read') is True)
    return {'artifact_ref': 'artifact_' + snapshot['sha256'], 'sha256': snapshot['sha256'],
        'size_bytes': snapshot['size_bytes'], 'format': format}
