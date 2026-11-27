"""The expected seconds of a job from its size, as a curve the estimate ledger's measured jobs make:

    seconds = constant + scale * product over keys of size[key] ** power[key]

The tool that runs the job declares the curve it starts from, ``{'constant': seconds, 'powers': {key: power}}``: the
keys are the size fields its job rows record in the ledger. Nothing here knows a tool, and nothing here reads a file:
the caller hands in the ledger's rows of one job kind and its forgetting policy (in a decision: the estimate table's
read handle, ``read('rows', kind, limit)`` and ``read('policy')``)."""
from datetime import datetime
import math

from scipy.optimize import least_squares


def age_weight(policy, at, now):
    """The weight of a ledger row expected at ``at`` as of ``now`` (ISO times) under the table's ``policy``: it halves
    every ``history_half_life_seconds``; ``None`` past ``history_seconds``."""
    age = (datetime.fromisoformat(now) - datetime.fromisoformat(at)).total_seconds()
    if age > policy['history_seconds']:
        return None
    return 2 ** (-max(age, 0.0) / policy['history_half_life_seconds'])


def measured_jobs(rows, weight):
    """The finished jobs with a measured duration among ``rows`` (the ledger's rows of one job kind): ``[{'size',
    'seconds', 'weight'}]``, ``size`` the numbers the row recorded of its job before it ran (``expected['job']``) and
    ``weight`` what ``weight(row)`` gives; a row it gives ``None`` is left out."""
    found = []
    for row in rows:
        actual = row['actual']
        if actual is None or actual['outcome'] != 'finished' or 'duration_seconds' not in actual:
            continue
        held = weight(row)
        if held is not None:
            found.append({'size': {name: value for name, value in row['expected'].get('job', {}).items()
                                   if type(value) in (int, float)},
                          'seconds': actual['duration_seconds'], 'weight': held})
    return found


def _product(size, powers):
    return math.prod(size[key] ** power for key, power in powers.items())


def _scale(rows, constant, powers):
    """The weighted median of ``(seconds - constant) / product`` over the rows above the constant (``None``: none)."""
    found = sorted(((row['seconds'] - constant) / _product(row['size'], powers), row['weight'])
                   for row in rows if row['seconds'] > constant)
    half, passed = math.fsum(weight for _, weight in found) / 2.0, 0.0
    for value, weight in found:
        passed += weight
        if passed >= half:
            return value
    return None


def fitted(rows, curve):
    """The curve the measured jobs ``rows`` (``measured_jobs``) make from the declared ``curve``: ``{'constant',
    'scale', 'powers'}``, or ``None`` when no row gives a scale. A row is on the curve when it records every key and
    its sizes and seconds are above 0. With at least as many distinct sizes as fitted numbers (the constant, the scale
    and one power per key) all of them are fitted, by weighted least squares on the logarithm of the seconds, from the
    declared values and with the constant kept at or above 0; with fewer the declared constant and powers are kept and
    only the scale is fitted."""
    constant, powers = curve['constant'], dict(curve['powers'])
    rows = [row for row in rows if row['seconds'] > 0 and all(row['size'].get(key, 0) > 0 for key in powers)]
    scale = _scale(rows, constant, powers)
    if len({tuple(row['size'][key] for key in powers) for row in rows}) < len(powers) + 2:
        return None if scale is None else {'constant': constant, 'scale': scale, 'powers': powers}
    if scale is None:
        scale = _scale(rows, 0.0, powers)

    def residuals(values):
        return [math.sqrt(row['weight']) * (math.log(row['seconds']) - math.log(
            values[0] + math.exp(values[1]) * _product(row['size'], dict(zip(powers, values[2:]))))) for row in rows]
    # the bounds on the scale's logarithm and the powers lie far outside any real job: they keep the arithmetic finite
    found = least_squares(residuals, [constant, math.log(scale), *powers.values()],
                          bounds=([0.0, -50.0] + [-10.0] * len(powers), [math.inf, 50.0] + [10.0] * len(powers))).x
    return {'constant': float(found[0]), 'scale': math.exp(found[1]),
            'powers': {key: float(power) for key, power in zip(powers, found[2:])}}


def predicted(curve, size):
    """The seconds the fitted ``curve`` gives for a job of ``size``."""
    return curve['constant'] + curve['scale'] * _product(size, curve['powers'])


__all__ = ['age_weight', 'fitted', 'measured_jobs', 'predicted']
