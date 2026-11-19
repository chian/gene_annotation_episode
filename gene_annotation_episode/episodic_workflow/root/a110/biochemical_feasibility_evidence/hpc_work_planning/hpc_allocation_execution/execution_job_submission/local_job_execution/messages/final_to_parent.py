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
    'practical_completed': Field('boolean', 'Whether the original requested endpoint predicates have a verified '
                                            'completion'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'commands_run': Field('integer', 'The number of commands executed'),
    'satisfied_keys': Field('list', 'The original requirement keys currently satisfied'),
    'unsatisfied_keys': Field('list', 'The original requirement keys not satisfied'),
    'failures': Field('list', 'The recorded failures of the commands that failed, in order'),
})

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested endpoint was verified, and what each command did',
                     form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether original requested endpoint predicates have a saved validated '
                                            'completion', required=False),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts',
                                       required=False),
    'practical_receipt_refs': Field('record_refs', 'Original selected command, actual result and earned operational '
                                                   'credit sources: the saved receipts', required=False),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources available to this episode: '
                                                   'the saved receipts of the commands that handed a job off',
                                    required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                                  'acquires no results', required=False),
    'execution_file_source_refs': Field('record_refs', 'Sources of captured local files: none for a launch',
                                        required=False),
    'execution_file_capture_outcomes': Field('list', 'Outcomes of local file captures: none for a launch',
                                             required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information; '
                                            'yielding alone is false', required=False),
})


def _facts(summary):
    """The facts a parent may select: the terminal facts and the handoff
    references."""
    completed = summary['execution_completion'] is not None
    return {'practical_completed': completed,
            'practical_receipt_digests': [digest(receipt) for receipt in summary['receipts']],
            'practical_receipt_refs': list(summary['receipt_refs']),
            'execution_handoff_refs': sorted(summary['handoff_refs']), 'execution_result_refs': [],
            'execution_file_source_refs': [], 'execution_file_capture_outcomes': [],
            'execution_completed': completed}


def final_to_parent(summary, completion, selection):
    progress = summary['execution_progress']
    satisfied = list(progress['satisfied_keys'])
    unsatisfied = [row['key'] for row in progress['requirements'] if not row['satisfied']]
    failures = [command['failure'] for command in summary['commands'] if command['failure'] is not None]
    facts = _facts(summary)
    result = {'credit': completion['credit'],
              'finding': {'practical_completed': facts['practical_completed'],
                          'endpoint': summary['assignment']['endpoint'], 'commands_run': len(summary['commands']),
                          'satisfied_keys': satisfied, 'unsatisfied_keys': unsatisfied, 'failures': failures}}
    for name in selection:
        result[name] = facts[name]
    return result
