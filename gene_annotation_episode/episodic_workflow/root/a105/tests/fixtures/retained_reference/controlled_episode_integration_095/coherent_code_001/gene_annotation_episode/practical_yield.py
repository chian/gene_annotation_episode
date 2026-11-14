"""Opt-in yield estimates for practical assignments with verified endpoints.

The ordinary estimator handles unfinished work unchanged. A completion proof
only changes the forecast for further work on this same assignment; it does
not change a completed action's credit or manufacture another observation.
Runtime supplies the original completion identity, and the caller's verifier
checks the proof against authoritative persisted practical state.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import math
from numbers import Real

from method_loop.durable import canonical
from method_loop.identities import UnitRef

from .completion_evidence import validate_completion_evidence
from .numerical import (NumericBand, YieldEstimate, YieldParameters,
                        estimate_score_yield)


ESTIMATOR_VERSION = "verified_practical_endpoint_yield_v1"
PROOF_VERSION = "practical_completion_v1"
_PROOF_FIELDS = frozenset({"version", "run_id", "episode_id", "assignment_sha256",
    "endpoint", "operation_key", "receipt_sha256", "validation_keys"})
_RUNTIME_FIELDS = frozenset({"unit_ref", "action_index"})


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def _sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(character in "0123456789abcdef" for character in value))


def _callable_name(callback):
    declared = callback if hasattr(callback, "__qualname__") else type(callback)
    return f"{declared.__module__}.{declared.__qualname__}"


def _proof(value, context, turns):
    """Check the proof envelope against this actual completed-action identity."""
    if not isinstance(value, Mapping) or set(value) != _PROOF_FIELDS | _RUNTIME_FIELDS:
        raise ValueError("invalid_practical_completion_proof")
    try:
        value = json.loads(canonical(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("invalid_practical_completion_proof") from error
    if (value["version"] != PROOF_VERSION
            or any(not _text(value[key]) for key in ("run_id", "episode_id", "operation_key"))
            or any(not _sha256(value[key]) for key in ("assignment_sha256", "receipt_sha256"))
            or not isinstance(value["endpoint"], str)
            or value["endpoint"] not in {"usable_handoff", "completed_job_outputs"}
            or not isinstance(value["validation_keys"], list)
            or any(not _text(key) for key in value["validation_keys"])
            or len(set(value["validation_keys"])) != len(value["validation_keys"])
            or type(value["action_index"]) is not int or value["action_index"] < 0):
        raise ValueError("invalid_practical_completion_proof")
    try:
        unit = UnitRef.from_record(value["unit_ref"])
        packet = validate_completion_evidence(context.get("current_completion_evidence"))
    except (TypeError, ValueError) as error:
        raise ValueError("practical_completion_identity_conflict") from error
    # Episode UnitRef indices are zero-based completed own actions. These
    # practical assignments retain one controller epoch for that same history.
    if (turns == 0 or unit.unit_index != turns - 1
            or unit.episode_id != value["episode_id"]
            or any(value[key] != packet[key] for key in ("run_id", "episode_id", "unit_ref"))
            or value["action_index"] != packet["original_decision_index"]):
        raise ValueError("practical_completion_identity_conflict")
    return {key: value[key] for key in _PROOF_FIELDS}


class PracticalYieldEstimator:
    """Contextual estimator selected explicitly for practical execution roles.

    ``verify_completion`` receives only the eight-field persisted proof, never
    runtime's ``unit_ref`` or ``action_index``. It must return a literal boolean.
    Neither this callback nor its verifier should execute or inspect new work
    during replay. Absent or unverified completion uses ``base_estimate``.
    """

    def __init__(self, verify_completion, base_estimate=estimate_score_yield):
        if not callable(verify_completion) or not callable(base_estimate):
            raise TypeError("practical_yield_requires_callable_bindings")
        self.verify_completion = verify_completion
        self.base_estimate = base_estimate

    def as_record(self):
        return {"version": ESTIMATOR_VERSION,
            "interface": "raw_credit_history_parameters_aligned_execution_contexts_v1",
            "base_estimator": _callable_name(self.base_estimate),
            "completion_verifier": _callable_name(self.verify_completion),
            "completion_proof": PROOF_VERSION,
            "terminal_forecast": "exact_zero_after_verified_assignment_completion",
            "continuation": "existing_available_upper_bound_lte_configured_cost",
            "raw_history": "unchanged_one_observation_per_completed_own_action"}

    def __call__(self, raw_signed_history, parameters, aligned_original_contexts):
        history, contexts = tuple(raw_signed_history), tuple(aligned_original_contexts)
        if len(history) != len(contexts):
            raise ValueError("practical_yield_requires_aligned_action_contexts")
        # The terminal branch must preserve the default estimator's input
        # validity requirements even when no statistical fit is needed.
        for value in history:
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
                raise ValueError("marginal credit must be a finite real number")
        if not isinstance(parameters, YieldParameters):
            raise TypeError("practical_yield_requires_YieldParameters")
        latest = contexts[-1] if contexts else None
        if latest is not None and not isinstance(latest, Mapping):
            raise TypeError("practical_yield_context_requires_mapping_or_none")
        supplied = None if latest is None else latest.get("practical_completion")
        if supplied is None:
            return self.base_estimate(history, parameters)
        proof = _proof(supplied, latest, len(history))
        verified = self.verify_completion(json.loads(canonical(proof)))
        if type(verified) is not bool:
            raise TypeError("practical_completion_verifier_requires_boolean")
        if not verified:
            return self.base_estimate(history, parameters)
        return YieldEstimate(len(history), NumericBand.exact(0), parameters,
            {"completed_acquisition_turns": len(history), "history_used": len(history),
             "fitting_scope": "verified_assignment_endpoint",
             "completion_proof": proof,
             "completion_unit_ref": dict(supplied["unit_ref"]),
             "completion_action_index": supplied["action_index"]},
            estimator_binding=self.as_record())


__all__ = ["PracticalYieldEstimator", "ESTIMATOR_VERSION", "PROOF_VERSION"]
