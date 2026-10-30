"""Assemble factual prerequisite handoffs from retained terminal receipts."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(sys.argv[1]).resolve()
REPO = PACKET.parents[1]


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw)}


def load(path):
    return json.loads(Path(path).read_text())


def save(name, body):
    Path(name).write_text(json.dumps(body, indent=2, allow_nan=False) + "\n")


receipts = []
for name in ("dependency_probe", "fixture_generation", "fixture_verification"):
    path = PACKET / name / "receipt.json"
    receipt = load(path)
    assert receipt["returncode"] == 0 and receipt["terminal"] and receipt["quiescent"]
    assert receipt["source_pins_unchanged"]
    assert receipt["metadata"]["policy"] == {
        "memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    assert receipt["metadata"]["verified_cgroup"] == {
        "memory_max": 21474836480, "memory_swap_max": 0, "runtime_max": "infinity",
        "kill_mode": "control-group", "oom_policy": "kill"}
    receipts.append({"job": name, "file": pin(path), "receipt": receipt,
                     "handle": pin(PACKET / name / "handle.json"),
                     "selected_request": pin(PACKET / name / "selected_request.json"),
                     "terminal_status": pin(PACKET / name / "terminal_status.json")})

dependencies_path = PACKET / "dependency_probe/DEPENDENCIES.json"
dependencies = load(dependencies_path)
dependencies["retained_probe_manifest"] = pin(dependencies_path)
dependencies["verification_receipts"] = receipts
dependencies["c3_handoff"] = {
    "selected_python_executable": dependencies["python"]["executable"],
    "selected_distribution_names": [dist["name"] for dist in dependencies["distributions"]],
    "environment_changes": [], "new_environment_created": False,
    "cooler_installation_required_for_this_format_binding": False,
    "freeze_guidance": "Freeze actual selected distribution/library files and Python identity from this record; freeze the later producer implementation only after it exists.",
    "production_binding_established": False,
}
save("DEPENDENCIES.json", dependencies)

expected_path = PACKET / "EXPECTED_INPUTS.json"
expected = load(expected_path)
verification_path = PACKET / "fixture_verification/ARRAY_VERIFICATION.json"
verification = load(verification_path)
assert verification["passed"]
fixtures = []
for hand_input, actual in zip(expected["fixtures"], verification["fixtures"]):
    assert hand_input["key"] == actual["fixture_key"]
    current = pin(actual["path"])
    assert current["sha256"] == actual["sha256"] and current["size_bytes"] == actual["size_bytes"]
    fixtures.append({"fixture_key": actual["fixture_key"], "file": current,
                     "group_path": actual["group_path"],
                     "expected_synthetic_input": hand_input,
                     "actual_complete_native_readback": actual})
save("FIXTURES.json", {
    "record_type": "chromatin_native_prerequisite_fixture_handoff_v1",
    "origin": "synthetic", "biological_observation": False,
    "reference_authority": "local_file_facts_only_no_store_artifact_authority",
    "fixtures": fixtures, "expected_input_file": pin(expected_path),
    "generation_script": pin(PACKET / "generate_fixtures.py"),
    "executed_generation_script": pin(PACKET / "fixture_generation/selected_input.py"),
    "verification_script": pin(PACKET / "verify_fixtures.py"),
    "executed_verification_script": pin(PACKET / "fixture_verification/selected_input.py"),
    "native_generation_receipt": pin(PACKET / "fixture_generation/GENERATION.json"),
    "full_array_verification_receipt": pin(verification_path),
    "verification_receipts": receipts,
    "cooler_library_agreement": verification["cooler_check"],
    "production_parser_tested": False, "production_calculator_tested": False,
    "production_producer_tested": False, "episode_path_tested": False,
    "hic_format_established": False, "tool_count_increment": 0,
})

source_packet = REPO / "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439"
schema_path = source_packet / "sources/cooler-schema_v3.rst"
assert pin(schema_path)["sha256"] == "8c07438c2dee6576a1b9ed37f5fb5d5b0311520381615605fc392a2a44249fb7"
save("SOURCES.json", {
    "record_type": "prerequisite_source_facts_v1",
    "implementation_source_files": [pin(source_packet / "SOURCE_FILES.json")],
    "primary_format_sources": [
        {"url": "https://raw.githubusercontent.com/open2c/cooler/master/docs/schema_v3.rst",
         "retained_complete_source": pin(schema_path),
         "rendered_url": "https://cooler.readthedocs.io/en/latest/schema.html",
         "used_for": "Cooler schema3 table layout, required attrs, dtypes, indexes and storage mode"},
        {"url": "https://docs.h5py.org/en/stable/strings.html",
         "observed_documentation_version": "3.16.0", "retained_complete_source": None,
         "used_for": "Scalar UTF-8 attributes and fixed-length ASCII dataset representation"},
    ],
    "no_goal_repository_file_read": True,
})
summary = {"dependency_distribution_file_counts": {item["name"]: item["file_count"]
                                                     for item in dependencies["distributions"]},
           "dependency_distribution_total_bytes": {item["name"]: item["total_size_bytes"]
                                                     for item in dependencies["distributions"]},
           "loaded_shared_library_file_count": len(dependencies["loaded_shared_library_files"]),
           "fixture_count": len(fixtures), "tool_count_increment": 0,
           "outputs": [pin(name) for name in ("DEPENDENCIES.json", "FIXTURES.json", "SOURCES.json")]}
save("HANDOFF_BUILD.json", summary)
print(json.dumps(summary))
