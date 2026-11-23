"""A selected wait on native job events, as one completed unit of an episode.

An episode may offer its model a ``wait`` selection: an ``event_condition`` condition naming registered native
event targets it owns or received, the event it waits for after the cursor it last saw (a native target has one
event, ``state_changed``), and an optional ``reconsider_at`` UTC time. Waiting reports readiness only: it earns no
credit, so the wait unit's controller input carries the credit the controller already holds
(``view.controller_state.current_credit``).

* ``await selected_wait(events, condition)`` checks the condition's targets against ``events`` (a
  ``NativeEventLedger`` of ``episode_support.jobs.native_event_ledger``: ``validate_event_targets`` and
  ``wait_events``), awaits the ledger's wake and returns the wait outcome
  ``{'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': <event_wake>}``. A target
  the ledger does not know or does not support for that event raises ``EventTargetError`` in the ledger; that is
  returned as a failed outcome with ``wait_target_feedback(error, status='failed')`` so it enters the iterator
  like any other failed unit. Every other error propagates.
* ``wait_target_feedback(error, *, status)`` is the model feedback for an ``EventTargetError``: a selection that
  fails admission uses ``status='invalid'`` (no unit), an executed wait uses ``status='failed'``.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.jobs.native_event_ledger import EventTargetError

STATUSES = ('invalid', 'failed')


def wait_target_feedback(error, *, status):
    """The feedback for a wait condition whose target the event ledger cannot use."""
    if not isinstance(error, EventTargetError):
        raise TypeError('wait_target_feedback_requires_an_EventTargetError')
    if status not in STATUSES:
        raise ValueError('wait_target_feedback_status_must_be_invalid_or_failed:' + repr(status))
    return {'status': status, 'category': 'wait_target', 'code': error.code,
            'affected_refs': list(error.affected_refs), 'detail': str(error)}


async def selected_wait(events, condition):
    """Wait for the selected native job events; the outcome of one wait unit (see the module docstring)."""
    try:
        checked = events.validate_event_targets(condition)
        wake = await events.wait_events(checked)
    except EventTargetError as error:
        return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': wait_target_feedback(error, status='failed')}
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': wake}


__all__ = ['selected_wait', 'wait_target_feedback']
