"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
resources were commissioned, how many usable handoffs are recorded and the availability each resource was last read
with).

Selectable: ``execution_handoff`` (the latest usable check when exactly one physical execution is known, ``{}`` for
zero or several), ``execution_handoffs`` (the usable check of each distinct execution identity, in identity order),
``adapter_facts`` (the resource adapters' own recorded facts, keyed by their names) and ``execution_handoff_refs``
(the handoff records the children returned, in custody)."""
from method_loop import Field, RecordForm

COMMISSION_FORM = RecordForm({
    'slot': Field('text', 'The resource child that was commissioned: launch_api, launch_hpc or launch_local'),
    'resource_id': Field('text', 'The resource it was commissioned on'),
    'usable_handoffs': Field('integer', 'The usable handoffs the child returned'),
    'credit': Field('number', "The child's own credit"),
})
AVAILABILITY_FORM = RecordForm({
    'resource_id': Field('text', 'The declared resource'),
    'kind': Field('text', 'api, local or hpc'),
    'availability': Field('text', 'available, unavailable, authentication_required or unknown, as last read'),
})
FINDING_FORM = RecordForm({
    'commissions': Field('list', 'Each commissioned resource child in order and what it returned',
                         items=COMMISSION_FORM),
    'usable_handoffs': Field('integer', 'The distinct usable execution handoffs recorded'),
    'unavailable_checks': Field('integer', 'The handoff checks that found the execution unavailable'),
    'resource_availability': Field('list', 'The declared resources and their availability as the capabilities '
                                   'were last read; empty when they were never read', items=AVAILABILITY_FORM),
    'qualification': Field('text', 'What the recorded handoffs do and do not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the work on the resources established', form=FINDING_FORM),
    'execution_handoff': Field('record', 'The latest original usable received or own selected check when exactly '
                               'one physical execution is known; {} for zero or several identities. No new '
                               'receiving check occurs at closure.', required=False),
    'execution_handoffs': Field('list', 'For each distinct registry and execution handle, the available usable '
                                'check with latest original checked_at, in identity order. This records available '
                                'facts without selecting a resource or rechecking it.', required=False),
    'adapter_facts': Field('record', "The resource adapters' own recorded fact sources, by their names",
                           required=False),
    'execution_handoff_refs': Field('record_refs', 'The handoff records the resource children returned, in '
                                    'custody', required=False),
})


def facts(summary):
    """The facts a parent may select; ``execution_handoff`` is ``{}`` when zero or several executions are known."""
    return {'execution_handoff': summary['execution_handoff'] if summary['execution_handoff'] is not None else {},
            'execution_handoffs': list(summary['execution_handoffs']),
            'adapter_facts': dict(summary['adapter_facts']),
            'execution_handoff_refs': list(summary['handoff_refs'])}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    count = len(summary['execution_handoffs'])
    finding = {'commissions': [{'slot': item['slot'], 'resource_id': item['resource_id'],
                                'usable_handoffs': item['handoff_count'], 'credit': item['credit']}
                               for item in summary['commissions']],
               'usable_handoffs': count, 'unavailable_checks': summary['unavailable_checks'],
               'resource_availability': [{'resource_id': item['resource_id'], 'kind': item['kind'],
                                          'availability': item['availability']}
                                         for item in summary['capabilities'] or ()],
               'qualification': ('Each handoff is the latest usable check of one execution identity as the '
                                 'resource adapter returned it; no check is made at closure.' if count else
                                 'No usable execution handoff is recorded; the resource availability is as last '
                                 'read.')}
    result = {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
    return result
