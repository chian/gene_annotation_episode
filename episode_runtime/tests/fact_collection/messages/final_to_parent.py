"""The report. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
facts its extractions returned and how many fact records it confirmed); also the confirmed fact records, returned
in custody."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'facts': Field('list', 'The extracted facts'),
    'confirmed': Field('integer', 'How many fact records were confirmed'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the collection found', form=FINDING_FORM),
    'fact_refs': Field('record_refs', 'The confirmed fact records'),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'],
            'finding': {'facts': summary['facts'], 'confirmed': len(summary['confirmed'])},
            'fact_refs': summary['confirmed']}
