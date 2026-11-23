"""The investigation finding of A108 (``INVESTIGATION_FINDING_FEATURES_a108.md``): controlled features that code
reads from the saved sheets, each with its validator, and the controlled returns of leads and screening answers.

Two sheets and nothing else (section 0 of the feature table):

- S1, the contextual observation subscoring sheet (``literature.a108.context_grading``, version
  ``a108_context_observation_sheet``): one finding per saved sheet, lines A1 to A28 (A29, one field per
  criterion of the grader, is left out: its field names change with the grader, so it has no fixed form).
- S2, the main evidence sheet (``literature.a108.aggregation``, version ``a108_across_observation_aggregation``):
  one finding per cell, lines B1 to B18.

A sheet or cell whose status is ``unavailable`` (no relation was graded) gives no finding: its counts are null in
the sheet and a finding holds counts only. No model-written text: qualifications, quotes, the assessment's
``investigation_finding`` and the formulas stay in the sheet and its records, inside the Episode that saved them;
the parent receives these features and the sheet's reference.

A source lead (``relevance_rationale`` and witness text are prose) is returned as the number of relevant leads and
the references of their sources; a screening answer (``reason`` and quotes are prose) as the number of examined
spans and whether they cover every commissioned span (lines D1, D2, K1, K4 of the A102 table, section 2.11).
"""
import json

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_numerical_contracts import (
    RETURN_MEANINGS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_grading import (
    COMPONENTS as COUNTS, DOMAIN_BY_TYPE, DOMAINS, GRADER_TYPES, ORIGINS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_AGGREGATION_TASK, A108_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    CELLS as GRADING_CELLS, NAMESPACE as GRADING_NAMESPACE, OPERATION_DESCRIPTION as GRADING_DESCRIPTION,
    PROVIDER as GRADING_PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_aggregation_storage import (
    CELLS as AGGREGATION_CELLS, NAMESPACE as AGGREGATION_NAMESPACE,
    OPERATION_DESCRIPTION as AGGREGATION_DESCRIPTION, PROVIDER as AGGREGATION_PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_sheet_updates import (
    current_sheet_refs)

GRADING_STATUSES = ('populated', 'conditional', 'partial')
AGGREGATION_STATUSES = ('complete', 'partial')
LEAD_ORIGINS = ('prediction', 'annotation_lead')

# name -> validator: ('count',) an integer >= 0; ('signed',) an integer; ('choice', options); ('boolean',);
# ('ref',) one record reference (a list of one, passed in custody).
GRADING_FEATURES = {
    'evidence_type': ('choice', DOMAINS),
    'grader_type': ('choice', GRADER_TYPES),
    'sheet_refs': ('ref',),
    'assertion_refs': ('ref',),
    **{name: ('signed',) if name == 'net_support' else ('count',) for name in COUNTS},
    'status': ('choice', GRADING_STATUSES),
    'direct_observation_count': ('count',),
    'qualified_transfer_observation_count': ('count',),
    'conditional_observation_count': ('count',),
    'source_count': ('count',),
    'source_subject_count': ('count',),
    'target_context_established': ('boolean',),
    'context_claim_count': ('count',),
    'demoted_support_count': ('count',),
    'demoted_conflict_count': ('count',),
    'physiology_report_observation_count': ('count',),
    'observed_phenotype_observation_count': ('count',),
    'recorded_condition_observation_count': ('count',),
    'curated_observation_count': ('count',),
    'lead_only_observation_count': ('count',),
    'unwitnessed_observation_count': ('count',),
    'relationship_unknown_count': ('count',),
    'criterion_unmet_count': ('count',),
}
UNIT = ' (distinct contextual observations)'
GRADING_MEANINGS = {
    'evidence_type': 'The A108 domain of the grader: physiology, environment, availability or localization',
    'grader_type': 'The purpose-specific grader the sheet was populated with (one of the eleven)',
    'sheet_refs': 'The saved subscoring sheet (one reference)',
    'assertion_refs': 'The contextual claim (hypothesis) the sheet grades (one reference)',
    'support_count': 'Original observations with an assessed supporting relation' + UNIT,
    'conflict_count': 'Original observations with an assessed conflicting relation' + UNIT,
    'overlap_count': 'Original observations that support one claim and conflict with another' + UNIT,
    'evidence_amount': 'Supporting or conflicting original observations counted once: support + conflict - '
                       'overlap' + UNIT,
    'net_support': 'Supporting minus conflicting original observations (signed); not the amount of evidence',
    'unresolved_count': 'Original observations whose contextual connection stays unresolved; not evidence credit'
                        + UNIT,
    'status': 'The sheet status: populated, conditional (transfer or condition-specific) or partial (some '
              'relations unresolved)',
    'direct_observation_count': 'Counted observations about the target organism/context itself' + UNIT,
    'qualified_transfer_observation_count': 'Counted observations transferred from another organism or sample '
                                            'with stated qualification' + UNIT,
    'conditional_observation_count': 'Counted observations that hold only under stated conditions' + UNIT,
    'source_count': 'Source records cited by the counted observations (not a count of independent studies)',
    'source_subject_count': 'Source subjects (organisms, samples, molecules) of the counted observations',
    'target_context_established': 'Whether the target organism/context identity was established by witnessed '
                                  'support',
    'context_claim_count': 'Contextual claims (hypotheses) the counted observations bear on',
    'demoted_support_count': 'Relations requested as support that the grader left unresolved',
    'demoted_conflict_count': 'Relations requested as conflict that the grader left unresolved',
    'physiology_report_observation_count': 'Counted observations of origin organism_physiology_report' + UNIT,
    'observed_phenotype_observation_count': 'Counted observations of origin observed_phenotype' + UNIT,
    'recorded_condition_observation_count': 'Counted observations of origin recorded_sample_condition' + UNIT,
    'curated_observation_count': 'Counted observations of origin curated_observation' + UNIT,
    'lead_only_observation_count': 'Observations that are only a prediction or annotation lead (always '
                                   'unresolved)' + UNIT,
    'unwitnessed_observation_count': 'Relations whose source observation was not witnessed',
    'relationship_unknown_count': 'Relations whose relationship to the target context is unknown',
    'criterion_unmet_count': "Relations with at least one of the grader's criteria not supported",
}
AGGREGATION_FEATURES = {
    'evidence_type': ('choice', AGGREGATION_COMPONENTS),
    'sheet_refs': ('ref',),
    'assertion_refs': ('ref',),
    **{name: ('signed',) if name == 'net_support' else ('count',) for name in COUNTS},
    'status': ('choice', AGGREGATION_STATUSES),
    'selected_sheet_count': ('count',),
    'unavailable_sheet_count': ('count',),
    'direct_observation_count': ('count',),
    'qualified_transfer_observation_count': ('count',),
    'conditional_observation_count': ('count',),
    'source_count': ('count',),
    'source_subject_count': ('count',),
    'domain_count': ('count',),
}
AGGREGATION_MEANINGS = {
    **{name: GRADING_MEANINGS[name] for name in AGGREGATION_FEATURES if name in GRADING_MEANINGS},
    'evidence_type': 'The main-sheet cell: one domain (physiology, environment, availability, localization) or '
                     'overall, the union across the four domains',
    'sheet_refs': 'The saved main evidence sheet (one reference)',
    'status': 'The cell status: complete, or partial (an input sheet unavailable or a relation unresolved)',
    'selected_sheet_count': 'Subscoring sheets whose evidence_amount the cell unions',
    'unavailable_sheet_count': 'Selected subscoring sheets that were unavailable',
    'source_count': 'Distinct source records cited by the counted observations of the cell',
    'domain_count': 'Domains within the cell (the four for overall, its own for a domain cell) whose '
                    'evidence_amount is at least one',
}

# The grader prompt, the owner's filling instructions and the meaning of the two sheets, for an episode's
# instructions (``decide``): the text reaches the model there and nowhere else.
GRADING_INSTRUCTIONS = ('\nA108 contextual grading. ' + A108_GRADING_TASK + '\nSubscoring sheet: ' + GRADING_DESCRIPTION
                        + '\nWhat a subscoring cell means: ' + RETURN_MEANINGS[GRADING_NAMESPACE]
                        + '\nThe common criteria (source_subject_identity, original_observation_identity, '
                          'context_applicability, function_context_connection) are prerequisites of a relation, '
                          'not scored checklist items.'
                        + '\nMain evidence sheet: ' + A108_AGGREGATION_TASK + ' ' + AGGREGATION_DESCRIPTION
                        + '\nWhat a main-sheet cell means: ' + RETURN_MEANINGS[AGGREGATION_NAMESPACE]
                        + '\nWhat your parent receives is your credit and the counts code reads from the sheets '
                          'you saved (and their references); nothing you write in prose is returned.\n')


def _valid(rule, value):
    if rule[0] == 'count':
        return type(value) is int and value >= 0
    if rule[0] == 'signed':
        return type(value) is int
    if rule[0] == 'choice':
        return value in rule[1]
    if rule[0] == 'boolean':
        return type(value) is bool
    return type(value) is list and len(value) == 1 and type(value[0]) is str


def _validate_counts(features, kind):
    if not features['overlap_count'] <= min(features['support_count'], features['conflict_count']):
        raise ValueError(kind + '_feature_invalid:overlap_count')
    if features['evidence_amount'] != features['support_count'] + features['conflict_count'] - features['overlap_count']:
        raise ValueError(kind + '_feature_invalid:evidence_amount')
    if features['net_support'] != features['support_count'] - features['conflict_count']:
        raise ValueError(kind + '_feature_invalid:net_support')
    for name in ('direct_observation_count', 'qualified_transfer_observation_count', 'conditional_observation_count'):
        if features[name] > features['evidence_amount']:
            raise ValueError(kind + '_feature_invalid:' + name)


def validate_grading_features(features):
    """Each S1 feature against its validator (lines A1 to A28). A violation raises ``ValueError``."""
    if set(features) != set(GRADING_FEATURES):
        raise ValueError('a108_grading_features_mismatch')
    for name, rule in GRADING_FEATURES.items():
        if not _valid(rule, features[name]):
            raise ValueError('a108_grading_feature_invalid:' + name)
    if DOMAIN_BY_TYPE[features['grader_type']] != features['evidence_type']:
        raise ValueError('a108_grading_feature_invalid:grader_type')
    _validate_counts(features, 'a108_grading')
    if features['evidence_amount'] > 0 and (features['source_count'] < 1 or features['source_subject_count'] < 1):
        raise ValueError('a108_grading_feature_invalid:source_count')
    if features['lead_only_observation_count'] > features['unresolved_count']:
        raise ValueError('a108_grading_feature_invalid:lead_only_observation_count')
    return features


def validate_aggregation_features(features):
    """Each S2 feature against its validator (lines B1 to B18). A violation raises ``ValueError``."""
    if set(features) != set(AGGREGATION_FEATURES):
        raise ValueError('a108_aggregation_features_mismatch')
    for name, rule in AGGREGATION_FEATURES.items():
        if not _valid(rule, features[name]):
            raise ValueError('a108_aggregation_feature_invalid:' + name)
    _validate_counts(features, 'a108_aggregation')
    if features['selected_sheet_count'] < 1 or features['unavailable_sheet_count'] > features['selected_sheet_count']:
        raise ValueError('a108_aggregation_feature_invalid:selected_sheet_count')
    if features['domain_count'] > (4 if features['evidence_type'] == 'overall' else 1):
        raise ValueError('a108_aggregation_feature_invalid:domain_count')
    return features


def _distinct(rows, condition):
    return len({row['original_observation_key'] for row in rows if condition(row)})


def _counted(rows):
    return [row for row in rows if row['relation'] in ('support', 'conflict')]


def _saved(reader, sheet_ref):
    """The saved payload of a sheet the Episode holds with its artifact (the sheet record names it)."""
    return json.loads(reader.get_artifact(reader.get(sheet_ref)['artifact_ref']))


def grading_features(reader, sheet_ref):
    """The finding of one saved S1 sheet (``None`` for an unavailable sheet), read from the sheet's cells and rows
    and from the saved grader input (``extraction``)."""
    saved = _saved(reader, sheet_ref)
    sheet, extraction = saved['sheet'], saved['extraction']
    cells, rows = sheet['cells'], sheet['relations']
    status = cells['evidence_amount']['status']
    if status == 'unavailable':
        return None
    counted = _counted(rows)
    net = cells['net_support']
    identity = extraction['target_identity']
    features = {
        'evidence_type': sheet['domain'], 'grader_type': sheet['grader_type'], 'sheet_refs': [sheet_ref],
        'assertion_refs': [sheet['assertion_ref']],
        **{name: cells[name]['value'] for name in COUNTS},
        'status': status,
        'direct_observation_count': _distinct(counted, lambda row: row['target_relationship'] == 'direct'),
        'qualified_transfer_observation_count': _distinct(
            counted, lambda row: row['target_relationship'] == 'qualified_transfer'),
        'conditional_observation_count': _distinct(counted, lambda row: row['target_relationship'] == 'conditional'),
        'source_count': len(net['source_refs']),
        'source_subject_count': len(net['source_subject_refs']),
        # The grader's own ``target_known`` rule on the saved input.
        'target_context_established': (extraction['target_context_ref'] is not None
                                       and identity['status'] == 'supported' and bool(identity['support_refs'])),
        'context_claim_count': len(net['relation_refs']),
        'demoted_support_count': sum(row['requested_relation'] == 'support' and row['relation'] == 'unresolved'
                                     for row in rows),
        'demoted_conflict_count': sum(row['requested_relation'] == 'conflict' and row['relation'] == 'unresolved'
                                      for row in rows),
        'physiology_report_observation_count': _distinct(counted,
                                                         lambda row: row['origin'] == 'organism_physiology_report'),
        'observed_phenotype_observation_count': _distinct(counted, lambda row: row['origin'] == 'observed_phenotype'),
        'recorded_condition_observation_count': _distinct(counted,
                                                          lambda row: row['origin'] == 'recorded_sample_condition'),
        'curated_observation_count': _distinct(counted, lambda row: row['origin'] == 'curated_observation'),
        'lead_only_observation_count': _distinct(rows, lambda row: row['origin'] in LEAD_ORIGINS),
        'unwitnessed_observation_count': sum('source_observation_unwitnessed' in row['reasons'] for row in rows),
        'relationship_unknown_count': sum('target_context_relationship_unknown' in row['reasons'] for row in rows),
        'criterion_unmet_count': sum(any(reason.startswith('criterion_') for reason in row['reasons'])
                                     for row in rows),
    }
    return validate_grading_features(features)


def sheet_amount(reader, finding):
    """The A108 sheet measure over the subscoring sheets a finding names and the reader holds: the sum of each held
    sheet's own ``evidence_amount`` cell (the distinct original observations it counts as support or conflict, once each;
    a sheet whose status is ``unavailable`` counts none). Each sheet is read through custody (``grading_features``), never
    from a figure a child returned. No weight and no constant: the sheet's own count is the measure (EXPERT_REVIEW: owner
    to confirm that the sheet's evidence_amount is the credit of A108 until a degree of relationship, direct above
    transferred, is given a weight)."""
    return sum(features['evidence_amount'] for item in finding['grading_sheets']
               if (features := grading_features(reader, item['sheet_refs'][0])) is not None)


def aggregation_features(reader, sheet_ref):
    """The findings of one saved S2 sheet: one per cell whose status is not ``unavailable``."""
    sheet = _saved(reader, sheet_ref)['sheet']
    domains = {name: sheet['cells'][name]['evidence_amount'] for name in AGGREGATION_COMPONENTS if name != 'overall'}
    found = []
    for component in AGGREGATION_COMPONENTS:
        cell = sheet['cells'][component]
        if cell['status'] == 'unavailable':
            continue
        counted = _counted(cell['relations'])
        scope = list(domains) if component == 'overall' else [component]
        features = {
            'evidence_type': component, 'sheet_refs': [sheet_ref], 'assertion_refs': [sheet['assertion_ref']],
            **{name: cell[name] for name in COUNTS},
            'status': cell['status'],
            'selected_sheet_count': len(cell['selected_components']),
            'unavailable_sheet_count': len(cell['unavailable_sheet_refs']),
            'direct_observation_count': _distinct(counted, lambda row: row['target_relationship'] == 'direct'),
            'qualified_transfer_observation_count': _distinct(
                counted, lambda row: row['target_relationship'] == 'qualified_transfer'),
            'conditional_observation_count': _distinct(counted,
                                                       lambda row: row['target_relationship'] == 'conditional'),
            'source_count': len({ref for row in counted for ref in row['source_refs']}),
            'source_subject_count': len({row['source_subject_ref'] for row in counted}),
            'domain_count': sum((domains[name] or 0) >= 1 for name in scope),
        }
        found.append(validate_aggregation_features(features))
    return found


def own_findings(reader):
    """The finding of the sheets this Episode saved and that are current (``literature_sheet_updates``): the
    features of each available subscoring sheet and of each available main-sheet cell, in the order saved."""
    produced = [ref for ref in current_sheet_refs(reader, None) if reader.receipt(ref)['how'] == 'produced']
    grading, aggregation = [], []
    for ref in produced:
        provider = reader.get(ref)['provider']
        if provider == GRADING_PROVIDER:
            features = grading_features(reader, ref)
            if features is not None:
                grading.append(features)
        elif provider == AGGREGATION_PROVIDER:
            aggregation.extend(aggregation_features(reader, ref))
    return {'grading_sheets': grading, 'aggregation_cells': aggregation}


def merged_findings(own, returned):
    """This Episode's own findings and those its children returned, side by side (never combined): one entry per
    subscoring sheet and per main-sheet cell, the first seen kept."""
    grading, aggregation = {}, {}
    for finding in (own, *returned):
        for item in finding['grading_sheets']:
            grading.setdefault(item['sheet_refs'][0], item)
        for item in finding['aggregation_cells']:
            aggregation.setdefault((item['sheet_refs'][0], item['evidence_type']), item)
    return {'grading_sheets': list(grading.values()), 'aggregation_cells': list(aggregation.values())}


def assessment_basis(reader, assessment_refs):
    """The observations the assessments rest on, by reference: the records a parent's credit reads beyond the
    assessments themselves (a pass carries only the records it names)."""
    return list(dict.fromkeys(reader.get(ref)['observation_ref'] for ref in assessment_refs))


def own_cell_refs(reader, namespace):
    """The cell rows this Episode saved for the requested components of its sheets (``publish_cells``), by family
    namespace: the rows a parent is passed in custody (their content stays a record; nothing is copied)."""
    table = {GRADING_NAMESPACE: GRADING_CELLS, AGGREGATION_NAMESPACE: AGGREGATION_CELLS}[namespace]
    return [row['id'] for row in reader.table(table).select() if reader.receipt(row['id'])['how'] == 'produced']


def lead_return(dispositions):
    """A lead return: the number of relevant leads and their sources (no rationale, no witness text)."""
    relevant = [lead['source_ref'] for lead in dispositions if lead['disposition'] == 'relevant']
    return {'relevant_lead_count': len(relevant), 'lead_source_refs': list(dict.fromkeys(relevant))}


def screening_return(spans, answers):
    """A screening return: the number of examined spans declared without applicable evidence and whether they
    cover every commissioned span."""
    return {'examined_span_count': len(spans), 'commissioned_spans_covered': bool(answers)}


def _field(name, rule, meaning):
    if rule[0] == 'choice':
        return ChoiceField('text', meaning, rule[1])
    if rule[0] == 'ref':
        return Field('record_refs', meaning)
    return Field({'count': 'integer', 'signed': 'integer', 'boolean': 'boolean'}[rule[0]], meaning)


GRADING_FORM = RecordForm({name: _field(name, rule, GRADING_MEANINGS[name]) for name, rule in GRADING_FEATURES.items()})
AGGREGATION_FORM = RecordForm({name: _field(name, rule, AGGREGATION_MEANINGS[name])
                               for name, rule in AGGREGATION_FEATURES.items()})
LEAD_FORM = RecordForm({
    'relevant_lead_count': Field('integer', 'Validated source leads judged relevant to the commissioned question'),
    'lead_source_refs': Field('record_refs', 'The sources of the relevant leads'),
})
SCREENING_FORM = RecordForm({
    'examined_span_count': Field('integer', 'Examined source spans declared to hold no applicable contextual '
                                 'observation'),
    'commissioned_spans_covered': Field('boolean', 'Whether those spans cover every commissioned span'),
})


def finding_form(meaning_of_assessments):
    """The form of an A108 finding: the subscoring-sheet and main-sheet-cell features and the assessments."""
    return RecordForm({
        'grading_sheets': Field('list', 'One entry per available subscoring sheet saved (own or returned)',
                                items=GRADING_FORM),
        'aggregation_cells': Field('list', 'One entry per available main evidence sheet cell saved (own or returned)',
                                   items=AGGREGATION_FORM),
        'assessment_refs': Field('record_refs', meaning_of_assessments),
        'observation_refs': Field('record_refs', 'The observations those assessments rest on'),
    })


__all__ = ['GRADING_FEATURES', 'GRADING_MEANINGS', 'AGGREGATION_FEATURES', 'AGGREGATION_MEANINGS',
           'GRADING_INSTRUCTIONS', 'GRADING_FORM', 'AGGREGATION_FORM', 'LEAD_FORM', 'SCREENING_FORM', 'finding_form',
           'validate_grading_features', 'validate_aggregation_features', 'grading_features', 'sheet_amount',
           'aggregation_features', 'own_findings', 'merged_findings', 'own_cell_refs', 'assessment_basis', 'lead_return',
           'screening_return']
