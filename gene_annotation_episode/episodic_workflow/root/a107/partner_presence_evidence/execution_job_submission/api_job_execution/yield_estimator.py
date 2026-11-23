"""The continuation (carried from ``yield_estimator.py``, ``completion.py`` and ``configuration.py``).

The old controller was ``YieldController`` with ``PracticalYieldEstimator(verify_completion)``: the profile
``launch_api:<request class>`` of ``task_yield_profiles`` gave its cutoff and parameters, and a verified original
handoff completion gave exact zero future gain. That is README 7b: completion, with the credit one verified
handoff earns as its target. The target is the commission's ``completion_target`` (read by ``read_from_parent``);
the cutoff is the controller's cost; the profile lookup keeps its key and reads this episode's own settings
(``settings['task_yield_profiles']``).
"""
from yield_control import CompletionYieldController


def request_yield_class(request):
    """Classify the original API request without generated ids (old ``_request_yield_class``, API branch)."""
    version = request.get('version')
    if version in ('api_execution_assignment', 'api_service_assignment'):
        parts = ['api', request.get('service', 'unknown')]
        for field in ('algorithm', 'database'):
            if request.get(field) is not None:
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
