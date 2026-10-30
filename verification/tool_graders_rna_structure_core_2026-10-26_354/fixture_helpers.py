"""Explicit synthetic producer fixtures; these do not execute ViennaRNA."""
from copy import deepcopy
import json
import os
from pathlib import Path

from gene_annotation_episode.rna_structure_contracts import (
    COORDINATE_SYSTEM, OPERATIONS, analyze_rna_input_sequence, issue,
    make_rna_structure, native_uncertainty, unavailable_energy,
)
from gene_annotation_episode.rna_structure_topology import parse_rna_topology
from gene_annotation_episode.rna_structure_native import parse_rna_native_record, populate_rna_feature_sheet

PARAMETERS = {"schema": "rna_calculation_parameters_v1",
    "topology": {"long_stem_min_pairs": 3, "include_exterior_in_loop_size_statistics": False},
    "pair_composition": {"accepted_ordered_pair_types": ["AU", "UA", "GC", "CG", "GU", "UG"], "denominator": "unambiguous_pairs"},
    "energy": {"normalization": "per_nt"}}


def feature_input(structure="(((...)))", sequence="GGGAAACCC", **changes):
    return {"schema": "rna_feature_input_v1", "record_key": "synthetic-rna", "sequence_id": None,
        "sequence": sequence, "normalization": "exact", "subject_binding": None,
        "structure_id": None, "dot_bracket": structure, "structure_origin": "supplied_unknown",
        "structure_source_ref": None, "energy_mode": "none", **changes}


def prediction_input(sequence="GGGAAACCC", **changes):
    return {"schema": "rna_prediction_input_v1", "record_key": "synthetic-rna", "sequence_id": None,
        "sequence": sequence, "normalization": "exact", "subject_binding": None, **changes}


def model_spec():
    return {"schema": "vienna_rna_model_spec_v1", "temperature_c": 37.0, "dangles": 2,
        "noLP": False, "noGU": False, "noGUclosure": False, "special_hp": True,
        "logML": False, "min_loop_size": 3, "max_bp_span": -1, "circ": False, "gquad": False,
        "hard_constraints": None, "soft_constraints": None,
        "parameters": {"kind": "turner2004", "operand_role": None}}


def model():
    selected = model_spec()
    return {"schema": "vienna_rna_effective_model_v1", "model_key": "synthetic-model",
        "selected": selected, "engine": "ViennaRNA", "engine_version": "synthetic-version",
        "effective_settings": {key: value for key, value in selected.items()
            if key not in ("schema", "hard_constraints", "soft_constraints", "parameters")},
        "other_observed_settings": [{"name": "salt", "value": None, "state": "unavailable"}],
        "parameter_artifact": {"relative_path": "effective-parameters.par", "sha256": "0" * 64, "size_bytes": 1},
        "parameter_load_return": 1, "parameter_save_return": 1}


def native_record(request, *, prediction_structure=None, energy=None, native_failure=None):
    """Serialize synthetic returned facts, visibly distinct from native execution."""
    mode = "mfe_prediction" if request["schema"] == "rna_prediction_input_v1" else "supplied_features"
    analysis, errors = analyze_rna_input_sequence(request, mode=mode)
    dot_bracket = prediction_structure if mode == "mfe_prediction" else request["dot_bracket"]
    requested = mode == "mfe_prediction" or request.get("energy_mode") == "viennarna_evaluate"
    structure = make_rna_structure(request, dot_bracket, for_energy=requested) if dot_bracket is not None else None
    topology = parse_rna_topology(dot_bracket, coordinate_system=COORDINATE_SYSTEM) if dot_bracket is not None else None
    if topology is not None:
        errors.extend({**row, "record_key": request["record_key"]} for row in topology["issues"])
    energies = {"native_mfe": unavailable_energy(), "native_evaluation": unavailable_energy()}
    selected_field = "native_mfe" if mode == "mfe_prediction" else "native_evaluation"
    effective = None
    if requested:
        if native_failure is not None:
            energies[selected_field] = unavailable_energy("failed", native_failure,
                structure_key=structure["structure_key"] if structure else None)
            errors.append(issue(native_failure, stage="native", record_key=request["record_key"], field="/" + selected_field))
        elif energy is not None:
            effective = model()
            energies[selected_field] = {"value": energy, "numeric_text": repr(energy), "unit": "kcal/mol", "state": "present",
                "reason": None, "structure_key": structure["structure_key"], "engine": "ViennaRNA",
                "engine_version": effective["engine_version"], "model_key": effective["model_key"]}
        else:
            raise AssertionError("Synthetic fixture must declare the native energy or failure")
    status = "complete" if all(row["code"] == "no_sequence_supplied" for row in errors) else "partial"
    if topology is None:
        status = "failed"
    return {"schema": "rna_native_record_v1", "operation": OPERATIONS[mode], "mode": mode,
        "record_key": request["record_key"], "input": deepcopy(request), "analysis_sequence": analysis,
        "structure": structure, "topology": topology, **energies,
        "native_uncertainty": native_uncertainty(), "model": effective, "status": status, "issues": errors}


def parsed(record):
    return parse_rna_native_record(json.dumps(record).encode(), format="rna_native_record_json_v1",
        expected_mode=record["mode"], record_key=record["record_key"])


def feature_sheet(request=None, *, native=None):
    request = feature_input() if request is None else request
    result = parsed(native_record(request)) if native is None else native
    return populate_rna_feature_sheet(result, record_key=request["record_key"], original_input=request,
        model_metadata=None, subject_binding=None)


def retain(name, **values):
    directory = os.environ.get("RNA_CORE_EXAMPLE_OUTPUT")
    if directory:
        path = Path(directory)
        path.mkdir(exist_ok=True)
        (path / (name + ".json")).write_text(json.dumps(values, indent=2, sort_keys=True, allow_nan=False) + "\n")
