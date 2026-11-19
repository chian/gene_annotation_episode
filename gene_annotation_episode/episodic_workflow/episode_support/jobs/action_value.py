"""The action-value calculation: is a costly action worth it, and is a cheaper one about as good?

These are pure functions an episode's ``action`` calls before it accepts a model's pick of a costly action (a job
launch, a child commission). They are not a yield estimator and decide no stopping: an unworthy pick is refused
(``action`` raises ``Rejected`` with the refusal as feedback) and the model decides again.

The model states its prediction with the pick: the candidate annotations it compares, its present support for
each (``current_support``, summing to one) and, for each possible outcome of the action, its probability and the
support after it (``support_after``). The action is valued by how well it tells the candidates apart:

- ``discrimination(prediction)``: the expected fall in uncertainty about which candidate is right, as a fraction
  of the present uncertainty (entropy of the support). One when every outcome settles the question, zero when no
  outcome changes the support;
- ``expected_gain(band, d, correction)``: the kind's typical gain band (``{'low', 'typical', 'high'}``, from the
  estimate table's ``kind_statistics`` or the episode's settings) times ``d`` times the kind's correction;
- ``refusal(pick, alternatives, threshold)``: the reason the pick is unworthy, or ``None``. It is unworthy when
  the upper bound of its expected gain minus its cost is at or below the threshold, or when an alternative costs
  less and its expected gain is at least ``(1 - threshold)`` times that upper bound. The rule reads the pick's
  upper bound, so a kind with little history and a wide band is still tried.
"""
from __future__ import annotations

import math

TOLERANCE = 1e-9


def _distribution(values, what):
    if (not isinstance(values, (list, tuple)) or not values
            or any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in values)
            or abs(math.fsum(values) - 1) > TOLERANCE):
        raise ValueError(what + '_must_be_nonnegative_numbers_summing_to_one')
    return list(values)


def entropy(support):
    """The entropy (natural logarithm) of a support vector."""
    return -math.fsum(value * math.log(value) for value in _distribution(support, 'support') if value > 0)


def discrimination(prediction):
    """The expected fractional fall in entropy of the candidates' support over the predicted outcomes."""
    present = entropy(prediction['current_support'])
    outcomes = prediction['outcomes']
    _distribution([outcome['probability'] for outcome in outcomes], 'outcome_probabilities')
    if any(len(outcome['support_after']) != len(prediction['current_support']) for outcome in outcomes):
        raise ValueError('support_after_must_have_one_number_per_candidate')
    if present == 0:
        return 0.0
    after = math.fsum(outcome['probability'] * entropy(outcome['support_after']) for outcome in outcomes)
    return (present - after) / present


def definitive_outcomes(prediction, definitive_support):
    """The labels of the outcomes whose support gives one candidate at least ``definitive_support``."""
    return [outcome['label'] for outcome in prediction['outcomes']
            if max(_distribution(outcome['support_after'], 'support_after')) >= definitive_support]


def expected_gain(band, d, correction):
    """The gain expected of an action of a kind with the gain band ``band``: ``{'value', 'lower', 'upper'}``."""
    scale = d * correction
    return {'value': band['typical'] * scale, 'lower': band['low'] * scale, 'upper': band['high'] * scale}


def refusal(pick, alternatives, threshold):
    """Why ``pick`` (``{'name', 'expected_gain', 'cost'}``) is unworthy among the available ``alternatives`` (the
    same form), or ``None`` when it is worth taking."""
    upper = pick['expected_gain']['upper']
    if upper - pick['cost'] <= threshold:
        return {'reason': 'not_worth_its_cost', 'action': pick['name'], 'expected_gain_upper': upper,
                'cost': pick['cost'], 'threshold': threshold}
    cheaper = [other for other in alternatives if other['name'] != pick['name'] and other['cost'] < pick['cost']
               and other['expected_gain']['value'] >= (1 - threshold) * upper]
    if cheaper:
        preferred = min(cheaper, key=lambda other: (other['cost'], other['name']))
        return {'reason': 'cheaper_action_gains_about_as_much', 'action': pick['name'],
                'preferred': preferred['name'], 'expected_gain_upper': upper, 'cost': pick['cost'],
                'preferred_expected_gain': preferred['expected_gain']['value'], 'preferred_cost': preferred['cost'],
                'threshold': threshold}
    return None


__all__ = ['definitive_outcomes', 'discrimination', 'entropy', 'expected_gain', 'refusal']
