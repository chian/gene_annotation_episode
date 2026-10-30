"""Research arithmetic for inspected TriA native quantities; no source scorer."""

import json
import math
from fractions import Fraction as F
from pathlib import Path


def main():
    limit = F(10, 1000)
    identity = F(475 - 9, 475)
    residual_amino = 1 - F(71, 100)
    residual_atrazine = 1 - F(12, 100)
    assert limit == F(1, 100)
    assert F(17) / limit == 1700
    assert F(245) / limit == 24500
    assert identity == F(466, 475)
    assert residual_amino / residual_atrazine == F(29, 88)
    assert F(245, 17) - F(135, 17) == F(110, 17)
    # Synthetic algebra only: shared purity cancels but substrate-specific
    # background does not. These numbers are NOT this paper's measurements.
    q1, q2, b1, b2, purity = F(10), F(5), F(2), F(1), F(1, 4)
    assert ((q1-b1)/purity)/((q2-b2)/purity) == (q1-b1)/(q2-b2)
    assert (q1-F(3))/(q2-b2) != q1/q2
    result = {
        "status": "native arithmetic checked; no statistical or target score fitted",
        "limit_nmol_per_min_per_mg": float(limit),
        "aminoatrazine_atrazine_point_limit_ratio": 1700,
        "aminoatrazine_atrazine_log_boundary": math.log(1700),
        "melamine_ammeline_ratio": float(F(245, 17)),
        "sequence_identity": float(identity),
        "residual_aminoatrazine": float(residual_amino),
        "residual_atrazine": float(residual_atrazine),
        "residual_rate_ratio": float(residual_amino/residual_atrazine),
        "unknown": ["printed_halfwidth_statistical_meaning", "sampling_covariance",
                    "background_activity", "protein_mass_fraction", "condition_response",
                    "source_profile_log_ratio", "target_contribution"],
        "synthetic_algebra_checks": "purity cancellation; unequal backgrounds do not cancel",
    }
    path = Path(__file__).with_name("tria_parent_arithmetic_005.json")
    if path.exists():
        prior = json.loads(path.read_text())
        assert prior == result, "Preserve prior result; write a new revision for corrections"
    else:
        path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
