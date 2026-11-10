"""Template-derived yield estimation and a plain continuation controller.

The exact nano-graphrag source is vendored with its MIT license and SHA-256.
The completed real-score quasi-likelihood adapter comes from the supplied
orbital template. Raw credit marks are fitted against measured progress-receipt
times. Signed corrections use paired gain/loss marks at the SAME real times:
positive=max(delta,0), loss=max(-delta,0). No raw observation is replaced,
removed, smoothed, or appended twice. Each mark fits the full observed history.

Gain/loss model bands use Bonferroni alpha/2 and interval subtraction. This is
an approximate, uncalibrated working-model interval; Bonferroni allocation does
not make the source Laplace approximation coverage calibrated. Before any loss
has been observed, only the nonnegative time-conditioned model is used.
The no-loss working model assumes zero loss until a correction is observed.
After a loss, both marked fits are retained for every later full-history fit.

The controller receives one cumulative score per completed local action and
passes its raw signed difference to the estimator. Its only numerical stop rule
is available upper bound <= configured cost. It has no memory, smoothing,
consecutive-zero rule, action cap, source-completion test, or scientific gate.
"""

from dataclasses import dataclass, replace
from copy import deepcopy
import json
import math
from numbers import Real
from typing import Mapping, Sequence

from .vendor import nano_rarefaction as template
from .execution_timing import PROGRESS_TIME_VERSION


NumericBand = template.NumericBand
STATUS_NORMAL = template.STATUS_NORMAL
STATUS_INSUFFICIENT = template.STATUS_INSUFFICIENT
STATUS_UNIDENTIFIABLE = template.STATUS_UNIDENTIFIABLE

SOURCE_SHA256 = "02af19652d69f368ee8875d3b27cad0bb2bbc8d1f8274344b72a4437092cdd35"
SOURCE_REVISION = "60a167f9eeda0c9ea2ca294724174948947baf3f"
ESTIMATOR_VERSION = "real_time_signed_credit_mark_yield_v2"


