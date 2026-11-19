"""Credit and continuation of an A102 API job-execution episode.

The commission assigns one API job. Its credit is the job's current usable
handoff: 1 when the latest decoded service event that carries the job's
original native handle reports it ready for handoff (accepted, running or
complete), otherwise 0. A later failed or unknown status revises it back to 0.
Its continuation is the completion controller toward that one-handoff target
with the binding's configured cutoff. Credit is never clamped or rescaled.
"""
from __future__ import annotations

CREDIT_DEFINITION = {
    'kind': 'a102_api_job_usable_handoff_v1',
    'unit': 'the assigned API job, counted when its latest decoded event carrying its original native '
            'handle reports it ready for handoff',
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


def completion_controller(epoch, initial_credit, continuation):
    from yield_control import CompletionYieldController, YieldParameters
    return CompletionYieldController(epoch, initial_credit, continuation['cutoff'], TARGET,
                                     YieldParameters(uncertainty_alpha=continuation['uncertainty_alpha']))


__all__ = ['CREDIT_DEFINITION', 'TARGET', 'completion_controller', 'handoff_credit']
