"""Where the annotation stands, from the loop's view: what the commissioner gave and, for each of the nine axes,
what its head's returns add up to. Only the reports ``messages/read_from_child.py`` made are read (numbers, flags
and record references); a head's own result is not.

For each axis: ``credit`` (the credit of its latest return; 0 before its first return), ``returned_credits`` (the
credit of each return, in order), ``finding`` (the numbers and flags of its latest finding), ``record_refs`` (every
record its head returned so far, which goes back to that head at its next commission) and ``outstanding_job_refs``
(the job records its head left outstanding at its latest return). ``commissions`` lists the axes commissioned, in
order."""
from ..credit import AXIS_WEIGHTS


def internal_summary(view):
    axes = {slot: {'credit': 0.0, 'returned_credits': [], 'finding': {}, 'record_refs': [],
                   'outstanding_job_refs': []} for slot in AXIS_WEIGHTS}
    for outcome in view.outcomes:
        axis, report = axes[outcome['slot']], outcome['report']
        axis['credit'] = report['credit']
        axis['returned_credits'].append(report['credit'])
        axis['finding'] = report['finding']
        axis['record_refs'].extend(ref for ref in report['record_refs'] if ref not in axis['record_refs'])
        axis['outstanding_job_refs'] = report['outstanding_job_refs']
    return {**view.parent_input, 'axes': axes, 'commissions': [outcome['slot'] for outcome in view.outcomes]}
