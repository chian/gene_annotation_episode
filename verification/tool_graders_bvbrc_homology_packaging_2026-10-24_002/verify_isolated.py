"""Verify wheel bytes and synthetic Homology calculations outside the checkout.

Input construction is a separate repository-only step. This program imports no
tests and resolves both application packages exclusively from the wheel extract.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

installed, original, evidence = map(lambda value: Path(value).resolve(), sys.argv[1:4])
expected_pin = sys.argv[4]
sys.dont_write_bytecode = True
assert not Path.cwd().is_relative_to(original)
assert sys.flags.isolated == 1
# -I removes script/cwd/PYTHONPATH. No checkout path is allowed as a fallback.
assert all(not Path(item).resolve().is_relative_to(original)
           or Path(item).resolve().is_relative_to(original / ".venv") for item in sys.path if item)
sys.path.insert(0, str(installed))

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_homology_inputs as native_inputs
from gene_annotation_episode import bvbrc_homology_metadata as native_metadata
from gene_annotation_episode import bvbrc_homology_grader as grader
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode.bvbrc_appservice_contracts import contract_schema
from gene_annotation_episode.bvbrc_homology_returns import homology_fact_sources
from gene_annotation_episode.bvbrc_homology_tool_info import homology_tool_contracts
from gene_annotation_episode.execution_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def forbidden(*args, **kwargs):
    raise AssertionError("pure installed calculation attempted file/network/native/parser I/O")


active_guard = False
denied_events = []


def audit(event, args):
    if active_guard and (event == "open" or event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn"))
                         or event in {"os.system", "os.fork", "os.listdir", "os.scandir", "os.chdir"}):
        denied_events.append(event)
        raise AssertionError("pure installed calculation attempted " + event)


sys.addaudithook(audit)


@contextmanager
def pure(*, forbid_parsers=False):
    global active_guard
    with ExitStack() as stack:
        for module, names in ((socket, ("socket", "create_connection", "getaddrinfo")),
                              (subprocess, ("Popen", "run", "call", "check_call", "check_output")),
                              (os, ("system", "popen"))):
            for name in names:
                stack.enter_context(patch.object(module, name, forbidden))
        if forbid_parsers:
            for module, names in (
                (adapter, ("consume_bundle", "read_homology_raw_json", "read_homology_processed_json",
                           "read_homology_tabular", "reconcile_homology_artifacts", "read_homology_metadata",
                           "bind_homology_metadata", "build_homology_sheet", "validate_pairwise_subject")),
                (native_inputs, ("read_homology_raw_json", "read_homology_processed_json", "read_homology_tabular",
                                 "reconcile_homology_artifacts")),
                (native_metadata, ("read_homology_metadata", "bind_homology_metadata")),
                (grader, ("build_homology_sheet",))):
                for name in names:
                    stack.enter_context(patch.object(module, name, forbidden))
        active_guard = True
        try:
            yield
        finally:
            active_guard = False


def load_case(directory):
    value = json.loads((directory / "SYNTHETIC_INPUTS.json").read_text())
    contents = {item["raw_artifact_ref"]: (directory / "native" / (item["role"] + ".bytes")).read_bytes()
                for item in value["bundle"]["artifacts"]}
    for artifact in value["bundle"]["artifacts"]:
        body = contents[artifact["raw_artifact_ref"]]
        assert hashlib.sha256(body).hexdigest() == artifact["sha256"]
        assert len(body) == artifact["byte_count"]
    if (directory / "supplied_sources").exists():
        for index, supplied in enumerate(value["supplied_values"]):
            raw_source = (directory / "supplied_sources" / (str(index) + ".json")).read_bytes()
            assert json.loads(raw_source) == supplied["value"]
            assert hashlib.sha256(raw_source).hexdigest() == supplied["evidence"]["content"]["sha256"]
            assert len(raw_source) == supplied["evidence"]["content"]["byte_count"]
    return value, contents


def consume(case):
    inputs, contents = case
    with pure():
        result = adapter.consume_bundle(inputs["bundle"], artifact_bytes=contents,
            supplied_values=inputs["supplied_values"], requested_form=inputs["requested_form"],
            parameters=inputs["parameters"])
    return result


# Compare every packaged application/module/resource byte and require every
# current .py and JSON package source to appear in the wheel.
package_hashes = {}
for package in ("gene_annotation_episode", "method_loop"):
    for path in sorted((installed / package).rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(installed)
        source = original / relative
        assert source.is_file(), str(relative)
        raw = path.read_bytes()
        assert raw == source.read_bytes(), str(relative)
        package_hashes[str(relative)] = hashlib.sha256(raw).hexdigest()
    for path in (original / package).rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".py", ".json"}:
            assert str(path.relative_to(original)) in package_hashes, str(path)
assert "bvbrc_homology_subject_binding.py" in adapter._DEPENDENCIES
dependency_hashes = {name: package_hashes["gene_annotation_episode/" + name] for name in adapter._DEPENDENCIES}
pin = adapter.implementation_sha256()
assert pin == expected_pin, (pin, expected_pin)
bound = bind_adapters([{"adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
                        "implementation_sha256": pin}])
assert bound[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)] == (adapter, pin)
try:
    bind_adapters([{"adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
                    "implementation_sha256": "0" * 64}])
except ValueError as error:
    assert str(error) == "appservice_adapter_implementation_conflict"
else:
    raise AssertionError("registry accepted a conflicting pin")
assert len(homology_fact_sources()) == 3
assignment = deepcopy(API_SERVICE_ASSIGNMENT_SCHEMA)
assignment["properties"]["request"] = BVBRCAppServiceService.request_schema
rows = homology_tool_contracts(resource_id="configured-fixture-api", assignment_schema=assignment)
assert [row["name"] for row in rows] == ["bvbrc.homology.database_identification", "bvbrc.homology.pairwise_correspondence"]
assert all(row["invocation_route"]["kind"] == "commission" for row in rows)
assert contract_schema("ResolvedInputs")
save(evidence / "PACKAGE_SOURCE_SHA256.json", package_hashes)
save(evidence / "INSTALLED_TOOL_CONTRACTS.json", rows)

database_dir = evidence / "retained_database"
database_case = load_case(database_dir)
expected = json.loads((database_dir / "EXPECTED_SYNTHETIC_RESULT.json").read_text())
database = consume(database_case)
save(database_dir / "INSTALLED_RESULT.json", database)
assert database == expected
assert len(database_case[1]) == 5
assert database["status"] == "ok"
assert database["facts"] == {"hits": 3, "no_hit_query": 0, "query_coverage": .6,
    "reference_coverage": .75, "weights": [
        {"function": "SYNTHETIC_FUNCTION_ALPHA", "weight": 2 / 3},
        {"function": "SYNTHETIC_FUNCTION_BETA", "weight": 1 / 3}], "missing": []}
save(database_dir / "SAVED_SHEET.json", database["sheet"])
saved_database = json.loads((database_dir / "SAVED_SHEET.json").read_text())
database_snapshot = deepcopy(saved_database)
with pure(forbid_parsers=True):
    rescored_database = grader.calculate_homology_scores(saved_database, database_model={"temperature_bits": 1})
save(database_dir / "INSTALLED_RECALCULATED_T1.json", rescored_database)
assert saved_database == database_snapshot
assert rescored_database == json.loads((database_dir / "EXPECTED_SYNTHETIC_RECALCULATED_T1.json").read_text())
kernel = rescored_database["queries"][0]["conditional_function_weights"]
assert kernel["parameters"]["temperature_bits"] == 1
assert kernel["unadjusted_probabilities"] == {"SYNTHETIC_FUNCTION_ALPHA": .8, "SYNTHETIC_FUNCTION_BETA": .2}

results, cases = {}, {}
for name in ("pairwise_valid", "pairwise_conflicting_subject_sha256", "pairwise_evalue_only"):
    case_dir = evidence / name
    cases[name] = load_case(case_dir)
    results[name] = consume(cases[name])
    save(case_dir / "INSTALLED_RESULT.json", results[name])
valid = results["pairwise_valid"]
expected_pairwise = {"hits": 1, "query_length": 15, "reference_length": 5, "pairs": 3,
    "query_coverage": 9 / 15, "reference_coverage": 3 / 5, "identity": 1,
    "native_evalue": 0.0, "missing": []}
assert valid["status"] == "ok", valid["diagnostics"]
assert valid["facts"] == expected_pairwise
union = valid["components"]["queries"][0]["pairwise_correspondence"]["union"]
assert union["counts"]["paired_query_positions"] == 9
assert union["counts"]["paired_reference_positions"] == 3
assert union["counts"]["distinct_residue_pairs"] == 3
assert union["denominators"] == {"query_length": 15, "reference_length": 5, "distinct_residue_pairs": 3}
assert [(p["query_start"], p["query_end"]) for p in union["pairs"]] == [(0, 3), (3, 6), (6, 9)]
assert [(p["reference_start"], p["reference_end"]) for p in union["pairs"]] == [(0, 1), (1, 2), (2, 3)]
assert valid["sheet"]["binding"]["c4_bundle"] == cases["pairwise_valid"][0]["bundle"]
assert valid["sheet"]["binding"]["supplied_values"] == cases["pairwise_valid"][0]["supplied_values"]

bad = results["pairwise_conflicting_subject_sha256"]
assert bad["status"] == "partial"
for field in ("pairs", "query_coverage", "reference_coverage", "identity"):
    assert bad["facts"][field] is None
for field in ("hits", "query_length", "reference_length", "native_evalue"):
    assert bad["facts"][field] == expected_pairwise[field]
assert "homology_subject_sequence_identity_conflict" in {row["code"] for row in bad["diagnostics"]}
assert "homology_subject_sequence_identity_conflict" in {row["reason_code"] for row in bad["missing_requirements"]}
assert bad["facts"]["missing"] == bad["missing_requirements"]
assert bad["sheet"]["queries"][0]["normalized_result"] == valid["sheet"]["queries"][0]["normalized_result"]
assert bad["sheet"]["artifact_statuses"] == valid["sheet"]["artifact_statuses"]
assert bad["sheet"]["binding"]["supplied_values"] == cases["pairwise_conflicting_subject_sha256"][0]["supplied_values"]
assert bad["sheet"]["binding"]["supplied_values"][0]["value"]["subject_binding"]["sequence_sha256"] == "0" * 64
assert bad["sheet"]["binding"]["subject_binding"] is None
assert bad["components"]["queries"][0]["pairwise_correspondence"] is None
assert cases["pairwise_valid"][1] == cases["pairwise_conflicting_subject_sha256"][1]
bad_source = cases["pairwise_conflicting_subject_sha256"][0]["supplied_values"][0]
source_bytes = (evidence / "pairwise_conflicting_subject_sha256/supplied_sources/0.json").read_bytes()
assert hashlib.sha256(source_bytes).hexdigest() == bad_source["evidence"]["content"]["sha256"]
assert len(source_bytes) == bad_source["evidence"]["content"]["byte_count"]

evalue_result = results["pairwise_evalue_only"]
assert evalue_result["status"] == "ok"
assert evalue_result["facts"] == {**expected_pairwise, "native_evalue": 1000000.0}
assert evalue_result["components"]["queries"][0]["pairwise_correspondence"]["union"] == union
assert "database E-value is not paired-sequence relevance" in valid["components"]["queries"][0]["pairwise_correspondence"]["meaning"]

pair_dir = evidence / "pairwise_valid"
save(pair_dir / "SAVED_SHEET.json", valid["sheet"])
saved_pairwise = json.loads((pair_dir / "SAVED_SHEET.json").read_text())
pairwise_snapshot = deepcopy(saved_pairwise)
with pure(forbid_parsers=True):
    rescored_pairwise = grader.calculate_homology_scores(saved_pairwise)
save(pair_dir / "INSTALLED_RECALCULATED.json", rescored_pairwise)
assert rescored_pairwise == valid["components"]
assert saved_pairwise == pairwise_snapshot

module_locations = {}
for name, module in list(sys.modules.items()):
    if name == "gene_annotation_episode" or name.startswith("gene_annotation_episode.") or name == "method_loop" or name.startswith("method_loop."):
        location = getattr(module, "__file__", None)
        if location:
            assert Path(location).is_relative_to(installed), (name, location)
            module_locations[name] = str(Path(location).relative_to(installed))
assert not any(name.startswith("test_bvbrc") for name in sys.modules)
assert denied_events == []
summary = {
    "status": "passed",
    "verification": "isolated extracted-wheel package and synthetic parser/calculator checks; not a full installed Workflow or live deployment",
    "scientific_implementation_sha256": pin,
    "expected_pin_matched": True,
    "dependency_sha256": dependency_hashes,
    "packaged_file_count_compared_to_current_source": len(package_hashes),
    "application_modules_loaded_only_from_wheel": module_locations,
    "isolated_python": True,
    "working_directory": str(Path.cwd()),
    "sys_path": list(sys.path),
    "tool_names": [row["name"] for row in rows],
    "static_registry_accepts_actual_pin_and_rejects_conflicting_pin": True,
    "database": {"artifact_count": len(database_case[1]), "exact_previous_result_match": True,
        "requested_facts": database["facts"], "exact_previous_saved_recalculation_match": True,
        "recalculated_temperature_bits": 1, "recalculated_weights": kernel["unadjusted_probabilities"]},
    "pairwise": {"requested_facts": valid["facts"], "union": union,
        "subject_sha256_conflict_status": bad["status"], "subject_sha256_conflict_facts": bad["facts"],
        "subject_sha256_conflict_diagnostics": bad["diagnostics"],
        "native_data_and_asserted_subject_retained": True,
        "evalue_only_variant_facts": evalue_result["facts"], "evalue_does_not_change_correspondence": True,
        "saved_sheet_exact_recalculation_match": True},
    "pure_calculation_guard": {"files_denied_by_audit": True, "sockets_and_subprocesses_disabled": True,
        "parsers_and_sheet_builders_disabled_during_recalculation": True, "attempted_denied_events": denied_events},
    "tests_imported_by_installed_process": False,
    "live_scientific_execution": False, "full_installed_workflow_verified": False,
}
save(evidence / "verification.json", summary)
print(json.dumps({"status": "passed", "scientific_implementation_sha256": pin,
                  "packaged_files": len(package_hashes), "database_facts": database["facts"],
                  "pairwise_facts": valid["facts"], "conflicting_subject_status": bad["status"],
                  "saved_database_weights_temperature_1": kernel["unadjusted_probabilities"],
                  "evalue_invariance": True}, sort_keys=True))
