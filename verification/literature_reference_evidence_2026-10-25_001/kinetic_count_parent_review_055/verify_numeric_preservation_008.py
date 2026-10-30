"""Compare unchanged canonical numerical behavior to frozen046 on synthetic data."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
from test_literature_kinetic_inputs import fixture, uncertainty_fixture


def main():
    path = Path('/home/chia/repos/gene_annotation_episode/verification/literature_reference_evidence_2026-10-25_001/a105_source_count_words_055/baseline_001/gene_annotation_episode/literature_kinetic_inputs.py')
    spec = importlib.util.spec_from_file_location("gene_annotation_episode._055_original_inputs", path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    cases = []
    for kind, unit in (("Km", "uM"), ("Km", "mM"), ("kcat", "per_min"),
                       ("kcat", "s^-1"), ("catalytic_efficiency", "uM^-1min^-1"),
                       ("catalytic_efficiency", "M^-1s^-1")):
        for numeral in ("8", "0", "-2", "about 8", "<8"):
            source, selected = fixture(kind, unit, numeral, "2")
            if numeral.startswith("about") or numeral.startswith("<"):
                selected["numerator"]["measurement"]["number"]["number_start"] += len("about ") if numeral.startswith("about") else 1
            cases.append((kind + ":" + unit + ":" + numeral, source, selected))
    for statistic in ("unspecified", "sd", "sem"):
        source, selected = uncertainty_fixture(statistic)
        cases.append(("decimal_count_with_" + statistic, source, selected))
    proof = []
    for name, source, selected in cases:
        before = deepcopy(selected)
        old = legacy.read_kinetic_inputs(selected, read_source=source.read)
        new = read_kinetic_inputs(selected, read_source=source.read)
        assert selected == before
        assert old["calculation_inputs"] == new["calculation_inputs"], name
        old_sheet = populate_kinetic_contrast(old["calculation_inputs"])
        new_sheet = populate_kinetic_contrast(new["calculation_inputs"])
        assert old_sheet == new_sheet, name
        encoded = json.dumps(old_sheet, sort_keys=True, ensure_ascii=False, allow_nan=False)
        assert encoded == json.dumps(new_sheet, sort_keys=True, ensure_ascii=False, allow_nan=False)
        proof.append({"case": name, "canonical_inputs_and_full_calculation_exact": True,
                      "sha256": hashlib.sha256(encoded.encode()).hexdigest()})
    result = {"passed": True, "synthetic_cases": len(proof), "cases": proof,
              "baseline046_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "new046_sha256": hashlib.sha256((ROOT / "gene_annotation_episode/literature_kinetic_inputs.py").read_bytes()).hexdigest(),
              "scope": "unchanged canonical scientific numerical behavior; representation versions/count sidecars intentionally differ"}
    with (OUT / "NUMERIC_PRESERVATION_008.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": True, "full_canonical_and_calculation_comparisons": len(proof)}))


if __name__ == "__main__":
    main()
