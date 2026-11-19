"""What the parent takes from a child's return: the child's credit and its controlled finding (the two choices, the
reading count, the extent covered and the sources read), with the slot that produced them (carried from the old
``from_child_*.py``, which only collected the references of the child's typed form). No model text is returned by a
child; a child's credit is information for the summary and is never added to this episode's credit."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
