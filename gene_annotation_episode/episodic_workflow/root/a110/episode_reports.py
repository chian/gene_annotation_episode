"""Small runtime facts available through a parent's existing typed form.

This projection never estimates, scores, schedules, chooses continuation or
reads global history. It copies selected fields of an already closed episode's
numerical state. Private diagnostics and action histories stay inside the child.
"""
from __future__ import annotations

from copy import deepcopy


def _object(fields, *, nullable=False):
    return {"type": ["object", "null"] if nullable else "object", "properties": fields,
            "required": list(fields), "additionalProperties": False}


_BAND = _object({
    "value": {"type": "number", "description": "The original band point in this child's configured controller units."},
    "lower": {"type": "number", "description": "The original band's lower coordinate; read status_code before interpreting it."},
    "upper": {"type": "number", "description": "The original band's upper coordinate; read status_code before interpreting it."},
    "status_code": {"type": "integer", "enum": [0, -1, -2],
        "description": "0 normal; -1 insufficient observations; -2 unidentifiable. Coded coordinates are not negative forecasts."},
    "uncertainty_code": {"type": "integer", "enum": [-1, 0, 1, 2],
        "description": "-1 unavailable; 0 exact; 1 Chebyshev; 2 Laplace approximation. The code does not establish calibrated coverage."},
    "alpha": {"type": "number", "description": "Original band parameter: -1 unavailable; 0 exact; otherwise the configured tail parameter."},
})
_YIELD = _object({
    "completed_actions": {"type": "integer", "minimum": 0,
        "description": "Completed own actions at this child's level; an investigation commissioned by it counts once."},
    "expected_next_gain": _BAND,
    "continuation_cost": {"type": "number", "minimum": 0,
        "description": "The actual child's decision threshold in its configured controller units."},
    "stop_requested": {"type": "boolean",
        "description": "The child's controller decision, not a parent instruction, job cancellation or scientific completion."},
}, nullable=True)


def report_sources():
    """Return independent schema values, never a caller-mutable singleton."""
    return {"episode_yield": {"type": ["object", "null"],
        "meaning": ("Recorded closing local numerical forecast and continuation decision, "
            "in the child's configured controller units. It is not task credit, a job ETA, "
            "a parent instruction or goal completion. Null when the controller does not "
            "expose the supported typed numerical state. Normal status is 0; -1 means "
            "insufficient observations and -2 means unidentifiable, not negative predicted gain."),
        "report_schema": {**deepcopy(_YIELD), "x-source": "episode_yield"}}}


def closing_yield(record):
    """Copy the actual final band, without refitting or expanding audit archives."""
    from .numerical import NumericBand, SignedNumericBand, YieldState

    state = getattr(record, "controller_state", None)
    if not isinstance(state, YieldState):
        return None
    band = state.estimate.expected_next_gain
    if not isinstance(band, (NumericBand, SignedNumericBand)):
        return None
    return {"completed_actions": record.units_consumed,
        "expected_next_gain": {field: getattr(band, field) for field in _BAND["properties"]},
        "continuation_cost": state.decision.continuation_cost,
        "stop_requested": state.decision.stop}
