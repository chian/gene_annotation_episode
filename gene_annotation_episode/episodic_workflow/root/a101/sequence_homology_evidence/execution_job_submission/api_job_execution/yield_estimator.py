"""The continuation (carried from ``yield_estimator.py``, ``completion.py`` and ``configuration.py``).

The old controller was ``YieldController`` with ``PracticalYieldEstimator(verify_completion)``: the profile
``launch_api:<request class>`` of ``task_yield_profiles`` gave its cutoff and parameters, and a verified original
handoff completion gave exact zero future gain. That is README 7b: completion, with the credit one established
handoff earns as its target. The target is the commission's ``completion_target`` (read by ``read_from_parent``);
the cutoff is the controller's cost; the profile lookup keeps its key and reads this episode's own settings
(``settings['task_yield_profiles']``).

The request class is the old ``_request_yield_class`` of an API request without generated ids: ``api``, the
service, the program and the database where the parent fixed them, ``handoff``."""
from yield_control import CompletionYieldController


def request_yield_class(parent_input):
    parts = ['api', parent_input['service']]
    parts.extend(parent_input['fixed_request'][name] for name in ('program', 'database')
                 if name in parent_input['fixed_request'])
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
