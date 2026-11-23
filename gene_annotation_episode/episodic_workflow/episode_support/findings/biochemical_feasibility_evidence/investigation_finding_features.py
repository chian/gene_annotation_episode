"""The controlled investigation finding of an A110 episode over the typed assessments it holds
(``INVESTIGATION_FINDING_FEATURES_a110.md`` sections 1, 2.3 and 3.3): counts, fixed-vocabulary values and record
references that code reads from the retained-finding projection (``investigation_progress``) and from the
assessment, observation and claim records it counts. No model-written text: the source claim, its subject and its
qualification stay in the records, inside the Episode that holds them.

``evidence_type`` is read from the cited observation's own kind (table 1, the owner's choice); the model never
writes it. ``credit`` is not repeated here (credit is the productivity signal).

``finding_record_refs`` are the records a receiver's own finding projection reads to count the retained findings
again (each retained assessment and every held record it names, transitively): a pass carries only the records
named (decision T5), so a parent that receives ``finding_refs`` measures them over what it holds.
"""
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_progress import (
    FindingProgressPolicy, project_finding_progress)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    canonical)

# table 1: observation.kind -> evidence_type (E1 to E10)
EVIDENCE_TYPES = {
    'reaction_context': 'reaction_record', 'biochemical_assay': 'biochemical_assay',
    'assay_report': 'biochemical_assay', 'mechanism': 'mechanism', 'comparison': 'prediction_contrast',
    'growth_assay': 'growth_phenotype', 'genetic_phenotype': 'growth_phenotype',
    'context_measurement': 'condition_context', 'context': 'condition_context',
    'source_annotation': 'database_annotation', 'source_content': 'source_statement',
    'alignment': 'sequence_correspondence', 'coordinate_mapping': 'sequence_correspondence',
    'sequence_composition': 'out_of_axis', 'gene_prediction': 'out_of_axis', 'profile_match': 'out_of_axis',
    'structure_match': 'out_of_axis', 'taxonomy_assignment': 'out_of_axis', 'read_support': 'out_of_axis',
}
EVIDENCE_TYPE_VALUES = ('reaction_record', 'biochemical_assay', 'mechanism', 'prediction_contrast',
                        'growth_phenotype', 'condition_context', 'database_annotation', 'source_statement',
                        'sequence_correspondence', 'out_of_axis')
INACTIVE_REASONS = ('typed_finding_not_recorded', 'finding_target_outside_scope', 'scientific_finding_withdrawn',
                    'finding_replaced', 'not_current_assessment_revision')
ARM_AGREEMENT = ('agree', 'conflict', 'none')

# name -> (validator, meaning); validators: ('count',), ('choice', options), ('counts', keys), ('refs',)
FEATURES = {
    'retained_finding_count': (('count',), 'Distinct retained findings this Episode holds (P1)'),
    'count_by_evidence_type': (('counts', EVIDENCE_TYPE_VALUES),
                               'Retained findings per evidence type, read from the cited observation kind (P2)'),
    'strengthening_count': (('count',), 'Retained findings whose relation is strengthens (P3)'),
    'weakening_count': (('count',), 'Retained findings whose relation is weakens (P4)'),
    'mixed_or_nondiscriminating_count': (('count',), 'Retained findings that are mixed or do not discriminate (P5)'),
    'direct_count': (('count',), 'Retained findings with direct applicability to the target (P6)'),
    'qualified_count': (('count',), 'Retained findings with a qualification kind other than none (P7)'),
    'independent_source_count': (('count',), 'Distinct sources among the retained findings (P8)'),
    'uncertainty_reported_count': (('count',), 'Retained findings whose claim value reports an uncertainty (P9)'),
    'controlled_count': (('count',), 'Retained findings whose observation or claim names a control (P10)'),
    'arm_agreement': (('choice', ARM_AGREEMENT),
                      'agree: only strengthening or only weakening findings; conflict: both; none: neither (P11)'),
    'inactive_count_by_reason': (('counts', INACTIVE_REASONS),
                                 'Known assessments that earn nothing, per fixed reason (P12)'),
    'finding_refs': (('refs',), 'The current retained assessments (P13)'),
    'finding_record_refs': (('refs',), 'Each retained assessment and the held records it names, transitively, so '
                            'that a receiver counts the findings over what it holds'),
}


