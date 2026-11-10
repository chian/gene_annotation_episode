"""Small, serial probabilistic calculations for HPC episode decisions.

The caller supplies priors and the scientific value of work. These functions
make no decisions, launch no work, and award no credit. Time models are Bayesian
linear regressions of log(1 + seconds), with measurement noise and parameter
uncertainty. Right-censored observations update by truncated-normal moments;
they are never passed off as completed durations.
"""
from __future__ import annotations

from copy import deepcopy
import math
from statistics import NormalDist

from .hpc_queue import digest
from .hpc_resource_prediction import (RESOURCE_UNITS, measured_value, forecast_metric,
                                      resource_summary, physical_attempt_key)


METRICS = ('queue', 'setup', 'work', 'return')
NORMAL = NormalDist()


def log_survival(z):
    if z < 8:
        return math.log(max(.5*math.erfc(z/math.sqrt(2)), 1e-300))
    # Mills' expansion avoids underflow when conditioning on a very long wait.
    inverse = 1/(z*z)
    return -.5*z*z-math.log(z)-.5*math.log(2*math.pi)+math.log(1-inverse+3*inverse**2)


def distribution(mu, sigma, *, elapsed=0):
    if not all(math.isfinite(x) for x in (mu, sigma, elapsed)) or sigma <= 0 or elapsed < 0:
        raise ValueError('invalid_time_distribution')
    return {'mu': mu, 'sigma': sigma, 'elapsed': elapsed}


def log_score(value, observed, *, censored=False):
    """Proper log density/survival score for *remaining* seconds at issue time."""
    if not math.isfinite(observed) or observed < 0:
        raise ValueError('nonnegative_observed_duration_required')
    mu, sigma, elapsed = (value[key] for key in ('mu', 'sigma', 'elapsed'))
    z0 = (math.log1p(elapsed)-mu)/sigma
    z = (math.log1p(elapsed+observed)-mu)/sigma
    normalizer = log_survival(z0)
    if censored:
        return log_survival(z)-normalizer
    return -.5*z*z-math.log(sigma)-.5*math.log(2*math.pi)-math.log1p(elapsed+observed)-normalizer


def probability_within(value, seconds):
    if seconds <= 0:
        return 0.0
    return max(0.0, min(1.0, -math.expm1(log_score(value, seconds, censored=True))))


def quantile(value, probability=.5):
    # Bisection of conditional survival also works in far censored tails.
    target = math.log1p(-probability)
    lo, hi = 0., 1.
    while log_score(value, hi, censored=True) > target and hi < 1e12:
        hi *= 2
    for _ in range(64):
        middle = (lo+hi)/2
        if log_score(value, middle, censored=True) > target:
            lo = middle
        else:
            hi = middle
    return (lo+hi)/2


def summary(value):
    return {'p10_seconds': quantile(value, .1), 'p50_seconds': quantile(value, .5),
            'p90_seconds': quantile(value, .9)}


def vector(features, specification):
    result = [1.]
    for field in specification:
        value = features.get(field['name'])
        missing = value is None
        if not missing:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError('finite_feature_required:'+field['name'])
            if field['transform'] == 'log1p':
                value = math.log1p(max(0., value))
            elif field['transform'] != 'identity':
                raise ValueError('unknown_feature_transform')
            value = (value-field.get('center', 0))/field['scale']
        result.extend((0. if missing else value, float(missing)))
    return result


