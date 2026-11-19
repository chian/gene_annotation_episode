"""Continuation: the handoff credit still to be earned is bounded by the original requests not yet handed off.

The old controller was a ``BoundedYieldController`` whose maximum was the number of permitted original requests
without a received usable handoff at the start, times the handoff unit (``_launch_yield_controller``); README 7b
maps it to the bounded quality controller with that maximum. The profile (cost and parameters) is the old
``task_yield_profiles['launch:<sorted request classes joined by +>']``, now from the episode's settings.

The old exact-zero estimator for "nothing remaining" (``launch_original_request_exhaustion_v1``) is not carried:
only the controller stops an Episode, and a maximum of zero is the controller's own ``ValueError``."""
from yield_control import BoundedQualityYieldController


def request_yield_class(request):
    """The class of the original execution request (the old ``_request_yield_class``, practical form)."""
    native = sorted(key for key in request['requested_job'] if key.startswith('native_'))
    parts = ['practical', request['resource_kind'], *native,
             {'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']]]
    return '_'.join(parts)


def yield_controller(initial_credit, settings, parent_input):
    eligible = parent_input['eligible']
    remaining = len(set(eligible) - set(parent_input['handed_off_resource_ids'])) * parent_input['handoff_unit']
    classes = sorted(request_yield_class(parent_input['requests'][resource_id]) for resource_id in eligible)
    key = 'launch:' + '+'.join(classes)
    profiles = settings['task_yield_profiles']
    if key not in profiles:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    profile = profiles[key]
    return BoundedQualityYieldController('execution_job_submission', initial_credit, profile['cutoff'], remaining,
                                         profile['parameters'])
