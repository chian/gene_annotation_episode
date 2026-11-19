"""What this episode takes from a ``literature_page`` child's return: its credit and the structure sheets of its finding (always returned) and
the selected answers as counts and references. The old receivers
(``from_child_source_evidence_examination.receive_report`` and ``received_evidence.py``) admitted the child form and
took its leads into ``lead_dispositions``; the system admits the result, and the relevant lead sources it names ride
in the report so that ``internal_summary`` counts them with the own leads in unit order. No text of the child
reaches this episode's model."""

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'


def read_from_child(slot, result, summary, records):
    if slot != 'literature_page':
        raise KeyError(slot)
    report = {'slot': slot, 'credit': result['credit'], 'structure_sheets': result['finding']['structure_sheets']}
    if LEADS in result:
        report['lead_source_refs'] = result[LEADS]['lead_source_refs']
    if SCREENING in result:
        report['screening'] = result[SCREENING]
    return report
