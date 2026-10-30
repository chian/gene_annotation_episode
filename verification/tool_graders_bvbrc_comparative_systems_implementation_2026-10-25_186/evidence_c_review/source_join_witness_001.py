"""Unchanged pinned producer on explicit synthetic repeated feature-side rows.

This creates a source-format fixture, not a service result or host admission.
No N/C runtime module imports this evidence utility.
"""
from pathlib import Path
from copy import deepcopy
import contextlib
import csv
import hashlib
import io
import json
import socket
import sys
import types
import urllib.request

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CONTRACT = BASE.parent / "tool_graders_bvbrc_comparative_systems_contract_2026-10-25_185"
FIXTURE = BASE / "candidate/tests/fixtures/bvbrc_comparative_systems_calculators/dependency_precision"
sys.dont_write_bytecode = True
sys.path.insert(0, str(CONTRACT / "vendor"))
import pandas as pd
import numpy as np
import requests

attempts = []
def forbidden(*args, **kwargs):
    attempts.append("forbidden_network_or_authentication")
    raise AssertionError(attempts[-1])

socket.create_connection = socket.getaddrinfo = forbidden
requests.sessions.Session.request = forbidden
urllib.request.urlopen = forbidden
stub = types.ModuleType("bvbrc_api")
for name in ("authenticateByEnv", "getGenomeIdsByGenomeGroup", "getFeatureDataFrame",
             "getSubsystemsDataFrame", "getPathwayDataFrame", "getDataForGenomes",
             "getQueryData", "getQueryDataText"):
    setattr(stub, name, forbidden)
sys.modules["bvbrc_api"] = stub
source = CONTRACT / "sources/comparative_systems_service/lib/compare_systems_lib.py"
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "052f74f971ee149bf5e07d1f6a6f965f9233d6a8f1795daae7a7b182b47b747f"
producer = types.ModuleType("pinned_subsystem_join_witness")
exec(compile(raw, str(source), "exec"), producer.__dict__)
input_path = CONTRACT / "source_executed_synthetic/discard_and_dependence/inputs.json"
inputs = json.loads(input_path.read_text())
inputs["classification"] = "source_executed_synthetic_feature_join_dependency_precision"
repeated = deepcopy(next(row for row in inputs["features"] if row["feature_id"] == "f1"))
repeated.update(product="Second synthetic feature-side product", patric_id="fig|second_feature_metadata",
                accession="second_synthetic_contig")
inputs["features"].append(repeated)
output = HERE / "source_executed_synthetic"
output.mkdir(exist_ok=True)
(output / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
supplied_calls = []
def supplied_response(base, query, headers):
    assert "/subsystem/" in base
    supplied_calls.append({"base": base, "query": query, "basis": "explicit_synthetic_response"})
    return json.dumps(inputs["subsystem_response"])
producer.getQueryDataText = supplied_response
features = pd.DataFrame(inputs["features"])
features["plfam_index"] = features["plfam_id"]
features["pgfam_index"] = features["pgfam_id"]
genomes = pd.DataFrame([{"genome_id": g, "genome_name": "Genome " + g} for g in inputs["genome_ids"]])
with (output / "stdout.txt").open("w") as out, (output / "stderr.txt").open("w") as err:
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = producer.run_subsystems(inputs["genome_ids"], {"feature": features}, "joined_metadata",
            str(output), genomes, types.SimpleNamespace(headers={"Authorization": "SYNTHETIC_NOT_A_TOKEN"}))
content = (output / "joined_metadata_subsystems_tables.json").read_bytes()
native = json.loads(content)
joined = list(csv.DictReader(io.StringIO(native["genes"]), delimiter="\t"))
summary = list(csv.DictReader(io.StringIO(native["subsystems"]), delimiter="\t"))[0]
repeats = [row for row in joined if row["id"] == "ss_f1"]
assert len(repeats) == 2
assert len({(r["genome_id"], r["feature_id"], r["subsystem_id"], r["role_id"]) for r in repeats}) == 1
assert len({r["product"] for r in repeats}) == 2
pairs = {(row["genome_id"], row["role_id"]) for row in joined}
assert len(pairs) == 3 and len(native["genome_ids"]) == 2
assert float(summary["role_conservation"]) == 75 == 100 * len(pairs) / (2 * 2)
assert attempts == []
FIXTURE.mkdir(exist_ok=True)
(FIXTURE / "joined_metadata_subsystems_tables.json").write_bytes(content)
receipt = {"basis": inputs["classification"], "live_service_execution": False,
    "producer_sha256": hashlib.sha256(raw).hexdigest(), "source_input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
    "fixture_sha256": hashlib.sha256(content).hexdigest(), "result": result,
    "environment": {"python": sys.version, "pandas": pd.__version__, "numpy": np.__version__},
    "network_or_authentication_attempts": attempts, "supplied_response_calls": supplied_calls,
    "joined_occurrences": len(joined), "repeated_association_rows": repeats,
    "genome_role_pairs": sorted(pairs), "reported_role_conservation_percent": float(summary["role_conservation"]),
    "recomputed_percent": 100 * len(pairs) / (2 * len(native["genome_ids"]))}
(HERE / "SOURCE_JOIN_WITNESS_001.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({key: receipt[key] for key in ("fixture_sha256", "joined_occurrences", "genome_role_pairs",
      "reported_role_conservation_percent", "recomputed_percent", "network_or_authentication_attempts")}, indent=2))
