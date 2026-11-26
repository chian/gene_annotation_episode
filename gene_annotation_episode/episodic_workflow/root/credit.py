"""Credit: the root's credit, feature calling's credit as the base and the nine axis credits multiplying it.

    credit = S * v_f * prod_i (1 + K * v_i) ** w_i

``v_f`` is the credit the feature calling head returned at its latest return (its feature credit, in its own unit; 0
before its first return), ``S`` the root's scale of that unit (``FEATURE_CREDIT_SCALE``). ``v_i`` is the axis credit of
slot ``i``: the credit its head returned at its latest return, on that axis's own scale; an axis whose head has not
returned yet has credit 0. A credit is used as returned: this file never bounds, clamps or rescales one beyond ``S``.
``w_i`` is the root's weight of the axis (``AXIS_WEIGHTS``) and ``K`` the one constant derived below, the same for every
axis.

Why feature calling is the base (the owner, 2026-11-25): "that is a credit assignment problem. evidence for feature type
and narrowing down the feature is part of the initial scoring and the protein annotation is a multiplier of that that
cannot gain anything until feature type scoring/credit is settled a certain amount"; "features need to be scored and
those features get annotations". So with no feature credited (``v_f = 0``) the credit is 0 whatever the axes earned, and
no axis head can raise it; with feature calling credited and no axis credit it is ``S * v_f``; each axis multiplies what
the features earned by its factor ``(1 + K * v_i) ** w_i``. This product form, with the base a plain factor and ``S``
starting at 1.0, is a starting choice of the session that built it (2026-11-25), not the owner's words: the owner ruled
that the annotation is a multiplier of the feature credit, not this formula.

Derivation of ``K`` from epsilon
--------------------------------
The axes' factor is the calibrated, rescaled offset-product hypervolume
(``docs/axis_restructure_20261117/README.md``; the arithmetic it restates is
``offset_normalized_product_hypervolume``, ``softened_hypervolume`` of ``gene_annotation_episode/credit.py`` at
``7e662ea29``). Its definition:

1. Offset product. Every axis contributes the factor ``epsilon + (1 - epsilon) * v`` with the offset
   ``0 < epsilon < 1``. An axis without credit contributes ``epsilon`` and not zero, so an axis without evidence
   does not erase what the other axes earned:

       H(v) = prod_i (epsilon + (1 - epsilon) * v_i) ** w_i

2. Rescaled by its value when no axis has credit, ``H(0) = prod_i epsilon ** w_i``. Dividing factor by factor,
   ``(epsilon + (1 - epsilon) * v) / epsilon = 1 + ((1 - epsilon) / epsilon) * v``:

       H(v) / H(0) = prod_i (1 + ((1 - epsilon) / epsilon) * v_i) ** w_i

   This is the axes' factor of the credit: 1 with no axis credit, so the credit is then the features' base.

Comparing step 2 with the formula at the top:

       K = (1 - epsilon) / epsilon

   and ``epsilon = 0.5`` gives ``K = (1 - 0.5) / 0.5 = 1``.

The old arithmetic also divided by ``1 - H(0)``, which maps axis scores in [0, 1] onto a credit in [0, 1]. That
step needs bounded axis scores and is not part of this credit: axis credits have no upper bound, and neither has
the root's credit.

What ``K`` is. With every ``w_i = 1`` the axes' factor less 1 expands to

       sum_i K * v_i  +  sum_{i<j} K**2 * v_i * v_j  +  sum_{i<j<l} K**3 * v_i * v_j * v_l  +  ...

The first sum is the linear reward, earned by an axis alone. The other sums are earned only by credit on several
axes at once. ``K`` is the ratio of the weight of a pair to the weight of a single axis. A smaller epsilon is a
larger ``K``: the terms of several axes grow and single-axis progress counts relatively less. At
``epsilon = 0.5`` the two weigh the same (``K = 1``).

What the weights do
-------------------
Every ``w_i`` is 1 (``AXIS_WEIGHTS``, a setting of the root). Then

- one axis alone, the others at 0, gives the credit ``S * v_f * (1 + K * v)``: the rise over the features' base is
  linear in the axis credit, and its slope is the base;
- the same total axis credit is worth more spread over axes than on one. Spend ``d`` with one axis at ``a`` and
  another at 0: on the first axis the factor rises by ``K * d``, on the other by ``K * d + K**2 * a * d``. For a
  total ``T`` split equally over ``n`` axes the factor is ``(1 + K * T / n) ** n``, which exceeds ``1 + K * T``
  for every ``n > 1`` and ``T > 0`` and grows with ``n``.

A weight other than 1 makes one axis's factor ``(1 + K * v) ** w``, which is not linear in ``v``.

Settings
--------
Everything the owner tunes about the root's credit is in this file: ``EPSILON``, the weight of each axis, the scale of
feature calling's credit (``FEATURE_CREDIT_SCALE``), and the credit units each axis head is commissioned with
(``AXIS_CREDIT_UNITS``, ``OPERATIONAL_CREDIT_UNITS``; ``messages/msg_to_child.py`` writes them into the commissions).
The units are what makes the nine axis scales comparable; the scale is what makes feature calling's unit the root's.
Feature calling's commission takes no credit unit (its assignment form has none), so its scale is applied here.

The estimate credit (the scores of the time estimates a head makes about its jobs) is a separate quantity. It is
not an axis credit and does not enter this credit."""
import math

