"""Continuation: the commission is finite. The Episode's credit reaches the credit of the assignment's handoff
requirement exactly when the handoff exists, so the controller is the completion controller with that credit as its
target: the Episode ends at handoff. Before that it ends when further actions stop earning (failed launches, holds).
The target comes from the parent input, which ``read_from_parent`` made from the assignment.

The profile selection is the owner's: the profile key is ``launch_local:`` plus the request's yield class, and the
episode's settings hold its ``task_yield_profiles`` (``cutoff`` is the controller's cost)."""
from yield_control import CompletionYieldController


def request_yield_class(request):
    """The class of the execution request, without generated ids."""
    native = sorted(key for key in request['requested_job'] if key.startswith('native_'))
    parts = ['practical', request['resource_kind'], *native,
             {'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']]]
    return '_'.join(parts)


def yield_controller(initial_credit, settings, parent_input):
    profile = settings['task_yield_profiles']['launch_local:' + request_yield_class(parent_input['assignment'])]
    return CompletionYieldController('local_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['handoff_credit'], profile['parameters'])