def _score(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite non-negative real number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative real number")
    return number


@dataclass(frozen=True)
class YieldParameters:
    # Compatibility operands for saved caller definitions only. Neither value
    # controls fit availability, truncates history, or changes a prediction.
    window_size: int | None = None
    subsample_size: int | None = None
    uncertainty_alpha: float = template.DEFAULT_ALPHA

    def __post_init__(self):
        for name in ("window_size", "subsample_size"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(name + "_legacy_value_requires_nonnegative_integer_or_none")
        if not 0 < _score(self.uncertainty_alpha, "uncertainty_alpha") < 1:
            raise ValueError("uncertainty_alpha must be between zero and one")

    def as_record(self):
        return {
            "window_size": self.window_size,
            "subsample_size": self.subsample_size,
            "uncertainty_alpha": self.uncertainty_alpha,
            "window_semantics": "legacy_ignored_no_minimum_history",
            "subsample_semantics": "legacy_ignored_full_history",
        }


def provenance():
    return {
        "estimator": ESTIMATOR_VERSION,
        "source_repository": "nano-graphrag",
        "source_path": "question_pipeline/utilities/rarefaction.py",
        "source_revision": SOURCE_REVISION,
        "source_sha256": SOURCE_SHA256,
        "source_license": "MIT; gene_annotation_episode/vendor/LICENSE.nano-graphrag",
        "vendored_source": "gene_annotation_episode/vendor/nano_rarefaction.py",
        "template_estimator": template.INCIDENCE_ESTIMATOR_VERSION,
        "turn_unit": "completed_episode_acquisition",
        "credit_input": "projected_marginal_credit",
        "fit_coordinate": "measured_progress_receipt_time",
        "forecast": "conditional_acquisition_credit_at_recorded_current_time",
        "forecast_units": "unchanged_iterator_credit_not_credit_per_second",
        "temporal_prior_scale": "first_measured_episode_start_to_progress_receipt_span",
        "minimum_history": None,
        "per_episode_units": {
            "direct_tool": "One completed selected acquisition supplies one local observation",
            "reasoning": "One completed scientific interpretation action supplies one local observation, including when it uses existing evidence",
            "read_or_comparison": "A completed acquisition can have zero marginal credit",
            "shared_refresh": "Shared credit refreshes do not add action observations",
            "executed_failure": "An executed failed or unavailable tool/reason action supplies its actual progress observation, including zero when none was retained",
            "unexecuted_request": "Invalid pre-execution requests create no acquisition or estimator observation",
            "root": "One root-selected completed reasoning action, tool or child investigation supplies one root action; nested child operations add no ancestor observations",
        },
        "adaptations": [
            "Real marginal credit responses pass into the fit without integer coercion",
            "Completed Episode acquisitions condition on observation; no failure/usability model",
            "A fresh fitter cold-fits the full raw credit history against its recorded real times",
            "Original numeric bands and delta/Laplace curvature approximation are retained",
            "Signed corrections use paired gain/loss marks at the same progress-receipt times",
            "After an observed loss, component alpha/2 bands subtract to an approximate signed net interval",
        ],
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
            "The inherited local optimizer has no global optimum or convergence certificate; bands can jump across history lengths",
            "Before any observed loss the original nonnegative model assumes zero loss; this is an explicit working-model assumption",
            "Gain/loss interval subtraction is not coverage calibrated; Bonferroni allocation cannot calibrate the underlying Laplace approximation",
        ],
    }


class _RealScoreFit(template._IncidenceEstimator):
    """Reuse the optimizer/kernel with real time as its explanatory operand."""

    def __init__(self, *, alpha):
        super().__init__(alpha=alpha)
        # Start at the existing prior mode and its true curvature. In
        # particular an empty history must not use the optimizer's identity
        # matrix as if it were prior/posterior information.
        self._fit_parameters = [0., math.log(.05), 0., 0.]
        self._fit_inverse_hessian = [[36., 0., 0., 0.], [0., 4., 0., 0.],
                                    [0., 0., 36., 0.], [0., 0., 0., 0.]]

    @staticmethod
    def _observation_loss(parameters, coordinate, discovery):
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
                for weight, latent in zip(
                    template._LOG_QUADRATURE_WEIGHTS, template._QUADRATURE_LATENT)
            )
        )
        return -template._logsumexp(terms)

    @classmethod
    def _history_loss(cls, parameters, coordinates, discoveries):
        # Deliberately no int(discovery), identity conversion or smoothing.
        return cls._prior_loss(parameters) + sum(
            cls._observation_loss(parameters, coordinate, discovery)
            for coordinate, discovery in zip(coordinates, discoveries)
        )

    @staticmethod
    def _metric_discovery(parameters, coordinate):
        beta, log_delta, _observation_intercept, _coupling = parameters
        delta = math.exp(float(log_delta))
        return sum(
            math.exp(weight) * math.exp(max(-50.0, min(50.0,
                beta - delta * coordinate + latent)))
            for weight, latent in zip(
                template._LOG_QUADRATURE_WEIGHTS, template._QUADRATURE_LATENT)
        )


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
        return {
            "turns": self.turns,
            "expected_next_gain": self.expected_next_gain.as_record(),
            "parameters": self.parameters.as_record(),
            "diagnostics": dict(self.diagnostics),
            "provenance": provenance() if self.estimator_binding is None else dict(self.estimator_binding),
        }


def _time_point(value):
    if not isinstance(value, Mapping) or value.get("version") != PROGRESS_TIME_VERSION:
        return None, "progress_time_unavailable"
    if value.get("status") != "available":
        return None, value.get("unavailable_reason") or "progress_time_unavailable"
    integers = ("origin_monotonic_ns", "observed_monotonic_ns",
                "reference_observation_monotonic_ns")
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
    if (scale == 0 or not math.isclose(scale, (reference-origin)/1e9, rel_tol=1e-12)
            or not math.isclose(elapsed, (observed-origin)/1e9, rel_tol=1e-12)):
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
                packet.get(key) != point.get(key) for key in
                ("run_id", "episode_id", "original_decision_index")):
            return (), 0., {"unavailable_reason": "progress_time_completion_identity_conflict"}
        points.append(point)
    target, reason = _time_point(evaluation_time if evaluation_time is not None else
                                points[-1] if points else None)
    if not points and target is None:
        # At an unobserved origin, the intercept prior requires no duration.
        # This does not fabricate time for any actual history entry.
        return (), 0., {"time_binding": "unobserved_origin_prior_only",
                       "unobserved_time_reason": reason}
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
    coordinates = tuple((point["observed_monotonic_ns"]-reference)/1e9/scale for point in points)
    coordinate = (target["observed_monotonic_ns"]-reference)/1e9/scale
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


