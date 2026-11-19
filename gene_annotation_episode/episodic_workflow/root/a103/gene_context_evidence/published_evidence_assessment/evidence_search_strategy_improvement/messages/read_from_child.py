"""What the parent takes from the child's return: its credit and its controlled finding (the counts of judged,
meriting and established sources and the sources that merit examination; carried from the old
``from_child_source_relevance_assessment.py``, which only collected the references of the child's typed form). No
model text is returned by the child."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
