"""The four yield controllers, as equal peers.

* ``AccumulationYieldController`` -- credit that accumulates without a declared
  limit: nano-graphrag's ``EstimatorController`` (its incidence estimator, its
  normalized marginal hypervolume statistic and its flat-streak stop rule, with
  the adaptive or the fixed threshold), configured by ``ADAPTIVE_CONTROL`` or
  ``FIXED_CONTROL``, and optionally the number of items of the episode's input
  list; it takes no cost (see the section ``AccumulationYieldController`` below).
* ``BoundedQualityYieldController`` -- a quality credit whose definition
  declares a maximum; the maximum limits the forecast of further credit, never
  the credit itself (``BoundedQualityYieldEstimator``).
* ``CompletionYieldController`` -- credit toward the commission's finite target;
  the episode is complete when credit reaches the target, credit above it is an
  error, and the forecast is limited by the remaining distance, exactly zero at
  the target (``CompletionYieldEstimator``).

* ``ForecastYieldController`` -- credit whose every offered action declares a ceiling (the most the credit can rise
  if that action is the next unit, or ``UNBOUNDED``); its forecast is a formula of the ceiling and of what such
  actions realized before, in this episode and in the estimate ledger, and it stops when no offered action's forecast
  exceeds its expected cost at the declared exchange rate (see the section ``ForecastYieldController`` below).

The bounded-quality and completion controllers receive one cumulative credit per
completed action, pass the raw signed difference to their estimator, and stop
only when the estimator's available upper bound on the next marginal credit is
at or below its cost.
Credits are never bounded, clamped or rescaled; unknown forecasts stay unknown.

The estimator fits every raw marginal credit against its measured progress
receipt time with the nano-graphrag incidence model (below, MIT license). Signed
corrections use paired gain/loss marks at the same receipt times; their alpha/2
bands subtract to an approximate, uncalibrated signed interval.
"""

from dataclasses import dataclass, replace
import math
from numbers import Real
from statistics import NormalDist, median
from typing import Mapping, Sequence

# The version of the per-unit progress-time receipt every estimator reads (``estimation_context["progress_time"]``).
# The runner (``episode_runtime.progress``) writes receipts of this version; it is defined here, with its reader, so
# this package imports nothing from the runner.
PROGRESS_TIME_VERSION = "episode_progress_time_v1"


ESTIMATOR_VERSION = "real_time_signed_credit_mark_yield_v2"
SOURCE_REVISION = "60a167f9eeda0c9ea2ca294724174948947baf3f"
DEFAULT_ALPHA = 0.05

STATUS_NORMAL = 0
STATUS_INSUFFICIENT = -1
STATUS_UNIDENTIFIABLE = -2

UNCERTAINTY_UNAVAILABLE = -1
UNCERTAINTY_EXACT = 0
UNCERTAINTY_LAPLACE = 2


# ============================================================================
# Incidence estimation, from nano-graphrag question_pipeline/utilities/rarefaction.py
# (revision 60a167f9eeda0c9ea2ca294724174948947baf3f), reduced to the parts the
# bounded-quality and completion controllers use: the numeric band, the
# quadrature kernel and the full-history MAP fit, with real progress time as the
# explanatory coordinate. The accumulation controller's estimator (its own
# section below) reuses the band, the kernel, the prior, the box and the BFGS
# arithmetic of this fit, with the unit's rank as the coordinate.
#
# MIT License
#
# Copyright (c) 2024 Gustavo Ye
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ============================================================================

_QUADRATURE_LATENT = (
    -6.3639478888298395, -5.190093591304782, -4.1962077112690155,
    -3.289082424398767, -2.432436827009758, -1.6067100690287297,
    -0.7991290683245481, 0.0, 0.7991290683245481, 1.6067100690287297,
    2.432436827009758, 3.289082424398767, 4.1962077112690155,
    5.190093591304782, 6.3639478888298395,
)
_LOG_QUADRATURE_WEIGHTS = (
    -20.87529295151139, -14.330441330013045, -9.782660903562084,
    -6.458364196415659, -4.053253993024127, -2.414435562921691,
    -1.4590272451296604, -1.144888133870829, -1.4590272451296604,
    -2.414435562921691, -4.053253993024127, -6.458364196415659,
    -9.782660903562084, -14.330441330013045, -20.87529295151139,
)


def _logsumexp(values: Sequence[float]) -> float:
    peak = max(values)
    return peak + math.log(sum(math.exp(value - peak) for value in values))


def _finite_number(name: str, value: Real) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


@dataclass(frozen=True)
class NumericBand:
    """One finite non-negative numeric estimate and its uncertainty contract."""

    value: float
    lower: float
    upper: float
    status_code: int
    uncertainty_code: int
    alpha: float

    def __post_init__(self) -> None:
        value = _finite_number("NumericBand.value", self.value)
        lower = _finite_number("NumericBand.lower", self.lower)
        upper = _finite_number("NumericBand.upper", self.upper)
        alpha = _finite_number("NumericBand.alpha", self.alpha)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "alpha", alpha)
        if self.status_code not in {STATUS_NORMAL, STATUS_INSUFFICIENT, STATUS_UNIDENTIFIABLE}:
            raise ValueError(f"unknown status_code {self.status_code!r}")
        if self.status_code != STATUS_NORMAL:
            coded = float(self.status_code)
            if (value, lower, upper) != (coded, coded, coded):
                raise ValueError("a coded band has value=lower=upper=status_code")
            if self.uncertainty_code != UNCERTAINTY_UNAVAILABLE or alpha != -1.0:
                raise ValueError("a coded band has uncertainty_code=alpha=-1")
            return
        if self.uncertainty_code not in {UNCERTAINTY_EXACT, UNCERTAINTY_LAPLACE}:
            raise ValueError(f"normal band has unknown uncertainty_code {self.uncertainty_code!r}")
        if value < 0.0 or lower < 0.0 or upper < 0.0:
            raise ValueError("a normal numeric band is non-negative")
        if not lower <= value <= upper:
            raise ValueError(f"numeric band must satisfy lower <= value <= upper, got {lower}, {value}, {upper}")
        if self.uncertainty_code == UNCERTAINTY_EXACT and alpha != 0.0:
            raise ValueError("an exact band has alpha=0")
        if self.uncertainty_code == UNCERTAINTY_LAPLACE and not 0.0 < alpha < 1.0:
            raise ValueError("a Laplace band has 0 < alpha < 1")

    @classmethod
    def exact(cls, value: Real) -> "NumericBand":
        point = _finite_number("exact value", value)
        return cls(point, point, point, STATUS_NORMAL, UNCERTAINTY_EXACT, 0.0)

    @classmethod
    def coded(cls, status_code: int) -> "NumericBand":
        if status_code not in {STATUS_INSUFFICIENT, STATUS_UNIDENTIFIABLE}:
            raise ValueError("coded bands use STATUS_INSUFFICIENT or STATUS_UNIDENTIFIABLE")
        coded = float(status_code)
        return cls(coded, coded, coded, status_code, UNCERTAINTY_UNAVAILABLE, -1.0)

    @classmethod
    def laplace(cls, value: Real, variance: Real, alpha: Real) -> "NumericBand":
        """Normal/Laplace approximation around a fitted joint model, floored at zero."""
        point = _finite_number("Laplace value", value)
        variance_value = _finite_number("Laplace variance", variance)
        alpha_value = _finite_number("Laplace alpha", alpha)
        if variance_value < 0.0:
            raise ArithmeticError(f"Laplace variance must be non-negative, got {variance_value}")
        if not 0.0 < alpha_value < 1.0:
            raise ValueError(f"alpha must satisfy 0 < alpha < 1, got {alpha!r}")
        radius = NormalDist().inv_cdf(1.0 - alpha_value / 2.0) * math.sqrt(variance_value)
        return cls(point, max(0.0, point - radius), point + radius, STATUS_NORMAL,
                   UNCERTAINTY_LAPLACE, alpha_value)

    def as_record(self) -> dict:
        return {"value": self.value, "lower": self.lower, "upper": self.upper,
                "status_code": self.status_code, "uncertainty_code": self.uncertainty_code,
                "alpha": self.alpha}


class _RealTimeCreditFit:
    """The incidence model's full-history MAP fit with real time as the coordinate.

    Parameters are (beta, log_delta, observation_intercept, coupling). With
    completed-only observations there is no failure model, so the coupling is
    never identifiable and stays at zero; the intercept is held by its prior.
    The fit starts at the prior mode and its true curvature, cold, every time.
    """

    @staticmethod
    def observation_loss(parameters, coordinate, discovery):
        beta, log_delta, _observation_intercept, _coupling = parameters
        delta = math.exp(float(log_delta))
        # The gamma term is constant with respect to parameters. It retains
        # the original kernel's numerical offset; it is not a density claim.
        terms = tuple(
            weight + discovery * potential
            - math.exp(max(-50.0, min(50.0, potential)))
            - math.lgamma(discovery + 1.0)
            for weight, potential in (
                (weight, beta - delta * coordinate + latent)
                for weight, latent in zip(_LOG_QUADRATURE_WEIGHTS, _QUADRATURE_LATENT)
            )
        )
        return -_logsumexp(terms)

    @staticmethod
    def prior_loss(parameters):
        return 0.5 * (
            parameters[0] * parameters[0] / 36.0
            + (parameters[1] - math.log(0.05)) ** 2 / 4.0
            + parameters[2] * parameters[2] / 36.0
            + parameters[3] * parameters[3] / 9.0
        )

    @classmethod
    def history_loss(cls, parameters, coordinates, discoveries):
        # Deliberately no int(discovery), identity conversion or smoothing.
        return cls.prior_loss(parameters) + sum(
            cls.observation_loss(parameters, coordinate, discovery)
            for coordinate, discovery in zip(coordinates, discoveries))

    @staticmethod
    def project(parameters):
        lower_bounds = (-20.0, -12.0, -20.0, -10.0)
        upper_bounds = (20.0, 3.0, 20.0, 10.0)
        projected = [max(lower_bounds[index], min(upper_bounds[index], float(value)))
                     for index, value in enumerate(parameters)]
        projected[3] = 0.0
        return projected

    @classmethod
    def gradient(cls, parameters, coordinates, discoveries):
        gradient = []
        for index in range(3):
            width = 1e-4 * (1.0 + abs(float(parameters[index])))
            upper = list(parameters)
            lower = list(parameters)
            upper[index] += width
            lower[index] -= width
            upper = cls.project(upper)
            lower = cls.project(lower)
            denominator = upper[index] - lower[index]
            if denominator == 0.0:
                gradient.append(0.0)
                continue
            gradient.append((cls.history_loss(upper, coordinates, discoveries)
                             - cls.history_loss(lower, coordinates, discoveries)) / denominator)
        gradient.append(0.0)
        return gradient

    @staticmethod
    def _dot(left, right):
        return sum(a * b for a, b in zip(left, right))

    @staticmethod
    def _matrix_vector(matrix, vector):
        return [sum(a * b for a, b in zip(row, vector)) for row in matrix]

    @staticmethod
    def _identity():
        return [[1.0 if row == column else 0.0 for column in range(4)] for row in range(4)]

    @classmethod
    def _bfgs_update(cls, inverse_hessian, displacement, gradient_change):
        curvature = cls._dot(displacement, gradient_change)
        if not math.isfinite(curvature) or curvature <= 1e-10:
            return cls._identity()
        inverse_curvature = 1.0 / curvature
        h_times_y = cls._matrix_vector(inverse_hessian, gradient_change)
        y_h_y = cls._dot(gradient_change, h_times_y)
        scale = (1.0 + y_h_y * inverse_curvature) * inverse_curvature
        return [[inverse_hessian[row][column]
                 + scale * displacement[row] * displacement[column]
                 - inverse_curvature * (displacement[row] * h_times_y[column]
                                        + h_times_y[row] * displacement[column])
                 for column in range(4)] for row in range(4)]

    @classmethod
    def fit(cls, coordinates, discoveries):
        """Cold full-history MAP fit using standard-library BFGS."""
        parameters = cls.project([0., math.log(.05), 0., 0.])
        inverse_hessian = [[36., 0., 0., 0.], [0., 4., 0., 0.], [0., 0., 36., 0.], [0., 0., 0., 0.]]
        objective = cls.history_loss(parameters, coordinates, discoveries)
        gradient = cls.gradient(parameters, coordinates, discoveries)
        for _iteration in range(100):
            if max(abs(value) for value in gradient[:3]) <= 1e-6:
                break
            direction = [-value for value in cls._matrix_vector(inverse_hessian, gradient)]
            direction[3] = 0.0
            directional_derivative = cls._dot(gradient, direction)
            if directional_derivative >= 0.0 or not math.isfinite(directional_derivative):
                direction = [-value for value in gradient]
                directional_derivative = -cls._dot(gradient, gradient)
                inverse_hessian = cls._identity()
            step = 1.0
            candidate = parameters
            candidate_objective = objective
            while step >= 2.0 ** -20:
                trial = cls.project([value + step * direction[index]
                                     for index, value in enumerate(parameters)])
                trial_objective = cls.history_loss(trial, coordinates, discoveries)
                if trial_objective <= objective + 1e-4 * step * directional_derivative:
                    candidate = trial
                    candidate_objective = trial_objective
                    break
                step *= 0.5
            if candidate == parameters:
                break
            candidate_gradient = cls.gradient(candidate, coordinates, discoveries)
            displacement = [candidate[index] - parameters[index] for index in range(4)]
            gradient_change = [candidate_gradient[index] - gradient[index] for index in range(4)]
            inverse_hessian = cls._bfgs_update(inverse_hessian, displacement, gradient_change)
            parameters = candidate
            objective = candidate_objective
            gradient = candidate_gradient
        for index in range(4):
            inverse_hessian[3][index] = 0.0
            inverse_hessian[index][3] = 0.0
        return parameters, tuple(tuple(row) for row in inverse_hessian), objective

    @staticmethod
    def expected_discovery(parameters, coordinate):
        beta, log_delta, _observation_intercept, _coupling = parameters
        delta = math.exp(float(log_delta))
        return sum(
            math.exp(weight) * math.exp(max(-50.0, min(50.0, beta - delta * coordinate + latent)))
            for weight, latent in zip(_LOG_QUADRATURE_WEIGHTS, _QUADRATURE_LATENT))

    @staticmethod
    def metric_variance(parameters, covariance, metric):
        gradient = [0.0 for _ in parameters]
        for index in range(len(parameters)):
            step = 1e-4 * (1.0 + abs(float(parameters[index])))
            upper = parameters.copy()
            lower = parameters.copy()
            upper[index] += step
            lower[index] -= step
            gradient[index] = (metric(upper) - metric(lower)) / (2.0 * step)
        variance = sum(gradient[row] * covariance[row][column] * gradient[column]
                       for row in range(len(gradient)) for column in range(len(gradient)))
        return max(0.0, variance)