def estimate_nonnegative_yield(scores: Sequence[Real], parameters: YieldParameters | None = None,
                               *, contexts=None, evaluation_time=None):
    """Fit all raw marks at real receipt times; never fit their action ranks."""
    parameters = YieldParameters() if parameters is None else parameters
    if not isinstance(parameters, YieldParameters):
        raise TypeError("parameters must be YieldParameters")
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

    # Never reuse last turn's prediction or fit state. The history alone
    # determines this turn's fit, including the original fixed yield priors.
    fit = _RealScoreFit(alpha=parameters.uncertainty_alpha)
    try:
        fitted, covariance, objective = fit._fit_full_history(
            coordinates, history, coupling_identifiable=False)
        if not all(math.isfinite(value) for row in covariance for value in row):
            raise ArithmeticError("Non-finite fitted covariance")
        point = fit._metric_discovery(fitted, target)
        variance = fit._metric_variance(fitted, covariance,
            lambda values: fit._metric_discovery(values, target))
        band = NumericBand.laplace(point, variance, parameters.uncertainty_alpha)
        diagnostics.update({"yield_intercept": fitted[0],
            "reference_span_decay": math.exp(fitted[1]), "fit_objective": objective,
            "next_gain_variance": variance})
    except (ArithmeticError, OverflowError, ValueError) as error:
        # Numerical non-identifiability is a prediction status, never a zero
        # yield or a reason for continuation to manufacture a stop.
        band = NumericBand.coded(STATUS_UNIDENTIFIABLE)
        diagnostics["fit_status"] = type(error).__name__
    return YieldEstimate(turns, band, parameters, diagnostics)




def _signed(value: object, name: str = "marginal credit") -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite real number")
    return number


@dataclass(frozen=True)
class SignedNumericBand:
    """Signed net interval; unavailable statuses retain numeric sentinel codes.

    The original NumericBand is intentionally left unchanged in the exact vendor
    copy. Its nonnegative restriction does not represent net gain after correction.
    """

    value: float
    lower: float
    upper: float
    status_code: int = STATUS_NORMAL
    uncertainty_code: int = template.UNCERTAINTY_LAPLACE
    alpha: float = template.DEFAULT_ALPHA

    def __post_init__(self):
        values = tuple(_signed(v, "band coordinate") for v in
                       (self.value, self.lower, self.upper))
        for name, value in zip(("value", "lower", "upper"), values):
            object.__setattr__(self, name, value)
        if self.status_code != STATUS_NORMAL:
            if self.status_code not in (STATUS_INSUFFICIENT, STATUS_UNIDENTIFIABLE):
                raise ValueError("Unknown numeric status")
            if values != (float(self.status_code),) * 3:
                raise ValueError("Unavailable bands must preserve status sentinels")
            if self.uncertainty_code != -1 or self.alpha != -1:
                raise ValueError("Unavailable uncertainty must be explicit")
        elif not values[1] <= values[0] <= values[2]:
            raise ValueError("Band must satisfy lower <= value <= upper")
        elif self.uncertainty_code not in (template.UNCERTAINTY_EXACT,
                template.UNCERTAINTY_CHEBYSHEV, template.UNCERTAINTY_LAPLACE):
            raise ValueError("Unknown uncertainty code")
        elif self.uncertainty_code == template.UNCERTAINTY_EXACT:
            if self.alpha != 0:
                raise ValueError("An exact signed band has alpha=0")
        elif not 0 < _signed(self.alpha, "alpha") < 1:
            raise ValueError("Signed model band requires 0 < alpha < 1")

    def as_record(self):
        return {"value": self.value, "lower": self.lower, "upper": self.upper,
                "status_code": self.status_code,
                "uncertainty_code": self.uncertainty_code, "alpha": self.alpha}


