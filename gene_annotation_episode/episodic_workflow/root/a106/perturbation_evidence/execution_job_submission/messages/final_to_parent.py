"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources got a usable handoff and which launches ran). The parent may select ``execution_handoff_refs`` (the job
identity, preserved across a return), ``execution_result_refs`` (always empty: a launch acquires no results),
``execution_completed``, ``bvbrc_appservice_support_refs`` (the AppService receipts the API launch child returned) and
``bvbrc_application_outcomes`` (the application outcomes it reported). All of them are computed from the summary."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import (
    FACT_SOURCE, application_fact_sources)

SUPPORT_SOURCE = 'bvbrc_appservice_support_refs'
SUPPORT_MEANING = ('Actually received AppService preparation, Workspace, upload or observation receipts; these are '
                   'not scientific result acquisitions.')

LAUNCH_FORM = RecordForm({
    'slot': Field('text', 'The launch child commissioned'),
    'resource_id': Field('text', 'The resource it was commissioned on'),
    'completed': Field('boolean', 'Whether the child verified the requested endpoint'),
    'handoff_refs': Field('list', 'The handoff records the child returned'),
})
FINDING_FORM = RecordForm({
    'handoff_established': Field('boolean', 'Whether at least one usable handoff was received'),
    'handoff_resources': Field('list', 'The resource ids that have a usable handoff from this launch'),
    'new_handoff_count': Field('integer', 'The handoffs of resources that had none when this launch began'),
    'launches_run': Field('integer', 'The launch children commissioned'),
    'launches': Field('list', 'Each launch child commissioned, in order', items=LAUNCH_FORM),
    'qualification': Field('text', 'What the recorded handoffs establish: a received handoff is not a finished job '
                                   'and a missing reply does not establish that no job was created'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources got a usable handoff and which launches ran', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources actually available to this '
                                                   'episode; a failed attempt does not establish a successful '
                                                   'endpoint', required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions available to this '
                                                  'episode: none, a launch acquires no results', required=False),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information; '
                                            'yielding alone is false', required=False),
    SUPPORT_SOURCE: Field('record_refs', SUPPORT_MEANING, required=False),
    FACT_SOURCE: Field('list', application_fact_sources()[FACT_SOURCE]['meaning'], required=False),
})


def facts(summary):
    """The facts a parent may select: the handoff references and whether one was received, the AppService receipts
    and the application outcomes the child reported; a launch has no results."""
    return {'execution_handoff_refs': sorted(summary['handoff_refs']),
            SUPPORT_SOURCE: sorted(summary['support_refs']),
            'execution_result_refs': [], 'execution_completed': bool(summary['handoff_resources']),
            FACT_SOURCE: list(summary['outcomes'])}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    new = len(set(summary['handoff_resources']) - set(summary['received_handoff_resources']))
    established = recorded['execution_completed']
    result = {'credit': completion['credit'],
              'finding': {'handoff_established': established, 'handoff_resources': list(summary['handoff_resources']),
                          'new_handoff_count': new, 'launches_run': len(summary['launches']),
                          'launches': [{'slot': launch['slot'], 'resource_id': launch['resource_id'],
                                        'completed': launch['completed'], 'handoff_refs': launch['handoff_refs']}
                                       for launch in summary['launches']],
                          'qualification': ('a usable original handoff was received from a launch child'
                                            if established else
                                            'no usable original handoff was received; a missing reply does not '
                                            'establish that no job was created')}}
    for name in selection:
        result[name] = recorded[name]
    return result
