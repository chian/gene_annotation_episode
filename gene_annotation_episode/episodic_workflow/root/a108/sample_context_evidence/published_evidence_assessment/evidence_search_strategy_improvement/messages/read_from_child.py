"""What the parent takes from its child's return: controlled data only. The child's credit (its productivity: the
decision to commission it again rests on it and its trend), the controlled features of the sheets the child and its
descendants saved, with their references, and the assessments committed with grading (``finding``), and the fields
this episode selected in ``msg_to_child``: the relevant lead count and lead sources, the screening counts and the cell
rows of the requested A108 components (references only). No text the child's model wrote reaches this episode."""
from .msg_to_child import LEADS, SCREENING, selected_fields

RENAMED = {LEADS: 'leads', SCREENING: 'screening'}


def read_from_child(slot, result, summary, records):
    report = {'credit': result['credit'], 'finding': result['finding']}
    for name in selected_fields(summary['task'], summary['literature_assignment']):
        report[RENAMED.get(name, name)] = result[name]
    return report
