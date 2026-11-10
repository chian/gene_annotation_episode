"""Declared contribution records and shared composition arithmetic.

These functions do not acquire evidence, establish attribution, or replace an
axis calculator. Callers supply current, received results for one scientific
question and original target scope. Missing information is never opposition.
"""
from copy import deepcopy
import math


VERSION = 'signed_root_axis_scalar_mappings_v1'
AXES = ('A101', 'A102', 'A103', 'A104', 'A105', 'A106', 'A107', 'A108', 'A110')
UNSIGNED_AXES = AXES[:4]


def _number(value, *, minimum=None, maximum=None):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or minimum is not None and value < minimum
            or maximum is not None and value > maximum):
        raise ValueError('root_scalar_invalid_native_number')
    return value


def _result(axis, value, *, formula, inputs, reasons=(), status=None):
    if axis not in AXES:
        raise ValueError('root_scalar_unknown_axis')
    if value is not None:
        _number(value, minimum=0 if axis in UNSIGNED_AXES else -1, maximum=1)
    return {'version': VERSION, 'axis': axis, 'value': value,
        'status': status or ('unavailable' if value is None else 'available'),
        'direction': ('unknown' if value is None else 'support' if value > 0
            else 'opposition' if value < 0 else 'measured_neutral'),
        'formula': formula, 'native_inputs': deepcopy(inputs),
        'missing_inputs': list(dict.fromkeys(reasons)),
        'interpretation': 'defined_root_index; not_a_function_probability'}


def bind_contribution(scalar, *, annotation, subject, scope, transfer, source_refs=()):
    """Record an owner's declared identity/applicability without inferring it."""
    from .communication import plain
    return {**scalar, 'proposed_annotation_ref': annotation['id'], 'subject_ref': subject,
        'scope': plain(scope), 'transfer': plain(transfer), 'source_refs': list(source_refs)}


def correspondence_scalar(axis, value, *, measured):
    """Preserve A101--A104 conventions; missing correspondence is not refutation."""
    if axis not in UNSIGNED_AXES or type(measured) is not bool:
        raise ValueError('root_scalar_unsigned_correspondence_required')
    if value is not None:
        _number(value, minimum=0, maximum=1)
    return _result(axis, value if measured else None,
        formula='existing_received_axis_correspondence',
        inputs={'value': value, 'measured': measured},
        reasons=() if measured else ('no_received_native_measurement',))








def prerequisite_scalar(axis, values, *, required, missing=(), inputs=None, formula=None):
    """Conjoin explicit necessary tests; a real counterexample can refute it.

    Unknown tests are not assigned -1 or silently dropped from positive support.
    A received negative test can oppose the stated conjunction even while
    another test is unresolved. All tests must concern this same qualified use.
    """
    if axis not in {'A107', 'A110'}:
        raise ValueError('root_scalar_necessary_test_axis_required')
    required = tuple(required)
    if not required or len(set(required)) != len(required) or set(values) - set(required):
        raise ValueError('root_scalar_explicit_unique_necessary_tests_required')
    known = {key: _number(value, minimum=-1, maximum=1)
        for key, value in values.items() if value is not None}
    reasons = [*missing, *(name for name in required if name not in known)]
    minimum = min(known.values()) if known else None
    value = minimum if not reasons or minimum is not None and minimum < 0 else None
    return _result(axis, value, formula=formula or 'min(qualified_required_component_indices)',
        inputs={'required': list(required), 'values': dict(values), 'native': inputs},
        reasons=reasons, status='partial' if value is not None and reasons else None)




def require_attribution(scalar, *, missing):
    """Unresolved source-to-target application cannot support or refute the target."""
    if not missing:
        return deepcopy(scalar)
    return {**deepcopy(scalar), **_result(scalar['axis'], None, formula=scalar['formula'],
        inputs=scalar['native_inputs'], reasons=(*scalar['missing_inputs'], *missing))}


def combine_scalars(scalars):
    """Separate support/opposition products, with explicit unknown dimensions."""
    rows = {}
    for row in scalars:
        axis = row['axis']
        if axis not in AXES or axis in rows or row.get('version') != VERSION:
            raise ValueError('root_scalar_unique_versioned_axes_required')
        value = row['value']
        if value is not None:
            _number(value, minimum=0 if axis in UNSIGNED_AXES else -1, maximum=1)
        rows[axis] = deepcopy(row)
    from .evidence_root import signed_offset_volume
    vector = {axis: rows[axis]['value'] if axis in rows else None for axis in AXES}
    return {'version': VERSION, 'axis_components': vector,
        'axis_status': {axis: rows[axis]['status'] if axis in rows else 'unavailable' for axis in AXES},
        'axis_results': rows, **signed_offset_volume(vector),
        'minimum': -(2 ** (len(AXES) - len(UNSIGNED_AXES)) - 1),
        'interpretation': 'signed_bounded_evidence_indices; not_calibrated_function_probability',
        'missing': 'unknown_dimensions_are_neutral_factors_not_opposing_observations'}
