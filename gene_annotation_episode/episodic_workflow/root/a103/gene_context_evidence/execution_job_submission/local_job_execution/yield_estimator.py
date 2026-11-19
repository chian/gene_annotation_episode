"""Continuation: the commission is finite, the original requested endpoint. The credit of the satisfied
requirements reaches the credit of the assignment's completion keys exactly when the completion is verified, so the
controller is the completion controller (old: ``YieldController`` with ``PracticalYieldEstimator(verify_completion)``,
README 7b). The target comes from the parent input, which ``read_from_parent`` made from the assignment.

The old profile selection is kept: the profile key is ``launch_local:`` plus the request's yield class, and the
episode's settings hold its ``task_yield_profiles`` (``cutoff`` is the controller's cost)."""
from yield_control import CompletionYieldController


def request_yield_class(request):
    """Classify the original execution request without generated IDs (old
    ``ExecutionEpisodeYield._request_yield_class``, for the ``practical_assignment_v1`` this episode admits)."""
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    profile = task_yield_profile(settings, 'launch_local:' + request_yield_class(parent_input['assignment']))
    return CompletionYieldController('local_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