from method_loop import UNBOUNDED

EPSILON = 0.5
K = (1.0 - EPSILON) / EPSILON

# The head whose credit is the base of the root's credit (``task.FEATURE_FINDER``).
FEATURE_FINDER = 'feature_calling'
# S: the root's scale of one unit of feature calling's credit. 1.0: the head's unit as it is (a firm claim at a new
# place earns about 1 there). A starting value of 2026-11-25 with no run behind it.
FEATURE_CREDIT_SCALE = 1.0
# The head whose credit is the pure multiple of the root's credit, and the weight of the organism's factor in an
# annotation's score.
ORGANISM_FINDER = 'organism_identification'
ORGANISM_WEIGHT = 1.0

# w_i: the root's weight of each axis. All 1: one axis alone is rewarded linearly and spread beats concentration.
AXIS_WEIGHTS = {
    'sequence_homology_evidence': 1.0,
    'structural_homology_evidence': 1.0,
    'gene_context_evidence': 1.0,
    'evolutionary_history_evidence': 1.0,
    'experimental_activity_evidence': 1.0,
    'perturbation_evidence': 1.0,
    'partner_presence_evidence': 1.0,
    'sample_context_evidence': 1.0,
    'biochemical_feasibility_evidence': 1.0,
}

# The credit of one distinct retained finding on each axis, as the root tells it to that axis's head in the
# whole-axis finding task of its commission. Tuning these makes the axis scales comparable.
AXIS_CREDIT_UNITS = {
    'sequence_homology_evidence': 1.0,
    'structural_homology_evidence': 1.0,
    'gene_context_evidence': 1.0,
    'evolutionary_history_evidence': 1.0,
    'experimental_activity_evidence': 1.0,
    'perturbation_evidence': 1.0,
    'partner_presence_evidence': 1.0,
    'sample_context_evidence': 1.0,
    'biochemical_feasibility_evidence': 1.0,
}

# The credit units a head hands to its operational children (launch, monitor, result acquisition), for the heads
# whose assignment takes them.
OPERATIONAL_CREDIT_UNITS = {
    'handoff_unit': 1.0,
    'acquired_record_unit': 1.0,
    'information_unit': 1.0,
    'completion_target': 1.0,
}


def axis_gain(axis_value, weight):
    """``(1 + K * axis_value) ** weight - 1``, without forming ``1 + x`` (which loses a small value and rounds
    a large one). With weight 1 it is ``K * axis_value`` itself. The factor ``1 + K * axis_value`` of an axis must be
    positive: a value at or below ``-1 / K`` is outside the hypervolume and fails."""
    scaled = K * axis_value
    if scaled <= -1.0:
        raise ValueError('hypervolume_axis_factor_not_positive:' + repr(axis_value))
    if weight == 1:
        return scaled
    return math.expm1(weight * math.log1p(scaled))


