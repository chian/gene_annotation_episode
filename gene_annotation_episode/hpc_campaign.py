"""Caller contracts, concrete launch portfolios, and measured outcome parsing."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path, PurePosixPath
import re

from .hpc_queue import canonical, digest, seconds
from .hpc_prediction import prior_model


def validate_commission(value, resources):
    """Fail before tools are exposed if the commission lacks real operands."""
    required = {'objective', 'resource_id', 'obligations', 'candidates', 'model', 'history',
                'validation_ids', 'credit', 'preferences', 'limits'}
    if set(value)-{'monitoring'} != required or not value['objective']:
        raise ValueError('explicit_hpc_commission_fields_required')
    if 'monitoring' in value:
        from .hpc_monitoring import validate_policy
        validate_policy(value['monitoring'])
    resource = resources[value['resource_id']]
    if resource['kind'] != 'pbs_ssh' or resource['account'] != 'BioReason-Aurora-Test':
        raise ValueError('Aurora_BioReason_resource_required')
    if not PurePosixPath(resource['workspace']).is_relative_to('/lus/flare/projects/BioReason-Aurora-Test/chian/runs'):
        raise ValueError('BioReason_run_storage_required')
    prior_model(value['model'])
    limits = value['limits']
    for key in ('max_nodes', 'max_wall_seconds', 'max_node_hours', 'shutdown_margin_seconds',
                'result_limit_bytes', 'queue_max_age_seconds'):
        if not math.isfinite(limits[key]) or limits[key] <= 0:
            raise ValueError('positive_hpc_limit_required:'+key)
    if limits['result_limit_bytes'] > 512*1024:
        raise ValueError('bounded_compact_result_limit_required')
    for name in ('deadline_seconds', 'elapsed_cost_per_second', 'node_hour_cost'):
        if not math.isfinite(value['preferences'][name]) or value['preferences'][name] < 0:
            raise ValueError('nonnegative_elapsed_time_preferences_required')
    for name, obligation in value['obligations'].items():
        if not name or obligation['credit'] < 0 or not math.isfinite(obligation['credit']) or not obligation['acceptance']:
            raise ValueError('explicit_useful_result_credit_and_acceptance_required')
        for predicate in obligation['acceptance']:
            if (not isinstance(predicate['field'], list) or not predicate['field']
                    or predicate['operator'] not in ('eq', 'ge', 'le') or 'value' not in predicate):
                raise ValueError('explicit_result_predicate_required')
            if predicate['operator'] != 'eq' and (type(predicate['value']) not in (int, float)
                    or not math.isfinite(predicate['value'])):
                raise ValueError('numeric_acceptance_threshold_required')
    if len(value['candidates']) > 32:
        raise ValueError('at_most_32_candidate_portfolios_required')
    seen = set()
    for candidate in value['candidates']:
        for item in candidate.get('files', []):
            path = PurePosixPath(item['path'])
            if (path.is_absolute() or '..' in path.parts or str(path) in ('.', 'runner.py', 'manifest.json')
                    or not isinstance(item['text'], str)):
                raise ValueError('candidate_file_must_be_relative_to_allocation_workspace')
        preparation = candidate.get('preparation', '')
        if not (isinstance(preparation, str) or isinstance(preparation, list)
                and all(isinstance(item, str) for item in preparation)):
            raise ValueError('candidate_preparation_must_be_text_or_list_of_text')
        if candidate['id'] in seen:
            raise ValueError('duplicate_candidate')
        seen.add(candidate['id'])
        if (type(candidate['nodes']) is not int or type(candidate['wall_seconds']) is not int
                or not re.fullmatch('[A-Za-z0-9_.-]+', candidate['queue'])):
            raise ValueError('integer_node_walltime_and_explicit_queue_required')
        if (not 1 <= candidate['nodes'] <= limits['max_nodes']
                or not 0 < candidate['wall_seconds'] <= limits['max_wall_seconds']
                or candidate['nodes']*candidate['wall_seconds']/3600 > limits['max_node_hours']):
            raise ValueError('candidate_exceeds_commission_budget')
        if not candidate['units'] or len(candidate['units']) > 128:
            raise ValueError('one_to_128_work_units_required')
        identifiers = set()
        obligations = set()
        for unit in candidate['units']:
            if (not re.fullmatch('[A-Za-z0-9_-]+', unit['unit_id']) or unit['unit_id'] in identifiers
                    or unit['obligation_id'] not in value['obligations'] or unit['obligation_id'] in obligations):
                raise ValueError('unique_units_and_obligations_per_portfolio_required')
            identifiers.add(unit['unit_id'])
            obligations.add(unit['obligation_id'])
            if (not unit['argv'] or any(not isinstance(arg, str) or not arg or '\0' in arg for arg in unit['argv'])
                    or not 0 < unit['minimum_seconds'] <= unit['maximum_seconds']
                    or unit['maximum_seconds'] > candidate['wall_seconds'] or unit['effort'] <= 0):
                raise ValueError('explicit_bounded_work_unit_required')
            if (not isinstance(unit['environment'], dict) or any(not isinstance(key, str) or not isinstance(val, str)
                    for key, val in unit['environment'].items()) or type(unit.get('reports_progress', False)) is not bool):
                raise ValueError('explicit_work_unit_environment_required')
    history = value['history']
    if len(history) > 2000 or len({row['id'] for row in history}) != len(history):
        raise ValueError('bounded_unique_measured_history_required')
    for row in history:
        if not row.get('provenance') or not math.isfinite(row['observed_at']):
            raise ValueError('historical_observation_provenance_required')
        for observation in row['metrics'].values():
            if observation['seconds'] < 0 or not math.isfinite(observation['seconds']):
                raise ValueError('nonnegative_measured_seconds_required')
    if not set(value['validation_ids']) <= {row['id'] for row in history}:
        raise ValueError('validation_id_not_in_measured_history')
    credit = value['credit']
    if not 0 <= credit['model_scale'] < credit['validation_scale']:
        raise ValueError('prospective_validation_scale_must_exceed_model_scale')
    slots = credit['validation_slots']
    if len({slot['id'] for slot in slots}) != len(slots):
        raise ValueError('unique_original_validation_slots_required')
    for slot in slots:
        if (slot['phase'] not in ('planned', 'queued', 'running')
                or slot['metric'] not in ('queue', 'work') or slot['weight'] < 0
                or slot['minimum_elapsed_seconds'] < 0):
            raise ValueError('invalid_fixed_validation_slot')
    if not math.isfinite(credit['model_scale']) or not math.isfinite(credit['validation_scale']):
        raise ValueError('finite_credit_scales_required')
    return deepcopy(value)


def build_plan(commission, candidate, configuration, owner, ordinal):
    plan_id = digest({'owner': owner, 'candidate': candidate, 'ordinal': ordinal})
    workspace = str(PurePosixPath(configuration['workspace'])/'hpc'/plan_id)
    def expand(value):
        if isinstance(value, str):
            return value.replace('{allocation_workspace}', workspace)
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            return {key: expand(item) for key, item in value.items()}
        return value
    manifest = {'version': 'hpc_allocation_manifest_v1', 'plan_id': plan_id,
        'workspace': workspace, 'wall_seconds': candidate['wall_seconds'],
        'shutdown_margin_seconds': commission['limits']['shutdown_margin_seconds'],
        'result_limit_bytes': commission['limits']['result_limit_bytes'], 'units': expand(candidate['units'])}
    manifest_sha = digest(manifest)
    runner = Path(__file__).with_name('hpc_allocation.py').read_text()
    files = [{'path': workspace+'/runner.py', 'text': runner},
             {'path': workspace+'/manifest.json', 'text': canonical(manifest)+'\n'}]
    files.extend({'path': workspace+'/'+item['path'], 'text': expand(item['text'])}
                 for item in candidate.get('files', []))
    for item in files:
        item['sha256'] = hashlib.sha256(item['text'].encode()).hexdigest()
    requirements = [{'key': 'file_'+str(i), 'credit': 0., 'predicate': {
        'kind': 'file_sha256', 'path': item['path'], 'sha256': item['sha256']}} for i, item in enumerate(files)]
    requirements.append({'key': 'handoff', 'credit': 1., 'predicate': {'kind': 'requested_job_handoff'}})
    wall = int(candidate['wall_seconds'])
    pbs_resources = [f"select={candidate['nodes']}",
                     f'walltime={wall//3600:02d}:{wall//60%60:02d}:{wall%60:02d}', 'filesystems=flare']
    request = {'version': 'practical_assignment_v1', 'assignment_id': plan_id, 'resource_kind': 'hpc',
        'resource_id': commission['resource_id'], 'workspace': workspace, 'endpoint': 'usable_handoff',
        'requested_job': {'argv': [configuration['python_executable'], '-B', workspace+'/runner.py',
                                  workspace+'/manifest.json', manifest_sha], 'environment': {}},
        'progress_requirements': requirements, 'completion_keys': [row['key'] for row in requirements],
        'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {}}, 'inventory_snapshot': {},
        'constraints': {'account': configuration['account'], 'queue': candidate['queue'], 'resources': pbs_resources}}
    return {'plan_id': plan_id, 'candidate_id': candidate['id'], 'manifest': manifest,
        'manifest_sha256': manifest_sha, 'files_to_stage': files,
        'preparation': expand(candidate.get('preparation', '')), 'practical_assignment': request,
        'launch_assignment': {'version': 'execution_launch_assignment_v1',
            'requests': {commission['resource_id']: request},
            'immutable_input_versions': [],
            'constraints': {'allowed_resource_ids': [commission['resource_id']], 'allowed_kinds': ['hpc']}},
        'submission_arguments': {'queue': candidate['queue'], 'resources': pbs_resources}}


def timestamp(value):
    if type(value) in (int, float):
        return float(value)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        # PBS observations are explicitly acquired with TZ=UTC.
        return datetime.strptime(value, '%a %b %d %H:%M:%S %Y').replace(tzinfo=timezone.utc).timestamp()


def telemetry(observation, allocation, candidate):
    now = timestamp(observation['observed_at'])
    fields = observation['native']['pbs_fields']
    queued_at, started_at = timestamp(fields.get('qtime')), timestamp(fields.get('stime'))
    state = {'submitted': 'queued', 'completed': 'complete'}.get(observation['state'], observation['state'])
    result = {'state': state, 'observed_at': now, 'phase': fields.get('job_state'),
              'queued_at': queued_at, 'started_at': started_at,
              'queue_elapsed_seconds': max(0., (started_at or now)-queued_at) if queued_at is not None else 0.,
              'work_elapsed_seconds': max(0., now-started_at) if started_at is not None else 0.}
    if started_at is not None:
        result['allocation_remaining_seconds'] = max(0., candidate['wall_seconds']-(now-started_at))
    if allocation is not None:
        done = [row['unit_id'] for row in allocation['units'] if row['state'] in ('complete', 'failed')]
        total = sum(row['effort'] for row in candidate['units'])
        result.update(completed_unit_ids=done,
            completed_fraction=sum(row['effort'] for row in candidate['units'] if row['unit_id'] in done)/total,
            current_unit_id=allocation['current_unit_id'], allocation_sample_at=allocation['updated_at'])
        result['work_elapsed_seconds'] = max(0., now-allocation['started_at'])
    result['peak_memory_bytes'] = memory_bytes(fields.get('resources_used', {}).get('mem'))
    result['memory_limit_bytes'] = memory_bytes(fields.get('Resource_List', {}).get('mem'))
    return result


def incorporate_progress(current, progress, candidate):
    """Optional tool-written progress, confined to the current original unit."""
    current = deepcopy(current)
    unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
    if (progress['unit_id'] != unit['unit_id'] or progress['observed_at'] > current['observed_at']+5
            or not 0 <= progress['completed_fraction'] <= 1):
        raise ValueError('invalid_original_unit_progress')
    current['completed_fraction'] += progress['completed_fraction']*unit['effort']/sum(row['effort'] for row in candidate['units'])
    current.update(phase=progress.get('phase'), progress_sample_at=progress['observed_at'],
                   progress_age_seconds=max(0., current['observed_at']-progress['observed_at']))
    if 'peak_memory_bytes' in progress:
        current['peak_memory_bytes'] = progress['peak_memory_bytes']
    return current


def memory_bytes(value):
    if value is None:
        return None
    match = re.fullmatch(r'([0-9.]+)([kmgt]?b)', str(value).lower())
    return float(match[1])*1024**{'b': 0, 'kb': 1, 'mb': 2, 'gb': 3, 'tb': 4}[match[2]] if match else None


def accepts(document, obligation):
    """Caller-frozen predicates, never an agent-supplied claim of credit."""
    for predicate in obligation['acceptance']:
        value = document
        try:
            for field in predicate['field']:
                value = value[field]
        except (KeyError, TypeError, IndexError):
            return False
        expected = predicate['value']
        if predicate['operator'] == 'eq':
            if type(value) is not type(expected) or value != expected:
                return False
        else:
            if type(value) not in (int, float) or not math.isfinite(value):
                return False
            if predicate['operator'] == 'ge' and value < expected:
                return False
            if predicate['operator'] == 'le' and value > expected:
                return False
    return True
