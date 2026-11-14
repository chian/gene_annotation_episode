"""Render only delivered A105 assay-grade components and their meanings."""
from collections.abc import Mapping

from .literature_assay_grading import EVALUATION_SCOPE, CRITERION_QUESTIONS, ASSAY_TYPE_LABELS

TYPE_NAMES = ASSAY_TYPE_LABELS


def is_row(value):
    return (isinstance(value, Mapping) and value.get('evaluation_scope') == EVALUATION_SCOPE
        and isinstance(value.get('sheet_ref'), str) and isinstance(value.get('component'), str))


def render_received(parts, rows, *, section, table, public_records=None):
    groups = {}
    experiments = {}
    records = public_records or {}
    for row in rows:
        if not is_row(row):
            raise ValueError('assay_grading_display_contract_mismatch')
        groups.setdefault(row['sheet_ref'], []).append(row)
    for index, selected in enumerate(groups.values(), 1):
        first = selected[0]
        experiment = first.get('experiment_ref')
        experiment_number = experiments.setdefault(experiment or first['sheet_ref'], len(experiments) + 1)
        label = records.get(experiment, {}).get('label') if experiment else None
        section(parts, 'A105 assay-type assessment', table(('Meaning', 'Value'), [
            ('Experiment', label or ('Experiment ' + str(experiment_number) if experiment else 'Historical experiment identity unrecorded')),
            ('Stored assessment', index),
            ('Assay type', TYPE_NAMES[first['assay_type']]),
            ('Measured quantity', first['quantity_kind'].replace('_', ' ')),
            ('Score scope', 'Experimental support for the selected reference functional assertion'),
        ]))
        section(parts, 'Requested A105 numerical grading components', table(
            ('Dimension', 'Component', 'Value', 'Unit', 'Status', 'Calculation', 'Meaning', 'Unresolved reasons'),
            [(row['dimension'], row['component'], row['value'], row['unit'], row['status'],
              row['formula'], row['meaning'], ', '.join(row['reasons']) or 'none') for row in selected]))
        bounded = [row for row in selected if row.get('bound') is not None]
        if bounded:
            section(parts, 'Recorded measurement limits', table(
                ('Component', 'Relation', 'Lower limit', 'Upper limit', 'Unit'),
                [(row['component'], row['bound']['relation'], row['bound']['lower'],
                  row['bound']['upper'], row['unit']) for row in bounded]))
        interpretations = {}
        for row in selected:
            interpretations.update(row['interpretations'])
        section(parts, 'Assay considerations affecting interpretation', table(
            ('Consideration', 'Recorded interpretation'),
            [(CRITERION_QUESTIONS[name], value['status']) for name, value in interpretations.items()]))
        conditions = list(dict.fromkeys(condition for row in selected for condition in row['conditions']))
        if conditions:
            section(parts, 'Conditions of the numerical assessment', '\n'.join(conditions))
        model = next((row['prediction_model'] for row in selected if row['prediction_model'] is not None), None)
        if model is not None:
            section(parts, 'Evidence comparison model', table(('Model', 'Variance meaning'),
                [(model['kind'], model['variance_interpretation'])]))
        section(parts, 'Dependence and scoring scope',
            'Each experiment retains its own populated sheet. Further assessments of the same experiment '
            'retain that experiment identity; they are not additional independent experiments. '
            'Components derived from the same measurements are dependent views. '
            'The evidence comparison describes the declared measurement model; it is not '
            'a probability of function, target-transfer score or final annotation credit.')


__all__ = ['is_row', 'render_received']
