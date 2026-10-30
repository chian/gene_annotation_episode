"""Root's independent custody and endpoint-component arithmetic review.

The frozen research packet is read-only. No production calculator, source
acquisition, model inference or episode execution is claimed by this script.
"""
from fractions import Fraction
import hashlib
from io import BytesIO
from itertools import product
import json
from pathlib import Path
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "research/experimental_scoring_review_2026-10-23/a105_quantitative_contributor_case_238"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((PACKET / "MANIFEST_001.json").read_text())
    for item in manifest["files"]:
        data = (PACKET / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"], item["path"]
    ledger = json.loads((PACKET / "SOURCE_WITNESSES_001.json").read_text())
    for item in ledger["witnesses"]:
        data = (PACKET / item["artifact"]).read_bytes()
        assert sha(data) == item["artifact_sha256"]
        assert data[item["start"]:item["end"]] == item["literal"].encode()
    derivation = json.loads((PACKET / "TEXT_DERIVATION_001.json").read_text())
    assert sha((PACKET / "originals/primary.html").read_bytes()) == derivation["source_sha256"]
    assert sha((PACKET / "originals/primary_text.txt").read_bytes()) == derivation["derived_sha256"]

    original = (PACKET / "originals/figure4.jpg").read_bytes()
    reading = json.loads((PACKET / "FIGURE_READING_COMPONENTS_001.json").read_text())
    assert sha(original) == reading["source_sha256"]
    with Image.open(BytesIO(original)) as image:
        assert image.size == (479, 262) and image.mode == "L"
        support = []
        for name, row in reading["selected_readings"].items():
            assert 0 <= row["y_enclosure"][0] <= row["y"] <= row["y_enclosure"][1] < image.height
            assert 0 <= row["x"] < image.width
            level = image.getpixel((row["x"], row["y"]))
            assert level < 200
            support.append({"role": name, "x": row["x"], "y": row["y"], "grayscale": level})

    # Work with the shared primitive A0 once. Independent interval division of
    # separately bounded differences would lose that dependency.
    initial, baseline, terminal = 39, 170, 181
    total, retained, additional = terminal - initial, baseline - initial, terminal - baseline
    fraction = Fraction(retained, total)
    assert (total, retained, additional) == (142, 131, 11)
    assert total == retained + additional
    assert fraction * total == retained and (1 - fraction) * total == additional
    corners = [Fraction(b - a, t - a) for a, b, t in product((38, 40), (168, 172), (180, 183))]
    assert min(corners) == Fraction(128, 143) and max(corners) == Fraction(67, 71)
    for slope, intercept in ((7, 23), (-3, 100)):
        a, b, t = [slope * value + intercept for value in (initial, baseline, terminal)]
        assert Fraction(a - b, a - t) == fraction

    expected = {
        "control_rate_threshold_per_volume": Fraction(2) / Fraction(3, 4),
        "reported_corrected_stoichiometry": Fraction(3, 5),
        "relative_excess_vs_named_half_reporter_model": Fraction(3, 5) / Fraction(1, 2) - 1,
        "electron_account_H2_at_reported_ratio": (4 * Fraction(3, 5) + 2) / 2,
        "electron_account_low_condition": (4 * Fraction(1, 2) + 2) / 2,
        "electron_account_high_condition": (4 * Fraction(7, 10) + 2) / 2,
        "graph_retained_fraction": fraction,
        "graph_additional_fraction": 1 - fraction,
        "graph_enclosure_lower": min(corners),
        "graph_enclosure_upper": max(corners),
    }
    arithmetic = json.loads((PACKET / "ARITHMETIC_001.json").read_text())["values"]
    for name, value in expected.items():
        observed = arithmetic[name]
        assert Fraction(int(observed["numerator"]), int(observed["denominator"])) == value
        assert observed["decimal"] == float(value)

    result = {"status": "passed", "observed_unix": time.time(),
              "frozen_source_files_verified": len(manifest["files"]),
              "literal_spans_verified": len(ledger["witnesses"]),
              "original_raster_readings_supported": support,
              "exact_arithmetic_results_verified": len(expected),
              "reading_enclosure_corners": len(corners),
              "affine_invariance_checks": 2,
              "shared_initial_ordinate_preserved": True,
              "control_limit_strictness": "lt; no lower floor or point estimate inferred",
              "physical_covariance": None, "published_slope_uncertainty": None,
              "source_correction_model_truth_verified": False,
              "new_implemented_graders": 0, "selected_episode_execution": False,
              "A105_complete": False, "goal_complete": False}
    with (OUT / "ROOT_SOURCE_CHECK_001.json").open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