def _parameters(value=None):
    if value is None:
        return YieldParameters()
    if isinstance(value, YieldParameters):
        return value
    if isinstance(value, Mapping):
        keys = {"window_size", "subsample_size", "uncertainty_alpha"}
        unknown = set(value) - keys - {"window_semantics", "subsample_semantics"}
        if unknown:
            raise ValueError(f"Unknown yield settings: {sorted(unknown)}")
        return YieldParameters(**{key: value[key] for key in keys if key in value})
    raise TypeError("settings must be YieldParameters or their record")


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
    component_parameters = YieldParameters(parameters.window_size,
        parameters.subsample_size, parameters.uncertainty_alpha / 2.0)
    contexts = None if contexts is None else tuple(contexts)
    gain = estimate_nonnegative_yield(gains, component_parameters, contexts=contexts, evaluation_time=evaluation_time)
    loss = estimate_nonnegative_yield(losses, component_parameters, contexts=contexts, evaluation_time=evaluation_time)
    diagnostics = {"completed_acquisition_turns": len(history),
                   "history_used": len(history), "fitting_scope": "full_history",
                   "initialization": "cold_template_prior",
                   "signed_model": "paired_gain_loss_marks_same_real_time_v2",
                   "negative_action_count": sum(value < 0 for value in history),
                   "gain_component": gain.as_record(),
                   "loss_component": loss.as_record(),
                   "interval_method": "bonferroni_allocated_model_band_subtraction",
                   "coverage_calibrated": False}
    if "unavailable_reason" in gain.diagnostics:
        diagnostics["unavailable_reason"] = gain.diagnostics["unavailable_reason"]
    statuses = {gain.expected_next_gain.status_code, loss.expected_next_gain.status_code}
    if statuses != {STATUS_NORMAL}:
        status = (STATUS_UNIDENTIFIABLE if STATUS_UNIDENTIFIABLE in statuses
                  else STATUS_INSUFFICIENT)
        band = NumericBand.coded(status)
    else:
        g, l = gain.expected_next_gain, loss.expected_next_gain
        band = SignedNumericBand(g.value-l.value, g.lower-l.upper,
                                 g.upper-l.lower, alpha=parameters.uncertainty_alpha)
    return YieldEstimate(len(history), band, parameters, diagnostics)


def estimate_bounded_credit_yield(scores: Sequence[Real], parameters=None, *, contexts=None,
                                  initial_credit, maximum_credit):
    """Forecast one more bounded native-score improvement from actual actions.

    The existing signed real-time fit supplies the working forecast. The
    native score's proven range restricts possible additional credit. A
    correction remains an actual signed observation; it can reopen headroom.
    Unknown model status stays unknown until the native maximum is attained.
    """
    parameters = _parameters(parameters)
    initial = _score(initial_credit, 'initial bounded credit')
    maximum = _score(maximum_credit, 'maximum bounded credit')
    if maximum <= 0 or initial > maximum:
        raise ValueError('bounded_credit_range_invalid')
    history = tuple(_signed(value) for value in scores)
    current = math.fsum((initial, *history))
    if not 0 <= current <= maximum:
        raise ValueError('bounded_credit_history_outside_native_range')
    base = estimate_score_yield(history, parameters, contexts=contexts)
    headroom = maximum - current
    band = base.expected_next_gain
    if headroom == 0:
        bounded = NumericBand.exact(0)
    elif band.status_code != STATUS_NORMAL:
        bounded = band
    elif isinstance(band, SignedNumericBand):
        lower = max(-current, min(band.lower, headroom))
        upper = max(lower, min(headroom, max(-current, band.upper)))
        bounded = SignedNumericBand(min(upper, max(lower, band.value)), lower, upper,
            uncertainty_code=band.uncertainty_code, alpha=band.alpha)
    else:
        upper = min(headroom, band.upper)
        lower = min(upper, band.lower)
        bounded = NumericBand(min(upper, max(lower, band.value)), lower, upper,
            band.status_code, band.uncertainty_code, band.alpha)
    return replace(base, expected_next_gain=bounded,
        diagnostics={**base.diagnostics, 'native_score_minimum': 0.,
            'native_score_maximum': maximum, 'current_native_credit': current,
            'remaining_positive_credit': headroom,
            'forecast_constraint': 'native_score_range_after_same_action_history'},
        estimator_binding={'kind': 'bounded_native_credit_yield_v1',
            'base_estimator': ESTIMATOR_VERSION,
            'native_score_minimum': 0., 'native_score_maximum': maximum,
            'forecast': 'next_marginal_credit_bounded_by_current_headroom',
            'uncertainty': 'base_working_model_uncalibrated'} )


