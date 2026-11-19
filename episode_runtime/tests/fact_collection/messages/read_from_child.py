"""What the parent takes from the extraction's return."""


def read_from_child(slot, result, summary, records):
    return {'fact': result['fact']}
