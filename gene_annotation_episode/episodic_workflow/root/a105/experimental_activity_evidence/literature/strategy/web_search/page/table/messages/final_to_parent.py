"""The return: controlled data only. Always returned: the Episode's credit (the system hands it in ``completion``) and the
finding, the counts of the fields of the held records of the table (how many they state, how many of those are newly
stated, how many the form asked). Selectable: the references of the leaf records that stand, one per experiment ref
(``internal_summary``: re-extractions of the table are superseded). No text."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'stated': Field('integer', 'How many fields the held records state, record by record'),
    'newly_stated': Field('integer', 'How many distinct fields the held records state'),
    'asked': Field('integer', 'How many fields the form asked'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The counts of the fields of the held records', form=FINDING_FORM),
    'record_refs': Field('record_refs', 'The extraction records of the table that stand, one per experiment',
                         required=False),
})


def final_to_parent(summary, completion, selection):
    result = {'credit': completion['credit'], 'finding': summary['counts']}
    if 'record_refs' in selection:
        result['record_refs'] = summary['record_refs']
    return result
