"""The user's ordinary A105 sum/max rules over selected experiment scores.

Selection identifies existing numerical components. This module neither creates
new quality scales nor changes the selected measurements' units or meanings.
"""
from copy import deepcopy
import math

from .domain import ContractError, obj, validate_schema
from .literature_assay_grading import COMPONENTS as GRADE_COMPONENTS
from .literature_assay_grading_storage import assay_grading_cells_schema

VERSION = 'a105_across_experiment_aggregation_v1'
SCOPE = 'a105_across_experiment_aggregation'
COMPONENTS = ('reliability', 'validity', 'relevance', 'attribution', 'overall')
REDUCERS = dict(reliability='sum', validity='sum', relevance='max', attribution='max', overall='sum')
DIMENSIONS = {name: 'experimental_evidence' if name == 'overall' else name for name in COMPONENTS}


def _reference(namespace, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference',
        'x-reference-namespace': namespace}


def _strings():
    return {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}


def aggregation_population_schema():
    selector = obj({'sheet_ref': _reference('source'),
        'component': {'enum': list(GRADE_COMPONENTS)}})
    return obj({'assertion_ref': _reference('hypothesis'),
        'comparison_ref': _reference('hypothesis', True),
        'experiments': {'type': 'array', 'items': obj({
            'experiment_ref': _reference('reference'),
            'metrics': obj({name: {'anyOf': [deepcopy(selector), {'type': 'null'}]}
                for name in COMPONENTS})})}})


def aggregation_cell_schema():
    references = {'type': 'array', 'items': _reference('reference'), 'uniqueItems': True}
    contributors = deepcopy(assay_grading_cells_schema())
    contributors.pop('x-source', None)
    return obj({'component': {'enum': list(COMPONENTS)},
        'dimension': {'enum': list(DIMENSIONS.values())}, 'evaluation_scope': {'const': SCOPE},
        'assertion_ref': _reference('hypothesis'), 'comparison_ref': _reference('hypothesis', True),
        'comparison_binding': {'enum': ['parent_declared', 'not_declared']},
        'reducer': {'enum': ['sum', 'max']},
        'value': {'type': ['number', 'null']},
        'available_value': {'type': ['number', 'null']},
        'status': {'enum': ['complete', 'partial', 'unavailable']},
        'unit': {'type': 'string'}, 'input_units': _strings(),
        'source_component_names': _strings(), 'source_meanings': _strings(),
        'selected_experiment_refs': deepcopy(references),
        'available_experiment_refs': deepcopy(references),
        'missing_experiment_refs': deepcopy(references),
        'missing_inputs': {'type': 'array', 'items': obj({
            'experiment_ref': _reference('reference'), 'reason': {'type': 'string'}})},
        'selected_components': contributors,
        'measurement_keys': _strings(),
        'source_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'uniqueItems': True},
        'input_origins': _strings(), 'conditions': _strings(),
        'formula': {'type': 'string'}, 'meaning': {'type': 'string'},
        'annotation_credit': {'type': 'null'}})


def aggregation_sheet_schema():
    return obj({'version': {'const': VERSION}, 'axis': {'const': 'A105'},
        'evaluation_scope': {'const': SCOPE},
        'assertion_ref': _reference('hypothesis'), 'comparison_ref': _reference('hypothesis', True),
        'experiment_refs': {'type': 'array', 'items': _reference('reference'), 'uniqueItems': True},
        'cells': obj({name: aggregation_cell_schema() for name in COMPONENTS}),
        'annotation_credit': {'type': 'null'}})


def _unique(values):
    return list(dict.fromkeys(values))


def _fail(reason):
    raise ContractError('a105_aggregation_' + reason)


