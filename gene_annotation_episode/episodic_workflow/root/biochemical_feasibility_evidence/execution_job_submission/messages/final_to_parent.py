"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (which
resources got a usable handoff and which launches ran) and the handoff records the launch children returned, in
custody, so the job's identity is preserved across a scientific return. The other facts a parent may select are
``execution_completed``, ``execution_result_refs``, ``execution_file_source_refs`` and
``execution_file_capture_outcomes``; a launch acquires no results, so the last three are empty."""
from method_loop import Field, RecordForm

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
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which resources got a usable handoff and which launches ran', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff sources received from the launch '
                                                   'children: the job identity, preserved across a return'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual verified endpoint information (a '
                                            'usable handoff was received); yielding alone is false',
                                 required=False),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions: none, a launch '
                                                  'acquires no results', required=False),
    'execution_file_source_refs': Field('record_refs', 'Source references of retained local file streams: none, a '
                                                       'launch acquires no results', required=False),
    'execution_file_capture_outcomes': Field('list', 'Recorded selected-file availability: always empty here',
                                             required=False),
})


def _facts(summary):
    """The facts a parent may select: the handoff references and whether one was received; a launch acquires no
    results, so every result source is empty."""
    return {'execution_handoff_refs': sorted(summary['handoff_refs']),
            'execution_completed': bool(summary['handoff_resources']),
            'execution_result_refs': [], 'execution_file_source_refs': [], 'execution_file_capture_outcomes': []}


def final_to_parent(summary, completion, selection):
    facts = _facts(summary)
    new = len(set(summary['handoff_resources']) - set(summary['received_handoff_resources']))
    result = {'credit': completion['credit'],
              'finding': {'handoff_established': facts['execution_completed'],
                          'handoff_resources': list(summary['handoff_resources']), 'new_handoff_count': new,
                          'launches_run': len(summary['launches']),
                          'launches': [{'slot': launch['slot'], 'resource_id': launch['resource_id'],
                                        'completed': launch['completed'], 'handoff_refs': launch['handoff_refs']}
                                       for launch in summary['launches']]},
              'execution_handoff_refs': facts['execution_handoff_refs']}
    for name in selection:
        result[name] = facts[name]
    return result
