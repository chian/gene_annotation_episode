"""Continuation: the commission is finite, the original usable handoff. A verified handoff earns exactly the
commissioned target, so the controller is the completion controller (old: ``YieldController`` with
``PracticalYieldEstimator(verify_completion)``, which README 7b maps to ``'completion'``).

The old profile selection is kept: the profile key is ``launch_api:`` plus the request's yield class, and the
episode's settings hold its ``task_yield_profiles`` (``cutoff`` is the controller's cost). The request is read
from the parent input only."""
from yield_control import CompletionYieldController


def request_yield_class(request):
    """Classify the original execution request without generated IDs (old ``_request_yield_class``)."""
    version = request.get('version')
    if version in ('api_execution_assignment_v1', 'api_service_assignment_v1'):
        parts = ['api', request.get('service', 'unknown')]
        for field in ('algorithm', 'database'):
            if field in request:
                parts.append(request[field])
        return '_'.join(parts) + '_handoff'
    return 'compact_' + str(version)


def task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    profile = task_yield_profile(settings, 'launch_api:' + request_yield_class(parent_input))
    return CompletionYieldController('api_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
