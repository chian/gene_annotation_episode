"""One published EMSA image; display-scale measurements, not molecular affinity.

No acquisition, OCR, curve fit, model call or production reader is performed.
Coordinates are analyst-declared from the original Figure 8A, zero-based, with
half-open rectangle bounds. The original JPEG is never changed. Re-run writes
JSON to stdout only. All arithmetic keeps negative background-corrected sums.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
IMAGE = ROOT / "research/experimental_scoring_review_2026-10-23/a105_gel_case_096/figure8.jpg"
EXPECTED_SHA256 = "d30e38e432492d114610de90c542ee04bffabb990a46c04331c9bae24fd8c0eb"
CENTERS = (47, 93, 140, 190, 242, 291, 341, 392)
PROTEIN_NM = (0, 10, 20, 30, 30, 30, 30, 30)
COMPETITOR_NM = (0, 0, 0, 0, 15, 30, 60, 120)
Y_BANDS = {"upper_shifted": (197, 215), "lower_shifted": (219, 239), "free": (248, 274)}


def rectangle_values(image, box):
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
        raise ValueError("out_of_image_roi")
    return list(image.crop(box).tobytes())


def divide(a, b):
    return a / b if b > 0 else None


def extract(image, *, half_width=19, expand_y=0, background_y=(151, 190), median_background=False):
    rows = []
    for lane, (x, p, c) in enumerate(zip(CENTERS, PROTEIN_NM, COMPETITOR_NM), 1):
        x0, x1 = x - half_width, x + half_width
        bg_box = (x0, background_y[0], x1, background_y[1])
        bg_darkness = sorted(255 - v for v in rectangle_values(image, bg_box))
        n = len(bg_darkness)
        bg = ((bg_darkness[(n - 1)//2] + bg_darkness[n//2]) / 2
              if median_background else sum(bg_darkness) / n)
        bands = {}
        for name, (y0, y1) in Y_BANDS.items():
            box = (x0, y0 - expand_y, x1, y1 + expand_y)
            vals = rectangle_values(image, box)
            raw = sum(255 - v for v in vals)
            bands[name] = {
                "roi": box, "pixel_count": len(vals), "raw_darkness_sum": raw,
                "background_term": len(vals) * bg,
                "corrected_darkness_sum": raw - len(vals) * bg,
                "digital_minimum_count": vals.count(0),
                "digital_minimum_fraction": vals.count(0) / len(vals),
            }
        shifted = sum(bands[k]["corrected_darkness_sum"] for k in ("upper_shifted", "lower_shifted"))
        total = shifted + bands["free"]["corrected_darkness_sum"]
        whole_box = (x0, 145, x1, 278)
        whole_vals = rectangle_values(image, whole_box)
        whole = sum(255-v for v in whole_vals) - len(whole_vals) * bg
        row = {
            "lane": lane, "iscR_nM_reported": p, "self_competitor_nM_reported": c,
            "labeled_probe_nM_reported": 5, "competitor_probe_molar_ratio": c/5,
            "protein_probe_nominal_molar_ratio": p/5,
            "background_roi": bg_box, "background_darkness_per_pixel": bg,
            "bands": bands, "shifted_darkness_sum": shifted, "selected_darkness_sum": total,
            "selected_shifted_darkness_fraction": divide(shifted, total),
            "whole_lane_roi": whole_box, "whole_lane_corrected_darkness": whole,
            "outside_selected_bands_darkness": whole-total,
            "outside_selected_bands_fraction": divide(whole-total, whole),
        }
        rows.append(row)
    f0 = rows[0]["selected_shifted_darkness_fraction"]
    f30 = rows[3]["selected_shifted_darkness_fraction"]
    for row in rows:
        f = row["selected_shifted_darkness_fraction"]
        row["no_protein_adjusted_shift_fraction"] = f-f0
        row["selected_signal_relative_to_no_protein_lane"] = divide(row["selected_darkness_sum"], rows[0]["selected_darkness_sum"])
        row["retained_fraction_vs_30nM_no_competitor"] = divide(f-f0, f30-f0) if row["lane"] >= 4 else None
        row["self_competition_reduction"] = (1-row["retained_fraction_vs_30nM_no_competitor"]
                                             if row["lane"] >= 4 else None)
    return rows


def main():
    data = IMAGE.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("original_figure_byte_identity_mismatch")
    image = Image.open(IMAGE)
    if image.mode != "L" or image.size != (600, 937):
        raise ValueError("unexpected_native_image_representation")
    baseline = extract(image)
    variants = []
    # Declared image-analysis choices; neither random samples nor confidence limits.
    for hw in (17, 19, 21):
        for ey in (0, 2):
            for median in (False, True):
                options = {"half_width": hw, "expand_y": ey,
                           "background_y": (151, 190), "median_background": median}
                variants.append({"options": options, "rows": extract(image, **options)})
    for bg in ((174, 194), (239, 247)):
        options = {"half_width": 19, "expand_y": 0,
                   "background_y": bg, "median_background": False}
        variants.append({"options": options, "rows": extract(image, **options)})
    sensitivity = []
    for i in range(8):
        cell = {"lane": i+1}
        for key in ("selected_shifted_darkness_fraction", "no_protein_adjusted_shift_fraction",
                    "self_competition_reduction", "selected_signal_relative_to_no_protein_lane"):
            vals = [v["rows"][i][key] for v in variants if v["rows"][i][key] is not None]
            cell[key] = {"minimum": min(vals), "maximum": max(vals)} if vals else None
        sensitivity.append(cell)
    f30 = baseline[3]["selected_shifted_darkness_fraction"]
    f120 = baseline[7]["selected_shifted_darkness_fraction"]
    combined_variants = [v["rows"][3]["selected_shifted_darkness_fraction"]
                         - v["rows"][7]["selected_shifted_darkness_fraction"] for v in variants]
    out = {
        "version": "one_case_published_gel_display_measurements_096_v1",
        "source": {"pmcid": "PMC4786714", "figure": "8A", "image_sha256": EXPECTED_SHA256,
                   "native_size": image.size, "native_mode": image.mode},
        "measurement_scale": "background_corrected_sum_of_255_minus_published_JPEG_gray_level",
        "origin": "image_derived_then_calculated_not_reported_densitometry",
        "baseline_options": {"half_width": 19, "expand_y": 0, "background_y": (151, 190),
                             "median_background": False},
        "rows": baseline, "analysis_choice_range_not_sampling_CI": sensitivity,
        "combined_self_competitor_removable_display_shift": {
            "value": f30-f120,
            "formula": "(f30-f0)*(1-(f120-f0)/(f30-f0)) = f30-f120",
            "operands": {"f30": f30, "f120": f120,
                         "f0": baseline[0]["selected_shifted_darkness_fraction"]},
            "unit": "display_darkness_fraction_difference",
            "analysis_choice_range_not_sampling_CI": [min(combined_variants), max(combined_variants)],
            "sampling_variance_formula_if_observed": "Var(f30)+Var(f120)-2*Cov(f30,f120)",
            "sampling_variance": None,
            "meaning": "IscR-associated shifted display signal removed by 120 nM same-DNA competitor",
            "not_meaning": "probability_of_binding_or_overall_experimental_reliability",
        },
        "declared_analysis_variants": variants,
        "unknown": {"raw_detector_linearity": None, "exposure": None, "source_saturation": None,
                    "molecular_bound_fraction": None, "independent_preparation_count": None,
                    "lane_sampling_covariance": None, "Kd": None, "false_positive_probability": None,
                    "overall_experimental_reliability": None, "annotation_credit": None},
    }
    json.dump(out, sys.stdout, indent=2, allow_nan=False)
    print()


if __name__ == "__main__":
    main()
