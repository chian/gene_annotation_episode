"""The investigation finding of a committed A104 literature assessment (``INVESTIGATION_FINDING_FEATURES_a104.md``
section 5, lines A0 to A12): controlled features that code reads from the assessment record, its typed
``investigation_finding`` and its observation, each with its validator. The finding's text never leaves the Episode:
no source claim value, no qualification prose, no quotation; the qualification travels as its fixed kind.

Used by the A104 literature episodes whose reading commits an assessment without an assay-grading sheet of its own
(the table and ordered readings); a graded experiment's features are its sheet's (``literature_assay_grading_features``)."""

from gene_annotation_episode.domain import FINDING_QUALIFICATIONS

EVIDENCE_TYPE = 'published_evolutionary_claim'
RELATIONS = ('strengthens', 'weakens', 'mixed', 'does_not_discriminate')
APPLICABILITIES = ('direct', 'transfer', 'contextual', 'scope_limited', 'incomparable')
STATUSES = ('retained', 'withdrawn', 'not_recorded')

# name -> (validator, meaning). Validators: ('choice', options), ('count',), ('boolean',), ('refs',) one reference.
FEATURES = {
    'evidence_type': (('choice', (EVIDENCE_TYPE,)), 'A0: a committed assessment of a published claim'),
    'assessment_refs': (('refs',), 'A12: the assessment (one reference)'),
    'source_refs': (('refs',), 'A12: the source its observation is in (one reference)'),
    'finding_status': (('choice', STATUSES), 'A1: the status of its typed investigation finding, or not_recorded'),
    'relation': (('choice', RELATIONS), 'A2: how the observation bears on the proposed annotation'),
    'applicability': (('choice', APPLICABILITIES), 'A3: how the observation applies to the target'),
    'qualification_kind': (('choice', (*FINDING_QUALIFICATIONS, 'not_recorded')),
                           'The fixed kind of the finding\'s qualification, or not_recorded'),
    'source_subject_count': (('count',), 'A6: subjects of the source claim'),
    'condition_count': (('count',), 'A7: conditions of the assessment and its qualification'),
    'assumption_count': (('count',), 'A8: assumptions of the assessment'),
    'anchored': (('boolean',), 'A9: the observation has a source or visual anchor'),
    'is_correction': (('boolean',), 'A10: the finding replaces earlier findings'),
    'same_claim_as_prior': (('boolean',), 'A11: the finding names an earlier assessment of the same source claim'),
}


def validate(features):
    if set(features) != set(FEATURES):
        raise ValueError('assessment_finding_features_mismatch')
    for name, value in features.items():
        rule = FEATURES[name][0]
        if rule[0] == 'choice':
            valid = value in rule[1]
        elif rule[0] == 'count':
            valid = type(value) is int and value >= 0
        elif rule[0] == 'boolean':
            valid = type(value) is bool
        else:
            valid = type(value) is list and len(value) == 1 and type(value[0]) is str
        if not valid:
            raise ValueError('assessment_finding_feature_invalid:' + name)
    return features


def assessment_features(records, reference):
    """The features of one held assessment (``records``: ``records`` or ``ctx.store``)."""
    assessment = records.get(reference)
    observation = records.get(assessment['observation_ref'])
    finding = assessment['investigation_finding'] if 'investigation_finding' in assessment else None
    qualification = finding['qualification'] if finding is not None else None
    return validate({
        'evidence_type': EVIDENCE_TYPE, 'assessment_refs': [reference], 'source_refs': [observation['source_ref']],
        'finding_status': finding['status'] if finding is not None else 'not_recorded',
        'relation': assessment['relation'], 'applicability': assessment['applicability'],
        'qualification_kind': qualification['kind'] if qualification is not None else 'not_recorded',
        'source_subject_count': len(finding['source_claim']['subject_refs']) if finding is not None else 0,
        'condition_count': len({*assessment['condition_refs'],
                                *(qualification['context_refs'] if qualification is not None else ())}),
        'assumption_count': len(assessment['assumption_refs']),
        'anchored': observation.get('anchor') is not None or observation.get('visual_anchor') is not None,
        'is_correction': bool(finding['replaces_refs']) if finding is not None else False,
        'same_claim_as_prior': finding['same_source_claim_as_ref'] is not None if finding is not None else False})


def committed_assessment_features(records, reasons):
    """The features of every assessment the Episode's own reasoning units committed, in commit order."""
    refs = [ref for outcome in reasons if outcome.get('status') in ('completed', 'partial')
            for ref in outcome['record_refs'] if records.get(ref)['record_type'] == 'assessment']
    return [assessment_features(records, ref) for ref in dict.fromkeys(refs)]


__all__ = ['FEATURES', 'EVIDENCE_TYPE', 'validate', 'assessment_features', 'committed_assessment_features']
