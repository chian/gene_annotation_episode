"""Continuation, carried from the old ``yield_estimator.py`` (``ExecutionEpisodeYield._launch_yield_controller``;
README 7b: the old ``BoundedYieldController`` is the bounded-quality controller).

The commission is finite: the old controller was bounded, with the maximum the credit of the original requests still
without a usable handoff, ``|eligible requests - resources already holding a usable handoff| * handoff_unit``, and the
cost and parameters of the profile ``task_yield_profiles['launch:' + '+'.join(sorted request classes)]`` of the
eligible requests (the old ``cutoff`` is the cost). It reads what ``read_from_parent`` produced, never the
assignment.

The old exact-zero estimator (``no_remaining_requests``, for a launch whose every eligible request already had a
usable handoff) is not carried (README 7b: only the controller stops an Episode), and the bounded-quality controller
refuses a maximum of 0 (``bounded_credit_range_invalid``). Such a launch gets the accumulation controller on the same
profile: no unit can earn credit (a nonzero initial credit still raises as before), so the forecast falls to the cost
and the controller stops it. The old raise ``execution_private_yield_binding_not_enabled`` (``require_private_yield``
false) is not carried: every Episode has a controller."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController


def _task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    """Cap one next handoff by the original request slots still uncredited."""
    permitted = parent_input['permitted']
    already_received = set(parent_input['received_handoff_resources'])
    remaining = len(set(permitted) - already_received) * parent_input['handoff_unit']
    classes = sorted(entry['yield_class'] for entry in permitted.values())
    profile = _task_yield_profile(settings, 'launch:' + '+'.join(classes))
    if remaining:
        return BoundedQualityYieldController('execution_job_submission', initial_credit, profile['cutoff'], remaining,
                                             profile['parameters'])
    if initial_credit != 0:
        raise ValueError('launch_no_uncredited_requests_but_nonzero_initial_credit')
    return AccumulationYieldController('execution_job_submission', initial_credit, profile['cutoff'],
                                       profile['parameters'])
