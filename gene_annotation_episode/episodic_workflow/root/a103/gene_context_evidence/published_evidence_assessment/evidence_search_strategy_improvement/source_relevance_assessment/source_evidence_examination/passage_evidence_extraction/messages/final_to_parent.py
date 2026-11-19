"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal and nothing restates it) and the finding: controlled values only (``INVESTIGATION_FINDING_FEATURES_a103.md``
section B, option D-a; A103 has no literature grading sheet). The model's ``report`` names, from fixed vocabularies,
whether the source subject corresponds to the target and which kind of gene-context evidence the passages report,
and the exact passages (source, representation, byte window) it rests on; code reads the finding from that report:
the two choices, the number of passages, the byte extent they cover (so the next selection does not repeat it) and
the passages' sources. No quotation and no model-written text is returned. Nothing is selectable."""
from method_loop import ChoiceField, Field, RecordForm

CORRESPONDENCE = ('established', 'unresolved', 'not_applicable')
EVIDENCE_TYPES = ('conserved_neighborhood', 'gene_fusion', 'phylogenetic_cooccurrence', 'context_channel_association',
                  'context_contrast', 'single_locus_organization', 'none_applicable')
REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

PASSAGE_FORM = RecordForm({
    'source_ref': Field('text', 'The held source the passage is from'),
    'representation': ChoiceField('text', 'The representation read', REPRESENTATIONS),
    'offset': Field('integer', 'The byte offset of the passage'),
    'limit': Field('integer', 'The byte length of the passage'),
})
# What the model writes with the report tool (validated by this form; it stays inside the Episode).
REPORT_FORM = RecordForm({
    'target_correspondence': ChoiceField('text', 'Whether the source subject corresponds to the target',
                                         CORRESPONDENCE),
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence the passages report', EVIDENCE_TYPES),
    'passages': Field('list', 'The separate source-bound passages the report rests on', items=PASSAGE_FORM),
})
FINDING_FORM = RecordForm({
    'reported': Field('boolean', 'Whether the episode reported; the other values are empty when not'),
    'target_correspondence': ChoiceField('text', 'Whether the source subject corresponds to the target',
                                         CORRESPONDENCE),
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence reported', EVIDENCE_TYPES),
    'passage_count': Field('integer', 'The number of passages the report rests on'),
    'covered_offset': Field('integer', 'The first byte the passages cover'),
    'covered_limit': Field('integer', 'The byte extent from covered_offset to the end of the last passage'),
    'source_refs': Field('record_refs', "The passages' sources"),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled values of the reported passages', form=FINDING_FORM),
})


def finding_of(report):
    """The finding code reads from the latest report (``None`` before one)."""
    if report is None:
        return {'reported': False, 'target_correspondence': 'unresolved', 'evidence_type': 'none_applicable',
                'passage_count': 0, 'covered_offset': 0, 'covered_limit': 0, 'source_refs': []}
    passages = report['passages']
    start = min((row['offset'] for row in passages), default=0)
    end = max((row['offset'] + row['limit'] for row in passages), default=0)
    return {'reported': True, 'target_correspondence': report['target_correspondence'],
            'evidence_type': report['evidence_type'], 'passage_count': len(passages), 'covered_offset': start,
            'covered_limit': end - start,
            'source_refs': list(dict.fromkeys(row['source_ref'] for row in passages))}


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': summary['finding']}
