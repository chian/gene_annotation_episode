"""Pure A102 result presentation for an original completed action.

The common work report owns action identity and recorded earned credit. This
adapter only selects numerical results already present in that action or an
existing receiver-authorized view. It reads no Store, source or child history,
and neither scores nor transfers structural evidence.
"""
from collections.abc import Mapping
from copy import deepcopy

from .literature_structure_calculations import COMPONENTS as EXPERIMENTAL_COMPONENTS


_COMPARISON_QUANTITIES = {
    'B': ('Native structural correspondence', 'dimensionless'),
    'rmsd_A': ('Paired C-alpha RMSD', 'angstrom'),
    'n_pairs': ('Paired C-alpha positions', 'pairs'),
    'target_length': ('Selected target length', 'residue'),
    'reference_length': ('Selected reference length', 'residue'),
    'target_coverage': ('Target coverage', 'fraction'),
    'reference_coverage': ('Reference coverage', 'fraction'),
    'symmetric_coverage': ('Symmetric coverage', 'fraction'),
    'rmsd_rounding_interval_A': ('Native-print RMSD rounding interval', 'angstrom'),
    'B_rounding_interval': ('Native-print correspondence rounding interval', 'dimensionless'),
}


def _mappings(value):
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _mappings(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _mappings(child)


def _references(value):
    """Use actual returned handles, not matching names or target identity."""
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _references(child)
    elif isinstance(value, str) and value.startswith((
            'source_', 'artifact_', 'reference_', 'hypothesis_', 'assessment_')):
        yield value


def _axis_selected(selection):
    return any(row.get('option_id') == 'A102' or
        row.get('id') == 'A102' and row.get('slot') == 'evidence_axis'
        or row.get('version') == 'a102_structural_evidence_v2'
        for row in _mappings(selection))


def _comparison(row):
    grade = row.get('grade', row)
    if not isinstance(grade, Mapping):
        return None
    components = grade.get('components')
    if not isinstance(components, Mapping) or 'B' not in components:
        return None
    if not isinstance(row.get('grade'), Mapping) and 'comparison_source_ref' not in row:
        return None
    result = {'evidence_path': 'comparative',
        'result': 'Saved structural comparison',
        'quantities': [{'name': meaning, 'value': deepcopy(components[name]), 'unit': unit}
            for name, (meaning, unit) in _COMPARISON_QUANTITIES.items()
            if name in components]}
    for name in ('target_ref', 'reference_ref', 'target_binding_ref', 'target_scope',
            'target_model', 'reference_model', 'eligible', 'exclusion', 'producer'):
        if name in grade:
            result[name] = deepcopy(grade[name])
    for name in ('comparison_source_ref', 'source_ref', 'grading_artifact_ref'):
        if name in row:
            result[name] = deepcopy(row[name])
    if 'comparison_ref' in row:
        result['comparison_ref'] = row['comparison_ref']
    if 'precision_status' in components:
        result['precision_status'] = components['precision_status']
    if 'function_specific' in grade:
        result['function_specific'] = deepcopy(grade['function_specific'])
    return result


def _functional(row):
    sources = ('feature_source_ref', 'contrast_source_ref', 'interface_source_ref')
    if not any(name in row for name in sources):
        return None
    names = (*sources, 'target_ref', 'target_scope', 'function_ref',
        'comparison_source_ref', 'actual_measured_binding_ref', 'actual_reference_binding_ref',
        'B', 'E', 'F', 'A102_f', 'raw_E', 'score', 'E_bounds', 'F_bounds',
        'features', 'constraints', 'missing_reason', 'reasons', 'conditions')
    return {'evidence_path': 'comparative', 'result': 'Saved function-specific structural component',
        **{name: deepcopy(row[name]) for name in names if name in row}}


def _experimental(row):
    if (row.get('component') not in EXPERIMENTAL_COMPONENTS
            or row.get('evaluation_scope') != 'conditional_deposited_model_geometry'):
        return None
    names = ('component', 'value', 'lower', 'upper', 'unit', 'status', 'origin',
        'formula_code', 'evaluation_scope', 'operand_source_kind',
        'unavailable_reason', 'conditional_on', 'sheet_ref', 'evidence_source_ref',
        'coordinate_source_ref', 'validation_source_ref', 'model_number',
        'geometry_definition', 'local_validation_definition', 'validation_binding',
        'protein_ref', 'construct_ref', 'experiment_ref', 'partner_ref',
        'experimental_system_ref', 'condition_ref', 'bound_kind',
        'unconditional_uncertainty', 'local_validation_granularity')
    return {'evidence_path': 'experimental',
        'result': 'Delivered conditional experimental-structure component',
        **{name: deepcopy(row[name]) for name in names if name in row}}


def completed_work_result(selection, outcome, received_records):
    """Return concrete A102/A111 results, without deriving another judgment.

    `received_axis_results` is supplied by the common report from already
    authorized receiver context. A result there is associated only through a
    source/sheet handle in the original outcome or admitted child form. Later
    sibling evidence and matching target names cannot enter this action.
    """
    if not isinstance(outcome, Mapping):
        return None
    direct = {key: value for key, value in outcome.items() if key != 'received_axis_results'}
    allowed = set(_references(direct))
    original_cells = {(row['sheet_ref'], row['component']) for row in _mappings(direct)
        if _experimental(row) is not None and row.get('sheet_ref')}
    related = _axis_selected(selection) or str(selection.get('tool', '')).startswith('structure.')
    results, limitations, seen = [], [], set()

    def append(row, *, received=False):
        nonlocal related
        comparative = _comparison(row) or _functional(row)
        experimental = _experimental(row)
        result = comparative or experimental
        if result is None:
            return
        identifiers = [row.get(name) for name in
            ('comparison_source_ref', 'source_ref', 'sheet_ref', 'feature_source_ref',
             'contrast_source_ref', 'interface_source_ref') if row.get(name)]
        if received and not allowed.intersection(identifiers):
            return
        if received and experimental is not None and (
                row.get('sheet_ref'), row.get('component')) not in original_cells:
            # Current receiver views may include more cells delivered later
            # from this same immutable sheet. They are not this action's result.
            return
        related = True
        identity = (result['evidence_path'], tuple(identifiers), row.get('component'))
        if identifiers and identity in seen:
            return
        if identifiers:
            seen.add(identity)
        results.append(result)
        if result.get('unavailable_reason'):
            limitations.append({'sheet_ref': result.get('sheet_ref'),
                'component': result.get('component'),
                'reason': result['unavailable_reason']})
        if result.get('exclusion'):
            limitations.append({'comparison_source_ref': row.get('comparison_source_ref', row.get('source_ref')),
                'reason': result['exclusion']})

    for row in _mappings(direct):
        append(row)
    for row in _mappings(outcome.get('received_axis_results', ())):
        append(row, received=True)
    if not related:
        return None
    # Keep explicitly delivered child-local progress with its original meaning;
    # the common work report supplies the receiving parent's earned credit.
    admitted = outcome.get('admitted_child_return')
    if isinstance(admitted, Mapping):
        progress = {name: admitted[name] for name in ('structural_credit', 'controller_progress')
            if name in admitted}
        if progress:
            results.append({'result': 'Delivered child-local progress',
                'original_fields': deepcopy(progress),
                'meaning': 'Child task units; receiving-parent earned credit is reported separately'})
    if not results:
        limitations.append({'reason': 'No numerical structural result in this action or its admitted resolved results'})
    return {'axis': 'A102', 'results': results, 'limitations': limitations}
