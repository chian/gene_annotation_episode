"""What the parent takes from the child's return: its credit and its controlled finding (the relevant source
candidates and their counts; carried from the old ``from_child_evidence_search_strategy_improvement.py``, which
collected the references of the child's typed form). No model text is returned by the child."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
