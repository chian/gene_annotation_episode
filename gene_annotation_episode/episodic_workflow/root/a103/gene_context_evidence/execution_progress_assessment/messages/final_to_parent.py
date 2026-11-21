"""The return: controlled fields only, read by code from the check rows this monitor holds. No text the model
wrote and no log text is returned.

Always returned: ``credit`` (the system's), ``finding`` (whether the job was observed and, from this monitor's
latest check of it, its state from the job service's fixed vocabulary, whether its results are available and when it
was observed) and ``check_refs`` (the check rows this monitor wrote and those its dependency monitors returned, in
custody: the commissioner passes them back as the baseline of the next check, and reads a dependency's state from
them). Selectable: the measurements of the latest check, each as ``{'known', 'value'}`` because a route does not
report every one and unknown stays unknown, and the records of the log windows read and of the end-event receipts
a wait brought into custody.

Not carried from the old report: the count of newly informative snapshots (credit is that signal), the
qualification text, the snapshots themselves and the committed record references (a monitor returns no result of
the job)."""
from datetime import datetime

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import JOB_STATES, LOG_NAMES

FINDING_FORM = RecordForm({
    'observed': Field('boolean', 'Whether this monitor made a check of the job that the job service answered'),
    'state': ChoiceField('text', "The job's state at this monitor's latest check", JOB_STATES, required=False),
    'result_available': Field('boolean', "Whether the job's results were available at that check", required=False),
    'observed_at_unix_seconds': Field('number', 'When that check observed the job (UTC, Unix seconds)',
                                      required=False),
})
NUMBER_FORM = RecordForm({'known': Field('boolean', 'Whether the latest check reported the quantity'),
                          'value': Field('number', 'The quantity, when known', required=False)})
INTEGER_FORM = RecordForm({'known': Field('boolean', 'Whether the latest check reported the quantity'),
                           'value': Field('integer', 'The quantity, when known', required=False)})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the monitor found of the job', form=FINDING_FORM),
    'check_refs': Field('record_refs', 'The check rows this monitor wrote and those its dependency monitors '
                                       'returned'),
    'job_returncode': Field('record', "The return code of the job's ended command", required=False,
                            form=INTEGER_FORM),
    'job_duration_seconds': Field('record', "The duration of the job's ended command, in seconds", required=False,
                                  form=NUMBER_FORM),
    'job_elapsed_seconds': Field('record', 'The elapsed seconds of the job still running at the latest check',
                                 required=False, form=NUMBER_FORM),
    'stdout_bytes': Field('record', "The size of the job's stdout.log at the latest check", required=False,
                          form=INTEGER_FORM),
    'stderr_bytes': Field('record', "The size of the job's stderr.log at the latest check", required=False,
                          form=INTEGER_FORM),
    'log_window_refs': Field('record_refs', 'The log windows this monitor read: each window row and the artifact '
                                            'of its bytes', required=False),
    'event_receipt_refs': Field('record_refs', "The receipts of the job's end event that a wait brought into "
                                               'custody: each receipt row and its artifact', required=False),
})


def _known(value):
    return {'known': False} if value is None else {'known': True, 'value': value}


def _measured(latest, name):
    return None if latest is None or name not in latest else latest[name]


def _log_bytes(latest, name):
    outputs = _measured(latest, 'outputs') or []
    return next((output['bytes'] for output in outputs if output['name'] == name), None)


def monitor_facts(summary):
    """The selectable facts, from this monitor's latest check of the job."""
    latest = summary['latest']
    stdout, stderr = LOG_NAMES
    return {'job_returncode': _known(_measured(latest, 'returncode')),
            'job_duration_seconds': _known(_measured(latest, 'duration_seconds')),
            'job_elapsed_seconds': _known(_measured(latest, 'elapsed_seconds')),
            'stdout_bytes': _known(_log_bytes(latest, stdout)),
            'stderr_bytes': _known(_log_bytes(latest, stderr)),
            'log_window_refs': list(summary['log_window_refs']),
            'event_receipt_refs': list(summary['event_receipt_refs'])}


def finding(summary):
    latest = summary['latest']
    if latest is None:
        return {'observed': False}
    found = {'observed': True,
             'observed_at_unix_seconds': datetime.fromisoformat(latest['observed_at']).timestamp()}
    found.update({name: latest[name] for name in ('state', 'result_available') if name in latest})
    return found


def final_to_parent(summary, completion, selection):
    facts = monitor_facts(summary)
    return {'credit': completion['credit'], 'finding': finding(summary),
            'check_refs': list(summary['received_check_refs']), **{name: facts[name] for name in selection}}
