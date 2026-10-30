"""Research-only recovery/check of CsiD Supplementary Figure 5.

Input is the published figure converted from PDF page 7 by pdftocairo -svg.
It is NOT an original measurement file. This does not implement a project
reader/scorer. Summary values are recovered from vector bar/whisker geometry;
individual markers are a graphical cross-check, not extra observations.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import t as t_dist


HERE = Path(__file__).resolve().parent
SVG = HERE / "supplement_fig5_page7.svg"
PDF = HERE / "41467_2018_7563_MOESM1_ESM.pdf"
root = ET.parse(SVG).getroot()
paths = list(root.iter("{http://www.w3.org/2000/svg}path"))
NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def numbers(s):
    return [float(x) for x in re.findall(NUMBER, s)]


def find_path(tx, ty, sw, *, line_y=None, negative_final_x=False):
    matches = []
    for p in paths:
        transform = p.attrib.get("transform", "")
        if not transform.startswith("matrix("):
            continue
        mat = numbers(transform)
        if (abs(mat[4] - tx) < 1e-5 and abs(mat[5] - ty) < 1e-5
                and p.attrib.get("stroke-width") == sw):
            if negative_final_x and numbers(p.attrib["d"])[2] >= 0:
                continue
            if line_y is None or abs(numbers(p.attrib["d"])[3] - line_y) < 0.01:
                matches.append(p)
    assert len(matches) == 1, (tx, ty, sw, len(matches))
    return matches[0]


def first_page_y(p):
    a, b, c, d, e, f = numbers(p.attrib["transform"])
    x, y = numbers(p.attrib["d"])[:2]
    return b * x + d * y + f


# Axis tick centers: label 0.00 and label 0.20. The labels were visually checked.
zero_path = find_path(212.361713, 245.809577, "1.447", line_y=0, negative_final_x=True)
top_path = find_path(212.361713, 99.721017, "1.447")
y0 = first_page_y(zero_path)
y02 = first_page_y(top_path)
rate_per_pt = 0.2 / (y0 - y02)


def rate(y):
    return (y0 - y) * rate_per_pt


rows = []
spec = [
    ("control_no_inhibitor", 0.0, 3, 221.649542, 128.483326, 230.817528, 120.993141),
    ("NOG", 0.1, 3, 276.837221, 191.221111, 286.005207, 189.962760),
    ("L2HG", 5.0, 3, 332.024901, 169.229930, 341.192887, 161.260373),
    ("D2HG", 5.0, 2, 387.212581, 179.716188, 396.380567, 174.323255),
]
for name, conc, n, bx, by, wx, wy in spec:
    bar = find_path(bx, by, "2.122")
    cap = find_path(wx, wy, "2.122")
    mean_y = first_page_y(bar)
    upper_y = first_page_y(cap)
    mean = rate(mean_y)
    sd = (mean_y - upper_y) * rate_per_pt
    rows.append({
        "condition": name, "added_compound_mM": conc,
        "reported_measurement_count": n,
        "independent_preparation_count": None,
        "replication_unit": "measurements; preparation identity and pairing unreported",
        "units": "micromole oxygen/minute",
        "mean": mean, "sample_sd_from_reported_error_bar": sd,
        "error_type": "SD per Supplementary Figure 5 caption",
        "data_origin": "recovered published vector plot, not original numeric source data",
        "bar_y_pdf_points": mean_y, "upper_whisker_y_pdf_points": upper_y,
        "mean_svg_path": bar.attrib["d"], "mean_svg_transform": bar.attrib["transform"],
        "whisker_svg_path": cap.attrib["d"], "whisker_svg_transform": cap.attrib["transform"],
    })

# A second graphical representation in the same figure: plotted individual
# points. For circles use start-point y (circle center); for squares/triangles
# use the center of their bounding box. This is a check of reconstruction,
# not a source of extra independent data. Symbol placement is approximate.
markers = [p for p in paths if p.attrib.get("stroke-width") == "0.096"]
assert len(markers) == 11
marker_values = []
for idx, p in enumerate(markers):
    vals = numbers(p.attrib["d"])
    mat = numbers(p.attrib["transform"])
    if idx < 3:
        local_y = vals[1]
    else:
        # M/L/Z only for the three squares and five triangles.
        local_y = (min(vals[1::2]) + max(vals[1::2])) / 2
    page_y = mat[3] * local_y + mat[5]
    marker_values.append(rate(page_y))
groups = [marker_values[:3], marker_values[3:6], marker_values[6:9], marker_values[9:11]]
for row, points in zip(rows, groups):
    row["approximate_marker_values"] = points
    row["marker_mean_crosscheck"] = statistics.mean(points)
    row["marker_sd_crosscheck"] = statistics.stdev(points)
    row["mean_graphical_disagreement"] = row["mean"] - statistics.mean(points)
    row["sd_graphical_disagreement"] = row["sample_sd_from_reported_error_bar"] - statistics.stdev(points)
    assert abs(row["mean_graphical_disagreement"]) < 0.001
    assert abs(row["sd_graphical_disagreement"]) < 0.001

# Main worked contrast: no-inhibitor preparation rate minus rate with 5 mM L2HG.
# Same assayed construct; oxygen endpoint. No zero-enzyme blank is substituted.
ctrl, treated = rows[0], rows[2]
mc, ml = ctrl["mean"], treated["mean"]
sc, sl = ctrl["sample_sd_from_reported_error_bar"], treated["sample_sd_from_reported_error_bar"]
nc, nl = ctrl["reported_measurement_count"], treated["reported_measurement_count"]
delta = mc - ml
ratio = ml / mc
vc, vl = sc**2 / nc, sl**2 / nl
v_independent = vc + vl
se_independent = math.sqrt(v_independent)
welch_df = v_independent**2 / (vc**2/(nc-1) + vl**2/(nl-1))
t = delta / se_independent
ci95 = [delta - t_dist.ppf(0.975, welch_df)*se_independent,
        delta + t_dist.ppf(0.975, welch_df)*se_independent]
ratio_variance_terms = [vl/mc**2, (ml/mc**2)**2*vc]
log_ratio_variance_terms = [vl/ml**2, vc/mc**2]
rho_range_se = [abs(math.sqrt(vc) - math.sqrt(vl)), math.sqrt(vc)+math.sqrt(vl)]

# Generalized/profile likelihood, conditional on independent Gaussian assay
# measurements in each arm, separate unknown variances, and the plotted
# summaries approximating the original data. Fitted variances remain nuisance
# parameters. Summary statistics are sufficient under this explicit model.
summary = [(mc, sc, nc), (ml, sl, nl)]
rss_fit = [(n-1)*s*s for m,s,n in summary]


def boundary_loss(mu, summary=summary):
    return sum(n/2*math.log(((n-1)*s*s + n*(m-mu)**2)/((n-1)*s*s))
               for m,s,n in summary)


def profile(summary):
    left = min(m for m,s,n in summary)
    right = max(m for m,s,n in summary)
    grid = np.linspace(left, right, 10001)
    losses = [boundary_loss(mu, summary) for mu in grid]
    candidates = [(left, losses[0]), (right, losses[-1])]
    for i in range(1, len(grid)-1):
        if losses[i] <= losses[i-1] and losses[i] <= losses[i+1]:
            res = minimize_scalar(lambda mu: boundary_loss(mu, summary),
                                  bounds=(grid[i-1], grid[i+1]),
                                  method="bounded", options={"xatol": 1e-14})
            candidates.append((float(res.x),float(res.fun)))
    candidates.sort(key=lambda r:r[1])
    return candidates


candidates = profile(summary)
common_mu, S = candidates[0]
sign = 1 if delta > 0 else -1
S *= sign
B = math.tanh(S/2)

# Equal-variance model is an explicit alternative assumption, not silently
# inferred from the two similar displayed SDs.
N = nc + nl
pooled_var = sum(rss_fit) / (N-2)
rss_0_equal = sum(rss_fit) + nc*nl/N*delta**2
S_equal = sign * N/2 * math.log(rss_0_equal/sum(rss_fit))

# Graphical sensitivity: compare calculations based on bar/whisker geometry
# with calculations based on point-marker geometry. This range describes two
# reconstructions only; it is not a confidence interval or guaranteed bound.
marker_summary = [(statistics.mean(groups[i]),statistics.stdev(groups[i]),3) for i in [0,2]]
marker_S = profile(marker_summary)[0][1]

# Check invariance to units, reversal, and the fact that summary/points are
# overlapping representations, not two evidence blocks.
scaled = [(m*1000,s*1000,n) for m,s,n in summary]
assert math.isclose(profile(scaled)[0][1],abs(S),rel_tol=1e-9)
assert math.isclose(profile(list(reversed(summary)))[0][1],abs(S),rel_tol=1e-9)
assert delta > 0 and 0 < ratio < 1 and all(x > 0 for x in rss_fit)
assert math.isclose(v_independent, vc + vl)
assert math.isclose(ratio_variance_terms[0]+ratio_variance_terms[1],
                    vl/mc**2+ml**2*vc/mc**4)

out = {
    "status": "research-only, graph-derived source-scoped example; no adopted score",
    "source": {
        "doi": "10.1038/s41467-018-07563-6",
        "pmcid": "PMC6265302", "case_group": "csiD_glutarate_hydroxylase",
        "file": PDF.name, "pdf_page_1_based": 7,
        "figure": "Supplementary Figure 5",
        "sha256_pdf": hashlib.sha256(PDF.read_bytes()).hexdigest(),
        "sha256_svg": hashlib.sha256(SVG.read_bytes()).hexdigest(),
        "raw_numeric_workbook_available": False,
    },
    "axis_calibration": {"y_at_zero":y0,"y_at_point2":y02,
                         "rate_units_per_pdf_point":rate_per_pt},
    "rows": rows,
    "contrast": {
        "scope": "observed preparation oxygen-consumption rate: no inhibitor minus 5 mM L2HG",
        "coefficients": [1,-1], "effect":delta,"units":"micromole oxygen/minute",
        "L2HG_to_control_ratio":ratio,"fractional_rate_reduction":1-ratio,
        "log_L2HG_to_control_ratio":math.log(ratio),
        "unconditional_se":None,"unconditional_df":None,
        "independent_preparation_count":None,
        "independent_arm_assumption": {
            "variance_terms": [vc,vl], "variance":v_independent,
            "se":se_independent,"welch_df":welch_df,"welch_t":t,
            "two_sided_p":float(2*t_dist.sf(abs(t),welch_df)),
            "welch_95_percent_interval": [float(v) for v in ci95],
            "ratio_variance_terms_delta_method":ratio_variance_terms,
            "ratio_se_delta_method":math.sqrt(sum(ratio_variance_terms)),
            "log_ratio_variance_terms_delta_method":log_ratio_variance_terms,
            "log_ratio_se_delta_method":math.sqrt(sum(log_ratio_variance_terms)),
        },
        "mean_correlation_sensitivity": {
            "rho_range":[-1,1],"se_extremes_holding_variance_estimates_fixed":rho_range_se,
            "meaning":"algebraic sensitivity, not estimated uncertainty or a confidence interval",
        },
        "profile_proposal_conditional": {
            "model":"independent normal measurements, separate unknown arm variances",
            "Hplus":"mu_control >= mu_L2HG","Hminus":"mu_control <= mu_L2HG",
            "rss_at_unconstrained_fit":rss_fit,
            "common_mean_at_best_opposed_fit":common_mu,
            "all_boundary_local_minima":[[float(a),float(b)] for a,b in candidates],
            "S_nats":S,"proposed_B":B,
            "reverse_statement_S_nats":-S,"reverse_statement_B":-B,
            "equal_unknown_variance_model_S_nats":S_equal,
            "equal_unknown_variance_model_B":math.tanh(S_equal/2),
            "marker_reconstruction_S_nats":marker_S,
            "marker_reconstruction_B":math.tanh(marker_S/2),
            "annotation_hypervolume_coordinate":None,
        },
    },
    "missing": [
        "raw electrode time traces and original numeric source file",
        "preparation identities; biological independence and between-arm pairing",
        "numerical matched no-enzyme blank and its variation",
        "electrode calibration uncertainty and condition-specific matrix response",
        "quantitative simultaneous L2HG production per oxygen consumed",
        "contaminating oxygen-consumption contribution",
        "reaction volume and arm-specific stock/pH preparation details",
        "source-to-target correspondence; target score",
    ],
    "checks": [
        "11 markers with arm counts 3,3,3,2 agree with caption",
        "bar/marker means and SDs agree within 0.001 micromole/minute",
        "all boundary stationary minima searched, not a single local optimum",
        "profile separation invariant to micromole-to-nanomole scaling",
        "opposed statement reverses signed contribution",
        "summary and markers represented as one source block",
        "unknowns remain null; control is not a blank",
    ],
}
output = HERE / "csid_plot_arithmetic_001.json"
assert not output.exists(), "Preserve previous research outputs; use an additive revision."
output.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"output":str(output),"effect":delta,"ratio":ratio,
                  "conditional_se":se_independent,"conditional_df":welch_df,
                  "conditional_S":S,"conditional_B":B},indent=2))
