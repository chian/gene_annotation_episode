"""The acting A107 episode's identity for one tool action on the generic runner.

An episode source (``partner_presence_evidence/head_cycle.py``) builds one
``ActionInvocation`` per executed tool action from ``bound`` (run id, episode
id, admitted request and assignment, recorder), its admitted Store scope, the
record references it has received, the unit position and the name of the
recorded decision that selected the action, and passes it explicitly to
``A107ToolRegistry.execute_async``. A107's own qualification, genomic-request
and component tools read it instead of a host context.

The received-input reader over it is ``received_inputs.ReceivedInputs``: it reads
a File/Source only when this episode received it, and establishes the record that
produced it from this episode's recorded tool outcomes (``recorder``) or from the
shared Store record in the episode scope.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionInvocation:
    """One tool action of one A107 episode: who acts, in which scope, on what it has received."""
    run_id: str
    episode_id: str
    role: str
    scope: dict
    received_record_refs: tuple
    request: dict
    assignment: dict
    position: int
    decision_name: str
    recorder: object

    def __post_init__(self):
        for name in ('run_id', 'episode_id', 'role', 'decision_name'):
            if type(getattr(self, name)) is not str or not getattr(self, name):
                raise ValueError('a107_action_invocation_requires_' + name)
        for name in ('scope', 'request', 'assignment'):
            if not isinstance(getattr(self, name), dict):
                raise ValueError('a107_action_invocation_requires_' + name)
        if type(self.received_record_refs) is not tuple or any(
                type(ref) is not str or not ref for ref in self.received_record_refs):
            raise ValueError('a107_action_invocation_requires_received_record_refs')
        if type(self.position) is not int or self.position < 0:
            raise ValueError('a107_action_invocation_requires_position')
        if not callable(getattr(self.recorder, 'recall', None)) or getattr(self.recorder, 'run_id', None) != self.run_id:
            raise ValueError('a107_action_invocation_requires_recorder')

    @property
    def operation_key(self):
        """The deterministic operation key of this action (``run:episode:position``)."""
        return self.run_id + ':' + self.episode_id + ':' + str(self.position)


__all__ = ['ActionInvocation']
