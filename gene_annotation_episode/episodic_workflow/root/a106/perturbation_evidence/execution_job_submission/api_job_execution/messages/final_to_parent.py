"""What this episode returns. Always returned: the Episode's credit (the system hands it in ``completion``) and the
finding about the request or job. The parent may select ``execution_handoff_refs``, ``execution_result_refs``,
``execution_completed``, ``bvbrc_appservice_support_refs`` (the other receipts the AppService job produced) and
``bvbrc_application_outcomes`` (literal original selected BV-BRC intervention observations and calculated components);
the last two are the service-reported facts."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import (
    FACT_SOURCE, application_fact_sources)

SUPPORT_SOURCE = 'bvbrc_appservice_support_refs'

FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The configured API resource that ran the work'),
    'service': Field('text', 'The API service that carried out the work'),
    'handoff_established': Field('boolean', 'Whether a usable monitoring/results handoff was recorded'),
    'completed': Field('boolean', 'Whether the original handoff completion was verified'),
    'last_status': Field('text', 'The status of the last unit that ran, as the service reported it'),
    'interpretation': Field('text', "The model's latest interpretation of the job for the parent"),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What was established about the assigned request or job', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources actually available to this '
                                    'episode; a failed attempt does not establish a successful endpoint',
                                    required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to '
                                   'this episode', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information; '
                                 'yielding alone is false', required=False),
    SUPPORT_SOURCE: Field('record_refs', 'Actually received AppService preparation, Workspace, upload or '
                          'observation receipts; these are not scientific result acquisitions', required=False),
    FACT_SOURCE: Field('list', application_fact_sources()[FACT_SOURCE]['meaning'], required=False),
})


def recorded_facts(summary):
    """The facts a parent may select: the handoff and result references and completion from the unit outcomes, the
    receipts and application outcomes as the service reported them."""
    return {'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
            'execution_completed': summary['completed'],
            SUPPORT_SOURCE: summary['facts'][SUPPORT_SOURCE],
            FACT_SOURCE: summary['facts'][FACT_SOURCE]}


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'],
              'finding': {'resource_id': summary['resource_id'], 'service': summary['service'],
                          'handoff_established': bool(summary['handoff_refs']), 'completed': summary['completed'],
                          'last_status': 'none' if summary['last_status'] is None else summary['last_status'],
                          'interpretation': summary['report_update']}}
    recorded = recorded_facts(summary)
    for name in selection:
        result[name] = recorded[name]
    return result
