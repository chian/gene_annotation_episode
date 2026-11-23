"""The investigation finding of a saved A105 assay grading sheet (``a105_assay_grading_sheet``): controlled features
that code reads from the saved grading record, each with its validator (``INVESTIGATION_FINDING_FEATURES_a105.md``
sections 2.7, 3.3 and 4, the "core" fields; adopted by the owner on 19 November 2026).

What a feature is: the evidence type (the sheet's ``assay_type``), the quantity kind, the sheet, experiment and
assertion references, the value, status, unit and origin of the measured effect, the effect variance, the signed log
evidence ratio and its status, the prediction model, the status of every interpretation criterion, and whether the
evidence ratio rests on synthetic or proposed inputs; and the classification of the fields the sheet leaves unknown
(``literature_unknown_classification``: how many fields the grading has and leaves unknown, whether a classification of
them against the source is held and, when one is, how many it holds justified and unjustified; credit reads these).
No model-written text: the cells' reasons, conditions, formulas
and meanings, the support passages and the assessment's ``investigation_finding`` stay in the Episode that saved the
sheet, behind its reference. A number the sheet leaves unavailable is absent from the features (its status says
why); the forms declare those fields not required.

A105 carries no annotation field of its own: the asserted function is the reference to the assertion record
(owner, 19 November 2026).
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (
    ASSAY_TYPES, CRITERIA, CRITERIA_BY_TYPE, QUANTITY_KINDS, _quantity_unit_supported)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_unknown_classification import (
    CLASSIFICATION_STATUSES, classification_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)

KINDS = tuple(dict.fromkeys(kind for kinds in QUANTITY_KINDS.values() for kind in kinds))
# Every unit ``_quantity_unit_supported`` admits for some quantity kind; a unit the grader does not admit for the
# sheet's quantity kind is ``unsupported_for_quantity_kind`` (its evidence ratio is then unavailable).
EFFECT_UNITS = ('fraction', 'dimensionless', 'display_fraction', 'display_darkness_sum', 'M', 'mM', 'uM', 'nM',
                'per_min', 'per_s', 's^-1', 'min^-1', '1/s', '1/min', 'U/mg', 'U/mL', 'umol/min/mg', 'nmol/min/mg',
                'pmol/min/mg', 'uM_inverse_min_inverse', 'uM^-1min^-1', 'M^-1s^-1', 'uM^-1s^-1', 'M^-1min^-1',
                'mM^-1s^-1', 'mM^-1min^-1', 'pA', 'nA', 'uA', 'A', 'pS', 'nS', 'uS', 'S',
                'elementary_charge_equivalents_per_s', 's', 'sec', 'min', 'h', 'hour', 'mol', 'mmol', 'umol', 'nmol',
                'pmol', 'molecules', 'count', 'mg', 'ug', 'ng', 'mg/ml', 'mg/mL', 'uM/min', 'uM/s', 'mM/min', 'mM/s',
                'nM/min', 'nM/s', 'mmol/min', 'umol/min', 'nmol/min', 'nmol/s', 'pmol/min',
                'unsupported_for_quantity_kind')
EFFECT_STATUSES = ('populated', 'bounded', 'unavailable')
VARIANCE_STATUSES = ('populated', 'unavailable')
RATIO_STATUSES = ('conditional', 'unavailable')
ORIGINS = ('reported', 'derived', 'graph_derived', 'synthetic', 'proposed', 'not_selected')
MODEL_KINDS = ('fixed_predictions_known_normal', 'fixed_predictions_estimated_normal', 'fixed_predictions_student_t',
               'not_selected')
VARIANCE_INTERPRETATIONS = ('known', 'estimated', 'unknown', 'not_selected')
CRITERION_STATUSES = ('supported', 'unknown', 'conflicting', 'not_applicable', 'not_selected')

# name -> validator: ('number',) finite (absent when the sheet has no value), ('nonnegative',), ('count',),
# ('choice', options), ('boolean',), ('refs',) one reference
FEATURES = {
    'evidence_type': ('choice', ASSAY_TYPES),
    'quantity_kind': ('choice', KINDS),
    'sheet_refs': ('refs',),
    'experiment_refs': ('refs',),
    'assertion_refs': ('refs',),
    'source_log_evidence_ratio': ('number',),
    'source_log_evidence_ratio_status': ('choice', RATIO_STATUSES),
    'effect_value': ('number',),
    'effect_status': ('choice', EFFECT_STATUSES),
    'effect_unit': ('choice', EFFECT_UNITS),
    'effect_origin': ('choice', ORIGINS),
    'effect_variance': ('nonnegative',),
    'effect_variance_status': ('choice', VARIANCE_STATUSES),
    'prediction_model_kind': ('choice', MODEL_KINDS),
    'variance_interpretation': ('choice', VARIANCE_INTERPRETATIONS),
    **{name + '_status': ('choice', CRITERION_STATUSES) for name in CRITERIA},
    'evidence_uses_synthetic_input': ('boolean',),
    'evidence_uses_proposed_input': ('boolean',),
    'graded_field_count': ('count',),
    'unknown_field_count': ('count',),
    'unknown_classification_status': ('choice', CLASSIFICATION_STATUSES),
    'justified_unknown_count': ('count',),
    'unjustified_unknown_count': ('count',),
}
# The numbers a sheet can leave without a value, and the counts of a classification that is not held.
OPTIONAL = ('source_log_evidence_ratio', 'effect_value', 'effect_variance', 'justified_unknown_count',
            'unjustified_unknown_count')
MEANINGS = {
    'evidence_type': 'The A105 evidence type: the assay type the sheet was graded as',
    'quantity_kind': 'The kind of native quantity the measured effect is',
    'sheet_refs': 'The saved assay grading sheet (one reference)',
    'experiment_refs': 'The source-anchored assay reference of the graded experiment (one reference)',
    'assertion_refs': 'The hypothesis record of the asserted function the experiment was graded against (one reference)',
    'source_log_evidence_ratio': 'Signed natural-log evidence ratio, assertion against alternative (positive supports '
                                 'the assertion); absent when unavailable',
    'source_log_evidence_ratio_status': 'Whether the log evidence ratio is a conditional value or unavailable',
    'effect_value': 'The measured native effect, in effect_unit; absent when unavailable',
    'effect_status': 'Whether the measured effect is populated, a censoring bound, or unavailable',
    'effect_unit': 'The unit of the measured effect, or unsupported_for_quantity_kind',
    'effect_origin': 'Where the measured effect comes from (reported, derived, graph_derived, synthetic, proposed), '
                     'or not_selected',
    'effect_variance': 'The variance of the measured effect, effect_unit squared; absent when unavailable',
    'effect_variance_status': 'Whether the effect variance is populated or unavailable',
    'prediction_model_kind': 'The fixed-prediction residual model of the evidence ratio, or not_selected',
    'variance_interpretation': 'Whether the effect variance is known or estimated for the model, or not_selected',
    **{name + '_status': 'The interpretation status of the ' + name + ' criterion, or not_selected when the sheet '
                         'does not carry it' for name in CRITERIA},
    'evidence_uses_synthetic_input': 'Whether the log evidence ratio rests on a synthetic input',
    'evidence_uses_proposed_input': 'Whether the log evidence ratio rests on a proposed input',
    'graded_field_count': 'The fields of the grading: its nine quantities, its prediction model and the criteria '
                          'it carries',
    'unknown_field_count': 'The fields the grading leaves unknown (a null quantity, a null prediction model, a '
                           'criterion unknown)',
    'unknown_classification_status': 'Whether a classification of the unknown fields against the source is held',
    'justified_unknown_count': 'Unknown fields the classification holds justified (the source does not state '
                               'them); absent when not classified',
    'unjustified_unknown_count': 'Unknown fields the classification holds unjustified (the source states them); '
                                 'absent when not classified',
}


def validate_features(features):
    """Each feature against its validator. A violation raises ``ValueError``."""
    absent = set(FEATURES) - set(features)
    if not absent <= set(OPTIONAL) or not set(features) <= set(FEATURES):
        raise ValueError('assay_grading_finding_features_mismatch')
    for name, value in features.items():
        rule = FEATURES[name]
        if rule[0] == 'number':
            valid = type(value) in (int, float) and math.isfinite(value)
        elif rule[0] == 'nonnegative':
            valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
        elif rule[0] == 'count':
            valid = type(value) is int and value >= 0
        elif rule[0] == 'choice':
            valid = value in rule[1]
        elif rule[0] == 'boolean':
            valid = type(value) is bool
        else:
            valid = type(value) is list and len(value) == 1 and type(value[0]) is str
        if not valid:
            raise ValueError('assay_grading_finding_feature_invalid:' + name)
    if features['quantity_kind'] not in QUANTITY_KINDS[features['evidence_type']]:
        raise ValueError('assay_grading_finding_feature_invalid:quantity_kind')
    carried = set(CRITERIA_BY_TYPE[features['evidence_type']])
    if any(features[name + '_status'] != 'not_selected' for name in CRITERIA if name not in carried):
        raise ValueError('assay_grading_finding_feature_invalid:criterion_of_another_assay_type')
    if ('source_log_evidence_ratio' in features) != (features['source_log_evidence_ratio_status'] == 'conditional'):
        raise ValueError('assay_grading_finding_feature_invalid:source_log_evidence_ratio')
    counts = [features[name] for name in ('justified_unknown_count', 'unjustified_unknown_count') if name in features]
    if (features['unknown_classification_status'] == 'classified') != (len(counts) == 2) or (
            counts and sum(counts) != features['unknown_field_count']):
        raise ValueError('assay_grading_finding_feature_invalid:unknown_classification')
    return features


def sheet_features(reader, sheet_ref):
    """The features of one saved grading sheet, read from its saved record (``reader``: ``records`` or
    ``ctx.store``; the sheet must be held)."""
    saved = LiteratureAssayGradingRepository(reader).read(sheet_ref)
    sheet, selection = saved['sheet'], saved['selection']
    cells = sheet['cells']
    effect, variance, ratio = cells['measured_effect'], cells['effect_variance'], cells['source_log_evidence_ratio']
    model = sheet['prediction_model']
    features = {
        'evidence_type': sheet['assay_type'], 'quantity_kind': sheet['quantity_kind'],
        'sheet_refs': [sheet_ref], 'experiment_refs': [selection['experiment_ref']],
        'assertion_refs': [sheet['assertion_ref']],
        'source_log_evidence_ratio_status': ratio['status'],
        'effect_status': effect['status'],
        'effect_unit': (effect['unit'] if _quantity_unit_supported(sheet['quantity_kind'], effect['unit'])
                        else 'unsupported_for_quantity_kind'),
        'effect_origin': effect['input_origins'][0] if effect['input_origins'] else 'not_selected',
        'effect_variance_status': variance['status'],
        'prediction_model_kind': 'not_selected' if model is None else model['kind'],
        'variance_interpretation': 'not_selected' if model is None else model['variance_interpretation'],
        **{name + '_status': (sheet['interpretations'][name]['status'] if name in sheet['interpretations']
                              else 'not_selected') for name in CRITERIA},
        'evidence_uses_synthetic_input': 'synthetic' in ratio['input_origins'],
        'evidence_uses_proposed_input': 'proposed' in ratio['input_origins'],
        **classification_features(reader, sheet_ref, selection),
    }
    for name, cell in (('source_log_evidence_ratio', ratio), ('effect_value', effect), ('effect_variance', variance)):
        if cell['value'] is not None:
            features[name] = cell['value']
    return validate_features(features)


def current_sheet_features(reader):
    """The features of each current grading sheet this Episode saved, in the order its families began."""
    return [sheet_features(reader, ref) for ref in LiteratureAssayGradingRepository(reader).current_sheet_refs()]


def merged_sheet_features(own, returned):
    """This Episode's own sheets and the sheets its children returned, one entry per sheet (first seen kept):
    sheets are listed side by side; each experiment stays its own instance and nothing is pooled."""
    result = {}
    for features in (*own, *returned):
        result.setdefault(features['sheet_refs'][0], features)
    return list(result.values())


def assay_counts(sheets, assertion_ref):
    """The per-episode counts of section 2.7 (A1 to A3) over the sheets of ``assertion_ref``: distinct experiments,
    sheets, and distinct experiments whose sheet has a conditional evidence ratio."""
    own = [features for features in sheets if features['assertion_refs'] == [assertion_ref]]
    return {'assay_count': len({features['experiment_refs'][0] for features in own}),
            'assessment_count': len(own),
            'assay_count_with_evidence_ratio': len({features['experiment_refs'][0] for features in own
                                                    if features['source_log_evidence_ratio_status'] == 'conditional'})}


COUNT_MEANINGS = {
    'assay_count': 'Distinct experiments graded for the commissioned assertion',
    'assessment_count': 'Grading sheets for the commissioned assertion',
    'assay_count_with_evidence_ratio': 'Distinct experiments whose sheet has a conditional log evidence ratio',
}


__all__ = ['FEATURES', 'MEANINGS', 'OPTIONAL', 'COUNT_MEANINGS', 'AGGREGATION_FEATURES', 'AGGREGATION_MEANINGS',
           'AGGREGATION_OPTIONAL', 'aggregation_features', 'current_aggregation_features', 'validate_features', 'sheet_features',
           'current_sheet_features', 'merged_sheet_features', 'assay_counts']


# The across-experiment aggregation sheet (section 3.3, core fields): the owner's reducers over selected grading
# components; the features are its overall cell and what it rests on.
AGGREGATION_STATUSES = ('complete', 'partial', 'unavailable')
AGGREGATION_FEATURES = {
    'evidence_type': ('choice', ('across_experiment_aggregate',)),
    'sheet_refs': ('refs',),
    'assertion_refs': ('refs',),
    'selected_assay_count': ('count',),
    'overall_value': ('number',),
    'overall_available_value': ('number',),
    'overall_status': ('choice', AGGREGATION_STATUSES),
    'overall_available_assay_count': ('count',),
    'overall_is_log_evidence_ratio': ('boolean',),
    'aggregate_uses_synthetic_input': ('boolean',),
    'aggregate_uses_proposed_input': ('boolean',),
}
AGGREGATION_OPTIONAL = ('overall_value', 'overall_available_value')
AGGREGATION_MEANINGS = {
    'evidence_type': 'The A105 evidence type: across_experiment_aggregate',
    'sheet_refs': 'The saved aggregation sheet (one reference)',
    'assertion_refs': 'The hypothesis record the aggregation is about (one reference)',
    'selected_assay_count': 'Experiments the aggregation selected',
    'overall_value': 'The overall SUM over every selected experiment; absent unless every one contributed',
    'overall_available_value': 'The overall SUM over the experiments that contributed; absent when none did',
    'overall_status': 'Whether the overall cell is complete, partial or unavailable',
    'overall_available_assay_count': 'Experiments that contributed to the overall cell',
    'overall_is_log_evidence_ratio': 'Whether the overall cell sums natural-log evidence ratios (dimensionless)',
    'aggregate_uses_synthetic_input': 'Whether the overall cell rests on a synthetic input',
    'aggregate_uses_proposed_input': 'Whether the overall cell rests on a proposed input',
}


def aggregation_features(reader, sheet_ref):
    """The features of one saved aggregation sheet (``reader`` must hold it)."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import (
        LiteratureA105AggregationRepository)
    sheet = LiteratureA105AggregationRepository(reader).read(sheet_ref)['sheet']
    overall = sheet['cells']['overall']
    features = {
        'evidence_type': 'across_experiment_aggregate', 'sheet_refs': [sheet_ref],
        'assertion_refs': [sheet['assertion_ref']], 'selected_assay_count': len(sheet['experiment_refs']),
        'overall_status': overall['status'],
        'overall_available_assay_count': len(overall['available_experiment_refs']),
        'overall_is_log_evidence_ratio': (overall['source_component_names'] == ['source_log_evidence_ratio']
                                          and overall['unit'] == 'dimensionless'),
        'aggregate_uses_synthetic_input': 'synthetic' in overall['input_origins'],
        'aggregate_uses_proposed_input': 'proposed' in overall['input_origins'],
    }
    for name, key in (('overall_value', 'value'), ('overall_available_value', 'available_value')):
        if overall[key] is not None:
            features[name] = overall[key]
    if (features['overall_available_assay_count'] > features['selected_assay_count']
            or not all(type(features[name]) in (int, float) for name in AGGREGATION_OPTIONAL if name in features)):
        raise ValueError('aggregation_finding_feature_invalid')
    return features


def current_aggregation_features(reader):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import (
        LiteratureA105AggregationRepository)
    return [aggregation_features(reader, ref) for ref in LiteratureA105AggregationRepository(reader).current_sheet_refs()]
