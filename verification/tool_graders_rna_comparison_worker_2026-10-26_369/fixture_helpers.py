"""Synthetic E-to-D boundaries; these identities do not prove episode authority."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.rna_structure_comparison_contracts import SITE_TRANSITIONS, PAIR_RELATIONS
from gene_annotation_episode.rna_structure_comparison_worker import PLAN_VERSION, comparison_calculation_key
from gene_annotation_episode.rna_structure_comparison_publication import RESOLVED_VERSION
from gene_annotation_episode.rna_structure_result_views import result_receipt_key

b = importlib.import_module("verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")
REPO = Path(__file__).resolve().parents[2]
KEY = "rna_comparison_receipt:" + digest({"run_id": "synthetic-run", "episode_id": "synthetic-results", "operation_key": "collect-0"})


def raw(value):
    return (canonical(value) + "\n").encode()


def sha(value):
    return hashlib.sha256(raw(value)).hexdigest()


def projection(family, **changes):
    defaults = {
        "energy_comparison": {"comparison_ids": ["compare-V"], "metrics": ["baseline_native_energy", "variant_native_energy", "energy_delta"],
            "include_order": True, "include_tolerance_band": False},
        "structures": {"member_ids": ["WT", "V"], "fields": ["dot_bracket"]},
        "position_changes": {"comparison_id": "compare-V", "selection_id": "selected", "transitions": list(SITE_TRANSITIONS)},
        "pair_changes": {"comparison_ids": ["compare-V"], "relations": list(PAIR_RELATIONS)},
        "comparison_counts": {"comparison_ids": ["compare-V"], "selection_ids": ["selected"],
            "metrics": ["pair_symmetric_difference_count", "changed_site_count", "changed_site_fraction"], "include_pairing_change_state": True},
        "scan_energy": {"scan_id": "scan", "metrics": ["baseline_rank_start", "baseline_rank_end", "minimum_selected_energy", "baseline_energy_above_minimum"],
            "include_rank_class": True},
        "scan_members": {"scan_id": "scan", "members": {"kind": "exceptions", "predicates": ["lower_than_baseline"]},
            "fields": ["energy", "rank_start", "rank_end", "eligibility"], "order": "declared", "limit": None},
        "scan_sites": {"scan_id": "scan", "selection_ids": ["selected"], "metrics": ["decidable_variant_count", "changed_variant_fraction"]},
    }
    return {"projection_id": family, "family": family, **defaults[family], **changes}


def resolved(sheet, projections=None):
    data = {o["member_id"]: {k: deepcopy(o[k]) for k in ("original_sheet", "original_bundle_software", "received_failure")}
        for o in sheet["operands"] if o["state"] != "alias"}
    question = deepcopy(sheet["selected_question"])
    receipts, refs = {}, []
    for member in question["membership"]:
        mid, kind = member["member_id"], member["kind"]
        if kind not in ("saved_sheet", "received_failure"):
            continue
        receipts[mid] = {"run_id": "synthetic-original", "episode_id": "synthetic-" + mid,
            "operation_key": "original-collect", "fixture_only": True}
        field = "saved_input" if kind == "saved_sheet" else "failure"
        record = member[field]
        record["result_receipt_key"] = result_receipt_key(receipts[mid])
        if kind == "saved_sheet":
            record["sheet_sha256"] = sha(data[mid]["original_sheet"])
            record["sheet_artifact_ref"] = "artifact_" + record["sheet_sha256"]
            refs += [record[k] for k in ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")]
        else:
            data[mid]["received_failure"] = deepcopy(record)
            if record["source_ref"] is not None:
                refs.append(record["source_ref"])
    selected = {"version": "native_rna_structure_comparison_selector_v1", "acquisition": "retained_inputs_only",
        "question": question, "parameters": deepcopy(sheet["parameters"]),
        "projections": projections or [projection("scan_energy") if question["kind"] == "scan" else projection("structures")]}
    return selected, {"version": RESOLVED_VERSION, "data": data, "original_receipts": receipts,
        "selected_references": list(dict.fromkeys(refs))}


def pair(projections=None, *, temperature=37.0, normalization="none"):
    sheet = b.pair(b.feature(energy=-3.0), b.feature("V", "GGGAAAUCC", energy=-2.0, temperature=temperature),
        energy=b.energy_request(normalization=normalization))
    return resolved(sheet, projections or [projection("energy_comparison"), projection("comparison_counts"), projection("structures")])


def scan(projections=None, *, missing=True):
    sheet = b.scan(extra_members=[b.absent("NS", "not_supplied"), b.absent("NT")] if missing else [],
        extra_operands={"NS": b.blank(), "NT": b.blank()} if missing else None)
    return resolved(sheet, projections or [projection("scan_energy"), projection("scan_members")])


def plan(directory, selector, operands):
    directory.mkdir(parents=True, exist_ok=True)
    payload = raw(operands["data"])
    (directory / "input-data.json").write_bytes(payload)
    return {"version": PLAN_VERSION, "selector": deepcopy(selector), "input_data": {
        "path": str(directory / "input-data.json"), "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)},
        "result_receipt_key": KEY, "calculation_key": comparison_calculation_key(selector, operands["data"]), "directory": str(directory)}


def load(path):
    return json.loads(path.read_bytes())


def keys(value):
    if isinstance(value, dict):
        return set(value).union(*(keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(keys(child) for child in value))
    return set()
