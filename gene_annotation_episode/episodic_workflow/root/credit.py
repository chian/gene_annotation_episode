"""Credit: the annotation credit over the nine axis credits.

    credit = prod_i (1 + K * v_i) ** w_i  -  1

``v_i`` is the axis credit of slot ``i``: the credit its head returned at its latest return, on that axis's own
scale; an axis whose head has not returned yet has credit 0. An axis credit is used as returned: this file never
bounds, clamps or rescales one. ``w_i`` is the root's weight of the axis (``AXIS_WEIGHTS``) and ``K`` the one
constant derived below, the same for every axis.

Derivation of ``K`` from epsilon
--------------------------------
The root credit is the calibrated, rescaled offset-product hypervolume
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

3. Calibrated so that no credit on any axis is credit 0: subtract 1.

Comparing step 3 with the formula at the top:

       K = (1 - epsilon) / epsilon

   and ``epsilon = 0.5`` gives ``K = (1 - 0.5) / 0.5 = 1``.

The old arithmetic also divided by ``1 - H(0)``, which maps axis scores in [0, 1] onto a credit in [0, 1]. That
step needs bounded axis scores and is not part of this credit: axis credits have no upper bound, and neither has
the annotation credit.

What ``K`` is. With every ``w_i = 1`` the product expands to

       sum_i K * v_i  +  sum_{i<j} K**2 * v_i * v_j  +  sum_{i<j<l} K**3 * v_i * v_j * v_l  +  ...

The first sum is the linear reward, earned by an axis alone. The other sums are earned only by credit on several
axes at once. ``K`` is the ratio of the weight of a pair to the weight of a single axis. A smaller epsilon is a
larger ``K``: the terms of several axes grow and single-axis progress counts relatively less. At
``epsilon = 0.5`` the two weigh the same (``K = 1``).

What the weights do
-------------------
Every ``w_i`` is 1 (``AXIS_WEIGHTS``, a setting of the root). Then

- one axis alone, the others at 0, has credit exactly ``K * v``: single-axis progress is linear;
- the same total credit is worth more spread over axes than on one. Spend ``d`` with one axis at ``a`` and
  another at 0: on the first axis the gain is ``K * d``, on the other it is ``K * d + K**2 * a * d``. For a
  total ``T`` split equally over ``n`` axes the credit is ``(1 + K * T / n) ** n - 1``, which exceeds ``K * T``
  for every ``n > 1`` and ``T > 0`` and grows with ``n``.

A weight other than 1 makes the single-axis credit ``(1 + K * v) ** w - 1``, which is not linear in ``v``.

Settings
--------
Everything the owner tunes about the annotation credit is in this file: ``EPSILON``, the weight of each axis, and
the credit units each axis head is commissioned with (``AXIS_CREDIT_UNITS``, ``OPERATIONAL_CREDIT_UNITS``;
``messages/msg_to_child.py`` writes them into the commissions). The units are what makes the nine axis scales
comparable. The root never rescales a credit a head returned.

The estimate credit (the scores of the time estimates a head makes about its jobs) is a separate quantity. It is
not an axis credit and does not enter this credit."""
import math

from method_loop import UNBOUNDED

EPSILON = 0.5
K = (1.0 - EPSILON) / EPSILON

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
    arithmetic. Over the axis credits it is the annotation credit (below); over the scores the axes give one candidate
    annotation it is that annotation's score (``messages/internal_summary.py``). The two never read each other."""
    total = 0.0
    for slot, weight in AXIS_WEIGHTS.items():
        gain = axis_gain(axis_values[slot], weight)
        total = total + gain + total * gain          # (1 + total) * (1 + gain) - 1
    return total


def annotation_credit(axis_credits):
    """The hypervolume over the axis credits ``{slot: v_i}`` of the nine axes."""
    return hypervolume(axis_credits)


def credit(summary, records):
    return annotation_credit({slot: summary['axes'][slot]['credit'] for slot in AXIS_WEIGHTS})


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the annotation credit can rise if the axis ``action_type`` is commissioned next: an axis credit has no
    upper bound (this file never bounds one), so neither has the rise: ``UNBOUNDED``, for every axis."""
    return UNBOUNDED
