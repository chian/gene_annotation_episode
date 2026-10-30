"""Save the complete real six-query sheet and independently replayed calculator."""
import hashlib
import json
from pathlib import Path
import runpy
import socket
import subprocess
import sys

from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores
from gene_annotation_episode.rfam_batch_table import parse_rfam_report_membership


ROOT = Path(__file__).resolve().parents[2]
helpers = runpy.run_path(str(ROOT / "tests/test_rfam_batch_table.py"))
case = helpers["native_case"]()
report_content, report_capture = helpers["report_case"]()
output = Path(sys.argv[1])
output.mkdir()


def forbidden(*args, **kwargs):
    raise AssertionError("No acquisition, native execution, or resource choice is allowed here")


socket.socket = socket.create_connection = subprocess.Popen = forbidden
membership = parse_rfam_report_membership(report_content, capture=report_capture)
result = helpers["parse"](case, report_membership=membership)


def write(name, value):
    path = output / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


saved = {"native.input_identity.json": result["input_identity"], "native.capture.json": result["capture"],
    "native.report_membership.json": membership, "native.parse_result.json": result,
    "native.sheet.json": result["sheet"]}
hashes = {name: write(name, value) for name, value in saved.items()}
reloaded = json.loads((output / "native.sheet.json").read_text())
calculation = calculate_infernal_search_scores(reloaded, parameters={"hit_scope": "reported"})
hashes["native.calculation.json"] = write("native.calculation.json", calculation)
changed = calculate_infernal_search_scores(reloaded, parameters={"hit_scope": "included"})
hashes["native.included.calculation.json"] = write("native.included.calculation.json", changed)
assert hashlib.sha256((output / "native.sheet.json").read_bytes()).hexdigest() == hashes["native.sheet.json"]
assert all(row["reported_set_complete"] for row in result["query_population"])
print("query\tscore_bits\tevalue\tquery_span_nt\tquery_length_nt\tquery_fraction\tmodel_fraction\tstrand")
for row in calculation["hits"]:
    c = row["components"]
    print("\t".join(map(str, [row["sequence"]["name"], c["bitscore"], c["evalue"], c["sequence_span_length"],
        row["denominators"]["sequence_length"], c["sequence_span_fraction"], c["model_span_fraction"], row["strand"]])))
write("manifest.json", {"evidence_kind": "retained_native_remote_results", "new_live_jobs": 0,
    "native_table_sha256": hashlib.sha256(case[0]).hexdigest(), "original_input_sha256": hashlib.sha256(case[1]).hexdigest(),
    "native_report_sha256": hashlib.sha256(report_content).hexdigest(), "output_sha256": hashes,
    "episode_communication_verified_by_this_workload": False,
    "saved_sheet_replay": "socket creation, connection and subprocess launch forbidden"})
