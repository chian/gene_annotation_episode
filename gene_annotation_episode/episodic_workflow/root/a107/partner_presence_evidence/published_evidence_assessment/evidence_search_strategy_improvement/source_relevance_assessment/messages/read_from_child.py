"""What this episode takes from a child's return: the child's credit and the controlled features of the partner
sheets it returned (with the sheets' references), and the agreement counts. Old ``from_child_*.py``: admitting the
child's typed form, recording its record references as received and progress notifications; all of it old receipts
and journal mechanics, which are the system's custody now."""


def read_from_child(slot, result, summary, records):
    finding = result['finding']
    return {'slot': slot, 'credit': result['credit'], 'partner_sheets': finding['partner_sheets'],
            'matched_sheet_count': finding['matched_sheet_count'],
            'matched_loss_sheet_count': finding['matched_loss_sheet_count'],
            'distinct_experiment_count': finding['distinct_experiment_count']}
