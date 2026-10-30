"""Run the focused tests and retain concrete byte-custody examples."""
from pathlib import Path
import hashlib
import json
import sys

import pytest

from gene_annotation_episode.native_file_capture import capture_declared_native_files, retained_native_file
from gene_annotation_episode.state import Store


attempt, snapshot = map(Path, sys.argv[1:])
status = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(attempt / "temporary/pytest"),
    "--rootdir", str(snapshot), "--junitxml", str(attempt / "pytest.xml"),
    str(snapshot / "tests/test_native_file_capture.py")])
if status:
    raise SystemExit(status)

producer = attempt / "example_producer"
producer.mkdir()
declarations = []
examples = [
    ("complete.bin", b"abc", b"abc", 3, "present"),
    ("empty.bin", b"", b"", 0, "present"),
    ("digest_mismatch.bin", b"xyz", b"abc", 3, "present"),
    ("size_mismatch.bin", b"abc", b"abc", 4, "present"),
    ("unavailable.bin", None, b"abc", 3, "present"),
    ("declared_absent.bin", b"present today but not consulted", None, None, "absent"),
]
for name, actual, declared, size, state in examples:
    if actual is not None:
        (producer / name).write_bytes(actual)
    declarations.append({"relative_path": name, "format": "synthetic_opaque_bytes",
        "state": state, "sha256": hashlib.sha256(declared).hexdigest() if declared is not None else None,
        "size_bytes": size})
with Store(attempt / "example_store") as store:
    rows = capture_declared_native_files(store, directory=str(producer), declarations=declarations)
    for row, example in zip(rows, examples):
        if row["observed"] is not None:
            assert retained_native_file(store, row["observed"]).read_bytes() == example[1]
    assert [row["outcome"] for row in rows] == ["verified", "verified", "digest_mismatch",
        "digest_mismatch", "unavailable", "declared_absent"]
(attempt / "example_capture.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps({"example_capture_path": str(attempt / "example_capture.json"),
    "rows": len(rows), "outcomes": [row["outcome"] for row in rows]}))
