"""Continuation: credit toward the commissioned requirements.

The old controller was a ``YieldController`` with an endpoint estimator that gave zero further gain once a recorded
completion proof verified (``PracticalYieldEstimator``). README 7b maps it to the completion controller. Its target
is the credit the commissioned requirements add up to, read from ``parent_input`` (the assignment
``read_from_parent`` produced). The profile (cost and parameters) is the old one of the request class,
``task_yield_profiles['launch_hpc:<class>']``, now from the episode's settings."""
import math

from yield_control import CompletionYieldController


def _request_yield_class(request):
    """Classify the original execution request without generated IDs (the old ``_request_yield_class``)."""
    version = request.get('version')
    if version != 'practical_assignment_v1':
        if version in ('api_execution_assignment_v1', 'api_service_assignment_v1'):
            parts = ['api', request.get('service', 'unknown')]
            for field in ('algorithm', 'database'):
                if field in request:
                    parts.append(request[field])
            return '_'.join(parts) + '_handoff'
        return 'compact_' + str(version)
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def yield_controller(initial_credit, settings, parent_input):
    assignment = parent_input['assignment']
    key = 'launch_hpc:' + _request_yield_class(assignment)
    profiles = settings['task_yield_profiles']
    if key not in profiles:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    profile = profiles[key]
    target = math.fsum(item['credit'] for item in assignment['progress_requirements'])
    return CompletionYieldController('hpc_job_execution', initial_credit, profile['cutoff'], target,
                                     profile['parameters'])
