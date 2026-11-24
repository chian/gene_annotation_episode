"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources handed off and whether each handoff is verified complete). The parent may select ``execution_handoff_refs``,
``execution_result_refs`` (always empty: a launch acquires no results), ``execution_completed``,
``bvbrc_appservice_support_refs`` and ``bvbrc_application_outcomes`` (empty for the same reason); every one is computed
from the summary."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import (
    FACT_SOURCE, application_fact_sources)

SUPPORT_SOURCE = 'bvbrc_appservice_support_refs'
HANDOFF_SOURCE = 'execution_handoff_refs'
RESULT_SOURCE = 'execution_result_refs'
COMPLETED_SOURCE = 'execution_completed'

COMMISSION_FORM = RecordForm({
    'resource_id': Field('text', 'The resource the request was commissioned on'),
    'slot': Field('text', 'The resource child that carried it out: launch_api'),
    'handoff_established': Field('boolean', 'Whether the child returned a usable handoff'),
    'completed': Field('boolean', 'Whether the child verified the handoff completion'),
})
FINDING_FORM = RecordForm({
    'commissions': Field('list', 'Each commissioned request in order: the resource, the child and what it returned',
                         items=COMMISSION_FORM),
    'handoff_resource_ids': Field('list', 'The resources with a usable received handoff'),
    'new_handoff_count': Field('integer', 'How many of them were not already handed off at the commission'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources handed off the commissioned execution requests',
                     form=FINDING_FORM),
    HANDOFF_SOURCE: Field('record_refs', 'Qualified original handoff sources actually available to this episode.',
                          required=False),
    RESULT_SOURCE: Field('record_refs', 'Qualified actual requested result acquisitions available to this episode: '
                         'none, a launch acquires no results.', required=False),
    COMPLETED_SOURCE: Field('boolean', 'Whether this assignment has actual verified endpoint information. '
                            'Yielding alone is false.', required=False),
    SUPPORT_SOURCE: Field('record_refs', 'Actually received AppService preparation, Workspace, upload or '
                          'observation receipts; these are not scientific result acquisitions.', required=False),
    FACT_SOURCE: Field('list', application_fact_sources()[FACT_SOURCE]['meaning'] + ' (empty: a launch acquires no '
                       'results)', required=False),
})


def facts(summary):
    """The facts a parent may select, from the summary; a launch acquires no results."""
    return {HANDOFF_SOURCE: list(summary['handoff_refs']), SUPPORT_SOURCE: list(summary['support_refs']),
            RESULT_SOURCE: [], COMPLETED_SOURCE: summary['completed'], FACT_SOURCE: []}


def final_to_parent(summary, completion, selection):
    finding = {'commissions': [{'resource_id': commission['resource_id'], 'slot': commission['slot'],
                                'handoff_established': bool(commission['handoff_refs']),
                                'completed': commission['completed']}
                               for commission in summary['commissions']],
               'handoff_resource_ids': list(summary['handed_off']),
               'new_handoff_count': len(summary['new_handoff_resource_ids']),
               'qualification': ('a handoff is usable when its API job execution child returned handoff '
                                 'references; the record itself is not re-read here, and no result was acquired')}
    recorded = facts(summary)
    result = {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
    return result
