"""What the page takes from a leaf's return, with the slot that produced it: controlled data only. The leaf's credit (its
productivity), the controlled features of the sheets it saved with their references and the assessments it committed with
grading (``finding``), and the fields this episode selected in ``msg_to_child``: the relevant lead count and lead sources
and the cell rows of the requested A108 components (references only). The three leaves return the same form."""
from .msg_to_child import LEADS, selected_fields

RENAMED = {LEADS: 'leads'}


def read_from_child(slot, result, summary, records):
    requested = summary['literature_assignment']
    report = {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
    for name in selected_fields(slot, requested):
        report[RENAMED.get(name, name)] = result[name]
    return report