def validate_features(features):
    """Each feature against its validator. A violation raises ``ValueError``."""
    if set(features) != set(FEATURES):
        raise ValueError('a110_finding_features_mismatch')
    for name, (rule, _) in FEATURES.items():
        value = features[name]
        if rule[0] == 'count':
            valid = type(value) is int and value >= 0
        elif rule[0] == 'choice':
            valid = value in rule[1]
        elif rule[0] == 'counts':
            valid = (type(value) is dict and set(value) == set(rule[1])
                     and all(type(count) is int and count >= 0 for count in value.values()))
        else:
            valid = type(value) is list and all(type(ref) is str and ref for ref in value) and len(set(value)) == len(value)
        if not valid:
            raise ValueError('a110_finding_feature_invalid:' + name)
    return features


def _uncertainty_reported(claim):
    return claim['value'].get('uncertainty') is not None


def _control_present(observation, claim):
    measured = any(item['name'] == 'control_ref' for item in observation.get('measurements', ()))
    roles = any(role['role'] == 'control' for role in claim['value'].get('roles', ()))
    return measured or roles


def held_closure(reader, refs):
    """``refs`` and every held Store record they name, transitively, in order of discovery."""
    result, pending = {}, list(refs)
    while pending:
        ref = pending.pop(0)
        if ref in result or not reader.holds(ref):
            continue
        result[ref] = None
        if reader.get(ref)['record_type'] != 'artifact':
            pending.extend(reader.named_references(ref))
    return list(result)


def investigation_finding(reader, scope, finding_unit, known_assessment_refs):
    """The controlled finding over the assessments this Episode knows (``known_assessment_refs``, all held)."""
    known = sorted(set(known_assessment_refs))
    progress = project_finding_progress(reader, scope, FindingProgressPolicy(finding_unit),
                                        known_assessment_refs=known, details_limit=len(known), details_offset=0)
    first = {}
    for row in progress['source_contributions']:
        first.setdefault(row['finding_key'], row)
    rows = list(first.values())
    by_type = dict.fromkeys(EVIDENCE_TYPE_VALUES, 0)
    counts = dict.fromkeys(('strengthening_count', 'weakening_count', 'mixed_or_nondiscriminating_count',
                            'direct_count', 'qualified_count', 'uncertainty_reported_count', 'controlled_count'), 0)
    sources, refs = set(), []
    for row in rows:
        assessment = reader.get(row['known_assessment_ref'])
        observation = reader.get(assessment['observation_ref'])
        finding = assessment['investigation_finding']
        claim = finding['source_claim']
        by_type[EVIDENCE_TYPES[observation['kind']]] += 1
        counts['strengthening_count'] += assessment['relation'] == 'strengthens'
        counts['weakening_count'] += assessment['relation'] == 'weakens'
        counts['mixed_or_nondiscriminating_count'] += assessment['relation'] in ('mixed', 'does_not_discriminate')
        counts['direct_count'] += assessment['applicability'] == 'direct'
        counts['qualified_count'] += finding['qualification']['kind'] != 'none'
        counts['uncertainty_reported_count'] += _uncertainty_reported(claim)
        counts['controlled_count'] += _control_present(observation, claim)
        sources.add(canonical(row['meaning']['source_claim']['source']))
        refs.append(row['current_assessment_ref'])
    refs = list(dict.fromkeys(refs))
    strengthening, weakening = counts['strengthening_count'], counts['weakening_count']
    inactive = dict.fromkeys(INACTIVE_REASONS, 0)
    for item in progress['inactive_dependencies']:
        inactive[item['reason']] += 1
    return validate_features({
        'retained_finding_count': progress['retained_finding_count'], 'count_by_evidence_type': by_type,
        **{name: int(value) for name, value in counts.items()},
        'independent_source_count': len(sources),
        'arm_agreement': ('conflict' if strengthening and weakening else 'agree' if strengthening or weakening
                          else 'none'),
        'inactive_count_by_reason': inactive, 'finding_refs': refs,
        'finding_record_refs': held_closure(reader, refs)})


def finding_progress_credit(reader, scope, finding_unit, known_assessment_refs):
    """The episode's credit: one ``finding_unit`` per distinct retained finding it knows (the retained-finding
    projection, ``known_retained_scientific_findings``)."""
    return project_finding_progress(reader, scope, FindingProgressPolicy(finding_unit),
                                    known_assessment_refs=known_assessment_refs)['credit']
