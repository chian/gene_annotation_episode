"""Continuation: a completion controller whose target is the credit of the verified original handoff.

Carried from the old ``yield_estimator.py`` (``_request_yield_class``, ``_task_yield_profile``,
``yield_controller`` / ``_launch_api_yield_controller``) and README 7b: ``PracticalYieldEstimator(verify_completion)``
becomes ``CompletionYieldController``. The verified ``practical_completion`` proof (endpoint ``usable_handoff``)
was exactly one new handoff, so the target is ``handoff_unit``, read from the parent input; the controller's forecast
is then zero ("verified original handoff completion gives exact zero future credit"). The profile of the request
class (``launch_api:<class>``: ``cutoff`` = the controller's cost and ``parameters``) is the episode's setting
``task_yield_profiles``. The old ``require_private_yield`` switch and the completion-proof plumbing
(``completion.py``, ``practical_estimator``) are not carried."""
from yield_control import CompletionYieldController


def _request_yield_class(request):
    """Classify the original execution request without generated IDs (api branch of the old function)."""
    version = request.get('version')
    if version not in ('api_execution_assignment', 'api_service_assignment'):
        raise ValueError('execution_request_version_not_an_api_assignment:' + str(version))
    parts = ['api', request.get('service', 'unknown')]
    for field in ('algorithm', 'database'):
        if field in request:
            parts.append(request[field])
    return '_'.join(parts) + '_handoff'


def _task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    profile = _task_yield_profile(settings, 'launch_api:' + _request_yield_class(parent_input['assignment']))
    return CompletionYieldController('api_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['handoff_unit'], profile['parameters'])