class ScalarScoreYieldEstimator:
    """One history entry for each completed action; corrections remain signed."""

    def __init__(self, parameters=None, *, estimate_with_context=None):
        self.parameters = _parameters(parameters)
        if estimate_with_context is not None and not callable(estimate_with_context):
            raise TypeError("contextual_estimator_must_be_callable")
        self.estimate_with_context = estimate_with_context
        self._scores = []
        self._contexts = []
        self._current = self._estimate((), ())

    def _estimate(self, history, contexts):
        if self.estimate_with_context is None:
            return estimate_score_yield(history, self.parameters, contexts=contexts)
        # Timing/snapshot history is paired with these SAME completed actions.
        # No previous prediction or another child's yield history is supplied.
        result = self.estimate_with_context(tuple(history), self.parameters, tuple(contexts))
        if result is None and getattr(self.estimate_with_context, 'uses_template_when_unbound', False):
            # The default real-time binding retains missing timing explicitly;
            # custom bindings do not silently fall back to action-rank fits.
            return estimate_score_yield(history, self.parameters, contexts=contexts)
        if not isinstance(result, YieldEstimate) or result.turns != len(history):
            raise TypeError("contextual_estimator_must_return_same_action_history_estimate")
        if result.estimator_binding is None:
            callback = self.estimate_with_context
            declared = callback if hasattr(callback, "__qualname__") else type(callback)
            result = replace(result, estimator_binding={"kind": "caller_injected",
                "function": f"{declared.__module__}.{declared.__qualname__}",
                "interface": "raw_credit_history_parameters_aligned_execution_contexts_v1",
                "template_relationship": "not_inferred"})
        return result

    @property
    def scores(self):
        return tuple(self._scores)

    @property
    def contexts(self):
        return tuple(self._contexts)

    def observe(self, marginal_credit, *, context=None):
        value = _signed(marginal_credit)
        history = self._scores + [value]
        contexts = self._contexts + [context]
        current = self._estimate(history, contexts)
        self._scores = history
        self._contexts = contexts
        self._current = current
        return current

    def state(self):
        return self._current


class BoundedScoreYieldEstimator:
    """Fit the actual signed actions within one native score's proven range."""

    def __init__(self, initial_credit, maximum_credit, parameters=None):
        self.parameters = _parameters(parameters)
        self.initial_credit = _score(initial_credit, 'initial bounded credit')
        self.maximum_credit = _score(maximum_credit, 'maximum bounded credit')
        if self.maximum_credit <= 0 or self.initial_credit > self.maximum_credit:
            raise ValueError('bounded_credit_range_invalid')
        self._scores = []
        self._contexts = []
        self._current = estimate_bounded_credit_yield((), self.parameters,
            initial_credit=self.initial_credit, maximum_credit=self.maximum_credit)

    @property
    def scores(self):
        return tuple(self._scores)

    def observe(self, marginal_credit, *, context=None):
        history = [*self._scores, _signed(marginal_credit)]
        contexts = [*self._contexts, context]
        current = estimate_bounded_credit_yield(history, self.parameters, contexts=contexts,
            initial_credit=self.initial_credit, maximum_credit=self.maximum_credit)
        self._scores, self._contexts, self._current = history, contexts, current
        return current

    def state(self):
        return self._current


