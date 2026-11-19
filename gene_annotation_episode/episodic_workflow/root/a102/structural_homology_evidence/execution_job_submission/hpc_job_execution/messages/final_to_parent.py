"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
episode's own: the endpoint, whether it is validated, the satisfied requirement keys, the receipts kept).
Selectable: ``practical_completed``, ``practical_receipt_digests``, ``practical_receipt_refs``,
``execution_handoff_refs``, ``execution_result_refs``, ``execution_file_source_refs``,
``execution_file_capture_outcomes``, ``execution_completed`` and ``execution_result_origin`` (the empty record: this
episode acquires no result bytes). The receipts and handoffs are records the command tool wrote; they are returned
in custody in ``record_refs`` fields."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'completed': Field('boolean', 'Whether the requested endpoint has a validated, recorded completion'),
    'satisfied_keys': Field('list', 'The original requirement keys currently satisfied by the command receipts'),
    'receipts': Field('integer', 'The number of command receipts kept'),
    'last_command_status': Field('text', 'The status of the last command outcome, or none when no command ran'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the execution achieved against the requested endpoint', form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether the original requested endpoint predicates have a saved '
                                 'validated completion', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'Original selected command, actual result and earned '
                                    'operational credit sources', required=False),
    'execution_handoff_refs': Field('record_refs', 'The command receipts that established the handoff to the '
                                    'actual job', required=False),
    'execution_result_refs': Field('record_refs', 'Result records of the job (none: this episode acquires no '
                                   'results)', required=False),
    'execution_completed': Field('boolean', 'Whether the assigned endpoint has verified completion information',
                                 required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of a retained result (the empty record: this episode '
                                     'acquires no result bytes)', required=False),
})


def facts(summary):
    """The facts the episode recorded."""
    receipts = summary['receipts']
    handoff = [ref for ref, receipt in zip(summary['receipt_refs'], receipts)
               if any(item['satisfied'] and item['predicate']['kind'] == 'requested_job_handoff'
                      for item in receipt['validations'])]
    completed = summary['completion'] is not None
    return {'practical_completed': completed,
            'practical_receipt_digests': [digest(receipt) for receipt in receipts],
            'practical_receipt_refs': list(summary['receipt_refs']),
            'execution_handoff_refs': sorted(handoff),
            'execution_result_refs': [],
            'execution_completed': completed, 'execution_result_origin': {}}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    last = summary['last_outcome']
    result = {'credit': completion['credit'],
              'finding': {'endpoint': summary['assignment']['endpoint'], 'completed': recorded['practical_completed'],
                          'satisfied_keys': summary['progress']['satisfied_keys'],
                          'receipts': len(summary['receipts']),
                          'last_command_status': 'none' if last is None else last['status']}}
    for name in selection:
        result[name] = recorded[name]
    return result
