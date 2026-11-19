"""The records passed in custody (job inputs, and the rows of jobs left outstanding) and the plan."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'input_refs': Field('record_refs', 'The inputs a job may stage, passed in custody'),
    'job_refs': Field('record_refs', 'The ledger rows of outstanding jobs, passed in custody'),
})


def read_from_parent(assignment, message):
    return {'input_refs': assignment['input_refs'], 'job_refs': assignment['job_refs'], 'plan': message['plan']}