class CompletionCreditYieldEstimator:
    """Forecast observed yield until a fixed artifact is delivered."""

    def __init__(self, initial_credit, parameters=None):
        self.parameters = _parameters(parameters)
        self.initial_credit = _score(initial_credit, 'initial completion credit')
        if self.initial_credit not in (0., 1.):
            raise ValueError('completion_credit_requires_binary_artifact')
        self._scores = []
        self._contexts = []
        self._current = self._estimate()

    @property
    def scores(self):
        return tuple(self._scores)

    def _estimate(self):
        current = math.fsum((self.initial_credit, *self._scores))
        if current not in (0., 1.):
            raise ValueError('completion_credit_requires_binary_artifact')
        estimate = estimate_bounded_credit_yield(self._scores, self.parameters,
            contexts=self._contexts, initial_credit=self.initial_credit, maximum_credit=1.)
        return replace(estimate, diagnostics={**estimate.diagnostics,
            'current_credit': current, 'remaining_deliverable_credit': 1. - current,
            'forecast_quantity': 'observed_yield_until_fixed_artifact_delivered'},
            estimator_binding={'kind': 'binary_artifact_completion_yield_v1',
                'unit': 'one_authenticated_delivered_artifact',
                'before_delivery': 'bounded_observed_action_yield',
                'after_delivery': 'exact_zero_remaining_credit'})

    def observe(self, marginal_credit, *, context=None):
        self._scores.append(_signed(marginal_credit))
        self._contexts.append(context)
        self._current = self._estimate()
        return self._current

    def state(self):
        return self._current


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
    """The complete continuation rule, applied unchanged at every episode level."""
    if not isinstance(projected_gain, (NumericBand, SignedNumericBand)):
        raise TypeError("Continuation consumes a numeric band")
    cost = _score(continuation_cost, "continuation cost")
    return ContinuationDecision(
        projected_gain.status_code == STATUS_NORMAL and projected_gain.upper <= cost,
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
                "marginal_credit": self.marginal_credit,
                "estimate": self.estimate.as_record(),
                "decision": self.decision.as_record(), "stop": self.stop,
                "is_root": self.is_root,
                "requests_transition": self.requests_transition}


@dataclass(frozen=True)
class YieldState:
    epoch: str
    initial_credit: float
    current_credit: float
    history: tuple
    estimate: YieldEstimate
    decision: ContinuationDecision

    def as_record(self):
        return {"epoch": self.epoch, "initial_credit": self.initial_credit,
                "current_credit": self.current_credit, "scores": list(self.history),
                "estimate": self.estimate.as_record(),
                "decision": self.decision.as_record()}


class YieldController:
    """Opaque-score method_loop controller. Runtime owns action completion."""

    def __init__(self, epoch, initial_credit, cost, settings=None, *, estimate_with_context=None):
        if not isinstance(epoch, str) or not epoch.strip():
            raise ValueError("epoch must be a nonempty string")
        self.epoch = epoch
        self.initial_credit = _signed(initial_credit, "initial_credit")
        self._current_credit = self.initial_credit
        self.cost = _score(cost, "continuation cost")
        self.settings = _parameters(settings)
        self.estimator = ScalarScoreYieldEstimator(self.settings, estimate_with_context=estimate_with_context)

    def observe(self, unit_label, value, is_root=False):
        context = None
        if hasattr(value, "as_record"):
            value = value.as_record()
        if isinstance(value, Mapping):
            if "credit" not in value:
                raise ValueError("Completed record must include cumulative credit")
            context = value.get("estimation_context")
            value = value["credit"]
        cumulative = _signed(value, "cumulative credit")
        delta = cumulative - self._current_credit
        estimate = self.estimator.observe(delta, context=context)
        self._current_credit = cumulative
        return YieldStep(str(unit_label), cumulative, delta, estimate,
                         predicted_gain_upper_bound(estimate.expected_next_gain, self.cost),
                         bool(is_root))

    def state(self):
        estimate = self.estimator.state()
        return YieldState(self.epoch, self.initial_credit, self._current_credit,
            self.estimator.scores, estimate,
            predicted_gain_upper_bound(estimate.expected_next_gain, self.cost))

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError("An explicit new epoch must have a distinct id")
        return type(self)(epoch, self._current_credit, self.cost, self.settings,
                          estimate_with_context=self.estimator.estimate_with_context)


class BoundedYieldController(YieldController):
    """Apply one task's cutoff to its bounded native-credit forecast."""

    def __init__(self, epoch, initial_credit, cost, maximum_credit, settings=None):
        super().__init__(epoch, initial_credit, cost, settings)
        self.maximum_credit = _score(maximum_credit, 'maximum bounded credit')
        self.estimator = BoundedScoreYieldEstimator(initial_credit, self.maximum_credit,
            self.settings)

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError('An explicit new epoch must have a distinct id')
        return type(self)(epoch, self._current_credit, self.cost, self.maximum_credit,
            self.settings)


