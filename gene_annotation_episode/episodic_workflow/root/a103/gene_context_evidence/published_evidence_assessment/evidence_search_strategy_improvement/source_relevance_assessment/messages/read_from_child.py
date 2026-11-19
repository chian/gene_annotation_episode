"""What the parent takes from the child's return: its credit and its controlled finding about the examined source
(the two choices, the reading count, the extent covered, the sources read; carried from the old
``from_child_source_evidence_examination.py``, which only collected the references of the child's typed form). No
model text is returned by the child."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
