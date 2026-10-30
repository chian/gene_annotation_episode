"""Observe the unchanged baseline validator and retain its actual exception."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

OWN = Path(__file__).resolve().parent
BASELINE = OWN / "baseline_candidate"
OUTPUT = OWN / "capture_failure_001"
OUTPUT.mkdir(exist_ok=False)
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["TMPDIR"] = str(OUTPUT)
sys.dont_write_bytecode = True
os.chdir(BASELINE)
sys.path.insert(0, str(BASELINE))
import pytest
from gene_annotation_episode import bvbrc_genome_alignment_sheet as sheet


def write_json(name, value):
    path = OUTPUT / name
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def reference_rows(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key == "requirement_ids":
                yield {"pointer": pointer, "values": child}
            yield from reference_rows(child, pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from reference_rows(child, path + "/" + str(index))


original = sheet.validate_genome_alignment_data
observations = []


@wraps(original)
def observe_validation(value):
    """Capture the exact argument, invoke the original, and preserve its result."""
    index = len(observations)
    stem = "data_%03d" % index
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ids = {row["requirement_id"] for row in value["requirements"]}
    row = {"index": index, "data_file": stem + ".json", "input_sha256": hashlib.sha256(encoded).hexdigest(),
           "top_level_requirement_ids": sorted(ids), "reference_arrays": list(reference_rows(value))}
    row["unresolved_against_scientific_union"] = [
        {**item, "unknown": [ref for ref in item["values"] if ref not in ids]}
        for item in row["reference_arrays"] if any(ref not in ids for ref in item["values"])]
    observations.append(row)
    write_json(stem + ".json", value)
    try:
        result = original(value)
    except BaseException as error:
        row["exception"] = {"type": type(error).__name__, "message": str(error)}
        raise
    else:
        row["returned"] = True
        return result
    finally:
        assert hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest() == row["input_sha256"]


sheet.validate_genome_alignment_data = observe_validation
started = datetime.now(timezone.utc)
start = time.perf_counter()
arguments = ["-q", "-p", "no:cacheprovider",
    "tests/test_form_reference_validation.py::test_public_genome_resolvers_reuse_facts_but_preserve_possession_and_semantics",
    "--basetemp=" + str(OUTPUT / "temporary"), "--junitxml=" + str(OUTPUT / "tests.xml")]
with (OUTPUT / "output.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
    code = pytest.main(arguments)
write_json("observations.json", observations)
receipt = {"baseline": str(BASELINE), "pytest_arguments": arguments, "argv": sys.argv,
    "started_at": started.isoformat(), "finished_at": datetime.now(timezone.utc).isoformat(),
    "seconds": time.perf_counter() - start, "exit_code": int(code),
    "memory_limit_bytes": 20 * 1024**3, "single_file_limit_bytes": 4 * 1024**3,
    "wall_time_limit": None, "source_edits": False,
    "instrumentation": "In-memory wrapper captures data argument, calls the original validator without modification, and re-raises its original exception."}
write_json("receipt.json", receipt)
print(json.dumps({"exit_code": int(code), "seconds": receipt["seconds"], "validation_calls": len(observations),
                  "unresolved": [r["unresolved_against_scientific_union"] for r in observations]}, sort_keys=True))
for path in OUTPUT.iterdir():
    if path.is_file():
        path.chmod(0o444)
raise SystemExit(int(code))
