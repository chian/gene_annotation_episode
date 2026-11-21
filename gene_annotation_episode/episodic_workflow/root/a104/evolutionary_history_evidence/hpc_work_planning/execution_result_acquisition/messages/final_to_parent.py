"""The return: controlled fields only. Always returned: the Episode's credit (the system hands it in ``completion``;
it is the productivity signal and no field restates it), the finding (whether the requested acquisition is complete,
the state of the job as last observed, the counts of what was acquired and what was refused, how often the job
service refused because the results of the job were not available, and the bytes retained), the result records this
Episode retained and whether the requested acquisition is complete. No model-written text and no open record is
returned.

Selectable: ``execution_handoff_refs`` (the handoff row), ``execution_job_record_refs`` (the latest check row and
the closure row of the job: the parent that holds the closure no longer counts the job as outstanding) and
``execution_result_artifact_refs`` (the information artifact of each returned result record and the fetched files
its windows lie in: what a later commission passes as ``initial_result_artifact_refs``)."""
from method_loop import ChoiceField, Field, RecordForm

JOB_STATES = ('not_observed', 'queued', 'running', 'finished', 'failed', 'cancelled', 'unknown')
ALWAYS = ('execution_result_refs', 'execution_completed')

FINDING_FORM = RecordForm({
    'execution_completed': Field('boolean', 'Whether the requested acquisition is complete: the job finished and '
                                            'every requested byte is retained'),
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
    'finding': Field('record', 'Whether the requested acquisition is complete and its counts', form=FINDING_FORM),
    'execution_result_refs': Field('record_refs', 'The result acquisitions this episode retained: one '
                                   'episode.execution_result source record for each fetch and each further window'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information: '
                                 'the job finished and every requested byte is retained. Yielding alone is false'),
    'execution_handoff_refs': Field('record_refs', 'The handoff row of the job', required=False),
    'execution_job_record_refs': Field('record_refs', 'The job ledger rows this episode chose for its parent: the '
                                       'latest check row it holds (the state of the job last observed) and, once '
                                       'the results were fetched, the closure row of the job', required=False),
    'execution_result_artifact_refs': Field('record_refs', 'The information artifact of each record in '
                                            'execution_result_refs and the fetched files its windows lie in',
                                            required=False),
})


def _finding(summary):
    windows = [window for result in summary['own'] for window in result['windows']]
    rows = summary['acquisitions']
    return {'execution_completed': summary['completed'],
            'acquisitions': sum(1 for row in rows if row['status'] == 'completed'),
            'failure_count': sum(1 for row in rows if row['status'] != 'completed'),
            'job_state': summary['job']['last_observed_state'] or 'not_observed',
            'results_not_available': sum(1 for row in rows if row['status'] == 'failed'
                                         and row['failure_code'] == 'results_not_available'),
            'windows_acquired': len(windows), 'bytes_acquired': sum(window['returned_bytes'] for window in windows)}


def final_to_parent(summary, completion, selection):
    facts = summary['execution_progress']
    return {'credit': completion['credit'], 'finding': _finding(summary),
            **{name: facts[name] for name in (*ALWAYS, *selection)}}
