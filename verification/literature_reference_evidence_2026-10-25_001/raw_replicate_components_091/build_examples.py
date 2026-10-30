"""Capture constructed raw-table examples and focused implementation evidence.

This script creates new evidence files once. It is not a goal, runtime rule,
paper acquisition path or controller action.
"""
from pathlib import Path
import builtins
import csv
import hashlib
import io
import json
import math
import os
import socket
import subprocess

from gene_annotation_episode.literature_rate_replicate_inputs import (
    HEADERS, read_rate_replicate_table,
)
from gene_annotation_episode.literature_rate_replicate_calculations import (
    summarize_rate_replicates, populate_rate_replicate_contrast,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PATHS = (
    "gene_annotation_episode/literature_rate_replicate_inputs.py",
    "gene_annotation_episode/literature_rate_replicate_calculations.py",
    "tests/test_literature_rate_replicates.py",
    "gene_annotation_episode/literature_rate_reader.py",
    "gene_annotation_episode/literature_rate_calculations.py",
    "gene_annotation_episode/literature_experimental_contracts.py",
    "tests/test_literature_rate_reader.py", "tests/test_literature_rate_calculations.py",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (OUT/name).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False, ensure_ascii=False)
        stream.write("\n")


def extraction(rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(HEADERS)
    for index, changes in enumerate(rows):
        row = dict(zip(HEADERS, ("Constructed preparation", "constructed assay",
            "reference", "buffer A", "oxygen consumption", "preparation", "A",
            "biological_preparations", f"observation-{index}", "10", "nmol/min", "synthetic")))
        row.update(changes)
        writer.writerow([row[name] for name in HEADERS])
    return read_rate_replicate_table({"source_ref": "constructed_source",
        "artifact_ref": "constructed_artifact", "text": stream.getvalue(),
        "representation": "synthetic_fixture", "delimiter": "\t"},
        expected_subject="Constructed preparation", expected_experiment="constructed assay")


before = {path: digest(ROOT/path) for path in PATHS}
unbalanced = extraction([{"value": "9"}, {"value": "11"},
    {"sampling_unit": "B", "value": "19"}, {"sampling_unit": "B", "value": "20"},
    {"sampling_unit": "B", "value": "21"}])
nested = summarize_rate_replicates(unbalanced, unit_model="iid_units")
assert nested["groups"][0]["measurement_count"] == 5
assert nested["groups"][0]["sampling_unit_count"] == 2
assert math.isclose(nested["groups"][0]["cells"]["mean"]["value"], .015)
assert math.isclose(nested["groups"][0]["cells"]["mean_se"]["value"], .005)
paired_rows = []
for index, (a, b) in enumerate(((10, 9), (20, 18), (30, 27))):
    paired_rows.extend(({"sampling_unit": f"unit-{index}", "value": str(a)},
                        {"sampling_unit": f"unit-{index}", "arm": "test", "value": str(b)}))
paired = extraction(paired_rows)
reference = {"arm": "reference", "condition": "buffer A", "endpoint": "oxygen consumption",
             "normalization": "preparation"}
test = dict(reference, arm="test")
kwargs = {"reference": reference, "test": test, "unit_model": "iid_units"}
paired_result = populate_rate_replicate_contrast(paired, **kwargs, dependence="paired_units")
assert math.isclose(paired_result["cells"]["rate_difference"]["value"], .002)
assert math.isclose(paired_result["cells"]["difference_se"]["value"], .001/math.sqrt(3))
independent_rows = [dict(row, sampling_unit="other-"+row["sampling_unit"])
                    if row.get("arm") == "test" else row for row in paired_rows]
independent = extraction(independent_rows)
independent_result = populate_rate_replicate_contrast(independent, **kwargs, dependence="independent")
assert math.isclose(independent_result["cells"]["difference_se"]["value"], math.sqrt((.01**2+.009**2)/3))
unknown_result = populate_rate_replicate_contrast(paired, **kwargs)
assert unknown_result["cells"]["difference_se"]["value"] is None
partial = summarize_rate_replicates(extraction([{"value": "10"}, {"value": "ND"},
    {"sampling_unit": "B", "value": "20"}]), unit_model="iid_units")
assert partial["groups"][0]["cells"]["mean"]["value"] is None
assert math.isclose(partial["groups"][0]["units"][1]["cells"]["mean"]["value"], .02)
examples = {"kind": "constructed engineering examples; no primary measurements",
    "unbalanced_technical_repeats": nested, "paired_preparations": paired_result,
    "independent_preparations": independent_result, "dependence_unknown": unknown_result,
    "nondetection_partial": partial}
write("WORKED_EXAMPLES.json", examples)
detached = json.loads((OUT/"WORKED_EXAMPLES.json").read_text())


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected file or network acquisition")


saved_open, saved_io_open, saved_connect = builtins.open, io.open, socket.create_connection
try:
    builtins.open = io.open = socket.create_connection = forbidden
    assert summarize_rate_replicates(detached["unbalanced_technical_repeats"]["extraction"],
                                     unit_model="iid_units") == nested
    assert populate_rate_replicate_contrast(detached["paired_preparations"]["summary"]["extraction"],
                                           **kwargs, dependence="paired_units") == paired_result
finally:
    builtins.open, io.open, socket.create_connection = saved_open, saved_io_open, saved_connect

command = [str(ROOT/".venv/bin/python"), "-m", "pytest", "-q",
    "tests/test_literature_rate_replicates.py", "tests/test_literature_rate_reader.py",
    "tests/test_literature_rate_calculations.py"]
process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
with (OUT/"TEST_RESULT.txt").open("x") as stream:
    stream.write(process.stdout)
    stream.write(process.stderr)
after = {path: digest(ROOT/path) for path in PATHS}
assert before == after
write("SOURCE_MANIFEST.json", {"files": before, "unchanged_during_examples_and_tests": True})
write("RESULTS.json", {"test_command": command, "test_exit_code": process.returncode,
    "constructed_examples": 5, "detached_reconstruction_with_file_network_access_forbidden": True,
    "source_hashes_unchanged_during_verification": before == after,
    "native_episode_integration": False, "new_catalog_operations": 0,
    "primary_papers_read": 0, "model_calls": 0, "completed_assay_specific_graders_claimed": 0,
    "controller_observations_added": 0})
assert process.returncode == 0
print(process.stdout.strip())
print("Five constructed examples retained; detached reconstruction passed with file/network access forbidden.")
