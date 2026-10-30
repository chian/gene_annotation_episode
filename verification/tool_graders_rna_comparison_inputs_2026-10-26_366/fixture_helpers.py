"""Explicitly synthetic retained-sheet fixtures, never native measurements."""
from copy import deepcopy
import json

from gene_annotation_episode.rna_structure_contracts import (
    COORDINATE_SYSTEM, analyze_rna_input_sequence, make_rna_structure,
    native_uncertainty, unavailable_energy,
)
from gene_annotation_episode.rna_structure_topology import parse_rna_topology
from gene_annotation_episode.rna_structure_native import parse_rna_native_record, populate_rna_feature_sheet
from gene_annotation_episode.rna_structure_comparison_contracts import (
    RNA_COMPARISON_PARAMETERS_SCHEMA, comparison_digest, COMPARISON_METRICS,
)


def parameters():
    return {key: value["const"] for key, value in RNA_COMPARISON_PARAMETERS_SCHEMA["properties"].items()}


def feature(key="WT", sequence="GGGAAACCC", structure="(((...)))", *, energy=None,
        temperature=37.0, normalization="exact", origin="supplied_unknown"):
    request = {"schema": "rna_feature_input_v1", "record_key": key, "sequence_id": key,
        "sequence": sequence, "normalization": normalization, "subject_binding": None,
        "structure_id": key + "-structure", "dot_bracket": structure, "structure_origin": origin,
        "structure_source_ref": None if origin == "supplied_unknown" else "source_" + key,
        "energy_mode": "none" if energy is None else "viennarna_evaluate"}
    analysis, issues = analyze_rna_input_sequence(request, mode="supplied_features")
    topology = parse_rna_topology(structure, coordinate_system=COORDINATE_SYSTEM)
    issues += [{**row, "record_key": key} for row in topology["issues"]]
    metadata = make_rna_structure(request, structure, for_energy=energy is not None)
    model = None
    evaluation = unavailable_energy()
    if energy is not None:
        settings = {"temperature_c": temperature, "dangles": 2, "noLP": False, "noGU": False,
            "noGUclosure": False, "special_hp": True, "logML": False, "min_loop_size": 3,
            "max_bp_span": -1, "circ": False, "gquad": False}
        model = {"schema": "vienna_rna_effective_model_v1", "model_key": key + "-synthetic-model",
            "selected": {"schema": "vienna_rna_model_spec_v1", **settings,
                "hard_constraints": None, "soft_constraints": None,
                "parameters": {"kind": "turner2004", "operand_role": None}},
            "engine": "ViennaRNA", "engine_version": "2.7.0", "effective_settings": settings,
            "other_observed_settings": [], "parameter_artifact": {"relative_path": "synthetic.par",
                "sha256": "a" * 64, "size_bytes": 123}, "parameter_load_return": 1, "parameter_save_return": 1}
        evaluation = {"value": energy, "numeric_text": str(energy), "unit": "kcal/mol", "state": "present",
            "reason": None, "structure_key": metadata["structure_key"], "engine": "ViennaRNA",
            "engine_version": "2.7.0", "model_key": model["model_key"]}
    native = {"schema": "rna_native_record_v1", "operation": "analyze_rna_secondary_structure_features",
        "mode": "supplied_features", "record_key": key, "input": request, "analysis_sequence": analysis,
        "structure": metadata, "topology": topology, "native_mfe": unavailable_energy(),
        "native_evaluation": evaluation, "native_uncertainty": native_uncertainty(), "model": model,
        "status": "partial" if any(i["code"] != "no_sequence_supplied" for i in issues) else "complete", "issues": issues}
    parsed = parse_rna_native_record(json.dumps(native).encode(), format="rna_native_record_json_v1",
        expected_mode="supplied_features", record_key=key)
    return populate_rna_feature_sheet(parsed, record_key=key, original_input=request,
        model_metadata=None, subject_binding=None)


def descriptor(sheet):
    key = sheet["record_key"]
    return {"schema": "rna_structure_saved_sheet_input_v1", "result_receipt_key": "rna_result_receipt:" + comparison_digest(key),
        "handoff_ref": "handoff-" + key, "source_ref": "source-" + key,
        "bundle_artifact_ref": "bundle-" + key, "sheet_artifact_ref": "sheet-" + key,
        "sheet_sha256": comparison_digest(sheet), "record_key": key,
        "operation": sheet["operation"], "mode": sheet["mode"]}


