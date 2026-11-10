"""Present original A106 saved results beside their recorded action credit.

Only original own outcomes and actual admitted child values enter this pure
projection. No source, sheet or child history is opened and no scientific value,
revision choice, score or credit is calculated.
"""
from collections.abc import Mapping
import json

from .literature_a106_render import _copy, assessment_groups, is_assessment, is_final


def _nodes(value):
    if isinstance(value, Mapping):
        yield value
        if is_assessment(value) or is_final(value):
            return
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _nodes(child)


def completed_work_result(selection, outcome, received_records):
    """Keep the exact saved experiment/quantity/version with its result values."""
    if not isinstance(selection, Mapping) or not isinstance(outcome, Mapping):
        return None
    direct = {name: value for name, value in outcome.items() if name != 'received_axis_results'}
    related = str(selection.get('tool', '')).startswith((
        'literature.intervention_grading.', 'literature.a106.')) or any(
        row.get('option_id') == 'A106'
        or row.get('id') == 'A106' and row.get('slot') == 'evidence_axis'
        for row in _nodes(selection))
    assessments, finals, seen = [], [], set()
    for row in _nodes(direct):
        if not (is_assessment(row) or is_final(row)):
            continue
        identity = json.dumps(_copy(row), sort_keys=True, ensure_ascii=False, allow_nan=False)
        if identity in seen:
            continue
        seen.add(identity)
        related = True
        if is_assessment(row):
            assessments.append(row)
        else:
            finals.append(row)
    if not related:
        return None
    results = [{'result': 'Saved A106 intervention subscoring sheet', **group}
               for group in assessment_groups(assessments)]
    limitations = []
    for row in finals:
        final = {name: _copy(value) for name, value in row.items()
                 if name != 'selected_components'}
        results.append({'result': 'Saved A106 main evidence scoring sheet',
            **final, 'selected_experiments': assessment_groups(row['selected_components']),
            'value_meaning': 'Conditional signed experimental evidence; not original action earned credit'})
        if row.get('unavailable_reasons'):
            limitations.append({'sheet_ref': row['sheet_ref'],
                'missing_inputs_or_conditions': _copy(row['unavailable_reasons'])})
    for row in assessments:
        if row.get('reasons'):
            limitations.append({'sheet_ref': row['sheet_ref'],
                'experiment_ref': row['experiment_ref'], 'component': row['component'],
                'missing_inputs_or_conditions': _copy(row['reasons'])})
    if not results:
        limitations.append({'reason':
            'No A106 numerical cells were present in this original action or its admitted child return'})
    return {'axis': 'A106', 'results': results, 'limitations': limitations}
