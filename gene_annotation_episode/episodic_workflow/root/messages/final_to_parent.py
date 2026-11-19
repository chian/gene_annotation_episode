"""The return of the annotation: controlled data only. Always returned: ``credit`` (the annotation credit its
controller stopped on, which the system hands in ``completion``) and ``finding``: how many commissions the root
made and, for each of the nine axes, its credit, how often it was commissioned and how many job records its head
left outstanding. Selectable, returned in custody: ``record_refs`` (the records the axis heads returned) and
``outstanding_job_refs`` (the records of the jobs still outstanding, with which a later run can return to them)."""
from method_loop import Field, RecordForm

from ..credit import AXIS_WEIGHTS

AXIS_FORM = RecordForm({
    'credit': Field('number', 'The axis credit: what its head returned at its latest return, 0 before the first'),
    'commissions': Field('integer', 'How often the axis was commissioned'),
    'outstanding_jobs': Field('integer', 'How many job records its head left outstanding at its latest return'),
})
AXES_FORM = RecordForm({slot: Field('record', 'The state of the ' + slot + ' axis', form=AXIS_FORM)
                        for slot in AXIS_WEIGHTS})
FINDING_FORM = RecordForm({
    'commissions': Field('integer', 'How many axis commissions the root made'),
    'axes': Field('record', 'The state of each of the nine axes', form=AXES_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The annotation credit when the Episode's controller stopped it"),
    'finding': Field('record', 'Where the annotation stands on each of the nine axes', form=FINDING_FORM),
    'record_refs': Field('record_refs', 'The records the axis heads returned', required=False),
    'outstanding_job_refs': Field('record_refs', 'The records of the jobs the axis heads left outstanding',
                                  required=False),
})


def final_to_parent(summary, completion, selection):
    axes = summary['axes']
    result = {'credit': completion['credit'],
              'finding': {'commissions': len(summary['commissions']),
                          'axes': {slot: {'credit': axis['credit'], 'commissions': len(axis['returned_credits']),
                                          'outstanding_jobs': len(axis['outstanding_job_refs'])}
                                   for slot, axis in axes.items()}}}
    if 'record_refs' in selection:
        result['record_refs'] = list(dict.fromkeys(ref for axis in axes.values() for ref in axis['record_refs']))
    if 'outstanding_job_refs' in selection:
        result['outstanding_job_refs'] = list(dict.fromkeys(
            ref for axis in axes.values() for ref in axis['outstanding_job_refs']))
    return result
