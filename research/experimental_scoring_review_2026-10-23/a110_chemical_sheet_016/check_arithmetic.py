"""Research arithmetic only. No paper reader, target analysis or production scorer.

All inputs are manually declared below. Source-derived examples are distinguished
from synthetic mathematical checks. Running this file writes only its adjacent
arithmetic_results.json; it does not populate or install an application sheet.
"""

from fractions import Fraction as F
from itertools import product
import json
from math import comb, isclose
from pathlib import Path


def contrast(y, c, a):
    ec = (y - c) ** 2
    ea = (y - a) ** 2
    return 0 if ec + ea == 0 else (ea - ec) / (ea + ec)


def relaxed_error_bounds(y, model):
    lo = max(0, y[0] - model[1], model[0] - y[1]) ** 2
    hi = max(abs(y[0] - model[1]), abs(y[1] - model[0])) ** 2
    return lo, hi


def relaxed_contrast_bounds(ec, ea):
    low_den = ea[0] + ec[1]
    high_den = ea[1] + ec[0]
    lo = (ea[0] - ec[1]) / low_den if low_den > 0 else 0
    hi = (ea[1] - ec[0]) / high_den if high_den > 0 else 0
    return lo, hi


def normalized_atom_defect(reactants, products):
    """Arithmetic fixture helper for already declared, canceled atom totals."""
    keys = reactants.keys() | products.keys()
    return max(
        (
            abs(products.get(k, 0) - reactants.get(k, 0))
            / max(products.get(k, 0), reactants.get(k, 0))
            if max(products.get(k, 0), reactants.get(k, 0)) > 0
            else F(0)
        )
        for k in keys
    )


