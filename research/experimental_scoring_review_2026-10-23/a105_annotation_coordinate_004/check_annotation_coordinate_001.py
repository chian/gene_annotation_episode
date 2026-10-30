"""Research-only A105 interface arithmetic; no scorer or reader is installed.

All assay inputs are explicitly synthetic. The production imports below only
exercise existing pure arithmetic and projection methods on in-memory fixtures.
The only file written is arithmetic_001.json beside this script.
"""
from __future__ import annotations

from contextlib import nullcontext
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.credit import (  # noqa: E402
    AXES, AnnotationScoringUnavailable, HypervolumeParameters,
    project_credit, softened_hypervolume,
)
from gene_annotation_episode.runtime import Workflow  # noqa: E402


def close(left, right, tolerance=1e-11):
    assert math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance), (left, right)


def signed_profile(effect, variance):
    """Known-normal scalar half-line comparison, as explicitly assumed here."""
    assert variance > 0 and math.isfinite(effect) and math.isfinite(variance)
    return math.copysign(effect * effect / (2 * variance), effect) if effect else 0.0


def signed_b(score):
    return math.tanh(score / 2)


def proposed_zero_based_coordinate(signed_value):
    """Explicit UNADOPTED one-sided projection; never modifies signed inputs."""
    if signed_value is None:
        return None
    assert -1 <= signed_value <= 1
    return max(0.0, signed_value)


def proposed_anchor_coordinate(score, anchor=0.2):
    """Alternative, unadopted coordinate convention, not posterior odds."""
    if score is None:
        return None
    x = math.log(anchor / (1 - anchor)) + score
    return 1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x))


def pooled_independent(effects, variances):
    weights = [1 / value for value in variances]
    precision = sum(weights)
    mean = sum(w * y for w, y in zip(weights, effects)) / precision
    variance = 1 / precision
    return {
        "effect": mean,
        "variance": variance,
        "S": signed_profile(mean, variance),
        "Q": sum(w * (y - mean) ** 2 for w, y in zip(weights, effects)),
    }


POLICY = HypervolumeParameters((("A105", 1.0), ("fixture_other", 1.0)), epsilon=0.2)


def fixture_volume(value):
    """No missing-data default: uncomputed point remains None."""
    return None if value is None else softened_hypervolume(
        {"A105": value, "fixture_other": 0.6}, POLICY)


def row(name, effect=None, variance=None, score=None, **other):
    if score is None and effect is not None:
        score = signed_profile(effect, variance)
    b = None if score is None else signed_b(score)
    coordinate = proposed_zero_based_coordinate(b)
    return dict(name=name, effect=effect, variance=variance, S=score, B=b,
                proposed_coordinate=coordinate, illustrative_H=fixture_volume(coordinate),
                alternative_anchor_0_2_coordinate=proposed_anchor_coordinate(score), **other)


V = 0.11124225
rows = [
    row("unknown_evidence", reason="no measured contrast or usable error model"),
    row("zero_contrast", effect=0.0, variance=V),
    row("positive_contrast", effect=0.68, variance=V),
    row("reversed_specificity", effect=-0.68, variance=V),
]
positive = rows[2]
equal_conflict = pooled_independent([0.68, -0.68], [V, V])
unequal_conflict = pooled_independent([0.68, -0.34], [V, V])
confirmation = pooled_independent([0.68, 0.78], [V, V])
for name, value in (("equal_conflict", equal_conflict),
                    ("unequal_conflict", unequal_conflict),
                    ("independent_confirmation", confirmation)):
    rows.append(row(name, effect=value["effect"], variance=value["variance"], Q=value["Q"]))

# One underlying observation returned twice remains one original measurement.
representations = [("original_experiment_1", "measurement_1", 0.68, V),
                   ("original_experiment_1", "measurement_1", 0.68, V)]
distinct = {(experiment, measurement): (effect, variance)
            for experiment, measurement, effect, variance in representations}
assert len(distinct) == 1
duplicate = pooled_independent([value[0] for value in distinct.values()],
                               [value[1] for value in distinct.values()])
rows.append(row("duplicate_return", effect=duplicate["effect"], variance=duplicate["variance"],
                representation_count=2, original_observation_count=1))
