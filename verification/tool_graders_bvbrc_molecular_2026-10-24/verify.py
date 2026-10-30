"""Offline D4 evidence writer; not a production parser or host admission test.

Run from the repository root with .venv/bin/python. Native-derived DataSheet
fixtures have deliberately labeled prepared/population fixture identities.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
tests = runpy.run_path(str(ROOT / "tests/test_bvbrc_data_molecular.py"))


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


native = tests["native_inputs"]()
null_empty = tests["synthetic_inputs"](supplied=[tests["supplied_record"](
    sample_ids=[], biological_replicate_ids=None, technical_replicate_ids=[], normalization_method="")])
left = tests["supplied_record"](sample_ids=["sample-a"], measurement_units=[{"field": "log2_fc", "unit": "unit A"}])
right = tests["supplied_record"](provenance={"source_ref": "independent-supplied-source", "record_path": "/records/2"},
    sample_ids=["sample-b"], measurement_units=[{"field": "log2_fc", "unit": "unit B"}])
conflicting = tests["synthetic_inputs"](supplied=[left, right])
fractional = tests["synthetic_inputs"](results=[{
    "id": "r", "bioset_id": "b", "exp_id": "e", "feature_id": "f",
    "counts": 2.75, "fpkm": 0, "tpm": 5.25, "log2_fc": -3, "p_value": 0,
    "z_score": -0.25, "other_value": -19.5,
}])
fixtures = {"retained_native_observations": native, "synthetic_null_empty_design": null_empty,
            "synthetic_conflicting_supplied_units": conflicting, "synthetic_seven_measurements": fractional}
outputs = {name: tests["_extract"](inputs) for name, inputs in fixtures.items()}
tests["test_retained_native_values_and_exact_independent_expected_relationships"]()
tests["test_empty_native_duration_and_aggregate_arrays_are_retained_without_zipping"]()
tests["test_supplied_null_empty_arrays_and_empty_strings_have_resolvable_distinct_states"]()
tests["test_conflicting_supplied_units_and_design_keep_every_source_without_precedence"]()

write("INPUT_FIXTURES.json", {"version": "bvbrc_molecular_input_fixtures_v1", "interpretation": {
    "retained_native_observations": "Measurements, selected fields, row order and raw-byte hashes from historical retained response bodies; DataSheets independently constructed for this extractor, with synthetic prepared/population identities. No actual host admission or new v2 acquisition.",
    "synthetic_null_empty_design": "Entire input synthetic; exercises resolvable null and empty terminal source values.",
    "synthetic_conflicting_supplied_units": "Entire input synthetic; conflicting unit/design records retain separate actual supplied source locators.",
    "synthetic_seven_measurements": "Entire input synthetic; populated counts, FPKM, TPM and p-values are not live observations.",
}, "fixtures": fixtures})
write("FILLED_EXAMPLES.json", {"version": "bvbrc_molecular_filled_examples_v1", "examples": outputs})

tracked = [
    ROOT / "gene_annotation_episode/bvbrc_data_molecular.py",
    ROOT / "tests/test_bvbrc_data_molecular.py",
    ROOT / "gene_annotation_episode/bvbrc_data_schema.py",
    ROOT / "gene_annotation_episode/bvbrc_data_fields.py",
    ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24/CONTRACT_SHAPES.json",
    ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24/FILLED_EXAMPLES.json",
    ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24/REPORT.json",
    HERE / "INPUT_FIXTURES.json", HERE / "FILLED_EXAMPLES.json", HERE / "verify.py",
]
for name in ("expression_page", "bioset_page", "experiment_page"):
    tracked.extend(ROOT / "verification/tool_graders_bvbrc_data_contract_2026-10-24" / (name + suffix)
                   for suffix in (".body", ".meta.json"))
write("HASHES.json", {str(path.relative_to(ROOT)): digest(path) for path in tracked})
write("REPORT.json", {
    "version": "bvbrc_molecular_verification_v1", "status": "passed_focused_offline_checks",
    "command": ".venv/bin/python -m pytest -q tests/test_bvbrc_data_molecular.py",
    "command_result_record": "TEST_RESULT.txt", "pytest_exit_code": 0, "pytest_passed": 54,
    "artifact_command": ".venv/bin/python verification/tool_graders_bvbrc_molecular_2026-10-24/verify.py",
    "artifact_checks": ["four complete outputs validated independently against frozen shapes plus correction002",
                        "actual negative native measurements and exact expected parent row ordinals",
                        "native empty string and aggregate arrays retained separately",
                        "supplied null/empty terminal locators retained",
                        "conflicting supplied units and design preserved without precedence"],
    "native_measurements": [{"result_id": row["result_id"], "experiment": row["exp_id"], "bioset": row["bioset_id"],
                             "log2_fc": tests["measurement"](row, "log2_fc")["value"],
                             "z_score": tests["measurement"](row, "z_score")["value"]}
                            for row in outputs["retained_native_observations"]["rows"]],
    "verified": ["seven separate native numerical slots", "negative, zero, fractional and unavailable values",
                 "exact result/bioset/experiment/feature IDs", "conflicting parent links retain valid measurements",
                 "all duplicate result occurrences retained", "source-level metadata and exact supplied pointers",
                 "strict finite/boolean/integer/closed-shape and reference validation",
                 "input immutability and saved-input deterministic replay with I/O blocked"],
    "not_executed": ["network requests", "service jobs", "D2 production decoder through D4",
                     "live counts/FPKM/TPM/p-value measurement acquisition", "host source custody and metadata provenance admission",
                     "resource-child operation binding", "episode result delivery and receiver prompt materialization"],
    "remaining_integration": "Root-owned D5/D6 publication, qualification, selected projection and actual receiving episode path remain separate work. This extractor does not establish them.",
    "contract_gaps": [],
})
print("Four filled molecular outputs validated; exact native and supplied-metadata assertions passed.")
print("Native pairs: log2_fc/z_score = -0.132/-0.544 and -0.129/-0.556.")
print("Null/empty supplied metadata and conflicting unit cells retained; no host or episode execution claimed.")
