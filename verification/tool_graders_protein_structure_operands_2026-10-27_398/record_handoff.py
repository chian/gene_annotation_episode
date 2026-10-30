"""Record metadata from retained bounded runs; perform no scientific work."""
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
run = PACKET / sys.argv[1]
receipt = json.loads((run / "receipt.json").read_bytes())
assert receipt["returncode"] == 0 and receipt["executed_snapshot_pins_unchanged"]
assert receipt["owned_live_source_pins_unchanged"]
fixtures = run / "temporary/pytest/398-original-native-fixtures0"
data = json.loads((fixtures / "fixture.json").read_bytes())
db = sqlite3.connect(f"file:{fixtures / 'store/state.sqlite3'}?mode=ro", uri=True)
db.row_factory = sqlite3.Row


def write(name, value):
    path = PACKET / name
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(REPO)), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}


def artifact(file):
    path = fixtures / "store/artifacts" / file["sha256"][:2] / file["sha256"]
    row = pin(path)
    assert row["sha256"] == file["sha256"] and row["byte_length"] == file["byte_length"]
    return dict(file_identity=file, retained_file=row)


def read_artifact(file):
    path = fixtures / "store/artifacts" / file["sha256"][:2] / file["sha256"]
    return json.loads(path.read_bytes())


pins = json.loads((run / "source_pins_before.json").read_bytes())
important = {"gene_annotation_episode/protein_structure_operands.py", "tests/test_protein_structure_operands.py",
    "gene_annotation_episode/protein_structure_authority.py", "gene_annotation_episode/protein_structure_selection.py",
    "gene_annotation_episode/protein_structure_publication.py", "gene_annotation_episode/native_protein_structure_returns.py"}
write("SOURCE_PINS_001.json", {"executed_snapshot": str((run / "source_snapshot").relative_to(REPO)),
    "all_executed_sources": pin(run / "source_pins_before.json"),
    "owned_and_public_ports": [row for row in pins if row["path"] in important],
    "immutable_objective_sha256": "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"})

runs = []
for folder in sorted(PACKET.glob("check*")):
    result = json.loads((folder / "receipt.json").read_bytes())
    output = (folder / "stdout.txt").read_text()
    counts = {name: int(number) for number, name in re.findall(r"(\d+) (passed|failed|errors?)(?=[, ])", output.splitlines()[-1])}
    runs.append({"run": folder.name, "counts": counts, "stdout": pin(folder / "stdout.txt"),
        "stderr": pin(folder / "stderr.txt"), "receipt": pin(folder / "receipt.json"), **result})
write("VERIFICATION_001.json", {"authoritative_run": run.name, "runs": runs,
    "qualification": "Module contracts tested with injected public received-authority ports. No full episode communication proof.",
    "inventory_tally": {"before": "112/308", "after": "112/308", "changed": False}})

aligned = []
for name, row in data["alignments"].items():
    descriptor = row["descriptor"]
    native, grade = read_artifact(descriptor["native_file"]), read_artifact(descriptor["grading_file"])
    operation = dict(db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (descriptor["original_operation_key"],)).fetchone())
    aligned.append({"name": name, "descriptor": descriptor,
        "native_file": artifact(descriptor["native_file"]), "original_outer_grading_file": artifact(descriptor["grading_file"]),
        "actual_original_operation": operation, "native": native,
        "sheet_geometry": grade["grading"]["sheet"]["geometry"],
        "residue_correspondence": grade["grading"]["sheet"]["residue_correspondence"],
        "outer_original_scores": grade["grading"]["scores"]})
examples = json.loads((fixtures / "filled_examples.json").read_bytes())
examples["alignments"] = aligned
examples["saved_descriptor"] = data["saved"]["descriptor"]
examples["original_sheet"] = artifact(data["saved"]["descriptor"]["sheet_file"])
examples["original_components"] = artifact(data["saved"]["descriptor"]["original_components_file"])
examples["later_components"] = artifact(data["later_view"]["components_file"])
examples["original_transform"] = data["saved"]["native"]["sheet"]["native_baseline"]["transform"]
examples["received_port_fixture_projections"] = data["projections"]
write("FILLED_EXAMPLES_001.json", examples)

write("FIXTURE_PROVENANCE_001.json", {"fixture_source": pin(fixtures / "fixture.json"),
    "store": pin(fixtures / "store/state.sqlite3"),
    "source_class": "fresh398 synthetic native engineering fixtures; not observed biological data",
    "executed": ["five actual C extraction driver executions", "one actual C held-out comparison driver execution",
        "actual C local reservations and D392 complete retained captures", "D393 original-native-result qualification",
        "four actual Biopython pairwise alignments, published by ToolRegistry with original operation rows and full grades",
        "one explicit later B calculation on the saved sheet", "D1 projections on recorded components"],
    "injected": ["public returns receipt/projection membership ports and detached root read views",
        "fixture-only result custody identifiers; no runtime commissions or completed result-action proof",
        "ToolRegistry sequence work transport supplied measured align_pair bytes within enclosing local_jobs"],
    "not_verified": ["real result-host original commission/receipt proof", "actual frozen typed return and redelivery",
        "shared scientific sequence.align/execution.estimate preflight", "real launch/results integration",
        "credit, continuation, practical closure, and root catalog through a completed episode"],
    "native_extractions": {name: {"descriptor": row["descriptor"], "native": artifact(row["view"]["native_file"]),
        "actual_capture": row["capture"], "actual_worker_qualification": row["prepared"]} for name, row in data["rows"].items()},
    "native_comparison": {"actual_capture": data["saved"]["capture"], "actual_worker_qualification": data["saved"]["prepared"]}})
write("FILLED_OUTPUT_MANIFEST_001.json", {"fixture_root": str(fixtures.relative_to(REPO)),
    "files": [pin(path) for path in sorted(fixtures.rglob("*")) if path.is_file()]})
db.close()
print(json.dumps({"run": run.name, "runs_retained": len(runs), "filled_artifacts": len(aligned)}))
