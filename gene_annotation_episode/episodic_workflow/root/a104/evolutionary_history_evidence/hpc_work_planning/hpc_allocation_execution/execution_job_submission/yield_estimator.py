"""The commission is finite: the old controller (``_launch_yield_controller``) was a bounded quality whose maximum
is the credit of the original requests still without a usable handoff: ``|eligible - already received| *
handoff_unit``. The cost and parameters are the profile ``task_yield_profiles['launch:' + '+'.join(sorted request
classes)]`` of the eligible requests, as before. It reads what ``read_from_parent`` produced, never the assignment.

The old exact-zero estimator (``no_remaining_requests``, for a launch whose every eligible request already had a
handoff, which raised on any nonzero credit) is not carried (README 7b: only the controller stops an Episode), and
no controller of the system has a maximum of 0 (``bounded_credit_range_invalid``): such a launch fails here."""
from yield_control import BoundedQualityYieldController


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
    if remaining:
        classes = sorted(entry['yield_class'] for entry in permitted.values())
        profile = _task_yield_profile(settings, 'launch:' + '+'.join(classes))
        return BoundedQualityYieldController('execution_job_submission', initial_credit, profile['cutoff'], remaining,
                                             profile['parameters'])
    raise ValueError('launch_every_original_request_already_has_a_handoff')
