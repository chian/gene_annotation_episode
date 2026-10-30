"""Pre-implementation independent algebra oracle; entirely synthetic numbers.

These invented source ordinates and covariance are mathematical verification
data, not Kaster measurements, graph-reading errors or biological replicates.
"""
from fractions import Fraction as F
import json
from pathlib import Path


OUT = Path(__file__).resolve().parent


def bilinear(left, matrix, right):
    return sum(left[i] * F(matrix[i][j]) * right[j] for i in range(3) for j in range(3))


def exact(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator), "decimal": float(value)}


def main():
    initial, baseline, terminal = map(F, (10, 4, 2))
    covariance = ((4, 1, 0), (1, 9, 2), (0, 2, 16))
    # Sylvester's criterion supplies an exact independent positive-definiteness
    # check for this synthetic matrix; no fitted/regularized covariance is used.
    leading_minors = (4, 4 * 9 - 1, 4 * (9 * 16 - 2 * 2) - 16)
    assert leading_minors == (4, 35, 544)
    total = initial - terminal
    corrected = initial - baseline
    additional = baseline - terminal
    fraction = corrected / total
    jd, jc, jg = (F(1), F(0), F(-1)), (F(1), F(-1), F(0)), (F(0), F(1), F(-1))
    variance_d = bilinear(jd, covariance, jd)
    variance_c = bilinear(jc, covariance, jc)
    variance_g = bilinear(jg, covariance, jg)
    covariance_cg = bilinear(jc, covariance, jg)
    covariance_cd = bilinear(jc, covariance, jd)
    gradient_f = ((baseline - terminal) / total**2, -1 / total, corrected / total**2)
    variance_f = bilinear(gradient_f, covariance, gradient_f)
    # Independently propagate from C,D, retaining their derived joint covariance.
    ratio_variance = variance_c / total**2 + corrected**2 * variance_d / total**4 - 2 * corrected * covariance_cd / total**3
    false_independent_variance = variance_c / total**2 + corrected**2 * variance_d / total**4
    assert (total, corrected, additional, fraction) == (8, 6, 2, F(3, 4))
    assert (variance_d, variance_c, variance_g, covariance_cg, covariance_cd) == (20, 11, 21, -6, 5)
    assert variance_d == variance_c + variance_g + 2 * covariance_cg
    assert variance_f == ratio_variance == F(59, 256)
    assert false_independent_variance == F(89, 256) != variance_f
    for slope in (F(7), F(-3)):
        a, b, t = (slope * value + 23 for value in (initial, baseline, terminal))
        d = a - t
        jacobian = ((b - t) / d**2, -1 / d, (a - b) / d**2)
        transformed = tuple(tuple(slope**2 * F(value) for value in row) for row in covariance)
        assert (a - b) / d == fraction
        assert bilinear(jacobian, transformed, jacobian) == variance_f
    result = {"status": "passed", "input_origin": "synthetic_mathematical_fixture_only",
              "source_primitive_order": ["initial", "baseline_at_addition", "terminal"],
              "synthetic_ordinates": [10, 4, 2], "synthetic_joint_covariance": covariance,
              "exact_results": {name: exact(value) for name, value in {
                  "total_amplitude": total, "corrected_amplitude": corrected,
                  "additional_amplitude": additional, "retained_fraction": fraction,
                  "total_variance": variance_d, "corrected_variance": variance_c,
                  "additional_variance": variance_g, "corrected_additional_covariance": covariance_cg,
                  "corrected_total_covariance": covariance_cd,
                  "retained_fraction_variance": variance_f,
                  "incorrect_independence_variance_for_comparison": false_independent_variance}.items()},
              "exact_leading_covariance_minors": leading_minors,
              "independent_propagation_forms_agree": True, "affine_covariance_checks": 2,
              "paper_physical_covariance_remains_unknown": True,
              "new_production_grader": False, "A105_complete": False}
    with (OUT / "SHARED_UNCERTAINTY_ORACLE_001.json").open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": "passed", "origin": result["input_origin"],
                      "retained_fraction_variance": exact(variance_f),
                      "false_independence_value": exact(false_independent_variance)}))


if __name__ == "__main__":
    main()
