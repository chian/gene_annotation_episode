"""Independent arithmetic/custody review of a retained single-paper packet.

No source acquisition, primary visual read, population, scientific run or score
imputation. All case files remain unchanged; this writes only its own receipt.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
CASE = BASE / "a105_specificity_case_038"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = {str(p.relative_to(CASE)): sha(p) for p in CASE.rglob("*") if p.is_file()}
    manifest = json.loads((CASE / "PACKET_MANIFEST.json").read_bytes())
    for row in manifest:
        path = CASE / row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["bytes"]
    selections = json.loads((CASE / "SOURCE_SELECTIONS.json").read_bytes())
    for row in selections:
        raw = (CASE / row["source_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["source_sha256"]
        assert raw[row["start_utf8_byte"]:row["end_utf8_byte"]] == row["text"].encode()
    example = json.loads((CASE / "NUMERICAL_EXAMPLE.json").read_bytes())
    rows = {row["substrate"]: row for row in example["rows"]}
    assert set(rows) == {"PAP", "IMP", "FBP"}
    assert [rows[name]["efficiency_per_uM_per_min"]["value"] for name in ("PAP", "IMP", "FBP")] == [42, .0027, .025]
    checked = []
    for contrast in example["contrasts"]:
        numerator = rows["PAP"]["efficiency_per_uM_per_min"]["value"]
        denominator = rows[contrast["alternative"]]["efficiency_per_uM_per_min"]["value"]
        ratio = numerator / denominator
        log_contrast = math.log(numerator) - math.log(denominator)
        assert contrast["ratio"] == ratio
        assert math.isclose(contrast["log_ratio"], log_contrast, rel_tol=1e-15)
        assert contrast["difference_efficiency"] == numerator - denominator
        assert math.isclose(contrast["signed_profile_numerator_e_squared_over_2"], log_contrast**2/2, rel_tol=1e-15)
        assert contrast["source_profile_log_ratio"] is None and contrast["source_signed_index"] is None
        checked.append({"alternative": contrast["alternative"], "ratio": ratio,
            "log_contrast": log_contrast, "conditional_profile_numerator": log_contrast**2/2,
            "profile_and_index": None})
    for row in rows.values():
        assert all(row[name]["uncertainty_kind"] == "unspecified" for name in
                   ("Km_uM", "kcat_per_s", "efficiency_per_uM_per_min"))
        quotient = 60 * row["kcat_per_s"]["value"] / row["Km_uM"]["value"]
        assert quotient == row["quotient_of_reported_parameter_means"]
        assert row["reported_efficiency_not_replaced_by_recomputed_quotient"]
    assert example["score_compilation"]["source_profile_log_ratio"] is None
    assert not example["score_compilation"]["uncertainty_or_quality_weights_invented"]
    assert all(sha(CASE / name) == digest for name, digest in before.items())
    reset = json.loads((BASE / "SPECIFICITY_PARENT_RESET_038.json").read_bytes())
    assert reset["status"] == "complete" and reset["acknowledged_chunks"] == 43
    result = {"status": "passed", "utc": datetime.now(timezone.utc).isoformat(),
        "meaning": "Independent retained-packet arithmetic and byte-custody checks; no fresh primary visual inspection, source reacquisition, experimental-truth reproof, model science or production grading",
        "manifest_files_verified": len(manifest), "all_case_files_unchanged": len(before),
        "exact_retained_source_spans_verified": len(selections), "contrasts": checked,
        "uncertainty_meaning_preserved_unspecified": True,
        "reported_efficiency_preserved_separately_from_quotient_of_means": True,
        "source_profile_index_and_target_credit_unfilled": True,
        "completed_parent_reset_sha256": sha(BASE / "SPECIFICITY_PARENT_RESET_038.json"),
        "latest_routing_direction_read": "LITERATURE_GRADER_SELECTION_TARGET_040.md",
        "script_sha256": sha(Path(__file__))}
    with (OUT / "RECEIPT.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "passed", "packet_files_verified": len(manifest),
        "case_files_unchanged": len(before), "source_spans_verified": len(selections),
        "contrasts": checked}))


if __name__ == "__main__":
    main()
