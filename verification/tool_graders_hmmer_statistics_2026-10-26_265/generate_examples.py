"""Retain full populated sheets and independently calculated native comparisons."""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.hmmer_statistics_calculations import calculate_hmmstat_components, native_hmmstat_parameters
from tests.test_hmmer_statistics_data import NATIVE, native_case


def main():
    destination = Path.cwd() / "examples"
    destination.mkdir()
    report = []
    for kind, alphabet in (("protein", "amino"), ("dna", "DNA"), ("rna", "RNA"), ("annotated", "amino")):
        sheet = native_case(kind)
        calculations = calculate_hmmstat_components(sheet, **native_hmmstat_parameters("3.4", alphabet))
        native = sheet["native_rows"][0]["values"]
        components = calculations["rows"][0]["components"]
        comparisons = {field: {"native": native[field], "calculated": components[name]["value"]}
            for field, name in (("relent", "mean_match_relative_entropy"), ("info", "mean_match_information"),
                               ("p_relE", "position_relative_entropy"), ("compKL", "composition_relative_entropy"))}
        for suffix, value in (("sheet", sheet), ("calculations", calculations)):
            (destination / f"{kind}_{suffix}.json").write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
        sources = [NATIVE / f"hmmbuild_{kind}/profile.hmm", NATIVE / f"hmmstat_{kind}/stdout.log"]
        report.append({"example": kind, "comparisons": comparisons,
            "input_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            "scope": "retained native data; pure sheet and calculation; no production episode binding"})
    (destination / "REPORT.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
