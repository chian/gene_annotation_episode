"""The return. The old episode returned the parent's requested form filled from the model's report update and had
no facts of its own (``fact_sources`` and ``facts`` were empty). The new return declares what it can return:
``credit`` (the system hands it in ``completion``) and ``finding``, the interpretation of the selected table or
sheet that the model wrote with the ``report`` tool, reading by reading (new field: the old form was written by
the parent).

The old ``validate_report`` body is ``validate_report`` below: it is this episode's check of its own report."""
from method_loop import Field, RecordForm

READING_FORM = RecordForm({
    'source_ref': Field('text', 'The source the reading is in; a source this episode holds'),
    'location': Field('text', 'Where in the source the reading is: the sheet, matching rows, header row, row numbers '
                      'and cell addresses, or the representation and byte window of an article XML table'),
    'statement': Field('text', 'What this reading itself says for the assigned question, in its own terms'),
    'qualification': Field('text', "The reading's own qualifications: the actual sequence or region and its aligned "
                           'homolog, headers, conditions, footnotes, and whether its applicability to the target is '
                           'resolved'),
})
FINDING_FORM = RecordForm({
    'written': Field('boolean', 'Whether the model wrote an interpretation before the episode ended'),
    'interpretation': Field('text', 'The interpretation of the selected table or sheet for the assigned question'),
    'readings': Field('list', 'One entry per reading the interpretation rests on', items=READING_FORM),
    'qualification': Field('text', 'What the interpretation leaves unresolved, including target correspondence'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The interpretation of the selected table or sheet', form=FINDING_FORM),
})

NOT_WRITTEN = {'written': False, 'interpretation': 'no interpretation was written before the episode ended',
               'readings': [], 'qualification': 'the table was not interpreted'}


def validate_report(summary, finding):
    """The old ``validate_report`` body, over the summary: the assignment still agrees with itself, the report is a
    valid form of its own, and every reference in it is one this episode holds."""
    page = summary['literature_assignment']['page']
    selection = summary['literature_assignment']['selection']
    if selection['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if 'representation' in selection and selection['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    FINDING_FORM.admit(finding, 'finding')
    for reference, held in summary['report_source_held'].items():
        if not held:
            raise ValueError('literature_reference_unavailable:' + reference)


def final_to_parent(summary, completion, selection):
    report = summary['report']
    finding = NOT_WRITTEN if report is None else {'written': True, **report}
    validate_report(summary, finding)
    return {'credit': completion['credit'], 'finding': finding}
