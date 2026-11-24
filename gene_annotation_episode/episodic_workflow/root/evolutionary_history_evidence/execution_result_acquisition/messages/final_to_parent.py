"""The return: controlled fields only. Always returned: the Episode's credit (the system hands it in ``completion``;
it is the productivity signal and no field restates it) and the finding: whether the requested acquisition is
complete, the family of the original target, the state of the job as last observed, the counts of what was acquired
and what was refused (how often the job service refused because the results of the job were not available) and the
bytes retained. No model-written text, no open record and no open list is returned.

Selectable: ``execution_handoff_refs`` (the handoff row), ``execution_job_record_refs`` (the latest check row and
the closure row of the job: the parent that holds the closure no longer counts the job as outstanding),
``execution_result_refs`` (each result acquisition this Episode retained: its record, its information artifact and
the fetched files its windows lie in) and ``execution_completed``."""
from method_loop import ChoiceField, Field, RecordForm

FAMILIES = ('local_file_source', 'native_blast_masking', 'native_blast_utility', 'api',
            'native_blast_standard_database', 'native_blast_database', 'native_hmmer_preparation', 'native_hmmer',
            'native_blast', 'native_bytes')
JOB_STATES = ('not_observed', 'queued', 'running', 'finished', 'failed', 'cancelled', 'unknown')

FINDING_FORM = RecordForm({
    'execution_completed': Field('boolean', 'Whether the requested acquisition is complete: the job finished and '
                                            'every requested byte is retained'),
    'target_family': ChoiceField('text', 'The family of the original target', FAMILIES),
    'acquisitions': Field('integer', 'The number of selected operations that completed'),
    'failure_count': Field('integer', 'The number of selected operations that returned a failed or an invalid '
                                      'outcome'),
    'job_state': ChoiceField('text', 'The state of the job in the latest check or closure row this episode holds',
                             JOB_STATES),
    'results_not_available': Field('integer', 'The number of fetches the job service refused because the results '
                                              'of the job were not available (the job had not ended)'),
    'windows_acquired': Field('integer', 'The number of byte windows this episode retained'),
    'bytes_acquired': Field('integer', 'The number of bytes in the windows this episode retained'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested acquisition is complete, the state of the job and the counts '
                               'of what was acquired and what was refused', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff row of the job this episode acquired results of',
                                    required=False),
    'execution_job_record_refs': Field('record_refs', 'The job ledger rows this episode chose for its parent: the '
                                       'latest check row it holds (the state of the job last observed) and, once '
                                       'the results were fetched, the closure row of the job', required=False),
    'execution_result_refs': Field('record_refs', 'The result acquisitions this episode retained: each result '
                                   'record, its information artifact and the fetched files its windows lie in',
                                   required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information: '
                                 'the job finished and every requested byte is retained, without a claim that the '
                                 'bytes are the output of that attempt. Yielding alone is false', required=False),
})


def _finding(summary):
    windows = [window for result in summary['results'] if not result['initial'] for window in result['windows']]
    rows = summary['acquisitions']
    return {'execution_completed': summary['execution_completed'], 'target_family': summary['family'],
            'acquisitions': sum(1 for row in rows if row['status'] == 'completed'),
            'failure_count': sum(1 for row in rows if row['status'] != 'completed'),
            'job_state': summary['job']['last_observed_state'] or 'not_observed',
            'results_not_available': sum(1 for row in rows if row['status'] == 'failed'
                                         and row['failure_code'] == 'results_not_available'),
            'windows_acquired': len(windows), 'bytes_acquired': sum(window['returned_bytes'] for window in windows)}


def final_to_parent(summary, completion, selection):
    facts = summary['execution_progress']
    return {'credit': completion['credit'], 'finding': _finding(summary), **{name: facts[name] for name in selection}}
