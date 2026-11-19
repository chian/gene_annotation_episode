"""The return. The old episode returned the parent's requested form filled from the model's report update and had
no facts of its own (``fact_sources`` and ``facts`` were empty). The new return declares what it can return:
``credit`` (the system hands it in ``completion``) and ``finding``, the interpretation the model wrote with the
``report`` tool, span by span (new field: the old form was written by the parent)."""
from method_loop import Field, RecordForm

PASSAGE_FORM = RecordForm({
    'source_ref': Field('text', 'The source the passage is in; a source this episode holds'),
    'offset': Field('integer', 'First byte of the passage in the representation read'),
    'limit': Field('integer', 'Bytes of the passage'),
    'statement': Field('text', 'What this passage itself says for the assigned question, in its own terms'),
    'qualification': Field('text', "The passage's own qualifications: the actual sequence or region and its aligned "
                           'homolog, coverage, conditions, and whether its applicability to the target is resolved'),
})
FINDING_FORM = RecordForm({
    'written': Field('boolean', 'Whether the model wrote an interpretation before the episode ended'),
    'interpretation': Field('text', 'The interpretation of the supplied passages for the assigned question; '
                            'separate spans stay separate'),
    'passages': Field('list', 'One entry per passage the interpretation rests on', items=PASSAGE_FORM),
    'qualification': Field('text', 'What the interpretation leaves unresolved, including target correspondence'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The interpretation of the supplied passages', form=FINDING_FORM),
})

NOT_WRITTEN = {'written': False, 'interpretation': 'no interpretation was written before the episode ended',
               'passages': [], 'qualification': 'the supplied passages were not interpreted'}


def validate_report(summary, finding):
    """The old ``validate_report`` body, over the summary: the assignment still agrees with itself, the report is
    a valid form of its own, and every reference in it is one this episode holds."""
    page = summary['literature_assignment']['page']
    for window in summary['literature_assignment']['selection']['spans']:
        if window['source_ref'] != page['source_ref']:
            raise ValueError('literature_reading_source_mismatch')
        if window['representation'] != page['representation']:
            raise ValueError('literature_reading_representation_mismatch')
    FINDING_FORM.admit(finding, 'finding')   # the report is a valid form (A101's validate_form admits no free text)
    for reference, held in summary['report_source_held'].items():
        if not held:
            raise ValueError('literature_reference_unavailable:' + reference)


def final_to_parent(summary, completion, selection):
    report = summary['report']
    finding = NOT_WRITTEN if report is None else {'written': True, **report}
    validate_report(summary, finding)
    return {'credit': completion['credit'], 'finding': finding}
