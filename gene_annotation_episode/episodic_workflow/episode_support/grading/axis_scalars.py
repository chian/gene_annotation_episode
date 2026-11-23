"""A102's private contribution and correspondence records."""
from copy import deepcopy
import math


VERSION = 'signed_root_axis_scalar_mappings'
AXIS = 'A102'


def _number(value, *, minimum=None, maximum=None):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or minimum is not None and value < minimum
            or maximum is not None and value > maximum):
        raise ValueError('root_scalar_invalid_native_number')
    return value


def _result(value, *, formula, inputs, reasons=(), status=None):
    if value is not None:
        _number(value, minimum=0, maximum=1)
    return {'version': VERSION, 'axis': AXIS, 'value': value,
        'status': status or ('unavailable' if value is None else 'available'),
        'direction': ('unknown' if value is None else 'support' if value > 0
            else 'opposition' if value < 0 else 'measured_neutral'),
        'formula': formula, 'native_inputs': deepcopy(inputs),
        'missing_inputs': list(dict.fromkeys(reasons)),
        'interpretation': 'defined_root_index; not_a_function_probability'}


def bind_contribution(scalar, *, annotation, subject, scope, transfer, source_refs=()):
    from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import plain
    return {**scalar, 'proposed_annotation_ref': annotation['id'], 'subject_ref': subject,
        'scope': plain(scope), 'transfer': plain(transfer), 'source_refs': list(source_refs)}


def correspondence_scalar(value, *, measured):
    if type(measured) is not bool:
        raise ValueError('root_scalar_unsigned_correspondence_required')
    if value is not None:
        _number(value, minimum=0, maximum=1)
    return _result(value if measured else None,
        formula='existing_received_axis_correspondence',
        inputs={'value': value, 'measured': measured},
        reasons=() if measured else ('no_received_native_measurement',))


def require_attribution(scalar, *, missing):
    if not missing:
        return deepcopy(scalar)
    return {**deepcopy(scalar), **_result(None, formula=scalar['formula'],
        inputs=scalar['native_inputs'], reasons=(*scalar['missing_inputs'], *missing))}
