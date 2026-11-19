"""The investigation finding of the two A106 graders: controlled features that code reads from a saved sheet,
each with its validator (``INVESTIGATION_FINDING_FEATURES_a106.md`` sections G1 and G2).

G1 is the intervention grading sheet (``literature_intervention_grading_cells``, one per experiment); G2 is the A106
final subscore (``literature_a106_subscore_cells``, across the experiments of one question). The operand sheets (B1 to
B38) are not graded against the annotation: their numbers reach a parent through the G1 sheet that selects them as
operands, so they produce no finding of their own (open point 4 of the feature table, read as "only G1 and G2").

Every feature is a number, a count, a boolean, a fixed vocabulary value or record references. Prose in a sheet
(conclusion, limitations, scope statement, rationale, quotations, reasons, units) stays in the sheet, inside the
Episode that saved it. A number that the sheet leaves unavailable (null) is left out of the feature record, so each
numeric field is optional and, when present, finite.
"""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_intervention_grading import (
    COMPONENTS as G1_COMPONENTS, CRITERIA, QUANTITY_KINDS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_intervention_storage import (
    PROVIDER as G1_PROVIDER, _rows as g1_rows)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore import (
    COMPONENTS as G2_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_subscore_storage import (
    PROVIDER as G2_PROVIDER)

G1_EVIDENCE_TYPE = 'intervention_response'
G2_EVIDENCE_TYPE = 'intervention_response_combined'
PREDICTION_KINDS = ('fixed_predictions_known_normal', 'fixed_predictions_estimated_normal',
                    'fixed_predictions_student_t', 'none')
VARIANCE_INTERPRETATIONS = ('known', 'estimated', 'unknown', 'none')
CRITERION_STATUSES = ('supported', 'unknown', 'conflicting', 'not_selected')

# name -> (validator, meaning). Validators: ('number', low, high) finite, optional (absent when the sheet has no
# value); ('count',); ('choice', options); ('boolean',); ('ref',) one record reference.
G1_FEATURES = {
    'evidence_type': (('choice', (G1_EVIDENCE_TYPE,)), 'The A106 evidence type of one intervention experiment'),
    'sheet_ref': (('ref',), 'The saved intervention grading sheet'),
    'experiment_ref': (('ref',), 'The assay reference of the graded experiment'),
    'assertion_ref': (('ref',), 'The proposed annotation (hypothesis) graded'),
    'comparison_ref': (('ref',), 'The named alternative (hypothesis)'),
    'quantity_kind': (('choice', tuple(QUANTITY_KINDS)), 'The scale of the measured effect'),
    'log_evidence_ratio': (('number', -math.inf, math.inf),
                           'Signed natural log evidence ratio; positive supports the annotation over the alternative'),
    'log_evidence_ratio_status': (('choice', ('populated', 'conditional', 'bounded', 'unavailable')),
                                  'Status of the log evidence ratio cell'),
    'measured_effect': (('number', -math.inf, math.inf), 'The measured effect on the quantity_kind scale (signal)'),
    'effect_is_censored': (('boolean',), 'Whether the measured effect is a bound, not a point'),
    'effect_variance': (('number', 0, math.inf), 'Variance of the measured effect (noise), squared effect scale'),
    'effect_over_noise': (('number', -math.inf, math.inf), 'Measured effect over the square root of its variance'),
    'assertion_prediction_error': (('number', -math.inf, math.inf), 'Effect minus the assertion prediction'),
    'alternative_prediction_error': (('number', -math.inf, math.inf), 'Effect minus the alternative prediction'),
    'recovery_deviation': (('number', -1, math.inf), 'Recovery minus 1, dimensionless'),
    'attributed_fraction': (('number', -math.inf, math.inf), 'Attributed over total signal'),
    'condition_response': (('number', 0, math.inf), 'Condition test over condition reference'),
    'prediction_model_kind': (('choice', PREDICTION_KINDS), 'The fixed-prediction model, or none'),
    'variance_interpretation': (('choice', VARIANCE_INTERPRETATIONS), 'How the variance is interpreted, or none'),
    **{'criterion_' + name: (('choice', CRITERION_STATUSES), 'Status of the ' + name + ' criterion')
       for name in CRITERIA},
    'unresolved_reason_count': (('count',), 'Reasons recorded on the log evidence ratio cell'),
    'prediction_reuses_observed_measurement': (('boolean',), 'A prediction reuses the observed measurement'),
    'uses_proposed_operand': (('boolean',), 'The log evidence ratio rests on a proposed operand'),
    'uses_synthetic_operand': (('boolean',), 'The log evidence ratio rests on a synthetic operand'),
    'uses_graph_derived_operand': (('boolean',), 'The log evidence ratio rests on a graph-derived operand'),
    'observed_measurement_count': (('count',), 'Observed measurements behind the effect and its variance'),
    'reference_sample_count': (('count',), 'Bound samples of the reference arm'),
    'intervention_sample_count': (('count',), 'Bound samples of the intervention arm'),
    'restoration_sample_count': (('count',), 'Bound samples of the restoration arm'),
    'biological_unit_witnessed_count': (('count',), 'Bound samples whose biological unit is witnessed'),
    'design_fields_witnessed_count': (('count',), 'Witnessed fields of the experimental design (0 to 14)'),
    'restoration_arm_witnessed': (('boolean',), 'The restoration arm of the design is witnessed'),
    'replication_witnessed': (('boolean',), 'The replication of the design is witnessed'),
    'shared_controls_witnessed': (('boolean',), 'The shared controls of the design are witnessed'),
    'is_revision': (('boolean',), 'The assessment revises an earlier sheet of the same experiment'),
}
G2_FEATURES = {
    'evidence_type': (('choice', (G2_EVIDENCE_TYPE,)), 'The A106 evidence type over several experiments'),
    'sheet_ref': (('ref',), 'The saved A106 final subscore sheet'),
    'subject_ref': (('ref',), 'The molecule the question is about'),
    'assertion_ref': (('ref',), 'The proposed annotation (hypothesis)'),
    'comparison_ref': (('ref',), 'The named alternative (hypothesis)'),
    'log_evidence_ratio': (('number', -math.inf, math.inf), 'The complete combined signed natural log evidence ratio'),
    'available_log_evidence_ratio': (('number', -math.inf, math.inf), 'The supported subtotal'),
    'status': (('choice', ('complete', 'partial', 'unavailable')), 'Status of the final subscore'),
    'experiment_count': (('count',), 'Original experiments of the question'),
    'scored_experiment_count': (('count',), 'Experiments with an available current score'),
    'missing_assessment_count': (('count',), 'Experiments without an assessment sheet'),
    'supporting_experiment_count': (('count',), 'Scored experiments with a positive log evidence ratio'),
    'opposing_experiment_count': (('count',), 'Scored experiments with a negative log evidence ratio'),
    'dependence_status': (('choice', ('independent', 'shared', 'unknown')), 'Declared dependence between experiments'),
    'dependence_witness_count': (('count',), 'Source witnesses of the dependence judgment'),
    'shared_observed_measurement': (('boolean',), 'Two experiments share an observed measurement'),
    'independence_unresolved': (('boolean',), 'Independence between experiments is unresolved'),
    'observed_measurement_count': (('count',), 'Observed measurements behind the selected scores'),
    'is_revision': (('boolean',), 'The subscore revises an earlier subscore of the same question'),
}


def validate(features, table):
    """Each feature against its validator. A violation raises ``ValueError``."""
    required = {name for name, (rule, _) in table.items() if rule[0] != 'number'}
    if not required <= set(features) <= set(table):
        raise ValueError('a106_finding_features_mismatch')
    for name, value in features.items():
        rule = table[name][0]
        if rule[0] == 'number':
            valid = type(value) in (int, float) and math.isfinite(value) and rule[1] <= value <= rule[2]
        elif rule[0] == 'count':
            valid = type(value) is int and value >= 0
        elif rule[0] == 'choice':
            valid = value in rule[1]
        elif rule[0] == 'boolean':
            valid = type(value) is bool
        else:
            valid = type(value) is list and len(value) == 1 and type(value[0]) is str
        if not valid:
            raise ValueError('a106_finding_feature_invalid:' + name)
    return features


def _numbers(features, values):
    """Put each finite number in; a null (unavailable) value stays out."""
    features.update({name: value for name, value in values.items() if value is not None})


def _saved(reader, sheet_ref):
    return json.loads(reader.get_artifact(reader.get(sheet_ref)['artifact_ref']))


def intervention_features(reader, sheet_ref):
    """The G1 finding of one saved intervention grading sheet, read from its cell rows."""
    cells = {row['component']: row for row in g1_rows(_saved(reader, sheet_ref), sheet_ref, G1_COMPONENTS)}
    score, effect, variance = (cells['source_log_evidence_ratio'], cells['measured_effect'],
                               cells['effect_variance'])
    shared = score
    model = shared['prediction_model']
    design, samples = shared['experimental_design'], shared['sample_bindings']
    features = {
        'evidence_type': G1_EVIDENCE_TYPE, 'sheet_ref': [sheet_ref], 'experiment_ref': [shared['experiment_ref']],
        'assertion_ref': [shared['assertion_ref']], 'comparison_ref': [shared['comparison_ref']],
        'quantity_kind': shared['quantity_kind'], 'log_evidence_ratio_status': score['status'],
        'effect_is_censored': effect['status'] == 'bounded',
        'prediction_model_kind': 'none' if model is None else model['kind'],
        'variance_interpretation': 'none' if model is None else model['variance_interpretation'],
        **{'criterion_' + name: (shared['interpretations'][name]['status'] if name in shared['interpretations']
                                 else 'not_selected') for name in CRITERIA},
        'unresolved_reason_count': len(score['reasons']),
        'prediction_reuses_observed_measurement': 'prediction_reuses_observed_measurement' in score['reasons'],
        'uses_proposed_operand': 'proposed' in score['input_origins'],
        'uses_synthetic_operand': 'synthetic' in score['input_origins'],
        'uses_graph_derived_operand': 'graph_derived' in score['input_origins'],
        'observed_measurement_count': len(shared['evidence_measurement_keys']),
        'reference_sample_count': sum(row['arm'] == 'reference' for row in samples),
        'intervention_sample_count': sum(row['arm'] == 'intervention' for row in samples),
        'restoration_sample_count': sum(row['arm'] == 'restoration' for row in samples),
        'biological_unit_witnessed_count': sum(row['biological_unit'] is not None for row in samples),
        'design_fields_witnessed_count': sum(value is not None for value in design.values()),
        'restoration_arm_witnessed': design['restoration_arm'] is not None,
        'replication_witnessed': design['replication'] is not None,
        'shared_controls_witnessed': design['shared_controls'] is not None,
        'is_revision': shared['experiment_assessment']['revises_sheet_ref'] is not None,
    }
    over = None
    if effect['value'] is not None and variance['value'] is not None and variance['value'] > 0:
        over = effect['value'] / math.sqrt(variance['value'])
    _numbers(features, {'log_evidence_ratio': score['value'], 'measured_effect': effect['value'],
                        'effect_variance': variance['value'], 'effect_over_noise': over,
                        **{name: cells[name]['value'] for name in (
                            'assertion_prediction_error', 'alternative_prediction_error', 'recovery_deviation',
                            'attributed_fraction', 'condition_response')}})
    return validate(features, G1_FEATURES)


def subscore_features(reader, sheet_ref):
    """The G2 finding of one saved A106 final subscore sheet, read from its cell."""
    saved = _saved(reader, sheet_ref)
    cell = saved['sheet']['cells'][G2_COMPONENTS[0]]
    scored = [row for row in cell['selected_components']
              if row['value'] is not None and row['status'] in ('populated', 'conditional')]
    features = {
        'evidence_type': G2_EVIDENCE_TYPE, 'sheet_ref': [sheet_ref], 'subject_ref': [cell['subject_ref']],
        'assertion_ref': [cell['assertion_ref']], 'comparison_ref': [cell['comparison_ref']],
        'status': cell['status'], 'experiment_count': len(cell['experiments']),
        'scored_experiment_count': len(scored),
        'missing_assessment_count': sum(row['sheet_ref'] is None for row in cell['experiments']),
        'supporting_experiment_count': sum(row['value'] > 0 for row in scored),
        'opposing_experiment_count': sum(row['value'] < 0 for row in scored),
        'dependence_status': cell['dependence']['status'],
        'dependence_witness_count': len(cell['dependence']['witnesses']),
        'shared_observed_measurement': 'shared_observed_measurement' in cell['unavailable_reasons'],
        'independence_unresolved': 'between_experiment_independence_unresolved' in cell['unavailable_reasons'],
        'observed_measurement_count': len(cell['evidence_measurement_keys']),
        'is_revision': cell['revises_subscore_ref'] is not None,
    }
    _numbers(features, {'log_evidence_ratio': cell['value'], 'available_log_evidence_ratio': cell['available_value']})
    return validate(features, G2_FEATURES)


def saved_sheets(outcomes, tools):
    """The sheets this Episode saved with ``tools``, in order: a completed population outcome names one; the
    outcome of the automatic score judgment lists one outcome per judgment (``judgments``)."""
    results = []
    for outcome in outcomes:
        if outcome['kind'] != 'tool' or outcome['tool'] not in tools:
            continue
        for value in outcome['outcome'].get('judgments', [outcome['outcome']]):
            if value.get('status') == 'completed':
                results.append(value['result']['sheet_ref'])
    return list(dict.fromkeys(results))


def own_findings(reader, outcomes):
    """The A106 finding of the sheets this Episode saved: the features of each current G1 sheet and of each current
    G2 sheet (the latter saved by ``literature.a106.finalize`` or by the automatic score judgment)."""
    g1 = [ref for ref in saved_sheets(outcomes, ('literature_intervention_grading_populate',))
          if reader.get(ref)['provider'] == G1_PROVIDER]
    g1_revised = {_saved(reader, ref)['selection']['experiment_assessment']['revises_sheet_ref'] for ref in g1}
    g2 = [ref for ref in saved_sheets(outcomes, ('literature_a106_finalize', 'literature_a106_score_judgment'))
          if reader.get(ref)['provider'] == G2_PROVIDER]
    revised = {_saved(reader, ref)['selection']['revises_subscore_ref'] for ref in g2}
    return {'intervention_assessments': [intervention_features(reader, ref) for ref in g1
                                                 if ref not in g1_revised],
            'a106_subscores': [subscore_features(reader, ref) for ref in g2 if ref not in revised]}


def merged_findings(own, returned):
    """The own finding and the findings the children returned, one entry per sheet (first seen kept): sheets are
    listed side by side, never combined."""
    result = {}
    for key in ('intervention_assessments', 'a106_subscores'):
        entries = {}
        for finding in (own, *returned):
            for features in finding[key]:
                entries.setdefault(features['sheet_ref'][0], features)
        result[key] = list(entries.values())
    return result


FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean', 'ref': 'record_refs'}


def feature_form(table):
    """The record form of one feature table: a choice field for a vocabulary, an optional number for a value the
    sheet may leave unavailable, a record_refs field (one reference) for a record."""
    from method_loop import ChoiceField, Field, RecordForm
    fields = {}
    for name, (rule, meaning) in table.items():
        if rule[0] == 'choice':
            fields[name] = ChoiceField('text', meaning, rule[1])
        else:
            fields[name] = Field(FIELD_TYPES[rule[0]], meaning, required=rule[0] != 'number')
    return RecordForm(fields)


def finding_form():
    """The A106 finding: the features of each current G1 sheet and of each current G2 sheet, each its own entry."""
    from method_loop import Field, RecordForm
    return RecordForm({
        'intervention_assessments': Field('list', 'One entry per current intervention grading sheet (G1)',
                                          items=feature_form(G1_FEATURES)),
        'a106_subscores': Field('list', 'One entry per current A106 final subscore sheet (G2)',
                                items=feature_form(G2_FEATURES)),
    })
