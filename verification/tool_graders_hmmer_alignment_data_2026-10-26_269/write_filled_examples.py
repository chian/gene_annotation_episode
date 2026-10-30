"""Reparse retained native bytes and save current filled B1 numerical examples."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
from test_hmmer_alignment_preparation_data import native_build, NATIVE, payload
from test_hmmer_alignment_preparation_calculations import AMINO_BACKGROUND
from gene_annotation_episode.hmmer_alignment_preparation_data import populate_hmmer_alignment_preparation_sheet
from gene_annotation_episode.hmmer_alignment_preparation_calculations import calculate_hmmer_alignment_preparation_components


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    suffix = sys.argv[1] if len(sys.argv) > 1 else ""
    directory = HERE / ("filled" + suffix)
    directory.mkdir(exist_ok=False)
    examples, evidence = [], []
    for case in ("protein", "dna", "rna", "annotated", "singlemx"):
        operation, inputs, outputs, extraction = native_build(case)
        background = dict.fromkeys("ACGT" if case == "dna" else "ACGU", .25) if case in {"dna", "rna"} else AMINO_BACKGROUND
        sheet = populate_hmmer_alignment_preparation_sheet(operation=operation, inputs=inputs, outputs=outputs, model_extraction=extraction)
        calculations = calculate_hmmer_alignment_preparation_components(sheet, parameters={"background": background})
        dump(directory / ("hmmbuild_" + case + ".sheet.json"), sheet)
        dump(directory / ("hmmbuild_" + case + ".calculations.json"), calculations)
        examples.append({"case": "hmmbuild_" + case,
            "values": {key: value["value"] for key, value in calculations["rows"][0]["components"].items()},
            "checks": [{"code": check["code"], "state": check["state"]} for check in calculations["checks"] if check["code"] != "model_components"]})
    for invocation in sorted((HERE / "native").iterdir()):
        receipt = json.loads((invocation / "receipt.json").read_text())
        original_sheet = json.loads((invocation / "sheet.json").read_text())
        operation = original_sheet["operation"]
        source = (invocation / "input.sto").read_bytes()
        outputs = {"stdout": [payload("stdout", (invocation / "stdout.log").read_bytes(), "output")],
                   "stderr": [payload("stderr", (invocation / "stderr.log").read_bytes(), "output")]}
        if (invocation / "output.sto").exists():
            outputs["masked_alignment"] = [payload("masked_alignment", (invocation / "output.sto").read_bytes(), "output")]
        sheet = populate_hmmer_alignment_preparation_sheet(operation=operation, inputs={"alignment": [payload("alignment", source)]}, outputs=outputs)
        calculations = calculate_hmmer_alignment_preparation_components(sheet)
        dump(directory / (invocation.name + ".sheet.json"), sheet)
        dump(directory / (invocation.name + ".calculations.json"), calculations)
        if receipt["returncode"] == 0:
            check_code = "mask_annotation" if operation["mode"].startswith("mask_") else "native_mapping"
            assert next(item for item in calculations["checks"] if item["code"] == check_code)["state"] == "pass", invocation.name
        row = calculations["rows"][0]
        examples.append({"case": invocation.name, "returncode": receipt["returncode"],
            "values": {key: value["value"] for key, value in row["components"].items()},
            "map": row["reconstruction"]["map"] if row["reconstruction"] else None,
            "input_mm": row["input_mm"], "output_mm": row["output_mm"],
            "issues": [item["code"] for item in calculations["issues"]]})
        evidence.append({"receipt": str((invocation / "receipt.json").relative_to(ROOT)),
                         "returncode": receipt["returncode"], "policy": receipt["policy"]})
    manifest259 = json.loads((NATIVE / "EVIDENCE_MANIFEST.json").read_text())
    compared = {}
    def compare(item):
        if isinstance(item, dict):
            if isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
                relative = item["path"]
                if relative.startswith(("inputs/protein", "inputs/dna.sto", "inputs/rna.sto", "native/hmmbuild_", "native/alimask_")):
                    path = NATIVE / relative
                    if path.is_file():
                        actual = hashlib.sha256(path.read_bytes()).hexdigest()
                        assert actual == item["sha256"], relative
                        compared[str(path.relative_to(ROOT))] = actual
            for child in item.values():
                compare(child)
        elif isinstance(item, list):
            for child in item:
                compare(child)
    compare(manifest259)
    assert compared
    code = [ROOT / ("gene_annotation_episode/" + stem + ".py") for stem in ("hmmer_alignment_preparation_data", "hmmer_alignment_preparation_calculations")]
    code += [ROOT / ("tests/test_" + stem + ".py") for stem in ("hmmer_alignment_preparation_data", "hmmer_alignment_preparation_calculations")]
    reused = [ROOT / ("gene_annotation_episode/" + stem + ".py") for stem in ("hmmalign_inputs", "hmmer_model_data", "hmmer_model_calculations", "local_jobs")]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in code}
    files = [path for path in HERE.rglob("*") if path.is_file() and path.suffix in {".py", ".json", ".sto", ".log", ".md"}]
    dump(HERE / ("FILLED_EXAMPLES" + suffix + ".json"), examples)
    dump(HERE / ("SOURCE_AND_EVIDENCE_MANIFEST" + suffix + ".json"), {"schema": "hmmer_alignment_preparation_verification_269_v1",
        "source_hashes": hashes, "reused_source_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in reused},
        "verified_259_evidence_hashes": compared, "native_receipts": evidence,
        "retained_files": [{"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(files)],
        "qualification": "Pure B1 parsers/calculators and retained/native verification; no episode integration or resource-library completion claimed."})
    print(json.dumps({"source_hashes": hashes, "verified_259_file_count": len(compared), "native_invocation_count": len(evidence),
        "examples": [{"case": example["case"], "values": example["values"], "map": example.get("map")} for example in examples]}, indent=2))


if __name__ == "__main__":
    main()