# ============================================================================
# Real-time credit-mark estimation shared by the bounded-quality and completion estimators.
# ============================================================================

def _score(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite non-negative real number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative real number")
    return number


def _signed(value: object, name: str = "marginal credit") -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite real number")
    return number


@dataclass(frozen=True)
class YieldParameters:
    uncertainty_alpha: float = DEFAULT_ALPHA

    def __post_init__(self):
        if not 0 < _score(self.uncertainty_alpha, "uncertainty_alpha") < 1:
            raise ValueError("uncertainty_alpha must be between zero and one")

    def as_record(self):
        return {"uncertainty_alpha": self.uncertainty_alpha}


def _parameters(value):
    if value is None:
        return YieldParameters()
    if isinstance(value, YieldParameters):
        return value
    if isinstance(value, Mapping):
        unknown = set(value) - {"uncertainty_alpha"}
        if unknown:
            raise ValueError(f"Unknown yield settings: {sorted(unknown)}")
        return YieldParameters(**value)
    raise TypeError("settings must be YieldParameters or their record")


def provenance():
    return {
        "estimator": ESTIMATOR_VERSION,
        "source_repository": "nano-graphrag",
        "source_path": "question_pipeline/utilities/rarefaction.py",
        "source_revision": SOURCE_REVISION,
        "source_license": "MIT; notice in yield_control/__init__.py",
        "turn_unit": "completed_episode_acquisition",
        "credit_input": "projected_marginal_credit",
        "fit_coordinate": "measured_progress_receipt_time",
        "forecast": "conditional_acquisition_credit_at_recorded_current_time",
        "forecast_units": "unchanged_iterator_credit_not_credit_per_second",
        "temporal_prior_scale": "first_measured_episode_start_to_progress_receipt_span",
        "minimum_history": None,
        "statistical_model": "latent_lognormal_fractional_poisson_working_quasi_likelihood",
        "uncertainty": "approximate_model_dependent_curvature_laplace_band",
        "calibrated_confidence_interval": False,
        "limitations": [
            "The fractional kernel is not a continuous-response probability density",
            "Uncertainty assumes the working model and is not coverage calibrated",
            "Credit units affect effective information and must remain fixed within an Episode",
            "Temporal mark decay assumes declining yield; late discoveries can violate it",
            "The first measured progress span sets an empirical prior scale; it is not a forecast duration",
            "The forecast conditions on current time; it does not predict a future completion time",
            "No failed-attempt probability is estimated from completed-only acquisitions",
            "The local optimizer has no global optimum or convergence certificate; bands can jump across history lengths",
            "Before any observed loss the nonnegative model assumes zero loss; this is an explicit working-model assumption",
            "Gain/loss interval subtraction is not coverage calibrated; Bonferroni allocation cannot calibrate the underlying Laplace approximation",
        ],
    }


@dataclass(frozen=True)
class SignedNumericBand:
    """Signed net interval after an observed correction; NumericBand stays non-negative."""

    value: float
    lower: float
    upper: float
    status_code: int = STATUS_NORMAL
    uncertainty_code: int = UNCERTAINTY_LAPLACE
    alpha: float = DEFAULT_ALPHA

    def __post_init__(self):
        values = tuple(_signed(v, "band coordinate") for v in (self.value, self.lower, self.upper))
        for name, value in zip(("value", "lower", "upper"), values):
            object.__setattr__(self, name, value)
        if self.status_code != STATUS_NORMAL:
            raise ValueError("An unavailable forecast is a coded NumericBand")
        if not values[1] <= values[0] <= values[2]:
            raise ValueError("Band must satisfy lower <= value <= upper")
        if self.uncertainty_code == UNCERTAINTY_EXACT:
            if self.alpha != 0:
                raise ValueError("An exact signed band has alpha=0")
        elif self.uncertainty_code != UNCERTAINTY_LAPLACE:
            raise ValueError("Unknown uncertainty code")
        elif not 0 < _signed(self.alpha, "alpha") < 1:
            raise ValueError("Signed model band requires 0 < alpha < 1")

    def as_record(self):
        return {"value": self.value, "lower": self.lower, "upper": self.upper,
                "status_code": self.status_code,
                "uncertainty_code": self.uncertainty_code, "alpha": self.alpha}


@dataclass(frozen=True)
class YieldEstimate:
    turns: int
    expected_next_gain: object
    parameters: YieldParameters
    diagnostics: dict
    estimator_binding: dict | None = None

    @property
    def ready(self):
        return self.expected_next_gain.status_code == STATUS_NORMAL

    def as_record(self):
        return {"turns": self.turns,
                "expected_next_gain": self.expected_next_gain.as_record(),
                "parameters": self.parameters.as_record(),
                "diagnostics": dict(self.diagnostics),
                "provenance": provenance() if self.estimator_binding is None else dict(self.estimator_binding)}


def _time_point(value):
    if not isinstance(value, Mapping) or value.get("version") != PROGRESS_TIME_VERSION:
        return None, "progress_time_unavailable"
    if value.get("status") != "available":
        return None, value.get("unavailable_reason") or "progress_time_unavailable"
    integers = ("origin_monotonic_ns", "observed_monotonic_ns", "reference_observation_monotonic_ns")
    if (any(type(value.get(key)) is not int or value[key] < 0 for key in integers)
            or any(not isinstance(value.get(key), str) or not value[key]
                   for key in ("run_id", "episode_id", "boot_id"))):
        return None, "invalid_progress_clock"
    origin, observed, reference = (value[key] for key in integers)
    if not origin < reference <= observed:
        return None, "invalid_progress_reference_span"
    try:
        scale = _score(value.get("reference_elapsed_seconds"), "reference span")
        elapsed = _score(value.get("elapsed_seconds"), "elapsed time")
    except ValueError:
        return None, "invalid_progress_reference_span"
    if (scale == 0 or not math.isclose(scale, (reference - origin) / 1e9, rel_tol=1e-12)
            or not math.isclose(elapsed, (observed - origin) / 1e9, rel_tol=1e-12)):
        return None, "invalid_progress_clock_arithmetic"
    return value, None


def _time_operands(turns, contexts, evaluation_time):
    contexts = (None,) * turns if contexts is None else tuple(contexts)
    if len(contexts) != turns:
        raise ValueError("real_time_yield_requires_aligned_contexts")
    points = []
    for context in contexts:
        point, reason = _time_point(context.get("progress_time") if isinstance(context, Mapping) else None)
        if point is None:
            return (), 0., {"unavailable_reason": reason}
        if point.get("point_kind") != "progress_receipt":
            return (), 0., {"unavailable_reason": "history_time_requires_actual_progress_receipt"}
        packet = context.get("current_completion_evidence")
        if isinstance(packet, Mapping) and any(
                packet.get(key) != point.get(key) for key in ("run_id", "episode_id", "original_decision_index")):
            return (), 0., {"unavailable_reason": "progress_time_completion_identity_conflict"}
        points.append(point)
    target, reason = _time_point(evaluation_time if evaluation_time is not None
                                 else points[-1] if points else None)
    if not points and target is None:
        # At an unobserved origin, the intercept prior requires no duration.
        return (), 0., {"time_binding": "unobserved_origin_prior_only", "unobserved_time_reason": reason}
    if target is None:
        return (), 0., {"unavailable_reason": reason}
    identity_keys = ("run_id", "episode_id", "boot_id", "origin_monotonic_ns",
                     "reference_observation_monotonic_ns", "reference_elapsed_seconds")
    previous = target["reference_observation_monotonic_ns"]
    for point in points:
        if any(point[key] != target[key] for key in identity_keys):
            return (), 0., {"unavailable_reason": "progress_clocks_not_comparable"}
        if point["observed_monotonic_ns"] < previous:
            return (), 0., {"unavailable_reason": "progress_receipt_clock_order_conflict"}
        previous = point["observed_monotonic_ns"]
    if target["observed_monotonic_ns"] < previous:
        return (), 0., {"unavailable_reason": "forecast_precedes_observed_progress"}
    scale = target["reference_elapsed_seconds"]
    reference = target["reference_observation_monotonic_ns"]
    coordinates = tuple((point["observed_monotonic_ns"] - reference) / 1e9 / scale for point in points)
    coordinate = (target["observed_monotonic_ns"] - reference) / 1e9 / scale
    return coordinates, coordinate, {
        "time_binding": PROGRESS_TIME_VERSION,
        "reference_elapsed_seconds": scale,
        "reference_observation_monotonic_ns": reference,
        "forecast_observed_monotonic_ns": target["observed_monotonic_ns"],
        "forecast_elapsed_seconds": target["elapsed_seconds"],
        "forecast_coordinate": coordinate,
        "forecast_point_kind": target.get("point_kind"),
        "time_scale_source": "first_measured_episode_start_to_progress_receipt_span",
        "log_decay_prior_mean": math.log(.05), "log_decay_prior_variance": 4.,
        "decay_unit": "per_recorded_reference_span_not_per_action",
        "forecast_quantity": "conditional_acquisition_credit_at_recorded_current_time"}


def estimate_nonnegative_yield(scores: Sequence[Real], parameters=None, *, contexts=None, evaluation_time=None):
    """Fit all raw non-negative marks at their real receipt times; never their action ranks."""
    parameters = _parameters(parameters)
    history = tuple(_score(value, "marginal credit") for value in scores)
    turns = len(history)
    diagnostics = {"completed_acquisition_turns": turns, "history_used": turns,
                   "fitting_scope": "full_history" if turns else "prior_only",
                   "initialization": "cold_template_prior",
                   "minimum_history": None, "credit_units": "unchanged_iterator_credit"}
    coordinates, target, timing = _time_operands(turns, contexts, evaluation_time)
    diagnostics.update(timing)
    if "unavailable_reason" in timing:
        return YieldEstimate(turns, NumericBand.coded(STATUS_INSUFFICIENT), parameters, diagnostics)
    try:
        fitted, covariance, objective = _RealTimeCreditFit.fit(coordinates, history)
        if not all(math.isfinite(value) for row in covariance for value in row):
            raise ArithmeticError("Non-finite fitted covariance")
        point = _RealTimeCreditFit.expected_discovery(fitted, target)
        variance = _RealTimeCreditFit.metric_variance(
            fitted, covariance, lambda values: _RealTimeCreditFit.expected_discovery(values, target))
        band = NumericBand.laplace(point, variance, parameters.uncertainty_alpha)
        diagnostics.update({"yield_intercept": fitted[0], "reference_span_decay": math.exp(fitted[1]),
                            "fit_objective": objective, "next_gain_variance": variance})
    except (ArithmeticError, OverflowError, ValueError) as error:
        # Numerical non-identifiability is a prediction status, never a zero yield.
        band = NumericBand.coded(STATUS_UNIDENTIFIABLE)
        diagnostics["fit_status"] = type(error).__name__
    return YieldEstimate(turns, band, parameters, diagnostics)


def estimate_score_yield(scores: Sequence[Real], parameters=None, *, contexts=None, evaluation_time=None):
    """Fit raw signed progress history on its aligned measured receipt times."""
    parameters = _parameters(parameters)
    history = tuple(_signed(value) for value in scores)
    if not any(value < 0 for value in history):
        return estimate_nonnegative_yield(history, parameters, contexts=contexts, evaluation_time=evaluation_time)
    # Every mark has one element for every actual action. Zeros below mean an
    # observed action's other sign, never an invented failure/action observation.
    gains = tuple(max(value, 0.0) for value in history)
    losses = tuple(max(-value, 0.0) for value in history)
    component_parameters = YieldParameters(parameters.uncertainty_alpha / 2.0)
    contexts = None if contexts is None else tuple(contexts)
    gain = estimate_nonnegative_yield(gains, component_parameters, contexts=contexts, evaluation_time=evaluation_time)
    loss = estimate_nonnegative_yield(losses, component_parameters, contexts=contexts, evaluation_time=evaluation_time)
    diagnostics = {"completed_acquisition_turns": len(history), "history_used": len(history),
                   "fitting_scope": "full_history", "initialization": "cold_template_prior",
                   "signed_model": "paired_gain_loss_marks_same_real_time_v2",
                   "negative_action_count": sum(value < 0 for value in history),
                   "gain_component": gain.as_record(), "loss_component": loss.as_record(),
                   "interval_method": "bonferroni_allocated_model_band_subtraction",
                   "coverage_calibrated": False}
    if "unavailable_reason" in gain.diagnostics:
        diagnostics["unavailable_reason"] = gain.diagnostics["unavailable_reason"]
    statuses = {gain.expected_next_gain.status_code, loss.expected_next_gain.status_code}
    if statuses != {STATUS_NORMAL}:
        band = NumericBand.coded(STATUS_UNIDENTIFIABLE if STATUS_UNIDENTIFIABLE in statuses
                                 else STATUS_INSUFFICIENT)
    else:
        g, l = gain.expected_next_gain, loss.expected_next_gain
        band = SignedNumericBand(g.value - l.value, g.lower - l.upper, g.upper - l.lower,
                                 alpha=parameters.uncertainty_alpha)
    return YieldEstimate(len(history), band, parameters, diagnostics)


def estimate_bounded_credit_yield(scores: Sequence[Real], parameters=None, *, contexts=None,
                                  initial_credit, maximum_credit):
    """Forecast one more marginal credit when the credit definition declares a maximum.

    The signed real-time fit supplies the forecast; the declared range
    [0, maximum_credit] limits the forecast to the remaining headroom (and a
    correction to the current credit). The credit itself is never changed: a
    history outside the declared range raises. A correction reopens headroom.
    """
    parameters = _parameters(parameters)
    initial = _score(initial_credit, 'initial bounded credit')
    maximum = _score(maximum_credit, 'maximum bounded credit')
    if maximum <= 0 or initial > maximum:
        raise ValueError('bounded_credit_range_invalid')
    history = tuple(_signed(value) for value in scores)
    current = math.fsum((initial, *history))
    if not 0 <= current <= maximum:
        raise ValueError('bounded_credit_history_outside_declared_range')
    base = estimate_score_yield(history, parameters, contexts=contexts)
    headroom = maximum - current
    band = base.expected_next_gain
    if headroom == 0:
        limited = NumericBand.exact(0)
    elif band.status_code != STATUS_NORMAL:
        limited = band
    elif isinstance(band, SignedNumericBand):
        lower = max(-current, min(band.lower, headroom))
        upper = max(lower, min(headroom, max(-current, band.upper)))
        limited = SignedNumericBand(min(upper, max(lower, band.value)), lower, upper,
                                    uncertainty_code=band.uncertainty_code, alpha=band.alpha)
    else:
        upper = min(headroom, band.upper)
        lower = min(upper, band.lower)
        limited = NumericBand(min(upper, max(lower, band.value)), lower, upper,
                              band.status_code, band.uncertainty_code, band.alpha)
    return replace(base, expected_next_gain=limited,
        diagnostics={**base.diagnostics, 'declared_credit_minimum': 0., 'declared_credit_maximum': maximum,
                     'current_credit': current, 'remaining_positive_credit': headroom,
                     'forecast_constraint': 'declared_credit_range_after_same_action_history'},
        estimator_binding={'kind': 'bounded_quality_credit_yield_v1', 'base_estimator': ESTIMATOR_VERSION,
                           'declared_credit_minimum': 0., 'declared_credit_maximum': maximum,
                           'forecast': 'next_marginal_credit_limited_by_current_headroom',
                           'uncertainty': 'base_working_model_uncalibrated'})


# ============================================================================
# The bounded-quality and completion estimators: one history entry per completed action, signed.
# ============================================================================

class BoundedQualityYieldEstimator:
    """A quality credit whose definition declares its maximum."""

    def __init__(self, initial_credit, maximum_credit, parameters=None):
        self.parameters = _parameters(parameters)
        self.initial_credit = _score(initial_credit, 'initial bounded credit')
        self.maximum_credit = _score(maximum_credit, 'maximum bounded credit')
        self._scores, self._contexts = [], []
        self._current = estimate_bounded_credit_yield((), self.parameters, contexts=(),
            initial_credit=self.initial_credit, maximum_credit=self.maximum_credit)

    @property
    def scores(self):
        return tuple(self._scores)

    def observe(self, marginal_credit, *, context=None):
        scores, contexts = [*self._scores, _signed(marginal_credit)], [*self._contexts, context]
        current = estimate_bounded_credit_yield(scores, self.parameters, contexts=contexts,
            initial_credit=self.initial_credit, maximum_credit=self.maximum_credit)
        self._scores, self._contexts, self._current = scores, contexts, current
        return current

    def state(self):
        return self._current


class CompletionYieldEstimator:
    """Observed yield until credit reaches the commission's finite target."""

    def __init__(self, initial_credit, target, parameters=None):
        self.parameters = _parameters(parameters)
        self.initial_credit = _score(initial_credit, 'initial completion credit')
        self.target = _score(target, 'completion target')
        if self.target <= 0:
            raise ValueError('completion_target_must_be_positive')
        self._scores, self._contexts = [], []
        self._current = self._estimate(self._scores, self._contexts)

    @property
    def scores(self):
        return tuple(self._scores)

    def _estimate(self, scores, contexts):
        current = math.fsum((self.initial_credit, *scores))
        if current > self.target:
            raise ValueError('completion_credit_exceeds_target')
        estimate = estimate_bounded_credit_yield(scores, self.parameters, contexts=contexts,
            initial_credit=self.initial_credit, maximum_credit=self.target)
        return replace(estimate, diagnostics={**estimate.diagnostics,
            'completion_target': self.target,
            'remaining_deliverable_credit': self.target - current,
            'forecast_quantity': 'observed_yield_limited_by_remaining_distance_to_target'},
            estimator_binding={'kind': 'target_completion_yield_v1',
                'completion_target': self.target,
                'before_target': 'observed_action_yield_limited_by_remaining_distance',
                'at_target': 'exact_zero_remaining_credit'})

    def observe(self, marginal_credit, *, context=None):
        scores, contexts = [*self._scores, _signed(marginal_credit)], [*self._contexts, context]
        current = self._estimate(scores, contexts)
        self._scores, self._contexts, self._current = scores, contexts, current
        return current

    def state(self):
        return self._current


# ============================================================================
# Continuation: the one stop rule, its step and state records.
# ============================================================================

@dataclass(frozen=True)
class ContinuationDecision:
    stop: bool
    projected_gain: object
    continuation_cost: float

    def as_record(self):
        return {"stop": self.stop, "projected_gain": self.projected_gain.as_record(),
                "continuation_cost": self.continuation_cost,
                "decision_basis": "current_estimator_marginal_credit_upper_bound"}


def predicted_gain_upper_bound(projected_gain, continuation_cost):
    """The complete continuation rule: stop when an available upper bound is at or below the cost."""
    if not isinstance(projected_gain, (NumericBand, SignedNumericBand)):
        raise TypeError("Continuation consumes a numeric band")
    cost = _score(continuation_cost, "continuation cost")
    return ContinuationDecision(projected_gain.status_code == STATUS_NORMAL and projected_gain.upper <= cost,
                                projected_gain, cost)


@dataclass(frozen=True)
class YieldStep:
    unit_label: str
    credit: float
    marginal_credit: float
    estimate: YieldEstimate
    decision: ContinuationDecision
    is_root: bool = False
    requests_transition: bool = False

    @property
    def stop(self):
        return self.decision.stop

    def as_record(self):
        return {"unit_label": self.unit_label, "credit": self.credit,
                "marginal_credit": self.marginal_credit, "estimate": self.estimate.as_record(),
                "decision": self.decision.as_record(), "stop": self.stop,
                "is_root": self.is_root, "requests_transition": self.requests_transition}


@dataclass(frozen=True)
class YieldState:
    epoch: str
    initial_credit: float
    current_credit: float
    history: tuple
    estimate: YieldEstimate
    decision: ContinuationDecision

    @property
    def stop(self):
        return self.decision.stop

    def as_record(self):
        return {"epoch": self.epoch, "initial_credit": self.initial_credit,
                "current_credit": self.current_credit, "scores": list(self.history),
                "estimate": self.estimate.as_record(), "decision": self.decision.as_record()}


def _epoch(epoch):
    if not isinstance(epoch, str) or not epoch.strip():
        raise ValueError("epoch must be a nonempty string")
    return epoch


def _completed(value):
    """The cumulative credit and estimation context of one completed action."""
    if hasattr(value, "as_record"):
        value = value.as_record()
    if isinstance(value, Mapping):
        if "credit" not in value:
            raise ValueError("Completed record must include cumulative credit")
        return _signed(value["credit"], "cumulative credit"), value.get("estimation_context")
    return _signed(value, "cumulative credit"), None


# ============================================================================
# AccumulationYieldController: nano-graphrag's EstimatorController
# (question_pipeline/utilities/rarefaction.py at the revision above, MIT notice above) in this library.
#
# The estimator (``_IncidenceEstimator``): unit r (rank r = 1, 2, ... in this controller; every unit the runtime
# hands over is an observed unit: the system has no failed or excluded unit) has the discovery d_r. With the
# potential  eta_r(z) = beta - delta (r - 1) + z  (z the latent of the 15-point Gauss-Hermite rule), the unit's
# likelihood is  sum_z w_z sigmoid(observation_intercept + coupling eta) exp(d eta - e^eta) / d!  (an observed unit's
# softplus term), with the same priors and box as nano-graphrag, fitted by MAP/BFGS over the full history, warm
# started from the previous fit (beta = log 0.25, log delta = log 0.05 and the identity curvature at the start of an
# epoch). The coupling is identifiable only with failed units, so it stays 0 here, as nano-graphrag keeps it without
# them. No fit before W = 8 attempted and m = 4 observed units (``insufficient``). From the fit: the next unit's
# discoveries (rank T + 1), the remaining discoveries  m1 / (1 - m2 / m1)  (m1, m2 the discoveries at ranks T + 1,
# T + 2) and the expected total (observed + remaining), each a Laplace band at alpha 0.05.
#
# The statistic (``_NumericalController.expected_next_volume_credit``): the expected next marginal hypervolume
# credit, the relaxed geometric volume of the progress observed / expected total after the next unit minus now,
# with the conservative outer interval band. One channel ("overall"), so the volume is the progress itself.
#
# The stop rule (``_NumericalController.observe``): a unit is flat when that band is normal and its upper bound is
# at or below gamma; a non-flat or unavailable unit resets the streak; ``streak_length`` = 4 consecutive flat units
# stop the episode. rho = 0 labels the stop (convergence when the remaining discoveries' upper bound is at or below
# rho, otherwise saturation); it does not gate it. gamma is fixed (``FIXED_CONTROL``, 0.06, nano-graphrag's
# lexical-probe/chunk grain) or adaptive (``ADAPTIVE_CONTROL``, nano-graphrag's page, report and source-table grains:
# after every unit gamma = max(one-result resolution, 0.1 x median of the productive realized hypervolume credits of
# the last W units, or the last such median carried); while neither exists there is no verdict and the streak is kept).
#
# The observation. nano-graphrag hands its controller, per completed unit, the accepted result identities of the unit
# (provider_binding.py, ``TableGoalState.preview``: ``identities = tuple(dict.fromkeys(identity for identity, _ in
# previewed.incidence))``); its estimator's discovery d_r is the number of those identities it had not seen before in
# the epoch, and the observed total is the number of distinct identities seen. The runtime here hands the
# controller, per completed unit, the episode's cumulative credit (``{'credit', 'estimation_context'}``), and an
# accumulating credit counts what the episode newly holds; so d_r is the unit's marginal credit (the rise of the
# cumulative credit over the previous unit) and the observed total is the sum of the marginal credits since the
# controller was built (credit minus initial credit). One credit unit is one result in the one-result resolution.
# Discoveries are real numbers here (nano-graphrag's are integer counts; at integer credits the arithmetic is the
# same); a credit that falls is not an observation of this model and raises. The progress-time receipt of the
# estimation context is not read: the coordinate is the unit's rank, as in nano-graphrag.
#
# The items. ``items`` is None or the number of items of the episode's input list when the episode starts. Every
# completed unit consumes one item; the controller stops when nano-graphrag's rule stops it or when no item remains.
# An episode whose list is not known at its start, or whose units do not use one item each, reports the number of
# items left on its list with each unit instead (``estimation_context['items_remaining']``, an integer >= 0): the
# reported number is then the number remaining (nothing is counted down), and 0 stops the episode (the owner,
# 2026-11-21: "add one more condition which is if the number of items on the list is zero we stop"; nano-graphrag's
# physical exhaustion of a page's or a search's list).
# ============================================================================

ACCUMULATION_ESTIMATOR_VERSION = "preferential_incidence_estimator_v2"
ACCUMULATION_CONTROLLER_VERSION = "preferential_discovery_controller_v7"
VOLUME_CREDIT_VERSION = "relaxed_geometric_hypervolume_v5"
ADAPTIVE_THRESHOLD_VERSION = "adaptive_marginal_credit_threshold_v2"
FIXED_THRESHOLD_VERSION = "fixed_marginal_credit_threshold_v1"
DEFAULT_EFFICIENCY_FRACTION = 0.1
VOLUME_RELAXATION_FACTOR = 2.0
MIN_DISCOVERABLE_COUNT = 1.0
ACCUMULATION_CHANNEL = "overall"


@dataclass(frozen=True)
class AccumulationControl:
    """One of nano-graphrag's two controller declarations (provider_binding.py): ``threshold`` is the threshold
    policy (adaptive or fixed), ``gamma`` the starting threshold, ``rho`` the convergence label, ``streak_length``
    the flat units that stop, ``window_size`` (W) the attempted and ``subsample_size`` (m) the observed units before
    the first fit, ``alpha`` the band level. An episode uses ``ADAPTIVE_CONTROL`` or ``FIXED_CONTROL``."""
    threshold: str
    gamma: float
    rho: float
    streak_length: int
    window_size: int
    subsample_size: int
    alpha: float

    def as_record(self):
        return {"version": ACCUMULATION_CONTROLLER_VERSION, "threshold": self.threshold, "gamma": self.gamma,
                "rho": {ACCUMULATION_CHANNEL: self.rho}, "streak_length": self.streak_length,
                "window_size": self.window_size, "subsample_size": self.subsample_size, "alpha": self.alpha}


# nano-graphrag DEFAULT_PAGE_CONTROL / DEFAULT_REPORT_CONTROL / DEFAULT_SOURCE_TABLE_CONTROL with
# ``adaptive_marginal_credit_threshold``.
ADAPTIVE_CONTROL = AccumulationControl(ADAPTIVE_THRESHOLD_VERSION, 0.0, 0.0, 4, 8, 4, 0.05)
# nano-graphrag DEFAULT_CHUNK_CONTROL of the lexical-probe grain, whose threshold is kept fixed.
FIXED_CONTROL = AccumulationControl(FIXED_THRESHOLD_VERSION, 0.06, 0.0, 4, 8, 4, 0.05)


def _softplus(value):
    if value > 0.0:
        return value + math.log1p(math.exp(-value))
    return math.log1p(math.exp(value))


def _laplace_band(value, variance, alpha, lower_floor):
    """nano-graphrag ``NumericBand.laplace`` with its ``lower_floor``."""
    point = _finite_number("Laplace value", value)
    variance_value = _finite_number("Laplace variance", variance)
    floor = _finite_number("Laplace lower_floor", lower_floor)
    if variance_value < 0.0:
        raise ArithmeticError(f"Laplace variance must be non-negative, got {variance_value}")
    radius = NormalDist().inv_cdf(1.0 - alpha / 2.0) * math.sqrt(variance_value)
    return NumericBand(point, max(floor, point - radius), point + radius, STATUS_NORMAL, UNCERTAINTY_LAPLACE, alpha)


def _coded_of(codes):
    return NumericBand.coded(STATUS_UNIDENTIFIABLE if STATUS_UNIDENTIFIABLE in codes else STATUS_INSUFFICIENT)


@dataclass(frozen=True)
class AccumulationIncidence:
    """nano-graphrag ``IncidenceEstimate`` of the one channel: observed and expected total, remaining and next
    discoveries."""
    units: int
    observed_results: NumericBand
    expected_results: NumericBand
    remaining_results: NumericBand
    expected_next_discoveries: NumericBand
    diagnostics: dict

    def as_record(self):
        return {"method_version": ACCUMULATION_ESTIMATOR_VERSION, "channel": ACCUMULATION_CHANNEL,
                "incidence_samples": self.units, "observed_results": self.observed_results.as_record(),
                "expected_results": self.expected_results.as_record(),
                "remaining_results": self.remaining_results.as_record(),
                "control_statistics": {"expected_next_discoveries": self.expected_next_discoveries.as_record()},
                "diagnostics": dict(self.diagnostics)}


class _AccumulationIncidenceEstimator:
    """nano-graphrag ``_IncidenceEstimator`` over the discoveries of observed units (see the section comment)."""

    def __init__(self, control):
        self.control = control
        self._discoveries = []
        self._fit_parameters = [math.log(0.25), math.log(0.05), 0.0, 0.0]
        self._fit_inverse_hessian = _RealTimeCreditFit._identity()
        self._fit_cache = None

    @property
    def units(self):
        return len(self._discoveries)

    @property
    def distinct(self):
        return math.fsum(self._discoveries)

    def observe(self, discovery):
        self._discoveries.append(discovery)
        self._fit_cache = None

    @staticmethod
    def observation_loss(parameters, rank, discovery):
        beta, log_delta, observation_intercept, coupling = parameters
        delta = math.exp(float(log_delta))
        potentials = tuple(beta - delta * (rank - 1) + latent for latent in _QUADRATURE_LATENT)
        terms = tuple(
            weight
            - _softplus(-(observation_intercept + coupling * potential))
            + discovery * potential
            - math.exp(max(-50.0, min(50.0, potential)))
            - math.lgamma(discovery + 1.0)
            for weight, potential in zip(_LOG_QUADRATURE_WEIGHTS, potentials))
        return -_logsumexp(terms)

    @classmethod
    def history_loss(cls, parameters, discoveries):
        return _RealTimeCreditFit.prior_loss(parameters) + sum(
            cls.observation_loss(parameters, rank, discovery)
            for rank, discovery in enumerate(discoveries, start=1))

    @classmethod
    def history_gradient(cls, parameters, discoveries):
        gradient = []
        for index in range(3):
            width = 1e-4 * (1.0 + abs(float(parameters[index])))
            upper = list(parameters)
            lower = list(parameters)
            upper[index] += width
            lower[index] -= width
            upper = _RealTimeCreditFit.project(upper)
            lower = _RealTimeCreditFit.project(lower)
            denominator = upper[index] - lower[index]
            if denominator == 0.0:
                gradient.append(0.0)
                continue
            gradient.append((cls.history_loss(upper, discoveries) - cls.history_loss(lower, discoveries))
                            / denominator)
        gradient.append(0.0)
        return gradient

    def _fit_full_history(self, discoveries):
        """Warm-started full-history MAP fit (nano-graphrag ``_fit_full_history``, coupling not identifiable)."""
        parameters = _RealTimeCreditFit.project(self._fit_parameters)
        inverse_hessian = [row.copy() for row in self._fit_inverse_hessian]
        objective = self.history_loss(parameters, discoveries)
        gradient = self.history_gradient(parameters, discoveries)
        for _iteration in range(100):
            if max(abs(value) for value in gradient[:3]) <= 1e-6:
                break
            direction = [-value for value in _RealTimeCreditFit._matrix_vector(inverse_hessian, gradient)]
            direction[3] = 0.0
            directional_derivative = _RealTimeCreditFit._dot(gradient, direction)
            if directional_derivative >= 0.0 or not math.isfinite(directional_derivative):
                direction = [-value for value in gradient]
                directional_derivative = -_RealTimeCreditFit._dot(gradient, gradient)
                inverse_hessian = _RealTimeCreditFit._identity()
            step = 1.0
            candidate = parameters
            candidate_objective = objective
            while step >= 2.0 ** -20:
                trial = _RealTimeCreditFit.project([value + step * direction[index]
                                                    for index, value in enumerate(parameters)])
                trial_objective = self.history_loss(trial, discoveries)
                if trial_objective <= objective + 1e-4 * step * directional_derivative:
                    candidate = trial
                    candidate_objective = trial_objective
                    break
                step *= 0.5
            if candidate == parameters:
                break
            candidate_gradient = self.history_gradient(candidate, discoveries)
            displacement = [candidate[index] - parameters[index] for index in range(4)]
            gradient_change = [candidate_gradient[index] - gradient[index] for index in range(4)]
            inverse_hessian = _RealTimeCreditFit._bfgs_update(inverse_hessian, displacement, gradient_change)
            parameters = candidate
            objective = candidate_objective
            gradient = candidate_gradient
        for index in range(4):
            inverse_hessian[3][index] = 0.0
            inverse_hessian[index][3] = 0.0
        self._fit_parameters = parameters.copy()
        self._fit_inverse_hessian = [row.copy() for row in inverse_hessian]
        return parameters, tuple(tuple(row) for row in inverse_hessian), objective

    @staticmethod
    def metric_discovery(parameters, rank):
        beta, log_delta, observation_intercept, coupling = parameters
        delta = math.exp(float(log_delta))
        return sum(
            math.exp(weight)
            * (1.0 / (1.0 + math.exp(max(-50.0, min(50.0, -(observation_intercept + coupling
                                                             * (beta - delta * (rank - 1.0) + latent)))))))
            * math.exp(max(-50.0, min(50.0, beta - delta * (rank - 1.0) + latent)))
            for weight, latent in zip(_LOG_QUADRATURE_WEIGHTS, _QUADRATURE_LATENT))

    @classmethod
    def metric_remaining(cls, parameters, next_rank):
        first = cls.metric_discovery(parameters, next_rank)
        if first == 0.0:
            return 0.0
        second = cls.metric_discovery(parameters, next_rank + 1)
        ratio = second / first
        if not math.isfinite(ratio) or ratio >= 1.0:
            return None
        return max(0.0, first / max(1e-12, 1.0 - ratio))

    @staticmethod
    def optional_metric_variance(parameters, covariance, metric):
        gradient = [0.0 for _ in parameters]
        for index in range(len(parameters)):
            step = 1e-4 * (1.0 + abs(float(parameters[index])))
            upper = parameters.copy()
            lower = parameters.copy()
            upper[index] += step
            lower[index] -= step
            upper_value = metric(upper)
            lower_value = metric(lower)
            if upper_value is None or lower_value is None:
                return None
            gradient[index] = (upper_value - lower_value) / (2.0 * step)
        variance = sum(gradient[row] * covariance[row][column] * gradient[column]
                       for row in range(len(gradient)) for column in range(len(gradient)))
        return max(0.0, variance)

    def _fit(self):
        discoveries = tuple(self._discoveries)
        if len(discoveries) < self.control.window_size or len(discoveries) < self.control.subsample_size:
            return None
        parameters, covariance, objective = self._fit_full_history(discoveries)
        if not all(math.isfinite(value) for row in covariance for value in row):
            return ()
        return parameters, covariance, objective

    def snapshot(self):
        cache_key = len(self._discoveries)
        if self._fit_cache is not None and self._fit_cache[0] == cache_key:
            return self._fit_cache[1]
        attempted = len(self._discoveries)
        alpha = self.control.alpha
        fit = self._fit()
        if fit is None:
            expected = remaining = next_discovery = NumericBand.coded(STATUS_INSUFFICIENT)
            fit_diagnostics = {}
        elif not fit:
            expected = remaining = next_discovery = NumericBand.coded(STATUS_UNIDENTIFIABLE)
            fit_diagnostics = {}
        else:
            parameters, covariance, objective = fit
            next_rank = attempted + 1
            next_point = self.metric_discovery(parameters, next_rank)
            next_variance = _RealTimeCreditFit.metric_variance(
                parameters, covariance, lambda values: self.metric_discovery(values, next_rank))
            next_discovery = _laplace_band(next_point, next_variance, alpha, 0.0)
            remaining_point = self.metric_remaining(parameters, next_rank)
            remaining_variance = (None if remaining_point is None else self.optional_metric_variance(
                parameters, covariance, lambda values: self.metric_remaining(values, next_rank)))
            if remaining_variance is None:
                remaining = expected = NumericBand.coded(STATUS_UNIDENTIFIABLE)
            else:
                remaining = _laplace_band(remaining_point, remaining_variance, alpha, 0.0)
                expected = _laplace_band(self.distinct + remaining_point, remaining_variance, alpha, self.distinct)
            fit_diagnostics = {"yield_intercept": float(parameters[0]), "rank_decay": math.exp(float(parameters[1])),
                               "observation_intercept": float(parameters[2]), "fit_objective": objective}
        estimate = AccumulationIncidence(
            attempted, NumericBand.exact(self.distinct), expected, remaining, next_discovery,
            {"minimum_attempts": self.control.window_size, "minimum_evaluated": self.control.subsample_size,
             "alpha": alpha, "attempted_units": attempted, "observed_units": attempted, **fit_diagnostics})
        self._fit_cache = (cache_key, estimate)
        return estimate


def _volume_relaxation(axis_count):
    return 1.0 / (VOLUME_RELAXATION_FACTOR * axis_count)


def _progress_denominator(expected_results, minimum_reachable_results):
    """Normalize progress on a total that can contain the stated results."""
    if expected_results <= 0.0:
        raise ValueError("positive expected_results required")
    return max(MIN_DISCOVERABLE_COUNT, expected_results, minimum_reachable_results)


def _relaxed_geometric_volume(progress):
    """geomean(epsilon + progress) - epsilon with epsilon = 1 / (2C) for C axes (one axis here: the progress)."""
    values = tuple(_finite_number(f"progress[{index}]", value) for index, value in enumerate(progress))
    epsilon = _volume_relaxation(len(values))
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("every progress coordinate must be in [0, 1]")
    volume = math.exp(sum(math.log(epsilon + value) for value in values) / len(values)) - epsilon
    return min(1.0, max(0.0, volume))


def expected_next_volume_credit(estimate):
    """The expected next marginal hypervolume credit of one channel's estimate, with its outer interval band, and the
    channel's record (nano-graphrag ``_NumericalController.expected_next_volume_credit``)."""
    total = estimate.expected_results
    next_discoveries = estimate.expected_next_discoveries
    bands = (total, next_discoveries)
    unavailable = [band.status_code for band in bands if band.status_code]
    if unavailable:
        return _coded_of(unavailable), {}
    observed = estimate.observed_results.value
    if total.value < observed or total.upper < observed:
        return NumericBand.coded(STATUS_UNIDENTIFIABLE), {}
    if total.value == 0.0:
        if observed != 0.0 or next_discoveries.upper > 0.0:
            return NumericBand.coded(STATUS_UNIDENTIFIABLE), {}
        p_now = p_now_lower = p_now_upper = 1.0
        p_next = p_next_lower = p_next_upper = 1.0
        p_increment_lower = p_increment_upper = 0.0
        point_denominator = MIN_DISCOVERABLE_COUNT
    else:
        point_open = total.value > observed or next_discoveries.value > 0.0
        interval_open = total.upper > observed or next_discoveries.upper > 0.0
        point_denominator = _progress_denominator(total.value,
                                                  observed + (MIN_DISCOVERABLE_COUNT if point_open else 0.0))
        interval_minimum = observed + (MIN_DISCOVERABLE_COUNT if interval_open else 0.0)
        lower_denominator = max(MIN_DISCOVERABLE_COUNT, interval_minimum, total.lower)
        upper_denominator = max(MIN_DISCOVERABLE_COUNT, interval_minimum, total.upper)
        p_now = min(1.0, observed / point_denominator)
        p_next = min(1.0, (observed + next_discoveries.value) / point_denominator)
        if total.upper == 0.0:
            return NumericBand.coded(STATUS_UNIDENTIFIABLE), {}
        p_now_lower = min(1.0, observed / upper_denominator)
        p_next_lower = min(1.0, (observed + next_discoveries.lower) / upper_denominator)
        p_now_upper = min(1.0, observed / lower_denominator)
        p_next_upper = min(1.0, (observed + next_discoveries.upper) / lower_denominator)

        def axis_increment(total_value, discovery):
            if total_value <= 0.0:
                return 0.0
            return max(0.0, min(1.0, (observed + discovery) / total_value) - min(1.0, observed / total_value))

        total_lower = max(MIN_DISCOVERABLE_COUNT, interval_minimum, total.lower)
        total_upper = max(total_lower, total.upper)
        upper_candidates = [total_lower, total_upper]
        peak = observed + next_discoveries.upper
        if total_lower <= peak <= total_upper:
            upper_candidates.append(peak)
        p_increment_lower = min(axis_increment(candidate, next_discoveries.lower)
                                for candidate in (total_lower, total_upper))
        p_increment_upper = max(axis_increment(candidate, next_discoveries.upper) for candidate in upper_candidates)
    record = {
        "current_expected_results": total.value, "current_expected_results_lower": total.lower,
        "current_expected_results_upper": total.upper, "progress_denominator": point_denominator,
        "axis_completed_by_zero_expectation": float(total.value == 0.0), "current_observed_results": observed,
        "expected_next_discoveries": next_discoveries.value,
        "expected_next_discoveries_lower": next_discoveries.lower,
        "expected_next_discoveries_upper": next_discoveries.upper,
        "current_progress": p_now, "current_progress_lower": p_now_lower, "current_progress_upper": p_now_upper,
        "projected_progress": p_next, "projected_progress_lower": p_next_lower,
        "projected_progress_upper": p_next_upper, "progress_increment": max(0.0, p_next - p_now),
        "progress_increment_lower": p_increment_lower, "progress_increment_upper": p_increment_upper,
        "volume_axis_count": 1.0, "volume_relaxation_factor": VOLUME_RELAXATION_FACTOR,
        "volume_relaxation_epsilon": _volume_relaxation(1)}
    point = max(0.0, _relaxed_geometric_volume((p_next,)) - _relaxed_geometric_volume((p_now,)))
    lower = max(0.0, _relaxed_geometric_volume((min(1.0, p_now_lower + p_increment_lower),))
                - _relaxed_geometric_volume((p_now_lower,)))
    upper = min(1.0, max(0.0, _relaxed_geometric_volume((min(1.0, p_now_upper + p_increment_upper),))
                         - _relaxed_geometric_volume((p_now_upper,))))
    lower = min(lower, point)
    upper = max(upper, point)
    if all(band.uncertainty_code == UNCERTAINTY_EXACT for band in bands):
        return NumericBand.exact(point), record
    return NumericBand(point, lower, upper, STATUS_NORMAL, max(band.uncertainty_code for band in bands),
                       max(band.alpha for band in bands if band.alpha > 0.0)), record


@dataclass(frozen=True)
class AccumulationVolumeCredit:
    """nano-graphrag ``VolumeCredit``: the unit's realized marginal hypervolume on the frozen pre-unit scale
    (``score``) and the expected next marginal hypervolume (``expected_next_score``, the stop statistic)."""
    score: NumericBand
    expected_next_score: NumericBand
    before_volume: float
    after_volume: float
    channel: dict

    def as_record(self):
        return {"version": VOLUME_CREDIT_VERSION, "score": self.score.as_record(),
                "expected_next_score": self.expected_next_score.as_record(), "before_volume": self.before_volume,
                "after_volume": self.after_volume, "channels": {ACCUMULATION_CHANNEL: dict(self.channel)}}


def assign_volume_credit(before, after):
    """The completed unit's realized marginal hypervolume (nano-graphrag ``_NumericalController.assign_volume_credit``),
    normalized by the expected total before the unit."""
    expected_next_score, record = expected_next_volume_credit(after)

    def coded(status):
        return AccumulationVolumeCredit(NumericBand.coded(status), expected_next_score, float(status), float(status),
                                        record)

    normalization = before.expected_results
    if normalization.status_code != STATUS_NORMAL:
        return coded(STATUS_UNIDENTIFIABLE if normalization.status_code == STATUS_UNIDENTIFIABLE
                     else STATUS_INSUFFICIENT)
    raw_expected_total = normalization.value
    observed_before = before.observed_results.value
    observed_after = after.observed_results.value
    if observed_after < observed_before:
        return coded(STATUS_UNIDENTIFIABLE)
    if raw_expected_total == 0.0:
        if observed_before != 0.0 or observed_after != 0.0:
            return coded(STATUS_UNIDENTIFIABLE)
        progress_before = progress_after = 1.0
        expected_total = MIN_DISCOVERABLE_COUNT
    else:
        if observed_before > raw_expected_total:
            return coded(STATUS_UNIDENTIFIABLE)
        expected_total = _progress_denominator(raw_expected_total, observed_after)
        progress_before = observed_before / expected_total
        progress_after = min(1.0, observed_after / expected_total)
    record = {**record, "raw_expected_results": raw_expected_total,
              "normalization_expected_results": expected_total,
              "axis_completed_by_zero_expectation": float(raw_expected_total == 0.0),
              "normalization_lower": normalization.lower, "normalization_upper": normalization.upper,
              "observed_before": observed_before, "observed_after": observed_after,
              "progress_before": progress_before, "progress_after": progress_after}
    before_volume = _relaxed_geometric_volume((progress_before,))
    after_volume = _relaxed_geometric_volume((progress_after,))
    return AccumulationVolumeCredit(NumericBand.exact(max(0.0, after_volume - before_volume)), expected_next_score,
                                    before_volume, after_volume, record)


def one_result_resolution(estimate):
    """The smallest hypervolume gain from one more result (one credit unit) on the open axis (nano-graphrag
    ``_one_result_resolution``)."""
    if estimate.expected_results.status_code != STATUS_NORMAL:
        return _coded_of((estimate.expected_results.status_code,))
    total = estimate.expected_results.value
    observed = estimate.observed_results.value
    if total < observed:
        return NumericBand.coded(STATUS_UNIDENTIFIABLE)
    next_discovery = estimate.expected_next_discoveries
    if total == 0.0:
        if observed != 0.0 or next_discovery.upper > 0.0:
            return NumericBand.coded(STATUS_UNIDENTIFIABLE)
        return NumericBand.exact(0.0)
    if not (observed < total or next_discovery.upper > 0.0):
        return NumericBand.exact(0.0)
    denominator = _progress_denominator(total, observed + MIN_DISCOVERABLE_COUNT)
    before = _relaxed_geometric_volume((min(1.0, observed / denominator),))
    increment = max(0.0, _relaxed_geometric_volume((min(1.0, (observed + 1.0) / denominator),)) - before)
    return NumericBand.exact(increment if increment > 0.0 else 0.0)


@dataclass(frozen=True)
class AccumulationThreshold:
    """nano-graphrag ``ThresholdUpdate``: one threshold decision."""
    gamma: NumericBand
    one_result_resolution: NumericBand
    productive_unit_baseline: NumericBand
    efficiency_fraction: float
    recent_credit_count: int
    recent_productive_count: int
    baseline_carried: bool
    ready: bool
    version: str

    @classmethod
    def fixed(cls, gamma):
        return cls(NumericBand.exact(gamma), NumericBand.coded(STATUS_INSUFFICIENT),
                   NumericBand.coded(STATUS_INSUFFICIENT), 0.0, 0, 0, False, True, FIXED_THRESHOLD_VERSION)

    def as_record(self):
        return {"version": self.version, "ready": self.ready, "gamma": self.gamma.as_record(),
                "one_result_resolution": self.one_result_resolution.as_record(),
                "productive_unit_baseline": self.productive_unit_baseline.as_record(),
                "efficiency_fraction": self.efficiency_fraction, "recent_credit_count": self.recent_credit_count,
                "recent_productive_count": self.recent_productive_count, "baseline_carried": self.baseline_carried}


def adaptive_marginal_credit_threshold(estimate, recent_realized_credits, last_productive_baseline):
    """gamma from the current one-result resolution and the recent productive realized credit (nano-graphrag
    ``adaptive_marginal_credit_threshold``)."""
    resolution = one_result_resolution(estimate)
    productive = tuple(value for value in recent_realized_credits if value > 0.0)
    carried = False
    if productive:
        baseline = NumericBand.exact(median(productive))
    elif last_productive_baseline is not None:
        baseline = NumericBand.exact(last_productive_baseline)
        carried = True
    else:
        baseline = NumericBand.coded(STATUS_INSUFFICIENT)
    candidates = []
    if resolution.status_code == STATUS_NORMAL:
        candidates.append(resolution.value)
    if baseline.status_code == STATUS_NORMAL:
        candidates.append(DEFAULT_EFFICIENCY_FRACTION * baseline.value)
    if candidates:
        gamma, ready = NumericBand.exact(max(candidates)), True
    else:
        gamma, ready = _coded_of((resolution.status_code, baseline.status_code)), False
    return AccumulationThreshold(gamma, resolution, baseline, DEFAULT_EFFICIENCY_FRACTION,
                                 len(recent_realized_credits), len(productive), carried, ready,
                                 ADAPTIVE_THRESHOLD_VERSION)


@dataclass(frozen=True)
class AccumulationEstimate:
    """The estimator's report after a unit: the incidence estimate, the volume credit of the last unit (``None``
    before any unit) and the stop statistic ``expected_next_gain`` (the expected next marginal hypervolume credit)."""
    incidence: AccumulationIncidence
    volume_credit: object
    expected_next_gain: NumericBand
    control: AccumulationControl

    def as_record(self):
        return {"turns": self.incidence.units, "expected_next_gain": self.expected_next_gain.as_record(),
                "parameters": self.control.as_record(), "incidence": self.incidence.as_record(),
                "volume_credit": None if self.volume_credit is None else self.volume_credit.as_record(),
                "provenance": accumulation_provenance()}


@dataclass(frozen=True)
class AccumulationDecision:
    """nano-graphrag ``ControllerVerdict`` and the items. ``stop`` is the verdict's stop or no item remaining
    (``stopped_by``). In the record, ``projected_gain`` is the stop statistic's band and ``continuation_cost`` the
    threshold gamma its upper bound was compared with (the names the runtime's yield table reads)."""
    stop: bool
    outcome: str
    flat_streak: int
    gamma: float
    control: AccumulationControl
    expected_next_hypervolume_credit: NumericBand
    threshold_update: AccumulationThreshold
    channel: dict
    items: object
    items_remaining: object
    stopped_by: tuple

    def as_record(self):
        return {"stop": self.stop, "projected_gain": self.expected_next_hypervolume_credit.as_record(),
                "continuation_cost": self.gamma,
                "decision_basis": "flat_streak_of_expected_next_hypervolume_credit_at_or_below_gamma_or_no_item_left",
                "outcome": self.outcome, "flat_streak": self.flat_streak,
                "controller": {**self.control.as_record(), "gamma": self.gamma},
                "threshold_update": self.threshold_update.as_record(),
                "channels": {ACCUMULATION_CHANNEL: dict(self.channel)}, "items": self.items,
                "items_remaining": self.items_remaining, "stopped_by": list(self.stopped_by)}


def accumulation_provenance():
    return {"controller": ACCUMULATION_CONTROLLER_VERSION, "estimator": ACCUMULATION_ESTIMATOR_VERSION,
            "volume_credit": VOLUME_CREDIT_VERSION, "source_repository": "nano-graphrag",
            "source_path": "question_pipeline/utilities/rarefaction.py", "source_revision": SOURCE_REVISION,
            "source_license": "MIT; notice in yield_control/__init__.py",
            "observation": "unit_marginal_credit_as_distinct_new_identity_count",
            "observed_total": "sum_of_marginal_credits_since_the_controller_was_built",
            "fit_coordinate": "unit_rank", "failed_units": "none_the_system_has_no_failed_unit",
            "stop": "streak_of_flat_units_or_no_item_left"}


class AccumulationYieldController:
    """Continue while nano-graphrag's estimator controller does not stop and an item remains (see the section
    comment). ``control`` is ``ADAPTIVE_CONTROL`` or ``FIXED_CONTROL``; ``items`` is None or the number of items of
    the episode's input list at its start (a positive integer: the loop runs at least one unit). A unit whose
    ``estimation_context`` carries ``items_remaining`` sets the number remaining to it (see the section comment). No
    cost."""

    def __init__(self, epoch, initial_credit, control, *, items=None):
        self.epoch = _epoch(epoch)
        self.initial_credit = _signed(initial_credit, "initial_credit")
        if not isinstance(control, AccumulationControl) or control not in (ADAPTIVE_CONTROL, FIXED_CONTROL):
            raise ValueError("accumulation_control_must_be_ADAPTIVE_CONTROL_or_FIXED_CONTROL")
        if items is not None and (type(items) is not int or items < 1):
            raise ValueError("accumulation_items_must_be_None_or_a_positive_integer")
        self.control = control
        self.items = items
        self._items_remaining = items
        self._estimator = _AccumulationIncidenceEstimator(control)
        self._gamma = control.gamma
        self._threshold_update = AccumulationThreshold.fixed(control.gamma)
        self._flat_streak = 0
        self._recent_realized_credits = []
        self._last_productive_baseline = None
        self._current_credit = self.initial_credit
        self._history = []
        self._volume_credit = None
        self._decision = self._record({}, NumericBand.coded(STATUS_INSUFFICIENT), False,
                                      "awaiting_eligible_observation")

    def _record(self, channel, expected_next, stop, outcome):
        exhausted = self._items_remaining == 0
        return AccumulationDecision(stop or exhausted, outcome, self._flat_streak, self._gamma, self.control,
                                    expected_next, self._threshold_update, channel, self.items,
                                    self._items_remaining,
                                    (("estimator",) if stop else ()) + (("items",) if exhausted else ()))

    def _verdict(self, after, volume_credit, is_root):
        """nano-graphrag ``_NumericalController.observe`` for the one channel."""
        remaining = after.remaining_results
        done = remaining.status_code == STATUS_NORMAL and remaining.upper <= self.control.rho
        channel = {"expected_next_discoveries": after.expected_next_discoveries.as_record(), "done": done,
                   "remaining_status_code": remaining.status_code, "remaining_upper": remaining.upper,
                   "rho": self.control.rho, "hypervolume_axis": dict(volume_credit.channel)}
        expected_next = volume_credit.expected_next_score
        flat = expected_next.status_code == STATUS_NORMAL and expected_next.upper <= self._gamma
        if not flat:
            self._flat_streak = 0
            return self._record(channel, expected_next, False,
                                "insufficient" if expected_next.status_code != STATUS_NORMAL else "continuing")
        self._flat_streak += 1
        if self._flat_streak >= self.control.streak_length:
            if done:
                outcome = "whole_convergence" if is_root else "local_convergence"
            else:
                outcome = "root_incomplete" if is_root else "local_saturation"
            return self._record(channel, expected_next, True, outcome)
        return self._record(channel, expected_next, False, "flat_progressing")

    def observe(self, unit_label, value, is_root=False):
        cumulative, context = _completed(value)
        discovery = cumulative - self._current_credit
        if discovery < 0:
            raise ValueError(f"accumulation_credit_cannot_fall:{unit_label}:{discovery!r}")
        if self._items_remaining == 0:
            raise RuntimeError(f"accumulation_no_item_left_for_unit:{unit_label}")
        reported = None if context is None else context.get("items_remaining")
        if reported is not None and (type(reported) is not int or reported < 0):
            raise ValueError(f"accumulation_items_remaining_must_be_an_integer_at_least_0:{unit_label}:{reported!r}")
        before = self._estimator.snapshot()
        self._estimator.observe(discovery)
        after = self._estimator.snapshot()
        volume_credit = assign_volume_credit(before, after)
        if volume_credit.score.status_code == STATUS_NORMAL:
            self._recent_realized_credits = [*self._recent_realized_credits,
                                             volume_credit.score.value][-self.control.window_size:]
        if self.control.threshold == ADAPTIVE_THRESHOLD_VERSION:
            update = adaptive_marginal_credit_threshold(after, tuple(self._recent_realized_credits),
                                                        self._last_productive_baseline)
        else:
            update = AccumulationThreshold.fixed(self._gamma)
        if (update.productive_unit_baseline.status_code == STATUS_NORMAL
                and update.productive_unit_baseline.value > 0.0):
            self._last_productive_baseline = update.productive_unit_baseline.value
        if update.ready:
            self._gamma = update.gamma.value
        self._threshold_update = update
        if reported is not None:
            self._items_remaining = reported      # the episode's own count of its list after this unit
        elif self._items_remaining is not None:
            self._items_remaining -= 1
        self._current_credit = cumulative
        self._history.append(discovery)
        self._volume_credit = volume_credit
        if update.ready:
            self._decision = self._verdict(after, volume_credit, bool(is_root))
        else:
            # nano-graphrag ``defer``: no verdict, the flat streak is kept.
            self._decision = self._record({}, volume_credit.expected_next_score, False, "threshold_insufficient")
        estimate = AccumulationEstimate(after, volume_credit, volume_credit.expected_next_score, self.control)
        return YieldStep(str(unit_label), cumulative, discovery, estimate, self._decision, bool(is_root),
                         self._decision.outcome == "root_incomplete")

    def state(self):
        incidence = self._estimator.snapshot()
        expected_next, _channel = expected_next_volume_credit(incidence)
        return YieldState(self.epoch, self.initial_credit, self._current_credit, tuple(self._history),
                          AccumulationEstimate(incidence, self._volume_credit, expected_next, self.control),
                          self._decision)


# ============================================================================
# The bounded-quality and completion yield controllers. Same shape: observe(unit_label, value, is_root),
# state(), transitioned(epoch); a runtime owns action completion.
# ============================================================================

class BoundedQualityYieldController:
    """Continue while more quality credit, within the declared maximum, is forecast above the cost."""

    def __init__(self, epoch, initial_credit, cost, maximum_credit, settings=None):
        self.epoch = _epoch(epoch)
        self.initial_credit = _signed(initial_credit, "initial_credit")
        self.cost = _score(cost, "continuation cost")
        self.maximum_credit = _score(maximum_credit, "maximum bounded credit")
        self.settings = _parameters(settings)
        self.estimator = BoundedQualityYieldEstimator(self.initial_credit, self.maximum_credit, self.settings)
        self._current_credit = self.initial_credit

    def observe(self, unit_label, value, is_root=False):
        cumulative, context = _completed(value)
        delta = cumulative - self._current_credit
        estimate = self.estimator.observe(delta, context=context)
        self._current_credit = cumulative
        return YieldStep(str(unit_label), cumulative, delta, estimate,
                         predicted_gain_upper_bound(estimate.expected_next_gain, self.cost), bool(is_root))

    def state(self):
        estimate = self.estimator.state()
        return YieldState(self.epoch, self.initial_credit, self._current_credit, self.estimator.scores,
                          estimate, predicted_gain_upper_bound(estimate.expected_next_gain, self.cost))

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError("An explicit new epoch must have a distinct id")
        return BoundedQualityYieldController(epoch, self._current_credit, self.cost, self.maximum_credit,
                                             self.settings)


class CompletionYieldController:
    """Continue until credit reaches the commission's finite target or is revised below it."""

    def __init__(self, epoch, initial_credit, cost, target, settings=None):
        self.epoch = _epoch(epoch)
        self.initial_credit = _signed(initial_credit, "initial_credit")
        self.cost = _score(cost, "continuation cost")
        self.settings = _parameters(settings)
        self.estimator = CompletionYieldEstimator(self.initial_credit, target, self.settings)
        self.target = self.estimator.target
        if self.cost >= self.target:
            raise ValueError('completion_cutoff_must_be_below_target')
        self._current_credit = self.initial_credit

    def observe(self, unit_label, value, is_root=False):
        cumulative, context = _completed(value)
        delta = cumulative - self._current_credit
        estimate = self.estimator.observe(delta, context=context)
        self._current_credit = cumulative
        return YieldStep(str(unit_label), cumulative, delta, estimate,
                         predicted_gain_upper_bound(estimate.expected_next_gain, self.cost), bool(is_root))

    def state(self):
        estimate = self.estimator.state()
        return YieldState(self.epoch, self.initial_credit, self._current_credit, self.estimator.scores,
                          estimate, predicted_gain_upper_bound(estimate.expected_next_gain, self.cost))

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError("An explicit new epoch must have a distinct id")
        return CompletionYieldController(epoch, self._current_credit, self.cost, self.target, self.settings)



# ============================================================================
# ForecastYieldController: the fourth controller. A forecast that is a formula of each offered action's ceiling and of
# what actions of its kind realized before; no estimator is fitted to the credit's history and the model estimates
# nothing. The credit formula enters only through ``ceiling`` (``method_loop.episode_type``).
#
# For an offered action ``a`` of the action kind ``k`` (the episode's binding path and the action type):
#
# * a bounded action (a finite ceiling c): forecast = (realized fraction of k) x c, a ceiling of 0 forecasts 0. The
#   realized fraction is the share of its ceiling that units of k earned (obtained/ceiling). The owner: "count this
#   current history always more. the ledger should count for equal weight with current history": the ledger's
#   history of k as a whole (each earlier run's unit weighted by its age when old rows are forgotten) and this
#   episode's own units of k as a whole each weigh one half: the fraction is the mean of the ledger's mean fraction
#   and this episode's mean fraction. With only one of the two, that one alone; with neither, one half. Within this
#   episode's own units of k the recent ones count more (the owner: "the yield estimator must learn just like the
#   accumulation estimator from past experience after the first round. So after nothing new is added a second
#   time, the yield estimator should be very low for that"; "why you can't just threshold better or have the yield
#   estimator update faster"): the latest own unit of k has weight 1 and each earlier one half the weight of the one
#   after it (half-life: one unit), so this episode's own fraction (own mean gain when UNBOUNDED) is that
#   recency-weighted mean, not the plain mean. The ledger's half and the equal weighting of ledger and own history
#   are unchanged. The ledger's shares of k are only its rows recorded under k's own definition of credit and
#   ceiling (``ForecastParameters.definition_of(k)``: the credit's definition and k's own ceiling version, so changing
#   one action's ceiling discards only that action's shares): a share learned under another definition is on another
#   scale and is not used; with no such row the ledger has no half.
# * a pending unit is not an observation: a unit whose outcome is pending (its action started work, e.g. a job a child
#   launched and returned parked, that a later unit of the same action finishes and extracts) has a rise that measures
#   nothing of its action yet, and seconds that cover only the start. It gives no share or gain of its kind, and its
#   seconds are not its kind's unit seconds, in this episode's own history (``pending`` of the unit's facts) as in the
#   ledger (its row is resolved with the outcome ``pending``, which the ledger's history skips). The later unit that
#   continues the work is the observation, as usual. There is no default: every unit's facts say whether it is pending.
# * an UNBOUNDED action: there is no ceiling to scale, so the forecast is the typical gain of k, by the same rule: the
#   mean of the ledger's mean gain and this episode's recency-weighted mean gain, or the one that exists. With no unit of k anywhere
#   the forecast is unknown, and an unknown forecast never lets the episode stop (as in the three controllers,
#   unknown stays unknown).
# * the cost of ``a`` is its expected seconds: for an action type of ``job_kinds`` whose ledger kind has measured
#   jobs, the median job duration plus the median seconds the model took to decide; otherwise the median measured
#   wall seconds of the units of k that are not pending (ledger history and this episode); with none, the median unit seconds of this
#   episode so far; with none, unknown (cost 0 in the stop rule). Seconds are not credit: the ledger's seconds of k
#   (unit and decision seconds) are every resolved row of k that is not pending, whatever definition it was recorded under.
# * the stop rule: stop when no offered action's forecast exceeds expected seconds x ``exchange_rate`` and the episode
#   must not continue. The episode must continue while it holds work it started and has not finished (the owner,
#   2026-11-21: "the head must finish parked jobs": a job a child launched and returned parked); the unit's facts say so
#   (``must_continue``, from the episode's ``resume_action``, ``method_loop.episode_type``), and while it is true the
#   controller does not stop, whatever the forecasts. There is no default: every unit's facts say whether it must.
# * the per-action gate (``method_loop.episode_type``): the same threshold also refuses the model's chosen action
#   before it runs when its forecast does not exceed it (the owner: "since the numbers for credit are very similar, you
#   should be able to find one threshold to cap wasteful actions reasonably well"). It is a forecast comparison, not a
#   budget. An unknown forecast is not refused.
# ============================================================================

FORECAST_VERSION = "forecast_yield_v1"
UNBOUNDED_TEXT = "unbounded"
FRACTION_TOLERANCE = 1e-9


def _is_ceiling_number(value):
    return not isinstance(value, str)


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0


def _fraction(gain, ceiling, what):
    """What share of its ceiling a unit earned (a Beta observation); a unit that lost credit is an error here."""
    fraction = gain / ceiling
    if fraction < -FRACTION_TOLERANCE:
        raise ValueError(f"forecast_cannot_learn_a_negative_rise:{what}:{gain!r}")
    return min(1.0, max(0.0, fraction))


@dataclass(frozen=True)
class ForecastParameters:
    """The parameter set of the forecast controller; nothing in it names a credit formula.

    ``exchange_rate``: credit per second; an action is worth taking while its forecast gain exceeds its expected
    seconds times this rate. ``forget_old_rows``: weight each ledger row by the estimate table's
    ``ForgettingPolicy`` (rows past ``history_seconds`` are dropped, the rest halve every
    ``history_half_life_seconds``). ``job_kinds``: action type -> the prefix of the ledger kinds of the jobs that
    action launches, whose measured durations are its expected seconds. ``definition``: the name of the definition of
    credit and ceiling the shares of each action are on (the episode derives it: a digest of its credit definition
    record and the action's ceiling version), as a mapping action type -> name, or one name for every action of an
    episode whose ceilings have one version together. ``definition_of(action_type)`` is that action's name; an action
    the mapping does not name raises ``forecast_definition_missing_for_action``. The controller hands
    ``definition_of`` to the ledger, which writes each action's name on its forecast rows and reads as that action's
    shares only the rows written under the same name (a share learned under another credit or ceiling is on another
    scale). Required: there is no default."""
    exchange_rate: float
    forget_old_rows: bool
    job_kinds: Mapping
    definition: str | Mapping

    def __post_init__(self):
        rate = _finite_number("exchange_rate", self.exchange_rate)
        if rate < 0:
            raise ValueError("exchange_rate_must_not_be_negative")
        if type(self.forget_old_rows) is not bool:
            raise ValueError("forget_old_rows_must_be_a_boolean")
        if (not isinstance(self.job_kinds, Mapping)
                or any(type(key) is not str or type(value) is not str or not key or not value
                       for key, value in self.job_kinds.items())):
            raise ValueError("job_kinds_must_map_action_types_to_ledger_kind_prefixes")
        if isinstance(self.definition, Mapping):
            if not self.definition or any(type(key) is not str or type(value) is not str or not key or not value
                                          for key, value in self.definition.items()):
                raise ValueError("forecast_definition_must_map_action_types_to_names")
            object.__setattr__(self, "definition", dict(self.definition))
        elif type(self.definition) is not str or not self.definition:
            raise ValueError("forecast_definition_required")
        object.__setattr__(self, "job_kinds", dict(self.job_kinds))

    def definition_of(self, action_type):
        """The name of the definition of credit and ceiling the shares of ``action_type`` are on."""
        if type(self.definition) is str:
            return self.definition
        if action_type not in self.definition:
            raise ValueError(f"forecast_definition_missing_for_action:{action_type}")
        return self.definition[action_type]

    def as_record(self):
        definition = self.definition if type(self.definition) is str else dict(self.definition)
        return {"exchange_rate": self.exchange_rate, "forget_old_rows": self.forget_old_rows,
                "job_kinds": dict(self.job_kinds), "definition": definition}


def _forecast_parameters(value):
    if isinstance(value, ForecastParameters):
        return value
    if isinstance(value, Mapping):
        return ForecastParameters(**value)
    raise TypeError("forecast settings must be ForecastParameters or their record")


def _forecast_context(context):
    """The facts of one completed unit the system puts in its estimation context (``estimation_context['forecast']``)."""
    required = {"action_type", "ceiling", "unit_seconds", "decision_seconds", "pending", "must_continue", "next_offered"}
    if not isinstance(context, Mapping) or not isinstance(context.get("forecast"), Mapping):
        raise ValueError("forecast_controller_requires_estimation_context_forecast")
    facts = context["forecast"]
    if set(facts) != required:
        raise ValueError(f"forecast_context_requires_exactly:{sorted(required)}")
    if type(facts["action_type"]) is not str or not facts["action_type"]:
        raise ValueError("forecast_action_type_required")
    for name in ("unit_seconds", "decision_seconds"):
        _score(facts[name], name)
    if type(facts["pending"]) is not bool:
        raise ValueError("forecast_pending_must_be_a_boolean")
    if type(facts["must_continue"]) is not bool:
        raise ValueError("forecast_must_continue_must_be_a_boolean")
    if _is_ceiling_number(facts["ceiling"]):
        _score(facts["ceiling"], "ceiling")
    elif facts["ceiling"] != UNBOUNDED_TEXT:
        raise ValueError("forecast_ceiling_is_a_number_or_unbounded")
    offered = facts["next_offered"]
    if not isinstance(offered, Mapping):
        raise ValueError("forecast_next_offered_must_map_action_types_to_ceilings")
    for name, ceiling in offered.items():
        if type(name) is not str or not name:
            raise ValueError("forecast_offered_action_type_required")
        if _is_ceiling_number(ceiling):
            _score(ceiling, "offered ceiling")
        elif ceiling != UNBOUNDED_TEXT:
            raise ValueError("forecast_ceiling_is_a_number_or_unbounded")
    return facts


def _recent(values):
    """This episode's own ``(_, value)`` pairs of one action kind, oldest first, with the weights of recency: the
    latest has weight 1 and each earlier one half the weight of the one after it (half-life: one unit)."""
    return [(0.5 ** (len(values) - 1 - index), value) for index, (_, value) in enumerate(values)]


def forecast_actions(parameters, observations, histories, offered):
    """One row per offered action (``{action type: ceiling number or 'unbounded'}``), from this episode's own
    ``observations`` (each ``{'action_type', 'ceiling', 'gain', 'unit_seconds', 'decision_seconds', 'pending'}``;
    a pending unit gives its kind no share, gain or unit seconds) and the
    ledger's ``histories`` (``{action type: {'rows': [{'ceiling', 'gain', 'weight'}], 'seconds': [{'seconds',
    'decision_seconds'}], 'job_seconds': [seconds]}}``: ``rows`` the shares, of the action's own definition only;
    ``seconds`` every resolved row of the kind whatever its definition): ``{'action_type', 'ceiling', 'forecast_gain' (``None``: unknown),
    'expected_seconds' (``None``: unknown), 'seconds_basis', 'threshold', 'worth'}``. The formulas are described
    above."""
    decision_pool = [item["decision_seconds"] for item in observations]
    unit_pool = [item["unit_seconds"] for item in observations]
    rows = []
    for action_type, ceiling in offered.items():
        history = histories[action_type]
        own = [item for item in observations if item["action_type"] == action_type and not item["pending"]]
        if _is_ceiling_number(ceiling):
            if ceiling == 0:
                forecast = 0.0
            else:
                ledger = [(row["weight"], _fraction(row["gain"], row["ceiling"], action_type))
                          for row in history["rows"] if _is_ceiling_number(row["ceiling"]) and row["ceiling"] > 0]
                mine = [(0.0, _fraction(item["gain"], item["ceiling"], action_type))
                        for item in own if _is_ceiling_number(item["ceiling"]) and item["ceiling"] > 0]
                mine = _recent(mine)
                weight = math.fsum(w for w, _ in ledger)
                means = ([math.fsum(w * f for w, f in ledger) / weight] if weight else []) + (
                    [math.fsum(w * f for w, f in mine) / math.fsum(w for w, _ in mine)] if mine else [])
                forecast = (math.fsum(means) / len(means) if means else 0.5) * ceiling
        else:
            weight = math.fsum(row["weight"] for row in history["rows"])
            mine = _recent([(0.0, item["gain"]) for item in own])
            means = ([math.fsum(row["weight"] * row["gain"] for row in history["rows"]) / weight] if weight else []) + (
                [math.fsum(w * g for w, g in mine) / math.fsum(w for w, _ in mine)] if mine else [])
            forecast = math.fsum(means) / len(means) if means else None
        decision = (_median(decision_pool) if decision_pool
                    else _median([row["decision_seconds"] for row in history["seconds"]]) if history["seconds"] else None)
        action_seconds = [row["seconds"] for row in history["seconds"]] + [item["unit_seconds"] for item in own]
        if history["job_seconds"]:
            seconds = _median(history["job_seconds"]) + (0.0 if decision is None else decision)
            basis = "ledger_job_duration_plus_decision"
        elif action_seconds:
            seconds, basis = _median(action_seconds), "action_unit_history"
        elif unit_pool:
            seconds, basis = _median(unit_pool), "episode_median_unit"
        else:
            seconds, basis = None, "unknown"
        threshold = (0.0 if seconds is None else seconds) * parameters.exchange_rate
        rows.append({"action_type": action_type, "ceiling": ceiling if _is_ceiling_number(ceiling) else UNBOUNDED_TEXT,
                     "forecast_gain": forecast, "expected_seconds": seconds, "seconds_basis": basis,
                     "threshold": threshold, "worth": forecast is None or forecast > threshold})
    return tuple(rows)


@dataclass(frozen=True)
class ForecastDecision:
    """``must_continue``: the episode holds work it started and must finish, so it does not stop (``stop`` is False)."""
    stop: bool
    rows: tuple
    must_continue: bool

    def as_record(self):
        return {"stop": self.stop, "rows": [dict(row) for row in self.rows], "must_continue": self.must_continue,
                "decision_basis": "no_offered_action_forecast_exceeds_expected_seconds_times_exchange_rate_"
                                  "and_no_started_work_to_finish"}


@dataclass(frozen=True)
class ForecastStep:
    unit_label: str
    credit: float
    marginal_credit: float
    decision: ForecastDecision
    is_root: bool = False
    requests_transition: bool = False

    @property
    def stop(self):
        return self.decision.stop

    def as_record(self):
        return {"unit_label": self.unit_label, "credit": self.credit, "marginal_credit": self.marginal_credit,
                "decision": self.decision.as_record(), "stop": self.stop, "is_root": self.is_root,
                "requests_transition": self.requests_transition}


class ForecastYieldState:
    """What the forecast controller holds after its completed units. ``forecast(offered)`` gives the rows for a
    decision that offers ``offered`` (``{action type: ceiling or 'unbounded'}``) from what has been learned so far."""

    def __init__(self, epoch, initial_credit, current_credit, history, decision, parameters, forecast):
        self.epoch, self.initial_credit, self.current_credit = epoch, initial_credit, current_credit
        self.history, self.decision, self.parameters, self._forecast = history, decision, parameters, forecast

    @property
    def stop(self):
        return self.decision.stop

    def forecast(self, offered):
        return self._forecast(offered)

    def as_record(self):
        return {"epoch": self.epoch, "initial_credit": self.initial_credit, "current_credit": self.current_credit,
                "scores": list(self.history), "decision": self.decision.as_record(),
                "parameters": self.parameters.as_record(), "provenance": forecast_provenance()}


def forecast_provenance():
    return {"controller": FORECAST_VERSION, "forecast": "realized_fraction_times_ceiling_or_typical_gain_if_unbounded",
            "fraction": "mean_of_ledger_mean_and_own_recency_weighted_mean_each_one_half_own_half_life_one_unit",
            "pending": "a_pending_unit_gives_its_kind_no_share_gain_or_unit_seconds_own_or_ledger",
            "cost": "expected_seconds",
            "stop": "no_offered_forecast_exceeds_expected_seconds_times_exchange_rate_and_not_must_continue",
            "model_estimates": False}


class ForecastYieldController:
    """Continue while some offered action is forecast to earn more than its expected seconds at the exchange rate.

    The system attaches the estimate-ledger access once (``attach``) and gives each completed unit's facts in its
    estimation context (``estimation_context['forecast']``: the action type and its ceiling, the unit's measured
    seconds and decision seconds, whether its outcome is pending, whether the episode must continue (it holds started
    work it must finish: no stop while it does) and the ceilings the next decision offers). Nothing here writes the
    ledger."""

    def __init__(self, epoch, initial_credit, settings):
        self.epoch = _epoch(epoch)
        self.initial_credit = _signed(initial_credit, "initial_credit")
        self.settings = _forecast_parameters(settings)
        self.exchange_rate = self.settings.exchange_rate
        self._ledger, self._observations, self._scores = None, (), ()
        self._current_credit = self.initial_credit
        self._decision = ForecastDecision(False, (), False)

    def attach(self, ledger):
        """The runner's read access to the estimate ledger: ``ledger.history(action_type, job_prefix, forget)``. The
        controller hands the ledger each action's definition (``ledger.define(settings.definition_of)``), so the ledger
        writes an action's definition on its forecast rows and reads as that action's shares only the rows of the same
        definition."""
        if self._ledger is not None:
            raise RuntimeError("forecast_controller_already_has_a_ledger")
        ledger.define(self.settings.definition_of)
        self._ledger = ledger

    def _histories(self, offered):
        if self._ledger is None:
            raise RuntimeError("forecast_controller_has_no_ledger")
        return {action_type: self._ledger.history(action_type, self.settings.job_kinds.get(action_type),
                                                  self.settings.forget_old_rows) for action_type in offered}

    def _rows(self, observations, offered):
        return forecast_actions(self.settings, observations, self._histories(offered), offered)

    def observe(self, unit_label, value, is_root=False):
        cumulative, context = _completed(value)
        facts = _forecast_context(context)
        delta = cumulative - self._current_credit
        self._observations = (*self._observations, {
            "action_type": facts["action_type"], "ceiling": facts["ceiling"], "gain": delta,
            "unit_seconds": facts["unit_seconds"], "decision_seconds": facts["decision_seconds"],
            "pending": facts["pending"]})
        self._scores = (*self._scores, delta)
        self._current_credit = cumulative
        rows = self._rows(self._observations, facts["next_offered"])
        must_continue = facts["must_continue"]
        self._decision = ForecastDecision(not must_continue and not any(row["worth"] for row in rows), rows, must_continue)
        return ForecastStep(str(unit_label), cumulative, delta, self._decision, bool(is_root))

    def state(self):
        observations = self._observations
        return ForecastYieldState(self.epoch, self.initial_credit, self._current_credit, self._scores,
                                  self._decision, self.settings,
                                  lambda offered: self._rows(observations, offered))
