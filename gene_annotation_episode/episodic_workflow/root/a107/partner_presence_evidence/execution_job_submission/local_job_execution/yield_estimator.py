"""The commission is finite: the old controller was ``YieldController(..., estimate_with_context=
PracticalYieldEstimator(verify_completion))`` with a private yield profile per original request class, whose
forecast fell to zero once a verified endpoint completion existed. That is the completion controller. The target is
the credit the commissioned requirements can earn, from the parent input.

The old settings (``task_yield_profiles``, keyed ``launch_local:<request class>``, each ``{cutoff, parameters}``) are
the episode's ``settings``; the old cutoff is the controller's cost."""
from yield_control import CompletionYieldController


def _request_yield_class(request):
    """Classify the original execution request without generated IDs (the old classifier; the assignment of this
    episode is always ``practical_assignment_v1``, so the old ``compact_<version>`` and API branches cannot
    occur)."""
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
    return CompletionYieldController('local_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
