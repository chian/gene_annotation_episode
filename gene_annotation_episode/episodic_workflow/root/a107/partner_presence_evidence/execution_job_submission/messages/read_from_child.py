"""What the parent takes from a launch child's return, all of it controlled data: the handoff records it returned
(record references, now in this Episode's custody), whether its handoff exists, its credit (the signal of whether
the launch was productive) and its finding (counts). All three children declare ``execution_handoff_refs`` and
``execution_completed`` selectable and ``msg_to_child`` selects both."""


def read_from_child(slot, result, summary, records):
    return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
            'credit': result['credit'], 'finding': result['finding']}
