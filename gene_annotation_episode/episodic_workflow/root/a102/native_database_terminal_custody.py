"""Native BLAST database scientific inputs and actual submitted-command custody.

No staging, environment setup, submission or driver invocation is performed
here. The episode chooses those actions through its ordinary terminal.
"""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import PurePosixPath

from .execution_contracts import digest


PROFILES = ('native_blast_database', 'native_blast_standard_database')


def _require(condition, code='native_database_terminal_custody_conflict'):
    if not condition:
        raise ValueError(code)


def validate_native_database_resource(configuration, key):
    """Preserve the previous deployment checks without its operation dispatcher."""
    from .domain import validate_schema
    value = configuration[key]
    _require(isinstance(value, dict) and set(value) == {'version', 'producer', 'environment', 'bindings'}
        and value['version'] == key + '_resource_v1'
        and isinstance(value['producer'], dict) and set(value['producer']) == {'module_root', 'manifest'}
        and isinstance(value['environment'], dict)
        and all(isinstance(k, str) and k and isinstance(v, str) and '\0' not in k + v
            for k, v in value['environment'].items()), key + '_resource_invalid')
    contracts = importlib.import_module('.' + key + '_contracts', __package__)
    information = importlib.import_module('.' + key + '_tool_info', __package__)
    validate_schema(value['producer']['manifest'], contracts.FILE_IDENTITY_SCHEMA)
    function = (information.native_blast_database_tool_contracts if key == 'native_blast_database'
        else information.standard_blast_database_tool_contracts)
    function(value['bindings'], resource_kind='hpc', resource_id='configuration-validation')
    paths = [value['producer']['module_root'], value['producer']['manifest']['path']]
    paths.extend(row['software']['executable'] for row in value['bindings'])
    paths.extend(item['path'] for row in value['bindings'] for item in row['database_manifests'])
    _require(all(isinstance(path, str) and PurePosixPath(path).is_absolute()
        and '..' not in PurePosixPath(path).parts and '\0' not in path for path in paths),
        key + '_resource_path_invalid')
    aurora = PurePosixPath('/lus/flare/projects/BioReason-Aurora-Test')
    if PurePosixPath(configuration['workspace']).is_relative_to(aurora):
        _require(configuration['account'] == 'BioReason-Aurora-Test'
            and all(PurePosixPath(path).is_relative_to(aurora)
                for path in [*paths, configuration['python_executable']]),
            key + '_aurora_storage_or_account_conflict')
    return deepcopy(value)


def validate_native_database_assignment(configuration, assignment):
    for key in PROFILES:
        if key not in assignment['requested_job']:
            continue
        binding = configuration.get(key)
        _require(binding is not None, key + '_hpc_binding_required')
        job = assignment['requested_job'][key]
        selected = [row for row in binding['bindings'] if row['program'] == job['program']]
        _require(len(selected) == 1 and selected[0]['software'] == job['software']
            and all(row['manifest_file'] in selected[0]['database_manifests'] for row in job['databases']),
            key + '_selected_binding_conflict')
        paths = [job['software']['executable'], *[row['path'] for row in job['inputs']]]
        for database in job['databases']:
            paths.extend(database['native_paths'])
            paths.append(database['manifest_file']['path'])
            manifest = database['manifest']
            paths.extend(row['path'] for row in manifest['files'])
            paths.extend(row['path'] for row in manifest['metadata_manifests'])
            paths.extend(row['path'] for row in (manifest['preparation']['receipt'],
                manifest['preparation']['input_manifest'], manifest['access']['offline_configuration']) if row is not None)
        root = PurePosixPath(configuration['workspace'])
        _require(all(PurePosixPath(path).is_relative_to(root) for path in paths),
            key + '_selected_path_outside_workspace')


