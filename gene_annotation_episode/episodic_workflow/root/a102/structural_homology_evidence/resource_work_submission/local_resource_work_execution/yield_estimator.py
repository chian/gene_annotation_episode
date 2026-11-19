"""The commission is finite: the old continuation of this resource episode was the practical completion estimator
(zero next gain once the completion is verified) under the private yield profile of the original request class
(``task_yield_profiles``, key ``launch_local:<request class>``). README 7b maps it to the completion controller.
The target is the total credit of the commissioned requirements, from the parent input; the practical credit is
the sum of the satisfied ones, so it cannot pass it.

The old settings (each profile ``{cutoff, parameters}``) are the episode's ``settings``; the old cutoff is the
controller's cost."""
from yield_control import CompletionYieldController


def _request_yield_class(request):
    """Classify the original execution request without generated identities: ``practical_<resource kind>`` plus
    the native job family, if any, plus ``handoff`` or ``outputs`` by the requested endpoint."""
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def _task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    """Choose only this admitted execution task's own yield binding."""
    profile = _task_yield_profile(settings, 'launch_local:' + _request_yield_class(parent_input['assignment']))
    return CompletionYieldController('local_resource_work_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
