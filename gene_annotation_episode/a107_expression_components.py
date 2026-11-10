"""Descriptive matched-condition expression components over supplied values.

Source criteria are conditional on their declared scale, calibration and
conditions. No source discovery, normalization, imputation, independence test,
p value, biological-absence claim or target transfer is performed here.
"""
from copy import deepcopy
import math

from .component_axis_native_contracts import PROFILES, validate_source


VERSION = PROFILES['A107']


def require(condition, code):
    if not condition:
        raise ValueError('a107_expression_'+code)


def index(rows, field):
    result = {}
    for position, row in enumerate(rows):
        key = row[field]
        require(key not in result, 'duplicate_'+field)
        result[key] = (position, row)
    return result


def criterion_comparison(measurement, criterion, quantity, sample):
    missing = []
    if any(criterion[key] != quantity[key] for key in ('unit', 'scale', 'normalization')):
        missing.append('criterion_quantity_unit_scale_or_normalization_mismatch')
    if criterion['calibration_condition_key'] is None:
        missing.append('calibration_condition_unreported')
    elif criterion['calibration_condition_key'] != sample['condition_key']:
        missing.append('calibration_condition_mismatch')
    if criterion['control_source_locator'] is None:
        missing.append('calibration_control_source_unreported')
    if criterion['value'] is None:
        missing.append('criterion_value_unreported')
    value, bound = measurement['value'], measurement.get('reported_bound')
    if value is None and bound is None:
        missing.append('measurement_unreported')
    satisfied = None
    if not missing:
        threshold, operator = criterion['value'], criterion['operator']
        if value is not None:
            satisfied = value > threshold if operator == 'greater_than' else value >= threshold
        elif bound['operator'] in {'greater_than', 'greater_or_equal'}:
            if bound['value'] > threshold or bound['value'] == threshold and (
                    operator == 'greater_or_equal' or bound['operator'] == 'greater_than'):
                satisfied = True
        elif bound['value'] < threshold or bound['value'] == threshold and (
                operator == 'greater_than' or bound['operator'] == 'less_than'):
            satisfied = False
        if satisfied is None:
            missing.append('reported_censor_domain_crosses_criterion')
    return {**deepcopy(criterion), 'criterion_satisfied': satisfied,
        'status': 'available' if satisfied is not None else 'unavailable', 'missing': missing,
        'formula': 'declared_strict_or_inclusive_inequality; censor_domain_must_imply_the_result',
        'interpretation': 'conditional_assay_criterion_comparison; not_biological_absence_or_function',
        'source_qualification': 'calibration_and_condition_labels_are_source_assertions; no_independent_source_verification'}