def member(sheet, *, key=None):
    return {"member_id": key or sheet["record_key"], "kind": "saved_sheet", "saved_input": descriptor(sheet)}


def supplied(sheet):
    return {"original_sheet": sheet, "original_bundle_software": None, "received_failure": None}


def absent(key, state="not_tested"):
    return {"member_id": key, "kind": "declared_absent", "state": state}


def failure(key="D"):
    return {"family": "failure", "record_key": key, "row_key": key + ":failure:0", "source_ref": None,
        "operation": "analyze_rna_secondary_structure_features", "mode": "supplied_features",
        "result_receipt_key": "rna_result_receipt:" + comparison_digest(key), "issue_ordinal": 0,
        "issue": {"stage": "native", "code": "rna_native_failed", "record_key": key,
            "field": "/native_evaluation", "index": None, "artifact_role": "native_result"}}


def site(key="selected", member_id="WT", positions=(), intervals=(), regions=()):
    return {"selection_id": key, "coordinate_member_id": member_id, "positions": list(positions),
        "intervals": [list(i) for i in intervals], "unpaired_region_keys": list(regions), "combine": "set_union"}


def comparison(variant="V", *, correspondence=None, selections=(), pairs=False, energy=None, key=None):
    return {"comparison_id": key or "compare-" + variant, "variant_member_id": variant,
        "correspondence": deepcopy(correspondence), "site_selections": list(selections),
        "calculate_pair_changes": pairs, "energy": deepcopy(energy)}


def energy_request(tolerance=None, normalization="none"):
    return {"quantity": "native_evaluation", "normalization": normalization,
        "compatibility_profile": "vienna_2_7_retained_linear_model_v1", "baseline_absolute_tolerance": tolerance}


def selector(members, comparisons, *, baseline="WT", scan=None, projections=None):
    return {"version": "native_rna_structure_comparison_selector_v1", "acquisition": "retained_inputs_only",
        "question": {"kind": "scan" if scan is not None else "pairwise", "baseline_member_id": baseline,
            "membership": members, "comparisons": comparisons, "scan": scan}, "parameters": parameters(),
        "projections": projections if projections is not None else [{"projection_id": "selected-structures",
            "family": "structures", "member_ids": [baseline], "fields": ["dot_bracket"]}]}


def scan_request(energy=None, selections=()):
    return {"scan_id": "scan", "population_unit": "unique_analyzed_sequence_variant",
        "baseline_in_rank": True, "member_order": "as_declared", "energy": energy,
        "topology_selection_ids": list(selections)}


def pair_inputs(*, a=None, b=None, request=None, selections=(), pairs=False, energy=None):
    a = feature() if a is None else a
    b = feature("V", "GGGAAAUCC") if b is None else b
    request = {"kind": "substitution_only", "substitutions": [{"index": 6, "baseline_symbol": "C", "variant_symbol": "U"}]} if request is None else request
    selected = selector([member(a), member(b)], [comparison(b["record_key"], correspondence=request,
        selections=selections, pairs=pairs, energy=energy)], baseline=a["record_key"])
    return selected, {a["record_key"]: supplied(a), b["record_key"]: supplied(b)}


def empty_components(sheet):
    """No-calculation fixture: selected structures only, no topology/energy work."""
    return {"schema": "rna_structure_comparison_components_v1", "calculator_version": "rna_comparison_calculators_v1",
        "input_sheet_sha256": comparison_digest(sheet), "parameters": deepcopy(sheet["parameters"]),
        "comparisons": [{"comparison_id": row["comparison_id"], "baseline_member_id": row["baseline_member_id"],
            "variant_member_id": row["variant_member_id"], "correspondence": deepcopy(row["correspondence"]),
            "resolved_selections": deepcopy(row["resolved_selections"]), "all_site_rows": [], "all_pair_rows": [],
            "components": [], "pairing_change_state": "not_requested", "energy": None, "issues": []}
            for row in sheet["comparisons"]], "scan": None,
        "used_input_paths": [], "unused_input_paths": [], "issues": []}