def aggregate_a105(arguments, source_cells):
    """Aggregate every selected experiment once, retaining unresolved inputs.

The supplied rows must already be possessed and authenticated by the storage
adapter. Scientific judgments and the choice of numerical component belong to
the parent. This function applies only the user's declared reducers.
"""
    validate_schema(arguments, aggregation_population_schema())
    validate_schema(source_cells, assay_grading_cells_schema())
    args, native = deepcopy(arguments), deepcopy(source_cells)
    experiments = [entry['experiment_ref'] for entry in args['experiments']]
    if len(set(experiments)) != len(experiments):
        _fail('duplicate_experiment')
    rows = {}
    for row in native:
        key = row['sheet_ref'], row['component']
        if key in rows:
            _fail('duplicate_source_component')
        rows[key] = row
    expected = {(selection['sheet_ref'], selection['component'])
        for experiment in args['experiments'] for selection in experiment['metrics'].values()
        if selection is not None}
    if set(rows) != expected:
        _fail('selected_components_not_received')
    cells = {}
    for metric in COMPONENTS:
        selected, available, missing = [], [], []
        for experiment in args['experiments']:
            selection = experiment['metrics'][metric]
            exp_ref = experiment['experiment_ref']
            if selection is None:
                missing.append({'experiment_ref': exp_ref, 'reason': 'metric_component_not_selected'})
                continue
            row = rows[selection['sheet_ref'], selection['component']]
            if row.get('experiment_ref') != exp_ref:
                _fail('experiment_binding_mismatch')
            if row['assertion_ref'] != args['assertion_ref']:
                _fail('assertion_binding_mismatch')
            if row['dimension'] != DIMENSIONS[metric]:
                _fail('metric_dimension_mismatch')
            selected.append(deepcopy(row))
            if row['value'] is None or row['status'] not in ('populated', 'conditional'):
                missing.append({'experiment_ref': exp_ref, 'reason': 'selected_component_' + row['status']})
            elif type(row['value']) not in (int, float) or not math.isfinite(row['value']):
                _fail('finite_component_required')
            else:
                available.append(row)
        value = None
        calculation_failure = None
        if available:
            try:
                values = [row['value'] for row in available]
                value = math.fsum(values) if REDUCERS[metric] == 'sum' else max(values)
                if not math.isfinite(value):
                    calculation_failure, value = 'numerical_range', None
            except (OverflowError, ValueError):
                calculation_failure, value = 'numerical_range', None
        complete = bool(experiments) and not missing and calculation_failure is None
        units = _unique(row['unit'] for row in selected)
        source_refs = _unique(ref for row in selected for ref in [row['sheet_ref'], *row['source_refs']])
        conditions = _unique(condition for row in selected for condition in row['conditions'])
        conditions.extend(('user_defined_' + REDUCERS[metric] + '_of_selected_experiment_values',
            'native_component_meanings_and_units_unchanged', 'no_weighting_or_orthogonality_adjustment'))
        if args['comparison_ref'] is not None:
            conditions.append('comparison_identity_is_parent_declared_not_inferred_from_native_predictions')
        if calculation_failure is not None:
            conditions.append(calculation_failure)
        if not experiments:
            conditions.append('no_experiments_selected')
        cells[metric] = {'component': metric, 'dimension': DIMENSIONS[metric], 'evaluation_scope': SCOPE,
            'assertion_ref': args['assertion_ref'], 'comparison_ref': args['comparison_ref'],
            'comparison_binding': 'not_declared' if args['comparison_ref'] is None else 'parent_declared',
            'reducer': REDUCERS[metric], 'value': value if complete else None, 'available_value': value,
            'status': 'complete' if complete else 'partial' if value is not None else 'unavailable',
            'unit': units[0] if len(units) == 1 else 'mixed_native_units' if units else 'unknown',
            'input_units': units, 'source_component_names': _unique(row['component'] for row in selected),
            'source_meanings': _unique(row['meaning'] for row in selected),
            'selected_experiment_refs': list(experiments),
            'available_experiment_refs': [row['experiment_ref'] for row in available],
            'missing_experiment_refs': [item['experiment_ref'] for item in missing],
            'missing_inputs': missing, 'selected_components': selected,
            'measurement_keys': _unique(key for row in selected for key in row['measurement_keys']),
            'source_refs': source_refs,
            'input_origins': _unique(origin for row in selected for origin in row['input_origins']),
            'conditions': conditions,
            'formula': REDUCERS[metric] + '(selected_' + metric + '_component_per_experiment)',
            'meaning': ('The user-defined ' + REDUCERS[metric] + ' of the explicitly selected ' + metric
                + ' components across experiments. Source component meanings are retained; no probability or new quality scale is inferred.'),
            'annotation_credit': None}
    result = {'version': VERSION, 'axis': 'A105', 'evaluation_scope': SCOPE,
        'assertion_ref': args['assertion_ref'], 'comparison_ref': args['comparison_ref'],
        'experiment_refs': experiments, 'cells': cells, 'annotation_credit': None}
    validate_schema(result, aggregation_sheet_schema())
    return result


__all__ = ['VERSION', 'SCOPE', 'COMPONENTS', 'REDUCERS', 'DIMENSIONS',
    'aggregation_population_schema', 'aggregation_cell_schema', 'aggregation_sheet_schema', 'aggregate_a105']


def annotation_scalar(cell):
    """Reuse the existing tanh-half-log-ratio convention after axis aggregation."""
    from collections.abc import Mapping
    from .root_axis_scalars import _number, _result
    axis = 'A105'
    if not isinstance(cell, Mapping):
        raise ValueError('root_scalar_log_evidence_input_required')
    expected = 'overall' if axis == 'A105' else 'experimental_subscore'
    if cell.get('component') != expected:
        raise ValueError('root_scalar_final_axis_component_required')
    value = cell.get('value')
    if value is not None:
        _number(value)
    complete = cell.get('status') == 'complete' and value is not None
    if complete and (cell.get('unit') != ('dimensionless' if axis == 'A105' else 'natural_log_ratio')
            or axis == 'A105' and cell.get('source_component_names') != ['source_log_evidence_ratio']):
        raise ValueError('root_scalar_natural_log_ratio_required')
    return _result(axis, math.tanh(value / 2) if complete else None,
        formula='tanh(current_complete_axis_log_evidence_ratio/2)', inputs=cell,
        reasons=() if complete else ('complete_axis_log_evidence_ratio_unavailable',))
