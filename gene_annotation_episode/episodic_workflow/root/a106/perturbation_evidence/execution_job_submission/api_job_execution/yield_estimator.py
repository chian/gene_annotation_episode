"""The continuation (carried from ``yield_estimator.py`` and ``configuration.py``).

The old controller was ``YieldController`` with ``PracticalYieldEstimator(verify_completion)``: the profile
``launch_api:<request class>`` of ``task_yield_profiles`` gave its cutoff and parameters, and a verified original
handoff completion gave exact zero future gain. That is README 7b: completion, with the credit one verified
handoff earns as its target. The target is the commission's ``completion_target`` (read by ``read_from_parent``);
the profile lookup keeps its key and reads this episode's own settings (``settings['task_yield_profiles']``).
"""
from yield_control import CompletionYieldController


def request_yield_class(parent_input):
    """Classify the original API request without generated ids (old ``_request_yield_class``)."""
    parts = ['api', parent_input['service']]
    for field in ('algorithm', 'database'):
        if parent_input[field] is not None:
            parts.append(parent_input[field])
    return '_'.join(parts) + '_handoff'


def task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    profile = task_yield_profile(settings, 'launch_api:' + request_yield_class(parent_input))
    return CompletionYieldController('api_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
