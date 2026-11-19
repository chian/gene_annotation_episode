"""What this parent takes from a literature child's admitted return: its credit, the controlled features of the A106
sheets saved below it (its finding: G1 and G2 features with the sheets' references) and the selected answers as
counts and references (the relevant lead sources, which count toward this episode's leads credit through
``credit.lead_dispositions``, and the screening counts). No text of the child reaches this episode's model. The old
receipt bookkeeping (``EpisodeReturnRecords``, ``workflow.receipts``, population-cell receipts) is the system's
custody and is not carried."""

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'


def read_from_child(slot, result, summary, records):
    report = {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
    if LEADS in result:
        report['lead_source_refs'] = result[LEADS]['lead_source_refs']
    if SCREENING in result:
        report['screening'] = result[SCREENING]
    return report
