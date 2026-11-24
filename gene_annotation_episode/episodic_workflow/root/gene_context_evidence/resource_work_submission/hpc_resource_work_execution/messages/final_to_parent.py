"""The return. Always returned: the Episode's credit (handed in ``completion``) and the finding (which resource, whether
it was available, whether a usable execution handoff is recorded, and what the recorded facts establish). A parent
selects the facts it wants: ``execution_handoff`` and ``execution_handoffs`` (the latest usable handoff when exactly
one physical execution is known, and every distinct handoff), ``execution_handoff_refs`` (the handoff records, in
custody) and ``adapter_facts`` (the selected adapter's own recorded fact sources, by their names). The form has no
null: ``execution_handoff`` is ``{}`` when zero or several physical executions are known."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The selected HPC resource'),
    'kind': Field('text', 'The resource kind: hpc'),
    'availability': Field('text', 'The actual availability recorded for the resource: available, unavailable, '
                          'authentication_required or unknown'),
    'usable_handoff': Field('boolean', 'Whether exactly one usable execution handoff is recorded'),
    'qualification': Field('text', 'What the recorded facts establish about the execution handoff'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the work on the selected HPC resource established', form=FINDING_FORM),
    'execution_handoff': Field('record', 'The latest original usable received or own selected check when exactly '
                               'one physical execution is known; empty for zero or several identities. No new '
                               'receiving check occurs at closure.', required=False),
    'execution_handoffs': Field('list', 'For each distinct registry and execution handle, the available usable '
                                'check with latest original checked_at, in identity order. This records available '
                                'facts without selecting a resource or rechecking it.', required=False),
    'adapter_facts': Field('record', "The selected adapter's own recorded fact sources, by their names",
                           required=False),
    'execution_handoff_refs': Field('record_refs', 'The handoff records, in custody', required=False),
})


def handoff_facts(adapter_facts):
    """The handoffs de-duplicated by (capability_binding_ref, execution_handle) in identity
    order, the single handoff when exactly one identity is known, and the adapter's other facts."""
    values = {'execution_handoff': None, 'execution_handoffs': []}
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
    resource_id = summary['assignment']['resource_selection']['resource_id']
    capability = next(value for value in summary['capabilities'] if value['resource_id'] == resource_id)
    facts = handoff_facts(summary['facts'])
    usable = facts['execution_handoff'] is not None and facts['execution_handoff']['state'] == 'usable'
    finding = {'resource_id': resource_id, 'kind': capability['kind'], 'availability': capability['availability'],
               'usable_handoff': usable,
               'qualification': ('exactly one usable execution handoff is recorded' if usable else
                                 'no single usable execution handoff is recorded; %d distinct handoff identities '
                                 'are known' % len(facts['execution_handoffs']))}
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