def qualify_manifest(target, receipt, raw, *, configuration=None):
    """Bind the caller's explicit scientific manifest to actual submission bytes."""
    from .practical_execution_records import terminal_job_matches
    assignment = target['assignment']
    descriptor = assignment.get('scientific_manifest')
    _require(isinstance(descriptor, dict), 'native_database_scientific_manifest_not_supplied')
    key = next((name for name in PROFILES if name in assignment['requested_job']), None)
    _require(key is not None and descriptor['format'] == key + '_run_plan_v1')
    _require(receipt['tool_name'] == 'exec_command'
        and receipt['assignment_sha256'] == digest(assignment)
        and receipt['run_id'] == target['run_id'] and receipt['episode_id'] == target['origin_episode_id']
        and terminal_job_matches(assignment, receipt['outcome']))
    detail = receipt['outcome']['native_outcome']
    _require(detail['actual_job']['job_id'] == target['execution_id'])
    snapshots = [row for row in detail.get('input_snapshots', []) if row['path'] == descriptor['path']]
    _require(len(snapshots) == 1 and snapshots[0]['available']
        and snapshots[0]['source_stable_during_read']
        and snapshots[0]['sha256'] == descriptor['sha256']
        and snapshots[0]['size_bytes'] == descriptor['size_bytes'])
    _require(len(raw) == descriptor['size_bytes'] and hashlib.sha256(raw).hexdigest() == descriptor['sha256'])
    contracts = importlib.import_module('.' + key + '_contracts', __package__)
    validator = (contracts._validate_plan if key == 'native_blast_database'
        else contracts.validate_standard_blast_database_plan)
    plan = validator(json.loads(raw))
    _require(plan['requested_job'] == assignment['requested_job']
        and plan['identity']['run_id'] == target['run_id']
        and plan['identity']['resource_id'] == target['resource_id']
        and PurePosixPath(plan['attempt_directory']).is_relative_to(assignment['workspace'])
        and descriptor['path'] == str(PurePosixPath(plan['attempt_directory']) /
            ('native-blast-database-plan.json' if key == 'native_blast_database'
                else 'native-blast-standard-database-plan.json')))
    if configuration is not None:
        binding = configuration[key]
        _require(plan['producer_manifest'] == binding['producer']['manifest']
            and plan['resource_environment'] == binding['environment'])
    return {'version': 'terminal_native_database_attempt_v1',
        'authenticated_attempt': {'identity': {**plan['identity'], 'execution_id': target['execution_id']},
            'attempt_directory': plan['attempt_directory'], 'plan_sha256': digest(plan)},
        'plan_path': descriptor['path'], 'scientific_manifest': deepcopy(descriptor),
        'plan': plan, 'submission_receipt': deepcopy(receipt)}


def validate_terminal_database_attempt(target, witness):
    """Recheck saved current custody; legacy submission ledgers remain separate."""
    from .practical_execution_records import terminal_job_matches
    _require(set(witness) == {'version', 'authenticated_attempt', 'plan_path',
        'scientific_manifest', 'plan', 'submission_receipt'}
        and witness['version'] == 'terminal_native_database_attempt_v1')
    assignment, receipt = target['assignment'], witness['submission_receipt']
    descriptor = assignment.get('scientific_manifest')
    plan = witness['plan']
    _require(descriptor == witness['scientific_manifest'] and descriptor['path'] == witness['plan_path']
        and receipt['tool_name'] == 'exec_command'
        and receipt['assignment_sha256'] == digest(assignment)
        and receipt['run_id'] == target['run_id'] and receipt['episode_id'] == target['origin_episode_id']
        and terminal_job_matches(assignment, receipt['outcome'])
        and receipt['outcome']['native_outcome']['actual_job']['job_id'] == target['execution_id']
        and plan['requested_job'] == assignment['requested_job'])
    key = next(name for name in PROFILES if name in assignment['requested_job'])
    contracts = importlib.import_module('.' + key + '_contracts', __package__)
    (contracts._validate_plan if key == 'native_blast_database'
        else contracts.validate_standard_blast_database_plan)(plan)
    _require(witness['authenticated_attempt'] == {
        'identity': {**plan['identity'], 'execution_id': target['execution_id']},
        'attempt_directory': plan['attempt_directory'], 'plan_sha256': digest(plan)})
    return deepcopy(witness['authenticated_attempt'])