close(rows[-1]["proposed_coordinate"], positive["proposed_coordinate"])

# Shared covariance reduces information gain without adding a second penalty.
shared_covariance = 0.08564225
shared_variance = (V + shared_covariance) / 2
rows.append(row("shared_calibration_confirmation", effect=0.73, variance=shared_variance,
                covariance=shared_covariance))

# A conjunction differs from two independent claims. These are standardized,
# independent unit-variance normal contrasts, both explicitly required by H+.
rows.append(row("compound_both_measured_positive", score=min(2 ** 2 / 2, 3 ** 2 / 2),
                contrasts=[2.0, 3.0], covariance=[[1.0, 0.0], [0.0, 1.0]]))
rows.append(row("compound_one_negative", score=-(2 ** 2 / 2),
                contrasts=[-2.0, 3.0], covariance=[[1.0, 0.0], [0.0, 1.0]]))
rows.append(row("narrower_claim_only", effect=2.0, variance=1.0,
                broader_compound_coordinate=None,
                broader_missing="second required molecular endpoint"))

tiny = row("precise_tiny_preference", effect=0.001, variance=0.00001 ** 2,
           measured_ratio=math.exp(0.001), percent_preference=100 * math.expm1(0.001))
rows.append(tiny)
rows.append(row("same_tiny_data_twofold_claim_only_for_illustration",
                effect=0.001 - math.log(2), variance=0.00001 ** 2,
                required_ratio=2.0,
                warning="twofold is a synthetic claim boundary, never a default"))

# Censored nonnegative activity example: the observation is Y < L, not Y=0.
limit, noise = 0.1, 0.2
phi = lambda z: math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
Phi = lambda z: math.erfc(-z / math.sqrt(2)) / 2
ell = lambda a: -(0.68 - a) ** 2 / (2 * V) + math.log(Phi((limit - a) / noise))
derivative = lambda a: (0.68 - a) / V - phi((limit - a) / noise) / (noise * Phi((limit - a) / noise))
lo, hi = 0.0, 0.68
assert derivative(lo) > 0 > derivative(hi)
for _ in range(100):
    mid = (lo + hi) / 2
    if derivative(mid) > 0:
        lo = mid
    else:
        hi = mid
maximum = (lo + hi) / 2
close(derivative(maximum), 0, tolerance=1e-10)
rows.append(row("positive_plus_sensitive_nondetection", effect=maximum, variance=None,
                score=ell(maximum) - ell(0), limit=limit, noise=noise,
                nondetection_95_percent_upper=limit + NormalDist().inv_cdf(0.95) * noise))

# Relevance worker's separately labeled uncalibrated numerical convention.
components = {"sequence": 2 * 240 / (300 + 320), "structure": min(0.90, 0.85),
              "site": 8 / 10, "evolution": 85 / 100,
              "system": math.exp(-0.5 * (7 ** 2 / 100 + 0.5 ** 2))}
R = sum(components.values()) / len(components)
observed = {key: value for key, value in components.items() if key != "evolution"}
R_available = sum(observed.values()) / len(observed)
R_bounds = (sum(observed.values()) / 5, (sum(observed.values()) + 1) / 5)
conventional = {
    "source_S": math.log(19), "source_B": 0.9,
    "components": components, "equal_family_weights": True,
    "complete_R": R, "signed_complete_index": 0.9 * R,
    "proposed_complete_coordinate": proposed_zero_based_coordinate(0.9 * R),
    "partial_R_available": R_available, "observed_weight_fraction": 4 / 5,
    "partial_R_full_identification_bounds": R_bounds,
    "signed_partial_conditional_index": 0.9 * R_available,
    "proposed_partial_conditional_coordinate": 0.9 * R_available,
    "partial_full_coordinate_bounds": [0.9 * bound for bound in R_bounds],
    "reversed_signed_index": -0.9 * R,
    "reversed_proposed_coordinate": proposed_zero_based_coordinate(-0.9 * R),
    "no_measured_correspondence_coordinate": None,
}
close(signed_b(conventional["source_S"]), 0.9)

errors = {}


def records_error(name, callback, expected):
    try:
        callback()
    except expected as error:
        errors[name] = {"type": type(error).__name__, "message": str(error)}
    else:
        raise AssertionError("expected rejection: " + name)