def main():
    check_count = 0

    def check(condition):
        nonlocal check_count
        assert condition
        check_count += 1

    # Source-derived NfnAB quantities; source means are approximate even when
    # these manually entered arithmetic fractions are represented exactly.
    nfn_reverse = contrast(F(5, 11), F(1, 2), F(1))
    nfn_forward = contrast(F(10, 11), F(1), F(0))
    nfn_sum = (nfn_reverse + nfn_forward) / 2
    check(nfn_reverse == F(143, 145))
    check(nfn_forward == F(99, 101))
    check(nfn_sum == F(14399, 14645))
    check(isclose(float(nfn_sum), 0.9832024581768521, abs_tol=1e-15))
    broad_nfn = ((nfn_sum - 2) / 3, (nfn_sum + 2) / 3)
    fdo_allocation_residual = F(5) - (F(2) + F(5, 2) + F(1, 2))
    energy_ceiling = (F(100, 80), F(100, 60))
    check(fdo_allocation_residual == 0)
    check(energy_ceiling == (F(5, 4), F(5, 3)))
    check(F(2) + F(2) == F(4))  # electron donation and acceptance
    check(-F(2) + F(0) + F(2) + F(1) == F(0) + F(1) + F(0))

    # UbiUV reported precursor fraction and author-model label distributions.
    p = F(16, 25)
    binomials = {
        m: [F(comb(m, k)) * p**k * (1 - p) ** (m - k) for k in range(m + 1)]
        for m in (2, 3, 4)
    }
    for m, probs in binomials.items():
        check(sum(probs) == 1)
        check(sum(F(k) * q for k, q in enumerate(probs)) == m * p)
    check(binomials[3] == [F(46656, 1000000), F(248832, 1000000), F(442368, 1000000), F(262144, 1000000)])
    check(3 * p == F(48, 25))
    check(3 * F(12, 1000) == F(36, 1000))

    # UbiUV FIGURE-DERIVED four-bar midpoints. These are not source table values.
    b = F(19, 2) / 45
    y = F(31, 2) / 4
    predictions = {m: b + m * p / (1 - p) for m in (0, 2, 3, 4)}
    partial_scores = {m: contrast(y, predictions[3], predictions[m]) for m in (0, 2, 4)}
    check(partial_scores[0] == F(689280, 1050481))
    check(partial_scores[2] == F(-179840, 181361))
    check(partial_scores[4] == F(589440, 950641))
    y_bounds = (F(14, 5), F(17, 3))
    b_bounds = (F(8, 47), F(11, 43))
    p_bounds = (F(628, 1000), F(652, 1000))
    prediction_bounds = {
        m: (
            b_bounds[0] + m * p_bounds[0] / (1 - p_bounds[0]),
            b_bounds[1] + m * p_bounds[1] / (1 - p_bounds[1]),
        )
        for m in (0, 2, 3, 4)
    }
    ec_bounds = relaxed_error_bounds(y_bounds, prediction_bounds[3])
    partial_bounds = {
        m: relaxed_contrast_bounds(ec_bounds, relaxed_error_bounds(y_bounds, prediction_bounds[m]))
        for m in (0, 2, 4)
    }
    for m, bounds in partial_bounds.items():
        check(bounds[0] <= partial_scores[m] <= bounds[1])
        # Check endpoint and midpoint combinations. This is a finite arithmetic
        # check, not proof of the interval derivation or a Monte Carlo CI.
        for yy, bb, pp in product(
            (y_bounds[0], y, y_bounds[1]),
            (b_bounds[0], b, b_bounds[1]),
            (p_bounds[0], p, p_bounds[1]),
        ):
            cc = bb + 3 * pp / (1 - pp)
            aa = bb + m * pp / (1 - pp)
            ss = contrast(yy, cc, aa)
            check(bounds[0] <= ss <= bounds[1])

    # Derived neutral-species Ubi donor half-reaction. The R-H and R-OH
    # fragments share their unspecified R skeleton; one H occurs on both.
    left_atoms = {"C": F(10), "H": F(11), "O": F(6)}
    right_atoms = {"C": F(9 + 1), "H": F(1 + 8 + 2), "O": F(1 + 3 + 2)}
    check(left_atoms == right_atoms)
    check(F(2) - F(2) == 0)  # 2 H+ plus 2 electrons, neutral input/output bases

    # SYNTHETIC boundary checks, not observations and not a target experiment.
    check(contrast(F(1), F(1), F(0)) == 1)
    check(contrast(F(0), F(1), F(0)) == -1)
    check(contrast(F(1, 2), F(1), F(0)) == 0)
    check(contrast(F(1), F(1), F(1)) == 0)
    check(contrast(F(5, 11), F(1, 2), F(1)) == contrast(F(5000, 11), F(500), F(1000)))
    check(contrast(F(5, 11), F(1, 2), F(1)) == -contrast(F(5, 11), F(1), F(1, 2)))
    check(relaxed_contrast_bounds((0, 0), (0, 0)) == (0, 0))
    check(relaxed_contrast_bounds((0, 0), (0, 1)) == (0, 1))
    check(relaxed_contrast_bounds((0, 1), (0, 0)) == (-1, 0))

    # Independent-unit error identity. Means alone would hide opposing results.
    synthetic_y = [F(0), F(1)]
    mean_y = sum(synthetic_y) / len(synthetic_y)
    sample_var = sum((v - mean_y) ** 2 for v in synthetic_y) / (len(synthetic_y) - 1)
    for mu in (F(0), F(1)):
        residual_mean = sum((v - mu) ** 2 for v in synthetic_y) / len(synthetic_y)
        identity_value = (mean_y - mu) ** 2 + F(len(synthetic_y) - 1, len(synthetic_y)) * sample_var
        check(residual_mean == identity_value)
    synthetic_errors = [sum((v - mu) ** 2 for v in synthetic_y) / 2 for mu in (F(1), F(0))]
    check(synthetic_errors == [F(1, 2), F(1, 2)])

    # Deduplication illustration uses explicit observation identity. Equal values
    # alone do not establish duplicate records. This is not an implemented reader.
    portrayals = [("nfn_reverse_observation", nfn_reverse), ("nfn_forward_observation", nfn_forward)]
    duplicated = portrayals + [portrayals[0]]
    unique = dict(duplicated)
    check(sum(unique.values()) / len(unique) == nfn_sum)

    # Synthetic demand coverage, separately flagged; not source measurements.
    resource_amounts = [F(4), F(9)]
    consumption = [F(2), F(3)]
    demand = F(4)
    z = min(u / a for u, a in zip(resource_amounts, consumption))
    f = min(F(1), z / demand)
    check((z, f, 2 * f - 1) == (F(2), F(1, 2), F(0)))
    check(normalized_atom_defect({"C": F(2)}, {"C": F(1)}) == F(1, 2))
    check(normalized_atom_defect({"C": F(20)}, {"C": F(10)}) == F(1, 2))
    check(normalized_atom_defect(left_atoms, right_atoms) == 0)

    for s, d in product((F(-1), F(-1, 2), F(0), F(1, 2), F(1)), (F(0), F(1, 2), F(1))):
        compiled = (1 - d) * s - d
        check(-1 <= compiled <= 1)
        if d == 0:
            check(compiled == s)
        if d == 1:
            check(compiled == -1)
    check((1 - F(1)) * (-F(1)) - F(1) == -1)
    check((1 - F(0)) * F(1) - F(0) == 1)

    results = {
        "status": "research arithmetic checks only; not reader implementation or axis completion",
        "checks_passed": check_count,
        "nfn_source_derived_conditional": {
            "reverse_signed_contrast": {"exact_arithmetic": str(nfn_reverse), "nominal": float(nfn_reverse)},
            "forward_signed_contrast": {"exact_arithmetic": str(nfn_forward), "nominal": float(nfn_forward)},
            "complete_reaction_compilation": {"exact_arithmetic": str(nfn_sum), "nominal": float(nfn_sum), "unconditional_bound_with_unconstrained_nuisance": [-1, 1]},
            "broad_pathway_bound_conditional_on_nominal_stoichiometry": [float(v) for v in broad_nfn],
            "author_model_allocation_residual": float(fdo_allocation_residual),
            "author_scenario_ATP_ceiling": [float(v) for v in energy_ceiling],
        },
        "ubi_source_parameter_derived_predictions": {
            "supplied_precursor_fraction": float(p),
            "binomial_distributions": {str(m): [float(q) for q in probs] for m, probs in binomials.items()},
            "three_oxygen_expected_count": float(3 * p),
            "technical_sensitivity_only": float(3 * F(12, 1000)),
        },
        "ubi_plot_derived_restricted_statistic": {
            "not_final_full_pattern_score": True,
            "baseline_ratio": float(b),
            "labeled_ratio": float(y),
            "m_model_predictions": {str(m): float(v) for m, v in predictions.items()},
            "scores_against_m": {str(m): {"exact_arithmetic": str(v), "nominal": float(v), "conservative_extraction_and_technical_sensitivity_bounds_only": [float(x) for x in partial_bounds[m]]} for m, v in partial_scores.items()},
            "missing_uncertainty": ["biological replicate values/covariance", "intracellular donor enrichment", "isotope-specific recovery", "full baseline and labeled vectors"],
        },
        "synthetic_arithmetic_checks": {
            "source_evidence": False,
            "perfect_match": 1,
            "perfect_alternative_match": -1,
            "equal_error": 0,
            "resource_z": float(z),
            "resource_coverage_f": float(f),
            "resource_signed_cell": float(2 * f - 1),
            "checked_properties": ["unit scaling", "claim/alternative sign reversal", "zero-error handling", "interval enclosure", "replicate residual identity", "duplicate portrayal no increase", "signed bounds", "conservation normalization", "unknown bound retained"],
        },
    }
    out = Path(__file__).with_name("arithmetic_results.json")
    out.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"checks_passed": check_count, "output": str(out), "nfn_conditional_compilation": float(nfn_sum)}, indent=2))


if __name__ == "__main__":
    main()
