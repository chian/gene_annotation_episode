"""Copy actual verification metadata and retained output; no scientific work."""
from pathlib import Path
import hashlib
import json

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


attempts = []
for name, code, summary in (("check001", 1, "8 failed, 22 passed in 23.19s"),
                            ("check002", 0, "30 passed in 32.73s")):
    directory = PACKET / name
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == code and receipt["executed_source_pins_unchanged"] is True
    assert receipt["metadata"]["policy"] == {"memory_bytes": 21474836480,
        "scratch_bytes": 4294967296, "wall_seconds": None}
    assert summary in (directory / "stdout.txt").read_text()
    attempts.append({"run": name, "result": summary, "receipt_sha256": sha(directory / "receipt.json"),
        "executed_source_pins_unchanged": True, "checkout_source_drift": receipt["checkout_source_drift"]})

paths = {"gene_annotation_episode/protein_structure_projection_publication.py",
    "tests/test_protein_structure_projection_publication.py",
    "verification/tool_graders_protein_structure_projection_publication_2026-10-27_404/run_bounded.py"}
pins = [row for row in read(PACKET / "check002/source_pins_before.json") if row["path"] in paths]
assert len(pins) == len(paths) and all(sha(ROOT / row["path"]) == row["sha256"] for row in pins)
examples = [path for path in (PACKET / "check002/temporary/pytest").glob("*/filled-projection.json")
    if read(path)["family"] == "comparison_summary" and read(path)["selection"]["window"] is None]
assert len(examples) == 1
original = examples[0]
example = read(original)
assert example["returned_count"] == 1 and example["delivery"]["kind"] == "artifact"
target = PACKET / "FILLED_ARTIFACT_PROJECTION_001.json"
with target.open("xb") as handle:
    handle.write(original.read_bytes())
result = {"scope": "selected_projection_publication_only", "distinct_tests_passed": 30,
    "attempts": attempts, "source_pins": pins,
    "retained_example": {"path": str(target.relative_to(ROOT)), "sha256": sha(target),
        "original_path": str(original.relative_to(ROOT)), "original_sha256": sha(original)},
    "limitations": ["Synthetic native-format engineering fixtures retained from393; no biological sample claim.",
        "Custody-shaped fixtures do not authenticate original episode actions or received-use permission.",
        "Actual Store table publication and typed form validation are covered; production result host remains absent.",
        "No native acquisition, parsing, fitting, alignment, subprocess or network work in the publisher."],
    "completed_tool_count": 112, "protein_tool_accepted": False}
with (PACKET / "VERIFICATION_001.json").open("x") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
print(json.dumps({"passed": 30, "example_sha256": sha(target), "source_pins": pins}))
