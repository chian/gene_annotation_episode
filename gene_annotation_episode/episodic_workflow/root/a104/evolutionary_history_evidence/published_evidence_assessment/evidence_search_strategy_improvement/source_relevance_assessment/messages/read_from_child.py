"""What this episode takes from a child's return: the child's credit and its controlled finding (the features of the
sheets and assessments it saved, with the references that let this episode read them), and the controlled screening
answer and relevant source leads when the commission selected them. No text of the child's model is taken: the
child returns none."""

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'


def read_from_child(slot, result, summary, records):
    read = {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
    for name in (LEADS, SCREENING):
        if name in result:
            read[name] = result[name]
    return read
