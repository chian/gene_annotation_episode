"""Retain populated examples; invoked inside the existing bounded local runner."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("blast_column_examples", ROOT / "tests/test_blast_hsp_sites.py")
examples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(examples)

directory = Path.cwd() / "examples"
directory.mkdir()
records = []


def save(name, sheet, evidence_class, input_artifact=None):
    scores = examples.calculate_blast_hsp_column_components(sheet)
    payload = {"evidence_class": evidence_class, "sheet": sheet, "scores": scores}
    if input_artifact is not None:
        payload["input_artifact"] = str(input_artifact.relative_to(ROOT))
        payload["input_sha256"] = hashlib.sha256(input_artifact.read_bytes()).hexdigest()
    path = directory / (name + ".json")
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    records.append({"name": name, "path": str(path.relative_to(Path.cwd())),
        "evidence_class": evidence_class, "status": sheet["status"],
        "program": sheet["program"], "native_locator": sheet["source"]["native_locator"],
        "summary": scores["summary"], "ratios": scores["ratios"]})


save("synthetic_reverse_blastn_window", examples.extract(examples.native("ACG-TAGG", "ACGT-AGG",
    query_from=3, query_to=9, hit_from=11, hit_to=5, query_strand="Plus", hit_strand="Minus",
    identity=6, gaps=2, midline="|||  |||"), program="blastn", qlength=12, rlength=18,
    offset=2, limit=4), "synthetic_independently_checked_case")
save("synthetic_reverse_blastx", examples.extract(examples.native(query_from=12, query_to=4,
    query_frame=-1, hit_from=2, hit_to=4), program="blastx", qlength=12), "synthetic_independently_checked_case")
save("synthetic_reverse_tblastn", examples.extract(examples.native(query_from=2, query_to=4,
    hit_from=12, hit_to=4, hit_frame=-1), program="tblastn", rlength=12), "synthetic_independently_checked_case")
save("synthetic_reverse_tblastx", examples.extract(examples.native(query_to=9, query_frame=1,
    hit_from=12, hit_to=4, hit_frame=-1), program="tblastx", qlength=12, rlength=12), "synthetic_independently_checked_case")
save("synthetic_empty_terminal", examples.extract(offset=3), "synthetic_independently_checked_case")
save("synthetic_missing_traceback", examples.extract(examples.native(qseq=None, hseq=None)),
     "synthetic_independently_checked_case")
save("synthetic_phase_conflict", examples.extract(examples.native(query_from=12, query_to=4,
    query_frame=-2), program="blastx", qlength=12), "synthetic_independently_checked_case")
save("synthetic_split_codon", examples.extract(examples.native("MKG*", "MKG*", query_to=4,
    hit_to=4, identity=4), qlength=4, rlength=4, offset=1, limit=1,
    original_mappings={"query": examples.mapping([examples.segment(0, 4), examples.segment(8, 16)]),
                       "reference": None}), "synthetic_independently_checked_case")
for name, program, length, scale, end in (
        ("unknown_material_protein_ancestry", "blastp", 5, 3, 15),
        ("unknown_material_nucleotide_ancestry", "blastx", 12, 1, 12),
        ("unknown_material_ancestry_unit_conflict", "blastx", 12, 3, 36)):
    bound = examples.operands(program, length, 5)
    bound["query"].update(unit="symbol", molecule="unknown")
    hsp = examples.native(query_to=9, query_frame=1) if program == "blastx" else examples.native()
    save("synthetic_" + name, examples.extract(hsp, program=program, qlength=length,
        operands_input=bound, original_mappings={"query": examples.mapping(
            [examples.segment(0, end)], length=length, scale=scale), "reference": None}),
        "synthetic_independently_checked_case")
local = ROOT / "tests/fixtures/blast_grading_inputs/native_pair_result.json"
_, sheets = examples.retained_sheets(local, "pairwise", "local")
for index, sheet in enumerate(sheets):
    save(f"retained_local_pair_{index}", sheet, "retained_native_local_pair_with_synthetic_reference", local)
api = ROOT / "verification/w04_blast_graders_2026-10-24_001/live_api/result.body"
_, sheets = examples.retained_sheets(api, "database", "api")
for index, sheet in enumerate(sheets):
    save(f"retained_api_zip_hsp_{index}", sheet, "retained_native_api_zip_no_new_request_no_host_admission", api)

(directory / "index.json").write_text(json.dumps(records, indent=2, allow_nan=False) + "\n")
print(json.dumps({"examples": len(records), "index": str(directory / "index.json"),
    "fresh_native_execution": False, "new_api_or_hpc_call": False, "host_custody_tested_here": False}))
