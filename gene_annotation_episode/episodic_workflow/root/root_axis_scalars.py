"""Received contribution records and root composition arithmetic.

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
