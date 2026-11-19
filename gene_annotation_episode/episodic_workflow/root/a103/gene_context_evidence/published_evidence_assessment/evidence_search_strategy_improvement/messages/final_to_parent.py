"""The return. Always returned: the Episode's credit (the system hands it in ``completion``; it is the productivity
signal: whether the strategy is productive is the credit and its trend, and nothing restates it) and the finding:
controlled values only (``INVESTIGATION_FINDING_FEATURES_a103.md`` section B, option D-a, and section C). The model's
``report`` names each relevant source candidate found, with fixed values for whether its subject corresponds to the
target and the kind of gene-context evidence it reports; code reads the finding from that report: the candidate
sources (the records the parent passes next) and their counts. No approach, outcome, relevance or other model text
is returned. Nothing is selectable."""
from method_loop import ChoiceField, Field, RecordForm

CORRESPONDENCE = ('established', 'unresolved', 'not_applicable', 'not_examined')
EVIDENCE_TYPES = ('conserved_neighborhood', 'gene_fusion', 'phylogenetic_cooccurrence', 'context_channel_association',
                  'context_contrast', 'single_locus_organization', 'none_applicable')

CANDIDATE_FORM = RecordForm({
    'source_ref': Field('text', 'The held relevant source candidate'),
    'target_correspondence': ChoiceField('text', 'Whether the source subject corresponds to the target',
                                         CORRESPONDENCE),
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence the source reports', EVIDENCE_TYPES),
})
# What the model writes with the report tool (validated by this form; it stays inside the Episode).
REPORT_FORM = RecordForm({
    'candidates': Field('list', 'One entry per relevant source candidate found', items=CANDIDATE_FORM),
})
FINDING_FORM = RecordForm({
    'candidate_count': Field('integer', 'The number of relevant source candidates found'),
    'established_correspondence_count': Field('integer', 'The number of candidates whose subject corresponds to the '
                                              'target'),
    'candidate_source_refs': Field('record_refs', 'The relevant source candidates'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The relevant source candidates and their counts', form=FINDING_FORM),
})


def finding_of(report):
    """The finding code reads from the latest report (empty before one)."""
    candidates = [] if report is None else report['candidates']
    return {'candidate_count': len(candidates),
            'established_correspondence_count': sum(1 for row in candidates
                                                    if row['target_correspondence'] == 'established'),
            'candidate_source_refs': list(dict.fromkeys(row['source_ref'] for row in candidates))}


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': summary['finding']}
