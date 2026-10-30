"""Save all nineteen complete sheets and calculations from original 259 bytes."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from test_hmmer_simulation_data import CASES, native_case
from gene_annotation_episode.hmmer_simulation_data import populate_hmmsim_sheet
from gene_annotation_episode.hmmer_simulation_calculations import calculate_hmmsim_components


def values(row):
    return {key: value["value"] for key, value in row["components"].items()}


def main():
    destination = Path(sys.argv[1])
    destination.mkdir()
    report = {"scope": "retained native bytes, final M1 decoder and pure S1; no new simulation or episode integration",
              "native_abi": {"byte_order": "little", "float_format": "ieee754_binary64", "bytes_per_float": 8},
              "abi_provenance": "explicit declaration for the retained 259 little-endian native build; binary segments checked against retained summaries and textual alignment scores",
              "cases": []}
    for case in CASES:
        sheet = populate_hmmsim_sheet(**native_case(case))
        calc = calculate_hmmsim_components(sheet)
        reference = calculate_hmmsim_components(sheet, parameters={"fit_tolerance": 1e-5})
        assert not [c for c in reference["checks"] if c["state"] == "fail"], case
        for suffix, content in (("sheet", sheet), ("components", calc)):
            (destination / f"{case}_{suffix}.json").write_text(json.dumps(content, allow_nan=False, indent=2)+"\n")
        stats = next(r for r in calc["rows"] if r["kind"] == "score_statistics")
        report["cases"].append({"case": case, "operation": sheet["operation"], "scores": values(stats),
            "fits": [{"variant": r["details"]["variant"], **values(r)} for r in calc["rows"] if r["kind"] == "fit"],
            "native_filter": [values(r) for r in calc["rows"] if r["kind"] == "native_filter"],
            "alignments": [values(r) for r in calc["rows"] if r["kind"] == "alignment_statistics"],
            "parser_issue_codes": sorted({i["code"] for i in sheet["issues"]}),
            "calculation_issue_codes": sorted({i["code"] for i in calc["issues"]}),
            "native_tolerance_reference_checks": reference["checks"]})
    # These are saved-data parameter changes; no fixture acquisition in this step.
    saved = json.loads((destination / "fwd_fs_sheet.json").read_text())
    changed = calculate_hmmsim_components(saved, parameters={"tail_masses": [.15], "fixed_lambda": .8,
        "filter_criterion": {"threshold": .05, "meaning": "survival_probability", "comparison": "<=", "fit_variant": "independent"}})
    (destination / "fwd_fs_changed_parameters.json").write_text(json.dumps(changed, allow_nan=False, indent=2)+"\n")
    (destination / "REPORT.json").write_text(json.dumps(report, allow_nan=False, indent=2)+"\n")
    for case in ("vit_fs", "fwd_fs"):
        item = next(c for c in report["cases"] if c["case"] == case)
        print(json.dumps({"case": case, "scores": item["scores"], "independent_fits": [f for f in item["fits"] if f["variant"] == "independent"],
                          "native_filter": item["native_filter"], "alignments": item["alignments"]}))
    changed_fit = next(r for r in changed["rows"] if r["kind"] == "fit" and r["details"]["variant"] == "independent")
    print(json.dumps({"saved_forward_changed_parameters": changed["parameters"], "fit": values(changed_fit),
                      "filter": [values(r) for r in changed["rows"] if r["kind"] == "filter_recalculation"]}))


if __name__ == "__main__":
    main()
