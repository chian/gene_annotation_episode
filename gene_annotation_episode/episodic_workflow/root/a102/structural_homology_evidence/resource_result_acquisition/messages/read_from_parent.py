"""What the scientific parent gives: the handed-off job, as the job ledger rows it holds, and the names of the
result files it requests. This is the only place the assignment is read.

Controlled messaging: the job travels as record references (its handoff row and the check rows the parent holds),
never as a described handoff; the requested data is a list of result file names, which the job's own result
catalog validates at the fetch. The old ``handoff`` record (``execution_handoff_v1``) and the open
``requested_data_selector`` are not fields of the form. The commission's message is not read."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import RESULTS_VERSION

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', RESULTS_VERSION),
    'job_refs': Field('record_refs', 'The job ledger rows of the one handed-off job whose results are acquired: '
                                     'its handoff row and the check rows the parent holds, passed in custody'),
    'requested_names': Field('list', 'The names of the result files the parent requests, as the job wrote them; '
                                     'at least one'),
})


def read_from_parent(assignment, message):
    return {'job_refs': list(assignment['job_refs']), 'requested_names': list(assignment['requested_names'])}
