"""What this parent takes from a leaf's admitted return: its credit, the controlled features of the A106 sheets it saved
(its finding: G1 and G2 features with the sheets' references) and the relevant lead sources (which count toward this
episode's credit through ``credit.lead_dispositions``). No text of the child reaches this episode's model."""

LEADS = 'literature_source_lead_dispositions'


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding'],
            'lead_source_refs': result[LEADS]['lead_source_refs']}
