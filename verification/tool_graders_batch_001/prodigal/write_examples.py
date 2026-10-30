"""Grade retained native outputs and explicit synthetic fixtures; no native rerun."""
from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.prodigal_grader import grade_prodigal, calculate_prodigal_scores


HERE = Path(__file__).resolve().parent


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    candidate = {"start": 0, "end": 9, "strand": "+", "code": 11,
                 "partial_begin": False, "partial_end": False,
                 "protein_sequence": "MK*", "native_confidence": 90., "native_score": 10.}
    synthetic = {"candidates": [candidate,
        {**candidate, "start": 6, "end": 15, "strand": "-", "protein_sequence": "M**",
         "partial_end": True, "native_confidence": 0., "native_score": -2.}, deepcopy(candidate)],
        "mode": "meta", "translation_code": 11, "pyrodigal_version": "explicit_synthetic_fixture",
        "coordinate_system": "zero_based_half_open",
        "limitations": ["synthetic measurements for arithmetic verification only"]}
    partial = {**synthetic, "candidates": [candidate,
        {"start": 30, "end": 39, "strand": "-", "code": 11, "protein_sequence": "MXX",
         "partial_begin": "false", "native_confidence": 120, "native_score": -4.}, None]}
    for name, raw in (("synthetic_overlap", synthetic), ("synthetic_partial", partial)):
        write(HERE / f"{name}.native.json", raw)
    cases = [("meta", 306, 0), ("single", 100000, 0),
             ("synthetic_overlap", 20, 100), ("synthetic_partial", 20, 100)]
    checks = []
    for name, length, start in cases:
        raw = json.loads((HERE / f"{name}.native.json").read_text())
        original = deepcopy(raw)
        result = grade_prodigal(raw, input_length=length, input_start=start)
        assert raw == original
        write(HERE / f"{name}.graded.json", result)
        saved = json.loads((HERE / f"{name}.graded.json").read_text())
        prior_sheet = deepcopy(saved["sheet"])
        recalculated = calculate_prodigal_scores(saved["sheet"])
        assert saved["sheet"] == prior_sheet
        assert recalculated == saved["scores"]
        write(HERE / f"{name}.recalculated.json", recalculated)
        summary = recalculated["summary"]
        check = {"case": name, "status": result["sheet"]["status"],
            **{key: summary[key] for key in ("reported_candidate_count", "valid_interval_candidate_count",
                "union_coding_bases", "coding_coverage", "partial_candidate_count",
                "invalid_component_count", "missing_component_count")},
            "native_input_unchanged": raw == original, "saved_sheet_unchanged": saved["sheet"] == prior_sheet,
            "saved_recalculation_equal": recalculated == saved["scores"],
            "acquisition_or_native_rerun": False}
        checks.append(check)
        print(json.dumps(check))
    write(HERE / "example_checks.json", checks)


if __name__ == "__main__":
    main()
