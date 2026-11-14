"""A108's private contextual contribution record and attribution binding."""
from copy import deepcopy
import math
from gene_annotation_episode.episodic_workflow.root.a108.communication import plain
VERSION = 'signed_root_axis_scalar_mappings_v1'

def _result(value, *, formula, inputs, reasons=(), status=None):
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < -1 or (value > 1)):
        raise ValueError('root_scalar_invalid_native_number')
    return {'version': VERSION, 'axis': 'A108', 'value': value, 'status': status or ('unavailable' if value is None else 'available'), 'direction': 'unknown' if value is None else 'support' if value > 0 else 'opposition' if value < 0 else 'measured_neutral', 'formula': formula, 'native_inputs': deepcopy(inputs), 'missing_inputs': list(dict.fromkeys(reasons)), 'interpretation': 'defined_root_index; not_a_function_probability'}

def bind_contribution(scalar, *, annotation, subject, scope, transfer, source_refs=()):
    return {**scalar, 'proposed_annotation_ref': annotation['id'], 'subject_ref': subject, 'scope': plain(scope), 'transfer': plain(transfer), 'source_refs': list(source_refs)}

def require_attribution(scalar, *, missing):
    if not missing:
        return deepcopy(scalar)
    return {**deepcopy(scalar), **_result(None, formula=scalar['formula'], inputs=scalar['native_inputs'], reasons=(*scalar['missing_inputs'], *missing))}
