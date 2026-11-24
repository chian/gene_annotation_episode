"""The commission is finite: the Episode stops when its credit reaches the credit of its completion keys, the
requirements whose satisfaction completes the commissioned endpoint (the old practical completion estimator)."""
import math

from yield_control import CompletionYieldController


def request_yield_class(request):
    """Classify the original execution request without generated IDs."""
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def yield_controller(initial_credit, settings, parent_input):
    assignment = parent_input['assignment']
    key = 'launch_hpc:' + request_yield_class(assignment)
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    keys = set(assignment['completion_keys'])
    target = math.fsum(item['credit'] for item in assignment['progress_requirements'] if item['key'] in keys)
    return CompletionYieldController('hpc_job_execution', initial_credit, profile['cutoff'], target,
                                     profile['parameters'])
