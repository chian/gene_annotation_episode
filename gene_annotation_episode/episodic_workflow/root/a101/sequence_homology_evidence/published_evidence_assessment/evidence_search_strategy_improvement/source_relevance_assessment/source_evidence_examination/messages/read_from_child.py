"""What this episode takes from a child's return: the child's credit and its typed finding, shown to the model
among the child reports. The old ``from_child_*.py`` recorded the record refs of the report as received (receipts:
the system's custody now) and added no validation, facts or evidence tokens of its own."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