def calculate(document, selection):
    validate_source('A107', document)
    features, samples = index(document['features'], 'id'), index(document['samples'], 'id')
    left, right = selection['left_feature_id'], selection['right_feature_id']
    require(left in features and (right is None or right in features and left != right),
        'selected_feature_or_distinct_comparison_features_required')
    ids = selection['sample_ids'] or [key for key, (_, row) in samples.items()
        if row['condition_key'] == selection['condition_key']]
    require(len(ids) == len(set(ids)) and set(ids) <= set(samples), 'selected_samples_unknown_or_repeated')
    require(all(samples[key][1]['condition_key'] == selection['condition_key'] for key in ids),
        'selected_sample_condition_mismatch')
    measured = {}
    for position, row in enumerate(document['measurements']):
        require(row['feature_id'] in features and row['sample_id'] in samples, 'unknown_measurement_endpoint')
        key = row['feature_id'], row['sample_id']
        require(key not in measured, 'duplicate_feature_sample_measurement; retain_distinct_samples')
        require((row['value'] is None) == (row['missing_reason'] is not None), 'missing_value_reason_required')
        if row.get('reported_bound') is not None:
            require(row['value'] is None and row['missing_reason'] is not None,
                'censored_measurement_must_not_supply_an_imputed_point')
            bound = row['reported_bound']
            if document['quantity']['nonnegative'] and bound['operator'] in {'less_than', 'less_or_equal'}:
                require(bound['value'] >= 0 and not (bound['value'] == 0 and bound['operator'] == 'less_than'),
                    'censor_domain_conflicts_with_declared_nonnegative_quantity')
        require(row['value'] is None or math.isfinite(row['value']), 'finite_measurement_required')
        if document['quantity']['nonnegative'] and row['value'] is not None:
            require(row['value'] >= 0, 'negative_nonnegative_quantity')
        measured[key] = (position, row)
    criteria, criterion_ids = {}, set()
    for position, row in enumerate(document.get('detection_criteria', [])):
        require(row['id'] not in criterion_ids, 'duplicate_criterion_identity')
        criterion_ids.add(row['id'])
        require(row['feature_id'] in features and row['sample_id'] in samples, 'unknown_criterion_endpoint')
        criteria.setdefault((row['feature_id'], row['sample_id']), []).append(
            {**row, 'pointer': '/detection_criteria/'+str(position)})
    pairs, complete = [], []
    for key in ids:
        sample_position, sample = samples[key]
        row = {'sample_id': key, 'sample': deepcopy(sample), 'sample_pointer': '/samples/'+str(sample_position)}
        for side, feature in (('left', left), ('right', right)):
            item = measured.get((feature, key))
            row[side] = {'value': None, 'missing_reason': 'second_feature_not_selected' if feature is None else 'measurement_row_unreported',
                'measurement_id': None, 'source_locator': None, 'pointer': None} if item is None else {
                    **deepcopy(item[1]), 'pointer': '/measurements/'+str(item[0])}
            row[side]['detection_criteria'] = [criterion_comparison(row[side], criterion,
                document['quantity'], sample) for criterion in criteria.get((feature, key), [])]
        row['complete'] = all(row[side]['value'] is not None for side in ('left', 'right'))
        if row['complete']:
            complete.append(row)
        pairs.append(row)
    # Scaling before centering avoids overflowing finite, large native values.
    # Pearson is invariant to these positive per-variable scale factors.
    correlation, reason = None, 'second_feature_not_selected' if right is None else 'fewer_than_two_complete_pairs'
    if len(complete) >= 2:
        x, y = ([row[side]['value'] for row in complete] for side in ('left', 'right'))
        sx, sy = max(map(abs, x)), max(map(abs, y))
        if sx and sy:
            x, y = [value/sx for value in x], [value/sy for value in y]
            mx, my = math.fsum(x)/len(x), math.fsum(y)/len(y)
            dx, dy = [value-mx for value in x], [value-my for value in y]
            xx, yy = math.fsum(value*value for value in dx), math.fsum(value*value for value in dy)
            if xx and yy:
                raw = math.fsum(a*b for a, b in zip(dx, dy))/math.sqrt(xx)/math.sqrt(yy)
                require(math.isfinite(raw) and abs(raw) <= 1+1e-12, 'correlation_numerical_range')
                correlation, reason = max(-1., min(1., raw)), None
            else:
                reason = 'constant_selected_feature'
        else:
            reason = 'constant_selected_feature'
    unit_groups = {}
    measured_samples = [row for row in pairs if any(row[side]['value'] is not None or
        row[side].get('reported_bound') is not None for side in ('left', 'right'))]
    for row in measured_samples:
        unit = row['sample']['biological_unit_id']
        if unit is not None:
            unit_groups.setdefault(unit, []).append(row['sample_id'])
    repeated = {key: values for key, values in unit_groups.items() if len(values) > 1}
    detection_rows = {side: [criterion for row in pairs for criterion in row[side]['detection_criteria']]
        for side in ('left', 'right')}
    return {'version': VERSION, 'dataset_id': document['dataset_id'], 'origin': document['origin'],
        'selection': deepcopy(selection), 'quantity': deepcopy(document['quantity']),
        'features': {side: None if key is None else {**deepcopy(features[key][1]), 'pointer': '/features/'+str(features[key][0])}
            for side, key in (('left', left), ('right', right))},
        'sample_scope': {'condition_key': selection['condition_key'],
            'declared_organism_ids': sorted({samples[key][1]['organism_id'] for key in ids
                if samples[key][1]['organism_id'] is not None}),
            'unknown_organism_samples': [key for key in ids if samples[key][1]['organism_id'] is None],
            'declared_genome_accessions': sorted({samples[key][1]['genome_accession'] for key in ids
                if samples[key][1].get('genome_accession') is not None}),
            'unknown_genome_samples': [key for key in ids if samples[key][1].get('genome_accession') is None],
            'meaning': 'declared_sample_metadata; no_automatic_target_sample_or_organism_identity'},
        'pairs': pairs, 'components': {
            'selected_sample_count': {'value': len(pairs), 'unit': 'samples', 'status': 'available'},
            'complete_pair_count': {'value': len(complete), 'unit': 'pairs', 'status': 'available'},
            'point_measurement_counts': {side: {'value': None if feature is None else sum(
                row[side]['value'] is not None for row in pairs), 'unit': 'measurements',
                'status': 'inapplicable' if feature is None else 'available'}
                for side, feature in (('left', left), ('right', right))},
            'detection_criterion_counts': {side: {
                'evaluated': sum(row['status'] == 'available' for row in rows),
                'satisfied': sum(row['criterion_satisfied'] is True for row in rows),
                'not_satisfied': sum(row['criterion_satisfied'] is False for row in rows),
                'unknown': sum(row['criterion_satisfied'] is None for row in rows),
                'unit': 'declared_criteria; not_independent_samples_or_expression_probability'}
                for side, rows in detection_rows.items()},
            'pearson_r': {'value': correlation, 'unit': 'dimensionless',
                'status': 'available' if reason is None else 'unavailable', 'missing_reason': reason,
                'formula': 'sum((x-mean(x))*(y-mean(y)))/sqrt(sum((x-mean(x))^2)*sum((y-mean(y))^2))',
                'conditional_on': ['declared_quantity_scale_and_normalization',
                    'complete_selected_pairs', 'same_declared_condition', 'descriptive_not_sampling_inference']}},
        'dependence': {'repeated_biological_units': repeated,
            'biological_unit_group_basis': 'selected_samples_with_any_retained_point_or_censor_measurement',
            'unknown_biological_unit_samples': [row['sample_id'] for row in measured_samples
                if row['sample']['biological_unit_id'] is None],
            'measurement_ids': [row[side]['measurement_id'] for row in pairs for side in ('left', 'right')],
            'distinct_rows_do_not_establish_independence': True},
        'detection_criteria': detection_rows,
        'limitations': ['No imputation, normalization, p value, confidence interval or causal interpretation.',
            'Positive native values do not establish expression above a validated detection threshold.',
            'Reported censor bounds remain bounds and are excluded from point-based Pearson correlation.',
            'Source-reported thresholds require the declared matching quantity and calibration conditions; below-threshold is not gene absence.',
            'Measured transcript, protein, reporter and functional activity remain different quantities.',
            'File feature identities require per-use correspondence to the target and required component.',
            'A correlation across selected samples does not establish physical interaction or a required partner.'],
        'combined_scientific_score': None}
