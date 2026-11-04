"""Template-derived yield estimation and a plain continuation controller.

The exact nano-graphrag source is vendored with its MIT license and SHA-256.
The completed real-score quasi-likelihood adapter comes from the supplied
orbital template. Its nonnegative path is unchanged numerically. Signed
corrections use estimator-owned paired gain/loss marks on the SAME action ranks:
positive=max(delta,0), loss=max(-delta,0). No raw observation is replaced,
removed, smoothed, or appended twice. Each mark fits the full observed history.

Gain/loss model bands use Bonferroni alpha/2 and interval subtraction. This is
an approximate, uncalibrated working-model interval; Bonferroni allocation does
not make the source Laplace approximation coverage calibrated. Before any loss
has been observed, the original nonnegative template path is used exactly.
The no-loss working model assumes zero loss until a correction is observed.
After a loss, both marked fits are retained for every later full-history fit.

The controller receives one cumulative score per completed local action and
passes its raw signed difference to the estimator. Its only numerical stop rule
is available upper bound <= configured cost. It has no memory, smoothing,
consecutive-zero rule, action cap, source-completion test, or scientific gate.
"""

from dataclasses import dataclass, replace
import math
from numbers import Real
from typing import Mapping, Sequence

from .vendor import nano_rarefaction as template


NumericBand = template.NumericBand
STATUS_NORMAL = template.STATUS_NORMAL
STATUS_INSUFFICIENT = template.STATUS_INSUFFICIENT
STATUS_UNIDENTIFIABLE = template.STATUS_UNIDENTIFIABLE

SOURCE_SHA256 = "02af19652d69f368ee8875d3b27cad0bb2bbc8d1f8274344b72a4437092cdd35"
SOURCE_REVISION = "60a167f9eeda0c9ea2ca294724174948947baf3f"
ESTIMATOR_VERSION = "completed_signed_score_preferential_yield_v1"


