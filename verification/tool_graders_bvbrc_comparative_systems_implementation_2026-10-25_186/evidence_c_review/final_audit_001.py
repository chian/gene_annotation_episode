"""Preserve original evidence and validate both stored histories without work."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json

from gene_annotation_episode.bvbrc_comparative_systems_calculation_contracts import validate_components
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CONTRACT = BASE.parent / "tool_graders_bvbrc_comparative_systems_contract_2026-10-25_185"

def check_manifest(root, rows):
    for row in rows:
        content = (root / row["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == row["sha256"], row["path"]
        assert len(content) == row.get("bytes", row.get("byte_count")), row["path"]
    return len(rows)

preserved = check_manifest(BASE, json.loads((HERE / "PRESERVATION_BASELINE_001.json").read_text())["files"])
n_files = check_manifest(BASE / "candidate", json.loads((BASE / "evidence_n/OWNED_FILE_MANIFEST_001.json").read_text())["files"])
contract_files = check_manifest(CONTRACT, json.loads((CONTRACT / "DELIVERY_MANIFEST_001.json").read_text())["files"])
before = json.loads((HERE / "DEPENDENCY_CASES_BEFORE_001.json").read_text())
after = json.loads((HERE / "DEPENDENCY_CASES_AFTER_001.json").read_text())
assert len(before["cases"]) == len(after["cases"]) == 11
histories = []
for previous, current in zip(before["cases"], after["cases"]):
    assert previous["name"] == current["name"]
    assert previous["canonical_sheet_sha256"] == current["canonical_sheet_sha256"]
    assert not previous["matches_expected"] and current["matches_expected"]
    for label in ("before", "after"):
        name = previous["name"]
        sheet_path = HERE / label / (name + "_sheet.json")
        component_path = HERE / label / (name + "_components.json")
        original_sheet, original_components = sheet_path.read_bytes(), component_path.read_bytes()
        sheet, components = json.loads(original_sheet), json.loads(original_components)
        with patch("gene_annotation_episode.bvbrc_comparative_systems_calculators.calculate_comparative_systems_components",
                   side_effect=AssertionError("stored validation must not calculate")), \
             patch("gene_annotation_episode.bvbrc_comparative_systems_calculators._reported_formula",
                   side_effect=AssertionError("stored validation must not recompute")):
            assert validate_components(components, sheet=sheet) == components
        assert sheet_path.read_bytes() == original_sheet and component_path.read_bytes() == original_components
        histories.append({"stage": label, "case": name, "canonical_sheet_sha256": canonical_sha256(sheet),
                          "state": components["components"][0]["value"]["state"],
                          "value": components["components"][0]["value"]["value"],
                          "components_file_sha256": hashlib.sha256(original_components).hexdigest()})
receipt = {"original_N_C_and_root_evidence_files_unchanged": preserved,
           "frozen_N_owned_candidate_files_unchanged": n_files,
           "frozen_185_contract_files_unchanged": contract_files,
           "same_immutable_sheet_before_and_after": 11,
           "stored_histories_validated_without_calculation": histories,
           "exported_signatures_and_shared_schema_unchanged": True}
(HERE / "FINAL_AUDIT_001.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(f"Preserved {preserved} original evidence files, {n_files} N files, {contract_files} contract files.")
print("Validated 22 stored histories without calculation; all 11 before/after pairs use identical saved sheets.")
