"""Private A110 contribution records and attribution binding."""
from copy import deepcopy
import math

VERSION = 'signed_root_axis_scalar_mappings'


def _number(value, *, minimum=None, maximum=None):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or minimum is not None and value < minimum
            or maximum is not None and value > maximum):
        raise ValueError('root_scalar_invalid_native_number')
    return value


def _result(value, *, formula, inputs, reasons=(), status=None):
    if value is not None:
        _number(value, minimum=-1, maximum=1)
    return {'version': VERSION, 'axis': 'A110', 'value': value,
        'status': status or ('unavailable' if value is None else 'available'),
        'direction': ('unknown' if value is None else 'support' if value > 0
            else 'opposition' if value < 0 else 'measured_neutral'),
        'formula': formula, 'native_inputs': deepcopy(inputs),
        'missing_inputs': list(dict.fromkeys(reasons)),
        'interpretation': 'defined_root_index; not_a_function_probability'}


def bind_contribution(scalar, *, annotation, subject, scope, transfer, source_refs=()):
    """Record declared identity/applicability without inferring it."""
    from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.communication import plain
    return {**scalar, 'proposed_annotation_ref': annotation['id'], 'subject_ref': subject,
        'scope': plain(scope), 'transfer': plain(transfer), 'source_refs': list(source_refs)}


def require_attribution(scalar, *, missing):
    """Unresolved source-to-target application cannot support or refute the target."""
    if not missing:
        return deepcopy(scalar)
    return {**deepcopy(scalar), **_result(None, formula=scalar['formula'],
        inputs=scalar['native_inputs'], reasons=(*scalar['missing_inputs'], *missing))}


def prerequisite_scalar(values, *, required, missing=(), inputs=None, formula=None):
    """Conjoin explicit necessary tests; a real counterexample can refute it.

    Unknown tests are not assigned -1 or silently dropped from positive support.
    A received negative test can oppose the stated conjunction even while
    another test is unresolved. All tests must concern this same qualified use.
    """
    required = tuple(required)
    if not required or len(set(required)) != len(required) or set(values) - set(required):
        raise ValueError('root_scalar_explicit_unique_necessary_tests_required')
    known = {key: _number(value, minimum=-1, maximum=1)
        for key, value in values.items() if value is not None}
    reasons = [*missing, *(name for name in required if name not in known)]
    minimum = min(known.values()) if known else None
    value = minimum if not reasons or minimum is not None and minimum < 0 else None
    return _result(value, formula=formula or 'min(qualified_required_component_indices)',
        inputs={'required': list(required), 'values': dict(values), 'native': inputs},
        reasons=reasons, status='partial' if value is not None and reasons else None)
