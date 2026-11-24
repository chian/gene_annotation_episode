"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (what the
acquisition established) and ``execution_result_refs`` (the acquired result records, returned in custody). The parent
may select ``execution_handoff_refs``, ``execution_completed``, ``bvbrc_appservice_support_refs`` and
``bvbrc_application_outcomes``; every one is a recorded fact of the summary."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import (
    FACT_SOURCE, application_fact_sources)

SUPPORT_SOURCE = 'bvbrc_appservice_support_refs'
HANDOFF_SOURCE = 'execution_handoff_refs'
RESULT_SOURCE = 'execution_result_refs'
COMPLETED_SOURCE = 'execution_completed'

FINDING_FORM = RecordForm({
    'handoff_ref': Field('text', 'The original handoff the results were acquired through'),
    'results_acquired': Field('integer', 'How many distinct acquired result records the episode holds'),
    'execution_completed': Field('boolean', 'Whether the assignment has actual verified endpoint information; '
                                 'yielding alone is false'),
    'qualification': Field('text', 'What the recorded service facts establish about the acquisition'),
})

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the result acquisition established', form=FINDING_FORM),
    RESULT_SOURCE: Field('record_refs', 'Qualified actual requested result acquisitions available to this '
                         'episode.'),
    HANDOFF_SOURCE: Field('record_refs', 'Qualified original handoff sources actually available to this episode.',
                          required=False),
    COMPLETED_SOURCE: Field('boolean', 'Whether this assignment has actual verified endpoint information. '
                            'Yielding alone is false.', required=False),
    SUPPORT_SOURCE: Field('record_refs', 'Actually received AppService preparation, Workspace, upload or '
                          'observation receipts; these are not scientific result acquisitions.', required=False),
    FACT_SOURCE: Field('list', application_fact_sources()[FACT_SOURCE]['meaning'], required=False),
})


def final_to_parent(summary, completion, selection):
    facts = summary['facts_by_source']
    acquired = len(summary['result_refs'])
    if summary['execution_completed']:
        qualification = 'actual complete acquisition established from recorded service facts'
    elif acquired:
        qualification = 'partial acquisition: results were acquired but complete acquisition is not established'
    else:
        qualification = 'no result acquired; yielding alone establishes nothing about the endpoint'
    finding = {'handoff_ref': summary['handoff_ref'], 'results_acquired': acquired,
               'execution_completed': summary['execution_completed'], 'qualification': qualification}
    result = {'credit': completion['credit'], 'finding': finding, RESULT_SOURCE: facts[RESULT_SOURCE]}
    for name in selection:
        result[name] = facts[name]
    return result