def _score(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite non-negative real number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative real number")
    return number


@dataclass(frozen=True)
class YieldParameters:
    # These preserve the actual template's availability semantics. They are
    # minimum information for a fit, not a rolling mean or an episode cap.
    window_size: int = template.DEFAULT_WINDOW_SIZE
    subsample_size: int = template.DEFAULT_SUBSAMPLE_SIZE
    uncertainty_alpha: float = template.DEFAULT_ALPHA

    def __post_init__(self):
        template._IncidenceEstimator.validate_parameters(
            self.window_size, self.subsample_size, self.uncertainty_alpha)

    def as_record(self):
        return {
            "window_size": self.window_size,
            "subsample_size": self.subsample_size,
            "uncertainty_alpha": self.uncertainty_alpha,
            "window_semantics": "minimum_completed_acquisition_turns_before_full_history_fit",
            "subsample_semantics": "minimum_evaluated_acquisition_turns_before_full_history_fit",
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
        "per_episode_units": {
            "direct_tool": "One completed selected acquisition supplies one local observation",
            "reasoning": "One completed scientific interpretation action supplies one local observation, including when it uses existing evidence",
            "read_or_comparison": "A completed acquisition can have zero marginal credit",
            "shared_refresh": "Shared credit refreshes do not add action observations",
            "failed_or_unexecuted_request": "Public invalid requests and failed or unexecuted tool attempts create no acquisition or estimator observation",
            "root": "One root-selected completed reasoning action, tool or child investigation supplies one root action; nested child operations add no ancestor observations",
        },
        "adaptations": [
            "Real marginal credit responses pass into the fit without integer coercion",
            "Completed Episode acquisitions condition on observation; no failure/usability model",
            "A fresh original fitter cold-fits the entire score history each turn",
            "Original numeric bands and delta/Laplace curvature approximation are retained",
            "Signed corrections use paired gain/loss marks at the same action ranks inside the estimator",
            "After an observed loss, component alpha/2 bands subtract to an approximate signed net interval",
        ],
        "statistical_model": "latent_lognormal_fractional_poisson_working_quasi_likelihood",
        "uncertainty": "approximate_model_dependent_curvature_laplace_band",
        "calibrated_confidence_interval": False,
        "limitations": [
            "The fractional kernel is not a continuous-response probability density",
            "Uncertainty assumes the working model and is not coverage calibrated",
            "Credit units affect effective information and must remain fixed within an Episode",
            "Rank-decay extrapolation assumes declining yield; late discoveries can violate it",
            "No failed-attempt probability is estimated from completed-only acquisitions",
            "The inherited local optimizer has no global optimum or convergence certificate; bands can jump across history lengths",
            "Before any observed loss the original nonnegative model assumes zero loss; this is an explicit working-model assumption",
            "Gain/loss interval subtraction is not coverage calibrated; Bonferroni allocation cannot calibrate the underlying Laplace approximation",
        ],
    }


class _RealScoreFit(template._IncidenceEstimator):
    """Reuse the original fitter, with the two input/model changes above."""

    @staticmethod
    def _observation_loss(parameters, rank, status, discovery):
        if status != template.OBSERVATION_OBSERVED:
            raise ValueError("Only completed Episode acquisition turns enter this estimator")
        beta, log_delta, _observation_intercept, _coupling = parameters
        delta = math.exp(float(log_delta))
        # The gamma term is constant with respect to parameters. It retains
        # the original kernel's numerical offset; it is not a density claim.
        terms = tuple(
            weight + discovery * potential
            - math.exp(max(-50.0, min(50.0, potential)))
            - math.lgamma(discovery + 1.0)
            for weight, potential in (
                (weight, beta - delta * (rank - 1) + latent)
                for weight, latent in zip(
                    template._LOG_QUADRATURE_WEIGHTS, template._QUADRATURE_LATENT)
            )
        )
        return -template._logsumexp(terms)

    @classmethod
    def _history_loss(cls, parameters, statuses, discoveries):
        # Deliberately no int(discovery), identity conversion or smoothing.
        return cls._prior_loss(parameters) + sum(
            cls._observation_loss(parameters, rank, status, discovery)
            for rank, (status, discovery) in enumerate(zip(statuses, discoveries), 1)
        )

    @staticmethod
    def _metric_discovery(parameters, rank):
        beta, log_delta, _observation_intercept, _coupling = parameters
        delta = math.exp(float(log_delta))
        return sum(
            math.exp(weight) * math.exp(max(-50.0, min(50.0,
                beta - delta * (rank - 1.0) + latent)))
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


def estimate_nonnegative_yield(scores: Sequence[Real], parameters: YieldParameters | None = None):
    """Pure current-history estimate; previous predictions are never an input."""
    parameters = YieldParameters() if parameters is None else parameters
    if not isinstance(parameters, YieldParameters):
        raise TypeError("parameters must be YieldParameters")
    history = tuple(_score(value, "marginal credit") for value in scores)
    turns = len(history)
    diagnostics = {"completed_acquisition_turns": turns, "history_used": turns,
                   "fitting_scope": "full_history", "initialization": "cold_template_prior"}
    if turns < parameters.window_size or turns < parameters.subsample_size:
        return YieldEstimate(turns, NumericBand.coded(STATUS_INSUFFICIENT), parameters, diagnostics)

    # Never reuse last turn's prediction or fit state. The history alone
    # determines this turn's fit, including the original fixed yield priors.
    fit = _RealScoreFit(window_size=parameters.window_size,
                        subsample_size=parameters.subsample_size,
                        alpha=parameters.uncertainty_alpha)
    statuses = (template.OBSERVATION_OBSERVED,) * turns
    try:
        fitted, covariance, objective = fit._fit_full_history(
            statuses, history, coupling_identifiable=False)
        if not all(math.isfinite(value) for row in covariance for value in row):
            raise ArithmeticError("Non-finite fitted covariance")
        next_rank = turns + 1
        point = fit._metric_discovery(fitted, next_rank)
        variance = fit._metric_variance(fitted, covariance,
            lambda values: fit._metric_discovery(values, next_rank))
        band = NumericBand.laplace(point, variance, parameters.uncertainty_alpha)
        diagnostics.update({"yield_intercept": fitted[0],
            "rank_decay": math.exp(fitted[1]), "fit_objective": objective,
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


def estimate_score_yield(scores: Sequence[Real], parameters=None):
    """Fit raw signed action history; marks are internal estimator operands."""
    parameters = _parameters(parameters)
    history = tuple(_signed(value) for value in scores)
    if not any(value < 0 for value in history):
        return estimate_nonnegative_yield(history, parameters)

    # Every mark has one element for every actual action. Zeros below mean an
    # observed action's other sign, never an invented failure/action observation.
    gains = tuple(max(value, 0.0) for value in history)
    losses = tuple(max(-value, 0.0) for value in history)
    component_parameters = YieldParameters(parameters.window_size,
        parameters.subsample_size, parameters.uncertainty_alpha / 2.0)
    gain = estimate_nonnegative_yield(gains, component_parameters)
    loss = estimate_nonnegative_yield(losses, component_parameters)
    diagnostics = {"completed_acquisition_turns": len(history),
                   "history_used": len(history), "fitting_scope": "full_history",
                   "initialization": "cold_template_prior",
                   "signed_model": "paired_gain_loss_marks_same_action_rank_v1",
                   "negative_action_count": sum(value < 0 for value in history),
                   "gain_component": gain.as_record(),
                   "loss_component": loss.as_record(),
                   "interval_method": "bonferroni_allocated_model_band_subtraction",
                   "coverage_calibrated": False}
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
            # The existing template has no time model. Merely receiving timing
            # context does not authorize an invented score/time conversion.
            return estimate_score_yield(history, self.parameters)
        # Timing/snapshot history is paired with these SAME completed actions.
        # No previous prediction or another child's yield history is supplied.
        result = self.estimate_with_context(tuple(history), self.parameters, tuple(contexts))
        if result is None and getattr(self.estimate_with_context, 'uses_template_when_unbound', False):
            # An opt-in binding can leave historical actions without its
            # operands exactly on the original estimator and provenance.
            return estimate_score_yield(history, self.parameters)
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
