"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding and the
records of the handoff checks, held in custody (``handoff_refs``: the reply records the tools wrote). Selectable:
``execution_handoff`` (the latest usable check when exactly one physical execution is known, the empty record
otherwise) and ``execution_handoffs``."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The selected HPC resource'),
    'kind': Field('text', 'The kind of the selected resource'),
    'availability': Field('text', 'The availability of the resource as last read (available, unavailable, '
                          'authentication_required, unknown), or not_read when no capability read happened'),
    'usable_handoffs': Field('integer', 'The distinct usable execution handoffs found'),
    'unavailable_checks': Field('integer', 'The handoff checks that found the execution unavailable'),
    'tool_calls': Field('integer', 'The resource operations run'),
    'failed_calls': Field('integer', 'The resource operations that did not complete'),
    'qualification': Field('text', 'What the handoffs do and do not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the work on the selected resource found', form=FINDING_FORM),
    'handoff_refs': Field('record_refs', 'The records of the handoff checks'),
    'execution_handoff': Field('record', 'The latest usable check when exactly one physical execution is known; '
                               '{} for zero or several identities. No new check occurs at closure', required=False),
    'execution_handoffs': Field('list', 'For each distinct registry and execution handle, the usable check with '
                                'the latest checked_at, in identity order', required=False),
})


def final_to_parent(summary, completion, selection):
    count = len(summary['execution_handoffs'])
    qualification = ('Each handoff is the latest usable check of one execution identity as the resource adapter '
                     'returned it; no check is made at closure.' if count else
                     'No usable execution handoff was found; the resource availability is as last read.')
    result = {'credit': completion['credit'],
              'finding': {'resource_id': summary['assignment']['resource_selection']['resource_id'], 'kind': 'hpc',
                          'availability': summary['availability'], 'usable_handoffs': count,
                          'unavailable_checks': summary['unavailable_checks'], 'tool_calls': len(summary['calls']),
                          'failed_calls': summary['failed_calls'], 'qualification': qualification},
              'handoff_refs': summary['handoff_refs']}
    if 'execution_handoff' in selection:
        result['execution_handoff'] = summary['execution_handoff'] or {}
    if 'execution_handoffs' in selection:
        result['execution_handoffs'] = summary['execution_handoffs']
    return result
