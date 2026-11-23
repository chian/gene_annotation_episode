"""The commission is finite: the old controller was the practical completion estimator (a verified completion of
the assignment's endpoint), with the cost and parameters of the profile of the request class. Its credit is the
sum of the satisfied requirements and its target is the credit of the assignment's completion keys, from the
parent input."""
from yield_control import CompletionYieldController


def _request_yield_class(request):
    """Classify the original execution request without generated IDs (old ``_request_yield_class`` for a
    ``practical_assignment`` request)."""
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
    """This admitted execution task's own yield profile, ``launch_hpc:<request class>``: ``{cutoff, parameters}``
    (the cutoff is the controller's cost)."""
    profile = _task_yield_profile(settings, 'launch_hpc:' + _request_yield_class(parent_input['assignment']))
    return CompletionYieldController('hpc_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
