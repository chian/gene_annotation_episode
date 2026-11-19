"""What the parent takes from a child's return, with the slot that produced it: controlled data only. The child's
credit (its productivity: the parent's decision to commission another reading rests on it), the controlled features
of the child's sheets with their references and the assessments it committed with grading (``finding``), and the
fields this episode selected in ``msg_to_child``: the relevant lead count and lead sources, the screening counts, the
cell rows of the requested A108 components (references only). The three children return the same form."""
from .msg_to_child import AGGREGATION_CELLS, GRADING_CELLS, LEADS, SCREENING, selected_fields
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

RENAMED = {LEADS: 'leads', SCREENING: 'screening'}


def read_from_child(slot, result, summary, records):
    requested = summary['literature_assignment']
    parent = {REQUESTED_GRADING: requested.get(REQUESTED_GRADING, []),
              REQUESTED_AGGREGATION: requested.get(REQUESTED_AGGREGATION, [])}
    report = {'credit': result['credit'], 'finding': result['finding']}
    for name in selected_fields(slot, summary['task'], parent):
        report[RENAMED.get(name, name)] = result[name]
    return report
