"""Retain one explicitly synthetic A/B1 -> B3 -> B4 numerical example.

This is a verification writer, not a deployed tool. B2 handoff values are
explicitly constructed in the focused tests; no B2, service, job or episode
execution is asserted. Existing artifacts are never overwritten.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("b3_verification_fixture", ROOT / "tests/test_bvbrc_proteome_sheet.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

from gene_annotation_episode.bvbrc_proteome_sheet import build_native_sheet
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components


def save(name, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    with (DEST / name).open("xb") as stream:
        stream.write(raw)


args = fixture.linked_arguments()
before = deepcopy(args)
native_bytes = json.dumps({"genome_names": {"ref_genome": "same label", "comp_genome_2": "same label", "comp_genome_4": "name only"},
                          "feature_matches": fixture.native_rows()}, ensure_ascii=False).encode()
parameters_bytes = json.dumps({"parameters": {
    "genome_ids": [], "user_genomes": [f"/selected-{i}.faa" for i in range(5)], "user_feature_groups": [],
    "reference_genome_index": 1, "min_ident": 0, "min_seq_cov": None, "max_e_val": 1e-5}}).encode()
raw_sources = [
    ("SYNTHETIC_NATIVE_001.json", native_bytes, args["native_results"][0]["value"]["source"]["content"]),
    ("SYNTHETIC_REFERENCE_INPUT_001.faa", b">R0\nAAAA\n>R1\nCCCC\n>R2\nDDDD\n>R3\nEEEE\n", args["inventories"][0]["source"]["content"]),
    ("SYNTHETIC_SUBJECT_INPUT_001.faa", b">S0\nFFFF\n>S1\nFFFF\n", args["inventories"][1]["source"]["content"]),
    ("SYNTHETIC_PARAMETER_RECORD_001.json", parameters_bytes, args["input_index"]["parameter_source"]["source_field"]),
]
source_manifest = []
for name, raw, binding in raw_sources:
    digest = hashlib.sha256(raw).hexdigest()
    assert binding["sha256"] == digest
    assert binding.get("byte_count", len(raw)) == len(raw)
    save(name, raw)
    source_manifest.append({"path": name, "source_ref": binding["source_ref"], "sha256": digest, "byte_count": len(raw)})

sheet_result = build_native_sheet(**args)
assert sheet_result["status"] == "partial" and sheet_result["value"] is not None
sheet = sheet_result["value"]
sheet_before = deepcopy(sheet)
first = calculate_native_components(sheet, parameters=fixture.parameters())
second = calculate_native_components(sheet, parameters=fixture.parameters(.9))
assert first["status"] == second["status"] == "partial"
assert args == before and sheet == sheet_before
track = first["value"]["tracks"][0]
assert track["first_hsp_identity_summary"]["mean"]["value"] == .5
assert track["observed_bound_reference_count"]["value"] == 3
assert track["observed_bound_subject_count"]["value"] == 2
assert track["multiple_reference_subject_count"]["value"] == 1
assert track["excess_bound_pair_count"]["value"] == 1
assert track["demonstrated_subject_sequence_group_count"]["value"] == 1
assert track["selection_counts"]["pass"]["value"] == 2
assert second["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
assert track["reference_input_record_count"]["value"] is None
assert track["observed_reference_fraction"]["fraction"]["value"] is None
assert first["value"]["sheet_sha256"] == second["value"]["sheet_sha256"]
save("SOURCE_INPUTS_001.json", {"origin": "synthetic_supplied_bytes_not_native_service_output", "sources": source_manifest})
save("BUILDER_ARGUMENTS_001.json", {"origin": "actual_A_and_B1_readers_with_explicit_synthetic_NativeJoins", "arguments": args})
save("FILLED_SHEET_RESULT_001.json", sheet_result)
save("CALCULATED_COMPONENTS_001.json", first)
save("RECALCULATED_COMPONENTS_001.json", second)
checks = {
    "origin": "synthetic_fixture_verification_no_scientific_program_service_or_episode_execution",
    "sheet_sha256": first["value"]["sheet_sha256"],
    "native_identity_fractions": [r[fixture.IDENTITY]["value"] for r in sheet["association_rows"]],
    "identity_percentages": [r["first_hsp_alignment_identity_percent"]["value"] for r in first["value"]["associations"]],
    "mean_identity_fraction": track["first_hsp_identity_summary"]["mean"]["value"],
    "mean_subject_endpoint_difference_fraction": track["subject_endpoint_difference_summary"]["mean"]["value"],
    "independent_expected_endpoint_mean": "56/75",
    "observed_bound_reference_count": 3, "observed_bound_subject_count": 2,
    "multiple_reference_subject_count": 1, "excess_bound_pair_count": 1,
    "demonstrated_subject_sequence_group_count": 1,
    "selected_count_at_identity_ge_0_6_and_endpoint_ge_0_7": 2,
    "selected_count_at_identity_ge_0_9_and_endpoint_ge_0_7": 0,
    "execution_denominator": None, "observed_reference_fraction": None,
    "arguments_unchanged": args == before, "sheet_unchanged": sheet == sheet_before,
    "live_execution_verified": False, "episode_integration_verified": False,
}
save("NUMERICAL_CHECKS_001.json", checks)
print(json.dumps(checks, indent=2))