assert AXES == ()
records_error("retired_categorical_projector", lambda: project_credit(), AnnotationScoringUnavailable)
records_error("hypervolume_without_explicit_policy", lambda: softened_hypervolume({"A105": 0.2}),
              AnnotationScoringUnavailable)
records_error("hypervolume_missing_axis", lambda: softened_hypervolume({"A105": 0.2}, POLICY), ValueError)
for label, value in (("null", None), ("negative", -0.1), ("above_one", 1.1),
                     ("boolean", True), ("nan", math.nan), ("infinite", math.inf)):
    records_error("hypervolume_" + label,
                  lambda value=value: softened_hypervolume({"A105": value, "fixture_other": 0.6}, POLICY),
                  ValueError)

# Exercise only the existing projection boundary, without a Store, episode,
# provider, run, report, controller, or durable state.
host = SimpleNamespace(store=SimpleNamespace(read_snapshot=nullcontext))
projection = Workflow.projection_view(host, lambda store, scope: {
    "credit": 0.25, "axis_components": {"A105": 0.6}}, {})
assert projection == {"credit": 0.25, "axis_components": {"A105": 0.6}}
records_error("runtime_scalar_null", lambda: Workflow.projection_view(
    host, lambda store, scope: {"credit": None}, {}), TypeError)
records_error("runtime_scalar_nan", lambda: Workflow.projection_view(
    host, lambda store, scope: {"credit": math.nan}, {}), ValueError)
assert Workflow.annotation_context(SimpleNamespace(project_annotation_score=None), {}) == {}
# Runtime itself requires finiteness, not [0,1]; the retained H enforces the
# stricter coordinate domain. This is observation of the interface, not policy.
assert Workflow.projection_view(host, lambda store, scope: -3.0, {}) == {"credit": -3.0}

for item in rows:
    value = item["proposed_coordinate"]
    if value is not None:
        close(item["illustrative_H"], 0.1 + (17 / 30) * value)
        assert 0 <= value <= 1
assert rows[0]["proposed_coordinate"] is None and rows[0]["illustrative_H"] is None
close(rows[1]["proposed_coordinate"], 0.0)
close(rows[3]["S"], -positive["S"])
close(rows[3]["B"], -positive["B"])
assert rows[3]["proposed_coordinate"] == 0 and rows[3]["B"] < 0
assert equal_conflict["S"] == 0 and equal_conflict["Q"] > 0
assert 0 < unequal_conflict["S"] < positive["S"]
assert fixture_volume(0) < positive["illustrative_H"]
close(signed_profile(1000 * 0.68, 1000 ** 2 * V), positive["S"])

inspected_modules = (
    "credit.py", "scientific_credit.py", "evidence_axis_scoring.py", "evidence_axis_contracts.py",
    "evidence_geometry.py", "default_scientific_binding.py", "investigation_policy.py",
    "investigation_progress.py", "runtime.py", "case_execution.py", "independent_execution.py",
    "scientific_support_metadata.py", "episode_services.py", "decision_context.py", "domain.py",
)
output = {
    "status": "research_only_unadopted_arithmetic",
    "all_assay_inputs_are_synthetic": True,
    "primary_proposal": "c=max(0,B_joint), explicit one-sided support projection; original S/B retained",
    "alternative": "c=logistic(logit(0.2)+S), arbitrary declared coordinate anchor, not a prior/probability",
    "hypervolume_fixture": {"axis_weights": list(POLICY.axis_weights), "epsilon": POLICY.epsilon,
                             "fixture_other": 0.6, "formula": "H=0.1+(17/30)*c_A105",
                             "adopted_policy": False},
    "examples": rows,
    "conventional_correspondence": conventional,
    "actual_existing_boundary_rejections": errors,
    "scope": "pure arithmetic and in-memory scalar projection; no scientific run or production tests",
    "source_sha256": {name: hashlib.sha256((ROOT / "gene_annotation_episode" / name).read_bytes()).hexdigest()
                      for name in inspected_modules},
}
(OUTPUT / "arithmetic_001.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
print(json.dumps({"output": str(OUTPUT / "arithmetic_001.json"), "examples": len(rows),
                  "boundary_rejections": len(errors), "status": "all_assertions_passed"}))
