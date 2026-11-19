"""The return. The old episode returned the parent's requested form filled from the model's report update and had
no facts of its own (``fact_sources`` and ``facts`` were empty). The new return declares what it can return:
``credit`` (the system hands it in ``completion``) and ``finding``, the typed A103 finding of the selected table or
sheet that the model wrote with the ``report`` tool: the actual source claim, the actual source subject and its
qualification (including unresolved target correspondence), reading by reading (new field: the old form was
written by the parent).

The old ``validate_report`` body is ``validate_report`` below: it is this episode's check of its own report."""
from method_loop import Field, RecordForm

READING_FORM = RecordForm({
    'source_ref': Field('text', 'The source the reading is in; a source this episode holds'),
    'location': Field('text', 'Where in the source the reading is: the sheet, matching rows, header row, row numbers '
                      'and cell addresses, or the representation and byte window of an article XML table'),
    'statement': Field('text', 'What this reading itself says for the assigned question, in its own terms'),
    'qualification': Field('text', "The reading's own qualifications: headers, conditions, footnotes, and the "
                           'neighboring-gene identity, order, orientation, spacing, fusion and cooccurrence it states'),
})
FINDING_FORM = RecordForm({
    'source_claim': Field('text', 'What the examined table or sheet actually claims, in the source scope'),
    'source_subject': Field('text', 'The actual locus, genome, construct or entity the claim is about'),
    'qualification': Field('text', 'The conditions, limits and alternative explanations the source attaches'),
    'target_correspondence': Field('text', 'Whether the source subject corresponds to the target: established, '
                                   'unresolved or not applicable, and why'),
    'readings': Field('list', 'One entry per reading the finding rests on', items=READING_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The actual source claim, subject and qualification of the examined table or sheet',
                     form=FINDING_FORM),
})


def validate_report(summary, finding):
    """The old ``validate_report`` body, over the summary: the assignment still agrees with itself, the report is a
    valid form of its own, and every reference in it is one this episode holds."""
    page = summary['assignment']['page']
    selection = summary['assignment']['selection']
    if selection['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if 'representation' in selection and selection['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    FINDING_FORM.admit(finding, 'finding')
    for reference, held in summary['report_sources_held'].items():
        if not held:
            raise ValueError('literature_reference_unavailable:' + reference)


def final_to_parent(summary, completion, selection):
    finding = summary['report']
    if finding is None:
        raise ValueError('a103_table_evidence_finding_not_reported')
    validate_report(summary, finding)
    return {'credit': completion['credit'], 'finding': finding}
