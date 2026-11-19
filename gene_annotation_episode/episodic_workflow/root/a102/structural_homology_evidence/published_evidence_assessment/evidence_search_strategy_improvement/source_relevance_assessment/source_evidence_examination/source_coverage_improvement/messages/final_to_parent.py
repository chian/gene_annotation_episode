"""The return. The old episode returned the parent's requested form filled from the model's report update and the
facts of ``to_parent.py`` (``facts``: ``SCREENING`` answers for a screening task, ``LEADS`` dispositions for a
``verified_source_leads`` task, the structure cells with ``structure_population``). The new return declares what it
can return: ``credit`` (the system hands it in ``completion``) and ``finding``, the interpretation the model wrote
with the ``report`` tool, passage by passage (new field: the old form was written by the parent), and the three fact
sources as selectable fields under their old names."""
from method_loop import Field, RecordForm

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
STRUCTURE = 'literature_structure_cells'

PASSAGE_FORM = RecordForm({
    'source_ref': Field('text', 'The source the passage is in; a source this episode holds'),
    'offset': Field('integer', 'First byte of the passage in the representation read'),
    'limit': Field('integer', 'Bytes of the passage'),
    'statement': Field('text', 'What this passage itself says for the assigned question, in its own terms'),
    'qualification': Field('text', "The passage's own qualifications: subject, conditions, representation and "
                           'whether its applicability to the target is resolved'),
})
FINDING_FORM = RecordForm({
    'written': Field('boolean', 'Whether the model wrote an interpretation before the episode ended'),
    'interpretation': Field('text', 'The interpretation of the source for the assigned question; '
                            'what was read in document order stays attributed to its own byte anchors'),
    'passages': Field('list', 'One entry per passage the interpretation rests on', items=PASSAGE_FORM),
    'qualification': Field('text', 'What the interpretation leaves unresolved, including target correspondence'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The interpretation of the examined source', form=FINDING_FORM),
    SCREENING: Field('list', 'The screening answer: the commissioned spans examined with no applicable evidence '
                     '(empty unless the task is a screening answer that the own declarations cover)',
                     required=False),
    LEADS: Field('list', 'The latest validated source lead per source for the commissioned question (empty unless '
                 'the task is verified_source_leads)', required=False),
    STRUCTURE: Field('list', 'The structure cells of the requested components (the structure population route is '
                     'not built: selecting this raises)', required=False),
})

NOT_WRITTEN = {'written': False, 'interpretation': 'no interpretation was written before the episode ended',
               'passages': [], 'qualification': 'the examined source was not interpreted'}


def validate_report(summary, finding):
    """The old ``validate_report`` body, over the summary: the assignment still agrees with itself, the report is a
    valid form of its own, every reference in it is one this episode holds, and the facts agree with the saved
    work (the old ``validate_received_report`` compared answers to ``lead_dispositions`` / ``screening_answers``;
    here both are computed from the same summary the facts are built from)."""
    page = summary['literature_assignment']['page']
    window = summary['literature_assignment']['selection']
    if window['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if window['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    for reference, held in summary['report_source_held'].items():
        if not held:
            raise ValueError('literature_reference_unavailable:' + reference)
    # The old call validate_form(form, original_schema, resolver) is the axis's report-form validator. A102 has
    # none (carry_over_guide README 5 item 11): the call raises here.
    raise NotImplementedError('validate_form_not_built:A102')


def final_to_parent(summary, completion, selection):
    report = summary['report']
    finding = NOT_WRITTEN if report is None else {'written': True, **report}
    validate_report(summary, finding)
    result = {'credit': completion['credit'], 'finding': finding}
    if SCREENING in selection:
        result[SCREENING] = summary['screening_answers']
    if LEADS in selection:
        result[LEADS] = summary['source_lead_dispositions']
    if STRUCTURE in selection:
        raise NotImplementedError('literature_structure_population_not_built')
    return result
