"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
state of the handoff whose results are acquired). The facts come only from the assigned adapter (the one the handoff
names).

Selectable: ``execution_handoff`` (a list of one handoff when exactly one physical execution is known, otherwise
empty), ``execution_handoffs`` (the usable check of each distinct execution identity, in identity order),
``adapter_facts`` (the adapter's other recorded facts, keyed by their names) and ``interpretation`` (the latest
interpretation the model recorded with the ``report`` tool; ``{}`` when none was recorded)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The resource the handoff names'),
    'kind': Field('text', 'The kind of that resource'),
    'handoff_state': Field('text', 'usable when a recorded handoff is usable, unavailable when every recorded '
                                   'handoff is unavailable, none when no handoff was recorded'),
    'handoff_count': Field('integer', 'The number of distinct recorded execution identities'),
    'failure_codes': Field('list', 'The failure codes the recorded handoffs and the last failed unit carry'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the handoff whose results are acquired', form=FINDING_FORM),
    'execution_handoff': Field('list', 'The latest original usable received or own selected check when exactly one '
                                       'physical execution is known; empty for zero or several identities. No new '
                                       'receiving check occurs at closure.', required=False),
    'execution_handoffs': Field('list', 'For each distinct registry and execution handle, the available usable '
                                        'check with latest original checked_at, in identity order. This records '
                                        'available facts without selecting a resource or rechecking it.',
                                required=False),
    'adapter_facts': Field('record', "The assigned adapter's own declared fact sources, by the adapter's names",
                           required=False),
    'interpretation': Field('record', 'The latest interpretation the episode recorded for the parent', required=False),
})


def facts_from(adapter_facts):
    """The handoffs de-duplicated by identity and in identity order, the single handoff when exactly one identity is known, and the adapter's other facts."""
    values = {'execution_handoff': None, 'execution_handoffs': []}
    for key, value in ({} if adapter_facts is None else adapter_facts).items():
        if key == 'execution_handoffs':
            values[key].extend(value)
            continue
        if key == 'execution_handoff':
            continue
        if value is not None:
            values[key] = value
        else:
            values.setdefault(key, None)
    identities = {(item['resource_selection']['capability_binding_ref'], item['execution_handle']): item
                  for item in values['execution_handoffs']}
    values['execution_handoffs'] = [identities[key] for key in sorted(identities)]
    values['execution_handoff'] = values['execution_handoffs'][0] if len(identities) == 1 else None
    return values


def final_to_parent(summary, completion, selection):
    facts = facts_from(summary['facts'])
    handoffs = facts['execution_handoffs']
    selected = summary['assignment']['handoff']['resource_selection']
    codes = [item['failure']['code'] for item in handoffs if item['failure'] is not None]
    last = summary['last_outcome']
    if last is not None and last['status'] not in ('completed', 'partial') and last.get('feedback'):
        codes.append(last['feedback'].get('code') or last['feedback'].get('category', 'work_failed'))
    state = 'none' if not handoffs else 'usable' if any(item['state'] == 'usable' for item in handoffs) \
        else 'unavailable'
    result = {'credit': completion['credit'],
              'finding': {'resource_id': selected['resource_id'], 'kind': selected['kind'],
                          'handoff_state': state, 'handoff_count': len(handoffs), 'failure_codes': codes}}
    if 'execution_handoff' in selection:
        result['execution_handoff'] = [] if facts['execution_handoff'] is None else [facts['execution_handoff']]
    if 'execution_handoffs' in selection:
        result['execution_handoffs'] = handoffs
    if 'adapter_facts' in selection:
        result['adapter_facts'] = {key: value for key, value in facts.items()
                                   if key not in ('execution_handoff', 'execution_handoffs')}
    if 'interpretation' in selection:
        result['interpretation'] = summary['interpretation'] or {}
    return result
