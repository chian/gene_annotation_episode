"""Verification-only actual P/N/D/C example; never imported by runtime."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request
from unittest.mock import patch

BASE = Path(__file__).resolve().parent.parent
CANDIDATE = BASE / "candidate"
sys.path[:0] = [str(CANDIDATE), str(CANDIDATE / "tests")]

from test_bvbrc_comparative_systems_bundle import adapter, field, form, measurement, reference_arguments, save_validate
from gene_annotation_episode import bvbrc_comparative_systems_bundle_resolution as resolution
from gene_annotation_episode import bvbrc_comparative_systems_native as native
from gene_annotation_episode import bvbrc_comparative_systems_sheet as builder
from gene_annotation_episode import bvbrc_comparative_systems_data_inputs as data
from gene_annotation_episode import bvbrc_comparative_systems_calculators as calculations


def forbidden(*args, **kwargs):
    raise AssertionError("scientific work or external acquisition forbidden during saved validation")


args = reference_arguments()
args["requested_form"] = form(measurement(args, availability="available_value"),
    field("retained_ratio", {"kind": "ratio", "component_id": "retained_pathway_percent"}, "available_value"),
    field("later_ratio", {"kind": "ratio", "component_id": "later_pathway_percent"}, "available_complete_population"),
    field("native_reference", {"kind": "ratio", "component_id": "native_reference"}, "available_complete_population"),
    field("later_reference", {"kind": "ratio", "component_id": "later_reference"}, "available_complete_population"),
    field("active_genomes", {"kind": "computed_measurement", "component_id": "unambiguous_active_genomes"}, "available_value"))
before = deepcopy(args)
with patch.object(socket, "create_connection", forbidden), patch.object(urllib.request, "urlopen", forbidden), patch.object(subprocess, "Popen", forbidden):
    result = adapter.consume_bundle(**args)
assert args == before and result["status"] == "ok"
patches = [(resolution, name) for name in ("parse_comparative_systems_document", "build_comparative_systems_sheet",
    "extract_comparative_systems_data_inputs", "calculate_comparative_systems_components")]
patches += [(native, "parse_comparative_systems_document"), (builder, "build_comparative_systems_sheet"),
            (data, "extract_comparative_systems_data_inputs"), (calculations, "calculate_comparative_systems_components"),
            (socket, "create_connection"), (urllib.request, "urlopen"), (subprocess, "Popen"),
            (Path, "read_bytes"), (Path, "read_text")]
from contextlib import ExitStack
with ExitStack() as stack:
    for owner, name in patches:
        stack.enter_context(patch.object(owner, name, forbidden))
    save_validate(result, args)

facts = result["facts"]
value = lambda key: facts[key]["values"][0]
assert value("native")["value"] == 75
assert value("retained_ratio")["output"]["value"] == 75
assert value("later_ratio")["numerator"]["value"] == 4
assert value("later_ratio")["denominator"]["value"] == 9
assert value("native_reference")["output"]["value"] == 2 / 4
assert value("later_reference")["output"]["value"] == 3 / 4
assert value("active_genomes")["value"] == 0

out = BASE / "evidence_p"
raw_dir = out / "filled_native_bytes"
raw_dir.mkdir(exist_ok=True)
byte_files = {}
for key, raw in args["artifact_bytes"].items():
    filename = hashlib.sha256(key.encode()).hexdigest() + ".bytes"
    path = raw_dir / filename
    path.write_bytes(raw)
    byte_files[key] = {"path": str(path.relative_to(out)), "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}
inputs = {key: value for key, value in args.items() if key != "artifact_bytes"}
inputs["byte_files"] = byte_files
inputs["classification"] = "Synthetic qualified wrappers and offline source-executed native fixtures; no live ComparativeSystems run or actual host admission"
(out / "FILLED_PROVIDER_INPUT_001.json").write_text(json.dumps(inputs, indent=2, sort_keys=True, allow_nan=False) + "\n")
(out / "FILLED_PROVIDER_RESULT_001.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
receipt = {"classification": inputs["classification"], "status": result["status"],
    "adapter_implementation_sha256": adapter.implementation_sha256(), "saved_validation": "passed with parsing, extraction, calculation, acquisition, process and file reads forbidden",
    "native_percent": value("native")["value"], "retained_percent": value("retained_ratio")["output"]["value"],
    "later_percent": value("later_ratio")["output"]["value"], "later_operands": [4, 9],
    "native_reference_operands": [2, 4], "later_reference_operands": [3, 4], "measured_active_genome_count": 0,
    "native_population_id": value("retained_ratio")["genome_population_id"],
    "later_population_id": value("later_ratio")["genome_population_id"],
    "reference_release": result["sheet"]["reference_memberships"][0]["release"],
    "files": [{"path": name, "sha256": hashlib.sha256((out / name).read_bytes()).hexdigest()}
              for name in ("FILLED_PROVIDER_INPUT_001.json", "FILLED_PROVIDER_RESULT_001.json")]}
(out / "FILLED_PROVIDER_RECEIPT_001.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
