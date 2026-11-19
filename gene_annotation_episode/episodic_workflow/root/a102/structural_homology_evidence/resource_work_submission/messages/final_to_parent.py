"""The return. Always returned: the Episode's credit (handed in ``completion``) and the finding (which resource
children were commissioned, what each established, how many usable execution handoffs are recorded). Selectable:
``execution_handoff`` (the one handoff when exactly one physical execution is known, the empty record otherwise),
``execution_handoffs``, ``adapter_facts`` (the adapters' own recorded facts, by their names) and
``execution_handoff_refs`` (the handoff records, in custody)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'commissions': Field('list', 'For each resource child commissioned, in order: its slot, the finding it '
                         'returned and the usable handoffs it returned'),
    'usable_handoffs': Field('integer', 'The distinct execution handoff identities that are usable'),
    'identities': Field('integer', 'The distinct execution handoff identities known (capability_binding_ref, '
                        'execution_handle)'),
    'qualification': Field('text', 'What the recorded facts establish about the execution handoff'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the work on the resource routes established', form=FINDING_FORM),
    'execution_handoff': Field('record', 'The latest original usable received or own selected check when exactly '
                               'one physical execution is known; empty for zero or several identities. No new '
                               'receiving check occurs at closure.', required=False),
    'execution_handoffs': Field('list', 'For each distinct registry and execution handle, the available usable '
                                'check with latest original checked_at, in identity order. This records available '
                                'facts without selecting a resource or rechecking it.', required=False),
    'adapter_facts': Field('record', "The configured adapters' own recorded fact sources, by their names",
                           required=False),
    'execution_handoff_refs': Field('record_refs', 'The handoff records, in custody', required=False),
})


def handoff_facts(adapter_facts, handoffs):
    """The handoffs (every adapter's and every child's) de-duplicated by
    (capability_binding_ref, execution_handle) in identity order, the single handoff when exactly one identity is
    known, and the adapters' other facts."""
    values = {'execution_handoff': None, 'execution_handoffs': list(handoffs)}
    for key, value in adapter_facts.items():
        if key == 'execution_handoffs':
            values[key].extend(value)
        elif key == 'execution_handoff':
            continue
        elif value is not None:
            values[key] = value
        else:
            values.setdefault(key, None)
    identities = {(item['resource_selection']['capability_binding_ref'], item['execution_handle']): item
                  for item in values['execution_handoffs']}
    values['execution_handoffs'] = [identities[key] for key in sorted(identities)]
    values['execution_handoff'] = values['execution_handoffs'][0] if len(identities) == 1 else None
    return values


def final_to_parent(summary, completion, selection):
    facts = handoff_facts(summary['adapter_facts'], summary['child_handoffs'])
    usable = [item for item in facts['execution_handoffs'] if item['state'] == 'usable']
    finding = {'commissions': summary['commissions'], 'usable_handoffs': len(usable),
               'identities': len(facts['execution_handoffs']),
               'qualification': ('exactly one usable execution handoff is recorded' if len(usable) == 1 else
                                 'no single usable execution handoff is recorded; %d usable of %d distinct '
                                 'handoff identities are known' % (len(usable), len(facts['execution_handoffs'])))}
    result = {'credit': completion['credit'], 'finding': finding}
    if 'execution_handoff' in selection:
        result['execution_handoff'] = facts['execution_handoff'] if facts['execution_handoff'] is not None else {}
    if 'execution_handoffs' in selection:
        result['execution_handoffs'] = facts['execution_handoffs']
    if 'adapter_facts' in selection:
        result['adapter_facts'] = {name: value for name, value in facts.items()
                                   if name not in ('execution_handoff', 'execution_handoffs')}
    if 'execution_handoff_refs' in selection:
        result['execution_handoff_refs'] = summary['handoff_refs']
    return result
