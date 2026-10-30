#!/usr/bin/env python3
"""Additional SYNTHETIC sensitivity checks preserving known independent error."""

import json
import math
from pathlib import Path

import numpy as np


def main():
    n, independent, residual, effect = 10, .10, .15, .8
    results = []
    for name, kappa in [("maximum_shared_residual", 1.0),
                        ("independent_residual", 0.0),
                        ("minimum_residual_mean_variance", -1 / (n - 1))]:
        r = residual * ((1 - kappa) * np.eye(n) + kappa * np.ones((n, n)))
        c = independent * np.eye(n) + r
        assert np.linalg.eigvalsh(r).min() >= -1e-12
        assert np.linalg.eigvalsh(c).min() > 0
        one = np.ones(n)
        variance = 1 / (one @ np.linalg.solve(c, one))
        expected_variance = independent / n + residual * (1 + (n - 1) * kappa) / n
        assert math.isclose(variance, expected_variance, rel_tol=1e-12, abs_tol=1e-12)
        s = effect ** 2 / (2 * variance)
        results.append({"name": name, "residual_correlation_kappa": kappa,
                        "total_pair_correlation": residual * kappa / (independent + residual),
                        "residual_covariance": r.tolist(), "total_covariance": c.tolist(),
                        "GLS_variance": variance, "S": s, "B": math.tanh(s / 2)})
    assert math.isclose(results[0]["S"], 2.0)
    assert math.isclose(results[1]["S"], 12.8)
    assert math.isclose(results[2]["S"], 32.0)
    output = {"status": "SYNTHETIC: fixed independent covariance .10 I, residual diagonal .15",
              "full_PSD_residual_bounds_for_ten_equal_effects": {"S": [2.0, 32.0], "B": [math.tanh(1), math.tanh(16)]},
              "nonnegative_exchangeable_residual_bounds": {"S": [2.0, 12.8], "B": [math.tanh(1), math.tanh(6.4)]},
              "endpoint_checks": results}
    path = Path(__file__).resolve().parent / "sensitivity_constraints_001.json"
    path.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "endpoint_checks"}, indent=2))


if __name__ == "__main__":
    main()