def prior_model(specification):
    if not 0 < len(specification['features']) <= 24:
        raise ValueError('one_to_24_features_required')
    if any(field['scale'] <= 0 for field in specification['features']):
        raise ValueError('positive_feature_scales_required')
    dimension = 1+2*len(specification['features'])
    result = {'version': 'hpc_time_model_v1', 'specification': deepcopy(specification),
              'training_ids': [], 'metrics': {}, 'successes': 0, 'failures': 0, 'ranges': {}}
    resources = specification.get('resource_priors', {})
    if set(resources)-set(RESOURCE_UNITS):
        raise ValueError('unsupported_resource_prediction_metric')
    for metric in (*METRICS, *resources):
        prior = (resources if metric in resources else specification['priors'])[metric]
        median = prior['median'] if metric in resources else prior['median_seconds']
        if metric in resources and prior.get('unit') != RESOURCE_UNITS[metric]:
            raise ValueError('explicit_resource_prior_unit_required')
        if (not all(math.isfinite(v) for v in (median, prior['log_sigma'], prior['coefficient_variance']))
                or median < 0 or prior['log_sigma'] <= 0 or prior['coefficient_variance'] <= 0):
            raise ValueError('explicit_positive_time_prior_required')
        result['metrics'][metric] = {'mean': [math.log1p(median)]+[0.]*(dimension-1),
            'covariance': [[prior['coefficient_variance'] if i == j else 0.
                            for j in range(dimension)] for i in range(dimension)],
            'noise_variance': prior['log_sigma']**2, 'observations': 0, 'censored': 0}
    alpha, beta = specification['success_prior']
    if alpha <= 0 or beta <= 0:
        raise ValueError('positive_success_beta_prior_required')
    return result


def _moments(state, x):
    cx = [sum(v*t for v, t in zip(row, x)) for row in state['covariance']]
    return sum(a*b for a, b in zip(state['mean'], x)), state['noise_variance']+sum(a*b for a, b in zip(x, cx)), cx


def fit(specification, observations):
    if len(observations) > 2000:
        raise ValueError('select_at_most_2000_historical_observations')
    model = prior_model(specification)
    attempts = set()
    for observation in sorted(observations, key=lambda item: (item['observed_at'], item['id'])):
        if observation['id'] in model['training_ids'] or not observation.get('provenance'):
            raise ValueError('unique_measured_history_with_provenance_required')
        attempt = physical_attempt_key(observation)
        if attempt is not None:
            if attempt in attempts:
                raise ValueError('one_training_case_per_physical_attempt_required')
            attempts.add(attempt)
        model['training_ids'].append(observation['id'])
        weight = observation.get('weight', 1.)
        if type(weight) not in (int, float) or not 0 < weight <= 1:
            raise ValueError('historical_weight_must_be_between_zero_and_one')
        x = vector(observation['features'], specification['features'])
        for name, item in observation['metrics'].items():
            if name not in (*METRICS, *RESOURCE_UNITS):
                raise ValueError('unknown_time_metric')
            value = measured_value(name, item)
            if name not in model['metrics']:
                continue  # Older timing-only models make no resource forecast.
            y = math.log1p(value)
            state = model['metrics'][name]
            mean, variance, cx = _moments(state, x)
            metric_weight = item.get('weight', weight)
            if type(metric_weight) not in (int, float) or not 0 < metric_weight <= 1:
                raise ValueError('historical_weight_must_be_between_zero_and_one')
            # Aged measurements contribute fractional precision. Censored
            # observations still use the survival likelihood, never a fake end.
            variance += state['noise_variance'] * (1/metric_weight - 1)
            sigma = math.sqrt(variance)
            if item.get('censored', False):
                z = (y-mean)/sigma
                mills = math.exp(-z*z/2-.5*math.log(2*math.pi)-log_survival(z))
                residual = sigma*mills
                shrink = max(0., min(1., mills*(mills-z)))
                state['censored'] += 1
            else:
                residual, shrink = y-mean, 1.
            for i in range(len(x)):
                state['mean'][i] += cx[i]/variance*residual
                for j in range(len(x)):
                    state['covariance'][i][j] -= shrink*cx[i]*cx[j]/variance
            state['observations'] += 1
        if observation.get('success') is not None:
            model['successes' if observation['success'] else 'failures'] += weight
        for name, value in observation['features'].items():
            if type(value) in (int, float) and math.isfinite(value):
                old = model['ranges'].get(name, [value, value])
                model['ranges'][name] = [min(value, old[0]), max(value, old[1])]
    return model


