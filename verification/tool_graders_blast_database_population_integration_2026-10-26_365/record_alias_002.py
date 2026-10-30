"""Add the selected-child report-alias proof without replacing earlier pins."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
OUT = Path(sys.argv[1])
read = lambda path: json.loads(path.read_bytes())
def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
def descriptor(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

run = PACKET / "alias_011"
receipt = read(run / "receipt.json")
assert receipt["returncode"] == 0
assert read(run / "before-source-pins.json") == read(run / "after-source-pins.json")
paths = [p for p in (run / "temporary").glob("*/qualified-result.json") if not p.parent.is_symlink()]
assert len(paths) == 1
body = read(paths[0])
examples = read(PACKET / "examples_001" / "ACTUAL_TYPED_NUMERICAL_EXAMPLES_001.json")
examples["negative"].append(dict(source=descriptor(paths[0]), complete=body["complete"],
    native_execution_successful=body["publication"]["native_execution_successful"],
    functions=body["publication"]["rows_by_family"]["sequence_function"], failures=body["failures"]))
assert len(examples["negative"]) == 14 and not body["complete"]
write(OUT / "ACTUAL_TYPED_NUMERICAL_EXAMPLES_002.json", examples)
pins = read(PACKET / "SOURCE_PINS_CURRENT_001.json")
changed = {"tests/blast_population_integration_fixtures.py", "tests/test_native_blast_database_population_integration.py"}
for rows in pins.values():
    for index, row in enumerate(rows):
        current = descriptor(ROOT / row["path"])
        if row["path"] not in changed:
            assert current == row, row["path"]
        else:
            target = PACKET / "final_tests_002" / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / row["path"], target)
            rows[index] = current
write(PACKET / "SOURCE_PINS_CURRENT_002.json", pins)
checks = read(PACKET / "CHECKS_001.json")
checks.append(dict(run=run.name, receipt=descriptor(run / "receipt.json"), command=receipt["command"],
    cwd=receipt["cwd"], policy=receipt["policy"], returncode=0,
    elapsed_seconds=receipt["metadata"]["elapsed_seconds"], pytest_summary=["1 passed, 29 deselected in 25.02s"], source_pins_unchanged=True))
write(PACKET / "CHECKS_002.json", checks)
print(json.dumps(dict(positive_cases=len(examples["positive"]), negative_cases=len(examples["negative"]),
    saved_cases=len(examples["saved"]), production_sources_unchanged=True)))
