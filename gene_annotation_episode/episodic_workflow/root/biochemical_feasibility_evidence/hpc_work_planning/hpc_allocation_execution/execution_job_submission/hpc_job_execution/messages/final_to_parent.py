"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (whether
the requested endpoint was verified, which requirements are satisfied and which commands failed or ran). Selectable:
the terminal practical facts (``practical_completed``, ``practical_receipt_digests``, ``practical_receipt_refs``) and
the execution facts (``execution_handoff_refs``, ``execution_completed``); this episode acquires no results, so
``execution_result_refs``, ``execution_file_source_refs`` and ``execution_file_capture_outcomes`` are always
empty."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'completed': Field('boolean', 'Whether the assigned endpoint has a saved, validated completion'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'commands_run': Field('integer', 'How many commands this episode ran'),
    'commands_failed': Field('integer', 'How many of them recorded an execution failure'),
    'satisfied_keys': Field('list', 'The requirement keys satisfied when the episode ended'),
    'qualification': Field('text', 'What the saved receipts do and do not establish: a command that ran is not a '
                           'completed endpoint, and a submission with an uncertain outcome is not a duplicate'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the assigned job execution', form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether original requested endpoint predicates have a saved validated '
                                 'completion', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'Original selected command, actual result and earned '
                                    'operational credit sources, saved as records', required=False),
    'execution_handoff_refs': Field('record_refs', 'Own command receipts that are returnable handoffs for this '
                                    'exact assignment', required=False),
    'execution_result_refs': Field('record_refs', 'Actual requested result acquisitions available to this episode '
                                   '(none: this episode acquires no results)', required=False),
    'execution_file_source_refs': Field('record_refs', 'Selected local file sources retained by this episode '
                                        '(none)', required=False),
    'execution_file_capture_outcomes': Field('list', 'Selected file availability and custody qualifications '
                                             '(none)', required=False),
    'execution_completed': Field('boolean', 'Whether the assigned endpoint has verified completion information',
                                 required=False),
})


def facts(summary):
    """The facts a parent may select: the practical facts of the terminal behavior plus the execution facts, from the
    summary."""
    completed = summary['completion_proof'] is not None
    return {'practical_completed': completed,
            'practical_receipt_digests': [digest(receipt) for receipt in summary['receipts']],
            'practical_receipt_refs': list(summary['receipt_refs']),
            'execution_handoff_refs': sorted(summary['handoff_refs']),
            'execution_result_refs': [], 'execution_file_source_refs': [],
            'execution_file_capture_outcomes': [],
            'execution_completed': completed}


def final_to_parent(summary, completion, selection):
    receipts = summary['receipts']
    failed = sum(1 for receipt in receipts if 'failure' in receipt['outcome'].get('native_outcome', {}))
    completed = summary['completion_proof'] is not None
    finding = {'completed': completed, 'endpoint': summary['assignment']['endpoint'],
               'commands_run': len(receipts), 'commands_failed': failed,
               'satisfied_keys': list(summary['progress']['satisfied_keys']),
               'qualification': ('the endpoint predicates have a saved, validated completion' if completed else
                                 'no saved, validated completion of the requested endpoint: the satisfied '
                                 'requirement keys are listed')}
    recorded = facts(summary)
    result = {'credit': completion['credit'], 'finding': finding}
    for name in selection:
        result[name] = recorded[name]
    return result
