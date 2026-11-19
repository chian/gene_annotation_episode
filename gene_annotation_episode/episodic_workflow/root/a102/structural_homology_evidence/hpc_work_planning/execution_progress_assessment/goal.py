"""The A102 HPC-planning progress monitor's goal (carried from its own ``goal.py`` at ``97308b94c``).

One monitor Episode investigates which further exposed progress information about its one assigned execution
target is useful, and returns what was actually observed. Its old role name is ``monitor``.
"""
from __future__ import annotations

from copy import deepcopy

ROLE = 'monitor'

# The grain declaration of this binding: what its cycle improves, its unit and what it returns.
GOAL = 'Investigate which further exposed progress information is useful for the assigned execution target'
UNIT = ('One model-selected progress tool action or one ordinary monitor commissioned for an exposed direct '
        'dependency')
RESULT = 'The monitoring facts actually delivered for the assigned target, with this monitor\'s information credit'

OWN_YIELD_CREDIT = "The monitor's information-credit projector and bound yield rule govern continuation. "
CALLER_CREDIT = "The caller's monitoring projector and configured controller own credit and continuation. "


def instructions(private_yield_binding):
    """The monitor's goal text; the credit sentence follows whether its own yield is configured."""
    credit_instruction = OWN_YIELD_CREDIT if private_yield_binding else CALLER_CREDIT
    return ("Investigate which further exposed progress information is useful for the assigned target. Use actual "
            "status, measured quantities, committed references and source-bound logs. Liveness establishes "
            "process presence only; elapsed time alone establishes neither productive work nor a stall. Unknown "
            "information stays unknown. Earlier outcomes and your admitted child forms inform later decisions. You "
            "may explicitly commission an ordinary monitor for one exposed direct dependency; no descendant "
            "traversal, fanout, cadence or depth is prescribed. Return the original parent's typed form at your "
            "closure even while the target remains active. Do not report private reasoning, intentions or "
            "unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or "
            "compose another report with a model. " + credit_instruction
            + 'Repeated observation identities and read timestamps alone earn no new information.')


def planning_context(request, assignment, yield_settings):
    """The monitor's planning context: objective, target, requested fields, its open question and progress rule."""
    return {'objective': request.goal.as_record().get('objective'), 'target_handle': assignment['target_handle'],
            'requested_fields': assignment['requested_fields'],
            'unresolved_question': 'Which exposed progress information would improve the original requested report?',
            'progress_definition': 'Actual received information under the caller-bound monitoring projector; '
                                   'repeated identities and timestamps alone earn no credit.',
            'yield_settings': deepcopy(yield_settings)}
