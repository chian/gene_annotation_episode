"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
assignment, whether the requested endpoint was verified, which requirements are satisfied, the requested job's
facts and the commands run). Selectable: ``execution_handoff_refs``, ``execution_result_refs``,
``execution_completed``, ``execution_result_origin`` and the terminal sources ``practical_completed``,
``practical_receipt_digests`` and ``practical_receipt_refs``. A launch acquires no results: ``execution_result_refs``
is empty and ``execution_result_origin`` is the empty record."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'assignment_id': Field('text', 'The identity of the assignment'),
    'assignment_sha256': Field('text', 'The digest of the original assignment'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'completion_target': Field('number', 'The total credit of the commissioned requirements'),
    'completed': Field('boolean', 'Whether the original requested endpoint predicates have a verified completion'),
    'completion_proof': Field('record', 'The verified completion, or the empty record when there is none'),
    'requested_job': Field('record', 'The facts of the requested job as the last command that ran it recorded '
                                     'them, or the empty record when no command ran it'),
    'satisfied_keys': Field('list', 'The original requirement keys currently satisfied'),
    'requirements': Field('list', 'Each original requirement with its credit and whether it is satisfied'),
    'commands_run': Field('integer', 'The number of commands executed'),
    'failures': Field('list', 'The recorded failures of the commands that failed, in order'),
    'receipt_sha256s': Field('list', 'The digests of the saved command receipts, in order'),
    'receipt_refs': Field('list', 'The references of the saved command receipts'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested endpoint was verified, and what the commands did',
                     form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether the original requested endpoint predicates have a saved '
                                            'validated completion', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'The saved receipts of the commands: original selected command, '
                                                   'actual result and earned operational credit', required=False),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources: the saved receipts of the '
                                                   'commands that handed the requested job off', required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                                  'acquires no results', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information; '
                                            'yielding alone is false', required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results (the empty record when '
                                               'none is retained)', required=False),
})


def _facts(summary):
    """The terminal facts plus every receipt that reads as a returnable handoff."""
    completed = summary['execution_completion'] is not None
    return {'practical_completed': completed,
            'practical_receipt_digests': [digest(receipt) for receipt in summary['receipts']],
            'practical_receipt_refs': list(summary['receipt_refs']),
            'execution_handoff_refs': sorted(summary['handoff_refs']), 'execution_result_refs': [],
            'execution_completed': completed, 'execution_result_origin': {}}


def _requested_job(summary):
    for receipt in reversed(summary['receipts']):
        job = receipt['outcome'].get('facts', {}).get('requested_job')
        if job is not None:
            return job
    return {}


def final_to_parent(summary, completion, selection):
    progress = summary['execution_progress']
    facts = _facts(summary)
    failures = [command['failure'] for command in summary['commands'] if command['failure'] is not None]
    result = {'credit': completion['credit'],
              'finding': {'assignment_id': summary['assignment']['assignment_id'],
                          'assignment_sha256': digest(summary['assignment']),
                          'endpoint': summary['assignment']['endpoint'],
                          'completion_target': summary['completion_target'],
                          'completed': facts['practical_completed'],
                          'completion_proof': summary['execution_completion'] or {},
                          'requested_job': _requested_job(summary),
                          'satisfied_keys': list(progress['satisfied_keys']),
                          'requirements': [{name: row[name] for name in ('key', 'credit', 'satisfied')}
                                           for row in progress['requirements']],
                          'commands_run': len(summary['commands']), 'failures': failures,
                          'receipt_sha256s': facts['practical_receipt_digests'],
                          'receipt_refs': facts['practical_receipt_refs']}}
    for name in selection:
        result[name] = facts[name]
    return result
