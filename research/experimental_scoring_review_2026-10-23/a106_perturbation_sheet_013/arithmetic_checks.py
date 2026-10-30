"""Standalone research arithmetic, not an implemented reader or production scorer.

Inputs below are manually transcribed source numbers or explicitly synthetic.
This script does not read papers, datasets, application state or scientific runs.
"""
from fractions import Fraction as F
from pathlib import Path
import json

def out(value):
    return {"exact": str(value), "decimal": float(value)}

source = {
    "YeaG_K116A_amount_comparability": out(F(64, 100)),
    "YeaG_R232A_amount_comparability": out(F(48, 100)),
    "YeaG_K426A_text_comparability": out(F(1)),
    "YeaG_K426A_figure_comparability": out(F(1) / F(112, 100)),
    "YeaG_Y382Stop_amount_comparability": out(F(96, 100)),
    "Cas2_listed_fraction_33bp": out(F(30, 32)),
    "Cas2_listed_fraction_34bp": out(F(2, 32)),
    "Cas2_listed_fraction_plasmid": out(F(26, 32)),
    "Cas2_listed_fraction_genomic": out(F(6, 32)),
    "Cas2_nominal_expansion_bp": out(F(33 + 28)),
}
for hours, percent in [(12, F(85, 1000)), (18, F(107, 1000)), (24, F(134, 1000))]:
    source[f"YeaG_lag_{hours}h_symmetric_contrast"] = out(percent / (2 - percent))

# All inputs from this line through the final assertions are SYNTHETIC.
W, K, R = F(100), F(20), F(90)
B = F(8)
C = F(90, 100)
coverage, identity, determinant_match = F(90, 100), F(72, 90), F(3, 4)
system_overlap = min(F(1), F(8, 10)) + min(F(0), F(2, 10))
H = coverage * identity * determinant_match * system_overlap
theta = (W - K) / (W + K)
restoration_fraction = (R - K) / (W - K)
restoration_agreement = 1 - abs(R - W) / abs(W - K)
isolation = 1 - B / abs(W - K)
q_point = theta * restoration_agreement * C * isolation * H

# Conservative interval arithmetic; no covariance or independence is assumed.
# W in [98,102], K in [18,22], R in [88,92], B in [6,10].
theta_lo, theta_hi = F(98 - 22, 98 + 22), F(102 - 18, 102 + 18)
r_lo, r_hi = F(88 - 22, 102 - 22), F(92 - 18, 98 - 18)
i_lo, i_hi = 1 - F(10, 98 - 22), 1 - F(6, 102 - 18)
q_lo = theta_lo * r_lo * C * i_lo * H
q_hi = theta_hi * r_hi * C * i_hi * H
U = q_lo / q_point

synthetic = {name: out(value) for name, value in {
    "endpoint_signal": theta,
    "raw_restoration_fraction": restoration_fraction,
    "restoration_agreement": restoration_agreement,
    "comparability": C,
    "effect_isolation": isolation,
    "mapping_coverage": coverage,
    "mapping_identity": identity,
    "mapping_determinants": determinant_match,
    "mapping_only": coverage * identity * determinant_match,
    "system_overlap": system_overlap,
    "correspondence_H": H,
    "q_point": q_point,
    "theta_lower": theta_lo,
    "theta_upper": theta_hi,
    "restoration_lower": r_lo,
    "restoration_upper": r_hi,
    "isolation_lower": i_lo,
    "isolation_upper": i_hi,
    "q_lower_conservative": q_lo,
    "q_upper_conservative": q_hi,
    "uncertainty_retention_U": U,
    "demonstration_points": 100 * q_lo,
    "two_opposite_groups_net": (q_lo - q_lo) / 2,
    "two_opposite_groups_positive_mass": q_lo / 2,
    "two_opposite_groups_negative_mass": q_lo / 2,
    "two_opposite_groups_interval_lower": (q_lo - q_hi) / 2,
    "two_opposite_groups_interval_upper": (q_hi - q_lo) / 2,
    "requirement_theta": F(1, 3),
    "counterevidence_effect_deficit": F(1, 3) - F(5, 100),
    "counterevidence_effective_perturbation": F(95, 100),
    "counterevidence_cancellation_isolation": F(9, 10),
    "counterevidence_q": -(F(1, 3) - F(5, 100)) * F(95, 100) * F(9, 10),
}.items()}

assert q_point == F(5103, 25000) == F("0.20412")
assert q_lo == F("0.176418")
assert q_hi == F("0.233766")
assert U == F(121, 140)
assert q_point * U == q_lo
assert 0 < q_lo < q_point < q_hi < 1
assert source["Cas2_listed_fraction_33bp"]["decimal"] + source["Cas2_listed_fraction_34bp"]["decimal"] == 1
assert source["Cas2_listed_fraction_plasmid"]["decimal"] + source["Cas2_listed_fraction_genomic"]["decimal"] == 1
assert (W * 60 - K * 60) / (W * 60 + K * 60) == theta
assert 1 - abs(F(100) - W) / abs(W - K) == 1  # complete restoration
assert 1 - abs(K - W) / abs(W - K) == 0        # no restoration
assert 1 - abs(F(110) - W) / abs(W - K) == restoration_agreement
assert (q_lo + q_lo) / 2 == q_lo               # duplicate representation has no additive gain
assert synthetic["counterevidence_q"]["exact"] == "-969/4000"

payload = {
    "status": "all exact arithmetic assertions passed",
    "scope": "research examples only; no production scorer or reader implemented",
    "source_transcriptions": source,
    "synthetic_example": synthetic,
    "limitations": [
        "Source percentages retain author rounding and unreported uncertainties.",
        "The interval is an outer bound from synthetic bounded errors, not a confidence interval.",
        "Source transcriptions were visually/textually inspected before the authority reset; this script does not reread sources.",
    ],
}
destination = Path(__file__).with_name("arithmetic_results.json")
if destination.exists():
    raise SystemExit("Preserve the existing result; write an additive revision if rerunning.")
destination.write_text(json.dumps(payload, indent=2) + "\n")
print(json.dumps({"status": payload["status"], "q_point": float(q_point), "q_lower": float(q_lo), "q_upper": float(q_hi), "U": float(U), "counter_q": synthetic["counterevidence_q"]["decimal"]}))
