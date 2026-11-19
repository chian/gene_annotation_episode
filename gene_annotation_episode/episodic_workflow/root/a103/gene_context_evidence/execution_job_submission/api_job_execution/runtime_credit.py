"""Credit and continuation of an A103 API job-execution episode.

The commission assigns one API job. Its credit is the job's current usable
handoff: 1 when the latest decoded service event that carries the job's
original native handle reports it ready for handoff (accepted, running or
complete), otherwise 0. A later failed or unknown status revises it back to 0.
An AppService job (``appservice_source``) is credited 1 while the episode holds
its confirmed ``TaskHandoff`` receipt and no later ``TaskObservation`` of that
task reports it failed, otherwise 0.
Its continuation is the completion controller toward that one-handoff target
with the binding's configured cutoff. Credit is never clamped or rescaled.
"""
from __future__ import annotations

CREDIT_DEFINITION = {
    'kind': 'a103_api_job_usable_handoff_v1',
    'unit': 'the assigned API job, counted when its latest decoded event carrying its original native '
            'handle reports it ready for handoff',
    'target': 1,
    'scientific_credit': False,
}
APPSERVICE_CREDIT_DEFINITION = {
    'kind': 'a103_api_job_usable_appservice_handoff_v1',
    'unit': "the assigned AppService job, counted while this episode holds its confirmed TaskHandoff receipt and "
            "no later status observation of that task reports it failed",
    'target': 1,
    'scientific_credit': False,
}
TARGET = 1.0


def handoff_credit(events):
    """The assigned job's current usable-handoff credit from its decoded events, in order."""
    latest = None
    for event in events:
        if event['native_handle'] is not None:
            latest = event
    return 1.0 if latest is not None and latest['handoff_ready'] else 0.0


def appservice_handoff_credit(handoff_held, latest_task_state):
    """The assigned AppService job's current usable-handoff credit from its handoff and latest task state."""
    return 1.0 if handoff_held and latest_task_state != 'failed' else 0.0


def completion_controller(epoch, initial_credit, continuation):
    from yield_control import CompletionYieldController, YieldParameters
    return CompletionYieldController(epoch, initial_credit, continuation['cutoff'], TARGET,
                                     YieldParameters(uncertainty_alpha=continuation['uncertainty_alpha']))


__all__ = ['APPSERVICE_CREDIT_DEFINITION', 'CREDIT_DEFINITION', 'TARGET', 'appservice_handoff_credit',
           'completion_controller', 'handoff_credit']
