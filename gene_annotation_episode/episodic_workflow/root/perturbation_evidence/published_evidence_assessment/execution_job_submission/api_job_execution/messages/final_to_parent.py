"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (the
service, the request or job identity, the submission outcome, whether the original usable handoff was established),
the handoff records (returned in custody) and whether the assignment has verified endpoint information. The parent may
select ``execution_result_refs``, ``bvbrc_appservice_support_refs`` and ``bvbrc_application_outcomes``; every field is
a recorded fact of the summary."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import (
    FACT_SOURCE, application_fact_sources)

SUPPORT_SOURCE = 'bvbrc_appservice_support_refs'
HANDOFF_SOURCE = 'execution_handoff_refs'
RESULT_SOURCE = 'execution_result_refs'
COMPLETED_SOURCE = 'execution_completed'

FINDING_FORM = RecordForm({
    'service': Field('text', 'The API service the work was carried out through'),
    'resource_id': Field('text', 'The bound API resource'),
    'handoff_established': Field('boolean', 'Whether the requested usable original handoff was established'),
    'qualification': Field('text', 'What the recorded service facts establish about the handoff and the submission'),
    'submission_outcome': Field('text', 'The recorded submission outcome, when a service reported one',
                                required=False),
    'request_identity': Field('text', 'The actual request identity, when a service reported one', required=False),
    'job_identity': Field('text', 'The actual job identity, when a service reported one', required=False),
})

RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the API service work established', form=FINDING_FORM),
    HANDOFF_SOURCE: Field('record_refs', 'Qualified original handoff sources actually available to this episode.'),
    COMPLETED_SOURCE: Field('boolean', 'Whether this assignment has actual verified endpoint information. '
                            'Yielding alone is false.'),
    RESULT_SOURCE: Field('record_refs', 'Qualified actual requested result acquisitions available to this episode.',
                         required=False),
    SUPPORT_SOURCE: Field('record_refs', 'Actually received AppService preparation, Workspace, upload or '
                          'observation receipts; these are not scientific result acquisitions.', required=False),
    FACT_SOURCE: Field('list', application_fact_sources()[FACT_SOURCE]['meaning'], required=False),
})


def final_to_parent(summary, completion, selection):
    facts = summary['facts_by_source']
    finding = {'service': summary['service'], 'resource_id': summary['resource_id'],
               'handoff_established': summary['handoff_established'],
               'qualification': ('original usable handoff established from recorded service facts'
                                 if summary['handoff_established'] else
                                 'original handoff not established; a missing reply does not establish that no job '
                                 'was created')}
    for name in ('submission_outcome', 'request_identity', 'job_identity'):
        if summary[name] is not None:
            finding[name] = summary[name]
    result = {'credit': completion['credit'], 'finding': finding, HANDOFF_SOURCE: facts[HANDOFF_SOURCE],
              COMPLETED_SOURCE: facts[COMPLETED_SOURCE]}
    for name in selection:
        result[name] = facts[name]
    return result
