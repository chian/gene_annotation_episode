"""Continuation: the completion controller toward the assignment's own finite target.

The target is the total credit of the assignment's progress requirements, read from the parent input. The
controller's cost and parameters are the episode's own ``task_yield_profiles`` entry for the class of the
original request (``launch_hpc:<request class>``)."""
import math

from yield_control import CompletionYieldController

EPOCH = 'hpc_job_execution'


def request_yield_class(request):
    """Classify the original execution request without generated IDs."""
    if request['version'] != 'practical_assignment':
        raise ValueError('execution_hpc_request_version_unsupported:' + str(request['version']))
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def yield_controller(initial_credit, settings, parent_input):
    key = 'launch_hpc:' + request_yield_class(parent_input)
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    target = math.fsum(item['credit'] for item in parent_input['progress_requirements'])
    return CompletionYieldController(EPOCH, initial_credit, profile['cutoff'], target, profile['parameters'])
