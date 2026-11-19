"""The return (the exemplar of a compressed return, ``TRANSFORM_GUIDE.md``). Always returned: credit (the system
hands it in ``completion``; it is the productivity signal and nothing restates it) and the minimal finding the
strategy investigation needs to decide how many more times to launch this episode and which sources to keep
(``INVESTIGATION_FINDING_FEATURES_a101.md`` section 10): the sources the latest controlled report marks as meriting
examination (record references) and the number of sources it assessed. No model-written text is returned. It
declares no selectable field."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'merits_examination_refs': Field('record_refs', 'The assessed sources that merit examination'),
    'assessed_source_count': Field('integer', 'The returned sources the latest report assessed'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Which returned sources merit examination', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    assessments = [] if summary['report'] is None else summary['report']['assessments']
    merits = list(dict.fromkeys(row['source_ref'] for row in assessments if row['merits_examination']))
    return {'credit': completion['credit'],
            'finding': {'merits_examination_refs': merits,
                        'assessed_source_count': len({row['source_ref'] for row in assessments})}}