class CompletionYieldController(YieldController):
    """Continue until the commissioned artifact is delivered or its credit is revised."""

    def __init__(self, epoch, initial_credit, cost, settings=None):
        super().__init__(epoch, initial_credit, cost, settings)
        if self.cost >= 1.:
            raise ValueError('completion_cutoff_must_be_below_artifact_credit')
        self.estimator = CompletionCreditYieldEstimator(initial_credit, self.settings)

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError('An explicit new epoch must have a distinct id')
        return type(self)(epoch, self._current_credit, self.cost, self.settings)


def annotation_arm_key(arm):
    """The original proposed annotation, native subject, scope and axis."""
    fields = ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')
    if (not isinstance(arm, Mapping) or not all(name in arm for name in fields)
            or any(not isinstance(arm[name], str) or not arm[name]
                   for name in ('proposed_annotation_ref', 'subject_ref', 'axis'))
            or not isinstance(arm['scope'], Mapping)):
        raise ValueError('annotation_axis_identity_required')
    return json.dumps({name: arm[name] for name in fields}, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def validate_task_credit(value):
    """Validate a scalar or the root's received annotation/axis credit."""
    if not isinstance(value, Mapping):
        return _signed(value, 'task credit')
    fields = set(value)
    if (fields not in ({'mode', 'arms'},
                       {'mode', 'arms', 'annotation_credits', 'root_score'})
            or value['mode'] != 'annotation_axis_credit'):
        raise ValueError('task_credit_collection_required')
    if not isinstance(value['arms'], list):
        raise ValueError('task_credit_arms_required')
    keys = set()
    for arm in value['arms']:
        key = annotation_arm_key(arm)
        if key in keys:
            raise ValueError('duplicate_annotation_axis_credit')
        keys.add(key)
        if arm['credit'] is not None:
            _signed(arm['credit'], 'annotation axis credit')
        if not isinstance(arm.get('status'), str) or not isinstance(arm.get('transfer'), Mapping):
            raise ValueError('annotation_axis_status_required')
    if 'root_score' in value:
        annotations, score = annotation_credit_summary(value['arms'])
        if (value['annotation_credits'] != annotations
                or _signed(value['root_score'], 'root task credit') != score):
            raise ValueError('root_credit_must_match_received_annotation_credits')
    return deepcopy(value)


def annotation_credit_summary(arms):
    """Sum axis-owner received progress for each annotation, then take the best total.

    This is root task progress. It does not read or combine functional-support
    scores, and the controller still estimates the next invocation per arm.
    """
    by_annotation = {}
    for arm in arms:
        by_annotation.setdefault(arm['proposed_annotation_ref'], []).append(
            0. if arm['credit'] is None else _signed(arm['credit'], 'annotation axis credit'))
    annotations = [{'proposed_annotation_ref': reference, 'credit': math.fsum(values)}
        for reference, values in sorted(by_annotation.items())]
    return annotations, max((row['credit'] for row in annotations), default=0.)


@dataclass(frozen=True)
class AnnotationAxisYieldState:
    epoch: str
    initial_credit: dict
    current_credit: dict
    arms: tuple
    annotation_credits: tuple
    root_score: float
    stop: bool

    def as_record(self):
        return {'epoch': self.epoch, 'initial_credit': self.initial_credit,
            'current_credit': self.current_credit, 'arms': list(self.arms),
            'annotation_credits': list(self.annotation_credits), 'root_score': self.root_score,
            'decision': {'stop': self.stop,
                'decision_basis': 'every_annotation_axis_available_upper_bound_lte_own_cutoff'}}


@dataclass(frozen=True)
class AnnotationAxisYieldStep:
    unit_label: str
    credit: dict
    completed_arm: dict | None
    marginal_credit: float | None
    state: AnnotationAxisYieldState
    is_root: bool = False
    requests_transition: bool = False

    @property
    def stop(self):
        return self.state.stop

    def as_record(self):
        return {'unit_label': self.unit_label, 'credit': self.credit,
            'completed_arm': self.completed_arm, 'marginal_credit': self.marginal_credit,
            'decision': self.state.as_record()['decision'], 'arms': list(self.state.arms),
            'stop': self.stop, 'is_root': self.is_root,
            'requests_transition': self.requests_transition}


class AnnotationAxisYieldController:
    """One independent yield estimate per assigned annotation/axis pair.

    Only an actual returned axis invocation supplies an observation. Other
    completed root actions can change received credit or resolve a transfer,
    but are not extra axis attempts. Unknown credit and forecasts remain unknown.
    """

    def __init__(self, epoch, initial_credit, cutoffs, settings=None):
        if not isinstance(epoch, str) or not epoch:
            raise ValueError('epoch_required')
        if not isinstance(cutoffs, Mapping) or not cutoffs:
            raise ValueError('explicit_annotation_axis_cutoffs_required')
        self.epoch = epoch
        self.cutoffs = {axis: _score(value, 'axis cutoff') for axis, value in cutoffs.items()}
        self.settings = _parameters(settings)
        self.initial_credit = validate_task_credit(initial_credit)
        if not isinstance(self.initial_credit, dict):
            raise ValueError('annotation_axis_credit_required')
        self._current_credit = deepcopy(self.initial_credit)
        self._estimators = {}
        self._sync(self._current_credit)

    def _sync(self, credit):
        previous = {annotation_arm_key(arm): arm for arm in self._current_credit['arms']}
        for arm in credit['arms']:
            key = annotation_arm_key(arm)
            if arm['axis'] not in self.cutoffs:
                raise ValueError('explicit_cutoff_missing_for_axis:' + arm['axis'])
            old = previous.get(key)
            # A changed dependency creates a different opportunity. Earlier
            # blocked attempts cannot declare that new opportunity exhausted.
            dependency = lambda item: (item['transfer'].get('status'),
                item['transfer'].get('needed_refs', []))
            if (key not in self._estimators or old is not None
                    and dependency(old) != dependency(arm)):
                self._estimators[key] = ScalarScoreYieldEstimator(self.settings)

    def observe(self, unit_label, value, is_root=False):
        body = value.as_record() if hasattr(value, 'as_record') else value
        credit = validate_task_credit(body['credit'])
        context = body.get('estimation_context') or {}
        completed = context.get('completed_annotation_axis')
        previous = {annotation_arm_key(arm): arm for arm in self._current_credit['arms']}
        self._sync(credit)
        delta = None
        if completed is not None:
            key = annotation_arm_key(completed)
            after = next((arm for arm in credit['arms'] if annotation_arm_key(arm) == key), None)
            before = previous.get(key)
            if after is None:
                raise ValueError('completed_annotation_axis_not_received')
            # Missing scientific support earns no contribution. An actual
            # completed invocation with no additional credited contribution is
            # therefore a zero gain, while its scientific value remains None.
            # This is not a fabricated zero measurement or an opposing datum.
            prior_credit = 0. if before is None or before['credit'] is None else before['credit']
            current_credit = 0. if after['credit'] is None else after['credit']
            delta = current_credit - prior_credit
            self._estimators[key].observe(delta, context=context)
        self._current_credit = credit
        return AnnotationAxisYieldStep(str(unit_label), deepcopy(credit),
            deepcopy(completed), delta, self.state(), bool(is_root))

    def state(self):
        arms = []
        for arm in self._current_credit['arms']:
            estimate = self._estimators[annotation_arm_key(arm)].state()
            band = estimate.expected_next_gain
            decision = predicted_gain_upper_bound(band, self.cutoffs[arm['axis']])
            arms.append({**deepcopy(arm), 'expected_additional_credit': band.as_record(),
                'completed_invocation_observations': estimate.turns,
                'cutoff': self.cutoffs[arm['axis']],
                'stop_requested': decision.stop,
                'forecast_unit': 'another_whole_axis_invocation'})
        annotation_credits, root_score = annotation_credit_summary(self._current_credit['arms'])
        return AnnotationAxisYieldState(self.epoch, deepcopy(self.initial_credit),
            deepcopy(self._current_credit), tuple(arms), tuple(annotation_credits), root_score,
            bool(arms) and all(arm['stop_requested'] for arm in arms))

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError('new_epoch_required')
        return type(self)(epoch, self._current_credit, self.cutoffs, self.settings)
