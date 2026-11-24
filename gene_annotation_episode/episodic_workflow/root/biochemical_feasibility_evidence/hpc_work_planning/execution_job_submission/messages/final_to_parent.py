"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (which
requests were commissioned, which resources have a usable handoff, how many are new). Selectable: the handoff
records the route children returned in custody (``execution_handoff_refs``), whether a usable handoff is returnable
(``execution_completed``) and the result sources, which are empty because a launch acquires no results
(``execution_result_refs``, ``execution_file_source_refs``, ``execution_file_capture_outcomes``)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'commissioned': Field('list', 'The route children commissioned, in order: resource_id, slot, the handoff '
                                  'references each returned and whether its endpoint was validated'),
    'handed_off_resource_ids': Field('list', 'The resource_ids with a usable handoff, including those held at '
                                             'the start'),
    'new_handoff_count': Field('integer', 'The usable handoffs this Episode obtained beyond those held at the '
                                          'start'),
    'completed': Field('boolean', 'Whether any usable handoff is returnable'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the launch commissioned and which handoffs it obtained', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The records of the usable handoffs to the actual jobs',
                                    required=False),
    'execution_result_refs': Field('record_refs', 'Result records of the jobs (none: a launch acquires no '
                                   'results)', required=False),
    'execution_file_source_refs': Field('record_refs', 'Source records of captured files (none for a launch)',
                                        required=False),
    'execution_file_capture_outcomes': Field('list', 'Outcomes of file captures (none for a launch)',
                                             required=False),
    'execution_completed': Field('boolean', 'Whether a usable handoff is returnable', required=False),
})


def facts(summary):
    """The facts a parent may select; a launch acquires no results, so every result source is empty."""
    return {'execution_handoff_refs': list(summary['handoff_refs']), 'execution_result_refs': [],
            'execution_file_source_refs': [], 'execution_file_capture_outcomes': [],
            'execution_completed': bool(summary['handoff_refs'])}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    initial = set(summary['initial_handed_off_resource_ids'])
    result = {'credit': completion['credit'],
              'finding': {'commissioned': summary['commissioned'],
                          'handed_off_resource_ids': list(summary['handed_off_resource_ids']),
                          'new_handoff_count': len(set(summary['handed_off_resource_ids']) - initial),
                          'completed': recorded['execution_completed']}}
    for name in selection:
        result[name] = recorded[name]
    return result
