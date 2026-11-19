"""What the parent takes from a resource child's admitted return (carried from the three identical
``from_child_<role>.py``). The old receivers recorded admission references, progress-provider receipts, timing
receipts and tool attributions: old-runner machinery (the system receipts the records a child returns). What is
kept is what the parent's report and credit read: the child's handoff references, whether it verified completion
and its own finding. All three children return the selected fields under the same names."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'handoff_refs': list(result['execution_handoff_refs']),
            'completed': result['execution_completed'], 'finding': result['finding']}