def predict(model, features):
    x = vector(features, model['specification']['features'])
    times, resources = {}, {}
    for metric, state in model['metrics'].items():
        mean, variance, _ = _moments(state, x)
        (resources if metric in RESOURCE_UNITS else times)[metric] = distribution(
            mean, math.sqrt(max(variance, 1e-9)))
    alpha, beta = model['specification']['success_prior']
    alpha, beta = alpha+model['successes'], beta+model['failures']
    extrapolated = [name for name, limits in model['ranges'].items()
        if features.get(name) is not None and not limits[0] <= features[name] <= limits[1]]
    return {'model_sha256': digest(model), 'features': deepcopy(features), 'times': times,
        **({'resources': resources} if resources else {}),
        'success_probability': alpha/(alpha+beta),
        'support': {'observations': len(model['training_ids']), 'extrapolated_features': extrapolated,
                    'prior_only': not model['training_ids'],
                    'metric_observations': {name: state['observations'] for name, state in model['metrics'].items()}}}


def quality(model, held_out):
    """Mean proper score on fixed, disjoint measured cases, including failures."""
    if not held_out:
        raise ValueError('nonempty_fixed_validation_cases_required')
    scores = []
    for case in held_out:
        if case['id'] in model['training_ids']:
            raise ValueError('training_validation_overlap')
        forecast = predict(model, case['features'])
        terms = [log_score(selected, measured_value(metric, item), censored=item.get('censored', False))
                 for metric, item in case['metrics'].items()
                 if (selected := forecast_metric(forecast, metric)) is not None]
        if case.get('success') is not None:
            p = forecast['success_probability']
            terms.append(math.log(p if case['success'] else 1-p))
        if terms:
            scores.append(sum(terms)/len(terms))
    if not scores:
        raise ValueError('validation_cases_have_no_measured_outcomes')
    return sum(scores)/len(scores)


def update(forecast, telemetry, *, refreshed_queue=None):
    """Condition on survival and combine measured progress with the prior.

    Raw telemetry must come from the actual observation/runner, not a model's
    claims. Recompute from the frozen forecast each time: repeated samples do
    not shrink uncertainty repeatedly. Phase and unit timing remain explicit.
    """
    value = deepcopy(forecast)
    state = telemetry['state']
    elapsed_queue = telemetry.get('queue_elapsed_seconds', 0.)
    elapsed_work = telemetry.get('work_elapsed_seconds', 0.)
    value['telemetry'] = deepcopy(telemetry)
    for metric, field in (('memory_bytes', 'peak_memory_bytes'), ('cpu_seconds', 'cpu_seconds')):
        original = forecast.get('resources', {}).get(metric)
        observed = telemetry.get(field)
        if original is not None and observed is not None:
            value['resources'][metric] = distribution(original['mu'], original['sigma'],
                elapsed=max(original['elapsed'], observed))
    if state == 'queued':
        original = refreshed_queue or value['times']['queue']
        value['times']['queue'] = distribution(original['mu'], original['sigma'], elapsed=elapsed_queue)
    elif state in ('running', 'complete', 'failed'):
        value['times']['queue'] = None
        value['times']['setup'] = None
        value['times']['work'] = distribution(value['times']['work']['mu'],
            value['times']['work']['sigma'], elapsed=elapsed_work)
    progress = telemetry.get('completed_fraction')
    if state == 'running' and progress is not None and 0 < progress < 1 and elapsed_work > 0:
        # Inferred total duration is blended with the original total-time prior.
        # Noisy early progress is less informative; phase changes widen noise.
        prior = forecast['times']['work']
        measured_mu = math.log1p(elapsed_work/progress)
        noise = (.25+1.5*(1-progress))**2
        recent_rate = telemetry.get('recent_fraction_per_second')
        if recent_rate is not None and recent_rate > 0:
            recent_total = elapsed_work+(1-progress)/recent_rate
            measured_mu = (measured_mu+math.log1p(recent_total))/2
        # A progress marker written long ago does not keep gaining precision.
        noise *= 1+telemetry.get('progress_age_seconds', 0)/max(1., elapsed_work)
        if telemetry.get('phase_changed'):
            noise *= 4
        weight = prior['sigma']**2/(prior['sigma']**2+noise)
        value['times']['work'] = distribution((1-weight)*prior['mu']+weight*measured_mu,
            math.sqrt((1-weight)*prior['sigma']**2), elapsed=elapsed_work)
    remaining = telemetry.get('allocation_remaining_seconds')
    value['overrun_probability'] = (1-probability_within(value['times']['work'], remaining)
        if remaining is not None and value['times']['work'] is not None else None)
    memory, limit = telemetry.get('peak_memory_bytes'), telemetry.get('memory_limit_bytes')
    value['memory_pressure'] = memory/limit if memory is not None and limit else None
    # A resource alarm is evidence to reconsider, not a fabricated calibrated risk.
    value['resource_alarm'] = (value['memory_pressure'] is not None and value['memory_pressure'] >= .9)
    value['failure_probability'] = 1-value['success_probability']
    if state in ('complete', 'failed'):
        value['times']['work'] = None
        value['failure_probability'] = float(state == 'failed')
        value['overrun_probability'] = 0. if state == 'complete' else None
    return value


