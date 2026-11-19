"""The root annotation episode's goal, unit, result and the task instructions its model receives."""
from __future__ import annotations

GOAL = ('Improve the annotation of the supplied subject, measured by the weighted hypervolume over its nine '
        'evidence-axis credits')
UNIT = 'One model-selected evidence-axis episode and the credit its result returns'
RESULT = 'The subject annotation: each axis credit and finding, and the root hypervolume credit'

# What the root asks of every axis it commissions.
AXIS_REPORT_CONTRACT = {
    'decision': 'Choose the next evidence axis to improve for the subject',
    'measurements': {'credit': "This commission's credit on the axis's own unbounded scale"},
    'information': {'finding': 'What this evidence axis established about the subject'},
}


def axis_objective(role):
    return 'Improve the ' + role.replace('_', ' ') + ' for the supplied subject'


INSTRUCTIONS = """You direct the annotation of one subject (a sequence record scope in the run's store).

Each step you commission exactly one evidence-axis episode. The axis investigates the subject on its own terms and
returns a credit on its own unbounded scale together with its finding. The annotation's credit is the weighted
hypervolume prod_i (1 + v_i) ** w_i - 1 over the nine axis credits v_i with weights w_i, so a gain on an axis that
still has little credit raises the annotation credit more than the same gain on an axis that already has much.

The context gives you the subject scope, the axis weights, each axis's accumulated credit, every finding returned
so far, the current annotation credit, and the continuation controller's per-axis forecast of the credit another
invocation of that axis is expected to add (an unknown forecast is not zero). Feedback on a rejected response, if
any, is in `feedback`.

Choose the axis whose next invocation you expect to raise the annotation credit most, judged from the findings and
forecasts. For that axis supply every choice it offers (its thought pattern and the tools it should use, chosen
from its own options). Respond only with the selection object the output schema defines."""

__all__ = ['AXIS_REPORT_CONTRACT', 'GOAL', 'INSTRUCTIONS', 'RESULT', 'UNIT', 'axis_objective']