def hypervolume(axis_values):
    """``prod_i (1 + K * v_i) ** w_i - 1`` over the values ``{slot: v_i}`` of the nine axes: the root's one
    arithmetic of the axes. Over the axis credits it is the axes' factor of the root's credit less 1 (``root_credit``);
    over the scores the axes give one candidate annotation it is the axes' part of that annotation's score
    (``messages/internal_summary.annotation_score``, which multiplies this result by the organism's factor
    ``((1 + K * s_o) ** w_o - 1)``, a pure multiple outside the product). The two never
    read each other."""
    total = 0.0
    for slot, weight in AXIS_WEIGHTS.items():
        gain = axis_gain(axis_values[slot], weight)
        total = total + gain + total * gain          # (1 + total) * (1 + gain) - 1
    return total


def feature_base(feature_credit):
    """``S * v_f``: the base of the root's credit, from the credit feature calling returned."""
    return FEATURE_CREDIT_SCALE * feature_credit


def root_credit(feature_credit, axis_credits, organism_credit):
    """``v_o * (1 + S * v_f * prod_i (1 + K * v_i) ** w_i)``: the organism identification head's credit ``v_o`` is a pure
    multiple of everything (with no organism call the credit is 0 whatever else was done); alone it earns itself, and
    feature calling's base ``feature_base(feature_credit)`` times the axes' factor multiplies it."""
    base = feature_base(feature_credit)
    over_axes = hypervolume(axis_credits)
    return organism_credit + organism_credit * (base + base * over_axes)


def credit(summary, records):
    return root_credit(summary['features']['credit'],
                       {slot: summary['axes'][slot]['credit'] for slot in AXIS_WEIGHTS}, summary['organism']['credit'])


# The record of this credit's definition: what the forecast controller's learned gains are on (``yield_estimator.py``).
# Its change on 2026-11-25 (feature calling's credit became the base) starts every action's learned shares afresh.
CREDIT_DEFINITION = {'kind': 'root_organism_times_one_plus_feature_base_times_axes_hypervolume',
                     'formula': 'v_o * (1 + S * v_f * prod_i (1 + K * v_i) ** w_i)',
                     'feature_credit_scale': FEATURE_CREDIT_SCALE,
                     'epsilon': EPSILON, 'axis_weights': dict(AXIS_WEIGHTS), 'axis_credit_units': dict(AXIS_CREDIT_UNITS)}
# What ``ceiling`` means for each action type the root offers. The forecast controller learns an action's gains only
# from ledger rows recorded under the same credit definition and the same name of that action's ceiling; the name of
# an action's ceiling changes when the derivation of that action's ceiling changes, and only that action's.
CEILINGS = {'feature_calling': 'root_ceiling_zero_without_organism_credit',
            'sequence_homology_evidence': 'root_ceiling_zero_without_organism_or_feature_credit',
            'experimental_activity_evidence': 'root_ceiling_zero_without_organism_or_feature_credit',
            'organism_identification': 'root_ceiling'}


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the root's credit can rise if ``action_type`` is taken next: the arithmetic of ``root_credit``. The
    organism identification head's credit has no upper bound: ``UNBOUNDED``. Feature calling multiplies the organism's
    credit: 0 while that is 0, else ``UNBOUNDED``. An axis head multiplies the organism's credit and the features'
    base: 0 while either is 0, else ``UNBOUNDED``."""
    organism, base = summary['organism']['credit'], feature_base(summary['features']['credit'])
    if action_type == ORGANISM_FINDER:
        return UNBOUNDED
    if action_type == FEATURE_FINDER:
        return UNBOUNDED if organism > 0 else 0.0
    return UNBOUNDED if organism > 0 and base > 0 else 0.0


def outcome_pending(summary, records, position):
    """Whether the outcome of unit ``position`` is pending (``method_loop.episode_type``; ``summary`` after the unit): a
    commission of a head that left a job running when it ended its turn. Its rise does not yet measure the commission
    (the job's results are not in), so the forecast controller learns nothing from it; the commission that returns to
    the head is the observation. Never pending is a
    commission of feature calling or of the organism identification head, which leave no job running (their returns
    declare no job field, and feature calling does not end while a search of its own is running)."""
    return summary['units'][position]['pending']