def compare(candidate, forecast, obligations, preferences, *, already_credited=()):
    """Expected useful credit and real elapsed cost for a sequential portfolio.

    Queue/setup are paid once. Work-unit effort fractions are caller estimates;
    they do not turn command count or node occupancy into reward. Integrate setup
    uncertainty rather than treating its median as a certain elapsed duration.
    Phase independence and effort fractions remain modeling approximations.
    """
    times = {key: summary(value) for key, value in forecast['times'].items() if value is not None}
    overhead = sum(times[key]['p50_seconds'] for key in ('queue', 'setup', 'return') if key in times)
    wall = candidate['wall_seconds']
    budget = wall
    remaining = forecast.get('telemetry', {}).get('allocation_remaining_seconds')
    if remaining is not None:
        budget = min(budget, remaining)
    total_effort = sum(unit['effort'] for unit in candidate['units'])
    completed = set(forecast.get('telemetry', {}).get('completed_unit_ids', []))
    remaining_effort = sum(unit['effort'] for unit in candidate['units'] if unit['unit_id'] not in completed)
    effort, expected, seen = 0., 0., set(already_credited)
    work = forecast['times']['work']
    resource_demand = resource_summary(forecast, candidate)
    setup = forecast['times'].get('setup')
    # Midpoint quadrature in conditional probability space includes only setup
    # durations that fit the allocation. The remaining probability contributes
    # zero; a broad prior must not make success impossible merely because its
    # median exceeds the requested walltime.
    setup_mass = probability_within(setup, budget) if setup is not None else 1.
    setup_samples = ([quantile(setup, setup_mass*(i+.5)/64) for i in range(64)]
                     if setup is not None and setup_mass > 0 else [0.])
    attainable = []
    for unit in candidate['units']:
        if unit['unit_id'] in completed:
            continue
        effort += unit['effort']
        fraction = effort/(remaining_effort or total_effort)
        chance = (setup_mass*sum(probability_within(work, (budget-seconds)/fraction)
                    for seconds in setup_samples)/len(setup_samples) if work is not None else 0.)
        chance *= forecast['success_probability']
        if resource_demand['memory_fit_probability'] is not None:
            chance *= resource_demand['memory_fit_probability']
        obligation = unit['obligation_id']
        gain = 0. if obligation in seen else obligations[obligation]['credit']*chance
        expected += gain
        seen.add(obligation)
        attainable.append({'unit_id': unit['unit_id'], 'obligation_id': obligation,
                           'completion_probability': chance, 'expected_credit': gain})
    elapsed = overhead+times.get('work', {}).get('p50_seconds', 0)
    node_hours = candidate['nodes']*wall/3600
    utility = expected-preferences['elapsed_cost_per_second']*elapsed-preferences['node_hour_cost']*node_hours
    return {'candidate_id': candidate['id'], 'expected_actual_credit': expected,
        'elapsed_p50_seconds': elapsed, 'requested_node_hours': node_hours,
        'net_expected_value': utility, 'attainable_units': attainable, 'time_estimates': times,
        'resource_estimates': resource_demand,
        'support': forecast['support'], 'method': 'sequential_effort_fraction_with_setup_probability_quadrature',
        'uncertainty_note': 'time components and scientific success may be correlated; validate prospectively'}
