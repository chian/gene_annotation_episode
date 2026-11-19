"""The A102 progress monitor's goal (carried from its own ``goal.py`` at 97308b94c).

The goal text and the planning context are this episode's own words. ``GOAL``, ``UNIT`` and ``RESULT`` are the
binding's declared identity (``Grain.unit`` / ``Grain.result``).
"""
from __future__ import annotations

from copy import deepcopy

ROLE = 'monitor'
BINDING_PATH = 'structural_homology_evidence/execution_progress_assessment'
GOAL = 'Improve the assessment of progress of running work'
UNIT = 'One progress observation'
RESULT = 'Observed progress of the assigned work'


def goal_instructions(*, private_yield_binding):
    """The monitor's own goal instructions (old ``MonitorGoal.instructions``)."""
    credit_instruction = ("The monitor's information-credit projector and bound yield rule govern continuation. "
                          if private_yield_binding else
                          "The caller's monitoring projector and configured controller own credit and continuation. ")
    return ('Investigate which further exposed progress information is useful for the assigned target. Use actual '
            'status, measured quantities, committed references and source-bound logs. Liveness establishes process '
            'presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information '
            'stays unknown. Earlier outcomes and your admitted child forms inform later decisions. You may explicitly '
            'commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, '
            "cadence or depth is prescribed. Return the original parent's typed form at your closure even while the "
            'target remains active. Do not report private reasoning, intentions or unrestricted findings. Recorded '
            'facts use saved delivered observations; closure does not poll or compose another report with a model. '
            + credit_instruction + 'Repeated observation identities and read timestamps alone earn no new information.')


def planning_context(request_goal, assignment, yield_settings):
    """The monitor's planning context (old ``MonitorGoal.planning_context``); ``request_goal`` is its request goal."""
    return {'objective': request_goal, 'target_handle': assignment['target_handle'],
            'requested_fields': assignment['requested_fields'],
            'unresolved_question': 'Which exposed progress information would improve the original requested report?',
            'progress_definition': 'Actual received information under the caller-bound monitoring projector; repeated '
                                   'identities and timestamps alone earn no credit.',
            'yield_settings': deepcopy(yield_settings)}
