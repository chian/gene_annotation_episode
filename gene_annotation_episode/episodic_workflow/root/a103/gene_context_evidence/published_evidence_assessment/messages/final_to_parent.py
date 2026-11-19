"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: controlled values only (``INVESTIGATION_FINDING_FEATURES_a103.md``
section B, option D-a, and section C: what the A103 head decides next is whether to commission a native measurement
on loci the literature names, and which records to pass). The model's ``report`` names each published source the
assessment rests on, with fixed values for whether its subject corresponds to the target and the kind of
gene-context evidence it reports; code reads the finding from that report: the sources whose correspondence is
established, the counts of established and unresolved sources, and one count per evidence type. No claim, subject,
qualification or interpretation text is returned. Nothing is selectable."""
from method_loop import ChoiceField, Field, RecordForm

CORRESPONDENCE = ('established', 'unresolved', 'not_applicable', 'not_examined')
EVIDENCE_TYPES = ('conserved_neighborhood', 'gene_fusion', 'phylogenetic_cooccurrence', 'context_channel_association',
                  'context_contrast', 'single_locus_organization', 'none_applicable')

ASSESSMENT_FORM = RecordForm({
    'source_ref': Field('text', 'The held published source the assessment rests on'),
    'target_correspondence': ChoiceField('text', 'Whether the source subject corresponds to the target',
                                         CORRESPONDENCE),
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence the source reports', EVIDENCE_TYPES),
})
# What the model writes with the report tool (validated by this form; it stays inside the Episode).
REPORT_FORM = RecordForm({
    'assessments': Field('list', 'One entry per published source the assessment rests on', items=ASSESSMENT_FORM),
})
FINDING_FORM = RecordForm({
    'established_correspondence_count': Field('integer', 'Sources whose subject corresponds to the target'),
    'unresolved_correspondence_count': Field('integer', 'Sources whose correspondence to the target is unresolved'),
    **{name + '_count': Field('integer', 'Assessed sources reporting evidence of type ' + name)
       for name in EVIDENCE_TYPES},
    'assessed_source_refs': Field('record_refs', 'The sources whose correspondence to the target is established'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The counts of the assessed published sources and the established ones',
                     form=FINDING_FORM),
})


def finding_of(report):
    """The finding code reads from the latest report (empty before one)."""
    rows = [] if report is None else report['assessments']
    return {'established_correspondence_count': sum(1 for row in rows if row['target_correspondence'] == 'established'),
            'unresolved_correspondence_count': sum(1 for row in rows if row['target_correspondence'] == 'unresolved'),
            **{name + '_count': sum(1 for row in rows if row['evidence_type'] == name) for name in EVIDENCE_TYPES},
            'assessed_source_refs': list(dict.fromkeys(row['source_ref'] for row in rows
                                                       if row['target_correspondence'] == 'established'))}


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': summary['finding']}
