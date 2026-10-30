"""Record already completed native capture examples without reacquisition."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


directory = Path(__file__).resolve().parent
root = directory.parents[1]
suite = directory / sys.argv[1]
index_path = root / "verification/tool_graders_infernal_preparation_producer_2026-10-26_251/NATIVE_PRODUCER_INDEX_001.json"
index = json.loads(index_path.read_bytes())


def file_record(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(root)), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


native = {}
for case in index["reservations"]:
    target = json.loads((root / case["target"]["path"]).read_bytes())
    native[json.dumps(target, sort_keys=True)] = case
examples = []
for capture_path in sorted((suite / "temporary/pytest").glob("test_true_native_original_*/capture/capture.json")):
    if capture_path.parent.parent.is_symlink():
        continue
    capture = json.loads(capture_path.read_bytes())
    intent = json.loads((capture_path.parent / "capture-intent.json").read_bytes())
    original = native[json.dumps(intent["target"], sort_keys=True)]
    store_directory = capture_path.parent.parent / "store"
    db = sqlite3.connect(store_directory / "state.sqlite3")
    source = json.loads(db.execute("SELECT data FROM records WHERE record_type='source'").fetchone()[0])
    refs = sorted({row["artifact_ref"] for row in capture["artifacts"]})
    byte_count = sum(db.execute("SELECT size FROM artifacts WHERE id=?", (ref,)).fetchone()[0] for ref in refs)
    db.close()
    examples.append({"case": original["case"], "program": original["program"], "mode": original["mode"],
        "native_returncode": original["returncode"], "bundle_validated": capture["bundle_validated"],
        "capture_complete": capture["complete"], "association_count": len(capture["artifacts"]),
        "direction_counts": {direction: sum(row["direction"] == direction for row in capture["artifacts"])
            for direction in ("input", "working_copy", "output")},
        "distinct_selected_paths": len({row["relative_path"] for row in capture["artifacts"]}),
        "distinct_selected_byte_artifacts": len(refs), "retained_unique_selected_file_bytes": byte_count,
        "source_id": source["id"], "source_payload": {k: v for k, v in source.items()
            if k not in {"id", "record_type", "origin"}},
        "original_bundle": original["bundle"], "original_plan": original["plan"],
        "original_target": original["target"], "original_native_receipt": original["native_receipt"],
        "capture_receipt": file_record(capture_path), "associations": capture["artifacts"],
        "failures": capture["failures"]})
assert len(examples) == 4
record = {"version": "infernal_preparation_capture_examples_v1",
    "meaning": "execution_file_custody_not_scientific_measurements_or_annotation_confidence",
    "suite_receipt": file_record(suite / "receipt.json"), "producer_index": file_record(index_path),
    "examples": examples}
path = directory / ("NATIVE_CAPTURE_EXAMPLES_" + sys.argv[2] + ".json")
path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
print(json.dumps([{k: row[k] for k in ("case", "native_returncode", "capture_complete", "association_count",
    "direction_counts", "distinct_selected_paths", "distinct_selected_byte_artifacts",
    "retained_unique_selected_file_bytes")} for row in examples], indent=2))
