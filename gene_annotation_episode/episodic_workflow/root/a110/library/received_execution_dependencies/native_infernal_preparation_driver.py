from __future__ import annotations
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_driver import _absolute_directory, _validate_identity
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_preparation_contracts import compile_native_infernal_preparation_job, validate_native_infernal_preparation_requested_job
PLAN_VERSION = 'native_infernal_preparation_run_plan_v1'
OWNER_NAME = '.native-infernal-preparation-owner.json'
_PREFIX = 'native_infernal_preparation_'
_FAILURES = {'software_digest_mismatch': ({'software'}, {}), 'software_not_executable': ({'software'}, {}), 'software_unavailable': ({'software'}, {'reason': 'reason', 'errno': 'errno'}), 'input_missing': ({'inputs'}, {'ordinal': 'uint'}), 'input_io_error': ({'inputs'}, {'ordinal': 'uint', 'errno': 'errno'}), 'input_not_regular': ({'inputs'}, {'ordinal': 'uint'}), 'input_identity_mismatch': ({'inputs'}, {'ordinal': 'uint'}), 'working_copy_not_staged': ({'staging'}, {'operand_ordinal': 'uint', 'relative_path': 'path'}), 'working_copy_io_error': ({'staging'}, {'operand_ordinal': 'uint', 'relative_path': 'path', 'errno': 'errno'}), 'working_copy_identity_mismatch': ({'staging'}, {'operand_ordinal': 'uint', 'relative_path': 'path'}), 'scratch_limit': ({'staging', 'execution'}, {'observed_bytes': 'uint', 'limit_bytes': 'uint', 'relative_path': 'nullable_path'}), 'nonzero_returncode': ({'execution'}, {'returncode': 'int'}), 'command_unavailable': ({'execution'}, {'errno': 'errno'}), 'immutable_input_changed': ({'execution'}, {'ordinal': 'uint'}), 'immutable_working_copy_changed': ({'execution'}, {'operand_ordinal': 'uint', 'relative_path': 'path'}), 'input_final_unavailable': ({'inputs', 'execution'}, {'ordinal': 'uint', 'reason': 'reason', 'errno': 'errno'}), 'working_copy_final_unavailable': ({'staging', 'execution'}, {'operand_ordinal': 'uint', 'relative_path': 'path', 'reason': 'reason', 'errno': 'errno'}), 'missing_output': ({'outputs'}, {'relative_path': 'path'}), 'invalid_output': ({'outputs'}, {'relative_path': 'path', 'reason': 'reason', 'errno': 'errno'})}

def _error(reason):
    raise ValueError(_PREFIX + reason)

def _staged_relative(operand):
    if operand['role'] == 'models':
        return 'inputs/models.cm'
    if operand['role'] == 'ssi':
        return 'inputs/models.cm.ssi'
    return 'inputs/' + operand['role'] + '/' + str(operand['ordinal'])

def _compile(job, root):
    paths = {}
    for row in job['operands']:
        paths.setdefault(row['role'], []).append(str(root / _staged_relative(row)))
    return compile_native_infernal_preparation_job(job, input_paths=paths, output_directory=str(root))

def validate_preparation_plan(value):
    """Validate the separate preparation plan; perform no native execution."""
    plan = finite_json_copy(value)
    if type(plan) is not dict or set(plan) != {'version', 'identity', 'requested_job', 'attempt_directory', 'policy'} or plan['version'] != PLAN_VERSION:
        _error('run_plan_required')
    request = validate_native_infernal_preparation_requested_job(plan['requested_job'])
    _validate_identity(plan['identity'], request)
    policy = plan['policy']
    if type(policy) is not dict or set(policy) != {'memory_bytes', 'scratch_bytes'}:
        _error('explicit_policy_required')
    LocalJobPolicy(**policy)
    root = _absolute_directory(plan['attempt_directory'])
    job = request['native_infernal_preparation']
    if any((Path(row['path']).is_relative_to(root) for row in job['operands'])):
        _error('supplied_operand_inside_attempt')
    _compile(job, root)
    return plan
