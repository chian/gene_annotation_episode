"""Export complete actual pure-provider examples and verify saved replay.

Run with the repository's absolute .venv Python from the staging directory:
  .../.venv/bin/python ../gene-provider-verification/export_examples.py examples_001
Each output directory is new; earlier evidence is never replaced.
"""
from __future__ import annotations

import builtins
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
STAGING = HERE.parent / "staging"
REPO = STAGING.parents[2]
assert Path.cwd() == STAGING, "Run from the real staging directory."
assert Path(sys.executable) == REPO / ".venv/bin/python"
assert len(sys.argv) == 2 and "/" not in sys.argv[1]
target = HERE / sys.argv[1]
target.mkdir(exist_ok=False)
spec = importlib.util.spec_from_file_location("gene_provider_verification_fixture",
                                            STAGING / "tests/test_bvbrc_gene_tree_provider.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

for module in (fixture.provider, fixture.grader, fixture.common_inputs,
               fixture.common_contracts, fixture.common_grader, fixture.formats,
               fixture.calculators, fixture.calculation_contracts):
    assert Path(module.__file__).resolve().parent == STAGING / "gene_annotation_episode"


raw_inputs = {}


def retain_raw(data, source_ref, artifact_ref):
    digest = hashlib.sha256(data).hexdigest()
    record = raw_inputs.setdefault(digest, {"data": data, "identities": []})
    assert record["data"] == data
    identity = {"source_ref": source_ref, "artifact_ref": artifact_ref}
    if identity not in record["identities"]:
        record["identities"].append(identity)


original_read = fixture.read
original_evidence = fixture.evidence


def read_and_retain(data, name, reader):
    result = original_read(data, name, reader)
    retain_raw(data, result["artifact"]["source_ref"], result["artifact"]["raw_artifact_ref"])
    return result


def evidence_and_retain(value, name, pointer=""):
    result = original_evidence(value, name, pointer)
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    retain_raw(data, result["content"]["source_ref"], result["content"]["artifact_ref"])
    return result


fixture.read = read_and_retain
fixture.evidence = evidence_and_retain


def save(name, value):
    (target / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


cases = []
for name, args in (("ordinary_hand_case", fixture.ordinary_args()),
                   ("concatenated_loci", fixture.concatenated_args()),
                   ("j_to_x_exact_digests", fixture.transformed_args()),
                   ("tree_without_alignment", fixture.tree_args())):
    extraction = fixture.provider.extract_gene_tree_sheet(**args)
    assert extraction["value"] is not None, extraction
    sheet = extraction["value"]
    params = fixture.tree_parameters(sheet)
    if sheet["documents"]["analyses"][0]["aligned_document_id"] is not None:
        params["alignment_requests"] = fixture.alignment_parameters(sheet)["alignment_requests"]
        params["original_coverage_population_ids"] = [params["alignment_requests"][0]["population_id"]]
    cases.append({"name": name, "evidence_kind": "synthetic fixture; no live or Store custody claim",
                  "input": args, "extraction": extraction, "calculation_parameters": params,
                  "components": fixture.grader.calculate_gene_tree(sheet, params)})

native_files = []
for name in fixture.XML_NAMES:
    path = fixture.NATIVE / name
    data = path.read_bytes()
    args = fixture.tree_args(data, xml=True, name="retained-official-example/" + name)
    extraction = fixture.provider.extract_gene_tree_sheet(**args)
    assert extraction["value"] is not None, extraction
    sheet = extraction["value"]
    params = fixture.tree_parameters(sheet)
    cases.append({"name": name, "evidence_kind": "retained official repository native XML; no live or task custody claim",
                  "input": args, "extraction": extraction, "calculation_parameters": params,
                  "components": fixture.grader.calculate_gene_tree(sheet, params)})
    native_files.append({"path": str(path.relative_to(REPO)), "sha256": hashlib.sha256(data).hexdigest(),
                         "byte_count": len(data)})

raw_required_args = deepcopy(cases[4]["input"])
raw_required_args["parameters"]["raw_tree_required_for_branch_facts"] = True
raw_required = fixture.provider.extract_gene_tree_sheet(**raw_required_args)
assert raw_required["value"] is not None
params = fixture.tree_parameters(raw_required["value"])
raw_required_components = fixture.grader.calculate_gene_tree(raw_required["value"], params)
assert raw_required_components["trees"][0]["tip_count"]["value"] == 17
assert raw_required_components["trees"][0]["branch_length_sum"]["value"] is None
cases.append({"name": "retained_xml_with_raw_tree_required", "evidence_kind": "retained official repository native XML; caller explicitly requires unavailable raw tree",
              "input": raw_required_args, "extraction": raw_required, "calculation_parameters": params,
              "components": raw_required_components})

partial_args = fixture.tree_args()
bad = fixture.read(b">a\nAAA\n>b\nAA\n", "synthetic/bad-alignment", "aligned_fasta")
partial_args["documents"]["reads"].append(bad)
if bad["result"]["value"] is not None:
    partial_args["documents"]["parsed"]["store"]["alignments"].append(bad["result"]["value"])
partial = fixture.provider.extract_gene_tree_sheet(**partial_args)
assert partial["status"] == "partial" and partial["value"] is not None
params = fixture.tree_parameters(partial["value"])
cases.append({"name": "malformed_independent_alignment", "evidence_kind": "synthetic failure fixture",
              "input": partial_args, "extraction": partial, "calculation_parameters": params,
              "components": fixture.grader.calculate_gene_tree(partial["value"], params)})

wrong_args = fixture.ordinary_args()
wrong_args["assembly"]["locus_bindings"][0]["input_members"].pop()
wrong = fixture.provider.extract_gene_tree_sheet(**wrong_args)
assert wrong["status"] == "invalid" and wrong["value"] is None
save("invalid_complete_locus_binding.json", {"evidence_kind": "synthetic wrong membership fixture",
                                            "input": wrong_args, "extraction": wrong})

# Serialize and reload first; all calls within this block use supplied objects.
saved = json.loads(json.dumps(cases, allow_nan=False))
def forbidden(*args, **kwargs):
    raise AssertionError("saved GeneTree replay attempted I/O")

with ExitStack() as guards:
    for obj, attr in ((builtins, "open"), (io, "open"), (os, "open"),
                      (Path, "read_bytes"), (Path, "read_text"),
                      (socket, "socket"), (socket, "create_connection"),
                      (urllib.request, "urlopen"), (subprocess, "run"), (subprocess, "Popen")):
        guards.enter_context(patch.object(obj, attr, forbidden))
    for case in saved:
        sheet = case["extraction"]["value"]
        assert fixture.provider.validate_gene_tree_sheet(sheet) == sheet
        assert fixture.grader.calculate_gene_tree(sheet, case["calculation_parameters"]) == case["components"]

metrics = []
for case in saved:
    save(case["name"] + ".json", case)
    components = case["components"]
    row = {"name": case["name"], "evidence_kind": case["evidence_kind"], "extraction_status": case["extraction"]["status"],
           "tip_counts": [tree["tip_count"]["value"] for tree in components["trees"]],
           "branch_length_sums": [tree["branch_length_sum"] for tree in components["trees"]],
           "native_support_count": len(case["extraction"]["value"]["support_observations"]),
           "locus_count": len(case["extraction"]["value"]["loci"]),
           "unknown_support_methods": all(s["method"] == "native_unknown" for s in case["extraction"]["value"]["support_observations"]),
           "io_disabled_replay_equal": True}
    if components["alignments"]:
        aligned = components["alignments"][0]
        row.update(cell_count=aligned["cell_count"]["value"], gap_cells=aligned["gap_cells"]["value"],
                   gap_fraction=aligned["gap_fraction"]["value"], canonical_cells=aligned["canonical_cells"]["value"],
                   ambiguity_cells=aligned["ambiguity_cells"]["value"])
    metrics.append(row)
save("METRICS.json", metrics)

raw_directory = target / "raw_inputs"
raw_directory.mkdir()
raw_manifest = []
for digest, record in sorted(raw_inputs.items()):
    path = raw_directory / (digest + ".bin")
    path.write_bytes(record["data"])
    raw_manifest.append({"path": str(path.relative_to(target)), "sha256": digest,
                         "byte_count": len(record["data"]), "identities": record["identities"]})
save("RAW_INPUTS.json", raw_manifest)

controls = [REPO / "AGENTS.md", REPO / "docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md",
    REPO / "research/tool_grader_inventory_2026-10-24/WORK_STATUS.json",
    Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")]
handoffs = REPO / "verification/tool_graders_bvbrc_phylogeny_provider_handoffs_2026-10-24"
controls += [handoffs / name for name in ("IMPLEMENTATION_WORKLOADS_001.md", "ADDITIVE_CONTRACT.md",
                                        "ACCEPTANCE_001.md", "PROVIDER_CLARIFICATIONS_001.md")]
controls += [STAGING / "gene_annotation_episode" / name for name in (
    "bvbrc_gene_tree_inputs.py", "bvbrc_gene_tree_grader.py", "bvbrc_phylogeny_common_inputs.py",
    "bvbrc_phylogeny_common_contracts.py", "bvbrc_phylogeny_common_grader.py", "phylogeny_calculators.py",
    "phylogeny_calculation_contracts.py", "phylogeny_formats.py", "phylogeny_format_contracts.py")]
controls += [STAGING / "tests/test_bvbrc_gene_tree_provider.py", Path(__file__).resolve()]
save("MANIFEST.json", {"python": sys.executable, "cwd": str(STAGING), "native_inputs": native_files,
    "retained_raw_input_count": len(raw_manifest),
    "control_and_code_hashes": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                "byte_count": path.stat().st_size} for path in controls],
    "claims": {"actual_provider_shared_path": True, "saved_sheet_replay_no_io": True,
               "live_scientific_execution": False, "authenticated_original_task_custody": False,
               "complete_episode_communication": False}})
print(json.dumps({"examples": len(saved), "saved_replay_equal": True, "output": str(target),
                  "ordinary_gap_fraction": metrics[0]["gap_fraction"],
                  "native_tip_counts": [row["tip_counts"][0] for row in metrics if row["name"].endswith(".xml")]}, sort_keys=True))
