"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: controlled values only (``INVESTIGATION_FINDING_FEATURES_a103.md``
section B, option D-a, and section C). The model's ``report`` judges each source considered with fixed values:
whether it merits examination, whether its subject corresponds to the target (``not_examined`` when the child did not
examine it) and the kind of gene-context evidence it reports; code reads the finding from that report: the sources
that merit examination (the records the parent sends next), and the counts of judged, meriting and established
sources. No reason, claim or other model text is returned. Nothing is selectable."""
from method_loop import ChoiceField, Field, RecordForm

CORRESPONDENCE = ('established', 'unresolved', 'not_applicable', 'not_examined')
EVIDENCE_TYPES = ('conserved_neighborhood', 'gene_fusion', 'phylogenetic_cooccurrence', 'context_channel_association',
                  'context_contrast', 'single_locus_organization', 'none_applicable')

JUDGEMENT_FORM = RecordForm({
    'source_ref': Field('text', 'The held source the judgement is about'),
    'merits_examination': Field('boolean', 'Whether the source merits examination for the assigned question'),
    'target_correspondence': ChoiceField('text', 'Whether the source subject corresponds to the target',
                                         CORRESPONDENCE),
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence the source reports', EVIDENCE_TYPES),
})
# What the model writes with the report tool (validated by this form; it stays inside the Episode).
REPORT_FORM = RecordForm({
    'judgements': Field('list', 'One judgement per source considered', items=JUDGEMENT_FORM),
})
FINDING_FORM = RecordForm({
    'judged_source_count': Field('integer', 'The number of sources judged'),
    'merits_examination_count': Field('integer', 'The number of sources judged to merit examination'),
    'established_correspondence_count': Field('integer', 'The number of sources whose subject corresponds to the '
                                              'target'),
    'merits_examination_source_refs': Field('record_refs', 'The sources judged to merit examination'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The counts and the sources that merit examination', form=FINDING_FORM),
})


def finding_of(report):
    """The finding code reads from the latest report (empty before one)."""
    judgements = [] if report is None else report['judgements']
    meriting = [row['source_ref'] for row in judgements if row['merits_examination']]
    return {'judged_source_count': len(judgements), 'merits_examination_count': len(meriting),
            'established_correspondence_count': sum(1 for row in judgements
                                                    if row['target_correspondence'] == 'established'),
            'merits_examination_source_refs': list(dict.fromkeys(meriting))}


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': summary['finding']}
