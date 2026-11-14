"""Private A105 contribution records and attribution binding."""
from __future__ import annotations
from copy import deepcopy
import math
VERSION = 'signed_root_axis_scalar_mappings_v1'

def _number(value, *, minimum=None, maximum=None):
    if type(value) not in (int, float) or not math.isfinite(value) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError('root_scalar_invalid_native_number')
    return value

def _result(value, *, formula, inputs, reasons=(), status=None):
    if value is not None:
        _number(value, minimum=-1, maximum=1)
    return {'version': VERSION, 'axis': 'A105', 'value': value, 'status': status or ('unavailable' if value is None else 'available'), 'direction': 'unknown' if value is None else 'support' if value > 0 else 'opposition' if value < 0 else 'measured_neutral', 'formula': formula, 'native_inputs': deepcopy(inputs), 'missing_inputs': list(dict.fromkeys(reasons)), 'interpretation': 'defined_root_index; not_a_function_probability'}

def bind_contribution(scalar, *, annotation, subject, scope, transfer, source_refs=()):
    """Record declared identity/applicability without inferring it."""
    from gene_annotation_episode.episodic_workflow.root.a105.communication import plain
    return {**scalar, 'proposed_annotation_ref': annotation['id'], 'subject_ref': subject, 'scope': plain(scope), 'transfer': plain(transfer), 'source_refs': list(source_refs)}

def require_attribution(scalar, *, missing):
    """Unresolved source-to-target application cannot support or refute the target."""
    if not missing:
        return deepcopy(scalar)
    return {**deepcopy(scalar), **_result(None, formula=scalar['formula'], inputs=scalar['native_inputs'], reasons=(*scalar['missing_inputs'], *missing))}
