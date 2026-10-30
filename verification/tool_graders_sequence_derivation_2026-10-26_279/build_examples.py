"""Index actual retained integration artifacts through read-only SQLite access."""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
TEMPORARY = HERE / "check003/temporary"
examples = []
patterns = ("test_native_transformation_ret[0-9]*", "test_chained_discontinuous_tra[0-9]*",
            "test_graded_external_reference[0-9]*")
directories = sorted({path for pattern in patterns for path in TEMPORARY.glob(pattern)
                      if path.is_dir() and not path.is_symlink()})
for case in directories:
    directory = case / "state"
    db = sqlite3.connect("file:" + str(directory / "state.sqlite3") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    def artifact(reference):
        row = db.execute("SELECT * FROM artifacts WHERE id=?", (reference,)).fetchone()
        path = directory / "artifacts" / row["sha256"][:2] / row["sha256"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["sha256"] and len(raw) == row["size"]
        return raw, {"path": str(path.relative_to(ROOT)), "sha256": row["sha256"],
                     "size_bytes": len(raw), "media_type": row["media_type"]}
    for operation in db.execute("SELECT * FROM tool_operations ORDER BY rowid"):
        result = json.loads(operation["result"])
        assert result["status"] == "completed"
        source = json.loads(db.execute("SELECT data FROM records WHERE id=?",
            (result["result"]["source_ref"],)).fetchone()[0])
        native_bytes, native_path = artifact(source["artifact_ref"])
        grades = []
        for reference in source["auxiliary_artifact_refs"]:
            raw, path = artifact(reference)
            if path["media_type"] == "application/vnd.gene-annotation.tool-grading+json":
                body = json.loads(raw)
                assert body["provider"] == source["provider"]
                assert body["native_artifact_ref"] == source["artifact_ref"]
                grades.append((body["grading"], path))
        (grading, grade_path), = grades
        examples.append({"case": case.name, "operation": operation["name"],
            "effective_request": grading["sheet"]["request"],
            "input_sequence": grading["sheet"]["input_sequence"],
            "output_sequence": json.loads(native_bytes)["sequence"],
            "summary": grading["scores"]["summary"],
            "output_source_coverage": grading["scores"].get("output_source_coverage"),
            "native_artifact": native_path, "grading_artifact": grade_path})
    db.close()
assert len(directories) == 8 and len(examples) == 10
destination = HERE / "FILLED_INTEGRATION_EXAMPLES_001.json"
with destination.open("x") as stream:
    json.dump({"schema": "sequence_derivation_integration_examples_v1",
        "source_run": "check003", "source_test_material": "explicitly synthetic sequences with actual local operations",
        "case_count": len(directories), "operation_count": len(examples), "examples": examples},
        stream, indent=2, ensure_ascii=False)
    stream.write("\n")
print(json.dumps({"examples": len(examples), "path": str(destination.relative_to(ROOT)),
    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
