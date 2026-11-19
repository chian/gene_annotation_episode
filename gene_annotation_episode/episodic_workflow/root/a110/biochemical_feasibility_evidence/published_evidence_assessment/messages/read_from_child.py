"""What this episode takes from a child's return: its credit and its controlled finding (the features code read from
the child's reaction sheets and committed assessments, with their record references, which the system receipted
when it admitted the return). Carried from the old ``from_child_*.py`` receivers, whose work was the old receipt
ledger, the reaction-cell receipts and the progress receipt (the system's custody now). No child prose exists to
take: the parent's next decision needs the child's
credit and those features only."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
