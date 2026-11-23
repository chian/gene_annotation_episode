"""Where the annotation stands, from the loop's view: what the commissioner gave and, for each of the nine axes,
what its head's returns add up to. Only the reports ``messages/read_from_child.py`` made are read (numbers, flags
and record references); a head's own result is not.

For each axis: ``credit`` (the axis credit; 0 before its head's first return), ``credit_after_each_return`` (the axis
credit after each return, in order), ``finding`` (the numbers and flags of its latest finding), ``record_refs`` (every
record its head returned so far, which goes back to that head at its next commission), ``sheet_state_refs`` (the
sheet states of its latest return, for a head that takes them back) and ``outstanding_job_refs`` (the job records its
head left outstanding at its latest return). ``commissions`` lists the axes commissioned, in order.

The axis credit is made from what the head's returned credit measures (``read_from_child.CREDIT_RETURNED``): a
``standing`` return is the axis credit itself; a ``rise`` return is added to the axis credit before it."""
from ..credit import AXIS_WEIGHTS
from .read_from_child import CREDIT_RETURNED


def internal_summary(view):
    axes = {slot: {'credit': 0.0, 'credit_after_each_return': [], 'finding': {}, 'record_refs': [],
                   'sheet_state_refs': [], 'outstanding_job_refs': []} for slot in AXIS_WEIGHTS}
    for outcome in view.outcomes:
        axis, report = axes[outcome['slot']], outcome['report']
        axis['credit'] = (axis['credit'] + report['credit'] if CREDIT_RETURNED[outcome['slot']] == 'rise'
                          else report['credit'])
        axis['credit_after_each_return'].append(axis['credit'])
        axis['sheet_state_refs'] = report['sheet_state_refs']
        axis['finding'] = report['finding']
        axis['record_refs'].extend(ref for ref in report['record_refs'] if ref not in axis['record_refs'])
        axis['outstanding_job_refs'] = report['outstanding_job_refs']
    return {**view.parent_input, 'axes': axes, 'commissions': [outcome['slot'] for outcome in view.outcomes]}
