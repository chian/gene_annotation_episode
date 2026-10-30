"""Export filled examples from immutable completed verification Store records."""
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys


def forbidden(*args, **kwargs):
    raise AssertionError("Saved publication examples require no acquisition or execution")


socket.socket = subprocess.Popen = forbidden
run = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
destination.mkdir()
examples = []
cases = [
    ("single_native", "test_retained_native_service_*", "retained-native",
        "Unchanged retained native single-query submission and response; fresh scoped Store/service binding; no new HTTP request."),
    ("batch_synthetic", "test_synthetic_generated_batch*", "synthetic-batch",
        "Synthetic generated-header submission/response; native table numerics retained while query names and job identity were explicitly adapted. Not a live v2 service run."),
    ("batch_zero_synthetic", "test_synthetic_complete_zero_*", "publication",
        "Synthetic complete table with every hit row removed and seven selected input occurrences retained. Not observed native no-hit output."),
]
for label, pattern, operation_key, qualification in cases:
    matches = list((run / "temporary/pytest").glob(pattern + "/state/state.sqlite3"))
    # pytest's *current symlink is an alias of the numbered case directory.
    matches = list(dict.fromkeys(path.resolve() for path in matches))
    assert len(matches) == 1, (label, matches)
    state = matches[0]
    directory = destination / label
    directory.mkdir()
    with sqlite3.connect(state.as_uri() + "?mode=ro", uri=True) as database:
        def artifact(reference):
            sha, = database.execute("SELECT sha256 FROM artifacts WHERE id=?", (reference,)).fetchone()
            content = (state.parent / "artifacts" / sha[:2] / sha).read_bytes()
            assert hashlib.sha256(content).hexdigest() == sha
            return content

        def record(reference):
            return json.loads(database.execute("SELECT data FROM records WHERE id=?", (reference,)).fetchone()[0])

        outcome = json.loads(database.execute("SELECT result FROM tool_operations WHERE operation_key=?",
            (operation_key,)).fetchone()[0])
        result = outcome["result"]
        manifest = json.loads(artifact(record(result["grading_source_ref"])["artifact_ref"]))
        parsed = json.loads(artifact(manifest["parse_ref"]))
        sheet = json.loads(artifact(result["sheet_ref"]))
        calculation = json.loads(artifact(result["calculation_ref"]))
        for name, value in (("outcome", outcome), ("manifest", manifest), ("parse", parsed),
                ("sheet", sheet), ("calculation", calculation)):
            (directory / (name + ".json")).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
        for name, ref in (("submission", result["submission_source_ref"]),
                ("result", result["source_ref"]), ("grading", result["grading_source_ref"])):
            source = record(ref)
            (directory / (name + ".source.json")).write_text(json.dumps(source, sort_keys=True, indent=2) + "\n")
            (directory / (name + ".body")).write_bytes(artifact(source["artifact_ref"]))
            if source["request_ref"] is not None:
                (directory / (name + ".request.json")).write_bytes(artifact(source["request_ref"]))
        examples.append({"example": label, "qualification": qualification,
            "status": outcome["status"], "format": result["format"],
            "source_artifact_sha256": hashlib.sha256(artifact(result["artifact_ref"])).hexdigest(),
            "saved_row_count": len(sheet["hits"]),
            "projection": result["projection"],
            "native_model_length_known": False,
            "files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.iterdir())}})
(destination / "examples.json").write_text(json.dumps(examples, sort_keys=True, indent=2, allow_nan=False) + "\n")
print(json.dumps([{key: example[key] for key in ("example", "status", "format", "saved_row_count")}
    for example in examples], indent=2))
