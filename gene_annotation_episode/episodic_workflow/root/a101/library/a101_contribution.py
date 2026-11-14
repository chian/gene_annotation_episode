"""A101 contribution projection from its native correspondence sheet."""
from copy import deepcopy
import math

VERSION = 'signed_root_axis_scalar_mappings_v1'

def _number(value, *, minimum=None, maximum=None):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or minimum is not None and value < minimum
            or maximum is not None and value > maximum):
        raise ValueError('root_scalar_invalid_native_number')
    return value


def _result(value, *, formula, inputs, reasons=(), status=None):
    if value is not None:
        _number(value, minimum=0, maximum=1)
    return {'version': VERSION, 'axis': 'A101', 'value': value,
        'status': status or ('unavailable' if value is None else 'available'),
        'direction': ('unknown' if value is None else 'support' if value > 0
            else 'opposition' if value < 0 else 'measured_neutral'),
        'formula': formula, 'native_inputs': deepcopy(inputs),
        'missing_inputs': list(dict.fromkeys(reasons)),
        'interpretation': 'defined_root_index; not_a_function_probability'}


def bind_contribution(scalar, *, annotation, subject, scope, transfer, source_refs=()):
    """Record A101's declared identity/applicability without inferring it."""
    from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
    return {**scalar, 'proposed_annotation_ref': annotation['id'], 'subject_ref': subject,
        'scope': plain(scope), 'transfer': plain(transfer), 'source_refs': list(source_refs)}


def correspondence_scalar(value, *, measured):
    """Preserve A101 correspondence; missing measurements are not refutation."""
    if type(measured) is not bool:
        raise ValueError('root_scalar_unsigned_correspondence_required')
    if value is not None:
        _number(value, minimum=0, maximum=1)
    return _result(value if measured else None,
        formula='existing_received_axis_correspondence',
        inputs={'value': value, 'measured': measured},
        reasons=() if measured else ('no_received_native_measurement',))


def require_attribution(scalar, *, missing):
    """Unresolved source-to-target application cannot support or refute the target."""
    if not missing:
        return deepcopy(scalar)
    return {**deepcopy(scalar), **_result(None, formula=scalar['formula'],
        inputs=scalar['native_inputs'], reasons=(*scalar['missing_inputs'], *missing))}
